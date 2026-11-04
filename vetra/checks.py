"""
What code decides, so the model doesn't have to: is it in force today, and does the answer
match the evidence.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .languages import western_digits
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
        if not e.history:  # read for how a rule changed, so it keeps its past seasons
            e.text, e.season = without_past_seasons({"text": e.text, "season": e.season}, question)
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
    return re.sub(r"[^\d.]", "", text).strip(".")


_MONTHS = "january february march april may june july august september october november december".split()
_MONTH = "|".join(m[:3] + m[3:].join(["(?:", ")?"]) for m in _MONTHS)
_DATE = re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?[ -]+(?:{_MONTH})\b|\b(?:{_MONTH})\s+\d{{1,2}}(?:st|nd|rd|th)?\b"
                   rf"|\b\d{{1,2}}[./-]\d{{1,2}}[./-]\d{{2,4}}\b|\b\d{{4}}-\d{{2}}-\d{{2}}\b", re.I)
_PERCENT = re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:%|per ?cent)", re.I)


def about_a_past_year(question: str, as_of: str) -> bool:
    return any(int(y) < int(as_of[:4]) for y in re.findall(r"\b(?:19|20)\d{2}\b", question))


_GENERIC = frozenset(
    "a about act amount an and application applications apply benefit benefits beneficiary card central claim cost criteria date "
    "deadline department details documents eligibility eligible farmer farmers fee form forms get government india "
    "how in information is last money of office officer on order package pay payment premium process procedure rate rates "
    "rule rules scheme schemes state subsidy the to yojana".split())
_WORD = re.compile(r"[a-z0-9]+")


def on_topic(items: list[Evidence], subject: str) -> bool:
    """
    Do the results mention what was asked about? Search always returns something, so a scheme
    we hold nothing on still brings back the nearest other scheme, looking relevant. More than
    half of the subject's distinctive words must appear: one isn't enough, because "Kisan" is
    in nearly everything. If it has no distinctive words, there's nothing to test.
    """
    def stems(words: set[str]) -> set[str]:  # first letters, so seed, seeds and seedlings match
        return {w[:4] for w in words}

    wanted = stems(set(_WORD.findall(subject.lower())) - _GENERIC)
    if not wanted:
        return True
    found = stems(set(_WORD.findall(" ".join(f"{e.doc} {e.text}" for e in items).lower())))
    return len(wanted & found) * 2 > len(wanted)


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


def clean(answer: str) -> str:
    """One form for every answer, so checks and cuts all see the same text: digits 0-9, single spaces."""
    return re.sub(r"(?<=\S)[ \t]{2,}", " ", re.sub(r"[\u00a0\u2009\u202f]", " ", western_digits(answer)))


@dataclass
class Statement:
    """One sentence of an answer, and the passages behind it."""
    text: str
    cited: tuple[int, ...]   # its own citations, or the nearest ones on the same line
    section: str = ""        # the heading it sits under: "It comes in three parts" means nothing alone


@dataclass
class Fault:
    why: str                 # told to the model when it rewrites
    sentence: str = ""       # the sentence at fault; empty if it's the whole answer's
    source: int = 0          # the passage that does say it, if code can correct the citation itself


# A sentence ends at a full stop in any script, unless a citation follows; or after a citation.
_ENDS = re.compile(r"(?<=[.!?\u0964\u0965\u06d4\u061f])\s+(?!\[E)|(?<=\])\s+(?=[A-Z])")
_SHORT_FORM = re.compile(r"(?:^|[\s(.\"'\u201c])(?:Rs|Nos?|Dt|Sl|Sri|Smt|Shri|Dr|Mrs?|Ms|Rt|vs|viz|e\.g|i\.e|w\.e\.f|G\.O|Govt|Dept|paras?|Sec|Art|Hon|[A-Z])\.$")
_MARKER = re.compile(r"^\s*(?:[-*\u2022\u2011]|\d+[.)])\s+")
_HEADING = re.compile(r"^\s*(?:#{1,6}\s|\*\*[^*]+\*\*:?\s*$)")
_LETTER = re.compile(r"[^\W\d_]")


# The writer's view of its own prompt, which means nothing to a citizen.
_BACKSTAGE = re.compile(r"\bEXACT\b|(?i:\b(?:the|this|provided|given) evidence\b(?! of)|\bexcerpts?\b"
                        r"|\bthe (?:provided|given) (?:text|passages?|documents?)\b|\bthe passages?\b)")


# The writer thinking out loud. Then the whole answer is a draft, so cutting a sentence can't fix it.
_THINKING = re.compile(r"\bI (?:must|will|should|need to)\b|(?:^|[\s*])Wait,|\bCorrection based\b|\bsnippets?\b"
                       r"|\bvisible text\b|\[E\d+\] (?:is|lists|says|does|mentions)\b", re.M)


def _sentences(line: str) -> list[str]:
    """A line's sentences. Short forms like "Rs. 6000" and "No. 34" don't end one."""
    out: list[str] = []
    for piece in _ENDS.split(line):
        if out and (_SHORT_FORM.search(out[-1]) or not _LETTER.search(out[-1])):
            out[-1] = f"{out[-1]} {piece}"
        else:
            out.append(piece)
    return out


def statements(answer: str) -> list[Statement]:
    """Every sentence that says something, each with the citations that back it. Headings don't count."""
    found = []
    section = ""
    for line in answer.splitlines():
        if _HEADING.match(line):
            section = re.sub(r"^[#*\s]+|[*:\s]+$", "", line)
            continue
        if not line.strip():
            continue
        body = _MARKER.sub("", line).strip()
        pieces = [body] if body.startswith("|") else _sentences(body)
        own = [tuple(int(n) for n in _CITATION.findall(p)) for p in pieces]
        for i, piece in enumerate(pieces):
            nearest = next((c for c in own[i:] if c), None) or next((c for c in reversed(own[:i]) if c), ())
            if _LETTER.search(_CITATION.sub("", piece)):
                found.append(Statement(piece.strip(), own[i] or nearest, section))
    return found


