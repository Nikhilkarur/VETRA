"""Ask the engine one question and print the answer, for reading by hand.
Run: python tools/ask.py STATE "question" [--as-of YYYY-MM-DD]"""
import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vetra import agent, llm  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("state")
p.add_argument("question")
p.add_argument("--as-of", default=dt.date.today().isoformat())
a = p.parse_args()
r = agent.answer(a.question, state=a.state, models=llm.from_env(), as_of=a.as_of)
print(f"[{r.kind} / {r.depth}]\n{r.answer}")
for n, s in enumerate(r.sources, 1):
    print(f"[E{n}] {str(s.get('title') or s.get('doc') or s)[:90]}")
print("verified:", r.trace.get("verified"), "| problems:", r.trace.get("problems"))
