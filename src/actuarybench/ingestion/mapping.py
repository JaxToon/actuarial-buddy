"""Explicit column mapping from user source columns to canonical field names."""

from __future__ import annotations

import re

import pandas as pd

from actuarybench.schemas.canonical import FieldSpec

# Common alternative spellings; only used to *suggest* a mapping the user then confirms.
_ALIASES: dict[str, tuple[str, ...]] = {
    "exposure_id": ("exposureid", "exp_id", "record_id"),
    "member_ref": ("member_id", "memberid", "member", "insured_ref"),
    "group_ref": ("group_id", "groupid", "employer", "policy_holder", "group"),
    "plan_code": ("plan", "product", "benefit_plan", "plan_id"),
    "coverage_start": ("start_date", "effective_date", "cov_start"),
    "coverage_end": ("end_date", "expiry_date", "cov_end"),
    "earned_member_months": ("member_months", "mm", "exposure_months", "earned_mm"),
    "earned_premium": ("premium", "earned_prem"),
    "current_rate_pmpm": ("rate_pmpm", "current_rate", "pmpm_rate"),
    "claim_id": ("claimid", "claim_no", "claim_number"),
    "service_date": ("incurred_date", "date_of_service", "loss_date", "dos"),
    "reported_date": ("report_date", "notification_date"),
    "paid_amount": ("paid", "amount_paid", "paid_amt"),
    "case_reserve": ("outstanding", "os_reserve", "reserve"),
    "incurred_amount": ("incurred", "incurred_amt"),
    "claim_type": ("benefit_type", "type"),
}


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def suggest_mapping(source_columns: list[str], fields: tuple[FieldSpec, ...]) -> dict[str, str]:
    """Suggest {canonical_field: source_column}. Exact (normalised) matches win over aliases.
    Each source column is used at most once. Unmatched fields are omitted."""
    normed = {_norm(c): c for c in source_columns}
    used: set[str] = set()
    out: dict[str, str] = {}
    for f in fields:
        candidates = [f.name, *_ALIASES.get(f.name, ())]
        for cand in candidates:
            src = normed.get(_norm(cand))
            if src is not None and src not in used:
                out[f.name] = src
                used.add(src)
                break
    return out


def apply_mapping(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Return a dataframe with only mapped columns, renamed to canonical names.

    Raises ValueError if a source column is missing or mapped to two canonical fields.
    """
    sources = list(mapping.values())
    dupes = {s for s in sources if sources.count(s) > 1}
    if dupes:
        raise ValueError(f"Source column(s) mapped more than once: {sorted(dupes)}")
    missing = [s for s in sources if s not in df.columns]
    if missing:
        raise ValueError(f"Mapped source column(s) not found in file: {missing}")
    return df[sources].rename(columns={v: k for k, v in mapping.items()}).copy()
