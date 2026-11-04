"""
The topics the agent covers. Adding one is an entry here plus its data under knowledge/.

Subtopics tell the planner what the topic covers, and later let each subtopic have its own
question sets. Nothing else in the agent names a topic, apart from "legacy" below.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Domain:
    name: str
    label: str
    hint: str                       # what it covers, for the planner
    subtopics: tuple[str, ...] = ()
    legacy: bool = False            # answered by rag/ unchanged, not by this agent
    # Text search settings, measured per topic (docs/RETRIEVAL_EXPERIMENTS.md).
    text_files: tuple[tuple[str, str], ...] = ()  # (chunk file, the state it came from)
    embed_title: bool = False
    rerank: str = ""                # cross-encoder over the top results; "" for none
    abbreviations_from: str = ""    # rag/ domain whose glossary expands the query


DOMAINS = {
    "finance": Domain(
        name="finance",
        label="Finance",
        hint="Money between citizens and government: taxes, duties, pensions, payments and budgets.",
        subtopics=("pensions and social security", "stamp duty and registration", "vehicle tax",
                   "professional tax", "property and land tax", "GST and income tax for citizens",
                   "government loans and interest subsidies", "welfare payments and DBT status",
                   "state and union budgets, allocations and spending"),
        embed_title=True,
        rerank="cross-encoder/ms-marco-MiniLM-L-6-v2",
    ),
    "agriculture": Domain(
        name="agriculture",
        label="Agriculture",
        hint="Farming: schemes, money and rules for farmers, including tenants and share-croppers.",
        subtopics=("farmer income support", "crop insurance", "crop loans and Kisan Credit Cards",
                   "subsidies for seeds, irrigation, machinery and horticulture",
                   "minimum support prices and procurement", "disaster and crop-loss relief",
                   "seed, fertiliser and pesticide law", "tenant farmers' rights",
                   "farmer pensions", "farm power", "offices and officers"),
        text_files=(("ingest/chunks_agriculture.json", "AP"),),
        embed_title=True,
        rerank="cross-encoder/ms-marco-MiniLM-L-6-v2",
        abbreviations_from="agriculture",
    ),
    "rti": Domain(
        name="rti",
        label="RTI",
        hint="Using the Right to Information Act to get records from a public body: fees, "
             "time limits, refusals and appeals.",
        legacy=True,
    ),
}
