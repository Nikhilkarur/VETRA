"""
How far an answer goes.

The planner picks a level from the question, and everything that differs between levels is in
this table. A reader's own preference can override it later: agent.answer(depth="deep").
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_PARTS = 8       # what one question can be split into; each part costs a search
_MANY_PARTS = 4     # too many to fit a short answer, whatever the planner called it

_RESEARCH = """Write a short research brief, for a reader who wants to understand this properly.
1. Start with the direct answer, in one to three sentences, with no heading.
2. Then a short section for each part below that the evidence covers, under a heading like "## Who qualifies". Give the rule and also its conditions, limits and exceptions: who it doesn't apply to, what happens if a step is missed, and what differs by season, crop or state. Keep the evidence's own numbers and wording of conditions. Don't repeat the printed records: say what they mean and what limits them. Within each section, say whether the rule is central or the state's own, and which season or period it applies to.
3. If the rule changed over time, add "## What changed": what it was, what changed it and from when, oldest first, naming each order.
4. Only if two current sources give different answers on the same point, add "## Where the sources differ": give each with its citation and date, then say which applies. A later order replaces an earlier one of the same weight. An Act outranks rules, rules outrank orders, orders outrank guidelines, and guidelines outrank circulars. If you can't tell which applies, say so. Never choose silently. Old rules that were replaced belong under "What changed", not here.
5. Rely on press explainers, manuals and budget speeches only where nothing binding covers the point, and say so.
6. If no document here answers something this question needs, end with "## What the documents don't settle". Never list something the printed records already give.
Leave out any section you have nothing for. Don't pad."""


@dataclass(frozen=True)
class Depth:
    name: str
    means: str              # for the planner
    passages: int           # per search
    each_part: bool         # search each part on its own, and read text alongside exact records
    evidence: int           # most records the answer model is given
    rounds: int             # how many times navigation may judge and look further
    moves: int              # how far it may look in one round
    calls: int              # LLM calls the whole question may use
    answer_calls: int       # of those, kept back for writing and checking the answer
    print_alone: bool       # exact records that answer everything are printed with no model
    verify: bool            # a second model checks each statement against what it cites
    shape: str              # how the answer is written


QUICK = Depth(
    "quick", '''one specific fact: a date, an amount, yes or no. "last date to insure my cashew", "is onion covered under PMFBY"''',
    passages=6, each_part=False, evidence=10, rounds=1, moves=1, calls=5, answer_calls=3, print_alone=True, verify=False,
    shape="Answer in one or two sentences. Add a condition only if the answer would mislead without it.")

STANDARD = Depth(
    "standard", '''how to do something, or what to do in a situation. "how do I get a kisan credit card", "the dealer sold me fake seeds, what can I do"''',
    passages=10, each_part=False, evidence=18, rounds=2, moves=2, calls=6, answer_calls=3, print_alone=True, verify=False,
    shape="Answer the question first, in one or two sentences. Then give what the person needs to act on it: the steps, "
          "conditions, limits and exceptions that could affect them. Use a short list where it helps. Leave out what "
          "doesn't bear on the question.")

DEEP = Depth(
    "deep", '''understanding a whole scheme, rule or law; comparing; how something changed; why; several linked questions; or asking for detail. "what is PM-KISAN and who gets it", "compare PMFBY and RWBCIS", "explain crop insurance in detail"''',
    passages=6, each_part=True, evidence=36, rounds=3, moves=3, calls=10, answer_calls=5, print_alone=False, verify=True,
    shape=_RESEARCH)

LEVELS = {d.name: d for d in (QUICK, STANDARD, DEEP)}


def choose(named: str | None, needs: list[str], override: str | None = None) -> Depth:
    """
    The level for this question, from the planner's word and the types of data it found the question
    needs. Standard if its word can't be read. The model isn't steady on this, so what it asked for
    decides when the two disagree: explaining something in several parts can't fit a short answer.
    """
    if override in LEVELS:
        return LEVELS[override]
    if len(needs) >= _MANY_PARTS or ("explanation" in needs and len(needs) >= _MANY_PARTS - 1):
        return DEEP
    return LEVELS.get(named or "", STANDARD)
