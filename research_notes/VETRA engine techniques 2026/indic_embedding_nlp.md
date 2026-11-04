# Multilingual embedding, reranking and Indian-language NLP on CPU, for VETRA (checked 5 November 2026)

How to read the labels:

- **[Indep]** was measured by someone with no stake in the model. **[Vendor]** was measured by the model's maker, or is a self-reported model card. **[Claim]** has no numbers behind it. **[Local]** was measured on this machine or read from this repository.
- **P** means I opened the primary source. **S** means it is secondary, or I saw only a search excerpt.
- File sizes come from the Hugging Face API (`?blobs=true`), read on 5 November 2026, so they are exact bytes on disk, not RAM. I found almost no published CPU speeds.
- Most arXiv table values reached me through a fetch tool's summariser. I read the IndicRAGSuite and "Lost in Transliteration" tables directly from the PDFs. Spot-check the other figures against the papers before publishing them.

## Which embedding models have measured results on Indian languages, how do they rank, and which fit on a CPU?

### Takeaway
**One line in `docs/ARCHITECTURE_RESEARCH.md` is overturned:** BGE-M3 does not lead 8 of 13 languages in IndicRAGSuite. In the paper's own table it ties multilingual-e5-large in 10 of 13. The ranking depends on the search direction. With a question in an Indian language and documents in English, Gemini Embedding leads the one large table that includes it (run by Google), and EmbeddingGemma leads the open models there in all but Odia. BGE-M3 leads the only independent test, which didn't include either Google model. With both in the same language the leaders are close together, and BM25 sometimes beats them all. No model should be adopted yet. The CPU candidates most worth testing are EmbeddingGemma 2 (text only, Apache 2.0, no published Indic retrieval score yet) and hosted Gemini.

### Cited Findings

