"""
The owner's monitoring station: the first tab of docs/AP RTI Assistant Knowledge Base.html.

Everything countable comes from the project's files, so a report can't drift from what's true.
The written parts come from docs/station.json. Add a report and redraw:

  python tools/station.py report --state "On track" --headline "..." --text "..." --five-hour 30 --weekly 10
  python tools/station.py draw            redraw from the files without a new report
"""
from __future__ import annotations

import argparse
import csv
import html
import importlib.util
import json
import re
import subprocess
import time
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs" / "AP RTI Assistant Knowledge Base.html"
STATE = ROOT / "docs" / "station.json"
MARKS = ROOT / "eval" / "aspect_marks.json"
ANSWERS = ROOT / "eval" / "cache" / "aspects" / "first.json"
BASELINE = ROOT.parent / "VETRA-baseline" / "eval" / "cache" / "gold" / "first.csv"
QUEUE = ROOT / "eval" / "cache" / "hand" / "queue.log"
STALL_MINUTES = 45
BEGIN, END = "<!--STATION:BEGIN-->", "<!--STATION:END-->"
CODE_BEGIN, CODE_END = "<!--CODE:BEGIN-->", "<!--CODE:END-->"
DEEP = {"AP": "Andhra Pradesh", "TN": "Tamil Nadu", "MH": "Maharashtra", "KA": "Karnataka"}
OTHERS = {"AR": "Arunachal Pradesh", "AS": "Assam", "BR": "Bihar", "CG": "Chhattisgarh", "GA": "Goa", "GJ": "Gujarat", "HR": "Haryana",
          "HP": "Himachal Pradesh", "JH": "Jharkhand", "KL": "Kerala", "MP": "Madhya Pradesh", "MN": "Manipur", "ML": "Meghalaya",
          "MZ": "Mizoram", "NL": "Nagaland", "OD": "Odisha", "PB": "Punjab", "RJ": "Rajasthan", "SK": "Sikkim", "TS": "Telangana",
          "TR": "Tripura", "UP": "Uttar Pradesh", "UK": "Uttarakhand", "WB": "West Bengal", "AN": "Andaman and Nicobar", "CH": "Chandigarh",
          "DN": "Dadra, Nagar Haveli, Daman and Diu", "DL": "Delhi", "JK": "Jammu and Kashmir", "LA": "Ladakh", "LD": "Lakshadweep", "PY": "Puducherry"}
ALIASES = {"TS": ("TS", "TG"), "UK": ("UK", "UT"), "OD": ("OD", "OR"), "CG": ("CG", "CT")}
MARK_LOOK = {"right": ("good", "Right"), "partial": ("warn", "Partly"), "wrong": ("bad", "Wrong"), "refused": ("warn", "Says not held"),
             "gap": ("bad", "No source")}


def esc(text) -> str:
    return html.escape(str(text))


def _aspects() -> dict:
    spec = importlib.util.spec_from_file_location("coverage_grid_src", ROOT / "tools" / "coverage_grid.py")
    source = spec.loader.get_source("coverage_grid_src")
    scope: dict = {"__name__": "station_import", "__file__": str(ROOT / "tools" / "coverage_grid.py")}
    exec(compile(source.split("def grid(")[0], "coverage_grid.py", "exec"), scope)
    return scope["ASPECTS"]


def _items(domain: str, state: str) -> list[dict]:
    path = ROOT / "knowledge" / domain / "text" / f"{state}.json"
    return json.loads(path.read_text(encoding="utf-8"))["items"] if path.exists() else []


def _records(domain: str, state: str) -> list[dict]:
    found = []
    for name in ("numbers", "dates", "rules"):
        path = ROOT / "knowledge" / domain / f"{name}.jsonl"
        if path.exists():
            found += [r for r in map(json.loads, path.open(encoding="utf-8")) if r.get("jurisdiction") in (state, "IN")]
    return found


def _files(domain: str, state: str) -> int:
    folder = ROOT / "documents" / domain / state
    return sum(1 for f in folder.glob("*") if f.suffix.lower() in (".pdf", ".txt")) if folder.exists() else 0


