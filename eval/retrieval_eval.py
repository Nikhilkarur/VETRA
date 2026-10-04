"""
Does the answering text reach the LLM? Measured through the real rag/retrieve.py.

For every question in eval/demo_questions.json, run retrieval and check whether
each probe phrase (a verbatim bit of the text that answers it) appears in the
top-k chunks. No LLM judges anything -- the only LLM call is HyDE's search
passage, and --no-hyde removes that too.

Probes are matched with all whitespace removed, so extraction artifacts in the
PDFs ("rup ees", "Informati on") can't cause false misses.

Run:  python eval/retrieval_eval.py              # all three question sets
      python eval/retrieval_eval.py --no-hyde
      python eval/retrieval_eval.py --set heldout2 --verbose
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rag"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from retrieve import TOP_K, retrieve  # noqa: E402

QUESTIONS = ROOT / "eval" / "demo_questions.json"


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set", choices=["dev", "heldout", "heldout2", "heldout3"], action="append")
    parser.add_argument("--k", type=int, default=TOP_K)
    parser.add_argument("--no-hyde", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    data = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    sets = args.set or ["dev", "heldout", "heldout2", "heldout3"]
    mode = "hybrid only" if args.no_hyde else "hybrid + HyDE"
    print(f"retrieval eval  |  top-{args.k}  |  {mode}\n")

    total_hit = total_n = 0
    for name in sets:
        hit = 0
        misses = []
        for item in data[name]:
            hits = retrieve(item["q"], args.k, hyde=not args.no_hyde)
            # Only the ranked top-k. Amendment chunks appended afterwards also reach
            # the LLM, but excluding them keeps this comparable with earlier runs.
            ranked = [h for h in hits if not h.get("added_because")]
            context = squash(" ".join(h["text"] for h in ranked))
            ok = all(squash(p) in context for p in item["probes"])
            hit += ok
            if args.verbose or not ok:
                misses.append(("OK  " if ok else "MISS", item["q"]))
        n = len(data[name])
        total_hit += hit
        total_n += n
        print(f"  {name:<9} {hit:>2}/{n}  {hit / n:>4.0%}")
        for mark, q in misses:
            print(f"      {mark} {q[:72]}")

    print(f"\n  {'all':<9} {total_hit:>2}/{total_n}  {total_hit / total_n:>4.0%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
