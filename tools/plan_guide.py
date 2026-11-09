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


def _cases_table() -> str:
    from vetra import structure

    rows = []
    for c in structure.CASES:
        parts = [line.split(". ", 1)[1] for line in c.standard.splitlines()[1:] if ". " in line[:4]]
        rows.append(f"<tr><td><strong>{esc(c.name)}</strong></td><td>{esc(c.asks)}</td>"
                    f"<td>{esc(c.quick)}</td><td>{'<br>'.join(esc(p) for p in parts)}</td>"
                    f"<td>{esc(c.deep) or 'the research brief as it is'}</td></tr>")
    return ("<div class='tw'><table><thead><tr><th>Case</th><th>The person wants</th><th>Quick answer opens with</th>"
            "<th>Standard answer, in order</th><th>Deep brief leads with</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


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
    <div class="card"><p class="label">MVP step 3 · first version tried, not satisfied, not tested</p><p class="big">Web search for what isn't there</p><p class="small muted">For what the review shows is missing, and for any part of a question still missing after the store, search official websites live. If the information is there and checks out, answer with it, labelled as fetched live, and add it to the store; if not, say clearly that no official source was found and what was searched.</p></div>
  </div>
  <div class="grid3" style="margin-top:12px">
    <div class="card"><p class="label">MVP step 4 · foundation laid 7 Nov, not tested</p><p class="big">Answer structure and quality</p><p class="small muted">Change how answers are built and read: structure and length per depth, the order of sections, plain language, every statement cited, figures printed exactly, conditions and exceptions kept, and clear notes for what isn't held. Checked by reading real answers by hand for every aspect, and fixed by design, not around single questions.</p></div>
  </div>
  <h3>MVP step 3 in more detail: the live web-search fallback (first version tried on 7 November; <span class="st-text-warn">not satisfied, not tested</span>)</h3>
  <div class="card" style="margin-bottom:12px"><p class="label">Status, plainly</p><p class="small">A first version is built and switched on, and it was tried on a handful of real questions on 7 November. <strong>You are not satisfied with it yet, and it has not been tested</strong>: no question set has been run through it and no answers using it have been read by hand. Treat everything below as a first attempt to be reviewed, not a finished feature.</p></div>
  <p class="small"><strong>What Tavily is:</strong> Tavily is a web-search service for programs, reached through an API (a key in <code>.env</code>, <code>TAVILY_API_KEY</code>, on its free tier). VETRA sends it a search such as "farm pond subsidy Andhra Pradesh" with a list of allowed websites; Tavily returns the matching page links (and short snippets). It does not write answers for VETRA: VETRA then opens and reads those pages itself, PDFs included, and decides what to use. Free search routes were tried first and failed: DuckDuckGo blocks automated requests, Bing ignored the government-sites filter (it returned Reddit), and Groq's built-in browsing took over two minutes. Brave Search is supported as an alternative (<code>BRAVE_API_KEY</code>).</p>
  <p class="small"><strong>What was built</strong> (<code>vetra/websearch.py</code>, wired into <code>vetra/agent.py</code> after looking further):</p>
  <ul class="small">
    <li><strong>When it runs:</strong> for a part of the question that found nothing in the store, or that the look-further judge says the evidence still doesn't answer. At most two parts per question, about 20 seconds each.</li>
    <li><strong>Where it looks:</strong> the state's own sites first (<code>ap.gov.in</code>, <code>tn.gov.in</code>), then other <code>gov.in</code> and <code>nic.in</code> sites, then RBI and NABARD. Only allow-listed official hosts are read, also after redirects; pages on another state's site are skipped.</li>
    <li><strong>What it keeps:</strong> up to three pages, two passages each, and only passages that contain the subject's own words ("silkworm", not just "subsidy" or "Andhra").</li>
    <li><strong>Checks:</strong> fetched passages go through the same answer checks as held documents (every figure must be in the passage it cites), and come last when evidence has to be cut.</li>
    <li><strong>What the reader sees:</strong> the source card says "Fetched live, not yet checked by VETRA" and the answer adds a note to confirm with the department; if nothing official is found, the answer says so and names the sites searched. Nothing is saved to the store.</li>
  </ul>
  <p class="small"><strong>Tried on 7 November:</strong> "AP farm pond subsidy" found the Nellore and Krishna district horticulture pages on ap.gov.in (about 8 seconds). "AP silkworm rearing shed subsidy" found no official page that says it, and the answer now says the documents held don't specify it and that official websites were searched, where before it wrongly said no subsidy exists. Three faults were fixed while trying it: NABARD and RBI files crowded out state sites, it stopped after the first round even when pages didn't answer, and it accepted passages sharing only generic words.</p>
  <p class="small"><strong>Known weaknesses to review:</strong> pages found live can be old (one district page was from 2018-19) and carry no date VETRA can check; a question that triggers it takes 10 to 20 seconds longer; Tavily's free tier has a monthly limit; the passage picking is simple word matching; and the judge's "still missing" verdict comes from the last round, so it can sometimes trigger a search that wasn't needed.</p>
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

<section id="pl-goal8">
  <div class="sec-head">
    <p class="label">Revised MVP goal, set by you on 8 November 2026 · a plan and research, nothing built yet</p>
    <h2>The MVP, revised: Andhra Pradesh and Tamil Nadu, every domain, government first, general research second</h2>
    <p>Your judgement: VETRA is not yet "intelligent". It relies entirely on the data given to it, so a reasonable question whose answer isn't sitting in one government document, such as "what is the difference between agriculture in Andhra Pradesh and Tamil Nadu?", is rejected. Data breadth and depth still matter, but the system must also be flexible: reason across what it holds, use the wider web when it must, say clearly where each part came from, and have a stronger model write the final answer once the API budget allows.</p>
  </div>
  <div class="grid3">
    <div class="card"><p class="label">Scope</p><p class="big">AP and TN, all domains</p><p class="small muted">Not only agriculture and finance: every area where citizens deal with the state government in Andhra Pradesh and Tamil Nadu. Other states stay for the full product.</p></div>
    <div class="card"><p class="label">Sources</p><p class="big">Government first, then the web</p><p class="small muted">Government documents and records stay the main and preferred source. Official websites come next, then general websites (research, news, institutions), always labelled as from the web, never used silently for a binding rule.</p></div>
    <div class="card"><p class="label">Intelligence</p><p class="big">Reason, compare, synthesise</p><p class="small muted">Answer questions that need several documents put together (comparisons between states, trends, "why" questions), and have a stronger model write the final draft when the budget allows. Today's limit is the free API tier.</p></div>
  </div>

  <h3>The design this points to (proposal, to review)</h3>
  <ol class="small">
    <li><strong>Route each question by what it needs</strong>, not one fixed pipeline: general (direct answer, built 8 Nov), record lookup (today's engine), or research and synthesis (new). Adaptive-RAG does this with a small classifier that predicts how complex a question is before any retrieval.</li>
    <li><strong>Source tiers, shown to the reader.</strong> Tier 1: held government documents and exact records. Tier 2: official websites read live (built 7 Nov, first version). Tier 3: general websites. Each section or sentence carries its tier, and the page groups sources under "From government records", "From official websites (read live)" and "From other websites (not verified by VETRA)". Tier 3 can explain and compare, but never sets an amount, deadline or right on its own.</li>
    <li><strong>Grade the evidence, then widen.</strong> Corrective RAG (CRAG) puts a light evaluator between retrieval and writing that grades what was found as correct, ambiguous or wrong, and widens to web search only when needed. VETRA's look-further judge already does part of this; the change is to let a weak grade step down the tiers instead of ending in "not covered".</li>
    <li><strong>Prepared summaries for "big picture" questions.</strong> "AP versus TN agriculture" isn't in any one document, but it can be answered from summaries VETRA builds ahead of time from its own documents: a profile of each state in each domain (main crops, schemes, budget lines, institutions). GraphRAG (Microsoft Research) does this for "global" questions by building summaries of related groups ahead of time and combining them at question time; RAPTOR builds a tree of summaries over the documents.</li>
    <li><strong>Outline first for long answers.</strong> Stanford's STORM writes an outline from several perspectives before any text, then fills it section by section with citations. This fits VETRA's deep briefs and the comparison case laid on 7 Nov.</li>
    <li><strong>A small model to plan and judge, a big model to write.</strong> Cheap fast models (Groq today) plan, route and grade; a stronger paid model writes the final draft from the gathered evidence; the code checks (figures must be in a cited source, no claiming something doesn't exist) stay in front of the reader whatever writes.</li>
    <li><strong>Check long answers claim by claim.</strong> The second-model check already reads deep answers against their sources; for web-sourced parts, the same idea as Google DeepMind's SAFE (search-augmented factuality evaluation): split the answer into claims and check each against search results.</li>
  </ol>

  <h3>What to read and borrow (research, 8 November)</h3>
  <div class="tw"><table><thead><tr><th>Work</th><th>What it is</th><th>What VETRA would take</th></tr></thead><tbody>
    <tr><td><strong>Adaptive-RAG</strong> (Jeong et al., NAACL 2024, arXiv 2403.14403)</td><td>A classifier routes each question to no retrieval, one retrieval or iterative retrieval</td><td>The router in point 1; today's general path is its first, rigid form</td></tr>
    <tr><td><strong>Corrective RAG</strong> (Yan et al., 2024, arXiv 2401.15884)</td><td>An evaluator grades retrieved passages; poor grades trigger web search</td><td>Grading evidence and stepping down source tiers (point 3)</td></tr>
    <tr><td><strong>Self-RAG</strong> (Asai et al., 2023, arXiv 2310.11511)</td><td>The model decides when to retrieve and critiques its own output with reflection steps</td><td>When to search more, and self-critique before the code checks</td></tr>
    <tr><td><strong>GraphRAG</strong> (Edge et al., Microsoft Research, 2024, arXiv 2404.16130)</td><td>Builds an entity graph and community summaries so "global" questions over a whole corpus can be answered</td><td>State and domain profiles for comparison and big-picture questions (point 4)</td></tr>
    <tr><td><strong>RAPTOR</strong> (Sarthi et al., 2024, arXiv 2401.18059)</td><td>A tree of summaries over documents, searched at several levels</td><td>Summaries of long policy notes and budgets that can still be cited</td></tr>
    <tr><td><strong>STORM</strong> (Shao et al., Stanford, NAACL 2024; github.com/stanford-oval/storm)</td><td>Outline-first, multi-perspective research writing with citations</td><td>Long briefs and comparisons (point 5)</td></tr>
    <tr><td><strong>GPT Researcher</strong> (github.com/assafelovic/gpt-researcher)</td><td>Open-source agent: plans sub-questions, searches and scrapes in parallel, summarises, writes a cited report</td><td>Parallel web research and summarising before writing</td></tr>
    <tr><td><strong>Open Deep Research</strong> (LangChain, github.com/langchain-ai/open_deep_research)</td><td>Configurable deep-research agent on LangGraph, a supervisor with researchers; uses Tavily by default</td><td>The supervisor and researcher split, and how to plug in different models and search</td></tr>
    <tr><td><strong>SAFE</strong> (Wei et al., Google DeepMind, 2024, arXiv 2403.18802)</td><td>Splits a long answer into facts and checks each with search</td><td>Checking web-sourced claims (point 7)</td></tr>
    <tr><td><strong>AI Engineering</strong>, Chip Huyen (O'Reilly, 2025)</td><td>Book: building applications on foundation models: evaluation, RAG, agents, cost and latency</td><td>How to evaluate, and how to manage model cost and speed</td></tr>
    <tr><td><strong>Hands-On Large Language Models</strong>, Alammar and Grootendorst (O'Reilly, 2024)</td><td>Book: embeddings, search, RAG and generation, with code</td><td>Better retrieval and embeddings for Telugu and Tamil</td></tr>
    <tr><td><strong>Prompt Engineering for LLMs</strong>, Berryman and Ziegler (O'Reilly, 2024)</td><td>Book: structuring prompts and context for applications</td><td>Writer and judge prompts as the model mix changes</td></tr>
  </tbody></table></div>
  <p class="small muted">Some details above (paper numbers, what each project includes) came from secondary summaries in the 8 November search and should be checked against the papers and repositories before building.</p>

  <h3>The MVP plan, in order (revised)</h3>
  <ol class="small">
    <li><strong>Deepen and broaden the data</strong> for Andhra Pradesh and Tamil Nadu, now across all citizen domains, government sources first.</li>
    <li><strong>Review the data by hand:</strong> what is present and missing, by state, domain and aspect.</li>
    <li><strong>Web search in tiers:</strong> official websites, then general websites, each clearly labelled (the official tier exists as a first version).</li>
    <li><strong>Make it intelligent:</strong> routing by question type, evidence grading, prepared state and domain profiles for synthesis, and outline-first long answers.</li>
    <li><strong>Answer structure and quality,</strong> with a stronger model writing the final draft once a paid API is chosen (the case foundation exists).</li>
  </ol>
  <p class="small"><strong>Not started.</strong> No code was written for this; you asked for the plan and research first.</p>

  <h3>Across every step: as fast as possible (added 9 November)</h3>
  <p class="small">Your goal: the whole system with the least latency and replies as fast as we can make them. Speed is a requirement for every step above, not a step of its own: each change should be measured for time as well as correctness.</p>
  <div class="tw"><table><thead><tr><th>Kind of answer</th><th>Measured now (7 to 9 Nov, Groq free tier)</th><th>Target to aim for</th></tr></thead><tbody>
    <tr><td>General question (direct path)</td><td>about 3 seconds</td><td>under 2 seconds, and words appearing at once</td></tr>
    <tr><td>Quick answer from exact records</td><td>3 to 30 seconds</td><td>under 3 seconds</td></tr>
    <tr><td>Standard answer</td><td>20 to 60 seconds</td><td>under 10 seconds</td></tr>
    <tr><td>Deep brief or comparison</td><td>2 to 3.5 minutes</td><td>under 30 seconds to the first section, under a minute in full</td></tr>
  </tbody></table></div>
  <p class="small"><strong>Where today's time goes, and what to try</strong> (to measure first, then change by design):</p>
  <ol class="small">
    <li><strong>Show the answer as it is written (streaming).</strong> The page waits for the whole answer today. Printing exact records at once and streaming the writer's text cuts the wait a person feels, even before anything else gets faster.</li>
    <li><strong>Fewer model calls per question.</strong> A deep answer makes 8 to 10 calls in turn (plan, look-further rounds, write, second-model check, a rewrite). Merge steps where one call can do two jobs, skip the look-further rounds when the evidence is already good, and run the second-model check only where the code checks can't decide.</li>
    <li><strong>Do things at the same time.</strong> The parts of a deep question are searched one after another, and web pages are read one after another; both can run in parallel.</li>
    <li><strong>Remember what was already done (caching).</strong> Keep plans, search results, fetched web pages and finished answers for repeated questions for a set time, with the date checked so nothing stale is served for a deadline or rate.</li>
    <li><strong>The right model for each job.</strong> A small, fast model to plan, route and judge; the bigger model only to write. A paid API removes the free tier's per-minute limits, which cause most of today's waiting between calls.</li>
    <li><strong>More than one question at a time.</strong> The server answers one question at a time, so a slow deep answer holds up everyone behind it, and it keeps working on a question even after the page is closed. Answer questions side by side, and stop work on a question nobody is waiting for.</li>
    <li><strong>Prepare ahead.</strong> The state and domain profiles planned for synthesis (point 4 above) also make comparison questions fast, because the heavy reading is done before anyone asks.</li>
    <li><strong>Faster search on the machine.</strong> The embedding and re-ranking models run on the laptop's processor; a smaller model, a GPU, or re-ranking only when needed would cut search time.</li>
    <li><strong>Measure every stage.</strong> Each answer already records its total seconds and number of calls; recording the time of each step (plan, search, look further, web, write, check) shows exactly where to cut.</li>
  </ol>
</section>

<section id="pl-general8">
  <div class="sec-head">
    <h2>General questions: a direct path (first version, 8 November)</h2>
    <p>Until now every question went through all the steps, even one that needs no government record at all. Now a simple general question is answered directly by the model, without searching, and labelled as general. <span class="st-text-warn">First version, rigid on purpose, not tested on a question set</span>: the line between "general" and "needs the records" will be made more flexible later, for the MVP and beyond.</p>
  </div>
  <ul class="small">
    <li><strong>Who decides:</strong> the planner, which already reads every question, now also says whether it is <em>general</em>: true only if a correct answer needs no scheme, law, rule, rate, fee, subsidy, eligibility, deadline, office, form or official figure ("what is crop rotation", "how do I keep pests off my tomatoes", "what does GST stand for"). Anything about a scheme, money to or from the government, a right, a procedure with an office, or a situation a rule decides is not general, and neither is anything the planner is unsure about.</li>
    <li><strong>What happens:</strong> one direct call to the writing model (Groq first), under 150 words, told not to state any scheme amount, rate, deadline, eligibility rule or office and to suggest asking about a scheme by name instead. Nothing is searched and no sources are shown.</li>
    <li><strong>The safety line in code:</strong> if the general answer contains a rupee amount or a percentage, it is thrown away and the question goes through the full process with the records. This is the first, simple version of the fine line.</li>
    <li><strong>What the reader sees:</strong> the answer, then "This is a general answer, not taken from government records. For a scheme, rate or rule, ask about it by name and I'll answer from the official documents." The page shows "General answer: not from government records" where sources would be.</li>
    <li><strong>Tried on 8 November:</strong> "What is crop rotation and why is it useful?" was answered directly in 2.6 seconds with two model calls; "How much money does PM-KISAN give?" still went through the full process and cited the official record. Three code tests cover it.</li>
    <li><strong>To refine later:</strong> questions that are partly general and partly about a scheme; general answers in languages other than English and Telugu (the label is translated by the model); and whether some general topics (farming practice, for example) should still show official advisories when VETRA holds them.</li>
  </ul>
</section>

<section id="pl-structure7">
  <div class="sec-head">
    <h2>MVP step 4: answer structure, the foundation laid on 7 November</h2>
    <p>Not the full job: the base the rest of step 4 builds on. It lives in one file, <code>vetra/structure.py</code>, so structure is decided in one place instead of scattered through prompts. <span class="st-text-warn">Not tested on answers yet</span>: two live questions were tried, and 265 code tests pass.</p>
  </div>
  <h3>1. Question cases, like the aspect lists but for answers</h3>
  <p class="small">The aspect lists say what the data must cover; the cases say how an answer must be built for each kind of question. Code picks the case from the question's words (English, Telugu and Tamil), or from the planner's data types when the words don't say, checked in the order below: "the difference in premium" is a comparison, not an amount. The writer is then given that case's structure for the answer's depth. On 19 sample questions, including Telugu and Tamil, all were sorted correctly.</p>
  {_cases_table()}
  <h3>2. Honest "not found" wording, enforced by code</h3>
  <p class="small">Every answer follows shared rules: put what the person can act on first, one idea per sentence, name the scheme, state and period, and above all, when the documents don't cover something, say "the documents I have don't mention it", never that it doesn't exist. A code check now sends an answer back if a sentence says something doesn't exist or isn't provided and no cited document says so. This came from a live answer that told a farmer "no subsidy is provided" for silkworm sheds, when VETRA simply held nothing on it.</p>
  <h3>3. Structure measured on every answer</h3>
  <p class="small">Each answer's trace now records its case, whether it opens with the answer (the records block code prints first is skipped), its section headings, length, list items and whether it has a table, beside the structure expected for its depth. This lets a question set show where structure goes wrong before anything is changed. A table the writer splits with blank lines is joined back by code, so it shows as one table on the page.</p>
  <h3>Tried on 7 November</h3>
  <p class="small">"Difference between PMFBY and RWBCIS in Andhra Pradesh" was sorted as a comparison. The first try had no table, because at deep level the case's instruction came after the research brief's layout and the writer followed the layout; the case now comes first and takes priority. The second try opened with the direct answer and gave a comparison table (premium rule, basis of claims, voluntary enrolment, current windows), with the enrolment windows printed by code above it. It took about three and a half minutes, which is too slow and is a next step.</p>
  <h3>Next for step 4 (not started)</h3>
  <ul class="small">
    <li>Run a question set with several questions per case for Andhra Pradesh and Tamil Nadu, read the answers by hand, and compare each answer's recorded structure with its case.</li>
    <li>Turn the most important case rules into code checks, as was done for "not found" wording (for example: a comparison must have a table; an eligibility answer must open with yes, no or depends).</li>
    <li>Speed: deep answers with a rewrite take minutes; find where the time goes (searches per part, the second-model check, the rewrite).</li>
    <li>Sub-cases inside a case where the reader needs them (comparing schemes, states or periods; eligibility for a person versus for a crop).</li>
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
