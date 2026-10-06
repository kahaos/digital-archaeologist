from __future__ import annotations

from uuid import uuid4

from digital_archaeologist.domain.models import Candidate, Evidence, OpportunityReport
from digital_archaeologist.storage.repositories import Repository
from .provider import ResearchProvider, ResearchRequest
from .prompts import adversarial_research_prompt, initial_research_prompt
from .validator import validate_response


class ResearchInvestigator:
    def __init__(self, provider: ResearchProvider, repository: Repository, evidence_collector=None) -> None:
        self.provider = provider
        self.repository = repository
        self.evidence_collector = evidence_collector

    def investigate(self, candidate: Candidate) -> OpportunityReport:
        evidence = [item for item in self.repository.get_evidence(candidate.id) if item.evidence_type == "observed"]
        if not evidence and self.evidence_collector is not None:
            collected = self.evidence_collector.collect(candidate)
            if any(item.evidence_type != "observed" for item in collected):
                raise ValueError("evidence collector may only create OBSERVED source records")
            for item in collected:
                self.repository.add_evidence(item)
            evidence.extend(collected)
        source_ids = {item.id for item in evidence if item.evidence_type == "observed"}
        if not source_ids:
            raise ValueError("investigation requires observed source evidence")
        request = ResearchRequest(candidate=candidate.model_dump(mode="json"), evidence=[item.model_dump(mode="json") for item in evidence], phase="initial", instructions=initial_research_prompt())
        first = validate_response(self.provider.generate(request), evidence_ids=source_ids, phase="initial")
        adversarial_request = request.model_copy(update={"phase": "adversarial", "instructions": adversarial_research_prompt(), "prior_analysis": first.model_dump(mode="json")})
        adversarial = validate_response(self.provider.generate(adversarial_request), evidence_ids=source_ids, phase="adversarial")
        observed_sources = {item.id: item for item in evidence if item.id in source_ids}
        persisted_ids = [item.id for item in evidence]
        for claim in [*first.evidence, *adversarial.evidence, *adversarial.adversarial_findings]:
            source_url = observed_sources[claim.source_evidence_ids[0]].source_url if len(claim.source_evidence_ids) == 1 else None
            stored = self.repository.add_evidence(Evidence(
                id=str(uuid4()), candidate_id=candidate.id, claim=claim.claim,
                evidence_type=claim.evidence_type.lower(), source_url=source_url,
                summary=claim.summary + (" Assumptions: " + "; ".join(claim.assumptions) if claim.assumptions else ""),
                supporting_evidence_ids=claim.source_evidence_ids,
            ))
            persisted_ids.append(stored.id)
        report = OpportunityReport(
            candidate_id=candidate.id, component_scores=adversarial.component_scores,
            total_score=adversarial.total_score, confidence=adversarial.confidence,
            verdict=adversarial.verdict,
            risks=[f"[{claim.evidence_type}] {claim.claim}" for claim in adversarial.adversarial_findings],
            recommendation=f"AI analysis for human review only (not approval): {adversarial.recommendation}", evidence_ids=persisted_ids,
            adversarial_review=f"AI sceptical analysis (not observed facts): {adversarial.adversarial_review}",
            next_action="Human review required before any action",
        )
        self.repository.save_report(report)
        return report
