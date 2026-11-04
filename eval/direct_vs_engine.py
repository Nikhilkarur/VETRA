"""
Is VETRA better than asking a model directly?

The same questions go to plain Gemini, answering from memory, and to VETRA. --search adds Gemini
with Google Search, the harder opponent, which the free tier refused on 5 November 2026 and so
needs a paid key. A correct fact must appear in the answer. For questions nobody can answer from what's held, the right response is to
say it can't be found. Text matching is a rough guide, so read the answers: they're all saved.

Answers are saved as they arrive, so a re-run only asks what's missing. --live starts again.

Run:  python eval/direct_vs_engine.py
      python eval/direct_vs_engine.py --show
      python eval/direct_vs_engine.py --search
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
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests  # noqa: E402

from vetra import agent, llm  # noqa: E402

TODAY = "2026-11-05"
LABELS = ROOT / "eval" / "direct_questions.json"
SAVED = ROOT / "eval" / "cache" / "direct_vs_engine.json"
NATIVE = "https://generativelanguage.googleapis.com/v1beta/models"
ARMS = ("plain", "vetra")
_ADMITS = re.compile(r"(?i)not found|not in our|don't have|do not have|doesn't appear|does not appear|could not find|couldn't find|"
                     r"cannot confirm|can't confirm|cannot find|can't find|no information|not aware|unable to (?:find|confirm|verify)|"
                     r"documents i have don't|no (?:such|record|official|publicly|verifiable)|not (?:publicly )?available|not exist|isn't (?:a|an) (?:official|recognised)")
SYSTEM = f"Today is {TODAY}. Answer this citizen's question about Indian government rules."


class NoLog:
    def report(self, gap) -> None:
        pass


def ask_plain(item: dict, models: llm.Models) -> dict:
    sent = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": item["q"]}]
    reply = models.call("compose", sent, llm.Meter())
    return {"answer": reply.text, "model": reply.model, "tokens": reply.tokens}


def ask_search(item: dict, models: llm.Models) -> dict:
    key = os.environ.get("LLM_API_KEY", "")
    body = {"system_instruction": {"parts": [{"text": SYSTEM}]}, "contents": [{"parts": [{"text": item["q"]}]}], "tools": [{"google_search": {}}]}
    last = ""
    for model in models.roles["compose"]:
        r = requests.post(f"{NATIVE}/{model}:generateContent", json=body, headers={"x-goog-api-key": key}, timeout=180)
        if r.ok:
            d = r.json()
            parts = d["candidates"][0].get("content", {}).get("parts", [])
            grounding = d["candidates"][0].get("groundingMetadata") or {}
            return {"answer": "".join(p.get("text", "") for p in parts), "model": model,
                    "tokens": (d.get("usageMetadata") or {}).get("totalTokenCount", 0),
                    "searches": grounding.get("webSearchQueries") or [],
                    "sources": [(c.get("web") or {}).get("title", "") for c in grounding.get("groundingChunks") or []]}
        last = f"{r.status_code} " + " ".join(r.text.replace(key, "<key>").split())[:160]
        time.sleep(4)
    raise llm.LLMError(last)


def ask_vetra(item: dict, models: llm.Models) -> dict:
    r = agent.answer(item["q"], state=item["state"], models=models, as_of=TODAY, gaps=NoLog())
    if r.kind == "failed" or r.trace.get("error"):
        raise llm.LLMError(f"{r.kind}: {r.trace.get('error')}")
    return {"answer": r.answer, "kind": r.kind, "depth": r.depth, "tokens": r.trace.get("tokens"), "calls": r.trace.get("calls"),
            "seconds": r.trace.get("seconds"), "models": [s.get("model") for s in r.trace.get("steps", [])],
            "problems": r.trace.get("final_problems"), "sources": [s["doc"] for s in r.sources]}


def score(item: dict, answer: str) -> str:
    if item["group"] in ("gap", "invented"):
        return "admits" if _ADMITS.search(answer) else "doesn't admit"
    if any(re.search(a, answer) for a in item["any"]):
        return "correct"
    return "admits" if _ADMITS.search(answer) else "wrong"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--live", action="store_true", help="ask everything again")
    parser.add_argument("--show", action="store_true", help="print every answer")
    parser.add_argument("--wait", type=float, default=8, help="seconds between questions")
    parser.add_argument("--search", action="store_true", help="also try Gemini with Google Search")
    args = parser.parse_args()
    arms = ("plain", "search", "vetra") if args.search else ARMS

    items = json.loads(LABELS.read_text(encoding="utf-8"))["questions"]
    saved = {} if args.live or not SAVED.exists() else json.loads(SAVED.read_text(encoding="utf-8"))
    models = llm.from_env()
    asks = {"plain": ask_plain, "search": ask_search, "vetra": ask_vetra}
    failures = 0
    for item in items:
        for arm in arms:
            if f"{item['id']}/{arm}" in saved:
                continue
            try:
                saved[f"{item['id']}/{arm}"] = asks[arm](item, models)
                SAVED.write_text(json.dumps(saved, ensure_ascii=False, indent=1), encoding="utf-8")
                got = saved[f"{item['id']}/{arm}"]["answer"]
                print(f"  {item['id']:<22} {arm:<7} {score(item, got)}", flush=True)
            except Exception as exc:
                failures += 1
                print(f"  {item['id']:<22} {arm:<7} FAILED {str(exc)[:110]}", flush=True)
            time.sleep(args.wait)

    print(f"\n{'group':<13}{'questions':>10}" + "".join(f"{a:>18}" for a in arms))
    for group, good in (("held", "correct"), ("other_state", "correct"), ("gap", "admits"), ("invented", "admits")):
        chosen = [i for i in items if i["group"] == group]
        cells = []
        for arm in arms:
            done = [i for i in chosen if f"{i['id']}/{arm}" in saved]
            right = sum(score(i, saved[f"{i['id']}/{arm}"]["answer"]) == good for i in done)
            cells.append(f"{right}/{len(done)} {good}")
        print(f"{group:<13}{len(chosen):>10}" + "".join(f"{c:>18}" for c in cells))
    for arm in arms:
        tokens = [v.get("tokens") or 0 for k, v in saved.items() if k.endswith("/" + arm)]
        if tokens:
            print(f"{arm}: {sum(tokens) // len(tokens):,} tokens a question on average")
    if failures:
        print(f"{failures} calls failed; run again to retry them")
    if args.show:
        for item in items:
            print(f"\n=== {item['q']}")
            for arm in arms:
                got = saved.get(f"{item['id']}/{arm}")
                if got:
                    print(f"--- {arm} [{score(item, got['answer'])}]\n{got['answer'][:900]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
