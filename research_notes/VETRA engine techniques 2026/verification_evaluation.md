# Verification, citation accuracy, abstention, calibration, evaluation and observability for VETRA (checked 5 November 2026)

**Evidence labels used below.**
- **[M-peer]**: measured, in a peer-reviewed paper or official shared-task report.
- **[M-pre]**: measured, in a preprint.
- **[M-repo]**: measured, in a GitHub repo or informal write-up.
- **[Vendor]**: a claim or measurement by the maker of the thing being measured, including model cards and vendor-affiliated authors.
- **[Docs]**: official documentation of how something behaves, not a measurement.
- **[Secondary]**: read through a summary or a search excerpt, not the original.
- **[Calc]**: my own arithmetic. Inference blocks are also mine.

**How the sources were read.** Most papers were read through a page-fetching summariser working from arXiv HTML or abstracts. I read the Mu-SHROOM and SHROOM-CAP tables directly from page images of the PDFs. Treat exact figures as "as reported" and re-open the paper before quoting one in public. Papers with arXiv IDs from 2606 onward are recent preprints, and I checked them only against their own text.

## NLI and entailment checks on CPU across Indian languages: can they replace or reduce the second reader?

### Takeaway
No small model has been shown to check Telugu answers against English evidence well enough to cut sentences, so none should replace the second reader. The cheapest measured gain is a better second-reader prompt with annotation guidelines and few-shot examples, not a new model. A small NLI model is worth testing only in log-only mode on quick and standard answers, which have no second reader today.

### Cited Findings

