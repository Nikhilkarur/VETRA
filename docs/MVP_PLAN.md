# VETRA MVP plan

**What we're building:** an assistant for agriculture and finance questions, for every Indian state. Answers are deep, factual and closer to research than to a chatbot reply, with every statement traced to an official document.

**The system has three parts:**

| Part | What it does | In the MVP? |
|---|---|---|
| Agentic engine | Works out what a question needs, finds its way to that information, and answers | **Yes: this is the MVP** |
| Data engineering | Collects, verifies and sorts documents automatically | No. Documents are added by hand with `vetra.intake` |
| Auto-update | Finds missing or new data on the internet and adds it | No. Gaps are logged, so it can plug in later (`GapHandler`) |

RTI stays as it is, on `rag/`. How deep an answer should go for a particular kind of user is decided later.

Which LLM provider to use, what it costs and how to pay is in [LLM_PROVIDERS.md](LLM_PROVIDERS.md). How the design compares with published work, and what to adopt next, is in [ARCHITECTURE_RESEARCH.md](ARCHITECTURE_RESEARCH.md). In short, the engine's structure holds up, and the biggest gains left are in what the search reads.

## Phases

Each phase ends with its tests passing, its documentation updated, and its own commits.

| # | Phase | Done when | State |
|---|---|---|---|
| 0 | **Foundation:** one clean repo, a working Docker image, accurate docs | Tests pass, the image answers a question, and the docs match the code | Done |
| 1 | **Navigation:** the engine judges what it has and goes after what's missing | It can reach an answer that takes more than one step, within a fixed limit, and stops when it has enough | Built. Measuring it needs a new API key |
| 2 | **Depth:** research-style answers | Answers cover conditions, exceptions, changes over time and disagreements between sources, and short questions still get short answers | Built. Search measured; answer quality needs a new API key |
| 3 | **Languages:** all 22 scheduled languages and English | Live checks per language, and documents written in Indian languages can be searched | Built and measured. Search model switched to E5-base. Documents in Indian languages still need OCR and a person's check |
| 4 | **Data:** agriculture and finance for every state: deep for Andhra Pradesh, Tamil Nadu, Maharashtra and Karnataka, partial elsewhere | Every state has its checklist items held or logged as gaps, the deep states' deadlines and rates are exact records, and scans are read reliably | Started. Andhra Pradesh agriculture and central schemes held; PRS budgets downloaded for 31 states and UTs |
| 5 | **Quality and release:** measured on real questions, ready to use | Question sets per topic, a final LLM provider, a safety check, and a person's review of the rules | Not started |

Live tests now run on Gemini's free tier. Its models are often busy, so writing often falls back to a cheaper model.

## Where things stand

### Phase 0: Foundation (done, 4 November 2026)

- **Repo:** one clone, `C:\Users\nkk77\Desktop\VETRA`. No nested copies. Work is on `feat/modular-agent-core`, ahead of `main`, and not pushed yet. `main` matches GitHub.
- **Docker:** the image builds and answered live questions in a container. Rebuilt on 4 November with Phases 0 to 2 and the Phase 3 work so far, and it runs healthy at http://localhost:8765. Docker Desktop stopped opening that day because Windows wouldn't remove leftover socket files: see "If Docker won't open" in the knowledge base's Run it tab.
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

### Phase 3: Languages (built and measured)

- Questions can come in any of the 22 scheduled languages or English, in the language's own script or typed in English letters.
- English and Telugu facts come from templates. For other languages the model translates them, code rejects any translation that changes a number, and the English original is printed beside it.
- **Known limits:**
  - Search now uses E5-base, which reads Indian languages, but still found only 12 of 20 Marathi test questions. Rebuilding the index takes about 39 minutes on this laptop, and the Docker build has to do it too.
  - RTI replies in English or Telugu only.
  - Translations can get terms wrong, and only numbers are checked by code. In a live test, "actuarial rate" came out in Hindi as a word meaning "enacted rate". That's why the English is printed beside each fact, and a speaker of each language should check before release.
  - Santali's Ol Chiki script needs a font that many phones lack.

**Measured on 5 November 2026 (Gemini, E5-base search):**

| Test | Result | How far to trust it |
|---|---|---|
| Planner: language, in 22 languages and English | 31/32, only Dogri missed | Prompt hints overlap some test words |
| Planner: topic, state, needs | 32/33, 30/33, 33/33 | Needs are scored loosely |
| Planner: depth level | 26/27 | Tuned on these questions |
| 16 real answers, known cases | 16/16 pass | Text guards only, so answers were also read by hand. Writing fell back to Gemini 3.5 Flash-Lite in most of the runs, because 3.8 timed out or was refused |
| Search, E5-base | Marathi 12/20, AP 82/93, deep parts 54/59, about 5s a deep question | bge-small scored 9/20, 80/93, 55/59, 3.9s. These gaps are too small to prove anything |
| Search with the reranker off | AP 75/93, Marathi 12/20 | Kept on |
| Second reader, 16 planted statements in English, Hindi and Telugu | 9/9 false caught, 0/7 false alarms, with or without the new rules | Too easy to show a difference, so the new rules are unproven |

