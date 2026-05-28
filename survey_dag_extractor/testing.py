from __future__ import annotations

from typing import Any

from survey_dag_extractor.model import SurveyModel


def evaluate_condition(condition: Any, state: dict[str, Any]) -> bool:
    if condition is None:
        return True
    if not isinstance(condition, list) or not condition:
        return bool(condition)
    op = condition[0]
    if not isinstance(op, str):
        raise ValueError(f"Unknown condition operator: {op}")
    if op == "TRUE":
        _require_arity(condition, 1, op)
        return True
    if op == "FALSE":
        _require_arity(condition, 1, op)
        return False
    if op == "AND":
        _require_min_arity(condition, 2, op)
        return all(evaluate_condition(part, state) for part in condition[1:])
    if op == "OR":
        _require_min_arity(condition, 2, op)
        return any(evaluate_condition(part, state) for part in condition[1:])
    if op == "NOT":
        _require_arity(condition, 2, op)
        return not evaluate_condition(condition[1], state)
    binary_ops = {"=", "!=", ">", "<", ">=", "<=", "contains", "in", "not_in"}
    if op not in binary_ops:
        raise ValueError(f"Unknown condition operator: {op}")
    _require_arity(condition, 3, op)
    if not isinstance(condition[1], str):
        raise ValueError(f"Malformed condition for operator {op}: variable must be a string")
    left = state.get(condition[1])
    right = condition[2]
    if op == "=":
        return left == right
    if op == "!=":
        return left != right
    if op == ">":
        return _compare(left, right, op)
    if op == "<":
        return _compare(left, right, op)
    if op == ">=":
        return _compare(left, right, op)
    if op == "<=":
        return _compare(left, right, op)
    if op == "contains":
        if left is None:
            return False
        if not isinstance(left, list):
            raise ValueError("Unsupported operands for condition operator contains: left operand must be a list")
        return right in left
    if op == "in":
        if not isinstance(right, list):
            raise ValueError("Unsupported operands for condition operator in: right operand must be a list")
        return left in right
    if op == "not_in":
        if not isinstance(right, list):
            raise ValueError("Unsupported operands for condition operator not_in: right operand must be a list")
        return left not in right
    raise AssertionError(f"Unhandled condition operator: {op}")


def simulate_route(model: SurveyModel, responses: dict[str, Any], max_steps: int = 1000) -> dict[str, Any]:
    if not model.entry_node:
        return {"path": [], "edge_ids": [], "terminated": False, "reason": "missing_entry_node"}
    current = model.entry_node
    path = [current]
    edge_ids: list[str] = []
    for _ in range(max_steps):
        if model.is_terminal(current):
            return {"path": path, "edge_ids": edge_ids, "terminated": True, "reason": "terminal"}
        edge = None
        for candidate in model.outgoing_edges(current):
            if evaluate_condition(candidate.get("condition"), responses):
                edge = candidate
                break
        if edge is None:
            return {"path": path, "edge_ids": edge_ids, "terminated": False, "reason": "no_matching_edge"}
        edge_ids.append(_edge_id(edge))
        current = edge["target"]
        path.append(current)
    return {"path": path, "edge_ids": edge_ids, "terminated": False, "reason": "max_steps"}


def generate_coverage_tests(model: SurveyModel, coverage_target: str = "edge") -> dict[str, Any]:
    paths = _enumerate_paths(model)
    tests = []
    covered_nodes: set[str] = set()
    covered_edges: set[str] = set()
    unverified_paths = []
    for index, path_info in enumerate(paths, start=1):
        try:
            responses = _synthesize_path_responses(model, path_info)
        except ValueError as error:
            unverified_paths.append(
                {"path": path_info["path"], "edge_ids": path_info["edge_ids"], "reason": str(error)}
            )
            continue
        if responses is None:
            unverified_paths.append(
                {"path": path_info["path"], "edge_ids": path_info["edge_ids"], "reason": "unsynthesizable"}
            )
            continue
        try:
            simulation = simulate_route(model, responses)
        except ValueError as error:
            unverified_paths.append(
                {"path": path_info["path"], "edge_ids": path_info["edge_ids"], "reason": str(error)}
            )
            continue
        if simulation["path"] != path_info["path"] or simulation["edge_ids"] != path_info["edge_ids"]:
            unverified_paths.append(
                {
                    "path": path_info["path"],
                    "edge_ids": path_info["edge_ids"],
                    "actual_path": simulation["path"],
                    "actual_edge_ids": simulation["edge_ids"],
                    "reason": "simulation_mismatch",
                }
            )
            continue
        covered_nodes.update(simulation["path"])
        covered_edges.update(simulation["edge_ids"])
        tests.append(
            {
                "id": f"TEST_{index:04d}",
                "responses": responses,
                "expected_path": simulation["path"],
                "covered_edges": simulation["edge_ids"],
            }
        )
    total_nodes = len(model.node_ids)
    total_edges = len(model.edges)
    edge_ids = {_edge_id(edge) for edge in model.edges if isinstance(edge, dict)}
    return {
        "survey_id": model.survey_id,
        "coverage_target": coverage_target,
        "tests": tests,
        "unverified_paths": unverified_paths,
        "uncovered_edges": sorted(edge_ids - covered_edges),
        "coverage": {
            "node_percent": _percent(len(covered_nodes), total_nodes),
            "edge_percent": _percent(len(covered_edges), total_edges),
        },
    }


