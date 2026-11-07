"""
How an answer is built: the foundation for MVP step 4 (answer structure and quality).

Three things live here, so structure is decided in one place instead of scattered through prompts:

1. RULES, the writing rules every answer follows, whatever its depth. The first is how to say a
   thing isn't held: "the documents I have don't mention it", never "it doesn't exist". A live
   answer (7 Nov 2026) told a farmer "no subsidy is provided" for silkworm sheds when VETRA simply
   held nothing on it.
2. denials(), a code check: a sentence that says something doesn't exist or isn't given must be
   backed by a cited passage that itself says so. Otherwise the writer is sent back to fix it.
3. report(), what an answer's structure looks like (opening, sections, length), recorded in the
   trace of every answer, so structure can be measured across a question set before it is changed.

4. CASES, the kinds of question people ask (a comparison, can I get it, how much, by when, how to
   apply, what changed, a complaint, ...), each with its own answer shape, the way the aspect lists
   say what the data must cover. choose() picks the case from the question's words and the plan's
   data types; shape() gives the writer that case's structure for the answer's depth.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# The parts an answer at each depth is built from, in order. Optional parts are left out when
# there is nothing for them; a deep brief's sections come from depth.DEEP's shape.
SKELETON = {
    "quick": ("direct answer", "one condition, if leaving it out would mislead"),
    "standard": ("direct answer", "what it gives or requires", "who it applies to and who it doesn't",
                 "how to do it", "what the documents don't cover"),
    "deep": ("direct answer", "a section per part of the question", "what changed", "where the sources differ",
             "what the documents don't settle"),
}

RULES = """How to write it:
- When the documents don't cover something, say "the documents I have don't mention ..." or "this isn't covered in the documents I have". Never say it doesn't exist, isn't provided or isn't available unless a document says exactly that, and cite it.
- Put what the person can act on first: the amount, the deadline, the place to apply. Background comes after, if at all.
- One idea per sentence. Short paragraphs; a list only for steps or several separate items.
- Name the scheme, the state and the period the rule applies to, so nobody mistakes a central rule for a state one or an old rule for today's."""

# "There is no subsidy", "is not provided", "does not exist", "no such scheme": a claim that
# something is absent from the world, not from our documents.
_DENIAL = re.compile(
    r"\b(?:there (?:is|are) no|no such|does(?:n't| not) exist|do(?:n't| not) exist|is not (?:provided|available|offered|given)"
    r"|are not (?:provided|available|offered|given)|no (?:\w+ ){0,2}(?:subsidy|scheme|assistance|benefit|support|incentive|grant|loan)s? (?:is|are) (?:provided|available|given|offered))\b",
    re.I)
# Saying it about our documents is honest, and is what RULES asks for.
_ABOUT_DOCUMENTS = re.compile(r"\b(?:document|documents|records|sources|information) (?:I|we) (?:have|hold)|\bin the documents\b"
                              r"|\b(?:documents|records) (?:held|available to me)|\bnot (?:mentioned|covered|specified|listed|stated) in\b", re.I)


def denials(sentences: list[tuple[str, list[str]]]) -> list[str]:
    """
    Sentences that say something doesn't exist without a cited passage saying so.
    Each sentence comes with the texts of the passages it cites.
    """
    bad = []
    for text, cited in sentences:
        if not _DENIAL.search(text) or _ABOUT_DOCUMENTS.search(text):
            continue
        if any(_DENIAL.search(passage) for passage in cited):   # the document itself says there is none
            continue
        bad.append(text)
    return bad


_HEADING = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$", re.M)
_TABLE_GAP = re.compile(r"(^\|[^\n]*\|[ \t]*)\n(?:[ \t]*\n)+(?=\|)", re.M)


def tidy_tables(text: str) -> str:
    """Blank lines between table rows split one table in two on the page; a writer leaves them in."""
    while True:
        tidied = _TABLE_GAP.sub(r"\1\n", text)
        if tidied == text:
            return text
        text = tidied


