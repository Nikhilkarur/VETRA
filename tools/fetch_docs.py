"""Download a list of official documents into documents/<topic>/<STATE>/ and add them to the manifest.
List: JSON lines with title, url, topic, state, doc_type, department, date (optional), file (optional), read_as_scan (optional).
A failed link is reported and skipped. Run: python tools/fetch_docs.py LIST.jsonl"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
def file_name(url: str) -> str:
    """A file name for a download. Links like goir.ap.gov.in/dgo.ashx?gid=N carry no name of their own,
    and every one would land on the same "dgo.ashx", each overwriting the last; name them by their query."""
    parsed = urlparse(url)
    name = re.sub(r"[^\w.-]+", "-", unquote(Path(parsed.path).name))
    if name.lower().endswith(".pdf"):
        return name
    gid = re.search(r"gid=(\d+)", parsed.query)
    if gid and "goir.ap.gov.in" in parsed.netloc:
        return f"ap-go-{gid.group(1)}.pdf"
    import hashlib
    return f"{Path(name).stem or 'doc'}-{hashlib.sha256(url.encode()).hexdigest()[:10]}.pdf"


ok = failed = 0
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    d = json.loads(line)
    folder = ROOT / "documents" / d["topic"] / d["state"]
    name = d.get("file") or file_name(d["url"])
    path = folder / name
    manifest = folder / "manifest.json"
    entries = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else []
    if not path.exists():
        try:
            r = requests.get(d["url"], headers=HEADERS, timeout=240)
            r.raise_for_status()
            if not r.content.startswith(b"%PDF"):
                raise ValueError("not a PDF")
            folder.mkdir(parents=True, exist_ok=True)
            path.write_bytes(r.content)
        except (requests.RequestException, ValueError) as e:
            print(f"FAIL {d['url'][:90]}: {type(e).__name__}", flush=True)
            failed += 1
            continue
    if not any(e["file"] == name for e in entries):
        entry = {k: d[k] for k in ("title", "doc_type", "department", "date", "in_force", "read_as_scan") if k in d}
        entry.update(file=name, source_url=d["url"])
        entries.append(entry)
        manifest.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
    ok += 1
print(f"got {ok}, failed {failed}", flush=True)
