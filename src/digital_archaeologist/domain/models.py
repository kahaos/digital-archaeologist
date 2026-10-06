from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

EvidenceType = Literal["observed", "inferred", "estimated", "unknown"]
CandidateStatus = Literal["NEW", "RESEARCH", "WATCH", "PURSUE", "IGNORE", "REJECTED"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CandidateDraft(BaseModel):
    model_config = ConfigDict(extra="allow")

    canonical_identity: str = ""
    source: str
    url: str
    category: str
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance_urls: list[str] = Field(default_factory=list)
    discovered_at: datetime = Field(default_factory=utcnow)


class Candidate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    canonical_identity: str
    source: str
    url: str
    category: str
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance_urls: list[str] = Field(default_factory=list)
    discovered_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    status: CandidateStatus = "NEW"
    score: float | None = None


class Evidence(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    candidate_id: str
    claim: str
    evidence_type: EvidenceType
    source_url: str | None = None
    summary: str
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    collected_at: datetime = Field(default_factory=utcnow)


class OpportunityReport(BaseModel):
    candidate_id: str
    component_scores: dict[str, float] = Field(default_factory=dict)
    total_score: float = 0
    confidence: float = 0
    verdict: str
    risks: list[str] = Field(default_factory=list)
    recommendation: str = ""
    adversarial_review: str = ""
    next_action: str = "Human review required before any action"
    evidence_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
