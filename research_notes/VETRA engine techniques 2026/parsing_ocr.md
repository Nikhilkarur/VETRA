# Document parsing and OCR for Indian government PDFs (checked 5 November 2026)

Evidence labels used throughout:
- **[M-open]**: measured by a party with no visible stake in the tools it tested. Affiliations were read only for GlotOCR Bench; for the others "no stake" means no tested product is theirs, as far as the text I read shows.
- **[M-stake]**: measured, but the tester sells or built one of the tools (Sarvam, Bodhan, Krutrim, Tencent, Allen AI).
- **[V]**: vendor claim about its own tool.
- **[P]**: practitioner blog, forum or aggregator.

How the numbers were read: paper and web pages were read through a summarising fetch tool, and some came only from search-result summaries (marked "summary only"). Re-open the source before quoting a figure in anything final. Nothing was run on this machine, and no figure here comes from VETRA's own documents.

## Which OCR tools have measured accuracy on Devanagari, Telugu, Tamil, Bengali, Kannada, Malayalam, Gujarati, Odia, Gurmukhi and Urdu?

### Takeaway
There are now real multi-script benchmarks, but none on Indian government documents and none scoring exact numbers. Gemini is the only option that scores well across all ten scripts in both vendor-run and no-stake tests and is also cheap and already wired in. Sarvam Vision 2.1 and Bodhan Indic-OCR score higher on vendor-run tests and should be tested. This overturns the "Marker or Surya for scans in Indian scripts" line in `docs/ARCHITECTURE_RESEARCH.md`.

### Cited Findings

**Largest Indian-language comparison: Sarvam Indic OCR Bench [M-stake].** It has 6,909 samples, 6,609 of them across 22 Indian languages, from newspapers, brochures, textbooks and historical writing dated 1800 onward. The scores are character and word "language accuracy", run and published by Sarvam, so treat the order as a vendor's result — [Sarvam](https://www.sarvam.ai/blogs/sarvam-vision-2-1). The dataset is public on Hugging Face under Apache-2.0, so VETRA can rerun it — [dataset](https://huggingface.co/datasets/sarvamai/indic-ocr-bench/discussions). Tesseract, PP-OCRv5, EasyOCR and Document AI are not in the table. All figures below are from the same [Sarvam table](https://www.sarvam.ai/blogs/sarvam-vision-2-1).

| Language | Sarvam 2.1 | Bodhan Indic-OCR | Gemini 3.6 Flash | Surya 2 | Mistral OCR4 | Google Cloud Vision | Azure Vision 4.0 |
|---|---|---|---|---|---|---|---|
| Overall (22 + English) | 87.39 | 84.94 | 79.35 | 69.96 | 69.16 | 71.76 | 41.29 |
| Hindi | 93.52 | 90.99 | 92.11 | 86.12 | 85.87 | 84.29 | 85.72 |
| Marathi | 95.06 | 90.76 | 93.14 | 86.58 | 84.17 | 86.50 | 87.86 |
| Telugu | 91.55 | 86.92 | 85.22 | 72.55 | 78.06 | 75.71 | 17.09 |
| Tamil | 87.70 | 84.21 | 84.58 | 79.07 | 79.73 | 78.14 | 80.96 |
| Bengali | 93.47 | 90.87 | 90.36 | 81.79 | 85.06 | 85.24 | 8.24 |
| Kannada | 90.54 | 86.51 | 82.70 | 79.60 | 77.84 | 75.40 | 9.32 |
| Malayalam | 90.24 | 86.38 | 84.41 | 76.61 | 71.50 | 76.06 | 10.16 |
| Gujarati | 88.87 | 83.26 | 83.68 | 65.80 | 68.19 | 64.40 | 11.79 |
| Odia | 80.01 | 75.45 | **81.01** | 69.34 | 57.04 | 68.32 | 4.16 |
| Punjabi | 89.16 | 86.51 | 87.06 | 83.06 | 81.65 | 81.65 | 7.76 |
| Urdu | 91.21 | 90.62 | 89.52 | 86.01 | 78.11 | 84.77 | 11.61 |

