from datetime import date

import pandas as pd
import pytest
from pydantic import ValidationError

from actuarybench.persistence.repositories import AssumptionRepository, DuplicateVersionError
from actuarybench.pricing.indication import PricingError, calculate_indicated_rate
from actuarybench.pricing.scenario import BLOCKED, OK, compare_scenarios, run_pricing
from actuarybench.pricing.trend import TrendError, project_claim_cost, suggest_elapsed_months
from actuarybench.schemas.assumptions import AssumptionSet
from actuarybench.studies.segmentation import StudyConfig, run_experience_study
from actuarybench.studies.weighting import WeightingError, calculate_weighted_pure_premium


def test_example_b_trend_and_rate():
    tp = project_claim_cost(100_000, 0.10, 12)
    assert tp.trend_factor == pytest.approx(1.10)
    assert tp.projected_pure_premium == pytest.approx(110_000)
    pr = calculate_indicated_rate(tp.projected_pure_premium, 5_000, 0.10, 0.05, 0.05, 125_000)
    assert pr.loading_denominator == pytest.approx(0.80)
    assert pr.indicated_rate_pmpm == pytest.approx(143_750)
    assert pr.indicated_change == pytest.approx(143_750 / 125_000 - 1)


@pytest.mark.parametrize("v,c,m", [(0.5, 0.3, 0.2), (0.6, 0.3, 0.2)])
def test_example_c_invalid_loading_blocks(v, c, m):
    with pytest.raises(PricingError, match="denominator"):
        calculate_indicated_rate(100_000, 5_000, v, c, m)


def test_rate_input_guards():
    with pytest.raises(PricingError):
        calculate_indicated_rate(100_000, 0, 1.0, 0, 0)
    with pytest.raises(PricingError):
        calculate_indicated_rate(float("inf"), 0, 0.1, 0, 0)
    assert calculate_indicated_rate(100, 0, 0, 0, 0, current_rate_pmpm=0).indicated_change is None
    with pytest.raises(TrendError):
        project_claim_cost(100, -1.0, 12)
    with pytest.raises(TrendError):
        project_claim_cost(100, 0.1, -1)


def test_fractional_trend_period():
    assert project_claim_cost(100, 0.21, 6).trend_factor == pytest.approx(1.1)


def test_suggest_elapsed_months():
    m = suggest_elapsed_months(
        date(2023, 1, 1), date(2025, 12, 31), date(2027, 1, 1), date(2027, 12, 31)
    )
    assert m == pytest.approx(36, abs=0.1)


PERIODS = pd.DataFrame(
    {
        "experience_period": [2023, 2024, 2025],
        "earned_member_months": [1_000, 1_200, 800],
        "claim_amount": [90_000_000, 120_000_000, 88_000_000],
    }
)


def test_year_weighted_pp():
    # PP = 90k, 100k, 110k; weights .2/.3/.5 -> 18k + 30k + 55k = 103k
    w = calculate_weighted_pure_premium(PERIODS, "year_weighted", {2023: 0.2, 2024: 0.3, 2025: 0.5})
    assert w.weighted_pure_premium == pytest.approx(103_000)
    assert list(w.periods["pure_premium"]) == pytest.approx([90_000, 100_000, 110_000])


def test_exposure_weighted_pp():
    w = calculate_weighted_pure_premium(PERIODS, "exposure_weighted")
    assert w.weighted_pure_premium == pytest.approx(298_000_000 / 3_000)


def test_weighting_guards():
    with pytest.raises(WeightingError, match="sum to 1"):
        calculate_weighted_pure_premium(PERIODS, "year_weighted", {2023: 0.5, 2024: 0.4})
    with pytest.raises(WeightingError, match="no exposure"):
        calculate_weighted_pure_premium(PERIODS, "year_weighted", {2022: 0.5, 2025: 0.5})
    zero = PERIODS.assign(earned_member_months=[0, 1_200, 800])
    with pytest.raises(WeightingError, match="no exposure"):
        calculate_weighted_pure_premium(zero, "year_weighted", {2023: 0.2, 2024: 0.3, 2025: 0.5})
    # zero weight on an empty period is allowed
    w = calculate_weighted_pure_premium(zero, "year_weighted", {2023: 0, 2024: 0.5, 2025: 0.5})
    assert w.weighted_pure_premium == pytest.approx(105_000)


