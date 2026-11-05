"""One plain citizen question for every aspect in docs/STATE_COVERAGE.md, for reading the answers by hand.
There's no answer key: this shows what a state's coverage really answers, and where it says nothing.
Run: python eval/aspect_questions.py NAME STATE [STATE ...]   then   --show NAME [MATCH] [WIDTH] to read a short view."""
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TODAY = "2026-11-05"
RUNS = ROOT / "eval" / "cache" / "aspects"

QUESTIONS = {
    "income support": "How much money does the state give farmers each year as income support, and when is it paid?",
    "crop loans": "What is the interest rate on a crop loan for a small farmer here, and is there an interest subsidy?",
    "loan waiver": "Is there a crop loan waiver scheme running in this state now?",
    "KCC": "How do I get a Kisan Credit Card and how much can I borrow?",
    "tenant farmers": "I farm leased land as a tenant. Can I get crop loans and government benefits?",
    "crop insurance": "What is the last date and premium to insure my paddy this Rabi season?",
    "disaster relief": "My crop was destroyed by flood. How much relief per hectare does the state pay?",
    "drought norms": "When is an area declared drought-hit, and what help do farmers get then?",
    "wildlife damage": "Wild boars and elephants damaged my crop. What compensation can I get?",
    "seed": "Is there a subsidy on seeds for farmers here? How do I get it?",
    "fertiliser": "What is the price of a bag of urea and where do I complain if a dealer overcharges?",
    "pesticide rules": "A shop sold me fake pesticide. What rules apply and whom do I complain to?",
    "soil health": "How do I get my soil tested and get a soil health card?",
    "natural farming": "What support does the state give for natural or organic farming?",
    "drip": "What is the subsidy for drip irrigation for a small farmer?",
    "farm ponds": "Is there a government subsidy for digging a farm pond?",
    "wells": "Does the government help pay for a borewell for small farmers?",
    "farm power": "Is electricity free for farm pump sets, and how do I get a new connection?",
    "solar pumps": "What is the subsidy on a solar pump set?",
    "machinery": "What subsidy can I get on a tractor or power tiller?",
    "custom hiring": "Where can I hire farm machinery at a low rate from a government scheme?",
    "drones": "Is there a subsidy to buy or hire agriculture drones?",
    "horticulture": "What subsidy can I get to grow vegetables or fruit crops?",
    "plantation": "Is there help for oil palm or coconut farmers?",
    "sericulture": "What support does the state give for silkworm rearing?",
    "animal husbandry": "What schemes help a farmer buy cows or goats?",
    "dairy": "Is there a milk incentive for dairy farmers, and how much per litre?",
    "fisheries": "What help do fishermen get during the fishing ban?",
    "poultry": "Is there a subsidy to start a poultry unit?",
    "MSP": "What is the minimum support price of common paddy for 2026-27?",
    "state bonus": "Does the state pay anything extra over MSP for paddy?",
    "procurement": "How do I sell my paddy at a government procurement centre?",
    "markets": "How do regulated markets work, and what fee does a farmer pay to sell there?",
    "eNAM": "How can I sell my crop on eNAM from this state?",
    "storage": "Can I store my produce in a government warehouse and get a loan against it?",
    "food processing": "What subsidy is there for a small food processing unit?",
    "FPOs": "How do we form a farmer producer organisation, and what support is available?",
    "land records": "How do I see my land records online and correct a mistake?",
    "tenancy law": "What does state law say about the rights of a land tenant?",
    "land conversion": "How do I convert farm land to non-agricultural use, and what fee applies?",
    "land acquisition": "What compensation do I get if the government acquires my farm land?",
    "extension": "Which local government office should a farmer go to for help and advice?",
    "helplines": "What is the helpline number for farmers?",
    "farmer pension": "Is there a pension or welfare board for farmers?",
    "grievance": "Where do I file a complaint if I did not get a farm scheme benefit?",
    "budget": "How much did the state budget 2026-27 allocate for agriculture?",
    "debt": "What is the outstanding debt and fiscal deficit of the state for 2026-27?",
    "finance commission": "How much does the state get under the 16th Finance Commission?",
    "stamp duty": "What are the stamp duty and registration charges to buy a house?",
    "gift deed": "What will it cost to gift my land to my daughter?",
    "guideline value": "How do I find the government guideline value of my land?",
    "vehicle tax": "How much road tax do I pay on a new Rs.8 lakh car?",
    "two wheeler": "How much life tax do I pay on a new motorcycle?",
    "profession tax": "How much profession tax does a person earning Rs.40,000 a month pay?",
    "state GST": "Who has to register for GST in this state, and where do I get help?",
    "land revenue": "Do I have to pay land revenue or land tax on my farm land?",
    "electricity duty": "What is the electricity duty on my home bill?",
    "property tax": "How is my house property tax calculated and when is it due?",
    "tax arrears": "Is there any scheme to settle old tax arrears with less penalty?",
    "women concessions": "Is there a stamp duty concession if the property is in the name of a woman?",
    "pensions": "How much is the old age pension and who is eligible?",
    "widow pension": "How much is the widow pension and how do I apply?",
    "direct benefits": "What direct cash schemes does the state have for women or mothers?",
    "state loans": "Can a backward class person get a government loan to start a small business?",
    "SHGs": "What loans can a women self-help group get, and at what interest?",
    "cooperatives": "How can I get a loan from a cooperative society?",
    "MSME": "What government scheme helps me start a small business, with what subsidy?",
    "housing": "How do I get a government house or housing subsidy?",
}
PLACES = {"AP": "Andhra Pradesh", "TN": "Tamil Nadu", "MH": "Maharashtra", "KA": "Karnataka"}


def run(name: str, states: list[str]) -> None:
    from vetra import agent, llm

    RUNS.mkdir(parents=True, exist_ok=True)
    path = RUNS / f"{name}.json"
    saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    models = llm.from_env()
    for state in states:
        for aspect, q in QUESTIONS.items():
            key = f"{state}|{aspect}"
            if key in saved:
                continue
            question = f"{q} I am in {PLACES.get(state, state)}."
            for attempt in range(4):
                try:
                    r = agent.answer(question, state=state, models=models, as_of=TODAY)
                    if r.kind == "failed" or r.trace.get("error") or "busy" in r.answer[:60].lower():
                        raise RuntimeError(r.trace.get("error") or "busy")
                    saved[key] = {"q": question, "kind": r.kind, "depth": r.depth, "answer": r.answer,
                                  "sources": [str(s.get("title") or s.get("doc") or "")[:90] for s in r.sources]}
                    break
                except Exception as e:  # a limit or a network drop: wait and try again, then move on
                    print(key, type(e).__name__, str(e)[:80], flush=True)
                    time.sleep(120 * (attempt + 1))
            path.write_text(json.dumps(saved, ensure_ascii=False, indent=1), encoding="utf-8")
            print(key, saved.get(key, {}).get("kind", "MISSED"), flush=True)


def show(name: str, match: str, width: int) -> None:
    saved = json.loads((RUNS / f"{name}.json").read_text(encoding="utf-8"))
    for key, v in saved.items():
        if match in key:
            text = re.sub(r"\s+", " ", re.sub(r"\[E\d+\]", "", v["answer"]))
            print(f"## {key} [{v['kind']}/{v['depth']}, {len(v['sources'])}src] {text[:width]}")


if __name__ == "__main__":
    if sys.argv[1] == "--show":
        show(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "", int(sys.argv[4]) if len(sys.argv) > 4 else 320)
    else:
        run(sys.argv[1], sys.argv[2:])
