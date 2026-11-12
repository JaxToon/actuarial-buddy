# M5 Readiness Checklist

Sources: [M4_1_ASSURANCE_REPORT.md](M4_1_ASSURANCE_REPORT.md),
[M4_2_IMPLEMENTATION_REPORT.md](M4_2_IMPLEMENTATION_REPORT.md). Items marked **[ACTUARY]** need
a qualified actuary's review; none are settled by this checklist.

## Verified

- [x] 82 tests pass (47 pre-M4.2 + 35 M4.2 regressions); ruff clean (M4.2)
- [x] Experience metrics match spec; invariants hold (≤ 2.2e-16) across 132 cells (M4.1)
- [x] Pricing chain matches independent recalculation exactly; Examples A/B/C pass (M4.1)
- [x] H1 Study periods that cut through coverage records are BLOCKED, not biased (M4.2)
- [x] H2 Every page works after real CSV and XLSX uploads (M4.2)
- [x] H3 Missing or partial current rate → change BLOCKED with reason; no fallback (M4.2)
- [x] H4 Runs store input, cleaned and exclusion snapshots, environment and output hashes; integrity and recalculation verified in a fresh process; corruption detected (M4.2)
- [x] Synthetic and prototype labels and limitations in UI and report; no compliance wording

## Before the synthetic walkthrough

- [ ] Use the synthetic workspace or uploads of the synthetic CSV/XLSX files only
- [ ] Explain that non-aligned study periods are blocked pending the D6 decision; show the diagnostic as an open question **[ACTUARY]**
- [ ] Present D6, D7, D8, D12 and D16 as open questions for practitioners
- [ ] Say that synthetic parameters are illustrative and were adjusted for plausibility (not a benchmark)
- [ ] Do not present assumption values pre-filled in the form as recommendations (backlog M5)

## Before any de-identified real data

- [ ] D6 partial-exposure convention approved and implemented **[ACTUARY]**
- [ ] M1 Claims grain and reversal/recovery handling defined **[ACTUARY]**
- [ ] M2 Overlapping member-cover detection
- [ ] M3/M4 Incurred < paid warning; date-only boundary comparisons
- [ ] M5/M6 No unconfirmed assumption defaults; weight-aware elapsed months **[ACTUARY]**
- [ ] Artifact store hardened (access control, encryption, retention) or data kept off shared machines
- [ ] Actuarial review of M4.1 §11 completed and recorded

## During M5 sessions

- [ ] Record which method choices practitioners expect (D6, D7, D8, claims grain, trend timing, D12 basis)
- [ ] Record which outputs, reports and reproducibility evidence reviewers need
- [ ] Never request or accept confidential policyholder or claims data
- [ ] Log rejected hypotheses alongside confirmed pain points ([CUSTOMER_DISCOVERY.md](CUSTOMER_DISCOVERY.md))
