# M4.2 — Critical Reliability Fixes: Implementation Report

**Scope:** the four high-priority issues from [M4_1_ASSURANCE_REPORT.md](M4_1_ASSURANCE_REPORT.md)
(H1–H4). No new actuarial features. Medium-priority items are deliberately left in the backlog.
**Versions:** package `0.2.0`, method `method-0.2.0` (bumped because D6 and D12 behaviour changed).

This is a prototype. Nothing here is an actuarial opinion or a claim of actuarial, accounting or
regulatory compliance.

## Summary

| Issue | Root cause | Fix | Regression tests |
|---|---|---|---|
| H1 D6 exposure bias | Records partly outside the study period were silently dropped | Such studies are now **BLOCKED**. A labelled, non-production diagnostic compares conventions. The methodology stays unresolved | `tests/unit/test_m4_2_d6_safeguard.py` (14) |
| H2 Overview crash after upload | Overview summed `earned_member_months` from the mapped upload, which is text until validation parses it | Overview shows totals from validated, typed rows only. The validation cache is now keyed to the exact data objects | `tests/integration/test_m4_2_upload_pages.py` (6: CSV and XLSX) |
| H3 Silent current-rate fallback | `dropna().iloc[-1]` picked the latest period *that had* a rate | Uses the latest study period with 100% rate coverage only; otherwise `change_status = BLOCKED` with the missing input named | `tests/unit/test_m4_2_current_rate.py` (5) |
| H4 Historical reproducibility | Only hashes and settings were stored | Local content-addressed artifact store; manifest schema 2; integrity verification and recalculation kept separate | `tests/integration/test_m4_2_artifacts.py` (10) |

## H1 — D6 exposure-period safeguard

- `run_experience_study` raises `UnsupportedStudyPeriodError` (a `StudyConfigError` subclass) when
  any validated exposure record partly overlaps the study period. The error gives the record count,
  member-months and up to five example IDs, and names decision D6 and the pending actuarial
  approval.
- **Supported periods are unchanged and reproducible.** Records wholly inside are used; records
  wholly outside are excluded and counted. A regression test locks the calendar-aligned synthetic
  results to their pre-M4.2 values (41,581 member-months; 11,700 claims; IDR 6,001,647,600;
  loss ratio 0.8081). The full data span is always supported.
- **Diagnostic** (`studies/exposure_diagnostics.py`): `compare_exposure_conventions` (whole-record
  vs overlap-by-days candidate) and `boundary_records` (per-record overlap days and pro-rated
  member-months). It is labelled "DIAGNOSTIC — not an approved exposure methodology". A test checks
  that no production module imports it. The UI shows it only inside the BLOCKED message on the
  Experience study page.
- The tests cover: starting before, ending after, spanning, one-day touches at either boundary,
  exact-period and wholly-outside records, the audit's 2,251-record non-aligned synthetic window,
  and sub-period reconciliation of the candidate convention (halves add back to the whole).
- **Unresolved, requires actuarial approval:** whole-record vs overlap; day vs month basis;
  mid-month rule; premium earning. Recorded in `METHOD_DECISIONS.md` D6.

## H2 — Overview after real upload

- **Reproduced:** `ValueError: Unknown format code 'f' for object of type 'str'` at
  `overview.py:27`, with CSV and XLSX uploads alike.
- **Root cause:** uploads are deliberately read as text (no silent coercion), and Overview summed a
  raw text column. The fix takes the total from `get_validation()`, using the typed clean rows,
  labelled "Earned member-months (validated rows)". Structurally invalid files show a warning
  instead of a number.
- **Related robustness fix:** `get_validation()` now remembers which dataframe objects it validated
  and recomputes when they change. Before, a result computed by Overview could go stale if data was
  replaced without going through `set_dataset`. An existing test exposed this.
- **Display-only fix:** the pricing trace's transposed row is rendered as text, because the new
  status columns mix strings and numbers.
- The tests drive the real reader and mapping code with CSV and XLSX copies of the synthetic files
  through Overview, Data, Validation, Experience study, Assumptions & pricing, save, integrity check
  and recalculation. They also cover invalid-row uploads and a missing required column.

## H3 — Current rate

- Basis constant `CURRENT_RATE_BASIS = "latest_experience_period_full_coverage"`. It is stored on
  `PricingRun` and in every manifest.
- The study tables gain `current_rate_coverage`: the share of member-months with a positive current
  rate.
- In pricing, the comparison is **BLOCKED** with a reason when the latest study period:
  - has no exposure in the segment ("no exposure in latest experience period 2025"); or
  - has no rate ("current_rate_pmpm not supplied …"); or
  - has partial coverage ("current_rate_pmpm missing for 50.0% of member-months …").

  `current_rate_pmpm` and `indicated_change` are then N/A. The indicated rate does not depend on
  the current rate and is still produced.
- No user-selectable comparison basis was added; that would be new scope. The D12 interpretation
  stays open for practitioner and actuarial review.

## H4 — Reproducibility and persistence

**Storage design (local prototype):**
- `data/artifacts/objects/<sha[:2]>/<sha256>.<ext>` (gitignored). Each object's file name is its
  SHA-256, it is written once by atomic rename and set to read-only, and identical content is shared
  between runs.
