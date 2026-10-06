from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

Verdict = Literal["STRONG OPPORTUNITY", "POSSIBLE", "WEAK", "REJECT"]
EvidenceType = Literal["OBSERVED", "INFERRED", "ESTIMATED", "UNKNOWN"]
WEIGHTS = {"demand": 25, "existing_traction": 20, "neglect": 15, "ease_of_resurrection": 15, "monetisation": 15, "competition": 5, "licence_ownership": 5}


class EvidenceClaim(BaseModel):
    id: str
    claim: str
    evidence_type: EvidenceType
    source_url: str | None = None
    summary: str
    source_evidence_ids: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class ResearchResponse(BaseModel):
    verdict: Verdict
    total_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    component_scores: dict[str, float]
    evidence: list[EvidenceClaim]
    adversarial_findings: list[EvidenceClaim] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendation: str
    adversarial_review: str
    next_action: str


class ValidatedResearch(ResearchResponse):
    pass


def validate_response(response: Any, *, evidence_ids: set[str] | None = None, phase: str = "initial") -> ValidatedResearch:
    if isinstance(response, str):
        response = json.loads(response)
    if hasattr(response, "model_dump"):
        response = response.model_dump()
    validated = ValidatedResearch.model_validate(response)
    if set(validated.component_scores) - set(WEIGHTS):
        raise ValueError("unsupported score component")
    for name, value in validated.component_scores.items():
        if not 0 <= value <= WEIGHTS[name]:
            raise ValueError(f"score for {name} outside allowed range")
    if not validated.evidence:
        raise ValueError("research response requires evidence")
    claims = [*validated.evidence, *validated.adversarial_findings]
    if any(not item.id.strip() for item in claims):
        raise ValueError("every claim requires an evidence reference")
    for item in claims:
        if item.evidence_type == "OBSERVED":
            raise ValueError("OBSERVED claims must be created by the source collector")
        if item.evidence_type in {"INFERRED", "ESTIMATED"} and not item.source_evidence_ids:
            raise ValueError(f"{item.evidence_type} claims require source evidence IDs")
        if item.evidence_type == "ESTIMATED" and not item.assumptions:
            raise ValueError("ESTIMATED claims require assumptions")
        if item.evidence_type == "UNKNOWN" and not item.summary.strip():
            raise ValueError("UNKNOWN claims must explain what remains unknown")
        if evidence_ids is not None and any(ref not in evidence_ids for ref in item.source_evidence_ids):
            raise ValueError("claim references uncollected evidence")
    if phase == "adversarial" and not validated.adversarial_findings:
        raise ValueError("adversarial pass requires at least one adversarial finding")
    if phase == "adversarial" and not validated.adversarial_review.strip():
        raise ValueError("strong verdict requires adversarial review")
    return validated
