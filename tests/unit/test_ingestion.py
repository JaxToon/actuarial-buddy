import io

import pandas as pd
import pytest

from actuarybench.ingestion.mapping import apply_mapping, suggest_mapping
from actuarybench.ingestion.readers import UploadError, read_table
from actuarybench.ingestion.validation import (
    validate_claims_data,
    validate_exposure_data,
)
from actuarybench.schemas.canonical import CLAIM_FIELDS, EXPOSURE_FIELDS
from actuarybench.synthetic import generate_invalid_fixture, generate_synthetic_dataset


def _csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode()


@pytest.fixture
def invalid():
    bad = generate_invalid_fixture()
    exp = read_table("e.csv", _csv_bytes(bad.exposures.drop(columns="_defect"))).data
    clm = read_table("c.csv", _csv_bytes(bad.claims.drop(columns="_defect"))).data
    ev = validate_exposure_data(exp)
    cv = validate_claims_data(clm, ev)
    return ev, cv


def _codes(result, record_id):
    i = result.issues
    return set(i.loc[(i["record_id"] == record_id) & (i["severity"] == "ERROR"), "code"])


def test_exposure_defects_detected(invalid):
    ev, _ = invalid
    assert ev.rows_in == 8
    assert sorted(ev.clean["exposure_id"]) == ["EXP1", "EXP2"]
    assert "coverage_end_before_start" in _codes(ev, "EXP3")
    assert "missing_plan_code" in _codes(ev, "EXP4")
    assert "negative_member_months" in _codes(ev, "EXP5")
    assert "duplicate_exposure_id" in _codes(ev, "EXP6")
    assert "invalid_coverage_start" in _codes(ev, "EXP7")
    reasons = ev.excluded_by_reason().set_index("code")["rows"]
    assert reasons["duplicate_exposure_id"] == 2


def test_claim_defects_detected(invalid):
    _, cv = invalid
    assert cv.rows_in == 10
    assert sorted(cv.clean["claim_id"]) == ["C1", "C3"]
    assert _codes(cv, "C2") == {"duplicate_claim_id"}
    assert _codes(cv, "C4") == {"orphan_claim"}
    assert _codes(cv, "C5") == {"service_outside_coverage"}
    assert "negative_paid" in _codes(cv, "C6")
    assert _codes(cv, "C7") == {"incurred_arithmetic_mismatch"}
    assert "missing_service_date" in _codes(cv, "C8")
    assert _codes(cv, "C9") == {"linked_exposure_excluded"}


def test_reconciliation_counts(invalid):
    _, cv = invalid
    rec = cv.reconciliation().set_index("measure")
    assert rec.loc["rows", "after"] == 2
    assert rec.loc["paid_amount", "after"] == 500_000 + 120_000
    assert rec.loc["rows", "excluded"] == 8


def test_clean_synthetic_has_no_errors():
    ds = generate_synthetic_dataset()
    ev = validate_exposure_data(ds.exposures)
    cv = validate_claims_data(ds.claims, ev)
    assert ev.rows_excluded == 0 and cv.rows_excluded == 0
    assert (ev.issues["severity"] == "ERROR").sum() == 0


def test_incurred_derivation_recorded():
    ds = generate_invalid_fixture()
    exp = ds.exposures.drop(columns="_defect").head(2)
    clm = ds.claims.drop(columns=["_defect", "incurred_amount"]).iloc[[0, 3]]
    cv = validate_claims_data(clm, validate_exposure_data(exp))
    assert cv.derivations
    assert list(cv.clean["incurred_amount"]) == [500_000.0, 150_000.0]


def test_missing_required_column_is_schema_error():
    ds = generate_synthetic_dataset()
    ev = validate_exposure_data(ds.exposures.drop(columns="earned_member_months"))
    assert not ev.ok and "earned_member_months" in ev.schema_errors[0]


def test_ambiguous_date_format_rejected():
    df = generate_invalid_fixture().exposures.drop(columns="_defect").head(1).astype(str)
    df["coverage_start"] = "01/02/2025"
    ev = validate_exposure_data(df)
    assert "invalid_coverage_start" in _codes(ev, "EXP1")


def test_reader_rejects_unsupported_and_empty():
    with pytest.raises(UploadError, match="Unsupported"):
        read_table("x.txt", b"a,b\n1,2")
    with pytest.raises(UploadError):
        read_table("x.csv", b"")


def test_reader_xlsx_roundtrip():
    buf = io.BytesIO()
    pd.DataFrame({"a": [1, 2]}).to_excel(buf, index=False)
    t = read_table("x.xlsx", buf.getvalue())
    assert list(t.data["a"]) == ["1", "2"] and len(t.sha256) == 64


def test_mapping_suggest_and_apply():
    df = pd.DataFrame(columns=["Claim No", "Exposure ID", "Date of Service", "Paid"])
    m = suggest_mapping(list(df.columns), CLAIM_FIELDS)
    assert m == {
        "claim_id": "Claim No",
        "exposure_id": "Exposure ID",
        "service_date": "Date of Service",
        "paid_amount": "Paid",
    }
    assert list(apply_mapping(df, m).columns) == list(m)
    with pytest.raises(ValueError):
        apply_mapping(df, {"claim_id": "Paid", "paid_amount": "Paid"})
    assert suggest_mapping(["exposure_id"], EXPOSURE_FIELDS) == {"exposure_id": "exposure_id"}
