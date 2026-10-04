"""
Find the chunks most likely to answer a citizen's question.

Three steps, each one earned its place on eval/demo_questions.json:

1. HYBRID SEARCH -- meaning + keywords.
   Dense search (bge-small embeddings) matches meaning; BM25 matches rare exact
   words like "penalty" or "court fee stamp" that embeddings blur. The two
   rankings are merged with Reciprocal Rank Fusion (RRF).

2. HyDE -- search with a hypothetical answer as well as the question.
   Citizens say "the office isn't answering my rti"; the Act says "deemed to have
   refused the request". Those share almost no words, so no search engine can
   connect them directly. We ask a small LLM to write what a legal text answering
   the question would sound like, and search with that too.

   The hypothetical passage is used ONLY to search. It is often wrong on details
   (it once invented a ₹150 fee) and is never shown to the user or to the model
   that writes the answer -- that model sees only real retrieved text.

3. FUSE both searches with RRF, so if the hypothetical passage is off the mark,
   the original question's results still carry it.

Measured: does the answering text reach the top 10? Casual phrasing, across
the three held-out sets in eval/demo_questions.json (34 questions):
    original pipeline ~50%  ->  hybrid ~55%  ->  hybrid + HyDE 82%

Run:  python rag/retrieve.py "govt office not answering my rti what do i do"
      python rag/retrieve.py "what is the fee" --no-hyde
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CHROMA_DIR = ROOT / "data" / "chroma"
COLLECTION = "ap_rti"
TOP_K = 10  # 8 -> 10 raised held-out coverage 76% -> 82%; 12 added nothing
RRF_K = 60

# bge is asymmetric: queries get this instruction, stored chunks do not.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

HYDE_MODEL = "openai/gpt-oss-20b"   # small and fast; only writes a search passage
HYDE_PROMPT = """Write the single sentence or short paragraph (40 to 80 words) that a statute or government RTI order would contain to answer the question below, in formal legal drafting style.

