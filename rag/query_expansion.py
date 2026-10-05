"""
LLM query expansion beyond HyDE -- the candidates tested in eval/experiments.py.

HyDE (rag/retrieve.py) writes ONE passage in the documents' style. These variants
ask for other things a search engine can use, all built from the domain's own
description in rag/domains.py (nothing here is specific to RTI or agriculture):

  rewrites()       {"topic", "queries", "keywords"} in one call:
                   topic    -- the name of the rule/scheme/section asked about
                               (step-back: "who checks fake pesticides" ->
                               "powers of insecticide inspectors")
                   queries  -- three formal rephrasings (multi-query / RAG-Fusion)
                   keywords -- terms likely to appear verbatim in the answer
                               (query expansion for keyword search, Query2doc-style)
  multi_hyde()     three hypothetical passages in different document styles
                   (an Act or order, a guideline, an FAQ or manual) -- the HyDE
                   paper averages several samples; here each style is searched.
  select_documents()  an agent step: the model reads the list of documents in
                   the collection and names the ones likely to hold the answer.

Every result is cached on disk when LLM_CACHE_DIR is set (the experiments set it
to eval/cache/), keyed by domain and question, because gpt-oss drifts even at
temperature 0 and a comparison must use identical text.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import domains

ROOT = Path(__file__).resolve().parent.parent
# Groq's free tier allows 200,000 tokens a DAY per model. gpt-oss spends hundreds of
# hidden reasoning tokens even on "low"; qwen3.8-27b answers these short structured
# requests without reasoning tokens (about 60 completion tokens for three queries),
# so it can run the expansion experiments without starving the HyDE and answer models.
MODEL = "qwen/qwen3.8-27b"


# ------------------------------------------------------------------ plumbing

def _model(kind: str) -> str:
    if kind == "docselect":
        return os.environ.get("AGENT_MODEL", MODEL)
    return os.environ.get("QX_MODEL", MODEL)


def _cache_file(kind: str) -> Path | None:
    """One cache file per technique AND model: outputs of different models never mix."""
    folder = os.environ.get("LLM_CACHE_DIR")
    return Path(folder) / f"{kind}@{_model(kind).split('/')[-1]}.json" if folder else None


_memory: dict[str, object] = {}  # this process's results, so the live app never asks twice


def _cached(kind: str, domain: str, key: str, make):
    return _cached_in(_cache_file(kind), kind, domain, key, make)


def cached_as(stem: str, domain: str, key: str, make):
    """_cached with the cache file named by the caller (eval/cache/<stem>.json)."""
    folder = os.environ.get("LLM_CACHE_DIR")
    return _cached_in(Path(folder) / f"{stem}.json" if folder else None, stem, domain, key, make)


def _cached_in(file: Path | None, kind: str, domain: str, key: str, make):
    k = f"{domain}|{key}"
    if f"{kind}|{k}" in _memory:
        return _memory[f"{kind}|{k}"]
    store = {}
    if file and file.exists():
        store = json.loads(file.read_text(encoding="utf-8"))
    if k in store:
        return store[k]
    value = make()
    if value is not None:   # failures are not remembered: the next question retries
        _memory[f"{kind}|{k}"] = value
    if value is not None and file:
        store = json.loads(file.read_text(encoding="utf-8")) if file.exists() else {}
        store[k] = value
        file.write_text(json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8")
    return value


FALLBACK = "openai/gpt-oss-20b"  # live use only, when MODEL has hit its daily limit

# Circuit breaker for Groq's DAILY limits: a model that reported one is skipped for a
# while, so later questions go straight to the fallback instead of each waiting on
# retries first (a live question once spent 26 s in search doing exactly that).
_resting: dict[str, float] = {}
REST_SECONDS = 600


def available(model: str) -> bool:
    import time

    return _resting.get(model, 0.0) <= time.time()


def note_limit(model: str, exc: Exception) -> None:
    """Remember a daily-limit refusal (a per-minute one passes on its own)."""
    import time

    text = str(exc)
    if "per day" in text or "(TPD)" in text or "(RPD)" in text:
        _resting[model] = time.time() + REST_SECONDS


def _ask(system: str, user: str, kind: str) -> str:
    """The technique's model; in live use, the fallback model if that one is rate-limited."""
    from groq import RateLimitError

    models = [_model(kind)]
    if not os.environ.get("LLM_CACHE_DIR"):   # experiments never switch models silently
        models = [m for m in (*models, FALLBACK) if available(m)] or models
    for n, model in enumerate(models):
        try:
            return _chat(system, user, model)
        except RateLimitError as exc:
            note_limit(model, exc)
            if n == len(models) - 1:
                raise
    return ""


