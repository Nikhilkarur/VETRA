"""
Eligibility and amounts, decided by code from reviewed rule files, never by the model.

A rule is data:

    {"inputs": {"crop_class": ["foodgrain_oilseed", "commercial_horticulture"]},
     "cases": [{"when": {"crop_class": "commercial_horticulture"},
                "outcome": {"farmer_premium_percent": 5}}]}

"when" compares a fact with a value, or with {"max": n}, {"min": n} or {"in": [...]}.
"aliases" maps everyday words onto a rule's values ({"crop_class": {"paddy": "foodgrain_or_oilseed"}}),
so which class a crop belongs to is reviewed data, not the model's judgement.

The first matching case wins. A fact the case needs but the user hasn't given is reported
as missing, so the agent can ask rather than guess.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Result:
    outcome: dict | None = None        # None: no decision was reached
    missing: list[str] = field(default_factory=list)


def _holds(test, value) -> bool:
    if not isinstance(test, dict):
        return str(value).lower() == str(test).lower()
    try:
        return (("max" not in test or float(value) <= test["max"])
                and ("min" not in test or float(value) >= test["min"])
                and ("in" not in test or str(value).lower() in [str(v).lower() for v in test["in"]]))
    except (TypeError, ValueError):
        return False


def _plain_words(rule: dict, facts: dict) -> dict:
    aliases = rule.get("aliases") or {}
    return {k: (aliases.get(k) or {}).get(str(v).strip().lower(), v) for k, v in facts.items()}


def facts_in_words(rule: dict, words: str) -> dict:
    """Facts the user's own words settle, by the rule's values and aliases. No model needed."""
    text = f" {re.sub(r'[^a-z0-9]+', ' ', words.lower())} "
    found = {}
    for key, values in (rule.get("inputs") or {}).items():
        for value in values:
            if f" {str(value).replace('_', ' ').lower()} " in text:
                found[key] = value
        for word, value in (rule.get("aliases") or {}).get(key, {}).items():
            if f" {word.lower()} " in text:
                found[key] = value
    return found


def not_notified(rule: dict, facts: dict, words: str) -> str | None:
    """A crop the person named that this scheme's order doesn't cover: its rate would mislead them."""
    said = f"{words} {' '.join(str(v) for v in facts.values())}".lower()
    text = f" {re.sub(r'[^a-z0-9]+', ' ', said)} "
    return next((c for c in rule.get("not_notified", ()) if f" {c} " in text), None)


def evaluate(rule: dict, facts: dict) -> Result:
    facts = _plain_words(rule, facts)
    missing: list[str] = []
    for case in rule.get("cases", []):
        needed = [k for k in case["when"] if facts.get(k) in (None, "")]
        if needed:
            missing += [k for k in needed if k not in missing]
            continue
        if all(_holds(test, facts[k]) for k, test in case["when"].items()):
            return Result(case["outcome"])
    return Result(None, missing)
