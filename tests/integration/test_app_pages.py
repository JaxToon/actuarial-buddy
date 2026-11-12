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
