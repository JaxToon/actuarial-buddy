# M4.1 — Technical & Methodological Assurance Audit

**Scope:** read-only audit of ActuaryBench at commit `e584ff4` (M0–M4), before practitioner validation (M5).
**Date:** 2026-11-12.
**Nature of this document:** an engineering and methodology review prepared by the development
assistant. It is **not** an actuarial opinion, a model validation, or a statement of compliance with
any actuarial, accounting or regulatory standard. Every point marked **[ACTUARY]** needs a qualified
actuary's professional review before it can be settled.

No calculation logic, dataset, test or git history was changed. All experiments used throwaway
scripts outside the repository. They are described below so that anyone can re-run them.

---

## 1. Executive summary

- **The formulas are implemented as specified.** The experience metrics and the pricing chain
  (weighted PP → trend → loading → indicated rate → change) match an independent recalculation from
  the raw clean tables exactly (relative error 0.0). The mathematical invariants hold to
  floating-point precision (≤ 2.2e-16) in all 132 result cells, on both the incurred and the paid
  basis.
- **The most important methodological weakness is the exposure convention (D6).** A member record
  is excluded if any part of its cover falls outside the study period. With calendar-aligned study
  periods on the synthetic data this changes nothing. With a non-aligned period it discards most of
  the exposure and **biases** the result. Example: for 2024-04-01 → 2025-03-31, only 642 of about
  13,789 overlapping member-months are kept, and the loss ratio comes out at 1.008 instead of 0.849
  under an overlap convention. Choosing the production convention is **[ACTUARY]**.
- **Four issues should be fixed before showing anything beyond a scripted synthetic demo:**
  1. The Overview page crashes after any real upload.
  2. The current rate is silently substituted when the latest period has no rate.
  3. Reversal and recovery transactions are rejected wholesale.
  4. Overlapping cover for the same member is not detected.
- **Reproducibility is sound within a session and conditional after a restart.** Hashes and full
  configuration are stored, but neither the input data nor a cleaned snapshot is retained. A run can
  only be reproduced if the user supplies byte-identical data again. Dependency versions are not
  recorded.
- **Synthetic data has no documented statistical rationale.** Its parameters were hand-picked, and
  claim sizes were cut by about 30% after M2 because loss ratios above 100% "looked unrealistic".
  That is calibration for plausibility, not a statistical basis. The data must not be presented as
  a benchmark.
- **M5 readiness:** **conditionally ready** for a synthetic-data walkthrough (conditions in §13).
  **Not ready** for de-identified real data.

## 2. Repository and test status

| Item | Result |
|---|---|
| Git | `main` at `e584ff4`, working tree clean before the audit, 5 commits, all authored by the repository owner |
| Tests | `python -m pytest`: **47 passed** (unit 30, integration 13, smoke 4) |
| Lint | `ruff check .`: all checks passed. `ruff format --check .`: 57 files already formatted |
| Runtime | Python 3.11.9 (the docs specify 3.12+; `pyproject.toml` sets `>=3.11`), pandas 2.3.3, numpy 2.3.5, streamlit 1.62.0, pydantic 2.13.4, openpyxl 3.1.5, xlsxwriter 3.2.9, plotly 7.1.0 |
| Requirements | `requirements.txt` gives lower bounds only (no lock file) |

Test distribution: `test_ingestion` 10, `test_experience` 7, `test_pricing` 13, `test_reporting` 4,
`test_app_pages` 9 (AppTest page runs and the full flow), `test_smoke` 4.

## 3. D1–D16 decision register

Classes: **EC** = engineering convention, **DC** = data contract, **SC** = statistical choice,
**AM** = actuarial methodology.

