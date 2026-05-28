from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

from survey_dag_extractor.issues import ValidationIssue
from survey_dag_extractor.model import SurveyModel

KNOWN_OPERATORS = {"=", "!=", ">", "<", ">=", "<=", "in", "not_in", "contains", "AND", "OR", "NOT", "TRUE", "FALSE"}
LOGICAL_OPERATORS = {"AND", "OR", "NOT"}


def validate_model(model: SurveyModel, schema_path: Path | None = None) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    issues.extend(_schema_issues(model, schema_path))
    issues.extend(_reference_issues(model))
    issues.extend(_condition_issues(model))
    issues.extend(_priority_issues(model))
    issues.extend(_routing_issues(model))
    return _renumber(issues)


def _schema_issues(model: SurveyModel, schema_path: Path | None) -> list[ValidationIssue]:
    schema_file = schema_path or Path(__file__).resolve().parents[1] / "schemas" / "canonical_survey_dag_schema.json"
    with schema_file.open("r", encoding="utf-8") as file:
        schema = json.load(file)
    validator = Draft7Validator(schema)
    issues = []
    for error in sorted(validator.iter_errors(model.document), key=lambda err: list(err.path)):
        issues.append(
            ValidationIssue(
                id="ISSUE_PENDING",
                severity="error",
                type="schema_invalid",
                message=error.message,
                evidence={"path": list(error.path)},
            )
        )
    return issues


def _reference_issues(model: SurveyModel) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not model.entry_node:
        issues.append(ValidationIssue("ISSUE_PENDING", "error", "missing_entry_node", "DAG has no entry_node."))
    elif not model.node_exists(model.entry_node):
        issues.append(
            ValidationIssue(
                "ISSUE_PENDING",
                "error",
                "missing_entry_node",
                f"Entry node {model.entry_node} does not exist.",
                node_id=model.entry_node,
            )
        )
    for terminal_id in model.terminal_ids:
        if terminal_id not in model.terminals:
            issues.append(
                ValidationIssue(
                    "ISSUE_PENDING",
                    "error",
                    "missing_terminal_node",
                    f"Terminal node {terminal_id} is listed in dag.terminal_nodes but is not defined.",
                    node_id=terminal_id,
                )
            )
    for edge in _safe_edges(model):
        edge_id = _edge_id(edge)
        source = _edge_node_id(edge, "source")
        target = _edge_node_id(edge, "target")
        if source is not None and not model.node_exists(source):
            issues.append(
                ValidationIssue(
                    "ISSUE_PENDING",
                    "error",
                    "missing_edge_source",
                    f"Edge {edge_id} source {source} does not exist.",
                    node_id=source,
                    edge_id=edge_id,
                )
            )
        if target is not None and not model.node_exists(target):
            issues.append(
                ValidationIssue(
                    "ISSUE_PENDING",
                    "error",
                    "missing_edge_target",
                    f"Edge {edge_id} target {target} does not exist.",
                    node_id=target,
                    edge_id=edge_id,
                )
            )
    return issues


def _condition_issues(model: SurveyModel) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for edge in _safe_edges(model):
        edge_id = _edge_id(edge)
        condition = edge.get("condition")
        for op in _condition_operators(condition):
            if op == "UNPARSED":
                issues.append(
                    ValidationIssue(
                        "ISSUE_PENDING",
                        "error",
                        "unparsed_condition",
                        f"Edge {edge_id} has an unparsed condition.",
                        edge_id=edge_id,
                        evidence={"condition": condition},
                    )
                )
            elif not isinstance(op, str) or op not in KNOWN_OPERATORS:
                issues.append(
                    ValidationIssue(
                        "ISSUE_PENDING",
                        "error",
                        "unknown_condition_operator",
                        f"Edge {edge_id} uses unknown condition operator {op}.",
                        edge_id=edge_id,
                        evidence={"operator": op, "condition": condition},
                    )
                )
        for variable in _condition_variables(condition):
            if variable not in model.questions:
                issues.append(
                    ValidationIssue(
                        "ISSUE_PENDING",
                        "error",
                        "missing_condition_variable",
                        f"Edge {edge_id} condition references missing question {variable}.",
                        node_id=variable,
                        edge_id=edge_id,
                    )
                )
    return issues


