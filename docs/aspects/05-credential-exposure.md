# 05 Credential exposure

Payload key: `sections.credential_exposure` · Module: [s05_credential_exposure.py](../../cyberrank_report/sections/s05_credential_exposure.py) · Shared rules: [README](README.md)

Appendix D.2 (supporting tables + row register) is built from the same data by `d4_credentials` / `d23_domains` in
[app_d_evidence_registers.py](../../cyberrank_report/sections/app_d_evidence_registers.py) and is documented here too.
All counts come from the **register rows** that `register_ref` points to, never from section metrics. Unit = register
rows, not accounts.

## Layout (top to bottom)

Section 05 (state `findings` / `partial` / `pending_review` / `none_identified`, at least one register row):

1. Opener and card (shared, README §3). Verdict = `summary`; the module has no `verdict()` hook.
2. KPI tiles (one row when there are ≤ 4 tiles, else 3 per row): "exposed account records", "include a password",
   the lead tile, "affected domains" (optional), "latest exposure year", "unique accounts" (optional).
3. Reconciliation notes, 0..n (headline vs rows, rows received vs total, withheld rows, payload metric mismatches).
4. "Affected domains" (H2): Domain | Rows | With password | Latest year. Only when rows carry `affected_domain`.
5. "Email domain of exposed accounts" (H2): Account email domain | With password | Without password |
   Fields not reported | Total, then the mailbox-provider caveat note.
6. "Rows by latest exposure year" (H2): one row of fixed year buckets + one note line.
7. "Row status as recorded: …" note (only when rows carry `status`).
8. Register pointer: "**Full register**  D.2 Credential exposure — supporting tables  ·  N rows  ·  Appendix D, pages a–b".
9. "Recommended mitigation measures" (H2): `attention_source` paragraph + bullets (only when there is a bullet).

Appendix D.2 (printed only for state `findings` / `partial` / `pending_review` with ≥ 1 analysed row):

1. "D.2  Credential exposure — supporting tables" (H2) + intro sentence + "Unit: … State: … Snapshot …" line +
   "Back to Section 05 Credential exposure, p. n".
2. "D.2.1  Rows by exposed field category": # | Field category | Data class | Rows | Share of rows, then notes.
3. "D.2.2  Rows by data class": intro, Data class | Rows, then the origin-flag note.
4. "D.2.3  Rows by affected domain": # | Domain | Rows | With password | Latest year. **Or**, without
   `affected_domain`: "D.2.3  Exposure episodes and sources" + an "unavailable" sentence.
5. "D.2.4  Credential register": intro, # | Account (masked, as delivered) | Approximate exposure period |
   Exposed fields | Status (optional). Grouped by affected domain when present.
6. End line "End of register · N rows. N of M register rows shown; … Totals: …".