| ID | Current implementation | Why | Potential impact | Class | Actuary? | Alternatives | Tests to compare |
|---|---|---|---|---|---|---|---|
| D1 | Only ISO `YYYY-MM-DD` dates (or spreadsheet date cells) are accepted; anything else is an error | Avoid day/month ambiguity | Legitimate files in `dd/mm/yyyy` are rejected wholesale (safe, but friction) | DC | No | A user-declared date format per file, applied explicitly and recorded in the manifest | Parse the same file under each declared format; check no silent swap of day and month (e.g. 03/04 vs 04/03) |
| D2 | All occurrences of a duplicated ID are excluded | Cannot know which copy is right | **Transaction/line-level claims files lose whole claims** (see §6) | DC | Yes, for claims grain **[ACTUARY]** | Declared grain: aggregate transactions per `claim_id`, or a composite key `claim_id`+`line_id` | Fixture with an original and a reversal: the aggregated result must equal the net amount and count one claim |
| D3 | Claims on an excluded exposure get the separate reason `linked_exposure_excluded` | Separate orphans from rejected parents | Reporting only | EC | No | None needed | Existing test covers it |
| D4 | incurred = paid + case reserve when incurred is absent. A mismatch above 1 currency unit is an error | PRD §7 | Strict tolerance may reject rounding in source systems. **Incurred < paid is accepted when there is no case-reserve column** | DC / AM | Yes, for definition and tolerance **[ACTUARY]** | Relative tolerance; a warning (not an error) for small mismatches; a rule that incurred ≥ paid | Tolerance sweep on mismatch fixtures; incurred < paid fixture |
| D5 | Zero member-months is a warning (row kept); negative is an error | Zero is plausible | Zero rows add records but no exposure; negative exposure adjustments are rejected | DC | Low | Allow signed adjustments when explicitly flagged | Fixture with an adjustment row netting to the true exposure |
| D6 | A record is included only if its **whole** cover lies inside the study period. No pro-rating | No apportionment method in the spec | **Material bias for non-aligned periods** (§4) | **AM** | **Yes [ACTUARY]** | Overlap by days; overlap by calendar months; mid-month convention | §4 fixtures plus a reconciliation test: partitioning the period must sum to the whole |
| D7 | Claims reported after the evaluation date are excluded; claims without a reported date are included, with a warning | Only cut-off available | Claims that were reported but are not yet paid are still included at full incurred; no paid-as-of history exists | DC / AM | Yes **[ACTUARY]** | Require `paid_date` / transaction history to build an as-of view | As-of fixture with transactions either side of the evaluation date |
| D8 | Experience period = calendar year of `coverage_start`. Claims follow their exposure's period | Matches the synthetic data | Policies crossing calendar years put all their claims in the start year | AM | Yes **[ACTUARY]** | Calendar-year accident basis (by service date, with exposure split); policy-year by anniversary | Cross-year fixture under each basis |
| D9 | Current rate in the study tables = member-month-weighted average over rows **that have a rate** | Comparable to PMPM | **Partial rate coverage silently averages the subset** (§7) | SC | Low | Report rate coverage %; N/A below 100% | Half-missing-rates fixture |
| D10 | Loss ratio is N/A if any row in the cell lacks premium | Avoid partial denominators | Conservative; may hide most loss ratios when premium is sparse | SC | Low | Show the loss ratio on the subset with premium, labelled with its coverage | Partial-premium fixture |
| D11 | `app_pages/` + `st.navigation` | Streamlit guidance | None numerically | EC | No | — | — |
| D12 | Current rate for the change = latest period's weighted rate | Closest to the rate in force | **Engine falls back to an earlier period without warning** (§7) | AM | Yes **[ACTUARY]** | Block the change, or require a user-supplied rate per segment | Latest-period-missing fixture |
| D13 | Positive weight on a period with no exposure → BLOCKED. The UI rescales weights only when the sum is off by less than 0.1%, and says so | Spec §4 | Correct per spec | AM | Review weights policy **[ACTUARY]** | Per-segment weights | Existing tests plus a rounding-rescale test |
| D14 | Equal default weights need an explicit confirmation | Spec §4 | Good. **Other assumption inputs have pre-filled defaults with no confirmation** (§7) | EC | No | Empty inputs that must be entered | AppTest: saving with untouched defaults should be refused |
| D15 | 0% trend only if marked illustrative or sourced | Spec §5 | "Illustrative" is ticked by default | EC / AM | Low | Unticked by default | AppTest |
| D16 | Elapsed months entered by the user; the UI suggests study midpoint → projection midpoint | Never estimate trend | **The suggestion ignores the period weights** (§7) | AM | Yes **[ACTUARY]** | Weight-adjusted midpoint, or trend each period separately before weighting | Compare the methods on 0.2/0.3/0.5 weights |

**Conventions that are implemented but missing from the log** (to add as D17+):
- Coverage end dates are **inclusive** (span = end − start + 1 day).
- Claim count = distinct `claim_id`, including **zero-amount** claims.
- Dates are compared as midnight timestamps (see §6, timestamp boundary).
- The low-exposure threshold defaults to 600 member-months.

