from __future__ import annotations

from typing import Any

from survey_dag_extractor.model import SurveyModel


def evaluate_condition(condition: Any, state: dict[str, Any]) -> bool:
    if condition is None:
        return True
    if not isinstance(condition, list) or not condition:
        return bool(condition)
    op = condition[0]
    if op == "TRUE":
        return True
    if op == "FALSE":
        return False
    if op == "AND":
        return all(evaluate_condition(part, state) for part in condition[1:])
    if op == "OR":
        return any(evaluate_condition(part, state) for part in condition[1:])
    if op == "NOT":
        return not evaluate_condition(condition[1], state)
    binary_ops = {"=", "!=", ">", "<", ">=", "<=", "contains", "in", "not_in"}
    if op not in binary_ops:
        raise ValueError(f"Unknown condition operator: {op}")
    left = state.get(condition[1])
    right = condition[2]
    if op == "=":
        return left == right
    if op == "!=":
        return left != right
    if op == ">":
        return left is not None and left > right
    if op == "<":
        return left is not None and left < right
    if op == ">=":
        return left is not None and left >= right
    if op == "<=":
        return left is not None and left <= right
    if op == "contains":
        return right in left if isinstance(left, list) else left == right
    if op == "in":
        return left in right if isinstance(right, list) else left == right
    if op == "not_in":
        return left not in right if isinstance(right, list) else left != right
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
        matching = [edge for edge in model.outgoing_edges(current) if evaluate_condition(edge.get("condition"), responses)]
        if not matching:
            return {"path": path, "edge_ids": edge_ids, "terminated": False, "reason": "no_matching_edge"}
        edge = matching[0]
        edge_ids.append(edge["id"])
        current = edge["target"]
        path.append(current)
    return {"path": path, "edge_ids": edge_ids, "terminated": False, "reason": "max_steps"}


def generate_coverage_tests(model: SurveyModel, coverage_target: str = "edge") -> dict[str, Any]:
    paths = _enumerate_paths(model)
    tests = []
    covered_nodes: set[str] = set()
    covered_edges: set[str] = set()
    for index, path_info in enumerate(paths, start=1):
        covered_nodes.update(path_info["path"])
        covered_edges.update(path_info["edge_ids"])
        tests.append(
            {
                "id": f"TEST_{index:04d}",
                "responses": {},
                "expected_path": path_info["path"],
                "covered_edges": path_info["edge_ids"],
            }
        )
    total_nodes = len(model.node_ids)
    total_edges = len(model.edges)
    return {
        "survey_id": model.survey_id,
        "coverage_target": coverage_target,
        "tests": tests,
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