- Rarer languages in the same table: Manipuri is Sarvam 85.12, Bodhan 82.85, and everyone else under 1. Kashmiri is Sarvam 54.82, Gemini 36.04. Santhali is Bodhan 68.30, Sarvam 53.91, Gemini 51.84 — [Sarvam](https://www.sarvam.ai/blogs/sarvam-vision-2-1).
- A second vendor's table gives a similar order: Sarvam 86.6, IndicOCR 86.2, Gemini 3.1 Pro 80.4 overall [M-stake]. Per-language figures shift a lot between the two: Bodhan reports its own Tamil at 91.3 where Sarvam's table gives it 84.21 — [Bodhan model card](https://huggingface.co/bodhan-ai/indic-doc-parser).

**GlotOCR Bench [M-open].** Authors are at LMU Munich, TU Munich and Sorbonne/CNRS. It tests 14 models on 158 scripts, using synthetic images rendered from real text. The score is Acc@5, the share of sentences with CER at or below 5%. It does not test Tesseract, Surya, EasyOCR or PP-OCRv5 — [GlotOCR Bench](https://arxiv.org/html/2604.12978).

| Script | Gemini 3.1 Flash-Lite | dots.ocr | PaddleOCR-VL-1.5 | Qwen3-VL-8B | HunyuanOCR | GPT-4.1 |
|---|---|---|---|---|---|---|
| Devanagari | 93.5 | 90.2 | 1.0 | 70.8 | 79.8 | 65.8 |
| Telugu | 92.0 | 93.0 | 81.0 | 0.0 | 35.0 | 20.0 |
| Tamil | 99.0 | 88.0 | 98.0 | 7.0 | 65.0 | 73.0 |
| Bengali | 63.0 | 73.0 | 29.0 | 33.0 | 53.0 | 27.0 |
| Kannada | 85.0 | 80.0 | 0.0 | 0.0 | 33.0 | 16.0 |
| Malayalam | 81.0 | 35.0 | 0.0 | 0.0 | 23.0 | 15.0 |
| Gujarati | 98.0 | 95.0 | 0.0 | 13.0 | 6.0 | 48.0 |
| Odia | 82.0 | 0.0 | 0.0 | 0.0 | 2.0 | 4.0 |
| Gurmukhi | 85.0 | 89.0 | 0.0 | 22.0 | 71.0 | 20.0 |
| Arabic script | 58.8 | 63.2 | 21.0 | 36.8 | 38.2 | 39.5 |

- Failure mode that matters here: on average, only 12.5% of predictions were in the correct script and 68.4% were hallucinated in a wrong one. The authors write that models "overwhelmingly prefer to confabulate in a wrong script rather than abstain". Gujarati and Gurmukhi drift toward Devanagari, Telugu, Kannada and Tamil get confused with each other, and Odia with Bengali — [GlotOCR Bench](https://arxiv.org/html/2604.12978).
- Scoring caveat: Acc@5 takes the best of four output variants, including one with combining marks removed — [GlotOCR Bench](https://arxiv.org/html/2604.12978).

**Gemini against Surya on IndicVisionBench-OCR [M-stake].** The testers are Krutrim, comparing their own Chitrapathak models. Scores are character-level ANLS, lower is better, shown as Gemini 2.5 Flash / Surya: Bengali 4.04 / 12.61, Hindi 5.88 / 8.38, Kannada 4.38 / 6.37, Malayalam 30.60 / 36.37, Marathi 1.79 / 4.33, Odia 18.60 / 25.58, Punjabi 4.98 / 7.31, Tamil 3.01 / 7.71, Telugu 7.16 / 16.85. Neither Krutrim model is stated to be released — [Chitrapathak](https://arxiv.org/html/2602.16430).

**Devanagari stress test on real and clean text [M-open].** The set is 300 real printed word and short-phrase scans of Sanskrit-typeset text, so page-oriented models are at a disadvantage. Mean CER, median CER and catastrophic rate (CER above 50%): Gemini 2.5 Flash 4.4 / 0.0 / 0.7%, Claude Opus 4.7 5.1 / 0.0 / 0.7%, Qwen3-VL-8B 9.3 / 0.0 / 3.3%, GPT-5.5 18.4 / 12.5 / 7.7%, EasyOCR 34.3 / 16.7 / 26.3%, olmOCR-7B 59.1 / 20.0 / 12.0%, Mistral OCR 90.7 / 0.0 / 8.0% with output 1.8 times the reference length, DeepSeek-OCR 112.0 / 100.0 / 89.0%. On clean renders the ten systems all land at chrF++ 91 to 98, and the authors warn that synthetic renders badly overstate Devanagari quality — [Can OCR-VLMs Read Devanagari?](https://arxiv.org/html/2606.29213).

**Multilingual benchmark from Tencent [M-stake].** MORE covers 149 languages, and its authors work for the company behind HunyuanOCR. Hindi, Tamil, Telugu and Bengali scores: HunyuanOCR 95.85 / 88.00 / 84.98 / 90.69, Qwen3-VL-2B 95.30 / 91.14 / 74.37 / 91.16, dots.ocr 95.44 / 89.58 / 53.71 / 63.11, PaddleOCR-VL 95.35 / 88.56 / 65.11 / 57.81, MinerU2.5 33.96 / 16.66 / 17.27 / 50.00. Gemini 3 is in the overall tables but not the per-language ones — [MORE](https://arxiv.org/html/2607.02956).

**Conflict between benchmarks.** PaddleOCR-VL scores Hindi 95.35 in [MORE](https://arxiv.org/html/2607.02956) but Devanagari 1.0 in [GlotOCR Bench](https://arxiv.org/html/2604.12978). Qwen3-VL Telugu is 74.37 (2B) in MORE and 0.0 (8B) in GlotOCR. The versions, prompts and data differ, and I could not resolve this.

**Tamil on clean synthetic lines [M-open].** CER: Document AI 0.78%, Cloud Vision 0.79%, Tesseract 5.5.0 7.80%, EasyOCR 11.72%, Surya 13.92%. WER: 11.98%, 12.04%, 61.45%, 28.76%, 65.00%. Text is black on white, and the authors say this does not reflect real conditions — [Zero-shot OCR](https://arxiv.org/html/2507.18264).

**Tesseract across scripts, the only multi-script table found, and it is old [M-stake].** Character accuracy from a 2022 IIIT paper on the Mozhi dataset, Tesseract version not read: Assamese 90.0, Bengali 91.3, Gujarati 96.9, Hindi 95.0, Kannada 85.7, Malayalam 88.0, Manipuri 85.7, Marathi 97.9, Odia 94.0, Punjabi 93.2, Tamil 79.3, Telugu 93.7, Urdu 68.3. Google Cloud Vision on the same data scored 90.9 to 98.4. The authors' own columns use ground-truth boxes and are not like-for-like — [Mathew et al.](https://arxiv.org/html/2205.06740).

**Tool summary**

| Tool | Evidence and source type | Indian scripts | Tables | CPU speed | Licence and cost | Verdict |
|---|---|---|---|---|---|---|
| **Gemini (Flash-Lite, Flash)** | [M-open] [GlotOCR](https://arxiv.org/html/2604.12978), [Devanagari](https://arxiv.org/html/2606.29213); [M-stake] [Sarvam](https://www.sarvam.ai/blogs/sarvam-vision-2-1), [Krutrim](https://arxiv.org/html/2602.16430) | Strong on all ten. Top on Odia. Bengali and Arabic script are its weak points in GlotOCR | OmniDocBench TEDS 0.869 (3.6 Flash, [Sarvam](https://www.sarvam.ai/blogs/sarvam-vision-2-1)); 81.02 in [MORE](https://arxiv.org/html/2607.02956) | API | [Paid per token](https://aistudio.google.com/docs/pricing); see cost section | **Adopt now** as main reader of scans |
| **Tesseract 5** | [M-open] [Zero-shot](https://arxiv.org/html/2507.18264), [Uruguay](https://arxiv.org/html/2607.24077v3); [M-stake] [Mathew 2022](https://arxiv.org/html/2205.06740) | [Traineddata](https://github.com/tesseract-ocr/tessdoc/blob/main/Data-Files-in-different-versions.md) for all ten scripts, but none listed for Kashmiri, Konkani, Maithili, Manipuri, Santali. Weak on Tamil and Urdu | None | About 0.76 s per small receipt on an unnamed CPU, my division of [a vendor's figure](https://imagetotable.ai/references/ocr-cost-per-1000-pages-benchmark) | [Apache-2.0](https://github.com/tesseract-ocr/tesseract), free | **Adopt now** as CPU second witness for digits, not as main reader |
| **PP-OCRv5 (or v6)** | [V] line accuracy; [M-open] [FinCriticalED](https://arxiv.org/html/2511.14998), [Uruguay](https://arxiv.org/html/2607.24077v3) | [Own test sets](https://www.paddleocr.ai/latest/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.html): Devanagari 84.96, Telugu 87.65, Tamil 94.2, Arabic script 81.27. Other six scripts not on that page | Not assessed | [1.75 s per image mobile, 4.34 s server](https://www.paddleocr.ai/latest/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5.html), on a Xeon Gold 6271C [V] | [Apache-2.0](https://github.com/PaddlePaddle/PaddleOCR), free | **Test** as digit witness for its four scripts. [PP-OCRv6](https://github.com/PaddlePaddle/PaddleOCR) is newer, Indian coverage not checked |
| **Sarvam Vision 2.1** | [M-stake] own benchmark, public data | Highest overall in its own test, 22 languages | [TEDS 0.890; olmOCR tables 91.9](https://www.sarvam.ai/blogs/sarvam-vision-2-1) | API | [₹0.50 per page digitisation, ₹100 free credit](https://docs.sarvam.ai/api/getting-started/pricing); closed | **Test**: tie-breaker and rare languages |
| **Bodhan Indic-OCR** (with AI4Bharat) | [M-stake] [model card](https://huggingface.co/bodhan-ai/indic-doc-parser); second in Sarvam's table | 22 languages, 13 scripts; Manipuri and Santhali strong | [TEDS 85.10, English](https://huggingface.co/bodhan-ai/indic-doc-parser) | None stated. [1.7 GB model, NVIDIA GPU implied](https://huggingface.co/bodhan-ai/indic-doc-parser) | [Indic Open Model License](https://huggingface.co/bodhan-ai/indic-doc-parser); ask before hosting as an API for others, with exceptions for government, nonprofit and academic users. [Hosted ₹0.20 per image, ₹10 credit](https://www.analyticsvidhya.com/blog/2026/09/bodhan-ai-indic-models/) | **Test** through hosted API, cheapest Indian option |
| **Surya** | [V] [repo](https://github.com/datalab-to/surya); [M-open] [Zero-shot](https://arxiv.org/html/2507.18264), [Uruguay](https://arxiv.org/html/2607.24077v3) | Behind Gemini on all nine scripts in [Krutrim's table](https://arxiv.org/html/2602.16430). Tamil WER 65% on clean lines. Own Arabic pass rate 45.4% | [Own bench 78.3](https://github.com/datalab-to/surya) | [0.19 pages/s on M4 Max; no CPU figure](https://github.com/datalab-to/surya) | [Code Apache-2.0; weights free under $5M funding or revenue](https://github.com/datalab-to/surya) | **Skip as default**; overturns the current note |
| **Marker** | [M-stake] [76.1 olmOCR-bench, in-house](https://arxiv.org/html/2510.19817); [M-open] [98.70% character accuracy, Spanish](https://arxiv.org/html/2608.24976) | No Indian-script result found. [OCR runs through Surya](https://github.com/datalab-to/marker), so it inherits Surya's Indian-script results | olmOCR tables 72.9 | [No-OCR mode only: 42 ms per page, on a GPU host but CPU-bound](https://github.com/datalab-to/marker) [V]. No OCR CPU figure | [Code Apache-2.0; weights free under $5M funding or revenue](https://github.com/datalab-to/marker) | **Skip for Indian scans**; its no-OCR mode may be worth a look for clean English PDFs |
| **Docling** | [M-open] [Soric et al.](https://arxiv.org/html/2511.16134v1), [Spanish study](https://arxiv.org/html/2608.24976) | No Indian result. OCR comes from a plugged-in engine, so it inherits that engine's accuracy (my inference from those configurations) | TEDS 0.86 / 0.67 / 0.79 on born-digital sets | [EasyOCR backend reported at 30+ s per page, secondhand](https://shekhargulati.com/2025/01/16/only-chatgpt-search-got-it-right) | [Code MIT; model licences separate](https://github.com/docling-project/docling) | **Test** for born-digital tables only; confirms half the current note |
| **EasyOCR** | [M-open] [Devanagari](https://arxiv.org/html/2606.29213), [Zero-shot](https://arxiv.org/html/2507.18264) | [No Gujarati, Malayalam, Odia, Punjabi](https://www.jaided.ai/easyocr/). 26.3% catastrophic on real Devanagari | None | [Runs CPU-only](https://github.com/JaidedAI/EasyOCR); speed as above | [Apache-2.0](https://github.com/JaidedAI/EasyOCR) | **Skip** |
| **Google Document AI** | [M-open] [Tamil 0.78% CER](https://arxiv.org/html/2507.18264), synthetic only | [Hindi, Marathi, Bengali, Nepali, Tamil, Telugu, Kannada, Malayalam, Gujarati, Punjabi. Odia, Assamese, Urdu, Sanskrit not in the OCR list](https://docs.cloud.google.com/document-ai/docs/languages) | Not assessed | API | [$1.50 per 1,000 pages, add-ons $6](https://cloud.google.com/document-ai/pricing) (summary only) | **Test** as a low-cost different-family witness |
| **Azure Document Intelligence** | [V] language list; [M-stake] [Sarvam](https://www.sarvam.ai/blogs/sarvam-vision-2-1) | [Printed list has Hindi, Marathi, Tamil, Urdu, Nepali, Sanskrit. Bengali, Telugu, Kannada, Malayalam, Gujarati, Odia are detect-only; Punjabi is Arabic script only](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/language-support/ocr), which fits the sub-20 scores Sarvam reports for Azure Vision 4.0, a sibling product rather than Document Intelligence itself | Not scored on these scripts | API | [About $1.50 per 1,000 Read, third-party](https://aitoolsatlas.ai/tools/azure-ai-document-intelligence/pricing) | **Skip** |
| **Mistral OCR** | [V] [OCR 4](https://mistral.ai/news/ocr-4/); [M-open] [Devanagari](https://arxiv.org/html/2606.29213); [M-stake] [Sarvam](https://www.sarvam.ai/blogs/sarvam-vision-2-1) | 69.16 overall. On real Devanagari, 8% catastrophic and output 1.8× too long, version not stated | [TEDS 0.826](https://www.sarvam.ai/blogs/sarvam-vision-2-1) | API | [$4 per 1,000, $2 batch](https://dev.to/aarhamforensics_eb3c024eb/mistral-ocr-4-document-intelligence-pricing-api-competitor-comparison-knk) [P]. Word-level confidence scores [V] | **Skip for now** |
| **olmOCR** | [M-stake] [own paper](https://arxiv.org/html/2510.19817); [M-open] [GlotOCR](https://arxiv.org/html/2604.12978) | [Telugu, Kannada, Malayalam, Odia 0.0](https://arxiv.org/html/2604.12978) | 84.9 on English bench | [Needs 12 GB GPU; no CPU route listed](https://github.com/allenai/olmocr) | [Apache-2.0](https://github.com/allenai/olmocr) | **Skip** |
| **dots.ocr / dots.mocr** | [V] [repo](https://github.com/rednote-hilab/dots.ocr); [M-open] [GlotOCR](https://arxiv.org/html/2604.12978) | Strong on several, but Odia 0.0 and Malayalam 35.0 | [39.81 in MORE](https://arxiv.org/html/2607.02956) | [CPU guide exists; no speed; GPU assumed](https://github.com/rednote-hilab/dots.ocr) | [MIT sidebar plus a separate licence file not read](https://github.com/rednote-hilab/dots.ocr) | **Skip** without a GPU |
| **MinerU** | [M-stake] [MORE](https://arxiv.org/html/2607.02956); [M-open] [FinCriticalED](https://arxiv.org/html/2511.14998) | MinerU2.5 Hindi 33.96, Tamil 16.66 | [33.83 in MORE; 84.9 English bench, author-reported](https://arxiv.org/html/2510.19817) | [`basic` runs on CPU with 2 GB RAM; `standard` 8 GB with llama.cpp](https://github.com/opendatalab/MinerU) | [Own licence: Apache-2.0 plus conditions](https://github.com/opendatalab/MinerU) | **Skip** |
| **GOT-OCR 2.0** | [Model card](https://huggingface.co/stepfun-ai/GOT-OCR2_0) only. [Would not run reliably in the Devanagari test](https://arxiv.org/html/2606.29213) | No Indian claim | No Indian result | [NVIDIA GPU assumed](https://huggingface.co/stepfun-ai/GOT-OCR2_0) | [Apache-2.0](https://huggingface.co/stepfun-ai/GOT-OCR2_0) | **Skip** |
| **Qwen vision models** | [M-open] [GlotOCR](https://arxiv.org/html/2604.12978), [Devanagari](https://arxiv.org/html/2606.29213), [FinCriticalED](https://arxiv.org/html/2511.14998); [M-stake] [MORE](https://arxiv.org/html/2607.02956) | Hindi good. Others conflict wildly between benchmarks | [68.27 and 65.21 in MORE](https://arxiv.org/html/2607.02956) | No CPU statement; [9B params, GPU-oriented examples](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct) | [Apache-2.0 weights](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct); claims 32 languages [V] | **Skip** locally |
| **AI4Bharat / Bhashini OCR** | [Consortium page](https://ilocr.iiit.ac.in/blog/loksabha/): 13 languages built, 1.5 million Hindi parliament pages processed, no accuracy figures | Claimed recognisers for 22 languages | Not found | Not found | No public API or model confirmed | **Skip** Bhashini for now; AI4Bharat's practical route is Bodhan |

### Inferences
- Current note in `docs/ARCHITECTURE_RESEARCH.md`, idea 3: "no benchmark on Indian government documents was found" still holds. "Marker or Surya for scans in Indian scripts" should go: Surya trails Gemini in every comparison I found on Indian scripts, and Marker has no Indian-script evidence of its own and does its OCR through Surya. "Docling for tables" survives only for born-digital pages.
- English benchmark rank does not predict Indian-script rank. PaddleOCR-VL leads OmniDocBench but scores 0 to 1 on six of ten scripts in GlotOCR, and olmOCR-2 scores 0 on four. Do not pick an engine from olmOCR-bench.
- Wrong-script confabulation is a concrete risk for this project. A code check on Unicode block against the expected state language is cheap and catches it. The project's language labels could feed it.
- The GlotOCR marks-removed variant could flatter Indian scripts, because vowel signs are combining marks. I did not confirm how it applies to them.
- Sarvam's rank should be checked before it is believed. Its data is public, so a sample of 50 pages per script would be cheap to rerun.

### Gaps
- No benchmark on Indian government PDFs with stamps, signatures or amendments exists that I could find.
- No recent multi-script Tesseract result. The 2022 table is old, and the version was not read. No PP-OCRv5 result independent of Baidu on Indian scripts other than as a general [Spanish test](https://arxiv.org/html/2607.24077v3).
- No Document AI result on real Indian documents, and none at all on Devanagari, Telugu, Bengali, Kannada, Malayalam, Gujarati, Odia or Gurmukhi.
- Bhashini's OCR API: two searches found no endpoint or terms. The portal was not reached.
- [WACV 2026 table benchmark](https://openaccess.thecvf.com/content/WACV2026/papers/Thomas_Zero-Shot_Table_Extraction_in_Business_Documents_A_Unified_Benchmark_with_WACV_2026_paper.pdf) returned 403 and [Bodhan's release post](https://bodhan.ai/research/blogs/indic-ocr) returned 404.
- GlotOCR's per-script tables do not say whether they use clean or degraded images.

## What do independent OCR and parsing benchmarks show (olmOCR-bench, OmniDocBench, or newer) rather than vendor numbers?

### Takeaway
Almost no benchmark is truly independent, and the most-quoted ones are English. Top systems are bunched within a few points, so the published gaps can't decide this choice. The useful message is that scores collapse on old scans and that no table method is close to solved.

### Cited Findings
- olmOCR-bench is officially an English-language benchmark — [olmOCR 2](https://arxiv.org/html/2510.19817). Sarvam adds that it contains some Chinese and other contaminant samples — [Sarvam](https://www.sarvam.ai/blogs/sarvam-vision-2-1).
- **In-house runs by Allen AI [M-stake]:** Mistral OCR 72.0, Marker 1.10.1 76.1, DeepSeek-OCR 75.7, Nanonets-OCR2-3B 69.5, olmOCR 2 82.4. **Author-reported figures in the same table [V]:** PaddleOCR-VL 80.0, MinerU 2.5.4 75.2, Infinity-Parser 82.5, Chandra 83.1 — [olmOCR 2](https://arxiv.org/html/2510.19817).
- The old-scan category is the hard one and the closest to our documents: 29.3 to 50.4 in that table — [olmOCR 2](https://arxiv.org/html/2510.19817) — and 24.7 to 58.0 in Sarvam's newer run, against 98 to 100 on the base category — [Sarvam](https://www.sarvam.ai/blogs/sarvam-vision-2-1).
- **Sarvam's run of olmOCR-bench [M-stake], overall:** Sarvam Vision 2.1 87.3, Infinity-Parser2 Pro 86.1, Opus 5 85.1, Chandra-OCR2 84.5, Mistral OCR4 83.1, Gemini 3.6 Flash 82.4, GPT 6 Astra 81.8, PaddleOCR-VL 1.6 81.1, Bodhan 78.8, Google Cloud Vision 39.6, AWS Textract 25.5, Azure Vision 24.5 — [Sarvam](https://www.sarvam.ai/blogs/sarvam-vision-2-1).
- **Sarvam's run of OmniDocBench v1.6 [M-stake], overall:** PaddleOCR-VL 1.6 96.01, Sarvam 94.97, GLM-OCR 94.71, GPT 6 Astra 93.74, Gemini 3.6 Flash 93.58, Opus 5 92.51, Mistral OCR4 91.72 — [Sarvam](https://www.sarvam.ai/blogs/sarvam-vision-2-1). Bodhan's card reports its own model at 92.76 and PaddleOCR-VL-1.6 at 96.36 — [Bodhan](https://huggingface.co/bodhan-ai/indic-doc-parser).
- **Vendor self-scores [V]:** dots.mocr 83.9 on olmOCR-bench — [dots.ocr](https://github.com/rednote-hilab/dots.ocr); Surya 2.5 83.7 — [Surya](https://github.com/datalab-to/surya); Mistral OCR 4 93.07 on OmniDocBench — [Mistral](https://mistral.ai/news/ocr-4/). A February report of Sarvam at 84.3 on olmOCR-bench traces to a social post — [summary only](https://northeastherald.in/life/not-openai-not-google-this-indian-ai-model-is-turning-heads).
- **Spanish historical sources, 18 engines [M-open]:** median CER Qwen 3.6 with reasoning 1.72%, Qwen 3.6 2.01%, Gemma 4 3.27%, Surya 4.00%, MinerU2.5-Pro 4.19%, DocTR 5.74%, PP-OCRv5 8.18%, Tesseract 11.86%, EasyOCR 20.70%. By mean CER the order changes, with Surya best at 8.87% and DocTR at 10.23% beating several vision models — [Uruguayan documents](https://arxiv.org/html/2607.24077v3).
- **Spanish academic PDFs, 13 pipelines [M-open]:** character accuracy Marker 98.70%, Docling + Tesseract 89.06%, Docling + EasyOCR 85.39%, PyMuPDF 84.05%. On digital PDFs, all three Docling setups scored 96.54%, so OCR made no difference. PyMuPDF fell to 57.27% on multi-column pages — [Digitization pipelines](https://arxiv.org/html/2608.24976).
- Mean and median can disagree enormously. Mistral's median CER is 0.0 but mean is 90.7 on real Devanagari scans, and the authors ask for median and catastrophic rate to be reported together — [Devanagari](https://arxiv.org/html/2606.29213).

### Inferences
- For VETRA, the catastrophic rate and the old-scan category matter more than headline scores, because one bad page can feed a wrong fact.
- Independent tests still favour modern vision models over Tesseract on general text, but the gap is not uniform: mean scores in the Uruguayan study show classical DocTR holding its own.

### Gaps
- I did not check whether OmniDocBench has an official leaderboard, or who built it. All OmniDocBench figures here are vendor-run.
- No third party has rerun the 2026 model releases on olmOCR-bench that I could find.

## What's the best way to handle table extraction from scanned government documents and merged cells?

### Takeaway
No tested method is reliable enough to trust alone. Use a vision model to recover the structure as HTML with rowspan and colspan, then have code check the grid and re-read each number from its own cell image. I found no benchmark of merged cells on scanned Indian tables.

### Cited Findings
- Across 15 methods and 86k pages of scientific PDFs, "no method achieves F1TEDS > 90%". VLMs hallucinate on heterogeneous data, and heuristic methods stay competitive on specific layouts — [Soric et al. project page](https://soricm.github.io/table-extraction-benchmark/).
- **F1 TEDS on PubTables / Table-arXiv / Table-BRGM (French Word reports) [M-open]:** Docling 0.86 / 0.67 / 0.79, PyMuPDF 0.27 / 0.17 / 0.68, Camelot 0.20 / 0.13 / 0.73, PDFPlumber 0.22 / 0.12 / 0.56. Structure scores beat content scores: Docling's topology F1 is 0.95 / 0.83 / 0.88. These are born-digital, not scans — [Soric et al.](https://arxiv.org/html/2511.16134v1).
- Classical libraries run about ten times faster, at roughly 1 s per image, than Docling, TATR or the vision model. GPT-4o mini cost about $0.29 per 1,000 pages — [Soric et al.](https://arxiv.org/html/2511.16134v1).
- **OmniDocBench v1.6 table TEDS [M-stake]:** PaddleOCR-VL 1.6 0.931, GLM-OCR 0.895, GPT 6 Astra 0.891, Sarvam 0.890, Gemini 3.6 Flash 0.869, Opus 5 0.856, Mistral OCR4 0.826, and 0.000 for Azure Vision, Google Cloud Vision and AWS Textract — [Sarvam](https://www.sarvam.ai/blogs/sarvam-vision-2-1).
- **Multilingual tables tell a different story [M-stake]:** TEDS Gemini 3 81.02, HunyuanOCR 78.56, Qwen2.5-VL 68.27, Qwen3-VL 65.21, DeepSeekOCR 61.63, PaddleOCR-VL 61.11, dots.ocr 39.81, MinerU2.5 33.83. Its per-language table covers no Indian language in the portion read — [MORE](https://arxiv.org/html/2607.02956).
- TEDS itself is questioned: Pearson correlation with human judgement was 0.68, against 0.93 for an LLM-based evaluation — [Beyond String Matching](https://arxiv.org/html/2603.18652v2) (summary only).
- Image-only models made plain digit slips in dense tables, reading 3,466 as 3,468 on Japanese securities reports — [arXiv 2505.17625](https://arxiv.org/pdf/2505.17625) (summary only).
- A rule-based numeric and row-count check is recommended by one vendor blog [P] — [Newtuple](https://www.newtuple.com/post/ocr-benchmark-paddleocr-docling-llamaparse-surya) (summary only).
- Output options: Indic-OCR returns tables as HTML by default — [Bodhan](https://huggingface.co/bodhan-ai/indic-doc-parser). dots.ocr's own team lists complex tables as an open problem — [dots.ocr](https://github.com/rednote-hilab/dots.ocr).

### Inferences
My recommended method, built from the above and not itself tested:
1. **Route by page type.** For born-digital table pages, try Docling or PyMuPDF first, since VLM risk is avoidable there. For scans, use Gemini.
2. **Ask for HTML with `rowspan` and `colspan`,** with one table per output block and no totals computed. Markdown can't express merged cells.
3. **Check the grid in code.** Expanding spans must give a rectangle. Row and column counts must stay constant, and header spans must cover their children.
4. **Check arithmetic where it exists.** Totals, instalment × count = amount, and shares summing to 100%.
5. **Re-read each number from its cell crop,** using an engine from a different family, and compare after normalising digits.
6. **Keep a crop for every extracted value,** so a person can see the source of any disputed number.

Structure is easier than content in every test above, which is why step 5 re-reads the digits rather than trusting a single pass. Stamps overlapping cells are the likely worst case here, and nothing measured that.

### Gaps
- No measured merged-cell accuracy for scans, in any language.
- No table scores on Indian-language documents that I could read. MORE's appendix was cut off.
- Per-model Gemini and GPT table scores in Soric et al., and its hallucination appendix, were not in the portion read.

## How can legacy non-Unicode fonts be detected and repaired (Kruti Dev, Shusha, Anu, Nudi, Baraha and others)? When should we just render the page and OCR it instead of trusting the text layer? Are there tested text-quality checks?

### Takeaway
Detection looks straightforward with font names plus text statistics. Repair tools exist for some Hindi and a few other fonts, with little accuracy evidence, and their digit handling is unverified. Default to rendering and OCR unless a page passes the checks, including a comparison against what the page looks like. I found no quality check validated on Indian-script PDFs.

### Cited Findings

**Why the text layer fails**
- Legacy fonts store Devanagari in 8-bit slots, so extraction returns Latin gibberish — [krutiextract](https://pypi.org/project/krutiextract/).
- **Unicode-looking text can also be wrong.** Extractors that sort glyphs by position scramble matras — [krutiextract](https://pypi.org/project/krutiextract/). A ToUnicode map can itself be wrong, as in a reported case mapping the visual letter NA to vowel sign I — [Adobe forum](https://community.adobe.com/questions-9/hindi-unicode-pdf-search-and-copy-paste-issue-1629373). One extractor outputs raw stream order and drops or misplaces combining marks — [pdfstrings issue](https://codeberg.org/simbo1905/pdfstrings/issues/1).
- A PDF can carry a wrong hidden text layer, and forcing fresh recognition fixes it — [Occular wiki](https://github.com/Bodhi42/Occular-ocr/wiki/Troubleshooting) [P].
- Text-only extraction gets 0% on image-only pages — [Digitization pipelines](https://arxiv.org/html/2608.24976).

**Detection**
- krutiextract detects encoding per document, first from the PDF's fonts, then from character statistics — [krutiextract](https://pypi.org/project/krutiextract/).
- pdf-inspector, a Rust crate, flags pages using any U+FFFD, private-use runs of 3 or more, C1 control characters at 5% or more, Latin-1 characters at 40% or more with few ASCII letters, non-alphanumeric characters over half, and letter-statistic cipher checks. The cipher check runs only on Latin-dominant text with at least 200 ASCII letters. None of its checks are script-specific — [pdf-inspector source](https://docs.rs/crate/pdf-inspector/latest/source/src/text_quality.rs).
- A dictionary hit rate can work as a check, but it is not accuracy. IndicPDF reports 88.0% of 19,885 Kruti Dev words and 95.2% of 17,025 DevLys words matching Tesseract's Hindi word lists, and itself says this is not an accuracy figure — [IndicPDF](https://www.indicpdf.in/hindi-kruti-dev-to-unicode) [V].

**Repair tools found**

| Script | Tool | Fonts | Evidence |
|---|---|---|---|
| Devanagari | [krutiextract 1.6.1](https://pypi.org/project/krutiextract/), MIT, September 2026 | KrutiDev/DevLys, Walkman-Chanakya, Chanakya, APS-DV-Priyanka, Shusha, Aakriti. Shree-Lipi partial: about a third of code points differ. **Not** Akruti, ISM, Shivaji, Ajanta | [V] Regression corpus only. Stated Hindi; Marathi not stated |
| Kannada | [ascii2unicode](https://github.com/aravindavk/ascii2unicode) | Nudi, Baraha | No accuracy found |
| Malayalam | [payyans](https://github.com/libindic/payyans) | ML-TT Ambili, Karthika, Nandini, Revathi | No accuracy found |
| Tamil | [tamencs2unicode](https://sourceforge.net/projects/tamencs2unicode) | TSCII only implemented; Bamini not confirmed | No accuracy found |
| Bengali | [unicode_converter](https://github.com/shahad-mahmud/unicode_converter) | Bijoy | No benchmark, despite claiming "accurate" |
| Many | [IndicPDF](https://www.indicpdf.in/hindi-kruti-dev-to-unicode), a commercial web tool, 10 pages without an account | Anu, Priyaanka, Kranthi (Telugu); Kruti Dev, DevLys, Chanakya, Akruti Marathi, Shree-Lipi, Sakal Marathi; Bijoy; TAB-ELCOT-Kovai, Bamini, TSCII; Nudi 01 e; ML-TT Karthika; LMG Arun; Akruti Oriya; Asees; Geetanjali | [V] Reads the file's font table, with word-list hit rates only |

- Mapping tables vary from font to font with little consistency, so a table for one family does not transfer — [TypeDrawers](https://typedrawers.com/discussion/comment/20088) [P].
- **Digits are a specific trap.** Kruti Dev 714 draws digits in Devanagari while 010 draws Western digits — [IndicPDF](https://www.indicpdf.in/hindi-kruti-dev-to-unicode). IndicPDF reads Kruti Dev 011 and 016 with the 010 table and has only measured 010 — [IndicPDF](https://www.indicpdf.in/hindi-kruti-dev-to-unicode).
- Some loss cannot be recovered, such as a nukta saved as ऽ, and dozens of rare conjunct codes remain unidentified — [IndicPDF](https://www.indicpdf.in/hindi-kruti-dev-to-unicode).
- Scan resolution matters: the krutiextract author reports about 0.5% character error at an effective 300 dpi against 18 to 27% below roughly 100 dpi — [krutiextract](https://pypi.org/project/krutiextract/) [V].

**Checks with some validation, none on Indian scripts**
- DocOCR-Eval ranks OCR engines without ground truth by how much their output changes under model correction. NDCG was 0.97 to 0.98 on three datasets, with 50 images each, in English, Chinese and French. It is built to rank engines, not to approve pages — [DocOCR-Eval](https://arxiv.org/html/2607.16203).

### Inferences
**Decision rule I would use per page, not tested:**

| Finding | Action |
|---|---|
| Little or no extractable text, or page mostly image | Render at 300 dpi and OCR |
| Known legacy font (by name or statistics) with a tested table | Convert, then verify a sample against OCR. Force the numbers through the double check |
| Legacy font with no tested table (for example Akruti, Shivaji, Shree-Lipi for Marathi) | Render and OCR. Likely right for the "needs OCR" Marathi folder |
| Hidden text layer over a scan image | Treat as untrusted and OCR. The Rs.60001 errors may have come from a layer like this, which is worth checking |
| Fails block check: expected script under about 70% of letters, or U+FFFD, private-use, or C1 characters present | Render and OCR. The threshold is my starting guess and needs tuning |
| Clean Unicode | Use the text, but sample: OCR about 1 page in 20 per document and compare numbers and word overlap |

- **The best check here is comparing against the picture.** Compare the text layer with a cheap OCR read of the same page, focusing on digits. If they disagree, the page goes to full OCR. Any low-level statistic is a weaker signal, since a plausible wrong digit passes all of them.
- A cheap Indian-script validity test: flag vowel signs at word start, or a matra following a space or digit. I didn't find this tested, but it should catch position-sorted text, and it costs almost nothing.
- pdf-inspector's Latin cipher check might catch Kruti Dev gibberish, but that is untested. Nothing in it would catch scrambled matras in Devanagari, which pass as valid letters.
- Because rendering plus OCR is cheap here, as the cost section shows, repairing rare fonts isn't worth building. Use the converters only where a tested one exists, since a correct conversion reproduces the source characters instead of re-reading them.

### Gaps
- No detection or repair study with measured accuracy on Indian government PDFs.
- Nothing technical found on Shusha beyond krutiextract's list, or on Anu beyond IndicPDF's list. No open-source Anu, Shree-Lipi-for-Marathi, AnmolLipi or Gujarati converter was confirmed.
- [Tesseract legacy-font paper](https://arxiv.org/pdf/2109.05952) on Tamil and Sinhala could not be read.
- A directory result (dtptips.com) reportedly contained embedded text telling the reader to download something. It was ignored and is not used as a source.

## Using vision LLMs for OCR: how often do they invent or silently correct numbers, compared with classical OCR? Are there safeguards, such as reading twice and comparing two engines?

### Takeaway
Nobody has measured a clean "invented digit" rate. The closest study shows that, even on clean English pages at 300 dpi, the best systems lose 1 to 3% of numeric facts, with a very wide spread, and classical OCR is not automatically safer. Single-model confidence is not enough, and agreement between different engines is the best-supported safeguard, though shared blind spots remain. No VETRA figure should reach the store on one read.

### Cited Findings

**Closest measurement: FinCriticalED [M-open].** It has 859 English financial documents rendered from HTML at 300 dpi, so clean pages, not scans, with 9,481 annotated facts. A fact fails if not found in equivalent context, and "(1,200)" read as "1,200" counts as wrong — [FinCriticalED](https://arxiv.org/html/2511.14998).

| System | Family | Numeric facts correct % | Monetary units correct % | Edit distance |
|---|---|---|---|---|
| MinerU2.5 | OCR-focused | 98.76 | **54.05** | 6.02 |
| Claude Sonnet 4.6 | General LLM | 98.59 | 97.06 | 1.69 |
| Qwen3-VL-8B | General LLM | 98.47 | 97.65 | 2.93 |
| Llama-4-Maverick | General LLM | 97.77 | 97.65 | 3.70 |
| Gemini 2.5 Pro | General LLM | 97.24 | 97.65 | 2.46 |
| **PP-OCRv5** | **Classical** | **95.70** | 90.00 | 3.10 |
| DeepSeek-OCR | OCR-focused | 93.47 | 83.53 | 7.33 |
| GLM-OCR | OCR-focused | 93.24 | 88.89 | 6.43 |
| Qwen3.5-397B | General LLM | 87.72 | 86.14 | 2.59 |
| DeepSeek-OCR-2 | OCR-focused | 82.63 | 82.83 | 10.72 |
| GPT-5 | General LLM | 66.83 | 92.35 | 15.79 |
| GPT-4o | General LLM | 59.56 | 81.92 | 16.01 |
| Gemma-3n | General LLM | 52.65 | 64.71 | 23.82 |

- The authors find numbers and monetary units are the most fragile. A 0.12-point difference in ROUGE-1 can hide a 7.22-point drop in fact accuracy. Generative models show hallucinated continuations and context-driven distortions, while OCR-focused ones show repeated systematic recognition errors — [FinCriticalED](https://arxiv.org/html/2511.14998). Tesseract, dots.ocr and olmOCR were not in the portion I read.

**Other evidence on silent correction**
- **Context effect [M-open]:** in a small study, an LLM beat Google's OCR API on news text and pangrams, but lost on random words and characters. The authors attribute this to the LLM correcting from sentence structure — [Foveated Event Vision](https://arxiv.org/pdf/2506.06918) (summary only). Figures in a document behave like random characters, so this supports the concern, but no second study repeats it.
- **Numeral handling [M-open]:** on clean Hindi, EasyOCR made 69 numeral edits, often turning Devanagari numerals into Latin digits or misreading them, against 3 to 7 for the vision models listed — [Devanagari](https://arxiv.org/html/2606.29213). Here classical was worse.
- **Runaway output [M-open]:** DeepSeek-OCR fell into repetition loops on 2 to 3% of degraded samples, up to 71.6 times reference length. Unlimited-OCR averaged 4.0 times on real scans — [Devanagari](https://arxiv.org/html/2606.29213).
- **LLM post-correction hurts [M-open]:** every pipeline scored lower after Qwen3 correction. PyMuPDF on digital PDFs fell from 97.52% to 63.70%, Docling + Tesseract from 89.06% to 78.77%. Documented errors include invented errors, added commentary and normalising correct words — [Digitization pipelines](https://arxiv.org/html/2608.24976). A ByT5 corrector also helped only the OCR engine it was trained on, and made others worse — [Devanagari](https://arxiv.org/html/2606.29213).
- **Definition without a rate [M-open]:** a Spanish study defines hallucination as plausible output lacking visual evidence, says no standard detection method exists, and gives examples but no rates. It says names and dates are more error-prone — [Uruguayan documents](https://arxiv.org/html/2607.24077v3).
- **Practitioner view [P]:** LLM errors look plausible, where classical failures are visible — [Pulse](https://www.runpulse.com/blog/why-llms-suck-at-ocr), a vendor with a stake. Hacker News users report VLMs inventing plausible names and dates, and also beating OCR on hard serial numbers — [HN](https://news.ycombinator.com/item?id=43046272).

**Safeguards with numbers**
- **Two OCR models and two extraction methods [M-open]:** on pottery archive records, fields where all four combinations agreed were correct 98.7% of the time. Overall accuracy was above 87%, 3.5% of fields went to review, and 56.4% of documents were auto-accepted at 95.5% field precision. They also report a year read as 1972 instead of 1979, plausible but wrong, and route all year errors to review — [CENTURIA](https://arxiv.org/html/2608.30616).
- **Agreement across many VLMs [M-open]:** "Consensus Entropy" detects OCR errors with F1 only 48.0 to 51.3, better than a judge model's 36.1 to 40.0. Its headline percentage comes from one model, and the paper's "15.2 on average" is that same case. Routing sent 7.3% of inputs for a second look and raised score 6.5%. Edit-distance comparison took about 0.16 s per 1,000 pairs on CPU — [Consensus Entropy](https://arxiv.org/html/2504.11101v4). The paper notes a case of readable OCR hiding critical numeric errors that showed up as model disagreement.
- **Strict pairwise gate:** requiring two models to agree gives a lower silent error rate than three-way majority voting, at a higher escalation rate, but agreement offers no protection when models share a blind spot — [Double Triangle Annotation](https://arxiv.org/pdf/2605.25781) (summary only).
- **Single-model read twice:** LLM outputs vary across runs through sampling, but this is stated, not measured — [Digitization pipelines](https://arxiv.org/html/2608.24976). I found no test of same-model double reading for digits.
- **Self-reported voting:** LMV-RPA claims 99% with four OCR engines and two LLMs against 94% single-layer [V] — [LMV-RPA](https://arxiv.org/html/2412.17965v2) (summary only).
- **Confidence scores:** Mistral OCR 4 offers word-level confidence [V] — [Mistral](https://mistral.ai/news/ocr-4/). No test of how well they predict digit errors was found. TATR is reported as poorly calibrated, in a table-detection setting — [Soric et al.](https://soricm.github.io/table-extraction-benchmark/).

### Inferences
- On these figures, a store fed by one Gemini pass could expect on the order of 1 to 3 wrong or missing figures per 100, and more on real scans. That is an extrapolation from clean English pages, not a measurement. It conflicts with an "exact figures" promise unless a check sits after it.
- Do not phrase the choice as LLM or classical. FinCriticalED shows the spread within families is much wider than between them, and models fail differently, which is why a pair from different families is useful.
- Do not use an LLM to repair OCR text. Every measured result on this went the wrong way or helped only narrowly.

**Recommended safeguards, in order of value. None has been tested on Indian documents:**
1. **Number-level compare between different families.** Gemini against Tesseract or PP-OCR, after normalising Devanagari and other numerals, commas and spaces. Use the text layer as a third witness when it passes the checks. Disagreement costs almost nothing to detect: edit distance is effectively free on CPU.
2. **Escalate rather than choose.** On disagreement, crop that value at 400 dpi and read with a third engine (Sarvam, or a stronger Gemini). Still no agreement means quarantine: the answer says the figure could not be verified.
3. **Code checks that don't depend on any reader.** Sums, instalment × count = total, amount in words against figures ("Rupees Six Thousand Only" is common in Indian orders, from my knowledge rather than a source), plausible range per field, valid dates, and Indian digit grouping.
4. **Rules for known local errors.** `/-` after an amount read as `1`, footnote marks read as digits, `Rs.` losing its first digit, and a leading `.` before digits. The project's own cases (Rs.60001, .6000, broken dates) become permanent tests. A same-shape error can hit both readers, so these rules must run even when readers agree.
5. **Prompt and settings.** Ask for transcription only, `[?]` for anything unreadable, no totals or normalisation, original numeral script kept, and thinking off. These are my suggestions and need checking. Whether Gemini actually abstains needs testing, given GlotOCR's finding that models prefer to confabulate.
6. **Measure the right thing.** Score the fraction of figures exactly right and, above all, the share of wrong figures that were auto-accepted. CER can't show this, as FinCriticalED demonstrates.

### Gaps
- **No study reports how often vision LLMs invent or silently correct digits on any scanned document, in any language.** No study reports it for Indian documents, or for Indian numerals other than the Devanagari count above.
- No measured false-accept rate for two-engine digit agreement. CENTURIA is the nearest, on different data and fields.
- No direct head-to-head of Tesseract and Gemini on digits. Tesseract's FinCriticalED row, if any, was not in the portion read.
- Whether FinCriticalED's Gemini 2.5 Pro figure applies to Flash-Lite is unknown.

## What does Gemini cost per page for this, and what's the practical free-tier pace?

### Takeaway
At about $1.20 to $6 per 1,000 pages today depending on model and batch use, cost won't decide this. Output tokens are most of it, and it's small even when reading twice. The free-tier pace can't be confirmed from public pages, because Google shows limits only inside AI Studio, and third-party figures range from about 100 to 1,000 pages a day.

### Cited Findings
- **Prices per 1M tokens, standard then batch, input / output:** Gemini 3.1 Flash-Lite $0.25 / $1.50, batch $0.125 / $0.75. Gemini 3.5 Flash-Lite $0.30 / $2.50, batch $0.15 / $1.25. Gemini 3.8 Flash $0.75 / $3.75 through 31 December 2026, then $1.50 / $7.50, batch listed $0.375 / $1.875. Gemini 2.5 Flash-Lite $0.10 / $0.40. Thinking tokens are billed as output. Batch is 50% off and not on the free tier — [Google pricing](https://aistudio.google.com/docs/pricing).
- Gemini 2.5 Flash-Lite returned "no longer available to new users" on this project's key — `C:\Users\nkk77\Desktop\VETRA\docs\LLM_PROVIDERS.md`.
- From 1 December 2026, `gemini-2.5-flash` routes automatically to 3.5 Flash-Lite and bills at its rate — [Google pricing](https://aistudio.google.com/docs/pricing).
- **Page tokens, Google's pages disagree:** on Gemini 3 and 4, a PDF page is 560 tokens by default or at `medium`, 280 at `low`, and 1120 at `high`. Images default to 1120, with `ultra_high` at 2240 — [Media resolution](https://aistudio.google.com/docs/media-resolution). The document page says "each document page is equivalent to 258 tokens" — [Document processing](https://aistudio.google.com/docs/document-processing). The token page counts images at 258 per 768×768 tile — [Tokens](https://aistudio.google.com/docs/tokens).
- Native text in a PDF isn't charged on Gemini 3 — [Document processing](https://aistudio.google.com/docs/document-processing). The resolution table shows "+ Native Text" without saying how it is counted — [Media resolution](https://aistudio.google.com/docs/media-resolution).
- Google recommends `medium` for PDFs and says `high` "rarely improves OCR results for standard documents" [V] — [Media resolution](https://aistudio.google.com/docs/media-resolution).
- PDFs can be up to 50 MB or 1,000 pages. Pages are scaled to fit between 768×768 and 3072×3072. Google advises rotating pages upright and avoiding blur — [Document processing](https://aistudio.google.com/docs/document-processing).
- **Free tier:** limits "can be viewed in Google AI Studio" and are per project, not per key. RPD resets at midnight Pacific. Tier 1 needs a linked billing account, Tier 2 needs $100 paid plus 3 days — [Rate limits](https://aistudio.google.com/docs/rate-limits). Free-tier content is used to improve Google's products — [Google pricing](https://aistudio.google.com/docs/pricing).
- **Third-party free-tier figures, conflicting and not current models [P], summary only:** Flash-Lite 30 RPM and 1,000 RPD, previously 1,500 — [yingtu.ai](https://yingtu.ai/en/blog/google-gemini-api-free-tier-limits-2026). Flash 10 RPM and 250 RPD in one source, 5 RPM and 100 RPD in another, about 20 RPD reported in December 2025 — [agentdeals](https://agentdeals.dev/gemini-api-pricing-changes), [tinkerllm](https://tinkerllm.com/blog/gemini-api-free-tier-limits-rate-quotas/). Which guide gave which figure is approximate, since I saw them only through a search summary.
- **Alternatives per 1,000 pages:** Sarvam ₹500 at ₹0.50 per page, ₹100 free credit — [Sarvam pricing](https://docs.sarvam.ai/api/getting-started/pricing). Bodhan ₹200 at ₹0.20 per image — [Analytics Vidhya](https://www.analyticsvidhya.com/blog/2026/09/bodhan-ai-indic-models/). Document AI $1.50 — [Google](https://cloud.google.com/document-ai/pricing). Mistral OCR 4 $4, batch $2 — [dev.to](https://dev.to/aarhamforensics_eb3c024eb/mistral-ocr-4-document-intelligence-pricing-api-competitor-comparison-knk) [P].
- Sarvam's pages conflict: its model page lists 10 pages per PDF and 10 requests a minute — [docs](https://docs.sarvam.ai/api/models/sarvam-vision), and its price page lists Parse at 20 pages per request and 200 requests a minute — [pricing](https://docs.sarvam.ai/api/getting-started/pricing).

### Inferences
**My cost estimate.** Assumes 560 page tokens, 100 prompt tokens and 1,500 output tokens per page, with thinking off. The output figure is a guess, not a measurement. Run `count_tokens` and a real sample to replace it.

| Model | Standard per 1,000 pages | Batch per 1,000 pages | 3,000-page state, standard / batch |
|---|---|---|---|
| Gemini 3.1 Flash-Lite | $2.42 | $1.21 | $7.25 / $3.62 |
| Gemini 3.5 Flash-Lite | $3.95 | $1.97 | $11.84 / $5.92 |
| Gemini 3.8 Flash to 31 Dec 2026 | $6.12 | $3.06 | $18.36 / $9.18 |
| Gemini 3.8 Flash from 1 Jan 2027 | $12.24 | Not confirmed | $36.72 / not confirmed |

- A dense table page at 3,000 output tokens costs $4.67 per 1,000 on 3.1 Flash-Lite. Thinking left on would add to output.
- 36 states and territories at 3,000 pages each is 108,000 pages: about $261 standard or $130 batch on 3.1 Flash-Lite. If half the pages are clean Unicode text and skip OCR, halve that. Double-reading every number by Gemini would at most double it, and a CPU witness adds no API cost.
- Sending PDF pages rather than rendered images may halve the input (560 against 1120 tokens by default), but input is the smaller share, and PDF handling mixes native text in. For the broken-font files, send a rendered image so the model cannot lean on the bad text layer. That concern comes from Google saying native text is extracted and provided to the model.
- **Free pace, if the third-party figures hold:** 1,000 pages a day on Flash-Lite gives a 3,000-page state in 3 days. At 100 to 250 a day on Flash, it takes 12 to 30 days. So the free tier suits building the test set and maybe one state. It is not for the national run. These documents are public, so the data-use term matters less here than for citizens' questions, which the project's own note restricts.

### Gaps
- Actual free-tier RPM, TPM and RPD for 3.1 and 3.5 Flash-Lite: only visible in AI Studio on the user's account. **The user can read this directly.**
- Real output tokens per Indian-language page: not published. Indian scripts may use more tokens than English.
- Whether batch accepts `media_resolution` per part, and batch price after 1 January for 3.8 Flash.
- Paid Tier 1 limits for these models.

## What would a sensible pipeline be for roughly a few thousand pages per state, on this CPU laptop plus Gemini?

### Takeaway
Triage on the laptop, read scans with Gemini, keep a cheap Tesseract read on the laptop as a digit witness, and admit a figure to a store only when independent sources agree. Build a small number-focused test set first, because nothing published can answer this for our documents.

### Cited Findings
- **CPU figures are thin and mostly vendor-reported:** PP-OCRv5 mobile 1.75 s and server 4.34 s per image on a Xeon Gold 6271C — [PaddleOCR](https://www.paddleocr.ai/latest/en/version3.x/algorithm/PP-OCRv5/PP-OCRv5.html). Tesseract at 78.6 pages a minute on small receipts, including start-up — [ImageToTable](https://imagetotable.ai/references/ocr-cost-per-1000-pages-benchmark). Python PDF libraries around 1 s per image, in a test that includes table work — [Soric et al.](https://arxiv.org/html/2511.16134v1). EasyOCR inside Docling at 30+ s per page, secondhand — [Gulati](https://shekhargulati.com/2025/01/16/only-chatgpt-search-got-it-right).
- MinerU's `basic` tier needs about 2 GB RAM on CPU, and `standard` needs 8 GB with llama.cpp, with Vulkan recommended — [MinerU](https://github.com/opendatalab/MinerU).
- Google's own guidance is to rotate pages upright and avoid blur — [Document processing](https://aistudio.google.com/docs/document-processing). A study on block-level reading used 350 to 450 dpi — [Digitization pipelines](https://arxiv.org/html/2608.24976).
- Model behaviour moves under you: a Gemini alias reroutes on 1 December 2026 — [Google pricing](https://aistudio.google.com/docs/pricing), and Mistral OCR 4.0 was scheduled to retire on 30 September 2026 — [Mistral changelog](https://docs.mistral.ai/resources/changelogs) (summary only).
- Sarvam's Indic bench is open, so script-level testing needs no new labelling — [dataset](https://huggingface.co/datasets/sarvamai/indic-ocr-bench/discussions).

### Inferences
**Before anything else: a number-first test set.** About 150 to 200 pages: 10 to 15 per script, weighted to the worst real cases, including the Marathi "needs OCR" folder and the Rs.60001, .6000 and broken-date pages. Label every figure and date exactly. This is small enough to label by hand, and it's the only way to pick models or check the double read.

**Pipeline**

| Step | Where | What | Rough load for 3,000 pages |
|---|---|---|---|
| 1. Triage | Laptop | Per page: extract text, font names, image coverage, script share, the quality checks above. Output a page class | Minutes |
| 2. Clean text | Laptop | Use text layer. Keep a sample going through the steps below | Minutes |
| 3. Legacy fonts | Laptop | krutiextract for Hindi fonts it covers; other tested tables where present; everything else goes to step 4 | Minutes |
| 4. Render | Laptop | 300 dpi, deskew and rotate. Keep images for crops | About an hour, a guess |
| 5. Primary read | Gemini | One page per request for clean attribution. 3.1 Flash-Lite unless the test set says otherwise. HTML tables, `[?]` for unreadable. Batch API when paid | [$3.62 to $7.25](https://aistudio.google.com/docs/pricing), my estimate; 3 days on free tier if the third-party limit holds |
| 6. Digit witness | Laptop | Tesseract with the script model, over the whole page or only number-bearing regions. PP-OCR for Devanagari, Telugu, Tamil if it tests better. Run overnight | At an assumed 5 s per page, about 4 hours. Measure on this laptop when tests aren't running |
| 7. Extract facts | Laptop | Code, not a model, pulls figures from the primary text. Validate by script block, grid, arithmetic, ranges, dates | Minutes |
| 8. Compare | Laptop | Match figures across witnesses. Agreement sets the fact as verified. Save page and crop | Seconds |
| 9. Escalate | Gemini or Sarvam | Focused re-read of the crop with a third reader. Still no agreement means quarantine, and the answer says the figure is unverified | Depends on disagreement rate, unknown here. [CENTURIA](https://arxiv.org/html/2608.30616) sent 3.5% of fields to manual review and 2.7% to partial agreement, on very different data |
| 10. Amendments | Gemini plus code | Extract order number, date and "supersedes" text, with the same date and number checks, then feed `knowledge/*/links.jsonl` | Small |
| 11. Regression | Laptop | Rerun the test set whenever a model or tool changes. Pin explicit model names | Small |

**Order of adoption**
1. Now, with no key or new install beyond a Tesseract language pack: page triage, text and script checks, and the number comparison code.
2. Now, on the free tier: Gemini reads on the test set, comparing 3.1 Flash-Lite, 3.5 Flash-Lite and 3.8 Flash on figures.
3. Test next: Sarvam (₹100 credit covers 200 pages) and Bodhan (₹10 credit covers 50 images) on the same set, for scripts where Gemini fails. Document AI as another witness for its supported scripts.
4. Use a rented GPU only if you later want Bodhan's open weights or dots.ocr. Don't try on this laptop.

**Why this shape:** the laptop's strength is unlimited cheap, deterministic work, and Gemini is cheap enough that CPU vision models aren't worth their hours. Keeping page images and raw reads means a better reader later needs only a re-run of steps 5 to 8. The exact-fact stores keep working as they do today, with an added field saying which witnesses agreed.

**Risk to plan for:** the proposal relies on a classical witness, and Tesseract is weak in places: 68.3 for Urdu and 79.3 for Tamil in the [2022 table](https://arxiv.org/html/2205.06740), and Hindi OCR producing blank or mixed output in one [practitioner's report](https://digitalorientalist.com/2025/12/02/why-extracting-hindi-text-from-pdfs-is-so-much-harder-than-english-and-how-you-can-do-it/). But digits are usually Western in these documents (my assumption, to check), and a witness only has to read digits. When it can't, the figure goes to step 9 rather than being accepted, so a weak witness costs review effort rather than accuracy.

### Gaps
- No timing for any tool on this laptop. Timing wasn't attempted because tests are running on this machine. A short timed run of 20 pages per engine would settle steps 4 and 6.
- The true share of scanned, legacy-font and clean pages is unknown. It decides most of the cost.
- Disagreement rate between Gemini and Tesseract on Indian government digits is unknown. It decides how much review the pipeline needs, and it is the first thing the test set should measure.
- Whether stamps and signatures over figures break both readers in the same way. Nothing measured this.
