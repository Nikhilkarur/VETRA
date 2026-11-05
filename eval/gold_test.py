"""
The hand-read test: does a change really make answers better?

Scored by a person, not by matching text, because matching hid real bugs. Each answer is marked:

    right            says the expected fact, and nothing false that matters
    wrong            says something false, or misleads
    right_refusal    says it isn't held, and it isn't
    needless_refusal says it isn't held, but it is

Run:  python eval/gold_test.py --check            every expected answer has its quote in a document?
      python eval/gold_test.py --run NAME         ask everything; re-running only asks what's missing
      python eval/gold_test.py --sheet NAME       write a sheet to fill in by hand
      python eval/gold_test.py --score NAME       totals by group and language
      python eval/gold_test.py --compare OLD NEW  are the two runs really different?

Runs and sheets are in eval/cache/gold/. A sheet is a CSV: fill in the "mark" column.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

QUESTIONS = ROOT / "eval" / "gold_questions.json"
RUNS = ROOT / "eval" / "cache" / "gold"
TODAY = "2026-11-05"
MARKS = ("right", "wrong", "right_refusal", "needless_refusal")
GOOD = {"right", "right_refusal"}


class NoLog:
    def report(self, gap) -> None:
        pass


def questions() -> list[dict]:
    return json.loads(QUESTIONS.read_text(encoding="utf-8"))["questions"]


def _plain(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def check() -> int:
    """Every quote must be in a chunk the question's state can see, so an answer can't rest on my memory."""
    from vetra import text_index

    chunks = {d: [(i["jurisdiction"], _plain(i["text"])) for i in text_index.corpus(d)] for d in ("agriculture", "finance")}
    items, missing = questions(), []
    for item in items:
        if item.get("quote") and not any(_plain(item["quote"]) in text and j in (item["state"], "IN") or (_plain(item["quote"]) in text and item["state"] is None)
                                         for rows in chunks.values() for j, text in rows):
            missing.append(item)
    for item in missing:
        print(f"  NOT FOUND {item['id']}: {item['quote'][:80]}")
    print(f"{len(items)} questions, {sum(1 for i in items if i.get('quote'))} with quotes, {len(missing)} quotes not found")
    print(dict(Counter(i["group"] for i in items)))
    print(dict(Counter(i["language"] for i in items)))
    print(dict(Counter(i["state"] or "central" for i in items)))
    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids)), "repeated ids"
    return 1 if missing else 0


def run(name: str, wait: float) -> int:
    from vetra import agent, llm

    path = RUNS / f"{name}.json"
    RUNS.mkdir(parents=True, exist_ok=True)
    saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    models, failures = llm.from_env(), 0
    for item in questions():
        if item["id"] in saved:
            continue
        try:
            r = agent.answer(item["q"], state=item["state"], models=models, as_of=TODAY, gaps=NoLog())
            if r.kind == "failed" or r.trace.get("error"):
                raise llm.LLMError(f"{r.kind}: {r.trace.get('error')}")
            saved[item["id"]] = {"answer": r.answer, "kind": r.kind, "depth": r.depth, "tokens": r.trace.get("tokens"),
                                 "calls": r.trace.get("calls"), "seconds": r.trace.get("seconds"),
                                 "models": [s.get("model") for s in r.trace.get("steps", [])],
                                 "problems": r.trace.get("final_problems"), "sources": [{"n": s.get("n"), "doc": s["doc"], "url": s.get("url")} for s in r.sources]}
            path.write_text(json.dumps(saved, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  {len(saved):>3} {item['id']:<28} {r.kind} {r.trace.get('seconds')}s", flush=True)
        except Exception as exc:
            failures += 1
            print(f"  FAILED {item['id']}: {str(exc)[:120]}", flush=True)
        time.sleep(wait)
    print(f"{len(saved)} of {len(questions())} answered, {failures} failed. Run again to retry them.")
    return 0


def sheet(name: str) -> int:
    saved = json.loads((RUNS / f"{name}.json").read_text(encoding="utf-8"))
    path = RUNS / f"{name}.csv"
    marks = _marks(name) if path.exists() else {}
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        out = csv.writer(f)
        out.writerow(["id", "group", "language", "question", "expected", "answer", "documents", "mark", "note"])
        for item in questions():
            got = saved.get(item["id"])
            if got:
                documents = "\n".join(f"[E{d['n']}] {d['doc']} {d.get('url') or ''}".strip() for d in got["sources"])
                out.writerow([item["id"], item["group"], item["language"], item["q"], item["expected"], got["answer"], documents, marks.get(item["id"], ""), ""])
    print(f"Marks allowed: {', '.join(MARKS)}\n{path}")
    return 0


def _marks(name: str) -> dict[str, str]:
    with (RUNS / f"{name}.csv").open(encoding="utf-8-sig", newline="") as f:
        return {row["id"]: row["mark"].strip() for row in csv.DictReader(f) if row["mark"].strip()}


def _wilson(good: int, total: int) -> tuple[int, int]:
    if not total:
        return 0, 0
    z, p = 1.96, good / total
    middle, half = p + z * z / (2 * total), z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    bottom = 1 + z * z / total
    return round(100 * (middle - half) / bottom), round(100 * (middle + half) / bottom)


def score(name: str) -> int:
    marks, items = _marks(name), questions()
    bad = {i: m for i, m in marks.items() if m not in MARKS}
    if bad:
        print(f"Unknown marks: {bad}")
        return 1
    for field in ("group", "language"):
        print(f"\n{field:<22}{'marked':>7}{'right':>7}{'wrong':>7}{'right refusal':>15}{'needless':>10}   good, with its range")
        for value in sorted({i[field] for i in items}):
            chosen = [marks[i["id"]] for i in items if i[field] == value and i["id"] in marks]
            count, good = Counter(chosen), sum(m in GOOD for m in chosen)
            low, high = _wilson(good, len(chosen))
            print(f"{value:<22}{len(chosen):>7}{count['right']:>7}{count['wrong']:>7}{count['right_refusal']:>15}{count['needless_refusal']:>10}   {good}/{len(chosen)} ({low}-{high}%)")
    good = sum(m in GOOD for m in marks.values())
    low, high = _wilson(good, len(marks))
    print(f"\nAll: {good}/{len(marks)} good ({low}-{high}%), {Counter(marks.values())['wrong']} wrong, {len(items) - len(marks)} not marked")
    return 0


def _exact_paired(only_a: int, only_b: int) -> float:
    """McNemar's exact test: how often would a split this lopsided happen by chance?"""
    n = only_a + only_b
    if not n:
        return 1.0
    tail = sum(math.comb(n, k) for k in range(min(only_a, only_b) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def compare(old: str, new: str) -> int:
    a, b = _marks(old), _marks(new)
    both = sorted(set(a) & set(b))
    only_old = [i for i in both if a[i] in GOOD and b[i] not in GOOD]
    only_new = [i for i in both if b[i] in GOOD and a[i] not in GOOD]
    print(f"{len(both)} questions marked in both. Good in {old}: {sum(a[i] in GOOD for i in both)}. Good in {new}: {sum(b[i] in GOOD for i in both)}.")
    print(f"Only {old} good: {len(only_old)} {only_old}\nOnly {new} good: {len(only_new)} {only_new}")
    p = _exact_paired(len(only_old), len(only_new))
    print(f"Chance of a split like this with no real difference: {p:.3f}. " + ("Probably a real difference." if p < 0.05 else "Not enough to say they differ."))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--run")
    parser.add_argument("--sheet")
    parser.add_argument("--score")
    parser.add_argument("--compare", nargs=2)
    parser.add_argument("--wait", type=float, default=8, help="seconds between questions")
    args = parser.parse_args()
    if args.check:
        return check()
    if args.run:
        return run(args.run, args.wait)
    if args.sheet:
        return sheet(args.sheet)
    if args.score:
        return score(args.score)
    if args.compare:
        return compare(*args.compare)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
