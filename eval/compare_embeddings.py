"""
Compare embedding models by evidence recall@k on the eval questions.

Cheaper and sharper than a full RAGAS run: it asks one question only --
did the text that ANSWERS the question actually arrive in the top-k?
No LLM, no judging, no cost. Run it before re-indexing with a new model.

Note on probes: they are exact substring matches against the chunk text, so
they inherit the corpus's extraction artifacts. "two hundred and fifty rupees"
finds nothing because the PDF reads "two hundred and fifty rup ees". Keep
probes short and verify a new one matches before trusting a MISS.

Run:  python eval/compare_embeddings.py
"""

import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from sentence_transformers import SentenceTransformer, util

items=json.load(open("ingest/chunks.json",encoding="utf-8"))["items"]
texts=[i["text"] for i in items]

# Key phrases that MUST be present in the retrieved context for the question to
# be answerable. Taken verbatim-ish from the corpus, lowercased for matching.
PROBES={
 "How do I apply for information under the RTI Act?":
   ["make a request in writing","specifying the particulars of the information"],
 "How long does the department have to reply to my RTI request?":
   ["thirty days of the receipt of the request","forty-eight hours"],
 "Can a department refuse to give me information, and on what grounds?":
   ["no obligation to give any citizen","sovereignty and integrity of india"],
 "What can I do if my RTI request is rejected or ignored?":
   ["thirty days from the expiry","senior in rank"],
 "Can I ask for government records that are more than twenty years old?":
   ["twenty years before the date"],
 "What information must a government department publish on its own without anyone asking?":
   ["publish within one hundred and twenty days","particulars of its organisation"],
 "Does the RTI Act override other laws that keep government information secret?":
   ["official secrets act","effect notwithstanding anything inconsistent"],
 "What penalty can be imposed on an officer who refuses to accept my RTI application?":
   ["two hundred and fifty rupees","twenty-five thousand rupees"],
}

def evaluate(name, model, prefix=""):
    E=model.encode(texts,batch_size=64,normalize_embeddings=True,show_progress_bar=False)
    hit=tot=0; perq=[]
    for q,probes in PROBES.items():
        qv=model.encode([prefix+q],normalize_embeddings=True)
        top=util.semantic_search(qv,E,top_k=8)[0]
        ctx=" ".join(texts[h["corpus_id"]] for h in top).lower()
        found=[p for p in probes if p in ctx]
        hit+=len(found); tot+=len(probes)
        perq.append((len(found),len(probes),q))
    print(f"\n=== {name}")
    print(f"    evidence recall@8: {hit}/{tot} = {hit/tot:.0%}")
    for f,t,q in perq:
        mark="OK " if f==t else ("part" if f else "MISS")
        print(f"      {mark} {f}/{t}  {q[:62]}")
    return hit/tot

r={}
m1=SentenceTransformer("all-MiniLM-L6-v2")
r["MiniLM"]=evaluate("all-MiniLM-L6-v2 (current)", m1)
m2=SentenceTransformer("BAAI/bge-small-en-v1.5")
r["BGE"]=evaluate("bge-small-en-v1.5 (no prefix)", m2)
r["BGE+pre"]=evaluate("bge-small-en-v1.5 (query prefix)", m2,
                      "Represent this sentence for searching relevant passages: ")
print("\n"+"="*60)
for k,v in r.items(): print(f"  {k:<10} {v:.0%}")
