"""
Pick the domain whose documents should answer a question -- before any search.

    route("is rti free for BPL families")                 -> rti
    route("pink bollworm destroyed my cotton, will insurance pay") -> agriculture
    route("how do i apply for a new ration card")          -> other

"other" means no domain covers the topic (ration cards, pensions, budgets, chit-chat).
The caller says so instead of searching -- an answer built from the wrong documents
is worse than "I can't help with that here".

Used by answer.answer_question(domain="auto"), the default of web.py, chat.py and
answer.py. Scored by eval/router_eval.py (eval/router_questions.json + 71 real FAQ
questions + every retrieval-eval question; docs/RETRIEVAL_EXPERIMENTS.md, section 5):

1. LLM (default). gpt-oss-20b (then qwen3.8-27b if it is rate-limited) reads a
   one-line description of each domain (router_hint in rag/domains.py) and the
   earlier questions, and answers with two words: the domain and the language of
   the question ("rti telugu"). It handles what keywords and embeddings can't: "can
   i file an rti about my crop insurance claim" is RTI, though most of its words are
   farming; "what is the time limit" after a mango-insurance question is agriculture.
   Two checks follow the call:
   - a follow-up sent to "other" is rewritten with the conversation (including the
     earlier answer) and routed again (rescue_followup): "what if i have a white
     ration card" after an RTI fee question was being declined;
   - a "telugu" label on a message made only of known English words is corrected
     to english (english_words_only).
2. Embedding (fallback, no network). Compares the question with each domain's own
   chunks; the domain with the closest passages wins. 228/274 (83%): it never says
   "other", leans towards agriculture (the bigger collection) and can't see earlier
   turns, so it is only used when no LLM answers.

Adding a domain to rag/domains.py with a router_hint is all the router needs.

Run:  python rag/router.py "my pm kisan money stopped who do i complain to"
      python rag/router.py "what is the fee" --embedding
"""

from __future__ import annotations

import argparse
import functools
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import domains  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OTHER = "other"
# Tried in order; the next one is used when a model hits Groq's free-tier limit
# (200,000 tokens per model per DAY -- the query rewrites and the router share
# qwen's, HyDE and the router share gpt-oss-20b's). ROUTER_MODEL=<id> pins one model.
ROUTER_MODELS = ("openai/gpt-oss-20b", "qwen/qwen3.8-27b")
MAX_HISTORY = 3                       # earlier questions shown to the router
# v2 (2026-10-06): the same call also names the language of the question, so Telugu
# typed in English letters ("rti fee entha") is recognised without an extra call.
# v3 (2026-10-06): prompt says a follow-up stays on the earlier topic even when it names
# something listed under "other", and the answer format no longer shows only "... telugu"
# (plain English was sometimes labelled telugu). route() also gets rescue_followup and
# the English-words check. Cached decisions are kept per version: v1 replies were one word.
ROUTER_VERSION = "v3"
LANGUAGES = ("english", "telugu")


@dataclass(frozen=True)
class Route:
    domain: str   # a key of domains.DOMAINS, or "other"
    method: str   # "llm" | "llm+rewrite" | "embedding"
    language: str = "english"   # "telugu" covers Telugu script and Telugu in English letters
    standalone: str | None = None   # the follow-up rewritten to stand alone, if routing needed it


def _labels() -> list[str]:
    return [*domains.DOMAINS, OTHER]


