# 05 Credential exposure

Payload key: `sections.credential_exposure` · Module: [s05_credential_exposure.py](../../cyberrank_report/sections/s05_credential_exposure.py) · Shared rules: [README](README.md)

Appendix D.2 (supporting tables + row register) is built from the same data by `d4_credentials` / `d23_domains` in
[app_d_evidence_registers.py](../../cyberrank_report/sections/app_d_evidence_registers.py) and is documented here too.
All counts come from the **register rows** that `register_ref` points to, never from section metrics. Unit = register
rows, not accounts.

## Layout (top to bottom)

Section 05 (state `findings` / `partial` / `pending_review` / `none_identified`, at least one register row):

1. Opener and card (shared, README §3). State `findings`: no summary paragraph (`KPI_ONLY`, owner 2026-10-21) — the
   tiles say it; other states keep the card and its reason.
2. KPI tiles, one row: "Credential score" ({n}%, `metrics[id=credential_score]` as sent; omitted when absent), then the
   supporting counts: "exposed account records" (every listed row), "open · {p}% resolved" (only with resolved
   rows), the lead tile ("[open, ]with password on {domain}", subdomains included, open rows only), "unique
   accounts" (optional).
3. Reconciliation notes, 0..n (headline vs rows, rows received vs total, withheld rows, payload metric mismatches).
4. "Affected domains" (H2): Domain | Rows | With password | Latest year; with resolved rows Domain | Open | Resolved
   ("n (p%)") | With password (open) | Latest year. Only when rows carry `affected_domain`.
