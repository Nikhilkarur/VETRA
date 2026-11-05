"""
The visual guide to the code, on the Architecture tab of the project page.

The pictures are drawn by hand from vetra/agent.py, text_index.py, navigate.py and intake.py, so change them
when those change. The tables are read from the source each time, so they can't go stale.
Run through: python tools/station.py draw
"""
from __future__ import annotations

import ast
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CODE, LLM, STORE, NEW, STOP, PLAIN = "--answer", "--llm", "--ingest", "--good", "--bad", "--hair-2"
W, H = 186, 78


def esc(text) -> str:
    return html.escape(str(text))


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def _const(path: str, name: str) -> str:
    found = re.search(rf"^{name}\s*=\s*([^\s#]+)", _source(path), re.M)
    return found.group(1) if found else "?"


def box(x, y, title, lines=(), color=PLAIN, code="", w=W, h=H):
    t = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="var(--surface)" stroke="var({color})" stroke-width="1.7"/>'
    t += f'<text x="{x + w / 2}" y="{y + 19}" text-anchor="middle" font-size="13" font-weight="600" fill="var(--ink)">{esc(title)}</text>'
    for i, line in enumerate(lines):
        t += f'<text x="{x + w / 2}" y="{y + 35 + i * 13.5}" text-anchor="middle" font-size="11" fill="var(--ink-2)">{esc(line)}</text>'
    if code:
        t += f'<text x="{x + w / 2}" y="{y + h - 6}" text-anchor="middle" font-size="9.5" font-family="var(--f-mono)" fill="var(--muted)">{esc(code)}</text>'
    return t


def line(points, label="", dashed=False, color="--muted", at=None):
    d = "M" + " L".join(f"{x} {y}" for x, y in points)
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    t = f'<path d="{d}" fill="none" stroke="var({color})" stroke-width="1.5" marker-end="url(#st-arrow)"{dash}/>'
    if label:
        x, y = at or ((points[0][0] + points[1][0]) / 2 + 5, (points[0][1] + points[1][1]) / 2 - 4)
        t += f'<text x="{x}" y="{y}" font-size="10.5" fill="var({color})">{esc(label)}</text>'
    return t


def svg(w, h, body, label):
    return f'<div class="st-diagram"><svg viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}" font-family="var(--f-body)">{body}</svg></div>'


def row(y, boxes, xs=(10, 212, 414, 616, 818)):
    """Boxes left to right, joined by arrows."""
    out = ""
    for n, b in enumerate(boxes):
        out += box(xs[n], y, *b)
        if n:
            out += line([(xs[n - 1] + W, y + H / 2), (xs[n], y + H / 2)])
    return out


def turn(y, from_x=911, to_x=103, gap=24):
    """Down from the end of one row and back to the start of the next."""
    return line([(from_x, y + H), (from_x, y + H + gap / 2), (to_x, y + H + gap / 2), (to_x, y + H + gap)])


LEGEND = ('<p class="small"><span class="st-key" style="border:1.7px solid var(--answer)">Code, no model</span>'
          '<span class="st-key" style="border:1.7px solid var(--llm)">Calls a model</span>'
          '<span class="st-key" style="border:1.7px solid var(--ingest)">Stored data</span>'
          '<span class="st-key" style="border:1.7px solid var(--good)">Added 5 November</span>'
          '<span class="st-key" style="border:1.7px solid var(--bad)">Stops here</span></p>')


