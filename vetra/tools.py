"""
The agent's tools. All read-only: no tool can file, send, pay or change anything.

Each tool takes the planner's arguments and returns Evidence. Adding one is a function and
a line in TOOLS; a domain chooses which it allows in domains.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from . import rules, text_search
from .knowledge import Knowledge


@dataclass
class Evidence:
    """One fact the answer may use. The model only ever sees these."""
    key: str                  # the record's id
    tool: str
    text: str
    doc: str                  # document name, for the citation code writes
    jurisdiction: str = ""
    url: str | None = None
    date: str | None = None
    status: str = "unknown"   # in_force, not_in_force, unknown
    valid_from: str | None = None
    valid_until: str | None = None
    season: str = ""          # the one-season rule list this text opens in, if any
    reviewed: bool = False


@dataclass
class Context:
    domain: str
    state: str | None
    as_of: str                # ISO date the question is about
    knowledge: Knowledge
    facts: dict = field(default_factory=dict)      # what the user has told us
    passage: str = ""         # the planner's search aids
    topic: str = ""
    keywords: tuple[str, ...] = ()
    missing: list[str] = field(default_factory=list)  # facts a rule needs, for the agent to ask


def _from_record(r: dict, tool: str, text: str | None = None) -> Evidence:
    s = r.get("source") or {}
    return Evidence(key=r["id"], tool=tool, text=text or r["text"], doc=s.get("doc", ""),
                    jurisdiction=r["jurisdiction"], url=s.get("url"), date=s.get("date"),
                    status=r.get("status", "unknown"), valid_from=r.get("valid_from"),
                    valid_until=r.get("valid_until"), season=r.get("season", ""),
                    reviewed=bool(r.get("reviewed")))


def text_search_tool(args: dict, ctx: Context) -> list[Evidence]:
    query = str(args.get("query") or "")
    hits = text_search.search(query, ctx.domain, ctx.state, ctx.passage, ctx.topic, ctx.keywords)
    status = {"yes": "in_force", "no": "not_in_force"}
    return [Evidence(key=h.get("id") or f"{h.get('file')}#{h.get('chunk_index')}", tool="text_search",
                     text=h["text"], doc=h.get("source", ""), url=h.get("source_url"),
                     jurisdiction=ctx.state or "", date=h.get("date") or None,
                     status=status.get(h.get("in_force"), "unknown"), season=h.get("season") or "")
            for h in hits]


def _pairs(values: dict) -> str:
    return ", ".join(f"{k.replace('_', ' ')} = {str(v).replace('_', ' ')}" for k, v in values.items())


def rule_check(args: dict, ctx: Context) -> list[Evidence]:
    query = str(args.get("query") or args.get("scheme") or "")
    facts = {**ctx.facts, **(args.get("facts") or {})}
    out = []
    for r in ctx.knowledge.find(ctx.domain, "rules", ctx.state, query, top=2):
        result = rules.evaluate(r, facts)
        if result.outcome is not None:
            out.append(_from_record(r, "rule_check", f"{r['text']} Decided for this user: {_pairs(result.outcome)}."))
        else:
            ctx.missing += [m for m in result.missing if m not in ctx.missing]
            cases = "; ".join(f"if {_pairs(c['when'])}: {_pairs(c['outcome'])}" for c in r["cases"])
            out.append(_from_record(r, "rule_check", f"{r['text']} All cases: {cases}."))
    return out


def _lookup(store: str, tool: str) -> Callable[[dict, Context], list[Evidence]]:
    def run(args: dict, ctx: Context) -> list[Evidence]:
        query = str(args.get("query") or args.get("subject") or "")
        return [_from_record(r, tool) for r in ctx.knowledge.find(ctx.domain, store, ctx.state, query)]
    return run


TOOLS = {
    "text_search": text_search_tool,
    "rule_check": rule_check,
    "dates_lookup": _lookup("dates", "dates_lookup"),
    "number_lookup": _lookup("numbers", "number_lookup"),
    "directory_lookup": _lookup("directory", "directory_lookup"),
    "links_walk": _lookup("links", "links_walk"),
    "form_search": _lookup("forms", "form_search"),
}

DESCRIPTIONS = {
    "text_search": "Search the official documents' text. For explanations and procedures. Args: query.",
    "rule_check": "Decide eligibility or an amount under a scheme's rule. Args: query (the scheme), facts (what the user said).",
    "dates_lookup": "Exact deadlines, cut-offs, and when an order was issued or is valid. Args: query.",
    "number_lookup": "Exact budget figures, allocations and statistics. Args: query.",
    "directory_lookup": "Officers, offices and helplines. Args: query (include department and district).",
    "links_walk": "What amended, extended, replaced or renamed an order or scheme. Args: query.",
    "form_search": "Application forms and annexures. Args: query.",
}
