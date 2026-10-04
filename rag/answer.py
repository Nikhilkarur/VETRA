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
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

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

SYSTEM_PROMPT = """\
You are an assistant that answers questions about the Right to Information Act
2005 as it applies in Andhra Pradesh, for ordinary citizens.

Answer ONLY from the numbered context passages provided. They come from the AP
government's own published documents: the RTI Act itself (labelled by section),
AP government orders and fee rules implementing it, and departmental Section
4(1)(b) manuals.

Rules:
- If the context does not contain the answer, say so plainly. Do not fill the
  gap from general knowledge -- a confident wrong answer about a legal right is
  worse than "the documents I have don't cover this".
- If the passages answer only part of the question, answer that part and say
  what they don't show. Never call something "the only" ground, option or right,
  and never say something is "not permitted", unless a passage says so -- a
  missing passage is not evidence that a rule doesn't exist.
- Copy every amount, time limit and number exactly as the passage states it.
  Do not combine, convert or re-express figures from different clauses.
- Cite the passages you used by their number, like [2] or [3][5]. When a passage
  is a section of the Act, name the section too, e.g. "Section 19 [2]". Cite a
  passage only for what that passage itself says -- check the section label
  before citing it.
- When someone asks what to do because a request was refused, ignored, delayed
  or answered badly, give EVERY remedy the passages contain -- e.g. first appeal,
  second appeal, complaint to the Information Commission -- each with its time
  limit and who it goes to. Lead with the appeal route if a passage describes it;
  do not offer just one remedy when the passages show several.
- Quote the Act's wording for anything about rights, deadlines or fees.
- The Act speaks of "Central" and "State" Public Information Officers. For
  Andhra Pradesh departments the relevant officer is the State one.
- Write plainly, for someone with no legal training. Keep it short.
- The question may be a follow-up. Earlier turns, if shown, are only there to
  help you understand what the question refers to. Take every fact from the
  numbered passages -- never from an earlier answer.
- The AP fee rules and orders here date from 2005-2011, so amounts or procedures
  may have changed since. Say so briefly when an answer gives a fee or a contact.

Three traps in these documents:
- AMENDMENTS. Some orders amend earlier ones (the source label says so). Where an
  amendment changes a rule, give the amended version, and mention it was amended.
- WHO HOLDS AN OFFICE. Government orders name officials as of the order's date.
  Never say someone "currently" holds a post unless the source is the AP State
  Portal page marked as the most current source. Otherwise say who was appointed,
  by which order and when, and that it may have changed.
- DEPARTMENT CONTACTS. Department manuals list officers, phone numbers and
  addresses for THAT department only (named in the source label). Give them only
  if the question is about that department. Never offer one department's officer
  as the contact for another department or for "any office".

Cite with plain square brackets like [2] -- no other citation markup.
"""


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

CONDENSE_PROMPT = """You rewrite the latest message in a chat about the Right to Information Act in Andhra Pradesh into one standalone question.

The question you write will be searched on its own, WITHOUT the conversation. So replace every vague reference -- "it", "that", "this", "they", "still", "too", "next", "what about", "and if" -- with the specific thing it refers to in the earlier conversation. If the message is about the user's own situation ("what if i am ...", "what if i was ...") it is asking about the TOPIC being discussed (a fee, an appeal, a deadline) -- name that topic in the question. Keep the user's plain wording otherwise. Leave the message unchanged only if it is already fully clear with no earlier context. Do not add "Right to Information Act" or "Andhra Pradesh" unless the user said them. Do not answer it.

Examples (different conversations from the one you will get):
- Earlier the user asked how to file an RTI application. Latest: "how long will it take" -> How long will it take to get a reply to an RTI application?
- Earlier the user asked about the deadline for a first appeal. Latest: "what if i was in hospital" -> Can I file the first appeal after the deadline if I was in hospital?
- Earlier the user asked whether they can get records older than 20 years. Latest: "what about cabinet papers?" -> Can I get cabinet papers?
- Earlier the user's RTI was refused and they asked what to do. Latest: "and if that fails too" -> What can I do if the first appeal against the refusal also fails?
- Earlier the user asked about fees. Latest: "who do i send the application to" -> Who do I send the application to? (already clear -- unchanged)

Output only the question, on one line."""


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


def standalone_question(question: str, history: list[dict] | None) -> str:
    """The question rewritten to stand alone, using earlier turns. Unchanged if no history."""
    turns = _recent(history)
    if not turns:
        return question
    messages = [
        {"role": "system", "content": CONDENSE_PROMPT},
        {"role": "user", "content": f"Earlier conversation:\n{format_history(turns, 300)}\n\n"
                                    f"Latest message: {question}"},
    ]
    try:
        from groq import Groq, RateLimitError

        client = Groq(max_retries=0)  # never sit waiting on a rate limit here
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
        print(f"  (couldn't rewrite the follow-up, searching with it plus the last question: {exc})",
              file=sys.stderr)
    # Fallback that still carries the topic: the last question plus the new one.
    return f"{turns[-1]['q']} {question}"


class MissingKey(RuntimeError):
    """No GROQ_API_KEY in the environment or .env."""


def answer_question(question: str, k: int = TOP_K, hyde: bool = True,
                    history: list[dict] | None = None) -> dict:
    """
    Retrieve, then answer. Returns everything a caller might display:
    answer, standalone (the question as searched), hits (the numbered passages),
    passage (the HyDE search text or None), context, model actually used, and
    timings in seconds.

    history: earlier turns, oldest first, as [{"q": question, "a": answer}, ...].
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

    started = time.perf_counter()
    standalone = standalone_question(question, history)
    hits, passage = retrieve_with_trace(standalone, k, hyde)
    searched = time.perf_counter()
    context = build_context(hits)

    earlier = format_history(history)
    prompt = f"Context passages:\n\n{context}\n\n"
    if earlier:
        prompt += ("Earlier in this conversation (to understand the question only -- "
                   f"not a source of facts):\n{earlier}\n\n")
    prompt += f"Question: {question}"
    if standalone != question:
        prompt += f"\n(In context, this means: {standalone})"

    model = os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    response, used = _complete(Groq(api_key=key, max_retries=3), model, messages)
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
        "search_s": searched - started,
        "answer_s": done - searched,
    }


def ask(question: str, k: int = TOP_K, show_context: bool = False, hyde: bool = True,
        history: list[dict] | None = None) -> str:
    """Answer a question and print it, with sources, for the terminal."""
    try:
        result = answer_question(question, k, hyde, history)
    except MissingKey as exc:
        print(exc)
        sys.exit(1)

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
    return result["answer"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--k", type=int, default=TOP_K)
    parser.add_argument("--show-context", action="store_true")
    parser.add_argument("--no-hyde", action="store_true", help="search with the question only")
    args = parser.parse_args()
    ask(args.question, args.k, args.show_context, not args.no_hyde)
    return 0


if __name__ == "__main__":
    sys.exit(main())
