# State coverage for the MVP

All 36 states and union territories are covered for agriculture and finance, in this order, decided 5 November 2026: first Andhra Pradesh and Tamil Nadu at the deepest level, then Maharashtra and Karnataka, then every other state at medium level.

## How deep each state goes

| Depth | States | What it means |
|---|---|---|
| **Deep** | Andhra Pradesh, Tamil Nadu, Maharashtra, Karnataka | Everything on the checklist below from official sources where possible, with exact dates and rates checked by hand |
| **Partial** | Everywhere else | At least the budget analysis, plus whatever scheme and tax documents can be found. Answers say when a state's own rules aren't held |

## What each state needs

The eight items below are the minimum for every state. Deep states need every aspect in the full lists after them. The status table tracks only the minimum; the deep lists are worked through state by state.

| Code | Topic | Document |
|---|---|---|
| A1 | Agriculture | Crop insurance notification for Kharif 2026 and Rabi 2026-27 |
| A2 | Agriculture | The state's main farmer income or loan scheme |
| A3 | Agriculture | Crop loss and disaster relief norms |
| A4 | Agriculture | Seed, drip and machinery subsidies |
| F1 | Finance | Budget 2026-27 |
| F2 | Finance | Stamp duty and registration rates |
| F3 | Finance | Motor vehicle tax |
| F4 | Finance | Professional tax, or a record that the state has none |

### Deep states: agriculture, all aspects

- **Income and credit:** income support, crop loans, interest subvention, loan waivers, Kisan Credit Card, tenant farmers' credit
- **Risk:** crop insurance by crop and season, disaster relief, drought and flood norms, compensation for wildlife damage
- **Inputs:** seed, fertiliser, pesticides and their quality rules, soil health, organic and natural farming
- **Water and power:** drip and sprinkler, farm ponds, wells, free or subsidised farm power, solar pumps
- **Machinery:** farm equipment subsidies, custom hiring, drones
- **Crops and allied work:** horticulture, plantation, sericulture, animal husbandry, dairy, fisheries, poultry
- **Selling:** minimum support price, state bonus, procurement, regulated markets, eNAM, storage, food processing, farmer producer organisations
- **Land:** land records, tenancy, land conversion, land acquisition compensation
- **Support and complaints:** extension offices, helplines, farmer welfare boards and pensions, grievance routes

### Deep states: finance, all aspects

- **State budget:** budget, debt, departmental allocations, finance commission grants
- **State taxes and fees:** stamp duty, registration, guideline values, motor vehicle tax, profession tax, state GST rules, land revenue, electricity duty, property tax
- **Relief for individuals:** tax arrears schemes, concessions for women, farmers and others
- **Pensions and welfare money:** state pensions, social security, direct benefit schemes
- **Loans and support:** state-run loans, self-help groups, cooperatives, MSME and self-employment schemes, housing

### Central rules every state relies on

- **Tax:** Income Tax Act 2025, GST, TDS, ITR dates and forms
- **Savings and pensions:** PPF, Sukanya Samriddhi, NPS, Atal Pension, EPF, PM Shram Yogi Maandhan, and small savings rates
- **Banking and insurance:** RBI customer rules, loans, Jan Dhan, PM Jeevan Jyoti and Suraksha Bima, Mudra, PMEGP, grievance ombudsmen
- **Agriculture:** PM-KISAN, PMFBY, KCC, MSP, seeds, fertiliser and pesticide laws, PMKSY, RKVY, Agriculture Infrastructure Fund

**Limit:** this covers rules, rates, eligibility and procedures from official sources. VETRA doesn't recommend which stock, fund or insurance product to buy, or calculate pesticide doses.

## Which source counts

Use the first one available, and label it in the manifest, because answers show the kind of source.

1. Official order, act or gazette.
2. Official web page or scheme guideline.
3. Trusted summary, such as PRS or PIB, marked as not official.
4. Nothing: answers say it isn't held, and the gap is logged. Blogs and insurers' marketing pages don't count.

## Where things stand

✅ held and searchable. 📥 downloaded, not yet in search. ⬜ not collected. Run `python -m vetra.intake status agriculture` or `status finance` for chunk counts.

| State or UT | Depth | A1 | A2 | A3 | A4 | F1 | F2 | F3 | F4 |
|---|---|---|---|---|---|---|---|---|---|
| Andhra Pradesh | Deep | ✅ | ✅ | ✅ | ✅ | 📥 | ✅ | ✅ | ✅ partial |
| Tamil Nadu | Deep | 📥 partial | 📥 partial | 📥 partial | 📥 partial | 📥 | 📥 partial | ✅ | ✅ Chennai only |
| Maharashtra | Deep | ⬜ | ⬜ | ⬜ | ⬜ | 📥 | ⬜ | ⬜ | ⬜ |
| Karnataka | Deep | ⬜ | ⬜ | ⬜ | ⬜ | 📥 | ⬜ | ⬜ | ⬜ |
| Odisha | Partial | ⬜ | ✅ | ⬜ | ✅ | 📥 | ⬜ | ⬜ | ⬜ |
| Rajasthan | Partial | ⬜ | ⬜ | ⬜ | ⬜ | 📥 | ✅ | ✅ | ⬜ |
| Himachal Pradesh | Partial | ✅ | ⬜ | ⬜ | ⬜ | 📥 | ⬜ | ⬜ | ⬜ |

**Budget analysis downloaded (F1 📥), nothing else yet:** Arunachal Pradesh, Assam, Bihar, Chhattisgarh, Delhi, Goa, Gujarat, Haryana, Jammu and Kashmir, Jharkhand, Kerala, Madhya Pradesh, Manipur, Meghalaya, Mizoram, Nagaland, Puducherry, Punjab, Sikkim, Telangana, Tripura, Uttar Pradesh, Uttarakhand, West Bengal.

