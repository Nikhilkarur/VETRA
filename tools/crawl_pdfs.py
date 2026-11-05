"""List the PDFs on official sites, for choosing what to collect. Saves nothing but the list.
Run: python tools/crawl_pdfs.py OUT.jsonl STATE=https://site.gov.in/ [STATE=https://...] """
import json
import re
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from urllib.parse import urljoin, urlparse

import requests

warnings.filterwarnings("ignore")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
LINK = re.compile(r"<a\b[^>]*?href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", re.I | re.S)
SKIP = re.compile(r"\.(jpg|jpeg|png|gif|zip|rar|doc|docx|xls|xlsx|mp4|css|js|svg|ico)(\?|$)|logout|login|javascript:|mailto:|tel:", re.I)
MAX_PAGES, TIMEOUT = 120, 15


def crawl(state: str, seed: str) -> list[dict]:
    host = urlparse(seed).netloc.removeprefix("www.")
    queue, seen, found, status = [(seed, 0)], {seed}, {}, "ok"
    pages = 0
    while queue and pages < MAX_PAGES:
        url, depth = queue.pop(0)
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        except requests.RequestException as e:
            status = type(e).__name__ if pages == 0 else status
            continue
        pages += 1
        if "html" not in r.headers.get("content-type", "").lower():
            continue
        for href, text in LINK.findall(r.text):
            link = urljoin(r.url, unescape(href.strip()))
            label = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)).strip()[:150]
            parsed = urlparse(link)
            if parsed.scheme not in ("http", "https"):
                continue
            if re.search(r"\.pdf(\?|$)", link, re.I):
                found.setdefault(link, {"state": state, "site": host, "url": link, "label": label, "page": url})
            elif parsed.netloc.removeprefix("www.") == host and depth < 2 and link not in seen and not SKIP.search(link):
                seen.add(link)
                queue.append((link, depth + 1))
    print(f"{state} {host}: {pages} pages, {len(found)} PDFs, {status}", flush=True)
    return list(found.values())


if __name__ == "__main__":
    seeds = [a.split("=", 1) for a in sys.argv[2:]]
    with ThreadPoolExecutor(8) as pool:
        results = pool.map(lambda s: crawl(*s), seeds)
    with open(sys.argv[1], "w", encoding="utf-8") as out:
        for rows in results:
            for row in rows:
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
