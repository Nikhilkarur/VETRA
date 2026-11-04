"""
Which embedding model should search use?

Runs one model through every search test, on an index of its own in data/chroma_eval, so the live
index is never touched. No API key is needed. The first run for a model has to index everything,
which on a CPU can take a long time for a large model.

The Marathi test needs its two documents in documents/_needs_ocr/agriculture/MH/ (see
eval/indic_questions.json), and they're added for this test only.

Run:  python eval/embedding_eval.py BAAI/bge-small-en-v1.5
      python eval/embedding_eval.py BAAI/bge-m3
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval")]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("model")
parser.add_argument("--reranker", default="", help="a cross-encoder to use instead of the domain's own, or none")
args = parser.parse_args()
os.environ["VETRA_EMBEDDING"] = args.model
os.environ.setdefault("VETRA_INDEX", str(ROOT / "data" / "chroma_eval"))   # two runs at once need separate folders
# Saved search passages, set before anything loads rag/, so scores never depend on the API's limits.
os.environ.setdefault("HYDE_CACHE", str(ROOT / "eval" / "cache" / "hyde.json"))
os.environ.setdefault("LLM_CACHE_DIR", str(ROOT / "eval" / "cache"))

from vetra import intake, text_index  # noqa: E402

LABELS = json.loads((ROOT / "eval" / "indic_questions.json").read_text(encoding="utf-8"))
FOLDER = ROOT / "documents" / "_needs_ocr" / "agriculture" / "MH"
CACHE = ROOT / "data" / "eval_marathi_chunks.json"


def marathi_chunks() -> list[dict]:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    report = intake.prepare(LABELS["documents"], FOLDER, "MH")
    assert not report.problems, report.problems
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(report.chunks, ensure_ascii=False), encoding="utf-8")
    return report.chunks


plain_corpus = text_index.corpus
extra = tuple({**c, "jurisdiction": "MH"} for c in marathi_chunks())


def corpus(domain: str) -> tuple[dict, ...]:
    return plain_corpus(domain) + (extra if domain == "agriculture" else ())


text_index.corpus = corpus

if args.reranker == "none":
    import dataclasses

    from vetra.domains import DOMAINS

    for name, domain in list(DOMAINS.items()):
        DOMAINS[name] = dataclasses.replace(domain, rerank=None)
elif args.reranker:
    import dataclasses

    from vetra.domains import DOMAINS

    for name, domain in list(DOMAINS.items()):
        if domain.rerank:
            DOMAINS[name] = dataclasses.replace(domain, rerank=args.reranker)


def hit(question: dict, passages: list[dict]) -> bool:
    return any(p["jurisdiction"] == "MH" and any(re.search(a, p["text"]) for a in question["any"]) for p in passages)


def marathi_test() -> None:
    questions = LABELS["questions"]
    runs = {
        "English question": lambda q: text_index.search(q["english"], "agriculture", "MH"),
        "Marathi question": lambda q: text_index.search(q["marathi"], "agriculture", "MH"),
        "both, as votes": lambda q: text_index.search(q["english"], "agriculture", "MH", passage=q["marathi"]),
    }
    for name, run in runs.items():
        started = time.perf_counter()
        missed = [q["english"] for q in questions if not hit(q, run(q))]
        print(f"  Marathi documents, {name}: {len(questions) - len(missed)}/{len(questions)}"
              f"  ({(time.perf_counter() - started) / len(questions):.1f}s a search)", flush=True)
        for m in missed:
            print(f"      MISS {m}", flush=True)


def main() -> int:
    print(f"\n=== {args.model}" + (f" + {args.reranker}" if args.reranker else ""), flush=True)
    started = time.perf_counter()
    for domain in ("agriculture", "finance"):
        text_index.build(domain)
    print(f"  indexed in {(time.perf_counter() - started) / 60:.1f} minutes", flush=True)
    marathi_test()

    import agent_retrieval_eval
    import depth_eval

    print("  English documents, AP question sets:", flush=True)
    agent_retrieval_eval.main()
    print("  English documents, parts of deep questions:", flush=True)
    depth_eval.search(False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