- This gives tamper evidence, not access control or encryption. It is **not suitable for sensitive
  insurer data in production**, and the UI says so.

**Persisted per run (manifest schema 2):**

| Element | Where |
|---|---|
| Raw uploaded file bytes | `inputs.<kind>.raw_artifact` (`null` for synthetic data, with generator provenance recorded instead) |
| Mapped canonical input snapshot | `inputs.<kind>.mapped_artifact` (its hash equals `mapped_data_sha256`) |
| Column mapping, provenance | `inputs.<kind>.mapping`, `.provenance` |
| Cleaned exposure and claims tables | `artifacts.clean_exposures`, `artifacts.clean_claims` |
| Every row-level validation issue (excluded rows with reason codes) | `artifacts.validation_issues` |
| Validation tolerances | `validation_config` |
| Study config, assumption snapshot, current-rate basis | `study_config`, `assumptions`, `current_rate_basis` |
| Package, method version, git SHA (`-dirty` now covers all tracked files) | `code_version` |
| Python, platform, package versions, dependency fingerprint | `environment` |
| Result hashes | `results_fingerprint` |
| SHA-256 of `report.html`, `results.xlsx`, `pricing_results.csv` | `output_hashes` |
| Manifest | SQLite (immutable trigger) and `manifest.json`, which are the **same bytes** whose hash is stored |

**Three separate checks** (`reporting/manifest.py`, and three labelled buttons on Runs & reports):
1. `verify_run_integrity`: are the manifest (database and disk), input and derived snapshots and
   output files present and unaltered? Each item reports OK, MISSING, CORRUPTED or NOT STORED.
   There is no recalculation. Runs saved before M4.2 are reported as legacy.
2. `recalculate_run`: re-runs validation → study → pricing from the stored mapped snapshot with the
   **current** software, and compares the cleaned-data and result hashes. It reports whether the
   code commit and dependency fingerprint match the saved run. If they differ, the note says a
   match is **not** a re-execution of the historical environment.
3. `reproduce_run` (unchanged): compares against the data currently loaded in the workspace.

**Tests:**
- Manifest completeness.
- Integrity OK.
- **Reopening, integrity check and recalculation in a fresh Python process** via `subprocess`.
- Detection of a corrupted input artifact (recalculation refuses with `ArtifactError`).
- Missing derived artifact and missing output file.
- Tampered output file, `manifest.json` and forged database record.
- Software-change note.
- Legacy runs.
- Synthetic typed input recalculating identically from its text snapshot.
- Excluded-row details retrievable from the store.

**Not claimed:** cross-version execution reproducibility. The historical environment is
*recorded*, not archived. Re-running an old run on newer software can only show whether the
current software reproduces the stored numbers.

## Change to an existing test (disclosed)

`tests/unit/test_experience.py::_fixture` had exposure record E4 crossing the study-period end,
and one assertion expected it to be silently excluded. That was the biased behaviour H1 removes.
E4 (and its claim C5) was moved wholly after the period, so every other assertion runs unchanged.
That one assertion now checks `outside_study_period == 1` and `partially_outside_study_period == 0`.
Straddling records are covered by the new D6 tests. No other existing test was modified.

## Verification

| Check | Result |
|---|---|
| `python -m pytest` | **82 passed** (47 pre-existing + 35 new) |
| `ruff check .` / `ruff format --check .` | clean / 65 files formatted |
| App boot (`streamlit run app.py`) | HTTP 200 |
| Git | no history rewrite, no branches; one M4.2 commit authored by the repository owner only |

## Files changed

- **Engine:** `studies/segmentation.py`, `studies/exposure_diagnostics.py` (new),
  `pricing/scenario.py`, `reporting/manifest.py`, `reporting/export.py`,
  `persistence/artifacts.py` (new), `config.py`, `__init__.py`.
- **UI:** `app_pages/overview.py`, `experience_study.py`, `run_history.py`, `data_upload.py`,
  `assumptions_pricing.py` (display-only), `ui/state.py`.
- **Tests:** 4 new files, plus the fixture change above.
- **Docs:** this report, `METHOD_DECISIONS.md` (D6, D12 updated; D17–D18 added),
  `M5_READINESS_CHECKLIST.md`, `README.md`; also commits the M4.1 audit documents.
- **Config:** `.gitignore` (`data/artifacts/`), `pyproject.toml` version.

## Backlog (not part of M4.2, from M4.1 §10)

- M1: reversal, recovery and multi-line claims.
- M2: overlapping member cover; member-months below the cover span.
- M3: incurred < paid without a reserve column.
- M4: timestamps on last-day boundaries.
- M5: pre-filled assumption values.
- M6: elapsed-month suggestion vs year weights.
- M7: synthetic generator documentation, versioning and scenario set.
- M8 (remainder): trace and period×segment not hashed.
- M9: remaining undocumented conventions.
- Low items L1–L6.

## Outstanding actuarial decisions

D6 (partial exposure), D7 (evaluation date / as-of data), D8 (experience-period basis),
D2/D4/D18 (claim grain, reversals, zero-amount claims, incurred tolerance), D9/D12 (current-rate
basis), D13/D16 (weighting and trend timing), the loading-formula scope and the low-exposure
policy. See M4.1 §11.
