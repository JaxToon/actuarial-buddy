"""Session-state helpers for the Streamlit UI (no calculation logic here)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from actuarybench import __version__
from actuarybench.config import ARTIFACTS_DIR, DB_PATH, DEFAULT_SEED, OUTPUTS_DIR
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
    prov = {
        "generator": "actuarybench.synthetic.generate_synthetic_dataset",
        "seed": DEFAULT_SEED,
        "package_version": __version__,
        "synthetic": True,
    }
    set_dataset(
        "exposures", exposures.copy(), "synthetic_demo_exposures", None, None, provenance=prov
    )
    set_dataset("claims", claims.copy(), "synthetic_demo_claims", None, None, provenance=prov)


def set_dataset(
    kind: str,
    mapped: pd.DataFrame,
    filename: str,
    file_sha256: str | None,
    mapping: dict[str, str] | None,
    raw_upload: tuple[str, bytes] | None = None,
    provenance: dict | None = None,
) -> None:
    """Store a canonical-named dataset and its provenance; invalidates downstream results.

    ``raw_upload`` = (file suffix, original bytes) is kept in session so a saved run can
    snapshot the exact uploaded file.
    """
    st.session_state[f"mapped_{kind}"] = mapped
    st.session_state[f"raw_upload_{kind}"] = raw_upload
    files = st.session_state.setdefault("source_files", {})
    files[kind] = {
        "filename": filename,
        "file_sha256": file_sha256 or "",
        "mapped_data_sha256": dataframe_fingerprint(mapped),
        "mapping": mapping or {c: c for c in mapped.columns},
        "provenance": provenance or {"source": "upload"},
    }
    for key in ("validation", "study_result", "pricing_runs"):
        st.session_state.pop(key, None)


def get_validation() -> tuple[ValidationResult, ValidationResult] | None:
    """Validate current datasets, memoised until the dataset objects change.

    The cache remembers the exact dataframe objects it validated (identity comparison), so a
    stale result is never returned when data is replaced (via ``set_dataset`` or directly).
    """
    if "mapped_exposures" not in st.session_state or "mapped_claims" not in st.session_state:
        return None
    exp, clm = st.session_state.mapped_exposures, st.session_state.mapped_claims
    src = st.session_state.get("validation_source")
    if (
        "validation" not in st.session_state
        or src is None
        or src[0] is not exp
        or src[1] is not clm
    ):
        ev = validate_exposure_data(exp)
        cv = validate_claims_data(clm, ev)
        st.session_state.validation = (ev, cv)
        st.session_state.validation_source = (exp, clm)
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


def outputs_dir() -> Path:
    return Path(st.session_state.get("outputs_dir", OUTPUTS_DIR))


def artifacts_dir() -> Path:
    """Defaults next to the outputs folder so tests overriding outputs_dir stay isolated."""
    if "artifacts_dir" in st.session_state:
        return Path(st.session_state["artifacts_dir"])
    if "outputs_dir" in st.session_state:
        return Path(st.session_state["outputs_dir"]).parent / "artifacts"
    return ARTIFACTS_DIR
