from digital_archaeologist.dashboard.views import build_candidate_card, empty_state
from digital_archaeologist.domain.models import Candidate, Evidence, OpportunityReport


def test_candidate_card_contains_score_verdict_confidence_and_recommendation():
    candidate = Candidate(canonical_identity="web:example.com", source="web", url="https://example.com", category="website", score=84)
    report = OpportunityReport(candidate_id=candidate.id, total_score=84, confidence=0.9, verdict="STRONG OPPORTUNITY", recommendation="Investigate acquisition", risks=["Unknown owner"])
    card = build_candidate_card(candidate, report, [])
    assert card["score"] == 84
    assert card["verdict"] == "STRONG OPPORTUNITY"
    assert card["confidence"] == 0.9
    assert card["recommendation"] == "Investigate acquisition"
    assert card["next_action"] == "Human review required before any action"
    assert card["risks"] == ["Unknown owner"]


def test_evidence_type_is_displayed_distinctly():
    candidate = Candidate(canonical_identity="web:example.com", source="web", url="https://example.com", category="website")
    evidence = [Evidence(candidate_id=candidate.id, claim="Demand exists", evidence_type="observed", source_url="https://example.com/issues", summary="Recent requests")]
    card = build_candidate_card(candidate, None, evidence)
    assert card["evidence"][0]["type"] == "OBSERVED"


def test_empty_database_renders_useful_empty_state():
    state = empty_state()
    assert "No opportunities" in state["title"]
    assert "discovery" in state["message"].lower()


def test_filter_candidates_can_filter_by_score_source_and_status():
    candidates = [
        Candidate(canonical_identity="a", source="github", url="https://github.com/a/a", category="software", score=90, status="NEW", metadata={"monetization_score": 8, "effort_score": 20}),
        Candidate(canonical_identity="b", source="web", url="https://b.test", category="website", score=40, status="WATCH"),
    ]
    result = __import__("digital_archaeologist.dashboard.views", fromlist=["filter_candidates"]).filter_candidates(candidates, min_score=80, sources={"github"}, statuses={"NEW"}, min_monetisation=5, max_effort=50)
    assert [item.canonical_identity for item in result] == ["a"]


def test_filter_candidates_can_bound_discovery_date():
    from datetime import datetime, timezone
    candidates = [
        Candidate(canonical_identity="old", source="web", url="https://old.test", category="website", discovered_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),
        Candidate(canonical_identity="new", source="web", url="https://new.test", category="website", discovered_at=datetime(2026, 10, 1, tzinfo=timezone.utc)),
    ]
    result = __import__("digital_archaeologist.dashboard.views", fromlist=["filter_candidates"]).filter_candidates(candidates, discovered_after=datetime(2026, 9, 1, tzinfo=timezone.utc))
    assert [item.canonical_identity for item in result] == ["new"]
