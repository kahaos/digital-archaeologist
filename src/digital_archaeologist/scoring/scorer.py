from __future__ import annotations

import math
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from digital_archaeologist.domain.models import Candidate
from .rules import WEIGHTS, bounded


class OpportunityScore(BaseModel):
    component_scores: dict[str, float] = Field(default_factory=dict)
    total_score: float
    reasons: list[str] = Field(default_factory=list)


def _scaled_log(value: object, cap: float) -> float | None:
    try:
        number = max(0.0, float(value))
    except (TypeError, ValueError):
        return None
    return min(1.0, math.log1p(number) / math.log1p(cap))


def _activity_age_days(value: object) -> float | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        activity = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if activity.tzinfo is None:
            activity = activity.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - activity.astimezone(timezone.utc)).total_seconds() / 86400)
    except (TypeError, ValueError):
        return None


def score_candidate(candidate: Candidate) -> OpportunityScore:
    m = candidate.metadata
    mapping = {
        "demand": "demand_score",
        "existing_traction": "traction_score",
        "neglect": "neglect_score",
        "ease_of_resurrection": "resurrection_score",
        "monetisation": "monetization_score",
        "competition": "competition_score",
        "licence_ownership": "license_clarity_score",
    }
    derived: dict[str, tuple[float | None, str]] = {}

    issue_signal = _scaled_log(m.get("open_issues"), 1000)
    derived["demand"] = (issue_signal * WEIGHTS["demand"] if issue_signal is not None else None,
                          "open issue count as a conservative community demand proxy")
    stars, forks = _scaled_log(m.get("stars"), 100_000), _scaled_log(m.get("forks"), 10_000)
    derived["existing_traction"] = ((0.75 * stars + 0.25 * forks) * WEIGHTS["existing_traction"]
                                    if stars is not None and forks is not None else None,
                                    "log-scaled GitHub stars and forks")
    age = _activity_age_days(m.get("last_activity"))
    if age is not None:
        neglect_fraction = min(1.0, age / (365 * 5))
        if m.get("archived") is True:
            neglect_fraction = max(neglect_fraction, 0.8)
        derived["neglect"] = (neglect_fraction * WEIGHTS["neglect"], "last activity age and archived status")
    else:
        derived["neglect"] = (None, "last activity date and archive status")

    # Completeness and an active, unarchived state are weak positive signs of lower revival effort.
    has_health = any(key in m and m.get(key) is not None for key in ("description", "last_activity", "license", "archived"))
    if has_health:
        resurrection = 0.0
        if m.get("description"):
            resurrection += 0.25
        if m.get("license"):
            resurrection += 0.25
        if age is not None and age < 365:
            resurrection += 0.25
        if m.get("archived") is False:
            resurrection += 0.25
        derived["ease_of_resurrection"] = (resurrection * WEIGHTS["ease_of_resurrection"], "repository description, licence, activity, and archive metadata")
    else:
        derived["ease_of_resurrection"] = (None, "repository health metadata")

    text = " ".join(str(m.get(k) or "") for k in ("description", "name", "title", "category")).lower()
    commercial_signals = ("analytics", "business", "commerce", "crm", "invoice", "marketing", "saas", "store", "workflow")
    hits = sum(signal in text for signal in commercial_signals)
    derived["monetisation"] = (min(WEIGHTS["monetisation"] * 0.4, hits * WEIGHTS["monetisation"] * 0.1) if hits else None,
                               "conservative commercial category keywords" if hits else None)
    derived["competition"] = (None, None)
    license_value = m.get("license")
    derived["licence_ownership"] = (WEIGHTS["licence_ownership"] if isinstance(license_value, str) and license_value.strip() and license_value.lower() not in {"none", "noassertion"} else (0.0 if "license" in m else None),
                                    "detected repository licence" if license_value else ("licence metadata reports no licence" if "license" in m else None))

    scores: dict[str, float] = {}
    reasons: list[str] = []
    for component, score_key in mapping.items():
        if score_key in m and m.get(score_key) is not None:
            value = bounded(m.get(score_key), WEIGHTS[component], 0)
            reason = "supplied deterministic component score"
        else:
            value, evidence = derived.get(component, (None, None))
            if value is None:
                value = 0.0
                reason = f"unknown evidence; conservative zero contribution ({evidence or 'no reliable signal'})"
            else:
                reason = f"scored from {evidence}"
        scores[component] = round(value, 4)
        reasons.append(f"{component}: {reason}")
    total = round(max(0.0, min(100.0, sum(scores.values()))), 4)
    return OpportunityScore(component_scores=scores, total_score=total, reasons=reasons)
