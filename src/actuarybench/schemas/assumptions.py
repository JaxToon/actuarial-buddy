"""Versioned pricing assumption sets (docs/PRD.md §5.5, docs/ACTUARIAL_METHODS.md §4–6).

All percentages are decimals (0.10 = 10%). An assumption set is immutable once created;
changing anything means saving a new version.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

WeightingMethod = Literal["year_weighted", "exposure_weighted"]
WEIGHT_TOLERANCE = 1e-9


class AssumptionSet(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=1)
    owner: str = Field(min_length=1, max_length=100)
    effective_from: date
    effective_to: date | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notes: str = ""

    annual_trend: float = Field(gt=-1.0, le=1.0, description="Annual medical trend g")
    trend_source: str = ""
    trend_is_illustrative: bool = False
    elapsed_months: float = Field(ge=0, le=120, description="Experience → projection midpoint")
    fixed_expense_pmpm: float = Field(ge=0, description="IDR per member-month")
    variable_expense_pct: float = Field(ge=0, lt=1)
    commission_pct: float = Field(ge=0, lt=1)
    target_margin_pct: float = Field(ge=0, lt=1)
    weighting_method: WeightingMethod = "year_weighted"
    period_weights: dict[int, float] = Field(default_factory=dict)

    @field_validator("name", "owner")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @property
    def loading_denominator(self) -> float:
        """d = 1 − variable expense − commission − target margin."""
        return 1.0 - self.variable_expense_pct - self.commission_pct - self.target_margin_pct

    @model_validator(mode="after")
    def _check(self) -> AssumptionSet:
        if self.loading_denominator <= 0:
            raise ValueError(
                "variable expense + commission + target margin must be below 100% "
                f"(loading denominator is {self.loading_denominator:.4f})"
            )
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to is before effective_from")
        if self.weighting_method == "year_weighted":
            if not self.period_weights:
                raise ValueError("year_weighted method requires period weights")
            if any(w < 0 for w in self.period_weights.values()):
                raise ValueError("period weights must be non-negative")
            total = sum(self.period_weights.values())
            if abs(total - 1.0) > WEIGHT_TOLERANCE:
                raise ValueError(f"period weights must sum to 1 (got {total:.6f})")
        if self.annual_trend == 0 and not self.trend_is_illustrative and not self.trend_source:
            raise ValueError("0% trend must be marked illustrative or given a documented source")
        return self

    @property
    def label(self) -> str:
        return f"{self.name} v{self.version}"