def report(text: str, depth: str, printed_heading: str = "") -> dict:
    """
    The answer's structure, for the trace: how it opens, its sections, its length, whether it has a
    table. The records block code prints first (under printed_heading) isn't the writer's, so it's skipped.
    """
    if printed_heading and text.lstrip().startswith(printed_heading):
        rest = text.lstrip()[len(printed_heading):].lstrip("\n")
        blocks = rest.split("\n\n", 1)   # the printed list, then the writer's answer
        text = blocks[1] if len(blocks) > 1 else rest
    lines = [l for l in text.strip().splitlines() if l.strip()]
    first = lines[0] if lines else ""
    return {
        "depth": depth,
        "opens_with_answer": bool(first) and not first.lstrip().startswith(("#", "-", "*")),
        "sections": _HEADING.findall(text),
        "words": len(text.split()),
        "list_items": sum(1 for l in lines if l.lstrip().startswith(("- ", "* ", "• "))),
        "has_table": sum(1 for l in lines if l.strip().startswith("|") and l.strip().endswith("|")) >= 3,
        "expected": list(SKELETON.get(depth, ())),
    }


# ---------------------------------------------------------------- question cases

@dataclass(frozen=True)
class Case:
    name: str
    asks: str             # what the person wants, in plain words (shown on the station page)
    words: str            # regex on the question: words that mark this case, in English, Telugu and Tamil
    types: tuple = ()     # planner data types that point to it when the words don't
    quick: str = ""       # how a one-or-two-sentence answer opens
    standard: str = ""    # the structure of a standard answer
    deep: str = ""        # what a research brief leads with or adds for this case


