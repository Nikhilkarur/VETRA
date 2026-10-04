"""
One place for everything that differs between subject domains.

The pipeline itself -- token chunking, bge-small embeddings, hybrid dense + BM25
search, HyDE, RRF, amendment links, the cited answer -- is shared. A domain only
supplies its documents, its index name and the three prompts that speak its
language: the HyDE search passage, the answer rules, and the follow-up rewrite.

Domains today: "rti" (the original assistant, settings unchanged) and
"agriculture". Finance comes later, as one domain with subcategories. Each
domain's router_hint tells the question router (rag/router.py) what it covers,
so adding a domain here is all the router needs.

Every script takes --domain; the default is "rti" so existing commands behave
exactly as before. (The router is a prototype, not yet wired into the web page
or chat.)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Domain:
    name: str
    title: str                 # shown in the chat banner and the web page
    blurb: str                 # one line under the title
    docs_dir: Path
    manifest: Path
    chunks: Path
    collection: str            # Chroma collection
    hyde_prompt: str
    system_prompt: str
    condense_prompt: str
    placeholder: str           # web input hint
    examples: tuple = ()       # "Try asking" suggestions on the web page
    embed_title: bool = False  # embed "document title + chunk" (build_index.py)
    hyde_weight: float = 1.0   # HyDE ranking's RRF vote relative to the question's
    hyde_mode: str = "rrf"     # how the HyDE passage is used (retrieve.py)
    # Extra search signals, chosen per domain by eval/experiments.py (see
    # docs/RETRIEVAL_EXPERIMENTS.md). All off by default.
    expansion: tuple = ()      # LLM rewrites searched too: "topic", "mq", "kw" (query_expansion.py)
    doc_boost: float = 0.0     # RRF vote for chunks of LLM-selected documents (0 = off)
    rerank: dict | None = None # cross-encoder over the fused top n: {"model", "n", "doc", "mode"}
    abbreviations: dict | None = None  # expanded in the question before searching
    router_hint: str = ""      # what this domain covers, for the question router (router.py)
    common_terms: tuple = ()   # words in nearly every document; query expansion must not add them


# ====================================================================== RTI
# Prompts moved here verbatim from retrieve.py / answer.py (2026-10-04).

RTI_HYDE = """Write the single sentence or short paragraph (40 to 80 words) that a statute or government RTI order would contain to answer the question below, in formal legal drafting style.

Rules: plain prose only -- no headings, no markdown, no bullet points, no dates, no reference numbers, no titles. Do not mention "Right to Information Act", "Andhra Pradesh" or "RTI" by name. Accuracy of details does not matter; the vocabulary and phrasing must match real legal text. Output only the passage."""
# Why the "do not mention" rule: every document here is about the RTI Act and
# Andhra Pradesh, so those words match everything and drown the real concept.
# Without the rule, rewritten queries retrieved WORSE than the raw question.

RTI_SYSTEM = """\
You are an assistant that answers questions about the Right to Information Act
2005 as it applies in Andhra Pradesh, for ordinary citizens.

Answer ONLY from the numbered context passages provided. They come from the AP
government's own published documents: the RTI Act itself (labelled by section),
AP government orders and fee rules implementing it, and departmental Section
4(1)(b) manuals.

Rules:
- If the context does not contain the answer, say so plainly. Do not fill the
  gap from general knowledge -- a confident wrong answer about a legal right is
  worse than "the documents I have don't cover this".
- If the passages answer only part of the question, answer that part and say
  what they don't show. Never call something "the only" ground, option or right,
  and never say something is "not permitted", unless a passage says so -- a
  missing passage is not evidence that a rule doesn't exist.
- Copy every amount, time limit and number exactly as the passage states it.
  Do not combine, convert or re-express figures from different clauses.
- Cite the passages you used by their number, like [2] or [3][5]. When a passage
  is a section of the Act, name the section too, e.g. "Section 19 [2]". Cite a
  passage only for what that passage itself says -- check the section label
  before citing it.