**Correction to the existing doc [Indep, P, read from the PDF]**
- IndicRAGSuite's text says BGE-M3 leads "8 out of 13" and e5-large leads 4, but its Table 2 bolds BGE-M3 in 6 languages and e5-large in 7. At the printed two decimals, BGE-M3 is strictly ahead in 2 (Assamese .46 v .45, Bengali .49 v .48), e5-large in 1 (Urdu .49 v .48), and they tie in 10 — [IndicRAGSuite](https://arxiv.org/pdf/2506.01615)
- Same table, mean MRR over 13 languages (my arithmetic): BGE-M3 .484, e5-large .483, e5-base .441, e5-small .364. Marathi: BGE-M3 .49, e5-large .49, e5-base .45, e5-small .36. The test is same-language retrieval, so it says nothing about Marathi questions against English documents — [IndicRAGSuite](https://arxiv.org/pdf/2506.01615)
- The paper's text also says LLM2VEC scored .49 in Marathi, while the table shows .45. It is a work-in-progress preprint — [IndicRAGSuite](https://arxiv.org/pdf/2506.01615)

**Indian-language question, English documents (closest to VETRA's English documents)**
- XTREME-UP cross-language retrieval puts the question in the user's language and the passages in English. It covers 21 under-represented languages; in-language retrieval covers only 6 — [XTREME-UP](https://arxiv.org/html/2305.11938)
- [Vendor, P] MRR@10 on XTREME-UP, average across languages: Gemini Embedding 64.3, voyage-3-large 39.2, Linq-Embed-Mistral 24.6, text-embedding-3-large 18.8, multilingual-e5-large-instruct 18.7. Marathi: Gemini 68.8, voyage-3-large 45.5, e5-large-instruct 23.0. Tamil: 68.6, 36.0, 22.9. Bodo: 25.7. Manipuri: 44.4 — [Gemini Embedding paper](https://arxiv.org/html/2503.07891)
- [Vendor, P] MRR@10 on the same benchmark, from another Google paper: EmbeddingGemma 47.7, voyage-3-large 39.2, bge-m3 26.9, Linq-Mistral 24.6, gte-multilingual 19.0, e5-large-instruct 18.7, Jina v3 8.5, Qwen3-0.6B 6.6. Marathi: EmbeddingGemma 58.3, bge-m3 31.8, Qwen3-0.6B 10.2. Hindi: 63.2, 35.1, 18.1. Weak spots for EmbeddingGemma: Boro 12.1, Manipuri 22.2, Odia 21.2. On Odia, bge-m3 (23.1) and voyage-3-large (32.3) beat it — [EmbeddingGemma paper](https://arxiv.org/html/2509.20354)
- [Indep, P] Sinhala and Tamil questions against a Sri Lankan government corpus (500 verified Q&A pairs, 1,699 contexts). Tamil Recall@15: BGE-M3 95.6, Google Translate then English search 93.0, NLLB 89.0, multilingual E5 88.6 (size not stated), mBART50 85.2, LaBSE 72.4, no adaptation 4.2. Sinhala: BGE-M3 96.2, E5 73.0 — [Balasubramaniyam and Madushanka, Aug 2026](https://arxiv.org/html/2608.12820v1)
- [Indep, P] Hindi-BEIR's one cross-lingual set (English queries, Hindi corpus, NDCG@10): e5-large 35.00, BGE-M3 34.40, NLLB-E5 31.73, e5-base 20.81, BM25 0.01 — [NLLB-E5 paper](https://arxiv.org/html/2409.05401v3)

**Same language on both sides**
- [Indep, P] Bengali agricultural PDFs (284 documents from BRRI, IRRI, DAE and others; 900 answerable generated queries). R@10: gemini-embedding-001 .464, BGE-M3 .408, E5-Large .284, Qwen3-8B .241. BM25 .506 beat all of them; hybrid BM25 + Gemini reached .539 — [Where Does Retrieval Fail?, Aug 2026](https://www.alphaxiv.org/abs/2608.14886.md)
- [Indep, P] Hindi-BEIR average NDCG@10 over 15 sets: NLLB-E5 48.57, BGE-M3 46.18, e5-large 44.37, e5-base 40.57, BM25 35.65, LaBSE 19.66. BM25 won on IndicQARetrieval: 74.02 v BGE-M3 69.92 — [NLLB-E5 paper](https://arxiv.org/html/2409.05401v3)
- [Partly independent, P] Indic-MTEB category scores for frozen models (my subtraction of the reported change). Retrieval: Qwen3-8B 93.50, Qwen-4B 88.80, Harrier-270M 80.98, Harrier-0.6B 80.69, EmbeddingGemma-300M 80.65. Overall: Qwen3-8B 72.89, Qwen-4B 70.94, Harrier-0.6B 65.87, EmbeddingGemma-300M 64.34, Harrier-270M 63.93. BGE-M3 and e5 are not included. The paper's text and tables disagree slightly — [TCFM paper, 2026](https://arxiv.org/html/2608.05785)
- [Vendor, P] bge-m3 per-language IndicQARetrieval nDCG@10 (16,775 queries): Marathi .6971, Hindi .6688, Tamil .6407, macro .7172. The fine-tuned Karmx model scored macro .7377, with one training seed and bge-m3 as the only comparator — [Karmx card](https://huggingface.co/karmx/Llama-Karmx-Indic-Embedding-bge-m3)
- [Vendor, P] A text-only EmbeddingGemma 2 base scored Hindi IndicQA NDCG@10 .7279, and a Hindi/Hinglish fine-tune .7324, which missed its own +.03 target. Tamil and Telugu were not measured. Truncation cost: 256d −.030, 128d −.103 — [Bharat-Embed card](https://huggingface.co/eulogik/bharat-embed-270m-gemma2)
- [Vendor, P] qwen-indic-v1 (Qwen3-8B tuned for the 22 languages) scored 73.80 on MTEB(Indic), with retrieval 94.89. It needs about 16 GB of VRAM, gives no per-language scores, and warns that Kashmiri, Manipuri, Bodo and Santali likely score much lower — [card](https://huggingface.co/LingoIITGN/qwen-indic-v1)
- [Vendor, P] EmbeddingGemma 2 v 1 on MTEB multilingual v2: 61.36 v 61.15. It has a total of 740M parameters, of which the text part (backbone + embedder) is 270M, and 8,192 tokens of context. No Indic results on the card — [card](https://huggingface.co/google/embeddinggemma-2)
- [Vendor, P] Harrier on MTEB multilingual v2: 270M 66.5, 0.6B 69.0, 27B 74.3. Hindi and Urdu are the only Indic languages named, and there is no CPU statement — [card](https://huggingface.co/microsoft/harrier-oss-v1-0.6b)
- [Vendor, S] Vyakyarth reports Flores cross-lingual scores: Bengali 98.7, Tamil 97.9, Telugu 97.5, against 97.4, 95.8, 97.3 for jina-v3. That is sentence matching, not passage retrieval — [Vyakyarth card](https://huggingface.co/krutrim-ai-labs/Vyakyarth)

**Configuration can matter more than the model**
- [Indep, P] Changing Gemini's task type from retrieval to similarity dropped R@10 from .464 to .063. At a 128-token limit, 95–99% of nodes were truncated and the ColBERT v dense ranking reversed — [Where Does Retrieval Fail?](https://www.alphaxiv.org/abs/2608.14886.md)
- [Vendor, P] multilingual-e5 is trained on `query: ` and `passage: ` prefixes, and omitting them degrades performance. Input is cut at 512 tokens — [e5-base card](https://huggingface.co/intfloat/multilingual-e5-base)
- [Local] `vetra/text_index.py` lines 46–49 set the right prefixes per model. `rag/retrieve.py:58,160` and `rag/router.py:272` still hardcode the English BGE prefix.

**CPU cost [Local, from the HF API unless linked]**
- [Local] The e5-base test index holds 3,710 chunks and 4.04M characters, and took 38.9 minutes. That is about 1.6 chunks a second (my arithmetic, using the timing from the brief).
- e5-small: 471 MB, ONNX qint8 118 MB. e5-base: 1.11 GB, qint8 279 MB. e5-large: 2.24 GB, qint8 562 MB. BGE-M3: 2.27 GB, with no official quantised file. All MIT.
- EmbeddingGemma-300M ONNX: fp32 1.23 GB, q8 309 MB, q4 197 MB, under the Gemma licence. The paper reports 578 MB memory use — [paper](https://arxiv.org/html/2509.20354). Its QAT checkpoints lose little: 768d 61.15, Q8 60.93, Q4 60.62 — [card](https://huggingface.co/google/embeddinggemma-300m)
- EmbeddingGemma 2 ONNX: fp32 1.08 GB, fp16 542 MB, q4 174 MB, Apache 2.0. The card warns that float16 can produce NaN — [card](https://huggingface.co/google/embeddinggemma-2)
- Harrier-270M: 536 MB, MIT. Qwen3-0.6B: 1.19 GB, Q8 GGUF 639 MB, Apache. Vyakyarth: 1.11 GB. IndicBERTv2: 1.12 GB, MIT. L3Cube indic SBERT: 950 MB, CC-BY-4.0.
- [S/Vendor] One BGE-M3 ONNX project measured 857 ms on long documents on an unnamed x86 CPU, 1.27× faster than FlagEmbedding. It refused to ship int8: dense cosine fell to .985 and top-1 overlap to .625 — [Sophia-AI card](https://huggingface.co/Sophia-AI/bge-m3-onnx)

**Licence traps**
- jina-v3, v5-nano and v5-small are tagged CC-BY-NC-4.0 (HF API). Jina-v4 is under the Qwen Research Licence and described as "not suitable for production workloads". Commercial licences are now sold through Elastic — [Jina page](https://jina.ai/embeddings/)
- Krutrim's licence requires a separate agreement for commercial use, modified versions, SaaS and derivative models. Its commercial definition applies above 1 million monthly users. It also bars competing products and allows audits — [licence](https://huggingface.co/krutrim-ai-labs/Vyakyarth/blob/main/LICENSE.md)
- IndicTrans2's paper says Meta's NLLB models are CC-BY-NC, which affects NLLB-E5 too — [S, search excerpt](https://arxiv.org/pdf/2305.16307.pdf)

### Inferences

**Recommendation table.** All of this is my judgement. None of these models has been run on VETRA's tests except e5-base, which is still running.

| Candidate | Best Indic evidence | Would improve in VETRA | CPU cost | Licence | Verdict |
|---|---|---|---|---|---|
| gemini-embedding-001 / -2 | 001: best on XTREME-UP (vendor-run) and best dense model on Bengali (independent). 2: nothing published | Native and cross-script dense search, with no laptop indexing | None locally; network on each query | Paid API | **Test first** |
| EmbeddingGemma 2, text only | Hindi .7279 on one third-party card. Predecessor strong on XTREME-UP (vendor) | Offline cross-script search, 8,192-token context | q4 174 MB. Speed unpublished; I would guess the same order as e5-base by parameter count | Apache 2.0 | **Test next** |
| BGE-M3 | Best open model in the only independent cross-script test | Native and cross-script search, Odia | 2.27 GB; hours here | MIT | **Test**, with the index built off this laptop. Check any int8 before trusting it |
| Harrier-270M | Indic-MTEB retrieval level with EmbeddingGemma; no XTREME-UP result | Offline search under MIT | 536 MB; ONNX not verified | MIT | Test only if EmbeddingGemma 2 disappoints |
| Voyage-4 | Older voyage-3-large was second on XTREME-UP; none for v4 | Hosted fallback | None locally | Paid API | Test only if Gemini disappoints |
| e5-base | Consistently below BGE-M3 and e5-large, especially cross-script (20.81 v 35.00) | Whatever your run shows | 279 MB–1.11 GB; 38.9 min | MIT | Finish the test, expect it to trail. A loss doesn't count against e5-large |
| e5-large | Ties BGE-M3 same-language and in Hindi-BEIR's cross-lingual set (35.00 v 34.40). The instruct variant trails on XTREME-UP (18.7 v 26.9) | Little over BGE-M3 | 2.24 GB, same order as BGE-M3 | MIT | Test only if BGE-M3 fails |
| e5-small | Worst of the family (.364) | Speed only | 118–471 MB | MIT | Skip |
| Karmx bge-m3 fine-tune | +.02 on its own test, self-reported | Small gain if BGE-M3 wins | Int8 570 MB; I did not see int8 retrieval scores | MIT, naming condition | Skip until BGE-M3 wins |
| Bharat-Embed 270M | Hindi and Hinglish only | Hinglish, if that proves common | Int8 ONNX, size unverified | Apache 2.0 | Skip for now |
| Qwen3-0.6B / 8B, qwen-indic-v1 | 0.6B weak on XTREME-UP; 8B strong on Indic-MTEB, weak on Bengali farm data | Unclear | 8B needs about 16 GB VRAM | Apache 2.0 | Skip on CPU |
| jina-v3, v4, v5 | v3 averages 8.5 on XTREME-UP | None shown | 424 MB–1.14 GB | Non-commercial or research | Skip |
| Vyakyarth | Self-reported Flores only | None shown | 1.11 GB | Restrictive | Skip |
| IndicBERTv2, L3Cube SBERT | I found no retrieval benchmark | None shown | ~1 GB | MIT / CC-BY | Skip |
| NLLB-E5, LaBSE | NLLB-E5 leads Hindi-BEIR; LaBSE weak everywhere | None worth the cost | NLLB-E5 3.3B | NLLB non-commercial | Skip |
| Sarvam | No embedding API on its price page | n/a | n/a | n/a | Nothing to test |

- XTREME-UP's numbers are vendor-run, so they need confirming here. The two Google papers report identical comparator scores, so they probably share one run and don't count as two confirmations.
- The 20-language tables are most likely XTREME-UP's cross-language task, because only that task has that many languages. The Gemini and EmbeddingGemma pages I read don't state it outright.
- Together with XOR-Retrieve (Bengali, Telugu) and IndicRAGSuite (Nepali), these cover 18 of the 22 scheduled languages. I found no retrieval measurement for Dogri, Kashmiri, Santali or Sindhi.
- Building the index elsewhere (a borrowed GPU, once per corpus version) and embedding only questions on this laptop would make BGE-M3 practical. A question is far shorter than a chunk. I have not costed or timed this.
- Audit first: confirm no e5 path goes through the hardcoded prefix in `rag/`, since a wrong prefix can change results more than the model does.

### Gaps
- I found no independent 22-language comparison, and no independent re-run of XTREME-UP results.
- No Indic scores found for Gemini Embedding 2, EmbeddingGemma 2 on XTREME-UP, Voyage-4, Cohere Embed v3 or v4, Jina v5, or Harrier beyond Indic-MTEB.
- I could not verify any published CPU throughput for these models, and I did not verify Google's public memory or speed claims for EmbeddingGemma.
- Whether Qwen3's low XTREME-UP scores reflect the model or missing instruction prefixes is unknown.
- The e5 size in the Sri Lankan paper isn't stated, and IndicRAGSuite is explicitly work in progress.

## Hosted embedding APIs: prices, free tiers, Indic quality, and would hosted beat indexing on this laptop?

### Takeaway
On cost and time, yes: a full re-index would cost well under a dollar, against 38.9 minutes on a laptop. On quality, Gemini has the best published Indic results, though for the older model. The catches are that every question must then reach the API, the free tier's data is used to improve Google's products, and changing models means re-embedding everything.

### Cited Findings
- **Gemini, official [P]:** gemini-embedding-2 text is $0.20 per million tokens, batch $0.10. gemini-embedding-001 is $0.15, batch $0.075. Both are free on the free tier, with no free batch. The free tier is marked "Used to improve our products: Yes", paid "No" — [Google pricing](https://aistudio.google.com/docs/pricing)
- **Gemini limits [P]:** Tier 1 allows 500,000 batch-enqueued tokens for Gemini Embedding. RPM, TPM and RPD aren't printed there; they appear in the account's own AI Studio page — [rate limits](https://aistudio.google.com/docs/rate-limits)
- **Gemini usage [P]:** Limits are 8,192 tokens for -2 and 2,048 for -001, with 128–3072 dimensions (768, 1536 and 3072 recommended). -2 has no `task_type`; use text prefixes such as `task: search result | query: ...` and `title: ... | text: ...`. The two models' vectors are incompatible, so upgrading means re-embedding — [embeddings docs](https://aistudio.google.com/docs/embeddings)
- **Voyage, official [P]:** voyage-4 $0.06, voyage-4-lite $0.02, voyage-4-large $0.12, voyage-3-large $0.18, voyage-multilingual-2 $0.12 per million tokens. The first 200M tokens are free on current models. The page contradicts itself on free tokens for older models — [Voyage pricing](https://docs.voyageai.com/docs/pricing)
- **Cohere [S for price]:** Embed v4 is most often quoted at $0.12 per million tokens (one blog says $0.10); Cohere's own page doesn't list it — [Puter summary](https://developer.puter.com/tutorials/cohere-api-pricing/). Trial keys are "not permitted to be used for production or commercial purposes" — [Cohere pricing, P](https://cohere.com/pricing)
- **Jina [P for limits]:** Free key 100 RPM and 100K TPM; paid 500 RPM and 2M TPM. No per-token price on that page. v4 is free but throttled and not for production. The site is now under Elastic branding — [Jina](https://jina.ai/embeddings/)
- **Sarvam [P]:** The price page lists no embedding or rerank API — [Sarvam pricing](https://docs.sarvam.ai/api/pricing.md)
- **Indic quality:** Gemini and voyage-3-large figures appear in the previous section. Independent check: gemini-embedding-001 led dense models on Bengali (.464 v BGE-M3 .408) but fell to R@10 .093 on colloquial farmer queries, where BM25 got .523 — [Where Does Retrieval Fail?](https://www.alphaxiv.org/abs/2608.14886.md)

### Inferences
- **Cost for today's corpus (my arithmetic, assuming 2–4 characters per token, so 1–2M tokens for 4.04M characters):** gemini-embedding-2 $0.20–0.40, batch $0.10–0.20. Voyage-4 $0.06–0.12, inside its free allowance.
- **At 100 times the corpus:** about $20–40 on Gemini, or $10–20 batched, against about 65 hours for e5-base here if time scales linearly. A Tier 1 batch queue of 500,000 tokens would need many small batches.
- **Query cost is negligible.** The real costs are the network call on each search and depending on one vendor's vector space.
- **Privacy:** official documents are public, so indexing on the free tier is low risk, but citizens' questions may contain personal details. I would keep questions on a paid tier. Google's free-tier terms are the deciding text; I read only the pricing line.
- **Recommendation:** test gemini-embedding-2 at 768 dimensions and -001 together on the Marathi set and the 80/93 and 55/59 tests. Prefixes must be right for -2, because the same paper shows configuration can swamp model choice. Local models remain the offline fallback.

### Gaps
- Free-tier RPM and RPD for embeddings aren't on the public page, so I can't say how long a free-tier index would take.
- The docs page doesn't mention an OpenAI-compatible embedding endpoint. I did not confirm whether VETRA's current client can call embeddings this way.
- Voyage's data-use terms and rate limits weren't checked, and neither was Cohere's current list price.
- Jina's per-token price isn't on the page I read.

## Which multilingual cross-encoder rerankers work on Indian-language passages, and how fast on CPU?

### Takeaway
I found no head-to-head test of rerankers on Indian-language passages. The only Indic number is a tiny self-reported gain. The one CPU timing suggests bge-reranker-v2-m3 takes about 20 seconds per question at VETRA's 30 candidates, which is too slow here. VETRA's current reranker is English-only, so the cheapest useful test is whether to turn it off for non-English text.

### Cited Findings
- [Local] VETRA currently uses `cross-encoder/ms-marco-MiniLM-L-6-v2` for both domains (`vetra/domains.py:37,50`), and the older `rag/domains.py:350` config reranks 30 candidates.
- [Vendor, P] Top-50 reranking with bge-reranker-v2-m3 moved IndicQARetrieval from 80.41 to 80.76 nDCG@10. That is the only Indic reranker number I found, and it comes from an embedder's own card — [Karmx card](https://huggingface.co/karmx/Llama-Karmx-Indic-Embedding-bge-m3)
- [Vendor, P] Jina's table, reporting MKQA (26 languages) / BEIR / MLDR (13 languages): jina-reranker-v2 54.83 / 53.17 / 68.95; bge-reranker-v2-m3 54.17 / 53.65 / 59.73; mmarco-mMiniLMv2 53.37 / 45.40 / 28.91. The page doesn't say whether Indian languages are included — [Jina reranker card](https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual)
- [S, low confidence] One personal wiki reports bge-reranker-v2-m3 at about 20.9 s median for 30 candidates at max_length 256 on an unnamed CPU, bge-reranker-base at about 5.4 s with 80% top-3 overlap. Its int8 speedup is a projection. I saw this only in search excerpts, because the page returned 404 when opened — [wiki excerpt](https://myforgelabs.github.io/myforge-vault-1111/wiki/reranker-cost-optimization-not-size.en/)
- [Indep, P] Sentence Transformers' CPU guidance, tested on an i7-13700K including bge-reranker-v2-m3: fp16 and bf16 run about 0.17× on CPU, so avoid them. Use openvino-qint8 if slight quality loss is acceptable. If it isn't, use openvino on Intel CPUs and onnx-O3 on others. The per-backend numbers are in a chart I couldn't read — [SBERT efficiency docs](https://www.sbert.net/docs/cross_encoder/usage/efficiency.html)
- [S] Dynamic int8 on the related BGE-M3 dropped top-1 overlap to .625, a warning rather than a measurement of the reranker — [Sophia-AI card](https://huggingface.co/Sophia-AI/bge-m3-onnx)
- [Vendor, P] mMiniLMv2 was trained on machine-translated MS MARCO in 14 languages, which the card doesn't list — [card](https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1)
- [Claim, P] FlashRank's `ms-marco-MultiBERT-L-12` claims 100+ languages at about 150 MB. Its benchmarks are marked "TBD" — [FlashRank](https://github.com/PrithivirajDamodaran/FlashRank). The zip is 104 MB, and the repo is tagged CC-BY-SA-4.0 (HF API).
- [Hosted, P] Voyage rerank-3 costs $0.05 and rerank-3-lite $0.02 per million tokens, with 200M free — [Voyage pricing](https://docs.voyageai.com/docs/pricing). No Indic evidence.
- [Hosted, S] Cohere Rerank is quoted at $2 per 1,000 searches. One tracker reports Rerank 5 moved to per-token pricing, which I couldn't confirm — [tracker](https://www.usagepricing.com/blueprint/activity/cohere-2026-10-23-rerank-5-per-token-pricing). A search unit is one query with up to 100 documents, and documents over 500 tokens count as several — [Cohere](https://cohere.com/pricing)

### Inferences

| Candidate | Evidence on Indic | Would improve in VETRA | CPU cost | Licence | Verdict |
|---|---|---|---|---|---|
| ms-marco-MiniLM-L-6-v2 (current), off for non-English | None; trained in English | Possibly stops harm to Indic rankings | Already in use | n/a | **Test now**: on v off on the Marathi set |
| bge-reranker-v2-m3 | Tiny self-reported gain | Possibly ordering | 2.27 GB; ~20 s/30, one low-confidence source | Apache 2.0 | Test only with fewer candidates, or on a quantised build with its quality checked |
| Voyage rerank-3-lite, hosted | None | Rerank without the laptop | None locally | Paid API | Test if on/off shows reranking matters |
| mMiniLMv2 | None; weak on Jina's MLDR | Lightweight option | qint8 118 MB | Apache 2.0 | Test only if a small multilingual reranker is needed |
| FlashRank MultiBERT | None | Lightweight option | ~104–150 MB | Library Apache; model tag CC-BY-SA | Skip until it has numbers |
| Jina reranker v2 | Not Indic-specific | Best MLDR score in its own table | int8 280 MB | CC-BY-NC | Skip unless licensed |
| Qwen3-Reranker-0.6B | None | Unknown | 1.19 GB | Apache 2.0 | Skip |
| Cohere Rerank | None found | Anthropic's gain in the existing doc used it | None locally | Paid; no production on trial | Skip for now |

- This confirms the existing doc's item 5 ("try a better reranker") only weakly. The first-stage retriever and BM25 have far stronger evidence, so rerankers should come after the embedding decision.
- A reranker can only reorder what search found. With Marathi at 9 of 20 before any change, most of the gain is likely in finding the passage at all.

### Gaps
- No per-language reranker results for any Indian language, and no measured CPU latency on a named laptop for any multilingual reranker.
- Whether the MKQA or MLDR sets include Indian languages wasn't stated on the page I read.
- No evidence on how an English cross-encoder scores Indic passages.

## Keyword search for Indic scripts: stemming, normalisation, Unicode variants, code-mixing and romanised input

### Takeaway
BM25 is worth keeping: on Bengali it beat every embedding model tested, and on colloquial farmer queries by a very wide margin. It collapses across scripts, so the dual-language query is needed. VETRA's tokeniser has fixable gaps I reproduced on sample strings: it splits words at ZWJ and ZWNJ, drops Meitei Mayek entirely, and treats Devanagari digits and Latin digits as different words. Romanised queries are the largest unmeasured risk.

### Cited Findings

**BM25 on Indian languages**
- [Indep, P] Bengali R@10: BM25 .506, dense Gemini .464. Farmer queries: BM25 .523, dense .093. Safety queries: BM25 .539, dense .970. English query, Bengali documents: BM25 .004, dense .425. Tokens were character bigrams plus full words — [Where Does Retrieval Fail?](https://www.alphaxiv.org/abs/2608.14886.md)
- [Indep, P] On Hindi, BM25 won IndicQARetrieval (74.02) and Touché-2020 (33.59), but averaged 35.65 against 46.18 for BGE-M3 — [NLLB-E5 paper](https://arxiv.org/html/2409.05401v3)

**VETRA's tokeniser [Local, on sample strings using the regex from `vetra/text_index.py:34`, without loading project code]**
- A ZWJ inside a Marathi word and a ZWNJ inside a Bengali word each split the word into two tokens.
- A Meitei Mayek word produced no tokens. Arabic presentation forms also produced none. The regex lacks these blocks, which Unicode lists at [ABC0–ABFF and AAE0–AAFF (Meetei Mayek) and FB50–FDFF, FE70–FEFF (Arabic forms)](https://www.unicode.org/Public/UNIDATA/Blocks.txt). Arabic Supplement 0750–077F is also outside it.
- `२०००` stays one token that will never match `2000`, although Python's `int()` reads it as 2000. `vetra/languages.py:58` already has a digit-mapping line that could be reused; I did not trace where it is called, but `words()` doesn't apply it.
- A search of `rag/` and `vetra/` finds no NFC or NFKC call, so precomposed U+0958 and U+0915 U+093C compare unequal. NFC makes them equal. NFC does **not** unify Malayalam's atomic chillu with its ZWJ form.
- `pm-kisan` becomes `pm` and `kisan`, so hyphenated scheme names match on parts.

**Unicode and normalisers**
- Nineteen precomposed nukta letters in Devanagari, Bengali, Gurmukhi and Oriya are composition exclusions, so NFC keeps base + nukta — [Unicode](https://www.unicode.org/Public/UNIDATA/CompositionExclusions.txt)
- [P] Indic NLP Library normalisers cover hi, mr, sa, kK, ne, sd, ur, pa, gu, bn, as, or, ml, kn, ta, te; anything else gets a generic fallback. The base normaliser deletes ZWJ and ZWNJ. Options include nasal handling, chandra normalisation, chillu canonicalisation for Malayalam and addak and tippi for Gurmukhi. It doesn't convert digits except for Urdu, which needs UrduHack — [source code](https://raw.githubusercontent.com/anoopkunchukuttan/indic_nlp_library/master/indicnlp/normalize/indic_normalize.py)
- [P] The library is MIT licensed, and its last changelog entry is May 2021. No stemmer is listed — [repo](https://github.com/anoopkunchukuttan/indic_nlp_library)

**Stemming [S, 2010–2013 work on FIRE 2008, seen in search excerpts; I did not open these papers, so check the links match the authors before citing]**
- Aggressive stemming gained about 28% for Hindi and 42% for Marathi over none, and 4-character truncation performed about the same — [Savoy and colleagues](https://libra.unine.ch/handle/20.500.14713/65208)
- Overlapping 3-grams were best for Bengali and Marathi and 4-prefixes for Hindi under BM25; with feedback, 4-prefixes led all three — [Leveling and Jones](https://doras.dcu.ie/16033/)
- Snowball offers Hindi, Nepali and Tamil stemmers among Indian languages, and no Urdu — [Snowball](https://snowballstem.org/algorithms/)

**Romanised and code-mixed input**
- [Indep, P, read from the PDF] BGE-M3 on transliterated queries: MRR@10 fell 97% for Chinese (.2342 to .0078) and 49% for Russian (.2444 to .1244). The mT5 reranker fell too. Mixed native and transliterated fine-tuning recovered much of this on the training domain (Russian .2770, Chinese .1382). On other collections results were mixed and some native-script quality was lost. No Indian language was tested — [Lost in Transliteration, SIGIR 2025](https://arxiv.org/pdf/2505.08411)
- [Vendor, P] IndicXlit has about 11M parameters, is MIT, runs both directions, and covers 21 languages plus zero-shot Dogri, with no Santali. Top-1 accuracy Roman to Indic: Dakshina 42.12 (Urdu) to 77.18 (Kannada), Aksharantar 28.76 (Kashmiri) to 84.69 (Telugu). No CPU speed given — [IndicXlit](https://github.com/AI4Bharat/IndicXlit)
- [Vendor, P] A newer 60M-parameter Marian model for romanised Hindi and Bengali: Hindi CER .09, WER .13, Bengali CER .16, WER .25. It gives no retrieval numbers and no licence — [Modeling Romanized Hindi and Bengali](https://arxiv.org/html/2511.22769)
- [S] Edinburgh's WMT22 system used the AI4Bharat transliterator's top 4 candidates per token for Hinglish — [paper](https://arxiv.org/pdf/2210.11309). A FIRE 2024 paper calls code-mixed IR "relatively underexplored" — [RetrieveGPT](https://arxiv.org/pdf/2411.04752v3)

### Inferences

| Candidate | Evidence | Would improve in VETRA | CPU cost | Licence | Verdict |
|---|---|---|---|---|---|
| NFC, strip ZWJ/ZWNJ, digits to ASCII, extra character ranges | Reproduced above | More matches in existing keyword search, all languages | Negligible | Code | **Adopt now**, after a before-and-after run on the current tests. Treat this as a tokeniser change and re-index |
| Indic NLP normaliser | Script-specific rules; old | Nasal, chandra, chillu, gurmukhi variants | Light | MIT | **Test**, one option at a time |
| Second keyword field of character 3-grams or 4-prefixes | Old FIRE results; a 2026 paper's bigrams | Inflection, without 22 stemmers | Larger index | n/a | **Test** on Marathi |
| Snowball Hindi, Nepali, Tamil | Covers 3 of 22 | Three languages only | Light | Not read | Skip for now |
| Planner rewrites romanised input to native script and English | Language detection is already 31 of 32 here; no retrieval measurement | Hinglish without a new model | One API call already made | n/a | **Test**: it should be measured as a condition of its own |
| IndicXlit | Word accuracy published; retrieval use unmeasured | No-key fallback when the API fails | 11M; speed unmeasured | MIT | Test as fallback only |

- Short numbers in queries matter here: VETRA prints exact facts, so a digit mismatch costs direct matches. Mapping digits must apply to both the documents and the queries.
- Keep Latin and Indic tokens both in the index, since official Indic documents routinely embed English scheme names. This is my expectation from code-mixing work, not something I measured here.
- The farmer-query result is a warning for VETRA's HyDE-style formal English passage. Formal wording may suit documents but won't help when the citizen's colloquial word appears only in one register.

### Gaps
- I found no 2025–2026 stemming study for BM25 on Indian languages, and nothing for Tamil.
- No published Indian-language measurement of embedding loss on romanised queries, so the 97% and 49% figures are transferred from Chinese and Russian. The closest statement, that BGE-M3 does poorly on romanised queries, cites this same paper.
- Whether stripping ZWJ/ZWNJ ever merges words that should stay distinct wasn't checked.
- Whether real citizens' questions are romanised at a high rate is unknown; VETRA's logs would answer it.

## Translation: IndicTrans2, Sarvam Translate, Bhashini, Gemini; quality on legal or government text; keeping numbers and terms safe

### Takeaway
For English to Hindi legal text, Gemini-2.5-Pro is among the top in human evaluation, so staying on Gemini is defensible for Hindi. Outside Hindi the evidence is thin and older. IndicTrans2 has the best independent multi-language legal evidence and is MIT licensed, and its placeholder method is worth copying. VETRA's approach of checking numbers and printing the English beside facts has more support than trusting any model, because no study shows a system safe enough to skip it.

### Cited Findings
- [Indep, P, abstract only] WMT 2025: on a 5,000-sentence English to Hindi legal test, Gemini-2.5-Pro, Claude-4 and ONLINE-B ranked highest in human evaluation. The authors still call for more robustness work before critical legal use. Data at github.com/helloboyn/WMT25-TS — [Singh et al.](https://aclanthology.org/2025.wmt-1.57/). The count of "thirty-seven LLMs" I saw only second-hand — [JUST-NLP paper, S](https://preview.aclanthology.org/ingest-ijcnlp-aacl/2025.justnlp-main.15.pdf)
- [Indep, P] JUST-NLP 2025 English to Hindi legal task: the top system was a fine-tuned distilled NLLB-200 with an average score of 72.1, and domain adaptation gave substantial gains — [findings](https://aclanthology.org/2025.justnlp-main.3)
- [Indep, P, 2023, older models] MILPaC (17,853 pairs, English plus nine languages). Automatic scores: GOOG, MSFT and IndicTrans led most settings; GPT-3.5-era LLMs were poor. On Acts, law students preferred IndicTrans for all three rated language pairs; English to Marathi meaning scores were IndicTrans 4.0, MSFT 3.60, GOOG 1.94. Suitability for legal use was below meaning for every system. Automatic metrics correlated poorly with human scores (about .1 on FAQs). Only five students rated — [MILPaC](https://arxiv.org/html/2310.09765v2)
- [Indep, P, Indic-to-Indic, not English] CorIL covers health, governance and general text. Governance scored above health. IndicTrans2 was very weak on Urdu and strong on Punjabi. Its count of languages and pairs varies within the paper — [CorIL](https://arxiv.org/html/2509.19941v1)
- [Indep, P] Handwritten Marathi legal documents: OCR then MT cascades errors, vision LLMs invent text, and handwritten dates were often wrong. No numeric scores — [Seeing Justice Clearly](https://arxiv.org/html/2512.18004v1)
- **IndicTrans2 [P]:** Its pre-processing maps Indic numerals to Roman, then wraps emails, URLs, dates, times, percentages, ratios and handles in `<ID1>`-style placeholders. It also recognises placeholders that got translated. **Numeral matches under 4 characters are left unprotected** — [source code](https://raw.githubusercontent.com/AI4Bharat/IndicTrans2/main/inference/normalize_regex_inference.py). It covers 22 languages under MIT — [S, excerpts](https://arxiv.org/pdf/2305.16307.pdf)
- **Sarvam Translate [Vendor, P]:** Gemma-3-4B based, GPL-3.0, CUDA examples only, English to and from Indian languages — [card](https://huggingface.co/sarvamai/sarvam-translate). The blog claims it beats larger open LLMs in human evaluation and is "suitable for professional legal use", with one Assamese example and no legal numbers. It does not compare with IndicTrans2. It admits lower quality for Bodo, Dogri, Kashmiri, Manipuri, Santali, Sanskrit and Sindhi — [Sarvam blog](https://www.sarvam.ai/blogs/sarvam-translate)
- **Sarvam API [P]:** ₹2 per 1,000 characters pay-as-you-go, ₹100 free credit — [docs](https://docs.sarvam.ai/api/pricing.md). The marketing page says ₹1,000 in credits — [conflict, S](https://sarvam.ai/api-pricing)
- [Vendor, third party, unvetted] One card scores itself above Sarvam Translate using a Gemini 3 Flash judge — [bodhan-ai](https://huggingface.co/bodhan-ai/indic-translate). I would not rely on it.
- [Vendor, S] A legal fine-tune of IndicTrans2 reports improved scores — [InLegalTrans](https://huggingface.co/law-ai/InLegalTrans-En2Indic-1B). I did not open it. Fine-tuning IndicTrans on MILPaC raised BLEU substantially, for example English to Marathi 20.6 to 40.1 — [MILPaC](https://arxiv.org/html/2310.09765v2)

### Inferences

| Candidate | Evidence | Would improve in VETRA | CPU cost | Licence | Verdict |
|---|---|---|---|---|---|
| Keep Gemini; keep number checks and printed English | Top human rank for Hindi legal; other languages untested | Already in place | None | API | **Adopt** (keep) |
| Copy IndicTrans2's placeholder idea, protecting short numbers too | Its code shows the method; it leaves short numbers exposed | Number faults caught before they happen; would also reduce retries | Negligible | MIT if code is reused | **Adopt** as a mask before Gemini, and keep the post-check. Measure with a small test |
| IndicTrans2 | Best independent legal evidence, older; weak on Urdu | Second opinion, a fallback without an API, or a cross-check on the number check | Model size not read for all checkpoints; CPU speed unpublished | MIT | **Test** on about 50 facts across a few languages, against Gemini |
| Sarvam Translate API | Vendor only | India-based option, price is low | None locally | Paid | Test only if Gemini fails in a language |
| Sarvam open model | Vendor only | Nothing on CPU | 4B, roughly 8 GB by card-derived estimate | GPL-3.0 | Skip here |
| Bhashini | I could not reach its documents | Possibly a free public option | n/a | Unknown | Could not assess |
| JUST-NLP-style fine-tuning | Good gains | Domain-specific quality | Training needed | Mixed, NLLB non-commercial | Skip for now |

- Automatic BLEU-type scores are poor stand-ins here, since MILPaC found they barely track legal readers. A small human or second-model review of meaning is better for VETRA.
- Maintain a glossary of scheme names, units and legal terms, kept in English or a fixed form, using the same masking. This is my suggestion and I did not find it measured in Indian languages.
- MILPaC's human-preference results come from a pre-Gemini generation of LLMs, so they don't argue against Gemini.

### Gaps
- **Bhashini:** the official site returned no usable text to my tool and my searches found only third-party pages, which conflict on pricing. I could not verify its API access, limits, price or quality.
- No head-to-head on government or legal text for Gemini, Sarvam Translate and IndicTrans2 together, and no 2026 multi-language legal benchmark.
- No published measure of number or date corruption by these translators. WMT25's per-metric scores were not in the abstract.
- Low-resource languages have effectively no legal evaluation.

## Benchmarks and datasets to test on, and what a small all-India test should include

### Takeaway
No public benchmark matches VETRA's task. The nearest are AgriTrust-RAG for agriculture and method, XTREME-UP for Indian questions on English passages, and IndicMSMarco for breadth. VETRA still needs its own small labelled test, reported by language condition and query type.

### Cited Findings
- **IndicMSMarco:** 1,000 queries across 13 languages, same-language; the abstract says manual translation while the conclusion mentions Llama 3.3 plus expert correction. Training data: about 14M Wikipedia triplets across 19 languages and translated MS MARCO — [IndicRAGSuite](https://arxiv.org/pdf/2506.01615)
- **XTREME-UP:** cross-language retrieval for 21 under-represented languages, with released code and scripts; I did not confirm where retrieval data is distributed — [paper](https://arxiv.org/html/2305.11938)
- **Hindi-BEIR:** 15 Hindi retrieval datasets; other languages are future work — [paper](https://arxiv.org/html/2409.05401v3)
- **IndicQARetrieval:** 10 languages, 16,775 queries as reported on one card. **Belebele:** 9,000 questions in that card's adapted retrieval form — [Karmx card](https://huggingface.co/karmx/Llama-Karmx-Indic-Embedding-bge-m3)
- **MTEB(Indic):** a benchmark task set with bitext, classification, clustering, retrieval and reranking; its only retrieval tasks in the card I read are XQuAD and Belebele — [MMTEB](https://arxiv.org/pdf/2502.13595), [task list](https://huggingface.co/LingoIITGN/qwen-indic-v1)
- **AgriTrust-RAG (Bengali, Bangladesh):** colloquial, knowledge-graph and safety queries, with results by language condition — [paper](https://www.alphaxiv.org/abs/2608.14886.md)
- **AgriGov:** 50 Indian farmer schemes in English, Hindi and Marathi at github.com/mohsina-bilal/Farmer-Chatbot. No retrieval labels or results, no licence stated, inconsistent counts (about 8,000 v "over 5,000" records), about 87–90% aligned — [paper](https://arxiv.org/html/2606.08272v1)
- **Translation sets:** MILPaC; WMT25-TS; JUST-NLP's 60,000 legal pairs; CorIL's governance domain — [MILPaC](https://arxiv.org/html/2310.09765v2), [WMT25](https://aclanthology.org/2025.wmt-1.57/), [JUST-NLP](https://aclanthology.org/2025.justnlp-main.3), [CorIL](https://arxiv.org/html/2509.19941v1)
- **Not retrieval:** MILU is 11 languages of exam-style LLM tests and found models struggled more in Law and Governance than STEM — [MILU](https://arxiv.org/abs/2411.02538). IndQA is 2,278 rubric-graded questions across 12 languages including Hinglish, and OpenAI says it isn't a language leaderboard — [OpenAI](https://openai.com/index/introducing-indqa)
- **FIRE:** 2024 code-mixed Roman Bengali track — [RetrieveGPT](https://arxiv.org/pdf/2411.04752v3); older Hindi, Bengali and Marathi collections from FIRE 2008 — [Leveling and Jones](https://doras.dcu.ie/16033/)
- The Bengali study recommends reporting by language condition and query type, and auditing configuration before comparing architectures — [paper](https://www.alphaxiv.org/abs/2608.14886.md)

### Inferences
**A small all-India test (my design):**
- **Questions from official documents only**, with the supporting chunk labelled. Include both English-document and Indian-language-document targets.
- **Five language conditions:** native to native; native to English; English to native; romanised to either; code-mixed to either. Report each one separately.
- **Three query styles:** colloquial citizen wording, formal wording, and exact-number questions. Add questions the corpus can't answer, as the existing doc recommends.
- **Three language tiers:** large (Hindi, Bengali, Marathi, Tamil, Telugu); middle (Gujarati, Kannada, Malayalam, Punjabi, Odia, Urdu, Assamese); low-resource (Bodo, Dogri, Kashmiri, Konkani, Maithili, Manipuri, Nepali, Sanskrit, Santali, Sindhi). Roughly 40 in the first tier and 15 to 20 in the others is a reasonable start, but low-resource tiers may be limited by available documents.
- **Metrics:** Recall@10 and MRR@10, with the same questions across every model and paired comparisons.
- **Sample size warning:** 20 questions are too few to rank models. Wilson 95% intervals (my arithmetic) are about 11–47% for 5 of 20 and 26–66% for 9 of 20. Those overlap, although a paired test on the same questions is more sensitive and could still show a real gain.
- **Pre-checks for each model:** prefixes, passage length, and truncation. Also record index time and peak RAM, which is the CPU data no one publishes.
- **Public datasets:** use them as a sanity check of a pipeline, not as the decision. Their Wikipedia and MS MARCO content is far from government orders.

### Gaps
- **AIRAVATA:** my search returned nothing on it, so I can't say what it offers. I would not assume it contains retrieval data.
- Distribution and licence of IndicQARetrieval, Belebele and the FIRE collections weren't checked individually.
- The size of Indian-language government test collections beyond AgriGov wasn't established; I found none with retrieval labels for India.

## Is translating every question to English and searching an English index competitive with multilingual embedding?

### Takeaway
Against English documents, it is close but slightly behind the best multilingual model, and it depends on the translator's quality. Against Indian-language documents it fails for keyword search, and an all-English index would need those documents translated first. VETRA's current design of searching with both English and native queries should stay, since it is what the evidence favours and what your own Marathi test shows.

### Cited Findings
- [Indep, P] Tamil to English, Recall@1 / 5 / 15: BGE-M3 61.0 / 89.6 / 95.6; Google Translate 59.4 / 85.2 / 93.0; NLLB 53.2 / 80.0 / 89.0; mBART50 48.4 / 76.0 / 85.2; no adaptation 0.6 / 2.0 / 4.2. For Sinhala, Google Translate edges BGE-M3 at Recall@1 (60.0 v 59.4), and BGE-M3 wins from Recall@3. Authors recommend cross-lingual embeddings as the foundation, with hybrids as future work — [Balasubramaniyam and Madushanka](https://arxiv.org/html/2608.12820v1)
- [Indep, P] Bengali, R@10: Bengali to Bengali dense .464, BM25 .506; English to Bengali dense .425, BM25 .004; English to English dense .442, BM25 .384 — [Where Does Retrieval Fail?](https://www.alphaxiv.org/abs/2608.14886.md)
- [Indep, P] Hindi-BEIR: English queries on Hindi articles gave BM25 0.01 — [paper](https://arxiv.org/html/2409.05401v3)
- [Local, from the brief] On the Marathi test with bge-small: English only 0 of 20, Marathi only 5 of 20, both 9 of 20.
- [Indep, S, a design not a comparison] One January 2026 Bengali farm system retrieves over English manuals and translates back, claiming practicality without a controlled comparison — [paper](https://arxiv.org/abs/2601.02065?context=cs)
- [S] Related work in the Sri Lankan paper notes query translation is sensitive to ambiguity in short queries — [paper](https://arxiv.org/html/2608.12820v1)

### Inferences
- **Adopt now (keep):** the planner's two queries. VETRA's Marathi result and the Bengali BM25 figures agree that each script's keyword search reaches different text.
- **Don't replace it with English-only search:** VETRA holds Indian-language documents, and state documents will add more. English-only search got 0 of 20 on the Marathi test, though with an English-only embedding model, and a multilingual one may close part of that gap.
- **Test:** on each candidate embedding model, compare English query only, native query only, and both, on the same questions. If the embedding model does well on native queries alone, a planner failure stops being fatal, which helps availability.
- **Unmeasured link:** the published query-translation results use Google Translate, NLLB and mBART. Gemini's query translation hasn't been measured in these studies. VETRA's planner also adds a formal passage, which behaves differently from a literal translation.
- **Limits of the evidence:** the closest study has only 500 questions and a small corpus, and its overlap with India is Tamil. Recall@15 on 1,699 contexts is an easy cut-off, so the smaller gaps at Recall@1 and @5 are more informative.

### Gaps
- No controlled test on Indian government documents of translate-then-search against multilingual embedding. The search that targeted it returned none.
- No result for a hybrid of translated and native queries in any Indian language other than your own Marathi test, which was run with an English embedding model.
- No figures on how query translation affects low-resource languages; Sarvam's own warnings suggest it would be worse there.
