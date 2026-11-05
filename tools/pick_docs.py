"""Pick documents worth fetching from the crawled lists, by subject words for each aspect, with no model.
Reads eval/cache/hand/gos.jsonl (AP orders) and pdfs.jsonl (official PDFs). Skips what's already held.
Run: python tools/pick_docs.py [--count]   writes eval/cache/hand/pick_STATE.jsonl for tools/fetch_docs.py"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
HAND = ROOT / "eval" / "cache" / "hand"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SINCE = 2023  # older orders are read only when a later one refers to them

AGRICULTURE = {
    "income support": r"annadatha|rythu bharosa|sukhibhava|pm.?kisan|input subsidy",
    "crop loans": r"crop loan|interest subvention|interest free|zero interest|vaddi leni|pavala vaddi|kisan credit",
    "tenant farmers": r"tenant|ccrc|crop cultivators?|cultivator rights|lease(d)? (land|farmer)",
    "crop insurance": r"crop insurance|fasal bima|pmfby|weather based",
    "disaster relief": r"input subsidy|crop damage|crop loss|natural calamit|sdrf|ndrf|cyclone.*(relief|assistance)|flood.*(relief|assistance)",
    "drought": r"drought|mandals? .*declar",
    "wildlife": r"wild ?(boar|animal|life).*(compensation|damage)|elephant.*(compensation|damage)|crop.*compensation",
    "seed": r"\bseeds?\b.*(subsid|distribution|policy)|seed (policy|act|village)",
    "fertiliser": r"fertili[sz]er|\burea\b",
    "pesticide": r"pesticide|insecticide|spurious",
    "soil": r"soil (health|test)",
    "natural farming": r"natural farming|organic farming|apcnf|zero budget|rythu sadhikara",
    "irrigation": r"micro irrigation|drip|apmip|farm pond|borewell|bore well|ntr jala|ysr jala|water harvesting",
    "farm power": r"free power|agricultur\w* (service|connection|power)|pump ?set|kusum|solar pump",
    "machinery": r"farm mechani[sz]ation|custom hiring|agricultural machinery|\bdrone|tractor",
    "horticulture": r"horticultur|midh|oil ?palm|coconut|plantation crop|cashew|nursery",
    "sericulture": r"sericultur|silk|mulberry|chawki",
    "animal husbandry": r"sheep|goat|livestock|cattle|pasu|gokulam|animal husbandry.*(scheme|subsid|policy|insurance)|fodder|mini gokul",
    "dairy": r"\bdairy|milk|jagananna pala|amul|apddcf",
    "fisheries": r"fisher(man|men|ies).*(relief|subsid|scheme|policy|assistance|diesel)|matsya|aqua|fishing ban|ban relief|prawn|shrimp",
    "poultry": r"poultry|broiler|layer",
    "MSP": r"minimum support price|\bmsp\b|procurement price",
    "procurement": r"paddy procurement|procurement of (paddy|maize|pulses|groundnut|cotton)|kharif marketing|rabi marketing|rythu seva|rbk\b|markfed|price stabili[sz]ation",
    "markets": r"market (fee|committee|yard)|agricultural market|\be-?nam\b|rythu bazar|apmc",
    "storage": r"warehouse|godown|cold storage|pledge loan|rythu bandhu",
    "food processing": r"food processing|mega food|apfps",
    "FPOs": r"farmer producer|\bfpos?\b",
    "land records": r"webland|dot ?ted land|land record|resurvey|bhu ?(bharathi|raksha)|pattadar|passbook|mutation|\b1-?b\b",
    "tenancy law": r"tenancy|\\binam\\b|assigned land|land reform|ceiling",
    "land conversion": r"conversion of (agricultural )?land|non.?agricultural|\\bnala\\b",
    "land acquisition": r"land acquisition.*(compensation|rules|act|market value)|land pooling|rehabilitation and resettlement",
    "farmer pension": r"farmers?.*(pension|welfare|ex-?gratia|suicide)|rythu bima",
}
FINANCE = {
    "stamp duty": r"stamp duty|registration fee|table of fees|registration act|indian stamp",
    "guideline value": r"market value|basic value|guideline value",
    "vehicle tax": r"life tax|motor vehicles? tax|road tax|green tax",
    "profession tax": r"profession tax|tax on professions",
    "state GST": r"gst (registration|help|facilitation)|goods and services tax.*(registration|act, 20)",
    "land revenue": r"land revenue|land tax|cess on land",
    "electricity duty": r"electricity duty|tariff order|power subsidy|free power to|surya ghar",
    "property tax": r"property tax|house tax|vacant land tax",
    "tax arrears": r"one time settlement|\bots\b|amnesty|arrears.*(waiv|settlement)|waiver of (interest|penalty)",
    "women concessions": r"women.*(stamp|registration|concession)|concession.*women",
    "pensions": r"social security pension|ntr bharosa|ysr pension|pension kanuka|old age pension|widow pension|disab\w+ pension",
    "direct benefits": r"thalliki|talli ki|aada ?bidda|deepam|free bus|sthree shakti|stree shakti|nidhi|kalyanamasthu|shaadi tohfa|amma vodi|ee?bc nestham|kapu nestham|cheyutha|asara|maternity|dokka seethamma",
    "state loans": r"(bc|sc|st|kapu|minorit\w+|ebc|ews) .*(corporation|loan|self.?employment)|self.?employment.*subsid|aadarana|subsidy loan",
    "SHGs": r"self help group|\bshgs?\b|dwcra|vaddi leni|sthreenidhi|velugu|serp\b",
    "cooperatives": r"co-?operative (bank|credit|societ)|pacs\b|dccb|apcob",
    "MSME": r"msme|micro,? small|industrial (development )?policy|pmegp|incentive.*industr|\\bida\\b",
    "housing": r"housing|house sites?|pmay|tidco|pattas?\b",
    "budget": r"budget (speech|at a glance|in brief|highlights)|finance commission|fiscal",
}
NOT_POLICY = re.compile(
    r"establishment|public services|service matter|disciplinary|suspension|transfer|posting|deputation|promotion|retirement|pay scale|"
    r"court|w\.?p\.?\s*no|writ|contempt|o\.a\.|nominat|nominee|appointment|chairman|member of|sanction of (leave|pension)|budget release|proceedings against|misappropriation|house building|advance of|general service rules|elections?\\b|"
    r"release of (funds|budget)|releasing|administrative sanction|engineering|tender|estimate|work of|construction of|revised administrative|"
    r"grants? to|grants? for|grant fund|tied|release of rs|first instal|second instal|\\bac\\.? ?\\d|survey no|sy\\.? ?no|click here|form-i|flow chart|filing procedure|export action plan|alienation|assignment of land|allotment of land|extension of (service|term)|tour|committee constitut|continuance of|temporary posts|creation of posts?", re.I)
ALL = {"agriculture": AGRICULTURE, "finance": FINANCE}


def aspect_of(text: str, table: dict) -> str | None:
    low = text.lower()
    for aspect, words in table.items():
        if re.search(words, low):
            return aspect
    return None


def held() -> set:
    seen = set()
    for manifest in (ROOT / "documents").glob("*/*/manifest.json"):
        for e in json.loads(manifest.read_text(encoding="utf-8")):
            seen.add(str(e.get("source_url") or e.get("url")))
            seen.add(str(e.get("file")))
    return seen


def orders(have: set) -> list[dict]:
    out, seen = [], set()
    for line in (HAND / "gos.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        cells = d["cells"]
        number, date, subject = cells[1], cells[2], cells[4]
        year = int(date[-4:]) if date[-4:].isdigit() else 0
        url = f"https://goir.ap.gov.in/dgo.ashx?gid={d['gid']}&fileType=E"
        # MS orders set policy; RT orders are mostly individual cases, kept only for a few kinds
        if year < SINCE or d["gid"] in seen or url in have or NOT_POLICY.search(subject) or not number.startswith("MS"):
            continue
        for topic, table in ALL.items():
            aspect = aspect_of(subject, table)
            if aspect:
                seen.add(d["gid"])
                out.append({"title": f"Andhra Pradesh G.O.{number} dated {date}: {subject[:160]}", "url": url, "topic": topic, "state": "AP",
                            "doc_type": "go", "department": d["dept"], "date": f"{date[-4:]}-{date[3:5]}-{date[:2]}",
                            "file": f"ap-go-{d['gid']}.pdf", "aspect": aspect})
                break
    return out


def pdfs(have: set) -> list[dict]:
    out, seen = [], set()
    for line in (HAND / "pdfs.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        url = d["url"]
        words = f"{d.get('label', '')} {unquote(url.rsplit('/', 1)[-1])}"
        if url in have or url in seen or d.get("state") not in ("AP", "TN") or NOT_POLICY.search(words):
            continue
        for topic, table in ALL.items():
            aspect = aspect_of(words, table)
            if aspect:
                seen.add(url)
                out.append({"title": f"{d['site']}: {d.get('label') or unquote(url.rsplit('/', 1)[-1])}"[:200], "url": url, "topic": topic, "state": d["state"],
                            "doc_type": "other", "department": d["site"], "aspect": aspect})
                break
    return out


def main() -> None:
    have = held()
    picked = orders(have) + pdfs(have)
    counts: dict = {}
    for p in picked:
        counts.setdefault((p["state"], p["topic"], p["aspect"]), 0)
        counts[(p["state"], p["topic"], p["aspect"])] += 1
    for key, n in sorted(counts.items()):
        print(*key, n)
    print("total", len(picked))
    if "--count" in sys.argv:
        return
    for state in ("AP", "TN"):
        rows = [p for p in picked if p["state"] == state]
        (HAND / f"pick_{state}.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in rows), encoding="utf-8")


if __name__ == "__main__":
    main()
