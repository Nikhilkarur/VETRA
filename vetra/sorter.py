"""
The sorting layer: put what a document contains into the store it belongs to.

Run:  python -m vetra.sorter sort knowledge/inbox/some_order.jsonl
      python -m vetra.sorter manifest ingest/incoming/agriculture/manifest.json --domain agriculture --state AP
      python -m vetra.sorter stats

"sort" takes records written by a person (or, later, an extraction step), checks each one,
and files it. A bad record is reported and left out. Filing the same id again replaces it.

"manifest" reads the facts already recorded for each collected document: its date and
validity go to "documents", its amendments to "links".

A sorted inbox file is removed: the stores hold its records from then on, and two copies
would drift apart. A file with rejected records stays until it's fixed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from . import knowledge

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def file_records(records: list[dict], root: Path = knowledge.ROOT) -> tuple[int, list[str]]:
    """File the good records into their stores. Returns how many, and what was rejected."""
    rejected, by_file = [], {}
    for r in records:
        bad = knowledge.problems(r)
        if bad:
            rejected.append(f"{r.get('id', '?')}: {', '.join(bad)}")
            continue
        by_file.setdefault(root / r["domain"] / f"{r['store']}.jsonl", []).append(r)
    for path, rows in by_file.items():
        kept = {}
        if path.exists():
            kept = {json.loads(l)["id"]: json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()}
        kept.update({r["id"]: r for r in rows})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept.values()), encoding="utf-8")
    return sum(len(v) for v in by_file.values()), rejected


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def from_manifest(entries: list[dict], domain: str, state: str) -> list[dict]:
    """Validity and amendment records from a collection manifest. No model, no guessing."""
    out = []
    for e in entries:
        place = "IN" if e.get("department") == "central" else state
        source = {"doc": e["title"], "url": e.get("source_url"), "date": e.get("date") or None}
        state_of = (e.get("in_force") or "unknown").split()[0].strip(",;-").lower()
        status = {"yes": "in_force", "no": "not_in_force"}.get(state_of, "unknown")
        base = {"domain": domain, "jurisdiction": place, "source": source, "status": status,
                "legal_weight": e.get("doc_type"), "reviewed": False}
        if e.get("date"):
            out.append({**base, "id": f"doc-{_slug(e['file'])}", "store": "documents", "subject": e["title"],
                        "date": e["date"], "valid_from": e["date"],
                        "text": f"{e['title']}: issued {e['date']}; in force: {e.get('in_force') or 'unknown'}."})
        for target in e.get("amends") or []:
            out.append({**base, "id": f"link-{_slug(e['file'])}-{_slug(target)}", "store": "links",
                        "subject": target, "relation": "amends", "target": target,
                        "text": f"{e['title']} amends or replaces {target}."})
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["sort", "manifest", "stats"])
    parser.add_argument("path", nargs="?")
    parser.add_argument("--domain")
    parser.add_argument("--state")
    args = parser.parse_args()

    if args.command == "stats":
        for (domain, store), rows in sorted(knowledge.Knowledge().records.items()):
            places = sorted({r["jurisdiction"] for r in rows})
            print(f"{domain:<12} {store:<10} {len(rows):>4}  {', '.join(places)}")
        return 0
    if not args.path:
        parser.error("this command needs a path")
    if args.command == "manifest":
        if not (args.domain and args.state):
            parser.error("manifest needs --domain and --state")
        records = from_manifest(json.loads(Path(args.path).read_text(encoding="utf-8")), args.domain, args.state)
    else:
        records = [json.loads(l) for l in Path(args.path).read_text(encoding="utf-8").splitlines() if l.strip()]
    filed, rejected = file_records(records)
    print(f"filed {filed}, rejected {len(rejected)}")
    for line in rejected:
        print(f"  {line}")
    if args.command == "sort" and not rejected:
        Path(args.path).unlink()
    return 1 if rejected else 0


if __name__ == "__main__":
    sys.exit(main())
