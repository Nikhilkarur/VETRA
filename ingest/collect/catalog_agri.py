"""
Catalogue every document on the Agriculture Department's current site, agriculture.ap.gov.in.

The old site (apagrisnet.gov.in) is dead: it presents an expired certificate for another
domain, and behind that Apache returns 403 "unable to read htaccess file" on every path.
The department's new site is an Angular app. Its document lists (Acts & GOs, Schemes,
RTI, ...) come from one public endpoint, getDepartmentReportData, keyed by a category
('compType'); the category names were read from the site's JS bundle on 2026-10-04.
Files download from comm/files/download/<fileUUID>.

Writes ingest/incoming/_catalog/agri_site.json. Nothing is downloaded here.

Run:  python ingest/collect/catalog_agri.py
"""

from __future__ import annotations

import datetime as dt
import json

from common import INCOMING, _polite, _session, save_json, today

BASE = "https://agriculture.ap.gov.in/staging/api/"
LIST = BASE + "cropAnalysis/getDepartmentReportData"
DOWNLOAD = BASE + "comm/files/download/{}"
SITE = "https://agriculture.ap.gov.in/"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

# compType -> the site page that shows it
CATEGORIES = {
    "Acts": "acts-gos/acts", "Notifications": "acts-gos/governemet-go", "Schemes": "home",
    "RTI": "rti", "Fertilizers": "home", "Farm mechanization": "reports/farm-mechanization",
    "Natural_Farming": "natural-farming", "Others": "others/department-activities",
    "Seasonal_Reports": "reports/seasonal-conditions", "AgroAdvisory": "reports/weekly-advisory",
    "News": "home", "E-Magzine": "farmers-corners/e-magazine",
    "Vyavasaya_Panchangam": "farmers-corners/e-info",
}


def fetch_list(comp: str, archived: bool) -> dict:
    _polite(LIST)
    r = _session.post(LIST, json={"compType": comp, "is_archived": archived}, timeout=60)
    return (r.json() or {}).get("response") or {}


def main() -> None:
    rows, errors, seen = [], [], set()
    for comp, page in CATEGORIES.items():
        n = 0
        # is_archived=False -> the current list, True -> the archive; current first
        for archived in (False, True):
            try:
                data = fetch_list(comp, archived)
            except Exception as e:
                errors.append({"compType": comp, "archived": archived, "error": str(e)[:200]})
                continue
            for f in data.values():
                if f.get("fileUUID") in seen:
                    continue
                seen.add(f.get("fileUUID"))
                n += 1
                ts = f.get("eventTs")
                rows.append({
                    "compType": comp, "group": f.get("egn"), "fileName": f.get("fileName"),
                    "heading": (f.get("infoJson") or {}).get("heading"),
                    "date": dt.datetime.fromtimestamp(ts / 1000, IST).date().isoformat() if ts else None,
                    "year": f.get("year"), "url": DOWNLOAD.format(f.get("fileUUID")),
                    "archived": archived, "source_page": SITE + page})
        print(f"{comp:22s} {n:4d} files")
    save_json(INCOMING / "_catalog" / "agri_site.json",
              {"source": LIST, "accessed": today(), "files": len(rows), "errors": errors, "rows": rows})
    print(f"\n{len(rows)} files, {len(errors)} errors -> incoming/_catalog/agri_site.json")


if __name__ == "__main__":
    main()
