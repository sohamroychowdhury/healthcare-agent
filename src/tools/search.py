"""The agent's one tool: a medical knowledge-base search.

We use DuckDuckGo (via the `ddgs` package) as a free, key-free stand-in for a
real clinical database like PubMed. The query is nudged toward medical sources,
and we hand back just the title/snippet/url of the top results.

If the network or `ddgs` is unavailable (or SEARCH_OFFLINE=true), we fall back
to bundled fixtures so the agent and the evaluation still run end-to-end.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from src.config import config
from src.schemas import SearchResult

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "data" / "fixtures"


def _from_web(query: str, max_results: int) -> List[SearchResult]:
    from ddgs import DDGS  # imported lazily so offline runs need no dependency

    # Nudge a general web search toward clinical sources.
    medical_query = f"medical clinical {query}"
    hits = DDGS().text(medical_query, max_results=max_results)
    return [
        SearchResult(
            title=h.get("title", "")[:200],
            snippet=h.get("body", "")[:500],
            url=h.get("href", ""),
        )
        for h in hits
    ]


def _from_fixtures(query: str, max_results: int) -> List[SearchResult]:
    q = query.lower()
    best: List[dict] = []
    default: List[dict] = []
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        if path.stem == "default":
            default = data["results"]
            continue
        if any(kw in q for kw in data["keywords"]):
            best = data["results"]
            break
    results = best or default
    return [SearchResult(**r) for r in results[:max_results]]


def search_medical_database(query: str) -> str:
    """Search and return the top results as a JSON string (the Observation).

    Always returns valid JSON; on any failure it transparently uses fixtures
    rather than raising, so the agent never crashes mid-loop.
    """
    n = config.search_max_results
    try:
        results = _from_fixtures(query, n) if config.search_offline else _from_web(query, n)
    except Exception:
        results = _from_fixtures(query, n)

    return json.dumps([r.model_dump() for r in results], indent=2)
