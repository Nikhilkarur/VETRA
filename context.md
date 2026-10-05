# AP RTI Assistant — AP Government RTI Chatbot

Living project document. **Every change to the project's plan or implementation gets logged here** (see Changelog at the bottom).

## What this is

A chatbot for ordinary citizens interested in government affairs. First scope: **Andhra Pradesh government — RTI Act & related documents.** It began as a basic vanilla RAG and was improved one measured change at a time into the pipeline below. The longer-term vision is a **multi-domain agentic assistant for the AP government** (see "Next steps").

## Goal (current phase)

**Demo-ready as of 2026-09-13.** The first vanilla pipeline worked mechanically but failed
real citizen questions; it was iterated, one measured change at a time, into the
pipeline below. Next phase: decide what to improve for real, not just for the demo.

## Stack (current)

- **Language:** Python 3.13
- **Answering LLM:** Groq `openai/gpt-oss-120b`, reasoning effort `medium`, falls back to
  `openai/gpt-oss-20b` if rate-limited. (No Llama chat model is available on our account.)
- **HyDE search passage:** Groq `openai/gpt-oss-20b`, reasoning effort `low`.
- **Embeddings:** local `BAAI/bge-small-en-v1.5` (384-dim, 512-token window). Query gets
  bge's instruction prefix; chunks go in raw.
- **Keyword search:** in-house Okapi BM25 over chunk text (~30 lines, no dependency).
- **Vector DB:** Chroma, local, cosine.
- **PDF parsing:** `pypdf`.

## How to run the demo

```bash
python rag/web.py      # web page at http://127.0.0.1:8000
python rag/chat.py     # or the terminal chat
```
Startup takes ~30 s (see "Known limitations" — it's the Python environment, not the
pipeline). After that, search is ~1.5 s and an answer ~2–7 s — **unless Groq's free-tier
limit is hit**: gpt-oss-120b allows 8,000 tokens/minute and one answer uses ~4,500, so
**pace questions ~30 s apart**. Faster than that, answers wait 20–40 s for the limit to
reset, or drop to the smaller model (the answer then says so). `/sources` in the chat
shows the retrieved passages and the HyDE search passage.

Rebuilding from scratch: `python ingest/load_and_chunk.py` then `python ingest/build_index.py`.
Measuring retrieval: `python eval/retrieval_eval.py` (add `--no-hyde` to compare).

## RAG pipeline (current)

