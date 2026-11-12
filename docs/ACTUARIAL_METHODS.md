# Actuarial Method Notes — MVP Boundaries

**Purpose:** define a transparent educational/prototype method for group-health experience analysis and preliminary pricing indication.  
**Important:** this document is not an actuarial standard, an actuarial opinion, a regulatory interpretation or an approved pricing basis. A qualified actuary must review the method and assumptions before operational use.

## 1. Product and method boundary

The MVP studies annual renewable group-health / medical experience using exposure and claims data. It does not produce life mortality rates, a full morbidity table, technical reserves, IBNR, or PSAK 117 measurements.

Use only synthetic or properly de-identified data. Do not ingest names, NIK, full dates of birth, addresses, diagnosis narratives, medical records or other direct identifiers in the public prototype.

## 2. Definitions

- **Exposure:** covered risk time measured as member-months (or member-years = member-months / 12).
- **Paid claims:** amounts paid by the evaluation date.
- **Case reserve:** outstanding reserve attached to reported claims, if supplied by the data owner.
- **Incurred claims:** supplied incurred amount, or paid + case reserve when that is the agreed definition. The report must state which definition is used.
- **Claim count:** count of unique claims at the claim grain selected by the user, not raw line count.
- **PMPM:** per member per month.
- **Experience period:** historical period included in the study.
- **Projection period:** future period for which the rate indication is prepared.

If only paid claims are available, label the metrics “paid-claims experience”. Do not call them ultimate claims or imply that claim development/IBNR has been allowed for.

## 3. Core experience metrics

For a selected segment and experience period:

Let:

- `E` = earned member months.
- `N` = number of distinct claims.
- `C` = total incurred claims under the chosen definition.
- `P` = earned premium, when supplied.

Then:

- Member years = `E / 12`.
- Claim frequency per 1,000 member-years = `(N / (E / 12)) * 1,000`.
- Average claim severity = `C / N`, when `N > 0`.
- Claim cost PMPM / pure premium PMPM = `C / E`, when `E > 0`.
- Loss ratio = `C / P`, when `P > 0`.

For zero claims, severity is undefined (show N/A), while claim cost PMPM is zero if exposure is positive. For zero exposure or zero premium denominators, show N/A and block rate calculation for that segment.

### Segment dimensions

Initial supported dimensions: `plan_code`, `age_band`, and `region` if present and selected. Segment definitions are user-configurable. Do not make gender, diagnosis or detailed occupation mandatory dimensions.

### Low-exposure flags

The user sets a minimum member-month threshold. Any segment below the threshold is marked “LOW EXPOSURE — REVIEW”. This is a simple operational warning, not a formal credibility factor or credibility-weighted estimate.

## 4. Experience-period weighting

For multiple experience periods `t`, calculate each period's pure premium PMPM:

`PP_t = incurred_claims_t / earned_member_months_t`

Given user-entered non-negative weights `w_t` that sum to 1:

`Weighted PP = sum(w_t * PP_t)`

The report must show each period's exposure, claims, PP and weight. Do not silently select weights. If user weights are not provided, default to equal weights only if the UI explicitly displays and asks the user to confirm that default.

Alternative exposure-weighted aggregate is `sum(C_t) / sum(E_t)`. Keep this as a separate method option; do not mix it with year-weighted averaging.

## 5. Simple trend projection

For the initial MVP, allow one user-supplied annual medical trend assumption `g` and a user-supplied elapsed time `m` in months from the experience midpoint to the projected midpoint.

`Trend factor = (1 + g) ** (m / 12)`

`Projected PP PMPM = Weighted PP PMPM * Trend factor`

The tool must not estimate medical trend automatically in MVP. Show the trend assumption source, owner, effective date and rationale. If the user lacks a defensible trend input, allow 0% only as an explicit illustrative assumption and put a warning in the report.

## 6. Preliminary indicated rate PMPM

Inputs:

- `Projected PP` = projected claim cost per member-month.
- `Fixed expense` = fixed administration expense per member-month.
- `v` = variable expense percentage of gross premium.
- `c` = commission percentage of gross premium.
- `m` = target margin/profit percentage of gross premium.

Define the loading denominator:

`d = 1 - v - c - m`

Then:

`Indicated gross rate PMPM = (Projected PP + Fixed expense) / d`

Conditions:

- `v`, `c`, and `m` must be entered as decimals in `[0, 1)`.
- `d` must be strictly greater than zero; otherwise block the calculation.
- This simplified formula excludes explicit taxes, reinsurance, investment income, risk capital costs, benefit limits, large-claim pooling, taxes, distribution-specific terms and other loads unless separately added in a later, reviewed version.
- Do not label this as a final filed tariff, quote, or binding premium.