**Head-to-head, 32 questions, read by hand:**

| Group | VETRA | Gemini from memory | Claude Haiku with web search |
|---|---|---|---|
| 22 questions VETRA holds documents for | **21 right, 1 "not found", 0 wrong** | 10 right, 9 "can't say", 3 wrong | 13 right (2 hedged), 9 "couldn't confirm", 0 wrong |
| 4 questions on states it doesn't hold | 0 answered, 4 honest "not found" | **4 right** | **4 right** |
| 3 real gaps | 3 admitted | 2 admitted, 1 unchecked figure stated | 2 admitted, 1 unchecked figure stated with a warning |
| 3 invented schemes | 3 admitted | 3 admitted | 3 admitted |
| Tokens a question | About 5,900 | About 200 | About 3,600 |

- **Don't quote 21/22 as a score.** On its first run VETRA got 17 right, 1 "not found" and 4 wrong. Reading those answers found real bugs, which were fixed and re-run on the same questions, so expect lower on new ones.
- **Bugs this found and fixed:** a question about Kharif 2026 got Rabi dates; a question about another scheme got the crop insurance premium rule printed as its answer; a timeout said "busy" instead of trying the next model; and answers pointed to "the amount stated above" when nothing was printed above.
- **What it shows:** VETRA wins where it holds the documents, especially exact dates and orders that a model can't know. A model with web search wins on states VETRA doesn't hold yet, so coverage is the biggest thing missing.
- **West Bengal's expected answer was changed** from ₹5,000 to ₹10,000 per acre after checking: press reports say it was doubled, while official documents found still show ₹5,000, so the current order is unconfirmed.
- **Gemini with Google Search couldn't be tested:** the free tier refused it, so Claude Haiku filled that arm.

**What to do next, ranked with evidence:** [the research report](../reports/VETRA%20engine%20techniques%202026.md). The first three are a hand-read test of 150 to 200 questions, start and end dates on rules, and reading figures from scans reliably.

### The plan from here (5 November 2026)

**Scope:** all 36 states and union territories, for agriculture and finance, in three parts: first Andhra Pradesh and Tamil Nadu at the deepest level, then Maharashtra and Karnataka, then every other state at medium level. The engine keeps improving alongside, wherever results show a real need. Automated data engineering stays out of the MVP, so documents are collected by hand. The checklist and progress are in [STATE_COVERAGE.md](STATE_COVERAGE.md).

| Step | Work | Done when | Needs you? |
|---|---|---|---|
| 1 | **Baseline:** finish the 179-question test and mark every answer | Scores by group and language, with every wrong answer listed | Your sample check |
| 2 | **Fix what the baseline exposes,** then re-run and compare | Wrong answers explained and fixed, and the comparison shows whether it really helped | No |
| 3 | **Check Docker** with the new search model | The rebuilt image answers the cashew question correctly | Keep the build running |
| 4 | **Load PRS budgets** for 31 states and UTs | Each state's budget questions find its own document | No |
| 5 | **Scan reading:** Gemini reads, Tesseract checks every number, disagreements go to a third read | Tested on 150-200 pages with figures labelled by hand, including Marathi and Tamil | Paid Gemini if free limits block it |
| 6 | **Deep states:** the full checklist for Tamil Nadu, then Maharashtra, then Karnataka, and finance for Andhra Pradesh | Every checklist item held or logged as not found, with exact dates and rates read by hand. Each state gets its own test questions | Browser downloads for sites blocked here |
| 7 | **Partial states:** crop insurance and the main farmer scheme, then stamp duty, vehicle tax and professional tax | At least the budget plus what can be found, with gaps logged. Biggest farming states first | Same |
| 8 | **Dates on rules:** start and end dates, and the question's date used in the filter | New date tests pass, and replaced orders stop answering current questions | No |
| 9 | **Chunks:** a fixed line naming state, scheme and order, and splits at numbered paragraphs, in one rebuild. Also try Gemini embeddings | Scores don't fall on the baseline. Rebuilds stay practical as documents grow | No |
| 10 | **Release gates:** safety rules, wording that doesn't imply an official service, spend limits and a planted-document test | All pass | A lawyer's view on data protection and SEBI |
| 11 | **Final measure:** fresh questions per deep state, models compared by reading answers, and a person's review of the rules | Results published in this plan | A reviewer, and paid Gemini |

**The order, and why:** the baseline comes first so later changes can be proved. Scan reading comes before state collection because many state orders are scans. Tamil Nadu goes first among the new deep states because a likely order is already downloaded, and Karnataka last because its stamp duty sites don't open from here.

**Rules for collecting:** official sources first; a trusted summary only if labelled; blogs and insurers' pages never count; anything not found is logged as a gap. Every exact date or rate is read by hand before it goes into the exact stores. Rebuilding the index takes a while, so documents go in by batch, never during a test.

**Time:** many sessions of work. There's no honest total until Tamil Nadu is done, which will show how long one deep state really takes.

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
