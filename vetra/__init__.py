"""
VETRA's modular agent. Three layers, each replaceable without touching the others:

1. Intake     documents collected and checked by hand for now (ingest/).
2. Sorting    each document's content is sorted into stores by what it is: text for
              search, dates, rules, numbers, directory, links, forms (knowledge.py, sorter.py).
3. Agent      the language model plans and explains; code picks what is in force, checks
              figures and adds citations (agent.py).

Adding a topic is one entry in domains.py. Adding a state is data, not code. Changing the
LLM vendor is an environment setting (llm.py). RTI stays on rag/ unchanged.
"""
