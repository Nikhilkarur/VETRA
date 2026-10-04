"""
Does the router send each question to the right domain?

Three sources, all labelled before the router existed:
  router_questions.json   plain / traps / other / followups (written for this test)
  ingest/incoming/questions/questions.json   71 real questions from official FAQs
                          (rti, agriculture, and PGRS grievance FAQs = "other")
  demo_questions.json + agri_questions.json  every retrieval-eval question
                          (rti and agriculture respectively)

A question is right when the router's domain is its label, or one of its
'also_ok' labels. Misroutes into "other" are counted separately: they are the
costly kind (a valid question gets no answer), where a domain-for-domain mistake
still searches some documents.

Run:  python eval/router_eval.py                  # LLM router
      python eval/router_eval.py --router embedding
      python eval/router_eval.py --only router    # just router_questions.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rag"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import router  # noqa: E402


def cases(only: str | None) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    if only in (None, "router"):
        data = json.loads((ROOT / "eval" / "router_questions.json").read_text(encoding="utf-8"))
        for name in ("plain", "traps", "other", "followups"):
            groups[name] = data[name]
    if only in (None, "faq"):
        faq = json.loads((ROOT / "ingest" / "incoming" / "questions" / "questions.json")
                         .read_text(encoding="utf-8"))
        groups["faq"] = [{"q": x["question"], "domain": "other" if x["domain"] == "general" else x["domain"]}
                         for x in faq]
    if only in (None, "eval"):
        for domain, file in (("rti", "demo_questions.json"), ("agriculture", "agri_questions.json")):
            data = json.loads((ROOT / "eval" / file).read_text(encoding="utf-8"))
            groups[f"eval_{domain[:4]}"] = [{"q": item["q"], "domain": domain}
                                           for v in data.values() if isinstance(v, list) for item in v]
    return groups


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--router", choices=["llm", "embedding"], default="llm")
    parser.add_argument("--only", choices=["router", "faq", "eval"])
    parser.add_argument("--verbose", action="store_true", help="show every question, not just misses")
    args = parser.parse_args()

    def decide(case: dict) -> str:
        if args.router == "embedding":
            history = case.get("history")
            # Same rule as router.route()'s fallback: a follow-up stays in the last domain.
            if history:
                return history[-1]["domain"]
            return router.route_embedding(case["q"])
        for attempt in range(3):
            try:
                return router.route_llm(case["q"], case.get("history"))
            except Exception as exc:  # rate limit after the SDK's own retries
                print(f"      (retrying after error: {exc})", file=sys.stderr)
                time.sleep(20)
        return "ERROR"

    print(f"router eval  |  {args.router}\n")
    total = right = to_other = 0
    confusion: Counter = Counter()
    started = time.perf_counter()
    for name, items in cases(args.only).items():
        ok_n = 0
        lines = []
        for case in items:
            got = decide(case)
            ok = got == case["domain"] or got in case.get("also_ok", [])
            ok_n += ok
            confusion[(case["domain"], got)] += 1
            if not ok and got == router.OTHER:
                to_other += 1
            if args.verbose or not ok:
                where = f"  (after: {case['history'][-1]['q'][:40]})" if case.get("history") else ""
                lines.append(f"      {'OK  ' if ok else 'MISS'} {case['domain']:>11} -> {got:<11} {case['q'][:70]}{where}")
        total += len(items)
        right += ok_n
        print(f"  {name:<10} {ok_n:>3}/{len(items):<3} {ok_n / len(items):>4.0%}")
        for line in lines:
            print(line)

    print(f"\n  {'all':<10} {right:>3}/{total:<3} {right / total:>4.0%}   "
          f"({to_other} valid questions sent to 'other'; {time.perf_counter() - started:.0f}s)")
    labels = sorted({a for a, _ in confusion} | {b for _, b in confusion})
    print("\n  confusion (rows = label, columns = routed to)")
    print("  " + " " * 12 + "".join(f"{l[:11]:>12}" for l in labels))
    for a in labels:
        print(f"  {a[:11]:<12}" + "".join(f"{confusion[(a, b)]:>12}" for b in labels))
    return 0


if __name__ == "__main__":
    sys.exit(main())