The Appendix D index always has a D.2 row (title, state chip, content, location).

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `title`, `intro_source`, `summary`, `state`, `state_reason`, `reason_code`, `what_checked`, `next_step`, `empty_state_source.coverage` | Opener / card (README §3) | Shared rules; `empty_state_source.text` is **not** used (see States) |
| `register_ref` | Dotted path to the register, e.g. `appendices.d_evidence_registers.credential_register` (`s05:142`, `lookup`) | No rows: body is "Register rows: Not available (not provided in the assessment data)." (`s05:514`) |
| register `rows[]` | Everything below: every count, table and D.2.4 row | See no-rows branches in Conditional rules |
| `rows[].account_label_masked` | D.2.4 "Account" column, **verbatim** (never re-masked), JetBrains Mono (`s05:456`) | "Label not delivered" |
| `rows[].exposure_period_source` | D.2.4 "Approximate exposure period", verbatim (`s05:457`) | "Period not given by source" |
| `rows[].exposed_field_categories[]` | Data class of the row; crosstab column; D.2.1 rows; D.2.4 "Exposed fields" (raw names joined ", ", `s05:458`) | Empty: crosstab "Fields not reported"; class "Fields not reported by source"; D.2.4 "Not provided by source" |
| `rows[].exposure_years[]` (ints) | Latest year = max → year buckets, "latest exposure year" tile, domain "Latest year", lead recency, D.2.4 sort (`s05:154-155`) | Non-int items ignored; no year → "Unknown" bucket (if flag) or "Not given" bucket |
| `rows[].exposure_period_has_unknown` | "Unknown" bucket when the row has no year; "row(s) list both a year and “Unknown”" note (`s05:156-165`) | false |
| `rows[].email_domain` | Mailbox-provider class (assessed / subdomain / other / unknown) for the crosstab and lead tile (`s05:121-130`); **never printed** | Empty → "Unknown Email" class |
| `rows[].email_state` | `unknown_email` → "Unknown Email" class (`s05:124`) | — |
| `rows[].affected_domain` *(optional)* | "Affected domains" table, "affected domains" tile, D.2.3 table, D.2.4 groups. Lower-cased, trailing dot stripped, must be a host name (`s05:133-136`) | Missing / not a host → "Domain not given" row/group. No row has one → none of these print |
| `rows[].status` *(optional)* | "Row status as recorded" note (capitalised, `s05:207`); D.2.4 "Status" column (raw text, `s05:459`) | Column only when any row has one; that row prints "Not recorded" |
| `rows[].id` | Named in QA `unmasked_account_label` detail only (`s05:442`) | — |
| register `counts.total_rows` (number, `{value}`, or NullReason) | Reconciliation "of {total_rows} rows"; D.2 intro "(Z in the source)" (`s05:183,188`; `app_d:411-413`) | "source total not provided" wording |
| register `counts.headline_found` | Headline fallback when metric `found_headline` is absent (`s05:182`) | — |
| `metrics[id=found_headline].value` | Source headline: mismatch note, no-rows tile, D.2 end line (`s05:182`) | Falls back to `counts.headline_found`; both absent → no mismatch note; end line "source headline not provided" |
| `metrics[id=unique_accounts]` `{value, grain \| unique_accounts_grain}` | "unique accounts" tile, only when `value` set and grain == `account` (`s05:258-268`) | No tile |
| `metrics[id ∈ returned_rows, rows_org_domain, rows_org_subdomain, rows_external_domain, rows_unknown_email, rows_with_password, rows_period_unknown]` `{value, label, source_label, note}` | Compared with the row-derived count; printed **only when different** (`s05:299-315`) | Not compared |
| `attention_source` | Paragraph under "Recommended mitigation measures" (`s05:491`) | Omitted |
| `mitigations_source[]` | Bullets, verbatim, before generated bullets (`s05:479`) | Omitted |
| `breach_source_name` (section level, NullReason) | Reason text in the D.2.3 fallback sentence (`s05:415-419`) | "not provided in the assessment data" |
| `rows_by_field_category[] {field_category, rows}` | D.2.1 difference note only (`app_d:431-435`) | No comparison |
| `identity.domain` | Assessed domain: class rule, labels, crosstab first row (`s05:144`) | "the assessed domain" / "Assessed domain" / "Subdomains of the assessed domain" |
| `snapshot.assessed_at` | Assessment year A (buckets, recency); D.2 "Snapshot {date}" (`app_d:106-109`) | Buckets anchor on the newest year in the rows; lead recency text omitted |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes (e.g. policy override key) |
|---|---|---|
| "exposed account records", "include a password", "affected domains", "latest exposure year", "unique accounts" | KPI tile labels (`s05:260-268`) | — |
| "rows on {domain}[ or its subdomains] with a password" | Lead tile label (`s05:241`) | — |
| "of {N} listed rows are on {domain}; all are on other email domains" | Lead tile label when no row is on the assessed domain (`s05:239`) | — |
| "Period “Unknown” in source" | Reason under a null "latest exposure year" tile (`s05:46,266`) | — |
| "Source headline: {headline} (unit not defined by the source); listed: {n} register rows; difference ±n — not explained by the source data." | Reconciliation (`s05:275-280`) | `reconciliation.source_mismatch`, `lists.credential_exposure.headline_unit`, `.list_unit` |
| "None of the {N} listed rows is an account on {domain}: they are on other mailbox providers or have no email. The 0 on the assessed domain describes the listed rows only; it is not a statement that the organisation is unaffected." | Reconciliation (`s05:283-286`) | — |
| "Computed over {n} rows; source total not provided — counts are lower bounds." | Reconciliation (`s05:289`) | `reconciliation.rows_total_unknown` |
| "Computed over {n} of {total} rows; counts are lower bounds." | Reconciliation (`s05:293`) | `reconciliation.rows_received` |
| "{n} rows withheld — domain text failed the masking check." | Reconciliation (`s05:297-298`) | `reconciliation.suppressed` |
| "Source metric “{label}” is {x}; the register rows give {y} (difference ±n).{ note}" / "Payload count (prepared from the source rows; not printed by the source) “{label}” …" | Reconciliation (`s05:311-315`) | First wording when the metric has `source_label` |
| "Affected domains"; "Domain", "Rows", "With password", "Latest year"; "{n} other domains"; "Domain not given"; "Unknown" / "Not given" (latest-year cell) | Affected domains table (`s05:333-349`) | — |
| "All {n} domains: Appendix D.2.3." | Under the domain table when cut (`s05:340`) | — |
| "Email domain of exposed accounts"; "Account email domain", "With password", "Without password", "Fields not reported", "Total"; "Subdomains of {domain}", "Other email domains", "Unknown Email", "All listed rows" | Crosstab (`s05:32,355-367`) | — |
| "The email domain is the account's mailbox provider, not the site where the credential leaked." | Note under the crosstab, always (`s05:47,368`) | — |
| "Rows by latest exposure year"; bucket heads "{year}", "{A-5} and before", "Unknown", "Not given" | Year table (`s05:371-403`) | — |
| "Each row counts once, under the latest year the source gives; “Unknown” rows have no year." | Year note, always (`s05:396`) | — |
| "{n} row lists / rows list both a year and “Unknown” and count under the year." | Year note (`s05:399`) | — |
| "Rows on {domain} with a password: {n} dated {A-1}–{A}[; {n} with latest year {y1}–{y2}][; {n} with period “Unknown” only]." | Year note (`s05:226-231,402`) | — |
| "Row status as recorded: {Status} {n}, …[; {n} rows without a status]." | Note (`s05:210-213`) | — |
| "Full register  D.2 Credential exposure — supporting tables  ·  {n} rows  ·  Appendix D, pages a–b" | Register pointer (`s05:517-518`, `components.py:432-438`) | `lists.credential_exposure.register_title`; "page reference pending" before pages resolve |
| "Recommended mitigation measures" | H2 (`s05:490`) | — |
| "{n} row(s) record a service/URL (origin) with the credential, a pattern typical of infostealer logs: revoke active sessions and tokens for the affected accounts and notify the affected users." | Generated bullet (`s05:482-484`) | — |
| "Rows on other email domains are not accounts the organisation manages; tell the affected users rather than resetting them centrally." | Generated bullet (`s05:486-487`) | — |
| "No exposed credentials were identified within the scope and period of this assessment." | Clear card reason (`s05:497-499`) | `states.overview_messages.clear_credential_exposure` |
| "reported by source (unit not defined by source); 0 register rows listed" | Headline-only tile (`s05:509`) | — |
| "No register rows are listed in the assessment data, so no breakdown by domain, period or data class can be shown." | Headline-only body (`s05:512`) | — |
| "Register rows: Not available (not provided in the assessment data)." | No rows, no headline (`s05:514`) | — |
| "D.2  Credential exposure — supporting tables" | D.2 H2 + index title (`app_d:404,414`) | `lists.credential_exposure.register_title` |
| "D.2.1–D.2.3 give the aggregates that support Section 05 (not repeated there); D.2.4 lists every register row with the account label as delivered by the Cyberrank system (masked upstream), the approximate exposure period and the exposed field categories. Showing {a} of {b} register rows ({c} in the source)." / "…; source total not provided." | D.2 intro (`app_d:411-417`) | — |
| "Unit: register rows, not accounts. State: {state label}. Snapshot {date}." | D.2 line 2 (`app_d:418-419`) | State label from `theme.STATE` (raw state, no INVENTORY mapping) |
| "D.2.1  Rows by exposed field category"; "#", "Field category", "Data class", "Rows", "Share of rows" | D.2.1 (`app_d:425-428`) | Field labels: `lists.credential_exposure.field_labels` (default: raw category name) |
| Data class cell: "Password category listed", "Category not in the data class map, no password", "Sensitive personal data, no password", "Other identity fields only", "Origin flag (counted apart from classes)" | D.2.1 (`s05:36-41,110-113`) | Class map: `lists.credential_exposure.data_class_map` (else built-in `_MAP` + `LABEL_CLASS`) |
| "A row can count in several categories; column total exceeds row total." | D.2.1 note (`app_d:429-430`) | `reconciliation.non_exclusive_note` |
| "Source field-category counts differ from the register rows: {cat} (source {n\|not listed}, rows {m}); …." | D.2.1 note (`app_d:432-435`) | — |
| "D.2.2  Rows by data class"; "Exclusive: each row counts once, in its highest class (password, then sensitive personal data, then other identity fields[, then a recorded service or URL only]). The origin flag is counted apart, below." | D.2.2 (`app_d:436-440`) | — |
| Data class rows: "Password category listed", ["Category not in the data class map, no password"], "Sensitive personal data, no password", "Other identity fields only", ["Service/URL recorded only"], "Fields not reported by source" | D.2.2 table (`s05:407-412`) | Bracketed rows only when non-zero |
| "Service/URL recorded (origin), counted apart from the classes: {n} row(s); the value itself is not provided by the source." | D.2.2 note (`app_d:442-443`) | — |
| "D.2.3  Rows by affected domain"; "#", "Domain", "Rows", "With password", "Latest year" | D.2.3 (`app_d:393-398`) | — |
| "D.2.3  Exposure episodes and sources" + "Data unavailable: episode grouping and breach source names are {reason}. This is not a zero result." | D.2.3 fallback (`app_d:391`, `s05:415-419`) | `states.overview_messages.unavailable` |
| "D.2.4  Credential register"; "#", "Account (masked, as delivered)", "Approximate exposure period", "Exposed fields", "Status" | D.2.4 (`s05:429,467,475`) | — |
| "One row per register row as delivered by the Cyberrank system. The account label is printed exactly as received (masking is applied upstream, not by this report). {Grouped by affected domain; inside a group, newest period first \| Sorted by the newest period a row lists}; rows whose period is only “Unknown” come last. Exposed fields are category names only; no password or other value is printed." | D.2.4 intro (`s05:469-474`) | — |
| Group row "{domain}" / "Domain not given" + "{n} rows" | D.2.4 (`s05:452-455`) | — |
| "{Column}: {value} (all rows)." | Above a D.2.x table when a text column holds one value in every row (`app_d:184-190,287-289`) | e.g. "Status: Open (all rows)." |
| "End of register · {n} rows. {n} of {m} register rows shown; {s} not shown ({mask policy violation \| none withheld}). Totals: {domain} a + subdomains of {domain} b + other email domains c + Unknown Email d = {n} rows = Section 05 overview total[; {f} label(s) without a mask character printed as received]; source headline {h} (unit not defined by the source; difference ±n, not explained by the source data) \| source headline not provided." | D.2 end line (`app_d:447-464`, `closing`) | `reconciliation.register_end` |
| Index content "Aggregates and all {n} of {m} register rows (masked account as delivered)" | Appendix D index (`app_d:465-466`) | When D.2 is not printed: `state_message(…, 'exposed credentials')` (`app_d:598-611`, policy `states.register_messages`) |

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| state `clear` | Card only; body empty | `s05:503-504` |
| No register rows **and** headline non-zero | Headline tile + reconciliation + "No register rows are listed…" sentence; QA `data_mismatch` | `s05:507-513` |
| No register rows, no headline | "Register rows: Not available (not provided in the assessment data)." | `s05:514` |
| Row `email_domain` contains `@` or `*` | Row withheld from every count and from D.2.4; "{n} rows withheld…" note; end line "mask policy violation" | `s05:145,296-298`; `app_d:457` |
| `email_state == unknown_email` or no `email_domain` | Class "Unknown Email" | `s05:124-125` |
| `email_domain == identity.domain` / ends with `.{domain}` / else | assessed / assessed_subdomain / other_domain | `s05:126-130` |
| Row's categories contain a password category | Crosstab "With password"; else categories present → "Without password"; none → "Fields not reported" | `s05:159` |
| Category class | policy/built-in map: password → sensitive personal → other identity (exact, then normalised, then breach-label list) → `service_recorded` (`origin`) → else unclassified + QA warn | `s05:97-107,178-180` |
| Row class (exclusive) | First present in: password, unclassified, sensitive_personal, other_identity, service_recorded_only, none_provided | `s05:33,116-118` |
| Lead count | Rows with class password on assessed domain or its subdomains | `s05:189` |
| No row on assessed domain or subdomains (but rows exist) | Lead tile label "of N listed rows are on …"; extra reconciliation sentence | `s05:216-218,238-239,281-286` |
| Subdomain rows with a password > 0 | " or its subdomains" in lead label | `s05:240` |
| Any row has a valid `affected_domain` | "affected domains" tile, "Affected domains" table, D.2.3 domain table, D.2.4 grouping | `s05:195,263-264,322-323`; `app_d:390`; `s05:439-441` |
| Named affected domains > 30 | Table shows top 10 + "{n} other domains" row + "All {n} domains: Appendix D.2.3." | `s05:49,326-340` |
| Some rows lack a valid `affected_domain` | "Domain not given" row (last) / group | `s05:334-335,452` |
| Domain order | Assessed domain, then its subdomains, then other hosts; each by rows desc, then name; "Domain not given" last | `s05:198-202` |
| Domain latest-year cell | Year; else "Unknown" if any row flagged unknown; else "Not given" | `s05:347` |
| Subdomain crosstab row | Only when any subdomain rows | `s05:358` |
| Assessed / With password cell non-zero | Bold | `s05:359-360` |
| Year buckets | Years > A (each); A … A-4 (each, zero shown muted); "{A-5} and before"; "Unknown" (always); "Not given" (only if any) | `s05:371-387` |
| `snapshot.assessed_at` missing | A = newest row year; lead recency text omitted | `s05:376`, `s05:190,223` |
| No row has a year | Latest tile "Not available" + "Period “Unknown” in source." | `s05:265-266` |
| Rows with both year and unknown flag | Note "… count under the year." | `s05:397-400` |
| Lead > 0 and A known | Recency note: recent = latest ≥ A-1; older as year range; unknown-only count | `s05:166-171,221-232,401-402` |
| Any row has `status` | Status note; D.2.4 Status column | `s05:207-213,443-466` |
| `unique_accounts` value set and grain `account` | "unique accounts" tile | `s05:259,267-268` |
| headline ≠ received rows | Source mismatch note | `s05:274-280` |
| `total_rows` missing / received < total | "source total not provided" note / "of {total} rows" note | `s05:287-295` |
| Payload metric value ≠ derived count | Mismatch note; `rows_org_domain` excludes subdomains only when `rows_org_subdomain` is also sent | `s05:299-315` |
| Origin rows > 0 / other-domain rows > 0 | Generated mitigation bullet(s) | `s05:481-487` |
| No `mitigations_source` and no generated bullet | Whole mitigation block (incl. `attention_source`) omitted | `s05:488-489` |
| D.2 printed | Section state ∈ findings / partial / pending_review **and** analysed rows > 0; else index row only | `app_d:408-409` |
| D.2.1 source differs | Difference note when `rows_by_field_category` is sent and any category count differs | `app_d:431-435` |
| D.2.4 sort | Newest latest year first; rows without a year after; among those, rows without `exposure_period_source` last; stable; then grouped by domain order | `s05:422-426,437-441` |
| D.2 end-line subdomain term | Omitted when 0; other terms always print | `app_d:451` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| received / suppressed / analysed | `len(rows)` / rows with `@`/`*` in `email_domain` / received − suppressed | `s05:145,185-186` |
| Crosstab cells | count by (email class × password / without / fields not reported) | `s05:147,159` |
| Rows with a password ("include a password") | class == password | `s05:193` |
| Lead | password rows on assessed domain + subdomains | `s05:189` |
| Lead recency | recent (latest ≥ A-1), older years, unknown-only | `s05:166-171` |
| Latest exposure year | max of every row's `max(exposure_years)` | `s05:184,193` |
| Year buckets | row counted once under its latest year | `s05:165,371-387` |
| Origin rows | rows with a `service_recorded` category (`origin`) | `s05:146,163` |
| By field / by class | Counter of categories (non-exclusive) / exclusive class | `s05:160-161` |
| Domain groups | per affected domain: rows, password rows, latest year, unknown flag | `s05:172-176` |
| Share of rows (D.2.1) | `round(100 * rows / analysed)` % | `app_d:422-423` |
| Status counts | Counter of capitalised `status`; rows without | `s05:207-212` |
| Differences | `signed(derived − source)` (+n / −n / ±0) | `app_d:94-95` |
| Used by other sections | 01 result line "N exposed account records" = analysed rows; 02 credential action note via `lead_metric` (policy `lists.credential_exposure.unit_rules.priority_action_text`) | `s01:320-326`; `s02:105-124`; `s05:246-252` |

