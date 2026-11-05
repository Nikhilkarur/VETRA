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
- When it's FINISHED, read the marking sheet `eval/cache/gold/first.csv` in that folder, mark each answer by hand, then run `--score first` there. These are the first honest quality numbers.

**Research:** `reports/VETRA engine techniques 2026.md` is the ranked list of what to adopt. Engine gaps are in `docs/ARCHITECTURE_RESEARCH.md`.

## Next steps, in order

1. Check the groundnut answer: it told a farmer to "gather documents" such as land-holding proof. Find out if G.O. 579 says so. Then consider a second reader on standard answers.
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
- **Scans:** some fonts swap letters but look fine, as in Maharashtra's order. Set `"read_as_scan": true` in the manifest. Reading takes about 10 seconds a page.
- **Gemini's free limit:** 500 requests a day per model, resetting around 1:30 pm India time, which is my estimate.

## Set up at the start

Scheduled checks stop when a session ends. Turn them back on with CronCreate every 2 hours, using a prompt like: "VETRA work check. Call get_usage. If the 5-hour or weekly limit is at or above 95%, say you're paused until the reset. Otherwise do one focused step from docs/HANDOFF.md, keep output short, save progress in docs/STATE_COVERAGE.md, and report in two or three plain lines."
