"""
Live search of official websites, for a part of a question the store has nothing on.

It runs only after the exact stores, text search and looking further have all come back empty for
a part. It searches government websites, reads the pages itself, and hands back passages as
evidence like any other, so the same checks apply: every figure in the answer must appear in a
cited passage, and a deep answer's statements are read against their sources. Nothing found here
goes into the store; the reader sees it marked as fetched live from an official website.

Safety: only hosts on the allow-list are searched or read, after redirects too. Page text is data,
and the writing model is told to ignore instructions in it. A page is never trusted over a held
document: fetched passages are last in line when evidence is cut.

Search needs a search service key in .env (none is used without one, and VETRA then behaves as before):
    TAVILY_API_KEY=...   (free tier; limited to official domains by the service)
    BRAVE_API_KEY=...    (free tier; limited with site: filters)
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import time
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

from .tools import Evidence

# Official hosts only. A suffix matches the host itself and any subdomain.
ALLOWED = ("gov.in", "nic.in", "rbi.org.in", "nabard.org", "sansad.in", "pmkisan.gov.in")
SEARCH_DOMAINS = ("gov.in", "nic.in", "rbi.org.in", "nabard.org")
KIND = "official website, fetched live"
TOOL = "web_search"
MAX_PAGES = 3           # pages read per part
PASSAGES_PER_PAGE = 2
PASSAGE_CHARS = 1200
PAGE_BYTES = 4_000_000  # bigger files are skipped, not half-read
PDF_PAGES = 15
TIME_BUDGET = 25.0      # seconds for one part: a citizen is waiting
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) VETRA official-information assistant"}


@dataclass
class Hit:
    url: str
    title: str = ""
    snippet: str = ""


class Backend(Protocol):
    name: str

    def search(self, query: str, limit: int) -> list[Hit]: ...


def allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in ALLOWED)


class Tavily:
    name = "Tavily"

    def __init__(self, key: str):
        self.key = key

    def search(self, query: str, limit: int) -> list[Hit]:
        import requests

        r = requests.post("https://api.tavily.com/search", timeout=15, json={
            "api_key": self.key, "query": query, "max_results": limit, "search_depth": "basic",
            "include_domains": list(SEARCH_DOMAINS)})
        r.raise_for_status()
        return [Hit(x.get("url", ""), x.get("title", ""), x.get("content", "")) for x in r.json().get("results", [])]


class Brave:
    name = "Brave"

    def __init__(self, key: str):
        self.key = key

    def search(self, query: str, limit: int) -> list[Hit]:
        import requests

        sites = " OR ".join(f"site:{d}" for d in SEARCH_DOMAINS)
        r = requests.get("https://api.search.brave.com/res/v1/web/search", timeout=15,
                         params={"q": f"{query} ({sites})", "count": limit, "country": "IN"},
                         headers={"X-Subscription-Token": self.key, "Accept": "application/json"})
        r.raise_for_status()
        return [Hit(x.get("url", ""), x.get("title", ""), x.get("description", ""))
                for x in (r.json().get("web") or {}).get("results", [])]


def from_env() -> Backend | None:
    """The configured search service, or None. Reads keys from the environment (.env is loaded by llm.from_env)."""
    if os.environ.get("TAVILY_API_KEY"):
        return Tavily(os.environ["TAVILY_API_KEY"])
    if os.environ.get("BRAVE_API_KEY"):
        return Brave(os.environ["BRAVE_API_KEY"])
    return None


def _text_of(content: bytes, kind: str) -> str:
    if "pdf" in kind or content[:4] == b"%PDF":
        import pypdf

        reader = pypdf.PdfReader(io.BytesIO(content))
        return " ".join((p.extract_text() or "") for p in reader.pages[:PDF_PAGES])
    import html as html_lib

    page = content.decode("utf-8", errors="replace")
    page = re.sub(r"(?is)<(script|style|nav|header|footer|noscript)[^>]*>.*?</\1>", " ", page)
    return html_lib.unescape(re.sub(r"<[^>]+>", " ", page))


def fetch(url: str) -> tuple[str, str] | None:
    """The page's text and final URL, or None if it isn't official, is too big, or fails."""
    import requests

    if not allowed(url):
        return None
    try:
        r = requests.get(url, headers=HEADERS, timeout=12, stream=True, allow_redirects=True)
        if not r.ok or not allowed(r.url):   # a redirect off the allow-list is refused
            return None
        content = r.raw.read(PAGE_BYTES + 1, decode_content=True)
        if len(content) > PAGE_BYTES:
            return None
        text = re.sub(r"\s+", " ", _text_of(content, r.headers.get("content-type", ""))).strip()
    except Exception:  # a page that can't be read is skipped; the others may answer
        return None
    return (text, r.url) if len(text) > 200 else None


_WORD = re.compile(r"[a-z0-9]+|[ऀ-෿]+")
_COMMON = frozenset("a an and are at by can do for from how i in is it me my of on or the to what when who why with".split())


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _COMMON}


def passages(text: str, wanted: str, n: int = PASSAGES_PER_PAGE) -> list[str]:
    """The n stretches of a page sharing the most words with what's wanted, best first."""
    want = _words(wanted)
    pieces = [text[i:i + PASSAGE_CHARS] for i in range(0, len(text), PASSAGE_CHARS - 200)]
    scored = sorted(((len(want & _words(p)), i, p) for i, p in enumerate(pieces)), reverse=True)
    return [p for score, _, p in scored[:n] if score >= min(2, len(want))]


def find(subject: str, place: str, question: str, backend: Backend | None,
         fetcher=None) -> tuple[list[Evidence], list[str]]:
    """
    Official web passages for one part of a question, and the hosts that were searched.
    Empty evidence means nothing official was found (or no search service is set up).
    """
    if backend is None:
        return [], []
    fetcher = fetcher or fetch
    started = time.perf_counter()
    query = f"{subject} {place}".strip()
    try:
        hits = [h for h in backend.search(query, limit=6) if allowed(h.url)]
    except Exception:  # the service is down or out of quota: say nothing was found live
        return [], list(SEARCH_DOMAINS)
    found: list[Evidence] = []
    for hit in hits[:MAX_PAGES]:
        if time.perf_counter() - started > TIME_BUDGET:
            break
        page = fetcher(hit.url)
        if not page:
            continue
        text, final = page
        host = urlparse(final).hostname or ""
        for p in passages(text, f"{subject} {question}"):
            key = "web:" + hashlib.sha256(f"{final}|{p[:80]}".encode()).hexdigest()[:12]
            found.append(Evidence(key=key, tool=TOOL, text=p, doc=f"{hit.title or host} ({host})",
                                  jurisdiction="", url=final, kind=KIND, status="unknown", reviewed=False))
    return found, list(SEARCH_DOMAINS)
