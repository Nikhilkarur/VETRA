"""
Readers for each store. All read-only: no tool can file, send, pay or change anything.

Each takes a query and the question's context, and returns Evidence. Which tool runs is
decided by the data type a question needs (datatypes.py), never by the model directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from . import facts as F
from . import rules, text_index
from .knowledge import KINDS, Knowledge


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
    fact: str = ""            # written by code and printed as is; the model never sees it
    note: str = ""            # what the model sees instead of an exact record's figures
    detail: str = ""          # a plain line printed with the fact when no model explains it
    in_language: bool = True  # the fact is in the reply language
    kind: str = ""            # what kind of source: an Act, a government order, a press explainer
    relation: str = ""        # why it was added: "amends G.O.Ms.No.80"
    history: bool = False     # read for how a rule changed, so its past seasons stay in


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
    question: str = ""        # the user's words, for matching a crop or a scheme by code
    language: str = "english" # what exact facts are printed in, where the data allows it
    missing: list[str] = field(default_factory=list)  # facts a rule needs, for the agent to ask
    k: int = 10               # passages per search
    rerank: bool = True       # slow on a CPU; a question's parts are searched without it


def _from_record(r: dict, tool: str, text: str | None = None) -> Evidence:
    s = r.get("source") or {}
    return Evidence(key=r["id"], tool=tool, text=text or r["text"], doc=s.get("doc", ""),
                    jurisdiction=r["jurisdiction"], url=s.get("url"), date=s.get("date"),
                    status=r.get("status", "unknown"), valid_from=r.get("valid_from"),
                    valid_until=r.get("valid_until"), season=r.get("season", ""),
                    reviewed=bool(r.get("reviewed")), kind=KINDS.get(r.get("legal_weight"), ""))


def _from_chunks(hits: list[dict], ctx: Context) -> list[Evidence]:
    status = {"yes": "in_force", "no": "not_in_force"}
    return [Evidence(key=h["id"], tool="text_search", text=h["text"], doc=h.get("source", ""),
                     url=h.get("source_url"), jurisdiction=h.get("jurisdiction", ""), date=h.get("date") or None,
                     status=status.get(h.get("in_force"), "unknown"), season=h.get("season") or "",
                     kind=ctx.knowledge.kind_of(ctx.domain, h.get("title", "")), relation=h.get("added_because", ""))
            for h in hits]


def text_search(query: str, ctx: Context) -> list[Evidence]:
    return _from_chunks(text_index.search(query, ctx.domain, ctx.state, ctx.passage, ctx.topic, ctx.keywords, ctx.k, ctx.rerank), ctx)


def read_around(chunk_id: str, ctx: Context) -> list[Evidence]:
    """More of a document already found: the passages either side of this one."""
    return _from_chunks(text_index.around(chunk_id, ctx.domain), ctx)


def look_inside(document: str, query: str, ctx: Context) -> list[Evidence]:
    """The passages of one document that best match a query: its annexure, or a clause it refers to."""
    return _from_chunks(text_index.search_within(query, ctx.domain, ctx.state, document), ctx)


def rule_check(query: str, ctx: Context) -> list[Evidence]:
    found = ctx.knowledge.find(ctx.domain, "rules", ctx.state, query, top=4)
    by_body: dict[str, list[dict]] = {}
    for r in F.names_scheme(found, ctx.question.lower()):
        result = rules.evaluate(r, {**ctx.facts, **rules.facts_in_words(r, ctx.question)})
        crop = rules.not_notified(r, ctx.facts, ctx.question)
        if crop:
            body = F.not_notified_fact(r, crop, ctx.language)
        elif result.outcome is not None:
            body = F.decided_fact(r, result.outcome, ctx.language)
        else:
            names = r.get(f"ask_as_{ctx.language}") or r.get("ask_as") or {}
            asked_as = [names.get(m, m) for m in result.missing]
            ctx.missing += [m for m in asked_as if m not in ctx.missing]
            body = F.all_cases_fact(r, ctx.language)
        by_body.setdefault(body, []).append(r)
    out = []
    for body, same in by_body.items():  # schemes with the same rates share one line
        names = " and ".join(r.get("name", "") for r in same if r.get("name"))
        fact = f"{names}: {body}" if names else body
        fact += "" if fact.endswith(".") else "."
        e = _from_record(same[0], "rule_check", fact)
        e.fact, e.note = fact, " ".join(r.get("note") or r["text"] for r in same)
        e.doc = "; ".join((r.get("source") or {}).get("doc", "") for r in same)
        e.detail = same[0].get(f"detail_{ctx.language}") or same[0].get("detail") or ""
        e.in_language = all(F.speaks(r, ctx.language) for r in same)
        out.append(e)
    return out


def dates_lookup(query: str, ctx: Context) -> list[Evidence]:
    found = ctx.knowledge.find(ctx.domain, "dates", ctx.state, query, top=12)
    words = f"{ctx.question} {' '.join(str(v) for v in ctx.facts.values())}"
    out = [_from_record(r, "dates_lookup") for r in found if not F.is_window(r)]
    for w in F.windows_for([r for r in found if F.is_window(r)], words, ctx.as_of):
        fact = F.window_fact(w, ctx.as_of, ctx.language)
        e = _from_record(w, "dates_lookup", fact)
        e.fact, e.note = fact, F.window_note(w, ctx.as_of)
        out.insert(0, e)
    return out


def _lookup(store: str, tool: str) -> Callable[[str, Context], list[Evidence]]:
    def run(query: str, ctx: Context) -> list[Evidence]:
        return [_from_record(r, tool) for r in ctx.knowledge.find(ctx.domain, store, ctx.state, query)]
    return run


TOOLS = {
    "text_search": text_search,
    "read_around": read_around,
    "look_inside": look_inside,
    "rule_check": rule_check,
    "dates_lookup": dates_lookup,
    "number_lookup": _lookup("numbers", "number_lookup"),
    "directory_lookup": _lookup("directory", "directory_lookup"),
    "links_walk": _lookup("links", "links_walk"),
    "form_search": _lookup("forms", "form_search"),
}
