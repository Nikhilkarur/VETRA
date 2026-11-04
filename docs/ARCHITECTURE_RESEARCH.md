# How VETRA's engine compares with published work

Checked 4 November 2026, against papers and engineering write-ups. It covers what they found, whether VETRA already does it, and what to do about it. Sources are listed at the end.

**The short answer:** the overall design holds up, so it doesn't need replacing. A single loop with fixed limits, read-only moves and a plan made before reading any document is what these sources recommend for this kind of system. The biggest gains left are in what the search reads, not in the agent's structure: how chunks are prepared, which embedding model is used, and how PDFs are read.

## What the design already gets right

| Published finding | What VETRA does |
|---|---|
| Start simple, and "consider adding complexity *only* when it demonstrably improves outcomes" (Anthropic, Building Effective Agents) | Fixed code paths with one bounded agent loop. Each addition was measured or tested |
| Scale effort to the question with explicit rules. Without them, early systems spawned 50 subagents for simple queries (Anthropic, Research system) | The quick, standard and deep table in `vetra/depth.py` |
| Judge what was retrieved, then act on the result (Corrective RAG) | The judge in `vetra/navigate.py`, plus the off-topic check |
| Once an agent reads untrusted text, that text must not be able to trigger consequential actions (Design Patterns for Securing LLM Agents) | The plan is made before any document is read, every move only reads, and code fixes the state and topic |
| Short, broad queries find more than long, specific ones (Anthropic, Research system) | Measured here too: a part searched on its own reached 58 of 59 parts, and adding the topic as a vote reached 53 |
| Check claims one at a time, and only those that can be verified (FActScore, SAFE, VeriScore) | Each sentence is checked by code, and deep answers by a second reader |
| RAG doesn't end hallucination: commercial legal tools were wrong over 17% of the time (Stanford, 2024) | Why exact facts are printed by code, and sentences are checked rather than trusted |
| Keyword-similar text from an unrelated area causes reasoning errors (Stanford, 2026) | Happened here: PM-KMY exclusions were mixed into a PM-KISAN answer. Writer and second reader now have a rule against it |

## What's worth adopting

| # | Idea | Evidence | Phase | Needs |
|---|---|---|---|---|
| 1 | **Add context to every chunk before indexing.** A model writes a line placing each chunk in its document, used by both embeddings and keyword search | Failures in the top 20 fell from 5.7% to 2.9%, and to 1.9% with reranking (Anthropic). A statute tool that kept each provision's definitions, cross-references and parent text reached 83% against 58% and 64% for commercial tools (Stanford, 2026) | 4 | API key, about $1 per million document tokens by Anthropic's estimate |
| 2 | **Use a multilingual embedding model.** E5-base has been the default since 5 November 2026 | On this project's tests: Marathi 12/20 against 9/20, AP 82/93 against 80/93, deep parts 53/59 against 55/59, about a third slower. These gaps are too small to prove anything. *Correction:* this page used to say BGE-M3 led in 8 of 13 languages. IndicRAGSuite's text says so, but its own table shows BGE-M3 and e5-large tied in 10 of 13, with e5-base behind both | Done | Larger or hosted models are still worth testing |
| 3 | **Read PDFs properly.** Gemini for scans in Indian scripts, with Tesseract as a second reader for digits. Docling only for born-digital tables. *Correction:* this page used to suggest Marker or Surya, but Surya trails Gemini in every Indian-script comparison found, and Marker does its OCR through Surya | No benchmark on Indian government documents exists. The best readers still lost 1-3% of numeric facts on clean pages. This project's scans read Rs.6000/- as Rs.60001 and broke Marathi text | 4 | Test on 150-200 of our own pages, with figures labelled by hand |
| 4 | **Score answers on 150-200 hand-read questions:** correct, wrong, right refusal and needless refusal, by state and language. *Correction:* about 20 is only a smoke test, with roughly 10% power for a 20% against 5% difference | Anthropic's small-sample method suits large effects only. Manual reading still catches what a judge misses | 2 | API key, reading time |
| 5 | **Keep the reranker for now.** Turning it off for all search dropped AP questions from 82/93 to 75/93 and gained nothing on Marathi with both queries (12/20), measured 5 November 2026. A multilingual reranker remains untested here, and may be too slow on this CPU | Stronger rerankers win in English. There's almost no evidence in Indian languages | Later | Test timing first |
| 6 | **Show how it searched.** Traceable paths let reviewers find errors: 75% of one tool's apparent errors were really gaps in the expert reference (Stanford, 2026) | Already in `trace["route"]`, but not on the page | 5 | No key |