5. "Email domain of exposed accounts" (H2): Account email domain | With password | Without password |
   Password unknown | Total. Rows: the assessed domain, "Subdomains of {domain}", then every other mailbox
   domain by name, most rows first (> 30 named: top 10 + "{n} other email domains" + "All {n} other email
   domains: Appendix D.2.4."), "Other email domains, name not given", "Unknown Email", "All listed rows";
   then the mailbox-provider caveat note.
6. "Exposure timeline" (H2, replaces the old "Rows by latest exposure year" table; owner 2026-10-21, no caption):
   left, stacked Open (orange) / Resolved (blue) bars per fixed year bucket with the total at the bar end and the legend on the
   header line; right, "Last 12 months" columns up to the assessment month (`snapshot.assessed_at`), from the
   latest month a row's `exposure_period_source` gives (`YYYY-MM` / `YYYY-MM-DD`). No row gives a month: the year
   bars alone, full width, with exact Open | Resolved | Total columns. Legend "Open" / "Resolved" on the header line
   in both layouts; a row without a status is drawn as Open (the status note gives the count). `cyberrank_report/charts.py`.
7. Status note only for what the tiles cannot show: "{n} row(s) without a status and {n} row(s) with status “{value}”
   count(s) as open." (missing / not open-resolved status). Open / resolved counts are in the tiles only.
8. Register pointer: "**Full register**  D.2 Credential exposure — supporting tables  ·  N rows  ·  Appendix D, pages a–b".
   Only when D.2 is printed (same rule, `register_printed`), so the pointer always has a target.
9. "Recommended mitigation measures" (H2): `attention_source` paragraph + bullets (only when there is a bullet).
   Without any bullet the `attention_source` paragraph prints on its own, without the heading.

Appendix D.2 (printed only for state `findings` / `partial` / `pending_review` with ≥ 1 analysed row):

1. "D.2  Credential exposure — supporting tables" (H2) + "Showing n of m register rows (k in the source)." only when rows are
   missing + "Back to Section 05 Credential exposure, p. n".
   "Back to Section 05 Credential exposure, p. n".
2. "D.2.1  Rows by exposed field category": # | Field category | Data class | Rows | Share of rows, then notes.
3. "D.2.2  Rows by data class": intro, Data class | Rows, then the origin-flag note.
4. "D.2.3  Rows by affected domain": the Section 05 table columns for every domain, only when Section 05 cut the list
   (> 30 named domains); otherwise one line "All {n} domains are listed in Section 05.". **Or**, without
   `affected_domain`: "D.2.3  Exposure episodes and sources" + an "unavailable" sentence.
5. "D.2.4  Rows by email domain" (only when Section 05 cut the other domains or grouped subdomains; otherwise "All
   email domains are listed in Section 05."): # | Account email domain | With password | Without password |
   Password unknown | Total: the assessed domain, each of its subdomains, then every other domain by rows;
   "Other email domains, name not given" and "Unknown Email" last.
6. "D.2.5  Credential register": intro, # | Account | Approximate exposure period |
   Exposed fields | Status (optional). Grouped by affected domain when present.
7. End line "End of register · N rows." + only differences: withheld rows, labels without a mask character, a source headline that differs.

The Appendix D index always has a D.2 row (title, state chip, content, location).

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `title`, `intro_source`, `summary`, `state`, `state_reason`, `reason_code`, `what_checked`, `next_step`, `empty_state_source {text, coverage}` | Opener / card (README §3) | Shared rules; `empty_state_source.text` is the `clear` card reason when there is no `state_reason` / `reason_code` (`s05:520-524`) |
| `register_ref` | Dotted path to the register, e.g. `appendices.d_evidence_registers.credential_register` (`s05:146`, `lookup`) | No rows: body is "Register rows: Not available (not provided in the assessment data)." (`s05:539`) |
| register `rows[]` | Everything below: every count, table and D.2.5 row | See no-rows branches in Conditional rules |
| `rows[].account_label_masked` | D.2.5 "Account" column, **verbatim** (never re-masked), JetBrains Mono (`s05:481`) | "Label not delivered" |
| `rows[].exposure_period_source` | D.2.5 "Approximate exposure period", verbatim (`s05:482`) | "Period not given by source" |
| `rows[].exposed_field_categories[]` | Data class of the row; crosstab column; D.2.1 rows; D.2.5 "Exposed fields" (raw names joined ", ", `s05:483`) | Empty: crosstab "Password unknown"; class "Exposed fields not listed (password unknown)"; D.2.5 "Not provided by source" |
| `rows[].exposure_years[]` (ints) | Latest year = max → year buckets, timeline year buckets, domain "Latest year", D.2.5 sort (`s05:165-166`) | Non-int items ignored; no year → "Unknown" bucket (if flag) or "Not given" bucket |
| `rows[].exposure_period_has_unknown` | "Unknown" bucket when the row has no year; "row(s) list both a year and “Unknown”" note (`s05:167-176`) | false |
| `rows[].email_domain` | Mailbox-provider class (assessed / subdomain / other / unknown) for the crosstab and lead tile (`s05:125-134`); **never printed** | Empty → "Unknown Email" class |
| `rows[].email_state` | `unknown_email` → "Unknown Email" class (`s05:128`) | — |
| `rows[].affected_domain` *(optional)* | "Affected domains" table, D.2.3 table, D.2.5 groups. Lower-cased, trailing dot stripped, must be a host name (`s05:137-140`) | Missing / not a host → "Domain not given" row/group; a value that is not a host also raises QA `invalid_affected_domain` (`s05:153-156`). No row has one → none of these print |
| `rows[].status` *(optional)* | Enum `open` / `resolved`, case-insensitive (`row_status`). Resolved rows: listed in D.2.5 with the green "Resolved" icon, counted in every total, left out of the open counts (tiles, Affected domains, D.2.3). Other text prints as received and counts as open (QA `unknown_row_status`) | Missing: "Not recorded" in D.2.5, counted as open; the column only when any row has one |
| `rows[].id` | Named in QA `unmasked_account_label` detail only (`s05:467`) | — |
| register `counts.total_rows` (number, `{value}`, or NullReason) | Reconciliation "of {total_rows} rows"; D.2 intro "(Z in the source)" (`s05:194,199`; `app_d:411-413`) | "source total not provided" wording |
| register `counts.headline_found` | Headline fallback when metric `found_headline` is absent (`s05:193`) | — |
| `metrics[id=found_headline].value` | Source headline: mismatch note, no-rows tile, D.2 end line (`s05:193`) | Falls back to `counts.headline_found`; both absent → no mismatch note; end line "source headline not provided" |
| `metrics[id=unique_accounts]` `{value, grain \| unique_accounts_grain}` | "unique accounts" tile, only when `value` set and grain == `account` (`s05:271-281`) | No tile |
| `metrics[id ∈ returned_rows, rows_org_domain, rows_org_subdomain, rows_external_domain, rows_unknown_email, rows_with_password, rows_period_unknown]` `{value, label, source_label, note}` | Compared with the row-derived count; printed **only when different** (`s05:324-340`) | Not compared |
| `attention_source` | Paragraph under "Recommended mitigation measures"; on its own (no heading) when there are no bullets (`s05:513-516`) | Omitted |
| `mitigations_source[]` | Bullets, verbatim, before generated bullets (`s05:504`) | Omitted |
| `breach_source_name` (section level, NullReason) | Reason text in the D.2.3 fallback sentence (`s05:440-444`) | "not provided in the assessment data" |
| `rows_by_field_category[] {field_category, rows}` | D.2.1 difference note only (`app_d:431-435`) | No comparison |
| `identity.domain` | Assessed domain: class rule, labels, crosstab first row (`s05:148`) | "the assessed domain" / "Assessed domain" / "Subdomains of the assessed domain" |
| `snapshot.assessed_at` | Assessment year A (buckets, recency) | Buckets anchor on the newest year in the rows; lead recency text omitted |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes (e.g. policy override key) |
|---|---|---|
| "exposed account records", "open · {p}% resolved", "[open, ]with password on {domain}", "unique accounts" | KPI tile labels (`kpis`, `lead_label`) | — |
| "rows on {domain}[ or its subdomains] with a password" | Lead tile label (`s05:254`) | — |
| "of {N} listed rows are on {domain}; all are {on other email domains \| Unknown Email \| on other email domains or Unknown Email}" | Lead tile label when no row is on the assessed domain; names only the classes that have rows (`s05:249-252`) | — |
| "Source headline {h}; {n} rows listed (difference ±d, not explained by the source data)." | Reconciliation, only when the headline differs from the listed rows (`reconciliation`) | — |
| "None of the {N} listed rows is an account on {domain}: they are on other mailbox providers or have no email. The 0 on the assessed domain describes the listed rows only; it is not a statement that the organisation is unaffected." | Reconciliation (`s05:308-311`) | — |
| "Computed over {n} rows; source total not provided — counts are lower bounds." | Reconciliation, only when there is no headline mismatch line (`s05:reconciliation`) | `reconciliation.rows_total_unknown` |
| "Computed over {n} of {total} rows; counts are lower bounds." | Reconciliation (`s05:318`) | `reconciliation.rows_received` |
| "{n} rows withheld — domain text failed the masking check." | Reconciliation (`s05:322-323`) | `reconciliation.suppressed` |
| "Source metric “{label}” is {x}; the register rows give {y} (difference ±n).{ note}" / "Payload count (prepared from the source rows; not printed by the source) “{label}” …" | Reconciliation (`s05:336-340`) | First wording when the metric has `source_label` |
| "Affected domains"; "Domain", "Rows", "With password", "Latest year"; "{n} other domains"; "Domain not given"; "Unknown" / "Not given" (latest-year cell) | Affected domains table (`s05:358-374`) | — |
| "All {n} domains: Appendix D.2.3." | Under the domain table when cut (`s05:365`) | — |
| "Email domain of exposed accounts"; "Account email domain", "With password", "Without password", "Password unknown", "Total"; "Subdomains of {domain}", "{n} other email domains", "Other email domains, name not given", "All {n} other email domains: Appendix D.2.4.", "Unknown Email", "All listed rows" | Crosstab (`s05:32,380-392`) | — |
| "The email domain is the account's mailbox provider, not the site where the credential leaked." | Note under the crosstab, always (`s05:51,393`) | — |
| "Exposure timeline"; "Latest year", "Open", "Resolved", "Total"; bucket labels "{year}", "{A-5} and before", "Unknown", "Not given"; "Last 12 months", month abbreviations, year under the first month | Timeline (`by_year`, `charts.py`) | — |
| "{n} row(s) without a status and {n} row(s) with status “{value}” count(s) as open."; "Domain", "Open", "Resolved", "With password (open)"; "All {n} domains are listed in Section 05." / "All email domains are listed in Section 05." | Status note (only for missing / other status), domain tables, D.2.3 / D.2.4 when Section 05 shows the full list (`status_line`, `domain_cols`, `app_d`) | — |
| "Full register  D.2 Credential exposure — supporting tables  ·  {n} rows  ·  Appendix D, pages a–b" | Register pointer, only when D.2 prints (`s05:542-544`, `components.py:432-438`) | `lists.credential_exposure.register_title`; "page reference pending" before pages resolve |
| "Recommended mitigation measures" | H2 (`s05:516`) | — |
| "{n} row(s) record a service/URL (origin) with the credential, a pattern typical of infostealer logs: revoke active sessions and tokens for the affected accounts and notify the affected users." | Generated bullet (`s05:507-509`) | — |
| "Rows on other email domains are not accounts the organisation manages; tell the affected users rather than resetting them centrally." | Generated bullet (`s05:511-512`) | — |
| "No exposed credentials were identified within the scope and period of this assessment." | Clear card reason when there is no `state_reason` / `reason_code` / `empty_state_source.text` (`s05:520-524`) | `states.overview_messages.clear_credential_exposure` |
| "reported by source (unit not defined by source); 0 register rows listed" | Headline-only tile (`s05:534`) | — |
| "No register rows are listed in the assessment data, so no breakdown by domain, period or data class can be shown." | Headline-only body (`s05:537`) | — |
| "Register rows: Not available (not provided in the assessment data)." | No rows, no headline (`s05:539`) | — |
| "D.2  Credential exposure — supporting tables" | D.2 H2 + index title (`app_d:404,414`) | `lists.credential_exposure.register_title` |
| "Showing {n} of {m} register rows[ ({k} in the source)]." | D.2 opening, only when rows are missing | `d4_credentials` |
| "D.2.1  Rows by exposed field category"; "#", "Field category", "Data class", "Rows", "Share of rows" | D.2.1 (`app_d:425-428`) | Field labels: `lists.credential_exposure.field_labels` (default: raw category name) |
| Data class cell: "Password category listed", "Category not in the data class map, no password", "Sensitive personal data, no password", "Other identity fields only", "Origin flag (counted apart from classes)" | D.2.1 (`s05:36-41,114-117`) | Class map: `lists.credential_exposure.data_class_map` (else built-in `_MAP` + `LABEL_CLASS`) |
| "A row can count in several categories; column total exceeds row total." | D.2.1 note (`app_d:429-430`) | `reconciliation.non_exclusive_note` |
| "Source field-category counts differ from the register rows: {cat} (source {n\|not listed}, rows {m}); …." | D.2.1 note (`app_d:432-435`) | — |
| "D.2.2  Rows by data class"; "Exclusive: each row counts once, in its highest class (password[, then a category not in the data class map], then sensitive personal data, then other identity fields[, then a recorded service or URL only]). The origin flag is counted apart, below." | D.2.2 intro; order = `s05.CLASSES`, bracketed parts only when that class has rows, like the table (`app_d:436-440`, `s05:42-44`) | — |
| Data class rows: "Password category listed", ["Category not in the data class map, no password"], "Sensitive personal data, no password", "Other identity fields only", ["Service/URL recorded only"], "Exposed fields not listed (password unknown)" | D.2.2 table (`s05:432-437`) | Bracketed rows only when non-zero |
| "Service/URL recorded (origin), counted apart from the classes: {n} row(s); the value itself is not provided by the source." | D.2.2 note (`app_d:442-443`) | — |
| "D.2.3  Rows by affected domain"; "#", "Domain", "Rows", "With password", "Latest year" | D.2.3 (`app_d:393-398`) | — |
| "D.2.3  Exposure episodes and sources" + "Data unavailable: episode grouping and breach source names are {reason}. This is not a zero result." | D.2.3 fallback (`app_d:391`, `s05:440-444`) | `states.overview_messages.unavailable` |
| "D.2.5  Credential register"; "#", "Account", "Approximate exposure period", "Exposed fields", "Status" | D.2.5 (`s05:454,492,500`) | — |
| "One row per register row as delivered by the Cyberrank system. The account label is printed exactly as received (masking is applied upstream, not by this report). {Grouped by affected domain; inside a group, newest period first \| Sorted by the newest period a row lists}; rows whose period is only “Unknown” come last. Exposed fields are category names only; no password or other value is printed." | D.2.5 intro (`s05:494-499`) | — |
| Group row "{domain}" / "Domain not given" + "{n} rows" | D.2.5 (`s05:477-480`) | — |
| "{Column}: {value} (all rows)." | Above a D.2.x table when a text column holds one value in every row (`app_d:184-190,287-289`) | e.g. "Status: Open (all rows)." |
| "End of register · {n} rows.[ {s} not shown (mask policy violation); {f} labels without a mask character printed as received; source headline {h}, difference {±d}, not explained by the source data.]" | D.2 end line, differences only | `d4_credentials` |
| Index content "Aggregates and all {n} of {m} register rows" | Appendix D index (`app_d:466-467`) | When D.2 is not printed: `state_message(…, 'exposed credentials')` (`app_d:599-612`, policy `states.register_messages`) |

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| state `clear` | Card only; body empty | `s05:528-529` |
| No register rows **and** headline non-zero | Headline tile + reconciliation + "No register rows are listed…" sentence; QA `data_mismatch` | `s05:532-538` |
| No register rows, no headline | "Register rows: Not available (not provided in the assessment data)." | `s05:539` |
| Row `email_domain` contains `@` or `*` | Row withheld from every count and from D.2.5; "{n} rows withheld…" note; end line "mask policy violation"; QA `mask_policy_violation` | `s05:149-152,321-323`; `app_d:457` |
| `email_state == unknown_email` or no `email_domain` | Class "Unknown Email" | `s05:128-129` |
| Mailbox domain (`email_domain` when it is a host name, else the part after '@' in `account_label_masked`) `== identity.domain` / ends with `.{domain}` / else (incl. `other_domain` / `external` with no host) | assessed / assessed_subdomain / other_domain; a subdomain such as `mail.{domain}` is never "other", even when the backend sent `other_domain` | `s05:130-134` |
| Row's categories contain a password category | Crosstab "With password"; else categories present → "Without password"; none → "Password unknown" | `s05:170` |
| Category class | policy/built-in map: password → sensitive personal → other identity (exact, then normalised, then breach-label list) → `service_recorded` (`origin`) → else unclassified + QA warn | `s05:101-111,189-191` |
| Row class (exclusive) | First present in: password, unclassified, sensitive_personal, other_identity, service_recorded_only, none_provided | `s05:33,120-122` |
| Lead count | Rows with class password on assessed domain or its subdomains | `s05:200` |
| No row on assessed domain or subdomains (but rows exist) | Lead tile label "of N listed rows are on …; all are …" (names other email domains and/or Unknown Email, whichever have rows); extra reconciliation sentence | `s05:227-229,249-252,306-311` |
| Subdomain rows with a password > 0 | " or its subdomains" in lead label | `s05:253` |
| Any row has a valid `affected_domain` | "Affected domains" table, D.2.3 domain table, D.2.5 grouping | `s05:206,276-277,347-348`; `app_d:390`; `s05:464-466` |
| Named affected domains > 30 | Table shows top 10 + "{n} other domains" row + "All {n} domains: Appendix D.2.3." | `s05:53,351-365` |
| Some rows lack a valid `affected_domain` | "Domain not given" row (last) / group; a non-empty value that is not a host also raises QA `invalid_affected_domain` (count only) | `s05:153-156,359-360,477` |
| Domain order | Assessed domain, then its subdomains, then other hosts; each by rows desc, then name; "Domain not given" last | `s05:209-213` |
| Domain latest-year cell | Year; else "Unknown" if any row flagged unknown; else "Not given" | `s05:372` |
| Subdomain crosstab row | Only when any subdomain rows | `s05:383` |
| Assessed / With password cell non-zero | Bold | `s05:384-385` |
| Year buckets | Years > A (each); A … A-4 (each, zero shown muted); "{A-5} and before"; "Unknown" (always); "Not given" (only if any) | `s05:396-412` |
| `snapshot.assessed_at` missing | A = newest row year; lead recency text omitted | `s05:401`, `s05:201,234` |
| No row has a year | Latest tile "Not available" + reason: "Period “Unknown” in source" when every yearless row is flagged Unknown, "Exposure year not given by the source" when none is, "Period “Unknown” or not given in source" for a mix | `s05:278-279,285-289` |
| Rows with both year and unknown flag | Note "… count under the year." | `s05:422-425` |
| Lead > 0 and A known | Recency note: recent = latest ≥ A-1; older as year range; unknown-only count | `s05:177-182,232-243,426-427` |
| Any row has `status` | Status note; D.2.5 Status column | `s05:218-224,468-491` |
| `unique_accounts` value set and grain `account` | "unique accounts" tile | `s05:272,280-281` |
| headline ≠ received rows | Source mismatch note | `s05:299-305` |
| `total_rows` missing / received < total | "source total not provided" note / "of {total} rows" note | `s05:312-320` |
| Payload metric value ≠ derived count | Mismatch note; `rows_org_domain` excludes subdomains only when `rows_org_subdomain` is also sent | `s05:324-340` |
| Origin rows > 0 / other-domain rows > 0 | Generated mitigation bullet(s) | `s05:506-512` |
| No `mitigations_source` and no generated bullet | Heading and bullets omitted; `attention_source` (if any) prints alone | `s05:513-515` |
| D.2 printed **and** Section 05 register pointer | Section state ∈ findings / partial / pending_review **and** analysed rows > 0 (`register_printed`); else index row only and no pointer (e.g. `none_identified` with rows) | `s05:45,292-294,542`; `app_d:408-409` |
| D.2.1 source differs | Difference note when `rows_by_field_category` is sent and any category count differs | `app_d:431-435` |
| D.2.5 sort | Newest latest year first; rows without a year after; among those, rows without `exposure_period_source` last; stable; then grouped by domain order | `s05:447-451,462-466` |
| D.2 end-line subdomain term | Omitted when 0; other terms always print | `app_d:451` |
| D.2 end-line headline difference | "; difference ±n, not explained by the source data" only when the headline ≠ rows shown | `app_d:462-465` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| received / suppressed / analysed | `len(rows)` / rows with `@`/`*` in `email_domain` / received − suppressed | `s05:149,196-197` |
| Crosstab cells | count by (email class × password / without / password unknown) | `s05:158,170` |
| Rows with a password ("include a password") | class == password | `s05:204` |
| Lead | password rows on assessed domain + subdomains | `s05:200` |
| Lead recency | recent (latest ≥ A-1), older years, unknown-only | `s05:177-182` |
| Latest exposure year | max of every row's `max(exposure_years)` | `s05:195,204` |
| Year buckets | row counted once under its latest year | `s05:176,396-412` |
| Origin rows | rows with a `service_recorded` category (`origin`) | `s05:157,174` |
| By field / by class | Counter of categories (non-exclusive) / exclusive class | `s05:171-172` |
| Domain groups | per affected domain: rows, password rows, latest year, unknown flag | `s05:183-187` |
| Share of rows (D.2.1) | `round(100 * rows / analysed)` % | `app_d:422-423` |
| Status counts | Counter of `status` as received (trimmed); rows without | `s05:218-223` |
| Differences | `signed(derived − source)` (+n / −n / ±0) | `app_d:94-95` |
| Used by other sections | 01 result line "N exposed account records" = analysed rows; 02 credential action note via `lead_metric` (policy `lists.credential_exposure.unit_rules.priority_action_text`) | `s01:320-326`; `s02:105-124`; `s05:259-265` |

## Read but never printed

| Field | Why it is read (QA, ordering, ...) |
|---|---|
| `rows[].email_domain`, `rows[].email_state` | Mailbox-provider class; mask check (withhold) |
| `rows[].exposure_years[]`, `rows[].exposure_period_has_unknown` | Buckets, recency, sort (only the counts print) |
| `rows[].id` | QA `unmasked_account_label` detail |
| `metrics[]` comparison ids (`returned_rows`, `rows_org_*`, `rows_external_domain`, `rows_unknown_email`, `rows_with_password`, `rows_period_unknown`) | Reconciliation; printed only on mismatch |
| `rows_by_field_category[]` | D.2.1 comparison; printed only on mismatch |
| `metrics[id=credential_score]` | First KPI tile "Credential score" (percent as sent) and the section 01 aspect score |
| Not read at all | `rows_by_exposure_year`, `exposure_years_source`, `aggregation_note` (kept in the payload for reconciliation, not printed), `state_label_source`, `rows[].breach_source_name`, `rows[].source_page`, register `state` / `columns` / `sanitised` / `source_pages` / `counts.returned_rows` / `counts.status` |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| `findings` | Findings | Full body; D.2 printed |
| `partial` | Partial coverage | Banner "{reason}. Counts below are lower bounds." (`app_d:120-121`), full body; D.2 printed |
| `pending_review` | Pending review | Card: reason, else policy `states.overview_messages.pending_review_banner`, else "Reason not recorded in the assessment data."; full body; D.2 printed |
| `none_identified` | None identified | Default card; body still built (rows → full body, but D.2 **not** printed and no register pointer) |
| `clear` | No findings | Card: reason (`state_reason` / `reason_code`), else `empty_state_source.text`, else the clear text above (`s05:520-524`); "What was checked" from `what_checked` / `empty_state_source.coverage`. No body; D.2 index "Not required — no exposed credentials identified." |
| `unavailable` | Unavailable | Card "{reason}. This is not a zero result." (`app_d:118-119`); no body |
| `not_assessed`, `not_applicable` | Not assessed / Not applicable | Default card; no body |

## QA checks raised

| check id | severity | when |
|---|---|---|
| `unmapped_field_category` | warn | A field category is in neither the policy map nor the breach-label list (once per category; counted as "unclassified", never as a password) (`s05:189-191`) |
| `data_mismatch` | warn | Headline non-zero but 0 register rows (`s05:533`) |
| `mask_policy_violation` | warn | Rows withheld because `email_domain` contains `@` / `*`; count only, never the value (`s05:150-152`) |
| `invalid_affected_domain` | warn | Rows whose `affected_domain` is not a host name (listed under "Domain not given"); count only (`s05:153-156`) |
| `unmasked_account_label` | warn | A D.2.5 label has no `*` / `•` (literal "Unknown Email" exempt); names row ids (`s05:467`, `qa.py:44-54`) |
| `unresolved_reference` | warn | Shared: the pointer's D.2 target did not render (README §9) |

## Backend checklist

- MUST: `state`; `register_ref` resolving to a register with `rows[]`.
- MUST per row: `id`, `account_label_masked` (already masked), `email_domain` (or `email_state: unknown_email`),
  `exposure_period_source`, `exposure_years[]` (ints), `exposure_period_has_unknown`, `exposed_field_categories[]`
  (category names only, never values).
- MUST at top level: `identity.domain`, `snapshot.assessed_at` (drives the year buckets).
- SHOULD: `metrics[id=found_headline]`, register `counts.total_rows` (else "source total not provided" + lower-bound note).
- Optional: `rows[].affected_domain` (plain host such as `app.example.com`; enables the domain table, tile, D.2.3, D.2.5 groups),
  `rows[].status`, `metrics[id=unique_accounts]` with `grain: account`, comparison metrics, `mitigations_source[]`,
  `attention_source` (under the mitigation heading, or alone when there are no bullets), `breach_source_name` NullReason, `rows_by_field_category[]`,
  `summary`, `intro_source`, `metrics[id=credential_score]` (01 only).
- Never send unmasked labels or an `email_domain` containing `@` / `*` (the row is withheld).
