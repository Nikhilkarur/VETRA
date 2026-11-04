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


# What a script settles, by Unicode range. Some scripts have one language, so the model can't be
# wrong about them. Others are shared, so the model chooses among those, and the first is the fallback.
_SCRIPTS = (
    (0x0C00, 0x0C7F, ("telugu",)), (0x0B80, 0x0BFF, ("tamil",)), (0x0C80, 0x0CFF, ("kannada",)),
    (0x0D00, 0x0D7F, ("malayalam",)), (0x0A80, 0x0AFF, ("gujarati",)), (0x0B00, 0x0B7F, ("odia",)),
    (0x0A00, 0x0A7F, ("punjabi",)), (0x1C50, 0x1C7F, ("santali",)),
    (0x0900, 0x097F, ("hindi", "marathi", "nepali", "maithili", "sanskrit", "konkani", "dogri", "bodo", "kashmiri", "sindhi")),
    (0x0980, 0x09FF, ("bengali", "assamese", "manipuri")),
    (0x0600, 0x06FF, ("urdu", "kashmiri", "sindhi")),
)


def is_templated(language: str) -> bool:
    return language in TEMPLATED


def settle(named: str, question: str) -> str:
    """
    The question's language, from the planner's word and what the script rules in or out. A third
    is enough, because people mix in English words: "rabi cut-off ఎప్పుడు" is still a Telugu question.
    """
    letters = [ord(c) for c in question if unicodedata.category(c)[0] in "LM"]
    for low, high, family in _SCRIPTS:
        if sum(low <= c <= high for c in letters) * 3 > len(letters):
            return named if named in family else family[0]
    return named


def western_digits(text: str) -> str:
    """१५ and ౧౫ become 15, so answers in any script get the same number checks."""
    return "".join(str(unicodedata.digit(c)) if not c.isascii() and unicodedata.category(c) == "Nd" else c
                   for c in text)


def _numbers(text: str) -> list[str]:
    return sorted(re.findall(r"\d+(?:\.\d+)?", western_digits(text).replace(",", "")))


_saved: dict[tuple[str, str], str] = {}   # the same facts come up again and again
_MAX_SAVED = 5000


def translate(lines: list[str], language: str, models: llm.Models, meter: llm.Meter) -> list[str | None]:
    """
    Each line in the language, or None where it can't be trusted: the model failed, or a number
    changed. The caller keeps the English then, because a wrong figure is the worst outcome.
    A line translated once isn't paid for again.
    """
    needed = list(dict.fromkeys(line for line in lines if (language, line) not in _saved))
    if needed:
        if len(_saved) + len(needed) > _MAX_SAVED:
            _saved.clear()
        for line, new in zip(needed, _ask(needed, language, models, meter)):
            if new:
                _saved[language, line] = new
    return [_saved.get((language, line)) for line in lines]


def _ask(lines: list[str], language: str, models: llm.Models, meter: llm.Meter) -> list[str | None]:
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
