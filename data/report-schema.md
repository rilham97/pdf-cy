# Report payload schema (draft 0.1)

Payload for the Cyberrank Cyber Risk Report generator (JSON -> PDF).
Sample: `claude-2026-10-02.json`, mapped from P2 `Claude - Cyber Risk Report.pdf` (45 pages, report date 02.10.2026, generated 03.10.2026, old openhtmltopdf pipeline).
Field names come from `06_Data_Wajib_dan_Usulan/Kontrak_Field_Usulan.json` (R01-R18) where one exists. Names without a contract field are new snake_case and are listed in section 9.

## 1. Conventions

**State enum** (`meta.state_enum`). A state is stored next to its value and never inside it.

| state | meaning | renderer must not say |
| --- | --- | --- |
| `findings` | Assessed, issues or items reported. In inventory modules (05 certifications, 07 fourth parties, 09 cloud) and registers, this means items were observed, not risk. | n/a |
| `clear` | Assessed, zero findings, within the sources and period checked. | "safe", "never breached" |
| `not_assessed` | Module not run or questionnaire not done. | 0, 0%, clean |
| `not_applicable` | Check does not apply (for example, no portal so no T&C clauses needed). | 0% as a failure |
| `unavailable` | Value could not be obtained, was not printed, was blank, or is a sentinel. | 0, false, clean |
| `partial` | Some components present, others missing. | full coverage |
| `pending_review` | Value exists but its meaning is ambiguous or contradicted in the source. Show the value with the review note. | a firm conclusion |

**NullReason** `{value: null, state, reason_code, note?, source_label?}`. Every null carries a reason, in one of three forms: a NullReason object; a row or object that has its own `state` + `reason_code` (for example `observed_hosting[1].country`); or sibling keys `<field>_state` + `<field>_reason_code` (`<field>_reason` free text on `pool360_range`) next to a null field in a table row, so the column keeps one type. The build fails on any null without a reason.

Reason codes used here: `not_printed_in_source`, `blank_in_source`, `dash_in_source` (cell printed '—'; label kept in `post_qc_source`), `sentinel_meaning_unconfirmed`, `not_identified`, `location_unknown`, `unknown_email_in_source`, `not_assigned`, `not_tracked`, `not_derivable`, `denominator_unavailable`, `asset_not_extracted`, `toggle_snapshot_not_printed`, `module_not_assessed`, `no_events`, `score_context_incomplete`, `policy_state_ambiguous`, `narrative_overclaim_and_provisional_rule`, `count_unreconciled`.

A `reason_code` is not only for nulls. On a section, sub-object or metric it can also explain a `partial`, `pending_review` or `not_assessed` state (for example `score_context_incomplete` on 01, `policy_state_ambiguous` on 03, `narrative_overclaim_and_provisional_rule` on 03 resourcing, `count_unreconciled` on 05), or a value that is kept but unconfirmed (`ip_reputation.rows[].reports`).

**Metric** `{id, label, value, unit, state, source_label?, denominator?, count_kind?, reason_code?, note?, section?}` (R05). `value` is number|null. `unit` is always set. `count_kind` is the grain: `reported`, `reported_headline`, `returned_rows`, `root_aggregate`, `distinct_finding_type`, `distinct_labels_as_printed`, `membership_not_unique_assets`, `cards_listed`, `observed`, `root_aggregate_plus_subdomains`.

**Text field suffixes**
- `*_source`: verbatim old-PDF product copy. It keeps source typos ('0 leakes'), so use it only where the template shows the original wording.
- `summary`, `neutral_message`, `note`, `state_reason`, `aggregation_note`: neutral copy written for the fixture, following the honest-message table in Kebutuhan_Data. Prefer these over `*_source` where RF-05 flags the source narrative.
- `source_label` / `state_label_source`: the exact printed token that justified a value or state. It is null only when the source printed no label.

**Dates** `{value: "YYYY-MM-DD", precision: "day", source_label}`. Timezone is not printed. Display format is `02 Oct 2026` in template style.

**Review flags.** `review_flags: ["RF-xx"]` points to the top-level `review_flags[]` list `{id, pages[], ref, text}`, which records contradictions and overclaims in the source.

## 2. Text fitting

| class | fields | rule |
| --- | --- | --- |
| ellipsis-allowed (display only) | header `identity.organisation_name`, `identity.domain` in running header | Ellipsis by font width. Source value never cut. Cover and section 01 show the full value. |
| never-truncate | all numbers, `value`, `unit`, grades, dates, `ip_address`, hostnames (`affected_assets[]`, `subdomain`, `domains[]`, `asset_label_source`), `finding_type`, `pre_qc_algorithm`, `standard`, `source_url`, ids, `exposure_period_source`, `exposed_field_categories` | Wrap inside the cell. Break hostnames only after `.` or `-`. Break URLs after `/`. |
| wrap (long prose) | `description_source`, `rationale_source`, `narrative_source`, `text_source`, `meaning_source`, `summary`, `*_reason`, `note`, methodology texts | Wrap freely. May flow across pages. Never ellipsis. |
| wrap (short label) | `label`, `title`, `state_label_source`, `status_label_source`, `required_role`, `estimated_time_reported` | Wrap to at most 2 lines. If a label exceeds 2 lines, it is a layout bug and must not be truncated. |
| long lists | `affected_assets[]` (up to 27), `pqc_detected[].domains[]` (25), registers in D | Chip or comma flow, wrapped. Registers split across pages with a repeated header. |

