"""Time real questions end to end, stage by stage: python tools/speed_run.py  (eval/speed_set.json)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from vetra import agent, text_index  # noqa: E402
from vetra.domains import DOMAINS  # noqa: E402

for name, d in DOMAINS.items():   # load search first, as the server does, so the first question isn't charged for it
    if not d.legacy and text_index.corpus(name):
        text_index.search("loading", name, None)
rows = []
for c in json.loads((ROOT / "eval" / "speed_set.json").read_text(encoding="utf-8")):
    r = agent.answer(c["q"], state=c["state"])
    t = r.trace
    failed = [(s["model"], s["failed"], s["seconds"]) for s in t.get("steps", []) if s.get("failed")]
    row = {"q": c["q"], "type": c["type"], "kind": r.kind, "depth": t.get("depth") or r.depth, "seconds": t.get("seconds"),
           "stages": t.get("stages"), "calls": t.get("calls"), "failed_calls": failed}
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False), flush=True)
(ROOT / "eval" / "cache" / "speed_run.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
