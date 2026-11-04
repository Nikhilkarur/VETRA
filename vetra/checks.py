"""
What code decides, so the model doesn't have to: is it in force today, and does the answer
match the evidence.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from .tools import Evidence

def _out_of_date(e: Evidence, as_of: str) -> bool:
    return bool(e.valid_until and e.valid_until < as_of) or bool(e.valid_from and e.valid_from > as_of)


def in_force(items: list[Evidence], as_of: str, question: str = "") -> list[Evidence]:
    """
    Remove what doesn't apply on as_of, cutting past seasons' rules out of the text.

    A question naming a past year asks about history, so it keeps those rules. Replaced
    documents stay, marked by their status, because they answer "what was it called".
    """
    rag = str(Path(__file__).resolve().parent.parent / "rag")
    if rag not in sys.path:
        sys.path.insert(0, rag)
    from answer import without_past_seasons

    keep = []
    for e in items:
        if _out_of_date(e, as_of) and (e.valid_until or e.valid_from or "")[:4] not in question:
            continue
        text, season = without_past_seasons({"text": e.text, "season": e.season}, question)
        e.text, e.season = text, season
        keep.append(e)
    return keep


def order(items: list[Evidence]) -> list[Evidence]:
    """Exact records before searched text, in-force before anything else. Removes repeats."""
    seen, unique = set(), []
    for e in items:
        if e.key not in seen:
            seen.add(e.key)
            unique.append(e)
    rank = {"rule_check": 0, "dates_lookup": 1, "number_lookup": 1, "directory_lookup": 1,
            "links_walk": 2, "form_search": 2, "text_search": 3}
    return sorted(unique, key=lambda e: (rank.get(e.tool, 3), e.status == "not_in_force"))


_CITATION = re.compile(r"\[E(\d+)\]")
# An amount, a percentage or a year: the figures that must never be invented.
_FIGURE = re.compile(r"(?:₹|Rs\.?\s*)\s*\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s*%|\b(?:19|20)\d{2}\b", re.I)


def tidy_citations(answer: str) -> str:
    """Models write citations many ways; the checks and the page expect [E2]."""
    answer = re.sub(r"【\s*E?(\d+)[^】]*】", r"[E\1]", answer)
    answer = re.sub(r"\[((?:\s*E?\d+\s*[,;]?)+)\]",
                    lambda m: "".join(f"[E{n}]" for n in re.findall(r"\d+", m.group(1))), answer)
    return re.sub(r"\(E(\d+)\)", r"[E\1]", answer)


def _digits(text: str) -> str:
    return re.sub(r"[^\d.]", "", text).rstrip(".")


def claim_problems(answer: str, evidence: list[Evidence], as_of: str, question: str = "") -> list[str]:
    """Citations that point nowhere, and figures found in no evidence. Empty means it passed."""
    found = []
    for n in {int(x) for x in _CITATION.findall(answer)}:
        if not 1 <= n <= len(evidence):
            found.append(f"cites [E{n}], which doesn't exist")
    if evidence and not _CITATION.search(answer):
        found.append("cites nothing")
    for stated in re.findall(r"today[^.\n]{0,20}?(\d{4}-\d{2}-\d{2})", answer, re.I):
        if stated != as_of:
            found.append(f"gives today as {stated}; today is {as_of}")
    allowed = re.sub(r"\s+", " ", " ".join(e.text + " " + e.doc for e in evidence) + f" {as_of} {question}").replace(",", "")
    for figure in _FIGURE.findall(answer):
        number = _digits(figure)
        if number and not re.search(rf"(?<![\d.]){re.escape(number)}(?![\d])", allowed):
            found.append(f"'{figure.strip()}' isn't in the evidence")
    return found


def citations(answer: str, evidence: list[Evidence]) -> list[dict]:
    """The sources behind an answer, written by code from the records it cites."""
    used = sorted({int(x) for x in _CITATION.findall(answer)})
    return [{"n": n, "doc": evidence[n - 1].doc, "url": evidence[n - 1].url, "date": evidence[n - 1].date,
             "status": evidence[n - 1].status, "tool": evidence[n - 1].tool,
             "reviewed": evidence[n - 1].reviewed}
            for n in used if 1 <= n <= len(evidence)]
