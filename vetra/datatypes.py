"""
The types of data a question can need, and where each type lives.

The planner names the types a question needs; it doesn't pick tools or stores. Code then
reads the matching store. A new type of data is one entry here plus its reader in tools.py.

"exact" lists what answers the type precisely. Text search is the fallback for every type:
an answer found only in text still reaches the user, but it's recorded as a gap, because
the fact should be sorted into its exact store.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DataType:
    name: str
    means: str                       # for the planner
    exact: tuple[str, ...] = ()      # tools reading exact stores; empty: text is the right place


DATA_TYPES = {t.name: t for t in (
    DataType("eligibility", "whether someone qualifies for a scheme or benefit", ("rule_check",)),
    DataType("amount", "how much must be paid or will be received: premiums, subsidies, rates, fees", ("rule_check", "number_lookup")),
    DataType("deadline", "last dates, cut-offs, enrolment windows, what is open now", ("dates_lookup",)),
    DataType("procedure", "how to apply or do something, step by step, and what documents it takes"),
    DataType("explanation", "what a scheme, rule, law or term means, and what it covers"),
    DataType("contact", "which officer, office or helpline to go to", ("directory_lookup",)),
    DataType("form", "an application form or annexure", ("form_search",)),
    DataType("change_history", "what amended, extended, replaced or renamed an order or scheme", ("links_walk",)),
    DataType("statistic", "budget figures, allocations, targets and statistics", ("number_lookup",)),
)}
