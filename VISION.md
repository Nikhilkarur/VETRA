# The idea

**One place where any Indian can ask the government a question in their own words, in
their own language, and get the answer the government's own documents give, with the
document named.**

This is the long-term vision. What exists today is narrower: an assistant for the Andhra
Pradesh government, covering the Right to Information Act and agriculture. The
[README](README.md) describes that working system and how it was measured.

## The problem

India's governments, central and state, publish an enormous amount: Acts, rules,
government orders, scheme guidelines, budgets, department manuals, Information Commission
decisions. In principle, almost every question a citizen has about the state is answered
somewhere in that record. In practice, almost nobody can find the answer:
- **It is scattered.** Every department and every state has its own portal, and each is
  organised differently.
- **It is filed for officials, not citizens.** Menus follow the government's structure,
  not people's questions. In AP, the RTI Act itself sits four menus deep under a
  department, in a file titled just "RTI ACT".
- **It is written in legal English.** A citizen asks "they didn't reply"; the law says
  "deemed to have refused". A citizen asks how to "apply"; the law says "make a request in
  writing". Ordinary search fails on exactly that gap.
- **It changes quietly.** A fee set in one order is changed by a later one, and a scheme is
  renamed or replaced. Reading one document is often not enough to get the right answer.

Government chatbots exist, but they answer like a help desk, not like the record. In a
side-by-side test with the AP state portal's chatbot, it lost the conversation on a
follow-up question. Ours answered both parts.

We haven't found a product that does all of this together:
- answers **only from official documents**, and cites every source;
- says **"the documents don't cover this"** instead of guessing;
- understands people **the way they actually type**, including Indian languages written in
  English letters ("rti fee entha");
- holds a **conversation**, not one question at a time;
- covers **every department**, not one scheme or one portal.

## Who it is for

**People who want to understand politics and power from the source.** Politically engaged
readers, and a younger generation trying to work out what is true while news, social media
and protests pull in different directions. They don't need another opinion. They need what
the law, the order, the budget or the official record actually says, with a citation they
can check themselves. They want to know:
- what a new law or order actually changes, and for whom;
- what the government has promised, allocated and spent;
- what their rights are when they protest, ask questions or are refused information;
- how to use the Right to Information Act to get the facts that aren't published.

**People who are less privileged, and need to know what they are entitled to.** Many of the
people who most need government help have little formal education, don't read English, and
can't navigate a portal. A missed scheme, a wrong form or an unpaid claim costs them the
most. They want plain answers to plain questions:
- which **schemes** they qualify for, and how to apply;
- which **free or subsidised benefits** exist: rations, pensions, seeds, insurance, loans,
  housing, scholarships, training;
- which **government jobs and opportunities** are open to them;
- what is reserved or offered for their **social category** (SC, ST, OBC/BC, EWS) and for
  women, minorities and people with disabilities;
- how to **buy land or a house safely**: checking the title, registration, stamp duty;
- **where to complain**, and what to do when an office doesn't respond.

## Where it goes

1. **Andhra Pradesh, department by department.** RTI and agriculture are live. Next come
   finance (pensions, stamp duty and registration, vehicle tax, the state budget), then
   welfare schemes by social category, jobs and recruitment, land and revenue.
2. **Every department of one state.** One assistant that routes each question to the right
   department's documents, as it already does between RTI and agriculture.
3. **Other states and the central government.** The same pipeline works for any state's
   documents, and central schemes and Acts apply everywhere.
4. **Every Indian language.** Telugu works today, in its own script and in English letters.
   The same approach extends to Hindi, Tamil, Kannada, Bengali and the rest.
5. **Voice.** For people who can't read or type comfortably, asking out loud is the only
   interface that works.

## What it will not do

- **Take political sides.** It reports what the official record says and cites it. Where
  the record is silent or disputed, it says so.
- **Guess.** If the documents don't answer a question, it says that, and points to where
  to ask.
- **Replace a lawyer or an official.** It explains the rules and where they come from; it
  doesn't file applications or give legal advice.