## 3. Top level

| key | type | notes |
| --- | --- | --- |
| `meta.report_schema_version` | str | `cyberrank-report/0.1-draft` (R01) |
| `meta.fixture_kind`, `fixture_note`, `language`, `extracted_at` | str | provenance of this sample |
| `meta.state_enum` | str[] | the 7 states |
| `meta.source_document` | obj | `ref`, `file`, `sha256`, `pages`, `pdf_title`, `producer`, `creator`, `pdf_created_at`, `pdf_modified_at`, `template_id` (NullReason) |
| `meta.sanitisation` | obj | `applied`, `rule`, `removed_fields[]`, `source_rows_with_unmasked_local_part` (int), `note` |
| `identity` | obj | `organisation_name`, `organisation_id` (NullReason, R01), `domain`, `website_source_label`, `sector` (deprecated alias `industry`, renamed at load), `sector_source_id?`, `description_source` (wrap), `logo` (NullReason; `value` = PNG/JPG path relative to the JSON file, inside its folder), `report_title` (PDF metadata only), `issuer {organisation_name, state, reason_code, note}` (template "ISSUED BY") |
| `snapshot` | obj | R01/R02/R04: `assessment_id`, `snapshot_id`, `timezone`, `methodology_version`, `active_version`, `viewed_version`, `score_context` (all NullReason here); `assessed_at`, `generated_at` (Date); `toggles_at_assessment.{pqc_scan, extended_scan}` (NullReason); `preferences_at_assessment {sovereignty_allowed_jurisdictions[], residency_allowed_countries[], source_pages[]}` (the two lists are used by 07 / 08 only when the section has no `allowed_set`) |
| `rating` | obj | `rating_name`, `grade` (AAA-D), `grade_source`, `grade_mark`, `risk_band` (`low`), `risk_band_label_source`, `band_description_source`, `net`, `pool`, `grade_table_id`, `stored_vs_calculated` (NullReason, R02), `review_flags[]` |
| `sections` | obj | 11 objects keyed by slug, in order 01-11 (section 4) |
| `appendices` | obj | `a_about`, `b_rating_scale`, `c_methodology`, `d_evidence_registers` (section 5) |
| `review_flags[]` | obj[] | `{id, pages[], ref, text}`, RF-01..RF-14 |

## 4. Sections

**Common envelope** (all 15): `number` ("01"-"15"), `title`, `group` (`overview_and_priorities` or `assessment_details`), `state`, `state_label_source`, `reason_code?`, `state_reason?`, `source_pages[]`, `old_section_label?` (e.g. "SECTION 2 OF 8 · VULNERABILITY"), `intro_source?`, `summary?`, `metrics[]?` (Metric), `review_flags[]?`.

Section layout v15 (user decision 2026-10-15): assessment sections follow the demerit ledger A–J (each rule has its own cap), then certifications, fourth-party vendors and cloud infrastructure. Data sovereignty (E), data residency (F), legal terms & conditions (G) and security resourcing (J) are their own sections, parallel to privacy (B). **Load-time alias:** a payload in the old shape (`privacy.sovereignty`, `privacy.residency`, `privacy.terms_conditions`, `privacy.resourcing`) is lifted to `data_sovereignty`, `data_residency`, `legal_terms`, `security_resourcing` by `build.normalise()` (its `subtitle_source` becomes `intro_source`); `tools/extract/section_layout.py` migrates a fixture file. When `summary` is absent these four sections take the opener verdict from the data (match_state copy, the rule G outcome line, `neutral_message`).

**Appendix D register ids** (user decision 2026-10-15) follow the section order of the generator registry, derived at build (`app_d_evidence_registers.RID`), not hard-coded: D.1 vulnerabilities (04; D.1.2 IP reputation), D.2 credential exposure (05; D.2.1–D.2.3 aggregates, D.2.5 row register), D.3 data leak history (06; index row only), D.4 quantum security (11; D.4.1 scopes, D.4.2 scope × algorithm rows), D.5 uploaded certificate documents (13; one page per uploaded document from `certificates[].document`, a path relative to the JSON file: PNG, JPEG or PDF), D.6 fourth-party vendors (14; D.6.1). An absent register keeps its slot as an index row. Every numbered section (01–15) and appendix opens on a new page.

**Section `summary` is system-provided** (user decision 2026-10-15, option b): every section's `summary` is the one-sentence (or short) verdict supplied by the system with the payload and printed under the section opener as is. The privacy summary covers the policy only; the sentences about governing law, hosting, legal T&C and resourcing live in the `summary` of `data_sovereignty`, `data_residency`, `legal_terms` and `security_resourcing` (the fixture builders write them there). The renderer's generated `verdict()` is only the fallback when `summary` is absent; when `summary` is present the generated reading, if different, prints in the section body.

