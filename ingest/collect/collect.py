"""
Download a domain's chosen documents and write its manifest and inventory.

Input:  ingest/incoming/<domain>/candidates.json -- every candidate looked at, with the
        human judgement (decision keep/skip/lead, reason, doc_type, why, in_force ...).
Output: ingest/incoming/<domain>/<files>, manifest.json (kept files, brief's fields),
        inventory.json (every candidate with its outcome).

Mechanical fields (file, pages, bytes, sha256, text_layer, language, accessed) are
computed here, never typed by hand. Re-running is cheap: a kept file already on disk with
the same source URL is not downloaded again.

Run:  python ingest/collect/collect.py rti
      python ingest/collect/collect.py agriculture --refetch   # download everything again
"""

from __future__ import annotations

import argparse
import re
from html import unescape

from common import (INCOMING, fetch, file_name, inspect_html, inspect_pdf, kind_of,
                    load_json, save_json, sha256, today, unverified_note)

DOMAINS = ("rti", "agriculture", "finance", "questions")
BIFURCATION = "2014-06-02"

# Fields the brief requires, in its order; the first nine match corpus_manifest.json.
MANIFEST_FIELDS = ["title", "department", "group", "file", "pages", "bytes", "sha256",
                   "source_url", "source_page", "domain", "doc_type", "number", "date",
                   "language", "text_layer", "in_force", "amends", "accessed", "why"]
EXTRA_FIELDS = ["pre_bifurcation", "needs_ocr", "notes"]
EXT = {"pdf": ".pdf", "html": ".txt", "zip": ".docx", "other": ".bin"}


def html_to_text(data: bytes, keep_chrome: bool = False) -> str:
    """Readable text of an HTML page, for pages that are themselves the document.

    Menus, header and footer are dropped unless keep_chrome (some sites put the
    office address only in the footer)."""
    s = data.decode("utf-8", "replace")
    tags = "script|style|noscript|svg" + ("" if keep_chrome else "|nav|footer|header")
    s = re.sub(rf"(?is)<({tags})\b.*?</\1>", " ", s)
    s = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d)>", "\n", s)
    s = unescape(re.sub(r"<[^>]+>", " ", s))
    lines = [re.sub(r"[ \t\xa0]+", " ", ln).strip() for ln in s.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("domain", choices=DOMAINS)
    ap.add_argument("--refetch", action="store_true")
    args = ap.parse_args()

    folder = INCOMING / args.domain
    candidates = load_json(folder / "candidates.json", [])
    old = {m["source_url"]: m for m in load_json(folder / "manifest.json", [])}
    manifest, inventory, seen_sha = [], [], {}

    for c in candidates:
        url = c.get("source_url", "")
        inv = {k: c.get(k) for k in ("title", "department", "group", "source_url",
                                     "source_page", "doc_type", "number", "date")}
        inv.update(decision=c["decision"], reason=c.get("reason", ""),
                   checked=c.get("checked") or today())
        if c["decision"] != "keep":
            inventory.append(inv)
            continue

        prev = old.get(url)
        if prev and not args.refetch and (folder / prev["file"]).exists():
            data = (folder / prev["file"]).read_bytes()
            kind, accessed, status = prev["file"].rsplit(".", 1)[-1], prev["accessed"], 200
            kind = {"txt": "html", "pdf": "pdf"}.get(kind, kind)
        else:
            r = fetch(url)
            status, accessed = r["status"], today()
            if not r["ok"]:
                inv.update(decision="blocked" if status in (401, 403) else "broken",
                           reason=f"{r['error']} on {accessed}; " + inv["reason"])
                inventory.append(inv)
                print(f"  ! {r['error']:>12}  {url}")
                continue
            data, kind = r["content"], kind_of(r["content"], r["content_type"])
            if kind == "html" and not c.get("page_is_document"):
                inv.update(decision="broken", reason="expected a file, got an HTML page "
                           f"({r['final_url']}); " + inv["reason"])
                inventory.append(inv)
                print(f"  ! html-page     {url}")
                continue
            if kind == "html":
                # optional markers trim the site's menus and footer off a page document
                text = html_to_text(data, c.get("keep_chrome", False))
                a, b = c.get("text_start"), c.get("text_end")
                if a and a in text:
                    text = text[text.index(a):]
                if b and b in text:
                    text = text[:text.index(b)]
                data = (f"Source: {url}\nAccessed: {accessed}\n\n{text}\n").encode("utf-8")

        digest = sha256(data)
        if digest in seen_sha:
            inv.update(decision="skip", reason=f"duplicate file of '{seen_sha[digest]}'")
            inventory.append(inv)
            continue
        seen_sha[digest] = c["title"]

        fname = prev["file"] if prev and prev["sha256"] == digest else \
            file_name(c["title"], data, EXT[kind])
        (folder / fname).write_bytes(data)
        info = inspect_pdf(data) if kind == "pdf" else inspect_html(data)

        entry = {k: c.get(k) for k in MANIFEST_FIELDS}
        entry.update(file=fname, bytes=len(data), sha256=digest, pages=info["pages"],
                     domain=args.domain if args.domain != "questions" else c.get("domain"),
                     accessed=accessed, amends=c.get("amends") or [],
                     language=c.get("language") or info["language"],
                     text_layer=c.get("text_layer", info["text_layer"]))
        entry["pre_bifurcation"] = bool(c.get("date") and c["date"] < BIFURCATION)
        entry["needs_ocr"] = entry["text_layer"] is False
        entry["notes"] = " ".join(x for x in (c.get("notes", ""), unverified_note(url)) if x)
        manifest.append({k: entry.get(k) for k in MANIFEST_FIELDS + EXTRA_FIELDS})
        inv.update(file=fname, pages=info["pages"], text_layer=entry["text_layer"],
                   language=entry["language"])
        inventory.append(inv)
        flag = "" if entry["text_layer"] else "  [scan]"
        print(f"  + {info['pages'] or '?':>4}p {entry['language']}  {fname}{flag}")

    save_json(folder / "manifest.json", manifest)
    save_json(folder / "inventory.json", inventory)

    scans = sum(not m["text_layer"] for m in manifest)
    telugu = sum(m["language"] == "te" for m in manifest)
    unknown = sum(m["language"] == "unknown" for m in manifest)
    by = {}
    for i in inventory:
        by[i["decision"]] = by.get(i["decision"], 0) + 1
    print(f"\n{args.domain}: {len(manifest)} kept ({scans} scans, {telugu} Telugu, "
          f"{unknown} language unknown); inventory {by}")


if __name__ == "__main__":
    main()
