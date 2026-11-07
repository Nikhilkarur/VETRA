"""Check that the figures in exact records appear in the documents they cite, with no model.

For each record whose source URL matches a held document, every figure in the record's text
(rupee amounts, percentages, plain numbers of two or more digits) is looked for in that document's
text as built for search (OCR included). A figure not found is listed: a typo, an inference, a figure
from somewhere else, or a figure the extraction split. A person checks each one; nothing is changed.
Records whose source isn't held (web pages, unheld orders) are counted as unchecked.
Run: python tools/check_grounding.py [STATE ...]"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
FIGURE = re.compile(r"\d[\d,]*(?:\.\d+)?(?:\s*(?:lakh|crore))?", re.I)
DATE = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b|\b(\d{4})-(\d{2})-(\d{2})\b")
YEARS = re.compile(r"\b(?:19|20)\d\d\s*[-–]\s*\d\d(?:\d\d)?\b")  # 2026-27: a financial year says when, not how much


def norm(figure: str) -> set:
    """A figure in the forms it may be written: 4.75 lakh is also 475000; 15,000 is 15000."""
    low = re.sub(r"\s*(%|per\s*cent\.?)$", "", figure.lower().replace(",", "").strip())  # 66% is the figure 66
    unit = 100000 if low.endswith("lakh") else 10000000 if low.endswith("crore") else 1
    number = re.sub(r"\s*(lakh|crore)$", "", low).rstrip(".")
    try:
        value = float(number)
    except ValueError:
        return set()
    forms = {f"{value:g}"}
    if unit > 1:
        forms.add(f"{value * unit:g}")
    return forms


def dates(text: str) -> set:
    out = set()
    for m in DATE.finditer(text):
        d, mo, y = (m.group(1), m.group(2), m.group(3)) if m.group(1) else (m.group(6), m.group(5), m.group(4))
        out.add(f"{int(y):04d}-{int(mo):02d}-{int(d):02d}")
    return out


def figures(text: str) -> set:
    """Every figure in a text, dates taken out first so their parts aren't read as figures."""
    plain = YEARS.sub(" ", DATE.sub(" ", text))
    out = set()
    for f in FIGURE.findall(plain):
        out |= norm(f)
    return out | dates(text)


def doc_figures(domain: str, state: str) -> dict:
    """Figures in each held document, by source URL."""
    path = ROOT / "knowledge" / domain / "text" / f"{state}.json"
    found: dict = defaultdict(set)
    if path.exists():
        for item in json.loads(path.read_text(encoding="utf-8"))["items"]:
            found[item.get("source_url")] |= figures(item["text"])
    return found


def main() -> int:
    states = sys.argv[1:] or ["AP", "TN", "IN"]
    checked = unchecked = flagged = 0
    # A record may cite a document filed under the other topic, so look in both.
    # Central documents are searchable from every state, and a file is held once, so a state record
    # may cite a document filed under IN (the same PDF a state portal also publishes).
    held = {s: defaultdict(set) for s in states}
    for s in states:
        for place in dict.fromkeys((s, "IN")):
            for domain in ("agriculture", "finance"):
                for url, found in doc_figures(domain, place).items():
                    held[s][url] |= found
    for domain in ("agriculture", "finance"):
        for store in ("numbers", "dates", "rules"):
            path = ROOT / "knowledge" / domain / f"{store}.jsonl"
            if not path.exists():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                if r.get("jurisdiction") not in held:
                    continue
                source = r.get("source") or {}
                urls = [source.get("url")] + list(source.get("also") or [])  # a record may draw on more than one document
                in_doc = set().union(*(held[r["jurisdiction"]][u] for u in urls if u in held[r["jurisdiction"]]))
                if not in_doc:
                    unchecked += 1
                    continue
                checked += 1
                text = r.get("text", "")
                own = set(dates(text))
                for f in FIGURE.findall(YEARS.sub(" ", DATE.sub(" ", text))):
                    forms = norm(f)
                    whole = [x for x in forms if not re.fullmatch(r"(19|20)\d\d", x)]  # years say when, not how much
                    if whole and max(len(x.replace(".", "")) for x in whole) >= 2 and not (forms & in_doc):
                        own.add(f.strip())
                own -= {d for d in dates(text) if d in in_doc}
                # Figures a person has checked against the page itself (written in words, read from an image, a web page).
                hand = {d for f in r.get("checked_by_hand") or [] for d in (norm(f) | dates(f) | {f})}
                missing = sorted(f for f in own if not ((norm(f) | {f}) & hand))
                if missing:
                    flagged += 1
                    print(f"{r['id']}: not in the cited document: {', '.join(missing)}")
    print(f"{checked} records checked against their documents, {flagged} with figures to look at; "
          f"{unchecked} cite a document that isn't held, so weren't checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
