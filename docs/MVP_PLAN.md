# VETRA MVP plan

**What we're building:** an assistant for agriculture and finance questions, for every Indian state. Answers are deep, factual and closer to research than to a chatbot reply, with every statement traced to an official document.

**The system has three parts:**

| Part | What it does | In the MVP? |
|---|---|---|
| Agentic engine | Works out what a question needs, finds its way to that information, and answers | **Yes: this is the MVP** |
| Data engineering | Collects, verifies and sorts documents automatically | No. Documents are added by hand with `vetra.intake` |
| Auto-update | Finds missing or new data on the internet and adds it | No. Gaps are logged, so it can plug in later (`GapHandler`) |

RTI stays as it is, on `rag/`. How deep an answer should go for a particular kind of user is decided later.

How the design compares with published work, and what to adopt next, is in [ARCHITECTURE_RESEARCH.md](ARCHITECTURE_RESEARCH.md). In short, the engine's structure holds up, and the biggest gains left are in what the search reads.

## Phases

Each phase ends with its tests passing, its documentation updated, and its own commits.

| # | Phase | Done when | State |
|---|---|---|---|
| 0 | **Foundation:** one clean repo, a working Docker image, accurate docs | Tests pass, the image answers a question, and the docs match the code | Done |
| 1 | **Navigation:** the engine judges what it has and goes after what's missing | It can reach an answer that takes more than one step, within a fixed limit, and stops when it has enough | Built. Measuring it needs a new API key |
| 2 | **Depth:** research-style answers | Answers cover conditions, exceptions, changes over time and disagreements between sources, and short questions still get short answers | Built. Search measured; answer quality needs a new API key |
| 3 | **Languages:** all 22 scheduled languages and English | Live checks per language, and documents written in Indian languages can be searched, using a multilingual embedding model that beats today's scores | Code built. Hindi and Tamil tried live on exact facts |
| 4 | **Data:** agriculture and finance for every state | Each state has its main schemes, its key deadlines and rates are exact records, PDFs are read properly including tables and scans, and chunks carry context from their document | Started |
| 5 | **Quality and release:** measured on real questions, ready to use | Question sets per topic, a final LLM provider, a safety check, and a person's review of the rules | Not started |

A working API key without the free tier's limits is needed to measure Phases 1 to 3 properly: on the current key, live test runs keep hitting Groq's rate limit.

## Where things stand

### Phase 0: Foundation (done, 4 November 2026)

- **Repo:** one clone, `C:\Users\nkk77\Desktop\VETRA`. No nested copies. Work is on `feat/modular-agent-core`, ahead of `main`, and not pushed yet. `main` matches GitHub.
- **Docker:** the image builds and answered live questions in a container. It was built before Phase 1, so rebuild it to include navigation.
- **Tests:** `python -m pytest tests -q`.
- **Older folder:** `Desktop\ap-rti-assistant` is an older copy, and its container uses port 8765, the same port as `docker compose up` here. Stop that container first.

### Phase 1: Navigation (built, not measured)

- After the first look, a model judges whether the evidence answers every part of the question. If not, it searches in other words or reads the passages around one it found, for up to 2 rounds. See `vetra/navigate.py` and "Finding its way" in [AGENT.md](AGENT.md).
- Every path is covered by tests with a fake model.
- **First live try (3 questions needing searched text):** the judge stopped when it had enough, and on the multi-part PM-KISAN question it read further and named what was still missing. None of these reached a written answer, because the answer model hit Groq's rate limit each time.
- **Not known yet:** how much this improves answers. It costs one more LLM call per searched question, so it needs the new API key to measure.
- **To finish the phase:** a set of questions that take more than one step, run with this step on and off.

### Phase 2: Depth (built, answer quality not measured)

How it works is in "How deep an answer goes" and "How an answer is checked" in [AGENT.md](AGENT.md).

| What was measured, with no LLM | Result |
|---|---|
| Parts of a deep question reached by one search, as before | 40 of 59 |
| Parts reached by searching each part on its own | 55 of 59 |
| Time for a deep question's searches | About 7 seconds |

Measuring also overturned two of my own design choices. Adding the scheme's name as a search vote reached fewer parts (53 against 58), so a part is now searched alone. The slow reranking step added nothing for part searches (56 with it off, 55 with it on, about 50 times faster), so it's off there.

**Reading real answers found more:** the writer mentioned its own prompt ("the EXACT record", "the evidence provided"), so that's now a fault code catches. The second reader wasn't shown the notes behind exact records, so it flagged correct sentences, and that's fixed. It did catch a real error in the same run: "the central government sets the premium rates".

A second run was worse: the writer printed its working notes ("Wait, [E5] is PM-KMY...") and mixed in another scheme's exclusions. Code now rejects working notes, the writer and second reader are both told not to carry rules across schemes, and the second reader now also reads an answer that had a sentence cut.

After these fixes, the same PM-KISAN question gave a clean, correct answer at the standard level. Three other real runs didn't finish cleanly: a Hindi brief stopped at the daily limit after printing its translated records, and two runs on the free tier had their evidence cut to 7 to 12 passages. One of those, on Atal Pension, lost a mostly good answer to a rewrite with no citations, which is also fixed. **No deep answer has yet been read with all the fixes and full evidence.**

**Bugs this phase found and fixed:**
- A scanned FAQ and flood order read "/-" as "1", so Rs.6000/- appeared as Rs.60001, ten times too big. These are corrected, and any new scan should be watched for the same fault.
- A rupee amount written "Rs.6000" was compared as ".6000", which wrongly rejected correct answers.
- Scans break dates up ("1 .6.2019"), and a year inside a written date ("28.02.2027") wasn't counted, so correct sentences were cut.
- A sentence containing "w.e.f." was split in two, leaving a broken fragment when one half was cut.

**Limits:**
- The 59-part test uses a split written by hand, and the settings were tuned on it, so real numbers will be somewhat lower.
- The planner's prompt changed, so its earlier 32 of 33 score needs re-measuring: `python eval/needs_eval.py --live`.
- The checks catch invented figures and dates. Only deep answers get a second reader for wrong wording, and how well it works is unmeasured.
- A deep answer is expensive: one real test used about 41,000 tokens, with the evidence cut to 12 passages to fit the free tier. A free tier allows only a few a day.

**To finish the phase, with the new API key:**
1. `python eval/depth_eval.py --planner --live` and `python eval/needs_eval.py --live`, to check the planner.
2. `python eval/agent_answers.py --show`, then read the deep answers.
3. Score about 20 real questions with a judge: factual accuracy, citation accuracy, completeness and source quality.

### Phase 3: Languages (code built)

- Questions can come in any of the 22 scheduled languages or English, in the language's own script or typed in English letters.
- English and Telugu facts come from templates. For other languages the model translates them, code rejects any translation that changes a number, and the English original is printed beside it.
- **Known limits:**
  - The search model reads English, so documents written in Indian languages aren't found reliably.
  - RTI replies in English or Telugu only.
  - Translations can get terms wrong, and only numbers are checked by code. In a live test, "actuarial rate" came out in Hindi as a word meaning "enacted rate". That's why the English is printed beside each fact, and a speaker of each language should check before release.
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
