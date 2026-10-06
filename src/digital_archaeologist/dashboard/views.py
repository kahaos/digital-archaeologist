from __future__ import annotations

from datetime import datetime

from digital_archaeologist.domain.models import Candidate, Evidence, OpportunityReport


def build_candidate_card(candidate: Candidate, report: OpportunityReport | None, evidence: list[Evidence]) -> dict:
    return {
        "title": candidate.title or candidate.url,
        "url": candidate.url,
        "source": candidate.source,
        "category": candidate.category,
        "score": report.total_score if report else candidate.score,
        "verdict": report.verdict if report else "NOT INVESTIGATED",
        "confidence": report.confidence if report else None,
        "recommendation": report.recommendation if report else "Investigate candidate",
        "risks": report.risks if report else [],
        "adversarial_review": report.adversarial_review if report else "",
        "evidence": [
            {"type": item.evidence_type.upper(), "claim": item.claim, "source_url": item.source_url, "summary": item.summary}
            for item in evidence
        ],
        "next_action": report.next_action if report else "Research required",
    }


def empty_state() -> dict[str, str]:
    return {
        "title": "No opportunities yet",
        "message": "Run a discovery cycle to find candidates, then investigate the strongest signals.",
    }


def filter_candidates(candidates: list[Candidate], *, min_score: float = 0, sources: set[str] | None = None, categories: set[str] | None = None, statuses: set[str] | None = None, min_monetisation: float = 0, max_effort: float = 100, discovered_after: datetime | None = None) -> list[Candidate]:
    sources = sources or set()
    categories = categories or set()
    statuses = statuses or set()
    return [
        candidate for candidate in candidates
        if (candidate.score or 0) >= min_score
        and (not sources or candidate.source in sources)
        and (not categories or candidate.category in categories)
        and (not statuses or candidate.status in statuses)
        and float(candidate.metadata.get("monetization_score", 0) or 0) >= min_monetisation
        and float(candidate.metadata.get("effort_score", 0) or 0) <= max_effort
        and (discovered_after is None or candidate.discovered_at >= discovered_after)
    ]