## Newer techniques worth trying

Found in a second round of research. None is tested here yet, and each has to beat our scores first.

| # | Technique | What it adds | Evidence | Needs |
|---|---|---|---|---|
| 1 | **Quote first, then answer.** The writer pulls exact quotes from the passages, then answers only from those | Code can check every quote really is in its passage, word for word. That catches wrong wording, which code can't catch today | Practitioner guides only, and it costs more tokens. The code check is my addition | API key |
| 2 | **Independent fact-checking.** Turn each claim into a question, and answer it without seeing the draft (Chain-of-Verification) | The second reader today sees the claim, so it can be swayed by it | The paper reports fewer hallucinations, on general knowledge tasks rather than documents | API key |
| 3 | **Search from the reasoning.** Each reasoning step writes the next search (IRCoT) | Better follow-up searches for questions needing several hops. Our judge is a simpler form of this | Up to 21 points better retrieval on four datasets. Another paper found results varied by setup | API key |
| 4 | **Score refusals too.** Test questions we can't answer, and count saying "not found" as correct | Checks that the engine admits what it doesn't know, which matters most here | OpenAI's 2025 paper recommends this, seen through a summary. GRACE trains for it, in a preprint | Some of it runs with no key |
| 5 | **Grow the tests from real failures.** Every bad answer becomes a test, and the judge is a different model from the writer | Failures can't quietly come back. Every bug found reading real answers so far would have been a test | Practitioner sources only, so treat the numbers as starting points | No key to start |
| 6 | **Pin down the period first. Now adopt, not just try.** The planner names the date the question means, and each rule gets start and end dates | Fewer mix-ups between old and current rules. French tax law went from 2.7% on current-law search to 98.3% with versioned records, though the authors are commercial and their retriever is closed, so expect far less on Indian orders | No record has an end date today, so this is mostly data work. Done so far: a rule now counts for any year it ran in | API key |
| 7 | **Caching saves little here.** *Correction:* Gemini 3.8 Flash won't cache under 4,096 tokens and our stable prompts are 300-600, so expect about 5-10%, by estimate. Exact-match answer caching tied to the document version may help once there's traffic; similarity-based answer caching isn't safe here | Provider documentation | Move date and place out of the top of the writer's prompt when convenient | Nothing |

My order would be 5, then 4, since both are cheap and make every later change safer, then 1, which fits this project's aim of having code verify what the model says.

## Adopted now

These needed no API key:

- **The second reader sees each statement's section.** Sentences like "It comes in three parts" can't be judged alone (DnDScore). It now sees each statement's heading, in order.
- **The judge is told to search short.** Up to 8 words rather than 12, following the short-queries finding above.
- **Deep answers state each rule's period.** Statutory surveys need an explicit time window, and old provisions cause contradictory readings (Stanford, 2026).

## Not worth doing yet

- **Several agents working in parallel.** Multi-agent research beat a single agent by 90.2% in Anthropic's own test, but costs about 15 times a chat's tokens, against about 4 times for one agent. It suits work that splits into many independent searches across the open web. Here, searches are local and take about a second each, so the parallel gain is small and the cost is real. Revisit it when the agent searches the internet.
- **Parent-child chunking.** The "lower half" ranking couldn't be confirmed in the paper's text, but a German statute test supports skipping it. Chunks split at numbered paragraphs look better.
- **Putting whole documents in the prompt.** Anthropic suggests this only under about 200,000 tokens. Our documents are well over that, and every state adds more.

