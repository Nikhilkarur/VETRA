# Retrieval architectures for answering from official documents, including versioned and amended law

Researched 5 November 2026. This builds on `docs/ARCHITECTURE_RESEARCH.md` and only mentions it to confirm or overturn it.

**How to read the evidence labels**
- **Independent:** the authors did not propose or sell the method they measured.
- **Author-run:** the authors measured their own method, in a paper.
- **Vendor:** a company's own claim about its own product, on a blog, README or model card.
- **Secondary:** read through someone else's summary.

**How far to trust the numbers**
- Most figures come from arXiv HTML pages read through a fetch tool that summarises the page with a small model, so I did not see the tables directly. Spot-check any number before quoting it in project docs.
- Most PDFs would not decode, so I used the HTML versions.
- None of these studies uses Indian government documents.

**What I read in the project, without running anything**
- `vetra/checks.py`, `vetra/sorter.py`, `rag/domains.py`, `vetra/domains.py`, and `knowledge/*/*.jsonl`.
- Claims about VETRA's code below come from reading these files.

## Late interaction: does it beat hybrid plus cross-encoder, and is it practical on CPU?

### Takeaway
No study I found measures modern late interaction against hybrid plus cross-encoder on Indian languages. The nearest evidence does not favour it: a cross-encoder beat ColBERTv2 as a reranker on all five shared benchmarks, and BGE-M3 beat the multilingual late-interaction models on Bengali and Telugu. It is practical on CPU at this corpus size, but there's no reason to adopt it before the BGE-M3 test. At most, test BGE-M3's own ColBERT vectors as a reranker.

| Technique | Evidence | What it would improve in VETRA | CPU cost and complexity | Recommendation |
|---|---|---|---|---|
| Replace hybrid plus cross-encoder with a ColBERT index (PLAID) | Independent, on English sets only: weaker than cross-encoders | Nothing measured | Needs a second index, since I found no multi-vector support in Chroma's docs | **Skip** |
| BGE-M3 ColBERT vectors as a reranker over hybrid results, no index | No Indian-language rerank result found | Multilingual reranking without a second model | Low to moderate: store token vectors, score only about 50 candidates. CPU time not measured anywhere | **Test**, only alongside the BGE-M3 switch |
| mLateOn | Author-run, MIRACL. Trails BGE-M3 on Bengali and Telugu, ties on Hindi | Possibly the languages BGE-M3 handles badly, which nobody has measured | Moderate, 307M parameters | **Test later**, only if BGE-M3 fails on specific languages |
| Jina-ColBERT-v2 | Author-run, plus LightOn's rerun | Same as above | Licence is CC-BY-NC | **Skip** for a product. Usable as a research reference |
| Reason-ModernColBERT | Author-run on BRIGHT, an English reasoning benchmark | Nothing here: English only | Licence is CC-BY-NC | **Skip** |
| LFM2-ColBERT-350M | Vendor | Nothing here: no Indian language listed | LFM licence | **Skip** |
| Multilingual cross-encoder (bge-reranker-v2-m3) replacing MiniLM | Independent on English sets. Multilingual result is only a vendor chart | The current reranker is an English model, which matters for 22 languages | Heavier than MiniLM (0.6B parameters). CPU time unmeasured | **Test**. Already idea 5 in the doc, now with better evidence |

