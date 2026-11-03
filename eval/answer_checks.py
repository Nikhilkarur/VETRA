"""
Does a known wrong ANSWER stay fixed? retrieval_eval.py only checks passages.

Crop insurance: the State paid the farmer's premium in Kharif 2024 only (G.O.Ms.80,
81), and later seasons are voluntary enrolment with a farmer's share (extended to
2026-27 by G.O.Ms.34, 35). Answers kept giving the 2024 rule as today's.

Two checks:
- offline (always, no API calls): that rule never reaches the answer model for a
  question about today, and does for a question naming 2024;
- --live N: ask the real pipeline N times. The model varies from run to run, so one
  good answer proves little. A run fails if a line says the State pays the farmer's
  premium or cover is free without naming Kharif 2024, or calls Kharif 2024 current. That is a
  pattern check for this one error, not a measure of answer quality: --show prints the
  answers, so read them.

Run:  python eval/answer_checks.py
      python eval/answer_checks.py --live 5 --show
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rag"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from answer import answer_question, build_context  # noqa: E402

QUESTION = "do i have to pay for crop insurance now"
RULE = "will bear both the Farmer"
KHARIF_2024 = re.compile(r"kharif.2024", re.I)

# Narrow on purpose: "you do not need to pay separately" (the bank debits a loanee's
# premium) and "if you do not pay, you are not covered" are not this error.
NOT_PAYING = re.compile(
    r"(\bstate\b[^.\n]{0,60}\b(bears?|pays?|covers?)\b[^.\n]{0,40}\b(farmer|premium)"
    r"|\bpaid by the state"
    r"|free of (cost|charge)|is free\b)",
    re.I,
)
CURRENT = re.compile(r"(kharif.2024[^.\n]{0,40}\bcurrent\b|\bcurrent\b[^.\n]{0,40}kharif.2024)", re.I)


def offline() -> bool:
    items = json.loads((ROOT / "ingest" / "chunks_agriculture.json").read_text(encoding="utf-8"))["items"]
    holding = [i for i in items if i["order"] in ("Ms.80/2024", "Ms.81/2024") and RULE in i["text"]]
    leaked = [i for i in holding if RULE in build_context([i], QUESTION)]
    for i in leaked:
        print(f"  FAIL {i['order']} chunk {i['chunk_index']}: the 2024 rule reaches the model")
    kept = all(RULE in build_context([i], "was it free in kharif 2024") for i in holding)
    if not kept:
        print("  FAIL a question naming 2024 no longer sees the 2024 rule")
    ok = bool(holding) and not leaked and kept
    print(f"offline: {'ok' if ok else 'FAILED'} ({len(holding)} chunks hold the rule)")
    return ok


def wrong_lines(answer: str) -> list[str]:
    return [line.strip() for line in answer.splitlines()
            if CURRENT.search(line) or (NOT_PAYING.search(line) and not KHARIF_2024.search(line))]


def live(runs: int, wait: float, show: bool) -> bool:
    failed = 0
    for n in range(1, runs + 1):
        if n > 1:
            time.sleep(wait)  # Groq's free tier: about one answer per 30 seconds
        result = answer_question(QUESTION, domain="agriculture")
        wrong = wrong_lines(result["answer"])
        failed += bool(wrong)
        print(f"  run {n}: {'FAIL' if wrong else 'ok'}  ({result['model']})")
        for line in wrong:
            print(f"      {line[:200]}")
        if show:
            print(result["answer"] + "\n")
    print(f"live: {runs - failed}/{runs} passed")
    return not failed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", type=int, default=0, metavar="N", help="also ask the real pipeline N times")
    parser.add_argument("--wait", type=float, default=30, help="seconds between live runs")
    parser.add_argument("--show", action="store_true", help="print each live answer")
    args = parser.parse_args()

    ok = offline()
    if args.live:
        ok = live(args.live, args.wait, args.show) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
