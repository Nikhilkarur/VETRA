"""
Ask a question: retrieve the top-10 chunks (plus any amendment chunks), send them
to Groq, print the answer.

Two calls go over the network, both to Groq: a small model writes the search
passage used by HyDE (see rag/retrieve.py), and a larger model writes the
answer. Embeddings, the vector store and keyword search are all local.

Setup:  put GROQ_API_KEY=... in a .env file at the project root
        (get one at https://console.groq.com)

Run:  python rag/answer.py "how do I file an RTI application in Andhra Pradesh?"
      python rag/answer.py "what is the fee?" --show-context
      python rag/answer.py "what is the fee?" --no-hyde     # no search-passage call
      python rag/answer.py "can tenant farmers get annadata sukhibhava" --domain agriculture

By default (--domain auto) the question is first sent to rag/router.py, which picks
the domain whose documents should answer it, or declines it as outside them.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

import domains
from retrieve import TOP_K, retrieve_with_trace

# Windows consoles default to cp1252, which cannot encode characters the model
# routinely emits (narrow no-break space, en-dashes, rupee sign). Without this
# a perfectly good answer dies with UnicodeEncodeError on the way to the screen.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

# Groq rotates its lineup. Checked 2026-09-04: this account has NO Llama chat
# models (the llama-prompt-guard entries are safety classifiers, not chat), so
# the brief's "a Llama model" is not currently available. Reachable chat models
# were: openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.8-27b,
# qwen/qwen3.6-27b, groq/compound, groq/compound-mini, allam-2-7b.
# Override with GROQ_MODEL in .env. To re-check what your key can reach:
#   python -c "from groq import Groq; [print(m.id) for m in Groq().models.list().data]"
DEFAULT_MODEL = "openai/gpt-oss-120b"

# The answer rules (SYSTEM prompt) and the follow-up rewrite (CONDENSE prompt)
# are per domain and live in rag/domains.py. RTI's were moved there verbatim.


def build_context(hits: list[dict]) -> str:
    """Number each passage and label its source, so the model can cite precisely."""
    blocks = []
    for n, hit in enumerate(hits, 1):
        note = f" -- included because it {hit['added_because']}" if hit.get("added_because") else ""
        blocks.append(f"[{n}] Source: {hit['source']}{note}\n    {hit['text']}")
    return "\n\n".join(blocks)


FALLBACK_MODEL = "openai/gpt-oss-20b"


def _complete(client, model: str, messages: list[dict]):
    """
    One chat completion, surviving Groq's free-tier limits.

    gpt-oss-120b is capped at 8,000 tokens per minute, and one answer with its
    context uses roughly 3,000-4,000 -- so two quick questions in a row can hit
    the cap. The SDK first retries on its own (max_retries), honouring Groq's
    "try again in N seconds". If the model is still limited, the smaller
    gpt-oss-20b has its own separate quota, and a slightly weaker answer beats a
    crash in the middle of a demo.
    """
    from groq import RateLimitError

    effort = os.environ.get("ANSWER_REASONING", "medium")  # low | medium | high
    try:
        return client.chat.completions.create(
            model=model, temperature=0.1, reasoning_effort=effort, messages=messages
        ), model
    except RateLimitError:
        if model == FALLBACK_MODEL:
            raise
        return (
            client.chat.completions.create(
                model=FALLBACK_MODEL, temperature=0.1, reasoning_effort=effort, messages=messages
            ),
            FALLBACK_MODEL,
        )


def tidy_citations(answer: str) -> str:
    """gpt-oss sometimes cites as 【2†L1-L4】; show plain [2] instead."""
    return re.sub(r"【\s*(\d+)[^】]*】", r"[\1]", answer)


# ------------------------------------------------------------------ memory
#
# Follow-ups like "what if i still dont get it" mean nothing on their own, and
# searching with them retrieves nothing useful. So when there is history:
#   1. a small model rewrites the follow-up into a standalone question, and
#      THAT is what we search with (the standard "condense question" step);
#   2. the answer model sees a short summary of earlier turns -- only to
#      understand the question. Facts must still come from the passages, never
#      from earlier answers.

# 120b, not 20b: on "what if my family belongs to bpl" after a fee question, 20b
# (at low AND medium effort) only fixed the spelling, and the white-card fee rule
# ranked 43rd; 120b wrote "Can I get a fee exemption ... if my family belongs to
# BPL?" and the rule ranked 1st. ~600 tokens, ~1 s. It shares 120b's per-minute
# quota with the answer, so if it is rate-limited we drop to 20b rather than wait.
CONDENSE_MODEL = "openai/gpt-oss-120b"
CONDENSE_FALLBACK = "openai/gpt-oss-20b"
MAX_TURNS = 3  # earlier turns kept; each adds ~200 tokens to the answer prompt



_TABLE_RULE = re.compile(r"\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?")


def _plain(text: str, limit: int) -> str:
    """
    Earlier answer as plain sentences: no citation markers, markdown or table
    syntax, cut to `limit` characters.

    The formatting matters more than it looks. A fee answer containing a
    markdown table reached the rewrite step as "| Authority level | Fee |
    |-----|-----| | Village ... ", and with that in its input gpt-oss-120b
    rewrote "what if my family belongs to bpl" WITHOUT mentioning fees -- the
    white-card fee rule then ranked 43rd. Given the same content as plain
    sentences, it wrote "Is there a fee exemption for RTI applications if my
    family belongs to BPL?".
    """
    text = re.sub(r"\[\d+(?:\s*\([^)\]]*\))?\]", "", text)   # citation markers
    parts = []
    for line in text.splitlines():
        line = line.strip()
        if not line or _TABLE_RULE.fullmatch(line):             # blank / |---|---|
            continue
        if line.startswith("|") and line.endswith("|"):          # table row -> "a, b;"
            cells = [c.strip() for c in line.strip("|").split("|")]
            line = ", ".join(c for c in cells if c) + ";"
        line = re.sub(r"^(#{1,6}|[-*•‑]|\d+[.)])\s+", "", line)  # headings, bullets, numbers
        parts.append(line)
    text = " ".join(" ".join(parts).replace("*", "").split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " ..."


def _recent(history: list[dict] | None) -> list[dict]:
    return [t for t in (history or []) if t.get("q") and t.get("a")][-MAX_TURNS:]


def format_history(history: list[dict] | None, answer_chars: int = 600) -> str:
    return "\n".join(
        f"User: {_plain(t['q'], 300)}\nAssistant: {_plain(t['a'], answer_chars)}"
        for t in _recent(history)
    )


def standalone_question(question: str, history: list[dict] | None, domain: str = "rti",
                        fallback: bool = True) -> str | None:
    """
    The question rewritten to stand alone, using earlier turns. Unchanged if no history.
    If the rewrite call fails: the last question plus this one (good enough to search
    with), or None with fallback=False -- the router's second look at a follow-up must
    not mistake that stand-in for a real rewrite (it always reads as the old topic).
    """
    turns = _recent(history)
    if not turns:
        return question
    messages = [
        {"role": "system", "content": domains.get(domain).condense_prompt},
        {"role": "user", "content": f"Earlier conversation:\n{format_history(turns, 300)}\n\n"
                                    f"Latest message: {question}"},
    ]
    try:
        from dotenv import load_dotenv
        from groq import Groq, RateLimitError

        load_dotenv(ROOT / ".env")   # callers like the router's evaluation may not have yet
        # A live question never sits waiting on a rate limit here; the evaluations
        # (LLM_CACHE_DIR set) wait out per-minute limits, as the other LLM steps do.
        client = Groq(max_retries=4 if os.environ.get("LLM_CACHE_DIR") else 0)
        try:
            reply = client.chat.completions.create(
                model=CONDENSE_MODEL, temperature=0, reasoning_effort="low", messages=messages)
        except RateLimitError:
            reply = client.chat.completions.create(
                model=CONDENSE_FALLBACK, temperature=0, reasoning_effort="low", messages=messages)
        rewritten = " ".join((reply.choices[0].message.content or "").split())
        if rewritten:
            return rewritten
    except Exception as exc:
        if not fallback:
            print(f"  (couldn't rewrite the follow-up: {exc})", file=sys.stderr)
            return None
        print(f"  (couldn't rewrite the follow-up, searching with it plus the last question: {exc})",
              file=sys.stderr)
    if not fallback:
        return None
    # Fallback that still carries the topic: the last question plus the new one.
    return f"{turns[-1]['q']} {question}"


# The language the answer is written in. "auto" = the question's language; a Telugu
# question gets Telugu script whether it was typed in Telugu letters or English ones.
# The web page lets the reader pick another (its "Reply in" menu).
REPLY_LANGUAGES = ("auto", "english", "telugu", "telugu_roman")

_REPLY_RULE = {
    "english": "Write the answer in English.",
    "telugu": ("Write the answer in Telugu script (తెలుగు), even if the question was typed in "
               "English letters. Keep section numbers, order numbers, amounts, dates and scheme "
               "names exactly as the passages give them."),
    "telugu_roman": ("Write the answer in Telugu using English letters (romanized Telugu, the way "
                     "people type Telugu in chat messages), not Telugu script. Keep section numbers, "
                     "order numbers, amounts, dates and scheme names exactly as the passages give them."),
}


def reply_language(preference: str | None, language: str) -> str:
    """english / telugu / telugu_roman, from the reader's choice and the question's language."""
    if preference in _REPLY_RULE:
        return preference
    return "telugu" if language == "telugu" else "english"


class MissingKey(RuntimeError):
    """No GROQ_API_KEY in the environment or .env."""


def out_of_scope(buttons: bool = False, language: str = "english") -> str:
    """The reply to a question no domain covers (the router said "other"), in the reply language."""
    if language == "telugu":
        topics = "; ".join(d.topic_te for d in domains.DOMAINS.values())
        tail = ("ఇది వీటిలో ఒకదానికి సంబంధించినదైతే, క్రింద ఎంచుకోండి — ఆ పత్రాలలో వెతుకుతాను."
                if buttons else "ఇది వీటిలో ఒకదానికి సంబంధించినదైతే, ప్రశ్నను మరోలా అడగండి.")
        return ("నేను ఆంధ్రప్రదేశ్ ప్రభుత్వ అధికారిక పత్రాల ఆధారంగా ఈ అంశాలపై మాత్రమే సమాధానం "
                f"ఇవ్వగలను: {topics}. మీ ప్రశ్న వేరే విషయం గురించి ఉన్నట్టుంది, కాబట్టి ఊహించి "
                f"చెప్పను. {tail}")
    if language == "telugu_roman":
        topics = "; ".join(d.topic_te_roman for d in domains.DOMAINS.values())
        tail = ("Idi veetilo okadaniki sambandhinchinadaite, kinda enchukondi — aa patralalo vetukutanu."
                if buttons else "Idi veetilo okadaniki sambandhinchinadaite, prashnanu marola adagandi.")
        return ("Nenu Andhra Pradesh prabhutva adhikarika patrala adharanga ee amshalapai matrame "
                f"samadhanam ivvagalanu: {topics}. Mee prashna vere vishayam gurinchi unnattundi, "
                f"kabatti oohinchi cheppanu. {tail}")
    topics = " and ".join(f"{d.label} ({d.blurb.split('.')[0].removeprefix('Ask about ')})"
                          for d in domains.DOMAINS.values())
    tail = ("If it is about one of them, choose it below and I'll search those documents."
            if buttons else
            "If it is about one of them, rephrase the question, or start with --domain "
            + " / --domain ".join(domains.DOMAINS) + ".")
    return (f"I can only answer from official Andhra Pradesh government documents on {topics}. "
            f"Your question looks like it is about something else, so I won't guess. {tail}")


def answer_question(question: str, k: int = TOP_K, hyde: bool = True,
                    history: list[dict] | None = None, domain: str = "rti",
                    buttons: bool = False, reply: str = "auto",
                    language: str | None = None) -> dict:
    """
    Retrieve, then answer. Returns everything a caller might display:
    answer, standalone (the question as searched), hits (the numbered passages),
    passage (the HyDE search text or None), context, model actually used,
    domain (the one searched, or "other"), route ("llm" / "embedding" when the
    domain was chosen by the router, else None) and timings in seconds.

    history: earlier turns, oldest first, as [{"q": question, "a": answer}, ...];
    a turn may also carry "domain", which helps the router with follow-ups.
    domain="auto": the router (rag/router.py) picks the domain for this question, and
    names its language. reply: the answer's language (REPLY_LANGUAGES; "auto" follows
    the question). language: the question's language if already known ("telugu" /
    "english", e.g. from an earlier routing of the same question); with a fixed
    domain and no language given, only Telugu script is recognised.
    """
    from dotenv import load_dotenv
    from groq import Groq

    load_dotenv(ROOT / ".env")
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise MissingKey(
            "GROQ_API_KEY not set. Put it in a .env file at the project root:\n"
            "    GROQ_API_KEY=gsk_..."
        )

    from groq import APIStatusError

    import router

    started = time.perf_counter()
    route = None
    rewritten = None
    if domain == domains.AUTO:
        # A follow-up the router sends to "other" is rewritten with the conversation and
        # routed again (router.rescue_followup); the rewrite is then reused below.
        picked = router.route(
            question, history, rewrite=lambda q, h, d: standalone_question(q, h, d, fallback=False))
        route, language, rewritten = picked.method, picked.language, picked.standalone
        if picked.domain == router.OTHER:
            replying = reply_language(reply, language)
            return {"answer": out_of_scope(buttons, replying), "standalone": question, "hits": [],
                    "passage": None, "context": "", "model": None, "domain": router.OTHER,
                    "route": route, "language": language, "reply_language": replying,
                    "search_s": time.perf_counter() - started, "answer_s": 0.0}
        domain = picked.domain
    language = language if language in router.LANGUAGES else router.script_language(question)
    replying = reply_language(reply, language)
    standalone = rewritten or standalone_question(question, history, domain)
    # A Telugu question (either alphabet) -> English for the search steps only
    # (hyde=False means no search-time LLM call, so no translation either). The answer
    # model below still gets the original question, and is told the reply language.
    if hyde:
        import query_expansion

        standalone = query_expansion.to_english(standalone, domain, telugu=language == "telugu")
    hits, passage = retrieve_with_trace(standalone, k, hyde, domain)
    searched = time.perf_counter()
    earlier = format_history(history)
    model = os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
    client = Groq(api_key=key, max_retries=3)

    # Groq's free tier refuses any single request over 8,000 tokens a minute
    # (HTTP 413, "Request too large") -- no wait or retry helps. Agriculture's
    # chunks are long, and 10 passages plus 4 amendment additions plus the rules
    # once came to 8,025. So on a 413, drop the lowest-ranked passages and ask
    # again. A normal request is sent exactly as before.
    while True:
        context = build_context(hits)
        prompt = f"Context passages:\n\n{context}\n\n"
        if earlier:
            prompt += ("Earlier in this conversation (to understand the question only -- "
                       f"not a source of facts):\n{earlier}\n\n")
        prompt += f"Question: {question}"
        if standalone != question:
            prompt += f"\n(In context, this means: {standalone})"
        # Always say which language to answer in. Left to itself the model followed
        # the English line above, or guessed for Telugu typed in English letters
        # ("rti fee entha" came back in English; checked 2026-10-06).
        prompt += "\n\n" + _REPLY_RULE[replying]
        messages = [
            # {today}: agriculture's rules tell the model the date, so a 2024 order
            # is not described as "the current season" in 2026. RTI's prompt has no
            # placeholder and is sent unchanged.
            {"role": "system", "content": domains.get(domain).system_prompt.replace(
                "{today}", time.strftime("%d %B %Y"))},
            {"role": "user", "content": prompt},
        ]
        try:
            response, used = _complete(client, model, messages)
            break
        except APIStatusError as exc:
            if exc.status_code != 413 or len(hits) <= 6:
                raise
            hits = hits[:-3]  # amendment additions sit at the end, then the lowest ranks
    answer = tidy_citations(response.choices[0].message.content or "")
    done = time.perf_counter()
    if used != model:
        answer += f"\n\n(answered by {used}: {model} was rate-limited)"

    return {
        "answer": answer,
        "standalone": standalone,
        "hits": hits,
        "passage": passage,
        "context": context,
        "model": used,
        "domain": domain,
        "route": route,
        "language": language,
        "reply_language": replying,
        "search_s": searched - started,
        "answer_s": done - searched,
    }


def ask(question: str, k: int = TOP_K, show_context: bool = False, hyde: bool = True,
        history: list[dict] | None = None, domain: str = "rti", reply: str = "auto") -> dict:
    """Answer a question and print it, with sources, for the terminal. Returns the result."""
    try:
        result = answer_question(question, k, hyde, history, domain, reply=reply)
    except MissingKey as exc:
        print(exc)
        sys.exit(1)

    if domain == domains.AUTO:
        if result["domain"] in domains.DOMAINS:
            print(f"\n(searched the {domains.get(result['domain']).label} documents)")
        else:
            print(f"\n{result['answer']}\n")
            return result

    if result["standalone"] != question:
        print(f"\n(understood as: {result['standalone']})")

    if show_context:
        if result["passage"]:
            print("\n--- search passage (HyDE: used only to search, never sent to the answer model) ---")
            print(result["passage"])
        print(f"\n--- context ({len(result['hits'])} passages) ---\n{result['context']}\n--- end ---\n")

    print(f"\n{result['answer']}\n")
    print("-" * 66)
    print("Sources:")
    for n, hit in enumerate(result["hits"], 1):
        extra = "  (added: amendment)" if hit.get("added_because") else ""
        print(f"  [{n}] {hit['source'][:74]}{extra}")
    print(f"\n(search {result['search_s']:.1f}s, answer {result['answer_s']:.1f}s)")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--k", type=int, default=TOP_K)
    parser.add_argument("--show-context", action="store_true")
    parser.add_argument("--no-hyde", action="store_true", help="search with the question only")
    parser.add_argument("--domain", default=domains.AUTO, choices=[domains.AUTO, *domains.DOMAINS],
                        help="auto (default): the router picks RTI or agriculture for the question")
    parser.add_argument("--reply", default="auto", choices=REPLY_LANGUAGES,
                        help="answer language; auto (default) follows the question")
    args = parser.parse_args()
    ask(args.question, args.k, args.show_context, not args.no_hyde, domain=args.domain, reply=args.reply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