## Looked at in the second research round (5 November 2026)

The full ranked report is `reports/VETRA engine techniques 2026.md`, with notes in `research_notes/`. Its main conclusion is that the engine doesn't need a new design or another model swap: the biggest gains are a proper hand-read test, dates on rules, and reliable reading of figures from scans.

- **Skip:** GraphRAG, LightRAG, RAPTOR, ColBERT, late chunking, agent frameworks, similarity-based answer caching, conformal abstention, and small NLI models replacing the second reader. Evidence for each is in the report.
- **Read-only isn't enough on its own:** it stops documents causing actions, but here a wrong answer is the action that matters. A forged "in force" label in a document can still mislead, so a planted-document test should run before launch.
- **Quote-first:** now has some peer-reviewed support, though short quotes can support a claim less often, and the word-for-word code check is still untested.
- **Search from the reasoning (IRCoT):** weakened. It scored 0.181 against plain search's 0.270 in one harsh test on a small model.
- **Iterative search can hurt honesty:** one study found correct refusals falling from 56.4% to 46.4% with iteration. Our judge loop should be measured for this.

## How far to trust this

- **Different data:** none of these numbers come from Indian government documents, and vendors measured some of them on their own systems. Each idea has to beat this project's own scores before replacing anything.
- **Disputed:** the vendors disputed Stanford's 17% figure, and Stanford said it would extend its evaluation of Westlaw.
- **Not read in full:** the FActScore, SAFE, VeriScore, DnDScore and parent-child points come from search excerpts and summaries, and Corrective RAG from its abstract.

## Sources

- [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents), Anthropic
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system), Anthropic
- [Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval), Anthropic
- [Corrective Retrieval Augmented Generation](https://arxiv.org/abs/2401.15884), Yan et al.
- [Agentic RAG: a survey](https://arxiv.org/abs/2501.09136)
- [Design Patterns for Securing LLM Agents against Prompt Injections](https://arxiv.org/abs/2506.08837), Beurer-Kellner et al.
- [Benchmarking Legal RAG: The Promise and Limits of AI Statutory Surveys](https://arxiv.org/abs/2603.03300), Afane, Hariri, Ouyang and Ho
- [Stanford study of legal AI tools, as reported](https://www.lawnext.com/2024/05/stanford-will-augment-its-study-finding-that-ai-legal-research-tools-hallucinate-in-17-of-queries-as-some-raise-questions-about-the-results.html), LawSites
- [IndicRAGSuite](https://arxiv.org/abs/2506.01615): retrieval benchmarks in 13 Indian languages
- [Chain-of-Verification](https://arxiv.org/abs/2309.11495), Dhuliawala et al.
- [IRCoT](https://arxiv.org/abs/2212.10509), Trivedi et al., and [a later comparison](https://arxiv.org/abs/2406.19820) of it with similar methods
- [GRACE](https://arxiv.org/abs/2601.04525): a preprint on training models to judge evidence and abstain
- [Building a golden dataset from production failures](https://oneuptime.com/blog/post/2026-08-31-build-golden-evaluation-dataset-production-failures/view), a practitioner's guide
- [Evidence-first answering patterns](https://vibe-engineering-guide.pages.dev/part-viii-retrieval-grounding-and-dont-make-stuff-up-engineering/26-guardrails-for-grounded-systems/26-1-answer-only-from-sources-prompting-patterns), a practitioner's guide
- [VeriScore](https://arxiv.org/abs/2406.19276), and [DnDScore](https://huggingface.co/papers/2412.13175): checking long answers claim by claim
- [Evaluating document parsers for RAG](https://dev.to/ashokan/from-pdfs-to-markdown-evaluating-document-parsers-for-air-gapped-rag-systems-58eh): a practitioner's comparison of Docling, Marker and PyMuPDF