| # | key | section-specific keys |
| --- | --- | --- |
| 01 | `executive_overview` | `scope_and_coverage {primary_domain, observed_targets[] (Metric), eligible_targets, coverage_percent (NullReason), coverage_statement_source, method_statement_source}`; `rating_overview {rating_ref, aspect_breakdown[] {aspect, section, value, unit, state, display_label_source, summary_label_source, secondary? (Metric), review_flags[]?}, note}`; `sector_comparison {sector, intro_source, metrics[] (your_score, sector_average, sector_top_10_percent; points of 100), performance_gap (NullReason), cohort {cohort_id, cohort_size, period, percentile_method, state, reason_code} (R15), note (not printed)}` |
| 02 | `priority_actions` | `intro_source`, `actions[] {action_id, rank, priority (high/medium/low), priority_label_source, title, estimated_time_reported, required_role, owner, due_at, status (NullReason), action_required_source, why_this_matters_source, linked_sections[], linked_finding_ids[], review_flags[]}` (R18), `note` |
| 03 | `privacy` | Demerit rule B. `policy {state, state_label_source, policy_state, policy_source (NullReason, R10), metrics[], areas (NullReason; 16 criteria A–P, criterion H 'Data residency' = policy text), issues[], review_flags[]}` |
| 04 | `vulnerabilities` | Demerit rule A. `severity_legend_source[] {severity, label, text}`, `findings[] {finding_id (unique per type and severity), finding_type, severity, severity_label_source, rationale_source, affected_assets_count, affected_assets[]}` (R07, R09); breach likelihood is per domain: `rows[].breach_likelihood {value, unit: "percent"}` on the D.1 register (`findings[].breach_likelihood` and `breach_likelihood_legend_source` are not printed); `assets_register_ref`, `coverage_note_source`; `email_dns_controls {state, state_label_source, controls[] {finding_id, control, result, state, status_label_source, line_source, key_strength_bits? / dmarc_policy? (NullReason), review_flags[]?}, guidance_source}`; `ip_reputation {state, state_label_source, reason_code, summary_source, ips_checked, rows[] {ip_address, isp, country, abuse_score (NullReason with source_label "-1"), reports {value, source_label, state (pending_review), reason_code}}, review_flags[]}`; `https_redirect {state, state_label_source, result, narrative_source, review_flags[]}` |
| 05 | `credential_exposure` | Demerit rule C. `attention_source`, `rows_by_field_category[] {field_category, rows}`, `exposure_years_source` / `rows_by_exposure_year[] {year, rows}` / `aggregation_note` (not printed, kept for reconciliation), `breach_source_name` (NullReason), `register_ref`, `mitigations_source[]` (R13) |
| 06 | `data_leak_history` | Demerit rule D. `last_valid_event` (NullReason; state `not_applicable` when there are no events, never `unavailable`; may name any record of a `canonical_event_id` group), `events[]` (R12 event objects; empty here; `validity_state` `reported_inaccurate` / `resolved` / `unknown`, absent = valid), `empty_state_source {title, text, coverage}` |
| 07 | `data_sovereignty` | Demerit rule E. `state, state_label_source, intro_source, enabled, observed_jurisdiction (NullReason), allowed_set[], match_state (match/mismatch/unknown; any other value reads as unknown), rows[] (not printed), narrative_source` (R14); optional `verdict_source`, `verdict_source_page` (not printed), `quote_source`, `metrics[]`. `allowed_set` absent or null -> `snapshot.preferences_at_assessment.sovereignty_allowed_jurisdictions` is used; an empty list means no preference. `enabled: false` prints no accepted jurisdictions |
| 08 | `data_residency` | Demerit rule F (hosting by IP location vs the owner/requestor preference; not privacy criterion H). Same as 07 (`allowed_set` absent or null -> `snapshot.preferences_at_assessment.residency_allowed_countries`) plus `observed_hosting[] {country, hosts, evidence_kind (NullReason: method not printed) / state, reason_code, source_label (not printed), match_state?}`, `note`. KPI strip derived from the rows (hosts observed = sum of `host_count`/`hosts`, only when every row has an int count; countries identified = distinct resolved ISO codes, placeholders and unresolved names excluded) unless `metrics[]` is given |

**Section 08 residency map contract** (`cyberrank_report/geo_map.py`, asset `assets/geo/world_110m_dots.json`, Natural Earth 1:110m, public domain). Each `observed_hosting[]` row:

| Field | Type | Rule |
| --- | --- | --- |
| `country_code` | ISO 3166-1 alpha-2, preferred | Used first. `XX`/`ZZ`/`--`/`??` = placeholder, never a country |
| `country` | string | Fallback when `country_code` is absent: alpha-2, alpha-3 or a Natural Earth name (case-insensitive exact match, no fuzzy match). Unresolvable -> off-map row "country name not recognised" + QA warn `residency_country` |
| `host_count` (alias `hosts`) | int | Hosts at that location; `host_count` wins when both are present. Null needs `host_count_reason_code` / `hosts_reason_code` (or `_reason`): the Hosts cell prints "Not available (<that reason>)" (no sibling reason: "not tracked by the assessment"); the map label prints the country name alone and the off-map counter "hosts … (count not available)", never 0 |
| `match_state` | `match` / `mismatch` (optional) | Payload decides; the renderer re-derives it from `allowed_set` and warns (`residency_country`) on a disagreement |
| `reason_code` | `location_unknown` / `country_code_placeholder` | Row is counted off the map (never placed or guessed). A placeholder code sent without a reason_code (e.g. `ZZ`) prints "Location not identified (the source printed the placeholder code “ZZ”)" and is counted under its own code; `country_code_placeholder` with no code sent means the source's “XX” |

