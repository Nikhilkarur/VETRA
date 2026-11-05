"""The agent's mechanics, with a fake model and fake data: no network, no API key."""

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vetra import agent, checks, facts, intake, jurisdictions, knowledge, languages, llm, rules, sorter, text_index, tools, verify, web  # noqa: E402
from vetra import depth as depths  # noqa: E402
from vetra import gaps as gaps_module  # noqa: E402
from vetra import navigate  # noqa: E402
from vetra.datatypes import DATA_TYPES  # noqa: E402
from vetra.domains import DOMAINS  # noqa: E402
from vetra.tools import Context, Evidence  # noqa: E402

TODAY = "2026-11-04"
EXPLORE = navigate.explore  # the real one; most tests skip this step


class Fake:
    """Answers from a script, and records what it was sent."""

    def __init__(self, *replies):
        self.replies, self.sent = list(replies), []

    def complete(self, model, messages, json_mode=False):
        self.sent.append((model, messages))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return llm.Reply(reply, model, 10)


def models(*replies):
    return llm.Models(Fake(*replies), {"plan": ("p1", "p2"), "compose": ("c1", "c2")})


def plan(**more):
    return json.dumps({"domain": "agriculture", "state": "Andhra Pradesh", "language": "english",
                       "standalone": "Do I pay?", "needs": [{"type": "deadline", "subject": "cut-off rabi"}], **more})


NEED_RULE = [{"type": "amount", "subject": "premium rule scheme"}]


class Gaps:
    def __init__(self):
        self.seen = []

    def report(self, gap):
        self.seen.append(gap)


@pytest.fixture(autouse=True)
def no_real_index_or_gap_file(monkeypatch):
    """Tests search a stub, and never write to the real gap log."""
    languages._saved.clear()
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda query, ctx: [])
    monkeypatch.setattr(agent, "GapLog", Gaps)
    monkeypatch.setattr(navigate, "explore", lambda q, subj, dom, items, base, m, meter, tidy, level: (items, navigate.Route()))


def chunk(id_, place, text="Searched text about the scheme."):
    return Evidence(id_, "text_search", text, f"doc {id_}", jurisdiction=place, status="in_force")


RULE = {"id": "r1", "store": "rules", "domain": "agriculture", "jurisdiction": "AP", "text": "Premium rule scheme",
        "source": {"doc": "G.O.1"}, "cases": [
            {"when": {"crop": "commercial"}, "outcome": {"percent": 5}},
            {"when": {"crop": "food", "income": {"max": 100}}, "outcome": {"percent": 2}}]}
DATE = {"id": "d1", "store": "dates", "domain": "agriculture", "jurisdiction": "AP", "text": "Rabi cut-off rabi window.",
        "source": {"doc": "G.O.2"}, "status": "in_force", "scheme": "PMFBY", "for_season": "Rabi 2026-27",
        "opens": "2026-10-01", "closes": "2026-12-15"}
OTHER_STATE = {**DATE, "id": "d2", "jurisdiction": "KA", "text": "Karnataka cut-off rabi window."}
CENTRAL = {**DATE, "id": "d3", "jurisdiction": "IN", "text": "Central cut-off rabi window.", "closes": "2026-12-20"}


@pytest.fixture
def kb(tmp_path):
    filed, rejected = sorter.file_records([RULE, DATE, OTHER_STATE, CENTRAL], tmp_path)
    assert (filed, rejected) == (4, [])
    return knowledge.Knowledge(tmp_path)


# ---------------------------------------------------------------- the sorting layer

def test_sorter_files_by_store_and_rejects_records_without_a_source(tmp_path):
    filed, rejected = sorter.file_records([DATE, {**DATE, "id": "bad", "source": {}}], tmp_path)
    assert filed == 1 and "no source document" in rejected[0]
    assert (tmp_path / "agriculture" / "dates.jsonl").exists()


def test_sorter_refiling_replaces_rather_than_duplicates(tmp_path):
    sorter.file_records([DATE], tmp_path)
    sorter.file_records([{**DATE, "text": "changed"}], tmp_path)
    assert [r["text"] for r in knowledge.Knowledge(tmp_path).records[("agriculture", "dates")]] == ["changed"]


def test_manifest_gives_documents_and_links():
    rows = sorter.from_manifest([{"title": "G.O.34", "file": "go34.pdf", "department": "Agri", "date": "2026-07-06",
                                  "in_force": "yes", "amends": ["G.O.80"], "doc_type": "go"}], "agriculture", "AP")
    assert {r["store"] for r in rows} == {"documents", "links"} and all(not knowledge.problems(r) for r in rows)


def test_a_state_sees_its_own_records_and_central_ones_only(kb):
    assert {r["id"] for r in kb.select("agriculture", "dates", "AP")} == {"d1", "d3"}


# ---------------------------------------------------------------- rules

def test_rule_decides_and_reports_missing_facts():
    assert rules.evaluate(RULE, {"crop": "commercial"}).outcome == {"percent": 5}
    assert rules.evaluate(RULE, {"crop": "food", "income": 50}).outcome == {"percent": 2}
    assert rules.evaluate(RULE, {"crop": "food", "income": 500}).outcome is None
    assert "crop" in rules.evaluate(RULE, {}).missing


def test_everyday_words_map_through_the_rule_file():
    rule = {"aliases": {"crop": {"paddy": "food"}}, "cases": [{"when": {"crop": "food"}, "outcome": {"percent": 2}}]}
    assert rules.evaluate(rule, {"crop": "Paddy"}).outcome == {"percent": 2}
    assert rules.evaluate(rule, {"crop": "unknown"}).outcome is None


# ---------------------------------------------------------------- what code decides

def test_invented_figures_and_bad_citations_are_caught():
    e = [Evidence("a", "t", "premium is 1.5% or Rs 5,000 by 15 December 2026", "G.O.")]
    assert checks.claim_problems("You pay 1.5% [E1], Rs 5000 [E1].", e, TODAY) == []
    assert any("2%" in p for p in checks.claim_problems("You pay 2% [E1].", e, TODAY))
    assert any("E9" in p for p in checks.claim_problems("You pay 1.5% [E9].", e, TODAY))
    assert "cites nothing" in checks.claim_problems("You pay 1.5%.", e, TODAY)
    assert any("today" in p for p in checks.claim_problems("Open today (2024-11-04) [E1].", e, TODAY))


def test_a_date_the_model_was_never_shown_is_caught_in_any_format():
    hidden = [Evidence("a", "t", "closes 15 December", "G.O.", fact="closes 15 December", note="a window")]
    shown = [Evidence("a", "t", "the cut-off is 15th July, 2026 for all", "G.O.")]
    assert checks.claim_problems("closes 15 December [E1]", hidden, TODAY)
    assert checks.claim_problems("closes 16 July [E1]", shown, TODAY)
    for same in ("15 July 2026", "15th July", "July 15", "15.07.2026"):
        assert not checks.claim_problems(f"closes {same} [E1]", shown, TODAY), same


def test_claiming_a_printed_fact_is_missing_is_rejected():
    hidden = [Evidence("a", "t", "x", "G.O.", fact="closes 15 December", note="a window")]
    assert checks.claim_problems("The deadline is not specified.", hidden, TODAY)
    plain = [Evidence("a", "t", "x", "G.O.")]
    assert not checks.claim_problems("The deadline is not specified [E1].", plain, TODAY)


def test_a_past_year_question_gets_history_not_todays_rates(kb, monkeypatch):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "It was free in 2024.")])
    r, _ = run(kb, plan(needs=[{"type": "deadline", "subject": "cut-off rabi"}, {"type": "procedure", "subject": "how to apply"}]),
               "It was free in 2024 [E1].", q="was the rabi cut-off free in 2024?")
    assert "Open now" not in r.answer and "free in 2024" in r.answer


def test_the_users_words_settle_a_rules_facts_without_the_planner():
    rule = {"inputs": {"crop_class": ["food", "commercial"], "season": ["rabi", "kharif"]},
            "aliases": {"crop_class": {"paddy": "food"}}}
    assert rules.facts_in_words(rule, "i grow Paddy in rabi") == {"crop_class": "food", "season": "rabi"}
    assert rules.facts_in_words(rule, "how much is it") == {}


def test_expired_records_go_unless_the_question_asks_about_that_year():
    old = Evidence("a", "t", "old", "G.O.", valid_until="2025-03-31")
    assert checks.in_force([old], TODAY, "is it free now") == []
    assert checks.in_force([old], TODAY, "was it free in 2025") == [old]


def test_past_season_rule_is_cut_from_text():
    e = Evidence("a", "t", "The State Govt will bear the premium. Rabi 2024-25 onwards: i. Farmers pay.", "G.O.", season="Kharif 2024")
    kept = checks.in_force([e], TODAY, "do i pay")[0]
    assert "will bear" not in kept.text and "Farmers pay" in kept.text


# ---------------------------------------------------------------- what data is needed

def test_planner_is_offered_every_data_type_and_no_tools():
    prompt = agent.planner_prompt(TODAY)
    assert all(name in prompt for name in DATA_TYPES)
    assert "rule_check" not in prompt and "dates_lookup" not in prompt


def test_plan_keeps_known_data_types_and_drops_the_rest():
    p = agent.parse_plan(plan(needs=[{"type": "send_money", "subject": "how to apply"}, {"type": "form", "subject": "y"}]))
    assert [n.data_type for n in p.needs] == ["form"] and p.needs[0].domain == "agriculture"


def test_each_data_type_reads_a_real_tool():
    for t in DATA_TYPES.values():
        assert all(tool in agent.TOOLS for tool in t.exact)


def test_a_need_can_belong_to_another_topic():
    p = agent.parse_plan(plan(needs=[{"type": "amount", "subject": "stamp duty", "domain": "finance"}]))
    assert p.needs[0].domain == "finance"


# ---------------------------------------------------------------- do we have it?

def run(kb, *replies, **kw):
    gaps = Gaps()
    r = agent.answer(kw.pop("q", "rabi cut-off?"), models=models(*replies), knowledge=kb, as_of=TODAY, gaps=gaps, **kw)
    return r, gaps.seen


def test_exact_store_answers_without_searching_text(kb, monkeypatch):
    def fail(query, ctx):
        raise AssertionError("text search shouldn't run")
    monkeypatch.setitem(agent.TOOLS, "text_search", fail)
    r, gaps = run(kb, plan())
    assert r.kind == "answer" and {s["doc"] for s in r.sources} == {"G.O.2"}
    assert "15 December 2026" in r.answer and "Open now" in r.answer and "[E" in r.answer
    assert r.trace["calls"] == 1 and r.coverage[0]["level"] == "exact" and gaps == []


def test_no_exact_data_falls_back_to_text_and_records_a_gap(kb, monkeypatch):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP")])
    r, gaps = run(kb, plan(needs=[{"type": "contact", "subject": "office"}]), "See the document [E1].")
    assert r.coverage[0]["level"] == "text"
    assert [(g.data_type, g.level, g.state) for g in gaps] == [("contact", "text_only", "AP")]
    assert "Not in our documents" not in r.answer


def test_a_procedure_in_text_is_not_a_gap(kb, monkeypatch):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP")])
    r, gaps = run(kb, plan(needs=[{"type": "procedure", "subject": "how to apply"}]), "Apply as described [E1].")
    assert gaps == [] and r.kind == "answer"


def test_state_with_only_central_data_answers_and_says_what_is_missing(monkeypatch, tmp_path):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "IN")])
    r, gaps = run(knowledge.Knowledge(tmp_path), plan(state="Karnataka", needs=[{"type": "procedure", "subject": "how to apply"}]),
                  "The central guideline says this [E1].")
    assert r.kind == "answer" and r.coverage[0]["level"] == "central_text"
    assert "Karnataka" in r.answer and "Not in our documents" in r.answer
    assert [(g.state, g.level) for g in gaps] == [("KA", "no_data")]


