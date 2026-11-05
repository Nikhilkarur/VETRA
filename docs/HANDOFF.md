# Handoff for the next session

Written 5 November 2026. Read this, then [STATE_COVERAGE.md](STATE_COVERAGE.md), and only read other docs when a task needs them.

## The goal

VETRA answers citizens' agriculture and finance questions for every Indian state, in 22 languages and English, from official documents. Answers are deep, factual and traceable. The agentic engine is the MVP. Automated data engineering and auto-update are out of scope, so documents are collected by hand.

**Order of work:**
1. Andhra Pradesh and Tamil Nadu to the deepest level, covering every aspect in `STATE_COVERAGE.md`.
2. Maharashtra and Karnataka.
3. Every other state and union territory at medium level.

Alongside that, improve the engine where results show a real need: fix a measured problem, add a test, re-measure.

The owner decides: RAM, local models, paid Gemini and the lawyer. Don't wait for these.

API keys stay on free tiers for now, until the owner sorts out paid ones. A question averages about 3 calls, so spread large runs across the daily reset and let Groq take over.

## Rules

- **Use the owner's weekly limits carefully:** do long work with PC scripts and API keys, not by reading long output. Keep command output short, don't re-read what's known, and don't spawn agents unless asked.
- **Never stop for a blocked step:** try another route, then move to other work. If Gemini is out, use Groq, Tesseract or work needing no model.
- **Try other angles before asking the owner:** plain HTTP, the built-in browser for JavaScript pages, listing pages, guessing file names, other official hosts (India Code, gazettes, CAG, PRS, archive.org). Ask only after those fail, and say what you tried.
- **Official sources first.** Blogs and insurers' pages never count. Label summaries.
- **Never invent dates or figures.** Leave a date blank rather than guess.
- **Exact records only after reading the source yourself.** Mark them `reviewed: false`.
- **Check rates against a live source:** official PDFs can be out of date. Andhra Pradesh's PDFs say 4% and 0.5% on a sale; its live calculator and CAG say 5% and 1%.
- **Read answers by hand.** Text-match scores hid real bugs. Say when a score comes from questions already used for fixing.
- **Never:** push, merge or open a PR without being told; pay or change accounts; print or commit keys or `.env`; add Claude as a contributor or any attribution line to commits, because the owner's rule overrides the default.
- **Talk plainly and briefly.** The owner writes casually and wants to know what's happening. Report what was measured and what wasn't.

## Where things stand

**Engine:** built and working. 228 code tests pass with `python -m pytest tests -q`. Search is E5-base. Scan reading is in `vetra/scans.py`, source ranking is in, and Groq is the automatic backup through `groq:` model names in `.env`. Docker's image passed before today's later changes and needs rebuilding at some point. It takes 40 minutes or more.

**Exact rates:** `knowledge/finance/numbers.jsonl` and `knowledge/agriculture/numbers.jsonl`. Dates and rules are in `knowledge/agriculture/`.

**Documents:** `documents/<topic>/<STATE>/manifest.json`, loaded with `python -m vetra.intake build <topic> <STATE>`. `documents/` isn't committed. Don't run two builds at once.

**Baseline test:** 179 hand-read questions in `eval/gold_questions.json`. It runs from a frozen copy of the engine in `C:\Users\nkk77\Desktop\VETRA-baseline`, so new documents don't change it. `tools/baseline_loop.sh` retries it until done, and its log is `gold_loop.log` there, ending in FINISHED. The owner hasn't checked the sample in `eval/gold_sample.md` yet.

- To check: `tail -3` the log.
- If it isn't running and isn't FINISHED, restart it: `nohup bash tools/baseline_loop.sh /c/Users/nkk77/Desktop/VETRA-baseline &`.
- **Result, 5 November 2026:** 157 of 179 good (82-92%), 15 wrong, 7 needless refusals, marked by Claude, not by the owner or a second person. Native-language answers were read only to about 520 characters. The groups: AP agriculture 39/51, central agriculture 30/33, finance 22/23, casual 10/10, languages 21/22, other states 9/9, dated 6/9, gaps 13/14, invented schemes 7/8.
- **What it found:** exact records printed when they didn't answer the question (5 of the 15 wrong; fixed, 4 confirmed by re-asking and the fifth hit "busy"); AP's enhanced relief rates, which were missing (fixed with records); a made-up worked example and uncited steps such as "obtain a loss certificate" (now refused by code). Questions where the expected answer is out of date: ap_agriculture-30, -36, casual-02 and indian_language-05. Update those in `eval/gold_questions.json` before the next baseline. No full re-run since the fixes, so 157/179 is before them.
- When it's FINISHED, read the marking sheet `eval/cache/gold/first.csv` in that folder, mark each answer by hand, then run `--score first` there. These are the first honest quality numbers.

