# Method decisions & ambiguities log

Implementation choices where `ACTUARIAL_METHODS.md` / `PRD.md` did not fully specify a rule. Each
uses the least-risky option that does not invent actuarial methodology. **All require review by a
qualified actuary before any operational use.**

| # | Topic | Decision | Rationale |
|---|---|---|---|
| D1 | Date formats | Only ISO `YYYY-MM-DD` (or spreadsheet date cells) are accepted. `01/02/2025` is rejected. | Day/month order is ambiguous; guessing would silently corrupt periods. |
| D2 | Duplicate IDs | All occurrences of a duplicated `exposure_id` / `claim_id` are excluded. | The tool cannot know which duplicate is correct. |
| D3 | Claims on excluded exposure | Excluded with reason `linked_exposure_excluded` (distinct from `orphan_claim`). | Keeps orphan vs. rejected-parent cases separately countable. |
| D4 | Incurred derivation | If `incurred_amount` is absent and `case_reserve` present: incurred = paid + case reserve, recorded as a derivation. If both supplied, a mismatch > 1 currency unit is an error. | PRD §7. |
| D5 | Zero member-months | Warning only (row kept, contributes zero exposure). Negative is an error. | Zero is plausible (e.g. cancelled-from-inception); negative is not. |
| D6 | Study period vs exposure | An exposure record is included only if its **whole** coverage period lies inside the study period. Partly-overlapping records are excluded and counted. Exposure is never pro-rated. | No apportionment method is specified; pro-rating would be invented methodology. |
| D7 | Evaluation date | Claims with `reported_date` after the evaluation date are excluded and counted. Claims without `reported_date` are included, with a warning. | The data does not carry paid-as-of history, so this is the only available cut-off. |
| D8 | Experience period | Calendar year of `coverage_start`. | Sample data uses calendar-year coverage; for other policy-year conventions the user should prepare a matching file. |
| D9 | Current rate per segment | Member-month-weighted average of `current_rate_pmpm` over records that supplied a positive rate. | Gives a rate comparable to PMPM claim cost. |
| D10 | Loss ratio with partial premium | If any exposure row in a cell lacks premium, the cell's loss ratio is N/A (not computed on partial premium). | Avoids overstated loss ratios from incomplete denominators. |
| D11 | Streamlit pages folder | Pages live in `app_pages/` with `st.navigation`, not `pages/`. | `pages/` triggers Streamlit's legacy auto-discovery. Calculation logic is still outside UI files. |
| D12 | Current rate for indicated change | Member-month-weighted current rate of the segment's **latest** experience period. | Rates change by year; the latest period is the closest proxy for the rate in force. |
| D13 | Weights in a pricing segment | If a period with positive weight has no exposure in a segment, that segment is BLOCKED (no re-normalisation). The UI only rescales weights whose sum is off by < 0.1% due to input rounding, and discloses it. | ACTUARIAL_METHODS §4: "Do not silently select weights." |
| D14 | Equal default weights | The UI pre-fills equal weights but refuses to save them unless the user ticks an explicit confirmation. | ACTUARIAL_METHODS §4. |
| D15 | 0% trend | Allowed only when marked illustrative or given a documented source; illustrative trend is shown as a warning on every result. | ACTUARIAL_METHODS §5. |
| D16 | Elapsed months | User-entered. The UI suggests study-period midpoint → projection-period midpoint (365.25/12-day months); the user must confirm or override. | Trend is never estimated automatically. |
