"""
What citizens needed that we don't have yet: the collection to-do list.

A gap is recorded when a data type wasn't found for a state, or was found only in text.
No question text or personal data is kept: only the topic, state, type and subject.

Today gaps tell people what to download next. Later, a collector that searches the internet
and sends documents through data engineering plugs in as another handler, with no change
to the agent:

    class WebCollector:
        def report(self, gap: Gap) -> None: ...

Run:  python -m vetra.gaps            # most-needed first
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

FILE = Path(__file__).resolve().parent.parent / "data" / "gaps.jsonl"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


@dataclass(frozen=True)
class Gap:
    domain: str
    state: str          # a state's code, or "any" when the user didn't say
    data_type: str
    subject: str
    level: str          # no_data: nothing found. text_only: found only in text. web_only: found only on an official website, live.
    date: str


class GapHandler(Protocol):
    def report(self, gap: Gap) -> None: ...


class GapLog:
    """Appends to a file. A failure here must never cost the citizen an answer."""

    def __init__(self, path: Path = FILE):
        self.path = path

    def report(self, gap: Gap) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(gap), ensure_ascii=False) + "\n")
        except OSError as exc:
            print(f"  (couldn't record a gap: {exc})", file=sys.stderr)


def main() -> int:
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    if not FILE.exists():
        print("no gaps recorded yet")
        return 0
    rows = [json.loads(line) for line in FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    counts = Counter((r["domain"], r["state"], r["data_type"], r["level"], r["subject"].lower()) for r in rows)
    for (domain, state, data_type, level, subject), n in counts.most_common(40):
        print(f"{n:>4}  {domain:<12} {state:<4} {data_type:<14} {level:<10} {subject[:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
