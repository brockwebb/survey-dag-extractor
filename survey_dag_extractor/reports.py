from __future__ import annotations

from survey_dag_extractor.issues import ValidationIssue
from survey_dag_extractor.model import SurveyModel


UNKNOWN_SURVEY_ID = "<unknown>"


def safe_survey_id(model: SurveyModel) -> str:
    survey_id = model.survey.get("id")
    return survey_id if isinstance(survey_id, str) and survey_id else UNKNOWN_SURVEY_ID


def format_markdown_report(model: SurveyModel, issues: list[ValidationIssue]) -> str:
    lines = [
        f"# Validation Report: {safe_survey_id(model)}",
        "",
        f"- Entry node: `{model.entry_node}`",
        f"- Questions: {len(model.questions)}",
        f"- Terminal nodes: {len(model.terminals)}",
        f"- Edges: {len(model.edges)}",
        f"- Issues: {len(issues)}",
        "",
    ]
    if not issues:
        lines.extend(["## Result", "", "No validation issues found.", ""])
        return "\n".join(lines)

    lines.extend(["## Issues", ""])
    for issue in issues:
        lines.extend(
            [
                f"### {issue.id}: {issue.type}",
                "",
                f"- Severity: `{issue.severity}`",
                f"- Status: `{issue.status}`",
                f"- Node: `{issue.node_id}`" if issue.node_id else "- Node: none",
                f"- Edge: `{issue.edge_id}`" if issue.edge_id else "- Edge: none",
                f"- Message: {issue.message}",
                "",
            ]
        )
    return "\n".join(lines)
