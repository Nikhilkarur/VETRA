"""Every Indian state and union territory, plus the central government."""

from __future__ import annotations

import re

CENTRAL = "IN"

STATES = {
    "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh", "AS": "Assam", "BR": "Bihar",
    "CG": "Chhattisgarh", "GA": "Goa", "GJ": "Gujarat", "HR": "Haryana",
    "HP": "Himachal Pradesh", "JH": "Jharkhand", "KA": "Karnataka", "KL": "Kerala",
    "MP": "Madhya Pradesh", "MH": "Maharashtra", "MN": "Manipur", "ML": "Meghalaya",
    "MZ": "Mizoram", "NL": "Nagaland", "OD": "Odisha", "PB": "Punjab",
    "RJ": "Rajasthan", "SK": "Sikkim", "TN": "Tamil Nadu", "TS": "Telangana",
    "TR": "Tripura", "UP": "Uttar Pradesh", "UK": "Uttarakhand", "WB": "West Bengal",
    "AN": "Andaman and Nicobar Islands", "CH": "Chandigarh",
    "DN": "Dadra and Nagar Haveli and Daman and Diu", "DL": "Delhi",
    "JK": "Jammu and Kashmir", "LA": "Ladakh", "LD": "Lakshadweep", "PY": "Puducherry",
}

_BY_NAME = {name.lower(): code for code, name in STATES.items()}


def normalise(state: str | None) -> str | None:
    """A state's code, from a code or a full name. None if it isn't one we know."""
    if not state:
        return None
    text = state.strip()
    if text.upper() in STATES:
        return text.upper()
    return _BY_NAME.get(text.lower())


def _spaced(text: str) -> str:
    """Lower case with punctuation as spaces, so "Tamil Nadu?" and "Andhra Pradesh," still match."""
    return " " + " ".join(re.sub(r"[^\w]+", " ", text.lower()).split()) + " "


def named_in(text: str) -> str | None:
    """The state a person's own words name, if any. Longest names first: "Andhra" isn't enough."""
    lowered = _spaced(text)
    for full in sorted(_BY_NAME, key=len, reverse=True):
        if f" {full} " in lowered:
            return _BY_NAME[full]
    return None


def all_named(text: str) -> list[str]:
    """Every state a person's own words name, in the order they come: "compare AP and Tamil Nadu"."""
    lowered = _spaced(text)
    spans: dict[str, int] = {}
    taken: list[tuple[int, int]] = []
    for full in sorted(_BY_NAME, key=len, reverse=True):   # "andhra pradesh" before "andhra"
        at = lowered.find(f" {full} ")
        while at >= 0:
            end = at + len(full) + 1
            if not any(a <= at < b or a < end <= b for a, b in taken):
                taken.append((at, end))
                spans.setdefault(_BY_NAME[full], at)
            at = lowered.find(f" {full} ", at + 1)
    return sorted(spans, key=spans.get)


def name(code: str) -> str:
    return "the central government" if code == CENTRAL else STATES.get(code, code)
