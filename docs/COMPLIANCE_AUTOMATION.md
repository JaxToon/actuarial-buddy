# Compliance Watch & Rule Update Architecture

## 1. Product goal

ActuaryBench should eventually monitor relevant regulatory and professional-standard sources, detect new or amended documents, explain what may have changed, identify potentially affected workflows, and help an authorized reviewer publish a versioned rule/method pack.

**The product must not silently change actuarial calculations just because a new document was detected.** Detection and summarization can be automated. Regulatory interpretation, applicability decisions, actuarial methodology changes, and production rule activation require human approval.

This is a regulatory-intelligence and controlled-change capability, not a guarantee of legal or regulatory compliance.

## 2. Source registry

Maintain an explicit, configurable source registry. Do not rely on general web search as the canonical production source.

Initial authoritative/discovery sources:

| Source | Primary role | Notes |
|---|---|---|
| OJK regulation search and OJK PPDP/insurance regulation pages | Indonesian regulator rules, circulars, consultation drafts, announcements | Primary source for OJK publications. The OJK regulation search supports discovery across regulatory document types and sectors. |
| JDIH BPK | Secondary verification of regulation metadata, status, promulgation and amendments | Cross-checking source, not a substitute for the issuing authority's original document if there is a discrepancy. |
| PAI — Dokumen Standar | SPA standards, technical guidance and tools | Track SPA-01 to SPA-09, especially SPA-04 for insurance contracts PSAK 117, plus technical guidance. Check the status and publication date of each file. |
| IAI / SAK Indonesia | PSAK / ISAK announcements, exposure drafts, amendments and effective dates | Separate official standards from exposure drafts, educational material and announcements. Check access and licensing before storing or redistributing standard text. |
| IFRS Foundation | International IFRS standards, amendments, project updates and effective dates | Use to understand the IFRS source layer; do not assume every IFRS publication automatically changes Indonesian PSAK requirements. |

Secondary sources (news, professional articles, vendor blogs) may be used to discover a potential update, but must never be treated as the authoritative basis for changing a rule.

### Source metadata

Each source record should contain:

- `source_id`, `publisher`, `source_type`, `jurisdiction`, `sector`, `topic_tags`.
- `canonical_url`, `monitoring_method`, `polling_interval`, `active`.
- `last_checked_at`, `last_success_at`, `last_seen_etag`, `last_seen_last_modified`, `last_content_hash`.
- `terms_reviewed_at`, `robots_checked_at`, `notes`.

Do not assume an API or RSS feed exists. Begin with stable official index pages and document links. Use RSS/API only when the publisher officially exposes one. Respect robots.txt, website terms, rate limits, access controls and copyright. Provide manual document upload as a fallback.

## 3. Regulatory document lifecycle

Represent lifecycle states explicitly. Avoid a single `is_current` boolean.

Suggested states:

- `consultation_draft`
- `issued_not_yet_effective`
- `effective`
- `amended`
- `partially_revoked`
- `revoked`
- `withdrawn_draft`
- `unknown_pending_review`

Store separate dates where available:

- publication / issuance date;
- promulgation date;
- effective-from date;
- effective-to / repeal date;
- consultation deadline;
- transitional or phased-in dates.

A draft regulation must never be treated as a current binding requirement. A document's publication date must not be assumed to be its effective date. Where status or date cannot be verified, mark it `unknown_pending_review`.

## 4. Monitoring pipeline

1. **Poll** configured official index pages on a scheduled cadence (for example, daily for OJK and weekly for standards publishers; make cadence configurable).
2. **Discover** new links and changed metadata.
3. **Fetch** documents only from approved source domains and record the final URL.
4. **Deduplicate** by canonical URL, publisher document identifier and content hash.
5. **Snapshot** the original file and metadata immutably; record retrieval timestamp and SHA-256 hash.
6. **Extract** PDF/HTML text with page/section references. Preserve page numbers and source links.
7. **Compare** metadata and content against the prior snapshot. Store a structured diff and changed sections.
8. **Classify** topic, jurisdiction, sector, document type and lifecycle state.
9. **Summarize** the possible change and cite the exact document sections. AI summaries are advisory only.
10. **Map impact** to product modules and rule packs, with confidence and rationale.
11. **Notify** an authorized reviewer of relevant or potentially relevant changes.
12. **Review and approve** the interpretation and any proposed rule/method change.
13. **Publish** an immutable, versioned rule/method pack only after required approvals and tests pass.

If the source page cannot be fetched, parsing fails, a PDF has no extractable text, or a document is ambiguous, create a monitoring exception. Never report “no change” when monitoring failed.

## 5. Change-impact record

For every detected publication, store:

- document title, number, issuer, jurisdiction and source URL;
- document type and lifecycle status;
- publication, promulgation and effective dates (each separately);
- content hash and snapshot ID;
- changed articles/paragraphs/pages with source references;
- AI-generated plain-language summary;
- potential obligations / requirements extracted;
- affected product modules (e.g. pricing, experience study, technical reserve, PSAK 117, solvency, reporting, governance, privacy);
- impact rating: `none`, `low`, `medium`, `high`, `unknown`;
- confidence score and explanation;
- reviewer decision: `relevant`, `not_relevant`, `needs_legal_review`, `needs_actuarial_review`;
- reviewer identity, timestamps, notes and approval evidence.

Each extracted requirement should be traceable to a paragraph/article/page in the source. If the exact citation cannot be identified, it cannot be promoted into a rule pack.

## 6. Controlled rule-pack release

A `RulePack` is not the source document itself. It is a curated, machine-readable set of approved calculation parameters, validation checks, reporting requirements or workflow controls that have been reviewed against source documents.

Suggested fields:

- `rule_pack_id`, `name`, `jurisdiction`, `business_line`, `module`;
- `version`, `status` (`draft`, `in_review`, `approved`, `scheduled`, `active`, `superseded`, `withdrawn`);
- `effective_from`, `effective_to`;
- `source_document_ids` and exact source references;
- `methodology_version`, `schema_version`, `tests_version`;
- `prepared_by`, `actuarial_reviewer`, `compliance_or_legal_reviewer`, `approved_at`;
- `change_summary`, `rollback_target`.

Activation rules:

- Never mutate a previously published rule pack. Publish a new version.
- Never activate a draft or unapproved rule pack.
- Support future effective dates and historical as-of dates.
- Calculation runs must pin the exact rule-pack version used.
- A run created under an older rule pack remains reproducible; do not silently recalculate historical results under a new pack.
- Require regression tests and documented expected-output changes before activation.
- Provide staged activation and rollback.
- Allow each customer/workspace to choose an approved rule-pack version where the business arrangement permits it.

## 7. Role of AI

AI may:

- classify a newly detected document;
- summarize a new or amended section;
- compare old and new text;
- suggest affected modules;
- draft a compliance impact note;
- answer questions using approved source documents with citations.

AI must not:

- decide conclusively whether a law applies to a particular insurer without reviewer confirmation;
- invent effective dates, thresholds, discount rates, assumptions or actuarial methods;
- translate narrative regulation into executable formulas without expert approval;
- edit calculation code or activate a rule pack autonomously;
- present an AI summary as legal advice or an official interpretation.

All AI outputs must include source references, retrieval date, model/version metadata and an uncertainty label. If sources conflict, show the conflict and ask for review rather than choosing silently.

## 8. MVP-to-product rollout

### Phase C0 — Design foundations (can be documented during the current MVP)

- Define source registry schema and document lifecycle states.
- Add `rule_pack_id` / `methodology_version` fields to calculation-run metadata where applicable.
- Add explicit compliance disclaimer: detected updates are informational and not an automatic compliance determination.
- No background crawler and no automatic rule changes.

### Phase C1 — Compliance Watch Lite (after core experience/pricing workflow is stable)

- Curated official source registry for OJK, PAI, IAI and IFRS Foundation.
- Manual refresh button / scheduled source check.
- Detect new or changed source pages and documents.
- Store document metadata, source URL, hash, lifecycle state and snapshot.
- Show a review inbox with links to original publications.
- Manual reviewer labels relevance and affected modules.
- No executable rule updates.

### Phase C2 — Assisted impact analysis

- Extract PDF/HTML text with page references.
- Generate AI-assisted summary and change comparison.
- Propose affected modules and draft impact memo.
- Require actuarial and/or legal/compliance reviewer acceptance.
- Notify users of newly detected items and review outcomes.

### Phase C3 — Versioned rule packs

- Define machine-readable approved rule packs for a narrow, validated calculation module.
- Build regression fixtures for every approved rule change.
- Introduce approval workflow, staged release, effective-date handling and rollback.
- Pin rule-pack versions to all calculation runs.

### Phase C4 — Enterprise compliance operations

- Tenant-specific applicability profiles (life, health, general, sharia, pension, etc.).
- Customer-specific policy overlays and evidence logs.
- Configurable notifications, review SLAs and approval chains.
- Private cloud / on-prem deployment and administrator controls.

## 9. Recommended first compliance topics

Do not monitor every financial regulation in Indonesia from day one. Begin with a narrow watchlist:

1. OJK regulations and circulars tagged insurance / reinsurance / PPDP that can affect product pricing, actuarial assumptions, liabilities, solvency, asset-liability management or financial reporting.
2. PAI SPA and technical guidance relevant to the selected line of business and module.
3. IAI SAK / PSAK announcements and amendments relevant to insurance contracts and related financial reporting.
4. IFRS 17 official amendments and project updates as an international source layer, clearly distinguished from Indonesian requirements.

Add OJK consultation drafts as `consultation_draft` signals, not as effective requirements.

