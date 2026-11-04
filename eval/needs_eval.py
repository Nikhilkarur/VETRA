"""
Does the planner work out what data each question needs?

Checks the topic, the state, the language, and that every needed data type is in the plan.
Extra types aren't counted as wrong: they cost a lookup, not an error. Plans are saved in
eval/cache/, so a re-run costs nothing; --live asks the model again.

Run:  python eval/needs_eval.py
      python eval/needs_eval.py --live
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from vetra import agent, llm  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CACHE = ROOT / "eval" / "cache" / "plans.json"
TODAY = "2026-11-04"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--wait", type=float, default=4, help="seconds between live calls")
    args = parser.parse_args()

    items = json.loads((ROOT / "eval" / "needs_questions.json").read_text(encoding="utf-8"))["questions"]
    cache = {} if args.live or not CACHE.exists() else json.loads(CACHE.read_text(encoding="utf-8"))
    models = None
    score = {"domain": 0, "state": 0, "language": 0, "needs": 0}
    failed = 0
    for item in items:
        q = item["q"]
        if q not in cache:
            models = models or llm.from_env()
            messages = [{"role": "system", "content": agent.planner_prompt(TODAY)}, {"role": "user", "content": f"Latest message: {q}"}]
            try:
                cache[q] = models.call("plan", messages, llm.Meter(), json_mode=True).text
            except llm.LLMError as exc:
                print(f"  FAILED CALL {q[:50]}: {exc}")
                failed += 1
                continue
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
            time.sleep(args.wait)
        plan = agent.parse_plan(cache[q])
        if plan is None:
            print(f"  UNUSABLE PLAN {q[:60]}")
            continue
        got = [n.data_type for n in plan.needs]
        checks = {"domain": plan.domain == item["domain"], "state": plan.state == item.get("state"),
                  "language": plan.language == item.get("language", "english"),
                  "needs": set(item["needs"]) <= set(got)}
        for key, ok in checks.items():
            score[key] += ok
        wrong = [k for k, ok in checks.items() if not ok]
        if wrong:
            print(f"  {','.join(wrong):<18} {q[:62]}\n      wanted {item['domain']}/{item.get('state')}/{item['needs']}  got {plan.domain}/{plan.state}/{got}")
    n = len(items)
    print(f"\n{n} questions" + (f", {failed} calls failed" if failed else ""))
    for key, value in score.items():
        print(f"  {key:<10} {value}/{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
