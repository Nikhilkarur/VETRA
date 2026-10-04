"""
Retrieval experiment bench: try combinations of search techniques on every
question set, without touching the live pipeline.

Each question is searched by several SIGNALS -- one retriever run over one text:

    retrievers   dense (bge-small, the live index's own vectors), dense:<model>
                 (another embedding model, corpus re-embedded here), bm25 (the
                 live keyword index), bm25s (light stemming + stopwords), bm25t
                 (document title indexed with the text)
    texts        q (the question, abbreviations expanded), hyde (the live HyDE
                 passage), and the LLM-made variants in rag/query_expansion.py:
                 mq1..mq3 (alternative queries), kw (key terms), topic,
                 hyde2/hyde3 (passages in other document styles)

A CONFIG fuses signals with Reciprocal Rank Fusion -- in groups, so the live
pipeline's "RRF of (question hybrid) and (HyDE hybrid)" is reproduced exactly --
then optionally reranks the top N with a cross-encoder, and applies the same
not-in-force cap as the live code. Metric: does every probe phrase appear in the
top-k chunks (k=10, what the answer model sees), as in eval/retrieval_eval.py;
plus the rank at which all probes are first covered.

Every LLM output is cached in eval/cache/ (committed), so a configuration is
always compared on identical passages; gpt-oss is not deterministic even at
temperature 0. The 'final' sets are excluded unless --final is given -- they are
run only for the baseline and the chosen configuration.

Run:  python eval/experiments.py --domain rti --exp baseline
      python eval/experiments.py --domain agriculture --exp fusion rerank
      python eval/experiments.py --domain rti --exp baseline best --final
      python eval/experiments.py --list
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "eval" / "cache"
CACHE.mkdir(exist_ok=True)
os.environ.setdefault("HYDE_CACHE", str(CACHE / "hyde.json"))
os.environ.setdefault("LLM_CACHE_DIR", str(CACHE))
sys.path.insert(0, str(ROOT / "rag"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import domains  # noqa: E402
import retrieve as R  # noqa: E402
from query_expansion import unit_key  # noqa: E402

QUESTIONS = {"rti": ROOT / "eval" / "demo_questions.json",
             "agriculture": ROOT / "eval" / "agri_questions.json"}
# Written on 2026-10-04 before any of these experiments: the clean test.
CLEAN = {"rti": "heldout4", "agriculture": "heldout3"}
DEPTH = 60  # how deep the cover rank is tracked


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


# ------------------------------------------------------------------ keyword search

STOP = set("""a an the of to in on for and or is are was were be been it its this that
these those with by as at from i my me we our you your do does did can could will would
shall should may might what which who whom how when where why if not no any all there
their they them he she his her about into than then so get got have has had am""".split())


def light_stem(word: str) -> str:
    """S-stemmer (Harman 1991) plus -ing/-ed: 'seeds'->'seed', 'farmers'->'farmer'."""
    for suffix, keep in (("ies", "y"), ("es", ""), ("s", ""), ("ing", ""), ("ed", "")):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3 and not word.endswith("ss"):
            return word[: -len(suffix)] + keep
    return word


def tokens_plain(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def tokens_stem(text: str) -> list[str]:
    return [light_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP]


class BM25:
    """Same scoring as rag/retrieve.py's _BM25, with a pluggable tokenizer and an inverted index."""

    def __init__(self, texts: list[str], tokenize, k1: float = 1.5, b: float = 0.75):
        self.tokenize, self.k1, self.b = tokenize, k1, b
        docs = [tokenize(t) for t in texts]
        self.n = len(docs)
        lengths = np.array([len(d) for d in docs], dtype=float)
        self.norm = 1 - b + b * lengths / lengths.mean()
        self.post: dict[str, list[tuple[int, int]]] = {}
        for i, d in enumerate(docs):
            counts: dict[str, int] = {}
            for w in d:
                counts[w] = counts.get(w, 0) + 1
            for w, c in counts.items():
                self.post.setdefault(w, []).append((i, c))
        self.idf = {w: math.log(1 + (self.n - len(p) + 0.5) / (len(p) + 0.5)) for w, p in self.post.items()}

    def rank(self, query: str) -> np.ndarray:
        scores = np.zeros(self.n)
        for w in self.tokenize(query):  # repeated query words count again, as in the live code
            for i, f in self.post.get(w, ()):
                scores[i] += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * self.norm[i])
        return np.argsort(-scores, kind="stable")