`allowed_set[]` takes alpha-2 codes or names (same resolver). Mode is chosen automatically from hosting + preferred countries: <= 1 (`geo_map.C_MAX`; 0 when location lookups failed) -> country table only (C); padded Equal Earth box <= 60% of the world width (re-centred on the Pacific when that is narrower; minimum span = world / 6) -> regional zoom + locator (A2); otherwise world map with badges carrying the ISO alpha-2 country code and up to 2 magnifier insets for clusters or small countries (A3). Shapes: circle = in a preferred country, square = outside, open ring = preferred, navy circle = not compared (no preference set). The caveat "IP geolocation shows where public systems are hosted, not where all customer data is stored." always prints; a payload `note` about IP location is replaced by it.
| 09 | `legal_terms` | Demerit rule G. `state, state_label_source, intro_source, portal_detected (bool, yes/no word or {value}; NullReason = unknown, prints "Not available (reason)" and is not counted as a portal), rows[] {id?, label, value_source (string or {value})}, narrative_source` (+ `portal_url`, `terms_found` kept, not printed). When `portal_detected` is missing, the portal flag is read only from the row with `id: portal_detected` or the label "Login / Payment Portal" (any case) |
| 10 | `ai_risk_governance` | Demerit rule H. `title_source` (not printed); `narrative_observation {is_assessment_result: false, subtitle_source, text_source, signals_observed[] {signal, method, example_source}, stated_conclusion_source, annex_iii_high_risk_sector {value, state, reason_code, source_label}, public_ai_policy {…same…}, privacy_policy_ai_disclosure {…same…}}`. The three sub-objects carry `state: not_assessed`; their values (`not_apparent`, `not_found`, `not_clear`) are narrative readings, never booleans or results |
| 11 | `quantum_security` | Demerit rule I. `beta_notice_source`; `findings_by_category[] {category, issues, domains_source_label, algorithms[] {algorithm, findings, protocol_labels[], pqc_alternative_available (+ `_state`/`_reason_code` when null: no chip printed), risk_level}}`; `pqc_detected[] {algorithm, algorithm_alias, purpose, status_source, domains_count, domains[]}`; `scope_summary[] {subdomain, scope_level (root_aggregate/subdomain), rows, high, moderate, low, ml_kem_on_key_exchange, algorithms_absent[]}`; `scope_register_ref`, `aggregation_note`; `scope_and_limitations_source {title, scope_and_limitations {title, intro, items[]}, post_quantum_readiness {title, intro, items[], closing}}` |
| 12 | `security_resourcing` | Demerit rule J (not privacy criterion J 'Complexity and clarity'). `state, state_label_source, reason_code, state_reason, intro_source, privacy_role_evidence, security_role_evidence (detected/not_detected), narrative_source, neutral_message, roles_found[] {role, sources[]}?, review_flags[]` |
| 13 | `certifications` | `certificates[] {certificate_id, standard, standard_full_name, origin (detected/uploaded), origin_label_source, card_text_source, source_url, category, approval_state, valid_from, valid_until, eligibility, credit_applied (NullReason)}` (R11); `reference_standards {is_vendor_evidence: false, title_source, items[] {standard, description}}` |
| 14 | `fourth_party_vendors` | `vendors[]` (R17; empty here), `empty_state_source {title, text, coverage}`. State `findings` prints "Identified"; `summary` / `state_reason` print verbatim (generated summary only when `summary` is absent). |
| 15 | `cloud_infrastructure` | `lead_source`, `detection_methods[]` (section level, taken from `intro_source`), `providers[] {provider, detection_methods (NullReason: per-provider method not printed), observed_at (NullReason)}`, `last_scanned` (Date), `note` |

## 5. Appendices

| key | keys |
| --- | --- |
| `a_about` | `letter`, `title`, `source_pages[]`, `about_source`, `closing_source` (printed last, verbatim), `data_sources_source[]`. Static content, so it has no state. |
| `b_rating_scale` | `intro_source`, `old_appendix_label`, `rows[] {grade, meaning_source, mark, is_current_grade, pool360_range [lo,hi] + pool360_range_source, or null + pool360_range_state/_reason}`. Pool-360 ranges come from the reference pack (Table360 observed v2), not from this PDF. Only BBB..AAA are verified. |
| `c_methodology` | `is_generic_material: true`, `note`, `headline_source`, `lead_source`, `columns_source[] {title, text}`, `steps_source[] {n, title, text (blank line = new paragraph), signals[]?, callout, callout_emphasis[]? (phrases of the callout printed bold)}`, `scale_caption_source`, `scale_ends_source {top, bottom}`, `supply_chain {headline_source, text_source, illustrative_values {individual_risk, combined_risk, is_illustrative}, formula_title_source, formula, formula_explainer_source, variables[] {symbol, text}, impact_tiers[] {tier, text}, reliance_points[] {title, text}, closing_source, dashboard_note_source}`, `copyright_source` |
| `d_evidence_registers` | Frame only (title, intro, state, summary): the registers D.1–D.6 are built from the section data even when this object is absent. Each register has `{source_pages[], state, columns[], counts?, sanitised?, rows[]}`: `credential_register` (`id, email_domain (+ email_domain_state/_reason_code when null), email_state, account_label_masked, exposure_period_source, exposure_years[], exposure_period_has_unknown, exposed_field_categories[], breach_source_name (NullReason), affected_domain? (host the leaked entry is linked to, e.g. `app.example.com`; optional), status?, source_page`), `quantum_scope_register` (`id, subdomain, scope_level, category, pre_qc_algorithm, source, post_qc_source, post_qc_algorithm (+ post_qc_algorithm_state/_reason_code dash_in_source when null), high, moderate, low, source_page`), `vulnerability_asset_register` (`asset_label_source, finding_ids[], finding_count, max_severity`), `pqc_domain_register` (`domain, algorithm`) |

