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
import sys
from functools import lru_cache
from pathlib import Path

from .domains import DOMAINS
from .jurisdictions import CENTRAL

ROOT = Path(__file__).resolve().parent.parent
RAG = str(ROOT / "rag")
CHROMA_DIR = ROOT / "data" / "chroma"
MAX_AMENDMENTS = 4  # keeps the prompt within small models' limits

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


def _collection(domain: str):
    import chromadb

    return chromadb.PersistentClient(path=str(CHROMA_DIR)).get_or_create_collection(
        f"vetra_{domain}", metadata={"hnsw:space": "cosine"})


def build(domain: str) -> int:
    """Embed chunks not yet in the index, and remove chunks no longer in the files."""
    items = corpus(domain)
    if not items:
        print(f"{domain}: no chunks yet")
        return 0
    model_name = "BAAI/bge-small-en-v1.5"
    collection = _collection(domain)
    have = set(collection.get(include=[])["ids"])
    wanted = {i["id"] for i in items}
    stale = list(have - wanted)
    for start in range(0, len(stale), 512):
        collection.delete(ids=stale[start:start + 512])
    new = [i for i in items if i["id"] not in have]
    if new:
        titled = DOMAINS[domain].embed_title
        vectors = _rag()._load_model(model_name).encode(
            [f"{i['title']}\n{i['text']}" if titled else i["text"] for i in new],
            batch_size=32, normalize_embeddings=True, show_progress_bar=True).tolist()
        for start in range(0, len(new), 256):
            part = new[start:start + 256]
            collection.add(ids=[i["id"] for i in part], documents=[i["text"] for i in part],
                           embeddings=vectors[start:start + 256],
                           metadatas=[{"jurisdiction": i["jurisdiction"]} for i in part])
    print(f"{domain}: {collection.count()} chunks indexed ({len(new)} new, {len(stale)} removed)")
    return len(new)


def _places(state: str | None) -> tuple[str, ...]:
    return (state, CENTRAL) if state and state != CENTRAL else (CENTRAL,)


@lru_cache(maxsize=None)
def _view(domain: str, places: tuple[str, ...]):
    """The chunks searchable from these places, their keyword index, and id positions."""
    items = [i for i in corpus(domain) if i["jurisdiction"] in places]
    bm25 = _rag()._BM25([i["text"] for i in items]) if items else None
    return items, bm25, {item["id"]: n for n, item in enumerate(items)}


def _dense(text: str, domain: str, places: tuple[str, ...], position: dict) -> list[int]:
    R = _rag()
    vector = R._load_model("BAAI/bge-small-en-v1.5").encode([R.QUERY_PREFIX + text], normalize_embeddings=True).tolist()
    where = {"jurisdiction": {"$in": list(places)}} if len(places) > 1 else {"jurisdiction": places[0]}
    found = _collection(domain).query(query_embeddings=vector, n_results=len(position), where=where, include=[])
    return [position[i] for i in found["ids"][0] if i in position]


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


def search(query: str, domain: str, state: str | None, passage: str = "", topic: str = "",
           keywords: tuple[str, ...] = (), k: int = 10) -> list[dict]:
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

    def hybrid(text: str) -> list[int]:
        return R._rrf(_dense(text, domain, places, position), bm25.rank(text))

    votes = [hybrid(query)]
    if passage:
        votes.append(hybrid(passage))
    if topic:
        votes.append(hybrid(topic))
    if keywords:
        votes.append(bm25.rank(" ".join(keywords)))
    ranking = R._rrf(*votes)
    if settings.rerank:
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


def _reranked(query: str, ranking: list[int], items: list[dict], model: str, n: int = 30) -> list[int]:
    """A cross-encoder over the top n, fused with the search order rather than replacing it."""
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