If current rate PMPM `R_current` is supplied:

`Indicated change = (Indicated gross rate PMPM / R_current) - 1`

Only calculate this when `R_current > 0`.

## 7. Claims data quality and actuarial caveats

The app must prominently warn about:

- Paid-only versus incurred claims.
- Claim reporting lag and claims development.
- Large claims / pooling arrangements.
- Benefit design changes across periods.
- Change in provider networks, underwriting rules or claim adjudication.
- Incomplete member exposure or mid-month joins/terminations.
- Data currency and inflation basis.
- Small or volatile segments.
- Changes in premium basis, commissions and expenses.

The v1 calculation does not adjust for these factors automatically. The user must document them in the study notes. A later version may add reviewed modules for large-claim treatment, benefit relativity, claim development, credibility and statistical uncertainty.

## 8. What “A/E” means in this product

Do not invent an expected mortality or morbidity table. An Actual-to-Expected comparison can only be enabled when the user explicitly supplies a matching expected-claim baseline with documented definition and segmentation.

`A/E = Actual experience / Expected experience`

The numerator and denominator must have consistent time period, coverage scope, currency, exposure, claim definition and segment dimensions. If those conditions are not satisfied, disable A/E.

## 9. PSAK 117 and valuation boundary

PSAK 117 is the Indonesian insurance-contract accounting standard aligned with IFRS 17. It is not just a mortality-reserve formula. A full implementation involves contract groups, cash-flow estimates, discount rates, risk adjustment for non-financial risk and contractual service margin under the applicable measurement model.

For this MVP:

- Do not implement GMM, VFA or PAA.
- Do not calculate FCF, RA, CSM or insurance contract liabilities.
- Do not output a PSAK 117 valuation or claim PSAK 117 compliance.

PAA eligibility is not automatic merely because a product is “health insurance”. IFRS 17 paragraph 53 permits PAA for a group if, at initial recognition, the entity reasonably expects the LRC measurement not to differ materially from the general model, or the coverage period of each contract in the group is one year or less. This requires contract-level assessment by the entity/actuary.

## 10. Technical reserve and solvency boundary

Do not equate:

1. actuarial pricing indication;
2. technical reserve / regulatory liability calculation;
3. PSAK 117 accounting liability measurement; and
4. solvency capital / MMBR / ORSA.

They may share source data and selected assumptions, but their calculation basis, output meaning and governance differ. Regulatory calculation modules should only be added after mapping current OJK regulations and implementing rules with an appointed actuary/regulatory specialist.

A 2017 OJK technical-reserve circular is publicly accessible and discusses experience data, best-estimate assumptions and justifications. Treat it as a historical regulatory reference requiring current legal-status verification, not as a hard-coded current ruleset.

## 11. Minimum unit-test examples

Use deliberately small fixtures that can be checked by hand.

### Example A — metrics

- Earned member months `E = 1,200`.
- Unique claims `N = 24`.
- Incurred claims `C = IDR 120,000,000`.
- Earned premium `P = IDR 150,000,000`.

Expected:

- Member years = 100.
- Frequency = 240 claims per 1,000 member-years.
- Severity = IDR 5,000,000.
- Claim cost PMPM = IDR 100,000.
- Loss ratio = 80%.

### Example B — trend and rate

- Weighted PP PMPM = IDR 100,000.
- Annual trend = 10%.
- Elapsed time = 12 months.
- Fixed expense = IDR 5,000 PMPM.
- Variable expense = 10%.
- Commission = 5%.
- Target margin = 5%.

Expected:

- Trend factor = 1.10.
- Projected PP = IDR 110,000 PMPM.
- Denominator = 0.80.
- Indicated rate = IDR 143,750 PMPM.

### Example C — invalid loading

If variable expense + commission + margin is `1.0` or greater, the calculation must fail with a clear validation message. It must not return infinity, a negative price or a silent fallback.

## 12. Reproducibility metadata

Each run must snapshot:

- run ID and timestamp;
- input filenames and SHA-256 hashes;
- selected source columns and canonical mapping;
- row counts before and after validation;
- excluded-row counts by reason;
- analysis period and evaluation date;
- selected segment dimensions;
- claim definition (paid / incurred / derived);
- weighting method and weights;
- trend assumption and elapsed months;
- pricing loads;
- calculation package version / git commit when available;
- generated output filenames.