def _chat(system: str, user: str, model: str) -> str:
    from dotenv import load_dotenv
    from groq import Groq

    load_dotenv(ROOT / ".env")
    extra = {"reasoning_effort": "low"} if model.startswith("openai/gpt-oss") else {"reasoning_effort": "none"}
    # Experiments wait out per-minute limits; a live question must not sit on a
    # limit -- it moves to the fallback model instead.
    reply = Groq(max_retries=6 if os.environ.get("LLM_CACHE_DIR") else 0).chat.completions.create(
        model=model, temperature=0,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        **extra,
    )
    return reply.choices[0].message.content or ""


def _json(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _about(d: domains.Domain) -> str:
    return d.router_hint or d.blurb


def _avoid(d: domains.Domain) -> str:
    if not d.common_terms:
        return ""
    names = ", ".join(f'"{t}"' for t in d.common_terms)
    return (f" Never use the words {names}: every document in this collection contains them, "
            "so they match everything and find nothing.")


# ------------------------------------------------------------------ techniques

def rewrites(question: str, domain: str = "rti") -> dict | None:
    d = domains.get(domain)
    system = f"""You help a search engine find the passage that answers a citizen's question in a collection of official documents about: {_about(d)}

Return JSON with exactly these keys:
"topic": the name of the specific rule, scheme, section, procedure or office the question is about, in the formal wording such documents use (at most 12 words).
"queries": a list of three different search queries a passage answering the question would match. Rephrase everyday words into the formal vocabulary of Acts, government orders and scheme guidelines. Keep every name, number, crop and scheme name from the question.
"keywords": a list of 5 to 10 short words or phrases likely to appear word-for-word in the answering passage.

Do not answer the question.{_avoid(d)} Output only the JSON."""

    def make():
        for _ in range(2):
            parsed = _json(_ask(system, question, "rewrites"))
            if parsed and isinstance(parsed.get("queries"), list):
                return {"topic": str(parsed.get("topic") or ""),
                        "queries": [str(x) for x in parsed["queries"]][:3],
                        "keywords": [str(x) for x in parsed.get("keywords") or []][:10]}
        return None
    try:
        return _cached("rewrites", domain, question, make)
    except Exception as exc:
        print(f"  (rewrites unavailable: {exc})", file=sys.stderr)
        return None


def multi_hyde(question: str, domain: str = "rti") -> list[str] | None:
    d = domains.get(domain)
    system = f"""The question below is about: {_about(d)}

Write three short passages (40 to 80 words each) that would answer it, each in the style of a different kind of official document:
1. a section of an Act, a statutory rule or a government order;
2. a scheme's operational guideline or a department circular;
3. an answer in an official FAQ or a department's citizen information manual.

Plain prose, formal drafting vocabulary. No headings, markdown, dates or reference numbers. Keep every name, number, crop and scheme name from the question. Accuracy of details does not matter; the vocabulary must match real documents.{_avoid(d)}

Return JSON: {{"passages": ["...", "...", "..."]}}. Output only the JSON."""

    def make():
        for _ in range(2):
            parsed = _json(_ask(system, question, "multihyde"))
            if parsed and isinstance(parsed.get("passages"), list) and parsed["passages"]:
                return [str(x) for x in parsed["passages"]][:3]
        return None
    try:
        return _cached("multihyde", domain, question, make)
    except Exception as exc:
        print(f"  (multi-HyDE unavailable: {exc})", file=sys.stderr)
        return None


# ------------------------------------------------------------------ agent step: pick documents

def unit_key(meta: dict) -> str:
    """A selectable unit: a whole document, or one section of a document split by section (the Act)."""
    return f"{meta.get('file')}#s{meta['section']}" if meta.get("section") else str(meta.get("file"))


def catalog(domain: str) -> list[tuple[str, str]]:
    """(unit key, label) for every selectable unit in the collection, in index order."""
    from retrieve import _corpus

    seen: dict[str, str] = {}
    _, texts, metas, _ = _corpus(domain)
    for text, m in zip(texts, metas):
        key = unit_key(m)
        if m.get("file") and key not in seen:
            label = " ".join(str(m.get("title") or m["file"]).split())[:160]
            if m.get("section"):
                # A section number alone means little to a model (qwen put "appeal"
                # questions on sections 14-15). The source label carries the
                # section's heading: "RTI Act 2005, Section 19: Appeal".
                label = " ".join(str(m.get("source") or label).split())[:160]
            if m.get("in_force") == "no":
                label += " [replaced, not in force]"
            seen[key] = label
    return list(seen.items())


def selection_prompt(domain: str, most: int = 3, batch: bool = False) -> str:
    """The document-selection instructions with the catalog; batch=True asks about numbered questions."""
    d = domains.get(domain)
    # Codes, not plain numbers: with "37. RTI ACT, section 20" in the list, both
    # gpt-oss-120b and qwen answered "20" (the section) for a penalty question and
    # so picked list item 20. "D37" can't be mistaken for a section number.
    listing = "\n".join(f"D{n}: {label}" for n, (_, label) in enumerate(catalog(domain), 1))
    task = (f"For EACH numbered question, name the documents most likely to contain the passage that "
            f"answers it -- at most {most}, best first, by their codes. Treat every question independently."
            if batch else
            f"Given a citizen's question, name the documents most likely to contain the passage that "
            f"answers it -- at most {most}, best first, by their codes.")
    reply = ('{"answers": {"<question number>": ["D..", ...], ...}}' if batch else '{"docs": ["D..", ...]}')
    return f"""You are the first step of a search over a collection of official documents about: {_about(d)}

The collection holds exactly these documents (an Act is listed section by section):
{listing}

{task} Prefer the specific order, guideline or section for the scheme or rule asked about over a general manual. Return JSON: {reply}. Output only the JSON."""


def parse_codes(codes: list, docs: list[tuple[str, str]]) -> list[str]:
    """["D12", "D3"] -> the unit keys of catalog entries 12 and 3, without repeats."""
    picked = []
    for code in codes:
        m = re.fullmatch(r"\s*D?(\d+)\s*", str(code))
        if m and 1 <= int(m.group(1)) <= len(docs) and docs[int(m.group(1)) - 1][0] not in picked:
            picked.append(docs[int(m.group(1)) - 1][0])
    return picked


def select_documents(question: str, domain: str = "rti", most: int = 3) -> list[str] | None:
    """The units (see unit_key) the model expects to hold the answer, at most `most`; None if unavailable."""
    docs = catalog(domain)
    system = selection_prompt(domain, most)

    def make():
        for _ in range(2):
            parsed = _json(_ask(system, question, "docselect"))
            if parsed and isinstance(parsed.get("docs"), list):
                return parse_codes(parsed["docs"], docs)[:most]
        return None
    try:
        return _cached("docselect", domain, question, make)
    except Exception as exc:
        print(f"  (document selection unavailable: {exc})", file=sys.stderr)
        return None


# ------------------------------------------------------------------ Telugu questions

TELUGU_SCRIPT = re.compile(r"[ఀ-౿]")


def to_english(question: str, domain: str = "rti") -> str:
    """
    A question written in Telugu script, translated to English for SEARCHING only.

    Every document is English, and the search side reads only English: keyword search
    keeps a-z/0-9 (Telugu letters vanish), bge-small-en and the MiniLM reranker are
    English models. Before this step a Telugu question was found only through HyDE and
    the rewrite, which happen to write English. The answer model still receives the
    original question, so it still replies in Telugu. Other questions (English, or
    Telugu typed in English letters) are returned unchanged, with no LLM call.
    """
    if not TELUGU_SCRIPT.search(question):
        return question
    system = ("Translate the user's question into plain English. Keep its meaning exactly. "
              "Write scheme, office, place and crop names in their usual English spelling "
              "(for example అన్నదాత సుఖీభవ -> Annadata Sukhibhava, కౌలు రైతు -> tenant farmer, "
              "ఆర్టీఐ -> RTI). Keep every number. Do not answer the question. "
              "Output only the English question, on one line.")

    def make():
        text = " ".join(_ask(system, question, "translate").split())
        return text or None
    try:
        return _cached("translate", domain, question, make) or question
    except Exception as exc:
        print(f"  (translation unavailable, searching with the original question: {exc})", file=sys.stderr)
        return question
