"""
Interactive chat over the AP RTI corpus.

Loads the embedding model and the Chroma collection once, then loops -- so
questions after the first are fast (the ~5s startup is the model loading, not
the search).

It remembers the last few questions and answers, so follow-ups like "what if i
still dont get it" work: the follow-up is rewritten into a standalone question
before searching (see answer.py). Type /new to start a fresh conversation.

Run:  python rag/chat.py
      python rag/chat.py --k 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from answer import ask
from retrieve import TOP_K, _collection, _corpus, _model

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

BANNER = """\
AP RTI assistant
Ask about the Right to Information Act as it applies in Andhra Pradesh.
Answers come only from the 41 documents published by the AP government.

  /new       start a new conversation (forget earlier questions)
  /sources   show retrieved passages for the next question
  /k N       change how many passages are retrieved
  /quit      exit
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=TOP_K)
    args = parser.parse_args()

    k = args.k
    show_context = False
    history: list[dict] = []

    print(BANNER)
    print("loading ...", end=" ", flush=True)
    _model()          # warm the embedding model
    _corpus()         # load chunk texts and build the keyword (BM25) index
    count = _collection().count()
    print(f"ready ({count} chunks indexed, top-{k})\n")

    while True:
        try:
            question = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return 0

        if not question:
            continue

        if question in ("/quit", "/exit", "/q"):
            print("bye")
            return 0

        if question == "/new":
            history.clear()
            print("  new conversation\n")
            continue

        if question == "/sources":
            show_context = not show_context
            print(f"  showing retrieved passages: {show_context}\n")
            continue

        if question.startswith("/k "):
            try:
                k = int(question.split()[1])
                print(f"  retrieving top-{k}\n")
            except (IndexError, ValueError):
                print("  usage: /k 5\n")
            continue

        if question.startswith("/"):
            print("  unknown command. try /new, /sources, /k N, /quit\n")
            continue

        try:
            answer = ask(question, k, show_context, history=history)
            history.append({"q": question, "a": answer})
        except Exception as exc:
            # A network blip or a retired model should not kill the session.
            print(f"  error: {exc}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