Rules: plain prose only -- no headings, no markdown, no bullet points, no dates, no reference numbers, no titles. Do not mention "Right to Information Act", "Andhra Pradesh" or "RTI" by name. Accuracy of details does not matter; the vocabulary and phrasing must match real legal text. Output only the passage."""
# Why the "do not mention" rule: every document here is about the RTI Act and
# Andhra Pradesh, so those words match everything and drown the real concept.
# Without the rule, rewritten queries retrieved WORSE than the raw question.


# ------------------------------------------------------------------ loading

@lru_cache(maxsize=1)
def _collection():
    import chromadb

    if not CHROMA_DIR.exists():
        sys.exit(f"no index at {CHROMA_DIR} -- run ingest/build_index.py first")
    return chromadb.PersistentClient(path=str(CHROMA_DIR)).get_collection(COLLECTION)


@lru_cache(maxsize=1)
def _model():
    """The model that built the index, read from the index -- never a second constant."""
    from sentence_transformers import SentenceTransformer

    name = _collection().metadata["model"]
    try:
        # Offline first, so a flaky connection can't stall a live demo.
        return SentenceTransformer(name, local_files_only=True)
    except Exception:
        return SentenceTransformer(name)


@lru_cache(maxsize=1)
def _corpus():
    """All chunk ids, texts and metadata, plus a BM25 index over the texts."""
    data = _collection().get(include=["documents", "metadatas"])
    return data["ids"], data["documents"], data["metadatas"], _BM25(data["documents"])


# ------------------------------------------------------------------ BM25

def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class _BM25:
    """Standard Okapi BM25. ~30 lines; not worth a dependency for 500 chunks."""

    def __init__(self, texts: list[str], k1: float = 1.5, b: float = 0.75):
        docs = [_tokens(t) for t in texts]
        self.k1, self.b = k1, b
        self.lengths = [len(d) for d in docs]
        self.avg = sum(self.lengths) / len(docs)
        self.tf = []
        df: dict[str, int] = {}
        for d in docs:
            counts: dict[str, int] = {}
            for w in d:
                counts[w] = counts.get(w, 0) + 1
            self.tf.append(counts)
            for w in counts:
                df[w] = df.get(w, 0) + 1
        n = len(docs)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}

    def rank(self, query: str) -> list[int]:
        scores = [0.0] * len(self.tf)
        for w in _tokens(query):
            idf = self.idf.get(w)
            if idf is None:
                continue
            for i, counts in enumerate(self.tf):
                f = counts.get(w)
                if f:
                    norm = 1 - self.b + self.b * self.lengths[i] / self.avg
                    scores[i] += idf * f * (self.k1 + 1) / (f + self.k1 * norm)
        return sorted(range(len(scores)), key=lambda i: -scores[i])


# ------------------------------------------------------------------ search

def _rrf(*rankings: list[int]) -> list[int]:
    """Reciprocal Rank Fusion: reward documents ranked well by any of the rankings."""
    score: dict[int, float] = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking):
            score[doc] = score.get(doc, 0.0) + 1.0 / (RRF_K + rank + 1)
    return sorted(score, key=lambda d: -score[d])


def _hybrid(text: str) -> list[int]:
    """Dense + BM25 ranking of every chunk for one piece of text."""
    ids, _, _, bm25 = _corpus()
    position = {cid: i for i, cid in enumerate(ids)}
    vector = _model().encode([QUERY_PREFIX + text], normalize_embeddings=True).tolist()
    result = _collection().query(query_embeddings=vector, n_results=len(ids), include=[])
    dense = [position[cid] for cid in result["ids"][0]]
    return _rrf(dense, bm25.rank(text))


_passages: dict[str, str] = {}


def hypothetical_passage(question: str) -> str | None:
    """Ask a small LLM what a legal text answering this would say. None if unavailable."""
    # Only successes are remembered. Caching a failure would mean one rate-limited
    # call silently disables HyDE for that question for the rest of the session.
    if question in _passages:
        return _passages[question]
    try:
        from dotenv import load_dotenv
        from groq import Groq

        load_dotenv(ROOT / ".env")
        reply = Groq().chat.completions.create(
            model=HYDE_MODEL,
            temperature=0,
            reasoning_effort="low",
            messages=[
                {"role": "system", "content": HYDE_PROMPT},
                {"role": "user", "content": question},
            ],
        )
        passage = (reply.choices[0].message.content or "").strip()
        if passage:
            _passages[question] = passage
        return passage or None
    except Exception as exc:
        print(f"  (HyDE unavailable, searching with the question only: {exc})", file=sys.stderr)
        return None


def retrieve(question: str, k: int = TOP_K, hyde: bool = True) -> list[dict]:
    """The k best chunks for a question, best first."""
    return retrieve_with_trace(question, k, hyde)[0]


# Kept small on purpose: every added chunk is ~330 tokens, and Groq's free tier
# allows 8,000 tokens per minute on the answer model.
MAX_AMENDMENT_CHUNKS = 4


def _amendment_family(chosen: list[int], ranking: list[int]) -> list[tuple[int, str]]:
    """
    Chunks of orders that amend -- or are amended by -- an order already retrieved.

    A rule without its amendments is wrong, not just incomplete: G.O.Ms.No.454 set
    the inspection fee at Rs.5 per fifteen minutes, and G.O.Ms.No.545 changed it to
    Rs.5 per hour. Similarity search has no reason to fetch both, so when one is
    retrieved we add the rest of its family. In this corpus that is exactly one
    family (the AP RTI fee rules: 454, amended by 530, 545 and 740); the links are
    detected automatically at ingest from each order's "Amendment to ... Read the
    following" header.
    """
    _, _, metas, _ = _corpus()
    by_order: dict[str, list[int]] = {}
    for i, m in enumerate(metas):
        if m.get("order"):
            by_order.setdefault(m["order"], []).append(i)

    wanted: dict[str, str] = {}
    for i in chosen:
        order = metas[i].get("order")
        for amended in filter(None, (metas[i].get("amends") or "").split(",")):
            wanted.setdefault(amended, f"the order it amends ({order.replace('.', '.No.')})")
        if order:
            for j, m in enumerate(metas):
                if order in (m.get("amends") or "").split(","):
                    wanted.setdefault(m["order"], f"amends {order.replace('.', '.No.')}")

    # Of all the family's chunks not already present, keep the ones the search
    # itself ranked highest -- e.g. G.O.545's inspection-fee change, not G.O.530's
    # accounting head.
    position = {doc: r for r, doc in enumerate(ranking)}
    have = set(chosen)
    candidates = [
        (i, why)
        for order, why in wanted.items()
        for i in by_order.get(order, [])
        if i not in have
    ]
    candidates.sort(key=lambda c: position.get(c[0], len(ranking)))
    return candidates[:MAX_AMENDMENT_CHUNKS]


def retrieve_with_trace(question: str, k: int = TOP_K, hyde: bool = True):
    """Like retrieve(), but also returns the hypothetical passage used (or None)."""
    _, texts, metas, _ = _corpus()
    ranking = _hybrid(question)
    passage = hypothetical_passage(question) if hyde else None
    if passage:
        ranking = _rrf(ranking, _hybrid(passage))

    chosen = ranking[:k]
    hits = [{"text": texts[i], "rank": r + 1, **metas[i]} for r, i in enumerate(chosen)]
    for i, why in _amendment_family(chosen, ranking):
        hits.append({"text": texts[i], "rank": len(hits) + 1, "added_because": why, **metas[i]})
    return hits, passage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--k", type=int, default=TOP_K)
    parser.add_argument("--no-hyde", action="store_true", help="search with the question only")
    args = parser.parse_args()

    hits, passage = retrieve_with_trace(args.question, args.k, not args.no_hyde)
    print(f"\nQ: {args.question}")
    if passage:
        print(f"\nsearch passage (HyDE, not shown to users):\n  {passage}\n")
    for hit in hits:
        print(f"[{hit['rank']}] {hit['source'][:70]}")
        print(f"     {hit['text'][:200].strip()} ...\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