# ------------------------------------------------------------------ the bench

class Bench:
    def __init__(self, domain: str):
        self.domain = domain
        self.d = domains.get(domain)
        self.ids, self.texts, self.metas, _ = R._corpus(domain)
        got = R._collection(domain).get(include=["embeddings"])
        pos = {cid: i for i, cid in enumerate(got["ids"])}
        self.E = np.array([got["embeddings"][pos[cid]] for cid in self.ids], dtype=np.float32)
        self.titled = [f"{m.get('title', '')}\n{t}" for t, m in zip(self.texts, self.metas)]
        self._bm25 = {}
        self._emb = {}
        self._rank_cache: dict[tuple, np.ndarray] = {}
        self._ce = {}
        self._ce_scores: dict[tuple, float] = {}

    # --- retrievers
    def bm25_index(self, kind: str) -> BM25:
        if kind not in self._bm25:
            if kind == "bm25":
                self._bm25[kind] = BM25(self.texts, tokens_plain)
            elif kind == "bm25s":
                self._bm25[kind] = BM25(self.texts, tokens_stem)
            elif kind == "bm25t":
                self._bm25[kind] = BM25(self.titled, tokens_plain)
            elif kind == "bm25st":
                self._bm25[kind] = BM25(self.titled, tokens_stem)
            else:
                raise ValueError(kind)
        return self._bm25[kind]

    def embeddings(self, model: str) -> tuple[np.ndarray, object]:
        """Corpus vectors for another embedding model, embedded the way build_index.py does."""
        if model not in self._emb:
            enc = R._load_model(model)
            file = CACHE / f"emb_{self.domain}_{model.replace('/', '_')}.npy"
            if file.exists():
                E = np.load(file)
            else:
                docs = self.titled if self.d.embed_title else self.texts
                t0 = time.perf_counter()
                E = enc.encode(docs, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
                np.save(file, E)
                print(f"  (embedded {len(docs)} chunks with {model} in {time.perf_counter() - t0:.0f}s)")
            self._emb[model] = (np.asarray(E, dtype=np.float32), enc)
        return self._emb[model]

    def rank(self, retriever: str, text: str) -> np.ndarray:
        key = (retriever, text)
        if key not in self._rank_cache:
            if retriever == "dense":
                v = R._model(self.domain).encode([R.QUERY_PREFIX + text], normalize_embeddings=True)[0]
                r = np.argsort(-(self.E @ v), kind="stable")
            elif retriever.startswith("dense:"):
                E, enc = self.embeddings(retriever[6:])
                prefix = R.QUERY_PREFIX if "bge" in retriever else ("query: " if "e5" in retriever else "")
                v = enc.encode([prefix + text], normalize_embeddings=True)[0]
                r = np.argsort(-(E @ v), kind="stable")
            else:
                r = self.bm25_index(retriever).rank(text)
            self._rank_cache[key] = r
        return self._rank_cache[key]

    def overlap(self, i: int, j: int) -> float:
        """Share of the smaller chunk's distinct words that the other chunk also has."""
        if not hasattr(self, "_words"):
            self._words = [set(tokens_plain(t)) for t in self.texts]
        a, b = self._words[i], self._words[j]
        return len(a & b) / max(1, min(len(a), len(b)))

    # --- cross-encoder
    def ce_scores(self, model: str, query: str, cand: list[int], doc: str) -> list[float]:
        if model not in self._ce:
            from sentence_transformers import CrossEncoder
            self._ce[model] = CrossEncoder(model, max_length=512)
        todo = [i for i in cand if (model, doc, query, i) not in self._ce_scores]
        if todo:
            docs = self.titled if doc == "title+text" else self.texts
            scores = self._ce[model].predict([(query, docs[i]) for i in todo], batch_size=16,
                                             show_progress_bar=False)
            for i, s in zip(todo, scores):
                self._ce_scores[(model, doc, query, i)] = float(s)
        return [self._ce_scores[(model, doc, query, i)] for i in cand]


def rrf(rankings: list, weights: list[float], k: int, depth: int | None = None) -> list[int]:
    score: dict[int, float] = {}
    for ranking, w in zip(rankings, weights):
        for r, doc in enumerate(ranking[:depth] if depth else ranking):
            doc = int(doc)
            score[doc] = score.get(doc, 0.0) + w / (k + r + 1)
    return sorted(score, key=lambda d: -score[d])


# ------------------------------------------------------------------ query texts

def texts_for(question: str, domain: str, needed: set[str]) -> dict[str, list[str]]:
    """The texts each source name stands for. A source may stand for several texts (mq)."""
    import query_expansion as QX

    d = domains.get(domain)
    q = domains.expand_abbreviations(question, d)
    out: dict[str, list[str]] = {"q": [q], "raw": [question]}
    if needed & {"hyde"}:
        p = R.hypothetical_passage(q, domain)
        out["hyde"] = [p] if p else []
    if needed & {"mq", "mq1", "kw", "topic", "q+kw"}:
        b = QX.rewrites(q, domain) or {}
        qs = b.get("queries") or []
        out["mq"] = qs
        for i, x in enumerate(qs[:3], 1):
            out[f"mq{i}"] = [x]
        out["kw"] = [" ".join(b.get("keywords") or [])] if b.get("keywords") else []
        out["topic"] = [b["topic"]] if b.get("topic") else []
        out["q+kw"] = [q + " " + out["kw"][0]] if out["kw"] else [q]
    if needed & {"hyde2", "hyde3", "mhyde"}:
        ps = QX.multi_hyde(q, domain) or []
        out["mhyde"] = ps
        for i, x in enumerate(ps[:3], 1):
            out[f"hyde{i}"] = [x]
    if "q+hyde" in needed:
        p = R.hypothetical_passage(q, domain)
        out["q+hyde"] = [f"{q}\n{p}"] if p else [q]
    return out


# ------------------------------------------------------------------ one configuration

def run_config(bench: Bench, cfg: dict, question: str, texts: dict[str, list[str]],
               extra: dict | None = None) -> list[int]:
    """The final ranked list of chunk indices for one question under one config."""
    groups_out, group_w = [], []
    for g in cfg["groups"]:
        rankings, weights = [], []
        for src, retriever, w in g["signals"]:
            for t in texts.get(src, []):
                if t:
                    rankings.append(bench.rank(retriever, t))
                    weights.append(w)
        if rankings:
            groups_out.append(rrf(rankings, weights, cfg.get("rrf_k", 60)) if len(rankings) > 1
                              else [int(x) for x in rankings[0]])
            group_w.append(g.get("weight", 1.0))
    ranking = rrf(groups_out, group_w, cfg.get("rrf_k", 60)) if len(groups_out) > 1 else groups_out[0]

    if extra and cfg.get("doc_boost"):   # agentic document selection (query_expansion.select_documents)
        chosen_docs = set(extra.get(cfg.get("doc_source", DOC_SOURCE)) or [])
        if chosen_docs:
            inside = [i for i in ranking if unit_key(bench.metas[i]) in chosen_docs]
            ranking = rrf([ranking, inside], [1.0, cfg["doc_boost"]], cfg.get("rrf_k", 60))

    rr = cfg.get("rerank")
    if rr:
        n = rr.get("n", 30)
        cand = ranking[:n]
        query = texts["q"][0] if rr.get("query", "q") == "q" else texts.get(rr["query"], texts["q"])[0]
        scores = bench.ce_scores(rr["model"], query, cand, rr.get("doc", "text"))
        if rr.get("query2"):
            q2 = texts.get(rr["query2"], [])
            if q2:
                s2 = bench.ce_scores(rr["model"], q2[0], cand, rr.get("doc", "text"))
                scores = [a + b for a, b in zip(scores, s2)]
        ce_rank = [cand[j] for j in sorted(range(len(cand)), key=lambda j: -scores[j])]
        if rr.get("mode", "replace") == "fuse":
            ce_rank = rrf([cand, ce_rank], [1.0, rr.get("ce_weight", 1.0)], cfg.get("rrf_k", 60))
        ranking = ce_rank + ranking[n:]

    # The live not-in-force cap (agriculture): at most one replaced-document chunk.
    # Optional diversity rules for the top k only: a cap on chunks per document, and
    # dropping a chunk whose words mostly repeat a chunk already chosen.
    k = cfg.get("k", 10)
    cap, dedupe = cfg.get("per_doc_cap"), cfg.get("dedupe")
    out, replaced, per_doc, deferred = [], 0, {}, []
    for i in ranking:
        if bench.metas[i].get("in_force") == "no":
            if replaced >= R.MAX_NOT_IN_FORCE:
                continue
            replaced += 1
        if len(out) < k:
            doc = bench.metas[i].get("file")
            if cap and per_doc.get(doc, 0) >= cap:
                deferred.append(i)
                continue
            if dedupe and any(bench.overlap(i, j) >= dedupe for j in out):
                deferred.append(i)
                continue
            per_doc[doc] = per_doc.get(doc, 0) + 1
        out.append(i)
        if len(out) == k and deferred:   # skipped chunks still count beyond the top k
            out.extend(deferred)
            deferred = []
        if len(out) >= DEPTH:
            break
    return out[:DEPTH]


def cover_rank(bench: Bench, ranking: list[int], probes: list[str]) -> int | None:
    """Smallest r such that every probe appears in the top r chunks."""
    need = {squash(p) for p in probes}
    found: set[str] = set()
    for r, i in enumerate(ranking, 1):
        t = squash(bench.texts[i])
        found |= {p for p in need if p in t}
        if found == need:
            return r
    return None


# ------------------------------------------------------------------ experiment catalogue

def hybrid(src: str, dense: str = "dense", bm25: str = "bm25", w: float = 1.0) -> dict:
    return {"weight": w, "signals": [(src, dense, 1.0), (src, bm25, 1.0)]}


BASE = {"groups": [hybrid("q"), hybrid("hyde")], "rrf_k": 60}  # the live pipeline
DOC_SOURCE = "docselect-batch@gpt-oss-120b"  # picks made 8 questions per call (see docs/RETRIEVAL_EXPERIMENTS.md)
MINILM = "cross-encoder/ms-marco-MiniLM-L-6-v2"
BGE_RR = "BAAI/bge-reranker-base"
BGE_M3 = "BAAI/bge-reranker-v2-m3"


def with_(cfg: dict, **kw) -> dict:
    out = json.loads(json.dumps(cfg))
    out.update(kw)
    return out


EXPERIMENTS: dict[str, dict[str, dict]] = {
    "baseline": {"live (hybrid q + hybrid HyDE)": BASE,
                 "no HyDE (hybrid q)": {"groups": [hybrid("q")]}},
    "signals": {
        "dense q only": {"groups": [{"signals": [("q", "dense", 1)]}]},
        "bm25 q only": {"groups": [{"signals": [("q", "bm25", 1)]}]},
        "dense HyDE only": {"groups": [{"signals": [("hyde", "dense", 1)]}]},
        "bm25 HyDE only": {"groups": [{"signals": [("hyde", "bm25", 1)]}]},
        "flat 4-way RRF": {"groups": [{"signals": [("q", "dense", 1), ("q", "bm25", 1),
                                                   ("hyde", "dense", 1), ("hyde", "bm25", 1)]}]},
        "q hybrid + HyDE dense": {"groups": [hybrid("q"), {"signals": [("hyde", "dense", 1)]}]},
        "q + HyDE concatenated": {"groups": [hybrid("q+hyde")]},
    },
    "fusion": {
        **{f"rrf k={k}": with_(BASE, rrf_k=k) for k in (10, 30, 100)},
        **{f"HyDE group weight {w}": {"groups": [hybrid("q"), hybrid("hyde", w=w)]} for w in (0.5, 1.5, 2.0)},
    },
    "bm25": {
        "bm25s (stem+stop)": {"groups": [hybrid("q", bm25="bm25s"), hybrid("hyde", bm25="bm25s")]},
        "bm25t (title)": {"groups": [hybrid("q", bm25="bm25t"), hybrid("hyde", bm25="bm25t")]},
        "bm25st (stem+stop+title)": {"groups": [hybrid("q", bm25="bm25st"), hybrid("hyde", bm25="bm25st")]},
    },
    "rerank": {
        **{f"MiniLM CE top{n} replace": with_(BASE, rerank={"model": MINILM, "n": n}) for n in (20, 30, 50)},
        "MiniLM CE top30 fuse": with_(BASE, rerank={"model": MINILM, "n": 30, "mode": "fuse"}),
        "MiniLM CE top30 title+text": with_(BASE, rerank={"model": MINILM, "n": 30, "doc": "title+text"}),
        "MiniLM CE top30 q+HyDE": with_(BASE, rerank={"model": MINILM, "n": 30, "query2": "hyde"}),
    },
    "rerank_bge": {
        **{f"bge-reranker-base top{n} replace": with_(BASE, rerank={"model": BGE_RR, "n": n}) for n in (20, 30, 50)},
        "bge-reranker-base top30 fuse": with_(BASE, rerank={"model": BGE_RR, "n": 30, "mode": "fuse"}),
        "bge-reranker-base top30 title+text": with_(BASE, rerank={"model": BGE_RR, "n": 30, "doc": "title+text"}),
    },
    "embed": {
        "bge-base dense + bm25 (q, HyDE)": {"groups": [hybrid("q", dense="dense:BAAI/bge-base-en-v1.5"),
                                                       hybrid("hyde", dense="dense:BAAI/bge-base-en-v1.5")]},
        "bge-small + bge-base + bm25": {"groups": [
            {"signals": [("q", "dense", 1), ("q", "dense:BAAI/bge-base-en-v1.5", 1), ("q", "bm25", 1)]},
            {"signals": [("hyde", "dense", 1), ("hyde", "dense:BAAI/bge-base-en-v1.5", 1), ("hyde", "bm25", 1)]}]},
    },
    "diversity": {
        **{f"live, max {c} chunks per document": with_(BASE, per_doc_cap=c) for c in (2, 3, 4)},
        **{f"live, drop near-duplicates >= {t}": with_(BASE, dedupe=t) for t in (0.6, 0.8)},
        "live, max 3 per doc + dedupe 0.8": with_(BASE, per_doc_cap=3, dedupe=0.8),
    },
    "agent_docs": {
        **{f"live + doc selection boost {w}": with_(BASE, doc_boost=w) for w in (0.5, 1.0, 2.0)},
    },
    "expand": {
        "live + multi-query (3)": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("mq")]},
        "live + keywords (bm25)": {"groups": [hybrid("q"), hybrid("hyde"), {"signals": [("kw", "bm25", 1)]}]},
        "live + topic": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("topic")]},
        "live + mq + kw": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("mq"), {"signals": [("kw", "bm25", 1)]}]},
        "q + mq (no HyDE)": {"groups": [hybrid("q"), hybrid("mq")]},
        "q+kw instead of q": {"groups": [hybrid("q+kw"), hybrid("hyde")]},
    },
    "combo": {
        "live + topic + mq + kw": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("topic"), hybrid("mq"),
                                              {"signals": [("kw", "bm25", 1)]}]},
        "live + topic + mq + kw, docs 0.5": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("topic"), hybrid("mq"),
                                                        {"signals": [("kw", "bm25", 1)]}], "doc_boost": 0.5},
        "live + topic + kw": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("topic"),
                                         {"signals": [("kw", "bm25", 1)]}]},
        "live + topic + kw, HyDE x1.5": {"groups": [hybrid("q"), hybrid("hyde", w=1.5), hybrid("topic"),
                                                    {"signals": [("kw", "bm25", 1)]}]},
        "live + mq + kw + MiniLM t+t": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("mq"),
                                                   {"signals": [("kw", "bm25", 1)]}],
                                        "rerank": {"model": MINILM, "n": 30, "doc": "title+text"}},
        "live + mq + kw + MiniLM t+t fuse": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("mq"),
                                                        {"signals": [("kw", "bm25", 1)]}],
                                             "rerank": {"model": MINILM, "n": 30, "doc": "title+text", "mode": "fuse"}},
        "live + topic + mq + kw + MiniLM fuse": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("topic"), hybrid("mq"),
                                                            {"signals": [("kw", "bm25", 1)]}],
                                                 "rerank": {"model": MINILM, "n": 30, "doc": "title+text", "mode": "fuse"}},
        "live + topic + kw + MiniLM t+t fuse": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("topic"),
                                                           {"signals": [("kw", "bm25", 1)]}],
                                                "rerank": {"model": MINILM, "n": 30, "doc": "title+text", "mode": "fuse"}},
        "live + topic + kw + MiniLM q+HyDE fuse": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("topic"),
                                                              {"signals": [("kw", "bm25", 1)]}],
                                                   "rerank": {"model": MINILM, "n": 30, "doc": "title+text",
                                                              "mode": "fuse", "query2": "hyde"}},
        "live, docs 0.5 + MiniLM t+t": with_(BASE, doc_boost=0.5, rerank={"model": MINILM, "n": 30, "doc": "title+text"}),
        "all + docs 0.5 + MiniLM t+t fuse": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("topic"), hybrid("mq"),
                                                        {"signals": [("kw", "bm25", 1)]}], "doc_boost": 0.5,
                                             "rerank": {"model": MINILM, "n": 30, "doc": "title+text", "mode": "fuse"}},
    },
    "pick": {   # the finalists, run together (and with --final at the very end)
        "live + topic + kw": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("topic"),
                                         {"signals": [("kw", "bm25", 1)]}]},
        "live + topic + kw + MiniLM t+t fuse": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("topic"),
                                                           {"signals": [("kw", "bm25", 1)]}],
                                                "rerank": {"model": MINILM, "n": 30, "doc": "title+text", "mode": "fuse"}},
        "live + topic + mq + kw + MiniLM fuse": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("topic"), hybrid("mq"),
                                                            {"signals": [("kw", "bm25", 1)]}],
                                                 "rerank": {"model": MINILM, "n": 30, "doc": "title+text", "mode": "fuse"}},
    },
    "pick_bge": {
        "live + topic + kw + bge-rr t+t": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("topic"),
                                                      {"signals": [("kw", "bm25", 1)]}],
                                           "rerank": {"model": BGE_RR, "n": 30, "doc": "title+text"}},
        "live + topic + kw + bge-rr t+t fuse": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("topic"),
                                                           {"signals": [("kw", "bm25", 1)]}],
                                                "rerank": {"model": BGE_RR, "n": 30, "doc": "title+text", "mode": "fuse"}},
        "live + bge-rr t+t q+HyDE": with_(BASE, rerank={"model": BGE_RR, "n": 30, "doc": "title+text", "query2": "hyde"}),
    },
    "chosen": {   # what rag/domains.py now runs, per domain (see docs/RETRIEVAL_EXPERIMENTS.md)
        "RTI: live + topic + kw": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("topic"),
                                              {"signals": [("kw", "bm25", 1)]}]},
        "agri: live + topic + kw + MiniLM fuse": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("topic"),
                                                             {"signals": [("kw", "bm25", 1)]}],
                                                  "rerank": {"model": MINILM, "n": 30, "doc": "title+text", "mode": "fuse"}},
    },
    "mhyde": {
        "live + 3 HyDE styles": {"groups": [hybrid("q"), hybrid("hyde"), hybrid("mhyde")]},
        "q + 3 HyDE styles (no live HyDE)": {"groups": [hybrid("q"), hybrid("mhyde")]},
    },
}