**Multilingual NLI models**
- [Vendor] mDeBERTa-v3-base-xnli has about 0.3B parameters. It was fine-tuned on 27 languages, of which Hindi, Bengali, Marathi, Tamil and Urdu are Indian. Telugu, Kannada, Malayalam and others were not fine-tuned. Reported XNLI accuracy is English 0.871, Hindi 0.769 and Urdu 0.744, with no scores for Bengali, Marathi or Tamil. ANLI is 0.537. Speed is quoted only on an A100 GPU (Hindi 1,115 texts/s). The card warns that claims of about 90% non-English accuracy are probably mistaken, and notes that machine-translated training data lowers quality — [model card](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7)
- [M-peer, older] IndicXNLI, 11 Indian languages including Telugu, machine-translated from XNLI. Same-language accuracy when trained on it:
  - Telugu: XLM-R 76, IndicBERT 62, mBERT 69, MuRIL 78.
  - Hindi: XLM-R 78, IndicBERT 68, mBERT 74, MuRIL 71.
  - Average: XLM-R 70, IndicBERT 65, mBERT 66, MuRIL 74.
  - Odia: XLM-R 32 and mBERT 35, against MuRIL 76. Tamil: IndicBERT 37.
  - Mixed input is the closest published analogue to VETRA: English premise with an Indian-language hypothesis, trained on English plus Indic. Telugu scores XLM-R 72, IndicBERT 64, mBERT 60, MuRIL 69. Hindi scores XLM-R 76, IndicBERT 69, mBERT 63, MuRIL 69. The paper says mixed-language input performs worse than same-language input, and that XLM-R beats the Indic-specific models there. No variance across runs is reported, and human checking of translations covered only 100 sentences — [IndicXNLI](https://arxiv.org/html/2204.08776)
- [M-repo, exploratory] mDeBERTa on the Hindi part of X-Fact (163 test items, already-inspected split, 0 SUPPORTED items, unreviewed):
  - Direct Hindi evidence: 42.94%. Machine-translated English: 28.22%. Exact McNemar p = 0.0088 on accuracy, but the Macro-F1 gap was not significant (p = 0.19).
  - The skewed labels mean these numbers cannot be read as general accuracy. They only suggest that translating evidence first isn't a free fix — [Kharat repo](https://github.com/Onkar-Kharat/research-crosslingual-rag)

**Purpose-built hallucination detectors (English-centred)**
- [M-pre/community leaderboard] LLM-AggreFact, average across 11 datasets, higher is better:
  - FactCG-DeBERTa-L (0.4B) 75.6; Granite Guardian 3.3 (8B) 76.5; GPT-4o 75.9; Claude 3.5 Sonnet 77.2; top entry 79.5.
  - Every model scores about 58-61 on Expert QA. FactCG is 59.1 there and 86.7 on LFQA.
  - The page states no languages and no CPU figures — [leaderboard](https://llm-aggrefact.github.io/)
- [M-peer] FactCG (NAACL 2025) reports beating GPT-4o on that benchmark with a much smaller model. The abstract gives no scores — [FactCG](https://arxiv.org/abs/2501.17144)
- [Vendor] Granite Guardian 4.1-8B: "only trained and tested on English data." Balanced accuracy 0.760 (no thinking) and 0.764 (thinking) on LM-AggreFact. No hardware figures. Apache 2.0 — [model card](https://huggingface.co/ibm-granite/granite-guardian-4.1-8b)
- [Vendor/author] LettuceDetect: ModernBERT token classifier, 79.22% F1 on RAGTruth at example level, 30-60 examples/s on a single GPU — [paper](https://arxiv.org/abs/2502.17125). The repo lists English, German, French, Spanish, Italian, Polish and Chinese, plus v2 models on a "14-language" dataset it doesn't name. Tiny models are 17-68M. No CPU latency and no per-language F1. Span-F1 on the v2 test set is 0.642-0.689, and on the RAGTruth slice 0.528-0.574. MIT licence — [repo](https://github.com/KRLabsOrg/LettuceDetect)
- [M-repo] An independent single-author GPU test on HaluBench (n = 1,094), with McNemar checks on each component:
  - LettuceDetect alone: 0.648 balanced accuracy, specificity 0.42, described as "a screen, not a judge."
  - Guardian with thinking: 0.743.
  - A stack with an added number rule: 0.795.
  - Judging sentences without the question cost 0.06 balanced accuracy. No CPU results — [local-groundedness-check](https://github.com/NortonDesignLab/local-groundedness-check)
- [M-pre] Trivia++ (3,224 human-labelled organic RAG answers):
  - NLI-style SelfCheckGPT on RAGTruth had recall 0.938 but precision 0.209, flagging most answers.
  - LLM-as-a-Judge reached F1 0.694 and ROC-AUC 0.766, competitive with methods that use labels.
  - Above 5K characters of context, every detector dropped (judge 0.621).
  - HaluEval's prompted hallucinations are far easier (F1 0.996), which undercuts results measured only on it. HaluBench draws on six sources, but I did not check whether HaluEval is one of them — [Trivia++](https://arxiv.org/html/2605.11330)
- [M-pre] HALT-RAG (two frozen English NLI models plus lexical features) reports F1 0.739-0.979, validated only on HaluEval. It needs task-specific classifiers and raises latency as a concern — [HALT-RAG](https://arxiv.org/html/2509.07475v1)
- [M-pre, abstract only] QuanTemp, real-world numeric claims: best baselines reach only 58.32 macro-F1 — [QuanTemp](https://arxiv.org/abs/2403.17169)

**What improves an LLM reader**
- [M-peer] MEMERAG, human-labelled faithfulness in EN, DE, ES, FR, HI. Average balanced accuracy for GPT-4o mini rose from 59.7 (zero-shot) to 71.6 with annotation guidelines, and 71.7 with chain-of-thought added. Qwen 2.5 32B went from 66.7 to 71.8. For Hindi, guidelines plus chain-of-thought gave 74.1 (GPT-4o mini), 75.41 (Qwen 32B) and 65.22 (Llama 11B) — [MEMERAG](https://arxiv.org/html/2502.17163)
- [M-peer] FaithJudge, which gives the judge human-annotated examples from the same source. Best prior zero-shot was 68.8 balanced accuracy, against 84.0 with FaithJudge on FaithBench. A later table on a different setup shows 77.6, so the two aren't directly comparable. It needs annotated answers on the same sources and tends to under-predict for some models. Multilingual performance wasn't reported — [FaithJudge](https://arxiv.org/html/2505.04847v2)

### Inferences

| Candidate | Would improve in VETRA | CPU cost (no published CPU figures found) | Verdict |
|---|---|---|---|
| Annotation guidelines plus few-shot examples from this project's real failures, in the second-reader prompt; pass the question with each statement | Catches more wrong-wording errors on deep answers | None beyond the same Gemini call | **Adopt now**, and score it on the hand-read set |
| Second reader on standard answers too (cheap Gemini model), on selected risky sentences | Closes the biggest gap: wording errors in quick and standard answers are unchecked | API cost and latency only | **Test** |
| mDeBERTa | Cheap log-only signal for wording errors; works directly on non-English text | About 1.1 GB RAM in float32 by arithmetic [Calc]; speed unknown. The card says it doesn't support FP16 | **Test** in log-only mode only. No Telugu training, ANLI 0.537 |
| XLM-R fine-tuned on En-IndicXNLI | Best published English-premise, Telugu-hypothesis figure (72) | Fine-tuning on a CPU laptop looks impractical; I found no verified ready checkpoint | **Skip** for now |
| IndicBERT or MuRIL NLI | Lower or unstable in the mixed setting | Same | **Skip** |
| FactCG | Good for an English intermediate check: same class as GPT-4o on English | About 1.6 GB by arithmetic [Calc]; speed unknown | **Test** only if the check runs on English text before translation |
| LettuceDetect | Span output; high recall as a screen | Tiny models are small, but no Indian language is confirmed | **Skip** until Hindi or Telugu support is proven |
| Granite Guardian | Good English accuracy | 8B model; English only; heavy on a laptop | **Skip** |
| HALT-RAG-style ensemble | Validated only on an easy benchmark | Two large models | **Skip** |

- **Code fixes must not be mistaken for entailment.** Code adds the passage holding a figure, which proves the figure, not the sentence's rule. On quick and standard answers nothing checks the words.
- **False flags are the main risk.** VETRA cuts failing sentences, so a checker with high recall and low specificity would remove correct facts. Keep any NLI out of the cut path until it beats the second reader on a labelled cross-language set.
- **Expert QA at about 60% for every model** suggests specialist rule text (eligibility, exclusions) may be harder than general benchmarks imply. This is the closest published signal for scheme documents.
- **Confirms ARCHITECTURE_RESEARCH.md:** showing each statement's section (DnDScore) fits the 0.06 gain from context; showing only cited passages fits the drop on long context.

### Gaps
- I found no paper called HALOs under that name. The closest results were HALT-RAG, HalluRAG and LettuceDetect, so please check the intended source.
- No published CPU latency for any candidate. It should be measured on this laptop when tests aren't running.
- No checker has been validated in Telugu with English evidence on real RAG output.
- I did not confirm whether HaluEval is one of HaluBench's six sources.
- I did not read FactCG's result tables. It states no language scope that I saw.

## Attributed and quote-first answering: what do measured results show?

### Takeaway
Fine-grained citation methods improve traceability in their authors' tests, but API-level guarantees cover only that a pointer is real, not that it supports the claim. VETRA's code checks remain necessary, and code-checked quote-first is the one idea here worth testing.

### Cited Findings
- [M-peer/shared task] TREC 2025 RAGTIME: organizers call citation accuracy "quickly becoming a solved problem" for systems with reasonable checks, while nugget coverage remains unsolved — [overview](https://arxiv.org/html/2602.10024)
- [M-peer, abstract] FRONT trains models to select quotes first, then generate. An average 14.21% citation-quality gain on ALCE with LLaMA-2-7B — [FRONT](https://arxiv.org/abs/2408.04568)
- [M-pre, author-reported] C²-Cite reports 5.8% better citation quality and 17.4% better correctness than FRONT — [C²-Cite](https://arxiv.org/pdf/2602.00004) [Secondary, search excerpt]
- [Author-reported, abstract] ReClaim alternates reference and claim generation for sentence-level citations, with a "citation accuracy rate of 90%." I did not see its definition or independent replication — [ReClaim](https://arxiv.org/abs/2407.01796)
- [M-peer] LAQuer (ACL 2025), post-hoc localisation of a fact to source text, tested on two English sets:
  - An LLM prompt cuts attributed length by about two orders of magnitude for Vanilla and ALCE (Vanilla MDS from 1,681.6 to 32.0), and about 59% for Attr. First.
  - Automatic support drops as spans shrink: Vanilla contextualised falls from 82.2 to 62.5 on MDS.
  - A small human check (20 examples per task) gave decontextualised support of 91.5/90.9 for Vanilla whole-source attribution, 39.0/59.5 with the prompt, and 54.3/53.6 for Attr. First. The internals method was weak (18.0/19.0) and needs open weights — [LAQuer](https://arxiv.org/html/2506.01187v1)
- [M-peer] ContextCite (NeurIPS 2024) needs one model pass per ablation. It matches or beats baselines at 32 ablations, and the verification experiments used 256. It is contributive: it finds what caused a statement, not what supports it. A misread fact would still be surfaced — [ContextCite](https://arxiv.org/html/2409.00729v2)
- [Docs] Anthropic Citations: citations are "guaranteed to contain valid pointers" and `cited_text` doesn't count toward output tokens. It can't be combined with structured outputs (400 error). PDFs without extractable text can't be cited, which rules out scans. The doc gives no measured accuracy — [Anthropic docs](https://platform.claude.com/docs/en/build-with-claude/citations)
- [Docs] Gemini Google Search grounding returns start and end offsets for citations and says it can "reduce model hallucinations," with no accuracy figure. It covers public web results, not private documents, and costs $14 per 1,000 requests after a free tier on Gemini 3+ — [Google](https://aistudio.google.com/docs/google-search)
- [Docs] Gemini File Search returns citations through grounding metadata and retrieved chunks. Query-time use is free apart from regular tokens, and indexing is $0.15 per million tokens — [File Search docs](https://ai.google.dev/gemini-api/docs/generate-content/file-search); [pricing](https://ai.google.dev/gemini-api/docs/pricing) [Secondary, search excerpt]
- [Anecdote] A developer reports Vertex grounding linking citations inaccurately to specific table rows — [Google forum](https://discuss.google.dev/t/vertex-ai-gemini-w-google-grounding-inaccurate-segment-citations/251345). A third-party package note says per-chunk confidence is empty on Gemini 2.5 and later, which I did not confirm with Google — [Go package docs](https://pkg.go.dev/github.com/cloudwego/eino/schema/gemini)

### Inferences

| Candidate | Would improve in VETRA | CPU and complexity | Verdict |
|---|---|---|---|
| Quote-first plus code exact-match, for non-numeric rule sentences | Detects made-up wording that today's figure checks can't see, including on quick and standard answers | No model on CPU; more tokens; quote matching across script needs care | **Test** |
| Sentence-interleaved citations (ReClaim-style prompt) | Might reduce citation corrections code has to make | Prompt change only | **Test** after quote-first, as a cheaper variant |
| LAQuer-style prompt | Short highlight beside each fact, for the page | One LLM call per fact; support falls as spans shrink | **Skip** now. Revisit for the UI |
| ContextCite | Debugging only | 32-256 calls per attribution | **Skip** |
| FRONT or C²-Cite model training | Training not feasible here; the idea is covered by quote-first | Needs GPU training | **Skip** |
| Anthropic Citations | Reliable pointers at low token cost | Change of provider; no structured output; no scans | **Skip** as the main path. A cross-check is possible if a Claude key is added |
| Gemini grounding or File Search | Hands retrieval to Google and hides the state and in-force filters | No CPU cost, but loses control | **Skip** |

- **Overturns one point in ARCHITECTURE_RESEARCH.md:** quote-first is no longer "practitioner guides only." FRONT and LAQuer give peer-reviewed support for quote-based generation. The word-for-word code check is still untested.
- **The LAQuer human numbers warn of a trap:** a short real quote is easier to check, but it may support the sentence less often. A quote-exists check is necessary, not sufficient.
- **Scripts:** quotes from English sources can be matched exactly only before translation. For other languages, check the English draft and print the original, as VETRA already does for facts.

### Gaps
- I found no head-to-head of these methods on one dataset, and none on Indian-language or government documents.
- I found no independent accuracy measurement of Anthropic Citations or Gemini File Search.
- I did not read FRONT's or ReClaim's full tables.

## Abstention and calibration: what works without big training sets?

### Takeaway
Don't trust model self-confidence, and don't use conformal guarantees at VETRA's data size. What holds up is a separate evidence-sufficiency decision kept in code, scored with planted unanswerable questions, plus thresholds reported with exact confidence intervals.

### Cited Findings
- [M-peer] RefusalBench (EACL 2026), 176 perturbations across six uncertainty types and three intensities, 30+ model variants:
  - Best refusal accuracy is 73.0% on single documents and 47.4% on multiple documents. Claude-4-Sonnet falls from 73.0% to 36.1%.
  - Calibration is poor: refusal ECE 0.226-0.519, with over 73% of predictions at maximum confidence despite 40-69% accuracy.
  - Up to 4,096 thinking tokens added under 1 point.
  - Models can detect when to refuse but struggle with why: GPT-4o's category accuracy is 54.1%, and models over-default to "missing information."
  - Generator consensus matters: inter-verifier κ was as low as 0.061 — [RefusalBench](https://arxiv.org/html/2510.10390v1)
- [M-pre] DeclineCraft (20 October 2026), a Minecraft Wiki corpus with 27 models:
  - Single-shot RAG raised correct abstention from 17.1% to 56.4%.
  - Iterative RAG lowered it to 46.4% in mean, significantly in 30 of 40 configurations, for little accuracy gain (68.5% to 69.3%).
  - Query rewriting and reranking lowered abstention for all 12 models tested.
  - Thinking lowered abstention by 14 points on average without retrieval. Many of those became premise denials ("that doesn't exist").
  - Fine-tuning moved models along the trade-off rather than past it: Trust-Align 3B reached 89.3% abstention but attempted only 43.6% of answerable questions.
  - One domain only, with one chunking scheme and embedding — [DeclineCraft](https://arxiv.org/html/2610.28340)
- [M-peer] Sufficient Context (ICLR 2025):
  - An LLM sufficiency rater reached 93.0% accuracy on 115 labelled instances (Gemini 1.5 Pro with one example). FLAMe-24B reached 87.8%.
  - With insufficient context, Gemini 1.5 Pro abstained 50.0% and hallucinated 40.4%, against GPT-4o at 61.5% and 15.4%.
  - A small logistic regression on the sufficiency label plus self-rated confidence improved the correct fraction among responses by 2-10%. Those are older models, and the paper does not state how many examples fit the combination — [paper](https://arxiv.org/html/2411.06037)
- [M-peer, abstract] FaithEval (ICLR 2025), 4.9K problems covering unanswerable, inconsistent and counterfactual contexts: larger models aren't necessarily more faithful. I did not read per-model figures — [FaithEval](https://arxiv.org/abs/2410.03727)
- [M-pre] AbstentionBench, 20 frontier models over 20 datasets: almost no benefit from scale; reasoning fine-tuning cut abstention 24% on average; its judge was 88% accurate on a hand-checked sample. No RAG conclusions — [AbstentionBench](https://arxiv.org/html/2506.09038)
- [M-pre] A-CRC-QA (calibrated acceptance thresholds), target error 0.15 — [paper](https://arxiv.org/html/2608.12008):

  | Calibration size | Target missed (violation rate), CoQA / MedMCQA | No valid threshold at all, CoQA / MedMCQA | Answers accepted, CoQA / MedMCQA |
  |---|---|---|---|
  | 100 | 26% / 20% | 8% / 5% | 30.8% / 42.1% |
  | 500 | 17% / 12% | 1% / 0% | 41.8% / 54.3% |
  | 1,000 | 13% / 8% | 0% / 0% | 46.2% / 58.7% |

  Its authors say the guarantee is asymptotic and not finite-sample. At a stricter 0.05 target, infeasibility rises to 16% and 22%, and I did not confirm the calibration size for those two figures.
- [M-peer, abstract] Conformal abstention needs multiple sampled responses plus calibration to bound error, tested on closed-book QA — [Abbasi Yadkori et al.](https://arxiv.org/abs/2405.01563)
- [Secondary] Conformal guarantees rest on calibration and test data being exchangeable, so shift between states or document types weakens them — [overview](https://www.emergentmind.com/topics/conformal-abstention). An open-source RAG project notes that 16 unanswerable questions give quantile steps of about 6%, far too coarse — [issue](https://github.com/keylorpineda/RAG-Research-Engine/issues/62)
- [M-pre] Entropy Alone is Insufficient: semantic entropy has a "risk floor" and a confidently wrong regime. On Ministral 8B/BioASQ it can't reach error ≤ 0.15 at useful coverage. Adding a correctness probe helps unevenly, requires labelled data, and needs repeated sampling for SE — [paper](https://arxiv.org/html/2603.21172)
- [M-pre, author-reported, vendor-affiliated] Why RAGs Hallucinate: three RAG systems were 97.0-98.0% accurate when answering, but violated knowledge-gap canaries at 16.7%, 22.2% and 98.1% — [paper](https://arxiv.org/html/2608.26385)
- [Secondary, excerpt] An audit reports 57.2% of model refusals cite a reason that fails at least one test — [Cited but Not Causal, EMNLP 2026](https://aclanthology.org/2026.emnlp-main.645/). LIT-RAGBench reports over-abstention even when a valid answer is possible — [LIT-RAGBench](https://arxiv.org/pdf/2603.06198)

### Inferences

| Candidate | Would improve in VETRA | CPU cost | Verdict |
|---|---|---|---|
| Code-listed gaps kept as the source of "what isn't held" (already built) | Avoids relying on poorly calibrated, reason-confused model refusal | None | **Keep**. The evidence supports it |
| Canary questions per state and topic | Direct measure of admitting what isn't held | None; some Gemini calls | **Adopt now** |
| Measure abstention at each loop round | DeclineCraft warns that more search lowers abstention, and VETRA's loop searches more | Eval calls only | **Adopt now**: compare deep with 0 extra rounds against normal |
| Separate sufficiency judgement per plan part, before writing | Stops the writer guessing; a clean refusal signal | One short Gemini call per part | **Test** on about 150 labelled cases |
| Thresholds on retrieval scores | Cheap, and already used off-topic | None | **Test**, per language and per state, reported with intervals; no published support found |
| Two-feature logistic regression | Combines sufficiency with a retrieval score | Trivial on CPU; 100-200 labels; overfits if more features are added | **Test** after the set exists |
| Conformal or A-CRC-QA | Formal error control | Trivial on CPU, but data-hungry | **Skip** until there are more than 500 labelled answers per setting; states and languages are unlikely to be exchangeable |
| Semantic entropy or conformal abstention by sampling | Adds cost per answer, and figures are already printed by code | Multiple Gemini calls per answer | **Skip** |

- **Show only code-derived gaps to the user.** RefusalBench and the EMNLP 2026 audit both suggest a model's stated reason for a gap is unreliable. VETRA's "not found in documents held" is safer than a model's explanation.
- **Report the premise-denial error separately.** "That scheme doesn't exist" is worse than "I don't hold that." DeclineCraft's split fits a citizen setting well.
- **The multi-document drop matters:** VETRA's deep answers read many passages, so test refusal with mixed evidence as well as with empty retrieval.
- **Thresholds at this data size:** 0 false alarms in 84 tests still allows a true rate up to about 4.3% (exact 95%), and 80 of 93 has a Wilson interval of 77.5-91.6% [Calc]. Publish the interval next to the score.

### Gaps
- I could not find an abstention paper called "Reasons to Reject." From memory, a paper with a similar title is about learning from language feedback rather than RAG refusal, but I did not verify this. Please confirm the intended source.
- I found no measured study of retrieval-score thresholds alone as an abstention signal in RAG, and nothing on abstention in Indian languages.
- FinAbstain ([arXiv](https://arxiv.org/pdf/2607.24875)) was not readable, and I did not read the COIN or LEC papers directly.

## Numeric and table faithfulness: what supports separating computation from generation?

### Takeaway
Direct evidence for "the writer never sees exact figures" doesn't exist as far as I could find, but neighbouring results point the same way. VETRA's design is well supported by inference, and FAITH suggests one concrete addition: check units and scale, not only digits.

### Cited Findings
- [M-peer] Program of Thoughts: having a program do the arithmetic gave about a 12% average gain over chain-of-thought on math and finance sets (FinQA, ConvFinQA, TATQA) — [PoT](https://arxiv.org/abs/2211.12588)
- [M-peer] FAITH (ICAIF 2025), masked figures in S&P 500 annual reports, 2,406 spans in the main split. Overall accuracy varied widely:
  - Claude-sonnet-4: 95.6. Gemini-2.5-pro: 91.9. Gemini-2.5-flash: 88.7. Gemini-2.5-flash-lite: 50.2. Qwen-3-8B: 30.6. Gemma-3-12B: 15.2.
  - Direct lookup is easier than calculation for most models.
  - Scale errors (right number, wrong magnitude) are a major error type. Fixing them alone would lift Llama-3.3-70B's value accuracy from 37.0% to 57.7%.
  - Even strong models ignored a table row in a case study — [FAITH](https://arxiv.org/html/2508.05201)
- [Secondary, conflicting] Google's DataGemma, with Data Commons: reports differ on what the numbers measure. RIG is described as raising factuality from 5-17% to about 58%, or as being correct 58% of the time when it retrieved anything, with 75% of cases finding nothing. RAG is reported at 99% numerical accuracy with 6-20% inference errors, or 80-94% correct. I could only read the abstract of the primary paper, which gives no figures — [abstract](https://arxiv.org/abs/2409.13741); [the-decoder](https://the-decoder.com/googles-datagemma-aims-to-ground-language-models-in-reality-and-curb-ai-hallucinations/); [SiliconANGLE](https://siliconangle.com/2024/09/13/google-debuts-new-accuracy-optimized-datagemma-llm-series/)
- [M-repo] A number rule was kept after McNemar tests in the local stack above — [local-groundedness-check](https://github.com/NortonDesignLab/local-groundedness-check)
- [M-pre, abstract] Numeric fact-checking stays hard for models: QuanTemp's 58.32 macro-F1 — [QuanTemp](https://arxiv.org/abs/2403.17169)

### Inferences

| Candidate | Would improve in VETRA | CPU cost | Verdict |
|---|---|---|---|
| Code prints figures; writer doesn't see them (already built) | Removes the model's chance to corrupt a value, and lets weaker, cheaper models write | None | **Keep** |
| Extend code checks to unit and scale, including lakh and crore, per-acre vs per-hectare, Indian-script digits, and rupee-word forms | FAITH's most fixable error type; Indian formats are a known risk here (Rs.6000/- read as Rs.60001) | None; rules plus tests | **Adopt now** |
| Check period and entity attached to each figure | Right number, wrong crop, year or state passes a figure-only check | None or small | **Adopt now** for crop and year, where structured records exist |
| Any calculated value computed by code from records | PoT-style: no arithmetic in the model | None | **Adopt now** where the answer would otherwise contain a sum or difference |
| Table reader evaluation | Prose claims about tables remain a risk | Eval only | **Test** with FAITH-style masking on VETRA's own records |

- **Cheap writer models:** FAITH shows large gaps between Gemini tiers (Flash-Lite at 50.2 vs 2.5-Pro at 91.9). Any route that lets a cheap model handle figures needs code checks, which supports keeping the code-printed design if the writer model changes.
- **What code-printing can't do:** it can't stop a correct figure being attached to a wrong condition in the prose. That stays with the second reader.

### Gaps
- I found no controlled study comparing writers that see figures with those that get code-printed figures.
- FAITH is English finance only, and I found no numeric-hallucination study in Indian languages. The FAITH table was garbled in the source, and columns were inferred by the summariser, so re-open it before quoting. Main-split scenario counts also don't add up in the paper (2,386 vs 2,406).

## Multi-language faithfulness: do checkers degrade with a Telugu answer and English evidence?

### Takeaway
For NLI models, yes: mixed-language input scores worse than same-language input. Low-resource Indian languages also score lower in shared tasks, and fluent text is a poor sign of factual accuracy. No study measures an LLM reader on Telugu answers against English evidence, so VETRA must measure it itself, and it should run checks on the English side wherever it can.

### Cited Findings
- [M-peer] Mu-SHROOM (SemEval-2025), 14 languages, Hindi the only Indian one, 43 teams, 2,618 submissions:
  - Hindi ranked 2nd of 14 by mean IoU (0.50, mean ρ 0.52). The top Hindi team reached IoU 0.74, ρ 0.78.
  - 52.60% of submissions used retrieval and scored statistically higher; those relying mainly on the provided data scored lower.
  - The fine-tuned XLM-R token baseline, without fact verification, ranked extremely low.
  - Organisers say rank differences generally aren't statistically significant. Mu-SHROOM tests answers without supplied source documents — [overview](https://arxiv.org/abs/2504.11975)
- [M-peer] SHROOM-CAP (CHOMPS 2025), scientific text, with Bengali, Gujarati, Malayalam and Telugu as unseen languages. Factuality macro-F1:
  - Top scores: en 0.92, hi 0.84, te 0.72, bn 0.69, ml 0.65, gu 0.64.
  - Means: en 0.59, hi 0.50, te 0.51, ml 0.50, gu 0.47, bn 0.37.
  - High-vs-low-resource difference: U test p < 0.001, r = 0.431.
  - In low-resource languages, models "often generate fluent yet factually inconsistent outputs." Only two teams competed in each low-resource language during the test phase, so these are thin results — [SHROOM-CAP](https://aclanthology.org/2025.chomps-main.7.pdf)
- [M-peer] MEMERAG, same-language: faithfulness agreement in Hindi Gwet's AC1 0.89, Fleiss κ 0.70. With guidelines plus chain-of-thought, the four-model average was HI 72.44 against EN 63.42, so Hindi was not worse for same-language judging. Evaluators weren't tested across languages — [MEMERAG](https://arxiv.org/html/2502.17163)
- [M-peer, older] IndicXNLI: mixed-language lower than same-language (figures above) — [IndicXNLI](https://arxiv.org/html/2204.08776)
- [M-repo, exploratory] Hindi direct 42.94% vs translated 28.22% on a skewed 163-item set — [Kharat repo](https://github.com/Onkar-Kharat/research-crosslingual-rag)
- [M-peer, abstract] mFACT moves English faithfulness metrics to other languages by translation-based transfer, and its authors report it detects hallucinations better than alternatives — [mFACT](https://arxiv.org/abs/2305.13632). A search excerpt adds that NLI classifiers don't match those trained directly on faithfulness data [Secondary]
- [M-peer/shared task] TREC RAGTIME 2025 covers Arabic, Chinese, English and Russian only, without per-language analysis in the overview — [overview](https://arxiv.org/html/2602.10024)

### Inferences

| Candidate | Would improve in VETRA | CPU cost | Verdict |
|---|---|---|---|
| Check the English draft against English evidence, then guard the translation step separately | Puts the check where checkers are strongest and passages can be matched exactly | None; a pipeline order question | **Adopt now** if not already done for all checks |
| Hand-read cross-language gold set: Telugu and Hindi first, then 1-2 lower-resource languages | The only way to answer this for VETRA | Reading time | **Adopt now** |
| Translation check by back-translation or an LLM comparing English and target sentence | Catches meaning changes in translation that a digit check misses; "not" or "only" flipped | One Gemini call per answer | **Test**; unmeasured here and I found no study on it |
| mFACT-style trained metric | Needs labelled data per language | Too heavy for now | **Skip** |

- **Telugu has an advantage in VETRA:** facts print from templates, so the risk is prose. For the other 21 scheduled languages, models translate facts, and only digits are verified. Words like "not eligible" or "up to" could flip without any check.
- **Fluent answers can mislead human readers too.** A reader in the gold set must compare with the English original, not judge the Telugu by how it reads.
- **Report by language,** with intervals. One blended score would hide weak languages.

### Gaps
- I found no measurement of LLM readers on Indian-language answers with English evidence.
- Coverage of Indian languages other than Hindi is thin: 2 teams per language in SHROOM-CAP, and nothing found for languages with little NLP data, such as Bodo, Santali and Dogri.

## Evaluation tools, LLM-judge flaws, and how many questions a test needs

### Takeaway
No framework's automatic score should decide a change. A hand-read set of about 150-200 paired questions can settle mid-sized differences, 20 can only catch large ones, and an LLM judge should be validated against that set before it is used at scale.

### Cited Findings

**Framework reliability**
- [M-peer, framework authors] RAGChecker (NeurIPS 2024), 280 human-labelled instances, two annotators each. Correlation (Pearson) of each framework's best metric with human overall assessment: RAGChecker 61.93, RAGAS Answer Similarity 48.31, CRUD-RAG 41.25, TruLens Answer Relevance 35.15, ARES Answer Relevance 17.81. Human-to-human upper bound 70.09 — [RAGChecker](https://arxiv.org/html/2408.08067)
- [M-peer, abstract] ARES trains light judges on synthetic data and uses prediction-powered inference with "a few hundred" human annotations — [ARES](https://arxiv.org/abs/2311.09476)
- [Secondary, unverified] RAGAS reports 0.95 agreement on faithfulness on WikiEval, from a blog — [Modulai](https://modulai.io/blog/evaluating-rag-systems-with-synthetic-data-and-llm-judge). A vendor blog claims 83.5% null results for RAGAS faithfulness on financial QA, and that ARES fell to rank correlation 0.33 on other languages. I could not confirm either — [Kili](https://kili-technology.com/blog/rag-evaluation-guide-measuring-retrieval-and-generation-as-separate-problems)
- [Docs] DeepEval offers a one-shot LLM abstention classifier — [DeepEval docs](https://deepeval.com/docs/classifiers-abstention). I found no independent reliability study for DeepEval.
- [Vendor] Cleanlab has benchmarks comparing RAGAS and DeepEval with its own model — [blog](https://cleanlab.ai/blog/rag-tlm-hallucination-benchmarking/). I didn't read the numbers because the paper's HTML wasn't available, and a vendor's comparison needs independent confirmation.

**LLM judges compared with humans**
- [M-peer] TREC 2024 RAG support judging (45 runs, 36 topics): GPT-4o matched humans 56% from scratch and 72% with post-editing. An independent human correlated better with GPT-4o than with the human judge — [Thakur et al.](https://arxiv.org/abs/2504.15205)
- [M-peer/shared task] RAGTIME 2025: an LLM judge scored precision 0.815 and recall 0.814 on 1,000 balanced pairs and was "very strict" on grounding — [overview](https://arxiv.org/html/2602.10024)
- [M-pre] Trivia++: LLM-labelled test sets inflate scores: F1 0.929 on LLM labels vs 0.692 on clean labels for the same method. Human annotators were about 77% accurate individually (Fleiss κ 0.46), so up to 6 votes per sample were used — [Trivia++](https://arxiv.org/html/2605.11330)
- [M-pre] Deep Research, Shallow Evaluation: LLM judges track human preference at system level (Kendall τ-b 0.40, or 0.60 on expert-agreed items), but only 0.25-0.36 per instance. Agreement on individual metrics is low, with citation precision 42.3-59.0%. Experts agreed on only about half of instances — [paper](https://arxiv.org/html/2603.06942)
- [M-pre] DeclineCraft: a response judge matched the human majority on 96% of labels. On accuracy, judge-human κ was 0.66 vs 0.42 between humans. Two judges showed small self-preference — [DeclineCraft](https://arxiv.org/html/2610.28340)
- [M-peer, reported by authors] CRAG-MM uses GPT-4o as a judge with 99.1% reported accuracy — [CRAG-MM](https://arxiv.org/pdf/2510.26160) [Secondary, search excerpt]

**Statistics**
- [M-peer, abstract] NLP comparisons are often underpowered: even 2,000-sentence MT test sets had about 75% power for 1 BLEU point — [Card et al.](https://aclanthology.org/2020.emnlp-main.745/)
- [M-peer, abstract] Significance tests are often ignored or misused in NLP; the paper offers a protocol for test choice — [Dror et al.](https://aclanthology.org/P18-1128/)
- [Calc] Exact two-sided McNemar test at p < 0.05. Only questions where exactly one system is right count (discordant pairs):

  | Discordant pairs | Split needed |
  |---|---|
  | 5 | Impossible (5-0 gives p = 0.0625) |
  | 6 | 6-0 |
  | 10 | 9-1 |
  | 20 | 15-5 |
  | 30 | 21-9 |
  | 50 | 33-17 |

- [Calc] Power of that test. "A wins / B wins" is the share of questions where only that system is right:

  | A wins / B wins | N=20 | N=50 | N=100 | N=150 | N=200 | N=300 | N=400 |
  |---|---|---|---|---|---|---|---|
  | 10% / 0% | 1% | 38% | 94% | 100% | 100% | 100% | 100% |
  | 20% / 5% | 10% | 48% | 84% | 96% | 99% | 100% | 100% |
  | 15% / 5% | 3% | 24% | 54% | 75% | 88% | 97% | 100% |
  | 10% / 2% | 1% | 20% | 56% | 79% | 91% | 98% | 100% |
  | 5% / 1% | 0% | 3% | 20% | 40% | 56% | 79% | 90% |
  | 10% / 5% | 1% | 7% | 18% | 28% | 37% | 56% | 70% |

- [Calc] Wilson 95% intervals at 90% observed: 18 of 20 gives 70-97%; 45 of 50 gives 79-96%; 90 of 100 gives 83-95%; 135 of 150 gives 84-94%. For VETRA's own: 80 of 93 gives 77.5-91.6%, 55 of 59 gives 83.8-97.3%.

### Inferences

| Candidate | Would improve in VETRA | CPU cost | Verdict |
|---|---|---|---|
| Own hand-read gold set with McNemar on paired pass/fail | Trustworthy decisions, replacing generous text-matching | stdlib; reading time | **Adopt now** |
| Own LLM judge (a different model family to the writer), validated on gold before use; report agreement with humans | Scale between hand readings | API only | **Test** after gold exists; AG+COT prompt |
| RAGChecker claim-level metric design | Useful ideas for correctness and completeness | Needs extractor and checker LLM calls | **Test** the idea, not the library |
| RAGAS, DeepEval, TruLens as scorers | Convenience; no support for Indian languages found | Light on CPU; LLM calls | **Skip** as decision makers. DeepEval's classifier is optional for a quick look |
| ARES or prediction-powered inference | Combines a few hundred labels with automatic scores | Light | **Skip** now; revisit once more than 200 labels exist |
| TREC-style tracks | Method only: nuggets and support; no VETRA languages | None | Copy the method; **Skip** participation |
| CRAG-MM | Multi-modal; wrong domain. Its scoring idea is covered below | None | **Skip** |

**Suggested gold set (my judgement, based on the above):**
- **Size:** 150-200 paired questions for decisions, plus 20-30 as a quick smoke test. Stratify by topic, state, depth, language and answerable or not.
- **Readers:** two readers on about 20% of items; report Gwet's AC1 and κ, since κ misbehaves on skewed labels (MEMERAG shows the gap between them). A third reader resolves disagreements.
- **Labels:** per question, plus critical and minor errors. Sentences within an answer aren't independent, so bootstrap by question, never by sentence.
- **Stats:** McNemar for pass/fail, a paired bootstrap for scores such as coverage. Correct for many comparisons, or pick one primary metric per change.
- **Holdout:** freeze about a third, unseen by anyone tuning prompts.

**Revision to ARCHITECTURE_RESEARCH.md (idea 4):** "about 20 real questions" stands only as a smoke test. At 20 pairs a 20% vs 5% difference has about 10% power [Calc], so don't conclude a change is equal or better from 20. Anthropic's point that small samples show *large* effects still holds. **"Judge different from writer" (technique 5) is confirmed:** self-preference is reported in DeclineCraft and flagged in the penalty-aware study and MEMERAG.

**The head-to-head result fits published findings:** Trivia++'s inflation from automatic labels mirrors what the text-matching scorer did here.

### Gaps
- I found no independent 2025-2026 reliability study of RAGAS faithfulness, DeepEval or TruLens against human labels on Indian languages.
- The RAGChecker table lists best metrics by framework, so it doesn't isolate RAGAS faithfulness. Its authors also evaluated their own framework.
- The power figures assume independent questions with fixed rates. They're planning numbers, not properties of VETRA's data.
- TREC 2025 RAG track overview not read; only RAGTIME was.

## Scoring refusals fairly, and scoring research depth and completeness

### Takeaway
Score each answer as correct, wrong, correct refusal or needless refusal, with a wrong figure costing several times a right answer. Score depth with a per-question checklist written before reading the answers, counting an item only if it is both present and supported.

### Cited Findings

**Refusals**
- [M-peer] CRAG scoring: perfect +1, acceptable +0.5, missing 0, incorrect −1. The automatic form is truthfulness = accuracy − hallucination — [CRAG](https://arxiv.org/html/2406.04744v2). Reported: <=34% LLM-only accuracy; 44% for plain RAG; industry RAG answers 63% without hallucination — [abstract](https://arxiv.org/abs/2406.04744)
- [Secondary, excerpt] CRAG-MM: +1, 0, −1 — [CRAG-MM](https://arxiv.org/pdf/2510.26160)
- [M-pre, vendor-affiliated authors] Why RAGs Hallucinate, on 1,000 SimpleQA-Verified questions with 3 repeats. Score is +1 correct, −4 wrong, 0 abstain, so answering pays only at ≥ 80% confidence. Plain accuracy and net score rank systems differently: Gemini RAG had the best accuracy (0.968) but a net score (+0.793) below OpenAI RAG (+0.862, accuracy 0.948). Canaries: 18 unanswerable questions, 54 trials per system; any answer counts as a violation, even a correct one. Judge: three model families, majority vote. The authors work at a vendor they evaluated — [paper](https://arxiv.org/html/2608.26385)
- [M-pre, abstract] OpenAI's 2025 paper: binary grading rewards guessing; it recommends changing benchmark scoring rather than adding new hallucination tests — [Kalai et al.](https://arxiv.org/abs/2509.04664)
- [M-pre] DeclineCraft reports correct abstention, answerable-attempt rate and accuracy together, and excludes premise denial from correct abstention — [DeclineCraft](https://arxiv.org/html/2610.28340)
- [M-peer] RefusalBench builds unanswerable items from six types with three intensities, needing multi-verifier consensus — [RefusalBench](https://arxiv.org/html/2510.10390v1)

**Depth and completeness**
- [M-peer, abstract] AutoNuggetizer: automatic nugget evaluation correlated strongly with mostly manual evaluation on 21 topics and 45 runs, with no coefficient in the abstract — [paper](https://arxiv.org/abs/2411.09607)
- [M-peer/shared task] RAGTIME 2025: a nugget counts as covered only if its sentence is also grounded in its citations. About 16.0 nugget questions per request. Best human nugget coverage on short topics was 0.227 — [overview](https://arxiv.org/html/2602.10024)
- [Secondary, excerpts] ResearcherBench: 65 expert questions, 931 weighted binary criteria (weights 1-3); the coverage score is the weighted share met. DeepScholar-Bench: best systems often below 0.40 nugget coverage; its nugget importance labels agreed 72% with humans and its entailment labels 80% — [DeepScholar-Bench](https://arxiv.org/html/2508.20033v1/)
- [Secondary, unverified] DeepResearch Bench citation-accuracy figures of 90.24% and 32.94% — [DeepResearch Bench](https://arxiv.org/html/2506.11763v1)
- [M-pre] Pairwise human preference works at system level only. For each metric, use annotation that mirrors the judge's instructions; use true domain experts for expert-level qualities — [Deep Research, Shallow Evaluation](https://arxiv.org/html/2603.06942)
- [M-peer] FaithJudge notes extractive or copy-heavy outputs trivially avoid hallucination — [FaithJudge](https://arxiv.org/html/2505.04847v2). Faithfulness alone therefore rewards saying little.

### Inferences

| Candidate | Would improve in VETRA | Cost | Verdict |
|---|---|---|---|
| Four-way outcome table, plus a penalty score | Stops a change that adds guesses looking like a win | stdlib | **Adopt now** |
| Stricter penalty for figures, dates and eligibility | Matches real harm to a farmer | stdlib | **Adopt now** |
| Per-question fact checklist, written from the documents before reading answers | Makes "depth" testable; catches over-cutting by the sentence checker | Reading time; no model on CPU | **Adopt now** for deep questions |
| RAGTIME's rule: covered only if present and supported | Stops credit for unsupported coverage | None | **Adopt now** |
| Automatic nuggetizer | Scale later | LLM calls | **Test** after hand checklists exist |

- **Penalty values (my suggestion):** the break-even confidence for penalty *k* is k/(k+1) [Calc]. −4 means 80%, and −9 means 90%. Use −9 for a wrong figure, date or eligibility rule, and −4 for other wrong statements. A needless refusal is 0, but report its rate alongside: a system that refuses everything would otherwise look safe. Report the score only with the raw counts.
- **Checklist weights:** 3 for what changes a person's action (amount, deadline, eligibility, documents needed); 2 for procedure; 1 for background.
- **Watch the cut path:** deep-answer coverage should be measured before and after sentence cuts, as cuts raise precision while lowering coverage.
- **Confirms ARCHITECTURE_RESEARCH.md technique 4** with direct reading of the abstract. The formula itself comes from other sources, since the abstract gives none.

### Gaps
- I could not confirm the DeepResearch Bench or ResearcherBench figures from the primary tables.
- No refusal or depth score has been studied for citizen-advice questions in Indian languages. These weights are my own judgement and need sign-off by someone who knows the farmers' side.

## Observability: what is the lightest setup for a hand-written loop?

### Takeaway
Nothing here justifies replacing JSON traces today. Make them append-only, versioned and queryable, using OpenTelemetry-like names where cheap, and try Phoenix only when someone needs to browse traces. I found no study measuring whether any of these tools actually improves outcomes.

### Cited Findings
- [Docs] OTel GenAI conventions now live in their own repo, with "Status: Development," covering inference, embeddings, retrieval, events, metrics, model spans and agent spans — [README](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/README.md). The old page says it has moved — [OTel docs](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
- [Secondary] Guides mention setting `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` for the newest attributes — [guide](https://dev.to/gabrielanhaia/opentelemetry-genai-semantic-conventions-your-llm-traces-should-look-like-this-in-2026-3ff6)
- [Docs] Langfuse self-hosting needs Web, Worker, PostgreSQL, ClickHouse, Redis or Valkey, and S3-style storage — [self-hosting](https://langfuse.com/self-hosting). For a VM its guide says "at least 4 cores and 16 GiB of memory," and calls Compose the way "to give it a try," lacking high availability, scaling and backup — [Docker Compose guide](https://langfuse.com/self-hosting/deployment/docker-compose)
- [Docs] Phoenix: `pip install arize-phoenix`, `phoenix serve`; Elastic License 2.0. Telemetry is on by default, off with `PHOENIX_TELEMETRY_ENABLED=false` — [repo](https://github.com/Arize-ai/phoenix). SQLite is the default for single-user use, with no setup; PostgreSQL for production — [architecture](https://arize.com/docs/phoenix/self-hosting/architecture). I found no stated CPU or memory needs.
- [Secondary] ELv2 restricts offering Phoenix as a managed service — [comparison](https://vdf.ai/blog/llm-observability-tools/)

### Inferences

| Candidate | Would improve in VETRA | CPU cost | Verdict |
|---|---|---|---|
| JSONL traces, one line per answer, schema version, with fields below | Cheap regression comparison, diffs and failure-to-test | None | **Adopt now** |
| Query traces with SQLite or DuckDB | "Which answers cut most sentences this week?" | Trivial | **Adopt now** if the need arises |
| Phoenix on demand (`phoenix serve`, SQLite) | Clickable trace view for a reviewer | One local process; memory unmeasured; turn telemetry off | **Test** when someone other than the author reviews traces |
| OTel spans with `gen_ai.*` names | Portability later | Small code cost; names can still change | **Test** names in JSON only; **Skip** a full SDK and collector |
| Langfuse self-hosted | Strong team tooling | Six services and a 16 GiB guide on a laptop that also runs tests | **Skip** |
| Hosted tracing | Would send citizen questions to a third party | None locally; privacy review needed | **Skip** |

**Fields worth recording per trace:**
- Trace ID and schema version.
- Git commit, prompt hash and model ID.
- Plan and language.
- Each retrieved passage's ID, score and document hash.
- Judge moves (already in `trace["route"]`).
- Each sentence's check result, with reason code.
- Any citation change code made.
- Second reader verdicts and whether it ran (`trace["verified"]`), any rewrite, and cuts.
- "Today" as used, plus tokens and latency per call.

Keep user questions out of any log leaving the machine, as they may contain personal details.

### Gaps
- No measured comparison of tracing tools exists in the sources I found, and most comparisons are vendor-adjacent blogs.
- I could not read versions from the OTel repo's front page. Phoenix's memory use and whether it's comfortable on this laptop were not checked, and shouldn't be until tests finish.

## Regression, drift, and catching stale answers as documents change

### Takeaway
Old documents can override correct knowledge, and telling the model explicitly when a rule stops applying is the best-supported fix. So store validity dates with evidence, show them to the writer, enforce them in code, and re-run only the test questions whose documents changed.

### Cited Findings
- [M-pre] Stale-Document Poisoning (September 2026), 317 dated reversals in medicine, law, software and platform policy:
  - Old retrieved text flipped 30% of Llama and 37% of Qwen answers, and 66% and 75% when told to trust the document. Across four open models and four domains the range was 17-91%. Matched current evidence was followed in 97-100% of trials.
  - Telling models when the old evidence stops applying made larger models switch almost perfectly.
  - A recency-aware reranker cut poisoning by only 4.6-10.0 points, and depends on accurate dates.
  - Changing only the evaluation date produced modest adaptation in 50 reversals. So "today" alone doesn't do it — [paper](https://arxiv.org/abs/2609.31342)
- [M-peer, abstract] HoH (ACL 2025): outdated evidence lowers accuracy and can steer answers towards harm, even when current information is also available. Uses token-level diffs plus LLM pipelines to capture changes — [HoH](https://aclanthology.org/2025.acl-long.301/). A search excerpt reports models doing about 2.77% worse than random guessing with outdated evidence, which I did not check in the tables [Secondary] — [PDF](https://aclanthology.org/2025.acl-long.301.pdf)
- [M-pre, own benchmark] VersionRAG: 90% vs 58% for naive RAG and 64% for GraphRAG on 100 questions over 34 versioned technical documents; 60% on implicit change detection, where baselines were 0-10%. A review says the headline used DeepSeek-R1 70B — [VersionRAG](https://arxiv.org/html/2510.08109); [review](https://www.themoonlight.io/en/review/versionrag-version-aware-retrieval-augmented-generation-for-evolving-documents)
- [Secondary, practitioner] Time-sliced evaluation, Contradiction@K and staleness penalties have been suggested — [Medium](https://medium.com/@Nexumo_/the-8-retrieval-benchmarks-lying-to-your-rag-5811ca3ee057). Frozen snapshot benchmarks hide temporal issues — [survey](https://arxiv.org/pdf/2407.13193)
- [M-peer, abstract] FaithEval includes inconsistent contexts, which models handle poorly, relevant when old and new orders are both retrieved — [FaithEval](https://arxiv.org/abs/2410.03727)

### Inferences

| Candidate | Would improve in VETRA | CPU cost | Verdict |
|---|---|---|---|
| Evidence fields: `valid_from`, `valid_until` (or "until replaced"), `superseded_by`, `issued_on`, `source_hash`, `last_checked` | Makes in-force decisions explicit; builds on `links.jsonl` amendment links and the existing in-force check | None | **Adopt now** |
| Show validity to the writer as data ("this order was replaced on...") and print the period by code | Best-measured fix; matches Deep answers stating periods | None | **Adopt now** |
| Code check: no expired evidence can be cited without a label; "today" is injected | Prevents wrong-period answers even if retrieval misfires | None | **Adopt now** |
| Date-frozen golden tests: each test pins a "today," plus one test just before and one after each rule change | Catches season and deadline bugs; repeatable | stdlib | **Adopt now** |
| Selective re-run: when a document's hash changes, re-run tests citing it, then diff figures and citations | Keeps API cost down as states are added | Trivial | **Adopt now** |
| Answer cache key includes evidence hashes and an expiry equal to the earliest `valid_until` | Makes the cache idea in ARCHITECTURE_RESEARCH.md safe | Trivial | **Adopt** with the cache |
| Scheduled checks: official source changed? (hash or HTTP headers), plus an "unchecked for N days" flag per topic | Catches new government orders not yet ingested; old evidence can look valid | Light script | **Test**; intervals per kind of data: seasonal rates, weekly mandi prices if added |
| Recency-boost reranker | Small measured gain and dependent on dates | Small | **Test** later; rules first |
| Contradiction check when old and new both retrieved | A new-vs-old conflict should be named or resolved by code | Rules; maybe one LLM call | **Test** |
| Full drift-monitoring tool | Few users so far; nothing to monitor at scale | Not needed | **Skip** |

- **Confirms ARCHITECTURE_RESEARCH.md technique 6** (pin down the period) and the "Deep answers state each rule's period" adoption. It also warns that answer caching (technique 7) needs the cache key above.
- **Tell the reader, too:** a "valid as of" and "last checked" line beside each fact lets a farmer see if it may be out of date, and the same line helps reviewers.
- **Unknown end dates are the hard case:** many orders have no end date and are replaced silently. Treat "until replaced" plus a stale `last_checked` as a warning rather than as in force.
- **Regression rule for the test suite:** every bad answer found by reading becomes a test (technique 5), and each scored run stores its traces so diffs can be read.

### Gaps
- Stale-Document Poisoning is a new preprint, and I read only the abstract. Results come from open models, not Gemini, and from other domains.
- I found no study on government-scheme documents or Indian orders, nor a measured best re-check interval. These intervals need the project's own experience.
- Whether official Indian portals expose reliable dates or stable URLs wasn't examined.