def router_prompt(batch: bool = False) -> str:
    topics = "\n".join(f"- {d.name}: {d.router_hint}" for d in domains.DOMAINS.values())
    names = ", ".join(domains.DOMAINS)
    first = next(iter(domains.DOMAINS))
    last = list(domains.DOMAINS)[-1]
    answer = (f'You will get several numbered messages, each from a different conversation. Route each '
              f'one independently. Return JSON mapping every number to two words, the topic ({names} or '
              f'{OTHER}) and the language (english or telugu), e.g. {{"1": "{OTHER} english", '
              f'"2": "{first} telugu"}}. Output only the JSON.'
              if batch else
              f'Answer with exactly two words: the topic ({names} or {OTHER}) and the language '
              f'(english or telugu), for example "{first} english" or "{last} telugu".')
    return f"""You route questions for an Andhra Pradesh government help assistant. Each topic below has its own document collection. Decide which collection should answer the user's LATEST message.

Topics:
{topics}
- {OTHER}: questions that are themselves about something else -- other government services (ration cards, pensions, certificates, land registration, taxes, budgets, salaries, health schemes, electricity bills), general knowledge, chit-chat.

Rules:
- Decide by what the user wants to know or do, not by single words. Words like "appeal", "complain", "information", "right", "penalty" or "time limit" appear in every topic.
- If the user wants to use the Right to Information Act -- to get records or information from any office, even about a farm scheme -- it is rti.
- A follow-up that depends on an earlier question ("can tenants get it", "what is the time limit", "and for cotton?") belongs to the earlier question's topic. This holds even when it mentions something listed under {OTHER} -- a ration card, a pension, a certificate, a land record -- because it asks how the earlier answer applies to the user's own situation. Choose {OTHER} for a follow-up only when it clearly starts a new subject that no longer depends on the earlier question.
- Answer {OTHER} only when the question is clearly outside every topic above. If one of the topics could reasonably answer it, choose that topic: a wrongly refused question gets no answer at all.
- Language: the language the latest message itself is written in -- not its topic, and not the language of earlier messages. telugu if it is in Telugu, written in Telugu script OR as Telugu words in English letters ("rti fee entha", "naa dabbulu raaledu", "panta bheema ela"); a Telugu sentence with English words in it (RTI, PM Kisan, MSP, subsidy) is still telugu. A message made of English words is english, however short or informal.

{answer}"""


def _history_lines(history: list[dict] | None) -> str:
    lines = []
    for turn in (history or [])[-MAX_HISTORY:]:
        if turn.get("q"):
            tag = f"[{turn['domain']}] " if turn.get("domain") else ""
            lines.append(f"- {tag}{' '.join(str(turn['q']).split())[:300]}")
    return "\n".join(lines)


def _parse(text: str) -> str | None:
    """First label word in the reply ("Agriculture." -> agriculture)."""
    import re

    for word in re.findall(r"[a-z]+", (text or "").lower()):
        if word in _labels():
            return word
    return None


def _parse_language(text: str) -> str | None:
    import re

    words = re.findall(r"[a-z]+", (text or "").lower())
    return next((w for w in words if w in LANGUAGES), None)


def script_language(text: str) -> str:
    """Without an LLM: telugu only if Telugu letters are present (misses Telugu in English letters)."""
    from query_expansion import TELUGU_SCRIPT

    return "telugu" if TELUGU_SCRIPT.search(text or "") else "english"


@functools.lru_cache(maxsize=1)
def english_words() -> frozenset[str]:
    """
    Words known to be English: every word in the indexed documents, plus the whole
    words of the embedding model's vocabulary (~22,500 common English words).
    Telugu typed in English letters always has words in neither ("entha", "undi",
    "cheyali"); checked on every romanized question in the test sets, 2026-10-06.
    """
    import json

    words: set[str] = set()
    for d in domains.DOMAINS.values():
        for item in json.loads(d.chunks.read_text(encoding="utf-8"))["items"]:
            words.update(re.findall(r"[a-z]+", f"{item['text']} {item.get('title') or ''}".lower()))
    try:
        from retrieve import _model   # already loaded for searching

        # isalpha() drops the "##ing"-style word pieces and keeps whole words.
        words.update(w for w in _model(next(iter(domains.DOMAINS))).tokenizer.get_vocab() if w.isalpha())
    except Exception as exc:  # document words alone still cover most questions
        print(f"  (embedding vocabulary unavailable for the language check: {exc})", file=sys.stderr)
    return frozenset(words)