def _enumerate_paths(model: SurveyModel) -> list[dict[str, Any]]:
    if not model.entry_node:
        return []
    paths: list[dict[str, Any]] = []

    def walk(node_id: str, path: list[str], edge_ids: list[str]) -> None:
        if model.is_terminal(node_id):
            paths.append({"path": path, "edge_ids": edge_ids})
            return
        outgoing = model.outgoing_edges(node_id)
        if not outgoing:
            paths.append({"path": path, "edge_ids": edge_ids})
            return
        for edge in outgoing:
            if edge["target"] in path:
                paths.append({"path": path + [edge["target"]], "edge_ids": edge_ids + [edge["id"]]})
            else:
                walk(edge["target"], path + [edge["target"]], edge_ids + [edge["id"]])

    walk(model.entry_node, [model.entry_node], [])
    return paths


def _percent(numerator: int, denominator: int) -> int:
    if denominator == 0:
        return 100
    return round((numerator / denominator) * 100)


def _require_arity(condition: list[Any], expected: int, op: str) -> None:
    if len(condition) != expected:
        operand_count = expected - 1
        raise ValueError(f"Malformed condition for operator {op}: expected {operand_count} operands")


def _require_min_arity(condition: list[Any], minimum: int, op: str) -> None:
    if len(condition) < minimum:
        operand_count = minimum - 1
        raise ValueError(f"Malformed condition for operator {op}: expected at least {operand_count} operands")


def _compare(left: Any, right: Any, op: str) -> bool:
    if left is None:
        return False
    try:
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == ">=":
            return left >= right
        if op == "<=":
            return left <= right
    except TypeError as error:
        raise ValueError(f"Unsupported operands for condition operator {op}") from error
    raise AssertionError(f"Unhandled comparison operator: {op}")


def _synthesize_path_responses(model: SurveyModel, path_info: dict[str, Any]) -> dict[str, Any] | None:
    responses: dict[str, Any] = {}
    edges_by_id = {_edge_id(edge): edge for edge in model.edges if isinstance(edge, dict)}
    for edge_id in path_info["edge_ids"]:
        edge = edges_by_id.get(edge_id)
        if edge is None:
            return None
        if not _synthesize_condition(edge.get("condition"), responses):
            return None
        for prior_edge in _higher_priority_edges(model, edge):
            if not _synthesize_condition_false(prior_edge.get("condition"), responses):
                return None
        if not _conditions_select_edge(model, edge, responses):
            return None
    return responses


def _higher_priority_edges(model: SurveyModel, edge: dict[str, Any]) -> list[dict[str, Any]]:
    higher_priority = []
    for candidate in model.outgoing_edges(edge["source"]):
        if _edge_id(candidate) == _edge_id(edge):
            return higher_priority
        higher_priority.append(candidate)
    return higher_priority


def _conditions_select_edge(model: SurveyModel, edge: dict[str, Any], responses: dict[str, Any]) -> bool:
    selected_edge_id = _edge_id(edge)
    for candidate in model.outgoing_edges(edge["source"]):
        condition_matches = evaluate_condition(candidate.get("condition"), responses)
        if _edge_id(candidate) == selected_edge_id:
            return condition_matches
        if condition_matches:
            return False
    return False


