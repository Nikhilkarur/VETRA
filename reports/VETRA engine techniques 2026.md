# Fix VETRA's dates and tests before models

VETRA doesn't need a new design or another model swap right now. The biggest gains left are in three places: telling old rules from current ones, proving changes with a bigger hand-checked test, and reading figures correctly from scanned documents. Almost all of this is cheap on your CPU, because the work is code, data and reading rather than heavy models.

## What to do first

1. **Build a proper test.** About 150 to 200 hand-checked questions, including ones VETRA can't answer. The E5 result shows why: today's sets are too small to prove anything.
2. **Give every rule start and end dates.** No record has an end date today, so code can't retire a replaced order by date, and old rules are the best-measured way these systems go wrong.
3. **Check units as well as digits.** Catch lakh against crore and per acre against per hectare. It's cheap and aimed at a known error type.
4. **Teach the second reader with examples.** Add written rules and your own past failures to its prompt. This is the cheapest measured gain in checking, and it needs no new model.
5. **Test turning off the English reranker for Indian-language text.** It's an English-trained model scoring Marathi and other Indian-script passages. The test should take very little effort.
6. **Test writing in English first, then translating.** Today the second reader checks Hindi or Telugu answers against English evidence, and nobody has measured how well that works.
7. **Read scans with Gemini, and double-check every number with Tesseract.** No figure should enter the exact-facts store on one read.
8. **Add a line to each chunk naming its state, scheme, order and date, and split chunks at numbered paragraphs.** Do both in one rebuild, because each rebuild now takes about 39 minutes.
9. **Before any public link, add the safety gates.** Block buy-or-sell advice, dose calculations and guesses about personal payment status, and add a crisis reply. Also stop the page implying it's an official government service.
10. **Try hosted Gemini embeddings before the document set grows.** E5-base stays the default, but rebuilding at 100 times today's size would take about 65 hours on this laptop.

**Don't spend time on:** graph systems, ColBERT, agent frameworks, a similarity-based answer cache, running a big reranker here, or training any model.

## Where the engine stands today

**E5-base is now the default search model** (`vetra/text_index.py`). That was the owner's decision and it has been applied. BGE-M3's local test was stopped because it was too slow here. The measurements below were taken on this machine. The ranges are 95% Wilson intervals, by my arithmetic.

| Test | E5-base | bge-small | Plain reading |
|---|---|---|---|
| Marathi documents, English and Marathi queries | 12/20 (39-78%) | 9/20 (26-66%) | Better, not proven |
| AP questions | 82/93 (80-93%) | 80/93 (78-92%) | About level |
| Parts of deep questions | 53/59 (80-95%) | 55/59 (84-97%) | Slightly worse, not proven |
| Time for a deep question | About 5.2s | About 3.9s | About a third slower |
| Indexing on CPU | 38.9 minutes | | About 1.6 chunks a second over 3,710 chunks |

None of these gaps can be proven on these sets. On an exact paired test, a gap of 2 or 3 questions can't reach significance however the questions split, by my arithmetic. The switch is a sensible practical choice, not a proven upgrade. Published tests also place e5-base behind BGE-M3 and e5-large: mean MRR over 13 languages is .441 against .484 and .483 ([IndicRAGSuite](https://arxiv.org/pdf/2506.01615)). On English queries over Hindi documents it scores 20.81 against 34.40 and 35.00 ([Hindi-BEIR](https://arxiv.org/html/2409.05401v3)). Those aren't VETRA's documents, and yours is the only test that is, so they're a reason to keep testing rather than to reverse the decision.

**Several fixes the notes asked for are already in the working copy.** I read these in the code, uncommitted, and did not run the engine. Keyword search now normalises text, ignores invisible joiners, treats every script's digits alike and reads Meitei Mayek. I confirmed this by running the same rules on sample strings. The planner now sees earlier questions only, history is masked, cached and thinking tokens are logged, and a rule is kept when the question names any year inside its period. The prefix worry from the notes is also closed: the agent uses E5's prefixes, and the hardcoded BGE prefix in `rag/` only serves `rag/`'s own older indexes. The files changed while I was reading them, so treat this as a snapshot.