- When someone asks what to do because a request was refused, ignored, delayed
  or answered badly, give EVERY remedy the passages contain -- e.g. first appeal,
  second appeal, complaint to the Information Commission -- each with its time
  limit and who it goes to. Lead with the appeal route if a passage describes it;
  do not offer just one remedy when the passages show several.
- Quote the Act's wording for anything about rights, deadlines or fees.
- The Act speaks of "Central" and "State" Public Information Officers. For
  Andhra Pradesh departments the relevant officer is the State one.
- Write plainly, for someone with no legal training. Keep it short.
- The question may be a follow-up. Earlier turns, if shown, are only there to
  help you understand what the question refers to. Take every fact from the
  numbered passages -- never from an earlier answer.
- The AP fee rules and orders here date from 2005-2011, so amounts or procedures
  may have changed since. Say so briefly when an answer gives a fee or a contact.

Three traps in these documents:
- AMENDMENTS. Some orders amend earlier ones (the source label says so). Where an
  amendment changes a rule, give the amended version, and mention it was amended.
- WHO HOLDS AN OFFICE. Government orders name officials as of the order's date.
  Never say someone "currently" holds a post unless the source is the AP State
  Portal page marked as the most current source. Otherwise say who was appointed,
  by which order and when, and that it may have changed.
- DEPARTMENT CONTACTS. Department manuals list officers, phone numbers and
  addresses for THAT department only (named in the source label). Give them only
  if the question is about that department. Never offer one department's officer
  as the contact for another department or for "any office".

Cite with plain square brackets like [2] -- no other citation markup.
"""

RTI_CONDENSE = """You rewrite the latest message in a chat about the Right to Information Act in Andhra Pradesh into one standalone question.

The question you write will be searched on its own, WITHOUT the conversation. So replace every vague reference -- "it", "that", "this", "they", "still", "too", "next", "what about", "and if" -- with the specific thing it refers to in the earlier conversation. If the message is about the user's own situation ("what if i am ...", "what if i was ...") it is asking about the TOPIC being discussed (a fee, an appeal, a deadline) -- name that topic in the question. Keep the user's plain wording otherwise. Leave the message unchanged only if it is already fully clear with no earlier context. Do not add "Right to Information Act" or "Andhra Pradesh" unless the user said them. Do not answer it.

Examples (different conversations from the one you will get):
- Earlier the user asked how to file an RTI application. Latest: "how long will it take" -> How long will it take to get a reply to an RTI application?
- Earlier the user asked about the deadline for a first appeal. Latest: "what if i was in hospital" -> Can I file the first appeal after the deadline if I was in hospital?
- Earlier the user asked whether they can get records older than 20 years. Latest: "what about cabinet papers?" -> Can I get cabinet papers?
- Earlier the user's RTI was refused and they asked what to do. Latest: "and if that fails too" -> What can I do if the first appeal against the refusal also fails?
- Earlier the user asked about fees. Latest: "who do i send the application to" -> Who do I send the application to? (already clear -- unchanged)

Output only the question, on one line."""


# ====================================================================== agriculture

AGRI_HYDE = """Write the single sentence or short paragraph (40 to 80 words) that an official agriculture document -- a state government order, a scheme's operational guidelines, or an Act -- would contain to answer the question below, in formal administrative drafting style.

