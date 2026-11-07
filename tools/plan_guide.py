"""The top of the "Current plan" tab: the goal as it stands, the MVP plan, and how VETRA works in detail.

Drawn by tools/station.py between <!--PLAN:BEGIN--> and <!--PLAN:END-->. Settings that live in code
(depth levels, data types, search models, topic lists, model order) are read from the code when the
page is drawn, so this page can't drift from what the engine does. The rest is written here.
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def esc(text) -> str:
    return html.escape(str(text))


def _depth_table() -> str:
    from vetra import depth

    rows = []
    for d in depth.LEVELS.values():
        rows.append(
            f"<tr><td><strong>{esc(d.name)}</strong></td><td>{esc(d.means.split(chr(34))[0].strip().rstrip(':'))}</td>"
            f"<td>{d.passages}</td><td>{'each part' if d.each_part else 'whole question'}</td><td>{d.evidence}</td>"
            f"<td>{d.rounds} × {d.moves}</td><td>{d.calls}</td><td>{'yes' if d.print_alone else 'no'}</td>"
            f"<td>{'yes' if d.verify else 'no'}</td></tr>")
    return ("<div class='tw'><table><thead><tr><th>Level</th><th>For</th><th>Passages per search</th><th>Searches</th>"
            "<th>Most evidence</th><th>Look-further rounds × moves</th><th>LLM calls allowed</th>"
            "<th>Exact records printed without a model</th><th>Second-model check</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def _types_table() -> str:
    from vetra.datatypes import DATA_TYPES

    names = {"rule_check": "rules (eligibility logic)", "number_lookup": "numbers (rates, amounts, fees)",
             "dates_lookup": "dates (deadlines, windows)", "directory_lookup": "directory (offices, helplines)",
             "links_walk": "links (which order amends which)", "form_search": "forms"}
    rows = [f"<tr><td><strong>{esc(t.name)}</strong></td><td>{esc(t.means)}</td>"
            f"<td>{esc(', '.join(names.get(x, x) for x in t.exact)) or 'text search only'}</td></tr>"
            for t in DATA_TYPES.values()]
    return ("<div class='tw'><table><thead><tr><th>Type</th><th>Means</th><th>Exact store read first</th></tr></thead>"
            "<tbody>" + "".join(rows) + "</tbody></table></div>")


def _search_settings() -> dict:
    from vetra import text_index
    from vetra.domains import DOMAINS

    agri = DOMAINS["agriculture"]
    return {"embedding": text_index.EMBEDDING.name, "rerank": agri.rerank or "none",
            "amendments": text_index.MAX_AMENDMENTS,
            "subtopics": {k: len(v.subtopics) for k, v in DOMAINS.items() if not v.legacy}}


def _models() -> str:
    try:
        from vetra import llm

        roles = llm.from_env().roles  # reads .env; only model names are shown, never keys
    except Exception:  # no key on this machine: say so rather than guess
        return "<p class='small muted'>Model lists couldn't be read on this machine (no .env).</p>"
    rows = []
    for role, models in roles.items():
        shown = [m[len("groq:"):] + " (Groq)" if m.startswith("groq:") else m + " (fallback service)" for m in models]
        rows.append(f"<tr><td><strong>{esc(role)}</strong></td><td>{esc(' → '.join(shown))}</td></tr>")
    return ("<div class='tw'><table><thead><tr><th>Job</th><th>Models, tried in this order</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def build() -> str:
    s = _search_settings()
    sub = ", ".join(f"{k} {v}" for k, v in s["subtopics"].items())
    return f"""
