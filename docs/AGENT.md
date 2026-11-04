# The agent (`vetra/`)

Agriculture and finance, for every Indian state, built to scale by adding data rather than code. RTI stays on `rag/` unchanged and is reached through the agent. The plan and current state are in [MVP_PLAN.md](MVP_PLAN.md).

## How a question is answered

1. **What data does it need, and how far should the answer go?** One LLM call turns the question into a plan: topic, state, language, how deep to go, and the *types of data* needed (`vetra/datatypes.py`). It's made from the user's words alone, before any document is read.
2. **Do we have it?** Code looks in the exact store for each type, for that state and the central government. If the exact store has nothing, it searches text. A deep answer reads both, and searches each part on its own.
3. **Is it on topic?** If the results don't mention the subject, one more search runs, and then it counts as missing.
4. **Is it in force?** Code removes what doesn't apply today. Past seasons' rules are cut unless the question names that year.
5. **Is it enough?** A model judges the evidence against the question. If a part is missing, it searches in other words, reads the passages around one it found, or looks inside a document (`vetra/navigate.py`). Exact records that answer everything skip this step, except in a deep answer.
6. **What's missing?** Gaps go to `data/gaps.jsonl`. `python -m vetra.gaps` lists them, most needed first: this is the to-do list for collecting documents.
7. **Answer.** Exact facts are printed by code, word for word. The model never sees those figures. If exact records answer everything, no answer model runs at all, except in a deep answer. Otherwise it explains the rest, and each sentence is checked (see "How an answer is checked").

| Data type | Exact store | Fallback |
|---|---|---|
| eligibility | rules | text |
| amount | rules, numbers | text |
| deadline | dates | text |
| contact | directory | text |
| form | forms | text |
| change_history | links | text |
| statistic | numbers | text |
| procedure, explanation | none: text is the right place | |

## How deep an answer goes

The planner picks a level from the question. Everything that differs between levels is one table in `vetra/depth.py`, so a reader's own preference can override it later (`answer(..., depth="deep")`, or `--depth` on the command line).

| Level | For | Search | Looks further | Second reader | Answer |
|---|---|---|---|---|---|
| quick | One fact: a date, an amount, yes or no | One search | 1 round | No | One or two sentences, or the exact records alone |
| standard | How to do something, or what to do | One search | 2 rounds | No | The answer, then the steps, conditions and exceptions |
| deep | Understanding a scheme, comparing, how something changed, several linked questions | Each part alone, plus the whole question | 3 rounds | Yes | A research brief with sections |

If the planner calls a question quick or standard but found four or more parts, or three parts including an explanation, it goes deep anyway. The model isn't steady on this choice.

A deep answer differs in these ways:

- **Each part gets its own search.** One search can't reach six different things. On 14 deep questions split into 59 parts, one search reached 40 parts, and searching each part reached 55 (`eval/depth_eval.py`). The settings were tuned on these same questions, so expect somewhat less on new ones.
- **Evidence is shared fairly.** Parts take turns, so one with many passages can't crowd out another. Exact records always stay.
- **Text sits beside exact records.** The records give the figures, and the text gives their conditions and exceptions.
- **It always looks for what changed.** Passages read for this keep their past seasons, marked as history. Elsewhere, past seasons are still cut.
- **The writer knows what each source is.** Each passage is labelled as an Act, rules, a government order, guidelines, a circular, a manual or a press explainer, with its date, status and why it was included. The brief says which applies when sources differ.
- **Code names what's missing.** A part with no evidence is listed by code under the answer, and the writer is told not to write about it.

## How an answer is checked

Every sentence is checked, in this order:

1. **Code corrects citations.** If a figure or date is in the evidence but its sentence cites the wrong passage or none, code adds the passage that says it. This costs no LLM call.
2. **Code finds what can't be true.** A figure or date in no passage, a citation to a passage that doesn't exist, or a wrong "today".
3. **A second model reads it (deep only).** It sees each statement and only the passages that statement cites, and can only report statement numbers. If it can't run, the answer stands on the code checks, and `trace["verified"]` says so.
4. **One rewrite.** The writer is told exactly what failed. If the rewrite is worse, the first answer is kept.
5. **What still fails is cut.** Only the failing sentences come out, and the reader is told some details were left out. If that would remove more than half the answer, the reader gets the exact records or the document names instead.

**Not checked by code:** whether a sentence gets a rule wrong in words. The second reader catches that for deep answers. Quick and standard answers don't have one, to keep them fast and cheap.

## Finding its way

The judge reads document text, so what it can do is kept small:

- **Moves:** it can search, read around a passage, or look inside a document. All of them only read.
- **Fixed by code:** the state and topic. A document can't redirect it to another state.
- **Same checks:** every new result goes through the in-force and off-topic checks.
- **Limits:** set per level in `vetra/depth.py`: rounds, moves a round, passages, total LLM calls, and how many calls are kept back for the answer.
- **If it fails:** the answer is written from what's already in hand.