## Read but never printed

| Field | Why it is read (QA, ordering, ...) |
|---|---|
| `rows[].email_domain`, `rows[].email_state` | Mailbox-provider class; mask check (withhold) |
| `rows[].exposure_years[]`, `rows[].exposure_period_has_unknown` | Buckets, recency, sort (only the counts print) |
| `rows[].id` | QA `unmasked_account_label` detail |
| `metrics[]` comparison ids (`returned_rows`, `rows_org_*`, `rows_external_domain`, `rows_unknown_email`, `rows_with_password`, `rows_period_unknown`) | Reconciliation; printed only on mismatch |
| `rows_by_field_category[]` | D.2.1 comparison; printed only on mismatch |
| `metrics[id=credential_score]` | Not printed in 05; section 01 aspect score (`s01:272-274`) |
| Not read at all | `rows_by_exposure_year`, `exposure_years_source`, `aggregation_note`, `state_label_source`, `rows[].breach_source_name`, `rows[].source_page`, register `state` / `columns` / `sanitised` / `source_pages` / `counts.returned_rows` / `counts.status` |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| `findings` | Findings | Full body; D.2 printed |
| `partial` | Partial coverage | Banner "{reason}. Counts below are lower bounds." (`app_d:120-121`), full body; D.2 printed |
| `pending_review` | Pending review | Card: reason, else policy `states.overview_messages.pending_review_banner`, else "Reason not recorded in the assessment data."; full body; D.2 printed |
| `none_identified` | None identified | Default card; body still built (rows → full body, but D.2 **not** printed) |
| `clear` | No findings | Card: reason (`state_reason` / `reason_code`) else the clear text above; "What was checked" from `what_checked` / `empty_state_source.coverage`; `empty_state_source.text` is overridden by `card()` (`s05:496-499`). No body; D.2 index "Not required — no exposed credentials identified." |
| `unavailable` | Unavailable | Card "{reason}. This is not a zero result." (`app_d:118-119`); no body |
| `not_assessed`, `not_applicable` | Not assessed / Not applicable | Default card; no body |