## 4. Exposure methodology findings (D6)

> The brief refers to this as "D1". In `METHOD_DECISIONS.md` it is **D6**; D1 is the date-format rule.

### 4.1 Boundary fixture (study period 2024-01-01 → 2024-12-31, inclusive end dates)

| Record | Cover | Overlap days | Production MM | Overlap by days | Overlap by calendar months |
|---|---|---|---|---|---|
| A inside | 2024-03-01 → 08-31 | 184/184 | 6 | 6.000 | 6 |
| B starts before | 2023-07-01 → 2024-06-30 | 182/366 | **0** | 5.967 | 6 |
| C ends after | 2024-07-01 → 2025-06-30 | 184/365 | **0** | 6.049 | 6 |
| D spans | 2023-01-01 → 2025-12-31 | 366/1096 | **0** | 12.022 | 12 |
| E touches start | 2023-01-01 → 2024-01-01 | 1/366 | 0 | 0.033 | 0 |
| F touches end | 2024-12-31 → 2025-12-30 | 1/365 | 0 | 0.033 | 0 |
| G outside | 2025-02-01 → 12-31 | 0 | 0 | 0 | 0 |

Observations:
- **Day versus month convention:** day-based pro-rating gives 5.967 and 6.049 for two
  six-month halves (a leap-year effect). A calendar-month convention gives exactly 6. Partial months
  (E, F) give 0.033 under days and 0 under months. The choice of mid-month or whole-month
  convention is **[ACTUARY]**.
- **Inclusive versus exclusive end:** the code treats the end as inclusive everywhere (validation
  span, study inclusion, claim attribution). An exclusive-end source file would be off by one day
  per record and could push service dates on the last day outside cover. The convention must be
  part of the data contract.
- **Zero or negative overlap:** under an overlap rule, `max(0, …)` must be applied. G must
  contribute nothing, and coverage_end < coverage_start is already a hard error.
- **Claim attribution:** under overlap, claims should be included when service date ∈
  [effective_start, effective_end]. The current code uses [study_start, study_end] plus the
  whole-record rule, which is equivalent only for included records.
- **Reconciliation:** under overlap, splitting the study period into sub-periods must add back to
  the whole (exposure, claims, premium). Under the current rule it does not: the 2024 and 2025
  halves of a straddling record are each excluded.
- **Premium:** an overlap rule also needs a premium earning assumption (pro-rata by days or by
  months). The current data contract gives only total `earned_premium` per record.

### 4.2 Impact on the synthetic portfolio (incurred basis, no segmentation)

| Study period | Method | Member-months | Claims | Freq /1,000 MY | Severity | PMPM | Loss ratio |
|---|---|---|---|---|---|---|---|
| 2023-01-01 → 2025-12-31 | production | 41,581 | 11,700 | 3,376.5 | 512,961 | 144,336 | 0.808 |
| | overlap (days) | identical | | | | | |
| 2023-07-01 → 2025-06-30 | production | 14,331 | 4,028 | 3,372.8 | 550,445 | 154,713 | 0.869 |
| | overlap (days) | 27,741 | 7,782 | 3,366.3 | 524,835 | 147,227 | 0.825 |
| 2024-04-01 → 2025-03-31 | production | **642** | 188 | 3,514.0 | 599,197 | 175,466 | **1.008** |
| | overlap (days) | 13,789 | 3,905 | 3,398.4 | 543,378 | 153,886 | 0.849 |

The production rule does not just shrink the sample. It **selects** mid-year joiners and leavers
(the only records fully inside a non-aligned window), so PMPM and loss ratio move by up to −12% and
−16%. Real portfolios with anniversary-based policy years would hit this with any calendar study
period. The UI shows these exclusions only in the "Study exclusions" tab, with no prominent warning.

**Conclusion:** the overlap convention (with an explicitly chosen day or month rule and premium
earning rule) is the more common analytical approach. Establishing the **correct production
convention cannot be done from the repository and requires actuarial approval [ACTUARY].** Until
then, the safe interim behaviour is to warn prominently whenever partly-overlapping exposure is
excluded.

## 5. Experience study mathematical verification

