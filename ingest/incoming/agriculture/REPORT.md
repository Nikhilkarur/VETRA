# Agriculture — first corpus (collected 2026-10-04)

**27 documents kept** (1,912 pages, 47 MB) · 6 skipped · 2 blocked · 2 leads · 1 broken.
18 are AP state documents, mostly G.O.s found through the AP G.O. register (GOIR,
`../_catalog/goir_agri.json`). 9 are central scheme guidelines (`department: central`).
`build_candidates.py` holds every keep/skip decision. Re-run it, then `collect.py agriculture`.

**Page count warning:** G.O.Ms.80 (PMFBY) alone is 864 pages, almost all district-wise
notified-crop tables. MIDH (327pp) and the PMFBY 2023 guidelines (213pp) are also large.
Consider indexing only the order and operational sections of G.O.Ms.80, or retrieval will
drown in village tables.

## Current scheme names (old → new)

| Today | Before | Evidence |
|---|---|---|
| **Annadatha Sukhibhava – PM Kisan** (Rs.20,000/yr = Rs.14,000 state + Rs.6,000 PM-KISAN; from 02-08-2025) | YSR Rythu Bharosa – PM Kisan (2019-24); called Annadata Sukhibhava in 2014-19 | G.O.Ms.33 (2025) kept; G.O.Ms.96 (2019) kept, marked not in force. The rename itself: press only (Deccan Chronicle, June 2024). G.O.Ms.33 does not say "renamed". |
| **Rythu Seva Kendras (RSK)** | Dr YSR Rythu Bharosa Kendralu (RBK) | Press only (The Hans India, July 2024). **No G.O. found on GOIR**; probably done by memo. Orders up to 2024 still say RBK. |
| **AP Uchita Vyavasaya Vidyut Pathakam** (free farm power) | YSR Uchita Vyavasaya Vidyut Pathakam | **G.O.Rt.No.74, Energy, 19-06-2024** (kept) |
| **e-Panta** (crop booking) | "e-Crop" in older usage | Used in G.O.Ms.80/81 (2024) as the basis of insurance coverage |
| **PMFBY / RWBCIS, voluntary enrolment** (farmer pays premium) | Dr YSR Free Crop Insurance (state paid all premium, 2019 to Kharif 2024) | G.O.Ms.80/81 (2024): free for Kharif 2024 only, then voluntary. Extended to 2026-27 by G.O.Ms.34/35 (06-07-2026). |
| YSR Sunna Vaddi Panta Runalu (interest-free crop loans) | — | G.O.Rt.464 (2020) kept with **in_force: unknown**. No later order found; may be renamed or dropped. |

## 1. Questions the kept documents answer (one example per type)

| doc_type | Example question | Answered by |
|---|---|---|
| scheme_guideline | "I'm a tenant farmer. Do I get the Rs.20,000?" | G.O.Ms.33 (tenants and RoFR cultivators covered; exclusions list) |
| scheme_guideline | "What premium do I pay for paddy insurance?" | PMFBY Operational Guidelines 2023 (2% kharif) + G.O.Ms.34 |
| go | "Is crop insurance still free in AP?" | G.O.Ms.80 (free only for Kharif 2024) + G.O.Ms.34 (2026-27, voluntary) |
| go | "How do I get subsidised seed?" | G.O.Rt.538 (D-Krishi app SOP) |
| go | "How much subsidy for drip irrigation?" | G.O.Rt.82 (2025) + G.O.Rt.206 (2026, FRA patta holders) |
| go | "Where and how do I sell paddy at MSP?" | Civil Supplies G.O.Ms.23 (KMS 2025-26 policy) |
| rules | "How does a tenant get a Crop Cultivator Rights Card?" | G.O.Ms.410 (AP CCR Rules 2019) |
| circular | "What interest do I pay on a crop loan?" | MISS 2025-26 (7%, or 4% with prompt repayment, up to Rs.3 lakh) + RBI KCC master circular |
| manual | "What do Horticulture offices do; whom do I ask?" | Horticulture 4(1)(b) report |
| faq | "My land was transferred after 01-02-2019. Am I eligible for PM-KISAN?" | PM-KISAN Revised FAQ |

## 2. Common questions they still cannot answer

| Question | Where the answer probably lives |
|---|---|
| Agriculture department schemes overview, 4(1)(b) manual, citizen charter | `apagrisnet.gov.in`, **blocked by an expired TLS certificate** (below) |
| Application forms (crop insurance, farm mechanisation, subsidy seed) | ap.gov.in Public Forms (titles recorded), unreachable since the file store returns 401/404 |
| "Has my Annadatha Sukhibhava instalment been paid?" | `annadathasukhibhava.ap.gov.in/know-your-status` (Aadhaar + CAPTCHA; a pointer, not a document) |
| Input subsidy amount for crop lost to flood or cyclone | MHA SDRF/NDRF norms (lead). GOIR has only per-event sanction orders without rates. |
| What a Rythu Seva Kendra offers today | No post-2024 order found. Agriculture department site (blocked) or a memo. |
| Interest-free crop loan scheme status today | Agriculture or Cooperation department; no order after 2021 on GOIR |
| Fertiliser availability and price | Fertiliser SOP for 2024-25 kept (scan); prices are central (Department of Fertilizers) |
| AP Crop Cultivator Rights **Act** text | indiacode.nic.in. **Returned 504 on 2026-10-04**, retry later (recorded as `broken`). |

## 3. Blocked or broken sources

| URL | Status on 2026-10-04 |
|---|---|
| `https://apagrisnet.gov.in/` (Department of Agriculture) | **HTTPS certificate expired** (`SEC_E_CERT_EXPIRED`). Plain HTTP returns 404 for every path. Not bypassed. **Needs your decision** (see below). |
| `https://www.ap.gov.in/api/Files/Images/PublicForm/...` (agriculture and revenue farm forms) | 401 / 404, like every ap.gov.in file |
| `https://www.indiacode.nic.in/bitstream/123456789/19897/1/...crop_cultivator_rights_act,_2019.pdf` | 504 Gateway Timeout (server side) |
| `apmip.ap.gov.in` | DNS does not resolve (APMIP content now lives on horticulture.ap.gov.in) |

**Decision needed:** apagrisnet.gov.in is the department's own site and probably holds the
4(1)(b) manual, citizen charter and scheme pages. The only way in today is to accept an
expired certificate. That weakens the guarantee that the files are genuine, but every saved
file would still be checksummed. I did not do it without asking.

## 4. Scans and Telugu

- **1 of 27 kept files is a scan:** G.O.Rt.288 (fertiliser distribution SOP 2024-25), marked
  for OCR. Every other G.O. on GOIR had a text layer.
- **0 Telugu files.** GOIR offers a Telugu copy (`url_te`) for some orders; none were taken.
- No kept file predates bifurcation.

## Size against the brief's target

27 kept is just under the 30-80 target. The easiest ways to grow it (each adds questions
that come up often): the apagrisnet site if unblocked; the SDRF norms; the AP Crop Cultivator
Rights Act (once indiacode is back); the Telugu GOIR copies for the multilingual phase;
Horticulture's Protected Cultivation and PHM guidelines (skipped for size).