def test_no_state_named_answers_from_central_and_asks_which_state(monkeypatch, tmp_path):
    seen = {}
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: seen.update(state=c.state) or [chunk("c1", "IN")])
    r, _ = run(knowledge.Knowledge(tmp_path), plan(state=None, needs=[{"type": "explanation", "subject": "how to apply"}]), "It covers crops [E1].")
    assert r.kind == "answer" and seen["state"] is None and "Which state" in r.answer


def test_nothing_anywhere_says_so_and_records_it(tmp_path):
    r, gaps = run(knowledge.Knowledge(tmp_path), plan(state="Goa", needs=[{"type": "procedure", "subject": "how to apply"}]))
    assert r.kind == "not_covered" and "Goa" in r.answer and r.trace["calls"] == 1
    assert gaps[0].level == "no_data" and gaps[0].state == "GA"


def test_one_text_search_serves_several_needs(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: calls.append(q) or [chunk("c1", "AP")])
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=[{"type": "procedure", "subject": "how to apply"}, {"type": "explanation", "subject": "how to apply"}]), "Text [E1].")
    assert len(calls) == 1 and len(r.sources) == 1


def test_gap_log_keeps_no_question_text(tmp_path):
    log = gaps_module.GapLog(tmp_path / "g.jsonl")
    log.report(gaps_module.Gap("agriculture", "KA", "deadline", "PMFBY", "no_data", TODAY))
    row = json.loads((tmp_path / "g.jsonl").read_text(encoding="utf-8"))
    assert set(row) == {"domain", "state", "data_type", "subject", "level", "date"}


def test_a_failing_gap_log_never_costs_an_answer(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    gaps_module.GapLog(blocker / "g.jsonl").report(gaps_module.Gap("a", "KA", "form", "x", "no_data", TODAY))


def test_a_chosen_state_beats_the_models_guess(kb):
    r, _ = run(kb, plan(state="Telangana", needs=[{"type": "deadline", "subject": "cut-off rabi"}]), state="AP")
    assert r.state == "AP"


def test_a_state_named_in_the_question_beats_the_chosen_one(tmp_path):
    r, _ = run(knowledge.Knowledge(tmp_path), plan(state=None, needs=[{"type": "procedure", "subject": "how to apply"}]),
               state="AP", q="how do i apply in tamil nadu")
    assert r.state == "TN"


def test_the_models_reading_is_used_when_nothing_else_says(kb):
    r, _ = run(kb, plan(state="Andhra Pradesh"))
    assert r.state == "AP"


def test_off_topic_results_get_one_more_search_then_count_as_missing(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: calls.append(q) or [chunk("c1", "IN", "PM-KISAN pays income support.")])
    r, gaps = run(knowledge.Knowledge(tmp_path), plan(state="Karnataka", needs=[{"type": "eligibility", "subject": "Rythu Bharosa"}]))
    assert len(calls) == 2 and calls[1] == "Rythu Bharosa" and r.kind == "not_covered" and gaps[0].level == "no_data"


def test_the_second_search_can_rescue_the_question(tmp_path, monkeypatch):
    def search(q, c):
        return [chunk("c2", "IN", "Rythu Bharosa rules.")] if q == "Rythu Bharosa" else [chunk("c1", "IN", "Something else.")]
    monkeypatch.setitem(agent.TOOLS, "text_search", search)
    r, _ = run(knowledge.Knowledge(tmp_path), plan(state="Karnataka", needs=[{"type": "eligibility", "subject": "Rythu Bharosa"}]), "Rules say [E1].")
    assert r.kind == "answer" and r.coverage[0]["level"] == "central_text"


def test_a_generic_subject_is_never_called_off_topic():
    assert checks.on_topic([Evidence("a", "t", "unrelated", "doc")], "scheme application process")


def test_one_common_word_is_not_enough_to_be_on_topic():
    results = [Evidence("a", "t", "PM-Kisan income support", "doc")]
    assert not checks.on_topic(results, "Mukhyamantri Kisan Kalyan Yojana")
    assert checks.on_topic(results, "PM Kisan")


def test_rti_at_its_rate_limit_says_busy_not_an_error(kb, monkeypatch):
    import answer as rag_answer  # rag/ is on the path once the agent has loaded search

    def fail(*a, **k):
        raise RuntimeError("vendor limit")
    monkeypatch.setattr(rag_answer, "answer_question", fail)
    r, _ = run(kb, json.dumps({"domain": "rti"}), q="rti fee")
    assert r.kind == "failed" and "busy" in r.answer


# ---------------------------------------------------------------- exact facts

def test_plan_is_made_without_any_document_text(kb):
    m = models(plan())
    agent.answer("rabi cut-off?", models=m, knowledge=kb, as_of=TODAY, gaps=Gaps())
    assert DATE["text"] not in json.dumps(m.provider.sent[0][1])


MIXED = [{"type": "deadline", "subject": "cut-off rabi"}, {"type": "procedure", "subject": "how to apply"}]


def test_the_model_never_sees_exact_figures(kb, monkeypatch):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP")])
    m = models(plan(needs=MIXED), "Enrol before it closes [E1].")
    agent.answer("rabi cut-off?", models=m, knowledge=kb, as_of=TODAY, gaps=Gaps())
    composer_sent = json.dumps(m.provider.sent[1][1])
    assert "15 December" not in composer_sent and "2026-12-15" not in composer_sent and "EXACT" in composer_sent


def test_garbled_figure_in_the_explanation_is_rejected_and_never_shown(kb, monkeypatch):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP")])
    r, _ = run(kb, plan(needs=MIXED), "Rabi closes 25 December 2026 [E1].", "It closes on 25 December [E1].")
    assert "25 December" not in r.answer and "15 December 2026" in r.answer
    assert r.trace["first_try_problems"] and r.trace["calls"] == 3


def test_exact_records_that_answer_everything_need_no_answer_model(kb):
    r, _ = run(kb, plan())
    assert r.trace["calls"] == 1 and "Open now" in r.answer


def test_telugu_windows_are_printed_in_telugu_with_no_answer_model(kb):
    r, _ = run(kb, plan(language="telugu"))
    assert r.trace["calls"] == 1 and "15 డిసెంబర్ 2026" in r.answer and "తెరిచి ఉంది" in r.answer


def test_a_rule_without_telugu_goes_to_the_model_in_telugu(kb):
    r, _ = run(kb, plan(language="telugu", needs=NEED_RULE), "తెలుగు వివరణ.", q="premium rule scheme?")
    assert r.trace["calls"] == 2 and "తెలుగు వివరణ" in r.answer


def test_a_rule_with_telugu_is_printed_in_telugu(tmp_path):
    rule = {**RULE, "render_telugu": "{percent}% చెల్లించాలి", "ask_as_telugu": {"crop": "పంట"},
            "cases": [{**c, "label_telugu": "ఒక రకం"} for c in RULE["cases"][:1]]}
    sorter.file_records([rule], tmp_path)
    r, _ = run(knowledge.Knowledge(tmp_path), plan(language="telugu", needs=NEED_RULE), q="premium rule scheme?")
    assert r.trace["calls"] == 1 and "ఒక రకం" in r.answer and "5% చెల్లించాలి" in r.answer and "పంట" in r.answer


def test_schemes_with_the_same_rates_share_one_line(tmp_path):
    other = {**RULE, "id": "r2", "name": "RWBCIS"}
    sorter.file_records([{**RULE, "name": "PMFBY"}, other], tmp_path)
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=NEED_RULE), q="premium rule scheme?")
    assert r.answer.count("[E") == 1 and "PMFBY and RWBCIS" in r.answer and r.trace["calls"] == 1


def test_a_short_rate_limit_is_waited_out_once(monkeypatch):
    slept = []
    monkeypatch.setattr(llm.time, "sleep", slept.append)
    m = llm.Models(Fake(llm.RateLimited("a", retry_after=3), "fine"), {"plan": ("a",)})
    assert m.call("plan", [], llm.Meter()).text == "fine" and slept == [3]
    m = llm.Models(Fake(llm.RateLimited("a", retry_after=90)), {"plan": ("a",)})
    with pytest.raises(llm.RateLimited):
        m.call("plan", [], llm.Meter())


def test_rice_gets_its_own_deadline_not_the_general_one():
    rice = {"scheme": "PMFBY", "opens": "2026-10-01", "closes": "2026-12-31", "applies_to": ["rice", "paddy"]}
    rest = {"scheme": "PMFBY", "opens": "2026-10-01", "closes": "2026-12-15", "except": ["rice", "paddy"]}
    assert facts.windows_for([rest, rice], "i grow paddy", TODAY) == [rice]
    assert len(facts.windows_for([rest, rice], "what is the last date", TODAY)) == 2


def test_a_crop_only_one_scheme_names_still_sees_the_other_schemes_general_window():
    rice = {"scheme": "PMFBY", "opens": "2026-10-01", "closes": "2026-12-31", "applies_to": ["rice"]}
    rest = {"scheme": "PMFBY", "opens": "2026-10-01", "closes": "2026-12-15", "except": ["rice"]}
    tomato = {"scheme": "RWBCIS", "opens": "2026-10-01", "closes": "2026-12-15", "applies_to": ["tomato"]}
    assert facts.windows_for([rice, rest, tomato], "my tomato crop", TODAY) == [rest, tomato]


def test_a_named_scheme_excludes_the_other():
    a = {"scheme": "PMFBY", "scheme_words": ["pmfby"], "opens": "2026-10-01", "closes": "2026-12-15"}
    b = {"scheme": "RWBCIS", "scheme_words": ["weather"], "opens": "2026-10-01", "closes": "2026-12-15"}
    assert facts.windows_for([a, b], "weather insurance date", TODAY) == [b]


def test_closed_window_says_closed_and_open_window_counts_days():
    closed = {"scheme": "X", "opens": "2026-04-01", "closes": "2026-07-15"}
    assert "Closed" in facts.window_fact(closed, TODAY)
    assert facts.windows_for([closed], "date", TODAY) == [closed]
    opened = {"scheme": "X", "opens": "2026-10-01", "closes": "2026-11-15"}
    assert "closes in 11 days" in facts.window_fact(opened, TODAY)


def test_rule_cases_are_kept_apart():
    text = facts.all_cases_fact({"name": "S", "render": "pays {p}%", "cases": [
        {"label": "Commercial", "when": {"c": "x"}, "outcome": {"p": 5}},
        {"label": "Food, Rabi", "when": {"c": "y"}, "outcome": {"p": 1.5}}]})
    assert "(1) Commercial: pays 5%." in text and "(2) Food, Rabi: pays 1.5%." in text


def test_a_window_that_closes_before_it_opens_is_rejected():
    assert any("closes before" in p for p in knowledge.problems({**DATE, "closes": "2026-01-01"}))


def test_facts_decide_the_rule(kb):
    r, _ = run(kb, plan(needs=NEED_RULE, facts={"crop": "commercial"}), q="premium rule scheme?")
    assert "percent: 5" in r.answer and r.trace["missing"] == []


def test_missing_facts_show_every_case_and_ask(kb):
    r, _ = run(kb, plan(needs=NEED_RULE), q="premium rule scheme?")
    assert r.trace["missing"] == ["crop", "income"] and "tell me your crop, income" in r.answer
    assert "(1) crop is commercial" in r.answer and "(2)" in r.answer


def test_rule_inputs_reach_the_planner(tmp_path):
    sorter.file_records([{**RULE, "inputs": {"crop": ["food", "commercial"]}}], tmp_path)
    m = models(json.dumps({"domain": "other"}))
    agent.answer("premium rule scheme?", models=m, knowledge=knowledge.Knowledge(tmp_path), as_of=TODAY, gaps=Gaps())
    assert "commercial" in json.dumps(m.provider.sent[0][1])


