"""Concise self-contained HTML report and results workbook for a pricing run."""

from __future__ import annotations

import html

import pandas as pd

from actuarybench.pricing.scenario import PricingRun

LIMITATIONS = [
    "Prototype analysis. Not an actuarial opinion, a filed tariff, a quote or a binding premium.",
    "Not a valuation, technical-reserve, insurance-contract accounting or solvency calculation.",
    "No allowance for IBNR / claim development, large-claim pooling, benefit changes, taxes, "
    "reinsurance, investment income or capital cost.",
    "The low-exposure flag is a review prompt, not a credibility method.",
    "Assumptions are user-supplied; the tool does not estimate trend or select weights.",
    "Must be reviewed by a qualified actuary before any operational use.",
]

_CSS = """
body{font-family:system-ui,Segoe UI,Arial,sans-serif;color:#1d2433;margin:32px;max-width:1200px}
h1{font-size:22px;margin-bottom:4px} h2{font-size:16px;margin-top:28px;border-bottom:1px solid #ccd;
padding-bottom:4px} table{border-collapse:collapse;font-size:12px;margin:8px 0}
th,td{border:1px solid #d5d9e2;padding:4px 8px;text-align:right} th{background:#eef1f6}
td:first-child,th:first-child{text-align:left} .warn{background:#fff6e0;border-left:4px solid
#d39e00;padding:6px 10px;margin:4px 0} .meta td{text-align:left} .synthetic{background:#e8f1fb;
border-left:4px solid #1f4e79;padding:6px 10px}
"""


def _table(df: pd.DataFrame, fmt: dict[str, str] | None = None) -> str:
    out = df.copy()
    for col, f in (fmt or {}).items():
        if col in out:
            out[col] = out[col].map(lambda v, f=f: "N/A" if pd.isna(v) else f.format(v))
    return out.to_html(index=False, na_rep="N/A", border=0, escape=True)


_RESULT_FMT = {
    "member_months": "{:,.0f}",
    "claim_count": "{:,.0f}",
    "weighted_pure_premium": "{:,.0f}",
    "trend_factor": "{:.4f}",
    "projected_pure_premium": "{:,.0f}",
    "fixed_expense_pmpm": "{:,.0f}",
    "loading_denominator": "{:.4f}",
    "indicated_rate_pmpm": "{:,.0f}",
    "current_rate_pmpm": "{:,.0f}",
    "indicated_change": "{:+.1%}",
}
_METRIC_FMT = {
    "earned_member_months": "{:,.0f}",
    "member_years": "{:,.1f}",
    "claim_count": "{:,.0f}",
    "claim_amount": "{:,.0f}",
    "earned_premium": "{:,.0f}",
    "frequency_per_1000_my": "{:,.1f}",
    "average_severity": "{:,.0f}",
    "claim_cost_pmpm": "{:,.0f}",
    "loss_ratio": "{:.1%}",
    "current_rate_pmpm": "{:,.0f}",
}


