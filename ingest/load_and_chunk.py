"""
Turn ingest/documents/ into ingest/chunks.json.

Two things changed from the first version, both measured on eval/demo_questions.json:

1. Chunks are counted in TOKENS with the embedding model's own tokenizer, not in
   characters. The old 1000-character chunks overflowed MiniLM's 256-token window
   27% of the time and were silently truncated. Here a chunk can never exceed the
   window.

2. The RTI Act is split by SECTION before chunking. Most citizen questions are
   answered by one section of the Act (s.6 how to apply, s.7 time limits, s.19
   appeals...), so a chunk never straddles two sections, and every Act chunk
   knows which section it came from -- which also gives the answer a precise
   citation ("RTI Act, Section 19: Appeal").

Chunks are still sentence-aligned with a token overlap. Nothing semantic, no LLM.

We tested prefixing each chunk with its document or section title before
embedding (contextual chunking). On this corpus it made retrieval WORSE: every
government order's title contains "Right to Information Act", so the prefix made
chunks look alike. The section title is stored as metadata for citations only.

Run:  python ingest/load_and_chunk.py
      python ingest/load_and_chunk.py --preview
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / "documents"
MANIFEST = ROOT / "corpus_manifest.json"
OUT = ROOT / "chunks.json"

# Must match the embedding model in build_index.py; its tokenizer sizes the chunks.
MODEL_NAME = "BAAI/bge-small-en-v1.5"   # 512-token window
CHUNK_TOKENS = 350                      # leaves headroom under 512
OVERLAP_TOKENS = 60

# The RTI Act's 31 section titles. Each was checked to appear verbatim in the
# extracted Act text (as the gazette's marginal notes).
ACT_SECTIONS = {
    1: "Short title, extent and commencement", 2: "Definitions",
    3: "Right to information", 4: "Obligations of public authorities",
    5: "Designation of Public Information Officers",
    6: "Request for obtaining information", 7: "Disposal of request",
    8: "Exemption from disclosure of information",
    9: "Grounds for rejection to access in certain cases", 10: "Severability",
    11: "Third party information", 12: "Constitution of Central Information Commission",
    13: "Term of office and conditions of service",
    14: "Removal of Chief Information Commissioner or Information Commissioner",
    15: "Constitution of State Information Commission",
    16: "Term of office and conditions of service",
    17: "Removal of State Chief Information Commissioner or State Information Commissioner",
    18: "Powers and functions of Information Commissions", 19: "Appeal",
    20: "Penalties", 21: "Protection of action taken in good faith",
    22: "Act to have overriding effect", 23: "Bar of jurisdiction of courts",
    24: "Act not to apply to certain organisations", 25: "Monitoring and reporting",
    26: "Appropriate Government to prepare programmes",
    27: "Power to make rules by appropriate Government",
    28: "Power to make rules by competent authority", 29: "Laying of rules",
    30: "Power to remove difficulties", 31: "Repeal",
}

_SENTENCE = re.compile(r"(?<=[.;:])\s+(?=[A-Z(\"“0-9])")
_ORDER = re.compile(r"G\.?\s?O\.?\s*(Ms|Rt)\.?\s*No\.?\s*:?\s*(\d+)", re.I)

# The only document captured from a live web page rather than a dated order.
PORTAL_PAGE_SOURCE = "AP State Portal, 'Instruction on RTI' page (captured 4 Sep 2026 -- most current source)"


def order_number(text: str) -> str | None:
    """'G.O.Ms.No. 454 Dated ...' -> 'Ms.454'."""
    m = _ORDER.search(text)
    return f"{m.group(1).title()}.{m.group(2)}" if m else None


def amended_orders(title: str, text: str) -> list[str]:
    """
    Orders that this order amends.

    AP amending orders say "Amendment to ..." in their abstract and cite the order
    they change under "Read the following". A fee rule is incomplete without its
    amendments -- G.O.545 changed the inspection fee set by G.O.454 -- so
    rag/retrieve.py uses this link to bring amendments into the answer's context.
    """
    if not re.search(r"amendment", text[:700], re.I):
        return []
    own = order_number(title)
    refs = {f"{a.title()}.{b}" for a, b in _ORDER.findall(text[:1500])}
    return sorted(refs - {own})


def extract_text(path: Path) -> str:
    if path.suffix == ".txt":
        return path.read_text(encoding="utf-8")
    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def clean(text: str) -> str:
    """Whitespace only. Extraction artifacts inside words are left alone on purpose."""
    text = text.replace("\xa0", " ")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def split_act(text: str) -> list[tuple[int, str]]:
    """
    Cut the RTI Act at its section starts: "6. (1) A person, who desires...".

    Sections are found strictly in order (1, then 2 after it, then 3...), which
    stops list items like "2. Border Security Force" in the schedule from being
    mistaken for section 2. The pattern tolerates "12. ( 1)" -- an extraction
    artifact puts a space inside the parenthesis for several sections.
    """
    starts, pos = [], 0
    for n in range(1, len(ACT_SECTIONS) + 1):
        m = re.search(rf"(?<![\d(]){n}\.\s*(?:\(\s*1\s*\)|[A-Z“\"])", text[pos:])
        if not m:
            raise ValueError(f"could not find section {n} of the RTI Act")
        starts.append(pos + m.start())
        pos = starts[-1] + 3
    starts.append(len(text))
    return [(n, text[starts[n - 1] : starts[n]]) for n in range(1, len(ACT_SECTIONS) + 1)]


def chunk_tokens(text: str, count, size: int, overlap: int) -> list[str]:
    """Sentence-aligned chunks of at most `size` tokens, carrying ~`overlap` tokens forward."""
    sentences: list[str] = []
    for sentence in _SENTENCE.split(text):
        if count(sentence) <= size:
            sentences.append(sentence)
            continue
        # A single "sentence" longer than a chunk -- usually a flattened table.
        # Split it on words so nothing is ever truncated by the encoder.
        words: list[str] = []
        for word in sentence.split():
            words.append(word)
            if count(" ".join(words)) >= size:
                sentences.append(" ".join(words))
                words = []
        if words:
            sentences.append(" ".join(words))

    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for sentence in sentences:
        n = count(sentence)
        if current and current_tokens + n > size:
            chunks.append(" ".join(current))
            tail: list[str] = []
            tail_tokens = 0
            for prev in reversed(current):
                t = count(prev)
                if tail_tokens + t > overlap:
                    break
                tail.insert(0, prev)
                tail_tokens += t
            current, current_tokens = tail, tail_tokens
        current.append(sentence)
        current_tokens += n
    if current:
        chunks.append(" ".join(current))
    return chunks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="print samples, write nothing")
    args = parser.parse_args()

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    count = lambda s: len(tokenizer.encode(s, add_special_tokens=False))

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    items: list[dict] = []

    texts = {}
    for entry in manifest["files"]:
        texts[entry["file"]] = clean(extract_text(DOCS_DIR / entry["file"]))
    present = {order_number(e["title"]) for e in manifest["files"]} - {None}

    for entry in manifest["files"]:
        path = DOCS_DIR / entry["file"]
        text = texts[entry["file"]]
        if len(text) < 100:
            print(f"  skipped (no text): {entry['file']}")
            continue

        order = order_number(entry["title"]) or ""
        amends = [o for o in amended_orders(entry["title"], text) if o in present]

        if entry["title"].strip() == "RTI ACT":
            units = [
                (f"RTI Act 2005, Section {n}: {ACT_SECTIONS[n]}", n, body)
                for n, body in split_act(text)
            ]
        elif entry["file"].endswith(".txt"):
            units = [(PORTAL_PAGE_SOURCE, None, text)]
        elif entry["department"].startswith("General Administration"):
            units = [(entry["title"], None, text)]
        else:
            # Name the department: these manuals list officers and phone numbers
            # that apply to that department only.
            units = [(f"{entry['title']} [{entry['department']} department]", None, text)]

        before = len(items)
        for source, section, body in units:
            pieces = chunk_tokens(body, count, CHUNK_TOKENS, OVERLAP_TOKENS)
            for i, piece in enumerate(pieces):
                items.append(
                    {
                        "id": f"{path.stem}::{section or 0}::{i}",
                        "text": piece,
                        "source": source,
                        "title": entry["title"],
                        "department": entry["department"],
                        "section": section,
                        "order": order,
                        "amends": ",".join(amends),
                        "source_url": entry["source_url"],
                        "file": entry["file"],
                        "chunk_index": i,
                        "chunk_count": len(pieces),
                    }
                )
        print(f"  {len(items) - before:>3} chunks  {entry['title'][:62]}")

    tokens = [count(i["text"]) for i in items]
    print(f"\n{len(items)} chunks | tokens per chunk: max {max(tokens)}, "
          f"median {sorted(tokens)[len(tokens)//2]} | window {tokenizer.model_max_length}")

    if args.preview:
        for item in [i for i in items if i["section"] in (6, 19)][:2]:
            print(f"\n--- {item['source']}\n{item['text'][:400]} ...")
        return 0

    OUT.write_text(
        json.dumps(
            {"model": MODEL_NAME, "chunk_tokens": CHUNK_TOKENS, "overlap_tokens": OVERLAP_TOKENS,
             "chunks": len(items), "items": items},
            indent=1, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