def test_any_citation_style_is_understood():
    for raw in ("x 【E2†L1-L4】", "x [2]", "x [E2]", "x (E2)", "x [E2, E3]"):
        assert "[E2]" in checks.tidy_citations(raw)


# ---------------------------------------------------------------- failure

def test_failed_check_regenerates_then_falls_back_to_the_facts(kb, monkeypatch):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP")])
    r, _ = run(kb, plan(needs=MIXED), "You pay 9% [E1].", "Still 9% [E1].")
    assert "9%" not in r.answer and "15 December 2026" in r.answer and r.trace["calls"] == 3


def test_rate_limit_moves_to_the_next_model(kb):
    m = models(llm.RateLimited("p1"), plan())
    assert agent.answer("rabi cut-off?", models=m, knowledge=kb, as_of=TODAY, gaps=Gaps()).kind == "answer"
    assert "p1" in m.resting


def test_vendor_format_failure_moves_to_the_next_model(kb):
    r, _ = run(kb, llm.BadOutput("p1"), plan())
    assert r.kind == "answer"


def test_vendor_json_failure_retries_without_json_mode(kb):
    m = models(llm.BadOutput("p1"), plan())
    seen = []
    complete = m.provider.complete
    m.provider.complete = lambda model, msgs, json_mode=False: seen.append(json_mode) or complete(model, msgs, json_mode)
    assert agent.answer("rabi cut-off?", models=m, knowledge=kb, as_of=TODAY, gaps=Gaps()).kind == "answer"
    assert seen[:2] == [True, False]


def test_a_short_rate_limit_rests_only_that_long():
    m = models(llm.RateLimited("p1", retry_after=5), "fine")
    m.call("plan", [], llm.Meter())
    assert m.resting["p1"] - time.time() < 10


def test_without_an_explanation_no_raw_document_text_is_shown(tmp_path, monkeypatch):
    raw = "The P.S. to the Hon'ble Minister for Food and Civil Supplies"
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", raw)])
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=[{"type": "procedure", "subject": "how to apply"}]), llm.LLMError("down"))
    assert raw not in r.answer and "doc c1" in r.answer and "try again" in r.answer


def test_compose_failure_still_gives_facts(kb, monkeypatch):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP")])
    r, _ = run(kb, plan(needs=MIXED), llm.LLMError("down"))
    assert r.kind == "answer" and "15 December 2026" in r.answer and r.sources


def test_budget_is_never_exceeded():
    meter = llm.Meter(limit=1)
    m = models("a", "b")
    m.call("plan", [], meter)
    with pytest.raises(llm.BudgetExceeded):
        m.call("plan", [], meter)


def test_rti_stays_on_the_old_pipeline(kb, monkeypatch):
    called = {}
    monkeypatch.setattr(agent, "_legacy", lambda q, h, p: called.update(q=q) or agent.Result("legacy", "old", "rti"))
    r, _ = run(kb, json.dumps({"domain": "rti"}), q="rti fee")
    assert r.kind == "legacy" and called["q"] == "rti fee"


def test_off_topic_is_declined_with_one_call(kb):
    r, _ = run(kb, json.dumps({"domain": "other"}), q="passport?")
    assert r.kind == "decline" and r.trace["calls"] == 1


def test_id_numbers_never_reach_the_model(kb):
    m = models(json.dumps({"domain": "other"}))
    agent.answer("my aadhaar 1234 5678 9012 is it ok", models=m, knowledge=kb, as_of=TODAY, gaps=Gaps())
    assert "5678" not in json.dumps(m.provider.sent[0][1])


def test_telugu_notes_are_in_telugu(monkeypatch, tmp_path):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "IN")])
    r, _ = run(knowledge.Knowledge(tmp_path), plan(state=None, language="telugu", needs=[{"type": "procedure", "subject": "how to apply"}]), "తెలుగు [E1].")
    assert "మీది ఏ రాష్ట్రం" in r.answer


# ---------------------------------------------------------------- the web page

def test_page_is_the_shared_page_with_a_state_picker():
    page = web.page_html()
    assert 'id="reply"' in page and "Karnataka" in page and "{{" not in page and "python -m vetra.web" in page


def test_result_reaches_the_page_in_the_shape_it_renders():
    r = agent.Result("answer", "Closes soon [E1].", "agriculture", "AP", "english",
                     [{"n": 1, "doc": "G.O.", "url": "u", "text": "fact", "tool": "dates_lookup"}], trace={"steps": []})
    out = web.to_page(r)
    assert out["answer"] == "Closes soon [1]." and out["sources"][0]["source"] == "G.O." and out["domain_label"] == "Agriculture"


def test_a_declined_question_has_no_label_or_sources():
    out = web.to_page(agent.Result("decline", "No."))
    assert out["domain_label"] is None and out["sources"] == []


def test_the_readers_language_choice_wins(kb):
    r, _ = run(kb, plan(), reply="telugu")
    assert r.language == "telugu" and "తెరిచి ఉంది" in r.answer


def test_telugu_in_english_letters_goes_to_the_model(kb):
    r, _ = run(kb, plan(), "Idi open lo undi.", reply="telugu_roman")
    assert r.trace["calls"] == 2 and "Idi open lo undi" in r.answer


# ---------------------------------------------------------------- adding a state

class Chunker:
    CHUNK_TOKENS, OVERLAP_TOKENS = 50, 5

    @staticmethod
    def clean(text):
        return " ".join(text.split())

    @staticmethod
    def extract_text(path):
        return path.read_text(encoding="utf-8")

    @staticmethod
    def chunk_tokens(text, count, size, overlap):
        return [text]

    @staticmethod
    def season_of(text, at):
        return ""


def entry(**more):
    return {"title": "Karnataka order", "file": "a.txt", "source_url": "https://x.gov.in/a", "doc_type": "go",
            "date": "2026-06-01", "in_force": "yes", **more}


def test_intake_chunks_a_new_state_with_its_place_on_every_chunk(tmp_path):
    (tmp_path / "a.txt").write_text("A long enough state order about crop insurance. " * 5, encoding="utf-8")
    report = intake.prepare([entry()], tmp_path, "KA", counter=len, chunker=Chunker)
    assert not report.problems and report.chunks[0]["jurisdiction"] == "KA" and report.chunks[0]["in_force"] == "yes"


def test_intake_stops_on_a_bad_manifest_and_reports_scans(tmp_path):
    (tmp_path / "scan.txt").write_text("x", encoding="utf-8")
    report = intake.prepare([{"title": "No fields"}, entry(file="missing.txt"), entry(file="scan.txt")], tmp_path, "KA", counter=len, chunker=Chunker)
    assert len(report.problems) == 2 and any("needs OCR" in w for w in report.warnings)


def test_intake_skips_a_file_already_taken(tmp_path):
    (tmp_path / "a.txt").write_text("Enough text about the crop insurance order here. " * 5, encoding="utf-8")
    first = intake.prepare([entry()], tmp_path, "KA", counter=len, chunker=Chunker).chunks[0]["id"]
    digest = first.split("-")[1].split("::")[0]
    report = intake.prepare([entry()], tmp_path, "KA", {digest}, counter=len, chunker=Chunker)
    assert report.chunks == [] and "already taken" in report.warnings[0]


# ---------------------------------------------------------------- modular by design

def test_every_state_and_ut_is_known():
    assert len(jurisdictions.STATES) == 36
    assert jurisdictions.normalise("tamil nadu") == "TN" and jurisdictions.normalise("Nowhere") is None


def test_finance_and_agriculture_are_live_domains_and_rti_is_frozen():
    assert not DOMAINS["finance"].legacy and not DOMAINS["agriculture"].legacy and DOMAINS["rti"].legacy


def test_a_state_sees_only_its_own_chunks_and_central_ones(monkeypatch):
    items = ({"id": "a", "jurisdiction": "AP", "text": "x"}, {"id": "k", "jurisdiction": "KA", "text": "x"},
             {"id": "c", "jurisdiction": "IN", "text": "x"})
    monkeypatch.setattr(text_index, "corpus", lambda domain: items)
    text_index._view.cache_clear()
    assert {i["id"] for i in text_index._view("t", text_index._places("KA"))[0]} == {"k", "c"}
    assert {i["id"] for i in text_index._view("t", text_index._places(None))[0]} == {"c"}
    text_index._view.cache_clear()


def test_central_chunks_are_labelled_from_their_department():
    assert text_index._applies_in({"department": "central"}, "AP") == "IN"
    assert text_index._applies_in({"department": "Revenue"}, "AP") == "AP"
    assert text_index._applies_in({"jurisdiction": "KA", "department": "central"}, "AP") == "KA"


def test_past_year_history_goes_to_the_model_even_with_exact_data(kb, monkeypatch):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "free in 2024")])
    m = models(plan(needs=MIXED), "It was free in 2024 [E1].")
    r = agent.answer("was it free in 2024?", models=m, knowledge=kb, as_of=TODAY, gaps=Gaps())
    assert "free in 2024" in r.answer and "Open now" not in r.answer


def test_no_module_names_the_llm_vendor_outside_llm_py():
    for path in Path(agent.__file__).parent.glob("*.py"):
        if path.name != "llm.py":
            assert "groq" not in path.read_text(encoding="utf-8").lower(), path.name


# ------------------------------------------------------------------ all languages

def test_all_22_scheduled_languages_and_english_are_known():
    assert len(languages.NAMES) == 23 and {"hindi", "santali", "urdu", "bodo"} <= set(languages.NAMES)


def test_a_detected_language_is_kept_and_an_unknown_one_is_english():
    assert agent.parse_plan(plan(language="tamil")).language == "tamil"
    assert agent.parse_plan(plan(language="klingon")).language == "english"


def test_native_digits_become_western():
    assert languages.western_digits("१५ ౧౫ 15") == "15 15 15"


def test_exact_facts_are_translated_with_the_english_beside_them(tmp_path):
    sorter.file_records([DATE], tmp_path)
    english = facts.window_fact(DATE, TODAY)
    numbers = " ".join(languages._numbers(english))
    r, _ = run(knowledge.Knowledge(tmp_path), plan(language="hindi"), json.dumps({"lines": [f"अनुवाद {numbers}"]}))
    assert f"अनुवाद {numbers} (English: " in r.answer and "15 December 2026" in r.answer


def test_a_translation_that_changes_a_number_is_thrown_away():
    m = models(json.dumps({"lines": ["दिसंबर 16"]}))
    assert languages.translate(["December 15"], "hindi", m, llm.Meter()) == [None]


def test_translation_failure_keeps_the_english():
    m = models("not json")
    assert languages.translate(["December 15"], "hindi", m, llm.Meter()) == [None]


def test_answers_in_native_digits_still_get_the_number_check():
    items = [chunk("c1", "AP", "The fee is Rs 500.")]
    assert checks.claim_problems("शुल्क ५०० रुपये है [E1]", items, TODAY) == []
    assert checks.claim_problems("शुल्क Rs ९०० है [E1]", items, TODAY)


def test_the_model_is_told_the_language():
    assert "Write in tamil" in agent.compose_prompt(TODAY, "tamil", "India")


def test_the_page_offers_every_language():
    assert "हिन्दी" in web.page_html() and "ᱥᱟᱱᱛᱟᱞᱤ" in web.page_html()


# ------------------------------------------------------------------ crops a scheme doesn't cover

def test_a_crop_the_scheme_does_not_cover_gets_no_rate(tmp_path):
    rule = {**RULE, "not_notified": ["cotton"]}
    sorter.file_records([rule], tmp_path)
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=NEED_RULE), q="premium rule scheme for cotton?")
    assert "cotton is not a notified crop" in r.answer and "5%" not in r.answer