**Ingest (once):**
1. **Extract** each PDF with pypdf; whitespace normalised only.
2. **Split the RTI Act by section** (31 sections, located in order; official section
   titles verified verbatim against the Act's marginal notes). Other documents stay whole.
3. **Chunk by tokens** with bge's own tokenizer: sentence-aligned, 350 tokens, 60 overlap.
   Largest chunk 377 tokens vs a 512 window — truncation is impossible. **535 chunks.**
4. **Label** every chunk's source for citation: Act chunks as
   "RTI Act 2005, Section 19: Appeal"; department manuals with their department; the
   portal page as the most current source. Labels are NOT embedded (tested; it hurt).
5. **Detect amendments** automatically: an order whose abstract says "Amendment to…" is
   linked to the orders it cites. In this corpus: G.O.454 (fee rules) ← 530, 545, 740.
6. **Embed** with bge-small into Chroma. The model name is stored in the collection.

**Per question:**
0. **Route (since 2026-10-05, the default for web.py / chat.py / answer.py):**
   gpt-oss-20b names the domain — rti, agriculture, or other (declined, with "ask
   anyway" buttons on the web page). See "Retrieval experiments and the router" below.
1. **HyDE:** gpt-oss-20b writes a 40–80-word passage in legal drafting style, forbidden
   from naming "RTI Act" / "Andhra Pradesh" (they're in every chunk and drown the signal).
   Used only to search; never shown to users or to the answering model.
2. **Hybrid search, twice:** for the question and for the HyDE passage, rank every chunk by
   dense similarity and by BM25, fuse with RRF.
2b. **Rewrite (since 2026-10-05):** qwen3.8-27b names the question's topic and key
   terms; the topic (hybrid) and key terms (BM25) are two more votes in the same RRF.
   Agriculture then re-scores the fused top 30 with a MiniLM cross-encoder (fused with
   the search order). Both are per-domain settings in `rag/domains.py`.
3. **Fuse** the rankings with RRF; take the **top 10**.
4. **Add amendments:** if a retrieved order has amending (or amended) orders, append up
   to 4 of their chunks, most relevant first.
5. **Answer:** gpt-oss-120b, numbered labelled passages, a prompt with explicit rules for
   partial answers, exact figures, amendments, dated office-holders and
   department-specific contacts. Citation markup normalised to `[n]`.

## Structure

```
ap-rti-assistant/
├── context.md                 # this file
├── requirements.txt
├── ingest/
│   ├── documents/             # 41 corpus files (40 PDFs + 1 txt)
│   ├── corpus_manifest.json   # title/department/source_url/sha256 per file
│   ├── inventory_rti_acts.json# audit of all 546 docs on the site
│   ├── load_and_chunk.py      # PDFs -> token chunks (--domain rti|agriculture)
│   ├── chunks.json            # RTI: 535 chunks + metadata (generated)
│   ├── chunks_agriculture.json# agriculture: 1,895 chunks (generated)
│   ├── build_index.py         # chunks -> bge-small -> Chroma, one collection per domain
│   ├── collect/               # tools that collected the new domains' documents
│   └── incoming/              # staged documents per domain (agriculture indexed from here)
├── rag/
│   ├── domains.py             # per-domain documents, index, prompts, web text
│   ├── retrieve.py            # HyDE + hybrid (dense+BM25) + RRF + amendment links
│   ├── answer.py              # passages + question -> Groq -> cited answer; follow-up rewrite
│   ├── chat.py                # terminal chat
│   ├── web.py                 # local web server (standard library only)
│   └── web.html               # the web page
├── docs/
│   └── AP RTI Assistant Knowledge Base.html   # self-contained explainer page
├── eval/
│   ├── demo_questions.json    # frozen RTI question sets: dev, heldout, heldout2, heldout3
│   ├── agri_questions.json    # frozen agriculture sets: dev, dev_casual, heldout, heldout2
│   ├── retrieval_eval.py      # does the answering text reach the top-k? (no LLM judge)
│   ├── compare_embeddings.py  # older encoder comparison harness
│   ├── testset.json + run_ragas.py   # RAGAS (LLM-judged) evaluation
└── data/chroma/               # vector store (generated, gitignored)
```

## The corpus (settled 2026-09-04)

**Source:** `ap.gov.in` → menu **RTI & Acts**. Seven sections, 546 documents total.
Audited all of them; **41 are worth indexing.**

### Why the site looks so disorganised

It isn't an RTI page — it's a **compliance page**. RTI Act **s.4(1)(b)(v)** obliges every
public authority to publish *"the rules, regulations, instructions, manuals and records
held by it."* That clause is why Acts, Service Rules, Manuals and GAD Circulars all sit
in a menu labelled RTI. It's a filing cabinet built to satisfy a statute, not to answer
a citizen's question — which is the gap this project fills.

### What we took, and what we skipped

| Section | Docs | Verdict |
|---|---|---|
| Acts | 20 | skip — generic statute library; **the RTI Act is not here** |
| Guidelines on Local status | 3 | skip — bifurcation HR |
| Service Rules | 218 | skip — cadre promotion rules, zero citizen relevance |
| Manuals (Business Rules) | 11 | skip — how the Secretariat runs itself |
| GAD Circulars | 9 | skip — five-day week, transfers |
| Instruction on RTI | 0 | **text only** — all links dead; only source of current commissioners |
| Department – Org RTI | 285 | **selective** — everything useful is here |

Funnel: 546 published → 194 RTI-related → minus 124 quarterly filing statistics
→ 69 substantive → **41** after dedup, scans and Telugu.

### The three layers we index

1. **The law** — RTI Act 2005 (23pp). Filed, oddly, at GAD → s.4(1)(A) → a file titled
   just `RTI ACT`. Answers s.6 how to apply, s.7 fees + 30 days, s.8 exemptions,
   s.19 appeals, s.20 penalties.
2. **AP's implementation** — 26 GAD orders 2005–2011. Commissioners, state fee rules,
   PIO appointments, compliance monitoring. Government-to-government.
3. **Citizen how-to** — 13 department 4(1)(b) manuals. Every one follows the Act's fixed
   17-chapter structure; **ch. XV = facilities for obtaining information, ch. XVI = PIO
   names.** This is the layer that tells a citizen where to actually send a request.

Plus the scraped Instruction-page text (sitting Chief Information Commissioner + 5 SICs).

### Selection rules used (for re-deriving the corpus later)

Crawled the site's JSON API, not the HTML — the Dept–Org RTI accordion has a
shared-state bug that hides 282 of its 285 files.

```
ApSubDepartmentRtiOrg/getbymasterid/{department}   # 13 departments, ids 10–22
ApDepartmentOrgRtiChilds/getbymasterid/{sub_org}   # the documents
```
The PDF URL arrives in a field named `imageBase64` — it is a plain URL string, not base64.

- **GAD (masterId 20)** wears two hats: nodal RTI coordinator *and* an ordinary public
  authority. Keep only its three RTI groups; skip its other 91 records (GA(SR),
  GA(AR&T.I), GA(AR&T.III) — training allowances, secretariat reorganisation).
- **All other departments:** keep everything after the exclusions below.
- **Exclude by group,** not just title: APTPC and Mee-Seva publish 124 quarterly returns,
  several titled plainly `RTI - ACT 2005 - 1st Quarter` with no filterable keyword.
- **Exclude** the 48pp RTI logo manual; **exclude Telugu** editions (2 files) —
  `all-MiniLM-L6-v2` is English-only.
- **Dedup** on G.O. number (same order often uploaded twice), preferring
  extractable text > newer edition > more pages.
- **Drop scans** with no text twin. In the GAD set every scan has a text twin, so
  **v1 needs no OCR at all.**

### Known gaps

- **1 broken URL** — Prisons PIO list, on a typo'd `api-1` host; 404s. Logged in
  `corpus_manifest.json` under `broken_urls`.
- **2 scans dropped** — Panchayat Raj and Transport R&B manuals; no text version exists.
- **2 Telugu files excluded** — revisit if we move to a multilingual embedding model.
- **Corpus is frozen at Dec 2011** for the GAD orders. Coverage is uneven, not dead —
  Water Resources published a 4(1)(b) manual in 2025.
- **Nothing here explains "how to file an RTI" in plain language.** That answer is in the
  Act's own sections. Expect retrieval imbalance: the Act is one 23pp document carrying
  most procedural weight against 26 order fragments of 1–3pp. If committee-constitution
  orders surface for "how do I file an RTI", that's the corpus shape, not a pipeline bug.

## Diagnosis: why the vanilla RAG underperforms (2026-09-04)

The baseline works mechanically and fails on real citizen questions. We spent a session
diagnosing it. **The retrieval mechanics are not the problem — the query is.**

### The evidence

**Benchmark failure.** Question: *"If I don't get a reply to my RTI application within
30 days, what can I do?"* Our system answered *"I can't tell you"* — while the chunk
containing the exact appeal provision (s.19, "senior in rank") sat at **rank 31 of 766**.
It did not hallucinate; the system prompt held. Retrieval simply never delivered it.

**RAGAS baseline** (2 questions, top-8, judge `gpt-oss-120b`):
`faithfulness 0.95` · `context_recall 0.667` · `context_precision 0.384`
(precision **0.14** on "how do I apply"). High faithfulness + low precision =
the model is behaving; retrieval is feeding it noise.

**Swapping the encoder does not fix it.** Evidence recall@8 over 8 probe questions:
`all-MiniLM-L6-v2` 60% · `bge-small-en-v1.5` 67% · bge + query prefix 40%.
A one-probe difference out of fifteen — noise. Both models fail the *same* questions.
(bge still has a structural edge: 512-token window vs 256, which would end our 27%
truncation. Not adopted yet — baseline deliberately left fixed.)

**The actual cause, measured.** Rewriting the question in the Act's own vocabulary,
*without copying any phrase from the target chunk*:

| question | raw rank | topic-worded rank |
|---|---|---|
| How do I apply for information? | **106** | **6** |
| If I don't get a reply in 30 days? | 4 | 2 |
| Does RTI override secrecy laws? | 2 | 1 |
| What penalty if an officer refuses? | 2 | 2 |

Given a corpus-worded query, MiniLM + Chroma + top-8 puts the gold chunk at rank 1–6.
**Nothing about the vector search was ever broken.**

**Retrieval is also brittle to phrasing.** The same appeal question, trivially reworded
(dropping "to my RTI application"), moved from rank 31 to rank 4. A ninefold swing on
cosmetics. A classifier would normalise this — every phrasing maps to one fixed query.

### Two reference systems, both beat us the same way

**AP govt's own chatbot** (ap.gov.in) answered the benchmark question correctly and
completely: deemed refusal (s.7(2)), 48 hours for life/liberty (s.7(1)), free of charge
when the deadline lapses (s.7(6)), first appeal to a senior officer within 30 days
(s.19(1)), appellate authority to decide in 30/45 days (s.19(6)), ₹250/day penalty
capped at ₹25,000 (s.20(1)). Every claim verified against our own copy of the Act.
Its flaws: says "CPIO" (central) rather than SPIO throughout — suggesting a DoPT/central
corpus, not AP-specific — and omits the second appeal to the SIC within 90 days (s.19(3)).
Its output includes a "Deep Thinking" step, so it is not vanilla either.

**`~/Desktop/rgbackup/sar-rag_v1`** (our own earlier project) is *not* vanilla RAG.
It is ahead on four things: heading-aware sectioning via PyMuPDF font sizes;
token-bounded sentence-aligned chunks (350 target / 480 hard cap, counted with the
encoder's own tokenizer, so truncation is impossible); **contextual chunking** —
`[Context: <doc> - Section: "<heading>"]` prepended before embedding; and
**multi-query fan-out** — N sub-queries, 5 results each, merged and deduped on best
distance. Neither system has a reranker or hybrid search.

**Correction to an early assumption:** sar-rag_v1's "classification" contains **no ML**.
It is eight hardcoded threshold checks (`800000 <= amount <= 999999`). Its input is a
JSON transaction with nothing embeddable, so a human wrote eight regulation-worded query
strings by hand. Their easy step (input → label) is our hard step, because our input is
open-ended natural language.

### The transferable principle

> **Never embed the user's raw words. Embed something written in the corpus's vocabulary.**

sar-rag_v1 does this with a lookup table (closed input set). HyDE does it for open inputs
by generating a fake answer and embedding that. Both close the same gap.

### Why one good query still is not enough

The AP bot's correct answer drew on **s.7(1), s.7(2), s.7(6), s.19(1), s.19(6), s.19(8),
s.20(1)** — seven provisions across three sections. Classification yields one better
query; one search over 1000-char chunks cannot assemble that. **Classification routes;
decomposition fans out.** We need the fan-out.

### Prior art (checked, not assumed)

Preprocessing is **not** an unexplored area — it is one of the most worked-on in IR:

- **Doc2Query** (arXiv 1904.08375, 2019) — generate the questions a document answers,
  append them, index that. Then **Doc2Query--** (2301.03266) for hallucination filtering
  and **Doc2Query++** (2510.09557) for cross-domain topic coverage.
- **Anthropic Contextual Retrieval** (2024) — prepend 50–100 tokens of chunk context
  before embedding. **49% fewer failed retrievals; 67% with reranking.** sar-rag_v1
  already implements a deterministic version of this.
- **HyDE** — embed an LLM-generated hypothetical answer instead of the question.
  Original: +5–20 nDCG@10. 2026 reruns: only +1–4 with frontier encoders — but we are on
  MiniLM with no hybrid search, so the gap it fills is still ours.
- **Adaptive-RAG** (arXiv 2403.14403) — trains a small query-complexity classifier to
  route between no-retrieval / single-step / multi-step. Reported 85.9% accuracy.

### The cost thesis (the direction worth pursuing)

Preprocessing is well-studied *because* it is the cost-efficient answer — work done at
index time is paid once; work at query time is paid per user, forever.

| technique | index time (once) | query time (per user) |
|---|---|---|
| contextual chunking | 766 cheap calls, cents | ₹0 |
| Doc2Query expansion | 766 cheap calls, cents | ₹0 |
| HyDE / decomposition | ₹0 | +1 LLM call per question |
| multi-agent | ₹0 | +3–10 calls per question |

For a citizen-facing government bot on a public budget this asymmetry is the argument.
And a big LLM / multi-agent stack is **not** needed here: with a corpus-worded query,
plain MiniLM + Chroma + top-8 already ranks the gold chunk 1–6.

**Where novelty may genuinely remain:** not "preprocessing for RAG" (taken), but
(a) this corpus type — Indian statutory + government-order text with real OCR damage
(`"rup ees"`, `"Informati on"`) and mixed English/Telugu; (b) the *lay question →
statutory provision* register gap, where the answer is split across sections that never
reference each other; (c) how far index-time work alone gets you under a hard budget
ceiling — a 22MB encoder, no query-time LLM calls. Finding where that ceiling sits is
itself the result.

## Not doing yet (future experiments)

- ~~Contextual chunking~~ — tested 2026-09-13; hurt on this corpus. Semantic chunking untested.
- Reranking retrieved chunks (cross-encoder) — untested
- Multi-agent architecture (router / corpus / live-info / drafting agents)
- Live web crawling / fresh-info tools
- RTI application drafting feature
- ~~Citations with exact doc + section~~ — done: Act chunks cite their section
- ~~Conversation memory in `chat.py`~~ — done 2026-09-19: follow-ups are rewritten into
  standalone questions (chat and web page)

## Open items

- ~~Confirm which AP govt URL(s) to pull the RTI PDFs from.~~ Done — see corpus section.
- ~~Pick the specific Groq model.~~ Done: gpt-oss-120b (no Llama chat model on our account).
- Decide whether to add OCR (would recover 2 department manuals) — not needed for v1.
- Decide whether to go multilingual (would recover 2 Telugu manuals).
- Later: `sic.ap.gov.in` (AP Information Commission) is the obvious source for
  citizen-facing how-to and current PIO contacts. It returned **403** to a plain
  request on 2026-09-04 — needs a browser, or may be down. Check before depending on it.

## Iterating to a working demo (2026-09-13)

### Method

Question sets were written and verified against the corpus **before** each change they
test, then frozen (`eval/demo_questions.json`). Metric: does every probe phrase — verbatim
text that answers the question — appear in the retrieved chunks? No LLM judges it.
- `dev` (20, fairly formal wording) — used while iterating
- `heldout` (12, casual) — first look after the architecture changes
- `heldout2` (12, casual) — written before query rewriting was built
- `heldout3` (10, casual) — written before testing section titles and choosing k

### Results (top-8 unless stated)

| change | dev | held1 | held2 | held3 |
|---|---|---|---|---|
| original pipeline (MiniLM, 1000-char, raw query) | 65% | 50% | 50% | — |
| token chunks 200/40 (MiniLM) | 70% | | | |
| + RTI Act split by section | 70% | | | |
| + contextual title prefix embedded | 70% (MRR ↓) | | | |
| + hybrid BM25 | 80% | | | |
| bge-small 350/60 + section + title prefix + hybrid | 85% | | | |
| **same, title prefix removed** | **95%** | 42% | 58% | |
| + LLM query rewrite (v1 prompt) | 85% | 25% | | |
| + rewrite, v2 prompt (no corpus-wide words) | 90% | 58% | | |
| + HyDE (v1 prompt) | 95% | 50% | | |
| **+ HyDE, v2 prompt, fused with original** | **95%** | **75%** | **92%** | **60%** |
| + rewrite v2 and HyDE v2, three-way fusion | 90% | 83% | | |
| section title embedded on Act chunks (3 variants) | 95% | 67–75% | 83% | 60% |
| **k = 10 (final)** | **95%** | **75%** | **92%** | **80%** |

Final pipeline through the real code (`eval/retrieval_eval.py`): **47/54 (87%) overall;
28/34 (82%) on the casual held-out questions.** Original pipeline on the same held-out
questions: ~50%.

### What we learned

- **Architecture changes alone did not generalise.** Token chunking, section splitting,
  bge and hybrid search took dev from 65% to 95% — and casual held-out questions from
  50% to 42–58%. They fixed formally-worded questions only. The register gap needs the
  query side fixed.
- **Contextual title prefixes hurt this corpus**, in every form tried: every G.O. title
  contains "Right to Information Act", and even bare Act section titles didn't help.
  This contradicts Anthropic's Contextual Retrieval result — on this corpus.
- **Naive query rewriting made retrieval worse** (held-out 42% → 25%): the LLM padded
  every query with "under the Right to Information Act, 2005 … Andhra Pradesh", words in
  every chunk. Forbidding them fixed it. Same IDF mechanism as the original diagnosis.
- **HyDE was the step that generalised.** A hypothetical legal-style passage speaks the
  corpus's language; fusing it with the original query protects against a bad passage.
- **Hybrid BM25 helped** (+10–20 points) — our earlier prediction that it wouldn't was
  too pessimistic: it fails only when the key term is absent, and helps whenever a rare
  term is present.
- **The RTI fee IS in the corpus.** Earlier we (and the model) said it wasn't — that was
  a retrieval failure. AP G.O.454: village level no fee, mandal ₹5, others ₹10 per
  application; ₹2/page; CD ₹100, DVD ₹200. G.O.545 changed inspection to ₹5/hour after
  the first free hour; G.O.740 added court-fee stamps/postal orders and exempted white
  card (BPL) holders.

### Answer-quality fixes (found by reading real answers, not by metrics)

Retrieval coverage doesn't catch these; a live demo would have:
1. **Outdated office-holder stated as current** ("currently Sri Jannat Husain", from a 2010
   order). Fix: portal page labelled as the most current source; prompt forbids calling
   anyone current from a dated order.
2. **One department's phone number offered for "any office"** (Water Resources' appellate
   officer). Fix: manuals labelled with their department; prompt restricts contacts.
3. **Superseded fee rule** (inspection ₹5/15 min instead of amended ₹5/hour). Fix:
   automatic amendment links, amending orders appended to context.
4. **Over-generalisation and garbled figures** ("copyright is the only ground", "₹25,000
   per day"). Fix: prompt rules on partial answers, "only"/"not permitted", and copying
   figures exactly. After: correct at both reasoning efforts; at medium it explicitly says
   s.8 wasn't in its passages.
5. **Rate limit crash (429)** in back-to-back questions. Fix: SDK retries, then fallback to
   gpt-oss-20b with a visible note. Amendment additions capped at 4 chunks.

### Known limitations (honest, as of the demo)

- **~18% of casual questions still miss the answering text.** Remaining misses: the current
  Commissioner (freshness), "office not answering" (s.19 at rank ~15), "can they just say
  no" (s.8 not in top 40), village-level free fee, reasons for rejection (s.7(8)), private
  companies (s.2(f)).
- **When evidence is missing, answers can still misattribute.** Rehearsal example: the
  private-companies answer reached a reasonable conclusion but cited the definition as
  "Section 4(1)(b)" (it is s.2(h)) and missed s.2(f). Grounding rules reduce this; they
  don't eliminate it.
- **Freshness.** Only the portal page is current; orders stop at 2011. The answer is now
  honest about dates, but it can't give the current Commissioner unless that page is
  retrieved.
- **Free-tier throughput.** ~1 answer per 30 s on gpt-oss-120b before throttling.
- **Startup ~30 s.** `import sentence_transformers` spends ~10 s in
  `transformers.utils.import_utils` probing hundreds of packages installed globally
  (ragas, langchain…). Not network (same with HF offline). Fix: a project virtualenv
  with only `requirements.txt`.
- **Query-time cost is no longer zero**: HyDE adds one small LLM call per question. This
  is in tension with the preprocessing-only cost thesis above — a zero-query-cost
  alternative (doc-side expansion, Doc2Query-style) is untested.
- **No clean held-out set remains.** Every set in `demo_questions.json` has now informed
  some decision. Any further tuning needs a fresh set written first.

## Agriculture domain (2026-10-04)

Goal of this step: agriculture answers through the same pipeline as RTI. No router yet
(the user picks the domain), finance later, router last.

### How it is wired

- `rag/domains.py` holds everything that differs per domain: documents, chunks file,
  Chroma collection, HyDE / answer / follow-up prompts, web text. Every script takes
  `--domain` (default `rti`). RTI's three prompts were moved there verbatim (checked
  byte-for-byte against git) and RTI still scores **47/54** on its sets.
- Documents: the 46 staged in `ingest/incoming/agriculture/` (44 with text; 2 scans
  skipped until OCR). **1,895 chunks** (RTI: 535), same 350/60 token chunking.
- Page limits for 5 table-heavy documents (`AGRI_PAGES` in `load_and_chunk.py`):
  G.O.Ms.80 PMFBY pp.1-47 of 864 (the rest is sowing calendars and village lists),
  G.O.Ms.81 pp.1-32, G.O.Ms.98 pp.1-23 (weather term sheets), MIDH pp.1-115 (polyhouse
  engineering specs), PDMC pp.1-42 (bill-of-quantity tables).
- Amendment links come from the manifest's curated `amends` field (not text
  heuristics); order keys include the year (`Ms.80/2024`) because numbers repeat.
- Every chunk carries `in_force`; replaced documents are labelled "NOT IN FORCE (...)"
  in the source line the answer model sees.

### Measured (eval/agri_questions.json; probe-in-top-10, same method as RTI)

Question sets were written before the code that they test: `dev` (24, formal), then
`dev_casual` (12) and `heldout` (16, casual); `heldout2` (13) was written after round 1
and before round 2.

| change (cumulative) | dev | dev_casual | heldout | heldout2 |
|---|---|---|---|---|
| baseline, hybrid only | 88% | | | |
| baseline + HyDE | 79% | | | |
| + max one not-in-force chunk in the top k | 92% | | | |
| + document title prefixed in the embedding, no HyDE | 100% | 83% | 50% | 54% |
| + title prefix + HyDE v1 | 88% | 92% | | |
| + HyDE v2 prompt (keep the question's names) — **round 1** | 92% | 92% | **69%** | **69%** |
| + abbreviation glossary + HyDE v3 — **round 2 (final)** | 96% | 92% | 69%* | **69%** |

\* heldout had been seen once by then. Also tried, no gain: HyDE weight 0.3 / 0.5 in
the fusion, HyDE used for dense search only (78%), question+passage concatenated (89%).
HyDE passages were cached to disk (`HYDE_CACHE`) so configurations were compared on
identical passages — gpt-oss drifts even at temperature 0, ±1-2 questions per run.

### What we learned

- **Title prefixes help agriculture, though they hurt RTI.** RTI's titles all say
  "Right to Information Act"; agriculture's name the scheme, crop and season
  ("Change of name of Schemes ...", "RWBCIS ... Mango"). +13 points (81% -> 94%).
  Caveat: several titles were written during collection, not copied from the source.
- **A replaced document must not outrank its replacement.** The YSR Rythu Bharosa
  order (12 chunks) took the top two places for every Annadata Sukhibhava question.
  Capping not-in-force chunks at one per answer: 79% -> 92%.
- **HyDE again earns its place on casual wording**: +15 to +19 points on both clean
  casual sets (50 -> 69%, 54 -> 69%), while costing 1-3 formal questions.
- **HyDE needs the local vocabulary.** It expanded "RBK" as "Rural Business Knowledge
  Centre". A glossary of official names (not descriptions -- "Kisan Credit Card crop
  loan" pulled in generic loan text) fixes that class without breaking others.
- **Agriculture is harder than RTI on casual questions (69% vs 82%).** The corpus is
  3.5x bigger and central guidelines (PMFBY OG: 465 chunks) crowd out short AP
  orders; most remaining misses sit at ranks 13-22.

### Answer quality (six farmer questions, read against the documents)

Round 1 problems and the rules added for them (agriculture prompt only):
- "the current Kharif 2024" in October 2026 -> the prompt now carries **today's date**
  and says to answer for the period in force (latest/extension order).
- a negative flipped ("must be recorded" for "name is NOT recorded") -> state
  conditions in the passage's own words, negatives included.
- a table put "tribal farmers" on the 40% rows -> prefer lists to tables.
- old name only ("YSR Sunna Vaddi") -> ALWAYS give the current name.
After: 5/6 right and cited, including the 2026 insurance cut-off dates. Still wrong:
cyclone relief for paddy -- G.O.No.2 (2025 enhanced rates, Rs.25,000/ha) has a garbled
text layer ("Padd Rs.17 000/- s.25 000/-"); needs OCR.

**Groq 413 "Request too large"** (8,025 tokens vs 8,000 per request on the free tier)
happened once with 14 long passages plus the longer rules: `answer.py` now drops the
three lowest-ranked passages and retries on a 413. Normal requests are unchanged.

### Known limitations (agriculture)

- Casual-question retrieval 69% (RTI 82%); misses are mostly near (ranks 13-22).
- 2 scans unindexed (fertiliser SOP 2024-25, FCO amendment 2024); G.O.No.2 garbled.
  No OCR engine is installed (no Tesseract/EasyOCR/RapidOCR) -- a separate step.
- Documents are still in `ingest/incoming/agriculture/` (staging), not promoted.
- Several orders are season-bound (Kharif 2026, KMS 2025-26); they need refreshing
  each season.

## Retrieval experiments and the router (2026-10-04/05)

Full write-up, every table and the reasons: `docs/RETRIEVAL_EXPERIMENTS.md`. Bench:
`eval/experiments.py`; every LLM output it used is cached in `eval/cache/`.

- **Each domain tuned separately, on all non-final question sets** (67 RTI, 79 agri),
  with new frozen sets written first: RTI `heldout4` (13) + `final` (15), agriculture
  `heldout3` (14) + `final` (14).
- **RTI: + LLM rewrite (topic + key terms).** 59 → 64/67; final set 12 → 15/15. The
  topic names the legal concept the casual question only describes ("third party
  information", "first appeal"). Rerankers *hurt* RTI (MiniLM 46–56, bge-reranker-base
  53–57): casual question vs legal wording is the same gap HyDE bridges.
- **Agriculture: + the same rewrite + MiniLM cross-encoder on the top 30, fused.**
  62 → 67/79, clean set 8 → 10/14; final set 14 → 13/14 (already saturated — the gain
  is real but smaller and less certain than RTI's). bge-reranker-base: 68/79 but
  11–15 s per question on this CPU vs 1.3–1.8 s for MiniLM.
- **No gain or worse:** RRF constants, BM25 stemming / title field, per-document caps
  and de-duplication (hurt), bigger embeddings for RTI, multi-query without HyDE, an
  agent picking documents first (right agriculture document 69/79, but documents are huge).
- **Router** (`rag/router.py`, `eval/router_eval.py`, `eval/router_questions.json`):
  one LLM call → rti / agriculture / other. gpt-oss-20b: 270/274 batched on all earlier
  sets incl. 71 real FAQ questions; **31/32 single-call on a set frozen before the
  router ever ran**. Embedding-similarity fallback: 83%, never says "other".
- **Free tier shaped everything:** 200,000 tokens per model per DAY. Experiments used
  qwen's and much of gpt-oss-20b's. Every LLM step now falls back (router 20b → qwen →
  embedding; rewrite qwen → 20b → none; HyDE → none; answer 120b → 20b), and a model
  that reports its daily limit is skipped for 10 minutes so questions don't wait on
  retries.
- Not run (token cap): corrective agent loop, LLM listwise reranking, HyPE,
  multi-style HyDE (34 RTI passages cached).

## Next steps

**Next major goal (decided 2026-10-04): multi-domain agentic assistant for the AP
government.** Route each question to one or more domains (RTI, finance, agriculture, or
a mix), run this pipeline's retrieval (HyDE + hybrid + amendment links) over each
domain's own index, and have a domain agent draft the cited answer. Follow-ups that stay
on topic should continue the conversation without re-running routing and retrieval.
Design to be settled with the faculty mentor; see `PROJECT_BRIEF.md`.

Improvements to the RTI domain itself:

1. **Project virtualenv** — cuts startup from ~30 s, and isolates the RAGAS/langchain
   dependency pile that slowed everything down.
2. **Write `heldout4` before any further change.**
3. **Test the zero-query-cost alternative to HyDE** — generate hypothetical *questions* per
   chunk at index time (Doc2Query/HyPE-style) and compare against HyDE on heldout4. This is
   the cost-thesis experiment.
4. **Remaining misses are mostly single sections of the Act** (s.2(f), s.7(8), s.8, s.19).
   Worth checking whether three-way fusion (question + rewrite + HyDE; best on heldout,
   83%) generalises — costs a second small call.
5. **Answer-level evaluation.** `retrieval_eval.py` only proves evidence arrived. The
   worst demo failures were in generation. A small hand-checked answer set (or RAGAS
   faithfulness on the demo questions) would catch them.

## Changelog

- **2026-10-05** — **Telugu questions translated for searching.** A question in Telugu script is translated to English (qwen3.8-27b) for every search step; the answer model gets the original plus an instruction to answer in Telugu script. 8 Telugu questions: 7/8 -> 8/8 in the top 10 (docs/RETRIEVAL_EXPERIMENTS.md, section 7). Web page fix: answer boxes stay inside the column.
- **2026-10-05** — **Docker.** `Dockerfile` + `compose.yaml` (+ allowlist `.dockerignore`):
  CPU-only PyTorch, both models and both Chroma indexes built into the image (2.77 GB;
  first build ~12 min, then `docker compose up --build` serves in ~40 s on
  http://localhost:8765 — 8000 was taken on the dev machine). Runs as a non-root user;
  the Groq key comes from `.env` at run time and is never in the image. Verified inside
  the container with the cached LLM outputs: RTI 79/82 and agriculture 80/93 (identical
  to the host), router final set 31/32; one live question answered. `web.py` gained
  `--host` (the container listens on 0.0.0.0).
- **2026-10-05** — **One interface for both domains, and each domain's best search
  switched on.** `rag/router.py` routes every question (default `--domain auto` in
  web.py, chat.py, answer.py); declined questions get "ask anyway" buttons. RTI adds the
  topic + key-terms rewrite (final set 12 → 15/15); agriculture adds it plus a MiniLM
  reranker (67/79). Fallbacks for every LLM step on Groq's daily limits.
  `eval/run_ragas.py` fixed (its system prompt moved to `rag/domains.py` on 10-04).
- **2026-10-04** — **Retrieval experiments.** `eval/experiments.py` bench,
  `rag/query_expansion.py`, `docs/RETRIEVAL_EXPERIMENTS.md`; ~40 configurations per
  domain on frozen sets, every LLM output cached.
- **2026-10-04** — **Agriculture runs through the same pipeline as RTI.** New
  `rag/domains.py` (per-domain documents, index, prompts); `--domain` on
  load_and_chunk, build_index, retrieve, answer, chat, web and retrieval_eval. RTI
  prompts moved verbatim; RTI retrieval unchanged at 47/54. Agriculture: 1,895 chunks,
  page limits for table-heavy orders, manifest-based amendment links, not-in-force
  labels and a one-chunk cap, title-prefixed embeddings, HyDE v3 + abbreviation
  glossary. Frozen sets in `eval/agri_questions.json`: dev 96%, dev_casual 92%, clean
  heldout2 69% (54% without HyDE). Agriculture answer rules: today's date, exact
  negatives, no invented steps, current scheme names. `answer.py` retries with fewer
  passages on Groq's 413 request-too-large. Web page text and suggestions per domain.
  See "Agriculture domain".
- **2026-10-04** — **Finance deferred; planned as one domain with subcategories.** A question
  routed to finance will be routed again to a subcategory (pensions, stamp duty &
  registration, vehicle tax, budget, professional tax, welfare payment status), each with its
  own documents. Collection waits until the owner has evaluated RTI (27) and agriculture
  (46). Recorded in `docs/DATA_COLLECTION_BRIEF.md` ("Status") and `ingest/incoming/finance/REPORT.md`.
- **2026-10-04** — **Agriculture: department site found, renames confirmed.** On the
  owner's approval, TLS verification was waived for apagrisnet.gov.in only (`UNVERIFIED_TLS`
  in `common.py`). Its certificate belongs to aptribes.gov.in (expired 2022), and behind it
  Apache returns 403 "unable to read htaccess file" on every path: the site is retired.
  The department now publishes on **agriculture.ap.gov.in**; new `catalog_agri.py` reads
  its document API (825 files). Added 19 agriculture documents (now **46**): **G.O.Ms.79
  (02-09-2024), the official rename table** (e-Crop -> e-Panta, YSR Rythu Bharosa ->
  Annadata Sukhibhava, Sunna Vaddi -> Vaddi Leni Runalu, Free Crop Insurance -> PMFBY,
  RBK -> Rythu Seva Kendram, ...), RBK founding G.O.Ms.37/2020, SDRF input-subsidy norms
  (Revenue DM G.O.Ms.1/2023, G.O.No.2/2025), Agriculture 4(1)(b) 2025-26, Kharif 2026 seed
  subsidy, farm mechanisation guide, Seeds/Fertiliser/Insecticides Acts and Orders. RTI
  gained the Agriculture PIO/FAA list (Dec 2025): **27**.
- **2026-10-04** — **Data collection for the multi-domain assistant** (branch
  `data-collection`, local only), following `docs/DATA_COLLECTION_BRIEF.md`. New tools in
  `ingest/collect/`: `catalog_apgov.py` (whole ap.gov.in API, 715 file links),
  `goir.py` (search of the AP G.O. register, every G.O. since 2008; the best single source),
  `collect.py` (candidates.json → files + manifest + inventory, computed checksums/pages/
  text layer/language). Staged in `ingest/incoming/`: **RTI 26 kept** (RTIMIS online
  filing live since G.O.Ms.25/2026; DPDP s.44(3) amending s.8(1)(j) in force 13-11-2025;
  RTI Amendment 2019 + Rules 2019; AP fee rules only changed by G.O.Ms.79/2020 head of
  account; current Commission G.O.Ms.7/2026 and sic.ap.gov.in now reachable),
  **agriculture 27 kept** (Annadatha Sukhibhava G.O.Ms.33/2025, PMFBY/RWBCIS 2024-27,
  seed/MSP/micro-irrigation/tenant orders, 9 central guidelines), **finance: scope
  proposal only** (awaiting review), **71 FAQ questions**. Found: every ap.gov.in file
  link, including all 41 current corpus sources, now returns 401/404; apagrisnet.gov.in
  has an expired certificate (not bypassed). Reports per domain in each `REPORT.md`.
- **2026-10-04** — **Put the project under git** and pushed to GitHub
  (`Nikhilkarur/AP-ASSIS`). Ignored: `.env`, `data/chroma/` (rebuild with the two ingest
  scripts), and the README exports (`README.html/.pdf/.png/.jpeg`, which go stale;
  README.md is the source). Refreshed stale docs: `PROJECT_BRIEF.md` rewritten to the
  current state (it still said "nothing coded yet" and MiniLM), `answer.py` docstring
  (top-10, not top-8), this file's structure and run sections (web UI was missing),
  conversation memory marked done. Recorded the next major goal: a multi-domain
  agentic assistant (README §7, Next steps above).
- **2026-09-29** — **Renamed the project to `ap-rti-assistant`** (folder
  `C:\Users\nkk77\Desktop\ap-rti-assistant`). Display name in titles and prose is
  "AP RTI Assistant", which the web UI already used; the slug is used for the folder,
  paths and code comments. Updated README.md, README.html, context.md,
  PROJECT_BRIEF.md, requirements.txt and the knowledge base.
- **2026-09-29** — Added `docs/AP RTI Assistant Knowledge Base.html`: a single
  self-contained page (no build step) modelled on `Desktop/OneClick Knowledge Base` —
  IBM Plex, light/dark, sticky contents, print styles. Ten sections: overview on one
  real question, why the portal fails a citizen (word-pair table, rare-word counts,
  the equity-gap study), the 546 -> 41 funnel and three corpus layers, a clickable
  8-stage pipeline (each stage gives what it does, the file it lives in and its
  numbers), three questions traced end to end with per-stage ranks (two successes,
  the BPL follow-up failure), decisions with measured numbers including five rejected
  ideas, how it is measured, a 15-term glossary, run commands, open items. OneClick's
  git-derived team/change-graph sections were dropped: this project is solo and not a
  git repo, so there is no data behind them.

- **2026-09-29** — **Correction to the 19 Sep "rewrite now carries the TOPIC" entry
  below: it does not.** That entry recorded an isolated test, where 120b turned "what
  if my family benglongs to bpl" into "Can I get a fee exemption ... if my family
  belongs to BPL?" and the white-card rule ranked 1st. Running the same two questions
  as a real conversation on 19 Sep, 120b twice returned "What if my family belongs to
  BPL?" with no mention of fees, and the white-card rule stayed at rank 43 — so the
  answer gave only the Act's s.7(5) proviso and missed the AP rule. The difference was
  the history text: the isolated test used a short hand-written summary, the real run
  a longer answer containing a markdown table. Cleaning tables and markdown out of the
  history (`_plain()` in `answer.py`, kept — it is an improvement) did NOT fix it: with
  the cleaned real history 120b still dropped the topic. Also rejected, with numbers:
  fusing a search on the previous question lifted the BPL case only to rank 7-13 and
  badly hurt topic switches (IB question rank 1 -> 18, "can the officer refuse" 15 -> 46).
  **Status: the rewrite carries "it"/"that" reliably but the topic only sometimes.**
  Untested idea for later: have the model emit the topic on a separate line and append
  it to the search text in code, so it cannot be dropped. Workaround meanwhile: name
  the subject in the follow-up. README limitations corrected to match.

- **2026-09-19** — Follow-up rewrite now carries the TOPIC, and uses `gpt-oss-120b`.
  Found in a live test: "what if my family benglongs to bpl" after a fee question was
  rewritten by 20b as "What if my family belongs to BPL?" — no mention of fees — and
  the AP white-card exemption (G.O.740) ranked 43rd, so the answer cited only the
  Act's s.7(5) BPL proviso and missed the AP rule. A topic rule in the prompt ("what
  if i am/was ..." asks about the topic under discussion) plus an example on appeals
  (not fees, so the BPL case stays a real test) did nothing on 20b at low or medium
  effort. 120b at low effort follows it: "Can I get a fee exemption for an RTI
  application if my family belongs to BPL?" -> white-card rule rank 1. Re-tested 5
  follow-ups: gold evidence at rank 1,1,1,1,2 (was 43,2,1,1,2); topic switch
  unaffected. ~600 tokens and ~1 s per follow-up on 120b's quota, so on a
  RateLimitError it drops to 20b immediately (max_retries=0) instead of waiting.
  Also observed: a follow-up answer took 15 s — Groq rate-limit wait, since the two
  questions were asked within seconds.

- **2026-09-19** — **Conversation memory**, cream/white UI, and a server hang fix.
  Memory: `answer.py` adds `standalone_question()` — with history, `gpt-oss-20b`
  rewrites the follow-up into a standalone question (the "condense question"
  pattern) and retrieval uses that; the answer prompt gets the last 3 turns
  (answers cut to 600 chars, citation markers stripped) labelled "to understand the
  question only — not a source of facts", plus a system-prompt rule to that effect.
  The first condense prompt only fixed spelling ("wht if i still dont get it" ->
  "What if I still don't get it?"); rewritten to say the output is searched WITHOUT
  the conversation, with examples on other topics. Now resolves "it" ("how much does
  it cost" -> "...to file an RTI application?") but neither 20b nor 120b carries the
  situation behind "still"/"now". Measured whether that matters: searching with the
  rewrite alone put the appeal sections at rank 2 and "free of charge" at rank 1;
  adding the previous question to the search text helped the first case (2 -> 1) but
  hurt a topic switch (2 -> 3/4), so rewrite-only was kept. `chat.py` keeps history
  and has `/new`; the web page keeps history client-side (stateless server), shows
  "Understood as: ..." for rewritten follow-ups, and has a New chat button.
  Theme: cream (#faf6ee) and white, light only, at the user's request.
  Bug fixed: the single-threaded `HTTPServer` froze when Chrome opened an idle
  preconnect socket; now `ThreadingHTTPServer` with a lock so questions still run
  one at a time. Tested end to end in the browser: question -> follow-up ("wht if i
  still dont get it", answered in context in 8 s) -> New chat.

- **2026-09-19** — Added a minimal web UI: `rag/web.py` (Python standard-library
  `http.server`, no new dependencies; GET / serves `rag/web.html`, POST /ask returns
  JSON) and `rag/web.html` (one page, no external scripts or fonts; tiny built-in
  markdown renderer; clickable citations open the cited source's text; "How it
  searched" shows the HyDE passage; suggested questions; light/dark). Single-threaded
  on purpose so rapid clicks queue instead of tripping Groq's rate limit. To support
  it, `answer.py` now splits `answer_question()` (returns a dict) from `ask()`
  (prints for the terminal); `chat.py` and `eval/` are unchanged in behaviour.
  Tested end to end in the browser pane: 4 s per answer, citation click, lists,
  tables, HTML escaping, empty-question error. Added `.claude/launch.json` for the
  preview server.

- **2026-09-19** — Pre-review fixes. (1) `retrieve.py`: HyDE failures are no longer
  cached — previously one rate-limited call silently disabled HyDE for that question
  for the rest of a chat session. (2) `answer.py`: two general rules added — cite a
  passage only for what it says; for refused/ignored/delayed requests give every
  remedy the passages contain, leading with the appeal route. Re-ran the 5
  ground-truthed demo questions; answers saved to `eval/demo_backup_answers.md`.
  Result: 4 correct, 1 improved but flawed — "not replied for 45 days" now leads with
  the first appeal (was: complaint only) but muddles first- vs second-appeal details
  (credits the Commission with the first appeal's late-filing rule and 30/45-day
  limit, omits the 90-day second-appeal limit) and offers a department officer and an
  old Hyderabad address. Section 7 (deemed refusal, free of charge) is still not
  retrieved for that phrasing. README corrected where it overstated this question.
  Found while reviewing, not fixed (changes rankings, needs re-evaluation):
  BM25 ranks zero-score chunks by index position, giving early-indexed chunks a small
  unearned RRF boost — may explain G.O.639 appearing in unrelated results.
  Correction: Section 10(2)(e) does mention review rights and the s.19 senior officer,
  but only for partial disclosure — so citing it for full refusals is a misapplication,
  not an unrelated section.

- **2026-09-13** — Added `README.md`: a standalone write-up of the problem statement,
  data, the four phases of work, current architecture, results, limitations and next
  steps, for readers who haven't followed this log. `PROJECT_BRIEF.md` is now stale
  (still says "nothing coded yet").
- **2026-09-13** — **Iterated the vanilla RAG into a working demo.** Full record in
  "Iterating to a working demo". Ingest: bge-small-en-v1.5; token-sized sentence-aligned
  chunks (350/60, 535 chunks, zero truncation); RTI Act split by its 31 sections with
  section citations; department and currency labels; automatic amendment links (G.O.454
  ← 530, 545, 740). Query: HyDE passage (gpt-oss-20b) + hybrid dense/BM25 search, RRF-fused
  with the original question, top 10, plus up to 4 amendment chunks. Answer: grounding
  rules for partial answers, exact figures, amendments, dated office-holders, and
  department contacts; `[n]` citations; rate-limit fallback to gpt-oss-20b. Retrieval
  coverage on casual held-out questions ~50% → 82%. Added `eval/demo_questions.json`
  (four frozen sets) and `eval/retrieval_eval.py`. Corrected an earlier claim: the AP RTI
  fee schedule is in the corpus. Contextual title prefixes and naive query rewriting were
  tested and rejected.
- **2026-09-04** — Initial plan. Vanilla RAG: gather AP RTI PDFs → standard chunking → Chroma → top-8 retrieval → Groq API for answers. Embeddings via local sentence-transformers (Groq has no embeddings API).
- **2026-09-04** — Audited the whole `ap.gov.in` RTI & Acts section (546 docs, 7 sections)
  and classified every document. Settled the corpus at **41 files / 398 pages**. Key
  finding: the RTI Act itself is not in the "Acts" section — it's buried at
  Department–Org RTI → GAD → s.4(1)(A). Full audit kept in `ingest/inventory_rti_acts.json`.
- **2026-09-04** — Downloaded the corpus into `ingest/documents/` with
  `ingest/corpus_manifest.json` (title, department, group, source URL, page count,
  SHA-256 per file). Added `requirements.txt` (versions verified against PyPI).
- **2026-09-04** — **Diagnosed why the vanilla RAG underperforms.** Full write-up in the
  "Diagnosis" section above. Headline: retrieval mechanics are fine, the query is the
  bottleneck — a corpus-worded rewrite moves the gold chunk from **rank 106 to rank 6**.
  Encoder swaps do not help (MiniLM 60% vs bge 67% evidence recall@8, within noise).
  Compared against the AP govt's own chatbot (it answered our benchmark question
  correctly, drawing on 7 provisions across 3 sections) and against
  `~/Desktop/rgbackup/sar-rag_v1` (not vanilla — contextual chunking, token-aware
  sectioning, multi-query fan-out). Added `eval/compare_embeddings.py`, a no-LLM
  recall@k harness for testing changes cheaply. Direction agreed: invest in
  **preprocessing / index-time work** for cost efficiency rather than a bigger LLM or
  multi-agent. Prior art checked and recorded (Doc2Query, Contextual Retrieval, HyDE,
  Adaptive-RAG) — the area is well-studied, so novelty must come from the domain and
  the budget constraint, not the technique.
- **2026-09-04** — **Working end to end against the live Groq API.** Added `rag/chat.py`
  (interactive loop; `/sources`, `/k N`, `/quit`). Verified answers are correct and
  cited: "time limit for the PIO to respond" → 30 days, +5 when filed via an Assistant
  PIO, quoting s.7; "can they refuse" → s.8 exemptions plus the duty to give reasons
  and appeal details. The model correctly refuses to invent a fee amount when the
  passages don't contain one.
  **Two corrections to the stack as planned:**
  1. **No Llama model is available on our Groq account.** Checked 2026-09-04 — the only
     `llama-*` entries are prompt-guard safety classifiers, not chat models. Reachable
     chat models: `openai/gpt-oss-120b` (now the default), `openai/gpt-oss-20b`,
     `qwen/qwen3.8-27b`, `qwen/qwen3.6-27b`, `groq/compound`, `groq/compound-mini`,
     `allam-2-7b`. Override with `GROQ_MODEL` in `.env`.
  2. **Windows console is cp1252** and crashed on characters the model emits
     (U+202F narrow no-break space). Both `rag/*.py` now force UTF-8 stdout.
  No conversation memory yet — each question is answered independently.
- **2026-09-04** — **Vanilla RAG complete end to end.** Added `ingest/build_index.py`
  (766 chunks → `all-MiniLM-L6-v2` → Chroma at `data/chroma`, cosine, 384 dims),
  `rag/retrieve.py` (top-8) and `rag/answer.py` (context + question → Groq).
  Added `.env.example` and `.gitignore`.
  **Measured: 207 of 766 chunks (27%) exceed MiniLM's 256-token window** and are
  silently truncated at embedding time (median chunk 216 tokens, max 503, 13,714
  tokens dropped). Kept MiniLM as planned; `build_index.py --check` re-reports this.
  **Known quality problem — vocabulary mismatch.** Retrieval is good when a question
  uses the Act's own wording ("request in writing to the Public Information Officer"
  → the right chunk of s.6 at 0.72) and poor in plain citizen language ("how do I
  apply for information under RTI?" → returns scheme-beneficiary lists and IT-staffing
  orders; s.6 does not appear at all). The corpus is legalese, users are not.
  First thing to fix in the next iteration — candidates: query rewriting, a reranker,
  hybrid BM25 + dense, or a larger embedding model.
- **2026-09-04** — Added `ingest/load_and_chunk.py`. Standard chunking, **1000 chars /
  200 overlap**, split on whitespace so words stay whole (both chunk starts and ends —
  the naive version opened chunks mid-word). Produces **766 chunks** from the 41
  documents (747,713 chars, avg 976/chunk) into `ingest/chunks.json`. Each chunk carries
  title, department and source URL so citations are possible later without re-indexing.
  Cleaning is deliberately light: whitespace normalisation only. The PDFs contain stray
  spaces inside words ("Informati on") from extraction; repairing those is unreliable
  and embeddings tolerate it.
- **2026-09-04** — Deleted the one-off downloader script after the fetch, to keep the
  repo focused on the vanilla RAG path. The corpus is fully re-derivable from the
  source URLs in `corpus_manifest.json` plus the selection rules recorded above.
  Revisit when we build a real crawler for refreshes.
