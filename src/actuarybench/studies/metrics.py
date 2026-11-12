"""Core experience metrics (docs/ACTUARIAL_METHODS.md §3).

Notation: E = earned member-months, N = distinct claims, C = claim amount under the chosen
basis, P = earned premium.

- member-years            = E / 12
- frequency per 1,000 MY  = N / (E / 12) * 1000        (N/A when E <= 0)
- average severity        = C / N                       (N/A when N == 0)
- claim cost PMPM         = C / E                       (N/A when E <= 0; 0 when C == 0, E > 0)
- loss ratio              = C / P                       (N/A when P is missing or <= 0)

N/A is represented as ``None`` in scalar results and ``NaN`` in tables.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

METRIC_COLUMNS = [
    "earned_member_months",
    "member_years",
    "claim_count",
    "claim_amount",
    "earned_premium",
    "frequency_per_1000_my",
    "average_severity",
    "claim_cost_pmpm",
    "loss_ratio",
]


@dataclass(frozen=True)
class ExperienceMetrics:
    earned_member_months: float
    member_years: float
    claim_count: int
    claim_amount: float
    earned_premium: float | None
    frequency_per_1000_my: float | None
    average_severity: float | None
    claim_cost_pmpm: float | None
    loss_ratio: float | None


def compute_metrics(
    member_months: float,
    claim_count: int,
    claim_amount: float,
    earned_premium: float | None = None,
) -> ExperienceMetrics:
    """Compute experience metrics for one cell. Raises ValueError for negative inputs."""
    if member_months < 0 or claim_count < 0 or claim_amount < 0:
        raise ValueError("member_months, claim_count and claim_amount must be non-negative")
    if earned_premium is not None and earned_premium < 0:
        raise ValueError("earned_premium must be non-negative")
    e, n, c = float(member_months), int(claim_count), float(claim_amount)
    my = e / 12.0
    return ExperienceMetrics(
        earned_member_months=e,
        member_years=my,
        claim_count=n,
        claim_amount=c,
        earned_premium=earned_premium,
        frequency_per_1000_my=(n / my * 1000.0) if e > 0 else None,
        average_severity=(c / n) if n > 0 else None,
        claim_cost_pmpm=(c / e) if e > 0 else None,
        loss_ratio=(c / earned_premium) if earned_premium else None,
    )


def add_metric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorised version of :func:`compute_metrics` on a table that already holds
    ``earned_member_months``, ``claim_count``, ``claim_amount`` and ``earned_premium``.
    Uses identical formulas; undefined values become NaN."""
    out = df.copy()
    e = out["earned_member_months"].astype(float)
    n = out["claim_count"].astype(float)
    c = out["claim_amount"].astype(float)
    p = out["earned_premium"].astype(float)
    out["member_years"] = e / 12.0
    out["frequency_per_1000_my"] = np.where(e > 0, n / (e / 12.0) * 1000.0, np.nan)
    out["average_severity"] = np.where(n > 0, c / n.where(n > 0), np.nan)
    out["claim_cost_pmpm"] = np.where(e > 0, c / e.where(e > 0), np.nan)
    out["loss_ratio"] = np.where(p > 0, c / p.where(p > 0), np.nan)
    return out