Rules: plain prose only -- no headings, no markdown, no bullet points, no dates, no reference numbers, no titles. Keep every scheme name, crop, season, document and place the question names, exactly as written; where the question gives what an abbreviation stands for in brackets, use that meaning. Write everyday words the way such documents do -- in the formal terms of subsidies, eligibility, beneficiaries, enrolment, assistance, notified crops and cut-off dates. Do not mention "Andhra Pradesh" by name. If you do not know the facts, still write the passage in the right vocabulary -- accuracy of details does not matter. Output only the passage."""
# v1 ("a government order, scheme guideline or statute on agriculture"): passages
# drifted to generic national-scheme wording and lost names like "e-Crop", so they
# matched the 465-chunk national PMFBY guidelines instead of the short AP order.
# v2 added "keep every term the question uses, exactly as written": that also kept
# casual words ("loan without interest") that no document uses, and the model
# expanded "RBK" as "Rural Business Knowledge Centre". v3 keeps names, translates
# everyday wording, and uses the abbreviation glossary below.

# Abbreviations farmers and these documents use. Matched as whole words in the
# question and expanded in brackets BEFORE searching and before HyDE, so the
# search and the passage writer know what "RBK" or "CCRC" means.
AGRI_ABBREVIATIONS = {
    # Official names only. Descriptive glosses ("Kisan Credit Card crop loan",
    # "e-Panta crop booking") added generic words that pulled in unrelated
    # chunks: measured, they fixed RBK but broke KCC and e-Crop questions.
    "rbk": "Rythu Bharosa Kendram / Rythu Seva Kendram",
    "rbks": "Rythu Bharosa Kendralu / Rythu Seva Kendralu",
    "rsk": "Rythu Seva Kendram / Rythu Bharosa Kendram",
    "rsks": "Rythu Seva Kendralu / Rythu Bharosa Kendralu",
    "ccrc": "Crop Cultivator Rights Card",
    "kcc": "Kisan Credit Card",
    "pmfby": "Pradhan Mantri Fasal Bima Yojana",
    "rwbcis": "Restructured Weather Based Crop Insurance Scheme",
    "msp": "Minimum Support Price",
    "cci": "Cotton Corporation of India",
    "apmip": "Andhra Pradesh Micro Irrigation Project",
    "pmkmy": "Pradhan Mantri Kisan Maan Dhan Yojana",
    "sdrf": "State Disaster Response Fund",
    "chc": "Custom Hiring Centre",
    "chcs": "Custom Hiring Centres",
    "vaa": "Village Agriculture Assistant",
    "fpo": "Farmer Producer Organisation",
    "kms": "Kharif Marketing Season",
    "e-crop": "e-Panta",
}

AGRI_SYSTEM = """\
You are an assistant that answers farmers' and citizens' questions about
agriculture schemes, subsidies and rules in Andhra Pradesh.

Answer ONLY from the numbered context passages provided. They come from AP
government orders (G.O.s), scheme guidelines and notes published by the
Agriculture, Horticulture, Revenue and Civil Supplies departments, and from
central government scheme guidelines, Acts and orders (labelled "central").

Rules:
- If the context does not contain the answer, say so plainly. Do not fill the
  gap from general knowledge -- a confident wrong answer about money a farmer
  is owed is worse than "the documents I have don't cover this".
- If the passages answer only part of the question, answer that part and say
  what they don't show. Never say something is "the only" option or "not
  allowed" unless a passage says so.
- Copy every amount, percentage, limit and date exactly as the passage states
  it. Say which season, year, crop or category of farmer a figure applies to
  (e.g. "for Kharif 2026", "for SC/ST small farmers", "in irrigated areas").
  Never apply a figure to a different season, crop or category.
- State every condition the way the passage words it, negatives included: if a
  passage says a tenant's name is NOT recorded, or a farmer shall NOT own land,
  say exactly that. Never turn a "must not" into a "must".
- For "how do I ..." questions, list only the steps, documents, payment methods
  and limits a passage actually states. Do not add plausible extra steps (a
  payment mode, an area ceiling, a form) that no passage mentions.
- Prefer short paragraphs or bullet lists to tables. If you do use a table, put
  a condition only on the rows the passage applies it to.
- Cite the passages you used by their number, like [2] or [3][5], and name the
  order or guideline, e.g. "G.O.Ms.No.33 (2025) [2]". Cite a passage only for
  what that passage itself says.
