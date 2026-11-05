"""Name downloaded orders from their own abstract, and drop routine ones (postings, court cases, fund releases), with no model.
A file with no readable text keeps its plain title; the build reads it by OCR. A dropped file stays on disk, out of the manifest.
Run: python tools/order_titles.py LIST.jsonl"""
import json
import re
import sys
from pathlib import Path

import pypdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pick_docs import NOT_POLICY  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ABSTRACT = re.compile(r"ABSTRACT\s*[:\-]?\s*(.{20,400}?)(?=\s(?:[A-Z&\s()\-.,]{12,}DEPARTMENT|G\.?O\.?\s?\(|Read|READ|Dated))", re.S)
DATED = re.compile(r"Dated\s*[:.]?\s*[^\d]{0,30}(\d{1,2})[./-](\d{1,2})[./-](\d{4})", re.I)


def abstract(text: str) -> str:
    flat = re.sub(r"\s+", " ", text)
    m = ABSTRACT.search(flat)
    if m:
        return m.group(1).strip(" -–")
    # OCR often loses the heading that ends an abstract; stop at "Orders" instead
    m = re.search(r"ABSTRACT\s*[»:\-]?\s*(.{20,300}?)\s*[-—–]*\s*Orders?\b", flat)
    return m.group(1).strip(" -–—") if m else ""


def scanned_first_page(pdf: Path) -> str:
    """A scan's first page as the build's OCR read it (documents/.scans), or nothing if not read yet."""
    import hashlib
    saved = ROOT / "documents" / ".scans" / f"{hashlib.sha256(pdf.read_bytes()).hexdigest()[:12]}.json"
    if not saved.exists():
        return ""
    return (json.loads(saved.read_text(encoding="utf-8")).get("0") or [""])[0]


def main() -> None:
    wanted = [json.loads(l) for l in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if l.strip()]
    named = dropped = 0
    for folder in {(d["topic"], d["state"]) for d in wanted}:
        path = ROOT / "documents" / folder[0] / folder[1] / "manifest.json"
        entries = json.loads(path.read_text(encoding="utf-8"))
        files = {d["file"] for d in wanted if (d["topic"], d["state"]) == folder}
        keep = []
        for e in entries:
            if e["file"] not in files:
                keep.append(e)
                continue
            try:
                first = pypdf.PdfReader(str(path.parent / e["file"])).pages[0].extract_text() or ""
            except Exception:
                first = ""
            if len(first.strip()) < 40:
                first = scanned_first_page(path.parent / e["file"])
            subject = abstract(first)
            if subject and NOT_POLICY.search(subject):
                dropped += 1
                continue
            if subject and subject[:40] not in e["title"]:
                e["title"] = f"{e['title']}: {subject[:170]}"
                named += 1
            when = DATED.search(first)
            if when and not e.get("date"):
                e["date"] = f"{when.group(3)}-{int(when.group(2)):02d}-{int(when.group(1)):02d}"
            keep.append(e)
        path.write_text(json.dumps(keep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"named {named}, dropped {dropped}")


if __name__ == "__main__":
    main()