def render_html_report(run: PricingRun, manifest: dict, synthetic: bool) -> str:
    s, a, cfg = run.study, run.assumptions, run.study.config
    e = html.escape
    meta = pd.DataFrame(
        [
            ("Run ID", manifest["run_id"]),
            ("Created (UTC)", manifest["created_at"]),
            (
                "Code version",
                f"{manifest['code_version']['package']} / "
                f"{manifest['code_version']['method']} / "
                f"{manifest['code_version']['git_commit'][:12]}",
            ),
            ("Study period", f"{cfg.period_start:%Y-%m-%d} to {cfg.period_end:%Y-%m-%d}"),
            ("Evaluation date", f"{cfg.evaluation_date:%Y-%m-%d}"),
            ("Segments", ", ".join(cfg.segment_by) or "overall only"),
            ("Claim definition", cfg.claim_basis_label),
            ("Low-exposure threshold", f"{cfg.low_exposure_threshold_mm:,.0f} member-months"),
            ("Currency / units", "IDR; PMPM = per member per month"),
        ],
        columns=["Item", "Value"],
    )
    files = pd.DataFrame(
        [
            {
                "dataset": k,
                "source": v.get("filename"),
                "file_sha256": v.get("file_sha256"),
                "mapped_data_sha256": v.get("mapped_data_sha256"),
            }
            for k, v in manifest["inputs"].items()
        ]
    )
    assumptions = pd.DataFrame(
        [
            ("Assumption set", a.label),
            ("Owner", a.owner),
            ("Effective from", str(a.effective_from)),
            ("Notes", a.notes or "—"),
            (
                "Annual trend g",
                f"{a.annual_trend:.2%}" + (" (ILLUSTRATIVE)" if a.trend_is_illustrative else ""),
            ),
            ("Trend source", a.trend_source or "—"),
            ("Elapsed months m", f"{a.elapsed_months:g}"),
            ("Fixed expense", f"{a.fixed_expense_pmpm:,.0f} IDR PMPM"),
            ("Variable expense v", f"{a.variable_expense_pct:.2%}"),
            ("Commission c", f"{a.commission_pct:.2%}"),
            ("Target margin m", f"{a.target_margin_pct:.2%}"),
            ("Loading denominator d", f"{a.loading_denominator:.4f}"),
            (
                "Weighting",
                a.weighting_method
                + (
                    " — " + ", ".join(f"{p}: {w:.2%}" for p, w in sorted(a.period_weights.items()))
                    if a.period_weights
                    else ""
                ),
            ),
        ],
        columns=["Item", "Value"],
    )
    val_rows = []
    for kind, v in manifest["validation"].items():
        reasons = ", ".join(f"{r['code']} ({r['rows']})" for r in v["excluded_by_reason"]) or "—"
        val_rows.append(
            {
                "dataset": kind,
                "rows_in": v["rows_in"],
                "rows_valid": v["rows_out"],
                "excluded_by_reason": reasons,
            }
        )
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        f"<title>ActuaryBench run {e(manifest['run_id'])}</title><style>{_CSS}</style></head>",
        "<body><h1>Group-health experience study &amp; preliminary pricing indication</h1>",
        f"<p>ActuaryBench prototype · run <b>{e(manifest['run_id'])}</b></p>",
    ]
    if synthetic:
        parts.append(
            "<p class='synthetic'><b>Synthetic demo data.</b> All values are generated "
            "and do not represent any real insurer, member or claim.</p>"
        )
    parts += [
        "<h2>Run & study definition</h2>",
        _table(meta).replace("<table", "<table class='meta'"),
        "<h2>Input data lineage</h2>",
        _table(files),
        "<h2>Data validation & exclusions</h2>",
        _table(pd.DataFrame(val_rows)),
        "<p>Study-definition exclusions:</p>",
        _table(s.exclusions),
        "<h2>Method</h2><p>PP<sub>t</sub> = claims<sub>t</sub> ÷ member-months<sub>t</sub>; "
        "weighted PP = Σ w<sub>t</sub>·PP<sub>t</sub> (year-weighted) or ΣC ÷ ΣE "
        "(exposure-weighted); projected PP = weighted PP × (1+g)<sup>m/12</sup>; indicated "
        "gross rate PMPM = (projected PP + fixed expense) ÷ (1 − v − c − m); indicated "
        "change = indicated ÷ current − 1.</p>",
        "<h2>Assumptions</h2>",
        _table(assumptions).replace("<table", "<table class='meta'"),
        "<h2>Warnings</h2>",
    ]
    parts += [f"<div class='warn'>{e(w)}</div>" for w in s.warnings] or ["<p>None.</p>"]
    parts += [
        "<h2>Experience — overall</h2>",
        _table(s.overall, _METRIC_FMT),
        "<h2>Experience — by experience period</h2>",
        _table(s.by_period, _METRIC_FMT),
        "<h2>Experience — by segment</h2>",
        _table(s.by_segment, _METRIC_FMT),
        "<h2>Preliminary pricing indication</h2>",
        _table(run.results, _RESULT_FMT),
        "<h2>Limitations</h2><ul>",
    ]
    parts += [f"<li>{e(x)}</li>" for x in LIMITATIONS]
    parts += ["</ul></body></html>"]
    return "\n".join(parts)


def results_workbook_sheets(run: PricingRun, manifest: dict) -> dict[str, pd.DataFrame]:
    s = run.study
    flat = pd.json_normalize(
        {k: v for k, v in manifest.items() if k not in ("study_exclusions", "validation")},
        sep=".",
    ).T.reset_index()
    flat.columns = ["field", "value"]
    flat["value"] = flat["value"].astype(str)
    return {
        "manifest": flat,
        "pricing_results": run.results,
        "pricing_trace": run.trace,
        "experience_overall": s.overall,
        "experience_by_period": s.by_period,
        "experience_by_segment": s.by_segment,
        "experience_period_segment": s.by_period_segment,
        "study_exclusions": s.exclusions,
        "warnings": pd.DataFrame({"warning": list(s.warnings)}),
        "limitations": pd.DataFrame({"limitation": LIMITATIONS}),
    }
