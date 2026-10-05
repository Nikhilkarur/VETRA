# ingest/incoming — staging area for new documents

Built against `docs/DATA_COLLECTION_BRIEF.md`. Files move to `ingest/documents/` only after
review. **Exception:** the assistant's agriculture domain is indexed directly from
`agriculture/` (since 2026-10-04); the other folders are not indexed.

| Folder | State (2026-10-04) | Read first |
|---|---|---|
| `rti/` | 27 kept, gaps filled | `rti/REPORT.md` |
| `agriculture/` | 46 kept; **indexed and live** (44 with text, 2 scans wait for OCR) | `agriculture/REPORT.md` |
| `finance/` | **deferred**: scope proposal only; will be split into subcategories later | `finance/REPORT.md` |
| `questions/` | 71 FAQ questions + PGRS FAQ page | `questions/REPORT.md` |
| `_catalog/` | raw search results: ap.gov.in API catalogue (715 file links), agriculture.ap.gov.in catalogue (825), GOIR searches | — |

Each domain folder has the files, `manifest.json` (kept files with the brief's fields plus
`pre_bifurcation`, `needs_ocr` and `notes`), `inventory.json` (every candidate with its
decision: keep / skip / lead / blocked / broken / proposed) and `candidates.json` (the human
judgement the other two are generated from).

## How the collection works (re-runnable)

The tools are in `ingest/collect/`. Judgement goes in `candidates.json`; everything
mechanical is computed.

```bash
python ingest/collect/catalog_apgov.py              # catalogue every file the ap.gov.in API links
python ingest/collect/catalog_agri.py               # catalogue agriculture.ap.gov.in (825 files)
python ingest/collect/goir.py --dept AGLC --text "crop insurance" --from 01-01-2019 --to 04-10-2026 --out agri
python ingest/incoming/agriculture/build_candidates.py   # agriculture judgement -> candidates.json
python ingest/collect/collect.py agriculture        # download kept files, write manifest + inventory
python ingest/incoming/questions/build_questions.py # rebuild questions.json from the live FAQs
```

- **`goir.py`** searches the AP Government Orders Issue Register (every G.O. since June 2008,
  by department, number, date and abstract text). It was the most productive source by far.
  No login or CAPTCHA is involved. Results are capped per query (about 50-100), so use
  `--by-year` for broad terms. Department codes: AGLC agriculture, GAD, FIN, REV, DM, FCS,
  PR, TRB, …
- **`collect.py`** derives the file name (slug + `--` + sha256[:8], the same convention as
  `ingest/documents/`), checksum, pages, text layer and language (handles bilingual
  Hindi/English gazettes and legacy-font Telugu). It never retries a 401/403/404, and it
  refuses to write into `ingest/documents/`. Re-running skips files already on disk.
- HTTPS uses the OS trust store (`truststore`, which ships inside pip) because several gov.in
  sites send incomplete certificate chains. Verification is switched off only for hosts listed
  in `UNVERIFIED_TLS` in `common.py`, each approved by the project owner with the evidence
  recorded, and every file from such a host carries that note in `manifest.json`. Today the
  only entry is apagrisnet.gov.in, and nothing was saved from it (the site is retired).

## Before indexing (open decisions)

1. ~~apagrisnet.gov.in~~: resolved. Certificate accepted as approved; the site is retired
   (403 on every path) and the department now publishes on agriculture.ap.gov.in (collected).
2. **Finance**: deferred by the owner; planned as one domain with subcategories (see the brief's "Status").
3. **OCR**: 9 kept scans (7 RTI, 2 agriculture) are marked `needs_ocr`.
4. **G.O.Ms.80 (864pp)**: index only its order and operational pages.
5. **ap.gov.in file store** returns 401/404 for every file, including the 41 current corpus
   sources. The corpus's `source_url`s no longer resolve.
