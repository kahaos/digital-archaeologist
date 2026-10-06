import pytest
from pydantic import ValidationError

from digital_archaeologist.research.validator import ResearchResponse, validate_response


def valid_response():
    return ResearchResponse(
        verdict="POSSIBLE", total_score=71, confidence=0.75,
        component_scores={"demand": 18, "existing_traction": 15, "neglect": 12, "ease_of_resurrection": 11, "monetisation": 10, "competition": 2, "licence_ownership": 3},
        evidence=[{"id": "c1", "claim": "Open issue activity may indicate unresolved needs", "evidence_type": "INFERRED", "source_evidence_ids": ["source-1"], "summary": "This is only a proxy."}],
        adversarial_findings=[{"id": "c2", "claim": "Current buyer demand is unknown", "evidence_type": "UNKNOWN", "source_evidence_ids": [], "summary": "No buyer evidence was collected."}],
        risks=["Demand may have shifted"], recommendation="Investigate competitors", adversarial_review="The strongest counterpoint is weak current demand.", next_action="Research competitors",
    )


def test_valid_structured_output_is_accepted():
    result = validate_response(valid_response(), evidence_ids={"source-1"}, phase="adversarial")
    assert result.verdict == "POSSIBLE"
    assert result.evidence[0].id == "c1"


def test_malformed_json_is_rejected():
    with pytest.raises((ValidationError, ValueError)):
        validate_response("not-json")


def test_claim_without_evidence_reference_is_rejected():
    response = valid_response()
    response.evidence[0].id = ""
    with pytest.raises(ValueError, match="evidence"):
        validate_response(response)


def test_unsupported_verdict_and_score_ranges_are_rejected():
    response = valid_response()
    response.verdict = "BUY IT"
    with pytest.raises(ValueError):
        validate_response(response)


def test_model_cannot_create_observed_claims_or_cite_uncollected_evidence():
    response = valid_response()
    response.evidence[0].evidence_type = "OBSERVED"
    with pytest.raises(ValueError, match="collector"):
        validate_response(response, evidence_ids={"source-1"})
    response = valid_response()
    response.evidence[0].source_evidence_ids = ["invented"]
    with pytest.raises(ValueError, match="uncollected"):
        validate_response(response, evidence_ids={"source-1"})


def test_estimates_require_assumptions_and_adversarial_pass_requires_counterpoints():
    response = valid_response()
    response.evidence[0].evidence_type = "ESTIMATED"
    response.evidence[0].source_evidence_ids = ["source-1"]
    with pytest.raises(ValueError, match="assumption"):
        validate_response(response, evidence_ids={"source-1"})
    response.evidence[0] = response.evidence[0].model_copy(update={"assumptions": ["Assume issue activity approximates retained interest"]})
    response.adversarial_findings = []
    with pytest.raises(ValueError, match="adversarial finding"):
        validate_response(response, evidence_ids={"source-1"}, phase="adversarial")
    response = valid_response()
    response.total_score = 101
    with pytest.raises(ValueError):
        validate_response(response)
