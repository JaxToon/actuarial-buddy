"""Row-level data validation for exposure and claims inputs.

Principles (docs/CLAUDE.md, docs/PRD.md §5.3):
- Nothing is silently dropped, imputed or coerced. Every excluded row has at least one
  ERROR issue with a reason code; WARNING issues never exclude rows.
- Dates must be ISO ``YYYY-MM-DD`` (or a spreadsheet date cell). Ambiguous formats such as
  ``01/02/2025`` are rejected rather than guessed.
- Duplicate IDs exclude *all* occurrences, because the tool cannot know which one is right.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from actuarybench.schemas.canonical import CLAIM_FIELDS, EXPOSURE_FIELDS, FieldSpec

ISSUE_COLUMNS = ["record_type", "source_row", "record_id", "field", "severity", "code", "message"]
ERROR = "ERROR"
WARNING = "WARNING"
_DAYS_PER_MONTH = 365.25 / 12


@dataclass(frozen=True)
class ValidationConfig:
    incurred_tolerance: float = 1.0  # currency units, for incurred = paid + case_reserve
    member_month_tolerance: float = 0.5  # months beyond coverage span before warning


@dataclass(frozen=True)
class ValidationResult:
    record_type: str
    clean: pd.DataFrame
    issues: pd.DataFrame
    rows_in: int
    amounts_in: dict[str, float] = field(default_factory=dict)
    amounts_out: dict[str, float] = field(default_factory=dict)
    derivations: tuple[str, ...] = ()
    schema_errors: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        """True when the file is structurally usable (required columns present)."""
        return not self.schema_errors

    @property
    def rows_out(self) -> int:
        return len(self.clean)

    @property
    def rows_excluded(self) -> int:
        return self.rows_in - self.rows_out

    def excluded_by_reason(self) -> pd.DataFrame:
        """Rows affected per ERROR code. A row with several errors counts under each code."""
        err = self.issues[self.issues["severity"] == ERROR]
        if err.empty:
            return pd.DataFrame(columns=["code", "rows", "example_message"])
        g = err.groupby("code").agg(
            rows=("source_row", "nunique"), example_message=("message", "first")
        )
        return g.reset_index().sort_values("rows", ascending=False, ignore_index=True)

    def warnings_by_reason(self) -> pd.DataFrame:
        w = self.issues[self.issues["severity"] == WARNING]
        if w.empty:
            return pd.DataFrame(columns=["code", "rows", "example_message"])
        g = w.groupby("code").agg(
            rows=("source_row", "nunique"), example_message=("message", "first")
        )
        return g.reset_index().sort_values("rows", ascending=False, ignore_index=True)

    def reconciliation(self) -> pd.DataFrame:
        rows = [{"measure": "rows", "before": self.rows_in, "after": self.rows_out}]
        for k, v in self.amounts_in.items():
            rows.append({"measure": k, "before": v, "after": self.amounts_out.get(k, 0.0)})
        df = pd.DataFrame(rows)
        df["excluded"] = df["before"] - df["after"]
        return df


class _Issues:
    def __init__(self, record_type: str, id_col: str, df: pd.DataFrame) -> None:
        self.record_type = record_type
        self.id_col = id_col
        self.df = df
        self.rows: list[dict] = []

    def add(self, mask: pd.Series, fld: str, severity: str, code: str, message) -> None:
        """Record an issue for every row where ``mask`` is True. ``message`` may be a
        string or a callable taking the row and returning a string."""
        mask = mask.fillna(False).astype(bool)
        for idx in self.df.index[mask]:
            row = self.df.loc[idx]
            rid = row.get(self.id_col)
            self.rows.append(
                {
                    "record_type": self.record_type,
                    "source_row": int(row["_source_row"]),
                    "record_id": None if pd.isna(rid) else str(rid),
                    "field": fld,
                    "severity": severity,
                    "code": code,
                    "message": message(row) if callable(message) else message,
                }
            )

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=ISSUE_COLUMNS)

    def error_rows(self) -> set[int]:
        return {r["source_row"] for r in self.rows if r["severity"] == ERROR}


def _prepare(df: pd.DataFrame, fields: tuple[FieldSpec, ...]) -> tuple[pd.DataFrame, list[str]]:
    missing = [f.name for f in fields if f.required and f.name not in df.columns]
    if missing:
        return df, [f"Required column(s) not mapped/present: {', '.join(missing)}"]
    work = df.copy().reset_index(drop=True)
    work["_source_row"] = range(1, len(work) + 1)
    return work, []


def _parse_types(work: pd.DataFrame, fields: tuple[FieldSpec, ...], issues: _Issues) -> None:
    """Parse typed columns in place, reporting missing required values and parse failures."""
    for f in fields:
        if f.name not in work.columns:
            continue
        raw = work[f.name]
        is_null = raw.isna() | (raw.astype("string").str.strip() == "")
        if f.required:
            issues.add(
                is_null, f.name, ERROR, f"missing_{f.name}", f"Required field {f.name} is empty"
            )
        if f.kind == "date":
            parsed = pd.to_datetime(raw, errors="coerce", format="ISO8601")
            bad = ~is_null & parsed.isna()
            issues.add(
                bad,
                f.name,
                ERROR if f.required else WARNING,
                f"invalid_{f.name}",
                lambda r, n=f.name: f"{n} '{r[n]}' is not an ISO date (YYYY-MM-DD)",
            )
            work[f.name] = parsed
        elif f.kind == "number":
            parsed = pd.to_numeric(raw, errors="coerce")
            bad = ~is_null & parsed.isna()
            issues.add(
                bad,
                f.name,
                ERROR if f.required else WARNING,
                f"invalid_{f.name}",
                lambda r, n=f.name: f"{n} '{r[n]}' is not a number",
            )
            work[f.name] = parsed.astype(float)
        else:
            work[f.name] = raw.astype("string").str.strip()


def _flag_duplicates(work: pd.DataFrame, id_col: str, issues: _Issues) -> None:
    dup = work[id_col].notna() & work[id_col].duplicated(keep=False)
    issues.add(
        dup,
        id_col,
        ERROR,
        f"duplicate_{id_col}",
        lambda r: f"{id_col} '{r[id_col]}' appears more than once; all occurrences excluded",
    )


def _flag_mixed_currency(work: pd.DataFrame, issues: _Issues) -> None:
    if "currency" not in work.columns:
        return
    cur = work["currency"].dropna()
    if cur.nunique() > 1:
        main = cur.mode().iloc[0]
        issues.add(
            work["currency"].notna() & (work["currency"] != main),
            "currency",
            ERROR,
            "mixed_currency",
            lambda r: f"currency {r['currency']} differs from dataset currency {main}",
        )


def _finish(
    record_type: str,
    work: pd.DataFrame,
    issues: _Issues,
    rows_in: int,
    amount_cols: list[str],
    derivations: list[str],
) -> ValidationResult:
    bad = issues.error_rows()
    clean = work[~work["_source_row"].isin(bad)].reset_index(drop=True)
    amounts_in = {c: float(work[c].sum(skipna=True)) for c in amount_cols if c in work}
    amounts_out = {c: float(clean[c].sum(skipna=True)) for c in amount_cols if c in clean}
    issues_df = issues.frame().sort_values(["source_row", "severity", "code"], ignore_index=True)
    return ValidationResult(
        record_type=record_type,
        clean=clean,
        issues=issues_df,
        rows_in=rows_in,
        amounts_in=amounts_in,
        amounts_out=amounts_out,
        derivations=tuple(derivations),
    )


def _schema_failure(record_type: str, df: pd.DataFrame, errors: list[str]) -> ValidationResult:
    return ValidationResult(
        record_type=record_type,
        clean=df.iloc[0:0].copy(),
        issues=pd.DataFrame(columns=ISSUE_COLUMNS),
        rows_in=len(df),
        schema_errors=tuple(errors),
    )


def validate_exposure_data(
    df: pd.DataFrame, config: ValidationConfig | None = None
) -> ValidationResult:
    """Validate a canonical-named exposure dataframe (apply the column mapping first)."""
    config = config or ValidationConfig()
    work, schema_errors = _prepare(df, EXPOSURE_FIELDS)
    if schema_errors:
        return _schema_failure("exposure", df, schema_errors)
    iss = _Issues("exposure", "exposure_id", work)
    _parse_types(work, EXPOSURE_FIELDS, iss)
    _flag_duplicates(work, "exposure_id", iss)

    s, e, mm = work["coverage_start"], work["coverage_end"], work["earned_member_months"]
    iss.add(
        e < s,
        "coverage_end",
        ERROR,
        "coverage_end_before_start",
        "coverage_end is before coverage_start",
    )
    iss.add(
        mm < 0,
        "earned_member_months",
        ERROR,
        "negative_member_months",
        lambda r: f"earned_member_months {r['earned_member_months']} is negative",
    )
    iss.add(
        mm == 0,
        "earned_member_months",
        WARNING,
        "zero_member_months",
        "earned_member_months is zero (record contributes no exposure)",
    )
    span = ((e - s).dt.days + 1) / _DAYS_PER_MONTH
    iss.add(
        (e >= s) & (mm > span + config.member_month_tolerance),
        "earned_member_months",
        WARNING,
        "member_months_exceed_coverage",
        "earned_member_months exceeds the coverage period length",
    )
    if "earned_premium" in work:
        p = work["earned_premium"]
        iss.add(p < 0, "earned_premium", ERROR, "negative_premium", "earned_premium is negative")
        iss.add(
            p.isna(),
            "earned_premium",
            WARNING,
            "missing_premium",
            "earned_premium missing; loss ratio will be incomplete",
        )
    if "current_rate_pmpm" in work:
        iss.add(
            work["current_rate_pmpm"] < 0,
            "current_rate_pmpm",
            ERROR,
            "negative_rate",
            "current_rate_pmpm is negative",
        )
    _flag_mixed_currency(work, iss)
    return _finish("exposure", work, iss, len(work), ["earned_member_months", "earned_premium"], [])


def validate_claims_data(
    df: pd.DataFrame,
    exposures: ValidationResult,
    config: ValidationConfig | None = None,
) -> ValidationResult:
    """Validate a canonical-named claims dataframe against the validated exposures.

    Claims linked to an exposure that was itself excluded are excluded with a distinct
    reason code, so orphan claims and claims on rejected exposures can be told apart.
    If ``incurred_amount`` is absent but ``case_reserve`` is present, incurred is derived as
    ``paid_amount + case_reserve`` and the derivation is recorded.
    """
    config = config or ValidationConfig()
    work, schema_errors = _prepare(df, CLAIM_FIELDS)
    if schema_errors:
        return _schema_failure("claims", df, schema_errors)
    iss = _Issues("claims", "claim_id", work)
    _parse_types(work, CLAIM_FIELDS, iss)
    _flag_duplicates(work, "claim_id", iss)
    derivations: list[str] = []

    clean_exp = exposures.clean.set_index("exposure_id")
    all_exp_ids: set[str] = set()
    if not exposures.issues.empty:
        all_exp_ids = set(exposures.issues["record_id"].dropna())
    all_exp_ids |= set(clean_exp.index)
    linked = work["exposure_id"].isin(clean_exp.index)
    has_id = work["exposure_id"].notna()
    iss.add(
        has_id & ~linked & work["exposure_id"].isin(all_exp_ids),
        "exposure_id",
        ERROR,
        "linked_exposure_excluded",
        lambda r: f"exposure {r['exposure_id']} was excluded during exposure validation",
    )
    iss.add(
        has_id & ~linked & ~work["exposure_id"].isin(all_exp_ids),
        "exposure_id",
        ERROR,
        "orphan_claim",
        lambda r: f"exposure_id {r['exposure_id']} not found in exposure file",
    )

    cov_start = work["exposure_id"].map(clean_exp["coverage_start"]) if linked.any() else None
    if cov_start is not None:
        cov_end = work["exposure_id"].map(clean_exp["coverage_end"])
        sd = work["service_date"]
        outside = linked & sd.notna() & ((sd < cov_start) | (sd > cov_end))
        iss.add(
            outside,
            "service_date",
            ERROR,
            "service_outside_coverage",
            lambda r: f"service_date {r['service_date']:%Y-%m-%d} outside coverage period",
        )

    iss.add(
        work["paid_amount"] < 0, "paid_amount", ERROR, "negative_paid", "paid_amount is negative"
    )
    if "case_reserve" in work:
        iss.add(
            work["case_reserve"] < 0,
            "case_reserve",
            ERROR,
            "negative_case_reserve",
            "case_reserve is negative",
        )
    if "incurred_amount" in work:
        iss.add(
            work["incurred_amount"] < 0,
            "incurred_amount",
            ERROR,
            "negative_incurred",
            "incurred_amount is negative",
        )
        if "case_reserve" in work:
            diff = (work["incurred_amount"] - work["paid_amount"] - work["case_reserve"]).abs()
            iss.add(
                diff > config.incurred_tolerance,
                "incurred_amount",
                ERROR,
                "incurred_arithmetic_mismatch",
                lambda r: (
                    f"incurred {r['incurred_amount']:,.0f} != paid "
                    f"{r['paid_amount']:,.0f} + case reserve {r['case_reserve']:,.0f}"
                ),
            )
    elif "case_reserve" in work:
        work["incurred_amount"] = work["paid_amount"] + work["case_reserve"]
        derivations.append("incurred_amount derived as paid_amount + case_reserve")
    if "reported_date" in work:
        iss.add(
            work["reported_date"] < work["service_date"],
            "reported_date",
            WARNING,
            "reported_before_service",
            "reported_date is before service_date",
        )
    _flag_mixed_currency(work, iss)
    return _finish(
        "claims",
        work,
        iss,
        len(work),
        ["paid_amount", "case_reserve", "incurred_amount"],
        derivations,
    )


def validation_summary(results: list[ValidationResult]) -> pd.DataFrame:
    """One row per record type: rows in/out/excluded, error and warning counts."""
    return pd.DataFrame(
        [
            {
                "record_type": r.record_type,
                "rows_in": r.rows_in,
                "rows_valid": r.rows_out,
                "rows_excluded": r.rows_excluded,
                "error_issues": int((r.issues["severity"] == ERROR).sum()),
                "warning_issues": int((r.issues["severity"] == WARNING).sum()),
                "schema_errors": "; ".join(r.schema_errors),
            }
            for r in results
        ]
    )
