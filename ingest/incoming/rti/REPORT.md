# RTI — gap-filling report (collected 2026-10-04)

**27 documents kept** (168 pages, 14 MB) · 16 skipped · 4 leads · 3 broken · 1 blocked.
Every candidate and its reason is in `inventory.json`; kept files and their provenance are in
`manifest.json`. Nothing was written to `ingest/documents/`.

## Headline findings

1. **AP now has online RTI.** RTIMIS (`rtionline.ap.gov.in`) went live under
   **G.O.Ms.No.25, GA(AR), 18-02-2026**. It handles requests, first appeals and complaints,
   with online fee payment and BPL exemption. Drawing & Disbursing Officers are designated
   Nodal Officers (RTI). The PIO/FAA mapping deadline was extended to 15-03-2026 (Circular Memo
   3150498, 02-03-2026). The portal's own home page says second appeals go to the Commission
   directly, but the Citizen User Manual and the G.O. ("Second Appeal Module") describe
   online second appeals. Answers should cite both.
2. **Both central amendments are in force.**
   - RTI (Amendment) Act 2019: ss.13, 16, 27. Commissioners' term and pay are now "as
     prescribed"; the RTI Rules 2019 (G.S.R. 810(E), 24-10-2019) set a 3-year term. The
     official commencement notice (S.O. 3843(E), 24-10-2019, per secondary sources) was **not
     retrieved**: the ncte.gov.in copy timed out.
   - DPDP Act 2023, s.44(3), rewrites RTI s.8(1)(j) (personal information). It has been **in
     force since 13-11-2025** under G.S.R. 843(E), which is kept as evidence.
3. **The AP fee rules have not changed since 2007, apart from the payment head of account.**
   GOIR (all GAD orders, June 2008 to today) shows one later amendment to G.O.Ms.454:
   **G.O.Ms.No.79 (10-08-2020)**, a change of head of account. It replaces G.O.Ms.356 (2011),
   which is kept and marked not in force. The amounts in G.O.Ms.454/530/545/740 still stand.
4. **The current Commission:** Sri Vajja Srinivasa Rao (State Chief IC, G.O.Ms.No.7,
   18-01-2026) and seven State ICs. Office: 1st Floor, MGM Capital, Chinnakakani, Mangalagiri,
   Guntur Dist. 522503. The Commission for post-bifurcation AP was constituted by
   G.O.Ms.No.111 (11-08-2017). `sic.ap.gov.in`, which returned 403 on 2026-09-04, now answers.
5. **New exemption:** the AP State Directorate of Revenue Intelligence was taken out of RTI by
   G.O.Ms.No.86 (01-09-2022). This adds to the s.24(4) list in G.O.Ms.667 (2007).

## 1. Questions the kept documents answer (one example per type)

| doc_type | Example question | Answered by |
|---|---|---|
| act | "Can I get someone's personal details under RTI now?" | DPDP Act 2023 s.44(3) + G.S.R. 843(E) |
| rules | "For how many years does a State Information Commissioner serve?" | RTI Rules 2019 (3 years) |
| rules | "What is the fee to ask a central office, e.g. a post office in Vijayawada?" | RTI Rules 2012 (central) |
| go | "Can I file RTI online in AP?" | G.O.Ms.25 (2026) |
| go | "Who is the Chief Information Commissioner?" | G.O.Ms.7 (2026), APIC home page |
| go | "Which account is RTI fee paid into?" | G.O.Ms.79 (2020) |
| circular | "The PIO asked me for extra fees. Is that allowed?" | U.O.Note 7490 (2011) *(scan, needs OCR)* |
| manual | "How do I register and pay on the RTI portal?" | RTIMIS Citizen User Manual |
| manual | "How does the Commission hear second appeals?" | APIC 4(1)(b) handbook |
| faq | "What is the time limit? +5 days via APIO? 40 days with a third party?" | APIC Procedure for Request |
| other | "Which commissioner hears appeals for my department?" | APIC work allocation *(scan)* |
| other | "Who is the PIO for agriculture / horticulture in my district?" | Agriculture PIO/APIO/FAA proceedings (Dec 2025); Horticulture PIO & APIO list |

