"""ActuaryBench Streamlit entry point. UI only — calculations live in src/actuarybench."""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import streamlit as st  # noqa: E402
from ui.state import init_state  # noqa: E402

st.set_page_config(page_title="ActuaryBench", page_icon=":material/monitoring:", layout="wide")
init_state()

page = st.navigation(
    [
        st.Page("app_pages/overview.py", title="Overview", icon=":material/home:", default=True),
        st.Page("app_pages/data_upload.py", title="Data", icon=":material/upload_file:"),
        st.Page("app_pages/validation.py", title="Validation", icon=":material/fact_check:"),
        st.Page(
            "app_pages/experience_study.py", title="Experience study", icon=":material/analytics:"
        ),
    ],
    position="top",
)

with st.sidebar:
    st.markdown("**ActuaryBench** · prototype")
    if st.session_state.get("data_source") == "synthetic":
        st.warning("Synthetic demo data", icon=":material/science:")
    st.caption(
        "Local, single-user prototype. Not a production or multi-user system, not a "
        "regulatory reporting tool, and not a substitute for a qualified actuary."
    )

page.run()
