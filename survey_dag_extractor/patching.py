from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

from survey_dag_extractor.issues import Recommendation


def apply_approved_recommendations(
    document: dict[str, Any],
    recommendations: list[Recommendation],
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    patched = copy.deepcopy(document)
    recommendation_by_id = {recommendation.id: recommendation for recommendation in recommendations}
    applied_recommendation_ids: set[str] = set()
    for decision in decisions:
        recommendation_id = decision["recommendation_id"]
        recommendation = recommendation_by_id.get(recommendation_id)
        if decision.get("decision") == "approved" and recommendation is not None and recommendation_id not in applied_recommendation_ids:
            for operation in recommendation.patch:
                _apply_operation(patched, operation)
            applied_recommendation_ids.add(recommendation_id)
        _append_decision(patched, recommendation, decision)
    return patched


def _apply_operation(document: dict[str, Any], operation: dict[str, Any]) -> None:
    if operation["op"] == "add_edge":
        document["survey"]["dag"]["edges"].append(copy.deepcopy(operation["edge"]))
        return
    raise ValueError(f"Unsupported patch operation: {operation['op']}")


def _append_decision(document: dict[str, Any], recommendation: Recommendation | None, decision: dict[str, Any]) -> None:
    metadata = document["survey"].setdefault("metadata", {})
    decision_log = metadata.setdefault("decision_log", [])
    decision_log.append(
        {
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "approver": decision["approver"],
            "issue_id": recommendation.issue_id if recommendation else None,
            "recommendation_id": decision["recommendation_id"],
            "decision": decision["decision"],
            "rationale": decision["rationale"],
        }
    )
