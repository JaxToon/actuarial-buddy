"""Preliminary indicated gross rate PMPM (docs/ACTUARIAL_METHODS.md §6).

d                         = 1 − v − c − m
Indicated gross rate PMPM = (Projected PP + Fixed expense PMPM) / d
Indicated change          = Indicated rate / Current rate − 1      (only if current rate > 0)

Excludes taxes, reinsurance, investment income, capital cost, pooling and other loads.
This is a preliminary indication — not a filed tariff, quote or binding premium.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


class PricingError(ValueError):
    pass


@dataclass(frozen=True)
class PricingResult:
    projected_pure_premium: float
    fixed_expense_pmpm: float
    variable_expense_pct: float
    commission_pct: float
    target_margin_pct: float
    loading_denominator: float
    indicated_rate_pmpm: float
    current_rate_pmpm: float | None
    indicated_change: float | None


def calculate_indicated_rate(
    projected_pure_premium: float,
    fixed_expense_pmpm: float,
    variable_expense_pct: float,
    commission_pct: float,
    target_margin_pct: float,
    current_rate_pmpm: float | None = None,
) -> PricingResult:
    if not math.isfinite(projected_pure_premium) or projected_pure_premium < 0:
        raise PricingError("Projected pure premium must be finite and non-negative.")
    if fixed_expense_pmpm < 0:
        raise PricingError("Fixed expense PMPM must be non-negative.")
    for name, v in (
        ("Variable expense", variable_expense_pct),
        ("Commission", commission_pct),
        ("Target margin", target_margin_pct),
    ):
        if not 0 <= v < 1:
            raise PricingError(f"{name} must be a decimal in [0, 1); got {v}.")
    d = 1.0 - variable_expense_pct - commission_pct - target_margin_pct
    if d <= 0:
        raise PricingError(
            f"Variable expense + commission + margin = {1 - d:.2%} ≥ 100%; the loading "
            "denominator must be strictly positive. Calculation blocked."
        )
    rate = (projected_pure_premium + fixed_expense_pmpm) / d
    change = None
    if current_rate_pmpm is not None and math.isfinite(current_rate_pmpm) and current_rate_pmpm > 0:
        change = rate / current_rate_pmpm - 1.0
    else:
        current_rate_pmpm = None
    return PricingResult(
        projected_pure_premium,
        fixed_expense_pmpm,
        variable_expense_pct,
        commission_pct,
        target_margin_pct,
        d,
        rate,
        current_rate_pmpm,
        change,
    )
