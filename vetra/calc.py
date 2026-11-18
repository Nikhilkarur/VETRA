"""
Worked figures, by code. The writer may do no arithmetic (it copies figures exactly), so "how much
will it cost for a 20 lakh property" got the rates but not the cost. When the question gives an
amount and a checked record gives a rate as a percentage of a value, code works it out and says so.
"""
from __future__ import annotations

import re

from .tools import Evidence

_RECORD_TOOLS = ("number_lookup", "rule_check", "dates_lookup")
_AMOUNT = re.compile(r"(?:rs\.?|₹|rupees?)?\s*(\d+(?:[.,]\d+)*)\s*(lakh|lakhs|lac|crore|crores|cr)?\b", re.I)
_RATE = re.compile(r"([A-Za-z][A-Za-z /-]{2,40}?)\s+(\d+(?:\.\d+)?)\s*%\s+of\s+(?:the\s+)?"
                   r"(market value|consideration|sum insured|value|guideline value)", re.I)


def asked_amount(question: str) -> int | None:
    """A rupee amount the citizen gives: "20 lakh", "Rs 15,00,000", "1.5 crore". Years and small numbers aren't."""
    for m in _AMOUNT.finditer(question):
        number, unit = m.group(1).replace(",", ""), (m.group(2) or "").lower()
        try:
            value = float(number)
        except ValueError:
            continue
        if unit.startswith("l"):
            value *= 1_00_000
        elif unit.startswith("c"):
            value *= 1_00_00_000
        elif value < 10_000 or (1900 <= value <= 2100 and "." not in number):
            continue   # not a property value, or a year
        return int(round(value))
    return None


def indian(n: float) -> str:
    """Rs 1,40,000, grouped the Indian way."""
    whole = f"{int(round(n))}"
    if len(whole) <= 3:
        return whole
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return ",".join([head] + groups + [tail]) if head else ",".join(groups + [tail])


def worked(question: str, items: list[Evidence]) -> list[str]:
    """Lines like "Stamp duty: 7% of Rs 20,00,000 = Rs 1,40,000 [E3]", from checked records only."""
    amount = asked_amount(question)
    if not amount:
        return []
    lines, total, seen = [], 0.0, set()
    for n, e in enumerate(items, 1):
        if e.tool not in _RECORD_TOOLS:
            continue
        for m in _RATE.finditer(e.text):
            what = m.group(1).strip().split(";")[-1].split(":")[-1].strip()
            rate = float(m.group(2))
            key = (what.lower(), rate)
            if key in seen or not what:
                continue
            seen.add(key)
            cost = amount * rate / 100
            total += cost
            lines.append(f"- {what[0].upper() + what[1:]}: {m.group(2)}% of Rs {indian(amount)} = Rs {indian(cost)} [E{n}]")
    if len(lines) > 1:
        lines.append(f"- Together: Rs {indian(total)}")
    return lines
