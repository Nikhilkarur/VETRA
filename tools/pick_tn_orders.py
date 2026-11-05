"""Pick Tamil Nadu orders by their coded file names (agri_e_ms_63_au_2022.pdf), which carry no subject in their links.
Takes English orders from 2020 on, plus current scheme orders on the horticulture site. fetch_docs.py downloads them; tools/order_titles.py then names them.
Run: python tools/pick_tn_orders.py   writes eval/cache/hand/pick_TN2.jsonl"""
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
HAND = ROOT / "eval" / "cache" / "hand"
CODED = re.compile(r"(?:\d+-)?([a-z]+)_e_(ms|d|2d|rt)_(\d+)_(?:[a-z0-9]+_)?(\d{4})\.pdf$", re.I)
MAWS = re.compile(r"maws_e_(\d+)_(\d{4})(?:_D|_2D)?\.pdf$", re.I)
TOPIC = {"agri": "agriculture", "maws": "finance", "rev": "finance", "fin": "finance", "ctr": "finance", "cooptn": "agriculture", "ahf": "agriculture"}
SINCE = 2020


def main() -> None:
    held = set()
    for manifest in (ROOT / "documents").glob("*/TN/manifest.json"):
        for e in json.loads(manifest.read_text(encoding="utf-8")):
            held.add(str(e.get("source_url")))
    out, seen = [], set()
    for line in (HAND / "pdfs.jsonl").read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        if d.get("state") != "TN" or d["url"] in held or d["url"] in seen:
            continue
        name = unquote(d["url"].rsplit("/", 1)[-1])
        coded = CODED.search(name)
        row = None
        if coded and int(coded.group(4)) >= SINCE and coded.group(1).lower() in TOPIC:
            kind = coded.group(2).capitalize()
            row = {"title": f"Tamil Nadu G.O.({kind}).No.{int(coded.group(3))} of {coded.group(4)}, {d['site']}", "topic": TOPIC[coded.group(1).lower()], "doc_type": "go", "date": coded.group(4)}
        elif d["site"] == "tnhorticulture.tn.gov.in" and re.search(r"\bGO\b|-GO-|Policy|PN-|Budget|BS-", name) and re.match(r"(20(2[4-9])|GO|5--PN|Agri-BS|CC_English)", name):
            row = {"title": f"Tamil Nadu horticulture department: {name[:-4]}", "topic": "agriculture", "doc_type": "go" if "GO" in name else "other"}
        if row:
            seen.add(d["url"])
            row.pop("date", None)
            out.append({**row, "url": d["url"], "state": "TN", "department": d["site"], "file": re.sub(r"[^\w.-]+", "-", name)})
    (HAND / "pick_TN2.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out), encoding="utf-8")
    print(len(out))


if __name__ == "__main__":
    main()
