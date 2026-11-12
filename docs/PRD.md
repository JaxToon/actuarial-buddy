# Product Requirements Document (PRD)

## 1. Product summary

**Working name:** ActuaryBench  
**Product type:** local-first actuarial analysis workbench; potential future B2B SaaS  
**Initial line of business:** annual renewable group health / medical insurance  
**Initial workflow:** data preparation → experience study → assumption/scenario review → pricing indication → reproducible report.

### Product vision

Help actuarial analysts turn policy exposure and claims data into transparent, reproducible experience metrics and preliminary rate indications, without relying on disconnected spreadsheets for every step.

### What the product is not

The first MVP is not a production actuarial valuation system, a PSAK 117 engine, an OJK regulatory reporting system, a replacement for an appointed actuary, or a promise of regulatory compliance. It is an analyst workbench that makes the input data, metrics, assumptions and calculations easier to inspect and reproduce.

## 2. Problem hypotheses (not yet validated with customers)

1. Actuarial analysts spend time cleaning and reconciling policy/exposure and claims files before they can perform the actual study.
2. Experience analysis is often assembled through repeated spreadsheet work, making assumptions, filters and calculation lineage difficult to reproduce across review cycles.
3. Pricing scenarios require analysts to update assumptions and recalculate rate indications consistently by product/plan/segment.
4. Reviewers need a clear explanation of data exclusions, exposure definitions, assumptions, model version and changes between runs.

These are hypotheses, not confirmed facts about every Indonesian insurer. The first customer-discovery activity must test which one is expensive enough to pay to solve.

## 3. Target users and buyer

### Primary users

- Pricing actuary / pricing analyst.
- Employee benefits or group medical actuary.
- Actuarial analyst supporting experience studies.
- Actuarial consultant who prepares study and pricing deliverables for multiple clients.

### Potential buyer / sponsor

- Head of Actuarial / Chief Actuary.
- Head of Product Pricing or Underwriting.
- Partner / practice lead at an actuarial consulting firm.

### Initial design-partner profile

Prefer a consultant or a small actuarial team willing to test a non-production prototype with synthetic or properly de-identified files. This is a discovery choice, not a claim that smaller firms are the largest market.

## 4. MVP positioning

**A transparent workbench for group-health experience analysis and preliminary pricing indication.**

The strongest initial wedge is not “all actuarial calculations in one SaaS”. It is one end-to-end workflow that can be demonstrated with a well-defined dataset and checked independently.

## 5. Scope

### P0 — must have

1. **Demo workspace**
   - Launch into a sample workspace populated with synthetic data.
   - Explain that all displayed records and values are synthetic.

2. **Data import**
   - Upload CSV and XLSX files for exposure/member-month data and claims.
   - Provide downloadable sample templates.
   - Preview rows, column names, inferred data types and basic statistics.
   - Allow explicit column mapping where user column names differ from canonical names.
   - Reject unsupported file types and oversized files with understandable errors.

3. **Data validation**
   - Required-field checks, type checks, date parsing, null checks, numeric range checks.
   - Duplicate claim-ID checks.
   - Orphan-claim checks (claims not linked to an exposure record).
   - Coverage-period checks (claim service date outside coverage period).
   - Non-negative amount checks and arithmetic checks where incurred = paid + case reserve is supplied.
   - Reconciliation counts and amounts before/after exclusions.
   - Every exclusion must be counted and listed with a reason; never silently drop records.
   - Produce a downloadable validation report.

4. **Experience study**
   - Select analysis period and evaluation date.
   - Calculate total member months and member years.
   - Calculate claim count, incurred claims, frequency, average severity, claim cost PMPM and loss ratio when earned premium is available.
   - Segment results by product/plan, age band and region. Segmentation fields must be configurable; do not hard-code sensitive attributes as mandatory dimensions.
   - Show overall totals and segment results with clear denominators.
   - Flag low-exposure segments using a configurable minimum member-month threshold. This is a review flag, not a formal credibility method.

5. **Assumption and scenario management**
   - Save named assumption sets with version, effective period, owner, creation timestamp and notes/source.
   - Inputs for annual medical trend, fixed administration expense per member-month, variable expense percentage, commission percentage, target margin percentage, and experience-year weights.
   - Validate percentages and ensure the loading denominator remains positive.
   - Compare a base scenario with one or more alternative scenarios.
   - Keep prior scenario results immutable; a new assumption set creates a new run.

