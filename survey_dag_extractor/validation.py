from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator

from survey_dag_extractor.issues import ValidationIssue
from survey_dag_extractor.model import SurveyModel

KNOWN_OPERATORS = {"=", "!=", ">", "<", ">=", "<=", "in", "not_in", "contains", "AND", "OR", "NOT", "TRUE", "FALSE"}


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
    for edge in model.edges:
        if not model.node_exists(edge["source"]):
            issues.append(
                ValidationIssue(
                    "ISSUE_PENDING",
                    "error",
                    "missing_edge_source",
                    f"Edge {edge['id']} source {edge['source']} does not exist.",
                    node_id=edge["source"],
                    edge_id=edge["id"],
                )
            )
        if not model.node_exists(edge["target"]):
            issues.append(
                ValidationIssue(
                    "ISSUE_PENDING",
                    "error",
                    "missing_edge_target",
                    f"Edge {edge['id']} target {edge['target']} does not exist.",
                    node_id=edge["target"],
                    edge_id=edge["id"],
                )
            )
    return issues


def _condition_issues(model: SurveyModel) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for edge in model.edges:
        condition = edge.get("condition")
        for op in _condition_operators(condition):
            if op == "UNPARSED":
                issues.append(
                    ValidationIssue(
                        "ISSUE_PENDING",
                        "error",
                        "unparsed_condition",
                        f"Edge {edge['id']} has an unparsed condition.",
                        edge_id=edge["id"],
                        evidence={"condition": condition},
                    )
                )
            elif op not in KNOWN_OPERATORS:
                issues.append(
                    ValidationIssue(
                        "ISSUE_PENDING",
                        "error",
                        "unknown_condition_operator",
                        f"Edge {edge['id']} uses unknown condition operator {op}.",
                        edge_id=edge["id"],
                        evidence={"operator": op, "condition": condition},
                    )
                )
        for variable in model.condition_variables(condition):
            if variable not in model.questions:
                issues.append(
                    ValidationIssue(
                        "ISSUE_PENDING",
                        "error",
                        "missing_condition_variable",
                        f"Edge {edge['id']} condition references missing question {variable}.",
                        node_id=variable,
                        edge_id=edge["id"],
                    )
                )
    return issues


def _condition_operators(condition: Any) -> list[str]:
    if condition is None or not isinstance(condition, list) or not condition:
        return []
    operators = [condition[0]] if isinstance(condition[0], str) else []
    for item in condition[1:]:
        operators.extend(_condition_operators(item))
    return operators


def _priority_issues(model: SurveyModel) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    by_source: dict[str, dict[int, list[str]]] = defaultdict(lambda: defaultdict(list))
    for edge in model.edges:
        by_source[edge["source"]][edge["priority"]].append(edge["id"])
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
        if not model.outgoing_edges(node_id):
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
        for edge in model.outgoing_edges(node_id):
            if model.node_exists(edge["target"]):
                stack.append(edge["target"])
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
                evidence={"entry_node": model.entry_node, "incoming_edges": [edge["id"] for edge in model.incoming_edges(node_id)]},
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
        for edge in model.outgoing_edges(node_id):
            if model.node_exists(edge["target"]):
                visit(edge["target"], path + [edge["target"]])
        visiting.remove(node_id)
        visited.add(node_id)

    if model.entry_node and model.node_exists(model.entry_node):
        visit(model.entry_node, [model.entry_node])

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
    terminal_ids = set(model.terminal_ids)
    memo: dict[str, bool] = {}

    def reaches_terminal(node_id: str, path: set[str]) -> bool:
        if node_id in terminal_ids:
            return True
        if node_id in memo:
            return memo[node_id]
        if node_id in path:
            memo[node_id] = False
            return False
        outgoing = [edge for edge in model.outgoing_edges(node_id) if model.node_exists(edge["target"])]
        if not outgoing:
            memo[node_id] = False
            return False
        memo[node_id] = any(reaches_terminal(edge["target"], path | {node_id}) for edge in outgoing)
        return memo[node_id]

    issues = []
    for node_id in sorted(_reachable_nodes(model)):
        if node_id not in terminal_ids and not reaches_terminal(node_id, set()):
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


def _fallthrough_issues(model: SurveyModel) -> list[ValidationIssue]:
    issues = []
    for source in sorted({edge["source"] for edge in model.edges}):
        outgoing = model.outgoing_edges(source)
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
                    evidence={"outgoing_edges": [edge["id"] for edge in outgoing]},
                )
            )
    return issues


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
