# VETRA MVP plan

**What we're building:** an assistant for agriculture and finance questions, for every Indian state. Answers are deep, factual and closer to research than to a chatbot reply, with every statement traced to an official document.

**The system has three parts:**

| Part | What it does | In the MVP? |
|---|---|---|
| Agentic engine | Works out what a question needs, finds its way to that information, and answers | **Yes: this is the MVP** |
| Data engineering | Collects, verifies and sorts documents automatically | No. Documents are added by hand with `vetra.intake` |
| Auto-update | Finds missing or new data on the internet and adds it | No. Gaps are logged, so it can plug in later (`GapHandler`) |

RTI stays as it is, on `rag/`. How deep an answer should go for a particular kind of user is decided later.

## Phases

Each phase ends with its tests passing, its documentation updated, and its own commits.

| # | Phase | Done when | State |
|---|---|---|---|
| 0 | **Foundation:** one clean repo, a working Docker image, accurate docs | Tests pass, the image answers a question, and the docs match the code | Done |
| 1 | **Navigation:** the engine judges what it has and goes after what's missing | It can reach an answer that takes more than one step, within a fixed limit, and stops when it has enough | Next |
| 2 | **Depth:** research-style answers | Answers cover conditions, exceptions, changes over time and disagreements between sources, and short questions still get short answers | Not started |
| 3 | **Languages:** all 22 scheduled languages and English | Live checks per language, and documents written in Indian languages can be searched | Code built, not live-tested |
| 4 | **Data:** agriculture and finance for every state | Each state has its main schemes, and its key deadlines and rates are exact records | Started |
| 5 | **Quality and release:** measured on real questions, ready to use | Question sets per topic, a final LLM provider, a safety check, and a person's review of the rules | Not started |

A working API key without the free tier's limits is needed to measure Phases 1 to 3 properly: on the current key, live test runs keep hitting Groq's rate limit.

## Where things stand

### Phase 0: Foundation (done, 4 November 2026)

- **Repo:** one clone, `C:\Users\nkk77\Desktop\VETRA`. No nested copies. Work is on `feat/modular-agent-core`, ahead of `main`, and not pushed yet. `main` matches GitHub.
- **Docker:** the image builds and answered a live deadline question in a container.
- **Tests:** `python -m pytest tests -q`.
- **Older folder:** `Desktop\ap-rti-assistant` is an older copy, and its container uses port 8765, the same port as `docker compose up` here. Stop that container first.

### Phase 3: Languages (code built)

- Questions can come in any of the 22 scheduled languages or English, in the language's own script or typed in English letters.
- English and Telugu facts come from templates. For other languages the model translates them, code rejects any translation that changes a number, and the English original is printed beside it.
- **Known limits:**
  - The search model reads English, so documents written in Indian languages aren't found reliably.
  - RTI replies in English or Telugu only.
  - Some translations have not been read by a speaker of that language.
  - Santali's Ol Chiki script needs a font that many phones lack.

### Phase 4: Data (started)

Run `python -m vetra.intake status agriculture` or `status finance` for the current counts.

| Topic | Have | Missing |
|---|---|---|
| Agriculture | Andhra Pradesh; central documents; a few from Odisha and Himachal Pradesh | The other 33 states and union territories |
| Finance | Union Budget 2026-27, Atal Pension and Income-tax Act explainers; Rajasthan budget notification | The Income-tax Act's full text, stamp duty, vehicle tax, professional tax, pensions, and almost every state |

**Downloads that failed from this network:** incometaxindia.gov.in (403), egazette.gov.in, jansuraksha.gov.in and krishakbandhu.wb.gov.in (connection failed). These may work in a normal browser.

**Set aside:** `documents/_needs_ocr/` holds Maharashtra's PMFBY order for 2026-27. It's in Marathi and its letters are damaged when extracted, so it needs OCR or hand sorting.

### Checked against the orders

The 7 AP deadline windows and the 2 AP premium rules match the text of G.O.Ms.No.34, 35, 80, 81 and 98. This was checked by Claude, not a person, so the rules stay marked `reviewed: false`.

The check found and fixed one real error: each rule gave a rate for crops its scheme doesn't cover, such as cotton under PMFBY. Each rule now lists only its own order's crops, and says so when a crop isn't covered. Which districts a crop is notified in isn't checked yet.
