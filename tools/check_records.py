"""Check exact records for topic words that are too loose, with no model.

A record's topic_words decide whether it is even looked at; applies_to then narrows among those found.
A crop name or a general word ("damage", "subsidy") as a topic word drags a record into questions about
something else: a paddy procurement rate into a question about elephants eating paddy. Those words belong
in applies_to. This lists them so a person can move them. Also flags repeated ids and missing sources.
Run: python tools/check_records.py"""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
CROPS = {"paddy", "rice", "wheat", "maize", "cotton", "groundnut", "sugarcane", "mango", "banana", "coconut", "chilli",
         "chillies", "turmeric", "tomato", "onion", "pulses", "millets", "ragi", "jowar", "bajra", "red gram", "black gram",
         "green gram", "guava", "papaya", "cashew", "citrus", "tobacco", "cow", "cows", "buffalo", "goat", "sheep", "seed", "seeds"}
GENERAL = {"damage", "destroyed", "compensation", "subsidy", "scheme", "loan", "assistance", "incentive", "help", "benefit",
           "relief", "price", "rate", "tax", "fee", "money", "support", "death", "died", "accident", "income", "6000"}


def main() -> int:
    problems = 0
    for path in sorted((ROOT / "knowledge").glob("*/*.jsonl")):
        ids = set()
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            r = json.loads(line)
            where = f"{path.parent.name}/{path.name}:{n} {r.get('id')}"
            if r.get("id") in ids:
                print(f"{where}: repeated id")
                problems += 1
            ids.add(r.get("id"))
            if not (r.get("source") or {}).get("url"):
                print(f"{where}: no source url")
                problems += 1
            loose = [w for w in r.get("topic_words") or [] if w.strip().lower() in CROPS | GENERAL or w != w.strip()]
            if loose:
                print(f"{where}: loose topic words {loose}")
                problems += 1
    print(f"{problems} to look at")
    return 0


if __name__ == "__main__":
    sys.exit(main())