Checked on the synthetic portfolio, segmented by plan × age band × region (32 segments, 3 periods,
96 period×segment cells, plus overall), on both the incurred and the paid basis:

| Invariant | Max relative deviation | Verdict |
|---|---|---|
| member-years × 12 = member-months | 0 | Exact |
| (freq/1,000 MY ÷ 1,000) × severity = claim amount ÷ member-years | 2.2e-16 | Floating-point rounding only |
| (annual cost per MY) ÷ 12 = PMPM | 2.2e-16 | Floating-point rounding only |
| Σ segment member-months, claims, amount = overall | 0 | Additive |
| Σ period×segment amount = overall | 0 | Additive |

Edge cases (vectorised metric function): zero exposure gives N/A for frequency, severity, PMPM and
loss ratio. Zero claims with positive exposure gives frequency 0, severity N/A, PMPM 0. Missing
premium gives loss ratio N/A. Negative inputs to `compute_metrics` raise an error. Negative claim
adjustments never reach the engine, because validation rejects them (§6). Small-exposure segments
are flagged, but **the demo never shows a flag**: 0 of 32 segments fall below the 600 member-month
default.

No genuine inconsistencies were found. The deviations above are binary floating-point rounding, not
method differences. The report formats display values only and do not round stored values.

## 6. Claim validation review

| Case | Current outcome | Correct classification | Notes |
|---|---|---|---|
| incurred ≠ paid + reserve (both supplied) | Hard error | Hard error, or warning within tolerance **[ACTUARY]** | Fixed 1-unit tolerance |
| incurred < paid, no reserve column | **Accepted silently** | Warning | Implies a negative reserve |
| Negative paid or incurred (recovery, reversal) | Hard error | **Requires source-system definition** | Legitimate in transaction-level data |
| Same claim with original + reversal rows | **Both rows excluded** (duplicate + negative) | Requires grain definition | Whole claim lost; the PRD's `claim_line_id` is not supported |
| Composite claim identifiers | Not supported | Requires source-system definition | Only one `claim_id` column |
| Service date after coverage end | Hard error | Hard error (the cover boundary is the contract) | Correct under inclusive-end dates |
| Service timestamp on the last day of cover (e.g. 14:30) | **Hard error (false positive)** | Should be valid | Dates are compared as timestamps, not calendar dates |
| Service date vs paid date | No paid date field | Requires source-system definition | Needed for an as-of view (D7) |
| Duplicate / overlapping member cover (same `member_ref`) | **Not detected** | Warning or error **[ACTUARY]** | Double-counts exposure |
| Member-months well below cover span (1 MM over 12 months) | Not flagged | Informational / warning | Only over-span is flagged |
| Zero-amount claim | Counted as a claim | Requires definition **[ACTUARY]** | Raises frequency, lowers severity |
| Paid-only data (no reserve or incurred columns) | Paid basis forced; warning shown | Warning | Correctly labelled "paid-claims experience" |
| Reported date before service date | Warning | Warning | Fine |
| XLSX date cells | Parsed correctly | — | Verified |
| `1,200` / `1.200.000` formatted numbers | Hard error (required) / warning (optional) | Informational hint | By design (no silent coercion); the message could suggest removing separators |

**Could current rules reject legitimate claims?** Yes:
- Transaction-level files (reversals, recoveries, multi-line claims) lose whole claims.
- Timestamped service dates on the final day of cover are falsely rejected.

Both bias the claim amount downwards without misstating the counts of what was excluded, which
remain visible.

## 7. Pricing formula verification

Trace (UI → engine):
1. The UI takes percentages and divides by 100 (`assumptions_pricing.py`).
2. `AssumptionSet` (pydantic) validates bounds: d > 0, weights ≥ 0 summing to 1 ± 1e-9, trend in
   (−1, 1], elapsed months in [0, 120], fixed expense ≥ 0.
3. `run_pricing` → `calculate_weighted_pure_premium` → `project_claim_cost` →
   `calculate_indicated_rate`.

Monetary inputs (fixed expense) are in IDR PMPM. v, c and m are decimals of gross premium. The
trend applies to claim cost only, not to fixed expense (per spec §5–6).

**Independent example** (synthetic data, plan segments, incurred basis, weights 0.2/0.3/0.5,
g = 8%, m = 30 months, fixed 7,500, v = 12%, c = 10%, margin = 3%, d = 0.75). Recalculated by hand
from the clean tables without using the package's metric functions:

| Plan | Weighted PP | Projected PP | Indicated rate | Current (2025) | Change | Engine match |
|---|---|---|---|---|---|---|
| PLAN_A | 95,520.66 | 115,786.17 | 164,381.56 | 108,766 | +51.13% | exact (0.0) |
| PLAN_B | 119,093.29 | 144,359.94 | 202,479.92 | 171,735 | +17.90% | exact |
| PLAN_C | 217,448.70 | 263,582.28 | 361,443.03 | 274,776 | +31.54% | exact |

Spec fixtures (Examples A, B, C) are covered by unit tests and pass. Exposure-weighted PP equals
ΣC/ΣE exactly. Bounds probes were all rejected correctly: trend −100%, negative elapsed months,
negative fixed expense, loads summing to 100%, weights summing to 1.0000001.

**Substitution and defaulting findings:**
- **Silent current-rate fallback (High).** If the latest period has no `current_rate_pmpm` in a
  segment, the engine uses the most recent earlier period's rate. In the probe: 2024's 101,650
  instead of "N/A", with no warning. This contradicts D12 and the "never silently substituted"
  principle.
- **Partial rate coverage (Medium).** With half the rates missing, the weighted rate is taken over
  the remaining half, with no warning.
- **Pre-filled assumption inputs (Medium).** Trend 10%, fixed 5,000, v 10%, c 5%, margin 5%,
  elapsed months = suggestion, and "illustrative" ticked are all pre-filled. They are visible and
  need an explicit save, so they are not silent. But only the weights need confirmation, so a user
  can save untouched defaults.
- **Elapsed-month suggestion (Medium) [ACTUARY].** It uses the unweighted midpoint of the study
  period. With 0.2/0.3/0.5 weights the experience centre is later, so the suggestion overstates
  trend time by several months.
- **Single trend period (method note) [ACTUARY].** Weighting the untrended PPₜ and then applying one
  trend factor is the spec's method. A common alternative trends each period to the projection
  midpoint before weighting. The two give different results when m differs by period.
- **BLOCKED handling is correct.** A segment with zero exposure, or a positively weighted period
  with no exposure, is BLOCKED with a reason, and its rate is N/A. No fallback is used. The overall
  "ALL" row is priced independently.
- Omitting a study year from the weights (weight 0) is accepted. That is explicit and visible in
  the trace, so it is acceptable.

This is a **pricing indication model**. It excludes taxes, reinsurance, investment income, capital
cost, large-claim pooling, IBNR and claim development, benefit or plan relativities and
credibility. It is **not a validated insurance tariff methodology**, and the UI and report say so.

## 8. Synthetic data review

- **Generator** (`synthetic.py`): fixed seed 20261112, 12 groups, 3 calendar years.
  - Plan frequencies 2.4 / 2.8 / 3.1 claims per member-year; age multipliers 0.8–1.6.
  - Claim mix 82% outpatient, 10% inpatient, 8% dental, with severity multipliers.
  - Lognormal severity (σ = 1, mean-preserving), frequency trend 6% a year, severity trend 8% a
    year, rate increase 7% a year.
  - Reporting lag ~ Gamma(2, 15 days). Claims reported after 2026-03-31 are dropped. Open-reserve
    share is random for claims reported within 120 days of evaluation.
- **Documented rationale:** none beyond the docstring. Parameters are illustrative choices and are
  not drawn from any cited source.
- **The ~30% severity reduction** was made after the first M2 run because loss ratios were 103–122%.
  The reason was presentational (to look "realistic"), not statistical. It is not recorded in
  `METHOD_DECISIONS.md`.
- **Built-in properties a reviewer should know:**
  - Claim costs rise about 14% a year against 7% rate increases, so loss-ratio drift is by
    construction.
  - Cover is always calendar-aligned, so D6 is never triggered by the default study.
  - There are no low-exposure segments at the default threshold.
  - The generator itself has no version, so changing a parameter silently changes the "same" demo
    data.