def _condition_operators(condition: Any) -> list[Any]:
    if condition is None or not isinstance(condition, list) or not condition:
        return []
    if not isinstance(condition[0], str):
        return [condition[0]]
    operators = [condition[0]]
    if condition[0] in LOGICAL_OPERATORS:
        for item in condition[1:]:
            operators.extend(_condition_operators(item))
    return operators


def _condition_variables(condition: Any) -> set[str]:
    if condition is None or not isinstance(condition, list) or not condition:
        return set()
    op = condition[0]
    if isinstance(op, str) and op in {"=", "!=", ">", "<", ">=", "<=", "in", "not_in", "contains"} and len(condition) >= 2:
        return {condition[1]} if isinstance(condition[1], str) else set()
    if not isinstance(op, str) or op not in LOGICAL_OPERATORS:
        return set()
    variables: set[str] = set()
    for item in condition[1:]:
        variables |= _condition_variables(item)
    return variables


def _priority_issues(model: SurveyModel) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    by_source: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    for edge in _safe_edges(model):
        source = _edge_node_id(edge, "source")
        priority = edge.get("priority")
        if source is None or type(priority) is not int:
            continue
        by_source[source][priority].append(_edge_id(edge))
    for source, priorities in by_source.items():
        for priority, edge_ids in priorities.items():
            if len(edge_ids) > 1:
                issues.append(
                    ValidationIssue(
                        "ISSUE_PENDING",
                        "error",
                        "duplicate_priority",
                        f"Source {source} has duplicate priority {priority}.",
                        node_id=source,
                        evidence={"priority": priority, "edge_ids": edge_ids},
                    )
                )
    return issues


def _routing_issues(model: SurveyModel) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    issues.extend(_missing_outgoing_issues(model))
    issues.extend(_reachability_issues(model))
    issues.extend(_cycle_issues(model))
    issues.extend(_dead_end_issues(model))
    issues.extend(_fallthrough_issues(model))
    return issues


def _missing_outgoing_issues(model: SurveyModel) -> list[ValidationIssue]:
    issues = []
    for node_id in model.questions:
        if not _outgoing_edges(model, node_id):
            issues.append(
                ValidationIssue(
                    "ISSUE_PENDING",
                    "error",
                    "missing_outgoing_edge",
                    f"Question {node_id} has no outgoing edge.",
                    node_id=node_id,
                )
            )
    return issues


def _reachable_nodes(model: SurveyModel) -> set[str]:
    if not model.entry_node or not model.node_exists(model.entry_node):
        return set()
    visited: set[str] = set()
    stack = [model.entry_node]
    while stack:
        node_id = stack.pop()
        if node_id in visited:
            continue
        visited.add(node_id)
        for edge in _outgoing_edges(model, node_id):
            target = _edge_node_id(edge, "target")
            if target is not None and model.node_exists(target):
                stack.append(target)
    return visited


def _reachability_issues(model: SurveyModel) -> list[ValidationIssue]:
    reachable = _reachable_nodes(model)
    issues = []
    for node_id in sorted(model.node_ids - reachable):
        if node_id == model.entry_node:
            continue
        issues.append(
            ValidationIssue(
                "ISSUE_PENDING",
                "error",
                "orphan_node",
                f"{node_id} is not reachable from the entry node.",
                node_id=node_id,
                evidence={"entry_node": model.entry_node, "incoming_edges": [_edge_id(edge) for edge in _incoming_edges(model, node_id)]},
            )
        )
    return issues


def _cycle_issues(model: SurveyModel) -> list[ValidationIssue]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cycles: list[list[str]] = []

    def visit(node_id: str, path: list[str]) -> None:
        if node_id in visiting:
            start = path.index(node_id)
            cycles.append(path[start:] + [node_id])
            return
        if node_id in visited or model.is_terminal(node_id):
            return
        visiting.add(node_id)
        for edge in _outgoing_edges(model, node_id):
            target = _edge_node_id(edge, "target")
            if target is not None and model.node_exists(target):
                visit(target, path + [target])
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in sorted(model.node_ids):
        if node_id not in visited and not model.is_terminal(node_id):
            visit(node_id, [node_id])

    return [
        ValidationIssue(
            "ISSUE_PENDING",
            "error",
            "cycle_detected",
            "Graph contains a directed cycle.",
            node_id=cycle[0],
            evidence={"cycle": cycle},
        )
        for cycle in cycles
    ]