def test_the_real_rules_keep_each_schemes_crops_apart():
    k = knowledge.Knowledge()
    records = {r["id"]: r for r in k.select("agriculture", "rules", "AP")}
    pmfby, weather = records["ap-pmfby-premium-rule"], records["ap-rwbcis-premium-rule"]
    assert "cotton" in pmfby["not_notified"] and "cotton" in weather["aliases"]["crop_class"]
    assert "paddy" in weather["not_notified"] and "paddy" in pmfby["aliases"]["crop_class"]
    assert rules.evaluate(weather, {"crop_class": "cashew"}).outcome["farmer_premium_percent_of_sum_insured"] == 5


def test_a_figure_written_after_rs_dot_counts_as_in_the_evidence():
    items = [chunk("c1", "IN", "Benefit of Rs.6000 per year, 1.5 per cent.")]
    assert checks.claim_problems("You get Rs\u202f6000 [E1]", items, TODAY) == []
    assert checks.claim_problems("You get Rs 5 [E1]", items, TODAY)


def test_a_past_year_question_with_only_exact_records_searches_the_old_orders(monkeypatch, tmp_path):
    sorter.file_records([RULE], tmp_path)
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "how to apply: free in Kharif 2024.")])
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=[{"type": "amount", "subject": "how to apply"}]),
               "It was free [E1].", q="premium rule scheme in 2024?")
    assert r.kind == "answer" and "free [E1]" in r.answer


def test_a_state_with_documents_is_not_told_they_are_missing(tmp_path):
    doc = {"id": "x", "store": "documents", "domain": "agriculture", "jurisdiction": "AP", "text": "A document",
           "source": {"doc": "G.O.1"}, "title": "A document"}
    sorter.file_records([doc], tmp_path)
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=[{"type": "contact", "subject": "office"}]))
    assert r.kind == "not_covered" and "aren't in yet" not in r.answer


# ------------------------------------------------------------------ navigation

ENOUGH = json.dumps({"enough": True})
HOW = [{"type": "procedure", "subject": "how to apply"}]


def go(action, **more):
    return json.dumps({"enough": False, "missing": "the fee", "next": [{"action": action, **more}]})


def test_enough_evidence_stops_after_one_judgement(monkeypatch, tmp_path):
    monkeypatch.setattr(navigate, "explore", EXPLORE)
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "how to apply here.")])
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=HOW), ENOUGH, "Apply here [E1].")
    assert r.trace["calls"] == 3 and r.trace["route"]["rounds"] == 1 and not r.trace["route"]["moves"]


def test_a_missing_part_gets_a_second_search_and_is_used(monkeypatch, tmp_path):
    monkeypatch.setattr(navigate, "explore", EXPLORE)
    asked = []

    def search(q, c):
        asked.append(q)
        return [chunk("fee", "AP", "how to apply: the fee is Rs 50.")] if "fee" in q else [chunk("c1", "AP", "how to apply here.")]
    monkeypatch.setitem(agent.TOOLS, "text_search", search)
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=HOW), go("search", query="application fee"), ENOUGH, "The fee is Rs 50 [E2].")
    assert "application fee" in asked and "Rs 50" in r.answer and r.trace["route"]["moves"][0]["found"] == 1


def test_read_more_brings_the_next_passage(monkeypatch, tmp_path):
    monkeypatch.setattr(navigate, "explore", EXPLORE)
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "how to apply: see the table below.")])
    monkeypatch.setitem(agent.TOOLS, "read_around", lambda key, c: [chunk("c2", "AP", f"table after {key}: Rs 70.")])
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=HOW), go("read_more", of="E1"), ENOUGH, "It is Rs 70 [E2].")
    assert "Rs 70" in r.answer and r.trace["route"]["moves"][0] == {"action": "read_more", "target": "c1", "query": "", "found": 1}


def test_navigation_stops_at_its_limit_and_still_answers(monkeypatch, tmp_path):
    monkeypatch.setattr(navigate, "explore", EXPLORE)
    n = iter(range(100))
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk(f"c{next(n)}", "AP", "how to apply here.")])
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=HOW), go("search", query="one"), go("search", query="two"), "Apply here [E1].")
    assert r.trace["route"]["rounds"] == depths.STANDARD.rounds and r.kind == "answer"


def test_the_same_move_is_not_repeated(monkeypatch, tmp_path):
    monkeypatch.setattr(navigate, "explore", EXPLORE)
    n = iter(range(100))
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk(f"c{next(n)}", "AP", "how to apply here.")])
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=HOW), go("search", query="one"), go("search", query="one"), "Apply here [E1].")
    assert len(r.trace["route"]["moves"]) == 1


def test_a_failed_judgement_still_answers_from_what_it_has(monkeypatch, tmp_path):
    monkeypatch.setattr(navigate, "explore", EXPLORE)
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "how to apply here.")])
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=HOW), llm.LLMError("down"), "Apply here [E1].")
    assert "Apply here" in r.answer


def test_off_topic_results_from_a_new_search_are_not_used(monkeypatch, tmp_path):
    monkeypatch.setattr(navigate, "explore", EXPLORE)
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("other", "AP", "Something else entirely.")] if q == "wrong" else [])
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=[{"type": "procedure", "subject": "Mahila Kisan Yojana"}]), go("search", query="wrong"), ENOUGH)
    assert r.kind == "not_covered"


def test_exact_records_that_answer_everything_skip_navigation(kb, monkeypatch):
    monkeypatch.setattr(navigate, "explore", EXPLORE)
    r, _ = run(kb, plan())
    assert r.trace["calls"] == 1 and r.trace["route"]["rounds"] == 0


def test_the_judge_never_sees_exact_figures():
    e = Evidence("d", "dates_lookup", "text", "doc", fact="closes 15 December 2026", note="a window exists")
    assert "15 December" not in navigate._show([e]) and "a window exists" in navigate._show([e])


def test_bad_moves_are_dropped():
    items = [chunk("c1", "AP"), Evidence("d", "dates_lookup", "t", "doc")]
    assert navigate.parse("nonsense", items) == ([], "")
    moves, _ = navigate.parse(go("read_more", of="E9"), items)
    assert moves == []
    moves, _ = navigate.parse(go("read_more", of="E2"), items)   # not a document passage
    assert moves == []
    moves, _ = navigate.parse(go("delete", query="x"), items)
    assert moves == []
    moves, _ = navigate.parse(go("search", query=" ".join(["w"] * 40)), items)
    assert len(moves[0].target.split()) == 12


def test_navigation_keeps_calls_back_for_the_answer():
    m, meter = models(ENOUGH), llm.Meter(calls=4)
    items, route = EXPLORE("q", ["s"], ["agriculture"], [], None, m, meter, lambda x: x, depths.STANDARD)
    assert route.rounds == 0 and meter.calls == 4


def test_read_around_finds_the_neighbours_in_the_same_document(monkeypatch):
    chunks = tuple({"id": f"x::{i}", "source": "doc", "chunk_index": i, "text": str(i)} for i in range(5))
    other = ({"id": "y::2", "source": "other", "chunk_index": 2, "text": "z"},)
    monkeypatch.setattr(text_index, "corpus", lambda domain: chunks + other)
    assert [c["id"] for c in text_index.around("x::2", "agriculture")] == ["x::1", "x::3"]
    assert text_index.around("nope", "agriculture") == []


def test_translated_details_keep_their_english():
    e = Evidence("d", "rule_check", "t", "doc", fact="pays 5%", detail="limited if the actuarial rate is lower")
    m = models(json.dumps({"lines": ["5% देता है", "सीमित"]}))
    agent.localise([e], [], "", "hindi", m, llm.Meter())
    assert e.fact == "5% देता है (English: pays 5%)" and e.detail == "सीमित (English: limited if the actuarial rate is lower)"


# ------------------------------------------------------------------ how far an answer goes

PARTS = [{"type": "procedure", "subject": "how to apply first"}, {"type": "procedure", "subject": "how to apply second"}]


def deep(**more):
    return plan(depth="deep", needs=PARTS, **more)


def test_the_level_comes_from_the_planner_and_defaults_to_standard():
    assert depths.choose("quick", ["deadline"]) is depths.QUICK and depths.choose("deep", ["amount"]) is depths.DEEP
    assert depths.choose(None, ["amount"]) is depths.STANDARD and depths.choose("very long", ["amount"]) is depths.STANDARD


def test_many_parts_cannot_be_a_short_answer():
    assert depths.choose("quick", ["amount", "deadline", "form", "contact"]) is depths.DEEP


def test_explaining_something_in_several_parts_goes_deep_whatever_the_model_called_it():
    assert depths.choose("standard", ["explanation", "eligibility", "eligibility"]) is depths.DEEP
    assert depths.choose("standard", ["eligibility", "amount", "deadline"]) is depths.STANDARD


def test_a_chosen_level_beats_the_planner():
    assert depths.choose("deep", ["amount"] * 6, override="quick") is depths.QUICK


def test_the_planner_is_asked_for_the_level_and_it_is_read():
    assert '"depth"' in agent.planner_prompt(TODAY) and "compare PMFBY" in agent.planner_prompt(TODAY)
    assert agent.parse_plan(plan(depth="deep")).depth == "deep"
    assert agent.parse_plan(plan()).depth == ""     # plans saved before levels existed still read


def test_each_level_shapes_the_answer_differently():
    short, long = agent.compose_prompt(TODAY, "english", "India", depths.QUICK), agent.compose_prompt(TODAY, "english", "India", depths.DEEP)
    assert "one or two sentences" in short and "What changed" not in short
    assert all(w in long for w in ("research brief", "What changed", "Where the sources differ", "What the documents don't settle"))


def test_a_quick_answer_reads_fewer_passages(monkeypatch, tmp_path):
    sizes = []
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: sizes.append(c.k) or [chunk("c1", "AP", "how to apply here.")])
    run(knowledge.Knowledge(tmp_path), plan(depth="quick", needs=HOW), "Apply here [E1].")
    assert sizes == [depths.QUICK.passages]


def test_a_deep_answer_searches_each_part_and_the_whole_question(monkeypatch, tmp_path):
    asked = []
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: asked.append((q, c.topic)) or [chunk(q, "AP", "how to apply here.")])
    run(knowledge.Knowledge(tmp_path), deep(topic="apply scheme"), "Apply here [E1].", '{"unsupported": []}')
    assert ("how to apply first", "") in asked and ("how to apply second", "") in asked   # searched alone
    assert ("Do I pay?", "apply scheme") in asked   # the whole question keeps every search aid


def test_a_subject_without_the_schemes_name_gets_it():
    assert agent._with_topic("who is excluded", "PM-KISAN") == "PM-KISAN who is excluded"
    assert agent._with_topic("PM-KISAN exclusions", "PM-KISAN") == "PM-KISAN exclusions"
    assert agent._with_topic("who is excluded", "") == "who is excluded"


def test_a_standard_answer_shares_one_search(monkeypatch, tmp_path):
    asked = []
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: asked.append(q) or [chunk("c1", "AP", "how to apply: first, then second.")])
    run(knowledge.Knowledge(tmp_path), plan(needs=PARTS), "Apply here [E1].")
    assert asked == ["Do I pay?"]


def test_a_deep_answer_reads_text_alongside_exact_records(monkeypatch, tmp_path):
    sorter.file_records([RULE], tmp_path)
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "premium rule scheme conditions.")])
    r, _ = run(knowledge.Knowledge(tmp_path), plan(depth="deep", needs=NEED_RULE), "It has conditions [E2].", '{"unsupported": []}', q="premium rule scheme?")
    assert r.depth == "deep" and "It has conditions" in r.answer and "\n- " in r.answer
    assert r.trace["calls"] == 3


