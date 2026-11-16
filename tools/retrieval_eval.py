"""
Does search find the right document, and how fast? Measured on eval/retrieval_set.json: citizen questions
whose answer is an exact record, so the record's source document is known. A hit is any of the top k
passages coming from that document. Each question is planned once by the real planner (cached), so
every variant searches with the same plan.

Run:  python tools/retrieval_eval.py            all variants
Variants: full (HyDE passage + topic + keywords, rerank 30), no HyDE, rerank 15, no rerank, ...
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from vetra import agent, llm, text_index  # noqa: E402
from vetra.knowledge import Knowledge  # noqa: E402

SET = ROOT / "eval" / "retrieval_set.json"
PLANS = ROOT / "eval" / "cache" / "retrieval_plans.json"

VARIANTS = {
    "full (HyDE, rerank 30)": dict(hyde=True, rerank=30),
    "no HyDE, rerank 30": dict(hyde=False, rerank=30),
    "HyDE, rerank 15": dict(hyde=True, rerank=15),
    "no HyDE, rerank 15": dict(hyde=False, rerank=15),
    "HyDE, no rerank": dict(hyde=True, rerank=0),
    "no HyDE, no rerank": dict(hyde=False, rerank=0),
}


def plans(cases: list[dict]) -> dict:
    have = json.loads(PLANS.read_text(encoding="utf-8")) if PLANS.exists() else {}
    models, knowledge, today = llm.from_env(), Knowledge(), time.strftime("%Y-%m-%d")
    for c in cases:
        if c["q"] in have:
            continue
        p = agent.make_plan(c["q"], [], models, llm.Meter(), today, knowledge)
        have[c["q"]] = {"standalone": p.standalone, "passage": p.passage, "topic": p.topic,
                        "keywords": list(p.keywords)} if p else None
        PLANS.parent.mkdir(parents=True, exist_ok=True)
        PLANS.write_text(json.dumps(have, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  planned: {c['q'][:60]}", flush=True)
    return have


def rank_of(found: list[dict], urls: set[str]) -> int | None:
    for n, item in enumerate(found, 1):
        if item.get("source_url") in urls:
            return n
    return None


def main() -> int:
    cases = json.loads(SET.read_text(encoding="utf-8"))
    planned = plans(cases)
    for c in cases:   # warm the indexes, so the first variant isn't charged for loading
        text_index.search("warm up", c["domain"], c["state"], rerank=True)
    rows = {}
    for name, v in VARIANTS.items():
        text_index.RERANK_DEPTH = v["rerank"] or 30
        hits6 = hits10 = 0
        rr, secs, by_style = [], [], {}
        for c in cases:
            p = planned.get(c["q"]) or {}
            started = time.perf_counter()
            found = text_index.search(p.get("standalone") or c["q"], c["domain"], c["state"],
                                      passage=p.get("passage", "") if v["hyde"] else "", topic=p.get("topic", ""),
                                      keywords=tuple(p.get("keywords") or ()), k=10, rerank=bool(v["rerank"]))
            secs.append(time.perf_counter() - started)
            n = rank_of(found[:10], set(filter(None, c["urls"])))
            hits6 += bool(n and n <= 6)
            hits10 += bool(n)
            rr.append(1 / n if n else 0)
            s = by_style.setdefault(c["style"], [0, 0])
            s[0] += bool(n and n <= 6)
            s[1] += 1
        rows[name] = (hits6, hits10, statistics.mean(rr), statistics.mean(secs), by_style)
        styles = ", ".join(f"{k} {a}/{b}" for k, (a, b) in sorted(by_style.items()))
        print(f"{name:24} top6 {hits6}/{len(cases)}  top10 {hits10}/{len(cases)}  MRR {statistics.mean(rr):.2f}  "
              f"{statistics.mean(secs):.2f}s/search  ({styles})", flush=True)
    out = ROOT / "eval" / "cache" / "retrieval_eval.json"
    out.write_text(json.dumps({k: {"top6": a, "top10": b, "mrr": round(m, 3), "seconds": round(s, 2), "by_style": st}
                               for k, (a, b, m, s, st) in rows.items()}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
