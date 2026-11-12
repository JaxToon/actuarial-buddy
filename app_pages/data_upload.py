"""Data upload & column mapping page."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from ui.state import set_dataset, synthetic_banner, use_demo_workspace

from actuarybench.config import MAX_UPLOAD_BYTES, SYNTHETIC_DIR
from actuarybench.ingestion.mapping import apply_mapping, suggest_mapping
from actuarybench.ingestion.readers import UploadError, list_sheets, read_table
from actuarybench.schemas.canonical import CLAIM_FIELDS, EXPOSURE_FIELDS

NOT_MAPPED = "— not mapped —"

st.header("Data upload & column mapping")
synthetic_banner()

with st.container(horizontal=True):
    if st.button("Use synthetic demo data", icon=":material/science:"):
        use_demo_workspace()
        st.rerun()
    st.download_button(
        "Download blank template (XLSX)",
        (SYNTHETIC_DIR / "template.xlsx").read_bytes(),
        file_name="actuarybench_template.xlsx",
        icon=":material/download:",
    )
    st.download_button(
        "Download sample exposures (CSV)",
        (SYNTHETIC_DIR / "demo_exposures.csv").read_bytes(),
        file_name="synthetic_exposures.csv",
        icon=":material/download:",
    )
    st.download_button(
        "Download sample claims (CSV)",
        (SYNTHETIC_DIR / "demo_claims.csv").read_bytes(),
        file_name="synthetic_claims.csv",
        icon=":material/download:",
    )

st.caption(
    f"CSV or XLSX, up to {MAX_UPLOAD_BYTES / 1e6:.0f} MB. Dates must be YYYY-MM-DD. "
    "Do not upload real names, national IDs, dates of birth or diagnosis text. Files are "
    "processed locally in memory."
)
st.warning(
    "Claims grain: one row per **claim**. If your source has several lines per claim, "
    "aggregate to claim level first so that lines are not counted as separate claims.",
    icon=":material/info:",
)


def column_profile(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "column": df.columns,
            "non_empty": [int(df[c].notna().sum()) for c in df.columns],
            "distinct": [int(df[c].nunique()) for c in df.columns],
            "looks_numeric": [
                bool(pd.to_numeric(df[c].dropna(), errors="coerce").notna().all())
                for c in df.columns
            ],
            "example": [df[c].dropna().iloc[0] if df[c].notna().any() else "" for c in df.columns],
        }
    )


def upload_block(kind: str, fields) -> None:
    up = st.file_uploader(f"{kind.capitalize()} file", type=["csv", "xlsx"], key=f"up_{kind}")
    if up is None:
        return
    content = up.getvalue()
    try:
        sheets = list_sheets(up.name, content)
        sheet = st.selectbox("Sheet", sheets, key=f"sheet_{kind}") if sheets else None
        table = read_table(up.name, content, sheet)
    except UploadError as exc:
        st.error(str(exc), icon=":material/error:")
        return
    raw = table.data
    st.caption(f"{len(raw):,} rows · {len(raw.columns)} columns · SHA-256 `{table.sha256[:16]}…`")
    with st.expander("Preview & column profile"):
        st.dataframe(raw.head(20), hide_index=True)
        st.dataframe(column_profile(raw), hide_index=True)

    suggested = suggest_mapping(list(raw.columns), fields)
    options = [NOT_MAPPED, *raw.columns]
    mapping: dict[str, str] = {}
    with st.form(f"map_{kind}"):
        st.markdown("**Map source columns to canonical fields**")
        cols = st.columns(3)
        for i, f in enumerate(fields):
            default = suggested.get(f.name, NOT_MAPPED)
            choice = cols[i % 3].selectbox(
                f.name + (" *" if f.required else ""),
                options,
                index=options.index(default),
                help=f.description,
                key=f"map_{kind}_{f.name}",
            )
            if choice != NOT_MAPPED:
                mapping[f.name] = choice
        submitted = st.form_submit_button("Apply mapping", type="primary")
    if submitted:
        missing = [f.name for f in fields if f.required and f.name not in mapping]
        if missing:
            st.error(f"Required fields not mapped: {', '.join(missing)}")
            return
        try:
            mapped = apply_mapping(raw, mapping)
        except ValueError as exc:
            st.error(str(exc))
            return
        set_dataset(kind, mapped, up.name, table.sha256, mapping)
        st.session_state.data_source = "upload"
        st.success(f"{kind.capitalize()} mapped. Continue to Validation.", icon=":material/check:")


left, right = st.columns(2)
with left, st.container(border=True):
    st.subheader("Exposures")
    upload_block("exposures", EXPOSURE_FIELDS)
with right, st.container(border=True):
    st.subheader("Claims")
    upload_block("claims", CLAIM_FIELDS)

st.subheader("Current workspace datasets")
files = st.session_state.get("source_files", {})
st.dataframe(
    pd.DataFrame(
        [
            {
                "dataset": k,
                "source": v["filename"],
                "file_sha256": v["file_sha256"][:16],
                "rows": len(st.session_state.get(f"mapped_{k}", [])),
            }
            for k, v in files.items()
        ]
    ),
    hide_index=True,
)
