"""
The text store: hybrid search over one index per topic, filtered by where each chunk applies.

A farmer in Karnataka searches Karnataka's chunks plus the central government's. Adding a
state adds chunks; nothing here changes. Search makes no LLM call: the planner's one call
already wrote the search passage, topic and key terms.

Chunks come from the files a domain lists, plus knowledge/<domain>/text/<STATE>.json from
intake.py. Build or update the index with:

    python -m vetra.text_index build agriculture
"""

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .domains import DOMAINS
from .jurisdictions import CENTRAL

ROOT = Path(__file__).resolve().parent.parent
RAG = str(ROOT / "rag")
CHROMA_DIR = Path(os.environ.get("VETRA_INDEX") or ROOT / "data" / "chroma")
MAX_AMENDMENTS = 4  # keeps the prompt within small models' limits
# Words in Latin letters or in an Indian or Perso-Arabic script, whole, with their vowel signs.
# The two Devanagari danda marks end a sentence, so they aren't part of a word.
_WORD = re.compile(r"[a-z0-9]+|[\u0600-\u06ff\u0900-\u0963\u0750-\u077f\u0966-\u0dff\u1c50-\u1c7f\uaae0-\uaaff\uabc0-\uabff]+")
# The same word can be typed differently: joiners that don't change it, and any script's digits.
_SAME_WORD = {0x200c: None, 0x200d: None, 0xad: None}
_SAME_WORD.update({0xd7a: "\u0d23\u0d4d", 0xd7b: "\u0d28\u0d4d", 0xd7c: "\u0d30\u0d4d", 0xd7d: "\u0d32\u0d4d",  # Malayalam chillu letters
                   0xd7e: "\u0d33\u0d4d", 0xd7f: "\u0d15\u0d4d"})
_SAME_WORD.update({ord(c): str(unicodedata.digit(c)) for start in (0x660, 0x6f0, *range(0x966, 0xd67, 0x80), 0x1c50, 0xabf0)
                   for c in map(chr, range(start, start + 10)) if unicodedata.category(c) == "Nd"})


@dataclass(frozen=True)
class Embedding:
    name: str
    tag: str = ""             # kept apart in the index, so changing models can't mix their vectors
    query_prefix: str = ""    # some models were trained to expect these
    passage_prefix: str = ""


EMBEDDINGS = {e.name: e for e in (
    Embedding("BAAI/bge-small-en-v1.5", query_prefix="Represent this sentence for searching relevant passages: "),
    Embedding("BAAI/bge-m3", tag="bge-m3"),
    Embedding("intfloat/multilingual-e5-base", tag="e5-base", query_prefix="query: ", passage_prefix="passage: "),
    Embedding("intfloat/multilingual-e5-large", tag="e5-large", query_prefix="query: ", passage_prefix="passage: "),
)}
EMBEDDING = EMBEDDINGS[os.environ.get("VETRA_EMBEDDING") or "intfloat/multilingual-e5-base"]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _rag():
    """rag/'s search parts (BM25, fusion, models): shared, so they're measured once."""
    if RAG not in sys.path:
        sys.path.insert(0, RAG)
    import retrieve

    return retrieve


def _applies_in(item: dict, default_state: str) -> str:
    return item.get("jurisdiction") or (CENTRAL if item.get("department") == "central" else default_state)


@lru_cache(maxsize=None)
def corpus(domain: str) -> tuple[dict, ...]:
    """Every chunk of a domain, each knowing where it applies. Repeats are dropped by id."""
    seen: dict[str, dict] = {}
    files = [(ROOT / path, state) for path, state in DOMAINS[domain].text_files]
    files += [(p, p.stem) for p in sorted((ROOT / "knowledge" / domain / "text").glob("*.json"))]
    for path, state in files:
        for item in json.loads(path.read_text(encoding="utf-8"))["items"]:
            seen.setdefault(item["id"], {**item, "jurisdiction": _applies_in(item, state)})
    return tuple(seen.values())


def chunks_in(domain: str, place: str) -> int:
    """How many chunks are specific to this place."""
    return sum(1 for i in corpus(domain) if i["jurisdiction"] == place)


@lru_cache(maxsize=None)
def _client():
    import chromadb

    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def _collection(domain: str):
    name = f"vetra_{domain}_{EMBEDDING.tag}" if EMBEDDING.tag else f"vetra_{domain}"
    return _client().get_or_create_collection(name, metadata={"hnsw:space": "cosine"})


