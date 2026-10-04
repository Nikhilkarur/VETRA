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
   conversation so far, and answers with one word. It handles what keywords and
   embeddings can't: "can i file an rti about my crop insurance claim" is RTI,
   though most of its words are farming; "what is the time limit" after a
   mango-insurance question is agriculture. 270/274 batched on the earlier sets;
   31/32 single-call on a set frozen before it first ran.
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
import os
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


@dataclass(frozen=True)
class Route:
    domain: str   # a key of domains.DOMAINS, or "other"
    method: str   # "llm" | "embedding"


def _labels() -> list[str]:
    return [*domains.DOMAINS, OTHER]


def router_prompt(batch: bool = False) -> str:
    topics = "\n".join(f"- {d.name}: {d.router_hint}" for d in domains.DOMAINS.values())
    names = ", ".join(domains.DOMAINS)
    answer = (f'You will get several numbered messages, each from a different conversation. Route each '
              f'one independently. Return JSON mapping every number to one word ({names} or {OTHER}), '
              f'e.g. {{"1": "{OTHER}", "2": "{next(iter(domains.DOMAINS))}"}}. Output only the JSON.'
              if batch else f"Answer with exactly one word: {names} or {OTHER}.")
    return f"""You route questions for an Andhra Pradesh government help assistant. Each topic below has its own document collection. Decide which collection should answer the user's LATEST message.

Topics:
{topics}
- {OTHER}: anything else -- other government services (ration cards, pensions, certificates, land registration, taxes, budgets, salaries, health schemes, electricity bills), general knowledge, chit-chat.

Rules:
- Decide by what the user wants to know or do, not by single words. Words like "appeal", "complain", "information", "right", "penalty" or "time limit" appear in every topic.
- If the user wants to use the Right to Information Act -- to get records or information from any office, even about a farm scheme -- it is rti.
- A short follow-up that depends on an earlier question ("can tenants get it", "what is the time limit", "and for cotton?") belongs to the earlier question's topic, unless it clearly changes the subject.
- Answer {OTHER} only when the question is clearly outside every topic above. If one of the topics could reasonably answer it, choose that topic: a wrongly refused question gets no answer at all.

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
    """One word from the first router model that isn't rate-limited. Raises if none answers."""
    from groq import RateLimitError

    import query_expansion as QX

    error: Exception | None = None
    models = [m for m in _models() if QX.available(m)] or list(_models())
    for model in models:
        def make():
            label = _parse(_complete(model, router_prompt(), _message(question, history), 10))
            if label is None:
                raise ValueError(f"{model} replied without a label")
            return label
        try:
            # Cached per model when LLM_CACHE_DIR is set (the evaluations), so a run
            # cut short by the daily limit resumes instead of starting over.
            return QX.cached_as(f"route@{model.split('/')[-1]}", "router",
                                _message(question, history), make)
        except RateLimitError as exc:
            QX.note_limit(model, exc)
            error = exc   # this model's daily or per-minute limit: try the next one
    raise error or RuntimeError("no router model configured")


def route_batch(items: list[dict], model: str) -> list[str | None]:
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
    return [_parse(str(answers.get(str(n), ""))) for n in range(1, len(items) + 1)]


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


def route(question: str, history: list[dict] | None = None) -> Route:
    """The domain for the latest message, given earlier turns [{"q", "domain"?}, ...]."""
    try:
        return Route(route_llm(question, history), "llm")
    except Exception as exc:
        print(f"  (router LLM unavailable, routing by similarity: {exc})", file=sys.stderr)
    # The embedding router can't read the conversation. For a follow-up, staying in
    # the previous turn's domain is the safer guess than routing "and for cotton?" alone.
    last = next((t.get("domain") for t in reversed(history or []) if t.get("domain")), None)
    if last in domains.DOMAINS:
        return Route(last, "embedding")
    return Route(route_embedding(question), "embedding")


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
