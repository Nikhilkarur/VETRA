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
      python ingest/load_and_chunk.py --domain agriculture

Agriculture (added 2026-10-04) reuses the same token chunking. What differs:
- Documents come from ingest/incoming/agriculture/manifest.json (collect.py format).
- Five large documents are indexed only on the pages a farmer's question can be
  answered from (AGRI_PAGES): G.O.Ms.80 alone is 864 pages, 817 of them sowing
  calendars and village lists that would swamp every search.
- Amendment links come from the manifest's curated "amends" field instead of
  being guessed from the text, and each chunk carries "in_force", so a replaced
  scheme (YSR Rythu Bharosa) is labelled NOT IN FORCE where the model sees it.
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
sys.path.insert(0, str(ROOT.parent / "rag"))
import domains  # noqa: E402  (rag/domains.py: per-domain paths and prompts)

# Set from the chosen domain in main().
DOCS_DIR = ROOT / "documents"
MANIFEST = ROOT / "corpus_manifest.json"
OUT = ROOT / "chunks.json"

# Agriculture: pages to index (1-based, inclusive) for documents whose remaining
# pages are tables no citizen question is answered from. Checked page by page.
AGRI_PAGES = {
    "g-o-ms-no-80-": (1, 47, "pp.48-864: sowing calendars, CCE plans, village notification lists"),
    "g-o-ms-no-81-": (1, 32, "pp.33-118: weather-index term sheets per district and crop"),
    "g-o-ms-no-98-": (1, 23, "pp.24-89: weather-index term sheets per district"),
    "mission-for-integrated-development-of-horticulture": (
        1, 115, "pp.116-327: polyhouse/cold-room engineering specifications and formats"),
    "operational-guidelines-of-per-drop-more-crop": (
        1, 42, "pp.43-78: bill-of-quantity tables and reporting formats"),
}

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


def extract_text(path: Path, pages: tuple[int, int] | None = None) -> str:
    if path.suffix == ".txt":
        return path.read_text(encoding="utf-8")
    from pypdf import PdfReader

    reader = PdfReader(path)
    first, last = (pages[0] - 1, pages[1]) if pages else (0, len(reader.pages))
    return "\n".join(page.extract_text() or "" for page in reader.pages[first:last])


# ---------------------------------------------------------------- agriculture

_GO = re.compile(r"G\.?\s?O\.?\s*(Ms|Rt)?\.?\s*No\.?\s*:?\s*(\d+)", re.I)
_YEAR = re.compile(r"\b(19|20)\d{2}\b")
_WORDS = re.compile(r"[a-z]+")


def agri_key(entry: dict) -> str:
    """A unique order key: 'Ms.80/2024' for G.O.s (numbers repeat across years), else the file stem."""
    m = _GO.search(entry.get("number") or "")
    year = (entry.get("date") or "")[:4]
    if m and year:
        return f"{(m.group(1) or 'GO').title()}.{m.group(2)}/{year}"
    return Path(entry["file"]).stem


def agri_label(entry: dict) -> str:
    """How an order is named in 'included because it amends ...' notes."""
    m = _GO.search(entry.get("number") or "")
    year = (entry.get("date") or "")[:4]
    if m:
        return f"G.O.{(m.group(1) or '').title()}{'.' if m.group(1) else ''}No.{m.group(2)}" + (f" ({year})" if year else "")
    return entry["title"][:60]


def resolve_amends(entry: dict, entries: list[dict]) -> list[str]:
    """
    Turn the manifest's free-text 'amends' list into order keys of documents we hold.

    'G.O.Ms.No.80 (2024)' matches by number and year; 'Seeds (Control) Order, 1983'
    matches the document whose title contains most of its words.
    """
    keys = []
    for ref in entry.get("amends") or []:
        m, y = _GO.search(ref), _YEAR.search(ref)
        if m and y:
            want = f"{(m.group(1) or 'GO').title()}.{m.group(2)}/{y.group(0)}"
            hit = [e for e in entries if agri_key(e) == want]
        else:
            # By title -- only among documents that are NOT G.O.s: a reference to a
            # G.O. always cites its number, and G.O. titles quote scheme names that
            # would otherwise match ("PM Kisan ... Operational Guidelines" in G.O.Ms.33).
            words = {w for w in _WORDS.findall(ref.lower()) if len(w) > 2} - {"the", "and", "para"}
            hit = [e for e in entries if e is not entry and words
                   and not _GO.search(e.get("number") or "")
                   and len(words & set(_WORDS.findall(e["title"].lower()))) / len(words) >= 0.75]
        keys += [agri_key(e) for e in hit[:1]]
    return keys


def agri_source(entry: dict) -> str:
    """The label the answering model sees: what, who, when -- and whether it still applies."""
    who = "central government" if entry["department"] == "central" else f"{entry['department']} department"
    label = f"{entry['title']} [{who}" + (f", {entry['date']}" if entry.get("date") else "") + "]"
    if (entry.get("in_force") or "").lower().startswith("no"):
        label = f"NOT IN FORCE ({entry['in_force']}) -- {label}"
    return label


def agriculture_units(count) -> list[dict]:
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    items: list[dict] = []
    for entry in entries:
        path = DOCS_DIR / entry["file"]
        pages = next((v[:2] for k, v in AGRI_PAGES.items() if entry["file"].startswith(k)), None)
        text = clean(extract_text(path, pages))
        if len(text) < 100:
            print(f"  skipped (no text -- scan, needs OCR): {entry['file']}")
            continue
        source = agri_source(entry)
        pieces = chunk_tokens(text, count, CHUNK_TOKENS, OVERLAP_TOKENS)
        for i, piece in enumerate(pieces):
            items.append({
                "id": f"{path.stem}::0::{i}",
                "text": piece,
                "source": source,
                "title": entry["title"],
                "department": entry["department"],
                "section": None,
                "order": agri_key(entry),
                "order_label": agri_label(entry),
                "amends": ",".join(resolve_amends(entry, entries)),
                "in_force": (entry.get("in_force") or "unknown").split()[0].strip(",;-").lower(),
                "date": entry.get("date") or "",
                "source_url": entry["source_url"],
                "file": entry["file"],
                "chunk_index": i,
                "chunk_count": len(pieces),
            })
        note = f"  (pp.{pages[0]}-{pages[1]} only)" if pages else ""
        print(f"  {len(pieces):>4} chunks  {entry['title'][:62]}{note}")
    return items


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
    parser.add_argument("--domain", default="rti", choices=list(domains.DOMAINS))
    args = parser.parse_args()

    global DOCS_DIR, MANIFEST, OUT
    domain = domains.get(args.domain)
    DOCS_DIR, MANIFEST, OUT = domain.docs_dir, domain.manifest, domain.chunks

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    count = lambda s: len(tokenizer.encode(s, add_special_tokens=False))

    if args.domain == "agriculture":
        return write(agriculture_units(count), tokenizer, args.preview)

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

    return write(items, tokenizer, args.preview)


def write(items: list[dict], tokenizer, preview: bool) -> int:
    count = lambda s: len(tokenizer.encode(s, add_special_tokens=False))
    tokens = [count(i["text"]) for i in items]
    print(f"\n{len(items)} chunks | tokens per chunk: max {max(tokens)}, "
          f"median {sorted(tokens)[len(tokens)//2]} | window {tokenizer.model_max_length}")

    if preview:
        sample = [i for i in items if i["section"] in (6, 19)][:2] or items[:2]
        for item in sample:
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