<section id="pl-goal7">
  <div class="sec-head">
    <p class="label">Updated 7 November 2026 · the sections further down are from 5 November and kept for history · live figures are on the Monitoring station tab</p>
    <h2>The goal and the MVP plan, as you set them on 7 November</h2>
    <p>The MVP is <strong>Andhra Pradesh and Tamil Nadu, agriculture and finance, at deep level</strong>. Every deep aspect now has an exact record from an official source, except three Andhra Pradesh aspects where no official source exists (recorded in <code>knowledge/searched.jsonl</code>). Your plan for the rest of the MVP has four steps, in this order. They are planned, not started: work resumes only when you say.</p>
  </div>
  <div class="grid3">
    <div class="card"><p class="label">MVP step 1</p><p class="big">Deepen the data</p><p class="small muted">For Andhra Pradesh and Tamil Nadu, fill every aspect from official documents, and split aspects into sub-aspects (crop insurance into enrolment, premium, claims, grievances; land records into mutation, subdivision, freehold, and so on), aiming at three or more exact records per sub-aspect.</p></div>
    <div class="card"><p class="label">MVP step 2</p><p class="big">Review the data by hand</p><p class="small muted">Go through what is held, state by state and aspect by aspect: which types of data are present (amounts, deadlines, eligibility, procedure, contacts, forms, amendments) and which are missing, and whether each record is current and correctly sourced. The result is a written list of what's present and what isn't.</p></div>
    <div class="card"><p class="label">MVP step 3</p><p class="big">Web search for what isn't there</p><p class="small muted">For what the review shows is missing, and for any part of a question still missing after the store, search official websites live. If the information is there and checks out, answer with it, labelled as fetched live, and add it to the store; if not, say clearly that no official source was found and what was searched.</p></div>
  </div>
  <div class="grid3" style="margin-top:12px">
    <div class="card"><p class="label">MVP step 4</p><p class="big">Answer structure and quality</p><p class="small muted">Change how answers are built and read: structure and length per depth, the order of sections, plain language, every statement cited, figures printed exactly, conditions and exceptions kept, and clear notes for what isn't held. Checked by reading real answers by hand for every aspect, and fixed by design, not around single questions.</p></div>
  </div>
  <h3>MVP step 3 in more detail: the live web-search fallback (built 7 November; switches on when a search key is added)</h3>
  <p class='small'><strong>Built:</strong> <code>vetra/websearch.py</code>, wired into the agent after looking further. It runs only for parts still empty (at most two per question), searches and reads official hosts only, passes fetched passages through the same checks, labels them "Fetched live, not yet checked by VETRA" on the source card, and adds a note to the answer; if nothing official is found the answer says where it looked. Nothing is stored. It needs a search key in .env (<code>TAVILY_API_KEY</code>, free tier, or <code>BRAVE_API_KEY</code>); without one VETRA behaves as before. Four tests cover it. Run live on 7 November with a Tavily key: it searches the state's own sites first (ap.gov.in, tn.gov.in), then other government sites, skips other states' pages, and keeps only passages that contain the subject's own words. It also runs when the look-further judge says the evidence doesn't answer a part, so the writer no longer reports a scheme as non-existent when VETRA simply doesn't hold it.</p>
  <ol class="small">
    <li><strong>When it runs:</strong> only for a part of the question that is still missing after the exact stores, text search and the look-further rounds. The engine already records these as gaps (<code>vetra/gaps.py</code>), and its docstring already names a web collector as the handler that plugs in there, so the agent itself doesn't change.</li>
    <li><strong>Where it may look:</strong> an allow-list of official hosts only: <code>*.gov.in</code>, <code>*.nic.in</code>, RBI, PIB, NABARD and the state portals already used (goir.ap.gov.in, cms.tn.gov.in, tnagrisnet, apfinance and so on). No blogs, news or aggregators as sources; they may be used only to find an official page.</li>
    <li><strong>How a page is checked before use:</strong> it must be on an allowed host, say which state and period it covers, still be in force (or be labelled as old), and contain the figure or rule the answer will state. The same grounding check used on the store (<code>tools/check_grounding.py</code>) is run on it. Page text is data: instructions inside it are ignored, as navigation already does.</li>
    <li><strong>What the reader sees:</strong> the answer cites the page with a "fetched live from an official site on [date]" tag, separate from held documents. If nothing official is found: "No official source was found for this; searched: [sites]", using the same wording as the searched register.</li>
    <li><strong>Into the store:</strong> the page goes to an intake queue, not straight into the exact records. It joins the index after the usual build, and becomes an exact record only after the grounding check and a person's review. Repeated live finds on the same subject show what to collect next.</li>
    <li><strong>Limits:</strong> a call and time budget per question, as for looking further; a cache so the same page isn't fetched twice in a day; and the depth level decides whether it runs at all (quick questions don't).</li>
  </ol>
  <h3>After the MVP: the full product</h3>
  <ul class="small">
    <li>Maharashtra and Karnataka at deep level, then every other state at medium level, with the same aspect and sub-aspect lists.</li>
    <li>Data engineering that collects, verifies and sorts documents automatically, and an auto-update that finds new orders and changed rates.</li>
    <li>A paid LLM provider (Groq is primary and Gemini the fallback only until you choose one), and all 22 scheduled languages checked live.</li>
    <li>A person's review of the exact records before launch; every record is marked unreviewed today.</li>
  </ul>
