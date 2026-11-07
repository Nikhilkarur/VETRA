"""How much do we hold on each aspect for a state? Counts passages and exact records by keyword.
Exact records include central (IN) ones, since the agent uses them for every state.
A low count means a likely gap. A high count doesn't prove the answer is there; read to be sure.
Run: python tools/coverage_grid.py AP TN"""
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
ASPECTS = {
    "agriculture": {
        "income support": r"annadata|sukhibhava|pm-?kisan|income support|farmers? assistance",
        "crop loans": r"crop loan|interest subvention|interest-free loan|zero interest|short.term loan",
        "loan waiver": r"loan waiver|waiver of (?:crop )?loan|debt relief",
        "KCC": r"kisan credit card|\bKCC\b",
        "tenant farmers": r"tenant farmer|tenant cultivator|\bCCRC\b|crop cultivator|oral lessee|cultivator rights",
        "crop insurance": r"fasal bima|\bPMFBY\b|crop insurance",
        "disaster relief": r"input subsidy|natural calamit|\bSDRF\b",
        "wildlife damage": r"wild ?animal|wild ?boar|elephant.{0,40}(?:crop|damage)|wildlife.{0,40}compensation",
        "seed": r"seed (?:subsidy|village|distribution|certification|testing)|subsidi[sz]ed seed|certified seed|seeds? act",
        "fertiliser": r"fertili[sz]er|urea|\bDAP\b",
        "pesticide rules": r"pesticide|insecticides act",
        "soil health": r"soil health|soil test",
        "natural farming": r"natural farming|organic farming|\bZBNF\b|\bAPCNF\b",
        "drip": r"micro.?irrigation|drip|sprinkler",
        "farm ponds": r"farm pond",
        "wells": r"(?:bore|tube|open) ?wells?",
        "farm power": r"free (?:farm )?power|free electricity|agricultur\w* (?:service|connection|power)|9.hours? (?:free )?power",
        "solar pumps": r"solar pump|pm-?kusum|\bKUSUM\b",
        "machinery": r"farm mechani[sz]ation|machinery subsidy|power tiller|\bSMAM\b",
        "custom hiring": r"custom hiring|\bCHC\b|yantra seva",
        "drones": r"drone",
        "horticulture": r"horticultur",
        "plantation": r"plantation|coconut|\bpalm\b|oil palm",
        "sericulture": r"sericultur|mulberry",
        "animal husbandry": r"animal husbandry|livestock|cattle",
        "dairy": r"dairy|\bmilk\b",
        "fisheries": r"fisheries|fishermen|aquaculture",
        "poultry": r"poultry",
        "MSP": r"minimum support price|\bMSP\b",
        "state bonus": r"(?:incentive|bonus).{0,40}(?:paddy|quintal)|(?:paddy|quintal).{0,40}(?:incentive|bonus)",
        "procurement": r"procurement|paddy purchase|direct purchase centre|\bDPC\b",
        "markets": r"regulated market|market committee|\bAPMC\b|uzhavar|rythu bazaar",
        "eNAM": r"e-?NAM",
        "storage": r"warehous|cold storage|godown",
        "food processing": r"food processing",
        "FPOs": r"farmer producer|\bFPOs?\b|\bFPCs?\b",
        "land records": r"land record|pattadar|patta|adangal|chitta|\b1-?b\b|meebhoomi|tamil nilam|bhu ?bharati",
        "tenancy law": r"tenancy|land licensed|cultivating tenant",
        "land conversion": r"land conversion|non-agricultural|NALA\b|reclassification",
        "land acquisition": r"land acquisition|solatium",
        "extension offices": r"rythu seva|rythu bharosa kendra|\bRSK\b|\bRBK\b|extension (?:centre|office|service)|uzhavan",
        "helplines": r"helpline|toll.?free|call centre",
        "welfare boards": r"farmers?.? (?:welfare|pension)|uzhavar pathukappu|welfare board",
        "grievance": r"grievance|complaint",
    },
    "finance": {
        "budget": r"budget (?:estimate|speech|in brief)",
        "debt": r"outstanding (?:debt|liabilit)|fiscal deficit|borrowing|public debt|state debt|debt swap",
        "finance commission": r"finance commission",
        "stamp duty": r"stamp duty",
        "registration fee": r"registration fee",
        "guideline values": r"guideline value|market value (?:guideline|register)",
        "vehicle tax": r"life tax|motor vehicles? tax",
        "profession tax": r"profession(?:al)? tax|tax on professions",
        "state GST": r"\bSGST\b|state goods and services|\bGST\b",
        "land revenue": r"land revenue|land cess|\bkist\b",
        "electricity duty": r"electricity duty",
        "property tax": r"property tax|house tax",
        "tax arrears": r"(?:tax|duty|vat|sales|cess)\w*.{0,60}(?:arrears|one.?time settlement|amnesty)|settlement of arrears",  # a tax context: a land OTS isn't a tax scheme
        "women concessions": r"(?:women|woman|female).{0,50}(?:stamp|concession|rebate)",
        "pensions": r"old age pension|social security pension|widow pension|\bNTR Bharosa\b|pension scheme",
        "direct benefits": r"direct benefit|\bDBT\b|magalir urimai|thalliki vandanam|amma vodi",
        "state loans": r"\bTABCEDCO\b|\bTHADCO\b|\bTAHDCO\b|corporation.{0,40}loan|BC corporation",
        "SHGs": r"self.help group|\bSHGs?\b|\bDWCRA\b|\bSERP\b|mahalir",
        "cooperatives": r"cooperative|co-operative",
        "MSME": r"\bMSMEs?\b|self.employment|\bUYEGP\b|\bNEEDS\b|\bAABCS\b",
        "housing": r"housing scheme|\bPMAY\b|housing for all|kalaignarin kanavu|free house",
    },
}


def searched() -> dict:
    """Aspects looked for and not found in any official source (knowledge/searched.jsonl), by state, topic and aspect."""
    path = ROOT / "knowledge" / "searched.jsonl"
    rows = [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()] if path.exists() else []
    return {(r["state"], r["domain"], r["aspect"]): r for r in rows}


def grid(state: str) -> None:
    print(f"== {state}")
    looked = searched()
    for domain, aspects in ASPECTS.items():
        path = ROOT / "knowledge" / domain / "text" / f"{state}.json"
        items = json.loads(path.read_text(encoding="utf-8"))["items"] if path.exists() else []
        # Record lookups search every topic, so records from both topics count for an aspect.
        records = [json.loads(line) for topic in ASPECTS for name in ("numbers", "dates", "rules")
                   if (ROOT / "knowledge" / topic / f"{name}.jsonl").exists()
                   for line in (ROOT / "knowledge" / topic / f"{name}.jsonl").open(encoding="utf-8")]
        records = [r for r in records if r.get("jurisdiction") in (state, "IN")]  # central rules apply in every state, as in the agent's lookups
        low = []
        for name, pattern in aspects.items():
            rx = re.compile(pattern, re.I)
            passages = [i for i in items if rx.search(i["text"])]
            docs = {i["title"] for i in passages}
            exact = sum(1 for r in records if rx.search(" ".join([r.get("text", ""), r.get("subject", "")] + list(r.get("topic_words") or []))))
            note = " (searched, no official source)" if not exact and (state, domain, name) in looked else ""
            low.append(f"{name} {len(passages)}/{len(docs)}/{exact}{note}")
        print(f"{domain} ({len(items)} passages, {len(records)} records). passages/docs/exact:")
        print("; ".join(low))


for s in sys.argv[1:]:
    grid(s)
