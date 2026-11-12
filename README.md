# ActuaryBench

Local-first prototype workbench for **group-health experience studies and preliminary pricing
indications**: data import → validation → experience study → assumptions & scenarios → pricing
indication → reproducible report.

> **Prototype.** Not a production actuarial system, not a regulatory reporting or
> insurance-contract accounting tool, and not a substitute for review by a qualified actuary.
> The demo uses **synthetic data only**. Outputs are preliminary indications, not filed tariffs,
> quotes or binding premiums.

## Run locally

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens in a synthetic demo workspace. Python 3.11+.

```bash
python -m pytest            # unit + integration tests (incl. Streamlit AppTest page runs)
ruff check . && ruff format --check .
python scripts/generate_synthetic_data.py   # regenerate data/synthetic/*
```

## Workflow (app pages)

| Page | What it does |
|---|---|
| Overview | Demo workspace, scope and limitations |
| Data | Upload CSV/XLSX, preview + column profile, explicit column mapping, templates |
| Validation | Row-level errors/warnings with reason codes, reconciliation before/after exclusions, XLSX/CSV report |
| Experience study | Study period, evaluation date, claim basis (incurred/paid), configurable segments, low-exposure flags; member-months, frequency per 1,000 MY, severity, PMPM, loss ratio by segment and period |
| Assumptions & pricing | Immutable versioned assumption sets; year- or exposure-weighted PP; trend; indicated rate PMPM with formula trace; scenario comparison |
| Runs & reports | Save run → HTML report, results XLSX/CSV, JSON manifest (SQLite); run history; reproducibility verification |

## Project layout

```text
app.py                     Streamlit entry (st.navigation)
app_pages/                 UI pages only — no calculations
ui/                        UI helpers (session state, formatting)
src/actuarybench/
  schemas/                 canonical fields, AssumptionSet (pydantic)
  ingestion/               readers, mapping, validation
  studies/                 metrics, segmentation (experience study), weighting
  pricing/                 trend, indication, scenario runner
  reporting/               workbook, HTML report, manifest/reproduce, export
  persistence/             SQLite (immutable assumption sets and runs)
  synthetic.py             deterministic synthetic data + invalid fixture
data/synthetic/            generated demo data & template (committed)
data/uploads, data/outputs gitignored
docs/                      PRD, methods, architecture, method decisions log
tests/                     unit/ and integration/
```

## Methods

Formulas follow [docs/ACTUARIAL_METHODS.md](docs/ACTUARIAL_METHODS.md). Implementation choices
where the spec was silent are logged in [docs/METHOD_DECISIONS.md](docs/METHOD_DECISIONS.md) and
need actuarial review.

## Status

Milestones M0–M4 from [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) are implemented, followed by the
M4.1 assurance audit ([report](docs/M4_1_ASSURANCE_REPORT.md)) and the M4.2 reliability fixes
([report](docs/M4_2_IMPLEMENTATION_REPORT.md)). Next: M5 practitioner walkthroughs; see
[docs/M5_READINESS_CHECKLIST.md](docs/M5_READINESS_CHECKLIST.md). Compliance Watch
([docs/COMPLIANCE_AUTOMATION.md](docs/COMPLIANCE_AUTOMATION.md)) is deliberately not started.

### Known limitations

- Single-user, local prototype. The run artifact store (`data/artifacts/`) is tamper-evident but not
  access-controlled or encrypted, so it is not for sensitive insurer data.
- Study periods that cut through any coverage record are **blocked**: the partial-exposure
  convention (D6) awaits actuarial approval. The full data span is always supported.
- The rate-change comparison is blocked when the latest period's current rate is missing or partial
  (D12 basis pending review).
- Claims must be at claim grain; reversals and recoveries are rejected (backlog).
- No IBNR/development, pooling or credibility; A/E comparison (P1) is not implemented.
- Recalculation uses the installed software. Cross-version execution reproducibility is not
  claimed; the historical environment is recorded, not archived.

Outstanding actuarial decisions are listed in [docs/METHOD_DECISIONS.md](docs/METHOD_DECISIONS.md)
and the M4.1 report §11.