def whole_flow() -> str:
    r1, r2, r3, r4, r5 = 14, 116, 218, 320, 422
    b = row(r1, [("Question", ["Any of 23 languages,", "plus earlier turns"], PLAIN, "answer()"),
                 ("Guard", ["Hides ID numbers,", "caps the length"], CODE, "mask()"),
                 ("Planner", ["Topic, state, language, depth,", "parts, search words, passage"], LLM, "make_plan()"),
                 ("Settle", ["Language from the script.", "State: words, menu, model"], CODE, "languages.settle()"),
                 ("Which topic?", ["Off topic: polite decline.", "RTI: old pipeline in rag/"], STOP, "_legacy()")])
    b += turn(r1)
    b += row(r2, [("Depth", ["Quick, standard or deep.", "Sets every limit below"], CODE, "depths.choose()"),
                  ("List the parts", ["Deep always adds", "how the rule changed"], CODE, "needs_for()"),
                  ("First look", ["For each part: exact records,", "then text. See picture 2"], CODE, "gather(), find()"),
                  ("Do records settle it?", ["If not, read the text too,", "and keep the records"], NEW, "records_answer()"),
                  ("Past year asked?", ["Today's records dropped,", "old orders read instead"], CODE, "about_a_past_year()")])
    b += turn(r2)
    b += row(r3, [("Fair shares", ["Parts take turns, so none", "loses all its evidence"], CODE, "share()"),
                  ("Keep what applies", ["Cuts out-of-date rules", "and past seasons, then ranks"], CODE, "in_force(), order()"),
                  ("Look further", ["Unless exact records settle", "it all. See picture 3"], LLM, "navigate.explore()"),
                  ("Record gaps", ["What's missing goes on", "the to-do list"], STORE, "record_gaps()"),
                  ("Anything found?", ["Nothing: says it isn't held,", "and which state is missing"], STOP, "not_covered")])
    b += turn(r3)
    b += row(r4, [("Notes and translation", ["Not found, central only, which", "state? In the reply language"], CODE, "messages, localise()"),
                  ("Exact records enough?", ["Short answer, all exact:", "print with no writer"], CODE, "all_exact()"),
                  ("Writer", ["Explains. Sees notes, never", "the exact figures"], LLM, "compose()"),
                  ("Fix citations", ["A right figure gets the", "passage that really says it"], CODE, "checks.recite()"),
                  ("Code checks", ["Figures, dates, scale. New:", "uncited steps, made-up examples"], NEW, "checks.faults()")])
    b += turn(r4)
    b += row(r5, [("Second reader", ["Deep only. Is each statement", "backed by what it cites?"], LLM, "verify.unsupported()"),
                  ("One rewrite", ["Told what failed. A worse", "rewrite is thrown away"], LLM, "draft(), review()"),
                  ("Cut what still fails", ["Over half cut: exact records", "or document names instead"], CODE, "cut(), facts_only()"),
                  ("Assemble", ["Exact facts, explanation,", "notes, sources"], CODE, "assemble()"),
                  ("Answer", ["With sources, coverage and", "a trace of every step"], PLAIN, "Result")])
    # the short route that skips the writer
    b += line([(305, r4 + H), (305, r4 + H + 8), (740, r4 + H + 8), (709, r5)], "yes: no writer, no checks needed", True, at=(370, r4 + H + 6))
    return svg(1014, 512, b, "One question from start to finish, as in vetra/agent.py")


