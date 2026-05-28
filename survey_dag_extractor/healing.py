from __future__ import annotations

from dataclasses import replace

from survey_dag_extractor.issues import Recommendation, ValidationIssue
from survey_dag_extractor.model import SurveyModel


def recommend_repairs(model: SurveyModel, issues: list[ValidationIssue]) -> list[Recommendation]:
    recommendations: list[Recommendation] = []
    for issue in issues:
        if issue.type == "missing_fallthrough" and issue.node_id:
            recommendation = _recommend_fallthrough(model, issue, len(recommendations) + 1)
            if recommendation:
                recommendations.append(recommendation)
        if issue.type == "orphan_node" and issue.node_id:
            recommendation = _recommend_orphan_reconnect(model, issue, len(recommendations) + 1)
            if recommendation:
                recommendations.append(recommendation)
    for issue in issues:
        if issue.type == "missing_outgoing_edge" and issue.node_id:
            recommendation = _recommend_terminal_exit(model, issue, len(recommendations) + 1)
            if recommendation:
                recommendations.append(recommendation)
    for issue in issues:
        if issue.type == "duplicate_priority" and issue.node_id:
            recommendation = _recommend_duplicate_priority_adjustment(model, issue, len(recommendations) + 1)
            if recommendation:
                recommendations.append(recommendation)
    return recommendations


def link_recommendations_to_issues(
    issues: list[ValidationIssue],
    recommendations: list[Recommendation],
) -> list[ValidationIssue]:
    recommendation_ids_by_issue: dict[str, list[str]] = {}
    for recommendation in recommendations:
        recommendation_ids_by_issue.setdefault(recommendation.issue_id, []).append(recommendation.id)
    return [
        replace(issue, recommendation_ids=recommendation_ids_by_issue.get(issue.id, []))
        for issue in issues
    ]


def _recommend_fallthrough(model: SurveyModel, issue: ValidationIssue, index: int) -> Recommendation | None:
    source = issue.node_id
    target = model.next_question_after(source)
    if target is None:
        target = _first_valid_terminal_id(model)
    if target is None:
        return None
    edge_id = _next_edge_id(model, index)
    priority = _next_fallthrough_priority(model, source)
    return Recommendation(
        id=f"REC_{index:04d}",
        issue_id=issue.id,
        type="add_fallthrough_edge",
        confidence="medium",
        rationale=f"Branching source {source} has no default path; use the next question or terminal as a human-reviewable fallthrough.",
        patch=[
            {
                "op": "add_edge",
                "edge": {
                    "id": edge_id,
                    "source": source,
                    "target": target,
                    "condition": None,
                    "condition_text": "fallthrough",
                    "priority": priority,
                    "type": "fallthrough",
                },
            }
        ],
    )


def _recommend_orphan_reconnect(model: SurveyModel, issue: ValidationIssue, index: int) -> Recommendation | None:
    target = issue.node_id
    source = _nearest_reachable_predecessor(model, target)
    if source is None or _direct_edge_exists(model, source, target):
        return None
    edge_type = "terminal" if model.is_terminal(target) else "fallthrough"
    return Recommendation(
        id=f"REC_{index:04d}",
        issue_id=issue.id,
        type="connect_orphan_node",
        confidence="low",
        rationale=f"{target} is unreachable; connect it from nearest reachable prior node {source} for human review.",
        patch=[
            {
                "op": "add_edge",
                "edge": {
                    "id": _next_edge_id(model, index),
                    "source": source,
                    "target": target,
                    "condition": None,
                    "condition_text": "orphan reconnect",
                    "priority": _orphan_reconnect_priority(model, source),
                    "type": edge_type,
                },
            }
        ],
    )


