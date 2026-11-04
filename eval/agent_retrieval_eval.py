"""
Does the agent's search find what rag/retrieve.py finds? Must match retrieval_eval.py.

Same questions and the same saved LLM outputs, through vetra/text_index.py, so it needs
no API key. The planner writes these search aids live; here they come from eval/cache/.

Run:  python eval/agent_retrieval_eval.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "rag")]
os.environ.setdefault("HYDE_CACHE", str(ROOT / "eval" / "cache" / "hyde.json"))
os.environ.setdefault("LLM_CACHE_DIR", str(ROOT / "eval" / "cache"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import domains  # noqa: E402
import query_expansion as QX  # noqa: E402
import retrieve as R  # noqa: E402

from vetra import text_index  # noqa: E402


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def main() -> int:
    data = json.loads((ROOT / "eval" / "agri_questions.json").read_text(encoding="utf-8"))
    hit = total = 0
    for name, items in data.items():
        if not isinstance(items, list):
            continue
        for item in items:
            question = domains.expand_abbreviations(item["q"], domains.get("agriculture"))
            passage = R.hypothetical_passage(question, "agriculture") or ""
            aids = QX.rewrites(question, "agriculture") or {}
            hits = text_index.search(item["q"], "agriculture", "AP", passage, aids.get("topic") or "",
                                     tuple(aids.get("keywords") or ()))
            context = squash(" ".join(h["text"] for h in hits if not h.get("added_because")))
            ok = all(squash(p) in context for p in item["probes"])
            hit += ok
            total += 1
            if not ok:
                print(f"  MISS {item['q'][:70]}")
    print(f"\nagent search, agriculture: {hit}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