- For "can I get ..." questions, give the eligibility conditions AND any
  exclusions the passages contain.
- For "how / where do I ..." questions, name the centre, office or portal the
  passages give (for example the Rythu Seva Kendram, a bank, a web address).
  Never invent a portal, helpline or phone number.
- Write plainly, for a farmer with no legal training. Keep it short.
- The question may be a follow-up. Earlier turns, if shown, are only there to
  help you understand what the question refers to. Take every fact from the
  numbered passages -- never from an earlier answer.

Four traps in these documents:
- RENAMED SCHEMES. In 2024 many schemes were renamed (G.O.Ms.No.79): e.g. YSR
  Rythu Bharosa -> Annadata Sukhibhava, Rythu Bharosa Kendram -> Rythu Seva
  Kendram, e-Crop -> e-Panta, YSR Sunna Vaddi Panta Runalu -> Vaddi Leni Runalu,
  Dr. YSR Free Crop Insurance -> PMFBY. ALWAYS give the current name, even when
  the passages you were given only use the old one; give the old name too when
  the user or a passage uses it.
- NOT IN FORCE. A source label marked "NOT IN FORCE" describes a replaced scheme
  or rule. Never present its amounts or conditions as current; use it only to
  explain what changed.
- TIME-BOUND ORDERS. Today's date is {today}. Many orders cover one season or
  year (Kharif 2026, KMS 2025-26, 2024-26). When passages cover different
  periods, answer for the one in force today -- usually the latest order, e.g.
  an extension order -- and mention older periods only as history. Never call a
  past season "current". Say the period; if even the latest order may have
  ended, say the current season's order should be checked. When guidelines are
  several years old, say their date.
- STATE vs CENTRAL. Say whether a rule comes from an AP order or a central
  scheme. Department manuals list officers and phone numbers for THAT office
  only -- give them only if the question is about that office.

Cite with plain square brackets like [2] -- no other citation markup.
"""

AGRI_CONDENSE = """You rewrite the latest message in a chat about agriculture schemes and rules in Andhra Pradesh into one standalone question.

The question you write will be searched on its own, WITHOUT the conversation. So replace every vague reference -- "it", "that", "this", "they", "still", "too", "next", "what about", "and if" -- with the specific thing it refers to in the earlier conversation (a scheme, a crop, a subsidy, a season). If the message is about the user's own situation ("what if i am ...", "what if i have ...") it is asking about the TOPIC being discussed -- name that topic in the question. Keep the user's plain wording otherwise. Leave the message unchanged only if it is already fully clear with no earlier context. Do not add "Andhra Pradesh" unless the user said it. Do not answer it.

Examples (different conversations from the one you will get):
- Earlier the user asked about the Annadata Sukhibhava payment. Latest: "what if i am a tenant" -> Can a tenant farmer get the Annadata Sukhibhava payment?
- Earlier the user asked about crop insurance premium for paddy. Latest: "and for cotton?" -> What is the crop insurance premium for cotton?
- Earlier the user asked how to get subsidy seed. Latest: "how much does it cost" -> How much does subsidy seed cost?
- Earlier the user asked about drip irrigation subsidy. Latest: "who do i apply to" -> Who do I apply to for the drip irrigation subsidy?
- Earlier the user asked about crop loans. Latest: "what is the paddy MSP" -> What is the paddy MSP? (already clear -- unchanged)