CASES = (
    Case("comparison", "the difference between two or more schemes, rules, states or periods",
         r"\b(?:differen\w*|compar\w*|vs\.?|versus|better|which (?:one|is better|scheme))\b|తేడా|పోలిక|வித்தியாசம்|ஒப்பிட",
         quick="Say in one sentence how they differ on the point asked.",
         standard="""Structure for a comparison:
1. One or two sentences: the main difference, and which fits whom.
2. A table with one column per scheme (or state, or period) and a row for each point the documents cover: who it is for, what it gives (amounts), conditions and exclusions, how to apply, deadlines, who runs it (central or state). Cite each cell. Write "not in the documents" in a cell they don't cover, so it never reads as if nothing exists.
3. Two to four bullets on the differences that matter most in practice.
4. Whether a person can get both, only if the documents say.""",
         deep="Lead with the comparison table described for comparisons (one column per scheme, a row per point, each cell cited, \"not in the documents\" where they are silent), then a section per point; keep the brief's other sections."),
    Case("change", "what changed in a rule, and what applies now",
         r"\b(?:chang\w*|new rule|earlier|previous|old (?:rule|rate)|revised|amend\w*|still (?:valid|in force))\b|మార్పు|மாற்ற",
         types=("change_history",),
         quick="Give today's rule and the date it changed.",
         standard="""Structure for what changed:
1. The rule today, with the order and date that set it.
2. What it was before, and what changed it, oldest first, one line per order.
3. What this means for someone who applied or paid under the old rule, only if the documents say.""",
         deep="Put \"What changed\" right after the direct answer, as a dated timeline naming each order."),
    Case("grievance", "something went wrong: rejected, not paid, cheated, a complaint",
         r"\b(?:complain\w*|grievance|rejected|denied|not (?:received|paid|credited|given)|delay\w*|cheat\w*|fake|fraud|problem|refus\w*|appeal)\b|ఫిర్యాదు|புகார்",
         quick="Say the first thing to do and where.",
         standard="""Structure for a problem or complaint:
1. The first thing to do now, and where (office, helpline or portal), cited.
2. If that doesn't work: the next level to go to, and any time limit.
3. What to keep or bring: documents, numbers, receipts.
4. Their rights in this situation, only as the documents state them.""",
         deep="Start with the steps to take, in order, before explaining the rule behind them."),
    Case("status", "where an application or payment has got to",
         r"\b(?:status|track|when will i (?:get|receive)|instal+ment)\b",
         quick="Say how to check the status.",
         standard="""Structure for a status question:
1. How to check the status (portal, app, office or helpline), cited.
2. When payments are made or the stages it goes through, only as the documents say.
3. Whom to contact if it is late.""",
         deep="Keep it practical: how to check, the timeline and whom to contact come first."),
    Case("eligibility", "whether they qualify",
         r"\b(?:eligib\w*|can i|am i|can a|who can|qualif\w*|entitled|allowed)\b|అర్హత|தகுதி",
         types=("eligibility",),
         quick="Start with yes, no, or it depends on (the one condition), then the reason.",
         standard="""Structure for eligibility:
1. Yes, no, or "it depends on ...", in the first sentence.
2. The conditions, as a short list, each cited: land, income, category, age, residence, crop or season.
3. Who is left out.
4. What to apply with and where, briefly.
5. If the person's facts are needed to decide, say which facts.""",
         deep="Open the brief with the yes, no or depends answer, then a section on conditions and one on exclusions."),
    Case("deadline", "the last date or the window",
         r"\b(?:last date|deadline|due date|cut.?off|till when|by when|window|open now|closing date)\b|చివరి తేదీ|கடைசி தேதி",
         types=("deadline",),
         quick="Give the date, and say whether it is still open today.",
         standard="""Structure for a deadline:
1. The date, and whether it is open or closed today.
2. Which season, crop or group it applies to, if dates differ.
3. What happens if it is missed, only if the documents say.""",
         deep="Lead with the dates by season or group, then what happens if they are missed."),
    Case("amount", "how much: a subsidy, rate, fee, premium or payment",
         r"\b(?:how much|amount|rate|fees?|cost|charges?|premium|subsidy|price|per (?:acre|hectare|unit|month|year))\b|ఎంత|எவ்வளவு",
         types=("amount",),
         quick="Give the figure, with its unit and any upper limit.",
         standard="""Structure for an amount:
1. The figure, with its unit (per acre, per hectare, per month, percentage) and any upper limit.
2. What it depends on: crop, area, category, season; a short table if it varies.
3. When and how it is paid or charged.
4. If the person's facts decide the figure, say which facts; never work out a total.""",
         deep="Give the figures first, as a table if they vary, then the conditions that change them."),
    Case("procedure", "how to apply or do something",
         r"\b(?:how (?:to|do i|can i) (?:apply|get|register|claim|enrol\w*|change|transfer|obtain)|procedure|process|steps|where to apply|documents? (?:needed|required))\b|ఎలా|எப்படி",
         types=("procedure", "form"),
         quick="Say where to apply and the one thing to bring.",
         standard="""Structure for how to do it:
1. Where and how to apply, in one sentence.
2. Numbered steps, each cited.
3. Documents to bring, as a list.
4. Fees and time taken, if the documents give them.
5. How to follow up.""",
         deep="Put the numbered steps and documents first, then the rules behind each step."),
    Case("contact", "which office, officer or helpline",
         r"\b(?:who (?:should|do) i (?:contact|approach)|contact|helpline|phone|toll.?free|email)\b",
         types=("contact",),
         quick="Give the office or number.",
         standard="""Structure for a contact:
1. The office, officer or helpline, with the number or address, cited.
2. What they handle, and an alternative if the first doesn't help.""",
         deep="Give the contacts first, then what each handles."),
    Case("options", "what schemes or options exist for them",
         r"\b(?:what (?:are the )?schemes|which schemes|schemes (?:for|available)|any schemes?|options|what help|what benefits)\b|పథకాలు|திட்டங்கள்",
         quick="Name the main one or two schemes.",
         standard="""Structure for a list of options:
1. One sentence on how many relevant schemes the documents show.
2. A list grouped by purpose; for each: name, who it is for, what it gives, in one line, cited.
3. Suggest asking about one of them for the details.""",
         deep="Group the schemes by purpose, with a short section for each group."),
    Case("explanation", "what a scheme, rule or term is",
         r"\b(?:what is|what are|explain|meaning|tell me about|details of)\b",
         types=("explanation",),
         quick="Say what it is in one sentence.",
         standard="""Structure for an explanation:
1. What it is, in one sentence: who runs it and what it gives.
2. Who it is for, and the main conditions.
3. How to get it, briefly.
4. What the documents don't cover."""),
)
BY_NAME = {c.name: c for c in CASES}


def choose(question: str, needs: list[str]) -> Case:
    """
    The case for this question: the first in CASES whose words appear in the question, else the
    first whose data types the plan asked for, else an explanation. Order matters: "the difference
    in premium" is a comparison, and "my claim was rejected, whom do I call" is a grievance.
    """
    for case in CASES:
        if re.search(case.words, question, re.I):
            return case
    for case in CASES:
        if set(case.types) & set(needs):
            return case
    return BY_NAME["explanation"]


def shape(case: Case, depth_name: str, depth_shape: str) -> str:
    """What the writer is told about structure: this case's structure at this depth."""
    if depth_name == "quick":
        return f"{depth_shape}\n{case.quick}".strip()
    if depth_name == "deep":
        # First, and binding: placed after the brief's long layout, the writer followed the layout and
        # dropped the comparison table (live answer, 7 Nov).
        return (f"This is a {case.name} question. Before anything else, follow this, and let it take priority over "
                f"the layout below: {case.deep}\n\n{depth_shape}") if case.deep else depth_shape
    return case.standard or depth_shape