def matrix() -> tuple[str, dict]:
    aspects = _aspects()
    marks = json.loads(MARKS.read_text(encoding="utf-8")) if MARKS.exists() else {}
    answered = json.loads(ANSWERS.read_text(encoding="utf-8")) if ANSWERS.exists() else {}
    totals: dict = {s: Counter() for s in DEEP}
    blocks = []
    data = {s: {d: (_items(d, s), _records(d, s)) for d in aspects} for s in DEEP}
    for domain, group in aspects.items():
        rows = []
        for name, pattern in group.items():
            rx = re.compile(pattern, re.I)
            cells = []
            for state in DEEP:
                items, records = data[state][domain]
                passages = sum(1 for i in items if rx.search(i["text"]))
                exact = sum(1 for r in records if rx.search(" ".join([r.get("text", ""), r.get("subject", "")] + list(r.get("topic_words") or []))))
                cls = "none" if not passages and not exact else "thin" if passages < 5 and not exact else "some" if not exact else "exact"
                totals[state]["aspects"] += 1
                totals[state]["covered"] += cls != "none"
                totals[state]["exact_aspects"] += bool(exact)
                totals[state][domain + "_aspects"] += 1
                totals[state][domain + "_held"] += cls != "none"
                totals[state][domain + "_exact"] += bool(exact)
                note = marks.get(f"{state}|{name}", "")
                dot = f'<i class="st-dot {MARK_LOOK[note][0]}" title="{MARK_LOOK[note][1]}"></i>' if note in MARK_LOOK else ""
                cells.append(f'<td class="st-{cls}">{passages}{f" · <b>{exact}</b>" if exact else ""}{dot}</td>')
            rows.append(f"<tr><td>{esc(name)}</td>{''.join(cells)}</tr>")
        head = "".join(f"<th>{s}</th>" for s in DEEP)
        blocks.append(f'<div class="tw"><table class="st-matrix"><thead><tr><th>{domain.title()}</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')
    for key, value in marks.items():
        state = key.split("|")[0]
        if state in totals:
            totals[state]["read"] += 1
            totals[state]["good"] += value == "right"
    for key in answered:
        state = key.split("|")[0]
        if state in totals:
            totals[state]["answered"] += 1
    return "".join(blocks), totals


