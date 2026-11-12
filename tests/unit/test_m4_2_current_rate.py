"""M4.2 Issue 3 — no implicit current-rate substitution (D12)."""

from datetime import date

import pandas as pd
import pytest

from actuarybench.pricing.scenario import BLOCKED, CURRENT_RATE_BASIS, OK, run_pricing
from actuarybench.schemas.assumptions import AssumptionSet
from actuarybench.studies.segmentation import StudyConfig, run_experience_study

A = AssumptionSet(
    name="T",
    version=1,
    owner="o",
    effective_from=date(2026, 1, 1),
    annual_trend=0.0,
    trend_is_illustrative=True,
    elapsed_months=0,
    fixed_expense_pmpm=0,
    variable_expense_pct=0.2,
    commission_pct=0,
    target_margin_pct=0,
    period_weights={2023: 0.5, 2024: 0.5},
)


def _study(rates_2023, rates_2024, mm_2024=(12.0, 12.0)):
    """Plan P, two members, two years; PP = 100,000 each year -> indicated 125,000."""
    rows = []
    for year, rates, mms in ((2023, rates_2023, (12.0, 12.0)), (2024, rates_2024, mm_2024)):
        for i, (r, mm) in enumerate(zip(rates, mms, strict=True)):
            rows.append(
                {
                    "exposure_id": f"E{year}{i}",
                    "plan_code": "P",
                    "coverage_start": pd.Timestamp(f"{year}-01-01"),
                    "coverage_end": pd.Timestamp(f"{year}-12-31"),
                    "earned_member_months": mm,
                    "earned_premium": 1.0e6,
                    "current_rate_pmpm": r,
                }
            )
    e = pd.DataFrame(rows)
    c = pd.DataFrame(
        {
            "claim_id": ["C1", "C2"],
            "exposure_id": ["E20230", "E20240" if mm_2024[0] > 0 else "E20241"],
            "service_date": pd.to_datetime(["2023-06-01", "2024-06-01"]),
            "reported_date": pd.to_datetime(["2023-06-02", "2024-06-02"]),
            "paid_amount": [2.4e6, 2.4e6 * sum(mm_2024) / 24],
            "incurred_amount": [2.4e6, 2.4e6 * sum(mm_2024) / 24],
        }
    )
    cfg = StudyConfig(
        date(2023, 1, 1), date(2024, 12, 31), date(2025, 6, 30), segment_by=("plan_code",)
    )
    return run_experience_study(e, c, cfg)


def _row(study, seg="plan_code=P"):
    return run_pricing(study, A).results.set_index("segment").loc[seg]


def test_full_latest_rate_used():
    r = _row(_study([90_000.0, 90_000.0], [100_000.0, 100_000.0]))
    assert r.change_status == OK and r.change_blocked_reason == ""
    assert r.current_rate_pmpm == 100_000
    assert r.indicated_rate_pmpm == pytest.approx(125_000)
    assert r.indicated_change == pytest.approx(0.25)


def test_missing_latest_rate_blocks_change_no_fallback():
    r = _row(_study([90_000.0, 90_000.0], [None, None]))
    assert r.change_status == BLOCKED
    assert "current_rate_pmpm not supplied" in r.change_blocked_reason
    assert "2024" in r.change_blocked_reason
    assert pd.isna(r.current_rate_pmpm) and pd.isna(r.indicated_change)
    assert r.current_rate_pmpm != 90_000  # the 2023 rate must never be substituted
    assert r.status == OK and r.indicated_rate_pmpm == pytest.approx(125_000)


def test_partial_latest_rate_blocks_change():
    r = _row(_study([90_000.0, 90_000.0], [100_000.0, None]))
    assert r.change_status == BLOCKED
    assert "missing for 50.0% of member-months" in r.change_blocked_reason
    assert pd.isna(r.current_rate_pmpm)


def test_overall_row_also_blocked():
    r = _row(_study([90_000.0, 90_000.0], [100_000.0, None]), seg="ALL")
    assert r.change_status == BLOCKED and pd.isna(r.indicated_change)


def test_basis_recorded():
    run = run_pricing(_study([1.0, 1.0], [1.0, 1.0]), A)
    assert run.current_rate_basis == CURRENT_RATE_BASIS
    assert {"change_status", "change_blocked_reason"} <= set(run.results.columns)