def _dead_end_issues(model: SurveyModel) -> list[ValidationIssue]:
    issues = []
    terminal_ids = set(model.terminal_ids)
    can_reach_terminal = _nodes_that_can_reach_terminal(model)
    for node_id in sorted(_reachable_nodes(model)):
        if node_id not in terminal_ids and node_id not in can_reach_terminal:
            issues.append(
                ValidationIssue(
                    "ISSUE_PENDING",
                    "error",
                    "dead_end",
                    f"{node_id} has no path to a terminal node.",
                    node_id=node_id,
                )
            )
    return issues


def _nodes_that_can_reach_terminal(model: SurveyModel) -> set[str]:
    reverse_edges: dict[str, set[str]] = defaultdict(set)
    for edge in _safe_edges(model):
        source = _edge_node_id(edge, "source")
        target = _edge_node_id(edge, "target")
        if source is not None and target is not None and model.node_exists(source) and model.node_exists(target):
            reverse_edges[target].add(source)

    visited: set[str] = set()
    stack = [terminal_id for terminal_id in model.terminal_ids if model.node_exists(terminal_id)]
    while stack:
        node_id = stack.pop()
        if node_id in visited:
            continue
        visited.add(node_id)
        stack.extend(reverse_edges.get(node_id, set()) - visited)
    return visited


def _fallthrough_issues(model: SurveyModel) -> list[ValidationIssue]:
    issues = []
    for source in sorted({source for edge in _safe_edges(model) if (source := _edge_node_id(edge, "source")) is not None}):
        outgoing = _outgoing_edges(model, source)
        has_branch = any(edge.get("type") == "branch" for edge in outgoing)
        has_fallthrough = any(edge.get("type") == "fallthrough" and edge.get("condition") is None for edge in outgoing)
        if has_branch and not has_fallthrough:
            issues.append(
                ValidationIssue(
                    "ISSUE_PENDING",
                    "error",
                    "missing_fallthrough",
                    f"Branching source {source} has no fallthrough edge.",
                    node_id=source,
                    evidence={"outgoing_edges": [_edge_id(edge) for edge in outgoing]},
                )
            )
    return issues


def _outgoing_edges(model: SurveyModel, node_id: str) -> list[dict[str, Any]]:
    return sorted(
        (edge for edge in _safe_edges(model) if _edge_node_id(edge, "source") == node_id),
        key=lambda edge: (_priority_sort_value(edge), _edge_id(edge)),
    )


def _incoming_edges(model: SurveyModel, node_id: str) -> list[dict[str, Any]]:
    return sorted(
        (edge for edge in _safe_edges(model) if _edge_node_id(edge, "target") == node_id),
        key=_edge_id,
    )


def _safe_edges(model: SurveyModel) -> list[dict[str, Any]]:
    return [edge for edge in model.edges if isinstance(edge, dict)]


def _priority_sort_value(edge: dict[str, Any]) -> int:
    priority = edge.get("priority")
    return priority if type(priority) is int else 999


def _edge_id(edge: dict[str, Any]) -> str:
    edge_id = edge.get("id", "<unknown>")
    return edge_id if isinstance(edge_id, str) else str(edge_id)


def _edge_node_id(edge: dict[str, Any], key: str) -> str | None:
    node_id = edge.get(key)
    return node_id if isinstance(node_id, str) else None


def _renumber(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    return [
        ValidationIssue(
            id=f"ISSUE_{index:04d}",
            severity=issue.severity,
            type=issue.type,
            message=issue.message,
            node_id=issue.node_id,
            edge_id=issue.edge_id,
            evidence=issue.evidence,
            recommendation_ids=issue.recommendation_ids,
            status=issue.status,
        )
        for index, issue in enumerate(issues, start=1)
    ]