**Credential account label (policy option B, user decision 2026-10-15).** Each register row carries `account_label_masked` (string): the account label exactly as the Cyberrank system delivers it — masked upstream, e.g. `j*****n@instagram.com`, a masked username, or the source literal `Unknown Email`. The generator prints it **as received** in Appendix D.2.5 (column "Account (masked, as delivered)"; never re-masked, never truncated; long labels wrap at `@ . - _ /`). QA warns `unmasked_account_label` (count + row ids, never the label) when a label other than `Unknown Email` has no mask character (`*` or `•`); the value still prints as received. Optional `status` (string) adds a Status column. Other fields: `email_domain` holds the organisation domain or one of its subdomains (kept as is), `external` / `other_domain` for any other domain, or null when `email_state` is `unknown_email`; it drives the Section 08 aggregates only. `email_state`: `masked_label_present` (source label was masked; copied as printed), `unmasked_label_masked_at_preparation` (sample fixtures only: the source printed the label without a mask character, so it was masked when the fixture was prepared — first and last character of the local part kept, the rest `*`, domain kept; recorded in `meta.sanitisation.account_labels`; Claude 1, Instagram 15, Gmail 9 rows), `unknown_email` (source printed 'Unknown Email'). No password, token or other secret value is stored — only field category names. Sample fixtures: labels re-extracted from the source PDFs with `tools/extract/*parse_tables.py` and added by `tools/extract/add_account_labels.py <fixture> <tables.json>` (run after `build_fixture.py`, whose own no-'@' assert covers the label-free intermediate).

## 6. Old PDF page -> new key

| old page(s) | old content | new key |
| --- | --- | --- |
| 1 | Cover: org, website, report date, date generated, industry (sector), description, logo | `identity.*`, `snapshot.assessed_at/generated_at` |
| 2 | IISRI External Rating badge (BB, image), band "Low" + description | `rating.*` |
| 2-3 | IISRI Rating Breakdown: Privacy 0%, Vulnerability 43%, Certification 2 / 72%, Data Leak 0 / 100%, Credential 40 Found | `sections.executive_overview.rating_overview.aspect_breakdown[]` |
| 4 | blank page (layout overflow) | none (RF-13) |
| 5 | Industry Comparison 53 / 47 / 82 | `executive_overview.sector_comparison` |
| 6 | Priority Action Items (2) | `priority_actions.actions[]` |
| 7 | Privacy header, overview (0%, 0, 1), Terms & Conditions, Data Sovereignty | `privacy.policy`, `legal_terms`, `data_sovereignty` |
| 8 | Data Residency, Security and Privacy Resourcing | `data_residency`, `security_resourcing` |
| 9 | Vulnerability header, severity legend, likelihood legend | `vulnerabilities.metrics/severity_legend_source/breach_likelihood_legend_source` |
| 9-14 | 17 findings (rationale, affected domains, breach likelihood) | `vulnerabilities.findings[]`, `d_evidence_registers.vulnerability_asset_register` |
| 14 | coverage note, Email & DNS controls | `vulnerabilities.coverage_note_source`, `vulnerabilities.email_dns_controls` |
| 15 | IP Reputation table, HTTPS Redirect | `vulnerabilities.ip_reputation`, `vulnerabilities.https_redirect` |
| 16 | Certification header 72%, 3 detected cards | `certifications.metrics`, `certifications.certificates[]` |
| 17 | Commonly Referenced Standards | `certifications.reference_standards` |
| 18 | Data Leak History empty state, 100% | `data_leak_history` |
| 19 | Fourth-Party Vendors empty state | `fourth_party_vendors` |
| 20-21 | Credential Leak header 40%, attention, 30-row table | `credential_exposure.*`, `d_evidence_registers.credential_register` |
| 22 | Recommended Mitigation Measures | `credential_exposure.mitigations_source[]` |
| 23 | Cloud Infrastructure | `cloud_infrastructure` |
| 24 | AI Usage & Risk Classification, NOT ASSESSED | `ai_risk_governance` |
| 25-26 | Quantum overview 56/0/192/25, category groups, ML-KEM chips | `quantum_security.metrics/findings_by_category/pqc_detected` |
| 26-40 | Scope Breakdown table (248 rows) | `quantum_security.scope_summary[]`, `d_evidence_registers.quantum_scope_register`, `pqc_domain_register` |
| 40 | beta notice | `quantum_security.beta_notice_source` |
| 41 | Post-Quantum Safety Scan Results (limits, readiness) | `quantum_security.scope_and_limitations_source` |
| 41 | About This Report | `appendices.a_about.about_source`, `executive_overview.scope_and_coverage.method_statement_source` |
| 42-43 | Appendix A IISRI Rating Scale, closing footer | `appendices.b_rating_scale.rows[]`, `a_about.closing_source` |
| 44 | Methodology in brief 1/2 | `appendices.c_methodology` (columns, steps, scale) |
| 45 | Supply-chain aggregation 2/2 | `appendices.c_methodology.supply_chain` |
| all | running header/footer "Generated 03.10.2026 n \| Page" | `snapshot.generated_at` only |

## 7. States observed in this report

