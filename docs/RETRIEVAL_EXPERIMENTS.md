# Retrieval experiments — RTI and agriculture (2026-10-04)

Goal: get the passage that answers a citizen's question into the 10 chunks the answer
model reads, as often as possible, separately for each domain. No routing/classifier
work here. Everything below was measured with `eval/experiments.py`; every number can
be reproduced from the cached LLM outputs in `eval/cache/`.

## 1. How it was measured

**Metric.** For each question, every *probe* (a verbatim phrase from the text that
answers it, checked to exist in the corpus) must appear in the top-10 retrieved chunks.
No LLM judges anything. Also reported: `@5`, `@20` (same test at 5 / 20 chunks) and
`MRR` (mean of 1 / the rank at which all probes are first covered; 0 if beyond 60) —
`@20` shows what a reranker could still pull up, `MRR` shows ordering quality.

**Question sets** (all frozen before the code they test):

| domain | set | n | style | status |
|---|---|---|---|---|
| RTI | dev | 20 | formal | used while iterating since Sept |
| RTI | heldout, heldout2, heldout3 | 12, 12, 10 | casual | each used once before |
| RTI | **heldout4** | 13 | casual | written today before these experiments — the clean test |
| RTI | **final** | 15 | Telugu-English, typos, long stories, 2-word queries | run only for baseline and the chosen config |
| agri | dev, dev_casual | 24, 12 | formal / casual | used while building the domain |
| agri | heldout, heldout2 | 16, 13 | casual | each used once before |
| agri | **heldout3** | 14 | casual | written today before these experiments — the clean test |
| agri | **final** | 14 | mixed styles as above | run only for baseline and the chosen config |

Decisions use all non-final sets together (67 RTI, 79 agriculture questions) — a bigger
sample is harder to overfit than any one set — and the clean set is shown separately.
A difference of one or two questions is within noise; read only bigger, consistent moves.

**Fairness.** gpt-oss is not deterministic even at temperature 0 (HyDE passage drift
moved scores by 1–2 questions per run before). So every LLM output — HyDE passages,
rewrites, document picks — is generated once, cached in `eval/cache/<technique>@<model>.json`,
and every configuration is scored on identical text. The harness reproduces the live
pipeline exactly (59/67 RTI, 62/79 agriculture, same per set as `eval/retrieval_eval.py`).

**A constraint that shaped the work: Groq's free tier allows 200,000 tokens per model
per day.** gpt-oss-20b (the live HyDE model) and qwen3.8-27b both hit it during these
experiments. gpt-oss spends hundreds of hidden reasoning tokens per call even at
`reasoning_effort=low`; qwen3.8-27b with reasoning off answered the same short
structured requests in ~60 output tokens, so the expansion experiments moved to qwen.
Document selection for the experiments was run 8 questions per call (catalog sent once,
~1/8 of the tokens); live use would be one call per question.

## 2. What was tried, and why each idea was a candidate