def test_a_deep_answer_goes_looking_even_when_exact_records_answer(kb, monkeypatch):
    called = []
    monkeypatch.setattr(navigate, "explore", lambda q, subj, dom, items, base, m, meter, tidy, level: called.append(level) or (items, navigate.Route()))
    run(kb, plan(depth="deep"), "Explained [E1].", '{"unsupported": []}')
    assert called == [depths.DEEP]


def test_a_deep_question_always_looks_for_what_changed_and_never_reports_it_missing(monkeypatch, tmp_path):
    asked = []

    def search(q, c):
        asked.append(q)
        return [] if "amended" in q else [chunk("c1", "AP", "how to apply: first, then second.")]
    monkeypatch.setitem(agent.TOOLS, "text_search", search)
    r, gaps = run(knowledge.Knowledge(tmp_path), deep(topic="the scheme"), "Apply here [E1].", '{"unsupported": []}')
    assert "the scheme amended" in asked and not gaps and "amended" not in r.answer
    assert all("amended" not in c["subject"] for c in r.coverage)


def test_a_part_with_nothing_is_named_by_code_and_the_writer_is_told(monkeypatch, tmp_path):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "how to apply here.")] if "apply" in q else [])
    wanted = [{"type": "procedure", "subject": "how to apply"}, {"type": "procedure", "subject": "Mahila Kisan Yojana"}]
    m = models(plan(depth="deep", needs=wanted), "Apply here [E1].", '{"unsupported": []}')
    r = agent.answer("rabi cut-off?", models=m, knowledge=knowledge.Knowledge(tmp_path), as_of=TODAY, gaps=Gaps())
    assert "Not found in the documents we hold: Mahila Kisan Yojana." in r.answer
    sent = next(messages[1]["content"] for _, messages in m.provider.sent if "Evidence:" in messages[1]["content"])
    assert "Parts of the question:\n- how to apply" in sent and "so don't write about them: Mahila Kisan Yojana" in sent


def test_a_scheme_we_do_not_hold_gets_no_overview_from_a_neighbour(monkeypatch, tmp_path):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("near", "AP", "Something else entirely.")])
    wanted = [{"type": "explanation", "subject": "Mahila Kisan Yojana"}]
    r, _ = run(knowledge.Knowledge(tmp_path), plan(depth="deep", topic="Mahila Kisan Yojana", needs=wanted))
    assert r.kind == "not_covered"


def test_shares_take_turns_so_no_part_loses_all_its_evidence():
    many = [chunk(f"a{n}", "AP") for n in range(10)]
    few = [chunk("b1", "AP")]
    found = [agent.Found(agent.Need("procedure", "a"), "text", many), agent.Found(agent.Need("procedure", "b"), "text", few)]
    kept = [e.key for e in agent.share(found, 3)]
    assert kept == ["a0", "b1", "a1"]


def test_exact_records_always_keep_their_place_in_the_share():
    fact = Evidence("f", "rule_check", "t", "doc", fact="pays 5%")
    found = [agent.Found(agent.Need("procedure", "a"), "text", [chunk(f"a{n}", "AP") for n in range(5)]),
             agent.Found(agent.Need("amount", "b"), "exact", [fact])]
    assert "f" in [e.key for e in agent.share(found, 2)]


def test_a_passage_read_for_history_keeps_its_past_seasons():
    now = Evidence("a", "text_search", "Farmers pay nothing.", "doc", season="Kharif 2024")
    then = Evidence("b", "text_search", "Farmers pay nothing.", "doc", season="Kharif 2024", history=True)
    checks.in_force([now, then], TODAY)
    assert "left out here" in now.text and then.text == "Farmers pay nothing." and then.season == "Kharif 2024"


def test_a_passage_found_by_two_parts_counts_as_history_if_either_read_it_for_that():
    plain, marked = chunk("c1", "AP"), chunk("c1", "AP")
    marked.history = True
    found = [agent.Found(agent.Need("procedure", "a"), "text", [plain]), agent.Found(agent.Need("change_history", "b"), "text", [marked])]
    assert agent.share(found, 5)[0].history


def test_a_change_history_need_marks_its_passages(monkeypatch, tmp_path):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "how to apply: replaced in 2025.")])
    m = models(plan(needs=[{"type": "change_history", "subject": "how to apply"}]), "It changed in 2025 [E1].")
    agent.answer("what changed?", models=m, knowledge=knowledge.Knowledge(tmp_path), as_of=TODAY, gaps=Gaps())
    sent = m.provider.sent[-1][1][1]["content"]
    assert "history: may describe earlier seasons" in sent


def test_the_writer_sees_each_sources_kind_and_why_it_was_added():
    e = Evidence("a", "text_search", "Text.", "G.O.34", jurisdiction="AP", kind="government order", relation="amends G.O.80", date="2026-07-06")
    block = agent.evidence_block([e])
    assert "government order" in block and "included because it amends G.O.80" in block and "dated 2026-07-06" in block


def test_chunks_know_what_kind_of_document_they_came_from(tmp_path):
    doc = {"id": "x", "store": "documents", "domain": "agriculture", "jurisdiction": "AP", "text": "A", "legal_weight": "go",
           "source": {"doc": "G.O.34"}}
    sorter.file_records([doc], tmp_path)
    k = knowledge.Knowledge(tmp_path)
    ctx = tools.Context("agriculture", "AP", TODAY, k)
    hits = [{"id": "c", "text": "t", "source": "G.O.34 [Agri]", "title": "G.O.34", "added_because": "amends G.O.80"},
            {"id": "d", "text": "t", "source": "Other", "title": "Other"}]
    first, second = tools._from_chunks(hits, ctx)
    assert first.kind == "government order" and first.relation == "amends G.O.80" and second.kind == ""


def test_documents_without_a_date_are_still_recorded():
    rows = sorter.from_manifest([{"title": "The Seeds Act, 1966", "file": "seeds.pdf", "doc_type": "act", "department": "central"}], "agriculture", "AP")
    assert rows[0]["store"] == "documents" and rows[0]["jurisdiction"] == "IN" and "date not recorded" in rows[0]["text"]


def test_the_page_shows_the_kind_and_marks_amendments():
    r = agent.Result("answer", "Text [E1].", "agriculture", sources=[{"n": 1, "doc": "G.O.34", "kind": "government order", "added_because": "amends G.O.80", "tool": "text_search"}])
    source = web.to_page(r)["sources"][0]
    assert source["source"] == "G.O.34 · government order" and source["added"] is True


def test_every_deep_question_stays_within_its_calls(monkeypatch, tmp_path):
    n = iter(range(100))
    monkeypatch.setattr(navigate, "explore", EXPLORE)
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk(f"c{next(n)}", "AP", "how to apply here.")])
    replies = [deep(), *[go("search", query=f"q{i}") for i in range(depths.DEEP.rounds)], "Apply [E1].",
               '{"unsupported": [1]}', "Apply here [E1].", '{"unsupported": []}', "spare", "spare"]
    r, _ = run(knowledge.Knowledge(tmp_path), *replies)
    assert r.trace["calls"] <= depths.DEEP.calls and r.kind == "answer"


# ------------------------------------------------------------------ checking sentence by sentence

def said(answer):
    return [s.text for s in checks.statements(answer)]


def test_short_forms_do_not_end_a_sentence():
    assert said("You get Rs. 6000 under G.O.Ms.No. 34 here. Then apply.") == ["You get Rs. 6000 under G.O.Ms.No. 34 here.", "Then apply."]


def test_a_citation_after_the_full_stop_stays_with_its_sentence():
    found = checks.statements("Pay 2%. [E3] Enrol by July. [E4]")
    assert [(s.text, s.cited) for s in found] == [("Pay 2%. [E3]", (3,)), ("Enrol by July. [E4]", (4,))]


def test_sentences_end_in_any_script():
    assert len(said("किसान भुगतान करता है। यह स्वैच्छिक है। [E1]")) == 2
    assert len(said("کسان ادا کرتا ہے۔ یہ اختیاری ہے۔ [E1]")) == 2


def test_a_sentence_borrows_the_next_citation_on_its_line_only():
    found = checks.statements("It pays Rs 6000. It comes in three parts [E1].\nNext line has none.")
    assert found[0].cited == (1,) and found[1].cited == (1,) and found[2].cited == ()


def test_headings_and_list_markers_are_not_statements():
    assert said("## Who qualifies\n- Small farmers [E1].\n1. Apply online [E2].\n**Note**") == ["Small farmers [E1].", "Apply online [E2]."]


def test_a_figure_must_be_in_the_passage_its_sentence_cites():
    items = [chunk("a", "AP", "The fee is Rs 500."), chunk("b", "AP", "Apply online.")]
    assert checks.claim_problems("The fee is Rs 500 [E1].", items, TODAY) == []
    problems = checks.claim_problems("The fee is Rs 500 [E2].", items, TODAY)
    assert len(problems) == 1 and "isn't in [E2]" in problems[0]


def test_a_figure_from_any_cited_passage_will_do():
    items = [chunk("a", "AP", "The fee is Rs 500."), chunk("b", "AP", "The fee is Rs 700.")]
    assert checks.claim_problems("One says Rs 500 and one says Rs 700 [E1][E2].", items, TODAY) == []


def test_a_figure_with_no_citation_is_a_fault():
    items = [chunk("a", "AP", "The fee is Rs 500.")]
    assert "has no citation" in checks.claim_problems("The fee is Rs 500.\nApply online [E1].", items, TODAY)[0]


def test_a_figure_the_person_gave_needs_no_citation():
    items = [chunk("a", "AP", "Apply online.")]
    assert checks.claim_problems("With your Rs 500 budget, apply online [E1].", items, TODAY, "i have Rs 500") == []


def test_a_date_must_be_in_the_passage_its_sentence_cites():
    items = [chunk("a", "AP", "Closes on 15 December."), chunk("b", "AP", "Apply online.")]
    assert checks.claim_problems("It closes on 15 December [E1].", items, TODAY) == []
    assert "isn't in [E2]" in checks.claim_problems("It closes on 15 December [E2].", items, TODAY)[0]


def test_rupee_formats_match_each_other():
    items = [chunk("a", "AP", "The fee is Rs 6,000 a year.")]
    assert checks.claim_problems("You pay Rs.6000 [E1].", items, TODAY) == []
    assert checks.claim_problems("You pay ₹6,000 [E1].", items, TODAY) == []


def test_the_source_name_and_date_count_as_what_a_passage_says():
    e = Evidence("a", "text_search", "Rule text.", "PMFBY Guidelines 2023", date="2024-09-04")
    assert checks.claim_problems("The 2023 guidelines, from 2024, say so [E1].", [e], TODAY) == []


def test_a_gap_is_allowed_in_a_long_answer_but_not_a_short_one():
    items = [Evidence("f", "rule_check", "t", "doc", fact="pays 5%", note="a rate"), chunk("a", "AP", "Apply online.")]
    text = "The claim process is not specified [E2]."
    assert checks.faults(text, items, TODAY)
    assert not checks.faults(text, items, TODAY, guard_gaps=False)


def test_a_sentence_can_be_taken_out_cleanly():
    text = "Short answer [E1].\n\n## Fees\n- Bad one [E2].\n\n## Steps\nGood one [E1]. Bad two [E2]."
    kept = checks.without(text, ["Bad one [E2].", "Bad two [E2]."])
    assert kept == "Short answer [E1].\n\n## Steps\nGood one [E1]."


def test_a_heading_left_with_nothing_goes_at_the_end_too():
    assert checks.without("Good [E1].\n\n## Fees\nBad [E2].", ["Bad [E2]."]) == "Good [E1]."


