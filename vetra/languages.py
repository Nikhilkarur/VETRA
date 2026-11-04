"""
The languages a citizen can ask in: India's 22 scheduled languages and English.

Code writes exact facts in English and Telugu from templates. For every other language they're
translated, the numbers are checked by code, and the English original is printed beside them.
"""

from __future__ import annotations

import json
import re
import unicodedata

from . import llm

NAMES = {
    "english": "English", "hindi": "हिन्दी", "bengali": "বাংলা", "marathi": "मराठी", "telugu": "తెలుగు",
    "tamil": "தமிழ்", "gujarati": "ગુજરાતી", "urdu": "اردو", "kannada": "ಕನ್ನಡ", "odia": "ଓଡ଼ିଆ",
    "malayalam": "മലയാളം", "punjabi": "ਪੰਜਾਬੀ", "assamese": "অসমীয়া", "maithili": "मैथिली",
    "santali": "ᱥᱟᱱᱛᱟᱞᱤ", "kashmiri": "کٲشُر", "nepali": "नेपाली", "sindhi": "سنڌي", "dogri": "डोगरी",
    "konkani": "कोंकणी", "manipuri": "মৈতৈলোন্", "bodo": "बड़ो", "sanskrit": "संस्कृतम्",
}
TELUGU_ROMAN = "telugu_roman"   # a reply choice only: the planner never returns it
TEMPLATED = ("english", "telugu", TELUGU_ROMAN)
REPLIES = (*NAMES, TELUGU_ROMAN)


def is_templated(language: str) -> bool:
    return language in TEMPLATED


def western_digits(text: str) -> str:
    """१५ and ౧౫ become 15, so answers in any script get the same number checks."""
    return "".join(str(unicodedata.digit(c)) if not c.isascii() and unicodedata.category(c) == "Nd" else c
                   for c in text)


def _numbers(text: str) -> list[str]:
    return sorted(re.findall(r"\d+(?:\.\d+)?", western_digits(text).replace(",", "")))


def translate(lines: list[str], language: str, models: llm.Models, meter: llm.Meter) -> list[str | None]:
    """
    Each line in the language, or None where it can't be trusted: the model failed, or a number
    changed. The caller keeps the English then, because a wrong figure is the worst outcome.
    """
    if not lines:
        return []
    sent = [{"role": "system", "content":
             f"Translate each string in the JSON array into {language}, in its usual script, in plain words "
             "a farmer would understand. Keep scheme names and every number unchanged, in digits 0-9. Keep the "
             'meaning exact; add nothing. Return {"lines": [...]} with the same number of strings, in order.'},
            {"role": "user", "content": json.dumps(lines, ensure_ascii=False)}]
    try:
        got = json.loads(models.call("compose", sent, meter, json_mode=True).text).get("lines")
    except (llm.LLMError, ValueError, AttributeError):
        return [None] * len(lines)
    if not isinstance(got, list) or len(got) != len(lines):
        return [None] * len(lines)
    return [western_digits(new) if isinstance(new, str) and new.strip() and _numbers(new) == _numbers(old) else None
            for old, new in zip(lines, got)]
