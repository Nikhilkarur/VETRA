"""The agent's mechanics, with a fake model and fake data: no network, no API key."""

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vetra import agent, checks, facts, intake, jurisdictions, knowledge, llm, rules, sorter, text_index, web  # noqa: E402
from vetra import gaps as gaps_module  # noqa: E402
from vetra.datatypes import DATA_TYPES  # noqa: E402
from vetra.domains import DOMAINS  # noqa: E402
from vetra.tools import Evidence  # noqa: E402

TODAY = "2026-11-04"


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
    monkeypatch.setitem(agent.TOOLS, "text_search", lambda query, ctx: [])
    monkeypatch.setattr(agent, "GapLog", Gaps)


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


def test_telugu_still_goes_to_the_model_for_exact_facts(kb):
    r, _ = run(kb, plan(language="telugu"), "తెలుగు వివరణ.")
    assert r.trace["calls"] == 2 and "తెలుగు వివరణ" in r.answer and "15 December 2026" in r.answer


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
    r, _ = run(kb, plan(), "వివరణ.", reply="telugu")
    assert r.language == "telugu" and r.trace["calls"] == 2


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
