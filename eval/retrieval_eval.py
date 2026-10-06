"""
Does the answering text reach the LLM? Measured through the real rag/retrieve.py.

For every question in the domain's question file, run retrieval and check whether
each probe phrase (a verbatim bit of the text that answers it) appears in the
top-k chunks. No LLM judges anything -- the only LLM call is HyDE's search
passage, and --no-hyde removes that too.

Probes are matched with all whitespace removed, so extraction artifacts in the
PDFs ("rup ees", "Informati on") can't cause false misses.

By default the LLM outputs (HyDE passages, query rewrites) come from eval/cache/, the
same text every earlier result was measured on, so a run makes no API calls and
reproduces the published numbers; --live asks the models afresh (gpt-oss drifts
even at temperature 0, and a rate-limited call silently drops that signal).

Run:  python eval/retrieval_eval.py              # RTI: every question set
      python eval/retrieval_eval.py --no-hyde
      python eval/retrieval_eval.py --set heldout2 --verbose
      python eval/retrieval_eval.py --domain agriculture --set dev
      python eval/retrieval_eval.py --live         # fresh LLM calls instead of the cache
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rag"))
# Read when rag/retrieve.py and rag/query_expansion.py load, so set before importing them.
if "--live" not in sys.argv:
    os.environ.setdefault("HYDE_CACHE", str(ROOT / "eval" / "cache" / "hyde.json"))
    os.environ.setdefault("LLM_CACHE_DIR", str(ROOT / "eval" / "cache"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import domains  # noqa: E402
from retrieve import TOP_K, retrieve  # noqa: E402

QUESTIONS = {
    "rti": ROOT / "eval" / "demo_questions.json",
    "agriculture": ROOT / "eval" / "agri_questions.json",
}


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", default="rti", choices=list(domains.DOMAINS))
    parser.add_argument("--set", action="append", help="question set(s) to run; default: all")
    parser.add_argument("--k", type=int, default=TOP_K)
    parser.add_argument("--no-hyde", action="store_true")
    parser.add_argument("--live", action="store_true",
                        help="call the LLMs afresh instead of using eval/cache/ (read at import time)")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--ranks", action="store_true",
                        help="for misses, show where each probe first appears in the top 60")
    args = parser.parse_args()

    data = json.loads(QUESTIONS[args.domain].read_text(encoding="utf-8"))
    available = [k for k, v in data.items() if isinstance(v, list)]
    sets = args.set or available
    unknown = set(sets) - set(available)
    if unknown:
        parser.error(f"unknown set(s) {sorted(unknown)}; {args.domain} has {available}")
    mode = "hybrid only" if args.no_hyde else "hybrid + HyDE"
    print(f"retrieval eval  |  {args.domain}  |  top-{args.k}  |  {mode}\n")

    total_hit = total_n = 0
    for name in sets:
        hit = 0
        misses = []
        for item in data[name]:
            hits = retrieve(item["q"], max(args.k, 60) if args.ranks else args.k,
                            hyde=not args.no_hyde, domain=args.domain)
            # Only the ranked top-k. Amendment chunks appended afterwards also reach
            # the LLM, but excluding them keeps this comparable with earlier runs.
            ranked = [h for h in hits if not h.get("added_because")]
            context = squash(" ".join(h["text"] for h in ranked[: args.k]))
            ok = all(squash(p) in context for p in item["probes"])
            hit += ok
            if args.verbose or not ok:
                where = ""
                if args.ranks and not ok:
                    first = [next((r + 1 for r, h in enumerate(ranked) if squash(p) in squash(h["text"])), None)
                             for p in item["probes"]]
                    where = f"  [probe first at rank {', '.join(str(f) if f else '>60' for f in first)}]"
                misses.append(("OK  " if ok else "MISS", item["q"], where))
        n = len(data[name])
        total_hit += hit
        total_n += n
        print(f"  {name:<9} {hit:>2}/{n}  {hit / n:>4.0%}")
        for mark, q, where in misses:
            print(f"      {mark} {q[:72]}{where}")

    print(f"\n  {'all':<9} {total_hit:>2}/{total_n}  {total_hit / total_n:>4.0%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
