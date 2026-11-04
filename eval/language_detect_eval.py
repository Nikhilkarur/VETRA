"""
Does the planner recognise each language, and turn the question into English for searching?

"language" scores the planner alone. "after code" scores what the agent will actually use, once
code has applied what the script settles. The planner's replies are saved in eval/cache/, so a
re-run costs nothing, and questions whose calls failed are asked again.

Run:  python eval/language_detect_eval.py
      python eval/language_detect_eval.py --live
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from vetra import agent, languages, llm  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CACHE = ROOT / "eval" / "cache" / "language_plans.json"
TODAY = "2026-11-04"


def english(text: str) -> bool:
    return bool(text) and all(ord(c) < 0x2000 for c in text) and sum(c.isascii() for c in text) / len(text) > 0.9


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--live", action="store_true", help="ask the model again")
    parser.add_argument("--wait", type=float, default=3, help="seconds between live calls")
    args = parser.parse_args()

    items = json.loads((ROOT / "eval" / "language_labels.json").read_text(encoding="utf-8"))["questions"]
    cache = {} if args.live or not CACHE.exists() else json.loads(CACHE.read_text(encoding="utf-8"))
    models, failed = None, 0
    planner = settled = translated = asked = 0
    for item in items:
        q = item["q"]
        if q not in cache:
            models = models or llm.from_env()
            sent = [{"role": "system", "content": agent.planner_prompt(TODAY)}, {"role": "user", "content": f"Latest message: {q}"}]
            try:
                cache[q] = models.call("plan", sent, llm.Meter(), json_mode=True).text
            except llm.LLMError as exc:
                print(f"  FAILED CALL {q[:40]}: {exc}")
                failed += 1
                continue
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
            time.sleep(args.wait)
        plan = agent.parse_plan(cache[q])
        asked += 1
        got = plan.language if plan else "no plan"
        final = languages.settle(got, q)
        planner += got == item["language"]
        settled += final == item["language"]
        translated += bool(plan) and english(plan.standalone)
        if final != item["language"]:
            print(f"  wanted {item['language']:<10} planner {got:<10} after code {final:<10} {q}")
    print(f"\n{asked} questions" + (f", {failed} calls failed" if failed else ""))
    print(f"  language, planner alone  {planner}/{asked}")
    print(f"  language, after code     {settled}/{asked}")
    print(f"  turned into English      {translated}/{asked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
