from __future__ import annotations
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from digital_archaeologist.domain.models import CandidateDraft
_TRACKING_PREFIXES = ("utm_", "mc_", "fbclid")
_TRACKING_EXACT = {"ref", "referrer", "gclid", "dclid"}
def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower(); host = (parts.hostname or "").lower(); port = parts.port
    netloc = host
    if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)): netloc = f"{host}:{port}"
    path = parts.path or "/"
    if path != "/": path = path.rstrip("/")
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not (k.lower().startswith(_TRACKING_PREFIXES) or k.lower() in _TRACKING_EXACT)]
    return urlunsplit((scheme, netloc, path, urlencode(query), ""))
def canonical_identity(draft: CandidateDraft) -> str:
    normalized = normalize_url(draft.url); parts = urlsplit(normalized); host = parts.hostname or ""; path = parts.path.strip("/").lower()
    if host == "github.com" and path:
        bits = path.split("/")
        if len(bits) >= 2: return f"github:{bits[0]}/{bits[1]}"
    return f"{draft.source}:{normalized}"
def normalize_candidate(draft: CandidateDraft) -> CandidateDraft:
    original = draft.url; normalized = normalize_url(original); identity = canonical_identity(draft)
    provenance = list(dict.fromkeys([*draft.provenance_urls, original])); metadata = dict(draft.metadata)
    metadata["sources"] = list(dict.fromkeys([draft.source, *metadata.get("sources", [])]))
    return draft.model_copy(update={"url": normalized, "canonical_identity": identity, "provenance_urls": provenance, "metadata": metadata})