6. **Pricing indication**
   - Produce a preliminary indicated rate per member-month for each supported segment using the explicit method in `ACTUARIAL_METHODS.md`.
   - Show the full formula inputs and intermediate values.
   - Where current premium is available, show indicated rate change versus current rate.
   - Display warnings when a segment is low exposure, has missing premium, uses paid-only claims, or lacks sufficient historical periods.

7. **Reports and exports**
   - Export the validated data-quality report and experience/pricing results to XLSX and CSV.
   - Generate a concise HTML or PDF report containing period, filters, dataset fingerprint, method, assumptions, results, exclusions, limitations and run ID.
   - Never use the phrase “PSAK 117 compliant” or “OJK compliant” in generated reports.

8. **Reproducibility**
   - Store analysis run ID, source file names, file hashes, data schema mapping, calculation-method version, assumptions snapshot, filters, evaluation date, timestamp and output summary.
   - A previous run must remain reproducible after a later assumption change.

### P1 — only after P0 is verified

- Optional A/E comparison where the user explicitly provides expected claims or an expected-rate table.
- Simple claim development/lag diagnostics (not a full IBNR model).
- More flexible segment builder and comparison charts.
- Reviewer comments and approval status for assumption sets.
- A documented bootstrap or statistical uncertainty method only after an actuary reviews the methodology.

### P1 — compliance watch foundation (after the core experience/pricing workflow is stable)

- Maintain a curated registry of official OJK, PAI, IAI and IFRS Foundation sources.
- Allow a reviewer to manually refresh sources and inspect detected new/changed publications.
- Store publisher, document number/title, canonical URL, document hash, retrieval timestamp, publication date, effective date and lifecycle status separately.
- Distinguish consultation drafts, issued-but-not-effective documents, effective documents, amended/revoked documents and unknown status.
- Provide an inbox where an authorized reviewer can mark an item relevant, not relevant, or requiring actuarial/legal review, with rationale.
- Keep source snapshots and provenance. Every regulatory summary must link to the original publication.
- Do not automatically modify calculation formulas, pricing assumptions or reports when a source update is detected.

### Future compliance automation (not part of the first MVP release)

- Scheduled source polling, PDF/HTML extraction, section-level diffing and AI-assisted impact summaries.
- Human-reviewed, versioned rule/method packs with approval, effective dates, regression tests, staged activation and rollback.
- Customer-specific applicability profiles and notifications.

### Explicitly out of scope for MVP

- Full life mortality table graduation or life insurance pricing.
- Full morbidity model or diagnosis-level medical risk adjustment.
- GLM/ML models, predictive underwriting, individual member risk scores.
- Full IBNR / chain-ladder / Bornhuetter-Ferguson reserving.
- Technical reserve calculation and regulatory filing.
- PSAK 117 / IFRS 17 GMM, VFA, PAA accounting engine, CSM roll-forward, RA calibration, contract grouping, or accounting journals.
- PSAK 109 / IFRS 9 expected-credit-loss module.
- RBC / MMBR / ORSA capital calculation.
- Policy administration, claims-system or data-warehouse integrations.
- Production multi-tenant SaaS, payment/subscription billing, SSO or enterprise identity federation.
- Autonomous regulatory interpretation or automatic activation of calculation rules.
- A guarantee of legal/regulatory compliance based solely on detected publications.

## 6. Main user journey

1. User opens the demo workspace or creates a local workspace.
2. User uploads the exposure and claims files.
3. User maps source columns to canonical fields.
4. User runs validation and reviews every error/warning/exclusion.
5. User chooses study period, evaluation date and segmentation dimensions.
6. User runs the experience study.
7. User reviews overall and segment-level metrics and low-exposure warnings.
8. User creates an assumption set and runs a pricing indication scenario.
9. User compares scenarios and inspects the formula trace.
10. User exports the report and calculation workbook.

## 7. Canonical data schema

### Exposure file (one row per covered member-period or member coverage record)

Required:

- `exposure_id` — unique synthetic or pseudonymous exposure record ID.
- `member_ref` — pseudonymous member reference, never a real name or national ID.
- `group_ref` — employer/group identifier (can be synthetic).
- `plan_code` — product/benefit plan.
- `coverage_start` — coverage start date.
- `coverage_end` — coverage end date.
- `earned_member_months` — earned exposure in member-months.

Optional:

- `age_band` — pre-banded age category, not date of birth.
- `region` — coarse geographic category.
- `earned_premium` — premium earned for the exposure period.
- `current_rate_pmpm` — current price per member-month, if relevant.
- `currency` — ISO currency code; default in sample dataset is IDR.

