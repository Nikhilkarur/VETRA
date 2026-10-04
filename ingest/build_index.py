"""
Embed ingest/chunks.json into a local Chroma collection.

Embedding model: BAAI/bge-small-en-v1.5 -- 384 dimensions, 512-token window, local.
Measured against all-MiniLM-L6-v2 on eval/demo_questions.json it was only slightly
better on its own; the reason it's here is the 512-token window, which our
token-sized chunks are built to fit.

The model name is written into the collection's metadata. rag/retrieve.py reads
it from there, so the query side can never silently use a different model from
the one that built the index.

The keyword (BM25) half of hybrid search needs no index file: rag/retrieve.py
builds it in memory from the stored chunk texts at startup (under a second).

Run:  python ingest/build_index.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CHUNKS = ROOT / "ingest" / "chunks.json"
CHROMA_DIR = ROOT / "data" / "chroma"
COLLECTION = "ap_rti"


def main() -> int:
    import chromadb
    from sentence_transformers import SentenceTransformer

    data = json.loads(CHUNKS.read_text(encoding="utf-8"))
    items, model_name = data["items"], data["model"]
    print(f"{len(items)} chunks, embedding with {model_name} ...")

    model = SentenceTransformer(model_name)
    too_long = sum(1 for i in items if len(model.tokenizer.encode(i["text"])) > model.max_seq_length)
    print(f"chunks over the {model.max_seq_length}-token window: {too_long}")

    # Chunks go in raw. bge is asymmetric: only QUERIES get its instruction prefix.
    vectors = model.encode(
        [i["text"] for i in items], batch_size=32, normalize_embeddings=True, show_progress_bar=True
    ).tolist()

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine", "model": model_name}
    )

    # Chroma metadata must be scalar and non-null.
    metadatas = [
        {
            "source": i["source"],
            "title": i["title"],
            "department": i["department"],
            "section": i["section"] or 0,
            "order": i["order"],
            "amends": i["amends"],
            "source_url": i["source_url"],
            "file": i["file"],
            "chunk_index": i["chunk_index"],
            "chunk_count": i["chunk_count"],
        }
        for i in items
    ]
    for start in range(0, len(items), 256):
        end = start + 256
        collection.add(
            ids=[i["id"] for i in items[start:end]],
            documents=[i["text"] for i in items[start:end]],
            embeddings=vectors[start:end],
            metadatas=metadatas[start:end],
        )

    print(f"indexed {collection.count()} vectors -> {CHROMA_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
