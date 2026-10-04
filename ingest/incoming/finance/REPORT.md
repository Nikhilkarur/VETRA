# Finance — scope proposal (for review, nothing downloaded)

> **Deferred (owner decision, 2026-10-04).** Nothing is collected until RTI and agriculture
> are evaluated. When work resumes, finance becomes **one domain with subcategories**: a
> finance question is routed again to a subcategory (pensions, stamp duty & registration,
> vehicle tax, budget, professional tax, welfare payment status), each with its own
> documents. The topic table below already follows that split. The three review questions
> at the end are settled by that design: pensions and stamp duty become subcategories, and
> budget depth is decided per subcategory.

The brief asks for a one-page scope before bulk downloading, then a stop for review. Every
URL below was checked on 2026-10-04 and resolves (HTTP 200, PDF) unless marked otherwise.
The full list with reasons is in `candidates.json` (`decision: proposed`) and `inventory.json`.

## Proposed citizen-facing topics

| # | Topic | Typical question | Official source found | Docs |
|---|---|---|---|---|
| 1 | **Social security pensions** (now **NTR Bharosa Pensions**; formerly YSR Pension Kanuka) | "How much is the widow pension? How do I apply?" | G.O.Ms.43 PR&RD 13-06-2024 (amounts: Rs.4,000 / 6,000 / 10,000 per month from July 2024; restores the scheme name) on GOIR; sspensions.ap.gov.in: new-pension sanction guidelines (Memo 3407491), application form, About page | 4 |
| 2 | **Stamp duty and registration** | "Stamp duty on a sale deed? How do I register?" | registration.ap.gov.in/igrs: StampFees, RegistrationFees, HowToRegisterDocument, StampDutyProcedure, forms, Acts | 5-7 |
| 3 | **Vehicle tax** | "Life tax on a new bike or car? Am I exempt?" | aptransport.org tax pages (life tax by vehicle type, quarterly, green tax; HTML), tax-exemptions PDF; G.O.Ms.2 (2024) commencement of the MV Taxation (Amendment) Act 2023 | 4-6 |
| 4 | **State budget in plain terms** | "How much did agriculture get this year?" | apfinance.gov.in: **Budget in Brief 2026-27** (Vol. VI), Budget Speech 2026-27; optional Outcome Budget and Gender/Child/BC/Minorities statements | 2-6 |
| 5 | Professional tax | "Do I pay professional tax; how much?" | **Not found yet**: apct.gov.in shows nothing; indiacode down (504) | lead |
| 6 | Welfare payment status (DBT) | "Has my scheme money been paid?" | Aadhaar-based status portals only; look for a published how-to | lead |

**Proposed size: about 20-30 documents.** This is below the brief's 30-80 because finance is
spread across four departments that each publish only a few citizen documents.

## Proposed out of scope (as the brief suggests)

Employees' pay, service and treasury rules; departmental budget circulars (CBRO guidelines,
meeting schedules); the 600+ GOIR "administrative sanction / budget release" orders. They are
government-internal and answer no citizen question.

## Questions for review

1. Is **pensions** finance, or a separate welfare domain? The pension G.O.s come from PR&RD and
   the Department of EWS Welfare, not Finance.
2. Is **stamp duty and registration** in scope? It is the largest citizen-facing money topic,
   but it is Revenue (Registration & Stamps), not Finance.
3. Budget depth: Budget in Brief plus Speech only, or also the Outcome Budget (scheme-wise
   targets, large)?

Once these are settled, `collect.py finance` downloads everything marked `keep`. Flip
`proposed` to `keep` in `candidates.json` and re-run.
