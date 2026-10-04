"""
Search the AP Government Orders Issue Register (goir.ap.gov.in): every G.O. issued
since June 2008, by department, number, date range and abstract text.

It is a public ASP.NET search form (no login, no CAPTCHA); this script posts the same
form a browser would. Results are G.O. rows with their abstract and PDF link -- the
fastest way to find "the orders that create or change a scheme" (brief, task 2).

Run:  python ingest/collect/goir.py --dept AGLC --text "Rythu Bharosa" --from 01-01-2019
      python ingest/collect/goir.py --dept GAD --text "Right to Information" --out rti
Writes ingest/incoming/_catalog/goir_<out>.json (appends, dedups on PDF URL).
"""

from __future__ import annotations

import argparse
import re
from html import unescape
from urllib.parse import urljoin

from common import INCOMING, _polite, _session, load_json, save_json, today

URL = "https://goir.ap.gov.in/"
P = "ctl00$ContentPlaceHolder1$"


def _hidden(html: str) -> dict:
    return {m.group(1): unescape(m.group(2)) for m in re.finditer(
        r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', html)}


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def search(dept="-1", text="", go_no="", go_type="-1", date_from="", date_to="") -> list[dict]:
    _polite(URL)
    page = _session.get(URL, timeout=60).text
    form = _hidden(page)
    form.update({
        P + "DDLDeptname": dept, P + "sectddl": "-1", P + "txtGoNo": go_no,
        P + "DDLGoType": go_type, P + "DdlGo_cat": "-1", P + "txtfrmdate": date_from,
        P + "txttodate": date_to, P + "fAmount": "", P + "tAmount": "",
        P + "txtSearchText": text, P + "BtnSearch": "Search"})
    _polite(URL)
    html = _session.post(URL, data=form, timeout=120).text
    rows = []
    # columns: S.No | MS-118 | dd/mm/yyyy | category | abstract | dept | section |
    #          amount | English file | Telugu file
    for tr in re.findall(r'(?is)<tr class="grivw\w*">.*?</tr>', html):
        cells = [_clean(c) for c in re.findall(r"(?is)<td\b[^>]*>(.*?)</td>", tr)]
        files = dict((t, i) for i, t in re.findall(r'downloadFile\("(\d+)",\s*"(\w)"\)', tr))
        if len(cells) < 8 or not files:
            continue
        kind, _, num = cells[1].partition("-")
        d, m, y = (cells[2].split("/") + ["", "", ""])[:3]
        rows.append({
            "number": f"G.O.{kind.strip().title()}.No.{num.strip()}",
            "date": f"{y}-{m}-{d}" if y else "", "category": cells[3],
            "abstract": cells[4], "department": cells[5], "section": cells[6],
            "url": urljoin(URL, f"dgo.ashx?gid={files['E']}&fileType=E") if "E" in files else None,
            "url_te": urljoin(URL, f"dgo.ashx?gid={files['T']}&fileType=T") if "T" in files else None,
        })
    if len(rows) >= 100:
        print("  (100 rows: GOIR caps results -- narrow the date range)")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dept", default="-1", help="GOIR dept code, e.g. AGLC, GAD, FIN, REV")
    ap.add_argument("--text", default="")
    ap.add_argument("--go", default="", help="G.O. number")
    ap.add_argument("--type", default="-1", help="1 = Ms, 2 = Rt")
    ap.add_argument("--from", dest="date_from", default="")
    ap.add_argument("--to", dest="date_to", default="")
    ap.add_argument("--by-year", action="store_true", help="split --from..--to by year")
    ap.add_argument("--out", default="search")
    a = ap.parse_args()
    windows = [(a.date_from, a.date_to)]
    if a.by_year:   # GOIR returns at most 100 rows; one query per year avoids the cap
        y0, y1 = int(a.date_from[-4:]), int((a.date_to or f"31-12-{today()[:4]}")[-4:])
        windows = [(f"01-01-{y}", f"31-12-{y}") for y in range(y0, y1 + 1)]
    rows = []
    for f, t in windows:
        rows += search(a.dept, a.text, a.go, a.type, f, t)
    path = INCOMING / "_catalog" / f"goir_{a.out}.json"
    data = load_json(path, {"source": URL, "rows": []})
    seen = {r["url"] for r in data["rows"]}
    query = {"dept": a.dept, "text": a.text, "go": a.go, "from": a.date_from,
             "to": a.date_to, "accessed": today()}
    new = [dict(r, query=query) for r in rows if r["url"] not in seen]
    data["rows"] += new
    save_json(path, data)
    for r in rows:
        print(f"{r['number']:<18} {r['date']}  {r['abstract'][:150]}")
    print(f"\n{len(rows)} results ({len(new)} new) -> {path.name}")


if __name__ == "__main__":
    main()
