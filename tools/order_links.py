"""Read each held order for its own number and for what it amends or replaces, with no model, and fill the manifests.
An order named as superseded, cancelled, rescinded, withdrawn or repealed by a later held order gets in_force "no" and replaced_by.
Every link found goes to eval/cache/hand/order_links.jsonl with its sentence, so a person can check it.
Run: python tools/order_links.py [--dry]   then rebuild each topic and state (python -m vetra.intake build)."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ORDER = r"G\.?\s?O\.?\s?\(?\s?(Ms|Rt|P|D)\s?\)?\.?\s?(?:No\.?\s?)?-?\s?(\d{1,4})"
DATED = r"(?:[^.]{0,70}?(?:dated|dt)?[.:,\s]*)(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})"
CITED = re.compile(ORDER + DATED, re.I)
ENDED = r"supersed\w*|supersession|rescind\w*|cancel\w*|withdraw\w*|repeal\w*"
CHANGED = r"amend\w*|modif\w*"
ENDED_BEFORE = re.compile(rf"\b({ENDED})\b[^.]{{0,60}}?$", re.I)
CHANGED_BEFORE = re.compile(rf"\b({CHANGED})\b[^.]{{0,60}}?$", re.I)
ENDED_AFTER = re.compile(rf"^[^.]{{0,40}}?\b(?:is|are|stands?|shall stand)\s+(?:hereby\s+)?({ENDED})\b", re.I)
CHANGED_AFTER = re.compile(rf"^[^.]{{0,40}}?\b(?:is|are)\s+(?:hereby\s+)?({CHANGED})\b", re.I)


def label(kind: str, number: str, year: str) -> str:
    return f"{kind.capitalize()}.{int(number)}/{year if len(year) == 4 else '20' + year}"


def own_order(title: str, first_page: str) -> str:
    """This document's own number: the title's, else the first dated one at the head of the first page."""
    for text in (title, first_page[:700]):
        m = re.search(ORDER + DATED, text, re.I) or re.search(r"G\.?O\.?\s?\.?(MS|RT)-(\d+)\s+dated\s+(\d{1,2})[./-](\d{1,2})[./-](\d{4})", text, re.I)
        if m:
            return label(m.group(1), m.group(2), m.group(5))
    return ""


def links(text: str, own: str) -> list[dict]:
    """What this text says it ends or changes. A bare reference in "Read the following" is neither."""
    flat = re.sub(r"\s+", " ", text)
    found = {}
    for m in CITED.finditer(flat):
        target = label(m.group(1), m.group(2), m.group(5))
        if target == own:
            continue
        before, after = flat[max(0, m.start() - 90):m.start()], flat[m.end():m.end() + 70]
        ended = ENDED_BEFORE.search(before) or ENDED_AFTER.search(after)
        changed = CHANGED_BEFORE.search(before) or CHANGED_AFTER.search(after)
        if ended or changed:
            relation = "ends" if ended else "amends"
            if found.get(target, {}).get("relation") != "ends":
                found[target] = {"target": target, "relation": relation, "sentence": flat[max(0, m.start() - 90):m.end() + 70]}
    return list(found.values())


def apply(entries: list[dict], read) -> list[dict]:
    """Fill order, amends_orders, in_force and replaced_by in place. read(entry) gives (first_page, whole_text)."""
    log = []
    for e in entries:
        first, whole = read(e)
        e["order"] = e.get("order") or own_order(e.get("title", ""), first)
        if e["order"]:
            found = links(whole, e["order"])
            log += [{"order": e["order"], "file": e["file"], **f} for f in found]
            e["amends_orders"] = sorted({f["target"] for f in found})
    by_order = {e["order"]: e for e in entries if e.get("order")}
    for row in log:
        target = by_order.get(row["target"])
        issued, later = target.get("date", "") if target else "", next(e for e in entries if e["file"] == row["file"]).get("date", "")
        # only a later order can end an earlier one
        if row["relation"] == "ends" and target and (not issued or not later or later >= issued):
            target["in_force"] = "no"
            target["replaced_by"] = row["order"]
    return log


def main() -> None:
    import pypdf

    dry, all_log = "--dry" in sys.argv, []
    for manifest in sorted((ROOT / "documents").glob("*/*/manifest.json")):
        if manifest.parent.name not in ("AP", "TN", "IN"):
            continue
        entries = json.loads(manifest.read_text(encoding="utf-8"))
        def read(e: dict) -> tuple[str, str]:
            if not str(e.get("file", "")).lower().endswith(".pdf") or e.get("doc_type") != "go":
                return "", ""
            try:
                pages = pypdf.PdfReader(str(manifest.parent / e["file"])).pages
                # the operative part of an order is short; a policy annexed to it isn't read for links
                texts = [(p.extract_text() or "") for p in list(pages)[:6]]
                return texts[0] if texts else "", "\n".join(texts)
            except Exception as exc:
                print(e["file"], type(exc).__name__, flush=True)
                return "", ""
        log = apply(entries, read)
        all_log += [{"folder": f"{manifest.parent.parent.name}/{manifest.parent.name}", **row} for row in log]
        print(manifest.parent.parent.name, manifest.parent.name, "orders", sum(bool(e.get("order")) for e in entries), "links", len(log), "ended", sum(bool(e.get("replaced_by")) for e in entries), flush=True)
        if not dry:
            manifest.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "eval" / "cache" / "hand" / "order_links.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in all_log), encoding="utf-8")


if __name__ == "__main__":
    main()
