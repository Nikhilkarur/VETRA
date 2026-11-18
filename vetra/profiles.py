"""
A state's profile for a topic: one exact record for each main aspect, so a broad comparison ("how does
agriculture support differ between AP and TN?") is answered from checked records for both states,
not from whichever passages one vague search happens to bring back.

The aspects and their patterns are the ones coverage is measured by (tools/coverage_grid.py).
"""
from __future__ import annotations

import importlib.util
import re
from functools import lru_cache
from pathlib import Path

from .knowledge import Knowledge
from .tools import Evidence, _from_record

ROOT = Path(__file__).resolve().parent.parent
STORES = ("numbers", "rules", "dates")
TOOL = {"numbers": "number_lookup", "rules": "rule_check", "dates": "dates_lookup"}

# What a broad question about a topic most likely means, when it names no aspect.
HEADLINE = {
    "agriculture": ("income support", "crop loans", "crop insurance", "disaster relief", "drip", "farm power",
                    "machinery", "horticulture", "MSP", "tenant farmers"),
    "finance": ("stamp duty", "registration fee", "vehicle tax", "pensions", "direct benefits", "SHGs", "housing",
                "budget"),
}


@lru_cache(maxsize=1)
def aspects() -> dict[str, dict[str, str]]:
    path = ROOT / "tools" / "coverage_grid.py"
    source = path.read_text(encoding="utf-8").split("def grid(")[0]
    scope: dict = {"__name__": "profiles_import", "__file__": str(path)}
    exec(compile(source, str(path), "exec"), scope)
    return scope["ASPECTS"]


def asked_aspects(domain: str, question: str) -> list[str]:
    """The aspects a question names, in the order of the aspect list."""
    return [a for a, pattern in aspects().get(domain, {}).items() if re.search(pattern, question, re.I)]


def profile(domain: str, state: str, knowledge: Knowledge, question: str, limit: int = 10) -> list[Evidence]:
    """One record of the state's own for each aspect the question names, or else for the topic's main aspects.
    Central records are left out: they are the same in every state, so they don't tell states apart."""
    patterns = aspects().get(domain, {})
    wanted = asked_aspects(domain, question) or [a for a in HEADLINE.get(domain, ()) if a in patterns]
    own = [(store, r) for store in STORES for r in knowledge.select(domain, store, state) if r["jurisdiction"] == state]
    chosen, used = [], set()
    for aspect in wanted:
        pattern = re.compile(patterns[aspect], re.I)
        # A record named for the aspect first ("crop insurance premium"), then one that only mentions it:
        # text alone picked a dairy loan for crop loans and a wild boar repellent for horticulture.
        word = aspect.lower().rstrip("s")
        titled = [r for _, r in own if r["id"] not in used and word in r.get("subject", "").lower()]
        named = titled or [r for _, r in own if r["id"] not in used and pattern.search(r.get("subject", ""))]
        mentioned = [r for _, r in own if r["id"] not in used and pattern.search(r["text"])]
        pick = (named or mentioned or [None])[0]
        if pick:
            store = next(st for st, r in own if r is pick)
            chosen.append(_from_record(pick, TOOL[store]))
            used.add(pick["id"])
        if len(chosen) >= limit:
            break
    return chosen