def _recommend_terminal_exit(model: SurveyModel, issue: ValidationIssue, index: int) -> Recommendation | None:
    source = issue.node_id
    if model.outgoing_edges(source):
        return None
    target = _first_valid_terminal_id(model)
    if target is None:
        return None
    return Recommendation(
        id=f"REC_{index:04d}",
        issue_id=issue.id,
        type="add_terminal_exit",
        confidence="low",
        rationale=f"Question {source} has no outgoing path; add terminal exit to {target} for human review.",
        patch=[
            {
                "op": "add_edge",
                "edge": {
                    "id": _next_edge_id(model, index),
                    "source": source,
                    "target": target,
                    "condition": None,
                    "condition_text": "terminal exit",
                    "priority": _next_fallthrough_priority(model, source),
                    "type": "terminal",
                },
            }
        ],
    )


def _recommend_duplicate_priority_adjustment(
    model: SurveyModel,
    issue: ValidationIssue,
    index: int,
) -> Recommendation | None:
    source = issue.node_id
    edge_ids = issue.evidence.get("edge_ids")
    duplicate_priority = issue.evidence.get("priority")
    if not isinstance(edge_ids, list) or len(edge_ids) < 2 or type(duplicate_priority) is not int:
        return None

    edge_by_id = {
        str(edge.get("id")): edge
        for edge in model.outgoing_edges(source)
        if isinstance(edge.get("id"), str)
    }
    used_priorities = {
        edge.get("priority")
        for edge in model.outgoing_edges(source)
        if type(edge.get("priority")) is int
    }
    patch = []
    next_priority = duplicate_priority + 1
    for edge_id in edge_ids[1:]:
        if not isinstance(edge_id, str) or edge_id not in edge_by_id:
            continue
        while next_priority in used_priorities:
            next_priority += 1
        patch.append(
            {
                "op": "update_edge",
                "edge_id": edge_id,
                "changes": {"priority": next_priority},
            }
        )
        used_priorities.add(next_priority)
        next_priority += 1
    if not patch:
        return None

    return Recommendation(
        id=f"REC_{index:04d}",
        issue_id=issue.id,
        type="adjust_duplicate_priority",
        confidence="high",
        rationale=f"Source {source} has duplicate priority {duplicate_priority}; assign unique priorities to later edges.",
        patch=patch,
    )


def _nearest_reachable_predecessor(model: SurveyModel, target: str) -> str | None:
    reachable = _reachable_nodes(model)
    ordered = model.block_order()
    if target in ordered:
        target_index = ordered.index(target)
        for candidate in reversed(ordered[:target_index]):
            if candidate in reachable:
                return candidate
        return None
    for candidate in reversed(ordered):
        if candidate in reachable:
            return candidate
    return None


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
            target = edge.get("target")
            if isinstance(target, str) and model.node_exists(target):
                stack.append(target)
    return visited


def _direct_edge_exists(model: SurveyModel, source: str, target: str) -> bool:
    return any(edge.get("target") == target for edge in model.outgoing_edges(source))


def _first_valid_terminal_id(model: SurveyModel) -> str | None:
    for terminal_id in model.terminal_ids:
        if model.node_exists(terminal_id):
            return terminal_id
    return None


def _next_edge_id(model: SurveyModel, index: int) -> str:
    existing = {str(edge["id"]) for edge in model.edges if isinstance(edge, dict) and "id" in edge}
    candidate = f"E_AUTO_{index:04d}"
    while candidate in existing:
        index += 1
        candidate = f"E_AUTO_{index:04d}"
    return candidate


def _next_fallthrough_priority(model: SurveyModel, source: str) -> int:
    existing = {
        edge.get("priority")
        for edge in model.outgoing_edges(source)
        if type(edge.get("priority")) is int
    }
    priority = 999
    while priority in existing:
        priority += 1
    return priority


def _orphan_reconnect_priority(model: SurveyModel, source: str) -> int:
    outgoing = model.outgoing_edges(source)
    existing = {
        edge.get("priority")
        for edge in outgoing
        if type(edge.get("priority")) is int
    }
    unconditional_priorities = [
        edge["priority"]
        for edge in outgoing
        if edge.get("condition") is None and type(edge.get("priority")) is int
    ]
    if unconditional_priorities:
        first_unconditional = min(unconditional_priorities)
        for priority in range(first_unconditional - 1, 0, -1):
            if priority not in existing:
                return priority
    return _next_fallthrough_priority(model, source)