### Cited Findings
**Reranking head-to-head (independent, English benchmarks, EMNLP Findings 2025)**
- nDCG@10 for ColBERTv2 against bge-reranker-v2-m3: DL19 69.02 vs 72.19, DL20 66.78 vs 66.98, Covid 72.6 vs 74.79, SciFact 67.74 vs 73.48, Robust04 45.83 vs 48.44. ColBERTv2 lost all five — [How Good are LLM-based Rerankers?](https://arxiv.org/html/2508.16757v1)
- The MiniLM cross-encoder scored 70.80, 66.27, 69.06, 66.28 and 47.18 on the same sets, so bge-reranker-v2-m3 beat it by 0.7 to 7.2 points, and ColBERTv2 against MiniLM was mixed. The MiniLM row is the FlashRank packaging — [same paper](https://arxiv.org/html/2508.16757v1)
- On the novel-query set, ColBERTv2 scored 54.20 and MiniLM-L-12 55.43. bge-reranker-v2-m3 has no reported score there — [same paper](https://arxiv.org/html/2508.16757v1)
- This tests ColBERTv2 only, not the 2025-26 models. I found no equivalent test with them.

**Multilingual late interaction (author-run, MIRACL, native-language queries over native-language documents)**

| Model | Hindi | Bengali | Telugu |
|---|---|---|---|
| mLateOn | 60.4 | 73.4 | 71.8 |
| mDenseOn | 54.6 | 54.5 | 61.6 |
| BGE-M3 | 60.1 | 79.9 | 86.3 |
| jina-colbert-v2 | 64.7 | 75.6 | 77.2 |

- Figures from the [LateOn paper, July 2026](https://arxiv.org/html/2607.27178). These three languages are unseen in mLateOn's training. Result goes against the authors' own model on two of three, which makes it more believable.
- Late interaction does generalise better than dense from the same training recipe, per the same table: mLateOn beats mDenseOn on all three — [same paper](https://arxiv.org/html/2607.27178)
- Conflict: Jina's own paper gives jina-colbert-v2 60.0 / 75.0 / 74.2, against 64.7 / 75.6 / 77.2 in LightOn's rerun. In Jina's paper, language-tuned mDPR beat it on Telugu (80.4), and BM25 scored 45.8 / 50.8 / 49.4 — [Jina-ColBERT-v2](https://arxiv.org/html/2408.16672v3)
- The mLateOn model card lists nine training languages, none Indian, under Apache 2.0, with 128 dimensions per token — [model card](https://huggingface.co/lightonai/mLateOn)
- Reason-ModernColBERT: English only, cc-by-nc-4.0. BRIGHT full mean 22.62 against BM25 14.53 and ReasonIR-8B 24.38. The page does not compare cross-encoders — [model card](https://huggingface.co/lightonai/Reason-ModernColBERT)
- Jina-ColBERT-v2 is cc-by-nc-4.0, with Hindi, Bengali and Telugu in its evaluation tables — [model card](https://huggingface.co/jinaai/jina-colbert-v2)
- LFM2-ColBERT-350M lists eight languages, none Indian, and all its figures are self-reported — [model card](https://huggingface.co/LiquidAI/LFM2-ColBERT-350M)
- BGE-M3 is MIT licensed, reads 8,192 tokens, and returns dense, sparse and ColBERT outputs through flags on `encode`. Its card recommends hybrid retrieval followed by a cross-encoder — [model card](https://huggingface.co/BAAI/bge-m3)

**CPU and index cost**
- Reranking BM25 results with ColBERTv2 took about 7 ms per query against 73 ms for the fastest PLAID setting, single-threaded on a Ryzen 9 5950X, with all embeddings in memory. It was less effective on the Pareto frontier and cannot reach peak effectiveness at higher latency, because lexical recall limits it. Independent reproducibility study — [MacAvaney and Tonellotto, SIGIR 2024](https://ar5iv.labs.arxiv.org/html/2404.14989)
- next-plaid's README reports 5,183 SciFact documents (1.2M tokens) indexed in 12.19 s, 300 queries in 16.38 s, and 480 MB peak memory against 3,361 MB for FastPlaid. No hardware is stated. Vendor claim, and about 55 ms per query is my division — [next-plaid README](https://docs.rs/crate/next-plaid/0.1.0/source/README.md)
- PyLate offers `rank.rerank` to rerank first-stage results with no index, and says `pool_factor=2` can halve index size with virtually no quality loss. Vendor docs — [PyLate retrieval docs](https://lightonai.github.io/pylate/documentation/retrieval/)
- Chroma's docs describe hybrid dense plus sparse with RRF, under its Cloud Search API. I found nothing on multi-vector — [Chroma hybrid search](https://docs.trychroma.com/cloud/search-api/hybrid-search)

**VETRA's own measurements**
- A comment in the code records that on 67 RTI questions, rerankers hurt: MiniLM 46-56 and bge-reranker-base 53-57, against 59 to 64 for live search without them. It blames casual questions and legal wording sharing too few words — [`rag/domains.py`, lines 283-286, project file](file:///C:/Users/nkk77/Desktop/VETRA/rag/domains.py)
- The agriculture and finance domains use `cross-encoder/ms-marco-MiniLM-L-6-v2` — [`vetra/domains.py`, project file](file:///C:/Users/nkk77/Desktop/VETRA/vetra/domains.py)

### Inferences
- The largest late-interaction advantage shown here is over dense models from the same recipe. BGE-M3 is already the planned upgrade, and it removes most of that advantage on the three Indian languages measured.
- Storage, as a rough sum: 1M tokens at 128 dimensions in 32-bit floats is about 512 MB before compression. At hundreds of documents, brute-force scoring of about 50 candidates needs no PLAID index at all. Indexes solve a problem VETRA doesn't have yet.
- Encoding on CPU is probably the real cost, and it's paid once per corpus build and again per query. Nobody publishes it, so time it on this machine before deciding.
- Against the doc: idea 5, "try a better reranker", is **confirmed and strengthened**. VETRA's own result that rerankers can hurt is a warning that the English benchmarks may not transfer, so the existing "must beat our scores" rule matters here.

### Gaps
- No study of ColBERT or late interaction against hybrid plus cross-encoder on Indian languages, or on legal or government text.
- MIRACL covers only Hindi, Bengali and Telugu of the 22 languages. Nothing here tests an Indian-language query over an English document, which is VETRA's main case.
- I could not confirm whether the BGE-M3 row in the LateOn table is dense only.
- No CPU encoding time for mLateOn, BGE-M3 ColBERT or bge-reranker-v2-m3. Model cards give none.
- [IndicIRSuite](https://huggingface.co/saifulhaq9/indiccolbert) offers 11 single-language Indic-ColBERT models. I read only the search snippet, and did not check its quality.
- [M3DR](https://www.emergentmind.com/papers/2512.03514), seen only as a search snippet, reports dense beating multi-vector cross-lingually by 10+ points on visual documents. Different task, not opened.
- Secondary comparisons I discarded as unverifiable: a [DEV post](https://dev.to/gabrielanhaia/rerankers-and-the-latency-budget-when-cross-encoders-are-worth-it-3efc) with nDCG figures, and a [johal.in article](https://www.johal.in/retrieval-augmented-generation-colbert-bm25-hybrid-dense-sparse-reranking-2026-4) citing "MLPerf" for retrieval.

## Contextual Retrieval: independent replications, and late chunking head-to-head

### Takeaway
I found no replication of Anthropic's 35/49/67% figures on its own corpora, but independent work agrees on direction. Contextual Retrieval beats late chunking head-to-head, by little on one corpus and by a lot on another, at about 120 times the indexing time. The best new finding for VETRA is that one summary per document roughly halves wrong-document retrieval in legal corpora, and that the quality of the contextualising LLM matters more than the embedder.

| Technique | Evidence | What it would improve in VETRA | CPU cost and complexity | Recommendation |
|---|---|---|---|---|
| Fixed header on every chunk from known fields: state, scheme, order number, date | No direct measurement. Headings on every chunk appear in D-RAC, with no ablation | Wrong-document mix-ups across 36 states' near-identical orders | Very low: no LLM, rebuild the index | **Test first**, it's the cheapest |
| Summary-Augmented Chunking, one LLM summary per document | Independent of any vendor, author-run, English contracts | Same, and it also helps when metadata is thin | Low: one call per document, plus a rebuild | **Test next** |
| Per-chunk Contextual Retrieval | Vendor original, plus three academic evaluations | Passages that make no sense alone, cross-references inside long orders | No CPU issue, API cost scales with chunks. One call per chunk | **Test**, as already planned for Phase 4. Don't use a weak model |
| Late chunking | Independent head-to-heads | Cheap context without an LLM | Needs a long-context model pass over each whole document. CPU time not measured anywhere | **Skip** |

### Cited Findings
**Head-to-head**
- ConTEB, nDCG@10 average: naive 52.0, late chunking 61.0, Anthropic-style contextual 72.4. Indexing 15.81 ms per document for late chunking against 1,890.94 for contextual, about 120 times slower. The late-chunking and naive rows use ModernBERT Large. The authors propose a competing method, InSeNT, at 75.6 — [Conti et al., 2025](https://arxiv.org/html/2505.24782)
- By subset, the 72.4 average hides a tie on two: Football 54.6 vs 53.9 and Geography 89.6 vs 89.4 for late vs contextual. Insurance is 41.0 vs 100.0 — [same paper](https://arxiv.org/html/2505.24782)
- NFCorpus subset, independent, 50 queries and about 300 documents, Jina-V3: late chunking NDCG@10 0.294 against contextual rank fusion 0.308, and all six metrics favour contextual by small margins. The context came from a small 4-bit Phi-3.5 model — [Merola and Singh, ECIR 2025 workshop](https://arxiv.org/html/2504.19754)
- The same paper found late chunking with BGE-M3 performed much worse on NFCorpus, and concluded neither approach is definitive — [same paper](https://arxiv.org/html/2504.19754)
- Late chunking helps in-corpus retrieval by about +2.8% to +6.4% on average, but hurts in-document retrieval by -3.8% to -53.2%, depending on the embedder. Independent. The authors advise against it for in-document tasks — [Zhou et al., 2026](https://arxiv.org/html/2602.16974)

**Legal-specific**
- CRAwLeR (June 2026) builds Danish and Polish legal queries whose answer needs a linked cross-reference. It removes any query that BM25 or BGE-M3 could already rank in the top 10 without context. Anthropic-style context then gives best Recall@10 of 55% (Danish) and 59% (Polish), with BGE-M3 ahead of BM25 (0.551 vs 0.392, 0.587 vs 0.470) — [CRAwLeR](https://arxiv.org/html/2606.21676)
- The contextualising model drives results. A strong model (Qwen3-235B) against a weak one (Qwen3-30B) moved Polish R@10 from 0.587 to 0.417 and Danish from 0.551 to 0.399. Swapping BGE-M3 for mE5small changed almost nothing (0.590 and 0.551) — [same paper, ablation](https://arxiv.org/html/2606.21676)
- Whole-document against local-window context showed no substantial difference, though that's on 29 queries. Windows were 32k tokens with 8k overlap — [same paper](https://arxiv.org/html/2606.21676)
- Summary-Augmented Chunking: a generic summary of about 150 characters from gpt-4o-mini, one call per document, "effectively halving" wrong-document retrieval. Baseline mismatch exceeded 95% on ContractNLI. SAC averaged 19.29% at 500-character chunks, over k from 1 to 64, so those two figures aren't directly comparable. Generic summaries beat expert-guided ones. BM25 hybrid lowered mismatch slightly but cut precision and recall. English contracts only, not legislation — [Reuter et al., NLLP 2025](https://arxiv.org/html/2510.06999v1)
- That paper did not compare with Contextual Retrieval, and its baseline numbers appear only in figures — [same paper](https://arxiv.org/html/2510.06999v1)

### Inferences
- Measured on a filtered set: CRAwLeR's filter means naive retrieval scores zero by construction on those queries, so its 55-59% is a real gain on hard cases but not a general uplift figure.
- VETRA's known PM-KMY and PM-KISAN mix-up is wrong-document retrieval. It will likely get worse as near-identical orders arrive from 36 states. That makes document-level context the first thing to try, ahead of per-chunk context.
- Don't choose the cheapest Gemini model for context without testing. CRAwLeR's gap between models is bigger than any embedder difference in these notes.
- Late chunking's in-document loss hits VETRA's "look inside a document" move directly.
- Against the doc: idea 1 is **confirmed in direction**, though Anthropic's own magnitudes remain unreplicated. "Late chunking faster but weaker" is **confirmed from primary sources**, where the doc had only a summary. The doc's "$1 per million document tokens" is Anthropic's estimate for its own model and prompt caching, so re-estimate it for Gemini.

### Gaps
- No replication of Anthropic's exact numbers on the same data, or any Contextual Retrieval test on Indian documents or in Indian languages. It's untested whether context should be in the document's language or English.
- No direct comparison of Summary-Augmented Chunking with per-chunk context.
- Merola and Singh's sample is small, and neither their nor Conti's work uses a Gemini contextualiser.
- CRAwLeR's full appendix, including the 8,192-token check, wasn't fully read.
- [Particula](https://particula.tech/blog/contextual-retrieval-vs-late-chunking) (a blog) was how I found the ConTEB figures. They are now confirmed from the paper.

## GraphRAG, LightRAG, HippoRAG 2, RAPTOR: independent gains and indexing costs

### Takeaway
On independent tests, full graph systems mostly lose to or barely match good vector retrieval on fact questions, and cost about 2 to 12 times the corpus in LLM tokens just to index. HippoRAG 2 is the only one with a repeated real gain, on multi-hop reasoning. VETRA should not build an LLM-extracted graph. Orders that cite and replace each other are better served by a small hand-checked link table, walked by code, which VETRA already has in `links.jsonl`.

| Technique | Evidence | What it would improve in VETRA | CPU cost and complexity | Recommendation |
|---|---|---|---|---|
| Microsoft GraphRAG | Independent: last in Samsung's test. Behind plain RAG on facts and ahead on reasoning in Xiang's | Global summaries, not VETRA's task | About 11.7x corpus tokens to index, 38,707-331,375 prompt tokens per query | **Skip** |
| LightRAG | Independent: uneven, with high query cost | Nothing measured | About 8.5x corpus tokens, about 100,000 tokens per query | **Skip** |
| HippoRAG 2 | Independent and author-run: real gain on multi-hop, level on facts | Multi-hop deep questions | About 5.9x corpus tokens, and query tokens near plain RAG | **Skip for now**. Revisit if misses turn out to be multi-hop |
| RAPTOR | Conflicting, and it crashed on one dataset | Summaries of long documents | About 2x corpus tokens, clustering step | **Skip** |
| LazyGraphRAG | Vendor, contradicted on cost by a benchmark | Nothing specific | Vendor says near vector RAG, benchmark says about 10.6x | **Skip** |
| UnWeaver, LiteSemRAG | Author-run | Cheaper entity indexing | LiteSemRAG used a server with a GPU | **Skip** |
| Hand-checked link table walked by code, with parsed order numbers | Design-level; expansion gain itself small | "What replaced this order?" and audit trails | Very low: code plus intake checks | **Adopt now** (see the temporal section) |
| General citation expansion on every search | Independent: small gains, negative once tokens are counted | Little | Low | **Skip** as a default. Keep it on demand |

### Cited Findings
**Independent or against-interest quality results**
- Samsung's comparison, factual F1: VectorRAG 0.3790 / 0.4793 / 0.3218 / 0.2007 on COVID-QA, eManual, Tech-QA and MuSiQue. HippoRAG2 0.3735 / 0.4680 / 0.3448 / 0.2196. RAPTOR 0.3643 / 0.4466 / failed / 0.1858. GraphRAG 0.3092 / 0.3424 / 0.2847 / 0.1353. GraphRAG ranked last. The authors propose their own UnWeaver, so vector and graph rows are the neutral part — [UnWeaving the knots of GraphRAG](https://arxiv.org/html/2603.29875)
- RAPTOR could not run on Tech-QA because of numerical instability in its clustering — [same paper](https://arxiv.org/html/2603.29875)
- GraphRAG-Bench, novels: fact retrieval RAG with rerank 60.92, HippoRAG2 60.14, LightRAG 58.62, MS-GraphRAG 49.29, RAPTOR 49.25. Complex reasoning RAG with rerank 42.93, HippoRAG2 53.38, MS-GraphRAG 50.93. Medical: 64.73 vs 66.28 on facts, 58.64 vs 61.98 on reasoning. The authors state that GraphRAG frequently underperforms vanilla RAG on real tasks — [Xiang et al., 2025-26](https://arxiv.org/html/2506.05690v3)
- Conflict on RAPTOR: a second benchmark, on domain-specific reasoning, puts RAPTOR first on generation accuracy (73.58) with plain BM25 at 71.66, so the gap is small. No dense RAG baseline is listed — [GraphRAG-Bench, Xiao et al.](https://arxiv.org/html/2506.02404). The HippoRAG 2 paper has it behind dense retrieval (F1 48.8 vs 57.0), though those are rival authors — [HippoRAG 2](https://arxiv.org/html/2502.14802)
- Author-run: HippoRAG 2 reports recall@5 of 78.2 average against 73.4 for dense NV-Embed-v2 and 65.6 for RAPTOR, QA F1 59.8 vs 57.0 — [HippoRAG 2, ICML 2025](https://arxiv.org/html/2502.14802)
- The authors of GraphRAG-Bench advise matching the graph to domain structure, since medical guidelines have explicit hierarchies that suit it. They also report standard RAG reasoning falling from 58.64% to 43.20% on a larger novel corpus while HippoRAG2 held up. These are observations, not a legal test, and legal is only suggested as a future domain — [Xiang et al., appendix](https://arxiv.org/html/2506.05690v3)

**Indexing and query cost**
- One book of about 56k tokens: RAPTOR 115,541 total tokens, HippoRAG2 329,993, LightRAG 474,172 (710 s), LazyGraphRAG 591,150, MS-GraphRAG 654,673. Those work out to about 2.1, 5.9, 8.5, 10.6 and 11.7 times the corpus, my division — [Xiang et al., Table 10](https://arxiv.org/html/2506.05690v3)
- Prompt tokens per query, novels: vanilla 879, HippoRAG2 1,008, RAPTOR 3,441, MS-GraphRAG local 38,707, LightRAG 100,832, MS-GraphRAG global 331,375 — [same paper](https://arxiv.org/html/2506.05690v3)
- MuSiQue, 11,656 passages: dense indexes in 12.1 minutes with no LLM, HippoRAG 2 in 99.5 minutes with 9.2M input tokens, GraphRAG in 277 minutes with 115.5M — [HippoRAG 2, Table 12](https://arxiv.org/html/2502.14802)
- Conflict: the second benchmark reports HippoRAG with the longest indexing time, and only 2.44 s retrieval against 44.87 s for GraphRAG. Its method set and token figures differ — [Xiao et al.](https://arxiv.org/html/2506.02404)
- LazyGraphRAG's "0.1% of the costs of full GraphRAG" is a Microsoft claim, tested on 5,590 news articles and 100 synthetic queries with LLM judging. It conflicts with the 591,150 tokens above, which may reflect a different implementation — [Microsoft Research](https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/)
- LiteSemRAG reports zero LLM tokens, but the setup used a GPU, it does not compare with flat dense retrieval, and SciFact recall is below LightRAG's. Author-run — [LiteSemRAG](https://arxiv.org/html/2604.16350)

**Documents that cite each other**
- German statutes, 12,037 cases, 58 federal codes. Cited-link expansion gave small gains (2.27 to 2.40, 2.28 to 2.40). Parent expansion changed results only at one level (1.36 to 2.13). When expansion tokens count against the budget, every expansion falls below its unexpanded baseline. The authors conclude expansion cannot make up for bad chunk size. Task is citation prediction from case facts, not citizens' questions — [Verifiable Retrieval for Legal Reasoning, October 2026](https://arxiv.org/html/2610.13695v1)
- Indian Penal Code statute identification: explicit graph inference substantially improved recall, but adding graph context to prompts lowered precision, which needs reranking. Abstract only, no figures read — [NyayGraph, NLLP 2025](https://aclanthology.org/2025.nllp-1.11/)

### Inferences
- On scale: 8 link records exist today (`knowledge/agriculture/links.jsonl`), and part-by-part search reaches 55 of 59. A graph can only help with what's left, and it adds an extraction step that can invent links, which conflicts with VETRA's requirement of traceability.
- Government orders typically name what they amend or replace, unlike the implicit entity links that LLM-extracted graphs infer. I did not survey this, though VETRA's link records show the pattern. Parsing those references and having a person check them is cheaper and auditable. No study here tests that on Indian orders, so this is reasoning from the evidence, not a result.
- Against the doc: "Not looked at closely" for GraphRAG and RAPTOR can now close as **not worth it for now**. Its remark that the link file is already a small graph is **confirmed** as the right way to go.

### Gaps
- No graph RAG evaluation on government orders, circulars, or any Indian corpus in a citizen-question setting.
- I found no controlled with-and-without test of citation expansion for amendment-heavy documents.
- [Domain-Partitioned Hybrid RAG](https://arxiv.org/pdf/2602.23371) and [Bridging Legal Knowledge and AI](https://arxiv.org/html/2502.20364v1) came up in searches, and I did not read their results.
- Dollar costs depend on Gemini's prices, which I did not compute.

## Temporal and versioned retrieval: amendments, superseded orders, "what applied on date X"

### Takeaway
The strongest measured result supports a simple design. Index every version with validity dates, and filter on the date the question means. That took accuracy from about 3% to about 98% on French tax law. No temporal graph or graph database was needed. This is the biggest gap in VETRA: no record in the knowledge store has a `valid_until`, and date filtering is tied to today and a year string. The hard, unmeasured part for VETRA is extracting validity from Indian orders.

| Technique | Evidence | What it would improve in VETRA | CPU cost and complexity | Recommendation |
|---|---|---|---|---|
| Versioned records with validity dates, filtered by the date the plan names | Measured, by authors with a commercial affiliation, retriever proprietary | "What applied in Kharif 2024?", and current-rule answers no longer depending on hand-set status | Very low on CPU. Moderate data work | **Adopt now** |
| Work, version and action records (Norm, Temporal Version, Action) with amendment events | Design only, no measured evaluation | Traceable amendment chains, partial amendments | Low: JSONL records and code | **Adopt**, simplified |
| Two time axes: when a rule applied, and when VETRA learned of it | Design only | Honest "as of the documents we hold on date Y" | Very low: a few fields | **Adopt** the fields |
| Temporal test set with deterministic scoring | Authors' recommendation, measured baseline | Stops current-rule substitution silently coming back | Very low | **Adopt now** |
| VersionRAG | Author-run, 100 questions on tech docs | Query types for version listing and change questions | Neo4j and Milvus, so no. Borrow only the idea | **Skip** the system |
| Graphiti or Zep | Vendor, on chat memory, disputed benchmark | Not this task | Graph database plus LLM extraction | **Skip** |
| TG-RAG, T-GRAG | Author-run, on company reports | Time-scoped questions on prose corpora | TG-RAG used 6.3M input and 7.1M output tokens to index its earnings-call corpus, and needs a graph | **Skip** |

### Cited Findings
**Measured versioned retrieval**
- Temporal Misgrounding: 209 scored questions on French tax law, 32,436 article versions from 1938 to 2031, 11 models. LLM alone 3.0%, RAG over current law only 2.7%, versioned RAG with the correct article given 99.1%, versioned RAG end to end 98.3%. Static RAG found the date-applicable version 0% of the time, and all its errors were current-law substitution. Dense plus BM25 with RRF placed the right version in the top 5 for about 99% of questions — [Cymbler, Guez and Fabre, 2026](https://arxiv.org/html/2608.09393)
- Its remedies: index by version with explicit validity dates, condition retrieval on the date implied by the question, and score deterministically with regex and numeric tolerance rather than an LLM judge, which it argues would share the same bias — [same paper](https://arxiv.org/html/2608.09393)
- Independence caveat: two authors are at Talia and one at Databricks, and the end-to-end retriever and index are proprietary, so the 98.3% cannot be reproduced from released material — [same paper](https://arxiv.org/html/2608.09393)
- LegalSearch-R1 gives Chinese statute chunks a validity window, filters on the query's temporal reference, then fuses keyword, dense and BM25 with RRF. It reports 57.7% to 80.3% gains on temporal consistency, but does not isolate the filter from RL training and web search. Search agents rarely add temporal constraints unprompted: baselines issued 97-227 temporally aware queries, against 502-537 for the trained agent — [Can LLMs Time Travel?](https://arxiv.org/html/2605.25920)
- TG-RAG on earnings calls: correct 0.599 against best baseline 0.410 (HippoRAG2) and naive 0.385. Removing temporal retrieval drops it to 0.382, so nearly all its gain comes from time scoping. Author-run. The ablation has one odd row (0.482 when removing both temporal retrieval and PPR, above 0.382 for temporal retrieval alone), so treat the detail with care — [TG-RAG](https://arxiv.org/html/2510.13590)
- VersionRAG: 90% against GraphRAG 64% and naive 58%, implicit change detection 60%, on its own 100-question benchmark of technical docs. It needs Neo4j and Milvus, and the authors say irregular or date-based versioning may fail — [VersionRAG](https://arxiv.org/html/2510.08109)
- T-GRAG introduces Time-LongQA on company annual reports. I read the abstract only — [T-GRAG](https://arxiv.org/abs/2508.01680)

**Data models, design only**
- The ontology-driven legal Graph RAG separates a norm, its components, temporal versions, language versions and reified actions. An amendment action links the source provision, the version it ends and the version it creates. A planner produces a target and time scope, defaulting to today. Code then selects the version whose interval contains the date, and states the policy used in the answer. It is explicitly qualitative, with no metrics. Built on the Brazilian Constitution using relational tables with a vector column, not a graph database — [de Martim, 2025](https://arxiv.org/html/2505.00039v4)
- A follow-up specifies typed retrieval functions with valid-time (`at`) and transaction-time (`observerTime`) parameters, confining uncertainty to translating intent, initial anchoring and final wording. The author states it "is not an empirical benchmark" — [Deterministic Legal Agents](https://arxiv.org/html/2510.06002)

**Graphiti and Zep**
- Zep's own paper reports 94.8% vs 93.4% for MemGPT on Deep Memory Retrieval, and up to 18.5% accuracy gain with 90% lower latency on LongMemEval. All authors are from Zep, and both benchmarks are conversation memory — [Zep paper](https://arxiv.org/abs/2501.13956v1)
- Graphiti needs Neo4j, FalkorDB or Neptune (Kuzu is deprecated), plus an LLM with structured output for extraction and deduplication. It is Apache-2.0, and shows no temporal accuracy benchmark — [Graphiti repo](https://github.com/getzep/graphiti)
- Disputed numbers, in a primary thread: Mem0's CTO said replication gave 58.44% rather than Zep's 84% on LoCoMo. Zep acknowledged a calculation error, gave a corrected 75.14% ± 0.17, and disputed the rest. Both are competitors, and neither is independent — [zep-papers issue #5](https://github.com/getzep/zep-papers/issues/5)

**VETRA today**
- `vetra/checks.py` drops a record only if it's out of date as of `as_of`, unless its validity year appears as a string in the question. `as_of` defaults to today in `vetra/agent.py` line 460.
- A search of `knowledge/` found no `valid_until` value in any record, and I found no code in `vetra/` that writes one. `vetra/sorter.py` sets `valid_from` to the issue date.
- Link records in `knowledge/agriculture/links.jsonl` hold free text such as "G.O.Ms.No.96 (2019) YSR Rythu Bharosa - replaced" as the target, not a canonical ID, and a link does not close the target's validity.

### Inferences
- From reading the code, not running it: with no `valid_until` values and `valid_from` set to the issue date, the date filter only removes orders issued after today. It can't retire a replaced order. That depends on the hand-set status and the past-season cut.
- Once `valid_until` values exist, a rule valid from 2022 until March 2025, asked about with "in 2024", would fail the year-string check ("2025" is not in the question), and would be dropped even though it applied. Worth a quick test to confirm.
- A simplified model that fits the existing JSONL stores:
  - An order: canonical ID, issue date, issuing authority, legal weight.
  - A version of an order or of one numbered paragraph: `effective_from`, `effective_until`, `superseded_by`.
  - An action: amends, extends, replaces, corrigendum, with source order and paragraph.
  - `ingested_on`, for the second time axis.
- Issue date is not effective date. Orders can apply retrospectively or from a named season, so `valid_from = issue date` will be wrong for some. Seasonal schemes are an additional axis beyond calendar dates.
- French law is available as clean versioned articles. Indian orders are not, and an amendment often changes one paragraph, so whole-document `in_force` status can be wrong. The 98% should not be expected here. The realistic risk is extraction, so keep a person checking links, as the `reviewed` field already allows.
- On the doc: "Pin down the period first" (idea 6) should move from worth trying to **adopt now**. This is now backed by measurement, not just a design principle.
- The 98.3% came from dense plus BM25 with RRF, the same general shape as VETRA's stack, though the exact retriever is unpublished. This suggests no retrieval replacement is needed.

### Gaps
- No benchmark on Indian orders, or on any corpus of executive orders with partial amendment and corrigenda.
- No measurement of LLM accuracy at extracting effective dates and amendment relations from orders.
- No independent replication of Temporal Misgrounding. Its questions are built to carry a date, whereas citizens' questions often imply one.
- I found no independent temporal-accuracy test of Graphiti. Later LoCoMo numbers I saw are on blogs, such as [this one](https://hugo-kusga-com.pages.dev/articles/llm-memory-in-2026-why-most-benchmark-claims-dont-survive-scrutiny/), so I did not rely on them.
- [ChronoQA](https://arxiv.org/html/2508.12282) and [TempRAGEval](https://www.arxiv.org/pdf/2412.15540) are further temporal benchmarks, seen only in search results.

## Query rewriting and decomposition: what helps, and what only adds latency

### Takeaway
Under a strong baseline, a single rewrite adds little: 0.2 to 3.7 points. Always-on HyDE is mostly the same or worse when keyword search has already worked, at 2.6 times the latency. What holds up is decomposition for true multi-part questions, and escalating only after retrieval comes back weak, which is what VETRA's judge loop already does. Predicting in advance which queries need rewriting failed.

| Technique | Evidence | What it would improve in VETRA | CPU cost and complexity | Recommendation |
|---|---|---|---|---|
| Part-by-part search for deep questions | Measured here 55 of 59. Independent support, though with a weak baseline | Multi-part coverage | One LLM plan already paid, one search per part | **Keep** |
| Escalate after weak retrieval (judge loop) | Production study by the cascade's authors, no vendor | Cost and latency | Already built | **Keep** |
| HyDE or a pseudo-document as a judge move when retrieval is weak | Author-run, simulated. Production study supports the shape | Casual wording against legal wording | One LLM call on a share of questions | **Test** |
| Always-on HyDE | Independent: worse often enough, high latency | Little | One extra call on every question | **Skip** |
| Predicting pre-retrieval which questions need rewriting | Independent: four ML approaches failed | Nothing | Training plus serving | **Skip** |
| Merging several rewrites | Author-run: big gain on hard corpus, hurts on an easy one | Hard misses only | Several LLM calls | **Test** only on the misses, not by default |
| Choosing a subset of sub-queries (bandit) | Author-run, TREC-style data | Cost on very broad questions | More machinery | **Skip** for now |

### Cited Findings
**Rewriting under a strong baseline**
- ServiceNow, baseline with dense retrieval, cross-encoder and MMR: HIT@10 97.13 / 93.67 / 39.22 on HotpotQA, AmbigNQ and an enterprise set. Best single rewrite 97.65 / 95.47 / 42.91. A five-way merge gave 99.40 / 92.96 / 52.98, so merging helped the hard set and significantly hurt AmbigNQ (-2.49, p<0.001). These combinations are post-hoc on one seed — [Better Together, 2026](https://arxiv.org/html/2609.05637)
- The paraphrase rewrite was best on two of three. A router running Query2Doc only when the top score is below 0.65 got +4.33 on the enterprise set with 39% of queries rewritten, about half the gain at 40% of the cost. This was simulated. Rewriting added about 9-18 times the run time on web QA. A reranking budget match reached about 44.3, so simply reranking more captures some of the same gain — [same paper](https://arxiv.org/html/2609.05637)
- Decomposition was not among its tested methods — [same paper](https://arxiv.org/html/2609.05637)

**HyDE and routing in production**
- Danish National Encyclopedia, 240,000 articles and 1,000 real queries, independent of any vendor: hybrid coverage 72.2% at 37 s, always-HyDE 86.4% at 96.2 s. A cheapest-first cascade that escalates only on empty results scored higher overall at 65.6 s, using an LLM on 27.8% of queries — [The Coverage Illusion](https://arxiv.org/html/2605.27220v1)
- Where hybrid had already found sources, HyDE scored the same 59.6% of the time, worse 21.2% and better 19.3%. Synthetic queries suggested over 90% needed augmentation, while real ones needed 27.8%. Pre-retrieval routing failed across four ML approaches, since need depends on what the index holds. Single corpus, Danish keyword-style queries — [same paper](https://arxiv.org/html/2605.27220v1)
- A LiveRAG 2025 system found HyDE reduced correctness and faithfulness and first left rewriting out. Search snippet only — [DoTA-RAG](https://arxiv.org/pdf/2506.12571)
- On a bias benchmark, plain rewriting cut mean bias by 53.9%, but the authors argue much of that is added noise. It barely helped on adversarial cases, where pseudo-document methods did better. Retrieval only, no answers measured — [Masking or Mitigating?](https://arxiv.org/html/2604.06097)

**Decomposition**
- MultiHop-RAG MRR@10 0.464 to 0.635 and HotpotQA F1 31.3 to 35.0. However, the baseline had no reranker: decomposition alone gave Hits@4 0.611 to 0.655, reranking alone 0.687, and only the pair did best. The LLM nearly always produced five sub-queries, with near-zero correlation to the evidence actually needed. Latency was 0.03 s for naive, 16.7 s with decomposition, on a local model — [Ammann, Golde and Akbik, ACL SRW 2025](https://arxiv.org/html/2507.00355v1)
- Selecting sub-queries with a budget claims a 35% precision gain and 15% in α-nDCG on NeuCLIR and Bing questions, with no latency reported. The paper's own caption and text disagree on one figure (24% vs 32.3%). Author-run — [Petcu et al., 2025](https://arxiv.org/html/2510.18633)
- On cross-section biomedical questions, no method retrieved both required sections for any question (CS Recall@20 of 0.000). Template questions — [GraLC-RAG](https://arxiv.org/html/2603.22633v1)

### Inferences
- These results agree with the doc's finding that a part searched alone beats adding the topic. The doc's 58/59 parts and VETRA's 55 of 59 are consistent with GraLC-RAG: a single merged query can't reach several sections, but separate searches can.
- VETRA's planner has an advantage over the Ammann setup, as it names parts from the question rather than always producing five. Keep a check that the number of parts tracks what the question asks, since over-splitting costs latency for nothing.
- VETRA's depth table is routed before retrieval, but on question shape rather than on predicted need, so the failed routing study doesn't apply to it.
- VETRA's RTI result (59 to 64 of 67 with topic and key terms searched as well, per the code comment) suggests vocabulary-gap rewriting does pay here. A code-only term expansion may be worth trying before an LLM rewrite.
- The 0.65 threshold is not portable. It depends on the reranker's score scale, so it would need measuring here. On a CPU, the cost is the LLM call and an extra rerank.
- Against the doc: "Search from the reasoning" remains unproven by anything here, since I did not find newer evidence.

### Gaps
- No rewriting study on Indian-language queries, or queries translated before search, in this research. It is likely the highest-value rewrite for VETRA, and needs its own measurement.
- No controlled comparison of decomposition against a reranked hybrid baseline on government or legal text.
- The [DEV comparison of HyDE, multi-query and decomposition](https://dev.to/gabrielanhaia/hyde-multi-query-decomposition-which-query-rewrite-actually-moves-recall-1m08) has no clear method, so I set it aside.

## Table-aware and structure-aware retrieval and chunking

### Takeaway
Chunking on document structure beats fixed size, usually by a little, with one large effect: statute text chunked at sentence or numbered-item level was about three times more efficient. Row-level table chunks look promising, but the evidence is thin. Always returning the parent section isn't supported once tokens count, so on-demand reading around a passage, as the judge does, is the better design. Exact table values should stay in VETRA's exact stores.

| Technique | Evidence | What it would improve in VETRA | CPU cost and complexity | Recommendation |
|---|---|---|---|---|
| Chunks on numbered paragraphs and paragraphs instead of fixed size | Independent, moderate gains; one big statute result | Precision, citation by paragraph, per-paragraph amendments | Low: parser work, re-index | **Test now**. Likely adopt |
| On-demand read-around | Already built. Supported by the failure of always-on parents | Context without token cost | None | **Keep** |
| Always-on parent or auto-merge retrieval | Mixed: +3 points recall in one, negative once charged in another | Evidence recall on multi-chunk answers | Low on CPU, but longer prompts | **Skip** as a default |
| One row per chunk with column headers | Work in progress, one legal CSV dataset. Vendor system lacks an ablation | Rate tables, crop and district schedules | Low, needs PDF table extraction | **Test** after PDF work |
| Heading path on every chunk | No isolated measure | Disambiguating similar passages | Very low | **Test**, in the fixed-header experiment |
| Model-based hierarchical chunking (HiChunk), LLM chunk planning (D-RAC), LumberChunker | Author-run or task-specific | Messy documents | A model or LLM per document. HiChunk reports about 1.5-60 s per document, hardware not stated | **Skip** |

### Cited Findings
**Structure against fixed-size**
- BEIR, independent: paragraph best for three of four embedders (0.4303, 0.4948, 0.4997), fixed-size close behind (0.4136, 0.4849, 0.4863). Gaps among structure-based methods were roughly 1-3%. Proposition chunking was lowest for all. Recursive chunking was not evaluated — [Zhou et al., 2026](https://arxiv.org/html/2602.16974)
- 36 strategies across 6 domains: paragraph groups had mean nDCG@5 about 0.459, Hit@5 about 59%, against fixed-character 0.244. In the Legal domain, paragraph groups led with Hit@5 about 78% and Precision@1 about 35%. In Agriculture, no method dominated, with paragraph groups, a paragraph-then-token hybrid and one other in the top three. Relevance was judged by an LLM and each configuration ran once — [Systematic Investigation, 2026](https://arxiv.org/html/2603.06976)
- German statutes: chunking at sentence or numbered-item level retrieved about three times more citations per 1,000 words than 100-word naive chunks (14.23 vs 4.19 at code level, 2.79 vs 0.81 at numbered-item level). Whole-section chunks fell below naive (3.06 vs 4.19). The authors credit granularity as much as structure — [Verifiable Retrieval for Legal Reasoning](https://arxiv.org/html/2610.13695v1)
- Biomedical: structure-aware chunking reached about 15.6 times more sections at k=20, while the best ranking (semantic, MRR 0.517) stayed in one section. Structure-aware scored MRR 0.365 against naive 0.344. So breadth and rank measure different things — [GraLC-RAG](https://arxiv.org/html/2603.22633v1)

**Parent retrieval**
- HiChunk auto-merge raised evidence recall 77.68 to 81.03 on its own benchmark, and overall fixed-200 to hierarchical with merge went 74.06 to 81.03 (single-chunk evidence), 72.95 to 80.65 (multi-chunk). General sets moved little (LongBench 46.33 to 46.92). Tencent, author-run, on a benchmark they built with evidence-dense questions — [HiChunk](https://arxiv.org/html/2509.11552)
- German statutes: parent expansion gave no change at most levels. Counting the tokens, Absatz plus parent fell to 0.36 from 1.36 as delivered text grew from about 70.6 to 415 words — [Verifiable Retrieval for Legal Reasoning](https://arxiv.org/html/2610.13695v1)
- In the 36-strategy paper, parent-child (500/100) has only efficiency figures in the text: RAM 994.77 MB, query 3.92 ms. The text gives no nDCG or rank for it — [Systematic Investigation](https://arxiv.org/html/2603.06976). The "lower half" claim comes from a [blog](https://www.olostep.com/blog/rag-chunking-strategies), and may be read from a figure.

**Tables**
- Row Tree: each row written as `column_name: value` pairs, split on row boundaries. MRR hybrid 0.3576 to 0.5945, BM25-only 0.3720 to 0.7757. Plain key-value text with recursive splitting scored worse (0.3296). A five-page work in progress on one CSV legal dataset, with string-match relevance and no answer evaluation. The abstract's chunk reductions don't match its table — [Structure-Aware Chunking for Tabular Data](https://arxiv.org/html/2605.00318v1)
- D-RAC turns rows into sentences and prepends headings, with Recall@6 0.798 against fixed-size 0.717 and agentic 0.795. There is no ablation, so neither feature's effect is separable. Its margins over agentic are tiny, and it uses a lexical judge. Vendor (Yellow.ai), and its conversion cost is left out of the savings figure — [D-RAC](https://arxiv.org/html/2609.24220v1)

### Inferences
- Numbered-paragraph chunks pay twice in VETRA: better retrieval, and they let an amendment point to the paragraph it changes, which the temporal section needs. Do these together.
- Row Tree's result suggests the row boundary is what counts, since key-value text alone got worse. A chunk that mixes rows from different crops or districts is the likely failure in rate tables.
- For a citizen's "what's the rate for X", the exact store remains right. A row chunk is a fallback, and helps code find rows that were never extracted.
- Against the doc: "Parent-child chunking, not worth doing yet" **stands, with better reasons**. The primary support is now the German statute test, but its specific "lower half" claim **could not be confirmed** in the paper's text. Note too that VETRA's read-around move already gives parent-like context on demand.

### Gaps
- No table-retrieval evidence on scanned or Indian-language PDFs.
- [Structure-Aware Chunking for Complex Tables](https://ijournalse.org/index.php/ESJ/article/view/3380) could not be opened (connection reset).
- No test of section-aware chunking on government orders. Their numbered paragraphs may be poorly preserved by PDF extraction, which the project's OCR issues suggest.
- VETRA's current chunk sizes and boundaries were not reviewed here, so the size of any gain is unknown until measured.