**Still open, checked in the code:**
- No record in `knowledge/` has a filled-in `valid_until`.
- The page title says "your government" (`vetra/web.py:28`).
- No LLM call sets `max_tokens`.
- Quick and standard answers have no second reader (`vetra/depth.py`).
- Masking covers only long digit runs, not PAN or email.
- The older `rag/` path's LLM calls aren't counted in the cost meter.
- One lock runs one question at a time.

## The ranked candidates

"Primary" means the original paper, code or official page. The notes read most of these through a summarising tool, and abstract-only sources are marked. "Effort" is an estimate: S is under a day, M a few days, L weeks.

### Adopt now, or test first where the table says so

| # | Candidate | Evidence | Source type | What it improves in VETRA | CPU cost and effort | Call |
|---|---|---|---|---|---|---|
| 1 | Hand-read test of 150-200 paired questions. Score correct, wrong, right refusal and needless refusal, by state and language | Machine-labelled tests inflate scores: F1 .929 against .692 on clean labels ([Trivia++](https://arxiv.org/html/2605.11330)). Scoring penalties reorder systems ([Why RAGs Hallucinate](https://arxiv.org/html/2608.26385)). Multi-state questions fell 11 points ([Vals via LawSites](https://www.lawnext.com/2025/10/vals-ais-latest-benchmark-finds-legal-and-general-ai-now-outperform-lawyers-in-legal-research-accuracy.html)) | Primary preprints; Vals is secondary | Every later decision, plus hidden weak states and languages | None on CPU. M, mostly reading | **Adopt now** |
| 2 | Validity dates on rules, a filter on the date the question means, and telling the writer when a rule was replaced | French tax law: 2.7% on current-law RAG, 98.3% with versions ([Temporal Misgrounding](https://arxiv.org/html/2608.09393)). Old text flipped 17-91% of answers, and stating the end date largely fixed it for larger models ([Stale-Document Poisoning](https://arxiv.org/abs/2609.31342)) | Primary. First has commercial authors and a closed retriever. Second is abstract only | Right rule for the right season, and old orders stop winning | Almost none. M to L of data work | **Adopt now**. Expect far less than 98%, since Indian orders aren't clean versioned text |
| 3 | Code checks for unit, scale, crop and year beside each figure | Scale errors are a major error type. Fixing them alone took one model from 37.0% to 57.7% ([FAITH](https://arxiv.org/html/2508.05201)). Monetary units are fragile ([FinCriticalED](https://arxiv.org/html/2511.14998)) | Primary, English finance only | Stops right digit, wrong meaning. `checks.py` has no lakh, crore or area rule today | None. S to M | **Adopt now** |
| 4 | Second-reader prompt with guidelines and examples from your own failures, passing the question too | Balanced accuracy 59.7 to 71.6; Hindi up to 75.41 ([MEMERAG](https://arxiv.org/html/2502.17163)). Same-source examples reached 84.0 ([FaithJudge](https://arxiv.org/html/2505.04847v2)) | Primary, peer reviewed | Catches more wrong wording in deep answers | None. S | **Adopt now**, scored on #1 |
| 5 | Reranker on or off for non-English text | No Indian-language test exists. Your own RTI comment records rerankers hurting (`rag/domains.py`). A multilingual swap gained only 80.41 to 80.76 ([Karmx card](https://huggingface.co/karmx/Llama-Karmx-Indic-Embedding-bge-m3)) | Local reading; vendor card | Could remove noise from Indian-language ranking. It's fused with search order, which softens any harm | Saves time. S | **Test now** |
| 6 | English draft checked first, then translated with numbers masked, against today's direct writing | Mixed-language checks score lower ([IndicXNLI](https://arxiv.org/html/2204.08776)). Fluent text can hide errors ([SHROOM-CAP](https://aclanthology.org/2025.chomps-main.7.pdf)). Masking method in [IndicTrans2's code](https://raw.githubusercontent.com/AI4Bharat/IndicTrans2/main/inference/normalize_regex_inference.py) | Primary, but none tests an LLM reader on this exact setup | Words like "not" or "up to" flipping in 21 languages, which digit checks miss | One extra call. M | **Test**. No study settles it |
| 7 | Scan pipeline: sort pages on the laptop, read with Gemini, compare numbers with Tesseract, send disagreements to a third read | Gemini scored strongly across scripts in no-stake tests ([GlotOCR](https://arxiv.org/html/2604.12978), [Devanagari](https://arxiv.org/html/2606.29213)). The best readers still lost 1-3% of numeric facts on clean pages ([FinCriticalED](https://arxiv.org/html/2511.14998)). Fields where all readers agreed were 98.7% right ([CENTURIA](https://arxiv.org/html/2608.30616)) | Primary, none on Indian government PDFs. The pipeline itself is untested | Fewer wrong facts, and more scanned states become usable | About $3.62-7.25 for 3,000 pages on 3.1 Flash-Lite ([prices](https://aistudio.google.com/docs/pricing); my estimate assumes output size). Tesseract about 4 hours, an assumed speed. L | **Adopt now**, starting with a 150-200 page number test |
| 8 | Fixed line on each chunk (state, scheme, order, date, heading), plus chunks split at numbered paragraphs | Item-level statute chunks found about 3 times more citations per 1,000 words ([German statutes](https://arxiv.org/html/2610.13695v1)). I found no direct test of the fixed line | Primary, German law | Mix-ups between near-identical state orders, citations by paragraph, and amendments that hit one paragraph | Full re-embed, about 39 minutes today. No LLM. M | **Test now**, both in one rebuild. Keep E5's 512-token limit in mind |
| 9 | Pre-launch gates: investment, dose, personal status and crisis. Also identity wording, spend caps, `max_tokens`, wider masking, disclaimers in the reply language, an off switch | [SEBI regulations](https://www.sebi.gov.in/sebi_data/attachdocs/mar-2023/1679546065355.pdf). [GOV.UK Chat](https://insidegovuk.blog.gov.uk/2026/03/16/5-things-we-learned-testing-gov-uk-chat-an-ai-assistant-for-government) users wanted answers about their own records. [MyCity](https://themarkup.org/artificial-intelligence/2026/01/30/mamdani-to-kill-the-nyc-ai-chatbot-we-caught-telling-businesses-to-break-the-law) was shut down despite warnings. About 1% clicked links in AI summaries ([Pew](https://www.pewresearch.org/short-reads/2025/07/22/google-users-are-less-likely-to-click-on-links-when-an-ai-summary-appears-in-the-results/)) | Mixed: SEBI primary, GDS self-reported, Markup secondary, Pew from a search excerpt. No study of the gates themselves | Avoids the failures most likely to harm people or end the project | None. S for small fixes, M for gates | **Adopt before any public link**. Ask a lawyer whether typed questions need consent, whether SEBI's public-media exception covers one-to-one answers, and what logs the rules require |
| 10 | Hosted embeddings as a challenger: gemini-embedding-2 and -001 | -001 led on Indian questions over English text, but Google ran that test ([paper](https://arxiv.org/html/2503.07891)). It led dense models on Bengali farm PDFs (.464 against BGE-M3 .408), yet fell to .093 on colloquial queries ([independent](https://www.alphaxiv.org/abs/2608.14886.md)) | Primary. One vendor test, one independent. -2 has no published Indian score | Quality for cross-language search, and no 39-minute or 65-hour rebuilds | About $0.20-0.40 per rebuild, by my arithmetic ([prices](https://aistudio.google.com/docs/pricing)). Needs network on each search and paid tier for real questions. M | **Test** before the big document growth |

### Worth testing next

| # | Candidate | Evidence | Source type | What it improves in VETRA | CPU cost and effort | Call |
|---|---|---|---|---|---|---|
| 11 | Query mix under E5: English only, native only, both, plus romanised | Keyword search collapses across scripts: .004 on English queries over Bengali ([study](https://www.alphaxiv.org/abs/2608.14886.md)). Romanised queries cost BGE-M3 49-97% in Russian and Chinese ([SIGIR 2025](https://arxiv.org/pdf/2505.08411)) | Primary. Nothing measured on romanised Indian languages | Shows if search survives a planner failure, and how Hinglish behaves | About 1 hour of runs. S | **Test** |
| 12 | Extra keyword field of character 3-grams or 4-letter prefixes; Indic NLP normaliser | Bengali BM25 with bigrams beat all embeddings at .506 ([study](https://www.alphaxiv.org/abs/2608.14886.md)). Older FIRE results agree ([Leveling and Jones](https://doras.dcu.ie/16033/)). [Library is MIT](https://github.com/anoopkunchukuttan/indic_nlp_library) | Primary; FIRE work from a search excerpt | Word endings in 22 languages without 22 stemmers | No re-embedding, since this index builds in memory. Larger memory. S to M | **Test** on Marathi |
| 13 | Thinking setting on the second reader, then the judge | Gains flatten near 1,000 tokens on 2.5 models ([paper](https://arxiv.org/html/2604.02460v1)). No study by role | Primary, different models | Catches more unsupported sentences | About ₹0.34 per 1,000 tokens to December (from the notes). S | **Test** with planted false sentences |
| 14 | Rounds 0, 1, 2, 3 and the evidence cap of 36 | One-shot 91.0, iterative 90.0 ([paper](https://arxiv.org/html/2509.04820v1)). Iterating lowered correct refusals from 56.4% to 46.4% ([DeclineCraft](https://arxiv.org/html/2610.28340)) | Primary preprints, other domains | Lower cost, and possibly more honest "not found" | S once #1 exists | **Test** |
| 15 | Second reader on risky sentences in standard answers | Standard answers have no word check today. LLM judge F1 .694 ([Trivia++](https://arxiv.org/html/2605.11330)) | Primary | Closes the biggest checking gap | API only. S to M | **Test** |
| 16 | Planted-document test of 30-50 fake passages | Attacker text posing as metadata succeeded 49.1%, and plan-then-execute still allowed 40.7% ([ADI](https://arxiv.org/html/2607.05120)) | Primary, on action-taking agents | Fake "in force" labels, fake amounts | None. M | **Adopt before launch** |
| 17 | Quote first, with code checking the quote exists | 14.21% citation gain ([FRONT](https://arxiv.org/abs/2408.04568), abstract). Short quotes support claims less often ([LAQuer](https://arxiv.org/html/2506.01187v1)) | Primary. The code check itself is untested | Wrong wording in non-numeric rules | More tokens, no CPU. M | **Test** |
| 18 | Separate "is this enough evidence?" check per part | 93.0% on 115 cases, older models ([Sufficient Context](https://arxiv.org/html/2411.06037)). Refusal accuracy fell to 47.4% with many documents ([RefusalBench](https://arxiv.org/html/2510.10390v1)) | Primary | Cleaner refusals in deep answers | One short call per part. M | **Test** |
| 19 | Cheap writer first, stronger on check failure; planner model comparison | Flash-Lite 50.2 against 2.5-Pro 91.9 reading figures ([FAITH](https://arxiv.org/html/2508.05201)), so code must keep printing figures. Learned routers plateau ([study](https://arxiv.org/abs/2606.07587)) | Primary. The cascade is my adaptation | Lower cost ahead of the 1 January doubling of [3.8 Flash](https://aistudio.google.com/docs/pricing) | M | **Test** on standard questions |
| 20 | Follow-up slots (state, scheme, crop, season) and tap-to-ask buttons | Buttons reached over 45% of interactions at peak ([Farmer.Chat](https://arxiv.org/html/2409.08916)), self-reported, cause not shown | Primary, builders' own | "And what about tomato?", and less typing | S to M | **Test** with 30-50 pairs |
| 21 | Move date and place out of the writer's system prompt; Flex tier for paid test runs | Prompts are 300-600 tokens against a [4,096 minimum](https://aistudio.google.com/docs/caching), so caching saves roughly 5-10% by the notes' estimate. [Flex](https://aistudio.google.com/docs/flex-inference) is half price | Vendor docs for prices; saving is an estimate | Small cost cut, about ₹117 to ₹59 for 20 deep questions by the notes' arithmetic | S. Retest date handling | **Adopt** when convenient |
| 22 | One-line summary per document, then per-chunk context | Summary roughly halved wrong-document retrieval ([contracts](https://arxiv.org/html/2510.06999v1)). A weak model lost far more than an embedder swap ([CRAwLeR](https://arxiv.org/html/2606.21676)) | Primary, authors' own | The same mix-ups as #8, if the fixed line isn't enough | LLM calls plus a rebuild. M | **Test after #8** |
| 23 | Schema-enforced output for planner and judge | Valid JSON isn't correct JSON: .983 valid against .822 accurate ([benchmark](https://arxiv.org/html/2604.25359)) | Primary; authors sell a rival | Fewer wasted calls only | S | **Test** later |
| 24 | Later items: GEPA on the planner, exact-key answer cache, Phoenix trace viewer, Prompt Guard 2 86M | [GEPA](https://arxiv.org/abs/2507.19457) is self-tested. [FreshCache](https://arxiv.org/pdf/2607.04281) supports strict keys. [Prompt Guard](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M) has no per-language or CPU figures | Authors or vendors | Polish rather than core quality | Varies | **Later**, after real traffic or settled prompts |

### Skip for now

| Candidate | Why | Source type |
|---|---|---|
| GraphRAG, LightRAG, RAPTOR, LazyGraphRAG | Mostly level with or behind plain search on facts, at 2-12 times the corpus in tokens just to index ([benchmark](https://arxiv.org/html/2506.05690v3), [Samsung](https://arxiv.org/html/2603.29875)). Use the hand-checked `links.jsonl` table instead | Primary |
| ColBERT and late chunking | ColBERTv2 lost all five reranking tests ([EMNLP Findings](https://arxiv.org/html/2508.16757v1)). Late chunking can hurt search inside a document by up to 53.2% ([study](https://arxiv.org/html/2602.16974)), which is one of your judge's moves | Primary, English |
| LangGraph, ADK, other agent frameworks | I found no quality evidence, and [LangChain has a serious security record](https://labs.cloudsecurityalliance.org/research/csa-research-note-langchain-langgraph-vulnerabilities-202603/) | Vendor docs; secondary |
| Similarity-based answer cache | False hits of 13.4-27.2% even when tuned ([InfoQ](https://www.infoq.com/articles/reducing-false-positives-retrieval-augmented-generation/)). Near-identical questions about different states have different answers here | Practitioner test |
| Small NLI model replacing the second reader | No model has been shown on Telugu against English evidence. Best mixed figure is 72 ([IndicXNLI](https://arxiv.org/html/2204.08776)). Log-only trial at most | Primary, older |
| Conformal abstention | 26% missed targets at 100 calibration items ([A-CRC-QA](https://arxiv.org/html/2608.12008)), and you'd need over 500 per setting | Primary preprint |
| bge-reranker-v2-m3 on this laptop | About 20 seconds per question, from one weak source seen only in a search excerpt ([wiki](https://myforgelabs.github.io/myforge-vault-1111/wiki/reranker-cost-optimization-not-size.en/)). Timing not confirmed | Secondary |
| LLM clean-up of OCR text | Scores fell in every pipeline, for example 97.52% to 63.70% ([study](https://arxiv.org/html/2608.24976)) | Primary, Spanish |
| Surya, Marker, EasyOCR, Azure as main readers of Indian scans | They trail Gemini or lack scripts ([Sarvam's table](https://www.sarvam.ai/blogs/sarvam-vision-2-1), [Krutrim's](https://arxiv.org/html/2602.16430)) | Vendor-run, with [independent Devanagari support](https://arxiv.org/html/2606.29213) |
| Training or fine-tuning models | No GPU, too few labels, and gains are small and self-reported | Model cards |

## What "fine-tuning" means for this engine

The engine needs settings adjusted, not models trained. Each change below should go through test #1, using a paired comparison on the same questions.

| Setting | Today | What to try | Watch out for |
|---|---|---|---|
| Reranker | English MiniLM, skipped on deep part searches | Off for non-English text | Check English scores don't drop |
| Planner's formal search passage | Always written | With and without, on casual questions | Formal wording may miss farmers' words: dense search fell to .093 on colloquial queries ([study](https://www.alphaxiv.org/abs/2608.14886.md)) |
| Chunk size and boundaries | Not reviewed by the notes | Numbered paragraphs, within E5's 512 tokens | A long header uses up the window |
| Keyword tokens | Much improved | Add Arabic Supplement (U+0750-077F) and Meetei Extensions (U+AAE0-AAFF), and unify Malayalam chillu forms. All three still fail in my test | Small but free |
| Judge's view | 700 characters per passage | Keep it. Longer context made follow-up searches rarer: 95% at 3k tokens, 25% at 12k ([paper](https://arxiv.org/html/2509.04820v1)) | Test before raising it |
| Rounds and evidence | 3 rounds, 36 records on deep | Lower both if coverage holds | Measure refusals as well |
| Thinking per role | Off for writer and verifier | Low or medium on verifier | Confirm `none` really means none on 3.8 Flash. The docs and your own test disagree |
| Cross-language score cut-offs | Off-topic check only | Per language, with intervals | I found no published support |
| Model per role | Fixed mix | Compare planners on your existing labels | Cheap models may fail on format |

## How much of this is proven

**Independent measurements are few, and none uses Indian government documents.** The strongest are GlotOCR and the Devanagari study for OCR, FinCriticalED for figures, the Bengali farm study and the Sri Lankan government study for search ([Tamil and Sinhala](https://arxiv.org/html/2608.12820v1): BGE-M3 95.6 against translate-then-search 93.0), and the EMNLP reranker comparison. These tell you the direction to go in. They don't tell you the size of the gain here.

**Authors testing their own methods make up most of the rest.** That includes Temporal Misgrounding, HippoRAG 2, GEPA, FRONT and CRAwLeR. Treat their numbers as upper limits. FrugalGPT's 98% saving reflects 2023 prices, for example.

**These are vendor or self-reported claims, not proof:**
- Google's lead on Indian-question search, which is a single shared run across two papers.
- Sarvam's and Bodhan's OCR rankings. [Sarvam's data is public](https://huggingface.co/datasets/sarvamai/indic-ocr-bench/discussions), so you can rerun it.
- GOV.UK Chat's 76% to 90% and its 508 blocked jailbreaks, which are the best public government evidence, but self-scored.
- Farmer.Chat's roughly 75% answered.
- Krishi Sathi's [97.53%](https://arxiv.org/abs/2508.03719), with no method given.
- Sarvam Translate's ["suitable for professional legal use"](https://www.sarvam.ai/blogs/sarvam-translate).
- LazyGraphRAG's [0.1% cost](https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/), contradicted by a benchmark.
- [DhvaniGuard's](https://huggingface.co/speedsharma/dhvaniguard-v0) 100% catch rate on its author's own test.

**My own judgement, not measured anywhere:** the ranking itself, the scan pipeline as a whole, the fixed chunk header, the dose rules, and the penalty weights for wrong figures.

## What this confirms or overturns in `docs/ARCHITECTURE_RESEARCH.md`

| Doc says | Now | Why |
|---|---|---|
| BGE-M3 led 8 of 13 languages | **Overturned** | The paper's own table shows a tie with e5-large in 10 of 13 ([IndicRAGSuite](https://arxiv.org/pdf/2506.01615)). The doc's multilingual idea is now settled locally by the E5 switch |
| Marker or Surya for Indian-script scans | **Overturned** | Surya trails Gemini in every Indian-script comparison found, and Marker does its OCR through Surya. Docling survives for born-digital tables only |
| Caching saves money | **Mostly overturned** | Prompts are far below the cache minimum |
| Judge on about 20 questions | **Limited** | Fine as a smoke test. A 20% against 5% difference has about 10% power at 20 pairs, by the notes' arithmetic |
| Quote-first has practitioner support only | **Partly overturned** | FRONT and LAQuer add peer-reviewed support. The word-for-word code check remains untested |
| Search from the reasoning (IRCoT) | **Weakened** | 0.181 against plain RAG's 0.270 on a small model ([Search Wisely](https://aclanthology.org/anthology-files/pdf/emnlp/2025.emnlp-main.998.pdf)), a harsh test |
| Pin down the period, worth trying | **Upgraded to adopt** | Now has measured support |
| Read-only design keeps text from acting | **Right, but incomplete** | A wrong answer is VETRA's consequential action, and forged labels stay open |
| Better reranker | **Weakly confirmed** | Stronger in English, with almost nothing in Indian languages |
| Chunk context | **Confirmed in direction** | Anthropic's exact figures remain unreplicated, and its $1 estimate needs redoing for Gemini |
| Late chunking weaker; no parallel agents; design holds | **Confirmed** | [ConTEB](https://arxiv.org/html/2505.24782) and [single-agent study](https://arxiv.org/html/2604.02460v1) |
| Parent-child sits in the lower half | **Claim unconfirmed, conclusion stands** | The paper's text doesn't give that rank, but the German statute test supports skipping it |

## What wasn't verified

- **Source reading:** I worked from the notes and did not reopen the sources. The notes read most papers through a summarising tool, so reopen any figure before quoting it publicly. Stale-Document Poisoning, FRONT, Read-Gate and several others were abstract only. The FAITH table was garbled in the source.
- **Indian documents:** there is no benchmark on Indian government PDFs, no independent 22-language search comparison, and no retrieval figures for Dogri, Kashmiri, Santali or Sindhi. No LLM checker has been measured on Indian-language answers against English evidence.
- **Local timings:** no CPU timing exists for Tesseract, PP-OCR, multilingual rerankers or EmbeddingGemma on this laptop. The 65-hour figure assumes indexing time grows in a straight line.
- **Could not check:** Bhashini's API and OCR, Gemini free-tier limits (only visible in your AI Studio account), the official DPDP gazette text, the KCC licence on data.gov.in, and Gemini 3.x jailbreak resistance. Whether model-written links can render in answers wasn't audited either.
- **Conflicting evidence I couldn't resolve:** PaddleOCR-VL scores Hindi 95.35 in [one benchmark](https://arxiv.org/html/2607.02956) and Devanagari 1.0 in [another](https://arxiv.org/html/2604.12978). The Vals article gives both 9 and 7 points for the lead over lawyers.
- **Sources the notes never found:** papers called HALOs and "Reasons to Reject", and anything on AIRAVATA. I'm making no claim about them.

## Conclusion

The E5 switch changes the order of work as much as the search itself. Every chunk experiment now costs about 39 minutes, so changes to what gets embedded should be grouped into one rebuild, while keyword and reranker experiments can run without re-embedding and should go first. The same cost is the real argument for trying hosted embeddings before the document set grows.

The research also points to one trap worth watching: the features that make VETRA search harder can make it worse at admitting what it doesn't know, and a test that only counts right answers would score that as a win. That's why the test comes first, and why it has to count refusals. VETRA's checks prove a figure was in the evidence, but not that the evidence is current or true, so dates and source checks are the next layer of trust to build.