def _synthesize_condition(condition: Any, responses: dict[str, Any]) -> bool:
    if condition is None:
        return True
    if not isinstance(condition, list) or not condition:
        return bool(condition)
    op = condition[0]
    if not isinstance(op, str):
        return False
    if op == "TRUE":
        return len(condition) == 1
    if op == "FALSE":
        return False
    if op == "AND":
        if len(condition) < 2:
            return False
        return all(_synthesize_condition(part, responses) for part in condition[1:])
    if op == "OR":
        if len(condition) < 2:
            return False
        for part in condition[1:]:
            candidate = dict(responses)
            if _synthesize_condition(part, candidate):
                responses.clear()
                responses.update(candidate)
                return True
        return False
    if op == "NOT":
        return len(condition) == 2 and _synthesize_condition_false(condition[1], responses)
    if len(condition) != 3 or not isinstance(condition[1], str):
        return False
    variable = condition[1]
    right = condition[2]
    if variable in responses:
        try:
            if evaluate_condition(condition, responses):
                return True
        except ValueError:
            pass
    if op == "=":
        return _assign_response(responses, variable, right)
    if op == "!=":
        return _assign_response(responses, variable, _different_value(right))
    if op == ">":
        value = _numeric_offset(right, 1)
        return value is not None and _assign_response(responses, variable, value)
    if op == "<":
        value = _numeric_offset(right, -1)
        return value is not None and _assign_response(responses, variable, value)
    if op == ">=":
        return isinstance(right, (int, float)) and _assign_response(responses, variable, right)
    if op == "<=":
        return isinstance(right, (int, float)) and _assign_response(responses, variable, right)
    if op == "in":
        return isinstance(right, list) and bool(right) and _assign_response(responses, variable, right[0])
    if op == "not_in":
        return isinstance(right, list) and _assign_response(responses, variable, _different_value(right))
    if op == "contains":
        return _assign_response(responses, variable, [right])
    return False


def _synthesize_condition_false(condition: Any, responses: dict[str, Any]) -> bool:
    if condition is None:
        return False
    if not isinstance(condition, list) or not condition:
        return not bool(condition)
    op = condition[0]
    if not isinstance(op, str):
        return False
    if op == "TRUE":
        return False
    if op == "FALSE":
        return len(condition) == 1
    if op == "AND":
        if len(condition) < 2:
            return False
        for part in condition[1:]:
            candidate = dict(responses)
            if _synthesize_condition_false(part, candidate):
                responses.clear()
                responses.update(candidate)
                return True
        return False
    if op == "OR":
        if len(condition) < 2:
            return False
        synthesized = _synthesize_or_equalities_false(condition, responses)
        if synthesized is not None:
            return synthesized
        return all(_synthesize_condition_false(part, responses) for part in condition[1:])
    if op == "NOT":
        return len(condition) == 2 and _synthesize_condition(condition[1], responses)
    if len(condition) != 3 or not isinstance(condition[1], str):
        return False
    variable = condition[1]
    right = condition[2]
    if variable in responses:
        try:
            if not evaluate_condition(condition, responses):
                return True
        except ValueError:
            pass
    if op == "=":
        return _assign_response(responses, variable, _different_value(right))
    if op == "!=":
        return _assign_response(responses, variable, right)
    if op == ">":
        return isinstance(right, (int, float)) and _assign_response(responses, variable, right)
    if op == "<":
        return isinstance(right, (int, float)) and _assign_response(responses, variable, right)
    if op == ">=":
        value = _numeric_offset(right, -1)
        return value is not None and _assign_response(responses, variable, value)
    if op == "<=":
        value = _numeric_offset(right, 1)
        return value is not None and _assign_response(responses, variable, value)
    if op == "in":
        return isinstance(right, list) and _assign_response(responses, variable, _different_value(right))
    if op == "not_in":
        return isinstance(right, list) and bool(right) and _assign_response(responses, variable, right[0])
    if op == "contains":
        existing = responses.get(variable)
        if isinstance(existing, list) and right not in existing:
            return True
        if variable not in responses:
            return _assign_response(responses, variable, [])
        return False
    return False


def _assign_response(responses: dict[str, Any], variable: str, value: Any) -> bool:
    if variable not in responses:
        responses[variable] = value
        return True
    return responses[variable] == value


def _synthesize_or_equalities_false(condition: list[Any], responses: dict[str, Any]) -> bool | None:
    variable = None
    disallowed_values = []
    for part in condition[1:]:
        if not isinstance(part, list) or len(part) != 3 or part[0] != "=" or not isinstance(part[1], str):
            return None
        if variable is None:
            variable = part[1]
        elif variable != part[1]:
            return None
        disallowed_values.append(part[2])
    if variable is None:
        return None
    if variable in responses:
        try:
            return not evaluate_condition(condition, responses)
        except ValueError:
            return False
    return _assign_response(responses, variable, _different_value(disallowed_values))


def _numeric_offset(value: Any, offset: int) -> int | float | None:
    if type(value) is bool or not isinstance(value, (int, float)):
        return None
    return value + offset


def _different_value(value: Any) -> Any:
    if isinstance(value, list):
        for candidate in (0, 1, 2, "OTHER", True, False, None):
            if candidate not in value:
                return candidate
        return "__OTHER__"
    if type(value) is bool:
        return not value
    if isinstance(value, (int, float)):
        return value + 1
    if isinstance(value, str):
        return f"{value}_OTHER"
    if value is None:
        return "__NON_NULL__"
    return "__OTHER__"


def _edge_id(edge: dict[str, Any]) -> str:
    edge_id = edge.get("id", "")
    return edge_id if isinstance(edge_id, str) else str(edge_id)
