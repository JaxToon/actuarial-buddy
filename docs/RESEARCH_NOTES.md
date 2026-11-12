# Research Notes — Indonesia Actuarial Software Opportunity

Research snapshot: **12 November 2026**. This is desk research from public sources. It does not replace interviews, legal review or actuarial-method review.

## 1. Industry and regulatory signals

### PSAK 117 / IFRS 17

- IAI's 2025 effective standards notice lists PSAK 117 as “Kontrak Asuransi” and states its effective date as 1 January 2025.
- IFRS 17 changes recognition, measurement, presentation and disclosure of insurance contracts. The IFRS Foundation describes current measurement of future cash flows and recognition of profit as insurance services are provided.
- PSAK 71 was renumbered as PSAK 109 in Indonesia's renumbering exercise. PSAK 109 relates to financial instruments; do not treat it as the primary insurance-contract valuation standard. Keep a future ECL/PSAK 109 module separate.

### OJK developments in 2026

- OJK reported that information-technology readiness and human-resource capacity remained major implementation challenges for PSAK 117 in May 2026. OJK said the new standard required significant changes to systems, business processes, actuarial methodology and reporting.
- OJK extended the deadline for audited FY2025 insurance/reinsurance financial statements based on PSAK 117 from 30 April 2026 to 30 June 2026, citing the need to ensure quality, consistency and reliability of implementation.
- OJK's October 2026 monthly release says POJK 18/2026 on insurer/reinsurer solvency adjusts the framework to PSAK 117 and Insurance Capital Standard concepts; it covers minimum solvency ratio, available capital, subordinated loans and ORSA.
- The same OJK release says POJK 19/2026 addresses integrity of financial reporting for insurance/reinsurance and related PPDP entities.
- As at 8 November 2026, public reporting indicated that OJK was still preparing a draft PADK with detailed procedures for solvency calculation, including available capital, MMBR and ORSA. The detailed implementation rules were therefore still moving at this research snapshot.
- OJK's October 2026 release reports 151 insurance and reinsurance companies as of September 2026; 121 had met the first-stage minimum equity requirement. It reports Rp1,192.84 trillion in insurance-industry assets and Rp252.80 trillion in commercial-insurance premium income through September 2026. These figures establish industry scale, not the addressable software market.

## 2. Professional standards and methods

- PAI publicly lists SPA-01 (basic actuarial practice), SPA-04 (insurance contracts / PSAK 117), SPA-07 (insurance risk management) and SPA-08 (insurance risk models), among other standards.
- PAI also lists PSAK 117 application guidance and downloadable PAA and GMA tools. These resources should be reviewed before a future valuation module is scoped.
- PAI explicitly states that its PSAK 117 application technical guide adopts IAN 100 and is an academic study/guidance, not a binding Standard of Practice. Do not describe it as a binding standard.
- The publicly accessible OJK SEOJK 27/2017 technical-reserve annex discusses data quality, latest best-estimate assumptions, experience data over 3–5 years (or industry data if company history is shorter), and justification for assumptions. It also discusses claim assumptions including mortality/morbidity and lapse. However, it is an older instrument; verify its current legal status and interaction with subsequent OJK rules before turning its provisions into software rules.
- Pricing methods generally use claim cost per exposure (or claim frequency × severity) and explicit fixed/variable expense and profit loads. The MVP formula is deliberately simplified and must be reviewed by an actuary.

## 3. Competitor and substitute landscape

### Enterprise actuarial platforms

- Moody's RiskIntegrity for IFRS 17 is a verified example in Indonesia: Moody's announced that Astra Life adopted the solution and completed its first IFRS 17 compliance audit review in 2024; the announcement describes SaaS deployment.
- International actuarial platforms such as Moody's AXIS and FIS Prophet are established enterprise categories for valuation/modelling. Their exact local deployment footprint, pricing and feature fit should be verified in future interviews/vendor research rather than assumed.

### Consulting and implementation services

- EY Indonesia publicly offers actuarial services and describes IFRS 17/9 implementation, data/technology enablement and vendor selection/implementation support.
- This makes actuarial consultants potential buyers/users, but also potential competitors, implementation partners or design partners.

### Professional-body tools and in-house alternatives

- PAI lists GMA and PAA tools for PSAK 117. These may be useful reference points or substitutes for parts of a future valuation module.
- Job descriptions for actuarial roles in Indonesia list work such as experience studies, technical reserves, life pricing, claims reserves and use of tools including SAS, SPSS, R, Emblem, ReMetrica and Prophet. Job listings are indicative snapshots, not a complete survey of industry practices.

## 4. What the research does and does not prove

### Supported by public evidence

- There is a regulated, sizeable insurance market with continuing change in accounting, solvency and reporting expectations.
- OJK has publicly identified technology readiness and actuarial/finance capability as implementation challenges.
- At least one Indonesian insurer has publicly announced adoption of an enterprise IFRS 17 SaaS solution.
- PAI makes practice standards and selected technical tools publicly discoverable.

### Not established by public evidence

- That Indonesian insurers are dissatisfied with incumbent platforms.
- That SMEs or smaller insurers lack a suitable solution.
- That analysts would pay for another pricing/experience-study application.
- How much work is currently performed in Excel versus Python, SAS, Prophet or enterprise systems.
- Exact willingness to pay, procurement budget, security requirements or buying timelines.
- Availability of public policy-level claims/exposure datasets. The MVP should assume those granular data are proprietary and unavailable publicly.

## 5. Product implications