**Nothing yet:** Andaman and Nicobar Islands, Chandigarh, Dadra and Nagar Haveli and Daman and Diu, Ladakh, Lakshadweep. PRS has no 2026-27 analysis for these.

Himachal Pradesh's A1 is only the central ministry's letter on its site, not the state's own notification. Puducherry's analysis is short, about 2,000 characters. PRS's terms for using its summaries in a product haven't been checked.

## What's still open for the first two states

**Tamil Nadu**
- **Crop insurance:** the policy note confirms the scheme and the Rs.648.55 crore outlay, but gives no cut-off dates. The 2026-27 notification is still needed.
- **Stamp duty:** done from the official Duty and Fees page: 7% stamp duty and 2% registration fee on a sale. The page is undated, so the 2023 gazette change and any later one should be compared with it. It has about 180 rows; only the main table is saved so far. Eighteen rates are now exact records in knowledge/finance/numbers.jsonl, marked not yet reviewed by a person.
- **Vehicle tax:** new-vehicle life tax is in as exact records from the 2023 bill's gazette copy: motor cycles 10% and 12%, other vehicles 12%, 13%, 18%, 20%. Press reports say it took effect on 9 November 2023. The enacted copy, old-vehicle rates and any change after 2023 aren't checked.
- **Profession tax:** Chennai's slabs are exact records from the Corporation's press release of 4 August 2026 (Rs.180, 425, 930, 1,025, 1,250 half-yearly). Other local bodies are open.

- **Other department notes, 2026-27:** agriculture, disaster relief, fisheries, dairy, cooperation, food, water resources, energy, rural development, MSME, social welfare, stamps, commercial taxes, finance, pensions, municipal and transport are held. Animal husbandry's note was found by guessing the name (`ah_e_pn_2026_27.pdf`); the first downloads timed out, so check it's complete before building. These notes describe schemes, so their rates still have to be read by hand before becoming exact records.

- **Relief rates:** G.O.(Ms).No.579 of 2023 is held, with its input subsidy rates as exact records. It was read from a scan, with 6 figures marked unclear across the order, so it needs a person's check. A special order may set a higher figure for a particular disaster, such as Rs.20,000 per hectare reported for Cyclone Ditwah.

**Andhra Pradesh**
- **Vehicle tax:** aptransport.org's life tax pages show the 2010 rates, so don't use them. Current rates are exact records from L.A. Bill 23 of 2021 (a scan, read by eye): motor cycles 9% and 12%, cars 13%, 14%, 17%, 18%. The date it took effect isn't held. The bill says the rates were last revised in 2010. Road Safety Cess is 10% of life tax from 13 January 2026 (Ordinance 1 of 2026, Tenth Schedule). The press reports the replacing bill passed; no official copy of the act yet. Used-vehicle rates aren't entered.
- **Stamp duty:** sale deed settled by the state's live calculator on 5 November 2026: 5% stamp duty, 1.5% transfer duty, 1% registration fee, Rs.500 user charges. This agrees with CAG. The IGRS PDFs still show 4% and 0.5%, so don't trust them on these rates. Gift, settlement, release, partition, exchange, mortgage, sale agreement, development agreement and will were read from the calculator on 5 November 2026 and are exact records. A first fast sweep gave stale results, so only rows re-read slowly at three values were saved. **Still open:** lease (the calculator shows 0 for it, so it needs more input than the form asks) and power of attorney (the readings didn't agree).
- **Profession tax:** salary slabs are exact records, read from the text of Act 12 of 2013 on a legal site, not yet an official copy: nil up to Rs.15,000, Rs.150 to Rs.20,000, Rs.200 above. The 2020 amendment's first page shows no rate change, but it should be read in full. Other classes of taxpayer aren't entered yet.
- **Budgets:** Budget Speech, Budget in Brief, Outcome Budget and agriculture estimates are held. The separate agriculture budget speech isn't found yet.
- **Relief rates:** G.O.Ms.No.1 of 7 January 2025 sets higher rates by crop for future calamities until further orders (paddy Rs.25,000 per hectare, was Rs.17,000), now exact records. It says these are over and above SDRF norms; I've recorded the enhanced column as the rate paid, not an addition, which a person should confirm. Whether the Rs.10,000 poultry ceiling still applies is unclear.
- **Agriculture:** existing orders haven't been checked for newer ones. The separate agriculture budget (Rs.53,752 crore per press) speech file isn't on apfinance's budget page; Volume-III-11 has the department's estimates. apagrisnet.gov.in has an expired security certificate, so it wasn't used.

## Only your browser can download

Nothing right now.

## Sites that responded on 5 November 2026

- **Responded:** pmfby.gov.in, krishi.maharashtra.gov.in, gr.maharashtra.gov.in, igrmaharashtra.gov.in, raitamitra.karnataka.gov.in, samrakshane.karnataka.gov.in, transport.karnataka.gov.in, tnagrisnet.tn.gov.in, tnreginet.gov.in, indiacode.nic.in, prsindia.org.
- **Tamil Nadu fees:** the Duty and Fees table on tnreginet.gov.in only appears after the page calls showDutyFeesPage(), so it needs the browser.
- **Tamil Nadu's best source:** tn.gov.in/document_dept_list.php lists each department's yearly policy notes, budget speeches and charters. Its pages need a browser to show links, and the PDFs on cms.tn.gov.in download normally. Most state portals may have an equivalent, so check before searching the web.
- **Plain HTTP only:** tnsdma.tn.gov.in has no secure version, so use http://.
- **Failed from this network:** igrs.karnataka.gov.in, kaverionline.karnataka.gov.in, mahatax.maharashtra.gov.in, upagripardarshi.gov.in. These may work in a normal browser.
