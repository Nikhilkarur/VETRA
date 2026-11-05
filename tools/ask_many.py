"""Ask a few questions and save the answers, for reading by hand.
Run: python tools/ask_many.py OUT.json STATE "question" ["question" ...]"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from vetra import agent, llm  # noqa: E402

out, state, questions = sys.argv[1], sys.argv[2], sys.argv[3:]
models = llm.from_env()
saved = []
for q in questions:
    r = agent.answer(q, state=state, models=models, as_of="2026-11-05")
    saved.append({"q": q, "kind": r.kind, "depth": r.depth, "answer": r.answer, "models": r.trace.get("models")})
    text = re.sub(r"\s+", " ", re.sub(r"\[E\d+\]", "", r.answer))
    print(f"## {q[:80]} [{r.kind}/{r.depth}, {r.trace.get("models")}] {text[:430]}", flush=True)
    Path(out).write_text(json.dumps(saved, ensure_ascii=False, indent=1), encoding="utf-8")
