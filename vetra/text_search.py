"""
The text store: hybrid search over the existing Chroma indexes, by domain and state.

It reuses rag/retrieve.py's ranking but makes no LLM call of its own. The planner's one
call already writes the search passage and the topic and key terms, so search stays
vendor-free and inside the question's budget.

An index is registered per (domain, state). A state with no index simply returns nothing,
and the agent says the documents for that state aren't in yet.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAG = str(Path(__file__).resolve().parent.parent / "rag")

# (domain, state) -> the rag/ collection that holds it. New states are added here as their
# documents are indexed.
INDEXES = {("agriculture", "AP"): "agriculture"}


def covered(domain: str, state: str | None) -> bool:
    return (domain, state) in INDEXES


def search(query: str, domain: str, state: str | None, passage: str = "", topic: str = "",
           keywords: tuple[str, ...] = (), k: int = 10) -> list[dict]:
    """The best chunks for a question, best first, with any amending orders added at the end."""
    name = INDEXES.get((domain, state))
    if not name:
        return []
    if RAG not in sys.path:
        sys.path.insert(0, RAG)
    import domains as legacy
    import retrieve as R

    d = legacy.get(name)
    query = legacy.expand_abbreviations(query, d)
    _, texts, metas, bm25 = R._corpus(name)
    votes, weights = [R._hybrid(query, name)], [1.0]
    if passage:
        votes.append(R._hybrid(passage, name))
        weights.append(d.hyde_weight)
    if topic and "topic" in d.expansion:
        votes.append(R._hybrid(topic, name))
        weights.append(1.0)
    if keywords and "kw" in d.expansion:
        votes.append(bm25.rank(" ".join(keywords)))
        weights.append(1.0)
    ranking = R._rrf(*votes, weights=tuple(weights))
    if d.rerank:
        ranking = R._reranked(query, ranking, name, **d.rerank)
    chosen = R._top_k(ranking, metas, k)
    hits = [{"text": texts[i], **metas[i]} for i in chosen]
    for i, why in R._amendment_family(chosen, ranking, name):
        hits.append({"text": texts[i], "added_because": why, **metas[i]})
    return hits
