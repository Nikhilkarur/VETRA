"""Pull lines that state a rate or amount from the held PDFs, grouped by aspect, with no model, so a person reads only those.
Skips documents that already have exact records. Run: python tools/rate_lines.py STATE [STATE ...]   writes eval/cache/hand/rates_STATE.jsonl"""
import json
import re
import sys
from pathlib import Path

import pypdf

ROOT = Path(__file__).resolve().parent.parent
RATE = re.compile(r"(Rs\.?\s?[\d,]+|₹\s?[\d,]+|INR\s?[\d,]+|\d+(\.\d+)?\s?(%|per\s?cent)|subsid)", re.I)
MONEY = re.compile(r"(Rs\.?\s?[\d,]+|₹\s?[\d,]+|INR\s?[\d,]+|\d+(\.\d+)?\s?(%|per\s?cent))", re.I)
ASK = re.compile(r"per\s+(hectare|ha\b|acre|litre|unit|family|month|year|farmer|beneficiary|quintal|kg|animal|cow|goat)|subsid|incentive|assistance|pension|loan|interest|duty|tax|fee", re.I)
BUDGET = re.compile(r"crore|allocat|lakh\s+(farmers|families|beneficiar|hectare|acres)", re.I)


def used(topic: str) -> set:
    urls = set()
    for store in ("numbers", "dates", "rules"):
        path = ROOT / "knowledge" / topic / f"{store}.jsonl"
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    urls.add(str((json.loads(line).get("source") or {}).get("url")))
    return urls


def lines(path: Path):
    for number, page in enumerate(pypdf.PdfReader(str(path)).pages, 1):
        text = re.sub(r"\s+", " ", page.extract_text() or "")
        for sentence in re.split(r"(?<=[.;:])\s+(?=[A-Z0-9(])", text):
            if MONEY.search(sentence) and ASK.search(sentence) and not BUDGET.search(sentence) and 30 < len(sentence) < 420:
                yield number, sentence


def main() -> None:
    for state in sys.argv[1:]:
        out = ROOT / "eval" / "cache" / "hand" / f"rates_{state}.jsonl"
        with out.open("w", encoding="utf-8") as f:
            for topic in ("agriculture", "finance"):
                folder = ROOT / "documents" / topic / state
                done = used(topic)
                for e in json.loads((folder / "manifest.json").read_text(encoding="utf-8")):
                    if str(e.get("source_url") or e.get("url")) in done or not str(e.get("file", "")).lower().endswith(".pdf"):
                        continue
                    seen = set()
                    try:
                        for page, sentence in lines(folder / e["file"]):
                            if sentence not in seen:  # policy notes print each page twice
                                seen.add(sentence)
                                f.write(json.dumps({"topic": topic, "doc": e["title"][:80], "file": e["file"], "page": page, "line": sentence}, ensure_ascii=False) + "\n")
                    except Exception as exc:
                        print(e["file"], type(exc).__name__, flush=True)
                    print(state, e["file"][:40], len(seen), flush=True)


if __name__ == "__main__":
    main()
