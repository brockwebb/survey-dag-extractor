from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Severity = Literal["error", "warning", "info"]
IssueStatus = Literal["open", "recommended", "approved", "rejected", "applied", "verified", "waived"]


@dataclass(frozen=True)
class ValidationIssue:
    id: str
    severity: Severity
    type: str
    message: str
    node_id: str | None = None
    edge_id: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    recommendation_ids: list[str] = field(default_factory=list)
    status: IssueStatus = "open"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "type": self.type,
            "node_id": self.node_id,
            "edge_id": self.edge_id,
            "message": self.message,
            "evidence": self.evidence,
            "recommendation_ids": self.recommendation_ids,
            "status": self.status,
        }


@dataclass(frozen=True)
class Recommendation:
    id: str
    issue_id: str
    type: str
    confidence: Literal["low", "medium", "high"]
    rationale: str
    patch: list[dict[str, Any]]
    requires_approval: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "issue_id": self.issue_id,
            "type": self.type,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "patch": self.patch,
            "requires_approval": self.requires_approval,
        }
