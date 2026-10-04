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
      python rag/retrieve.py "can tenant farmers get annadata sukhibhava" --domain agriculture

Every function takes a domain ("rti" by default); each domain has its own Chroma
collection and its own HyDE prompt (rag/domains.py). The search itself is identical.
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

import domains  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CHROMA_DIR = ROOT / "data" / "chroma"
TOP_K = 10  # 8 -> 10 raised held-out coverage 76% -> 82%; 12 added nothing
RRF_K = 60

# bge is asymmetric: queries get this instruction, stored chunks do not.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

HYDE_MODEL = "openai/gpt-oss-20b"   # small and fast; only writes a search passage
# The HyDE prompt is per domain (rag/domains.py). For RTI it forbids naming
# "Right to Information Act" / "Andhra Pradesh": those words are in every chunk
# and drowned the real concept -- rewritten queries retrieved WORSE without it.


# ------------------------------------------------------------------ loading

@lru_cache(maxsize=None)
def _collection(domain: str = "rti"):
    import chromadb

    if not CHROMA_DIR.exists():
        sys.exit(f"no index at {CHROMA_DIR} -- run ingest/build_index.py first")
    name = domains.get(domain).collection
    try:
        return chromadb.PersistentClient(path=str(CHROMA_DIR)).get_collection(name)
    except Exception:
        sys.exit(f"no '{name}' collection -- run: python ingest/build_index.py --domain {domain}")


def _model(domain: str = "rti"):
    """The model that built the index, read from the index -- never a second constant."""
    return _load_model(_collection(domain).metadata["model"])


@lru_cache(maxsize=None)
def _load_model(name: str):
    from sentence_transformers import SentenceTransformer

    try:
        # Offline first, so a flaky connection can't stall a live demo.
        return SentenceTransformer(name, local_files_only=True)
    except Exception:
        return SentenceTransformer(name)


@lru_cache(maxsize=None)
def _corpus(domain: str = "rti"):
    """All chunk ids, texts and metadata, plus a BM25 index over the texts."""
    data = _collection(domain).get(include=["documents", "metadatas"])
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

def _rrf(*rankings: list[int], weights: tuple[float, ...] | None = None) -> list[int]:
    """Reciprocal Rank Fusion: reward documents ranked well by any of the rankings."""
    score: dict[int, float] = {}
    for ranking, w in zip(rankings, weights or (1.0,) * len(rankings)):
        for rank, doc in enumerate(ranking):
            score[doc] = score.get(doc, 0.0) + w / (RRF_K + rank + 1)
    return sorted(score, key=lambda d: -score[d])


def _dense(text: str, domain: str = "rti") -> list[int]:
    """Embedding-similarity ranking of every chunk."""
    ids = _corpus(domain)[0]
    position = {cid: i for i, cid in enumerate(ids)}
    vector = _model(domain).encode([QUERY_PREFIX + text], normalize_embeddings=True).tolist()
    result = _collection(domain).query(query_embeddings=vector, n_results=len(ids), include=[])
    return [position[cid] for cid in result["ids"][0]]


def _hybrid(text: str, domain: str = "rti") -> list[int]:
    """Dense + BM25 ranking of every chunk for one piece of text."""
    return _rrf(_dense(text, domain), _corpus(domain)[3].rank(text))


_passages: dict[tuple[str, str], str] = {}

# Experiments only: set HYDE_CACHE=<file.json> so every configuration being
# compared searches with the SAME passages. gpt-oss is not deterministic even at
# temperature 0, and passage drift alone moved the eval by 1-2 questions per run.
_CACHE_FILE = os.environ.get("HYDE_CACHE")


