"""Display formatting for metric tables (UI only; never used in calculations)."""

from __future__ import annotations

import pandas as pd

DISPLAY_NAMES = {
    "earned_member_months": "Member-months",
    "member_years": "Member-years",
    "claim_count": "Claims",
    "claim_amount": "Claim amount (IDR)",
    "earned_premium": "Earned premium (IDR)",
    "frequency_per_1000_my": "Freq / 1,000 MY",
    "average_severity": "Avg severity (IDR)",
    "claim_cost_pmpm": "Claim cost PMPM (IDR)",
    "loss_ratio": "Loss ratio",
    "current_rate_pmpm": "Current rate PMPM (IDR)",
    "flag": "Flag",
}


def format_metrics_table(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    out = df.drop(columns=["low_exposure"], errors="ignore").rename(columns=DISPLAY_NAMES)
    fmt = {c: "{:,.0f}" for c in out.columns if "IDR" in c or c in ("Member-months", "Claims")}
    fmt |= {"Member-years": "{:,.1f}", "Freq / 1,000 MY": "{:,.1f}", "Loss ratio": "{:.1%}"}
    fmt = {k: v for k, v in fmt.items() if k in out.columns}
    return out.style.format(fmt, na_rep="N/A")
