# M5 — Practitioner Validation Kit

**Status:** preparation material for M5. No product features are added in M5.
**Builds on:** [CUSTOMER_DISCOVERY.md](CUSTOMER_DISCOVERY.md) (channels, outreach, base interview
guide, decision rule), [M5_READINESS_CHECKLIST.md](M5_READINESS_CHECKLIST.md),
[METHOD_DECISIONS.md](METHOD_DECISIONS.md).

**Purpose:** to *test* whether ActuaryBench's methodology and workflow match how actuarial
practitioners actually work. The goal is not to collect praise. Every target below is a search
target, not a claim that these people are available.

## 1. Three kinds of evidence and the exit criteria

| Evidence | Question | Minimum by the end of M5 |
|---|---|---|
| E1 Methodology | Does the calculation make sense to practitioners? | ≥ 2 actuaries (pricing/valuation/consultant) give a written position on D6, D7, D8 and D12 |
| E2 Workflow | Does the workflow solve a problem that actually exists? | ≥ 3 people independently describe the same pain point in data prep / experience study (rule in CUSTOMER_DISCOVERY §7) |
| E3 Adoption | Are there prospective users who want to go further? | ≥ 1 person willing to test with synthetic or properly de-identified data under a clear agreement |

If E2 fails (most people care more about IBNR, PSAK 117 reconciliation, mortality and so on), we
**re-scope** per CUSTOMER_DISCOVERY §7. We do not add every module at once.

## 2. Demo-impact triage of the medium issues (checked 2026-11-12)

Checked read-only against the default synthetic dataset (3,804 exposure rows, 11,700 claims; seed
20261112):

| Issue | Seen in the synthetic demo? | Handling in M5 |
|---|---|---|
| M1 Reversal/recovery transactions | No (0 negative amounts, 0 zero-amount claims) | State it as a **limitation**; ask for the source-system definition (M5.1) |
| M2 Overlapping member coverage | **No** (0 overlapping rows; 0 members with > 1 row in the same year; member-months match the coverage span) | The demo is safe. Detection is still a hard requirement before any real data. Ask how practitioners handle duplicate cover |
| M3 Incurred < paid without a reserve column | No (0 rows; incurred = paid + reserve throughout) | Review the definition and data contract with an actuary |
| M4 Last-day coverage timestamps | No (all dates at midnight; 36 claims fall exactly on the last day of cover and validate correctly) | The issue arises only with timestamped files. Upload only the provided synthetic files during the demo |
| M5 Pre-filled assumptions | Yes: the form fills in trend 10%, fixed 5,000, v/c/m 10/5/5% | **Presenter rule:** fill in values explicitly in front of the participant and say they are illustrative; record in sessions whether people accept defaults unknowingly |
| M6 Trend period vs year weighting | Yes: the suggested elapsed months ignore weights | Agenda item for actuarial review (M5.1, D16) |

The demo also triggers no exclusions, validation warnings, current-rate BLOCKED or D6 BLOCKED by
default. Those behaviours are shown deliberately (§3, step 4) as discussion material.

**Guardrail:** the participant must not upload their own file. ActuaryBench does not accept
company data in M5.

## 3. Demo script (15–20 minutes, synthetic only)

1. **Context (1 min).** Prototype, synthetic data, not a validated tariff, not "PSAK 117
   compliant", not a replacement for the appointed actuary.
2. **Data & validation (3 min).** Upload `data/synthetic/invalid_*.csv` to show that every
   exclusion has a reason code and a reconciliation. Then go back to the demo workspace.
3. **Experience study (4 min).** Period 2023-01-01 → 2025-12-31, evaluation date 2026-03-31,
   segments plan_code (+ age_band). Show the denominators, claim definition and paid/incurred
   warning.
4. **The intentional BLOCKED case (3 min).** Change the period to 2024-04-01 → 2025-03-31: the
   study is **BLOCKED**. Open the diagnostic (whole-record vs overlap-by-days). Ask the D6 question
   (§4). Do not present any candidate as the correct answer.
5. **Assumptions & pricing (4 min).** Type the assumptions explicitly. Show the formula trace,
   scenario comparison and BLOCKED segments.
6. **Run & reproducibility (3 min).** Save the run, then show *Check artifact integrity*,
   *Recalculate* and the difference between the three kinds of reproducibility.
7. **Stop presenting; start asking (remaining time).**

## 4. M5.1 — Actuarial Methodology Review

**Target:** pricing actuary, valuation actuary, actuarial consultant (2–3 people).
**Format:** 30–45 minutes; send `METHOD_DECISIONS.md` and a demo screenshot beforehand. Record
positions, not "agree / disagree".