### Claims file (one row per claim or claim line; the app must declare which grain is used)

Required:

- `claim_id` — unique claim identifier at the declared grain.
- `exposure_id` — link to exposure record.
- `service_date` — date service/risk event occurred.
- `paid_amount` — paid amount for the claim record.

Optional:

- `reported_date` — date claim was reported.
- `case_reserve` — outstanding case reserve.
- `incurred_amount` — supplied incurred amount. If absent and case reserve exists, calculate paid + case reserve; record this derivation.
- `claim_type` — broad synthetic category such as inpatient/outpatient; avoid diagnosis text.
- `currency` — currency code.

**Data grain warning:** If source claims have multiple line items per claim, the user must either provide a unique `claim_line_id` or aggregate them to claim level first. Do not count claim lines as separate claims by accident.

## 8. Key screens

1. Overview / Demo workspace.
2. Data Upload & Column Mapping.
3. Validation Results.
4. Study Setup.
5. Experience Study Results.
6. Assumption Sets & Scenario Builder.
7. Pricing Indication Results.
8. Run History & Report Downloads.

## 9. Non-functional requirements

- Local-only data processing by default; no external API calls or telemetry.
- Deterministic numerical calculations for fixed inputs.
- Clear errors, no silent coercion of invalid records.
- Responsive layout for laptop screens.
- All critical calculations unit-tested.
- Input and output files remain in user-controlled local storage in the prototype.
- No authentication requirement for the local demo, but make it explicit that the prototype is not safe for multi-user or production use.

## 10. Product success criteria

Technical acceptance:

- Synthetic sample files load successfully.
- Validation detects deliberately introduced invalid rows and shows exact reasons.
- The same input, configuration and code version produce identical results.
- Unit tests match independently computed fixture values.
- A report can be generated with complete data lineage and assumptions.

Discovery acceptance (before commercial positioning):

- At least 5 interviews with relevant actuarial practitioners or consultants.
- At least 3 interviewees confirm the same specific workflow pain, not merely that “automation is useful”.
- At least 2 practitioners are willing to test the prototype using synthetic or de-identified sample data.
- At least 1 reviewer with actuarial credentials reviews the calculation definitions before any external claim about actuarial validity.

These are proposed validation gates, not market facts.

## 11. Customer discovery questions

Do not ask anyone to share confidential policyholder or claims data.

1. Walk me through the last group-health experience study or renewal pricing exercise you completed.
2. What files/tables did you need, and what took the most time before analysis began?
3. How do you define exposure, incurred claims and claim count for that exercise?
4. How do you handle claim lag, case reserves, large claims, changes in benefit design and medical trend?
5. How do you choose or document experience-period weights and segment thresholds?
6. What output does the reviewer, product team or management expect?
7. What evidence is required to reproduce last period's result?
8. Which current tools are used (Excel, R, Python, SAS, Prophet, other)? What is hard about them?
9. Could a local-first tool that imports spreadsheets and produces traceable study workbooks be tested?
10. Who would evaluate, approve and pay for a tool like this?

## 12. Initial distribution / discovery strategy without an existing industry network

- Build a public demo using synthetic data and a short screen recording.
- Publish a clear technical note explaining the data schema and calculations; invite critique rather than claiming compliance.
- Identify public professional touchpoints: PAI public events/CPD, university actuarial programs and clubs, actuarial job posts, insurance conferences and publicly listed consulting practices.
- Contact people by role (pricing actuary, valuation actuary, actuarial consultant, head of actuarial), not by asking for confidential data.
- Offer a 20-minute workflow interview and a no-data prototype walkthrough.
- Track interview evidence and rejected hypotheses in a simple research log.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| No access to real portfolio data | Use reproducible synthetic data for engineering; seek a reviewer/design partner before validating actuarial assumptions. |
| Incorrect actuarial interpretation | Make calculations explicit, unit-test them, get an actuary to review methods, do not claim formal validity. |
| Regulatory requirements change | Version rules and source references; keep compliance modules out of MVP. |
| Confidentiality blocks SaaS adoption | Local-first prototype; later evaluate private cloud/on-prem deployments. |
| Too many user segments | Start only with group-health experience analysis and pricing indication. |
| Existing enterprise vendors | Compete initially on a small, inspectable workflow and ease of experimentation; validate buyer demand before claiming a market gap. |
