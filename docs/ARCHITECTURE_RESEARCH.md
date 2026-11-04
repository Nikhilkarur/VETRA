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
| 2 | **Use a multilingual embedding model.** BGE-M3 led in 8 of 13 Indian languages (IndicRAGSuite). Today's model reads English only, which is why Indian-language documents aren't found | Retrieval benchmarks in Indian languages. Not tested on English documents with Indian-language queries | 3 | No key. Must beat 80/93 and 55/59 here before replacing anything |
| 3 | **Read PDFs properly.** Docling for tables, Marker or Surya for scans in Indian scripts | Features only: no benchmark on Indian government documents was found. This project's scans read Rs.6000/- as Rs.60001 and broke Marathi text | 4 | Test on our own documents |
| 4 | **Score answers with a judge on about 20 real questions:** factual accuracy, citation accuracy, completeness and source quality, as one pass or fail plus a score | Anthropic's method: a small sample shows large effects. Manual reading still caught what the judge missed | 2 | API key |
| 5 | **Try a better reranker.** The small one here added nothing for part searches, but Anthropic gained from a stronger one | Anthropic used Cohere's. A multilingual option is untested here | 3 | Test it |
| 6 | **Show how it searched.** Traceable paths let reviewers find errors: 75% of one tool's apparent errors were really gaps in the expert reference (Stanford, 2026) | Already in `trace["route"]`, but not on the page | 5 | No key |

## Adopted now

These needed no API key:

- **The second reader sees each statement's section.** Sentences like "It comes in three parts" can't be judged alone (DnDScore). It now sees each statement's heading, in order.
- **The judge is told to search short.** Up to 8 words rather than 12, following the short-queries finding above.
- **Deep answers state each rule's period.** Statutory surveys need an explicit time window, and old provisions cause contradictory readings (Stanford, 2026).

## Not worth doing yet

- **Several agents working in parallel.** Multi-agent research beat a single agent by 90.2% in Anthropic's own test, but costs about 15 times a chat's tokens, against about 4 times for one agent. It suits work that splits into many independent searches across the open web. Here, searches are local and take about a second each, so the parallel gain is small and the cost is real. Revisit it when the agent searches the internet.
- **Parent-child chunking.** One 36-strategy benchmark placed it in the lower half, from a secondary summary only. Chunk context (idea 1) addresses the same problem with stronger evidence.
- **Putting whole documents in the prompt.** Anthropic suggests this only under about 200,000 tokens. Our documents are well over that, and every state adds more.

## Not looked at closely

GraphRAG and RAPTOR came up only in surveys and summaries, so nothing here says whether they'd help. The amendment links in `knowledge/*/links.jsonl` are a small graph already. Late chunking also appeared only in a summary, which found it faster than contextual retrieval but weaker on relevance.

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
- [VeriScore](https://arxiv.org/abs/2406.19276), and [DnDScore](https://huggingface.co/papers/2412.13175): checking long answers claim by claim
- [Evaluating document parsers for RAG](https://dev.to/ashokan/from-pdfs-to-markdown-evaluating-document-parsers-for-air-gapped-rag-systems-58eh): a practitioner's comparison of Docling, Marker and PyMuPDF
