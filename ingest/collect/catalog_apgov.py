"""
Catalogue every file the ap.gov.in state portal links to, through its JSON API.

The portal is an Angular app; its menus are built from this API and can hide files
(the RTI accordion hid 282 of 285). Reading the API directly sees everything. The
controller names below were taken from the portal's own JS bundle
(src_app_website_website_module_ts.js) on 2026-10-04.

Writes ingest/incoming/_catalog/apgov.json: one row per file link, with the menu path
it sits under. No files are downloaded here; collect.py does that for chosen rows.

Run:  python ingest/collect/catalog_apgov.py
"""

from __future__ import annotations

import re

from common import INCOMING, get_json, save_json, today

API = "https://www.ap.gov.in/api/api/"
SITE = "https://ap.gov.in/#/"
FILE_RE = re.compile(r"^https?://\S+\.(pdf|docx?|xlsx?|pptx?|zip)$", re.I)

# (portal section, master controller, child path(s) taking the master id, portal page)
TREES = [
    ("Acts", "ApActs", [], "rti-acts/acts"),
    ("GAD Circulars", "ApGadCirculars", [], "rti-acts/gadcirculars"),
    ("Manuals", "ApManuals", [], "rti-acts/manuals"),
    ("Service Rules", "ApServiceRules", [], "rti-acts/servicerules"),
    ("Socio Economic Survey", "ApSocioEconomicSurveys",
     ["ApSocioEconomicSurveyChilds/getbymaster/"], "socioeconomicsurvey"),
    ("Public Forms", "ApStateServicesPublicForms",
     ["ApStateServicesPublicFormsChilds/getbymasterid/"], "services/publicforms"),
    ("Investment Policies", "ApInvestmentPolicy",
     ["ApInvestmentPolicyChild/getbymaster/"], "quicklinks/investmentpolicies"),
    ("Principal Accountant General", "ApOfficeOfPrincipalAccountantGenerals",
     ["ApOfficeOfPrincipalAccountantGeneralChilds/getbymaster/"], "pag"),
    ("Societies/Missions/Projects", "ApSocietiesMissionsProjects",
     ["ApSocietiesMissionsProjectsChilds/getbymaster/"], "societies"),
    ("PSUs", "ApPsus", ["ApPsusChilds/getbymaster/"], "psus"),
    ("HoDs", "ApHoDs", ["ApHodsChilds/getbymaster/"], "hods"),
]


def rows(resp) -> list[dict]:
    """The API puts lists under 'dataList', 'data' or (sometimes) 'responseCode'."""
    for key in ("dataList", "data", "responseCode"):
        v = resp.get(key) if isinstance(resp, dict) else None
        if isinstance(v, list):
            return v
    return []


def title_of(r: dict) -> str:
    return (r.get("subject") or r.get("name") or r.get("title") or "").strip()


def files_in(r: dict):
    for k, v in r.items():
        if isinstance(v, str) and FILE_RE.match(v.strip()):
            yield k, v.strip()


def main() -> None:
    out, errors = [], []

    def add(section, group, rec, endpoint, page, department=""):
        for field, url in files_in(rec):
            out.append({"section": section, "department": department, "group": group,
                        "title": title_of(rec), "url": url, "field": field,
                        "year": rec.get("year"), "api": endpoint,
                        "source_page": SITE + page, "modified": rec.get("modifiedDate")
                        or rec.get("createdDate")})

    for section, master, children, page in TREES:
        try:
            masters = rows(get_json(API + master))
        except Exception as e:
            errors.append({"api": API + master, "error": str(e)})
            continue
        for m in masters:
            add(section, title_of(m), m, API + master, page)
            for child in children:
                ep = f"{API}{child}{m['id']}"
                try:
                    for c in rows(get_json(ep)):
                        add(section, title_of(m), c, ep, page)
                except Exception as e:
                    errors.append({"api": ep, "error": str(e)})
        print(f"{section:32s} {sum(r['section'] == section for r in out):5d} files")

    # Department-Org RTI: department -> sub-organisation -> documents (3 levels).
    section, page = "Department - Org RTI", "rti-acts/departmentorgrti"
    for d in rows(get_json(API + "ApDepartmentOrgRtis")):
        try:
            subs = rows(get_json(f"{API}ApSubDepartmentRtiOrg/getbymasterid/{d['id']}"))
        except Exception as e:
            errors.append({"api": f"ApSubDepartmentRtiOrg/{d['id']}", "error": str(e)})
            continue
        for s in subs:
            ep = f"{API}ApDepartmentOrgRtiChilds/getbymasterid/{s['id']}"
            try:
                for c in rows(get_json(ep)):
                    add(section, title_of(s), c, ep, page, department=title_of(d))
            except Exception as e:
                errors.append({"api": ep, "error": str(e)})
    print(f"{section:32s} {sum(r['section'] == section for r in out):5d} files")

    save_json(INCOMING / "_catalog" / "apgov.json",
              {"source": API, "accessed": today(), "files": len(out),
               "errors": errors, "rows": out})
    print(f"\n{len(out)} file links, {len(errors)} API errors -> incoming/_catalog/apgov.json")


if __name__ == "__main__":
    main()
