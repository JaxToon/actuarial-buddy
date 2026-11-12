"""M4.2 Issue 1 — D6: study periods that cut through exposure records are blocked."""

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from actuarybench.ingestion.validation import validate_claims_data, validate_exposure_data
from actuarybench.studies.exposure_diagnostics import (
    boundary_records,
    compare_exposure_conventions,
)
from actuarybench.studies.segmentation import (
    StudyConfig,
    StudyConfigError,
    UnsupportedStudyPeriodError,
    run_experience_study,
)
from actuarybench.synthetic import generate_synthetic_dataset

SRC = Path(__file__).resolve().parents[2] / "src" / "actuarybench"


def _exp(start: str, end: str, mm: float = 12.0, eid: str = "E1") -> pd.DataFrame:
    e = pd.DataFrame(
        {
            "exposure_id": [eid],
            "member_ref": ["M"],
            "group_ref": ["G"],
            "plan_code": ["P"],
            "coverage_start": [start],
            "coverage_end": [end],
            "earned_member_months": [mm],
            "earned_premium": [mm * 100.0],
        }
    )
    return validate_exposure_data(e).clean


NO_CLAIMS = pd.DataFrame(
    {
        "claim_id": pd.Series(dtype="string"),
        "exposure_id": pd.Series(dtype="string"),
        "service_date": pd.Series(dtype="datetime64[ns]"),
        "reported_date": pd.Series(dtype="datetime64[ns]"),
        "paid_amount": pd.Series(dtype=float),
        "incurred_amount": pd.Series(dtype=float),
    }
)
CFG = StudyConfig(date(2024, 1, 1), date(2024, 12, 31), date(2025, 6, 30))


@pytest.mark.parametrize(
    "start,end",
    [
        ("2023-07-01", "2024-06-30"),  # starts before
        ("2024-07-01", "2025-06-30"),  # ends after
        ("2023-01-01", "2025-12-31"),  # spans the whole period
        ("2023-01-02", "2024-01-01"),  # touches start by one day
        ("2024-12-31", "2025-12-30"),  # touches end by one day
    ],
)
def test_straddling_record_blocks_study(start, end):
    with pytest.raises(UnsupportedStudyPeriodError) as exc:
        run_experience_study(_exp(start, end), NO_CLAIMS, CFG)
    assert exc.value.rows == 1 and exc.value.examples == ["E1"]
    assert "D6" in str(exc.value) and "actuarial approval" in str(exc.value)
    assert isinstance(exc.value, StudyConfigError)


@pytest.mark.parametrize(
    "start,end",
    [
        ("2024-01-01", "2024-12-31"),  # exactly the period (inclusive ends)
        ("2024-03-01", "2024-08-31"),  # inside
        ("2025-01-01", "2025-12-31"),  # wholly after -> excluded, not blocking
        ("2023-01-01", "2023-12-31"),  # wholly before
    ],
)
def test_supported_boundaries(start, end):
    r = run_experience_study(_exp(start, end), NO_CLAIMS, CFG)
    ex = r.exclusions.set_index("reason")
    assert ex.loc["partially_outside_study_period", "rows"] == 0


@pytest.fixture(scope="module")
def synthetic_clean():
    ds = generate_synthetic_dataset()
    ev = validate_exposure_data(ds.exposures)
    cv = validate_claims_data(ds.claims, ev)
    return ev.clean, cv.clean


def test_synthetic_non_aligned_period_is_blocked(synthetic_clean):
    exp, clm = synthetic_clean
    cfg = StudyConfig(date(2024, 4, 1), date(2025, 3, 31), date(2026, 3, 31))
    with pytest.raises(UnsupportedStudyPeriodError) as exc:
        run_experience_study(exp, clm, cfg)
    assert exc.value.rows == 2251  # audit M4.1 §4.2: records cut by this window


def test_supported_synthetic_period_unchanged(synthetic_clean):
    """Regression lock: calendar-aligned results are identical to pre-M4.2 values."""
    exp, clm = synthetic_clean
    cfg = StudyConfig(date(2023, 1, 1), date(2025, 12, 31), date(2026, 3, 31))
    o = run_experience_study(exp, clm, cfg).overall.iloc[0]
    assert o.earned_member_months == 41_581
    assert o.claim_count == 11_700
    assert o.claim_amount == pytest.approx(6_001_647_600)
    assert o.loss_ratio == pytest.approx(0.8081, abs=1e-4)


def test_diagnostic_boundary_fixture():
    rows = [
        ("A", "2024-03-01", "2024-08-31", 6),
        ("B", "2023-07-01", "2024-06-30", 12),
        ("C", "2024-07-01", "2025-06-30", 12),
        ("G", "2025-02-01", "2025-12-31", 11),
    ]
    exp = pd.concat([_exp(s, e, mm, i) for i, s, e, mm in rows], ignore_index=True)
    b = boundary_records(exp, date(2024, 1, 1), date(2024, 12, 31)).set_index("exposure_id")
    assert sorted(b.index) == ["B", "C"]
    assert b.loc["B", "overlap_days"] == 182 and b.loc["B", "coverage_days"] == 366
    assert b.loc["B", "pro_rated_member_months"] == pytest.approx(12 * 182 / 366)
    cmp = compare_exposure_conventions(exp, NO_CLAIMS, date(2024, 1, 1), date(2024, 12, 31))
    cmp = cmp.set_index("convention")
    assert cmp.loc["whole_record", "member_months"] == 6
    assert cmp.loc["overlap_days (candidate)", "member_months"] == pytest.approx(
        6 + 12 * 182 / 366 + 12 * 184 / 365
    )


def test_diagnostic_overlap_reconciles_across_subperiods(synthetic_clean):
    """Candidate convention: two halves add back to the whole (MM, claims, amount)."""
    exp, clm = synthetic_clean
    whole = compare_exposure_conventions(exp, clm, date(2023, 7, 1), date(2025, 6, 30))
    h1 = compare_exposure_conventions(exp, clm, date(2023, 7, 1), date(2024, 6, 30))
    h2 = compare_exposure_conventions(exp, clm, date(2024, 7, 1), date(2025, 6, 30))
    i = 1  # overlap_days row
    for col in ("member_months", "claim_count", "claim_amount"):
        assert h1.loc[i, col] + h2.loc[i, col] == pytest.approx(whole.loc[i, col])


def test_diagnostic_module_not_used_in_production_paths():
    for rel in (
        "studies/segmentation.py",
        "pricing/scenario.py",
        "reporting/manifest.py",
        "reporting/export.py",
        "reporting/report.py",
    ):
        text = (SRC / rel).read_text(encoding="utf-8")
        assert "import exposure_diagnostics" not in text, rel
        assert "exposure_diagnostics import" not in text, rel