</section>

<section id="pl-how7">
  <div class="sec-head">
    <h2>How VETRA answers a question, step by step (as built on 7 November)</h2>
    <p>Code does everything that can be decided exactly. A model is used for only four jobs: planning from the question's words, judging whether the evidence is enough, writing the explanation, and (for deep answers) checking that each statement says what its sources say. The code is in <code>vetra/</code>; each step names its file.</p>
  </div>

  <h3>1. Guard (<code>agent.py</code>)</h3>
  <p class="small">Long ID-like numbers (Aadhaar, phone, account) are masked before anything else sees the question, and questions are limited to 500 characters. Earlier turns are masked the same way.</p>

  <h3>2. Plan (<code>agent.py</code>, one LLM call, job "plan")</h3>
  <p class="small">The planner reads only the person's words: the latest question and up to three earlier questions (never earlier answers, which came from documents). No document has been read yet, so no document text can steer the plan. It returns: the topic (agriculture, finance, RTI or other), the state if named, the language, how deep to go, a stand-alone version of the question, a short passage written the way an official document would say it (used as an extra search signal), keywords, and the list of <em>needs</em>: each a type of data, the subject in a few words naming the scheme, and its topic. If rules held in the store take facts (a crop, a land size), their exact keys are passed in so the plan uses them. A malformed plan gets one retry; a question outside the topics is declined politely.</p>
  {_types_table()}

  <h3>3. Settle state, language and depth (<code>jurisdictions.py</code>, <code>languages.py</code>, <code>depth.py</code>)</h3>
  <p class="small">State: a state named in the question wins, then the one picked on the page, then the model's guess, because a model can guess wrongly from a scheme's name. Language: the reader's choice on the page wins; Telugu letters can only be Telugu, so that can't be mistaken. Depth: the planner's word, but code overrides it when the needs say otherwise (four or more parts can't fit a short answer).</p>
  {_depth_table()}

  <h3>4. Look in the exact stores first (<code>tools.py</code>, <code>knowledge.py</code>, <code>facts.py</code>)</h3>
  <p class="small">For each need, the stores that answer its type are read first (table above). An exact record is one fact written from an official document, with its figures, dates, who it applies to, its legal weight, whether it's in force, and its source (document, URL, date, and any other documents it draws on). How a record is found:</p>
  <ul class="small">
    <li><strong>Which records:</strong> the chosen state's records plus central (all-India) records, because a central rule applies in every state.</li>
    <li><strong>Which topic:</strong> both topics are searched, the planner's first. A cooperative crop loan may be filed under agriculture and still answer a finance question.</li>
    <li><strong>Matching:</strong> words of the question against each record's text, subject and <em>topic words</em> (how people ask about it, including Telugu and Tamil words); at least two shared words, best first.</li>
    <li><strong>On topic:</strong> a record must name the scheme or subject the question names (its topic words), so a paddy price doesn't answer a question about elephants eating paddy.</li>
    <li><strong>Narrowed:</strong> a record that applies only to some crops, seasons or people (<code>applies_to</code>) is kept only if the question names one of them. Dates and windows are matched to the season and crop asked about.</li>
    <li><strong>Settled or not:</strong> code decides whether the records answer what was asked. If they do (quick and standard answers), no text search is needed. If not, the records stay and the text is read too.</li>
  </ul>

  <h3>5. Search the documents' text (<code>text_index.py</code>, shared parts in <code>rag/retrieve.py</code>)</h3>
  <p class="small">Every held document (orders, policy notes, Acts, budgets, scheme pages) is cut into passages of about 350 tokens with 60 overlapping, each carrying its document's title, date, order number, what it amends, whether it's in force, and whether it was read from a scan. Search is per topic ({esc(sub)} subtopics), over the chosen state's passages plus central ones:</p>
  <ul class="small">
    <li><strong>Two searches in one:</strong> a meaning search, using the multilingual embedding model <code>{esc(s['embedding'])}</code> stored in Chroma (it understands Telugu, Tamil and Hindi as well as English), and a keyword search (BM25), which catches exact names and order numbers. The two rankings are merged by reciprocal rank fusion.</li>
    <li><strong>Extra votes:</strong> the planner's official-style passage, the topic name and the keywords each add their own ranking to the merge, so a question in everyday words still finds the formal wording.</li>
    <li><strong>Repeats dropped:</strong> a passage held twice (the same policy note from two official sites) takes only one place.</li>
    <li><strong>Reranked:</strong> for a search on a whole question, the top 30 are re-scored by the cross-encoder <code>{esc(s['rerank'])}</code>, which reads question and passage together, and that order is merged with the search order rather than replacing it.</li>
    <li><strong>Top passages:</strong> the best ones up to the depth's limit, with at most one no-longer-in-force passage.</li>
    <li><strong>Amendments follow:</strong> if a passage comes from an order that was amended, or amends another, up to {s['amendments']} linked orders are added, because a rule without its amendment is wrong.</li>
    <li><strong>Deep answers:</strong> each part of the question is searched on its own (one search can't reach six different things), always including "how it changed"; then a search on the whole question as a safety net for a part the planner missed.</li>
    <li><strong>Off-topic results:</strong> if what comes back doesn't mention the subject, the subject alone is searched once more; if that fails too, the part is marked missing rather than answered from the wrong scheme.</li>
  </ul>

  <h3>6. Keep what applies today (<code>checks.py</code>)</h3>
  <p class="small">Records and passages outside their valid dates, or no longer in force, are cut, unless the question is about a past year or about how a rule changed. Evidence is ordered: exact records first, binding documents before summaries, unofficial summaries (press explainers, independent analysis) last and labelled. Evidence is shared fairly across the parts of the question, so one part with plenty of passages can't crowd out another.</p>

  <h3>7. Look further when a part is missing (<code>navigate.py</code>, LLM job "plan")</h3>
  <p class="small">Unless exact records already answer everything, a model judges the evidence against the question. It sees up to 700 characters of each passage, and for exact records only that the record exists, not its figures. If a part is missing it chooses up to the depth's number of moves: search again in other words, read the passages just before and after one it found, or look inside one document for something specific. Every move only reads; code fixes the state and topic; results pass the same in-force and on-topic checks. It repeats for the depth's number of rounds and stops as soon as the evidence is enough. Text inside documents is treated as data: instructions in it are ignored.</p>

  <h3>8. Record what's missing (<code>gaps.py</code>)</h3>
  <p class="small">A part with nothing found, or found only for the centre when a state was asked, goes on the to-do list (<code>data/gaps.jsonl</code>, no personal data, just topic, state, type and subject). A type that should have an exact record but was answered from text is logged too. This is where the live web-search fallback (MVP step 3) will plug in.</p>

  <h3>9. Write the answer (<code>agent.py</code>, LLM job "compose")</h3>
  <p class="small">If exact records answer everything in a quick or standard question, they are printed as stored and no model writes anything. Otherwise the writing model gets the evidence and the shape for the depth: a short answer, a standard answer with steps and conditions, or a research brief (direct answer first, a section per part, what changed, where sources differ and which applies by legal weight, and what the documents don't settle). Exact figures are printed by code from the records, so the model can't change a number. Notes are added in code: a part not found, a part found only for the centre, a question without a state, or facts the person should tell us. Answers can be in the question's language or one picked on the page.</p>

  <h3>10. Check the answer (<code>checks.py</code>, <code>verify.py</code>)</h3>
  <ul class="small">
    <li><strong>Code checks, every answer:</strong> it must cite something; no working notes; every figure and date must appear in the evidence it cites; lakh, crore, acre and hectare can't be mixed up; procedure steps must be cited (uncited steps are how a writer invents procedure); a worked example can't borrow a figure from a passage about something else; and it can't claim a document doesn't cover something that a printed record gives.</li>
    <li><strong>Second model, deep answers:</strong> each statement is read against only the passages it cites. Wrong scheme or state, a changed limit, a dropped condition, a past rule told as current, or the wrong unit counts as unsupported.</li>
    <li><strong>Then:</strong> one rewrite told exactly what failed; if faults remain, only the faulty sentences are cut, unless too little would be left; if the model can't run, the facts are printed on their own.</li>
  </ul>

  <h3>11. What the reader gets (<code>web.py</code>, <code>web.html</code>)</h3>
  <p class="small">The answer with numbered citation markers, and a card for each source: title, site, date, and tags for "no longer in force", "read from a scan" and "not an official document". Clicking a marker or card shows the passage itself and a link to the official document.</p>

  <h3>Models (<code>llm.py</code>, settings in <code>.env</code>, which is never committed)</h3>
  <p class="small">Any OpenAI-compatible service works. A model written <code>groq:name</code> goes to Groq; the rest go to the main service. A model at its limit rests for a while and the next one is tried; each question has a call budget by depth. Today (your instruction of 7 November), Groq comes first and Gemini is the fallback:</p>
  {_models()}

  <h3>How data gets in (<code>intake.py</code>, <code>tools/</code>)</h3>
  <ol class="small">
    <li><strong>Find:</strong> official sources only. The AP GO index is crawled by script (<code>tools/goir.py</code>); Tamil Nadu policy notes, gazettes and department pages, and central PIB, RBI and ministry documents, are searched and picked by hand into pick lists.</li>
    <li><strong>Download:</strong> <code>tools/fetch_docs.py</code> saves each file and adds it to <code>documents/&lt;topic&gt;/&lt;state&gt;/manifest.json</code> with title, URL, type, department and date.</li>
    <li><strong>Read and index:</strong> <code>python -m vetra.intake build &lt;topic&gt; &lt;state&gt;</code> reads the text, uses Tesseract OCR for scanned pages (cached, so a page is read once), skips a file already held for another state, cuts passages and adds them to the search index. Builds run one at a time (<code>tools/build_queue.sh</code>).</li>
    <li><strong>Exact records:</strong> Claude reads the documents and writes each record by hand, using only figures the document states, with its source and any other documents it draws on.</li>
    <li><strong>Checks with no model:</strong> <code>tools/check_records.py</code> (no loose topic words, no repeated ids, every record has a source) and <code>tools/check_grounding.py</code> (every figure and date in a record must appear in a document it cites; figures checked by eye against a scan are listed on the record). Both report nothing to look at today.</li>
    <li><strong>Not found:</strong> an aspect searched without an official source goes in <code>knowledge/searched.jsonl</code> with what was tried and the date; this page shows those separately and never counts them as done.</li>
    <li><strong>Measured:</strong> <code>tools/coverage_grid.py</code> and this station count, for each state and aspect, the passages held and the exact records (state plus central, both topics).</li>
  </ol>

  <h3>Known limits today</h3>
  <ul class="small">
    <li>Nothing has been tested on answers yet: the one question run on 7 November answered in about 44 seconds with 16 sources, but answers haven't been read by hand per aspect.</li>
    <li>Coverage percentages count keyword matches, so they guide rather than grade.</li>
    <li>Free-tier models have per-minute limits; several questions in a row can slow down or fall back.</li>
    <li>Sub-aspects don't exist yet (MVP step 1); an aspect with one record counts as covered.</li>
  </ul>
</section>
"""
