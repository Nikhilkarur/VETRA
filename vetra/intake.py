"""
Add hand-collected documents for any state. No code changes, no LLM.

    1. Put the files in documents/<domain>/<STATE>/ (PDF or .txt). Use IN for central documents.
    2. List them in documents/<domain>/<STATE>/manifest.json. "template" writes a starter.
       "order" and "amends_orders" link an order's chunks to those it amends; both are optional.
       "read_as_scan": true reads every page by OCR, for fonts that swap letters but look fine.
    3. python -m vetra.intake build agriculture KA

This chunks each file, files its validity and amendments, and updates the search index.
Scans and garbled pages are read by vetra/scans.py, which marks figures it can't confirm.

    python -m vetra.intake template agriculture KA
    python -m vetra.intake check agriculture KA      # build without changing anything
    python -m vetra.intake status agriculture        # what we have, per state
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import jurisdictions, scans, sorter, text_index
from .domains import DOMAINS
from .knowledge import ROOT as KNOWLEDGE
from .knowledge import Knowledge

ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS = ROOT / "documents"
REQUIRED = ("title", "file", "source_url", "doc_type")
EXAMPLE = {"title": "G.O.Ms.No.12 Agriculture Dept Dt.01.06.2026 - State crop insurance notification", "file": "order-12.pdf",
           "source_url": "https://official-site.gov.in/order-12.pdf", "doc_type": "go", "department": "Agriculture",
           "date": "2026-06-01", "in_force": "yes", "order": "Ms.12/2026", "amends": [], "amends_orders": []}

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


@dataclass
class Report:
    chunks: list[dict] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)   # stops the build
    warnings: list[str] = field(default_factory=list)


def _chunker():
    """ingest/load_and_chunk.py's parts, so every state is chunked as agriculture was measured."""
    spec = importlib.util.spec_from_file_location("load_and_chunk", ROOT / "ingest" / "load_and_chunk.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(entries: list[dict], folder: Path, state: str, known_hashes: set[str] | None = None,
            counter=None, chunker=None) -> Report:
    """Check a manifest against its files, and chunk what's good. Changes nothing on disk."""
    report = Report()
    known = set(known_hashes or ())
    for n, e in enumerate(entries, 1):
        name = e.get("title") or e.get("file") or f"entry {n}"
        lacking = [k for k in REQUIRED if not e.get(k)]
        if lacking:
            report.problems.append(f"{name}: missing {', '.join(lacking)}")
            continue
        path = folder / e["file"]
        if not path.exists():
            report.problems.append(f"{name}: file not found: {e['file']}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        if digest in known:
            report.warnings.append(f"{name}: same file as one already taken, skipped")
            continue
        known.add(digest)
        if not e.get("date"):
            report.warnings.append(f"{name}: no date, so it can't be checked for validity")
        if not e.get("in_force"):
            report.warnings.append(f"{name}: in_force not set; it will be treated as unknown")
        reading = None
        if path.suffix.lower() == ".pdf":
            try:
                reading = scans.read(path, state, digest, force=bool(e.get("read_as_scan")))
            except FileNotFoundError as exc:
                report.warnings.append(f"{name}: {exc}; its good pages were kept")
            if reading:
                report.warnings.append(f"{name}: {reading.read_as_scan} of {reading.pages} pages read as a scan, "
                                       f"{reading.unclear} figures marked unclear")
        report.chunks += _chunks_for(e, path, state, digest, counter, chunker or _chunker(), reading)
        if not any(c["file"] == e["file"] for c in report.chunks):
            report.warnings.append(f"{name}: no text found (a scan?); needs OCR, not added")
    return report


def _chunks_for(e: dict, path: Path, state: str, digest: str, counter, chunker, reading=None) -> list[dict]:
    text = chunker.clean(reading.text if reading else chunker.extract_text(path))
    if len(text) < 100:
        return []
    count = counter or _token_counter(chunker)
    pieces = chunker.chunk_tokens(text, count, chunker.CHUNK_TOKENS, chunker.OVERLAP_TOKENS)
    who = "central government" if state == jurisdictions.CENTRAL else f"{e.get('department') or state} department"
    source = f"{e['title']} [{who}" + (f", {e['date']}" if e.get("date") else "") + "]"
    out, at = [], 0
    for i, piece in enumerate(pieces):
        at = text.find(piece, at)
        out.append({"id": f"{state}-{digest}::{i}", "text": piece, "source": source, "title": e["title"],
                    "department": e.get("department") or "", "jurisdiction": state,
                    "season": chunker.season_of(text, at) if at >= 0 else "",
                    "order": e.get("order") or "", "order_label": e.get("order") or "",
                    "amends": ",".join(e.get("amends_orders") or []),
                    "in_force": (e.get("in_force") or "unknown").split()[0].strip(",;-").lower(),
                    "date": e.get("date") or "", "source_url": e["source_url"], "file": e["file"],
                    "chunk_index": i, "chunk_count": len(pieces), "read_by": "scan" if reading else "text"})
    return out


def _token_counter(chunker):
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(chunker.MODEL_NAME)
    return lambda s: len(tokenizer.encode(s, add_special_tokens=False))


def _known_hashes(domain: str, state: str) -> set[str]:
    """Files already taken for other states, so the same PDF isn't filed twice."""
    taken = (re.match(r"([A-Z]{2})-([0-9a-f]{12})::", i["id"]) for i in text_index.corpus(domain))
    return {m.group(2) for m in taken if m and m.group(1) != state}


def build(domain: str, state: str, dry_run: bool = False) -> int:
    folder = DOCUMENTS / domain / state
    manifest = folder / "manifest.json"
    if not manifest.exists():
        print(f"no {manifest.relative_to(ROOT)}; run: python -m vetra.intake template {domain} {state}")
        return 1
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    report = prepare(entries, folder, state, _known_hashes(domain, state))
    for line in report.problems:
        print(f"  PROBLEM  {line}")
    for line in report.warnings:
        print(f"  warning  {line}")
    print(f"{len(entries)} documents, {len(report.chunks)} chunks")
    if report.problems:
        print("Nothing changed. Fix the problems and run it again.")
        return 1
    if dry_run:
        print("Check only: nothing changed.")
        return 0
    out = KNOWLEDGE / domain / "text" / f"{state}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"chunks": len(report.chunks), "items": report.chunks}, ensure_ascii=False, indent=1), encoding="utf-8")
    filed, rejected = sorter.file_records(sorter.from_manifest(entries, domain, state))
    print(f"filed {filed} document and link records; rejected {len(rejected)}")
    text_index.corpus.cache_clear()
    text_index.build(domain)
    return 0


def template(domain: str, state: str) -> int:
    folder = DOCUMENTS / domain / state
    folder.mkdir(parents=True, exist_ok=True)
    manifest = folder / "manifest.json"
    if manifest.exists():
        print(f"{manifest.relative_to(ROOT)} already exists")
        return 1
    manifest.write_text(json.dumps([EXAMPLE], indent=1), encoding="utf-8")
    print(f"wrote {manifest.relative_to(ROOT)}. Put the files beside it, replace the example, then run build.")
    return 0


def status(domain: str) -> int:
    kb = Knowledge()
    stores = sorted({s for (d, s) in kb.records if d == domain})
    print(f"{'place':<26}{'chunks':>8}" + "".join(f"{s:>11}" for s in stores))
    places = {i["jurisdiction"] for i in text_index.corpus(domain)}
    places |= {r["jurisdiction"] for (d, _), rows in kb.records.items() if d == domain for r in rows}
    for place in sorted(places):
        counts = [sum(1 for r in kb.records.get((domain, s), []) if r["jurisdiction"] == place) for s in stores]
        print(f"{jurisdictions.name(place)[:25]:<26}{text_index.chunks_in(domain, place):>8}" + "".join(f"{c:>11}" for c in counts))
    print(f"\n{len(jurisdictions.STATES) - len(places - {jurisdictions.CENTRAL})} of {len(jurisdictions.STATES)} states and UTs have nothing of their own yet.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["template", "check", "build", "status"])
    parser.add_argument("domain", choices=[d.name for d in DOMAINS.values() if not d.legacy])
    parser.add_argument("state", nargs="?")
    args = parser.parse_args()
    if args.command == "status":
        return status(args.domain)
    state = args.state and (jurisdictions.normalise(args.state) or (args.state.upper() if args.state.upper() == jurisdictions.CENTRAL else None))
    if not state:
        parser.error("give a state or UT code or name, or IN for central")
    if args.command == "template":
        return template(args.domain, state)
    return build(args.domain, state, dry_run=args.command == "check")


if __name__ == "__main__":
    sys.exit(main())
