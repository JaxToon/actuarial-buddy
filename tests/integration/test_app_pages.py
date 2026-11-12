"""Smoke-run each Streamlit page with AppTest (synthetic demo workspace)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from actuarybench.synthetic import generate_invalid_fixture

APP = str(Path(__file__).resolve().parents[2] / "app.py")

PAGES = [
    "app_pages/overview.py",
    "app_pages/data_upload.py",
    "app_pages/validation.py",
    "app_pages/experience_study.py",
    "app_pages/assumptions_pricing.py",
    "app_pages/run_history.py",
]


def _app(page: str) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    at.switch_page(page)
    return at.run()


@pytest.mark.parametrize("page", PAGES)
def test_page_runs_without_exception(page):
    at = _app(page)
    assert not at.exception, at.exception


def test_validation_page_shows_invalid_fixture_exclusions():
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    bad = generate_invalid_fixture()
    at.session_state["mapped_exposures"] = bad.exposures.drop(columns="_defect").astype(str)
    at.session_state["mapped_claims"] = bad.claims.drop(columns="_defect").astype(str)
    at.session_state["data_source"] = "upload"
    at.switch_page("app_pages/validation.py")
    at.run()
    assert not at.exception, at.exception
    assert any("excluded" in w.value for w in at.warning)


def test_experience_study_runs_on_demo():
    at = _app("app_pages/experience_study.py")
    at.button[0].click()
    at.run()
    assert not at.exception, at.exception
    assert any(m.label == "Claim cost PMPM (IDR)" for m in at.metric)


def test_full_flow_study_assumptions_pricing(tmp_path):
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["db_path"] = str(tmp_path / "t.db")
    at.session_state["outputs_dir"] = str(tmp_path / "out")
    at.run()
    at.switch_page("app_pages/experience_study.py")
    at.run()
    at.button[0].click()
    at.run()
    at.switch_page("app_pages/assumptions_pricing.py")
    at.run()
    assert not at.exception, at.exception
    confirm = [c for c in at.checkbox if "equal weights" in c.label][0]
    confirm.check()
    save = [b for b in at.button if "Save new assumption" in b.label][0]
    save.click()
    at.run()
    assert not at.exception, at.exception
    assert any("Saved Base v1" in s.value for s in at.success), [e.value for e in at.error]
    run_btn = [b for b in at.button if "Run pricing" in b.label][0]
    run_btn.click()
    at.run()
    assert not at.exception, at.exception
    runs = at.session_state["pricing_runs"]
    assert len(runs) == 1 and runs[0].results["indicated_rate_pmpm"].notna().all()

    at.switch_page("app_pages/run_history.py")
    at.run()
    [b for b in at.button if "Save run" in b.label][0].click()
    at.run()
    assert not at.exception, at.exception
    assert any("Saved run" in s.value for s in at.success)
    [b for b in at.button if "Verify" in b.label][0].click()
    at.run()
    assert not at.exception, at.exception
    assert any("Reproduced" in s.value for s in at.success), [e.value for e in at.error]
