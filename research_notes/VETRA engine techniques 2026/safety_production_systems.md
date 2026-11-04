# Safety, prompt injection and real production systems for VETRA (checked 5 November 2026)

Tags: **[Primary]** the organisation's or authors' own document, read by me. **[Secondary]** press or law-firm reporting. **[Vendor]** the builder reporting on its own system. **[Snippet]** seen only in search results, page not opened. **Measured** means a number from a stated test. **Claim** means no method was published.

This is research, not legal advice. Complexity is my estimate: S is under a day, M is a few days, L is weeks. VETRA code was read but not run, because tests are running on this machine.

## 1. What do deployed agricultural and government systems show?

### Takeaway
Only GOV.UK Chat and Farmer.Chat publish enough to learn from, and both are reports on their own systems. Almost every Indian government deployment publishes usage counts with no accuracy figure, so VETRA can't borrow a benchmark from them and will have to measure itself.

### Cited Findings

**GOV.UK Chat (the strongest public evidence)**
- Measured, self-reported: internal benchmark accuracy rose from 76% to 90% across all topics, scored by subject experts and automated tools. An answer counted only if it met all published-content standards. Over 10,000 users asked about 26,000 questions across 2 pilots (web: 10,136 users, 23,838 questions; app: 641 users, 2,670 questions) — [GDS, March 2026](https://insidegovuk.blog.gov.uk/2026/03/16/5-things-we-learned-testing-gov-uk-chat-an-ai-assistant-for-government) [Primary, Vendor]
- Measured, self-reported: the answer rate for in-scope questions is 88%. Ambiguous phrasing produced no answer, so clarifying questions were added — [GDS](https://insidegovuk.blog.gov.uk/2026/03/16/5-things-we-learned-testing-gov-uk-chat-an-ai-assistant-for-government) [Primary]
- Measured, self-reported: 508 jailbreak attempts were recorded, and guardrails prevented all of them. By my arithmetic that is about 1.9% of 26,508 questions. It counts only attempts that were detected, among recruited pilot users — [GDS](https://insidegovuk.blog.gov.uk/2026/03/16/5-things-we-learned-testing-gov-uk-chat-an-ai-assistant-for-government) [Primary]
- Some users wanted advice using their own information or an adviser with their records. Handoff to departments is planned, not built — [GDS](https://insidegovuk.blog.gov.uk/2026/03/16/5-things-we-learned-testing-gov-uk-chat-an-ai-assistant-for-government) [Primary]
- 73% found it useful and 64% were satisfied, in a survey of app users. The app study's method list gives only 45 survey responses, so these percentages may rest on a small sample. Average response time was 10.7 seconds, and satisfaction rose when faster speeds were simulated. Streaming tested well but would need safety guardrails redesigned — [GDS](https://insidegovuk.blog.gov.uk/2026/03/16/5-things-we-learned-testing-gov-uk-chat-an-ai-assistant-for-government) [Primary]
- Guardrails are extra LLM calls: one jailbreak check on the input, and one multi-category check on the output (personal data, advice on anything illegal, political rhetoric). The page warns it may be out of date, and the full rule set is in a private repository — [GOV.UK developer docs](https://docs.publishing.service.gov.uk/repos/govuk-chat/guardrails.html) [Primary]
- Pages likely to hold personal data are removed from the searchable database. Conversations are kept 12 months. The model is Claude on AWS Bedrock in government accounts, and the notice says Anthropic has no access to the data — [GOV.UK privacy notice](https://www.gov.uk/government/publications/govuk-chat-privacy-notice/govuk-chat-privacy-notice) [Primary]

**Farmer.Chat (Digital Green)**
- Measured, self-reported, mostly Kenya: close to 75% of questions answered. Of unanswered questions, 66% were missing from the content, 23% were non-agricultural and 11% were unsupported crops. Faithfulness was high for nearly 80% of answers, and relevance was high for 67%. Context precision was 71% over 1,000+ queries, and average response time 9.05 seconds — [Farmer.Chat paper](https://arxiv.org/html/2409.08916) [Primary, Vendor]
- Measured: 35% of users produced nearly 80% of queries, and clickable follow-up questions made up over 45% of interactions in peak periods. Among even the top 5% of users, 41.7% of questions were only "somewhat clear" — [Farmer.Chat paper](https://arxiv.org/html/2409.08916) [Primary, Vendor]
- Satisfaction surveys were two rounds of about 20 people, and one round's counts add up to 22 rather than 20. Gender red-teaming scored 59/60, weakest on gender-based violence questions. No pesticide-hazard test results are reported, although Kenya's content includes banned chemicals and pesticide hazards — [Farmer.Chat paper](https://arxiv.org/html/2409.08916) [Primary, Vendor]
- 66% of 450 Kenyan farmers reported acting on a response. I saw this only in a search summary, and it is self-reported behaviour — [60 Decibels](https://60decibels.com/?p=5673) [Snippet]
- IFPRI's independent test in India and Kenya has no results yet: official results will be published once analysis is complete — [Rural 21](https://www.rural21.com/english/news/detail/article/testing-ai-advisory-services-insights-from-farmerchat-in-india-and-kenya.html) [Secondary]

**AIEP (Gates Foundation, GIZ and partners), across several builders including Digital Green**
- 114 golden question-answer pairs were checked by agronomists and aren't public. Digital Green has about 5,000 curated pairs for Bihar in English and Hindi. LLM-as-judge tracked human ratings fairly well, while lexical and embedding metrics were mixed — [AIEP paper](https://arxiv.org/html/2601.11537v1) [Primary]
- Measured: 800+ farmers surveyed, with an average NPS of about 60. 33% said information was hard to understand, more often those with less education, and the sample was more educated than the average smallholder (30% with a university degree or higher). Among those who didn't act on advice, 50% cited input availability or money — [AIEP paper](https://arxiv.org/html/2601.11537v1) [Primary]
- Phone and IVR channels were called "indispensable" for women, elderly and nonliterate farmers. Combined speech recognition plus translation performed substantially worse than either alone in Gikuyu. RAG is "not a full safety mechanism" — [AIEP paper](https://arxiv.org/html/2601.11537v1) [Primary]

**Indian government and related systems (usage counts, no published accuracy)**
- Kisan e-Mitra: 11 languages and 49 query categories. Reported daily volumes conflict (8,000 versus 20,000), with about 9.2 to 9.3 million answered in total. I found no accuracy evaluation — [Wadhwani AI](https://www.wadhwaniai.org/empowering-millions-of-indian-farmers-with-instant-ai-chatbot-support/) [Vendor]; [Telecom Talk](https://telecomtalk.info/indian-government-deploys-ai-technologies-farm-productivity/1002484/) [Secondary]; [Construction World](https://constructionworld.in/policy-updates-and-economic-news/kisan-e-mitra-and-iot-enabled-systems-boost-agricultural-productivity/71284) [Secondary]
- Bharat-VISTAAR (not on your list, launched around February 2026): a voice helpline, 155261, built for basic feature phones, plus website and chatbot, in Hindi and English for phase 1. It covers weather, prices, pest alerts and at least ten central schemes. No accuracy or usage results are reported — [Open Magazine](https://openthemagazine.com/india/bharat-vistaar-explained-how-the-governments-ai-tool-will-support-farmers) [Secondary]
- Jugalbandi: 10 languages and 171 schemes in 2023, with anecdotes only, including farmers asking why assistance payments stopped. Microsoft itself says the models sometimes make errors — [Microsoft](https://news.microsoft.com/source/asia/features/with-help-from-next-generation-ai-indian-villagers-gain-easier-access-to-government-services/) [Vendor]
- Sarvam: UIDAI voice agent in 10 languages, hosted on-premise, with no accuracy figure — [Business Standard](https://business-standard.com/finance/personal-finance/now-get-aadhaar-multi-language-services-via-ai-voice-to-detect-fraud-125032400486_1.html) [Secondary, Snippet]. The Odisha figure of 77% seed receipt is a survey finding, not answer accuracy, and "95%+ policy accuracy" for a health-authority training is a claim with no method I could see — [Sarvam, Listen at Scale](https://www.sarvam.ai/stories/ekstep) [Vendor, Snippet]
- AgriLLM is a research model, not a deployment. It trained on about 4 million Tamil Nadu KCC records. Government scheme answers scored lowest on BLEU (0.443, against 0.628 for fertiliser). These scores measure overlap with the expert's words, not correctness — [AgriLLM](https://arxiv.org/html/2407.04721v2) [Primary]
- Krishi Sathi (BharatGen) reports 97.53% query response accuracy. The abstract gives no definition or test size, so treat it as a claim — [arXiv](https://arxiv.org/abs/2508.03719) [Primary, Vendor]

**Outside India**
- NYC MyCity told businesses things that broke the law, such as refusing Section 8 vouchers and cash. The city added a warning that responses weren't legal or professional advice and kept the bot running. A new mayor called it "functionally unusable", citing a cost of around $500,000, and it was removed on 4 February 2026 — [The Markup](https://themarkup.org/artificial-intelligence/2026/01/30/mamdani-to-kill-the-nyc-ai-chatbot-we-caught-telling-businesses-to-break-the-law) [Secondary, original investigator]
- Singapore's Pair is a tool for public officers, not citizens. More than half of 150,000 officers are said to use it regularly, and no public accuracy report turned up — [The Star](https://www.thestar.com.my/aseanplus/aseanplus-news/2026/06/02/singapore-to-create-a-registry-of-ai-agents-for-150000-public-officers-amid-ai-push) [Secondary, Snippet]; [Pair report](https://reports.open.gov.sg/pair) [Vendor, Snippet]
- Ask Sage: FedRAMP High is a security authorisation, not evidence of answer quality. The "98% accuracy" figure is about compliance paperwork in a marketing case study — [Ask Sage](https://asksage.ai/press-releases/ask-sage-receives-fedramp-r-high-authorization) [Vendor, Snippet]; [Carahsoft](https://www.carahsoft.com/resources/25711-how-ask-sage-achieved-compliance-in-record-time-with-chainguard) [Vendor, Snippet]

### Inferences

| Lesson | Evidence | VETRA change | Size | Call |
|---|---|---|---|---|
| Personal-status questions ("why did my payment stop?") can't be answered from documents, and people ask them | GOV.UK users asked for this, and Jugalbandi's anecdotes match. No rate is published | Detect them in the planner, then say what the record would show, where to check it, and who to call. Don't guess | M | Adopt now |
| Being official raises over-trust. GDS's 2024 experiment reported that some users underestimated inaccuracy risk because of the GOV.UK brand ([GDS 2024, via mirror](https://hn.jakechampion.name/reader/https://insidegovuk.blog.gov.uk/2024/01/18/the-findings-of-our-first-generative-ai-experiment-gov-uk-chat)) [Snippet] | Qualitative only | `vetra/web.py:28` titles the page "your government, from its own documents", and `vetra/agent.py:106` calls it "an Indian government assistant". Both imply an official service. Say plainly that it's independent and not a government service | S | Adopt now |
| Set a target for answering, not only for accuracy | 88% in-scope (GOV.UK) and about 75% (Farmer.Chat) are the only public reference points, with different scopes | Report answer rate beside accuracy on the test set. Treat these as context, not targets to copy | S | Adopt now |
| Most non-answers are content gaps | 66% (Farmer.Chat, self-reported) | Confirms `vetra/gaps.py`. Review the gap log weekly once live, without keeping question text | S | Adopt now |
| Ambiguous questions are normal | GOV.UK added clarifying questions. Farmer.Chat's clarity ratings show the same | One clarifying question when state or scheme is missing, not a refusal | M | Test |
| Tap-to-ask follow-ups help less literate users | Over 45% of interactions at peak (Farmer.Chat), though causation isn't shown | Offer 2 or 3 follow-ups, each checked to be answerable from the corpus | M | Test |
| Don't stream checked answers | GOV.UK says streaming would mean redesigning guardrails. Users accepted about 10 seconds | Keep checks before display, and show progress instead | S | Adopt now |
| Voice is the channel for those hardest to reach, and it is a separate pipeline | AIEP (qualitative), Bharat-VISTAAR's design. No measured split found | Keep it out of the MVP as planned, but test now with typed text that looks like speech recognition output | S | Adopt now (test text only) |
| Government AI can be shut down over a few bad answers | One case, MyCity | Publish how VETRA is tested, and have an off switch for a topic or the whole service | S | Adopt now |

Bharat-VISTAAR is a free government service covering central schemes in Hindi and English, with a feature-phone line. VETRA's distinct value looks like state-level detail, more languages and checked citations, not general farm advice.

### Gaps
- No published accuracy, refusal or voice-share figures found for Kisan e-Mitra, Jugalbandi, UMANG, Bhashini-based bots, Bharat-VISTAAR or Sarvam's government work. I can't say that none exist internally.
- Nothing found on UMANG's AI features or any named Bhashini bot evaluation.
- "Krishi Sakhi" is ambiguous. Results showed a developer project with a self-reported 10,000 farmers ([Devfolio](https://devfolio.co/@shaswatkureel), Snippet) and a separate Agriculture Insurance Company programme for women farmers that isn't described as AI ([Chronicle India](https://www.chronicleindia.in/online-magazine/archive-csch-may-2026/krshi-sakhee-mahila-kisaanon-ka-sashakteekaran), Snippet). I couldn't verify a deployed Kerala system.
- Nothing usable on KissanAI or Dhenu evaluations.
- No US state chatbot evaluation or audit turned up in the one search I ran.
- FarmChat (34 farmers near Ranchi) compared audio and audio-plus-text by literacy, but it predates this window and I didn't read it ([UW](https://ubicomplab.cs.washington.edu/publications/farmchat), Snippet). IFPRI's Farm Vaidya report says speech recognition often fails in the field, but the page came back empty, so this is from a search summary only ([IFPRI](https://www.ifpri.org/?p=165838), Snippet).
- No study reports speech error rates by dialect or literacy in an Indian deployment.

## 2. What failed and worked in legal and financial RAG?

### Takeaway
Independent testing shows AI level with or ahead of a lawyer baseline on general research, but weaker on multi-jurisdiction questions and on source quality. Finding the right document is far easier than finding the right passage. Both failures map directly onto VETRA's all-state, cited design.

### Cited Findings
- Measured, independent but with a selection effect: in Vals' October 2025 legal research report, lawyers scored 71% on accuracy, against Counsel Stack 81%, Alexi 80%, ChatGPT 80% and Midpage 79%. Authoritativeness was 76% for legal tools on average against 70% for ChatGPT. Thomson Reuters and LexisNexis didn't opt in, and vLex withdrew — [LawSites on Vals](https://www.lawnext.com/2025/10/vals-ais-latest-benchmark-finds-legal-and-general-ai-now-outperform-lawyers-in-legal-research-accuracy.html) [Secondary]. The same article gives both 9 and 7 points for the gap over lawyers.
- Measured: multi-jurisdiction questions dropped 11 points on average against single-state questions. Some tools said they couldn't find the right documents but gave an explanation anyway. Technical non-responses also occurred — [LawSites](https://www.lawnext.com/2025/10/vals-ais-latest-benchmark-finds-legal-and-general-ai-now-outperform-lawyers-in-legal-research-accuracy.html) [Secondary]
- Measured: in Vals' February 2025 report, Harvey Assistant scored 94.8 on document Q&A. The lawyer baseline won redlining and EDGAR research, and Harvey withdrew from EDGAR — [Vals](https://vals.ai/vlair) [Primary, Snippet]; [LawSites](https://www.lawnext.com/2025/02/legal-ai-tools-show-promise-in-first-of-its-kind-benchmark-study-with-harvey-and-cocounsel-leading-the-pack.html) [Secondary, Snippet]
- Vendor benchmark: BigLaw Bench measures how much of a lawyer-quality work product a model completes, run by Harvey: GPT-5 at 89.22% and GPT-5.5 at 91.7%. A critic argues it doesn't test case-law research. I found no hallucination or citation percentage — [Harvey](https://www.harvey.ai/blog/introducing-biglaw-bench) [Vendor, Snippet]; [Artificial Lawyer](https://www.artificiallawyer.com/2025/08/08/gpt-5-tops-harveys-biglaw-bench-eval/) [Secondary, Snippet]; [Legalcomplex via Pulse](https://www.pulse.bot/legal/news/you-do-know-harveys-biglaw-bench-does-not-actually-test-case-law-research-right-65e0dc46-f4a9-4951-a907-fa735034cb22/) [Secondary, Snippet]
- Measured, 2023: on a 150-case FinanceBench sample, GPT-4-Turbo with a retrieval system answered incorrectly or refused on 81% of questions. That figure combines wrong answers and refusals. With long context it failed 21% of the time — [FinanceBench](https://arxiv.org/abs/2311.11944v1) [Primary, Snippet]; [Patronus](https://prnewswire.com/news-releases/patronus-ai-launches-industry-first-llm-benchmark-for-finance-to-address-hallucinations-301990858.html) [Vendor, Snippet]. A 2026 system reports 89.3% on it, self-reported — [MimirRAG](https://arxiv.org/html/2605.25030v1) [Snippet]
- Measured: FinAgentBench found document ranking nDCG@5 of 0.770 to 0.783 and chunk ranking of only 0.351 to 0.419 across three strong models. Fine-tuning added 0.05 and 0.026 respectively. The paper has no systematic error analysis — [FinAgentBench](https://arxiv.org/html/2508.14052v4) [Primary]
- IL-TUR found LLMs "far from solving" Indian legal tasks. I didn't read its tables — [IL-TUR](https://arxiv.org/abs/2407.05399v2) [Primary, Snippet]. NyayaRAG reports that adding retrieved statutes and precedents improves judgment prediction, and I have no numbers — [NyayaRAG](https://arxiv.org/html/2508.00709v3) [Primary, Snippet]
- Measured, closed-book exam questions: on BhashaBench-Krishi, top models exceed 70% in English and reach about 60 to 65% in Hindi, with regional crop management below 50% — [dataset card](https://huggingface.co/datasets/bharatgenai/BhashaBench-Krishi) [Primary]. In BhashaBench-Finance, problem solving reached 47.12% for top models — [BhashaBench-Finance](https://huggingface.co/datasets/bharatgenai/BhashaBench-Finance) [Primary, Snippet]

### Inferences

| Lesson | Evidence | VETRA change | Size | Call |
|---|---|---|---|---|
| Test per state, not on average | 11-point multi-jurisdiction drop, in US law | Report scores by state and flag questions spanning several states. An all-India average would hide failures | M | Adopt now |
| "Couldn't find it, but here's an explanation" is a distinct failure | Vals' observed failure | Add a test: when evidence is missing, the answer must stop rather than explain from memory. Fits the refusal scoring already planned in ARCHITECTURE_RESEARCH | S | Adopt now |
| Score the cited passage, not only the document | Chunk ranking far below document ranking (FinAgentBench) | Check that the cited passage itself supports the sentence. VETRA's citation checks may already do this, which I didn't confirm | S | Test |
| Keep arithmetic in code | Finance problem solving under 50%, closed-book | Confirms VETRA's code-checked figures. Don't let the model compute premiums or dose conversions | S | Already done, keep |
| Expect a language penalty | About 5 to 10 points English to Hindi, closed-book, not RAG | Measure each language separately. Don't assume English scores carry over | M | Adopt now |
| Don't use vendor legal benchmarks as a model | BigLaw Bench is vendor-run and legal drafting | No change | None | Skip |
| Indian legal benchmarks | Judgment prediction and legal NLP, not citizen Q&A | No change, except a look at IL-TUR if RTI grows | None | Skip |

### Gaps
- I read Vals' October findings through LawSites, not the report itself. The article also gives both 210 questions across nine types and 21 question types without reconciling them.
- Nothing on Harvey's own citation or hallucination rate.
- No Indian financial RAG benchmark turned up, and none on tax or scheme documents.

## 3. What did teams find about citation trust, stale information and source checking?

### Takeaway
People rarely click through, so citations can't be the safety net. Code checks and the date in the answer itself have to do that work. No deployed system I found publishes how often its users check sources, or a measured stale-answer rate.

### Cited Findings
- Measured, US: of 900 adults' Google browsing, links inside an AI summary were clicked in about 1% of visits to pages with a summary. Traditional results were clicked in 8% of visits with a summary against 15% without. This is search, not a government assistant — [Pew, July 2025](https://www.pewresearch.org/short-reads/2025/07/22/google-users-are-less-likely-to-click-on-links-when-an-ai-summary-appears-in-the-results/) [Primary, Snippet]
- Qualitative: GOV.UK users said they valued links and accuracy warnings for double-checking. GDS published no click rate, even though it analysed 4,764 user journeys — [GDS](https://insidegovuk.blog.gov.uk/2026/03/16/5-things-we-learned-testing-gov-uk-chat-an-ai-assistant-for-government) [Primary]
- Measured: across 22 public broadcasters and 18 countries, 45% of AI answers about news had at least one significant issue, and 31% had serious sourcing problems. Gemini had a significant sourcing issue in 72% of responses, others under 25%. The models tested are from 2025, and this was on news — [ASIS on EBU/BBC](https://www.asisonline.org/security-management-magazine/latest-news/today-in-security/2025/october/ai-assistant-news-inaccuracies/) [Secondary, Snippet]; [EBU/BBC report](https://www.mediaguru.cz/media/xfhplvup/report_ebu-mis-bbc.pdf) [Primary, not opened]
- MyCity didn't know the minimum wage and contradicted a 2020 city law. The reporting doesn't say whether stale data caused it — [The Markup](https://themarkup.org/artificial-intelligence/2026/01/30/mamdani-to-kill-the-nyc-ai-chatbot-we-caught-telling-businesses-to-break-the-law) [Secondary]

### Inferences

| Lesson | Evidence | VETRA change | Size | Call |
|---|---|---|---|---|
| Put the safety information in the answer, not behind the link | 1% click rate, from a different setting | Answer text states the source's name, its date and "check before acting" for money or deadlines, in the reply language | S | Adopt now |
| Log source clicks | No public rate exists | Count clicks without tying them to a person. It would be new evidence for India | S | Adopt now |
| Show evidence age | No measured stale rate, so this is judgment | State when the document was issued, and warn beyond a set age. Document updates are out of scope, so an honest age label matters more | S | Adopt now |
| Gemini's sourcing result is worth watching | One 2025 test on news questions, not of VETRA's retrieval | VETRA's code citation checks don't depend on the model's own sourcing. Confirm this holds on the Gemini models you adopt | S | Test |

### Gaps
- No Indian evidence on whether farmers or citizens check sources, or can read them. An official PDF in English may not help someone who asked in Santali, which is my inference and untested.
- No measured rate of stale answers in any deployed citizen assistant.

## 4. Are there real farmer or citizen question sets VETRA could use?

### Takeaway
Yes for farmers: Kisan Call Centre (KCC) data is the only large Indian source, and the catalogue lists an open licence. Digital Green's Kenyan set shows raw typed phrasing. I found no public log of real Indian citizen questions on schemes, tax or pensions.

### Cited Findings

| Dataset | Real questions? | Size and languages | Licence and access | Best use |
|---|---|---|---|---|
| [KCC on AIKosh](https://aikosh.indiaai.gov.in/home/datasets/details/kisan_call_centre_kcc_transcripts_of_farmers_queries_and_answers.html) [Primary], redirecting to [data.gov.in](https://www.data.gov.in/resource/kisan-call-centre-kcc-transcripts-farmers-queries-answers) (returned 403 to me) | Yes, calls with adviser answers, by district and month | Size not stated | "Open Government License, India" on AIKosh. Not confirmed on data.gov.in | Main source of farmer topics |
| [KCC-CHAKSHU](https://krishi.icar.gov.in/jspui/handle/123456789/81363) via ICAR [Snippet] | Yes | About 40 million calls since 2006 by one account; [32 million+ to 2023](https://arxiv.org/html/2407.04721v2) by another | Papers cite an ICAR Data Use Licence, terms unverified | Only if the open route falls short |
| [DigiGreen/Kenya_Agri_queries](https://huggingface.co/datasets/DigiGreen/Kenya_Agri_queries) [Primary] | Yes, anonymised, with typos, from a Telegram bot | 100K to 1M, English, Kenya | Apache-2.0. Anonymisation method not described | Vague, informal and off-topic phrasing. Not content |
| [DigiGreen/AgricultureVideosQnA2](https://huggingface.co/datasets/DigiGreen/AgricultureVideosQnA2) [Primary] | The card doesn't say; a [third party](https://scour.ing/@matmat/p/https://weval.org) says real [Snippet] | 1K to 10K, Hindi and Odia | Apache-2.0 | Hindi and Odia sample after checking |
| [DigiGreen/TranslationDataset_AgriQueries](https://huggingface.co/datasets/DigiGreen/TranslationDataset_AgriQueries/tree/main) [Snippet] | Agricultural query translations | 10K to 100K, Hindi, English, Latin-script Hindi | Listed Apache-2.0 | Romanised Hindi test cases |
| [BhashaBench-Krishi](https://huggingface.co/datasets/bharatgenai/BhashaBench-Krishi) [Primary] | No, 55+ official exams | 15,405, English and Hindi | CC BY 4.0, gated | Not a realistic test set |
| [BhashaBench-Multi](https://aikosh.indiaai.gov.in/home/datasets/details/bhashabench_multi.html) [Primary] | No | 22 Indian languages plus English, agriculture, finance, legal, Ayurveda | CC BY-NC 4.0, translation method not stated | Internal language stress test only, non-commercial |

- KCC records need work: run-on text had to be separated by hand, and doses appear in forms like "5gmlit" — [AgriLLM](https://arxiv.org/html/2407.04721v2) [Primary]

### Inferences

| Candidate | VETRA change | Size | Call |
|---|---|---|---|
| Sample KCC questions, stratified by state, season and query type, as test questions | Add to `eval/`. Use the question only. Never use adviser answers as ground truth, because they weren't checked against VETRA's documents | M | Adopt now, after confirming the licence on data.gov.in |
| Add Kenyan-style messiness | Rewrite patterns (typos, fragments, off-topic) onto Indian topics rather than copying the content | S | Adopt now |
| Write the citizen-finance set by hand | No public log exists, so draft from scheme FAQs and helpline topics, labelled synthetic | M | Adopt now |
| Use exam benchmarks as the main measure | They test recall, not answering from documents | None | Skip |

KCC questions may be advisers' typed summaries in English or Romanised text, not farmers' words. If so, they show topics rather than phrasing. Read a sample before relying on them.

### Gaps
- Couldn't open data.gov.in (403), so fields, dates and the licence there are unconfirmed.
- Unknown whether KCC text contains callers' names or numbers. Screen before use.
- Digital Green's 5,000 Bihar pairs and 2.2 million query corpus: no public release found.
- Whether any KCC-derived set covers the 22 languages: I found none.

## 5. Are read-only tools enough against indirect prompt injection?

### Takeaway
Read-only tools remove the worst outcome, an attacker making the system do something. They don't stop a poisoned or forged passage from producing a confident wrong answer, and that is VETRA's real exposure. VETRA's plan-first design holds up, but the risk now sits in evidence labels and source integrity, so a small planted-document test is worth doing before launch.

### Cited Findings
- Measured: adaptive attacks broke 12 recent defences, most above 90% success, where the original papers reported near zero. A human red-team competition reached 100% — [The Attacker Moves Second](https://arxiv.org/abs/2510.09023) [Primary, Snippet]. An earlier study broke all eight defences it tested at above 50% — [Adaptive Attacks](https://arxiv.org/pdf/2503.00061) [Primary, Snippet]
- Measured: CaMeL solves 77% of AgentDojo tasks with provable security against 84% undefended — [CaMeL](https://arxiv.org/abs/2503.18813) [Primary]. FIDES stops all AgentDojo injections with policy checks on, and without them all planners fall — [FIDES](https://www.microsoft.com/en-us/research/publication/securing-ai-agents-with-information-flow-control/) [Primary, Snippet]
- A 2026 preprint says action controls don't address poisoned summaries or misleading output, and that CaMeL lists this as a non-goal. It reports CaMeL's overhead at about 2.8 times input and 2.7 times output tokens. Workspace tasks showed 0% attack success even undefended, but the authors say that reflects a weak model on read-and-summarise tasks rather than a tested defence. It is preliminary and used a 7B model — [Narisetty et al.](https://arxiv.org/html/2606.26479v1) [Primary, not peer-reviewed]
- Measured: agent data injection (ADI) makes the model treat attacker text as trusted metadata rather than instructions. On AgentDojo with GPT-5.2, instruction injection succeeded 0.2% of the time and ADI 49.1%. Llama Prompt Guard 2 left it at 50.0%, and LlamaFirewall AlignmentCheck at 45.4%. Plan-then-execute (IsolateGPT) gave 40.7%. Only CaMeL Strict reached 0%, with utility falling from 86.5% to 36.5%. The paper tested web and coding agents and action tasks, not read-only agents, though it notes ADI can alter a final answer, such as fabricated reviews — [ADI paper](https://arxiv.org/html/2607.05120) [Primary]
- Mitigations it names: fine-grained policies, data-flow tracking, and random per-request nonces on field names, which worked for key-value formats only. Sanitising cut JSON attacks to 0 to 3%, with utility falling to 67.9 to 72.3% — [ADI paper](https://arxiv.org/html/2607.05120) [Primary]
- Measured: PoisonedRAG reached 90% attack success with 5 malicious texts per target question, in databases of millions of texts. Paraphrasing and perplexity checks weren't enough — [PoisonedRAG](https://arxiv.org/pdf/2402.07867) [Primary, Snippet]. Later defences report gains but are self-reported, and TriShieldRAG says it hasn't faced an adaptive attacker — [RAGDefender](https://arxiv.org/abs/2511.01268v1) [Snippet]; [TriShieldRAG](https://www.alphaxiv.org/abs/2607.23838) [Snippet]
- Unverified: one blog reports NIST's CAISI raising agent hijacking from 11% to 81% with adaptive attacks. I didn't check NIST's own publication — [Stingrai](https://www.stingrai.io/blog/prompt-injection-statistics-2026) [Secondary]
- VETRA code (read, not run): `vetra/web.py:127-129` accepts past questions and answers from the browser, and `vetra/agent.py:162` puts them into the planner prompt as `User:` and `Assistant:` turns.

### Inferences

What read-only design closes: sending data out through a tool, taking actions, and a document changing the plan, which is made before reading. Local search limits the outward path further.

What stays open for VETRA:
1. **False content in a real-looking source.** A hacked state site, or a forged PDF added by hand. VETRA's checks confirm a figure appears in the evidence, not that the evidence is true.
2. **Forged labels.** A document containing text that imitates VETRA's evidence labels, such as a fake "in force" status or fake state. This is ADI's idea applied to VETRA, and it's untested here.
3. **Direct jailbreaks by users.** Effects are limited to that user, but a screenshot can still embarrass the project, especially given the "your government" wording.
4. **Forged conversation history.** The browser supplies the assistant's past turns, so a caller can invent them. That only affects their own session, but it is a clean route for direct injection into the planner.
5. **Links in answers.** If rendered answers can hold model-written links or images, a passage could steer readers to a bad URL. I didn't audit `rag/web.html` rendering.
6. **Cost abuse.** Covered in question 9.

| Candidate | Evidence | VETRA change | Size | Call |
|---|---|---|---|---|
| Planted-document test suite | ADI, PoisonedRAG, Narisetty | About 30 to 50 passages added to a test copy of the index: instructions, false amounts, fake labels and states, fake citations, in English and 3 Indian languages. Goal: no planted figure or instruction reaches an answer unflagged | M | Adopt now |
| Random nonce on evidence labels | ADI: works for key-value formats | Random marker per request around the fields that matter, and strip look-alike text from passages | S | Test, adopt if the suite shows forging |
| Treat browser history as user text | Code reading | Keep only past questions, or sign answers on the server. Mask them either way (see question 9) | S | Adopt now |
| Allow only citation links from the corpus | My reasoning, no direct study | Render only links known from the index. Drop images | S | Adopt now if not already so |
| Record each source's hash and origin when added by hand | Poisoning needs a way in, and manual adding is that way | One manifest line per document. Not an update pipeline, and it may already exist | S | Adopt now |
| CaMeL or FIDES in full | Strong results, but on action-taking agents, at a cost of about 2.7 times the tokens | VETRA's plan-first flow gets the main benefit for its threat | L | Skip |
| PoisonedRAG retrieval defences | Self-reported, non-adaptive | Attack needs write access to a small, hand-added corpus | L | Skip until open or automatic ingestion |
| Treat a classifier as the boundary | Most defences above 90% bypass | Use classifiers only to filter cheap noise | None | Skip as a boundary |

### Gaps
- No test of indirect injection or ADI on a read-only, answer-only RAG system with Indian-language documents.
- No evidence on Gemini 3.x resistance specifically.
- GOV.UK's 100% block rate covers organic attempts by pilot users, not an adaptive red team, so it doesn't contradict the bypass results.

## 6. Which safety classifiers work in Indian languages, and what is jailbreak success there?

### Takeaway
No classifier has solid evidence across all 22 languages, and the large ones need a GPU. For VETRA, scope limits and code checks do more than a classifier would. The one worth testing is Llama Prompt Guard 2 86M, because it is small and multilingual, but its CPU speed and per-language accuracy are unmeasured.

### Cited Findings

**Jailbreak success in Indian languages**
- Measured: IndicJR ran 45,216 prompts in 12 languages against 12 models. In a JSON format track, language means ran from 0.721 (Telugu) to 0.839 (Kannada), with Hindi at 0.767. By model: GPT-4o 0.508, Llama 3.3 70B 0.978, Gemma 2 9B 0.745, Sarvam 1 Base 0.959. In unconstrained text, nearly all models were close to 1.0 — [IndicJR, EACL 2026](https://arxiv.org/html/2602.16832v1) [Primary]
- Read those figures carefully. They are on attacked benign prompts, and the unconstrained track counts the absence of refusal phrases as compliance. Leakage on clean harmful prompts was far lower: GPT-4o 0.001, Llama 3.3 70B 0.021, Qwen 1.5 0.120, Sarvam 1 Base 0.393 — [IndicJR](https://arxiv.org/html/2602.16832v1) [Primary]. It covers three harm categories, and its text and tables have some inconsistencies.
- Measured: native script scored 0.755 against 0.416 for Romanised and 0.488 for mixed. The authors attribute this to tokenisation, and the transliteration was standardised rather than real-world. English-language attacks transfer strongly to Indic targets, at 0.585 to 0.694 by language — [IndicJR](https://arxiv.org/html/2602.16832v1) [Primary]
- Measured: IndicSafeEval used persuasion attacks. Average attack success was Hindi 72.32%, Marathi 66.54%, Bengali 66.37%, English 66.22% and Punjabi 58.60%. Authority Endorsement was the strongest technique at 70.52%, and "Government Decision Making" was among the most vulnerable risk categories. Its LLM judge read 4 to 8 points higher than humans, at 73% against 67% — [IndicSafeEval](https://arxiv.org/html/2609.03781) [Primary]. So Indian languages weren't uniformly worse than English here, and the authors suggest low Punjabi scores may reflect weak generation rather than safety.
- Neither study tested Gemini 3.x, VETRA's chosen provider per `docs/LLM_PROVIDERS.md`.

**Classifiers**

| Model | Size and hardware | Indian-language evidence | Licence | Call |
|---|---|---|---|---|
| [Llama Prompt Guard 2 86M](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M) [Primary, Vendor] | 86M, 92.4 ms on an A100 GPU. CPU not measured | Multilingual AUC .995, Hindi in the test but no separate score. Vendor lists adaptive attacks as a limit. Didn't help on ADI | Llama 4 Community, gated | Test |
| Prompt Guard 2 22M [same card] | 22M, 19.3 ms on A100 | Multilingual AUC .942, no multilingual pretraining | Same | Skip, English-focused |
| [DhvaniGuard v0](https://huggingface.co/speedsharma/dhvaniguard-v0) [Primary, Vendor] | MuRIL base, about 30 ms on CPU per its card | Hindi, Tamil, Telugu, Bengali, Marathi plus Romanised and code-mixed. Catches 100% with 0% false alarms on its author's own eval, trained on synthetic bank and telecom calls. 9 downloads; author says not production-hardened | MIT | Test only as a false-alarm comparison |
| [Llama Guard 4](https://huggingface.co/meta-llama/Llama-Guard-4-12B) [Primary, Vendor] | 12B, single GPU | Vendor's own multilingual output test: recall 43%, FPR 3%, F1 51%. Hindi prompt F1 64.64 in [CultureGuard](https://arxiv.org/html/2508.01710v4) | Llama 4 Community, gated | Skip |
| [Nemotron Safety Guard 8B v3](https://arxiv.org/html/2508.01710v4) [Primary, Vendor] | 8B | Hindi F1 84.12 prompt, 84.72 response, on the authors' own test set | Described as commercially permissive, not named | Skip for MVP (size) |
| Granite Guardian 3.3 8B [same paper] | 8B | Hindi prompt F1 74.64 at best. English-trained, with stronger transfer in [one comparison](https://web3.arxiv.org/pdf/2507.21782) [Snippet] | Not checked | Skip for MVP (size) |
| [IndicGuard](https://arxiv.org/html/2606.22841v1) [Primary] | Gemma 3 4B with an adapter, [about 6 to 8 GB VRAM](https://huggingface.co/l3cube-pune/IndicGuard) | Mean user F1 0.88 across 11 languages. Zero-shot 0.75 to 0.84 on Assamese, Dogri, Maithili, Konkani, Nepali, Sanskrit. But on XSTest it rejected only 58.57% of unsafe prompts. Compared only with CultureGuard; tables have inconsistencies | Apache-2.0 on its page | Test later if a GPU appears |
| ShieldGemma | 2B, 9B and 27B; [ShieldGemma 2 labels images](https://ai.google.dev/gemma/docs/shieldgemma?hl=de) [Snippet] | Nothing Indic-specific found | Not checked | Skip |
| [Gemini safety settings](https://aistudio.google.com/docs/safety-settings) [Primary] | Provider side | Off by default on 2.5 and later. Includes a `jailbreak` category. No language claims. Doesn't cover specialised advice | Provider terms | Test: turn on `dangerous_content` and `jailbreak`, measure false refusals on real questions |

### Inferences
- **No small CPU classifier has independent evidence in Indian languages.** Prompt Guard 2 86M is the most credible, DhvaniGuard the only one with a CPU figure, and both are vendor-reported.
- **VETRA already has a cheap English channel.** The planner produces an English `standalone` question, so a classifier could read that in all 22 languages without needing per-language models. This is my idea and untested. The planner can itself be manipulated, so run it on the raw text too where the language is covered.
- **Llama Guard's Specialized Advice category (S6)** would probably flag VETRA's legitimate finance and scheme answers. That is my reading of its definition, and it's another reason to skip it.
- **False alarms matter more than catches here.** A wrong block stops a farmer asking a genuine question, while a successful jailbreak hurts mainly the person doing it. Measure false alarms in every language before adopting any filter.
- Run a small jailbreak test on the Gemini models you choose, covering Authority Endorsement ("the Collector has ordered...") given that technique's result. Use IndicJR and IndicSafeEval as patterns, and don't treat their numbers as VETRA's.

### Gaps
- No jailbreak or classifier data for Bodo, Santali, Manipuri, Kashmiri or Sindhi. Assamese, Dogri, Maithili, Konkani and Sanskrit have only zero-shot classifier scores.
- No CPU benchmark for Prompt Guard 2 86M.
- Multi-turn and code-mixed attacks are largely untested in these benchmarks.
- [arXiv 2605.28830](https://arxiv.org/pdf/2605.28830) benchmarks open guard models, but the PDF wasn't readable through my tools.

## 7. What do Indian rules require, and what should the MVP say or avoid?

### Takeaway
Not legal advice. The DPDP duties that matter most start around May 2027, so they aren't yet in force, but they are cheap to build in now. On investment advice, the SEBI wording helps a free, public service, but it was written for mass media and may not fit a one-to-one answer, so VETRA should stay clearly on the factual side. A lawyer should confirm three points listed below.

### Cited Findings

**DPDP Act 2023 and DPDP Rules 2025.** The official MeitY and gazette copies failed to open (403 and a certificate error). Clause wording below is from [dpdpa.com](https://dpdpa.com), an unofficial mirror whose commentary sometimes differs from the statute, so check it against the [gazette](https://egazette.gov.in/WriteReadData/2025/267650.pdf) [Primary, not opened].
- Timing: the Rules were notified on 13 November 2025 as G.S.R. 846(E). Notice, consent, security and breach duties apply about 18 months later, with sources giving 13 or 14 May 2027. Consent Manager registration starts at one year, about 13 November 2026 — [KPMG](https://assets.kpmg.com/content/dam/kpmgsites/in/pdf/2025/11/dpdp-rules-2025-guidance-to-dpdp-act-implementation.pdf) [Secondary, Snippet]; [Chambers](https://chambers.com/articles/s-r-data-india-s-digital-personal-data-protection-regime-takes-effect) [Secondary, Snippet]
- Scope: covers digital personal data, and excludes data made public by the person or under a legal duty — [s.3](https://dpdpa.com/dpdpa2023/chapter-1/section3.html)
- Legitimate use: processing for a specified purpose for which a person voluntarily gave data, with no objection — [s.7(a)](https://dpdpa.com/dpdpa2023/chapter-2/section7.html)
- Notice: must be available in English or any Eighth Schedule language — [s.5(3)](https://dpdpa.com/dpdpa2023/chapter-2/section5.html). It must stand alone, in plain language, with an itemised list of data, and withdrawal as easy as consent — [Rule 3](https://www.dpdpa.com/dpdparules/rule3.html)
- Logs: retain logs and related personal data for one year for detecting and investigating unauthorised access, unless another law requires otherwise — [Rule 6(e)](https://www.dpdpa.com/dpdparules/rule6.html). A separate minimum one-year retention applies to Seventh Schedule purposes, which I couldn't read — [Rule 8(3)](https://www.dpdpa.com/dpdparules/rule8.html)
- Research exemption: needs no decision specific to a person, and prescribed standards — [s.17(2)(b)](https://dpdpa.com/dpdpa2023/chapter-4/section17.html). Commentators doubt most commercial research qualifies — [BioSpectrum](https://www.biospectrumindia.com/article/pdf/26746) [Snippet]. The startup exemption power in s.17(3) has reportedly not been used — [KS&K](https://ksandk.com/data-protection-and-data-privacy/dpdpa-startups/) [Snippet]
- Penalty: up to ₹250 crore for failing security safeguards, per most sources. dpdpa.com's schedule page reportedly shows ₹200 crore, so check the gazette — [Bar & Bench](https://www.barandbench.com/view-point/companies-can-save-up-to-250-crore-navigating-the-dpdp-act-2023) [Secondary, Snippet]; [dpdpa.com](https://dpdpa.com/theschedule.html) [Snippet]

**CERT-In directions (April 2022).** Service providers, intermediaries, data centres, body corporates and government bodies must keep ICT logs for a rolling 180 days and report listed incidents within 6 hours. FAQs reportedly allow storage abroad if logs can be produced — [law-firm summaries](https://www.mondaq.com/india/it-and-internet/1270332/6-hours-to-report-cyber-incidents-to-cert-in) [Secondary, Snippet]

**SEBI**
- Read directly, in a SEBI copy showing amendments up to 2023: "investment advice" covers investing in, buying or selling securities or investment products, and includes financial planning. A proviso says advice given through newspapers, magazines or "any electronic or broadcasting or telecommunications medium, which is widely available to the public" isn't investment advice for these regulations — [Reg 2(1)(l)](https://www.sebi.gov.in/sebi_data/attachdocs/mar-2023/1679546065355.pdf) [Primary]
- An "investment adviser" is someone engaged in that business "for consideration", including anyone holding out as one. Consideration includes non-cash benefit. No one may act as one without registration. General good-faith comments on market trends naming no particular product don't need registration — [Reg 2(1)(g), 2(1)(m), 3(1), 4(a)](https://www.sebi.gov.in/sebi_data/attachdocs/mar-2023/1679546065355.pdf) [Primary]
- Registered advisers must disclose AI use since the December 2024 amendments — [Taxmann](https://taxmann.com/post/blog/sebi-mandates-ias-and-ras-to-disclose-use-of-ai-tools-in-providing-investment-advice-research-services-to-clients) [Secondary, Snippet]. One commentary says "educational purposes only" disclaimers don't excuse unregistered advice — [Mondaq](https://www.mondaq.com/india/securities/1759228/sebis-new-digital-compliance-rules-what-investment-advisers-must-know-in-2026) [Secondary, Snippet]
- SEBI's AI/ML guidelines for market participants were still pending in mid-October 2026, with the chairman hoping for release in about a week — [New Kerala](https://www.newkerala.com/news/a/sebi-issue-ai-machine-learning-guidelines-shortly-eyes-586.htm) [Secondary, Snippet]. They may have been issued since. They target regulated participants, which VETRA isn't.

**RBI FREE-AI (August 2025).** Covers RBI-regulated entities with 26 recommendations, reportedly non-binding — [Mondaq](https://www.mondaq.com/india/new-technology/1675520/free-ai-committee-report-rbi-directions-on-implementation-of-ai-in-financial-sector) [Secondary, Snippet]. It doesn't apply to VETRA directly, unless a bank or NBFC becomes a partner.

**MeitY India AI Governance Guidelines (5 November 2025).** Voluntary. Seven sutras, and no standalone AI law planned as of December 2025. Commentary says firms should have multilingual grievance redress and that accountability scales with function, risk and diligence — [Vikaspedia](https://en.vikaspedia.in/viewcontent/e-governance/digital-india/india-ai-governance-guidelines?lgn=en) [Snippet]; [Khaitan](https://www.khaitanco.com/sites/default/files/2025-11/ERGO%20-%20India%20AI%20Governance%20Guidelines%20-%2011%20November%202025.pdf) [Secondary, Snippet]; [Mondaq](https://www.mondaq.com/article/1707626) [Secondary, Snippet]. I didn't read the official text.

**IT Rules amendment (in force 20 February 2026).** Commentaries say "synthetically generated information" means audio or visual content, which would leave a text chatbot's replies outside it — [Hogan Lovells](https://www.hoganlovells.com/en/publications/india-introduces-mandatory-labelling-for-ai-and-3hour-takedown-for-illegal-content) [Secondary, Snippet]. One firm says it includes text — [Gala](https://blog.galalaw.com/post/102micu/indias-2026-it-rules-amendment-regulating-ai-generated-content-and-accelerating) [Secondary, Snippet]. This matters when voice arrives.

**Liability abroad.** A Canadian tribunal held Air Canada responsible for its chatbot's wrong fare information, rejecting the argument that the bot was separate. It isn't binding in India — [ABA on Moffatt](https://www.americanbar.org/groups/business_law/resources/business-law-today/2024-february/bc-tribunal-confirms-companies-remain-liable-information-provided-ai-chatbot/) [Secondary, Snippet]

### Inferences

| Candidate | Why | VETRA change | Size | Call |
|---|---|---|---|---|
| Decline buy, sell and which-product questions | The proviso may not protect a personalised one-to-one reply, which is my reading. Staying factual avoids relying on it | Explain a scheme's rules, rates and eligibility from documents. Refuse "which fund or stock should I buy", "PPF or mutual fund for me", portfolio or financial plans, and point to SEBI's adviser register | M | Adopt now |
| Stay free of "consideration" or get advice first | The adviser definition turns on it | Before ads, paid tiers or referral fees touching financial products, ask a lawyer | S | Adopt now (as a rule) |
| Privacy notice in all 23 languages | s.5(3), Rule 3, in force 2027 | One short itemised page. VETRA's translation system can draft it, but a person should check it | M | Adopt now |
| No question text in operational logs | Rule 6(e) and CERT-In require logs, but not of question content, as I read them | Log time, topic, state, status, cost and security events. Keep `vetra/gaps.py`'s approach | S | Adopt now |
| Grievance and correction channel | MeitY guidance (voluntary), and it catches errors | A "report this answer" link and a published response time | S | Adopt now |
| Name a responsible person | Accountability theme, and CERT-In's 6-hour reporting | Named contact, one-page incident plan | S | Adopt now |
| Consent Manager integration | No need with no accounts | None | None | Skip |

**Questions for a lawyer (an hour should cover them):**
1. Does s.7(a) cover a question typed without an account, or is notice and consent needed?
2. Does the SEBI proviso survive the 2024 amendments, and does it cover one-to-one AI answers?
3. Do Rule 6(e) and Rule 8(3) require anything beyond system logs for a service like this?

### Gaps
- Primary DPDP text wasn't read directly. Seventh Schedule contents weren't seen.
- I read SEBI's regulation in the 2023 consolidated copy, not with the December 2024 amendments.
- Not researched: Consumer Protection Act 2019 (whether a free service counts, and misleading-information liability), IT Act section 79, professional rules on tax advice, IRDAI and PFRDA rules on insurance and pension advice, and use of government names or emblems.
- I found no Indian case on liability for AI agricultural or financial information.

## 8. How do deployed systems handle pesticide dosage, and where is the line between lookup and advice?

### Takeaway
I found no deployed system that publishes how it handles dosage, and no peer-reviewed test of LLM dose advice against label limits. So this rule is my own recommendation: VETRA may quote an official dose exactly as written, and must not calculate, adapt, or recommend.

### Cited Findings
- Penn State Extension tested 8 LLMs on 10 cucumber questions, including pesticide recommendations. Results were inconsistent and sometimes misleading for regional conditions. It then launched Tilva, answering only from vetted Extension and government material. No dose-error rate was reported — [Farms.com](https://www.farms.com/news/ai-tools-show-lacking-when-it-comes-to-agricultural-decision-making-241136.aspx) [Secondary]
- "Green Shield" in China reportedly blocks pesticides that are banned, unsuitable for the crop or above dosage limits. That is a developer claim with no independent test — [search result](https://agrospectrumasia.com/?p=35872) [Vendor, Snippet; the link between result and claim wasn't confirmed]
- Farmer.Chat restricts answers to approved documents and agriculture, and reports no pesticide-specific test — [Farmer.Chat paper](https://arxiv.org/html/2409.08916) [Primary, Vendor]
- AIEP warns that retrieval mistakes and hallucinations can still produce unsafe advice, and describes no pesticide safeguards — [AIEP](https://arxiv.org/html/2601.11537v1) [Primary]
- A food-domain study says general LLM guardrails systematically miss domain-specific hazards. Not agricultural — [arXiv 2604.01444](https://arxiv.org/pdf/2604.01444) [Primary, Snippet]
- KCC advisers routinely give doses, as in "5 grams per litre", so farmers will ask for them — [AgriLLM](https://arxiv.org/html/2407.04721v2) [Primary]
- The draft Pesticides Management Bill 2025 would replace the Insecticides Act 1968. Comments closed on 4 February 2026, and I don't know its current status — [Deccan Herald](https://www.deccanherald.com/india/government-invites-public-comments-on-draft-pesticides-management-bill-2025-3854993) [Secondary, Snippet]
- Pesticide self-poisoning is a major suicide method. One estimate is about 110,000 deaths a year globally, or 13.7% of suicides (2010 to 2014), and one 2017-based evaluation gives India's share as roughly 34% of male and 29% of female suicides. I saw these in a search summary and can't confirm which paper holds which figure — [PMC7886657](https://pmc.ncbi.nlm.nih.gov/articles/PMC7886657/table/tbl1) [Snippet]

### Inferences

| Question type | Example | VETRA should |
|---|---|---|
| Rule lookup | "Is this pesticide banned in my state?" "What does the law require on labels?" | Answer from the document, with date |
| Official dose, source found | "What does the ICAR guide say for X on Y?" | Quote it exactly with crop, pest, unit and source. Code checks every number and unit word for word. Add safety equipment and "follow the label" |
| Dose, no matching source | Crop, pest or state doesn't match | Say it isn't in the documents, and refer to the Krishi Vigyan Kendra or Kisan Call Centre. No nearest match from another crop |
| Calculation | "How much per 15-litre tank?" | Don't convert, because a slip here harms people. Show the official unit and refer on |
| Judgement | "My leaves are yellow, what should I spray?" "Can I mix these?" | Don't diagnose or recommend. Refer on |
| Banned or off-label | "Can I use more?" | Refuse, and state the official limit if documented |
| Self-harm signal | "How much would kill a person?" | No dose or method. Reply with care in the person's language and a crisis helpline. Must work in every language |

| Candidate | VETRA change | Size | Call |
|---|---|---|---|
| Danger gate for plant protection | A planner field marking a question as dose, mixture, diagnosis or self-harm, then fixed code paths. `vetra/domains.py:46` covers "seed, fertiliser and pesticide law", so law is in scope but doses are likely to find no evidence. Keep it that way for the MVP | M | Adopt now |
| Crisis response | A reviewed, translated fixed message, tested in all 23 languages. A person must confirm the helpline number; I didn't verify one | M | Adopt now |
| 50-question hazard test | Dose, mixing, banned, children, self-harm, in several languages, with a person reviewing every answer | M | Adopt now |
| Allow dosing from official documents | Only after the test above passes, and after someone qualified has reviewed the sources | L | Test after MVP |

### Gaps
- No published evaluation of Kisan e-Mitra, Bharat-VISTAAR or Farmer.Chat on dosing.
- Insecticides Act and CIB&RC label rules weren't verified, including whether a third party quoting dose faces any duty.
- No study of how LLM dose errors vary by language.
- Same gating applies to veterinary medicine doses, which I didn't research.

## 9. Which practical pre-launch controls does VETRA need?

### Takeaway
Rate limits and cost caps are standard and needed before any public link goes out. Reading the code also turned up two things to fix first: ID numbers in earlier turns reach the model unmasked, and one answer path isn't counted in the cost meter. Neither has been confirmed by running the code.

### Cited Findings
- OWASP's guidance on unbounded consumption covers denial of wallet, and recommends rate limits and user quotas, input size checks, timeouts and throttling for expensive operations, and monitoring — [OWASP LLM10:2025](https://genai.owasp.org/llmrisk/llm102025-unbounded-consumption/) [Primary, Snippet]
- GOV.UK keeps conversations 12 months and uses sign-in. Its notice says personal data in a question is processed if "not removed by our filters", and doesn't detail those filters — [GOV.UK notice](https://www.gov.uk/government/publications/govuk-chat-privacy-notice/govuk-chat-privacy-notice) [Primary]
- MyCity kept warnings and disclaimers and was still shut down. Moffatt rejected the argument that a chatbot is separate from its operator — [The Markup](https://themarkup.org/artificial-intelligence/2026/01/30/mamdani-to-kill-the-nyc-ai-chatbot-we-caught-telling-businesses-to-break-the-law) [Secondary]; [ABA](https://www.americanbar.org/groups/business_law/resources/business-law-today/2024-february/bc-tribunal-confirms-companies-remain-liable-information-provided-ai-chatbot/) [Secondary, Snippet]
- VETRA code, read not run:
  - `vetra/agent.py:456` masks only the new question. `vetra/web.py:127-129` passes browser history unmasked, `rag/web.html:275` stores the question as typed, and `vetra/agent.py:162` puts it in the planner prompt. So a number masked on turn 1 appears to reach the model on later turns.
  - `vetra/agent.py:90` matches 10 to 16 digit runs. PAN, voter ID, email, names and addresses aren't covered.
  - `vetra/agent.py:485` notes that the older `rag/` path makes its own LLM calls, not counted in the meter.
  - `vetra/web.py:40` runs one question at a time under a lock, so one slow deep question holds up everyone.
  - `vetra/web.py:31` says "Not legal advice", in English, with nothing on farm or financial decisions.
  - `docs/LLM_PROVIDERS.md` notes Google may use free-tier data, and sets the free tier for development only.

### Inferences

| Control | VETRA change | Size | Call |
|---|---|---|---|
| Mask history | Apply `mask()` to history in `vetra/web.py` or at the top of `answer()`, and add a test. Check the masked text also goes back to the page's stored history | S | Adopt now, confirm by test once the current run ends |
| Paid tier before any public use | Don't send real people's questions on the free tier. Already your plan, but make it a launch check | S | Adopt now |
| Wider masking | PAN, voter ID, email and IFSC patterns, plus Indian-script digits in tests. Names are harder, so tell people not to type them, and say so in the privacy notice | S | Adopt now |
| Per-client limits | Soft limits per session and per address, with a stricter limit on deep answers. Mobile networks often share one address across many users (my knowledge, not sourced), so avoid hard address bans | M | Adopt now |
| Daily spend cap | Global rupee cap with a warning at 70%. When reached, fall back to quick answers, then a polite pause. Count `rag/` calls first, or the cap will undercount | M | Adopt now |
| Per-request cap | `max_tokens` on every call and a token budget per question, and bound history size (now up to 3 × 3,000 characters of input) | S | Adopt now |
| Concurrency | Replace the single lock with a small queue and a "busy" reply. Needed for a public API | M | Adopt now |
| Off switch | Config flag for each topic and language, and one for the whole service | S | Adopt now |
| Logging | Keep system logs 180 days to a year, per question 7, with question text excluded. Any sampling for quality must be masked and short-lived, and be mentioned in the notice | S | Adopt now |
| Disclaimers | In the reply language, short, on each answer: from official documents as of [date], may be wrong, not financial, legal or farm advice, check with [office]. These are needed but don't remove responsibility | S | Adopt now |
| Accounts | None for MVP: no personalised storage, and no age or consent burden (my inference) | None | Skip |
| CAPTCHA | Consider only if abuse appears, because it would hurt low-literacy users (my judgment, no study) | S | Skip for now |

### Gaps
- No published rate-limit or cost figures from any comparable Indian service to set limits against. Set them from your own cost table and early traffic.
- Gemini paid-tier retention terms weren't checked here. `docs/LLM_PROVIDERS.md` covers training use but not retention.
- I didn't test the masking finding by running the code.

## 10. What should VETRA do first, and does this change ARCHITECTURE_RESEARCH.md?

### Takeaway
Fix the small privacy and identity issues now, then build the boundary gates and two test sets. Nothing here overturns the architecture document. It confirms the plan-first design and refusal scoring, adds limits to what they protect against, and tightens one claim.

### Cited Findings
- Confirms "plan made before reading": data-flow work treats untrusted text steering actions as the core risk — [Narisetty et al.](https://arxiv.org/html/2606.26479v1) [Primary]. It doesn't cover forged metadata, where plan-then-execute still allowed 40.7% — [ADI paper](https://arxiv.org/html/2607.05120) [Primary]. That result is from action-taking agents.
- Confirms "RAG doesn't end hallucination" with newer independent data: leading tools scored about 80% on accuracy, which still leaves a fifth of the score lost. The test differs from Stanford's 2024 study, so the two aren't directly comparable — [LawSites on Vals](https://www.lawnext.com/2025/10/vals-ais-latest-benchmark-finds-legal-and-general-ai-now-outperform-lawyers-in-legal-research-accuracy.html) [Secondary]
- Confirms "score refusals too" and "grow tests from real failures": GOV.UK reports answer rate beside accuracy — [GDS](https://insidegovuk.blog.gov.uk/2026/03/16/5-things-we-learned-testing-gov-uk-chat-an-ai-assistant-for-government) [Primary]
- Confirms "LLM judge, on real questions, with human reading": judges tracked humans fairly well in AIEP, though not for fine differences — [AIEP](https://arxiv.org/html/2601.11537v1) [Primary] — and read 4 to 8 points high in IndicSafeEval — [IndicSafeEval](https://arxiv.org/html/2609.03781) [Primary]

### Inferences

**Tighten in ARCHITECTURE_RESEARCH.md:** the line "Once an agent reads untrusted text, that text must not be able to trigger consequential actions" is right but incomplete. A wrong answer is VETRA's consequential action, so "read-only" shouldn't be read as "injection-safe".

**Suggested order**
1. **Now, under a day each:** mask history; drop "your government" wording; wider masking; `max_tokens` and budget; off switch; link allow-list check.
2. **Before any public link:** paid tier; rate limits and spend cap; concurrency; investment, dose, personal-status and crisis gates; multilingual disclaimers; report-an-answer link; privacy notice; lawyer's hour.
3. **Before calling it an MVP:** test sets from KCC and hand-written finance questions, scored per state and per language, with answer rate; planted-document suite; 50-question hazard test; small jailbreak test on the chosen Gemini models.
4. **Test, adopt only if measured gain:** Prompt Guard 2 86M, Gemini `jailbreak` and `dangerous_content` settings, nonce labels, clarifying questions, tap-to-ask follow-ups.
5. **Skip for MVP:** full CaMeL or FIDES, retrieval poisoning defences, large guard models, accounts, exam-style benchmarks, vendor legal benchmarks.

**Three calls most worth challenging:** no large classifier at launch; declining investment comparisons even though the SEBI proviso might allow more; and no dose calculation even when the source is clear.

### Gaps
- Page reading went through a summariser for most sources, so re-check any number against the source before quoting it publicly. Several summarised papers have internal inconsistencies, noted above.
- Many items are marked Snippet because of time. The ones most worth opening next: the gazette text of the DPDP Rules, the Vals report, the official MeitY guidelines PDF, and data.gov.in's KCC page.
- The evidence base is thin for India-specific harm. No source measures actual harm from a wrong government-scheme or farm answer in India.