def english_words_only(text: str) -> bool:
    """No Telugu letters, and every word is a known English word."""
    from query_expansion import TELUGU_SCRIPT

    words = re.findall(r"[a-z]+", (text or "").lower())
    return bool(words) and not TELUGU_SCRIPT.search(text) and all(w in english_words() for w in words)


def _checked_language(question: str, language: str) -> str:
    """
    The router LLM sometimes calls plain English "telugu" (2 of ~40 English questions
    in single calls on 2026-10-06, e.g. "i didnt get it, can i file an rti to find out
    why"), and the answer then comes back in Telugu. A message made only of known
    English words is English. Only telugu -> english is corrected, never the reverse.
    """
    return "english" if language == "telugu" and english_words_only(question) else language


def _message(question: str, history: list[dict] | None) -> str:
    earlier = _history_lines(history)
    return (f"Earlier questions in this conversation (oldest first, with the topic used):\n"
            f"{earlier}\n\nLatest message: {question}") if earlier else f"Latest message: {question}"


def _complete(model: str, system: str, user: str, tokens: int) -> str:
    from dotenv import load_dotenv
    from groq import Groq

    load_dotenv(ROOT / ".env")
    gpt_oss = model.startswith("openai/gpt-oss")
    # Evaluations wait out per-minute limits; a live question moves to the next model.
    reply = Groq(max_retries=4 if os.environ.get("LLM_CACHE_DIR") else 0).chat.completions.create(
        model=model,
        temperature=0,
        reasoning_effort="low" if gpt_oss else "none",
        # gpt-oss reasons before it answers, so it needs room for that too.
        max_completion_tokens=tokens + (1500 if gpt_oss else 0),
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return reply.choices[0].message.content or ""


def _models() -> tuple[str, ...]:
    return (os.environ["ROUTER_MODEL"],) if os.environ.get("ROUTER_MODEL") else ROUTER_MODELS


def route_llm(question: str, history: list[dict] | None = None) -> str:
    """The topic only (see route_llm_full)."""
    return route_llm_full(question, history)[0]


def route_llm_full(question: str, history: list[dict] | None = None) -> tuple[str, str]:
    """(topic, language) from the first router model that isn't rate-limited. Raises if none answers."""
    from groq import RateLimitError

    import query_expansion as QX

    error: Exception | None = None
    models = [m for m in _models() if QX.available(m)] or list(_models())
    for model in models:
        def make():
            text = _complete(model, router_prompt(), _message(question, history), 10)
            label = _parse(text)
            if label is None:
                raise ValueError(f"{model} replied without a label")
            return f"{label} {_parse_language(text) or script_language(question)}"
        try:
            # Cached per model when LLM_CACHE_DIR is set (the evaluations), so a run
            # cut short by the daily limit resumes instead of starting over.
            label, language = QX.cached_as(f"route-{ROUTER_VERSION}@{model.split('/')[-1]}", "router",
                                           _message(question, history), make).split()
            return label, _checked_language(question, language)
        except RateLimitError as exc:
            QX.note_limit(model, exc)
            error = exc   # this model's daily or per-minute limit: try the next one
    raise error or RuntimeError("no router model configured")


def route_batch(items: list[dict], model: str) -> list[tuple[str | None, str | None]]:
    """
    Evaluation only: route several {"q", "history"?} items in ONE call (the prompt is
    sent once). ~1/15 of the tokens of single calls; checked against single calls in
    eval/router_eval.py. Live questions always use route_llm().
    """
    user = "\n\n".join(f"{n}. {_message(it['q'], it.get('history'))}" for n, it in enumerate(items, 1))
    text = _complete(model, router_prompt(batch=True), user, 30 * len(items))
    import json
    import re

    match = re.search(r"\{.*\}", text, re.S)
    try:
        answers = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        answers = {}
    return [(_parse(str(answers.get(str(n), ""))), _parse_language(str(answers.get(str(n), ""))))
            for n in range(1, len(items) + 1)]


def domain_scores(question: str, n: int = 5) -> dict[str, float]:
    """Mean cosine similarity of the question to each domain's n closest chunks."""
    from retrieve import QUERY_PREFIX, _collection, _model

    scores = {}
    for name in domains.DOMAINS:
        vector = _model(name).encode([QUERY_PREFIX + question], normalize_embeddings=True).tolist()
        found = _collection(name).query(query_embeddings=vector, n_results=n, include=["distances"])
        distances = found["distances"][0]
        scores[name] = sum(1 - d for d in distances) / len(distances)
    return scores


def route_embedding(question: str) -> str:
    scores = domain_scores(question)
    return max(scores, key=scores.get)


def rescue_followup(question: str, history: list[dict] | None, rewrite) -> tuple[str, str] | None:
    """
    A follow-up the router sent to "other": rewrite it to stand alone using the
    conversation, and route the rewritten question. (domain, rewritten) if that names a
    domain, else None.

    The router reads only the earlier QUESTIONS, and gpt-oss-20b decides "what if i
    have a white ration card" after an RTI fee question is about ration cards --
    "That's other." -- whatever the prompt says (three prompt variants and medium
    reasoning all failed, 2026-10-06). The follow-up rewrite also reads the earlier
    ANSWER and writes "Can I get exemption from the RTI application fee if I have a
    white ration card?", which the router places at once. A real change of subject
    ("how do i apply for a new ration card") is rewritten unchanged and stays "other".
    """
    # The conversation's topic: the last turn that was answered from a domain (the
    # terminal chat also records declined turns, as "other").
    last = next((t["domain"] for t in reversed(history or []) if t.get("domain") in domains.DOMAINS), None)
    if last is None:
        return None
    try:
        standalone = rewrite(question, history, last)
        if not standalone or " ".join(standalone.split()).lower() == " ".join(question.split()).lower():
            return None
        label, _ = route_llm_full(standalone, None)
    except Exception as exc:
        print(f"  (couldn't re-route the follow-up: {exc})", file=sys.stderr)
        return None
    return (label, standalone) if label != OTHER else None


def route(question: str, history: list[dict] | None = None, rewrite=None) -> Route:
    """
    The domain for the latest message, given earlier turns [{"q", "a"?, "domain"?}, ...].
    rewrite(question, history, domain) -> standalone question: if given, a follow-up
    the router sends to "other" gets a second look (rescue_followup). It costs two
    more calls, and only in that case; a rescued question reuses its rewrite.
    """
    try:
        label, language = route_llm_full(question, history)
    except Exception as exc:
        print(f"  (router LLM unavailable, routing by similarity: {exc})", file=sys.stderr)
    else:
        if label == OTHER and history and rewrite:
            rescued = rescue_followup(question, history, rewrite)
            if rescued:
                return Route(rescued[0], "llm+rewrite", language, rescued[1])
        return Route(label, "llm", language)
    # Without an LLM, Telugu is recognised by its letters only.
    language = script_language(question)
    # The embedding router can't read the conversation. For a follow-up, staying in
    # the previous turn's domain is the safer guess than routing "and for cotton?" alone.
    last = next((t.get("domain") for t in reversed(history or []) if t.get("domain")), None)
    if last in domains.DOMAINS:
        return Route(last, "embedding", language)
    return Route(route_embedding(question), "embedding", language)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--embedding", action="store_true", help="similarity router only (no LLM)")
    args = parser.parse_args()
    if args.embedding:
        scores = domain_scores(args.question)
        print(max(scores, key=scores.get), {k: round(v, 3) for k, v in scores.items()})
    else:
        print(route(args.question))
    return 0


if __name__ == "__main__":
    sys.exit(main())