def rag() -> str:
    b = ""
    # which searches run
    b += box(10, 14, "Quick or standard", ["One search on the rewritten", "question, with every helper,", "reranker on"], CODE, "_read_text()", w=214, h=92)
    b += box(10, 120, "Deep", ["Each part alone, words only,", "reranker off. Plus one whole-", "question search as a safety net"], CODE, "_read_text(), gather()", w=214, h=92)
    # expansion
    b += box(254, 66, "Clean the query", ["Expands PMFBY-style", "abbreviations"], CODE, "expand_abbreviations()", w=170, h=78)
    b += line([(224, 60), (254, 90)]) + line([(224, 166), (254, 120)])
    # votes
    ys = (10, 76, 142, 208)
    votes = [("Question", "meaning + keywords"), ("Passage (HyDE)", "planner's imagined order"), ("Topic", "scheme name"), ("Key terms", "keywords only")]
    for y, (t, s) in zip(ys, votes):
        b += box(452, y, t, [s], CODE, w=170, h=56)
        b += line([(424, 105), (452, y + 28)])
    b += box(650, 76, "Fuse all votes", ["Reciprocal Rank Fusion:", "good in any list wins"], CODE, "_rrf()", w=160, h=78)
    for y in ys:
        b += line([(622, y + 28), (650, 115)])
    b += box(838, 66, "Rerank top 30", ["MiniLM cross-encoder,", "fused with the order.", "Single searches only"], CODE, "_reranked()", w=166, h=92)
    b += line([(810, 115), (838, 112)])
    # how a vote works
    b += box(10, 290, "One vote: meaning", ["E5-base vector, Chroma, one", "collection per topic, filtered to", "state + central"], STORE, "_dense()", w=214, h=92)
    b += box(244, 290, "One vote: keywords", ["BM25 over the same passages.", "Reads Indian scripts"], STORE, "bm25.rank()", w=190, h=92)
    b += box(452, 290, "Hybrid", ["Both lists fused. That's", "one vote above"], CODE, "hybrid()", w=170, h=92)
    b += line([(224, 336), (244, 336)]) + line([(434, 336), (452, 336)])
    b += line([(537, 290), (537, 268)], "", True)
    # results
    b += box(838, 186, "Top passages", ["6 or 10, by depth. At most", f"{_const('rag/retrieve.py', 'MAX_NOT_IN_FORCE')} replaced documents"], CODE, "_top_k()", w=166, h=78)
    b += line([(921, 158), (921, 186)])
    b += box(838, 290, "Add amendments", [f"Up to {_const('vetra/text_index.py', 'MAX_AMENDMENTS')} linked orders,", "with the reason told"], CODE, "_with_amendments()", w=166, h=92)
    b += line([(921, 264), (921, 290)])
    b += box(650, 408, "On topic?", ["Over half the part's", "distinctive words appear"], CODE, "checks.on_topic()", w=170, h=78)
    b += line([(921, 382), (921, 447), (820, 447)])
    b += box(838, 408, "Evidence", ["Goes to fair shares,", "then the judge"], PLAIN, "Evidence", w=166, h=78)
    b += line([(735, 408), (735, 396), (838, 396), (860, 408)], "yes", at=(760, 392))
    b += box(380, 408, "Search once more", ["On the part's own words,", "with no helpers"], CODE, "corrective search", w=190, h=78)
    b += line([(650, 447), (570, 447)], "no")
    b += box(120, 408, "Still off topic", ["Counts as missing:", "logged as a gap"], STOP, "Found(need, 'none')", w=190, h=78)
    b += line([(380, 447), (310, 447)], "no")
    return svg(1014, 498, b, "How text search works, as in vetra/text_index.py and vetra/agent.py")


def agent_loop() -> str:
    from vetra import depth as d
    limits = ", ".join(f"{x.name} {x.rounds}" for x in (d.QUICK, d.STANDARD, d.DEEP))
    moves = ", ".join(f"{x.name} {x.moves}" for x in (d.QUICK, d.STANDARD, d.DEEP))
    b = box(10, 110, "Evidence so far", ["First look's passages and", "records, after fair shares"], PLAIN, "items", w=190, h=84)
    b += box(250, 110, "Judge", [f"Sees {_const('vetra/navigate.py', '_SHOWN')} characters of each", "passage. Exact records as", "notes, never their figures"], LLM, "explore()", w=200, h=84)
    b += line([(200, 152), (250, 152)])
    b += box(510, 110, "Enough?", ["Could a careful person", "answer every part?"], CODE, "parse()", w=180, h=84)
    b += line([(450, 152), (510, 152)])
    b += box(760, 110, "Writer", ["Goes on with the evidence", "in hand"], LLM, "compose()", w=210, h=84)
    b += line([(690, 152), (760, 152)], "yes, or limits reached", at=(690, 102))
    x = (250, 490, 730)
    moves_list = [("Search", ["New words, up to 8.", "Must pass the on-topic check"], "text_search"),
                  ("Read around", ["The passages just before", "and after one it found"], "read_around"),
                  ("Look inside", ["Best match within one", "document: annexure, clause"], "look_inside")]
    for xx, (t, s, c) in zip(x, moves_list):
        b += box(xx, 240, t, s, CODE, c, w=220, h=78)
    b += line([(600, 194), (600, 216), (360, 216), (360, 240)], "no: up to the level's moves", at=(372, 212))
    b += line([(600, 216), (600, 240)])
    b += line([(600, 216), (840, 216), (840, 240)])
    b += box(490, 352, "Add what's new", ["First look stays first.", "In-force check again, capped"], CODE, "tidy()", w=220, h=78)
    for xx in x:
        b += line([(xx + 110, 318), (600, 352)])
    b += line([(490, 391), (105, 391), (105, 194)], "round again")
    b += box(10, 8, "Limits, set in depth.py", [f"Rounds: {limits}. Moves a round: {moves}.", "Stops on no new moves or nothing new. Calls kept back for the writer."], STOP, w=470, h=64)
    b += box(510, 8, "Safety, enforced by code", ["Every move only reads. Code fixes state and topic.", "Evidence is data: instructions inside it are ignored."], CODE, w=460, h=64)
    return svg(980, 442, b, "How the agent looks further, as in vetra/navigate.py")


