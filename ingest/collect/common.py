"""
Shared helpers for the data-collection tools (see docs/DATA_COLLECTION_BRIEF.md).

Everything here is mechanical: fetching with provenance, checksums, file naming, and
inspecting a downloaded PDF (pages, text layer, language). Judgement -- what to keep and
why -- lives in each domain's candidates.json, written by a person or research agent.

Rules from the brief that this module enforces:
- no logins, no CAPTCHA, no retrying past a 401/403: the URL is recorded as blocked;
- every saved file carries its direct URL, the page it was linked from, and the date;
- nothing is ever written to ingest/documents/.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import re
import sys
import time
from pathlib import Path

# Several gov.in servers send an incomplete certificate chain that certifi rejects but
# the OS trust store (which fetches intermediates) accepts. Use the OS store; never
# switch verification off. truststore ships inside pip, so no extra dependency.
# Must run before requests/urllib3 is imported.
try:
    import truststore
except ImportError:
    from pip._vendor import truststore
truststore.inject_into_ssl()

import requests  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]          # ingest/
INCOMING = ROOT / "incoming"
PROTECTED = ROOT / "documents"                      # never written to

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0 Safari/537.36 ap-rti-assistant-research")
DELAY_S = 1.0          # politeness gap between requests to the same host
TIMEOUT_S = 60

_session = requests.Session()
_session.headers["User-Agent"] = UA
_last_hit: dict[str, float] = {}


def today() -> str:
    return dt.date.today().isoformat()


def _polite(url: str) -> None:
    host = requests.utils.urlparse(url).netloc
    wait = DELAY_S - (time.time() - _last_hit.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    _last_hit[host] = time.time()


def fetch(url: str, *, tries: int = 3, stream_limit: int = 80_000_000) -> dict:
    """GET a URL. Returns {ok, status, content, content_type, final_url, error}.

    401/403/404/410 are final and never retried: blocked means blocked (brief rule 3).
    Network errors and 5xx get a couple of retries with backoff.
    """
    out = {"ok": False, "status": None, "content": b"", "content_type": "",
           "final_url": url, "error": None}
    for attempt in range(tries):
        _polite(url)
        try:
            r = _session.get(url, timeout=TIMEOUT_S, allow_redirects=True)
        except requests.RequestException as e:
            out["error"] = f"{type(e).__name__}: {e}"[:300]
            time.sleep(2 * (attempt + 1))
            continue
        out.update(status=r.status_code, content_type=r.headers.get("content-type", ""),
                   final_url=r.url)
        if r.status_code in (401, 403, 404, 410):
            out["error"] = f"HTTP {r.status_code}"
            return out
        if r.status_code >= 500:
            out["error"] = f"HTTP {r.status_code}"
            time.sleep(2 * (attempt + 1))
            continue
        out["content"] = r.content[:stream_limit]
        out["ok"] = r.ok
        if not r.ok:
            out["error"] = f"HTTP {r.status_code}"
        return out
    return out


def get_json(url: str):
    r = fetch(url)
    if not r["ok"]:
        raise RuntimeError(f"{url}: {r['error']}")
    return json.loads(r["content"].decode("utf-8-sig"))


# ---------- naming and checksums ----------

def slug(title: str, maxlen: int = 70) -> str:
    s = title.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:maxlen].rstrip("-") or "untitled"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_name(title: str, data: bytes, ext: str) -> str:
    """Same convention as ingest/documents/: slug of the title + '--' + first 8 hex of sha256."""
    return f"{slug(title)}--{sha256(data)[:8]}{ext}"


# ---------- inspecting a document ----------

TELUGU = re.compile(r"[ఀ-౿]")
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
EN_WORDS = {"the", "of", "and", "to", "in", "is", "for", "be", "by", "or", "on", "as",
            "with", "shall", "any", "this", "that", "under", "from", "which", "are"}


def guess_language(text: str) -> str:
    """'en', 'te', 'hi' or 'unknown'.

    AP orders in Telugu often use legacy non-Unicode fonts that extract as Latin
    gibberish, so 'no Telugu codepoints' does not mean English: we also require
    real English function words. Central gazettes are bilingual (Hindi half first);
    they count as 'en' when the English half is substantial. Anything else is
    'unknown' and needs a human look.
    """
    if not text.strip():
        return "unknown"
    letters = sum(c.isalpha() for c in text) or 1
    # 'uni' and single letters are what legacy-font Hindi/Telugu extracts as
    words = [w for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 1 and w != "uni"]
    latin_share = sum(len(w) for w in words) / letters
    if (words and latin_share > 0.2
            and sum(w in EN_WORDS for w in words) / len(words) > 0.08):
        return "en"
    if len(TELUGU.findall(text)) / letters > 0.3:
        return "te"
    if len(DEVANAGARI.findall(text)) / letters > 0.3:
        return "hi"
    return "unknown"


def inspect_pdf(data: bytes, max_pages: int = 40) -> dict:
    """Page count, whether there is a usable text layer, and the language guess.

    Reads up to max_pages spread across the document: bilingual gazettes put the
    Hindi half first, so sampling only the opening pages misjudges them.
    """
    from pypdf import PdfReader
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = len(reader.pages)
        step = max(1, pages // max_pages)
        sample_idx = list(range(0, pages, step))[:max_pages]
        texts = []
        for i in sample_idx:
            try:
                texts.append(reader.pages[i].extract_text() or "")
            except Exception:
                texts.append("")
    except Exception as e:
        return {"pages": None, "text_layer": None, "language": "unknown",
                "chars_per_page": 0, "inspect_error": str(e)[:200]}
    text = "\n".join(texts)
    cpp = len(text.strip()) / max(len(sample_idx), 1)
    lang = guess_language(text)
    return {"pages": pages,
            # a scan with only a stamp/header line extracts a few dozen characters
            "text_layer": cpp >= 200 and lang != "unknown",
            # scanned pages often carry a stray OCR-less header; per-page minimum
            # catches PDFs that are half text, half scan
            "scanned_pages": sum(len(t.strip()) < 100 for t in texts),
            "language": lang, "chars_per_page": round(cpp)}


def inspect_html(data: bytes) -> dict:
    text = re.sub(r"<[^>]+>", " ", data.decode("utf-8", "replace"))
    return {"pages": 1, "text_layer": True, "language": guess_language(text),
            "chars_per_page": len(text.split())}


def kind_of(data: bytes, content_type: str) -> str:
    if data[:5] == b"%PDF-":
        return "pdf"
    if b"<html" in data[:2000].lower() or "html" in content_type:
        return "html"
    if data[:4] == b"PK\x03\x04":
        return "zip"   # docx/xlsx
    return "other"


# ---------- json files ----------

def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path: Path, obj) -> None:
    assert PROTECTED not in path.resolve().parents, "never write into ingest/documents/"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
