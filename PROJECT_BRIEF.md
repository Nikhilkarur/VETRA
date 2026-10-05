# AP Government Assistant — Project Brief

One-page summary of where the project stands and where it is going. The full story is
in [`README.md`](README.md); every decision and number is logged in
[`context.md`](context.md); every retrieval experiment is in
[`docs/RETRIEVAL_EXPERIMENTS.md`](docs/RETRIEVAL_EXPERIMENTS.md).

## What it is

A chatbot for ordinary citizens about two areas of the Andhra Pradesh government: **the
RTI Act, 2005 as it applies in AP**, and **farm schemes, subsidies, crop insurance and
agriculture rules**. It answers only from official documents and cites the passage behind
each statement. Questions can be in English or Telugu.

## Where it stands (5 Oct 2026)

- **Documents:** RTI — 41 (the Act, AP orders 2005–2011, department manuals, the
  portal's RTI page); agriculture — 44 (AP orders, scheme guidelines, central Acts).
- **Pipeline:** a router LLM picks the domain (or declines the question) → Telugu-script
  questions are translated for searching → search by meaning and keywords with the
  question, a HyDE passage and an LLM rewrite (topic + key terms), merged → agriculture
  only: a reranker → top 10 passages + amending orders → `gpt-oss-120b` writes a cited
  answer in the question's language.
- **Interfaces:** one web page for both domains (`rag/web.py`), a terminal chat
  (`rag/chat.py`), and Docker (`docker compose up --build` → http://localhost:8765).
- **Measured:** answering text retrieved for 79/82 RTI and 80/93 agriculture test
  questions; RTI final set 15/15; router 31/32 on fresh questions; Telugu-script
  questions 8/8.
- **Weak spots:** answers are checked by reading, not measured; agriculture's gain is
  less certain than RTI's; mixed RTI + agriculture questions go to one domain; Groq's
  free tier (~40–45 full answers a day); Telugu typed in English letters isn't
  translated.

## Stack

Python 3.13 · `pypdf` · `sentence-transformers` (local `bge-small-en-v1.5` embeddings and
`ms-marco-MiniLM-L-6-v2` reranker) · Chroma (local) · Groq API (`openai/gpt-oss-120b`,
`openai/gpt-oss-20b`, `qwen/qwen3.8-27b`) · Docker.

## Next

1. **Finance** as a third domain, with subcategories (pensions, stamp duty, vehicle tax,
   state budget, ...), each routed again to its own documents.
2. **Mixed questions** that need two domains in one answer.
3. **A corrective agent loop** (check the passages, search again if they don't answer)
   and **answer-level evaluation**.
4. **Cheaper per question:** move work to index time (stored hypothetical questions per
   chunk) instead of extra LLM calls per question.
