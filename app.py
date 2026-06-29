"""Minimal Streamlit UI for the healthcare agent.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import json

import streamlit as st

from src.agent import run_agent, validate_query
from src.config import config


def _observation_titles(content: str) -> str:
    """Turn a raw observation JSON string into a short, readable summary."""
    try:
        results = json.loads(content)
        titles = [r["title"] for r in results]
        return f"{len(titles)} results — " + "; ".join(titles)
    except (json.JSONDecodeError, KeyError, TypeError):
        return "results"

st.set_page_config(page_title="Healthcare Q&A Agent", page_icon="+")

st.title("Healthcare Q&A Agent")
st.caption(
    f"ReAct agent · provider: `{config.provider}` · "
    f"{'offline fixtures' if config.search_offline else 'live web search'}"
)

with st.sidebar:
    st.header("How it works")
    st.markdown(
        "1. **Think** about the question\n"
        "2. **Search** a medical knowledge base (DuckDuckGo as a PubMed stand-in)\n"
        "3. **Observe** the results\n"
        "4. **Answer**, grounded in sources"
    )
    st.info("Educational demo only — not medical advice.")

query = st.text_input(
    "Ask a health question",
    placeholder="What are the treatment options for Type 2 diabetes?",
)

if st.button("Ask", type="primary") and query:
    try:
        validate_query(query)
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    with st.spinner("Reasoning..."):
        result = run_agent(query, verbose=False)

    st.subheader("Answer")
    st.write(result.answer)

    if result.sources:
        st.subheader("Sources")
        for url in result.sources:
            st.markdown(f"- [{url}]({url})")

    with st.expander("Reasoning trace", expanded=True):
        st.caption(
            f"Steps taken: {result.steps_taken}"
            + (" (fallback used)" if result.used_fallback else "")
        )
        for event in result.trace:
            kind = event["kind"]
            if kind == "thought":
                st.markdown(f"**Thought:** {event['text']}")
            elif kind == "tool_call":
                st.markdown(f"**Action:** `{event['tool']}({event['input']!r})`")
            elif kind == "observation":
                titles = _observation_titles(event["content"])
                st.markdown(f"**Observation:** retrieved {titles}")
            elif kind == "note":
                st.markdown(f"_Note: {event['text']}_")
            elif kind == "final_answer":
                st.markdown("**Final answer produced.**")
