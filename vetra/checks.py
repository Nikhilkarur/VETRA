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


_MONTHS = "january february march april may june july august september october november december".split()
_MONTH = "|".join(m[:3] + m[3:].join(["(?:", ")?"]) for m in _MONTHS)
_DATE = re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?[ -]+(?:{_MONTH})\b|\b(?:{_MONTH})\s+\d{{1,2}}(?:st|nd|rd|th)?\b"
                   rf"|\b\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}}\b|\b\d{{4}}-\d{{2}}-\d{{2}}\b", re.I)
_PERCENT = re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:%|per ?cent)", re.I)


def about_a_past_year(question: str, as_of: str) -> bool:
    return any(int(y) < int(as_of[:4]) for y in re.findall(r"\b(?:19|20)\d{2}\b", question))


def has_facts(evidence: list[Evidence]) -> bool:
    return any(e.fact for e in evidence)


def fact_lines(evidence: list[Evidence]) -> str:
    """The block code prints: every exact fact, word for word, with its citation."""
    return "\n".join(f"- {e.fact} [E{n}]" for n, e in enumerate(evidence, 1) if e.fact)


_WITHHELD = re.compile(r"\b(?:not (?:specified|provided|given|stated|mentioned|listed|available)|does(?:n't| not) (?:specify|give|state|provide|mention|list)"
                       r"|cannot be determined|can't be determined|no (?:specific|exact) (?:date|deadline|amount|rate)"
                       r"|no \w+(?: \w+)? (?:is|are) (?:specified|given|provided|stated|listed))\b", re.I)


def _date_key(text: str) -> tuple[int, int] | None:
    """(day, month) from any way orders write a date, so 15th July and 15.07.2026 match."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return int(m.group(3)), int(m.group(2))
    m = re.match(r"(\d{1,2})[./-](\d{1,2})[./-]\d{2,4}", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    day = re.search(r"\d{1,2}", text)
    month = re.search(r"[a-z]{3}", re.sub(r"\d+(?:st|nd|rd|th)?", "", text.lower()))
    if day and month and month.group(0) in _MONTH_NUMBER:
        return int(day.group(0)), _MONTH_NUMBER[month.group(0)]
    return None


_MONTH_NUMBER = {m[:3]: n for n, m in enumerate(_MONTHS, 1)}


def claim_problems(answer: str, evidence: list[Evidence], as_of: str, question: str = "") -> list[str]:
    """
    What the model can't honestly have written. Empty means it passed.

    Exact records' figures are hidden from it, so any figure it writes must come from the
    text it was shown; if it isn't there, the model made it up.
    """
    found = []
    for n in {int(x) for x in _CITATION.findall(answer)}:
        if not 1 <= n <= len(evidence):
            found.append(f"cites [E{n}], which doesn't exist")
    if evidence and not has_facts(evidence) and not _CITATION.search(answer):
        found.append("cites nothing")
    if has_facts(evidence) and _WITHHELD.search(answer):
        # Text can truly lack something, but only say so when nothing exact covers the question.
        found.append("says something isn't given, but the exact records printed above give it. Refer to them instead")
    for stated in re.findall(r"today[^.\n]{0,20}?(\d{4}-\d{2}-\d{2})", answer, re.I):
        if stated != as_of:
            found.append(f"gives today as {stated}; today is {as_of}")
    shown = " ".join((e.note if e.fact else e.text) + " " + e.doc for e in evidence) + f" {as_of} {question}"
    allowed = re.sub(r"\s+", " ", shown).replace(",", "")
    for figure in _FIGURE.findall(answer):
        number = _digits(figure)
        if number and not re.search(rf"(?<![\d.]){re.escape(number)}(?![\d])", allowed):
            found.append(f"'{figure.strip()}' isn't in the evidence you were given")
    known_dates = {_date_key(m.group(0)) for m in _DATE.finditer(shown)}
    for m in _DATE.finditer(answer):
        if _date_key(m.group(0)) not in known_dates:
            found.append(f"the date '{m.group(0)}' isn't in the evidence you were given")
    return found


def citations(answer: str, evidence: list[Evidence]) -> list[dict]:
    """The sources behind an answer, written by code from the records it cites."""
    used = sorted({int(x) for x in _CITATION.findall(answer)})
    return [{"n": n, "doc": evidence[n - 1].doc, "url": evidence[n - 1].url, "date": evidence[n - 1].date,
             "status": evidence[n - 1].status, "tool": evidence[n - 1].tool,
             "reviewed": evidence[n - 1].reviewed, "text": evidence[n - 1].fact or evidence[n - 1].text}
            for n in used if 1 <= n <= len(evidence)]