Output only the question, on one line."""


DOMAINS = {
    "rti": Domain(
        name="rti",
        title="AP RTI assistant",
        blurb="Ask about the Right to Information Act as it applies in Andhra Pradesh. "
              "Answers come only from the 41 documents published by the AP government.",
        docs_dir=ROOT / "ingest" / "documents",
        manifest=ROOT / "ingest" / "corpus_manifest.json",
        chunks=ROOT / "ingest" / "chunks.json",
        collection="ap_rti",
        common_terms=("Right to Information Act", "Andhra Pradesh", "RTI"),
        hyde_prompt=RTI_HYDE,
        system_prompt=RTI_SYSTEM,
        condense_prompt=RTI_CONDENSE,
        placeholder="Ask a question about RTI…",
        router_hint="The Right to Information Act 2005 and using it in Andhra Pradesh: "
                    "asking any government office for information or records, RTI fees, "
                    "time limits, refusals and exemptions, first and second appeals, "
                    "complaints and penalties, the State Information Commission and its "
                    "commissioners, and Public Information Officers.",
        examples=("how do i file an rti application",
                  "how much money do i need to pay for an rti in andhra pradesh",
                  "the officer keeps delaying it what should i do",
                  "can the officer refuse to give me information",
                  "is rti free for BPL families",
                  "does rti work for intelligence agencies like IB"),
    ),
    "agriculture": Domain(
        name="agriculture",
        title="AP agriculture assistant",
        blurb="Ask about farm schemes, subsidies, crop insurance and rules in Andhra Pradesh. "
              "Answers come only from 44 official AP and central government documents.",
        # Staged, not yet promoted to ingest/documents (see ingest/incoming/README.md).
        docs_dir=ROOT / "ingest" / "incoming" / "agriculture",
        manifest=ROOT / "ingest" / "incoming" / "agriculture" / "manifest.json",
        chunks=ROOT / "ingest" / "chunks_agriculture.json",
        collection="ap_agriculture",
        common_terms=("Andhra Pradesh",),
        hyde_prompt=AGRI_HYDE,
        system_prompt=AGRI_SYSTEM,
        condense_prompt=AGRI_CONDENSE,
        placeholder="Ask about a farm scheme, subsidy or crop insurance…",
        router_hint="Farming in Andhra Pradesh: farmer income support (Annadata Sukhibhava, "
                    "PM-KISAN), crop insurance, crop loans and Kisan Credit Cards, interest-free "
                    "loans, tenant farmers' cultivator cards, subsidies for seeds, drip and "
                    "sprinkler irrigation, farm machinery and horticulture, minimum support "
                    "prices and paddy or cotton procurement, relief for crops and livestock "
                    "lost to floods, cyclones or drought, the laws on seeds, fertilisers and "
                    "pesticides, Rythu Seva Kendrams, farmer pensions, free farm power, and "
                    "the Agriculture and Horticulture departments' own offices and officers.",
        examples=("i take land on lease, can i get annadata sukhibhava money",
                  "what is rythu bharosa called now",
                  "do i have to pay for crop insurance now",
                  "my crop was damaged in the cyclone, how much will govt give",
                  "how do i get subsidy seeds",
                  "drip irrigation subsidy for small farmers"),
        # Measured 2026-10-04 on eval/agri_questions.json dev + dev_casual (36 q):
        # title prefix off/on, no HyDE: 81% / 94%; with HyDE v1: 86% / 89%;
        # on + HyDE v2 (above): 92% (casual 92%). HyDE weight 0.3-1.0 and the
        # "dense"/"concat" modes changed nothing or hurt.
        embed_title=True,
        abbreviations=AGRI_ABBREVIATIONS,
    ),
}


def expand_abbreviations(question: str, domain: Domain) -> str:
    """'what do they call the RBK now' -> 'what do they call the RBK (Rythu Bharosa Kendram, ...) now'."""
    import re

    if not domain.abbreviations:
        return question
    def repl(m):
        meaning = domain.abbreviations.get(m.group(0).lower())
        return f"{m.group(0)} ({meaning})" if meaning else m.group(0)
    return re.sub(r"(?<![\w-])[A-Za-z][\w-]*(?![\w-])", repl, question)


def get(name: str) -> Domain:
    try:
        return DOMAINS[name]
    except KeyError:
        raise SystemExit(f"unknown domain {name!r}; choose from {', '.join(DOMAINS)}")
