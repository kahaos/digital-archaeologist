from digital_archaeologist.domain.models import Candidate
from digital_archaeologist.scoring.scorer import score_candidate


def test_known_fixture_produces_expected_components_and_total():
    candidate = Candidate(
        canonical_identity="github:owner/repo", source="github", url="https://github.com/owner/repo", category="software",
        metadata={
            "demand_score": 20, "traction_score": 16, "neglect_score": 12,
            "resurrection_score": 11, "monetization_score": 10, "competition_score": 3,
            "license_clarity_score": 4,
        },
    )
    result = score_candidate(candidate)
    assert result.component_scores == {"demand": 20, "existing_traction": 16, "neglect": 12, "ease_of_resurrection": 11, "monetisation": 10, "competition": 3, "licence_ownership": 4}
    assert result.total_score == 76


def test_missing_evidence_uses_conservative_unknown_treatment():
    candidate = Candidate(canonical_identity="web:example.com", source="web", url="https://example.com", category="website")
    result = score_candidate(candidate)
    assert result.total_score == 0
    assert all("unknown" in reason.lower() for reason in result.reasons)


def test_github_observable_metadata_produces_differentiated_scores():
    from datetime import datetime, timedelta, timezone

    common = dict(source="github", category="software")
    active = Candidate(
        canonical_identity="github:active/tool", url="https://github.com/active/tool", **common,
        metadata={"stars": 1200, "forks": 180, "open_issues": 25,
                  "last_activity": datetime.now(timezone.utc).isoformat(), "license": "MIT",
                  "archived": False, "description": "Self-hosted analytics platform"},
    )
    neglected = Candidate(
        canonical_identity="github:old/tool", url="https://github.com/old/tool", **common,
        metadata={"stars": 4, "forks": 0, "open_issues": 0,
                  "last_activity": (datetime.now(timezone.utc) - timedelta(days=1500)).isoformat(),
                  "license": None, "archived": True, "description": "Old game mod"},
    )

    active_score = score_candidate(active)
    neglected_score = score_candidate(neglected)
    assert active_score.total_score != 50
    assert neglected_score.total_score != 50
    assert active_score.component_scores != neglected_score.component_scores
    assert active_score.component_scores["existing_traction"] > neglected_score.component_scores["existing_traction"]
    assert neglected_score.component_scores["neglect"] > active_score.component_scores["neglect"]
    assert active_score.component_scores["licence_ownership"] > neglected_score.component_scores["licence_ownership"]
    assert 0 <= active_score.total_score <= 100
    assert 0 <= neglected_score.total_score <= 100


def test_github_missing_fields_are_conservative_and_marked_unknown():
    candidate = Candidate(canonical_identity="github:owner/empty", source="github", url="https://github.com/owner/empty", category="software", metadata={})
    result = score_candidate(candidate)
    assert result.component_scores["competition"] == 0
    assert result.component_scores["licence_ownership"] == 0
    assert any("unknown" in reason.lower() for reason in result.reasons)


def test_total_is_always_between_zero_and_hundred():
    high = Candidate(canonical_identity="x", source="web", url="https://x.test", category="website", metadata={
        "demand_score": 999, "traction_score": 999, "neglect_score": 999, "resurrection_score": 999,
        "monetization_score": 999, "competition_score": 999, "license_clarity_score": 999,
    })
    low = Candidate(canonical_identity="y", source="web", url="https://y.test", category="website", metadata={
        "demand_score": -999, "traction_score": -999, "neglect_score": -999, "resurrection_score": -999,
        "monetization_score": -999, "competition_score": -999, "license_clarity_score": -999,
    })
    assert 0 <= score_candidate(high).total_score <= 100
    assert 0 <= score_candidate(low).total_score <= 100
