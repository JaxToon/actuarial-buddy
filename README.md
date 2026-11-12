# ActuaryBench — MVP Starter Pack

Working name: **ActuaryBench**  
Product wedge: **Group Health Experience Study & Pricing Indication Workbench**  
Document status: product/engineering proposal, not an actuarial standard or regulatory interpretation.  
Research snapshot: **12 November 2026**.

## What this pack contains

- `PRD.md` — product scope, personas, workflows, functional requirements and acceptance criteria.
- `ACTUARIAL_METHODS.md` — definitions, transparent formulas, calculation boundaries and test cases.
- `ARCHITECTURE.md` — practical local-first architecture for the first prototype and SaaS evolution path.
- `CLAUDE.md` — persistent project instructions/guardrails for Claude Code.
- `START_PROMPT.md` — initial prompt to paste into Claude Code.
- `RESEARCH_NOTES.md` — public-source findings and links used in the product decision.
- `CUSTOMER_DISCOVERY.md` — outreach, interview guide and validation plan for someone without an existing industry network.

## Recommended build order

1. Put these documents in the project root (or copy `CLAUDE.md` to the root and the rest into `docs/`).
2. Ask Claude Code to inspect the repository and implement only Milestone M0: project scaffold and synthetic demo dataset.
3. Verify the synthetic-data workflow and automated tests before moving to experience study calculations.
4. Add the pricing indication module only after the experience metrics are independently checked.
5. Do not use real policyholder or claims data in the public demo. Do not describe outputs as compliant, approved or production-ready.
6. Treat regulatory monitoring as a later controlled-change module; detected publications must not silently alter calculations.

## Run target for the first prototype

The prototype is intended to run locally:

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Claude Code should create the actual `requirements.txt`, source code, synthetic data, tests and app during implementation. These docs are specifications, not runnable application code.

## Compliance automation design

See [COMPLIANCE_AUTOMATION.md](COMPLIANCE_AUTOMATION.md) for the proposed source-monitoring, document-diff, human-review and versioned-rule-pack architecture. Compliance Watch is deliberately staged after the core experience/pricing workflow; no regulatory update may silently change calculations.
