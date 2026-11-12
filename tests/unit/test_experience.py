from datetime import date

import pandas as pd
import pytest

from actuarybench.ingestion.validation import validate_claims_data, validate_exposure_data
from actuarybench.studies.metrics import compute_metrics
from actuarybench.studies.segmentation import (
    LOW_EXPOSURE_LABEL,
    StudyConfig,
    StudyConfigError,
    run_experience_study,
)
from actuarybench.synthetic import generate_synthetic_dataset


def test_example_a_metrics():
    m = compute_metrics(1_200, 24, 120_000_000, 150_000_000)
    assert m.member_years == pytest.approx(100)
    assert m.frequency_per_1000_my == pytest.approx(240)
    assert m.average_severity == pytest.approx(5_000_000)
    assert m.claim_cost_pmpm == pytest.approx(100_000)
    assert m.loss_ratio == pytest.approx(0.80)


def test_zero_claims_and_zero_denominators():
    m = compute_metrics(120, 0, 0, None)
    assert m.average_severity is None and m.claim_cost_pmpm == 0 and m.loss_ratio is None
    z = compute_metrics(0, 0, 0, 0)
    assert z.frequency_per_1000_my is None and z.claim_cost_pmpm is None and z.loss_ratio is None
    with pytest.raises(ValueError):
        compute_metrics(-1, 0, 0)


def _fixture():
    """Two plans. PLAN_A: 2 members x 12 mm in 2024, 3 claims (incurred 600k, paid 500k).
    PLAN_B: 1 member x 6 mm, no claims. One exposure straddles the study period."""
    e = pd.DataFrame(
        {
            "exposure_id": ["E1", "E2", "E3", "E4"],
            "member_ref": ["M1", "M2", "M3", "M4"],
            "group_ref": ["G1"] * 4,
            "plan_code": ["PLAN_A", "PLAN_A", "PLAN_B", "PLAN_B"],
            "coverage_start": ["2024-01-01", "2024-01-01", "2024-07-01", "2024-10-01"],
            "coverage_end": ["2024-12-31", "2024-12-31", "2024-12-31", "2025-03-31"],
            "earned_member_months": [12, 12, 6, 6],
            "earned_premium": [1_200_000, 1_200_000, 900_000, 900_000],
            "current_rate_pmpm": [100_000, 100_000, 150_000, 150_000],
        }
    )
    c = pd.DataFrame(
        {
            "claim_id": ["C1", "C2", "C3", "C4", "C5"],
            "exposure_id": ["E1", "E1", "E2", "E2", "E4"],
            "service_date": ["2024-02-01", "2024-03-01", "2024-04-01", "2024-12-20", "2024-11-01"],
            "reported_date": ["2024-02-10", "2024-03-10", "2024-04-10", "2025-02-15", "2024-11-05"],
            "paid_amount": [100_000, 200_000, 200_000, 50_000, 10_000],
            "case_reserve": [0, 0, 100_000, 0, 0],
            "incurred_amount": [100_000, 200_000, 300_000, 50_000, 10_000],
        }
    )
    ev = validate_exposure_data(e)
    cv = validate_claims_data(c, ev)
    assert ev.rows_excluded == 0 and cv.rows_excluded == 0
    return ev.clean, cv.clean


def _cfg(**kw):
    base = dict(
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        evaluation_date=date(2025, 1, 31),
        low_exposure_threshold_mm=12,
    )
    return StudyConfig(**{**base, **kw})


def test_fixture_incurred_by_plan():
    exp, clm = _fixture()
    r = run_experience_study(exp, clm, _cfg())
    a = r.by_segment.set_index("plan_code").loc["PLAN_A"]
    # C4 reported after evaluation date -> excluded. C1..C3: N=3, C=600k, E=24.
    assert a.earned_member_months == 24 and a.claim_count == 3 and a.claim_amount == 600_000
    assert a.frequency_per_1000_my == pytest.approx(3 / 2 * 1000)
    assert a.average_severity == pytest.approx(200_000)
    assert a.claim_cost_pmpm == pytest.approx(25_000)
    assert a.loss_ratio == pytest.approx(600_000 / 2_400_000)
    assert a.current_rate_pmpm == pytest.approx(100_000)
    b = r.by_segment.set_index("plan_code").loc["PLAN_B"]
    # E4 straddles period end -> excluded; E3 6 mm, no claims.
    assert b.earned_member_months == 6 and b.claim_count == 0
    assert pd.isna(b.average_severity) and b.claim_cost_pmpm == 0
    assert b.flag == LOW_EXPOSURE_LABEL and a.flag == ""
    ex = r.exclusions.set_index("reason")
    assert ex.loc["partially_outside_study_period", "rows"] == 1
    assert ex.loc["reported_after_evaluation_date", "rows"] == 1
    assert ex.loc["exposure_not_in_study", "rows"] == 1  # C5 on E4
    o = r.overall.iloc[0]
    assert o.earned_member_months == 30 and o.claim_count == 3


def test_fixture_paid_basis():
    exp, clm = _fixture()
    r = run_experience_study(exp, clm, _cfg(claim_basis="paid"))
    a = r.by_segment.set_index("plan_code").loc["PLAN_A"]
    assert a.claim_amount == 500_000
    assert any("Paid-claims experience" in w for w in r.warnings)


def test_incurred_basis_requires_incurred_column():
    exp, clm = _fixture()
    with pytest.raises(StudyConfigError):
        run_experience_study(exp, clm.drop(columns="incurred_amount"), _cfg())


def test_invalid_config():
    exp, clm = _fixture()
    with pytest.raises(StudyConfigError):
        run_experience_study(exp, clm, _cfg(period_end=date(2023, 1, 1)))
    with pytest.raises(StudyConfigError):
        run_experience_study(exp, clm, _cfg(segment_by=("gender",)))


def test_synthetic_study_reconciles_and_is_deterministic():
    ds = generate_synthetic_dataset()
    ev = validate_exposure_data(ds.exposures)
    cv = validate_claims_data(ds.claims, ev)
    cfg = _cfg(
        period_start=date(2023, 1, 1),
        period_end=date(2025, 12, 31),
        evaluation_date=date(2026, 3, 31),
        segment_by=("plan_code", "age_band"),
    )
    r1 = run_experience_study(ev.clean, cv.clean, cfg)
    r2 = run_experience_study(ev.clean, cv.clean, cfg)
    pd.testing.assert_frame_equal(r1.by_segment, r2.by_segment)
    o = r1.overall.iloc[0]
    assert r1.by_segment["earned_member_months"].sum() == pytest.approx(o.earned_member_months)
    assert r1.by_segment["claim_amount"].sum() == pytest.approx(o.claim_amount)
    assert r1.by_period["claim_count"].sum() == o.claim_count
    assert o.earned_member_months == ds.exposures["earned_member_months"].sum()
    assert sorted(r1.by_period["experience_period"]) == [2023, 2024, 2025]