def test_one_bad_sentence_is_left_out_not_the_whole_answer(monkeypatch, tmp_path):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "how to apply online.")])
    bad = "Apply online [E1]. Go to the office [E1]. It costs Rs 900 [E1]."
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=HOW), bad, bad)
    assert "Apply online" in r.answer and "Rs 900" not in r.answer and "left out" in r.answer


def test_when_most_of_it_is_wrong_nothing_of_it_is_used(monkeypatch, tmp_path):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "how to apply online.")])
    bad = "It costs Rs 900 [E1]. It costs Rs 800 [E1]. Apply online [E1]."
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=HOW), bad, bad)
    assert "Apply online" not in r.answer and "couldn't verify" in r.answer


def test_a_failed_rewrite_still_leaves_the_first_answer(monkeypatch, tmp_path):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "how to apply online.")])
    first = "Apply online [E1]. Go there [E1]. It costs Rs 900 [E1]."
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=HOW), first, llm.LLMError("down"))
    assert "Apply online" in r.answer and "Rs 900" not in r.answer and r.trace["rewrite_error"]


def test_a_rewrite_with_more_faults_is_not_used(monkeypatch, tmp_path):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "how to apply online.")])
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=HOW), "Apply online [E1]. Go there [E1]. It costs Rs 900 [E1].",
               "It costs Rs 800 [E1]. It costs Rs 700 [E1].")
    assert "Apply online" in r.answer and "Rs 700" not in r.answer


def test_too_much_evidence_is_thinned_fairly_and_the_answer_still_written(monkeypatch, tmp_path):
    n = iter(range(100))
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk(f"c{next(n)}", "AP", "how to apply: first, then second.") for _ in range(6)])
    r, _ = run(knowledge.Knowledge(tmp_path), deep(), llm.RequestTooLarge("too big"), "Apply here [E1].", '{"unsupported": []}')
    assert "Apply here" in r.answer and 6 <= r.trace["evidence"] < depths.DEEP.evidence


# ------------------------------------------------------------------ a second reader, for deep answers

def deep_run(monkeypatch, tmp_path, *replies):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "how to apply online.")])
    return run(knowledge.Knowledge(tmp_path), deep(), *replies)[0]


def test_a_supported_deep_answer_stands(monkeypatch, tmp_path):
    r = deep_run(monkeypatch, tmp_path, "Apply online [E1].", '{"unsupported": []}')
    assert "Apply online" in r.answer and r.trace["verified"] is True and "left out" not in r.answer


def test_a_short_answer_gets_no_second_reader(monkeypatch, tmp_path):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "how to apply online.")])
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=HOW), "Apply online [E1].")
    assert r.trace["calls"] == 2 and "verified" not in r.trace


def test_an_unsupported_statement_gets_a_rewrite(monkeypatch, tmp_path):
    r = deep_run(monkeypatch, tmp_path, "Apply online [E1]. Bring a photo [E1].", '{"unsupported": [2]}', "Apply online [E1].", '{"unsupported": []}')
    assert "photo" not in r.answer and "left out" not in r.answer and r.trace["first_try_problems"]


def test_a_rewrite_is_told_which_statement_failed(monkeypatch, tmp_path):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "how to apply online.")])
    m = models(deep(), "Apply online [E1]. Bring a photo [E1].", '{"unsupported": [2]}', "Apply online [E1].", '{"unsupported": []}')
    agent.answer("how?", models=m, knowledge=knowledge.Knowledge(tmp_path), as_of=TODAY, gaps=Gaps())
    rewrite = m.provider.sent[3][1][1]["content"]
    assert "Bring a photo [E1]." in rewrite and "isn't backed by the passages" in rewrite


def test_a_statement_still_unsupported_is_left_out(monkeypatch, tmp_path):
    text = "Apply online [E1]. Use the portal [E1]. Bring a photo [E1]."
    r = deep_run(monkeypatch, tmp_path, text, '{"unsupported": [3]}', text, '{"unsupported": [3]}')
    assert "photo" not in r.answer and "Use the portal" in r.answer and "left out" in r.answer


def test_if_the_second_reader_fails_the_answer_stands_and_the_trace_says_so(monkeypatch, tmp_path):
    r = deep_run(monkeypatch, tmp_path, "Apply online [E1].", llm.LLMError("down"))
    assert "Apply online" in r.answer and r.trace["verified"] is False


def test_nonsense_from_the_second_reader_is_ignored(monkeypatch, tmp_path):
    r = deep_run(monkeypatch, tmp_path, "Apply online [E1].", "not json")
    assert "Apply online" in r.answer and r.trace["verified"] is False


def test_the_second_reader_sees_only_what_was_cited_and_can_only_name_real_statements():
    items = [chunk("a", "AP", "First passage."), chunk("b", "AP", "Second passage.")]
    m, meter = models('{"unsupported": [1, 99, "x"]}'), llm.Meter()
    doubted, ran = verify.unsupported("It says so [E1].", items, m, meter)
    sent = m.provider.sent[0][1][1]["content"]
    assert doubted == ["It says so [E1]."] and ran and "First passage" in sent and "Second passage" not in sent


def test_the_second_reader_can_see_exact_facts():
    fact = Evidence("f", "rule_check", "t", "doc", fact="pays 5%", note="limited if the actuarial rate is lower")
    m = models('{"unsupported": []}')
    verify.unsupported("See the rate above [E1].", [fact], m, llm.Meter())
    sent = m.provider.sent[0][1][1]["content"]
    assert "pays 5%" in sent and "limited if the actuarial rate is lower" in sent


# ------------------------------------------------------------------ looking inside a document

def test_it_can_look_inside_a_document(monkeypatch, tmp_path):
    monkeypatch.setattr(navigate, "explore", EXPLORE)
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "how to apply: see Annexure II.")])
    seen = []

    def inside(document, query, c):
        seen.append((document, query))
        return [chunk("c9", "AP", "Annexure II: Rs 70.")]
    monkeypatch.setitem(agent.TOOLS, "look_inside", inside)
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=HOW), go("look_inside", of="E1", query="Annexure II rates"), ENOUGH, "It is Rs 70 [E2].")
    assert seen == [("doc c1", "Annexure II rates")] and "Rs 70" in r.answer


def test_looking_inside_needs_a_real_passage_and_a_query():
    items = [chunk("c1", "AP"), Evidence("d", "dates_lookup", "t", "doc")]
    assert navigate.parse(go("look_inside", of="E1"), items)[0] == []
    assert navigate.parse(go("look_inside", of="E2", query="x"), items)[0] == []
    assert navigate.parse(go("look_inside", of="E1", query="x"), items)[0][0].target == "doc c1"


def test_each_level_limits_how_far_it_looks(monkeypatch, tmp_path):
    monkeypatch.setattr(navigate, "explore", EXPLORE)
    n = iter(range(100))
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk(f"c{next(n)}", "AP", "how to apply here.")])
    r, _ = run(knowledge.Knowledge(tmp_path), plan(depth="quick", needs=HOW), go("search", query="one"), "Apply here [E1].")
    assert r.trace["route"]["rounds"] == depths.QUICK.rounds


def test_moves_are_limited_by_the_level():
    items = [chunk("c1", "AP")]
    many = json.dumps({"enough": False, "next": [{"action": "search", "query": f"q{i}"} for i in range(5)]})
    assert len(navigate.parse(many, items, depths.QUICK.moves)[0]) == 1
    assert len(navigate.parse(many, items, depths.DEEP.moves)[0]) == 3


def test_search_within_stays_inside_the_document(monkeypatch):
    items = [{"id": "a", "source": "doc one", "text": "x", "jurisdiction": "AP"}, {"id": "b", "source": "doc two", "text": "y", "jurisdiction": "AP"},
             {"id": "c", "source": "doc one", "text": "z", "jurisdiction": "AP"}]

    class Index:
        def rank(self, q):
            return [1, 2, 0]

    class Rag:
        @staticmethod
        def _rrf(*votes):
            return votes[0]
    monkeypatch.setattr(text_index, "_view", lambda d, p: (items, Index(), {}))
    monkeypatch.setattr(text_index, "_dense", lambda *a: [1, 2, 0])
    monkeypatch.setattr(text_index, "_rag", lambda: Rag)
    assert [i["id"] for i in text_index.search_within("q", "agriculture", "AP", "doc one")] == ["c", "a"]


def test_a_wrong_citation_is_corrected_by_code():
    items = [chunk("a", "AP", "The fee is Rs 500."), chunk("b", "AP", "Apply online.")]
    fixed = checks.recite("The fee is Rs 500 [E2].", items, TODAY)
    assert fixed == "The fee is Rs 500 [E2]. [E1]" and checks.claim_problems(fixed, items, TODAY) == []


def test_a_missing_citation_is_added_by_code():
    items = [chunk("a", "AP", "Closes on 15 December 2026.")]
    fixed = checks.recite("It closes on 15 December.\nApply online [E1].", items, TODAY)
    assert "It closes on 15 December. [E1]" in fixed and checks.claim_problems(fixed, items, TODAY) == []


def test_an_invented_figure_is_not_given_a_source():
    items = [chunk("a", "AP", "The fee is Rs 500.")]
    assert checks.recite("The fee is Rs 900 [E1].", items, TODAY) == "The fee is Rs 900 [E1]."


def test_a_right_figure_with_a_wrong_citation_costs_no_rewrite(monkeypatch, tmp_path):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("a", "AP", "how to apply: fee Rs 500."), chunk("b", "AP", "how to apply online.")])
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=HOW), "The fee is Rs 500 [E2].")
    assert r.trace["calls"] == 2 and "[E1]" in r.answer and "first_try_problems" not in r.trace


def test_misread_amounts_are_corrected_when_documents_are_read():
    module = intake._chunker()
    assert "Rs.6000/-" in module.clean("benefit of Rs.60001 per annum") and "Rs.20011" in module.clean("cost Rs.20011 here")


def test_a_brief_gives_the_printed_records_a_heading(monkeypatch, tmp_path):
    sorter.file_records([RULE], tmp_path)
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "premium rule scheme conditions.")])
    r, _ = run(knowledge.Knowledge(tmp_path), plan(depth="deep", needs=NEED_RULE), "It has conditions [E2].", '{"unsupported": []}', q="premium rule scheme?")
    assert r.answer.startswith("## From the official records\n\n- ")


def test_a_short_answer_has_no_headings_of_ours(kb):
    r, _ = run(kb, plan())
    assert "##" not in r.answer


def test_the_page_says_a_brief_takes_longer():
    assert "up to a minute for a full brief" in web.page_html()


def test_the_answer_must_not_talk_about_its_own_prompt():
    items = [chunk("a", "AP", "Apply online.")]
    for bad in ("The rates are in the EXACT record [E1].", "The evidence states this [E1].", "The provided excerpts say so [E1]."):
        assert any("talks about the evidence" in f.why for f in checks.faults(bad, items, TODAY)), bad
    assert not checks.faults("Bring evidence of land ownership [E1].", items, TODAY)
    assert not checks.faults("The evidence of ownership is a patta [E1]. It must be exact [E1].", items, TODAY)


def test_working_notes_condemn_the_whole_answer_not_one_sentence():
    items = [chunk("a", "AP", "Apply online.")]
    for notes in ("Apply online [E1]. Wait, that is another scheme.", "I must not mix them [E1].", "[E1] is about something else.",
                  "*Correction based on the rules:* apply online [E1].", "The snippet says apply online [E1]."):
        assert any(f.sentence == "" and "working notes" in f.why for f in checks.faults(notes, items, TODAY)), notes