Each answer's `trace["route"]` shows the moves it made and anything still missing.

## Languages

A question can be in any of India's 22 scheduled languages or English, in its own script or typed in English letters (`vetra/languages.py`). The planner turns it into English for searching, and the answer comes back in the person's language.

- **English and Telugu:** exact facts are printed from templates, so no model touches them.
- **Other languages:** the model translates the facts. Code throws out any translation that changes a number, and prints the English original beside each fact.
- **RTI:** English and Telugu only, since `rag/` stays as it is.

## Adding your data

### Documents (any state, any topic)

```bash
python -m vetra.intake template agriculture KA
```

Put the PDFs or `.txt` files in `documents/agriculture/KA/`, and list them in the `manifest.json` there. Use `IN` as the state for central documents. Then:

```bash
python -m vetra.intake check agriculture KA
```

```bash
python -m vetra.intake build agriculture KA
```

```bash
python -m vetra.intake status agriculture
```

`check` reports bad entries, missing files, duplicates and scans that need OCR, and changes nothing. `build` chunks the files, records each document's validity and amendments, and updates the search index. `documents/` isn't committed, because all-India PDFs are too large for git; `knowledge/` is.

A document in the text store can be found, but its deadlines and rates are only *searched*. To make them exact, sort them.

### Exact facts (the sorting step)

Write records in a `.jsonl` file in `knowledge/inbox/`, then:

```bash
python -m vetra.sorter sort knowledge/inbox/karnataka_crop_insurance.jsonl
```

Each record must say where it applies and where it came from, or it's rejected. Once sorted, the file is removed and the record lives in `knowledge/<domain>/<store>.jsonl`.

A deadline:

```json
{"id": "ka-pmfby-rabi-2026-27", "store": "dates", "domain": "agriculture", "jurisdiction": "KA",
 "scheme": "PMFBY", "scheme_words": ["pmfby", "fasal bima"], "for_season": "Rabi 2026-27",
 "activity": "enrolment", "opens": "2026-10-01", "closes": "2026-12-31", "except": ["rice", "paddy"],
 "subject": "crop insurance PMFBY enrolment deadline cut-off last date rabi",
 "text": "Crop insurance PMFBY, Rabi 2026-27: enrolment window.", "status": "in_force", "reviewed": false,
 "source": {"doc": "G.O. name and number", "date": "2026-07-06", "url": "https://official-site.gov.in/order.pdf"}}
```

A rule: see `knowledge/agriculture/rules.jsonl`. Which crop falls in which class is data in the rule's `aliases`, so check it against that state's notified crops. List crops the scheme's order doesn't cover in `not_notified`, so nobody is quoted a rate for them. Keep `reviewed` false until a person has checked the rule against the order. Add `render_telugu`, `label_telugu`, `detail_telugu` and `ask_as_telugu` to print it in Telugu; without them, the model explains it in Telugu.

### A new topic or a new type of data

- **Topic:** one entry in `vetra/domains.py`.
- **Data type:** one entry in `vetra/datatypes.py`, and a reader in `vetra/tools.py` if it needs a new store.

## Changing the LLM provider

Set these in `.env`; no code changes for any OpenAI-compatible service. RTI (`rag/`) stays on Groq for now.

```
LLM_BASE_URL=https://api.example.com/v1
LLM_API_KEY=...
LLM_MODEL_PLAN=small-model,fallback-model
LLM_MODEL_COMPOSE=large-model,fallback-model
```

## Running it

```bash
python -m vetra.text_index build agriculture
```

```bash
python -m vetra.web
```

Or `python -m vetra.agent "your question" --state KA` in a terminal. With Docker, `docker compose up --build`, then http://localhost:8765. Stop any older container on that port first.

## Checking it

| Command | Checks | Uses the LLM |
|---|---|---|
| `python -m pytest tests -q` | the mechanics | no |
| `python eval/agent_retrieval_eval.py` | search still matches the measured pipeline | no |
| `python eval/on_topic_eval.py` | the off-topic check | no |
| `python eval/needs_eval.py` | the planner picks the right data types (`--live` to re-ask) | saved plans |
| `python eval/depth_eval.py` | a deep answer's search reaches every part of the question | no |
| `python eval/depth_eval.py --planner` | the planner picks the right level (`--live` to re-ask) | saved plans |
| `python eval/agent_answers.py --show` | real answers, known cases | yes |

## Later: finding data by itself

When data is missing, `gaps.py` hands the gap to a handler. Today that's a log. An agent that searches the internet and sends what it finds through data engineering plugs in as another handler (`GapHandler`), and the rest of the system doesn't change. Automated collection isn't built, on purpose: for now documents are collected by hand.
