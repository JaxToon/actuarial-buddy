"""Session-state helpers for the Streamlit UI (no calculation logic here)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from actuarybench.synthetic import generate_synthetic_dataset


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
    st.session_state.raw_exposures = exposures.copy()
    st.session_state.raw_claims = claims.copy()
    st.session_state.source_files = {
        "exposures": "synthetic:generate_synthetic_dataset",
        "claims": "synthetic:generate_synthetic_dataset",
    }