## QA checks raised

| check id | severity | when |
|---|---|---|
| `unmapped_field_category` | warn | A field category is in neither the policy map nor the breach-label list (once per category; counted as "unclassified", never as a password) (`s05:178-180`) |
| `data_mismatch` | warn | Headline non-zero but 0 register rows (`s05:508`) |
| `unmasked_account_label` | warn | A D.2.4 label has no `*` / `•` (literal "Unknown Email" exempt); names row ids (`s05:442`, `qa.py:44-54`) |
| `unresolved_reference` | warn | Shared: the pointer's D.2 target did not render (README §9) |

## Backend checklist

- MUST: `state`; `register_ref` resolving to a register with `rows[]`.
- MUST per row: `id`, `account_label_masked` (already masked), `email_domain` (or `email_state: unknown_email`),
  `exposure_period_source`, `exposure_years[]` (ints), `exposure_period_has_unknown`, `exposed_field_categories[]`
  (category names only, never values).
- MUST at top level: `identity.domain`, `snapshot.assessed_at` (drives the year buckets).
- SHOULD: `metrics[id=found_headline]`, register `counts.total_rows` (else "source total not provided" + lower-bound note).
- Optional: `rows[].affected_domain` (plain host such as `app.example.com`; enables the domain table, tile, D.2.3, D.2.4 groups),
  `rows[].status`, `metrics[id=unique_accounts]` with `grain: account`, comparison metrics, `mitigations_source[]`,
  `attention_source` (prints only with a mitigation block), `breach_source_name` NullReason, `rows_by_field_category[]`,
  `summary`, `intro_source`, `metrics[id=credential_score]` (01 only).
- Never send unmasked labels or an `email_domain` containing `@` / `*` (the row is withheld).