def _shown(e: Evidence) -> str:
    """All the model saw of a record. Exact records' figures are hidden, so they aren't in here."""
    # Scans break numbers up: "1 .6.2019" is the date 1.6.2019.
    text = re.sub(r"(?<=\d) (?=[./-]\d)|(?<=\d[./-]) (?=\d)", "", e.note if e.fact else e.text)
    return f"{text} {e.doc} {e.date or ''}"


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).replace(",", "")


def _has_number(number: str, text: str) -> bool:
    """5 isn't in 1.5, but a year is in the date 28.02.2027."""
    before = r"(?<!\d)" if re.fullmatch(r"(?:19|20)\d\d", number) else r"(?<!\d)(?<!\d\.)"
    return bool(re.search(rf"{before}{re.escape(number)}(?!\d)", text))


def _holder(says: Callable[[str], bool], evidence: list[Evidence]) -> int:
    """The number of the first passage that says it."""
    return next((n for n, e in enumerate(evidence, 1) if says(_shown(e))), 0)


def faults(answer: str, evidence: list[Evidence], as_of: str, question: str = "", guard_gaps: bool = True) -> list[Fault]:
    """
    What the model can't honestly have written, sentence by sentence. Empty means it passed.

    Exact records' figures are hidden from it, so any figure it writes must come from the text
    it was shown. It must also come from the passage its sentence cites: a right number with the
    wrong source sends the reader to a document that doesn't say it.

    guard_gaps: refuse "that isn't given" whenever exact records are printed. A short answer has
    no business saying it, but a long one can truly find a part the records don't cover.
    """
    answer = clean(answer)
    found = []
    if evidence and not has_facts(evidence) and not _CITATION.search(answer):
        found.append(Fault("cites nothing"))
    if _THINKING.search(answer):
        found.append(Fault("contains your working notes. Write only the finished answer, for the citizen"))
    asked = f" {as_of} {question}"
    everything = " ".join(_shown(e) for e in evidence) + asked
    allowed, flat_asked = _flat(everything), _flat(asked)
    known_dates = {_date_key(m.group(0)) for m in _DATE.finditer(everything)}
    asked_dates = {_date_key(m.group(0)) for m in _DATE.finditer(asked)}
    for s in statements(answer):
        def fault(why: str, source: int = 0) -> None:
            found.append(Fault(why, s.text, source))

        for n in dict.fromkeys(s.cited):
            if not 1 <= n <= len(evidence):
                fault(f"cites [E{n}], which doesn't exist")
        if _BACKSTAGE.search(s.text):
            fault("talks about the evidence or the records instead of the rules. Say \"the documents\" or \"the rates above\"")
        if guard_gaps and has_facts(evidence) and _WITHHELD.search(s.text):
            fault("says something isn't given, but the exact records printed above give it. Refer to them instead")
        for stated in re.findall(r"today[^.\n]{0,20}?(\d{4}-\d{2}-\d{2})", s.text, re.I):
            if stated != as_of:
                fault(f"gives today as {stated}; today is {as_of}")
        sources = [evidence[n - 1] for n in s.cited if 1 <= n <= len(evidence)]
        cited = " ".join(_shown(e) for e in sources) + asked
        flat_cited, cited_dates = _flat(cited), {_date_key(m.group(0)) for m in _DATE.finditer(cited)}
        names = ", ".join(f"[E{n}]" for n in s.cited)
        for figure in _FIGURE.findall(s.text):
            number, shown = _digits(figure), figure.strip()
            if not number or _has_number(number, flat_asked):
                continue
            if not _has_number(number, allowed):
                fault(f"'{shown}' isn't in the evidence you were given")
            elif not sources:
                fault(f"'{shown}' has no citation. Cite the passage it comes from", _holder(lambda t: _has_number(number, _flat(t)), evidence))
            elif not _has_number(number, flat_cited):
                fault(f"'{shown}' isn't in {names}, which this sentence cites. Cite the passage it comes from",
                      _holder(lambda t: _has_number(number, _flat(t)), evidence))
        for m in _DATE.finditer(s.text):
            key = _date_key(m.group(0))
            holder = _holder(lambda t: key in {_date_key(d.group(0)) for d in _DATE.finditer(t)}, evidence)
            if key in asked_dates:
                continue
            if key not in known_dates:
                fault(f"the date '{m.group(0)}' isn't in the evidence you were given")
            elif not sources:
                fault(f"the date '{m.group(0)}' has no citation. Cite the passage it comes from", holder)
            elif key not in cited_dates:
                fault(f"the date '{m.group(0)}' isn't in {names}, which this sentence cites. Cite the passage it comes from", holder)
    return found