| ID | Current state | Question for the reviewer | Options to discuss |
|---|---|---|---|
| D6 | Periods that cut through coverage are BLOCKED | "When the study period doesn't line up with policy anniversaries, how do you count exposure? Days or months? How is premium earned?" | whole-record / overlap-days / overlap-months / mid-month |
| D7 | Claims reported after the evaluation date are excluded; no paid-as-of history | "How do you build the claims view as at the evaluation date? Do you have transaction history?" | report cut-off / paid-date cut-off / development triangle |
| D8 | Experience period = year of coverage start | "Policy year or calendar/accident year for group-health renewals?" | policy-year / calendar-year with exposure split |
| D12 | Rate-change comparison only with 100% rate coverage in the latest period | "Which current rate is the right comparison? In-force at renewal, latest period, or user input?" | latest period / in-force rate / user-supplied |
| D2/D18 | One row per claim; reversals rejected; zero-amount claims counted | "What is the claim grain in your system? How are reversals and recoveries recorded?" | net per claim / claim-line / transaction-level |
| D13/D16 | Weighted PP then one trend factor; elapsed months from the unweighted midpoint | "Do you trend each year to the projection midpoint before weighting?" | as now / per-period trending / weighted midpoint |
| Loading | (PP + fixed) / (1 − v − c − m) | "Which components are missing for group health (tax, reinsurance, pooling, investment income)?" | — |
| Threshold | Low exposure < 600 MM is a review flag | "Do you use a credibility standard? Full credibility?" | flag / limited fluctuation / Bühlmann |

Each answer goes into the decision log (§8) together with the respondent's role and the evidence
strength. **A decision changes only through a separate M6 milestone**, after enough evidence, with
regression tests and a method-version bump.

## 5. M5.2 — Workflow Validation (task-based)

**Target:** actuarial analyst / associate (2 people).
**Format:** the participant operates the app themselves (screen share) and thinks aloud. The
facilitator does not help unless they get stuck for more than 2 minutes.

| Task | Observe |
|---|---|
| T1 Upload the synthetic file and map columns | Do the canonical column names match their mental model? Is the mapping confusing? |
| T2 Read the validation result for `invalid_*.csv` | Are the reason codes understood? Is anything missing compared with their checks in Excel? |
| T3 Run an experience study by plan × age band | Are the denominators, units and labels clear? Which segments do they normally use? |
| T4 Create an assumption set and run 2 scenarios | Do they accept the defaults without checking (M5)? Are the weights confusing? |
| T5 Export the report and XLSX | Which output does their reviewer actually need? What is missing? |
| T6 Explain "integrity vs recalculation" back in their own words | Is the reproducibility concept understood and relevant? |

Measure: task completed? time, error points, direct quotes (with permission), and the question
"Which step in your current workflow does this replace?"

## 6. M5.3 — Product Discovery

**Target:** actuarial manager, head of actuarial, insurance product manager (1 person or more).
Use the base guide in CUSTOMER_DISCOVERY §5, plus:

1. How does the experience study / pricing workflow run today, end to end?
2. Which part takes the most time, and who does it?
3. What software is used (Excel, R, Python, SAS, Prophet, other)? What is still done in Excel, and
   why?
4. What do reviewers / internal audit / the regulator ask for to reproduce a past result?
5. Is regulatory monitoring (OJK, PAI, IAI) a real need? How is it done now, and who is
   responsible?
6. What are the constraints for software that touches policy/claims data (on-prem, private cloud,
   InfoSec approval)?
7. Who evaluates, approves and owns the budget for a tool like this? What is the procurement
   process?

**Interpretation rule:** polite interest ≠ willingness to buy. Record the concrete next step
(trial, introduction to InfoSec, a request for a proposal) as the E3 signal.

## 7. Recruitment plan

Target: **5 people** — 2 actuarial analyst/associate, 2 pricing/valuation actuary, 1 actuarial
manager/consultant. Sources: life, general and health insurers, actuarial consultants, and the
PAI community and network (see CUSTOMER_DISCOVERY §2). Use LinkedIn and email from
CUSTOMER_DISCOVERY §3–4, offering a **15–20 minute walkthrough**.

Add a role-specific line to the message:

- **Analyst/associate:** "Saya ingin melihat apakah alur upload → validasi → experience study di
  prototype ini cocok dengan cara kerja harian Anda, dan bagian mana yang masih terasa manual."
- **Pricing/valuation actuary:** "Saya sedang mengumpulkan pandangan praktisi tentang beberapa
  keputusan metodologi yang sengaja kami biarkan terbuka (konvensi exposure, evaluation date,
  basis current rate) sebelum mengubah apa pun."
- **Manager/consultant:** "Saya ingin memahami apakah masalah persiapan data dan reproducibility
  experience study cukup penting untuk diselesaikan dengan tool khusus."

Track: name/role (with consent), channel, date contacted, response, session date, workstream
(M5.1/2/3), follow-up. Store the tracker outside the repo if it contains personal data. Never
commit names or contacts.

## 8. Feedback and decision log template

One row per finding (store outside git if it contains identifying information):

| Field | Contents |
|---|---|
| Date / session ID | |
| Role, line of business | no company name without permission |
| Workstream | M5.1 / M5.2 / M5.3 |
| Topic / decision ID | e.g. D6, T3, budget |
| Finding | what was said or observed |
| Evidence strength | observed workflow / opinion / assumption |
| Proposed action | none / backlog / M6 candidate / re-scope |
| Consensus so far | number of people with the same position |

**Rules:**
- One opinion does not change methodology.
- A D-decision becomes an M6 candidate if ≥ 2 actuaries take a consistent position **and** an
  actuary is willing to review the specification.

## 9. What must not be done in M5

- Do not use or accept company policy or claims data; do not let participants upload their own
  files.
- Do not call pricing output a validated tariff, quote or premium.
- Do not call the model "PSAK 117 compliant" or "OJK compliant".
- Do not start a valuation engine or Compliance Watch.
- Do not change methodology or add features during M5; findings go into the log and then into
  M6.
- Do not present synthetic numbers as industry benchmarks.
