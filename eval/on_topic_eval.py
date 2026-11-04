"""
Does the off-topic check reject good results? And does it catch schemes we don't hold?

Uses the saved LLM outputs, so it makes no API calls. Two measures:
- false alarms: questions whose answer really is in the results, called off-topic;
- catches: schemes from states whose documents we don't hold, on central documents only.

Run:  python eval/on_topic_eval.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "rag")]
os.environ.setdefault("HYDE_CACHE", str(ROOT / "eval" / "cache" / "hyde.json"))
os.environ.setdefault("LLM_CACHE_DIR", str(ROOT / "eval" / "cache"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import domains  # noqa: E402
import query_expansion as QX  # noqa: E402
import retrieve as R  # noqa: E402

from vetra import checks, text_index  # noqa: E402
from vetra.tools import Evidence  # noqa: E402

NOT_HELD = ["Rythu Bandhu", "Krushak Odisha KALIA", "Mukhyamantri Kisan Kalyan Yojana", "Namo Shetkari Mahasanman Nidhi",
            "Krishi Bhagya", "Rajiv Gandhi Kisan Nyay Yojana", "Bangla Shasya Bima", "Kuruvai package"]


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def evidence(hits: list[dict]) -> list[Evidence]:
    return [Evidence(h["id"], "text_search", h["text"], h.get("source", "")) for h in hits]


def main() -> int:
    data = json.loads((ROOT / "eval" / "agri_questions.json").read_text(encoding="utf-8"))
    good = alarms = 0
    for items in (v for v in data.values() if isinstance(v, list)):
        for item in items:
            question = domains.expand_abbreviations(item["q"], domains.get("agriculture"))
            passage = R.hypothetical_passage(question, "agriculture") or ""
            aids = QX.rewrites(question, "agriculture") or {}
            topic = aids.get("topic") or item["q"]
            hits = text_index.search(item["q"], "agriculture", "AP", passage, topic, tuple(aids.get("keywords") or ()))
            context = squash(" ".join(h["text"] for h in hits))
            if not all(squash(p) in context for p in item["probes"]):
                continue
            good += 1
            if not checks.on_topic(evidence(hits), topic):
                alarms += 1
                print(f"  FALSE ALARM topic={topic[:45]!r} q={item['q'][:50]!r}")
    print(f"false alarms: {alarms} of {good} questions whose answer is in the results")
    caught = 0
    for scheme in NOT_HELD:
        ok = not checks.on_topic(evidence(text_index.search(scheme, "agriculture", "KA")), scheme)
        caught += ok
        print(f"  {'caught' if ok else 'MISSED'}  {scheme}")
    print(f"schemes we don't hold, recognised as missing: {caught} of {len(NOT_HELD)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
