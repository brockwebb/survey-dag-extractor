from __future__ import annotations

from survey_dag_extractor.issues import Recommendation, ValidationIssue
from survey_dag_extractor.model import SurveyModel


def recommend_repairs(model: SurveyModel, issues: list[ValidationIssue]) -> list[Recommendation]:
    recommendations: list[Recommendation] = []
    for issue in issues:
        if issue.type == "missing_fallthrough" and issue.node_id:
            recommendation = _recommend_fallthrough(model, issue, len(recommendations) + 1)
            if recommendation:
                recommendations.append(recommendation)
    return recommendations


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