| section | state | state label in source | why |
| --- | --- | --- | --- |
| 01 executive_overview | partial | none | grade, band, aspects and benchmark are printed; net, pool, score context and assessment id are not (RF-11) |
| 02 priority_actions | findings | Priority Action Items | 2 actions (high, medium) |
| 03 privacy | pending_review | 0% PRIVACY SCORE | policy_state is ambiguous (RF-06) |
| 03 policy | pending_review | 0% Privacy Score | same |
| 09 legal_terms | not_applicable | Not detected | no login or payment portal |
| 07 data_sovereignty | findings | Not identified in published policies | jurisdiction unknown vs Australia |
| 08 data_residency | findings | United States of America (28 hosts), 1 host with unknown location | mismatch vs New Zealand |
| 12 security_resourcing | pending_review | We found no public sign of a dedicated security or privacy team. | no role evidence; source overclaims; J rule is provisional (RF-05) |
| 04 vulnerabilities | findings | 43% VULNERABILITY SCORE | 17 types (8 medium, 9 low) |
| 04 email_dns_controls | findings | Email & DNS Security Controls | DKIM `findings`, DMARC `partial` (mode blank, RF-01), DNSSEC `findings` |
| 04 ip_reputation | pending_review | IP Reputation — Clean | abuse score -1 sentinel (RF-07) |
| 04 https_redirect | clear | # HTTPS Redirect — Secure | redirects correctly |
| 13 certifications | pending_review | 72% COMPLIANCE SCORE | headline 2 vs 3 cards (RF-02) |
| 06 data_leak_history | clear | No Data Leaks Identified | 0 events in the sources checked |
| 14 fourth_party_vendors | clear | No Fourth-Party Vendors Identified | 0 vendors discovered |
| 05 credential_exposure | findings | 40% CREDENTIAL SCORE | 40 headline, 30 rows (RF-03) |
| 15 cloud_infrastructure | findings | 1 Cloud Providers Detected | Cloudflare |
| 10 ai_risk_governance | not_assessed | NOT ASSESSED | narrative kept as an observation (RF-04) |
| 11 quantum_security | findings | Quantum Security Overview | 56 high, 0 moderate, 192 low |

## 8. Table counts (this fixture)

| table | rows | check |
| --- | --- | --- |
| `priority_actions.actions` | 2 | |
| `vulnerabilities.findings` | 17 | each `affected_assets_count` equals the printed (N); 89 memberships in total |
| `d.vulnerability_asset_register` | 28 | distinct labels as printed, including 3 truncated (RF-08) |
| `vulnerabilities.ip_reputation.rows` | 2 | |
| `certifications.certificates` / `reference_standards.items` | 3 / 4 | |
| `data_leak_history.events` / `fourth_party_vendors.vendors` | 0 / 0 | |
| `d.credential_register` | 30 | 29 with org domain, 0 external, 1 unknown email, 19 include password, 4 include an Unknown period (3 Unknown only, 1 "2022, Unknown"); headline 40 is kept separately |
| `credential_exposure.rows_by_exposure_year` | 11 | 2008-2026; these are memberships, not row totals |
| `credential_exposure.rows_by_field_category` | 15 | |
| `quantum_security.findings_by_category` | 4 (9 algorithms) | 84 + 56 + 80 + 28 = 248 = 56 + 192 |
| `quantum_security.scope_summary` | 28 | 1 root aggregate + 27 subdomains |
| `d.quantum_scope_register` | 248 | root rows sum to 56 / 0 / 192 |
| `quantum_security.pqc_detected[0].domains` / `d.pqc_domain_register` | 25 | equals scopes with ML-KEM |
| `b_rating_scale.rows` | 10 | AAA..D |

## 9. Naming notes

**`sections.<key>.aspect_score`** (optional, every assessed section 03–15; owner decision 2026-10-19): the aspect's percent score **computed by the backend** (e.g. `(cap − demerit) / cap × 100`), `{value: 0–100, unit: "percent"}`. When present it is the score the Rating overview shows for that aspect (meter + value), also for aspects without a score metric. A null carries a reason: `no_preference_set` prints "Not compared" on the track; any other reason prints "Score not available". The generator never derives a score and never prints the demerit, cap or rule behind it.

**Contract names used:** `organisation_id`, `assessment_id`, `snapshot_id`, `report_schema_version`, `generated_at`, `assessed_at`, `timezone`, `methodology_version`, `active_version`, `viewed_version`, `score_context`, `stored_vs_calculated`, `pool`, `net`, `grade`, `grade_table_id`, `reason_code`, `source_label`, `toggles_at_assessment`, `value`, `unit`, `denominator`, `count_kind`, `finding_id`, `finding_type`, `severity_*`, `likelihood_type`, `policy_state`, `policy_source`, `certificate_id`, `standard`, `category`, `origin`, `approval_state`, `valid_from`, `valid_until`, `eligibility`, `credit_applied`, `enabled`, `allowed_set`, `match_state`, `evidence_kind`, `returned_rows`, `total_rows`, `cohort_id`, `cohort_size`, `period`, `percentile_method`, `action_id`, `linked_finding_ids`, `priority`, `owner`, `due_at`, `status`, `observed_at`.

