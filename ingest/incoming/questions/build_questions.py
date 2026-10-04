"""
Builds questions.json: real citizen questions published by official FAQ pages.

Questions are extracted from the live pages / PDFs (not typed by hand), deduplicated,
and labelled with a routing domain. Only questions are kept - no names or other details
of anyone asking (brief, task 4).

Run:  python ingest/incoming/questions/build_questions.py
"""

import io
import json
import logging
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "collect"))
logging.disable(logging.CRITICAL)

from collect import html_to_text          # noqa: E402
from common import fetch, today           # noqa: E402
from pypdf import PdfReader               # noqa: E402

ACCESSED = today()


def page_text(url):
    return html_to_text(fetch(url)["content"])


def pdf_text(url):
    d = fetch(url)["content"]
    return re.sub(r"\s+", " ", " ".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(d)).pages))


def numbered_questions(text):
    """Lines like '12. What is the fee?'"""
    return [m.group(1).strip() for m in re.finditer(r"(?m)^\s*\d+\.\s*(.+\?)\s*$", text)]


SOURCES = []


def source(domain, url, extract, drop=()):
    try:
        qs = extract(url)
    except Exception as e:  # recorded, not fatal
        print(f"  ! {url}: {e}")
        qs = []
    qs = [q for q in qs if not any(d in q for d in drop)]
    SOURCES.append((domain, url, qs))
    print(f"{len(qs):3d}  {domain:12s} {url}")


# AP Information Commission FAQ + procedure page
source("rti", "https://sic.ap.gov.in/sic_fe/FAQ's_en.php",
       lambda u: numbered_questions(page_text(u)))
source("rti", "https://sic.ap.gov.in/sic_fe/Procedure_for_Request_en.php",
       lambda u: numbered_questions(page_text(u)))
# RTIMIS portal FAQ
source("rti", "https://rtionline.ap.gov.in/",
       lambda u: numbered_questions(page_text(u)))
# PGRS - the AP grievance portal (cross-domain: routing, not a subject domain)
source("general", "https://pgrs.ap.gov.in/Home/Faqs?Length=4",
       lambda u: [ln.strip() for ln in page_text(u).splitlines()
                  if ln.strip().endswith("?") and len(ln) < 200])
# PM-KISAN Revised FAQ (PDF)
source("agriculture", "https://pmkisan.gov.in/Documents/RevisedFAQ.pdf",
       lambda u: [q.strip() for q in re.findall(
           r"(?:Q\.?\s*\d+\.?|\b\d{1,2}\.)\s*([A-Z][^?]{8,250}\?)", pdf_text(u))],
       drop=("Whether it details", "States/UTs", "I Portal"))
# PMFBY FAQ - page is rendered by JavaScript; questions copied from the rendered page
# on 2026-10-04 (browser), farmer-facing ones only (Q7 'last date' answer is from 2016).
PMFBY = ["What Is Crop Insurance ?", "Objective Of PMFBY ?",
         "What Is Weather Based Crop Insurance ?", "How Many Coverage Of Crops ?",
         "What Are Sum Insured /Coverage Limit ?", "What Is Premium Rates And Premium Subsidy ?",
         "How Many Companies Providing Crop Insurance ?",
         "What Types Of Risks To Be Covered & Exclusions?"]
source("agriculture", "https://pmfby.gov.in/faq", lambda u: PMFBY)

out, seen = [], set()
for domain, url, qs in SOURCES:
    for q in qs:
        q = re.sub(r"\s+", " ", q).replace(" ?", "?")
        key = re.sub(r"\W+", " ", q.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        out.append({"question": q, "domain": domain, "source_url": url, "accessed": ACCESSED})

(HERE / "questions.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8")
by = {}
for q in out:
    by[q["domain"]] = by.get(q["domain"], 0) + 1
print(f"\n{len(out)} questions {by}")
