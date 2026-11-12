"""M4.2 Issue 2 — every page works on *uploaded* (text-typed) CSV and XLSX data."""

import io
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from actuarybench.ingestion.mapping import apply_mapping, suggest_mapping
from actuarybench.ingestion.readers import read_table
from actuarybench.schemas.canonical import CLAIM_FIELDS, EXPOSURE_FIELDS
from actuarybench.synthetic import generate_invalid_fixture
from actuarybench.utils.hashing import dataframe_fingerprint

ROOT = Path(__file__).resolve().parents[2]
APP = str(ROOT / "app.py")
SYN = ROOT / "data" / "synthetic"


def _xlsx(csv_path: Path) -> bytes:
    buf = io.BytesIO()
    pd.read_csv(csv_path, dtype=str).to_excel(buf, index=False)
    return buf.getvalue()


def _upload(name: str, content: bytes, fields) -> tuple[pd.DataFrame, dict]:
    table = read_table(name, content)
    mapping = suggest_mapping(list(table.data.columns), fields)
    mapped = apply_mapping(table.data, mapping)
    info = {
        "filename": name,
        "file_sha256": table.sha256,
        "mapped_data_sha256": dataframe_fingerprint(mapped),
        "mapping": mapping,
        "provenance": {"source": "upload"},
    }
    return mapped, info


def _app_with_upload(tmp_path, exp_file, clm_file) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=180)
    at.session_state["db_path"] = str(tmp_path / "t.db")
    at.session_state["outputs_dir"] = str(tmp_path / "out")
    at.run()
    (me, ie), (mc, ic) = (_upload(*exp_file, EXPOSURE_FIELDS), _upload(*clm_file, CLAIM_FIELDS))
    at.session_state["mapped_exposures"] = me
    at.session_state["mapped_claims"] = mc
    at.session_state["source_files"] = {"exposures": ie, "claims": ic}
    suffix = "." + exp_file[0].rsplit(".", 1)[-1]
    at.session_state["raw_upload_exposures"] = (suffix, exp_file[1])
    at.session_state["raw_upload_claims"] = (suffix, clm_file[1])
    at.session_state["data_source"] = "upload"
    at.run()
    return at


@pytest.fixture(scope="module", params=["csv", "xlsx"])
def demo_files(request):
    e, c = SYN / "demo_exposures.csv", SYN / "demo_claims.csv"
    if request.param == "csv":
        return ("exposures.csv", e.read_bytes()), ("claims.csv", c.read_bytes())
    return ("exposures.xlsx", _xlsx(e)), ("claims.xlsx", _xlsx(c))


def test_overview_after_upload_shows_validated_member_months(tmp_path, demo_files):
    at = _app_with_upload(tmp_path, *demo_files)
    assert not at.exception, at.exception
    m = {x.label: x.value for x in at.metric}
    assert m["Earned member-months (validated rows)"] == "41,581"
    assert m["Exposure records"] == "3,804"


def test_full_flow_on_uploaded_data(tmp_path, demo_files):
    at = _app_with_upload(tmp_path, *demo_files)
    for page in ("app_pages/data_upload.py", "app_pages/validation.py"):
        at.switch_page(page)
        at.run()
        assert not at.exception, (page, at.exception)
    at.switch_page("app_pages/experience_study.py")
    at.run()
    at.button[0].click()
    at.run()
    assert not at.exception, at.exception
    assert at.session_state["study_result"].overall.iloc[0].earned_member_months == 41_581
    at.switch_page("app_pages/assumptions_pricing.py")
    at.run()
    [c for c in at.checkbox if "equal weights" in c.label][0].check()
    [b for b in at.button if "Save new assumption" in b.label][0].click()
    at.run()
    [b for b in at.button if "Run pricing" in b.label][0].click()
    at.run()
    assert not at.exception, at.exception
    at.switch_page("app_pages/run_history.py")
    at.run()
    [b for b in at.button if "Save run" in b.label][0].click()
    at.run()
    assert not at.exception, at.exception
    assert any("Saved run" in s.value for s in at.success)
    [b for b in at.button if "Check artifact integrity" in b.label][0].click()
    at.run()
    assert any("Integrity verified" in s.value for s in at.success), [e.value for e in at.error]
    [b for b in at.button if "Recalculate" in b.label][0].click()
    at.run()
    assert any("match the saved run" in s.value for s in at.success), [e.value for e in at.error]


def test_overview_after_upload_with_invalid_rows(tmp_path):
    bad = generate_invalid_fixture()
    e = ("e.csv", bad.exposures.drop(columns="_defect").to_csv(index=False).encode())
    c = ("c.csv", bad.claims.drop(columns="_defect").to_csv(index=False).encode())
    at = _app_with_upload(tmp_path, e, c)
    assert not at.exception, at.exception
    m = {x.label: x.value for x in at.metric}
    assert m["Earned member-months (validated rows)"] == "24"  # EXP1 + EXP2


def test_overview_after_upload_missing_required_column(tmp_path):
    exp = pd.read_csv(SYN / "demo_exposures.csv", dtype=str).drop(columns="earned_member_months")
    e = ("e.csv", exp.to_csv(index=False).encode())
    c = ("c.csv", (SYN / "demo_claims.csv").read_bytes())
    at = _app_with_upload(tmp_path, e, c)
    assert not at.exception, at.exception
    assert any("not structurally valid" in w.value for w in at.warning)