- **Recommended scenario set** (future milestone; existing data unchanged). Each scenario should
  carry its own seed, parameter table and a `SYNTHETIC` label in file names and the report:
  1. *Base portfolio*: the current generator, parameters documented as illustrative.
  2. *High-claims portfolio*: higher inpatient share and severity tail.
  3. *Low-exposure portfolio*: small groups so that low-exposure flags and BLOCKED segments appear.
  4. *Paid-only portfolio*: no reserve or incurred columns, exercising the paid basis.
  5. *Data-quality-defect portfolio*: a scaled-up invalid fixture, including reversals,
     overlapping member cover, timestamps, anniversary-based cover (to exercise D6) and
     inclusive/exclusive end-date variants.

Synthetic outputs must never be presented as industry benchmarks or as evidence about real loss
ratios.

## 9. Reproducibility assessment

**What is persisted per saved run.** SQLite `runs` (immutable via trigger) plus
`data/outputs/<run_id>/`, holding `report.html`, `results.xlsx`, `pricing_results.csv` and
`manifest.json`.

| Element | Status |
|---|---|
| Immutable input snapshot | **Missing.** Only `file_sha256` and `mapped_data_sha256` are stored; uploads are not saved to `data/uploads/` (contrary to ARCHITECTURE §4). Synthetic inputs have an empty file hash and no seed or generator version |
| Cleaned-data snapshot | **Missing** |
| Excluded-row metadata | Partial: counts by reason only; no row-level IDs in the manifest or workbook |
| Column mapping | Stored |
| Assumption snapshot | Stored in full (all fields, weights, owner, created_at) |
| Calculation settings | Study config stored. **Validation tolerances (`ValidationConfig`) are not stored** |
| Methodology version | `method-0.1.0`, a static constant never bumped through M2–M4; no bump rule |
| Engine version / git SHA | Stored. The `-dirty` flag checks `src/` only (UI changes are not detected) |
| Dependency versions / Python | **Missing** |
| Output hash | Hashes of pricing results, experience by segment and by period are stored. Not hashed: the pricing trace, period×segment, and the output files themselves. The `manifest.json` on disk is not the exact serialisation that `manifest_sha256` was computed over |

| Scenario | Assessment |
|---|---|
| Same-session determinism | **Holds.** Covered by tests; re-reading the same CSV gives an identical mapped hash |
| After application restart | **Conditional.** Possible only if the user re-supplies identical data with the same mapping; the run record and outputs survive in SQLite and on disk |
| After importing a different dataset | **Correctly detected** as not reproduced (input-hash check fails; tested) |
| Across software versions | **Not guaranteed.** The code version is shown but not enforced. Result hashes depend on the pandas CSV float formatting, so a dependency upgrade could change hashes with identical numbers. Dependencies are not recorded |

Storing the JSON configuration plus hashes is **not sufficient** for historical reproduction without
retained inputs.

## 10. Issues by priority

**Critical:** none for a synthetic-only demo. (D6 would be critical for real-data use.)

**High**

| # | Issue | Evidence |
|---|---|---|
| H1 | D6 whole-record exclusion biases non-aligned studies; no prominent warning | §4.2 |
| H2 | Overview page crashes after any real upload (`ValueError: Unknown format code 'f' for object of type 'str'`); the existing tests did not cover it | AppTest probe with uploaded CSV |
| H3 | Silent current-rate fallback to an earlier period; partial rate coverage unflagged | §7 probes |
| H4 | No input or cleaned-data snapshot or dependency record, so historical reproduction depends on the user | §9 |

**Medium**

| # | Issue |
|---|---|
| M1 | Reversal, recovery and multi-line claim transactions rejected wholesale (D2/negative-amount rules) |
| M2 | Overlapping cover for the same member not detected; member-months far below the cover span not flagged |
| M3 | Incurred < paid accepted without a case-reserve column |
| M4 | Timestamps on boundary dates falsely flagged as outside cover |
| M5 | Pre-filled assumption defaults can be saved without confirmation; "illustrative" ticked by default |
| M6 | Elapsed-month suggestion ignores period weights |
| M7 | Synthetic generator calibration undocumented; severity cut for presentation; generator unversioned |
| M8 | Static `METHOD_VERSION`; `-dirty` limited to `src/`; output files and trace not hashed; `ValidationConfig` not persisted |
| M9 | Undocumented conventions: inclusive end date, claims attributed to the exposure start year, zero-amount claims counted, midnight timestamp comparison |

**Low**