def run(domain: str, names: list[str], final: bool, show: bool) -> None:
    bench = Bench(domain)
    data = json.loads(QUESTIONS[domain].read_text(encoding="utf-8"))
    sets = [k for k, v in data.items() if isinstance(v, list) and (final or k != "final")]
    if final and "final" not in sets:
        sets.append("final")
    configs: dict[str, dict] = {}
    for n in names:
        if n not in EXPERIMENTS:
            raise SystemExit(f"unknown experiment {n!r}; choose from {', '.join(EXPERIMENTS)}")
        configs.update(EXPERIMENTS[n])
    needed = {s for cfg in configs.values() for g in cfg["groups"] for s, _, _ in g["signals"]}
    needed |= {cfg["rerank"].get("query2") for cfg in configs.values() if cfg.get("rerank")} - {None}

    questions = [(s, item) for s in sets for item in data[s]]
    t0 = time.perf_counter()
    texts = {item["q"]: texts_for(item["q"], domain, needed) for _, item in questions}
    print(f"{domain}: {len(questions)} questions, sets {sets}  (query texts ready in {time.perf_counter() - t0:.0f}s)\n")

    # Document picks are read from a cache file named by the config ("doc_source"),
    # never fetched here: the batched experiment picks and live single-call picks
    # come from different runs and must not mix silently.
    extras: dict[str, dict] = {item["q"]: {} for _, item in questions}
    for source in {cfg.get("doc_source", DOC_SOURCE) for cfg in configs.values() if cfg.get("doc_boost")}:
        file = CACHE / f"{source}.json"
        store = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}
        missing = 0
        for _, item in questions:
            picked = store.get(f"{domain}|{texts[item['q']]['q'][0]}")
            missing += picked is None
            extras[item["q"]][source] = picked
        if missing:
            print(f"  ({missing} questions have no picks in {file.name})")

    results = {}
    for name, cfg in configs.items():
        t0 = time.perf_counter()
        ranks = []
        for s, item in questions:
            ranking = run_config(bench, cfg, item["q"], texts[item["q"]], extras.get(item["q"]))
            ranks.append((s, item["q"], cover_rank(bench, ranking, item["probes"])))
        results[name] = (ranks, time.perf_counter() - t0)

    def hits(ranks, k, which=None):
        rs = [r for s, _, r in ranks if which is None or s == which]
        return sum(1 for r in rs if r is not None and r <= k), len(rs)

    clean = CLEAN[domain]
    head = f"{'configuration':<38}{'@10 all':>9}{'@5':>6}{'@20':>6}{'MRR':>6}  " + "".join(f"{s[:9]:>10}" for s in sets) + "   time"
    print(head)
    print("-" * len(head))
    for name, (ranks, secs) in results.items():
        h10, n = hits(ranks, 10)
        mrr = sum(1 / r for _, _, r in ranks if r) / n
        per = "".join(f"{'%d/%d' % hits(ranks, 10, s):>10}" for s in sets)
        print(f"{name[:37]:<38}{h10:>4}/{n:<3} {hits(ranks, 5)[0]:>5} {hits(ranks, 20)[0]:>5} {mrr:>5.2f}  {per}  {secs:5.1f}s")
    print(f"\n(clean held-out for these experiments: {clean}; '@5/@20' = questions fully covered in the top 5 / 20)")

    if show and len(results) > 1:
        names_ = list(results)
        print("\nquestions where configurations disagree (cover rank, '-' = beyond 60):")
        for j, (s, q, _) in enumerate(results[names_[0]][0]):
            row = [results[n][0][j][2] for n in names_]
            if len({(r is not None and r <= 10) for r in row}) > 1:
                print(f"  {s:<10} " + " ".join(f"{(str(r) if r else '-'):>3}" for r in row) + f"  {q[:70]}")
        print("  columns: " + " | ".join(names_))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--domain", default="rti", choices=list(domains.DOMAINS))
    parser.add_argument("--exp", nargs="+", default=["baseline"])
    parser.add_argument("--final", action="store_true", help="include the 'final' sets (baseline and chosen config only)")
    parser.add_argument("--show", action="store_true", help="list questions where configurations disagree")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.list:
        for n, cfgs in EXPERIMENTS.items():
            print(f"{n}: {', '.join(cfgs)}")
        return 0
    run(args.domain, args.exp, args.final, args.show)
    return 0


if __name__ == "__main__":
    sys.exit(main())
