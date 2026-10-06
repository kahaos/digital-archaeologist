from __future__ import annotations
from digital_archaeologist.domain.models import CandidateDraft
def deduplicate(drafts: list[CandidateDraft]) -> list[CandidateDraft]:
    merged: dict[str, CandidateDraft] = {}
    for draft in drafts:
        key = draft.canonical_identity
        if key not in merged: merged[key] = draft; continue
        current = merged[key]
        provenance = list(dict.fromkeys([*current.provenance_urls, *draft.provenance_urls, draft.url]))
        sources = list(dict.fromkeys([*current.metadata.get("sources", []), *draft.metadata.get("sources", []), draft.source]))
        metadata = {**current.metadata, **draft.metadata, "sources": sources}
        merged[key] = current.model_copy(update={"provenance_urls": provenance, "metadata": metadata, "title": current.title or draft.title})
    return list(merged.values())
