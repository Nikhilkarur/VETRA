"""The agent's mechanics, with a fake model and fake data: no network, no API key."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from vetra import agent, checks, jurisdictions, knowledge, llm, rules, sorter, text_search  # noqa: E402
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
                       "standalone": "Do I pay?", "steps": [{"tool": "dates_lookup", "args": {"query": "cut-off rabi"}}],
                       **more})


RULE = {"id": "r1", "store": "rules", "domain": "agriculture", "jurisdiction": "AP", "text": "Premium rule scheme",
        "source": {"doc": "G.O.1"}, "cases": [
            {"when": {"crop": "commercial"}, "outcome": {"percent": 5}},
            {"when": {"crop": "food", "income": {"max": 100}}, "outcome": {"percent": 2}}]}
DATE = {"id": "d1", "store": "dates", "domain": "agriculture", "jurisdiction": "AP", "text": "Rabi cut-off rabi is 15 December 2026.",
        "source": {"doc": "G.O.2"}, "status": "in_force"}
OTHER_STATE = {**DATE, "id": "d2", "jurisdiction": "KA", "text": "Karnataka cut-off rabi is 1 January 2027."}
CENTRAL = {**DATE, "id": "d3", "jurisdiction": "IN", "text": "Central cut-off rabi note."}


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


def test_manifest_gives_dates_and_links():
    rows = sorter.from_manifest([{"title": "G.O.34", "file": "go34.pdf", "department": "Agri", "date": "2026-07-06",
                                  "in_force": "yes", "amends": ["G.O.80"], "doc_type": "go"}], "agriculture", "AP")
    assert {r["store"] for r in rows} == {"dates", "links"} and all(not knowledge.problems(r) for r in rows)


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


def test_expired_records_go_unless_the_question_asks_about_that_year():
    old = Evidence("a", "t", "old", "G.O.", valid_until="2025-03-31")
    assert checks.in_force([old], TODAY, "is it free now") == []
    assert checks.in_force([old], TODAY, "was it free in 2025") == [old]


def test_past_season_rule_is_cut_from_text():
    e = Evidence("a", "t", "The State Govt will bear the premium. Rabi 2024-25 onwards: i. Farmers pay.", "G.O.", season="Kharif 2024")
    kept = checks.in_force([e], TODAY, "do i pay")[0]
    assert "will bear" not in kept.text and "Farmers pay" in kept.text


# ---------------------------------------------------------------- the workflow

def test_answers_from_exact_store_with_citations_by_code(kb):
    m = models(plan(), "Rabi closes 15 December 2026 [E1].")
    r = agent.answer("rabi cut-off?", models=m, knowledge=kb, as_of=TODAY)
    assert r.kind == "answer" and r.sources[0]["doc"] == "G.O.2"
    assert r.trace["calls"] == 2 and r.trace["plan"] == ["dates_lookup"]


def test_rule_is_consulted_even_if_the_plan_forgot_it_and_all_cases_are_shown(kb):
    m = models(plan(standalone="premium rule scheme"), "Commercial crops pay 5 percent [E1].")
    r = agent.answer("premium rule scheme?", models=m, knowledge=kb, as_of=TODAY)
    assert r.sources[0]["tool"] == "rule_check" and r.trace["missing"] == []
    assert "All cases" in json.dumps(m.provider.sent[1][1])


def test_a_rule_the_plan_chose_asks_for_its_missing_facts(kb):
    m = models(plan(steps=[{"tool": "rule_check", "args": {"query": "premium rule scheme"}}]), "Commercial pays 5 percent [E1].")
    r = agent.answer("premium rule scheme?", models=m, knowledge=kb, as_of=TODAY)
    assert r.trace["missing"] and "Not known yet" in json.dumps(m.provider.sent[1][1])


def test_facts_decide_the_rule(kb):
    m = models(plan(standalone="premium rule scheme", facts={"crop": "commercial"}), "You pay 5 percent [E1].")
    agent.answer("premium rule scheme?", models=m, knowledge=kb, as_of=TODAY)
    assert "percent = 5" in json.dumps(m.provider.sent[1][1])


def test_rule_inputs_reach_the_planner(tmp_path):
    sorter.file_records([{**RULE, "inputs": {"crop": ["food", "commercial"]}}], tmp_path)
    m = models(json.dumps({"domain": "other"}))
    agent.answer("premium rule scheme?", models=m, knowledge=knowledge.Knowledge(tmp_path), as_of=TODAY)
    assert "commercial" in json.dumps(m.provider.sent[0][1])


def test_any_citation_style_is_understood():
    for raw in ("x 【E2†L1-L4】", "x [2]", "x [E2]", "x (E2)", "x [E2, E3]"):
        assert "[E2]" in checks.tidy_citations(raw)


def test_vendor_format_failure_moves_to_the_next_model(kb):
    m = models(llm.BadOutput("p1"), plan(), "Closes 15 December 2026 [E1].")
    assert agent.answer("rabi cut-off?", models=m, knowledge=kb, as_of=TODAY).kind == "answer"


def test_plan_is_made_without_any_document_text(kb):
    m = models(plan(), "Closes 15 December 2026 [E1].")
    agent.answer("rabi cut-off?", models=m, knowledge=kb, as_of=TODAY)
    planner_sent = json.dumps(m.provider.sent[0][1])
    assert DATE["text"] not in planner_sent


def test_document_text_cannot_add_tools():
    p = agent.parse_plan(plan(steps=[{"tool": "send_money", "args": {}}, {"tool": "form_search", "args": {}}]))
    assert [s.tool for s in p.steps] == ["form_search"]


def test_asks_for_the_state_rather_than_guessing(kb):
    r = agent.answer("rabi cut-off?", models=models(plan(state=None)), knowledge=kb, as_of=TODAY)
    assert r.kind == "ask" and "state" in r.answer


def test_state_with_no_data_says_so_honestly(kb):
    r = agent.answer("what is rabi?", models=models(plan(state="Goa", steps=[{"tool": "text_search", "args": {"query": "x"}}])),
                     knowledge=knowledge.Knowledge(Path("no-such")), as_of=TODAY)
    assert r.kind == "not_covered" and "Goa" in r.answer


def test_failed_check_regenerates_then_falls_back_to_the_facts(kb):
    m = models(plan(), "You pay 9% [E1].", "Still 9% [E1].")
    r = agent.answer("rabi cut-off?", models=m, knowledge=kb, as_of=TODAY)
    assert "9%" not in r.answer and "15 December 2026" in r.answer and r.trace["calls"] == 3


def test_rate_limit_moves_to_the_next_model(kb):
    m = models(llm.RateLimited("p1"), plan(), "Closes 15 December 2026 [E1].")
    assert agent.answer("rabi cut-off?", models=m, knowledge=kb, as_of=TODAY).kind == "answer"
    assert "p1" in m.resting


def test_compose_failure_still_gives_facts(kb):
    m = models(plan(), llm.LLMError("down"))
    r = agent.answer("rabi cut-off?", models=m, knowledge=kb, as_of=TODAY)
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
    r = agent.answer("rti fee", models=models(json.dumps({"domain": "rti", "steps": []})), knowledge=kb, as_of=TODAY)
    assert r.kind == "legacy" and called["q"] == "rti fee"


def test_off_topic_is_declined_with_one_call(kb):
    r = agent.answer("passport?", models=models(json.dumps({"domain": "other"})), knowledge=kb, as_of=TODAY)
    assert r.kind == "decline" and r.trace["calls"] == 1


def test_id_numbers_never_reach_the_model(kb):
    m = models(json.dumps({"domain": "other"}))
    agent.answer("my aadhaar 1234 5678 9012 is it ok", models=m, knowledge=kb, as_of=TODAY)
    assert "5678" not in json.dumps(m.provider.sent[0][1])


# ---------------------------------------------------------------- modular by design

def test_every_state_and_ut_is_known():
    assert len(jurisdictions.STATES) == 36
    assert jurisdictions.normalise("tamil nadu") == "TN" and jurisdictions.normalise("Nowhere") is None


def test_finance_and_agriculture_are_live_domains_and_rti_is_frozen():
    assert not DOMAINS["finance"].legacy and not DOMAINS["agriculture"].legacy and DOMAINS["rti"].legacy


def test_search_needs_no_llm_vendor():
    assert "groq" not in Path(text_search.__file__).read_text(encoding="utf-8").lower()
    assert "groq" not in Path(agent.__file__).read_text(encoding="utf-8").lower()
