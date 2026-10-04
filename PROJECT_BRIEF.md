# AP RTI Assistant — Project Brief

One-page summary of where the project stands and where it is going. The full story is
in [`README.md`](README.md); every decision and number is logged in
[`context.md`](context.md).

## What it is

A chatbot for ordinary citizens about **the RTI Act, 2005 as it applies in Andhra
Pradesh**. It answers only from documents the AP government publishes and cites the
passage (and Act section) behind each statement.

## Where it stands (Oct 2026)

- **Corpus:** 41 documents from `ap.gov.in` → RTI & Acts (the Act, 26 GAD orders
  2005–2011, 13 department 4(1)(b) manuals, the portal's RTI page), chosen from 546.
- **Pipeline:** section-aware token chunking (535 chunks) → `bge-small-en-v1.5` in
  Chroma → per question: HyDE search passage + hybrid dense/BM25 search fused with RRF,
  top 10, plus amendment-linked orders → Groq `gpt-oss-120b` writes a cited answer.
- **Conversation:** follow-ups are rewritten into standalone questions before searching.
- **Interfaces:** local web page (`rag/web.py`) and terminal chat (`rag/chat.py`).
- **Measured:** the answering text reaches the model for 95% of formal and 82% of casual
  questions (first version: ~50% casual).
- **Weak spots:** ~1 in 5 casual questions still misses; noisy context; appeal answers
  can mix the two appeal stages; follow-up rewrite can drop the topic; no untouched test
  set left; Groq free-tier throughput.

## Stack

Python 3.13 · `pypdf` · `sentence-transformers` (local embeddings) · Chroma (local) ·
Groq API (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`). No Llama chat model is available
on our Groq account.

## Next major goal: multi-domain agentic assistant for the AP government

Grow the RTI bot into an assistant that covers several departments:

1. **Router** — classify each question into one or more domains (RTI, finance,
   agriculture, ... or a mix).
2. **Domain retrieval** — run the pipeline built here (HyDE + hybrid search + amendment
   links) over each domain's own index.
3. **Drafting agent** — a domain agent writes the cited answer; mixed questions get
   their parts merged.
4. **Cheap continuation** — follow-ups on the same topic reuse the routing and retrieved
   documents instead of re-running every step.

Open questions to settle before building: which domains and documents come next, how
to evaluate routing and mixed-domain answers, and how much per-question LLM cost the
design can afford.