def _disk_cache() -> dict:
    import json

    if not _CACHE_FILE:
        return {}
    try:
        return json.loads(Path(_CACHE_FILE).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def hypothetical_passage(question: str, domain: str = "rti") -> str | None:
    """Ask a small LLM what a legal text answering this would say. None if unavailable."""
    # Only successes are remembered. Caching a failure would mean one rate-limited
    # call silently disables HyDE for that question for the rest of the session.
    if (domain, question) in _passages:
        return _passages[(domain, question)]
    cached = _disk_cache().get(f"{domain}|{question}")
    if cached:
        _passages[(domain, question)] = cached
        return cached
    try:
        from dotenv import load_dotenv
        from groq import Groq

        load_dotenv(ROOT / ".env")
        reply = Groq().chat.completions.create(
            model=HYDE_MODEL,
            temperature=0,
            reasoning_effort="low",
            messages=[
                {"role": "system", "content": domains.get(domain).hyde_prompt},
                {"role": "user", "content": question},
            ],
        )
        passage = (reply.choices[0].message.content or "").strip()
        if passage:
            _passages[(domain, question)] = passage
            if _CACHE_FILE:
                import json

                store = _disk_cache()
                store[f"{domain}|{question}"] = passage
                Path(_CACHE_FILE).write_text(json.dumps(store, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
        return passage or None
    except Exception as exc:
        print(f"  (HyDE unavailable, searching with the question only: {exc})", file=sys.stderr)
        return None


def retrieve(question: str, k: int = TOP_K, hyde: bool = True, domain: str = "rti") -> list[dict]:
    """The k best chunks for a question, best first."""
    return retrieve_with_trace(question, k, hyde, domain)[0]


# Kept small on purpose: every added chunk is ~330 tokens, and Groq's free tier
# allows 8,000 tokens per minute on the answer model.
MAX_AMENDMENT_CHUNKS = 4


def _amendment_family(chosen: list[int], ranking: list[int], domain: str = "rti") -> list[tuple[int, str]]:
    """
    Chunks of orders that amend -- or are amended by -- an order already retrieved.

    A rule without its amendments is wrong, not just incomplete: G.O.Ms.No.454 set
    the inspection fee at Rs.5 per fifteen minutes, and G.O.Ms.No.545 changed it to
    Rs.5 per hour. Similarity search has no reason to fetch both, so when one is
    retrieved we add the rest of its family. In this corpus that is exactly one
    family (the AP RTI fee rules: 454, amended by 530, 545 and 740); the links are
    detected automatically at ingest from each order's "Amendment to ... Read the
    following" header. Agriculture's links come from the manifest's "amends" field.

    A document marked not in force is never ADDED this way (it can still be
    retrieved on its own merits): a question that finds the current Annadata
    Sukhibhava order must not be padded with the replaced YSR Rythu Bharosa one.
    """
    _, _, metas, _ = _corpus(domain)

    def name(m: dict) -> str:
        return m.get("order_label") or m["order"].replace(".", ".No.")
    by_order: dict[str, list[int]] = {}
    for i, m in enumerate(metas):
        if m.get("order"):
            by_order.setdefault(m["order"], []).append(i)

    wanted: dict[str, str] = {}
    for i in chosen:
        order = metas[i].get("order")
        for amended in filter(None, (metas[i].get("amends") or "").split(",")):
            wanted.setdefault(amended, f"is the order amended by {name(metas[i])}")
        if order:
            for j, m in enumerate(metas):
                if order in (m.get("amends") or "").split(","):
                    wanted.setdefault(m["order"], f"amends {name(metas[i])}")

    # Of all the family's chunks not already present, keep the ones the search
    # itself ranked highest -- e.g. G.O.545's inspection-fee change, not G.O.530's
    # accounting head.
    position = {doc: r for r, doc in enumerate(ranking)}
    have = set(chosen)
    candidates = [
        (i, why)
        for order, why in wanted.items()
        for i in by_order.get(order, [])
        if i not in have and metas[i].get("in_force") != "no"
    ]
    candidates.sort(key=lambda c: position.get(c[0], len(ranking)))
    return candidates[:MAX_AMENDMENT_CHUNKS]


# A replaced document (labelled not in force) keeps at most this many places in
# the top k. The YSR Rythu Bharosa order (12 chunks) is ABOUT Rythu Bharosa, so it
# out-ranked both the current Annadata Sukhibhava order and the rename order for
# every "what is Rythu Bharosa called now / am I eligible" question. One chunk
# still answers "what was Rythu Bharosa"; more only crowds out current rules.
# RTI chunks carry no in_force label, so RTI is unaffected.
MAX_NOT_IN_FORCE = 1


def _top_k(ranking: list[int], metas: list[dict], k: int) -> list[int]:
    chosen, replaced = [], 0
    for i in ranking:
        if metas[i].get("in_force") == "no":
            if replaced >= MAX_NOT_IN_FORCE:
                continue
            replaced += 1
        chosen.append(i)
        if len(chosen) == k:
            break
    return chosen


def _expanded(question: str, ranking: list[int], passage: str | None, domain: str) -> list[int]:
    """
    The domain's extra signals (rag/domains.py: expansion, doc_boost, rerank), each
    measured in eval/experiments.py. With none configured the ranking is unchanged.

    Every extra LLM ranking joins the SAME fusion as the question and HyDE rankings,
    as one more vote -- exactly how the experiments combined them.
    """
    import query_expansion as QX

    d = domains.get(domain)
    if d.expansion:
        votes, weights = [_hybrid(question, domain)], [1.0]
        if passage:
            votes.append(_hybrid(passage, domain))
            weights.append(float(os.environ.get("HYDE_WEIGHT") or d.hyde_weight))
        b = QX.rewrites(question, domain) or {}
        if "topic" in d.expansion and b.get("topic"):
            votes.append(_hybrid(b["topic"], domain))
            weights.append(1.0)
        if "mq" in d.expansion and b.get("queries"):
            bm25 = _corpus(domain)[3]
            votes.append(_rrf(*[r for x in b["queries"] for r in (_dense(x, domain), bm25.rank(x))]))
            weights.append(1.0)
        if "kw" in d.expansion and b.get("keywords"):
            votes.append(_corpus(domain)[3].rank(" ".join(b["keywords"])))
            weights.append(1.0)
        if len(votes) > (2 if passage else 1):   # at least one rewrite arrived
            ranking = _rrf(*votes, weights=tuple(weights))

    if d.doc_boost:
        picked = set(QX.select_documents(question, domain) or [])
        if picked:
            metas = _corpus(domain)[2]
            inside = [i for i in ranking if QX.unit_key(metas[i]) in picked]
            ranking = _rrf(ranking, inside, weights=(1.0, d.doc_boost))

    if d.rerank:
        ranking = _reranked(question, ranking, domain, **d.rerank)
    return ranking


@lru_cache(maxsize=None)
def _cross_encoder(name: str):
    from sentence_transformers import CrossEncoder

    try:
        return CrossEncoder(name, max_length=512, local_files_only=True)
    except Exception:
        return CrossEncoder(name, max_length=512)


def _reranked(question: str, ranking: list[int], domain: str, model: str, n: int = 30,
              doc: str = "text", mode: str = "replace", ce_weight: float = 1.0) -> list[int]:
    """Re-score the top n with a cross-encoder; "fuse" keeps the fused order as a second vote."""
    _, texts, metas, _ = _corpus(domain)
    cand = ranking[:n]
    docs = [f"{metas[i].get('title', '')}\n{texts[i]}" if doc == "title+text" else texts[i] for i in cand]
    scores = _cross_encoder(model).predict([(question, x) for x in docs], batch_size=16)
    order = [cand[j] for j in sorted(range(len(cand)), key=lambda j: -scores[j])]
    if mode == "fuse":
        order = _rrf(cand, order, weights=(1.0, ce_weight))
    return order + ranking[n:]


def retrieve_with_trace(question: str, k: int = TOP_K, hyde: bool = True, domain: str = "rti"):
    """Like retrieve(), but also returns the hypothetical passage used (or None)."""
    _, texts, metas, _ = _corpus(domain)
    # "RBK" -> "RBK (Rythu Bharosa Kendram, ...)": only the SEARCH text is expanded
    # (agriculture's glossary; RTI has none). HyDE once wrote "Rural Business
    # Knowledge Centre" for RBK; with the expansion it knows what is meant.
    d = domains.get(domain)
    question = domains.expand_abbreviations(question, d)
    ranking = _hybrid(question, domain)
    passage = hypothetical_passage(question, domain) if hyde else None
    if passage:
        # The HyDE ranking's vote relative to the question's (1.0 = equal, as RTI was tuned).
        weight = float(os.environ.get("HYDE_WEIGHT") or d.hyde_weight)
        mode = os.environ.get("HYDE_MODE") or d.hyde_mode
        if mode == "dense":      # passage searched by meaning only, not keywords
            ranking = _rrf(ranking, _dense(passage, domain), weights=(1.0, weight))
        elif mode == "concat":   # one hybrid search with question + passage
            ranking = _hybrid(f"{question}\n{passage}", domain)
        else:                    # "rrf": two hybrid searches fused (RTI's tuned setting)
            ranking = _rrf(ranking, _hybrid(passage, domain), weights=(1.0, weight))
    # hyde=False means no search-time LLM call at all, so it also turns these off.
    if hyde:
        ranking = _expanded(question, ranking, passage, domain)

    chosen = _top_k(ranking, metas, k)
    hits = [{"text": texts[i], "rank": r + 1, **metas[i]} for r, i in enumerate(chosen)]
    for i, why in _amendment_family(chosen, ranking, domain):
        hits.append({"text": texts[i], "rank": len(hits) + 1, "added_because": why, **metas[i]})
    return hits, passage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--k", type=int, default=TOP_K)
    parser.add_argument("--no-hyde", action="store_true", help="search with the question only")
    parser.add_argument("--domain", default="rti", choices=list(domains.DOMAINS))
    args = parser.parse_args()

    hits, passage = retrieve_with_trace(args.question, args.k, not args.no_hyde, args.domain)
    print(f"\nQ: {args.question}")
    if passage:
        print(f"\nsearch passage (HyDE, not shown to users):\n  {passage}\n")
    for hit in hits:
        print(f"[{hit['rank']}] {hit['source'][:70]}")
        print(f"     {hit['text'][:200].strip()} ...\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