## 10. Illustrative watchlist based on publications found on 12 November 2026

These are examples to seed monitoring and product discovery. They are not a complete legal inventory, and a production rule must be checked against the full original text, subsequent amendments, transitional clauses and current status.

| Publication | Why ActuaryBench should watch it | Initial handling |
|---|---|---|
| POJK 36 Tahun 2025 — Penguatan Ekosistem Asuransi Kesehatan | Directly relevant to the proposed group-health pilot. OJK's December 2025 RDKB summary describes medical/digital capability, medical advisory board, utilization review and coordination among guarantee providers as key topics. | Store original document; extract each obligation and applicability; do not infer a premium formula from the press-release summary. Verify the full regulation and effective date. |
| POJK 26 Tahun 2025 — Pengelolaan Aset dan Liabilitas Perusahaan Asuransi dan Perusahaan Reasuransi | Asset-liability management and financial-health framework; OJK's regulation page states it took effect on 24 November 2025 and superseded specified older provisions. | Track current status and cross-references; likely more relevant to later valuation / ALM / solvency modules than the first pricing demo. |
| POJK 27 Tahun 2025 — Pengelolaan Aset dan Liabilitas ... dengan Prinsip Syariah | Relevant to a future takaful/sharia product path. | Keep in a separate applicability category; do not apply to conventional group-health pilot by default. |
| POJK 28 Tahun 2025 — Penerapan Manajemen Risiko bagi PPDP | Relevant to governance and risk-management workflows; OJK announced an effective date of 1 January 2026. | Map to governance/control features, not automatically to pricing formulas. Verify full text. |
| POJK 18 Tahun 2026 — Perhitungan Solvabilitas Perusahaan Asuransi dan Perusahaan Reasuransi | OJK's October 2026 RDKB says the framework aligns solvency with PSAK 117 and ICS and includes minimum solvency ratios, available capital, subordinated loans and ORSA. | Flag as high-priority for future solvency/valuation roadmap. Retrieve and review the complete regulation and technical follow-up before implementation. |
| POJK 19 Tahun 2026 — Integritas Pelaporan Keuangan PPDP and related entities | Relevant to evidence, data lineage, reporting controls and approval workflows. | Map potential impact to report governance and audit trail; do not assume it creates a specific calculation method without reviewing text. |
| PAI SPA-04 — Standar Praktik Aktuaria Kontrak Asuransi PSAK 117 | Professional actuarial practice layer for insurance-contract work. PAI's standards page also lists SPA-01 to SPA-09 and technical guidance/tools. | Track PAI publication/version changes separately from OJK regulations and accounting standards. |

## 11. Acceptance criteria for Compliance Watch Lite

- A reviewer can see all configured sources and the last successful check time.
- The system distinguishes a successful check with no change from a failed check.
- A newly found document is stored with its original source URL, retrieval time and content hash.
- Duplicate detection prevents repeat alerts for an unchanged publication.
- Draft, issued and effective statuses are not conflated.
- Publication and effective dates are separate fields.
- Every summary and impact suggestion links to the source document.
- A reviewer can mark an item relevant / not relevant / pending expert review and record rationale.
- No calculation result changes when a new document is merely detected or summarized.
- Historical calculation runs remain reproducible with their original rule-pack and method versions.

## 11. Official starting points researched on 12 November 2026

- OJK regulation search: https://ojk.go.id/id/regulasi/default.aspx
- OJK December 2025 RDKB (mentions POJK 36/2025 for health insurance ecosystem, POJK 26/2025 and POJK 28/2025): https://ojk.go.id/id/berita-dan-kegiatan/siaran-pers/Pages/RDKB-Des-2025.aspx
- OJK October 2026 RDKB (mentions POJK 18/2026 solvency and POJK 19/2026 reporting integrity): https://ojk.go.id/id/berita-dan-kegiatan/siaran-pers/Pages/RDKB-Oktober-2026.aspx
- OJK insurance / PPDP regulation examples: https://ojk.go.id/id/regulasi/Pages/POJK-26-Tahun-2025-Pengelolaan-Aset-dan-Liabilitas-Perusahaan-Asuransi-dan-Perusahaan-Reasuransi.aspx
- JDIH BPK database: https://peraturan.bpk.go.id/
- PAI standards and technical guidance: https://www.aktuaris.or.id/page/content/225/dokumen-standar
- IFRS 17 official standard page: https://www.ifrs.org/issued-standards/list-of-standards/ifrs-17-insurance-contracts/
- IFRS 2026 issued standards update: https://www.ifrs.org/news-and-events/news/2026/01/now-available-ifrs-accounting-standards-required-2026-two-editions/
- IAI / SAK Indonesia: https://web.iaiglobal.or.id/

The source list is a starting point, not an exhaustive inventory. Verify the issuing authority's latest publication, amendments, transitional provisions and legal status before applying any requirement.
