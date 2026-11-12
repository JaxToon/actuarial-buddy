# Architecture — ActuaryBench MVP

## 1. Build principle

Build a **local-first, single-user prototype** before adding enterprise SaaS infrastructure. This lets us test a real actuarial workflow without collecting sensitive customer data or spending the first development cycle on tenancy, billing, SSO and cloud operations.

The numerical engine must be independent of the UI and deterministic. It must not call an LLM or external API.

## 2. Recommended MVP stack

- Python 3.12+
- Streamlit for the initial interface
- Pandas for tabular transformations
- Pydantic for input/configuration validation
- Plotly for interactive charts
- SQLite for local run metadata and settings
- Local file storage for uploads and outputs
- OpenPyXL or XlsxWriter for Excel export
- ReportLab or HTML export for reports (choose one simple approach first)
- Pytest for unit/integration tests
- Ruff for linting and formatting

Avoid adding Celery, Redis, PostgreSQL, Docker, vector databases or LLM APIs to the first prototype unless an actual requirement appears.

## 3. Proposed repository structure

```text
actuarybench/
├── app.py
├── pages/
│   ├── 1_Data_Upload.py
│   ├── 2_Validation.py
│   ├── 3_Experience_Study.py
│   ├── 4_Assumptions_and_Pricing.py
│   └── 5_Run_History_and_Reports.py
├── src/
│   └── actuarybench/
│       ├── __init__.py
│       ├── config.py
│       ├── schemas/
│       │   ├── exposure.py
│       │   ├── claims.py
│       │   └── assumptions.py
│       ├── ingestion/
│       │   ├── readers.py
│       │   ├── mapping.py
│       │   └── validation.py
│       ├── studies/
│       │   ├── metrics.py
│       │   ├── segmentation.py
│       │   └── weighting.py
│       ├── pricing/
│       │   ├── trend.py
│       │   └── indication.py
│       ├── reporting/
│       │   ├── workbook.py
│       │   └── report.py
│       ├── persistence/
│       │   ├── database.py
│       │   └── repositories.py
│       └── utils/
│           ├── hashing.py
│           └── dates.py
├── data/
│   ├── synthetic/
│   ├── uploads/       # gitignored
│   └── outputs/       # gitignored
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
│   ├── PRD.md
│   ├── ACTUARIAL_METHODS.md
│   ├── ARCHITECTURE.md
│   └── RESEARCH_NOTES.md
├── .gitignore
├── requirements.txt
└── README.md
```

Claude Code may adjust the tree if there is a clear reason, but must keep calculation logic out of Streamlit page files.

## 4. Data and persistence

### MVP storage

- Save uploaded source files under a local `data/uploads/<workspace_id>/` folder.
- Save outputs under `data/outputs/<run_id>/`.
- Keep filenames, hashes, mappings, settings and run metadata in SQLite.
- Do not store direct personal identifiers.
- Add `data/uploads/`, `data/outputs/`, SQLite database files and `.env` to `.gitignore`.

### Future SaaS path (not MVP)

Only after workflow validation:

- FastAPI service boundary around the calculation package.
- PostgreSQL for workspace, tenant, users, assumptions, runs and approvals.
- S3-compatible encrypted object storage for source data and reports.
- OIDC/SSO and MFA, role-based permissions, tenant isolation tests.
- Managed secrets/KMS, key rotation, backups, retention/deletion controls, monitoring and security event logs.
- Dedicated/private cloud or on-prem deployment option for customers that cannot place claims/policy data in a shared SaaS environment.

Do not market the local Streamlit prototype as a secure multi-tenant SaaS.

## 5. Layering rules

1. **UI layer:** display controls and results only.
2. **Ingestion layer:** read files, map user columns and validate schema/data.
3. **Study layer:** calculate exposure, claims metrics and segments.
4. **Pricing layer:** calculate trend and rate indication from explicit assumptions.
5. **Reporting layer:** serialize the method, assumptions, validation and outputs.
6. **Persistence layer:** store run metadata and immutable calculation snapshots.

The engine must accept explicit dataframes/configuration and return structured results. It must not read Streamlit session state, environment variables or hidden global state.