def build(domain: str) -> int:
    """Embed chunks not yet in the index, and remove chunks no longer in the files."""
    items = corpus(domain)
    if not items:
        print(f"{domain}: no chunks yet")
        return 0
    collection = _collection(domain)
    have = set(collection.get(include=[])["ids"])
    wanted = {i["id"] for i in items}
    stale = list(have - wanted)
    for start in range(0, len(stale), 512):
        collection.delete(ids=stale[start:start + 512])
    new = [i for i in items if i["id"] not in have]
    if new:
        titled = DOMAINS[domain].embed_title
        vectors = _rag()._load_model(EMBEDDING.name).encode(
            [EMBEDDING.passage_prefix + (f"{i['title']}\n{i['text']}" if titled else i["text"]) for i in new],
            batch_size=16, normalize_embeddings=True, show_progress_bar=True).tolist()
        for start in range(0, len(new), 256):
            part = new[start:start + 256]
            collection.add(ids=[i["id"] for i in part], documents=[i["text"] for i in part],
                           embeddings=vectors[start:start + 256],
                           metadatas=[{"jurisdiction": i["jurisdiction"]} for i in part])
    print(f"{domain}: {collection.count()} chunks indexed ({len(new)} new, {len(stale)} removed)")
    return len(new)


def words(text: str) -> list[str]:
    """What keyword search matches on. Without the Indian scripts, a Hindi document has no keywords."""
    return _WORD.findall(unicodedata.normalize("NFKC", text).translate(_SAME_WORD).lower())


def _places(state: str | None) -> tuple[str, ...]:
    return (state, CENTRAL) if state and state != CENTRAL else (CENTRAL,)


BM25_TITLE = True   # keyword search also reads each passage's document title, as meaning search does: on the 46-question
                    # set (16 Nov) the right document reached the top 6 for 38 questions instead of 37, at no cost


@lru_cache(maxsize=None)
def _view(domain: str, places: tuple[str, ...]):
    """The chunks searchable from these places, their keyword index, and id positions."""
    items = [i for i in corpus(domain) if i["jurisdiction"] in places]
    texts = [i.get("title", "") + "\n" + i["text"] if BM25_TITLE else i["text"] for i in items]
    bm25 = _rag()._BM25(texts, tokenize=words) if items else None
    return items, bm25, {item["id"]: n for n, item in enumerate(items)}


DENSE_DEPTH = 300   # how far down the meaning ranking is read; fusion gives a passage below this almost no weight


def _dense_many(texts: list[str], domain: str, places: tuple[str, ...], position: dict) -> list[list[int]]:
    """Meaning rankings for several texts at once: one encode and one index query, not one each.
    Reading the top 300 instead of every passage made each query about ten times faster (measured 16 Nov)."""
    vectors = _rag()._load_model(EMBEDDING.name).encode([EMBEDDING.query_prefix + t for t in texts],
                                                        normalize_embeddings=True).tolist()
    where = {"jurisdiction": {"$in": list(places)}} if len(places) > 1 else {"jurisdiction": places[0]}
    # The index can be mid-rebuild when new documents are added while the server runs (seen on 18 Nov:
    # "Error finding id"). Try once more on a fresh connection; failing that, keyword search answers alone.
    for attempt in range(2):
        try:
            found = _collection(domain).query(query_embeddings=vectors, n_results=min(DENSE_DEPTH, len(position)),
                                              where=where, include=[])
            return [[position[i] for i in ids if i in position] for ids in found["ids"]]
        except Exception as exc:   # chromadb raises its own error types
            print(f"  meaning search failed ({type(exc).__name__}); {'retrying' if not attempt else 'keywords only'}",
                  file=sys.stderr, flush=True)
            _client.cache_clear()
    return [[] for _ in texts]


def _dense(text: str, domain: str, places: tuple[str, ...], position: dict) -> list[int]:
    return _dense_many([text], domain, places, position)[0]


def distinct(ranking: list[int], items: list[dict]) -> list[int]:
    """The ranking with repeated passages dropped, the best-ranked copy kept. One document held from two
    official sites (a policy note on the department's site and on the state portal) gives the same passage
    twice; both copies would fill places in the top k that other evidence should have."""
    seen, kept = set(), []
    for n in ranking:
        key = " ".join(items[n]["text"].split()).lower()
        if key not in seen:
            seen.add(key)
            kept.append(n)
    return kept


def _with_amendments(chosen: list[int], ranking: list[int], items: list[dict]) -> list[tuple[int, str]]:
    """A rule without its amendments is wrong: add the orders linked to what was found."""
    wanted: dict[str, str] = {}
    for n in chosen:
        order = items[n].get("order")
        for amended in filter(None, (items[n].get("amends") or "").split(",")):
            wanted.setdefault(amended, f"is the order amended by {items[n].get('order_label') or order}")
        if order:
            for other in items:
                if order in (other.get("amends") or "").split(","):
                    wanted.setdefault(other["order"], f"amends {items[n].get('order_label') or order}")
    rank = {doc: r for r, doc in enumerate(ranking)}
    have = set(chosen)
    extra = [(n, wanted[item["order"]]) for n, item in enumerate(items)
             if item.get("order") in wanted and n not in have and item.get("in_force") != "no"]
    extra.sort(key=lambda pair: rank.get(pair[0], len(ranking)))
    return extra[:MAX_AMENDMENTS]


