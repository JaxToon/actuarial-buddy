import pandas as pd

import actuarybench
from actuarybench.synthetic import (
    CLAIMS_COLUMNS,
    EXPOSURE_COLUMNS,
    generate_invalid_fixture,
    generate_synthetic_dataset,
)
from actuarybench.utils.hashing import dataframe_fingerprint


def test_version():
    assert actuarybench.__version__


def test_synthetic_shape_and_integrity():
    ds = generate_synthetic_dataset()
    assert list(ds.exposures.columns) == EXPOSURE_COLUMNS
    assert list(ds.claims.columns) == CLAIMS_COLUMNS
    assert len(ds.exposures) > 1000 and len(ds.claims) > 1000
    assert ds.exposures["exposure_id"].is_unique
    assert ds.claims["claim_id"].is_unique
    assert ds.claims["exposure_id"].isin(ds.exposures["exposure_id"]).all()
    assert (ds.exposures["earned_member_months"] > 0).all()
    assert (ds.claims[["paid_amount", "case_reserve"]] >= 0).all().all()
    pd.testing.assert_series_equal(
        ds.claims["paid_amount"] + ds.claims["case_reserve"],
        ds.claims["incurred_amount"],
        check_names=False,
    )
    merged = ds.claims.merge(ds.exposures, on="exposure_id")
    assert (merged["service_date"] >= merged["coverage_start"]).all()
    assert (merged["service_date"] <= merged["coverage_end"]).all()


def test_synthetic_is_deterministic():
    a, b = generate_synthetic_dataset(), generate_synthetic_dataset()
    assert dataframe_fingerprint(a.claims) == dataframe_fingerprint(b.claims)
    assert dataframe_fingerprint(a.exposures) == dataframe_fingerprint(b.exposures)


def test_invalid_fixture_is_separate():
    bad = generate_invalid_fixture()
    assert "_defect" in bad.claims.columns
    assert (bad.claims["_defect"] != "valid").sum() >= 5
