"""
The sorted knowledge: one store for each kind of content, in plain files people can review.

    knowledge/<domain>/<store>.jsonl     one record per line

Search is only for "text". A date, an amount, an officer or an amendment link has its own
store, so it's looked up exactly and never has to survive a similarity search.

Every record carries where it applies and where it came from:

    id, store, domain, jurisdiction ("AP" or "IN"), text, source {doc, section, url, date},
    plus optional valid_from, valid_until, status, season, legal_weight, reviewed
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "knowledge"
STORES = ("dates", "rules", "numbers", "directory", "links", "forms")  # "text": see text_search.py
_WORDS = re.compile(r"[a-z0-9]+")
_COMMON = frozenset("a an and are at can do for from how i in is it me my of on or the to what when who why with".split())


def problems(record: dict) -> list[str]:
    """What's wrong with a record. A record without a source or a place never gets in."""
    found = [f"no {k}" for k in ("id", "store", "domain", "jurisdiction", "text") if not record.get(k)]
    if record.get("store") and record["store"] not in STORES:
        found.append(f"unknown store {record['store']}")
    if not (record.get("source") or {}).get("doc"):
        found.append("no source document")
    if record.get("store") == "rules" and not record.get("cases"):
        found.append("rule has no cases")
    if record.get("closes"):
        try:
            if record.get("opens") and date.fromisoformat(record["opens"]) > date.fromisoformat(record["closes"]):
                found.append("window closes before it opens")
        except ValueError:
            found.append("window dates aren't YYYY-MM-DD")
    return found


def _words(text: str) -> set[str]:
    return set(_WORDS.findall(text.lower())) - _COMMON


class Knowledge:
    def __init__(self, root: Path = ROOT):
        self.records: dict[tuple[str, str], list[dict]] = {}
        for path in sorted(Path(root).glob("*/*.jsonl")):
            if path.parent.name == "inbox":  # waiting to be sorted, not knowledge yet
                continue
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.records[(path.parent.name, path.stem)] = rows

    def select(self, domain: str, store: str, state: str | None) -> list[dict]:
        """Records that apply in this state: its own, and the central government's."""
        return [r for r in self.records.get((domain, store), []) if r["jurisdiction"] in (state, "IN")]

    def find(self, domain: str, store: str, state: str | None, query: str, top: int = 6) -> list[dict]:
        """Records sharing the most words with the query. Exact stores are small; no index needed."""
        wanted = _words(query)
        scored = []
        for r in self.select(domain, store, state):
            hay = _words(f"{r['text']} {r.get('subject', '')} {r.get('name', '')}")
            score = len(wanted & hay)
            if score >= min(2, len(wanted)):  # one shared word is usually chance
                scored.append((score, r))
        scored.sort(key=lambda s: -s[0])
        return [r for _, r in scored[:top]]

    def rule_inputs(self, question: str) -> dict[str, dict]:
        """The facts rules matching a question need, so the planner uses their exact values."""
        wanted = _words(question)
        found = {}
        for (_, store), rows in self.records.items():
            if store == "rules":
                for r in rows:
                    if len(wanted & _words(f"{r['text']} {r.get('subject', '')}")) >= 2:
                        found[r["id"]] = r.get("inputs") or {}
        return found
