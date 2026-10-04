# Agriculture — first corpus (collected 2026-10-04)

**46 documents kept** (2,447 pages, 82 MB) · 8 skipped · 6 leads · 2 broken · 1 blocked.
Within the brief's 30-80 target. 29 are AP state documents and 17 are central acts or
guidelines (`department: central`). Sources: GOIR, the AP G.O. register (17); the
department's current site agriculture.ap.gov.in (18); pmkisan / pmfby / rbi / nhb (9);
horticulture.ap.gov.in (2). `build_candidates.py` holds every keep/skip decision. Re-run
it, then `collect.py agriculture`.

**Page count warning:** G.O.Ms.80 (PMFBY, 864pp) is almost all district-wise notified-crop
tables; the Agriculture 4(1)(b) manual (263pp), MIDH (327pp) and the PMFBY 2023 guidelines
(213pp) are also large. Index only the order and operational sections of G.O.Ms.80, or
retrieval will drown in village tables.

## The department's website moved

- **apagrisnet.gov.in is retired, not just misconfigured.** As you approved, I accepted its
  bad certificate for that one host. The certificate turned out to be issued to a different
  site (aptribes.gov.in, expired June 2022), on a NIC Hyderabad server (164.100.187.11).
  Behind it, Apache returns **403 "Server unable to read htaccess file"** on every path, to
  every client. No file was downloaded from it.
- **The current site is agriculture.ap.gov.in** (valid certificate). It is a JavaScript app.
  `ingest/collect/catalog_agri.py` reads its document API and lists all 825 files
  (`_catalog/agri_site.json`). Downloads come from `staging/api/comm/files/download/<id>`.

## Current scheme names: the official table (G.O.Ms.79, 02-09-2024)

| Old name | Current name |
|---|---|
| e-Crop App | **e-Panta** |
| YSR Rythu Bharosa – PM Kisan | **Annadata Sukhibhava** (Rs.20,000/yr = Rs.14,000 state + Rs.6,000 PM-KISAN; guidelines G.O.Ms.33, 01-08-2025) |
| YSR Sunna Vaddi Panta Runalu | **Vaddi Leni Runalu** (interest-free crop loans; only guidelines found are the 2020 ones, G.O.Rt.464) |
| Dr. YSR Free Crop Insurance | **PMFBY**, voluntary enrolment from Rabi 2024-25 (G.O.Ms.80/81), extended to 2026-27 (G.O.Ms.34/35) |
| YSR Yantra Seva Padhakam | **Farm Mechanization Scheme** (SMAM guide kept) |
| YSR Yantra Seva Kendram | **Village / Cluster CHCs** |
| Dr. YSR Agri Testing Laboratories | **Integrated Agri-Labs** |
| Rythu Bharosa Kendram (RBK) | **Rythu Seva Kendram (RSK)** (founding order G.O.Ms.37, 2020, kept) |
| YSR App | VAA Performance Monitoring App |
| RBK Channel/Studio; "Dr. YSR Rythu Bharosa" magazine | Paadi Pantalu Channel/Studio; "Paadi Pantalu" magazine |

Also renamed, by a separate order: **YSR Uchita Vyavasaya Vidyut Pathakam → AP Uchita
Vyavasaya Vidyut Pathakam** (free farm power, G.O.Rt.74, Energy, 19-06-2024).

## 1. Questions the kept documents answer (one example per type)