| # | Issue |
|---|---|
| L1 | Demo never shows a low-exposure flag or a BLOCKED segment |
| L2 | `manifest.json` on disk differs from the hashed serialisation |
| L3 | Missing tests (§12) |
| L4 | Number-format errors give no hint about thousands separators |
| L5 | An invalid optional premium raises two warnings for one cause |
| L6 | Python 3.11 in use against the docs' 3.12+; no dependency lock file |

## 11. Professional actuarial review requirements [ACTUARY]

1. Exposure convention for partial overlap: day or month basis, mid-month rule, premium earning (D6).
2. Experience-period basis: policy-year by start year versus calendar/accident year (D8).
3. Claim definition: grain, treatment of reversals and recoveries, zero-amount claims, incurred
   tolerance (D2, D4).
4. Evaluation-date treatment and the need for paid-as-of data and development or IBNR caveats (D7).
5. Current-rate basis for the indicated change (D9, D12).
6. Weighting policy, and whether to trend per period before weighting; the elapsed-month convention
   (D13, D16).
7. Whether the loading formula (expenses, commission and margin as % of gross; fixed PMPM) fits the
   intended product context, and which omitted loads must be added before any external use.
8. Low-exposure threshold policy and whether any credibility treatment is expected (out of MVP
   scope).
9. The synthetic data parameters, if they are to be described as "plausible" in any demo narrative.

None of these can be settled from the repository.

## 12. Recommended changes for a future implementation milestone (M4.2, not done here)

1. Make the exposure convention selectable and explicit (whole-record versus overlap by days or
   months), defaulting to the actuary-approved one. Show a prominent warning when partial exposure
   is excluded. Add a reconciliation test that sub-periods sum to the whole.
2. Fix the Overview crash: compute validated totals, or coerce for display only with an
   "unvalidated" label. Add an AppTest using uploaded (string) data on every page.
3. Remove the current-rate fallback: use the latest period only, otherwise N/A plus a warning. Report
   rate and premium coverage %.
4. Claims grain: support `claim_line_id`, or explicit aggregation of transactions to the claim, with
   the net amount; make negative-adjustment handling a declared option.
5. Detect overlapping cover per `member_ref`; flag member-months well below the cover span.
6. Compare calendar dates, not timestamps, for boundary checks; flag incurred < paid.
7. Assumption inputs: no pre-filled numbers, or an explicit "use defaults" confirmation; untick
   "illustrative" by default; weight-aware elapsed-month suggestion.
8. Reproducibility: copy inputs into `data/uploads/<hash>/`; store a cleaned-data snapshot
   (Parquet/CSV), excluded row IDs with reasons, `ValidationConfig`, Python and dependency versions,
   and hashes of every output file. Bump `METHOD_VERSION` on any formula or convention change. Make
   the `-dirty` check cover the whole repository. Hash results from rounded, canonical values so
   that dependency upgrades don't break the hashes.
9. Synthetic scenario set (§8) with a versioned generator and documented illustrative parameters.
10. Log D17+ conventions (§3) in `METHOD_DECISIONS.md`.

**Missing tests to add:**
- Invariant tests (§5) on segment and period tables.
- Boundary dates: cover start = study start, service date = cover end, leap year, timestamped
  dates.
- Partial-overlap reconciliation.
- Mixed currency.
- `member_months_exceed_coverage`; `reported_before_service`.
- Incurred < paid.
- Reversal transactions.
- Overlapping member cover.
- Current rate missing in the latest period.
- Partial rate or premium coverage.
- Blank segment values in pricing.
- AppTest with uploaded string data on every page.
- Saving with untouched assumption defaults.
- Reproduction after a simulated restart (new process, same files).
- Manifest field completeness.

## 13. M5 readiness assessment

**Synthetic-data practitioner walkthrough: conditionally ready**, provided that:
- the walkthrough uses the built-in synthetic workspace (or H2 is fixed before showing uploads);
- the study periods are calendar-aligned, or D6's behaviour is explained explicitly;
- the presenter states that the method choices in §11 are open questions for the practitioner, not
  settled methodology;
- the data is described as synthetic and illustrative, never as a benchmark.

**De-identified real data: not ready** until H1–H4 and M1–M4 are resolved and an actuary has
reviewed §11.

Is the prototype safe to demonstrate with synthetic data? **Yes, within the conditions above.** The
calculations are internally consistent and match the specification. The UI and reports carry
prototype and synthetic labels and limitations. No compliance claims appear (checked by an existing
test), and no real data is involved.
