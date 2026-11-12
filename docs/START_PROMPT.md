# Initial Prompt for Claude Code

Paste this into Claude Code after placing the starter documents in the repository root (or adjusting paths under `docs/`).

---

You are the lead engineer helping me build **ActuaryBench**, a local-first prototype for group-health experience study and preliminary pricing indication.

First, inspect the current repository and its git status. Do not overwrite or delete existing user work. Read these documents completely:

- `CLAUDE.md`
- `PRD.md`
- `ACTUARIAL_METHODS.md`
- `ARCHITECTURE.md`
- `RESEARCH_NOTES.md`

The documents define the scope and numerical boundaries. Do not expand the product into full PSAK 117, reserving, mortality, IBNR, RBC or ORSA. Do not claim regulatory compliance. The calculations must be deterministic Python functions, never LLM-generated.

## First task: M0 project scaffold only

Before coding, provide a short implementation plan identifying:

1. existing repository structure and any important existing code;
2. the files you intend to create/change;
3. dependencies and why each is needed;
4. tests you will add;
5. risks or ambiguous actuarial definitions you found.

Then implement **M0 only**:

- project structure from `ARCHITECTURE.md`;
- minimal Streamlit landing page with a clearly visible “Synthetic demo data” label;
- deterministic synthetic group-health exposure and claims generator;
- sample CSV/XLSX templates if straightforward;
- `requirements.txt`, `.gitignore`, README and initial pytest configuration;
- one smoke test that imports the app's core modules and validates the synthetic dataset shape.

Do not implement experience calculations, pricing, valuation or authentication in M0. Do not add external APIs, telemetry, LLM libraries or cloud infrastructure.

## Quality gates

- Use Python 3.12+ and type hints.
- Make synthetic data reproducible with a fixed random seed.
- Synthetic data must contain realistic data-quality edge cases only in a separate invalid-fixture dataset, not silently mixed into the clean demo dataset.
- Keep local uploads, outputs, `.env` and local database files out of git.
- Run pytest and ruff and fix all issues before reporting completion.
- If a specification detail is genuinely ambiguous, record the ambiguity and use the least risky implementation that does not invent actuarial methodology.

At completion, report:

- exact files created/changed;
- commands run;
- test/lint results;
- how I run the app locally;
- known limitations;
- the precise next milestone, without starting it automatically.

Do not commit or push anything unless I explicitly ask.
