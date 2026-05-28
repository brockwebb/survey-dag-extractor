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
        terminal_ids = model.terminal_ids
        target = terminal_ids[0] if terminal_ids else None
    if target is None:
        return None
    edge_id = _next_edge_id(model, index)
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
                    "priority": 999,
                    "type": "fallthrough",
                },
            }
        ],
    )


def _next_edge_id(model: SurveyModel, index: int) -> str:
    existing = {edge["id"] for edge in model.edges}
    candidate = f"E_AUTO_{index:04d}"
    while candidate in existing:
        index += 1
        candidate = f"E_AUTO_{index:04d}"
    return candidate