def test_an_answer_of_working_notes_is_never_shown(monkeypatch, tmp_path):
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda q, c: [chunk("c1", "AP", "how to apply online.")])
    notes = "Apply online [E1]. Go there [E1]. Wait, that is wrong [E1]."
    r, _ = run(knowledge.Knowledge(tmp_path), plan(needs=HOW), notes, notes)
    assert "Wait" not in r.answer and "Apply online" not in r.answer and "couldn't verify" in r.answer


def test_ordinary_words_are_not_working_notes():
    items = [chunk("a", "AP", "Apply online.")]
    for fine in ("If you wait, the window closes [E1].", "This is what I can tell you [E1].", "See the rule in [E1] for this."):
        assert not any("working notes" in f.why for f in checks.faults(fine, items, TODAY)), fine


def test_a_date_after_with_effect_from_stays_in_its_sentence():
    assert len(said("It was revised \"w.e.f. 1.6.2019\" for all farmers [E1].")) == 1


def test_a_models_reasoning_tags_never_reach_the_answer(monkeypatch):
    class Response:
        ok, status_code, headers, text = True, 200, {}, ""

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": "<think>let me see\nmaybe</think>\nApply online."}}]}
    import requests
    monkeypatch.setattr(requests, "post", lambda *a, **k: Response)
    assert llm.OpenAICompatible("http://x", "k").complete("m", []).text == "Apply online."


def test_an_answer_with_a_sentence_cut_still_goes_to_the_second_reader(monkeypatch, tmp_path):
    text = "Apply online [E1]. Use the portal [E1]. Bring a photo [E1]. It costs Rs 900 [E1]."
    r = deep_run(monkeypatch, tmp_path, text, text, '{"unsupported": [3]}')
    assert "Rs 900" not in r.answer and "photo" not in r.answer and "Use the portal" in r.answer
    assert r.trace["verified"] is True and "left out" in r.answer


def test_the_writer_and_the_second_reader_keep_schemes_apart():
    assert "another scheme's document is not a rule of this one" in agent.compose_prompt(TODAY, "english", "India")
    assert "different scheme" in verify._PROMPT


def test_a_date_broken_up_by_a_scan_still_counts():
    items = [chunk("a", "IN", "The Scheme was later on revised w.e.f. 1 .6.2019 for all.")]
    assert checks.claim_problems("It was revised from 1.6.2019 [E1].", items, TODAY) == []


def test_a_year_inside_a_written_date_counts_but_part_of_a_decimal_does_not():
    items = [chunk("a", "AP", "It runs until 28.02.2027, at 1.5 percent.")]
    assert checks.claim_problems("It runs into 2027 [E1].", items, TODAY) == []
    assert checks.claim_problems("You pay 5% [E1].", items, TODAY)


def test_the_second_reader_sees_each_statements_section():
    items = [chunk("a", "AP", "First passage.")]
    m = models('{"unsupported": []}')
    verify.unsupported("Opening line [E1].\n\n## Who qualifies\nIt covers small farmers [E1].", items, m, llm.Meter())
    sent = m.provider.sent[0][1][1]["content"]
    assert "1. [opening] (E1) Opening line" in sent and "2. [Who qualifies] (E1) It covers small farmers" in sent


def test_a_rewrite_with_no_citations_does_not_replace_a_mostly_good_answer(monkeypatch, tmp_path):
    first = "Apply online [E1]. Use the portal [E1]. Bring a photo [E1]."
    r = deep_run(monkeypatch, tmp_path, first, '{"unsupported": [3]}', "Apply online, using the portal.", '{"unsupported": []}')
    assert "Use the portal [E1]" in r.answer and "photo" not in r.answer and "couldn't verify" not in r.answer


# ------------------------------------------------------------------ searching Indian-language documents

def test_keyword_search_can_read_indian_scripts_whole():
    assert text_index.words("पीक विमा योजना।") == ["पीक", "विमा", "योजना"]
    assert text_index.words("పంట బీమా") == ["పంట", "బీమా"]
    assert text_index.words("فصل بیمہ") == ["فصل", "بیمہ"]
    assert text_index.words("PMFBY 2026-27 Rs.6000") == ["pmfby", "2026", "27", "rs", "6000"]


def test_keyword_search_finds_a_marathi_document_and_english_ranks_as_before():
    bm25 = text_index._rag()._BM25(["पीक विमा योजना", "crop insurance scheme", "other text"], tokenize=text_index.words)
    assert bm25.rank("पीक विमा")[0] == 0 and bm25.rank("crop insurance")[0] == 1


def test_rti_search_keeps_its_own_tokenizer():
    R = text_index._rag()
    assert R._BM25(["crop insurance"]).tokenize is R._tokens


def test_every_embedding_model_has_its_own_place_in_the_index():
    tags = [e.tag for e in text_index.EMBEDDINGS.values()]
    assert len(tags) == len(set(tags)) and "BAAI/bge-m3" in text_index.EMBEDDINGS


# ------------------------------------------------------------------ what the script settles

def test_a_script_with_one_language_settles_it_whatever_the_model_said():
    assert languages.settle("english", "పంట బీమా ప్రీమియం ఎంత") == "telugu"
    assert languages.settle("hindi", "ਫ਼ਸਲ ਬੀਮੇ ਦਾ ਪ੍ਰੀਮੀਅਮ") == "punjabi"
    assert languages.settle("english", "ᱯᱷᱚᱥᱚᱞ ᱵᱤᱢᱟ") == "santali"


def test_a_shared_script_keeps_the_models_choice_if_it_fits():
    assert languages.settle("marathi", "पीक विम्याचा हप्ता") == "marathi"
    assert languages.settle("assamese", "শস্য বীমাৰ") == "assamese"
    assert languages.settle("sindhi", "فصل بيمي") == "sindhi"


def test_a_shared_script_falls_back_when_the_model_is_plainly_wrong():
    assert languages.settle("english", "फसल बीमा का प्रीमियम") == "hindi"
    assert languages.settle("tamil", "ফসল বিমার") == "bengali"
    assert languages.settle("english", "فصل بیمہ") == "urdu"


def test_english_letters_leave_the_model_to_decide():
    assert languages.settle("hindi", "fasal bima ka premium kitna hai") == "hindi"
    assert languages.settle("english", "how much is the premium") == "english"


def test_a_scheme_name_in_english_letters_does_not_change_the_script():
    assert languages.settle("english", "PMFBY का प्रीमियम कितना है") == "hindi"


def test_a_wrong_language_from_the_planner_is_corrected_in_the_answer(kb):
    m = models(plan(language="english"))
    r = agent.answer("పంట బీమా rabi cut-off?", models=m, knowledge=kb, as_of=TODAY, gaps=Gaps())
    assert r.language == "telugu" and "డిసెంబర్" in r.answer


def test_a_line_translated_once_costs_nothing_the_second_time():
    m, meter = models(json.dumps({"lines": ["नमस्ते"]})), llm.Meter()
    assert languages.translate(["Hello"], "hindi", m, meter) == ["नमस्ते"]
    assert languages.translate(["Hello"], "hindi", m, meter) == ["नमस्ते"]
    assert meter.calls == 1


def test_only_lines_not_yet_translated_are_sent():
    m, meter = models(json.dumps({"lines": ["नमस्ते"]}), json.dumps({"lines": ["अलविदा"]})), llm.Meter()
    languages.translate(["Hello"], "hindi", m, meter)
    assert languages.translate(["Hello", "Bye"], "hindi", m, meter) == ["नमस्ते", "अलविदा"]
    assert '["Bye"]' in m.provider.sent[1][1][1]["content"]


def test_a_failed_translation_is_not_saved():
    m = models("not json", json.dumps({"lines": ["नमस्ते"]}))
    assert languages.translate(["Hello"], "hindi", m, llm.Meter()) == [None]
    assert languages.translate(["Hello"], "hindi", m, llm.Meter()) == ["नमस्ते"]


def test_translations_are_kept_per_language():
    m = models(json.dumps({"lines": ["नमस्ते"]}), json.dumps({"lines": ["வணக்கம்"]}))
    languages.translate(["Hello"], "hindi", m, llm.Meter())
    assert languages.translate(["Hello"], "tamil", m, llm.Meter()) == ["வணக்கம்"]


def test_a_plan_missing_its_topic_takes_it_from_its_parts():
    reply = json.dumps({"language": "kashmiri", "standalone": "premium?", "needs": [{"type": "amount", "subject": "premium", "domain": "agriculture"}]})
    assert agent.parse_plan(reply).domain == "agriculture"
    assert agent.parse_plan(json.dumps({"language": "english", "needs": []})) is None


# ------------------------------------------------------------------ provider behaviour

class Response:
    def __init__(self, status=200, text="ok"):
        self.status_code, self.ok, self.headers, self.text = status, status == 200, {}, text

    def json(self):
        return {"choices": [{"message": {"content": self.text}}], "usage": {"total_tokens": 5}}


def test_a_busy_model_is_passed_over_and_costs_no_budget():
    m, meter = models(), llm.Meter()
    m.provider.replies = [llm.RateLimited("c1", llm.BUSY_SECONDS), "written"]
    assert m.call("compose", [], meter).text == "written" and meter.calls == 1


def test_a_busy_or_retired_model_counts_as_unavailable(monkeypatch):
    import requests
    for status in (503, 404):
        monkeypatch.setattr(requests, "post", lambda *a, **k: Response(status))
        with pytest.raises(llm.RateLimited):
            llm.OpenAICompatible("http://x", "k").complete("m", [])


def test_hidden_thinking_is_set_per_model(monkeypatch):
    import requests
    sent = []
    monkeypatch.setattr(requests, "post", lambda *a, **k: sent.append(k["json"]) or Response())
    provider = llm.OpenAICompatible("http://x", "k", reasoning={"big": "none"})
    provider.complete("big", [])
    provider.complete("small", [])
    assert sent[0]["reasoning_effort"] == "none" and "reasoning_effort" not in sent[1]


def test_the_planner_sees_earlier_questions_but_not_earlier_answers(kb):
    fake = Fake(plan(domain="other"))
    m = llm.Models(fake, {"plan": ("p1",), "compose": ("c1",)})
    agent.answer("and tomato?", history=[{"q": "cashew date in AP", "a": "SECRET passage from a document"}], models=m, knowledge=kb, as_of=TODAY, gaps=Gaps())
    sent = str(fake.sent)
    assert "cashew date in AP" in sent and "SECRET" not in sent


def test_id_numbers_in_earlier_turns_never_reach_a_model(kb):
    fake = Fake(plan(domain="other"))
    m = llm.Models(fake, {"plan": ("p1",), "compose": ("c1",)})
    agent.answer("and tomato?", history=[{"q": "my aadhaar is 1234 5678 9012", "a": "ok"}], models=m, knowledge=kb, as_of=TODAY, gaps=Gaps())
    assert "1234 5678" not in str(fake.sent)


def test_a_rule_counts_for_any_year_it_ran_not_only_its_last():
    old = Evidence("a", "rule_check", "Rate 2%.", "doc", valid_from="2022-04-01", valid_until="2025-03-31")
    assert checks.in_force([old], "2026-11-05", "what was the rate in 2024") == [old]
    assert checks.in_force([old], "2026-11-05", "what was the rate in 2020") == []
    assert checks.in_force([old], "2026-11-05", "what is the rate") == []


def test_keyword_search_treats_spellings_of_one_word_as_the_same():
    assert text_index.words("\u0915\u094d\u200d\u0937\u0947\u0924\u094d\u0930") == text_index.words("\u0915\u094d\u0937\u0947\u0924\u094d\u0930")
    assert text_index.words("\u0968\u0966\u0966\u0966 rupees") == ["2000", "rupees"]
    assert text_index.words("\u0c68\u0c66 \u0be8\u0be6") == ["20", "20"]
    assert text_index.words("\uabc1\uabe4\uabc7")
    assert text_index.words("\ufe8d\ufe91") == text_index.words("\u0627\u0628")