SUBASPECT_VOTE = False   # also search on the citizen case (knowledge/subaspects.json) closest to the question
SUBASPECT_MIN = 0.80     # how close, in meaning, a case must be to count


@lru_cache(maxsize=None)
def _cases(domain: str) -> tuple[list[str], object]:
    """Every "aspect: case" of a domain, and their meaning vectors."""
    path = ROOT / "knowledge" / "subaspects.json"
    if not path.exists():
        return [], None
    cases = [f"{aspect}: {case}" for aspect, names in json.loads(path.read_text(encoding="utf-8")).get(domain, {}).items()
             for case in names]
    if not cases:
        return [], None
    vectors = _rag()._load_model(EMBEDDING.name).encode([EMBEDDING.passage_prefix + c for c in cases], normalize_embeddings=True)
    return cases, vectors


def case_for(query: str, domain: str) -> str:
    """The citizen case this question is closest to, or "" if none is close enough."""
    cases, vectors = _cases(domain)
    if not cases:
        return ""
    q = _rag()._load_model(EMBEDDING.name).encode([EMBEDDING.query_prefix + query], normalize_embeddings=True)[0]
    scores = vectors @ q
    best = int(scores.argmax())
    return cases[best] if scores[best] >= SUBASPECT_MIN else ""


def search(query: str, domain: str, state: str | None, passage: str = "", topic: str = "",
           keywords: tuple[str, ...] = (), k: int = 10, rerank: bool = True) -> list[dict]:
    """The best chunks for a question in this state, best first, then any amending orders."""
    R = _rag()
    places = _places(state)
    items, bm25, position = _view(domain, places)
    if not items:
        return []
    settings = DOMAINS[domain]
    if settings.abbreviations_from:
        import domains as legacy

        query = legacy.expand_abbreviations(query, legacy.get(settings.abbreviations_from))

    case = case_for(query, domain) if SUBASPECT_VOTE else ""
    texts = [t for t in (query, passage, topic, case) if t]
    votes = [R._rrf(dense, bm25.rank(text)) for text, dense in zip(texts, _dense_many(texts, domain, places, position))]
    if keywords:
        votes.append(bm25.rank(" ".join(keywords)))
    ranking = distinct(R._rrf(*votes), items)
    if settings.rerank and rerank and RERANK_DEPTH:
        ranking = _reranked(query, ranking, items, settings.rerank)
    chosen = R._top_k(ranking, items, k)
    found = [dict(items[n]) for n in chosen]
    found += [{**items[n], "added_because": why} for n, why in _with_amendments(chosen, ranking, items)]
    return found


def around(chunk_id: str, domain: str, reach: int = 1) -> list[dict]:
    """The passages just before and after this one in its document, for a state that can see it."""
    items = corpus(domain)
    this = next((i for i in items if i["id"] == chunk_id), None)
    if this is None:
        return []
    near = range(this["chunk_index"] - reach, this["chunk_index"] + reach + 1)
    return [i for i in items if i["id"] != chunk_id and i.get("source") == this.get("source") and i["chunk_index"] in near]


def search_within(query: str, domain: str, state: str | None, document: str, k: int = 3) -> list[dict]:
    """The best passages inside one document, ranked the same way as any search."""
    R = _rag()
    places = _places(state)
    items, bm25, position = _view(domain, places)
    if not items:
        return []
    ranking = R._rrf(_dense(query, domain, places, position), bm25.rank(query))
    inside = [n for n in ranking if items[n].get("source") == document]
    return [dict(items[n]) for n in distinct(inside, items)][:k]


# How many fused results the cross-encoder reads; 0 turns it off. Measured on 16 Nov (tools/retrieval_eval.py,
# 46 citizen questions with a known source document): reranking found the right document in the top 6 for
# 33-34 questions, against 37 without it, and took 3-5 s a search against 1.6 s. The reranker is an
# English web-search model; these are formal Indian orders and casual or romanised questions. Off.
RERANK_DEPTH = 0


def _reranked(query: str, ranking: list[int], items: list[dict], model: str, n: int | None = None) -> list[int]:
    """A cross-encoder over the top n, fused with the search order rather than replacing it."""
    n = n or RERANK_DEPTH or 30
    R = _rag()
    top = ranking[:n]
    scores = R._cross_encoder(model).predict(
        [(query, f"{items[i].get('title', '')}\n{items[i]['text']}") for i in top], batch_size=16)
    order = [top[j] for j in sorted(range(len(top)), key=lambda j: -scores[j])]
    return R._rrf(top, order) + ranking[n:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["build"])
    parser.add_argument("domain", choices=[d.name for d in DOMAINS.values() if not d.legacy])
    args = parser.parse_args()
    build(args.domain)
    return 0


if __name__ == "__main__":
    sys.exit(main())
