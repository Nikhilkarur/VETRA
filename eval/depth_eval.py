"""
Does a deep answer's search reach every part of the question?

Each question in deep_questions.json is split into parts, and each part says what a passage must
contain to answer it. This runs the agent's real first look on those parts and counts how many
are reached in the evidence the answer model would be given. It needs no API key: the split that
the planner would write is in the file.

--planner measures the other half: does the planner choose the right level? That needs the model.
Its replies are saved in eval/cache/, so a re-run costs nothing, and --live asks again.

Run:  python eval/depth_eval.py
      python eval/depth_eval.py --show
      python eval/depth_eval.py --planner --live
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from vetra import agent, checks, depth as depths, llm  # noqa: E402
from vetra.knowledge import Knowledge  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TODAY = "2026-11-04"
LABELS = ROOT / "eval" / "depth_labels.json"
CACHE = ROOT / "eval" / "cache" / "depth_plans.json"


def evidence(q: dict, level: depths.Depth, knowledge: Knowledge) -> list:
    """What the answer model would be given on the first look at this level."""
    plan = agent.Plan(domain=q["domain"], state=q["state"], standalone=q["q"], passage=q["passage"], topic=q["topic"],
                      keywords=tuple(q["keywords"]), needs=[agent.Need(p["type"], p["subject"], q["domain"]) for p in q["parts"]])
    found, _, _ = agent.gather(plan, agent.needs_for(plan, level, q["q"]), level, TODAY, knowledge, q["q"])
    kept = agent.share(found, level.evidence - level.moves * 2)
    return checks.order(checks.in_force(kept, TODAY, q["q"]))


def reached(part: dict, items: list) -> bool:
    return any((not part.get("doc") or re.search(part["doc"], e.doc, re.I))
               and any(re.search(a, e.text, re.I) for a in part["any"]) for e in items)


def search(show: bool) -> int:
    questions = json.loads((ROOT / "eval" / "deep_questions.json").read_text(encoding="utf-8"))["questions"]
    knowledge = Knowledge()
    total = sum(len(q["parts"]) for q in questions)
    for level in (depths.STANDARD, depths.DEEP):
        hit, sizes, started, missed = 0, [], time.perf_counter(), []
        for q in questions:
            items = evidence(q, level, knowledge)
            sizes.append(len(items))
            for part in q["parts"]:
                if reached(part, items):
                    hit += 1
                else:
                    missed.append(f"{q['id']}: {part['subject']}")
        seconds = (time.perf_counter() - started) / len(questions)
        print(f"{level.name:<9} {hit}/{total} parts reached, {sum(sizes) / len(sizes):.0f} passages on average, {seconds:.1f}s a question")
        if show:
            for m in missed:
                print(f"    MISS {m}")
    return 0


def planner(live: bool, wait: float) -> int:
    items = json.loads(LABELS.read_text(encoding="utf-8"))["questions"]
    cache = {} if live or not CACHE.exists() else json.loads(CACHE.read_text(encoding="utf-8"))
    models, right, wrong, failed = None, 0, [], 0
    for item in items:
        q = item["q"]
        if q not in cache:
            models = models or llm.from_env()
            sent = [{"role": "system", "content": agent.planner_prompt(TODAY)}, {"role": "user", "content": f"Latest message: {q}"}]
            try:
                cache[q] = models.call("plan", sent, llm.Meter(), json_mode=True).text
            except llm.LLMError as exc:
                print(f"  FAILED CALL {q[:50]}: {exc}")
                failed += 1
                continue
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
            time.sleep(wait)
        plan = agent.parse_plan(cache[q])
        got = depths.choose(plan.depth, [n.data_type for n in plan.needs]).name if plan else "no plan"
        if got == item["depth"]:
            right += 1
        else:
            wrong.append(f"  wanted {item['depth']:<9} got {got:<9} {q[:70]}")
    print("\n".join(wrong))
    print(f"\nplanner chose the right level: {right}/{len(items) - failed}" + (f", {failed} calls failed" if failed else ""))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--show", action="store_true", help="list the parts not reached")
    parser.add_argument("--planner", action="store_true", help="measure the planner's choice of level instead")
    parser.add_argument("--live", action="store_true", help="ask the model again")
    parser.add_argument("--wait", type=float, default=4, help="seconds between live calls")
    args = parser.parse_args()
    return planner(args.live, args.wait) if args.planner else search(args.show)


if __name__ == "__main__":
    sys.exit(main())