def intake() -> str:
    chunk = _const("ingest/load_and_chunk.py", "CHUNK_TOKENS")
    overlap = _const("ingest/load_and_chunk.py", "OVERLAP_TOKENS")
    r1, r2 = 14, 140
    b = row(r1, [("Find", ["Crawl official sites,", "list every order"], STORE, "crawl_pdfs, goir"),
                 ("Choose", ["Subject words per aspect,", "routine orders dropped"], CODE, "pick_docs, pick_tn_orders"),
                 ("Download", ["Failed links logged", "and skipped"], CODE, "fetch_docs.py"),
                 ("Order links", ["Own number, what it amends", "or ends; replaced_by"], CODE, "order_links.py"),
                 ("Check", ["Fields present, duplicates", "by file hash"], CODE, "intake.prepare()")])
    b += turn(r1)
    b += row(r2, [("Read each page", ["Good text kept. Scans go to", "Tesseract, read twice"], CODE, "scans.read()"),
                  ("Unclear figures", ["Reads disagree: marked", "[unclear figure]"], CODE, "scans.agree()"),
                  ("Chunk", [f"Sentences, about {chunk} tokens,", f"{overlap} overlap"], CODE, "chunk_tokens()"),
                  ("Embed", ["E5-base, on the CPU", "of this PC"], CODE, "text_index.build"),
                  ("Text index", ["Chroma + JSON,", "one per topic"], STORE, "knowledge/*/text")])
    b += box(10, 264, "Exact records", ["rate_lines.py pulls rate lines;", "Claude reads and enters them"], LLM, "rate_lines.py")
    b += box(212, 264, "Sorter", ["Rejects anything with", "no source or place"], CODE, "sorter.py")
    b += line([(196, 303), (212, 303)])
    b += box(414, 264, "Exact stores", ["Dates, rules, numbers,", "links, documents"], STORE, "knowledge/*/*.jsonl")
    b += line([(398, 303), (414, 303)])
    b += box(616, 264, "Aspect questions", ["Paused until AP and TN data", "is complete. No free models"], LLM, "aspect_questions.py")
    b += line([(600, 303), (616, 303)])
    b += box(818, 264, "Station", ["Held, right, wrong:", "reported to you"], STORE, "station.py")
    b += line([(802, 303), (818, 303)])
    b += line([(709, 342), (709, 366), (103, 366), (103, 342)], "after AP and TN are complete: test once, then fill what's missing", True, "--bad", at=(240, 362))
    return svg(1014, 374, b, "How data gets in, and how it's tested")


