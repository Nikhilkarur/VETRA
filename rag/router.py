"""
Pick the domain whose documents should answer a question -- before any search.

    route("is rti free for BPL families")                 -> rti
    route("pink bollworm destroyed my cotton, will insurance pay") -> agriculture
    route("how do i apply for a new ration card")          -> other

"other" means no domain covers the topic (ration cards, pensions, budgets, chit-chat).
The caller says so instead of searching -- an answer built from the wrong documents
is worse than "I can't help with that here".

Two routers, scored by eval/router_eval.py on eval/router_questions.json + 71 real
FAQ questions + every retrieval-eval question. PROTOTYPE: only the embedding router
has been scored so far (228/274, 83% -- it never says "other" and leans towards
agriculture, the bigger collection); the LLM router is not yet measured or wired in.

1. LLM (default). gpt-oss-20b reads a one-line description of each domain
   (router_hint in rag/domains.py) and the conversation so far, and answers with
   one word. It handles what keywords and embeddings can't: "can i file an rti
   about my crop insurance claim" is RTI, though most of its words are farming;
   "what is the time limit" after a mango-insurance question is agriculture.
2. Embedding (fallback, no network). Compares the question with each domain's own
   chunks; the domain with the closest passages wins. It never says "other" and
   can't see earlier turns, so it is only used when the LLM call fails.

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
ROUTER_MODEL = "openai/gpt-oss-20b"  # one word out; the small model is enough
MAX_HISTORY = 3                       # earlier questions shown to the router


@dataclass(frozen=True)
class Route:
    domain: str   # a key of domains.DOMAINS, or "other"
    method: str   # "llm" | "embedding"


def _labels() -> list[str]:
    return [*domains.DOMAINS, OTHER]


def router_prompt() -> str:
    topics = "\n".join(f"- {d.name}: {d.router_hint}" for d in domains.DOMAINS.values())
    names = ", ".join(domains.DOMAINS)
    return f"""You route questions for an Andhra Pradesh government help assistant. Each topic below has its own document collection. Decide which collection should answer the user's LATEST message.

Topics:
{topics}
- {OTHER}: anything else -- other government services (ration cards, pensions, certificates, land registration, taxes, budgets, salaries, health schemes, electricity bills), general knowledge, chit-chat.

Rules:
- Decide by what the user wants to know or do, not by single words. Words like "appeal", "complain", "information", "right", "penalty" or "time limit" appear in every topic.
- If the user wants to use the Right to Information Act -- to get records or information from any office, even about a farm scheme -- it is rti.
- A short follow-up that depends on an earlier question ("can tenants get it", "what is the time limit", "and for cotton?") belongs to the earlier question's topic, unless it clearly changes the subject.
- If the topic is not listed, answer {OTHER}. Do not stretch a topic to cover it.

Answer with exactly one word: {names} or {OTHER}."""


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


def route_llm(question: str, history: list[dict] | None = None) -> str:
    """One word from gpt-oss-20b. Raises if the call fails or the reply has no label."""
    from dotenv import load_dotenv
    from groq import Groq

    load_dotenv(ROOT / ".env")
    earlier = _history_lines(history)
    user = (f"Earlier questions in this conversation (oldest first, with the topic used):\n"
            f"{earlier}\n\nLatest message: {question}") if earlier else f"Latest message: {question}"
    reply = Groq(max_retries=2).chat.completions.create(
        model=os.environ.get("ROUTER_MODEL", ROUTER_MODEL),
        temperature=0,
        reasoning_effort="low",
        messages=[{"role": "system", "content": router_prompt()},
                  {"role": "user", "content": user}],
    )
    label = _parse(reply.choices[0].message.content)
    if label is None:
        raise ValueError(f"router reply had no label: {reply.choices[0].message.content!r}")
    return label


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