**New snake_case names** (no contract field): every `*_source` copy field; `state_label_source`; `state_reason`; `summary`; `review_flags`; `source_pages`; `old_section_label`; `aspect_breakdown`; `secondary`; `display_label_source`; `summary_label_source`; `rank`; `estimated_time_reported` (kept apart from `due_at`); `required_role` (kept apart from `owner`); `affected_assets(_count)`; `breach_likelihood`; `controls`; `dmarc_policy`; `key_strength_bits`; `ip_reputation.rows`; `abuse_score`; `reports`; `https_redirect`; `observed_hosting`; `privacy_role_evidence`; `security_role_evidence`; `neutral_message`; `reference_standards`; `is_vendor_evidence`; `last_valid_event`; `email_domain`; `email_state`; `exposure_years`; `exposure_period_has_unknown`; `exposed_field_categories`; `<field>_state` / `<field>_reason_code` null siblings; `breach_source_name`; `rows_by_exposure_year`; `rows_by_field_category`; `providers`; `detection_methods`; `last_scanned`; `narrative_observation`; `is_assessment_result`; `signals_observed`; `findings_by_category`; `risk_level`; `pqc_alternative_available`; `pqc_detected`; `scope_summary`; `scope_level`; `pre_qc_algorithm`; `post_qc_algorithm`; `algorithms_absent`; `ml_kem_on_key_exchange`; `pool360_range`; `is_current_grade`; `is_generic_material`; `illustrative_values`; `*_register`; `*_ref` (dotted path into the payload).

**Old content with no template slot**, placed under the closest section:
- IP Reputation, HTTPS Redirect and Email & DNS controls go to 04 `vulnerabilities`.
- Commonly Referenced Standards goes to 05 `certifications.reference_standards`, flagged as not vendor evidence.
- Recommended Mitigation Measures goes to 08 `credential_exposure.mitigations_source`.
- The Quantum beta notice and the scope/readiness text go to 11 `quantum_security`.
- The aspect breakdown cards (old p2-3) go to 01 `rating_overview.aspect_breakdown`.
- The old Appendix A rating scale goes to new B; the methodology brief (p44-45) goes to C.
- `preferences_at_assessment` sits in `snapshot`, lifted from the privacy cards.
- `review_flags[]` sits at top level; the template has no slot for it, so render it as reviewer notes or omit it.

## 10. Optional fields read by the renderer (condition-matrix gaps, 15 Oct 2026)

None of these is in the Claude fixture; synthetic examples are in `tests/gap_fixtures.py`.

| Section | Field | Rendering |
| --- | --- | --- |
| 07, 08 | `data_sovereignty.quote_source`, `data_residency.quote_source` | Printed as "Policy text: “…”" |
| 08 | `data_residency.observed_hosting[].match_state` | Per-row comparison; an unknown location is a mismatch only when this says so |
| 03 | `policy.policy_state` outside the three known values | Section held as `pending_review` (`policy_state_unrecognised`) |
| 13 | `certificates[].approval_state` = `pending` / `approved` / `rejected` | Status column: "Awaiting approval" / "Approved" (same wording for detected and uploaded; uploads arrive approved) / "Rejected" (detected or uploaded) |
| 13 | `certificates[].file_reference` | Link under "Uploaded" |
| 13 | `certificates[].category` = `security` / `privacy` / `both` | "Security + Privacy" for both |
| 13 | `certificates[].expired` (bool or {value}) | System flag: "Expired" (icon + text) beside the dates; expiry is never computed from `valid_until` |
| 13 | `credit_applied`, `eligibility`, `credit_summary` | Internal weighting (pending 1, approved 2, rejected 0): never printed; QA warns only when a rejected certificate carries credit |
| 06 | `events[].canonical_event_id` | Records sharing it are one event (one row, sources merged) |
| 06 | `events[].records_unit`, `events[].records_scope` (`organisation` / `aggregate_multi_service` / `customer_tenant`) | Under the records count |
| 06 | `events[].date_basis`, `age_days_at_assessment` | Under the date ("Dated by disclosure date", "406 days before assessment"); never computed by the renderer |
| 06 | `events[].demerit_applied` | Not printed (hidden scoring) |
| 11 | `snapshot.toggles_at_assessment.pqc_scan` | `false` without results -> section `not_assessed` (`pqc_scan_disabled`); `false` with quantum results is rejected at load (data error); `true` or a non-empty `pqc_detected` allows "No PQC detected", otherwise "PQC not reported" |

Dates (`*_at`, `valid_from`, `valid_until`, `last_scanned`) must be ISO 8601; a date shorter than YYYY-MM-DD needs `precision`.

## 11. Business answers (15 Oct 2026) and fields from the 2026-10-15 production samples

Business answers applied: (1) detected certificates can be rejected; (2) certificate weighting (pending 1,
approved 2, rejected 0) is internal, the PDF shows status only; (3) `expired` is the system's flag, dates are shown,
never compared; (4) `enabled` false -> "Not compared: no preference set"; enabled -> compared with the preference set
by the report owner/requestor; (5) a breach event without a flag is valid; `validity_state: resolved` (user or admin)
prints "Resolved" (icon, green as `theme.TONE` resolved), is listed but not counted as open ("Open events (excludes resolved)" tile + note);
(6) quantum KPI = source headline (apex aggregate, as scored in the product), apex row labelled "apex aggregate", the
subdomain-row sum printed in a note; (7) `pqc_scan` false + quantum results = load error; (8) cloud: scan date only,
no staleness note; (9) Critical/High tier copy and T&C rule-G copy approved.