| doc_type | Example question | Answered by |
|---|---|---|
| scheme_guideline | "I'm a tenant farmer. Do I get the Rs.20,000?" | G.O.Ms.33 (tenants and RoFR cultivators covered; exclusions) |
| go | "What is Rythu Bharosa called now?" | G.O.Ms.79 (2024) |
| go | "Is crop insurance still free?" | G.O.Ms.80 (free only for Kharif 2024) + G.O.Ms.34 (2026-27, voluntary) |
| go | "My crop was lost in the cyclone. How much relief do I get?" | G.O.Ms.1 Revenue (DM) 2023 (SDRF norms) + G.O.No.2 (2025, enhanced rates) + department note |
| go | "Where and how do I sell paddy at MSP?" | Civil Supplies G.O.Ms.23 (KMS 2025-26) |
| circular | "What does subsidised groundnut seed cost this Kharif?" | Seed subsidy memo 2026-27 |
| circular | "What interest do I pay on a crop loan?" | MISS 2025-26 (4% with prompt repayment, up to Rs.3 lakh) + RBI KCC master circular |
| rules | "How does a tenant get a Crop Cultivator Rights Card?" | G.O.Ms.410 (AP CCR Rules 2019) |
| rules / act | "The seed I bought didn't germinate. What can I do?" | Seeds Act 1966, Seeds Rules 1968, Seed Control Order 1983 |
| manual | "How do I apply for a subsidised farm machine?" | SMAM farmer registration guide (eseed.ap.gov.in/FM) |
| manual | "What does the Agriculture department do; whom do I ask?" | Agriculture 4(1)(b) manual 2025-26 |
| faq | "My land was transferred after 01-02-2019. Am I eligible for PM-KISAN?" | PM-KISAN Revised FAQ |

## 2. Common questions they still cannot answer

| Question | Where the answer probably lives |
|---|---|
| Application forms (crop insurance, subsidy seed, farm mechanisation) | ap.gov.in Public Forms (titles recorded), unreachable since the file store returns 401/404. Most applications are now online (D-Krishi, eseed FM portal, RSK). |
| "Has my Annadatha Sukhibhava instalment been paid?" | `annadathasukhibhava.ap.gov.in/know-your-status` (Aadhaar + CAPTCHA; a pointer, not a document) |
| Current Vaddi Leni Runalu rules (post-2024) | Only the 2020 guidelines exist online. Agriculture or Cooperation department. |
| What a Rythu Seva Kendram offers today | G.O.Ms.37 (2020) describes RBK services; no post-rename order on services found |
| Implement prices after subsidy | Farm Mechanization approved price list 2025-26 (lead: 106-page table) |
| Annadatha Sukhibhava FAQ | Exists only in **Telugu** on agriculture.ap.gov.in, in a legacy font (lead) |
| AP Crop Cultivator Rights **Act** text | indiacode.nic.in, **504 on 2026-10-04**; retry later |

## 3. Blocked or broken sources

| URL | Status on 2026-10-04 |
|---|---|
| `https://apagrisnet.gov.in/` (old department site) | Retired: certificate for another domain (expired 2022), then 403 "unable to read htaccess file" on every path, for every client. Replaced by agriculture.ap.gov.in. |
| `https://www.ap.gov.in/api/Files/Images/PublicForm/...` (agriculture and revenue farm forms) | 401 / 404, like every ap.gov.in file |
| `https://www.indiacode.nic.in/bitstream/123456789/19897/1/...crop_cultivator_rights_act,_2019.pdf` | 504 Gateway Timeout (server side) |
| agriculture.ap.gov.in: ATMA.pdf (2 files), Digital Agriculture Mission guidelines | 404 on the site's own download API |
| `apmip.ap.gov.in` | DNS does not resolve (APMIP content is on horticulture.ap.gov.in) |

## 4. Scans and Telugu

- **2 of 46 kept files are scans** (marked for OCR): G.O.Rt.288 (fertiliser distribution SOP
  2024-25) and the FCO amendment instructions of 20-12-2024. Where a scan had a text twin
  (e.g. G.O.Ms.79), the text copy was kept.
- **0 Telugu files kept; 5 Telugu leads recorded**: Agriculture 4(1)(b) manual (Telugu),
  Annadatha Sukhibhava FAQ, PM-KISAN FAQ, input-subsidy note, plus the department's Telugu
  magazines and almanacs (catalogued). GOIR also offers Telugu copies (`url_te`) for some
  orders.
- No kept AP order predates bifurcation. The central Acts (1966-1985) have no `date` set.