## 6. Calculation contract

Suggested functions (exact names can vary):

```python
validate_exposure_data(df, mapping, config) -> ValidationResult
validate_claims_data(df, mapping, config) -> ValidationResult
calculate_experience_metrics(exposures, claims, study_config) -> ExperienceStudyResult
calculate_weighted_pure_premium(period_results, weights) -> WeightedExperienceResult
project_claim_cost(pure_premium, annual_trend, elapsed_months) -> TrendProjection
calculate_indicated_rate(projected_claim_cost, pricing_assumptions) -> PricingResult
build_run_manifest(inputs, mapping, assumptions, outputs, code_version) -> RunManifest
```

Use dataclasses or Pydantic models for return values; avoid loosely structured nested dictionaries where validation matters.

## 7. UX design direction

- Calm professional financial-workbench design; avoid consumer-fintech neon styling.
- Use clear status labels: Valid, Warning, Error, Low Exposure.
- Keep units visible: IDR, PMPM, member-months, member-years, %, claims per 1,000 member-years.
- Every chart must show selected period, denominator and segment definition.
- Every table must make the data grain clear.
- Show “Synthetic demo data” visibly in demo mode.
- Provide an explanation/tooltip for actuarial metrics in plain language.
- Do not show a single overall metric without its population/exposure denominator.

## 8. Future compliance-watch layer (not required for M0–M4)

Keep this as a bounded module separate from the calculation engine:

```text
src/actuarybench/compliance/
├── source_registry.py
├── polling.py
├── document_fetch.py
├── fingerprinting.py
├── extraction.py
├── lifecycle.py
├── change_detection.py
├── impact_analysis.py
├── review_workflow.py
└── rule_packs.py
```

- Initial prototype: curated source registry and manual refresh/review inbox; no autonomous crawler is required for the first release.
- Later SaaS service: scheduled polling and document processing can run as separate background jobs.
- Use official source pages from OJK, PAI, IAI and IFRS Foundation; use JDIH BPK for secondary metadata/status cross-checks.
- Preserve document snapshots, hashes, canonical source URLs and page/paragraph references.
- Model publication status and publication/effective dates as separate fields.
- AI may summarize and suggest impact; it must not edit calculation logic or activate a rule pack.
- Rule packs must be immutable, versioned, approved, effective-date aware and pinned to every applicable calculation run.
- A new publication must never silently change historical or future calculation outputs. Activation requires review, regression tests and an explicit release action.
- Respect source site terms, robots policies, access restrictions and document licensing; provide manual upload as a fallback.

## 9. Test strategy

- Unit tests for each numerical formula and edge condition.
- Data-quality tests with intentionally invalid rows.
- Integration test from sample CSV/XLSX upload to report export.
- Regression fixtures with fixed expected outputs.
- Determinism test: same file hashes + same config + same code version => same result values.
- Test zero claims, zero exposure, zero premium, duplicate IDs, orphan claims, out-of-period claims and invalid loading denominator.

## 10. Build milestones

### M0 — scaffold

Create project structure, dependencies, configuration, logging, sample synthetic data generator, README and test harness. App should start and display a demo workspace.

### M1 — ingestion and validation

CSV/XLSX upload, mapping, preview, validation summary and downloadable validation report. Do not add pricing yet.

### M2 — experience study

Core metrics, segment filters, denominator/claim-definition labels, low-exposure warnings, hand-checked unit fixtures.

### M3 — assumptions and pricing indication

Versioned assumption sets, explicit trend inputs, simple formula, scenario comparison and formula trace.

### M4 — reporting and run history

XLSX/PDF or HTML exports, immutable run manifest, run history and reproducibility verification.

### M5 — user testing

Walk through the demo with practitioners; collect comments; fix workflow and method definition before any SaaS/cloud work.

## 11. Definition of done

A milestone is done only when:

- user-visible workflow works end-to-end for that milestone;
- unit and integration tests pass;
- invalid inputs fail clearly;
- documentation is updated;
- no secrets or real customer data are committed;
- no unsupported regulatory or compliance claims appear in UI, code, sample reports or README.