def deep_table(totals: dict) -> str:
    rows = []
    question_count = 0
    try:
        spec = (ROOT / "eval" / "aspect_questions.py").read_text(encoding="utf-8")
        question_count = len(re.findall(r'^    "[^"]+": "', spec, re.M))
    except OSError:
        pass
    for rank, (state, name) in enumerate(DEEP.items(), 1):
        t = totals[state]
        docs = _files("agriculture", state) + _files("finance", state)
        passages = len(_items("agriculture", state)) + len(_items("finance", state))
        records = len(_records("agriculture", state)) + len(_records("finance", state))
        read = f"{t['read']} of {question_count}" + (f", {t['good']} right" if t["read"] else "")
        rows.append(f"<tr><td><strong>{rank}. {name}</strong></td><td>{docs}</td><td>{passages:,}</td><td>{records}</td>"
                    f"<td>{t['covered']} of {t['aspects']}</td><td>{t['answered']} of {question_count}</td><td>{read}</td></tr>")
    return ('<div class="tw"><table><thead><tr><th>Target, in order</th><th>Documents</th><th>Passages in search</th><th>Exact records</th>'
            "<th>Aspects with anything held</th><th>Aspect questions asked</th><th>Answers read by hand</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def others_table() -> str:
    cells = []
    held = 0
    for code, name in sorted(OTHERS.items(), key=lambda kv: kv[1]):
        docs = passages = 0
        for c in ALIASES.get(code, (code,)):
            docs += _files("agriculture", c) + _files("finance", c)
            passages += len(_items("agriculture", c)) + len(_items("finance", c))
        held += passages > 0
        cls = "st-none" if not docs else "st-thin" if not passages else "st-some"
        cells.append(f'<tr><td>{esc(name)}</td><td class="{cls}">{docs}</td><td class="{cls}">{passages:,}</td></tr>')
    return (f'<p class="small muted">{held} of {len(OTHERS)} have anything in search. The medium level starts after the four main targets.</p>'
            '<details><summary>All other states and union territories</summary><div class="tw"><table><thead><tr><th>State or UT</th><th>Documents</th>'
            '<th>Passages in search</th></tr></thead><tbody>' + "".join(cells) + "</tbody></table></div></details>")


def baseline() -> str:
    if not BASELINE.exists():
        return '<p class="small muted">No marked test yet.</p>'
    rows = list(csv.DictReader(BASELINE.open(encoding="utf-8-sig")))
    marks = Counter(r["mark"] for r in rows if r["mark"])
    good = marks["right"] + marks["right_refusal"]
    groups: dict = {}
    for r in rows:
        groups.setdefault(r["group"], Counter())[r["mark"]] += 1
    body = "".join(f"<tr><td>{esc(g.replace('_', ' '))}</td><td>{c['right'] + c['right_refusal']} of {sum(c.values())}</td><td>{c['wrong']}</td>"
                   f"<td>{c['needless_refusal']}</td></tr>" for g, c in groups.items())
    wrong = "".join(f"<li><code>{esc(r['id'])}</code> {esc(r['note'])}</li>" for r in rows if r["mark"] == "wrong")
    return (f'<div class="grid3"><div class="card"><p class="label">Good answers</p><p class="big">{good} of {len(rows)}</p><p class="small muted">{good / len(rows):.0%}, range 82 to 92%. '
            f'Marked by Claude, before the 5 November fixes</p></div><div class="card"><p class="label">Wrong</p><p class="big">{marks["wrong"]}</p><p class="small muted">States something false or misleading</p></div>'
            f'<div class="card"><p class="label">Needless refusals</p><p class="big">{marks["needless_refusal"]}</p><p class="small muted">Said not held, but it is</p></div></div>'
            f'<div class="tw"><table><thead><tr><th>Group</th><th>Good</th><th>Wrong</th><th>Needless refusal</th></tr></thead><tbody>{body}</tbody></table></div>'
            f'<details><summary>The {marks["wrong"]} wrong answers</summary><ul class="small">{wrong}</ul></details>')


def running() -> str:
    try:
        out = subprocess.run(["bash", "-c", "ps -ef | grep -E 'python|work_queue' | grep -v grep"], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        out = ""
    jobs = []
    names = {"aspect_questions": "Asking the aspect questions", "vetra.intake build": "Building search", "fetch_docs": "Downloading documents",
             "gold_test": "Running the baseline test", "crawl_pdfs": "Listing official PDFs", "goir.py": "Listing AP government orders"}
    for key, label in names.items():
        count = out.count(key)
        if count:
            jobs.append(label)
    queue = QUEUE.read_text(encoding="utf-8").splitlines()[-6:] if QUEUE.exists() else []
    shown = "".join(f"<li>{esc(j)}</li>" for j in jobs) or "<li>Nothing is running at this moment</li>"
    log = "".join(f"<li><code>{esc(q[:110])}</code></li>" for q in queue)
    stall = ""
    if any("aspect" in j for j in jobs) and ANSWERS.exists():
        idle = (time.time() - ANSWERS.stat().st_mtime) / 60
        if idle > STALL_MINUTES:
            stall = f'<p class="small"><strong>Stalled: no new answer for {idle:.0f} minutes.</strong></p>'
    return stall + f'<ul class="small">{shown}</ul>' + (f'<details><summary>Latest work queue lines</summary><ul class="small">{log}</ul></details>' if log else "")


def commits() -> str:
    out = subprocess.run(["git", "log", "-8", "--format=%h|%ad|%s", "--date=format:%d %b %H:%M"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
    rows = [line.split("|", 2) for line in out.splitlines() if line.count("|") >= 2]
    return "<ul class=\"small\">" + "".join(f"<li><code>{esc(h)}</code> {esc(d)}: {esc(s)}</li>" for h, d, s in rows) + "</ul>"


def _searched() -> set:
    """Aspects looked for and not found in any official source (knowledge/searched.jsonl)."""
    path = ROOT / "knowledge" / "searched.jsonl"
    rows = [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()] if path.exists() else []
    return {(r["state"], r["domain"], r["aspect"]) for r in rows}


def completion(totals: dict) -> str:
    """Per state and topic: exact-record share of the deep aspect list, with the held share beside it."""
    cells = []
    for state in ("AP", "TN"):
        for domain in ("agriculture", "finance"):
            t = totals.get(state, {})
            n = t.get(domain + "_aspects", 0) or 1
            exact, held = t.get(domain + "_exact", 0), t.get(domain + "_held", 0)
            none = sum(1 for (st, dom, _a) in _searched() if st == state and dom == domain)
            gap = f"; {none} searched, no official source" if none else ""
            cells.append(f'<div class="stat"><b>{exact / n:.0%}</b><span>{state} {domain}, deep: {exact} of {n} aspects with exact records{gap}; {held / n:.0%} held</span></div>')
    return "".join(cells)


def _list(items: list) -> str:
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def build() -> str:
    s = json.loads(STATE.read_text(encoding="utf-8"))
    table, totals = matrix()
    now = datetime.now()
    last = datetime.fromisoformat(s["last_report"])
    tone = {"On track": "good", "In progress": "good", "At risk": "warn", "Blocked": "bad", "Paused": "warn"}.get(s["state"], "warn")
    log = "".join(f'<div class="card st-log"><p class="label">{esc(e["time"])} · {esc(e["state"])}</p><p>{e["text"]}</p></div>' for e in reversed(s["log"]))
    return f"""
<section id="st-now">
  <div class="sec-head">
    <p class="label">Monitoring station · you are head of the project, Claude is senior project manager, the PC does the long work</p>
    <h2>Where the project stands</h2>
    <p>{s['headline']}</p>
  </div>
  <div class="stats">
    <div class="stat"><b class="st-text-{tone}">{esc(s['state'])}</b><span>Overall state</span></div>
    <div class="stat"><b>{last:%d %b %H:%M}</b><span>Last update (on your request)</span></div>
    {completion(totals)}
  </div>
  <p class="small muted">Completion = share of the deep-level aspect list (docs/STATE_COVERAGE.md) with at least one exact record from an official source (the state's own, or a central rule that applies there), counted by keyword from the files when this page is drawn. "Held" = some text in search. Nothing here is tested yet; a keyword count can miss a record worded differently.</p>
  <p class="small muted">Page drawn {now:%d %B %Y, %H:%M}. Counts on this tab come from the project's files by script; the written parts are Claude's report.</p>
</section>
<section id="st-you">
  <div class="sec-head"><h2>Needs you</h2></div>
  {_list(s['decisions'])}
</section>
<section id="st-goal">
  <div class="sec-head"><h2>Targets</h2><p>Andhra Pradesh and Tamil Nadu, then Maharashtra and Karnataka, then every other state at medium level. A target is done only when its answers have been read by hand, not when its documents are in.</p></div>
  {deep_table(totals)}
  {others_table()}
</section>
<section id="st-aspects">
  <div class="sec-head"><h2>Every aspect, state by state</h2><p>Each cell is passages in search, then exact records in bold. A colour shows what's held, not that it's correct. A dot appears once the answer has been read: green right, amber partial or says not held, red wrong or no source found.</p></div>
  <p class="small"><span class="st-key st-none">Nothing held</span> <span class="st-key st-thin">Under 5 passages</span> <span class="st-key st-some">Text held</span> <span class="st-key st-exact">Exact records held</span></p>
  <p class="small muted">These counts come from keyword matches, so a low count can hide a differently worded document, and a high count can be passing mentions.</p>
  {table}
</section>
<section id="st-quality">
  <div class="sec-head"><h2>Measured quality</h2><p>179 hand-read questions, run from a frozen copy of the engine. Most of its documents are Andhra Pradesh and central ones, so it doesn't yet measure Tamil Nadu. It hasn't been re-run since the fixes.</p></div>
  {baseline()}
</section>
<section id="st-work">
  <div class="sec-head"><h2>Who's doing what</h2></div>
  <h3>Running now</h3>
  {running()}
  <h3>Next</h3>
  {_list(s['next'])}
  <h3>Open problems</h3>
  {_list(s['issues'])}
  <h3>Team</h3>
  {s['team_diagram']}
  <div class="tw"><table><thead><tr><th>Worker</th><th>Does</th><th>Limit</th></tr></thead><tbody>
    {''.join(f"<tr><td><strong>{esc(a)}</strong></td><td>{esc(b)}</td><td>{esc(c)}</td></tr>" for a, b, c in s['workers'])}
  </tbody></table></div>
  <h3>Latest commits</h3>
  {commits()}
</section>
<section id="st-log">
  <div class="sec-head"><h2>Report log</h2><p>Newest first. One entry each time you ask for an update.</p></div>
  {log}
</section>
"""


def draw() -> None:
    page = PAGE.read_text(encoding="utf-8")
    a, b = page.index(BEGIN) + len(BEGIN), page.index(END)
    page = page[:a] + build() + page[b:]
    sys.path.insert(0, str(ROOT / "tools"))
    import code_guide

    a, b = page.index(CODE_BEGIN) + len(CODE_BEGIN), page.index(CODE_END)
    PAGE.write_text(page[:a] + code_guide.build() + page[b:], encoding="utf-8")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["report", "draw"])
    for flag in ("--state", "--headline", "--text"):
        parser.add_argument(flag)
    parser.add_argument("--five-hour", type=int)
    parser.add_argument("--weekly", type=int)
    args = parser.parse_args()
    if args.command == "report":
        s = json.loads(STATE.read_text(encoding="utf-8"))
        now = datetime.now()
        s["last_report"] = now.isoformat(timespec="minutes")
        s["state"] = args.state or s["state"]
        s["headline"] = args.headline or s["headline"]
        if args.five_hour is not None:
            s["usage"]["five_hour"] = args.five_hour
        if args.weekly is not None:
            s["usage"]["weekly"] = args.weekly
        s["log"].append({"time": f"{now:%d %b %H:%M}", "state": s["state"], "text": args.text or ""})
        STATE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    draw()
    print("drawn")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