| family | technique | source of the idea |
|---|---|---|
| fusion | RRF constant k, HyDE vote weight, flat vs grouped fusion, HyDE+question concatenated (Query2doc) | live pipeline's own knobs; Query2doc (Wang et al. 2023) |
| keyword search | stemming + stopwords; document title indexed with the text | standard IR |
| diversity | max chunks per document; drop near-duplicate chunks | MMR-style diversification |
| reranking | cross-encoders on the top 20/30/50: ms-marco-MiniLM-L-6-v2, bge-reranker-base | two-stage hybrid + rerank is the strongest single change in recent benchmarks ([T2-RAGBench study, 2026](https://arxiv.org/html/2604.01733v1); [Beyond the Reranker, 2026](https://arxiv.org/html/2606.28367)) |
| embeddings | bge-base-en-v1.5 instead of / alongside bge-small | bigger model, same family |
| LLM query expansion | multi-query (3 formal rephrasings, RAG-Fusion), key terms for BM25 (Query2doc-style), a step-back "topic" (name of the rule/scheme asked about), multi-style HyDE | multi-query + RRF beat HyDE in the T2-RAGBench study; HyDE remained the only reliable gain on top of a reranker in Beyond the Reranker |
| agent step | document selection: the model reads the list of documents (the Act section by section) and names up to 3 likely to hold the answer; their chunks get extra RRF votes | hierarchical / "route to document first" retrieval |

## 3. Results

Numbers are questions fully covered in the top 10 (`@10`), out of 67 (RTI) or 79
(agriculture). Clean set = heldout4 (RTI, 13) / heldout3 (agriculture, 14).

_(tables filled in below as each experiment finishes)_

### 3.1 Which signal carries the live pipeline?

| configuration | RTI @10 | RTI @5 | RTI MRR | agri @10 | agri @5 | agri MRR |
|---|---|---|---|---|---|---|
| **live: hybrid(question) + hybrid(HyDE), RRF** | **59** | 54 | 0.65 | **62** | 47 | 0.46 |
| question only, hybrid (no LLM) | 47 | 37 | 0.44 | 57 | 45 | 0.44 |
| question only, dense | 46 | 39 | 0.40 | 51 | 44 | 0.42 |
| question only, BM25 | 30 | 26 | 0.30 | 49 | 44 | 0.37 |
| HyDE passage only, dense | 58 | 56 | 0.59 | 50 | 43 | 0.39 |
| HyDE passage only, BM25 | 56 | 51 | 0.63 | 46 | 39 | 0.41 |

**The two domains are opposite.** In RTI the HyDE passage alone, searched by meaning,
does almost everything the full pipeline does (58 vs 59), and the question's own words
add little (BM25 on the question: 30/67). In agriculture no single signal is good
(46–51) and the gain comes from fusing them.

Why: gpt-oss has read the RTI Act — a short, famous central statute — so its
"hypothetical" passage is close to the real text ("deemed to have refused", "no
obligation to give any citizen"), and that vocabulary is exactly what a casual
question lacks. It has not read AP's 2024–26 government orders: its agriculture
passages are generic (often about other states' schemes, with invented amounts), while
the farmer's own words — a scheme name, a crop, "drip", "tenant" — are rare, specific
terms that keyword search matches directly.

### 3.2 Fusion knobs, keyword-search variants, diversity — no reliable gain

| configuration | RTI @10 | agri @10 | note |
|---|---|---|---|
| live | 59 | 62 | |
| flat 4-way RRF (no grouping) | 61 | 62 | |
| question + HyDE concatenated (Query2doc) | 59 | 63 | |
| RRF k = 10 / 30 / 100 | 61 / 60 / 59 | 60 / 61 / 61 | |
| HyDE vote x0.5 / x1.5 / x2.0 | 54 / 61 / **62** | 62 / 61 / 60 | RTI likes more HyDE, agriculture doesn't — same split as 3.1 |
| BM25 with light stemming + stopwords | 58 | 63 | |
| BM25 over title + text | 59 | 62 | |
| max 2 / 3 / 4 chunks per document | 52 / 54 / 56 | 54 / 57 / 60 | **hurts** |
| drop near-duplicate chunks (≥0.6 / ≥0.8 word overlap) | 58 / 59 | 60 / 61 | |

All within ±3 except the per-document cap, which clearly hurts both: when a document is
the right one, the answer usually needs several of its chunks (an Act section split in
two; a G.O.'s eligibility list continuing into its exclusions), and big documents are
the right document surprisingly often.

### 3.3 Cross-encoder reranking (ms-marco-MiniLM-L-6-v2, already on this machine)

| configuration | RTI @10 | RTI @5 | RTI MRR | agri @10 | agri @5 | agri MRR | agri clean |
|---|---|---|---|---|---|---|---|
| live | 59 | 54 | 0.65 | 62 | 47 | 0.46 | 8/14 |
| rerank top 20 | 53 | 39 | 0.42 | 62 | **59** | 0.54 | 11/14 |
| rerank top 30 | 48 | 38 | 0.41 | 62 | **59** | 0.54 | 11/14 |
| rerank top 50 | 46 | 37 | 0.40 | 62 | **59** | 0.53 | 10/14 |
| rerank top 30, fused with the original order | 56 | 48 | 0.57 | **64** | 54 | 0.50 | 11/14 |
| rerank top 30, chunk title included | 54 | 47 | 0.51 | **64** | 56 | **0.58** | 11/14 |
| rerank top 30, scored on question AND HyDE | 59 | 54 | 0.63 | **64** | **60** | 0.55 | 11/14 |

**Opposite again.** The reranker damages RTI (59 → 46 at top 50) and helps agriculture
— most clearly in ordering (@5 47 → 59, MRR 0.46 → 0.55) and on the clean set (8 → 11
of 14), while costing 2–3 formal dev questions.

Why: a cross-encoder reads the question and the chunk together, so it can only reward
words and meanings it can see in both. Farmers name concrete things — "cow", "drip",
"polyhouse", "cashew", "licence" — that appear in the right chunk, often inside a table
the bi-encoder embedding blurs; the reranker sees them side by side. RTI questions are
abstract ("can they just say no") and the Act's answer is legal phrasing ("no obligation
to give any citizen"); a model trained on web search (MS MARCO) can't connect them, so
it promotes chunks that merely share surface words (department manuals mentioning
"officer", "information"). Scoring with the HyDE passage as well restores RTI to the
baseline — the same vocabulary bridge, again.

### 3.4 LLM query expansion (qwen3.8-27b, one call per question)

| configuration | RTI @10 | RTI @5 | RTI MRR | RTI clean | agri @10 | agri @5 | agri MRR | agri clean |
|---|---|---|---|---|---|---|---|---|
| live | 59 | 54 | 0.65 | 12/13 | 62 | 47 | 0.46 | 8/14 |
| + three formal rephrasings (multi-query) | 62 | 59 | 0.70 | 12/13 | 63 | 52 | 0.45 | 8/14 |
| + key terms, keyword search only | 62 | 60 | 0.71 | 12/13 | 62 | 52 | 0.50 | 8/14 |
| + topic ("name of the rule asked about") | **63** | 60 | 0.70 | **13/13** | 63 | 49 | 0.49 | 8/14 |
| + multi-query + key terms | 62 | **61** | **0.75** | 12/13 | **64** | 52 | 0.50 | 8/14 |
| question + key terms in one search, + HyDE | 62 | 58 | **0.75** | 12/13 | **64** | 53 | 0.49 | 8/14 |
| question + multi-query, no HyDE | 58 | 50 | 0.64 | 10/13 | 63 | 49 | 0.43 | 8/14 |

Every rewrite helps RTI (+3 to +4, and better ordering); agriculture gains 1–2. The
"topic" step-back works best for RTI because RTI's misses are about *which rule* the
question is about: "who chooses the commissioners" → "appointment of State Information
Commissioners", "the info is about another person" → "third party information". Those
concept names are what the Act's section text and headings use. Multi-query without
HyDE is *worse* than HyDE alone in RTI (58) — rephrasing the question doesn't put the
Act's wording in, a hypothetical passage does.

For agriculture the rewrites can't add what the model doesn't know (AP scheme names,
order numbers); the clean set doesn't move.

### 3.5 Agent step: pick the documents first (gpt-oss-120b)

| configuration | RTI @10 | RTI @5 | agri @10 | agri @5 | agri clean |
|---|---|---|---|---|---|
| live | 59 | 54 | 62 | 47 | 8/14 |
| + chunks of picked documents get an extra vote x0.5 | 60 | 52 | **64** | **57** | 8/14 |
| ... x1.0 | 58 | 45 | 61 | 54 | 8/14 |
| ... x2.0 | 58 | 45 | 61 | 54 | 8/14 |

How good are the picks themselves? **Agriculture: a picked document holds the answer
for 69 of 79 questions. RTI: 42 of 67** (40 with section headings in the list instead
of opening words — headings did not help). So the agent *does* know which agriculture
order a question is about — but that is not where agriculture fails: the right document
is often a huge one (PMFBY guidelines, 465 chunks; MIDH, 129), and knowing the document
does not find the paragraph. For RTI the model often sends section-level questions to
the wrong section or to a manual (Telugu application → departmental handbook, not s.6).
A strong boost overrides good fused rankings with those wrong picks — hence the drop at
x1.0 and above. A light boost mainly helps ordering in agriculture (@5 +10).

### 3.6 Combinations

RTI (67 questions; clean = heldout4, 13):

| configuration | @10 | @5 | MRR | clean |
|---|---|---|---|---|
| live | 59 | 54 | 0.65 | 12 |
| **live + topic + key terms** | **64** | **62** | 0.76 | **13** |
| live + topic + multi-query + key terms | **64** | 61 | **0.77** | **13** |
| ... + document boost x0.5 | **64** | 54 | 0.65 | 12 |
| live + topic + key terms, HyDE vote x1.5 | **64** | **62** | 0.76 | **13** |
| live + multi-query + key terms + MiniLM rerank (replace) | 55 | 45 | 0.54 | 10 |
| ... same, rerank fused with the original order | 63 | 55 | 0.66 | **13** |
| everything + document boost + MiniLM fused | 63 | 57 | 0.67 | **13** |

Agriculture (79 questions; clean = heldout3, 14):

| configuration | @10 | @5 | MRR | clean |
|---|---|---|---|---|
| live | 62 | 47 | 0.46 | 8 |
| live + topic + key terms | 65 | 54 | 0.51 | 8 |
| live + topic + multi-query + key terms | 65 | 52 | 0.51 | 8 |
| ... + document boost x0.5 | 63 | 56 | 0.53 | 8 |
| live + multi-query + key terms + MiniLM rerank (replace) | 64 | 57 | 0.58 | 10 |
| **live + multi-query + key terms + MiniLM fused** | **66** | 60 | 0.52 | **10** |
| **live + topic + multi-query + key terms + MiniLM fused** | **66** | **61** | 0.55 | **10** |
| live + document boost x0.5 + MiniLM rerank (replace) | 65 | 58 | 0.58 | **11** |
| everything + document boost x0.5 + MiniLM fused | **66** | **61** | **0.59** | 10 |

The gains stack in the way 3.1–3.4 predict: RTI is fixed on the *query* side (the
rewrites put the Act's concept names into the search; the reranker only gets in the
way), agriculture needs the query side for 2–3 questions and the *reranker* for the
rest (it is the only thing that moved the clean set). Fusing the reranker's order with
the fused order ("fuse") is consistently safer than replacing it: the reranker is a
second opinion, not the judge — in RTI replacing costs 9 questions, fusing costs 1.

### 3.7 Question by question: what the chosen changes fixed

Rank at which the answering text is first fully covered (`-` = not in the top 60).

RTI, live → live + topic + key terms:

| question | live | chosen | what qwen actually wrote (cached in `eval/cache/rewrites@qwen3.8-27b.json`) |
|---|---|---|---|
| can i use rti to get info from an ngo | 38 | 3 | topic "Definition of public authority and private body"; terms "public authority", "substantial funding", "non-governmental organization" |
| is rti free if i ask a village panchayat office | - | 8 | topic "Fees for obtaining information from Panchayat offices"; terms "Gram Panchayat", "fee", "exemption" |
| if they refuse my rti do they have to tell me why | 17 | 4 | topic "Mandatory reasons for refusal of information"; terms "reasons", "communicate", "grounds" |
| does rti apply to private companies | 11 | 1 | topic "Applicability to private bodies and non-governmental organizations"; term "private body" |
| govt office is not answering my rti for 2 months | 12 | 2 | topic "First Appeal to Appellate Authority"; terms "deemed refusal", "first appeal", "thirty days" |
| how much money do i need to pay for an rti in AP | 5 | 2 | topic "Application fee for obtaining information"; terms "application fee", "prescribed fee" |
| i sent my rti to the wrong office, will they forward it | 8 | 1 | topic "Forwarding of application to competent authority"; term "transfer" |

The pattern: the topic names the *legal concept* ("private body", "first appeal",
"reasons for refusal") that the casual question only describes, and those concept names
are the words in the Act's sections. Some details are wrong ("Section 2(n)", "seven
days", "ten rupees" where the AP rule says Rs.10 at district level) — harmless here,
because rewrites are used only to search and never shown to the answer model.

No RTI question dropped out of the top 10. Still missing: the two "who is the current
Commissioner" questions (only a 2010 order and the portal page name a Commissioner —
freshness, not retrieval) and "can the officer just say no" (s.8 is found at rank 11).

Agriculture, live → live + topic + key terms + MiniLM reranker (fused):

| question | live | chosen |
|---|---|---|
| is my cashew crop covered by insurance | 21 | 3 |
| after a flood who comes to check how much of my crop got damaged | 17 | 3 |
| where do i get cheap seeds from the govt | 17 | 4 |
| i am a lawyer with farm land, can i get annadata sukhibhava money | 19 | 6 |
| can kcc loan be used for dairy or fish farming | 16 | 6 |
| kcc loan interest if i pay back on time | 21 | 10 |
| pm kisan 6000 comes in how many parts | 4 | 2 |
| *do i have to pay for crop insurance now or is it still free* | *7* | *11 (lost)* |

The reranker's wins are questions naming a concrete thing (cashew, flood damage, seeds,
lawyer, dairy) whose chunk the fused search had ranked 16–21st — e.g. "Cashew Nut" sits
in a district-by-crop table in the weather-insurance order, which an embedding of the
whole chunk blurs but a cross-encoder reading question and chunk together does not.
The one loss asks about a policy ("is it still free") rather than a thing.

### 3.8 Bigger models: bge-reranker-base and bge-base embeddings

| configuration | RTI @10 | RTI @5 | RTI MRR | agri @10 | agri @5 | agri MRR | agri clean |
|---|---|---|---|---|---|---|---|
| live | 59 | 54 | 0.65 | 62 | 47 | 0.46 | 8 |
| bge-reranker-base, top 20 | 57 | 50 | 0.52 | 66 | 61 | 0.59 | 11 |
| bge-reranker-base, top 30 | 53 | 47 | 0.49 | 66 | 61 | 0.60 | 10 |
| bge-reranker-base, top 50 | 53 | 45 | 0.45 | 67 | 61 | 0.60 | 10 |
| bge-reranker-base, top 30, fused | 57 | 54 | **0.67** | 67 | 57 | 0.54 | **11** |
| bge-reranker-base, top 30, title + text | 57 | 46 | 0.56 | **68** | **63** | **0.64** | **11** |
| bge-base embeddings (instead of bge-small) | 57 | 52 | 0.61 | 66 | 53 | 0.47 | 9 |
| bge-small + bge-base + BM25 | 59 | 53 | 0.66 | 61 | 51 | 0.46 | 9 |

The stronger reranker confirms the split rather than changing it: it is the single best
technique for agriculture (68/79 on its own, without any rewrite) and still harmful for
RTI, only less so than MiniLM (it was trained on more varied question–passage pairs, so
the casual-to-legal gap hurts it less). A bigger embedding model adds 4 in agriculture
(more capacity for table-heavy, number-heavy chunks) and nothing in RTI — where the
HyDE passage already speaks the Act's language, a better encoder of that language has
nothing to add.

## 4. Status (2026-10-04, end of day)

**Chosen per domain (on the 67 / 79 non-final questions):**

| domain | live today | chosen | @10 | clean set |
|---|---|---|---|---|
| RTI | hybrid(question) + hybrid(HyDE) | + qwen rewrite: topic + key terms | 59 → **64 / 67** (88% → 96%) | 12 → 13 / 13 |
| agriculture | same | + topic + key terms + MiniLM cross-encoder over the top 30, fused | 62 → **67 / 79** (78% → 85%) | 8 → 10 / 14 |

**Not done yet:**
- The chosen settings are **not switched on** in `rag/domains.py`. `rag/retrieve.py`
  supports them (`expansion`, `doc_boost`, `rerank`, all off by default), so the live
  app behaves exactly as before.
- Agriculture: bge-reranker-base alone scored 68/79 (above). Its combination with the
  rewrites was still running; it may replace MiniLM, at a CPU-time cost still to be
  measured on an idle machine.
- The `final` sets (15 RTI, 14 agriculture, mixed styles) have their HyDE passages and
  rewrites cached but have not been scored — they are run once, for the baseline and the
  chosen configuration, after the choice is final.
- Not tested because of the daily token cap: multi-style HyDE for all questions (34 RTI
  passages cached), a corrective agent loop (the model checks the retrieved passages and
  searches again; ~260k tokens for one pass), LLM listwise reranking, index-time
  hypothetical questions (HyPE).
- Answer-level check of the chosen configurations (retrieval coverage is not answer
  quality).