**Language.** Reports are English. Display strings the system localises (sector, risk band, other enum labels) are
rendered exactly as given; logic stays on the enum codes (`risk_band`, `severity`, `state`). Fixtures built from the
Indonesian-localised samples store the English product term and keep the printed label in `*_source_id`
(never rendered): `identity.sector_source_id` ("Manufaktur" -> "Manufacturing", "Telekomunikasi" ->
"Telecommunications"), `rating.risk_band_label_source_id` ("Rendah" -> "Low", "Sedang" -> "Medium"; the English
reports in 02_PDF_Assessment_Valid print Low / Medium).

| Section | Field | Rendering |
| --- | --- | --- |
| identity | `sector`, `sector_source_id`, `sector_label_source` | "Sector" row; source id not printed |
| rating | `risk_band` (code) + `risk_band_label_source` (display) | Chip text from the display string, colour from the code |
| rating | `net`, `pool` (printed by the remediation page) | "Net score" / "Point pool" rows in the rating panel; `snapshot.score_context` is not printed |
| 02 | `actions[].title_source`, `category` | Issue-based actions (title = category); text quoted in 03 prints "Described in 03 (Issue n)" |
| 02 | `remediation_impact {current, projected {grade, score, pool}, points_recoverable, active_issues {total, privacy, vulnerability, credentials}, conditional_on_rescan, narrative_source}` | "Projected rating after remediation" block: grade staircase current → projected; score, pool and points read for QA only, never printed |
| 03 | `policy.issues[] {label, category, text}` | Active issues table |
| 08 | `data_residency.observed_hosting[]` `country` null + `reason_code: country_code_placeholder` | "Location not identified (the source printed the placeholder code “XX”)" |
| 12 | `security_resourcing.roles_found[] {role, sources[]}` | "Role found: Data Protection Officer (source: …)" |
| 04 | `scanned_assets {domains[], subdomains[]}` | "Scanned assets" list |
| 04 | `active_scan {state, results[] {target, status clean/scanned, scanned_at, findings_reported, summary_source, findings[] {title, severity (info), description, impact, remediation}}}` | "Vulnerability scan results"; reported vs listed count mismatch noted (QA warn); "Informational" is not a tier |
| 06 | `events[].validity_state` = `resolved` | See answer 5 |
| 14 | `vendors[]` `employees`, `revenue_source`, `headquarters`, `founded`, `technologies_count` (+ `description_source`, `technologies_sample_source` kept, not printed) | Profile line under the vendor name; `risk_band_label_source` as the band text (plain, exactly as sent; no chip) |
| 05 | register `rows[].status` | "Row status as recorded: Open n, …" (counts only) |
| 10 | section `unavailable` + `reason_code: section_not_in_source` | The source report has no AI page |

## 11. Source wording kept next to our reading (comparison fixes, 15 Oct 2026)

Rule: the source's own wording, verdict or headline is quoted; our interpretation follows as a note. Never replaced silently.

| Section | Field | Rendering |
| --- | --- | --- |
| 01 | `rating_overview.aspect_breakdown[]`, `rating_overview.note` | Not quoted: the rating overview prints no source text. `aspect_breakdown[].value` (unit percent) is only the fallback score when the section has no score metric |
| 01 | credential result line | "N exposed account records" = register rows listed (as the section's register pointer) |
| 01 | `identity.review_flags[]`, any `review_flags[]` on 02 `remediation_impact` and on 04 | "Review flag RF-x: <text from top-level review_flags>" note |
| 02 | credential action (`linked_sections` credential_exposure, text counting accounts) | "Source: “<action_required_source>”", then "Note: <rows reading>" |
| 03 | `policy.policy_state {value, source_label, source_page}` | "Valid policy, assessed (source p. 2: “…”)" |
| 07 | `data_sovereignty.verdict_source` (+ `narrative_source`) | "Source verdict" row + "Source text: “…”" and a review note when our comparison differs |
| 04 | `breach_likelihood_note_source` | No longer printed (likelihood moved to one value per domain) |
| 04 | `active_scan.results[] {summary_label_source, recommendations_label_source}`; `scanned_at.precision: minute` | Source labels ("Executive Summary", "Top Recommendations"); time printed "12 Oct 2026 18:29" |
| 06 | `last_reported_source` or `last_valid_event.source_label` | "Source: “Last data leak has been reported on …”" |
| 05 | `exposure_years_source`; metrics without `source_label` | `exposure_years_source` not printed (kept for reconciliation; years print in fixed buckets from the rows); payload-derived counts labelled "Payload count (… not printed by the source)", their `note` printed only on a mismatch |
| 10 | `narrative_observation.text_source` | Always printed in full |
| 11 | `findings_by_category[].domains_source_label`; scope register | "· 2 domains" under the category; headline relation stated from the data (rows by level vs apex row); every scope × algorithm row printed in D.4.2 |
| 11 | metric `partly_quantum_safe` null + `placeholder_in_source` (source "#") | "Not available (the source printed a placeholder)" |
| 11 | `findings_by_category[].category` = "Key exchange" (SSH host keys) | Key icon |
| 11 | `pqc_detected[]` with several algorithms (ML-KEM, NTRU Prime) | One block each |
| 11 | register `rows[].risk_level`, `risk_note_source` | "Risk after PQC coverage" table; counts stay as reported |
| 11 | `affected_protocols[] {protocol, algorithms[], pqc_source, risk_level}` | "Affected protocols" table |

Mock Cyberrank fixture: `mock-cyberrank-2026-10-13.json`, built by `tools/extract/build_mock_fixture.py` (counts
asserted against the source PDF; review flags RF-01, RF-07, RF-M01..RF-M04).