def _modules(folder: str, pattern: str = "*.py") -> str:
    rows = []
    for path in sorted((ROOT / folder).glob(pattern)):
        if path.name == "__init__.py":
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(source)
            doc = (ast.get_docstring(tree) or "").strip().split("\n")[0]
            funcs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_")]
        except SyntaxError:
            doc, funcs = "", []
        shown = ", ".join(funcs[:7]) + (f" and {len(funcs) - 7} more" if len(funcs) > 7 else "")
        rows.append(f"<tr><td><code>{esc(path.name)}</code></td><td class=\"num\">{source.count(chr(10))}</td><td>{esc(doc)}</td><td class=\"small\">{esc(shown)}</td></tr>")
    return ('<div class="tw"><table><thead><tr><th>File</th><th>Lines</th><th>What it does</th><th>Main functions</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")


def tables() -> str:
    from vetra import datatypes, depth as d
    from vetra.domains import DOMAINS
    level_rows = "".join(
        f"<tr><td><strong>{x.name.title()}</strong></td><td>{x.passages}</td><td>{'Each part alone' if x.each_part else 'One search'}</td><td>{x.evidence}</td><td>{x.rounds}</td><td>{x.moves}</td><td>{x.calls}</td><td>{x.answer_calls}</td><td>{'Yes' if x.print_alone else 'No'}</td><td>{'Yes' if x.verify else 'No'}</td></tr>"
        for x in (d.QUICK, d.STANDARD, d.DEEP))
    type_rows = ""
    counts = {}
    for domain in ("agriculture", "finance"):
        for f in (ROOT / "knowledge" / domain).glob("*.jsonl"):
            with f.open(encoding="utf-8") as handle:
                counts[f.stem] = counts.get(f.stem, 0) + sum(1 for _ in handle)
    store_of = {"rule_check": "rules", "number_lookup": "numbers", "dates_lookup": "dates", "directory_lookup": "directory", "form_search": "forms", "links_walk": "links"}
    for t in datatypes.DATA_TYPES.values():
        tools = ", ".join(t.exact) or "None: text only"
        stores = ", ".join(f"{store_of[x]} ({counts.get(store_of[x], 0)})" for x in t.exact) or "None"
        type_rows += f"<tr><td><strong>{esc(t.name.replace('_', ' '))}</strong></td><td>{esc(t.means)}</td><td><code>{esc(tools)}</code></td><td>{esc(stores)}</td></tr>"
    text_rows = ""
    for domain in ("agriculture", "finance"):
        for f in sorted((ROOT / "knowledge" / domain / "text").glob("*.json")):
            pass
    env = sorted(set(re.findall(r'"([A-Z][A-Z_]+)"', " ".join(re.findall(r"(?:environ(?:\.get)?[\[(]|getenv\()\s*f?\"[A-Z_]+\"", "".join(p.read_text(encoding="utf-8", errors="replace") for p in (ROOT / "vetra").glob("*.py")))))))
    env_rows = "".join(f"<code>{esc(e)}</code> " for e in env)
    tests = sum(len(re.findall(r"^def test_", p.read_text(encoding="utf-8", errors="replace"), re.M)) for p in (ROOT / "tests").glob("test_*.py"))
    topics = ", ".join(f"{d_.name}{' (old pipeline)' if d_.legacy else ''}" for d_ in DOMAINS.values())
    return f"""
  <h3>The three depth levels, read from <code>vetra/depth.py</code></h3>
  <div class="tw"><table><thead><tr><th>Level</th><th>Passages a search</th><th>Search</th><th>Evidence cap</th><th>Judge rounds</th><th>Moves a round</th><th>Calls allowed</th><th>Kept for writing</th><th>Records alone?</th><th>Second reader</th></tr></thead><tbody>{level_rows}</tbody></table></div>
  <h3>What the planner can ask for, read from <code>vetra/datatypes.py</code></h3>
  <p class="small muted">Each part of a question is one of these types. Exact stores are tried first, with their current record counts in brackets, and text search covers the rest.</p>
  <div class="tw"><table><thead><tr><th>Type</th><th>Means</th><th>Exact tool</th><th>Store</th></tr></thead><tbody>{type_rows}</tbody></table></div>
  <h3>Every check on an answer</h3>
  <div class="tw"><table><thead><tr><th>Check</th><th>Done by</th><th>On failure</th></tr></thead><tbody>
    <tr><td>A figure or date must be in the passage its sentence cites</td><td><code>checks.faults</code></td><td>Citation moved to the right passage, or the sentence is rewritten or cut</td></tr>
    <tr><td>Lakh, crore, acre and hectare must match the source</td><td><code>checks.scale_or_area_wrong</code></td><td>Rewritten or cut</td></tr>
    <tr><td>Working notes, or talk of "the evidence"</td><td><code>checks.faults</code></td><td>Rewritten. The whole answer is rejected if it can't be cut out</td></tr>
    <tr><td>Uncited steps and requirements (new)</td><td><code>checks.faults</code></td><td>Rewritten or cut</td></tr>
    <tr><td>Worked examples the passage doesn't give (new)</td><td><code>checks.faults</code></td><td>Rewritten or cut</td></tr>
    <tr><td>Today's date stated wrongly, and "[unclear figure]" repeated</td><td><code>checks.faults</code></td><td>Rewritten or cut</td></tr>
    <tr><td>Each statement backed by what it cites (deep only)</td><td><code>verify.unsupported</code>, a second model</td><td>Rewritten or cut</td></tr>
    <tr><td>Translated facts keep every number</td><td><code>languages.translate</code></td><td>The English is kept</td></tr>
    <tr><td>Exact records actually fit the question (new)</td><td><code>checks.records_answer</code></td><td>The text is read as well</td></tr>
    <tr><td>Results mention what was asked</td><td><code>checks.on_topic</code></td><td>One more search, then counts as missing</td></tr>
  </tbody></table></div>
  <h3>Models and settings</h3>
  <p class="small">Two roles, set in <code>.env</code> and read by <code>vetra/llm.py</code>: <strong>plan</strong> (planner, judge) and <strong>compose</strong> (writer, second reader). The baseline test ran on Gemini flash-lite models. A <code>groq:</code> model name takes over when the main service is out. A model at its limit rests {_const('vetra/llm.py', 'REST_SECONDS')} seconds and the next is tried. Topics: {esc(topics)}.</p>
  <p class="small">Setting names only, never their values: {env_rows}</p>
  <h3>Every file</h3>
  <p class="small muted">Read from the source on each redraw. {tests} code tests in <code>tests/</code>.</p>
  <h4>The engine, <code>vetra/</code></h4>{_modules('vetra')}
  <details><summary>Tools for collecting and reporting, <code>tools/</code></summary>{_modules('tools')}</details>
  <details><summary>Tests of quality, <code>eval/</code></summary>{_modules('eval')}</details>
  <details><summary>Reading and chunking documents, <code>ingest/</code></summary>{_modules('ingest')}</details>
  <details><summary>The old pipeline, still used for RTI and for search helpers, <code>rag/</code></summary>{_modules('rag')}</details>
"""


def build() -> str:
    return f"""
  {LEGEND}
  <h3>1. One question, start to finish</h3>
  <p class="small muted">From <code>vetra/agent.py</code>. Read left to right, row by row. The small text under each box is the function that does it.</p>
  {whole_flow()}
  <h3>2. How text search works: the RAG part</h3>
  <p class="small muted">From <code>vetra/text_index.py</code> and <code>_read_text()</code> in <code>agent.py</code>. Exact records are looked up first by their type, and this runs for text.</p>
  {rag()}
  <h3>3. How the agent looks further</h3>
  <p class="small muted">From <code>vetra/navigate.py</code>. A model chooses the next move, and code carries it out.</p>
  {agent_loop()}
  <h3>4. How data gets in, and how it's tested</h3>
  <p class="small muted">From <code>vetra/intake.py</code>, <code>vetra/scans.py</code>, <code>ingest/</code> and <code>tools/</code>.</p>
  {intake()}
  {tables()}
"""
