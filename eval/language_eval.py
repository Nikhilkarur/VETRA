"""
Does the assistant recognise the question's language, find the answer, and reply in it?

On eval/language_questions.json (English, Telugu script, Telugu typed in English letters):

1. Router: right domain, and right language? (one live call per question, the same
   call that routes it -- rag/router.py)
2. Search: rank of the answering text when searching with the question AS TYPED vs
   with its English translation (query_expansion.to_english), through the live
   pipeline (HyDE + rewrite + rerank). Top 10 = found.
3. --answers N: for N questions per group, the full answer, and whether it came back
   in the expected language (auto setting: Telugu in either alphabet -> Telugu
   script). Costs N answer-model calls per group; not cached.

LLM outputs for 1 and 2 are cached in eval/cache/ (router decisions, HyDE passages,
rewrites, translations), so a rerun reproduces the numbers without API calls.

Run:  python eval/language_eval.py
      python eval/language_eval.py --answers 2
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "rag"))
os.environ.setdefault("LLM_CACHE_DIR", str(ROOT / "eval" / "cache"))
os.environ.setdefault("HYDE_CACHE", str(ROOT / "eval" / "cache" / "hyde.json"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import domains  # noqa: E402
import query_expansion as QX  # noqa: E402
import retrieve as R  # noqa: E402
import router  # noqa: E402


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def rank(hits: list[dict], probes: list[str]) -> int | None:
    need = {squash(p) for p in probes}
    found: set[str] = set()
    for r, h in enumerate([h for h in hits if not h.get("added_because")], 1):
        found |= {p for p in need if p in squash(h["text"])}
        if found == need:
            return r
    return None


def telugu_share(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    return sum(1 for c in letters if "ఀ" <= c <= "౿") / max(1, len(letters))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--answers", type=int, default=0, help="full answers to check per group")
    args = parser.parse_args()

    data = json.loads((ROOT / "eval" / "language_questions.json").read_text(encoding="utf-8"))
    groups = {k: v for k, v in data.items() if isinstance(v, list)}
    print("language eval\n")
    print(f"{'group':<15}{'domain':>9}{'language':>10}{'found, as typed':>18}{'found, translated':>19}")
    misses = []
    for name, items in groups.items():
        dom_ok = lang_ok = typed = translated = searched = 0
        for it in items:
            picked = router.route(it["q"])
            dom_ok += picked.domain == it["domain"]
            lang_ok += picked.language == it["language"]
            if picked.domain != it["domain"] or picked.language != it["language"]:
                misses.append(f"  router: {it['q'][:60]!r} -> {picked.domain} {picked.language}"
                              f" (expected {it['domain']} {it['language']})")
            if not it.get("probes"):
                continue
            searched += 1
            d = it["domain"]
            as_typed, _ = R.retrieve_with_trace(it["q"], 60, True, d)
            english = QX.to_english(it["q"], d, telugu=picked.language == "telugu")
            in_english, _ = R.retrieve_with_trace(english, 60, True, d)
            a, b = rank(as_typed, it["probes"]), rank(in_english, it["probes"])
            typed += bool(a and a <= 10)
            translated += bool(b and b <= 10)
            if english != it["q"]:
                misses.append(f"  search: {it['q'][:40]!r} -> {english!r}: rank {a or '>60'} -> {b or '>60'}")
        n = len(items)
        print(f"{name:<15}{f'{dom_ok}/{n}':>9}{f'{lang_ok}/{n}':>10}"
              f"{f'{typed}/{searched}':>18}{f'{translated}/{searched}':>19}")
    print("\ndetails (router mistakes; every translated search):")
    print("\n".join(misses) or "  none")

    if args.answers:
        from answer import answer_question

        print(f"\nreply language (auto setting), {args.answers} per group:")
        for name, items in groups.items():
            for it in [i for i in items if i["domain"] in domains.DOMAINS][: args.answers]:
                result = answer_question(it["q"], domain="auto", buttons=True)
                share = telugu_share(result["answer"])
                want = "telugu" if it["language"] == "telugu" else "english"
                got = "telugu" if share > 0.5 else "english" if share < 0.15 else "mixed"
                print(f"  {'OK  ' if got == want else 'MISS'} {name:<14} wanted {want:<8} got {got:<8}"
                      f"({share:.0%} Telugu letters)  {it['q'][:50]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
