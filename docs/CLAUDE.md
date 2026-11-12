# Claude Code Project Instructions — ActuaryBench

You are working on ActuaryBench, a local-first prototype for **group-health experience study and preliminary pricing indication**. Read `PRD.md`, `ACTUARIAL_METHODS.md`, `ARCHITECTURE.md` and `RESEARCH_NOTES.md` before implementation.

## Product boundaries

- Build only the group-health experience/pricing workflow described in `PRD.md`.
- Do not implement life insurance, mortality table graduation, full reserving, IBNR, PSAK 117, PSAK 109, RBC/MMBR or ORSA in this MVP.
- Never describe the app or its outputs as “PSAK 117 compliant”, “OJK compliant”, approved, production-ready or a substitute for an appointed actuary.
- Keep regulatory requirements outside the calculation engine until an expert confirms the current rule, applicability and effective date.
- Regulatory monitoring may detect and summarize a publication, but must never automatically change formulas, assumptions, code or active calculation rules.
- Separate consultation drafts from issued/effective regulations; do not confuse publication date with effective date.
- Preserve source URLs, document hashes, exact article/paragraph/page references and retrieval timestamps for every compliance record.
- Any future rule/method pack must be immutable, versioned, approved by an authorized reviewer, covered by regression tests and pinned to calculation runs.
- AI may draft summaries and impact suggestions only; it must not make legal determinations, invent rules or activate rule packs.
- Treat all product requirements and customer pain points as hypotheses until validated with real users.

## Numerical integrity

- All actuarial calculations must be deterministic, explicit, independently testable Python functions.
- Never use an LLM, generative AI, embeddings or external API for numerical calculations or assumption selection.
- Do not silently impute, delete, coerce or aggregate invalid data. Every exclusion or derivation must be visible and counted.
- Preserve units and denominators in every output.
- Guard all divisions, date arithmetic, negative exposures, invalid rates and zero/negative loading denominators.
- Follow formulas and definitions in `ACTUARIAL_METHODS.md`. If an ambiguity is found, document it and stop before inventing a method.
- Add tests before or alongside new calculation logic. Use hand-calculated fixtures from `ACTUARIAL_METHODS.md`.

## Data security and privacy

- Use synthetic data only in the demo and tests.
- Never request, create, log or commit real names, NIK, full dates of birth, medical records, diagnosis notes, policy documents or real claims data.
- Do not send user data to external services.
- Keep uploads, outputs, database files, `.env` and secrets out of git.
- The first app is local-only and single-user; clearly display that it is not a production multi-tenant system.

## Engineering rules

- Keep calculation code outside Streamlit page files.
- Use type hints for public functions and structured result models.
- Add clear docstrings for formulas, units and edge cases.
- Prefer small, testable modules over one large app file.
- Avoid unnecessary infrastructure/dependencies. No Docker, Redis, Celery, cloud storage, payment, auth or LLM API unless explicitly requested later.
- Use `pytest` for tests and `ruff` for lint/format.
- Update README and docs when workflows or formulas change.
- Do not overwrite user files or refactor unrelated code.
- Inspect the current repository before making changes and preserve existing user work.

## User experience

- Label sample data as synthetic.
- Use visible units: IDR, PMPM, member-months, member-years, claims per 1,000 member-years and percentages.
- Display selected periods, segmentation and claim definitions beside outputs.
- Show warnings for paid-only claims, low exposure and incomplete premium data.
- Keep the interface clear and professional; prioritize workflow clarity over decorative charts.

## Development process

1. Inspect repository status and existing files before editing.
2. Read the relevant specification before each milestone.
3. Implement one milestone at a time.
4. Run tests and lint after each milestone.
5. Report files changed, tests run, results and known limitations.
6. Do not silently proceed to a later milestone if the current one has failed tests.