## 2. Common questions they still cannot answer

| Question | Where the answer probably lives |
|---|---|
| Current PIO / FAA for department X in district Y | RTIMIS directory (`rti_ap_info.php`), behind a "Security Verification" step. Found as files only for Agriculture (Dec 2025) and Horticulture. |
| Official sample application / appeal format | No statewide prescribed format found. RTIMIS online form; a few departments publish their own (e.g. APPCB citizen-charter page). |
| Current RTI fee in one table | No consolidated notice exists. The answer still has to be assembled from G.O.Ms.454 + 530 + 545 + 740 (corpus) + 79 (here). |
| Status of a filed request or appeal | RTIMIS (login). |
| Commission decisions and cause lists | `sic.ap.gov.in/sic_be/Template/decisions.php`, `cause_list.php` (not collected). Large, and they contain appellants' names. |
| Whether the s.44(3) DPDP amendment is stayed by a court | Secondary sources report a constitutional challenge. Watch the Supreme Court; nothing official collected. |

## 3. Blocked or broken sources

| URL | Status on 2026-10-04 |
|---|---|
| `https://www.ap.gov.in/api/Files/...` (**every** file the state portal links: all 715 catalogued, including **all 41 source URLs of our current corpus**) | HEAD → 401, GET → 404. The portal's own pages link these same URLs. Not bypassed. Our local copies in `ingest/documents/` are now the only working record. |
| `https://www.ap.gov.in/api-1/Files/Images/Deptaretments/637732731081459218.pdf` (Prisons PIO list) | 404, also on the corrected `api` host |
| Panchayat Raj manual (3 uploads) and Transport R&B manual on ap.gov.in | Unreachable (above). No text edition found anywhere. |
| `https://rtionline.ap.gov.in/templates/layouts/rti_ap_info.php` (PIO/FAA directory) | Security-verification gate. Not bypassed. |
| `https://ncte.gov.in/website/pdf/RTI/RTI(Amendment)Act_2019_24_10_2019.pdf` (2019 commencement notice) | Connect timeout |
| `sic.ap.gov.in` | **Now open** (403 on 2026-09-04). Python needed the OS trust store, because the site sends an incomplete certificate chain. Verification was **not** disabled. |

## 4. Scans and Telugu

- **7 of 27 kept files are scans** with no text version, all marked `needs_ocr`: five GAD
  circulars on fees and receipts, G.O.Ms.86 (APSDRI exemption) and the APIC work allocation.
  Where a scan had a text twin, the twin was kept. G.O.Ms.25 and G.O.Ms.259 are scans on
  their portals but text on GOIR.
- **0 Telugu files kept.** Telugu leads recorded for the multilingual phase: RTI Act (Telugu,
  scan, RTIMIS), IT&C 4(1)(b) Telugu, Planning 4(1)(b) Telugu 2023 (both on the now-unreachable
  ap.gov.in file store).
- 8 kept files predate the June 2014 bifurcation (`pre_bifurcation: true`). G.O.Ms.259 (2008)
  may name Hyderabad Secretariat offices.

## Sources used

`sic.ap.gov.in` (pages, G.O. and circular listings, its `getDataController.php` public data
endpoint) · `rtionline.ap.gov.in` · `goir.ap.gov.in` (GAD search, 2008-2026; results in
`../_catalog/goir_rti.json`) · `cic.gov.in/rti-notifications` · `egazette.gov.in` ·
`meity.gov.in` · `horticulture.ap.gov.in` · `agriculture.ap.gov.in` · `ap.gov.in` JSON API (catalogue in
`../_catalog/apgov.json`).