def recite(answer: str, evidence: list[Evidence], as_of: str, question: str = "") -> str:
    """
    A right figure with a wrong or missing citation needs no second try: the passage that says it
    is known, so code adds it, and the reader is sent to a document that does say it.
    """
    answer = clean(answer)
    sources: dict[str, list[int]] = {}
    for f in faults(answer, evidence, as_of, question):
        if f.source:
            sources.setdefault(f.sentence, []).append(f.source)
    for sentence, numbers in sources.items():
        answer = answer.replace(sentence, sentence + "".join(f" [E{n}]" for n in dict.fromkeys(numbers)), 1)
    return answer


def claim_problems(answer: str, evidence: list[Evidence], as_of: str, question: str = "") -> list[str]:
    return [f.why for f in faults(answer, evidence, as_of, question)]


def without(answer: str, sentences: list[str]) -> str:
    """The answer with these sentences taken out, and no bullet or heading left with nothing to say."""
    text = clean(answer)
    for s in sentences:
        text = text.replace(s, "", 1)
    lines = [line.rstrip() for line in text.splitlines() if not re.fullmatch(r"\s*(?:[-*\u2022\u2011]|\d+[.)])\s*", line)]
    kept: list[str] = []
    for line in lines:
        if _HEADING.match(line) and _HEADING.match(next((k for k in reversed(kept) if k.strip()), "")):
            while not _HEADING.match(kept.pop()):   # back to the last heading, which has nothing under it
                pass
        kept.append(line)
    while kept and (not kept[-1].strip() or _HEADING.match(kept[-1])):
        kept.pop()
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def citations(answer: str, evidence: list[Evidence]) -> list[dict]:
    """The sources behind an answer, written by code from the records it cites."""
    used = sorted({int(x) for x in _CITATION.findall(answer)})
    return [{"n": n, "doc": evidence[n - 1].doc, "url": evidence[n - 1].url, "date": evidence[n - 1].date,
             "status": evidence[n - 1].status, "tool": evidence[n - 1].tool, "kind": evidence[n - 1].kind,
             "added_because": evidence[n - 1].relation, "reviewed": evidence[n - 1].reviewed,
             "text": evidence[n - 1].fact or evidence[n - 1].text}
            for n in used if 1 <= n <= len(evidence)]
