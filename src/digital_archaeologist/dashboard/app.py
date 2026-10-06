from __future__ import annotations

from datetime import datetime, time, timezone

from digital_archaeologist.config import Settings
from digital_archaeologist.dashboard.views import build_candidate_card, empty_state, filter_candidates
from digital_archaeologist.storage.database import Database
from digital_archaeologist.storage.repositories import Repository


def main() -> None:
    try:
        import streamlit as st
    except ImportError as exc:
        raise RuntimeError("Streamlit is required to run the dashboard; install project dependencies first.") from exc

    repo = Repository(Database(Settings().database_url))
    all_candidates = repo.list_candidates()
    st.set_page_config(page_title="Digital Archaeologist", layout="wide")
    st.title("Digital Archaeologist")
    source_options = sorted({c.source for c in all_candidates})
    category_options = sorted({c.category for c in all_candidates})
    status_options = sorted({c.status for c in all_candidates})
    min_score = st.sidebar.slider("Minimum score", 0, 100, 0)
    min_monetisation = st.sidebar.slider("Minimum monetisation", 0, 15, 0)
    max_effort = st.sidebar.slider("Maximum effort", 0, 100, 100)
    min_confidence = st.sidebar.slider("Minimum confidence", 0.0, 1.0, 0.0)
    min_discovery_date = st.sidebar.date_input("Discovered after", value=None)
    discovered_after = datetime.combine(min_discovery_date, time.min, tzinfo=timezone.utc) if min_discovery_date else None
    selected_sources = set(st.sidebar.multiselect("Source", source_options))
    selected_categories = set(st.sidebar.multiselect("Category", category_options))
    selected_statuses = set(st.sidebar.multiselect("Status", status_options))
    candidates = filter_candidates(all_candidates, min_score=min_score, sources=selected_sources, categories=selected_categories, statuses=selected_statuses, min_monetisation=min_monetisation, max_effort=max_effort, discovered_after=discovered_after)
    reports = [repo.get_report(candidate.id) for candidate in candidates]
    if min_confidence:
        filtered = [(candidate, report) for candidate, report in zip(candidates, reports) if report is not None and report.confidence >= min_confidence]
        candidates = [item[0] for item in filtered]
        reports = [item[1] for item in filtered]
    investigated = sum(report is not None for report in reports)
    strong = sum(report is not None and report.verdict == "STRONG OPPORTUNITY" for report in reports)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Candidates", len(candidates))
    col2.metric("Investigated", investigated)
    col3.metric("Strong opportunities", strong)
    col4.metric("Needs review", sum(report is not None and report.verdict in {"POSSIBLE", "WEAK"} for report in reports))
    if not candidates:
        state = empty_state()
        st.info(f"{state['title']} — {state['message']}")
        return
    for candidate, report in zip(candidates, reports):
        evidence = repo.get_evidence(candidate.id)
        card = build_candidate_card(candidate, report, evidence)
        with st.container(border=True):
            st.subheader(card["title"])
            st.write(card["url"])
            st.metric("Score", card["score"] if card["score"] is not None else "—")
            st.write(f"**Verdict:** {card['verdict']}")
            if card["confidence"] is not None:
                st.write(f"**Confidence:** {card['confidence']:.0%}")
            st.write(f"**Recommendation:** {card['recommendation']}")
            if card["adversarial_review"]:
                st.write(f"**Adversarial review:** {card['adversarial_review']}")
            for risk in card["risks"]:
                st.warning(risk)
            if report is not None:
                st.caption(card["next_action"])
            for item in card["evidence"]:
                st.caption(f"[{item['type']}] {item['claim']} — {item['summary']}")


if __name__ == "__main__":
    main()
