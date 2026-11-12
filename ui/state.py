"""Session-state helpers for the Streamlit UI (no calculation logic here)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from actuarybench.config import DB_PATH
from actuarybench.ingestion.validation import (
    ValidationResult,
    validate_claims_data,
    validate_exposure_data,
)
from actuarybench.synthetic import generate_synthetic_dataset
from actuarybench.utils.hashing import dataframe_fingerprint


@st.cache_data(show_spinner=False)
def load_synthetic() -> tuple[pd.DataFrame, pd.DataFrame]:
    ds = generate_synthetic_dataset()
    return ds.exposures, ds.claims


def init_state() -> None:
    """Load the synthetic demo workspace on first visit."""
    if "data_source" not in st.session_state:
        use_demo_workspace()


def use_demo_workspace() -> None:
    exposures, claims = load_synthetic()
    st.session_state.data_source = "synthetic"
    set_dataset("exposures", exposures.copy(), "synthetic_demo_exposures", None, None)
    set_dataset("claims", claims.copy(), "synthetic_demo_claims", None, None)


def set_dataset(
    kind: str,
    mapped: pd.DataFrame,
    filename: str,
    file_sha256: str | None,
    mapping: dict[str, str] | None,
) -> None:
    """Store a canonical-named dataset and its provenance; invalidates downstream results."""
    st.session_state[f"mapped_{kind}"] = mapped
    files = st.session_state.setdefault("source_files", {})
    files[kind] = {
        "filename": filename,
        "file_sha256": file_sha256 or "",
        "mapped_data_sha256": dataframe_fingerprint(mapped),
        "mapping": mapping or {c: c for c in mapped.columns},
    }
    for key in ("validation", "study_result", "pricing_runs"):
        st.session_state.pop(key, None)


def get_validation() -> tuple[ValidationResult, ValidationResult] | None:
    """Validate current datasets (memoised in session state until data changes)."""
    if "mapped_exposures" not in st.session_state or "mapped_claims" not in st.session_state:
        return None
    if "validation" not in st.session_state:
        ev = validate_exposure_data(st.session_state.mapped_exposures)
        cv = validate_claims_data(st.session_state.mapped_claims, ev)
        st.session_state.validation = (ev, cv)
    return st.session_state.validation


def synthetic_banner() -> None:
    if st.session_state.get("data_source") == "synthetic":
        st.info(
            "Synthetic demo data — not real insurer, member or claims data.",
            icon=":material/science:",
        )


def db_path() -> Path:
    """SQLite path; tests may override via session_state['db_path']."""
    return Path(st.session_state.get("db_path", DB_PATH))
