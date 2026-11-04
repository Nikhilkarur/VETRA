"""
Does the second reader catch wrong statements, and leave right ones alone?

Statements written by hand against passages written by hand, some true and some planted false, in
English, Hindi and Telugu. It compares the reader's plain prompt with today's, which adds written
rules and examples of past failures. This is a small check, so a difference of one or two isn't proof.

Run:  python eval/second_reader_eval.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from vetra import llm, verify  # noqa: E402
from vetra.tools import Evidence  # noqa: E402

PASSAGES = [
    "Under PM Kisan Maan Dhan Yojana the pension is Rs.3000 a month after the age of 60.",
    "Tenant farmers holding a valid crop cultivator card can apply for the loan, up to Rs.2 lakh.",
    "In Kharif 2024 farmers paid no premium. From Rabi 2024-25 enrolment is voluntary and the farmer pays his share.",
    "The minimum crop loss needed for input subsidy is 33 per cent.",
    "A seed dealer's licence is valid for five years.",
]

# (statement, the passage it cites, is it true)
CASES = [
    ("PM Kisan Maan Dhan Yojana pays a pension of Rs.3000 a month from age 60.", 1, True),
    ("PM-KISAN pays Rs.3000 a month.", 1, False),
    ("The pension is Rs.3000 a year.", 1, False),
    ("Tenant farmers with a valid cultivator card can get a loan of up to Rs.2 lakh.", 2, True),
    ("All tenant farmers can apply for the loan.", 2, False),
    ("A tenant farmer with a cultivator card gets Rs.2 lakh.", 2, False),
    ("Enrolment has been voluntary since Rabi 2024-25, and the farmer pays a share.", 3, True),
    ("Farmers pay no premium.", 3, False),
    ("Input subsidy needs a crop loss of at least 33 per cent.", 4, True),
    ("Any crop loss qualifies for input subsidy.", 4, False),
    ("A seed licence lasts five years.", 5, True),
    ("A seed licence must be renewed every year.", 5, False),
    ("प्रधानमंत्री किसान मानधन योजना में 60 वर्ष की आयु के बाद हर महीने 3000 रुपये पेंशन मिलती है।", 1, True),
    ("प्रधानमंत्री किसान मानधन योजना में 60 वर्ष से पहले पेंशन मिलती है।", 1, False),
    ("పంట నష్టం కనీసం 33 శాతం ఉంటేనే ఇన్‌పుట్ సబ్సిడీ వస్తుంది.", 4, True),
    ("పంట నష్టం ఎంత ఉన్నా ఇన్‌పుట్ సబ్సిడీ వస్తుంది.", 4, False),
]

_RULES = re.compile(r"Check these closely.*?judge the meaning, not the words\.\n\n", re.S)


def run(prompt: str, models: llm.Models) -> tuple[int, int, int, int]:
    verify._PROMPT = prompt
    evidence = [Evidence(f"p{n}", "text_search", text, f"Passage {n}") for n, text in enumerate(PASSAGES, 1)]
    answer = "\n".join(f"- {statement} [E{cited}]" for statement, cited, _ in CASES)
    flagged, ran = verify.unsupported(answer, evidence, models, llm.Meter())
    if not ran:
        raise llm.LLMError("the second reader didn't run")
    said = [any(statement in f for f in flagged) for statement, _, _ in CASES]
    caught = sum(s and not true for s, (_, _, true) in zip(said, CASES))
    false_alarms = sum(s and true for s, (_, _, true) in zip(said, CASES))
    for s, (statement, _, true) in zip(said, CASES):
        if s == true:
            print(f"    {'false alarm' if s else 'missed'}: {statement[:80]}")
    return caught, sum(not c[2] for c in CASES), false_alarms, sum(c[2] for c in CASES)


def main() -> int:
    models = llm.from_env()
    today = verify._PROMPT
    assert _RULES.search(today), "the prompt no longer has its rules section"
    for name, prompt in (("plain prompt", _RULES.sub("", today)), ("with rules and examples", today)):
        print(name)
        caught, wrong, alarms, right = run(prompt, models)
        print(f"  caught {caught}/{wrong} false statements, {alarms}/{right} false alarms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