**Research:** `reports/VETRA engine techniques 2026.md` is the ranked list of what to adopt. Engine gaps are in `docs/ARCHITECTURE_RESEARCH.md`.

## Finish AP and TN (owner's deadline: 6 November 2026)

All aspects of agriculture and finance. Tools: `tools/coverage_grid.py` (gaps by aspect), `tools/crawl_pdfs.py` (PDFs on official sites, list in `eval/cache/hand/pdfs.jsonl`), `tools/goir.py` (AP orders by department, list in `eval/cache/hand/gos.jsonl`), `tools/fetch_docs.py` (batch download), `eval/aspect_questions.py` (one question per aspect, answers in `eval/cache/aspects/`).

1. Pick scheme orders and guidelines from the two lists, fetch them, and build each topic and state, one build at a time.
2. Run `eval/aspect_questions.py first AP TN` and read every answer with `--show`.
3. Each wrong or empty answer is a gap or a bug: collect the document, add the exact rate after reading it, or fix the engine with a test.
4. Re-run the aspects that changed and read them again. Say what's still unanswered.
5. Mark the baseline by hand when it's FINISHED.

## Next steps, in order

1. Groundnut answers, read on 5 November: G.O. 579 asks farmers for no papers, and four new wordings didn't repeat the "gather documents" advice. They showed three other faults. One made up a sum insured of Rs.20,000 for groundnut (now refused by a check). One gave a range up to the perennial rate, Rs.22,500, for an annual crop. A heavy-rain question was answered only from crop insurance and missed G.O. 579. Decide on a second reader for standard answers from the baseline's hand marks.
2. **Andhra Pradesh:** gift, settlement, release, partition and lease rates on the calculator (`registration.ap.gov.in/igrs/DutyFeeCalculator/Property`, public, with no personal details). Current vehicle life tax rates and the 2026 Road Safety Cess rates. Other profession tax classes. The separate agriculture budget speech. Department sites for fisheries, animal husbandry, horticulture, seeds, natural farming and markets, linked from `agriculture.ap.gov.in`.
3. **Tamil Nadu:** crop insurance cut-off dates and the 2026-27 notification. Vehicle tax rates after the 2023 change. Profession tax slabs, starting with Chennai's official notice. The animal husbandry note. The rest of the `tnreginet` fee table. Exact rates from the dairy, fisheries, cooperation and food notes.
4. Write test questions for the new Andhra Pradesh and Tamil Nadu documents, including finance, and measure them.
5. Dates on rules, since old orders can still outrank new ones. Tamil Nadu's 2022 relief order came above G.O. 579 in one search.
6. Then Maharashtra and Karnataka. Maharashtra's 481-page crop insurance order is already read and in search, with no exact dates pulled yet.

## Useful routes found

- **Tamil Nadu:** `tn.gov.in/document_dept_list.php?cate_name=YWxs` lists each department's policy notes, shown only in a browser. PDFs are at `cms.tn.gov.in/cms_migrated/document/docfiles/<name>_e_pn_2026_27.pdf`, and names can often be guessed. Registration fees appear after calling `showDutyFeesPage()` on `tnreginet.gov.in/portal/`.
- **Tamil Nadu disaster orders:** `tnsdma.tn.gov.in` works only over plain `http://`. See `/pages/view/governmentorders`.
- **Andhra Pradesh:** `registration.ap.gov.in/igrs/` has the fee table and calculator. Budget files are on `apfinance.gov.in`.
- **Bills:** PRS hosts official gazette copies, at `prsindia.org/files/bills_acts/bills_states/<state>/<year>/Bill<n>of<year><XX>.pdf`.
- **CAG:** `cag.gov.in` worked when `saiindia.gov.in` refused the connection.
- **Tesseract** isn't on the PATH. Use `vetra.scans.TESSERACT` or `C:\Program Files\Tesseract-OCR	esseract.exe`.
- **PRS bill pages:** `prsindia.org/bills/states/<slug>` has the real PDF link when the guessed name fails.
- **To read one answer by hand:** `python tools/ask.py STATE "question"`.
- **Scans:** some fonts swap letters but look fine, as in Maharashtra's order. Set `"read_as_scan": true` in the manifest. Reading takes about 10 seconds a page.
- **Gemini's free limit:** 500 requests a day per model, resetting around 1:30 pm India time, which is my estimate.

## Set up at the start

Scheduled checks stop when a session ends. Turn them back on with CronCreate every 2 hours, using a prompt like: "VETRA work check. Call get_usage. If the 5-hour or weekly limit is at or above 95%, say you're paused until the reset. Otherwise do one focused step from docs/HANDOFF.md, keep output short, save progress in docs/STATE_COVERAGE.md, and report in two or three plain lines."
