"""
Exact facts, written by code.

An amount or a deadline from a reviewed record goes into the answer exactly as it's stored.
The model gets a description with no figures in it (the "note"), so it can explain what the
fact means but has nothing to garble. In testing it read a correct "31 December for rice" as
15 December, and merged 5% and 1.5% into one line; checks can't catch that, because both
figures really are in the evidence.

A deadline record is a window:

    {"scheme": "PMFBY", "scheme_words": ["pmfby", "fasal bima"], "for_season": "Rabi 2026-27",
     "activity": "enrolment", "opens": "2026-10-01", "closes": "2026-12-31",
     "applies_to": ["rice", "paddy"]}          # or "except": [...], or neither for all crops
"""

from __future__ import annotations

from datetime import date

_MONTHS_TE = ("జనవరి", "ఫిబ్రవరి", "మార్చి", "ఏప్రిల్", "మే", "జూన్", "జూలై", "ఆగస్టు", "సెప్టెంబర్", "అక్టోబర్", "నవంబర్", "డిసెంబర్")


def long_date(iso: str, language: str = "english") -> str:
    d = date.fromisoformat(iso)
    month = _MONTHS_TE[d.month - 1] if language == "telugu" else d.strftime("%B")
    return f"{d.day} {month} {d.year}"


def is_window(record: dict) -> bool:
    return bool(record.get("closes"))


def is_open(record: dict, as_of: str) -> bool:
    return record.get("opens", "") <= as_of <= record["closes"]


def _mentions(words: list[str], text: str) -> bool:
    return any(w.lower() in text for w in words)


def names_scheme(records: list[dict], asked: str) -> list[dict]:
    """If the user named a scheme, only that scheme's records. Otherwise all of them."""
    named = [r for r in records if _mentions(r.get("scheme_words") or [], asked)]
    return named or records


def _names_its_crop(window: dict, asked: str) -> bool:
    return _mentions(window.get("applies_to") or [], asked)


def _covers(window: dict, asked: str) -> bool:
    """For a crop the windows know about: does this window include it?"""
    if window.get("applies_to"):
        return _names_its_crop(window, asked)
    return not _mentions(window.get("except") or [], asked)


def windows_for(records: list[dict], asked: str, as_of: str) -> list[dict]:
    """
    The windows to show. No crop named: all of them, each labelled with its crop, so rice's
    later deadline can't be missed. A crop the windows know about: only those covering it,
    and within a scheme a window naming that crop wins over a general one.

    Open windows win over closed. If none is open, the latest closed, so the user learns
    it has passed.
    """
    asked = asked.lower()
    chosen = names_scheme(records, asked)
    known_crop = any(_names_its_crop(w, asked) or _mentions(w.get("except") or [], asked) for w in chosen)
    if known_crop:
        chosen = [w for w in chosen if _covers(w, asked)]
        named = {w.get("scheme") for w in chosen if _names_its_crop(w, asked)}
        chosen = [w for w in chosen if w.get("scheme") not in named or _names_its_crop(w, asked)]
    current = [w for w in chosen if is_open(w, as_of)]
    if current:
        return sorted(current, key=lambda w: (w.get("scheme", ""), w["closes"]))
    upcoming = [w for w in chosen if w.get("opens", "") > as_of]
    if upcoming:
        return sorted(upcoming, key=lambda w: w["opens"])[:2]
    return sorted(chosen, key=lambda w: w["closes"], reverse=True)[:2]


def _who(window: dict) -> str:
    if window.get("applies_to"):
        return f"for {window['applies_to'][0]}"
    if window.get("except"):
        return f"for notified crops except {window['except'][0]}"
    return "for all notified crops"


def _who_te(window: dict) -> str:
    if window.get("applies_to"):
        return f"{window['applies_to'][0]} పంటకు"
    if window.get("except"):
        return f"{window['except'][0]} తప్ప నోటిఫై చేసిన పంటలకు"
    return "నోటిఫై చేసిన అన్ని పంటలకు"


def _window_fact_te(w: dict, as_of: str) -> str:
    what = f"{w.get('scheme', '')}, {w.get('for_season', '')}, {_who_te(w)} నమోదు".strip(", ")
    span = f"{long_date(w['opens'], 'telugu')} నుండి {long_date(w['closes'], 'telugu')} వరకు" if w.get("opens") else f"{long_date(w['closes'], 'telugu')} వరకు"
    if is_open(w, as_of):
        left = (date.fromisoformat(w["closes"]) - date.fromisoformat(as_of)).days
        return f"{what}: {span}. ఇప్పుడు తెరిచి ఉంది, {left} రోజుల్లో ముగుస్తుంది."
    if w.get("opens", "") > as_of:
        return f"{what}: {span}. ఇంకా ప్రారంభం కాలేదు."
    return f"{what}: {span}. ముగిసింది."


def window_fact(w: dict, as_of: str, language: str = "english") -> str:
    if language == "telugu":
        return _window_fact_te(w, as_of)
    what = f"{w.get('scheme', '')}, {w.get('for_season', '')}, {w.get('activity', 'enrolment')} {_who(w)}".strip(", ")
    span = f"{long_date(w['opens'])} to {long_date(w['closes'])}" if w.get("opens") else f"until {long_date(w['closes'])}"
    if is_open(w, as_of):
        left = (date.fromisoformat(w["closes"]) - date.fromisoformat(as_of)).days
        return f"{what}: {span}. Open now, closes in {left} day{'' if left == 1 else 's'}."
    if w.get("opens", "") > as_of:
        return f"{what}: {span}. Not open yet."
    return f"{what}: {span}. Closed."


def window_note(w: dict, as_of: str) -> str:
    state = "open now" if is_open(w, as_of) else "not open yet" if w.get("opens", "") > as_of else "closed"
    return f"{w.get('scheme', '')} {w.get('activity', 'enrolment')} window {_who(w)}, {w.get('for_season', '')}: {state}."


def _values(outcome: dict) -> dict:
    return {k: f"{v:g}" if isinstance(v, (int, float)) else v for k, v in outcome.items()}


def speaks(rule: dict, language: str) -> bool:
    """Can this rule be printed in this language? If not, it goes in English."""
    return language == "english" or f"render_{language}" in rule


def decided_fact(rule: dict, outcome: dict, language: str = "english") -> str:
    template = rule.get(f"render_{language}") or rule.get("render")
    if template:
        return template.format(**_values(outcome))
    return "; ".join(f"{k.replace('_', ' ')}: {v}" for k, v in outcome.items())


def not_notified_fact(rule: dict, crop: str, language: str = "english") -> str:
    if language == "telugu":
        return f"{crop} ఈ పథకం కింద నోటిఫై చేసిన పంట కాదు, కాబట్టి ఈ పథకం ప్రీమియం రేటు దీనికి వర్తించదు"
    return f"{crop} is not a notified crop under this scheme, so its premium rate doesn't apply"


def all_cases_fact(rule: dict, language: str = "english") -> str:
    """What a rule says for everyone, when the user's facts don't decide it yet."""
    lines = []
    for case in rule.get("cases", []):
        condition = (case.get(f"label_{language}") or case.get("label")
                     or ", ".join(f"{k.replace('_', ' ')} is {v}" for k, v in case["when"].items()))
        lines.append(f"{condition}: {decided_fact(rule, case['outcome'], language)}")
    return " ".join(f"({n}) {line}." for n, line in enumerate(lines, 1))
