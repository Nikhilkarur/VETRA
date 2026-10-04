# Citizen questions (collected 2026-10-04)

`questions.json`: **71 real questions** from official FAQs, in the brief's format
`{question, domain, source_url, accessed}`. Built by `build_questions.py`, which extracts
them from the live pages and PDFs and deduplicates them. No names or details of anyone asking.

| Source | Domain | Questions |
|---|---|---|
| AP Information Commission FAQ + Procedure page | rti | 18 (+4 duplicates dropped) |
| RTIMIS portal FAQ | rti | 3 |
| PGRS (AP grievance portal) FAQ | general | 14 |
| PM-KISAN Revised FAQ (PDF) | agriculture | 28 |
| PMFBY FAQ (JavaScript page; copied from the rendered page) | agriculture | 8 |

`domain: general` is used for PGRS (grievance routing). It is not one of the three subject
domains, but the router needs it: **PGRS does not take RTI matters** (its own FAQ), so "my RTI
was not answered" must route to RTI, while "my ration card is not issued" goes to PGRS.

The PGRS FAQ page is also kept as a document (`manifest.json`). Its answers cover where to
file a grievance (Sachivalayam, Monday at the Collectorate, portal, app, 1100), re-opening
twice, and SLAs of 24 hours to 90 days.

## Not collected

- **PGRS grievance categories and sub-categories.** The name today is PGRS, Public Grievance
  Redressal System, relaunched with stats from 15-06-2024 and run by RTGS. The category tree
  only appears inside grievance registration, which needs login (Aadhaar/OTP). Blocked; not
  attempted.
- Finance questions: none until the finance scope is approved. The SSP and IGRS portals are
  the likely FAQ sources.
- The questions are formal FAQ phrasing. They are good routing labels, but **not a
  substitute for casual citizen phrasing** in a test set (see context.md on the casual-vs-
  formal retrieval gap).
