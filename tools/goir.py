"""List Andhra Pradesh government orders from goir.ap.gov.in by department and date, for choosing what to collect.
Run: python tools/goir.py OUT.jsonl FROM_YEAR DEPT [DEPT ...]   e.g. python tools/goir.py gos.jsonl 2024 AGLC REV"""
import html
import json
import re
import sys
import time
from datetime import date, timedelta

import requests

URL = "https://goir.ap.gov.in/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
P = "ctl00$ContentPlaceHolder1$"


def hidden(page: str) -> dict:
    return {n: html.unescape(v) for n, v in re.findall(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"', page)}


def rows(page: str) -> list[dict]:
    found = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        gid = re.search(r"""downloadFile\(\s*(?:&#39;|&quot;|'|")?(\d+)""", row)
        if not gid:
            continue
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        found.append({"gid": gid.group(1), "cells": [c for c in cells if c]})
    return found


def search(session: requests.Session, dept: str, start: date, end: date) -> list[dict]:
    page = session.get(URL, headers=HEADERS, timeout=60).text
    form = hidden(page)
    form.update({P + "DDLDeptname": dept, P + "sectddl": "-1", P + "txtGoNo": "", P + "fAmount": "", P + "tAmount": "", P + "txtSearchText": "", P + "DDLGoType": "-1", P + "DdlGo_cat": "-1",
                 P + "txtfrmdate": start.strftime("%d-%m-%Y"), P + "txttodate": end.strftime("%d-%m-%Y"), P + "BtnSearch": "Search"})
    return rows(session.post(URL, data=form, headers=HEADERS, timeout=90).text)


if __name__ == "__main__":
    out, first_year, depts = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
    session, seen = requests.Session(), set()
    with open(out, "a", encoding="utf-8") as f:
        for dept in depts:
            count, start = 0, date(first_year, 1, 1)
            while start <= date.today():
                end = min(start + timedelta(days=14), date.today())
                try:
                    for r in search(session, dept, start, end):
                        if r["gid"] not in seen:
                            seen.add(r["gid"])
                            count += 1
                            f.write(json.dumps({"dept": dept, **r}, ensure_ascii=False) + "\n")
                except requests.RequestException as e:
                    print(dept, start, type(e).__name__, flush=True)
                f.flush()
                start = end + timedelta(days=1)
                time.sleep(1)
            print(dept, count, flush=True)