1. Do not compete head-on with enterprise IFRS 17 platforms in v1.
2. Start with one analyst workflow: data QA + group-health experience study + simple pricing indication.
3. Use synthetic data to prove the workflow and numerical determinism; do not pretend synthetic results validate actuarial assumptions.
4. Make the first prototype local-first because claims/policy datasets are sensitive and enterprise cloud approval may be difficult.
5. Build traceability and assumption versioning early because OJK's reporting-integrity direction and actuarial review workflows make these foundational capabilities.
6. Keep PSAK 117, technical reserve and solvency calculations separate and versioned. Add them only after expert review of current effective rules.
7. Treat the market opportunity as a hypothesis. Validate it through practitioner interviews before investing in multi-tenant SaaS infrastructure.

## 6. Public source list

1. OJK, RDKB October 2026 (industry statistics; POJK 18/2026 and POJK 19/2026):  
   https://ojk.go.id/id/berita-dan-kegiatan/siaran-pers/Pages/RDKB-Oktober-2026.aspx
2. OJK, RDKB March 2026 (new-RBC/PSAK 117 implementation context):  
   https://ojk.go.id/id/berita-dan-kegiatan/siaran-pers/Pages/RDKB-Maret-2026.aspx
3. OJK, extension of audited FY2025 PSAK 117 reporting deadline:  
   https://ojk.go.id/id/berita-dan-kegiatan/siaran-pers/Pages/Perpanjangan-Waktu-Pelaporan-Keuangan-dan-SLIK-Asuransi-Penjaminan.aspx
4. Kontan, OJK says IT readiness and human-resource capability remain PSAK 117 implementation challenges, 19 May 2026:  
   https://keuangan.kontan.co.id/news/kesiapan-teknologi-dan-sdm-jadi-tantangan-implementasi-psak-117-di-industri-asuransi
5. PAI, official list of Standards of Practice and Technical Guidance:  
   https://www.aktuaris.or.id/page/content/225/dokumen-standar
6. PAI, PSAK 117 application technical guidance; explicitly non-binding:  
   https://www.aktuaris.or.id/page/news_detail/268/petunjuk-teknis-aplikasi-psak-117
7. IAI, Indonesian Accounting Standards effective 1 January 2025:  
   https://web.iaiglobal.or.id/Berita-IAI/detail/standar_akuntansi_keuangan_indonesia_efektif_per_1_januari_2025
8. IFRS Foundation, IFRS 17 overview:  
   https://www.ifrs.org/issued-standards/list-of-standards/ifrs-17-insurance-contracts/
9. Australian Accounting Standards Board, IFRS 17 text / PAA criteria (paragraph 53):  
   https://standards.aasb.gov.au/node/4052
10. Moody's, Astra Life adoption of RiskIntegrity for IFRS 17, 14 August 2024:  
    https://www.moodys.com/web/en/us/insights/announcements/astra-life-leads-the-way-in-indonesia-with-successful-completion-of-ifrs-17-compliance-audit-review.html
11. EY Indonesia, IFRS 17 implementation services:  
    https://www.ey.com/en_id/industries/insurance/ifrs-17-implementation
12. OJK, POJK 26/2025 on asset-liability management for insurers and reinsurers:  
    https://ojk.go.id/id/regulasi/Pages/POJK-26-Tahun-2025-Pengelolaan-Aset-dan-Liabilitas-Perusahaan-Asuransi-dan-Perusahaan-Reasuransi.aspx
13. OJK, publicly accessible annex to SEOJK 27/2017 technical-reserve guidance (historical reference; verify current status):  
    https://ojk.go.id/id/kanal/iknb/regulasi/asuransi/surat-edaran-ojk/Documents/SAL%20Lampiran%20SEOJK%2027%20-%20Cadangan%20%20Teknis%20PA%20PR.pdf
14. Open Actuarial Textbooks, Loss Data Analytics — Premium Foundations:  
    https://openacttexts.github.io/LDAVer2/ChapPremiumFoundations.html
15. OJK, POJK 28/2025 on risk management for insurance, guarantee and pension entities (effective 1 January 2026):  
    https://ojk.go.id/id/regulasi/Pages/POJK-28-Tahun-2025-Penerapan-Manajemen-Risiko-bagi-Perusahaan-Perasuransian%2C-Lembaga-Penjamin%2C-dan-Dana-Pensiun.aspx
16. JDIH Kementerian Komunikasi dan Digital, UU 27/2022 Pelindungan Data Pribadi (Article 4 identifies health information as specific personal data):  
    https://jdih.komdigi.go.id/produk_hukum/view/id/832/t/crc32/


## Compliance automation opportunity (research snapshot: 12 November 2026)

A future product capability should monitor official regulatory and professional-standard sources, but it must not silently rewrite calculation logic. The recommended workflow is detect → preserve source snapshot → classify status/dates → compare document changes → propose impact → human review → approve versioned rule/method pack → regression test → staged release. See `COMPLIANCE_AUTOMATION.md` for the full design.

Useful official source starting points:

- OJK regulation search: https://ojk.go.id/id/regulasi/default.aspx
- PAI standards and technical guidance: https://www.aktuaris.or.id/page/content/225/dokumen-standar
- JDIH BPK: https://peraturan.bpk.go.id/
- IFRS 17: https://www.ifrs.org/issued-standards/list-of-standards/ifrs-17-insurance-contracts/
- IFRS 2026 issued standards update: https://www.ifrs.org/news-and-events/news/2026/01/now-available-ifrs-accounting-standards-required-2026-two-editions/

Illustrative recent items for the source watchlist include POJK 36/2025 (health insurance ecosystem), POJK 26/2025 (insurance asset-liability management), POJK 28/2025 (risk management for PPDP), and the October 2026 OJK announcement of POJK 18/2026 (insurance solvency) and POJK 19/2026 (financial reporting integrity). Their exact legal status, full obligations, amendments and effective dates must be verified from the complete official instruments before coding a rule.
