"""
Evaluate the RAG pipeline with RAGAS.

Runs every question in eval/testset.json through the real pipeline (retrieve ->
Groq -> answer), then scores the results on four metrics. Groq is the judge;
embeddings for scoring run locally, same as in the pipeline itself.

The four metrics, and what a low score actually tells you:

  context_precision  Of the chunks we retrieved, how many were relevant?
                     Low = we are stuffing the prompt with noise.
  context_recall     Of the facts in the ground truth, how many were present
                     in the retrieved chunks?
                     Low = RETRIEVAL is the problem. The answer could not have
                     been right, because the evidence never arrived.
  faithfulness       Is every claim in the answer supported by the context?
                     Low = the model is inventing. Worst failure for a legal
                     assistant.
  answer_relevancy   Does the answer actually address the question?
                     Low = evasive or padded answers.

Read them as a pair: low recall with high faithfulness means retrieval is
starving a well-behaved model. High recall with low faithfulness means the
evidence was there and the model ignored it.

Run:  python eval/run_ragas.py
      python eval/run_ragas.py --k 12          # does more context help?
      python eval/run_ragas.py --limit 3       # quick smoke test
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rag"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TESTSET = ROOT / "eval" / "testset.json"
RESULTS = ROOT / "eval" / "results.json"
JUDGE_MODEL = "openai/gpt-oss-120b"
EMBED_MODEL = "all-MiniLM-L6-v2"


def generate_answers(questions: list[dict], k: int) -> list[dict]:
    """Run the real pipeline over the test questions and collect what it produced."""
    from dotenv import load_dotenv
    from groq import Groq

    from answer import DEFAULT_MODEL, SYSTEM_PROMPT, build_context
    from retrieve import retrieve

    load_dotenv(ROOT / ".env")
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    model = os.environ.get("GROQ_MODEL", DEFAULT_MODEL)

    rows = []
    for n, item in enumerate(questions, 1):
        question = item["question"]
        hits = retrieve(question, k)
        context = build_context(hits)

        reply = client.chat.completions.create(
            model=model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Context passages:\n\n{context}\n\nQuestion: {question}",
                },
            ],
        )

        rows.append(
            {
                "user_input": question,
                "retrieved_contexts": [h["text"] for h in hits],
                "response": reply.choices[0].message.content,
                "reference": item["ground_truth"],
                "_titles": [h["source"] for h in hits],
                "_scores": [h["rank"] for h in hits],
            }
        )
        print(f"  [{n}/{len(questions)}] {question[:62]}")
        time.sleep(0.5)  # stay under the free-tier rate limit

    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=8, help="chunks to retrieve")
    parser.add_argument("--limit", type=int, help="only run the first N questions")
    args = parser.parse_args()

    testset = json.loads(TESTSET.read_text(encoding="utf-8"))
    questions = testset["questions"][: args.limit] if args.limit else testset["questions"]

    print(f"running the pipeline over {len(questions)} questions (top-{args.k}) ...")
    rows = generate_answers(questions, args.k)

    print("\nscoring with RAGAS ...")
    from datasets import Dataset
    from langchain_groq import ChatGroq
    from langchain_huggingface import HuggingFaceEmbeddings
    from ragas import evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )
    from ragas.run_config import RunConfig

    # RAGAS defaults to a 180s timeout and 16 parallel workers. Against Groq's
    # free tier that produces TimeoutErrors and silent `nan` scores -- notably
    # faithfulness, which fires several long calls per question. Serialise the
    # judging and give it room. Slower, but every metric actually returns.
    run_config = RunConfig(timeout=600, max_workers=2, max_retries=5)

    # answer_relevancy defaults to strictness=3, which asks the LLM for three
    # completions in one call (n=3). Groq rejects that: "'n' : number must be at
    # most 1". strictness=1 keeps the metric, at slightly higher variance.
    answer_relevancy.strictness = 1

    judge = LangchainLLMWrapper(ChatGroq(model=JUDGE_MODEL, temperature=0, timeout=180))
    embedder = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(model_name=f"sentence-transformers/{EMBED_MODEL}")
    )

    dataset = Dataset.from_list(
        [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    )

    result = evaluate(
        dataset,
        metrics=[context_precision, context_recall, faithfulness, answer_relevancy],
        llm=judge,
        embeddings=embedder,
        run_config=run_config,
    )

    df = result.to_pandas()

    print("\n" + "=" * 72)
    print(f"RAGAS  --  {len(rows)} questions, top-{args.k}, judge={JUDGE_MODEL}")
    print("=" * 72)
    metrics = ["context_precision", "context_recall", "faithfulness", "answer_relevancy"]
    for m in metrics:
        if m in df:
            print(f"  {m:<20} {df[m].mean():.3f}")

    print("\nper question:")
    for i, row in df.iterrows():
        print(f"\n  {row['user_input'][:66]}")
        cells = "  ".join(
            f"{m.split('_')[-1][:4]}={row[m]:.2f}" if m in df and row[m] == row[m] else f"{m.split('_')[-1][:4]}=n/a"
            for m in metrics
        )
        print(f"    {cells}")
        print(f"    top sources: {', '.join(t[:34] for t in rows[i]['_titles'][:3])}")

    RESULTS.write_text(
        json.dumps(
            {
                "k": args.k,
                "judge": JUDGE_MODEL,
                "questions": len(rows),
                "means": {m: float(df[m].mean()) for m in metrics if m in df},
                "rows": [
                    {
                        "question": rows[i]["user_input"],
                        "answer": rows[i]["response"],
                        "reference": rows[i]["reference"],
                        "titles": rows[i]["_titles"],
                        "scores": rows[i]["_scores"],
                        **{m: (float(row[m]) if row[m] == row[m] else None)
                           for m in metrics if m in df},
                    }
                    for i, row in df.iterrows()
                ],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {RESULTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