def test_token_details_are_kept_for_cost_checks(monkeypatch):
    class Response:
        ok, status_code, text = True, 200, ""

        def json(self):
            return {"choices": [{"message": {"content": "x"}}], "usage": {
                "total_tokens": 30, "prompt_tokens": 20, "completion_tokens": 10,
                "prompt_tokens_details": {"cached_tokens": 5}, "completion_tokens_details": {"reasoning_tokens": 4}}}

    import requests
    monkeypatch.setattr(requests, "post", lambda *a, **k: Response())
    reply = llm.OpenAICompatible("http://x", "k").complete("m", [])
    meter = llm.Meter()
    meter.record("plan", reply)
    assert meter.steps[0] == {"role": "plan", "model": "m", "tokens": 30, "in": 20, "out": 10, "cached": 5, "thinking": 4}


def test_more_personal_details_are_masked():
    masked = agent.mask("my pan is ABCDE1234F and mail me at ram.k@example.com please")
    assert "ABCDE1234F" not in masked and "example.com" not in masked and "please" in masked
    assert agent.mask("PMFBY 2026-27 pays Rs.5000") == "PMFBY 2026-27 pays Rs.5000"


def test_keyword_search_reads_the_rest_of_the_scripts():
    assert text_index.words("\u0750\u0751")
    assert text_index.words("\uaae0\uaae1")
    assert text_index.words("\u0d05\u0d35\u0d7b") == text_index.words("\u0d05\u0d35\u0d28\u0d4d\u200d")


def _faults(sentence, passage):
    return [f.why for f in checks.faults(sentence, [Evidence("a", "text_search", passage, "doc")], TODAY)]


def test_the_wrong_scale_is_a_fault_even_with_the_right_digits():
    assert any("lakh or crore" in w for w in _faults("The limit is Rs.3 crore [E1].", "The limit is Rs.3 lakh."))
    assert not _faults("The limit is Rs.3 lakh [E1].", "The limit is Rs.3 lakh.")
    assert not _faults("The limit is Rs.3 lakh [E1].", "The limit is Rs.3,00,000.")
    assert not _faults("The limit is Rs.3 lakh [E1].", "The limit is \u20b93 lakhs.")


def test_a_rounded_large_amount_is_allowed_and_a_different_one_is_not():
    assert not _faults("Spending is 53.47 lakh crore [E1].", "Total expenditure is 53,47,315 crore.")
    assert _faults("Spending is 60 lakh crore [E1].", "Total expenditure is 53,47,315 crore.")


def test_the_wrong_area_is_a_fault():
    assert any("per hectare" in w for w in _faults("It pays Rs.5000 per acre [E1].", "It pays Rs.5000 per hectare."))
    assert not _faults("It pays Rs.5000 per acre [E1].", "It pays Rs.5000 per acre.")
    assert not _faults("It pays Rs.5000 per hectare [E1].", "It pays Rs.5000/ha.")


def _window(season, closes, **more):
    return {"scheme": "PMFBY", "for_season": season, "opens": "2026-01-01", "closes": closes, **more}


def test_a_named_season_gets_that_seasons_dates_even_when_another_is_open():
    kharif, rabi = _window("Kharif 2026", "2026-08-15"), _window("Rabi 2026-27", "2026-12-31")
    assert facts.windows_for([kharif, rabi], "last date for kharif 2026", TODAY) == [kharif]
    assert facts.windows_for([kharif, rabi], "last date for kharif", TODAY) == [kharif]
    assert facts.windows_for([kharif, rabi], "last date for rabi 2026-27", TODAY) == [rabi]
    assert facts.windows_for([kharif, rabi], "what is the last date", TODAY) == [rabi]


def test_a_record_on_another_topic_is_not_an_answer():
    rule = {"topic_words": ["insur", "premium"], "text": "Crop insurance"}
    assert facts.on_its_topic([rule], "how much does annadatha sukhibhava pay a farmer") == []
    assert facts.on_its_topic([rule], "what premium do i pay") == [rule]
    assert facts.on_its_topic([{"text": "No list"}], "anything") == [{"text": "No list"}]


def test_the_real_rules_stay_off_other_schemes_questions():
    kb = knowledge.Knowledge()
    ctx = lambda q: Context("agriculture", "AP", TODAY, kb, question=q)
    from vetra.tools import TOOLS
    assert not TOOLS["rule_check"]("farmer family amount per year Annadatha Sukhibhava", ctx("how much does a farmer family get under annadatha sukhibhava"))
    assert TOOLS["rule_check"]("farmer pays premium paddy rabi crop insurance PMFBY", ctx("what premium for paddy in rabi under pmfby"))


def test_a_timeout_moves_on_to_the_next_model(monkeypatch):
    import requests

    def post(url, json, **k):
        if json["model"] == "slow":
            raise requests.Timeout()
        return Response()

    monkeypatch.setattr(requests, "post", post)
    m = llm.Models(llm.OpenAICompatible("http://x", "k"), {"compose": ("slow", "quick")})
    meter = llm.Meter()
    assert m.call("compose", [], meter).model == "quick" and meter.calls == 1


def test_pointing_to_figures_above_needs_something_printed_above():
    assert any("printed above" in w for w in _faults("It pays the amount stated above each year [E1].", "It pays Rs.6000 a year."))
    printed = Evidence("a", "rule_check", "x", "doc")
    printed.fact, printed.note = "Rs.6000 a year.", "A yearly payment."
    assert not checks.faults("It pays the amount stated above each year [E1].", [printed], TODAY)
    assert not _faults("See the rules above the district level [E1].", "The rules above the district level apply.")


def test_the_hand_read_test_file_is_sound_and_its_sums_are_right():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))
    import gold_test

    items = gold_test.questions()
    assert len(items) >= 150 and len({i["id"] for i in items}) == len(items)
    for i in items:
        assert i["q"] and i["expected"] and bool(i["quote"]) != (i["group"] in ("gap", "invented")), i["id"]
    assert gold_test._exact_paired(0, 0) == 1.0
    assert round(gold_test._exact_paired(1, 6), 3) == 0.125
    assert gold_test._exact_paired(0, 6) < 0.05
    assert gold_test._wilson(0, 0) == (0, 0) and gold_test._wilson(80, 93) == (78, 92)


def test_garbled_fonts_and_empty_pages_are_caught_and_good_pages_pass():
    from vetra import scans

    assert scans.page_problem("") == "no text"
    assert scans.page_problem("\u0bc6\u0b9a.\u0bc6\u0bb5.\u0b8e\u00d9-06 \u0ba8\u0bbe\u00e3- \u00d9\u00e3\u00d9\u00e3 " * 4) == "garbled"
    assert scans.page_problem("(cid:12)(cid:13)(cid:14) some words here to be long enough for this page check " * 2) == "garbled"
    assert not scans.page_problem("The premium is 5% of the sum insured for commercial crops in the Rabi season.")
    assert not scans.page_problem("\u0c2a\u0c02\u0c1f \u0c28\u0c37\u0c4d\u0c1f\u0c02 \u0c15\u0c28\u0c40\u0c38\u0c02 33 \u0c36\u0c3e\u0c24\u0c02 " * 3)
    assert not scans.page_problem("Caf\u00e9 is one accented word in a long English sentence about crop loans and insurance today.")


def test_a_figure_two_reads_disagree_on_becomes_unclear():
    from vetra import scans

    text, unclear = scans.agree("Pay Rs.6,000 by 31.12.2026 in 3 parts", "Pay Rs.6000 by 31/12/2026 in 3 parts")
    assert text == "Pay Rs.6,000 by 31.12.2026 in 3 parts" and unclear == 0
    text, unclear = scans.agree("Pay Rs.60001 by 31.12.2026", "Pay Rs.6000 by 31.12.2026")
    assert text == "Pay Rs.[unclear figure] by 31.12.2026" and unclear == 1


def test_a_scan_is_labelled_and_its_unclear_figures_cant_be_repeated():
    e = Evidence("a", "text_search", "Pay [unclear figure] now.", "doc", scanned=True)
    assert "read from a scan" in agent.evidence_block([e])
    assert any("couldn't confirm" in f.why for f in checks.faults("Pay [unclear figure] now [E1].", [e], TODAY))


def test_summaries_come_last_and_are_named_when_nothing_else_is_held():
    summary = Evidence("a", "text_search", "x", "PRS", kind=knowledge.KINDS["analysis"])
    order_ = Evidence("b", "text_search", "y", "G.O.", kind=knowledge.KINDS["go"])
    assert checks.order([summary, order_]) == [order_, summary]
    assert not checks.only_summaries([summary, order_]) and checks.only_summaries([summary]) and not checks.only_summaries([])


def test_scan_figures_end_up_in_digits_the_checks_can_read():
    from vetra import scans

    text, unclear = scans.agree("२०२० रु.", "2020 रु.")
    assert text.startswith("2020") and unclear == 0


def test_tamil_nadu_stamp_rates_come_from_the_exact_records_and_stay_on_topic():
    kb = knowledge.Knowledge()
    from vetra.tools import TOOLS
    ctx = lambda q: Context("finance", "TN", TODAY, kb, question=q)
    found = TOOLS["number_lookup"]("stamp duty registration fee sale deed Tamil Nadu", ctx("what is the stamp duty on a sale deed"))
    assert found and any("Sale: stamp duty 7% of market value; registration fee 2% of market value" in e.text for e in found)
    assert not TOOLS["number_lookup"]("budget fiscal deficit Tamil Nadu registration", ctx("what is the fiscal deficit in the budget"))
    assert all(not knowledge.problems(r) for r in kb.records[("finance", "numbers")])


def test_a_groq_model_is_the_backup_when_the_main_service_is_out():
    class Service:
        def __init__(self, fails=False):
            self.fails, self.asked = fails, []

        def complete(self, model, messages, json_mode=False):
            self.asked.append(model)
            if self.fails:
                raise llm.RateLimited(model)
            return llm.Reply("ok", model, 1)

    main, groq = Service(fails=True), Service()
    models = llm.Models(llm.Backup(main, groq), {"plan": ("gemini", "groq:gpt-oss")})
    meter = llm.Meter()
    reply = models.call("plan", [], meter)
    assert reply.model == "groq:gpt-oss" and groq.asked == ["gpt-oss"] and main.asked == ["gemini"] and meter.calls == 1


def test_without_a_groq_key_no_backup_is_tried(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("LLM_MODEL_PLAN", "gemini,groq:gpt-oss")
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: None)
    assert llm.from_env().roles["plan"] == ("gemini",)


def test_exact_rates_are_printed_when_no_model_can_write():
    rate = Evidence("a", "number_lookup", "Tamil Nadu. Input subsidy: Rs.8,500 per hectare.", "G.O. 579")
    text = agent.facts_only([rate], "english", "busy")
    assert "Rs.8,500 per hectare" in text and "[E1]" in text and "busy" not in text.lower()
    assert "busy" in agent.facts_only([Evidence("b", "text_search", "words", "doc")], "english", "busy").lower()


def test_made_up_worked_example_is_refused():
    items = [Evidence("a", "t", "Prevented sowing pays 25% of the sum insured. Distress relief is Rs.20,000.", "G.O.")]
    bad = "For example, on a sum insured of Rs.20,000 per hectare, the benefit is 25% [E1]."
    assert any("worked example" in f.why for f in checks.faults(bad, items, TODAY))
    assert not checks.faults("Prevented sowing pays 25% of the sum insured [E1].", items, TODAY)
    shown = [Evidence("a", "t", "Example: on a sum insured of Rs.20,000 the benefit is 25%.", "G.O.")]
    assert not checks.faults(bad, shown, TODAY)
