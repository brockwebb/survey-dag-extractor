from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from survey_dag_extractor.issues import Recommendation


@dataclass(frozen=True)
class PatchResult:
    document: dict[str, Any]
    decision_count: int
    applied_count: int
    skipped_count: int
    logged_count: int


def apply_approved_recommendations(
    document: dict[str, Any],
    recommendations: list[Recommendation],
    decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    return apply_approved_recommendations_with_summary(document, recommendations, decisions).document


def apply_approved_recommendations_with_summary(
    document: dict[str, Any],
    recommendations: list[Recommendation],
    decisions: list[dict[str, Any]],
) -> PatchResult:
    if not isinstance(decisions, list):
        raise ValueError("Decisions must be a list")

    patched = copy.deepcopy(document)
    recommendation_by_id = {recommendation.id: recommendation for recommendation in recommendations}
    applied_recommendation_ids: set[str] = set()
    applied_count = 0
    skipped_count = 0
    logged_count = 0
    for decision in decisions:
        _validate_decision(decision)
        recommendation_id = decision["recommendation_id"]
        recommendation = recommendation_by_id.get(recommendation_id)
        if decision.get("decision") == "approved" and recommendation is not None and recommendation_id not in applied_recommendation_ids:
            applied_operations = 0
            for operation in recommendation.patch:
                if _apply_operation(patched, operation):
                    applied_operations += 1
            applied_recommendation_ids.add(recommendation_id)
            if applied_operations:
                applied_count += 1
            else:
                skipped_count += 1
        else:
            skipped_count += 1
        _append_decision(patched, recommendation, decision)
        logged_count += 1
    return PatchResult(
        document=patched,
        decision_count=len(decisions),
        applied_count=applied_count,
        skipped_count=skipped_count,
        logged_count=logged_count,
    )


def _validate_decision(decision: Any) -> None:
    if not isinstance(decision, dict):
        raise ValueError("Each decision must be an object")
    required_fields = {"recommendation_id", "decision", "approver", "rationale"}
    missing = sorted(required_fields - set(decision))
    if missing:
        raise ValueError(f"Decision is missing required fields: {', '.join(missing)}")


def _apply_operation(document: dict[str, Any], operation: dict[str, Any]) -> bool:
    if operation["op"] == "add_edge":
        edge = operation["edge"]
        edges = document["survey"]["dag"]["edges"]
        edge_id = edge.get("id")
        if any(isinstance(existing, dict) and existing.get("id") == edge_id for existing in edges):
            return False
        edges.append(copy.deepcopy(edge))
        return True
    if operation["op"] == "update_edge":
        edge = _find_edge(document, operation["edge_id"])
        if edge is None:
            return False
        changes = operation["changes"]
        changed = False
        for key, value in changes.items():
            if edge.get(key) != value:
                edge[key] = copy.deepcopy(value)
                changed = True
        return changed
    raise ValueError(f"Unsupported patch operation: {operation['op']}")


def _find_edge(document: dict[str, Any], edge_id: str) -> dict[str, Any] | None:
    for edge in document["survey"]["dag"]["edges"]:
        if isinstance(edge, dict) and edge.get("id") == edge_id:
            return edge
    return None


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