def _assumptions(**kw) -> AssumptionSet:
    base = dict(
        name="Base",
        version=1,
        owner="analyst",
        effective_from=date(2026, 1, 1),
        annual_trend=0.10,
        trend_source="illustrative test",
        elapsed_months=12,
        fixed_expense_pmpm=5_000,
        variable_expense_pct=0.10,
        commission_pct=0.05,
        target_margin_pct=0.05,
        weighting_method="year_weighted",
        period_weights={2024: 1.0},
    )
    return AssumptionSet(**{**base, **kw})


def test_assumption_validation():
    with pytest.raises(ValidationError, match="below 100%"):
        _assumptions(variable_expense_pct=0.5, commission_pct=0.3, target_margin_pct=0.2)
    with pytest.raises(ValidationError, match="sum to 1"):
        _assumptions(period_weights={2024: 0.5})
    with pytest.raises(ValidationError, match="illustrative"):
        _assumptions(annual_trend=0.0, trend_source="")
    assert _assumptions(annual_trend=0.0, trend_source="", trend_is_illustrative=True)
    with pytest.raises(ValidationError):
        _assumptions(commission_pct=1.2)


def _study():
    e = pd.DataFrame(
        {
            "exposure_id": ["E1", "E2", "E3"],
            "plan_code": ["A", "A", "B"],
            "coverage_start": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-01"]),
            "coverage_end": pd.to_datetime(["2024-12-31", "2024-12-31", "2024-12-31"]),
            "earned_member_months": [600.0, 600.0, 0.0],
            "earned_premium": [60e6, 60e6, 0.0],
            "current_rate_pmpm": [125_000.0, 125_000.0, None],
        }
    )
    c = pd.DataFrame(
        {
            "claim_id": ["C1", "C2"],
            "exposure_id": ["E1", "E2"],
            "service_date": pd.to_datetime(["2024-03-01", "2024-06-01"]),
            "reported_date": pd.to_datetime(["2024-03-05", "2024-06-05"]),
            "paid_amount": [60e6, 60e6],
            "incurred_amount": [60e6, 60e6],
        }
    )
    cfg = StudyConfig(
        date(2024, 1, 1),
        date(2024, 12, 31),
        date(2025, 6, 30),
        segment_by=("plan_code",),
        low_exposure_threshold_mm=100,
    )
    return run_experience_study(e, c, cfg)


def test_run_pricing_trace_matches_example_b():
    run = run_pricing(_study(), _assumptions())
    r = run.results.set_index("segment")
    a = r.loc["plan_code=A"]
    # PP = 120m / 1200 = 100k -> Example B -> 143,750
    assert a.status == OK
    assert a.weighted_pure_premium == pytest.approx(100_000)
    assert a.indicated_rate_pmpm == pytest.approx(143_750)
    assert a.indicated_change == pytest.approx(0.15)
    b = r.loc["plan_code=B"]
    assert b.status == BLOCKED and "no exposure" in b.blocked_reason
    assert pd.isna(b.indicated_rate_pmpm)
    assert "LOW EXPOSURE" in b.warnings
    assert r.loc["ALL"].indicated_rate_pmpm == pytest.approx(143_750)
    assert set(run.trace["segment"]) == {"ALL", "plan_code=A", "plan_code=B"}


def test_compare_scenarios():
    s = _study()
    base = run_pricing(s, _assumptions())
    alt = run_pricing(s, _assumptions(name="High trend", annual_trend=0.21, elapsed_months=12))
    cmp = compare_scenarios([base, alt]).set_index("segment")
    assert cmp.loc["ALL", "High trend v1"] == pytest.approx((121_000 + 5_000) / 0.8)
    assert cmp.loc["ALL", "High trend v1 vs Base v1"] == pytest.approx(126_000 / 115_000 - 1)


def test_assumption_repository(tmp_path):
    repo = AssumptionRepository(tmp_path / "t.db")
    a = _assumptions()
    repo.save(a)
    assert repo.next_version("Base") == 2
    with pytest.raises(DuplicateVersionError):
        repo.save(a)
    assert repo.get("Base", 1) == a
    assert [x.label for x in repo.list()] == ["Base v1"]
