# 04 Vulnerabilities

Payload key: `sections.vulnerabilities` · Module: [s04_vulnerabilities.py](../../cyberrank_report/sections/s04_vulnerabilities.py) · Shared rules: [README](README.md)

Demerit rule A. This section also holds the Email & DNS controls, IP reputation, HTTPS redirect and the active
scan. Its Appendix registers D.1 and D.1.2 are built in [app_d_evidence_registers.py](../../cyberrank_report/sections/app_d_evidence_registers.py) (`d1_assets`, `app_d:351`; `d12_ip`, `app_d:406`).

## Layout (top to bottom)

1. Opener (shared, [README §3](README.md#3-how-every-section-renders)): eyebrow "04 · ASSESSMENT DETAILS", H1 `title` (else "Vulnerabilities"), `intro_source`, state chip + `summary`. There is no `verdict()`.
2. Section state card, for card states and no-result states. With a no-result state, only the sub-checks print after the card (`build_context`, `s04:726-728`).
3. KPI strip (`metrics[]` without the per-tier ids).
4. Review-flag notes: "Review flag RF-xx: …".
5. H2 "Scanned assets": a count sentence, then a grid of host names.
6. H2 "Finding types by severity" with a severity legend on the heading line, then 4 tier lines (Critical, High, Medium, Low), then an informational/unknown note.
7. Findings summary table (no heading of its own; continuation caption "Finding types"), then a breach-likelihood note.
8. H2 "Finding details" with a severity legend, then the detail table, a coverage note and a bare-label note.
9. Register pointer: "Full register  Affected assets by finding · N rows · Appendix D, pages x–y". Only when D.1 prints (more than 30 register rows).
10. H2 "Vulnerability scan results": a sentence, a host table, then per host "Findings on <target>" + summary + findings table + "Recommendations".
11. Sub-check blocks in this order: H2 "Email and DNS security controls", H2 "IP reputation", H2 "HTTPS redirect". Only sub-checks in the states `findings`, `partial` or `pending_review` get a block. An IP list over 30 rows shows its 10 highest abuse scores and a pointer to D.1.2.
12. H2 "Other checks": one row per remaining sub-check (`clear`, a no-result state, or missing).
13. H2 "Related priority actions" with a severity legend on the heading line (action counts per priority) + table + note.
14. Appendix D: index rows D.1 and D.1.2, then the D.1 / D.1.2 register blocks when their lists are over 30 rows (see the Appendix D section below).

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `title`, `intro_source`, `summary`, `state`, `state_reason`, `reason_code`, `what_checked`, `next_step`, `empty_state_source` | Opener + section card (shared `default_card`) | Shared fallbacks |
| `metrics[]` (Metric) except ids `finding_types_{critical,high,medium,low,critical_high}` | KPI tiles in payload order, e.g. `vulnerability_score` "38%", `finding_types`, `asset_memberships`, `distinct_asset_labels` (`s04:715-717`) | No strip. A null value prints "Not available" + reason. |
| `metrics[id=finding_types_<tier>]` | Tier count when `findings[]` is empty. A null record → "Not available". Also used for QA. (`s04:190-201`) | With no findings: "Not available" + " Count not available (not provided in the assessment data)." |
| `metrics[id=finding_types]` | "Finding types in total: N." in the info note, and QA (`s04:211-227`) | No total sentence |
| `review_flags[]` (ids) + top-level `review_flags[] {id, text}` | Note "Review flag <id>: <text>" (`s04:718`, `text.py:271`) | Nothing. An id with no text is skipped. |
| `scanned_assets.domains[]`, `.subdomains[]` | "Scanned assets" grid (domains first, then subdomains, in payload order, monospace, 1–4 columns) (`s04:600-623`) | Block omitted. A NullReason prints H2 + "Not available (reason)." |
| `severity_legend_source[] {severity, text}` | Tier line text for `critical`/`high`/`medium`/`low` (`s04:186`, `s04:201`) | Hardcoded tier text (`theme.SEVERITY_TEXT`, all four tiers) |
| `findings[]` | Summary table + detail table, sorted Critical → High → Medium → Low → other (stable) (`s04:245-247`) | "Finding list: Not available (not provided in the assessment data)" (unless the state is `clear`) |
| `findings[].finding_id` | Summary "ID". Detail "ID …". Link/anchor key. D.1 cross-reference. | Summary blank. Detail "ID not recorded". |
| `findings[].finding_type` | "Finding" (summary, linked to the detail row). Detail code line. Both use `_name` (`s04:58-60`, `s04:253`, `s04:283`) | `finding_id`, else "Unnamed finding" (summary and detail alike) |
| `findings[].severity` | Siren icon only. The word is invisible text (`s04:255`, `s04:280`). | Unknown term: printed as text + QA |
| `findings[].affected_assets_count` | Summary "Affected domains". Detail label count; when fewer than the hosts listed, both numbers print and QA `data_mismatch` (`s04:296-305`). | `len(affected_assets)` (`_count`, `s04:63-65`), else "Not available" + footnote |
| `findings[].affected_assets[]` | Detail host list, monospace, wrapping only between hosts (`s04:265-272`) | "No affected domain recorded (count reported: N)." |
| `findings[].breach_likelihood {value, unit}` | Summary "Breach likelihood" (e.g. "38%"). Detail "Breach likelihood 38%". | NullReason `not_printed_in_source` → "Not available" |
| `findings[].rationale_source` | Detail right column, verbatim | "Rationale: Not available (not provided in the assessment data)" |
| `breach_likelihood_legend_source` | Note "Breach likelihood. <legend>" (`s04:331-335`) | Omitted |
| `breach_likelihood_note_source` | Appended to the same note | Omitted |
| `coverage_note_source` | Note under the details. A leading "Note:" is removed. (`s04:338-340`) | Omitted |
| `assets_register_ref` (dotted path, e.g. `appendices.d_evidence_registers.vulnerability_asset_register`) | D.1 source, read through `app_d.d1_register` by both the pointer and D.1 (`s04:315-320`, `app_d:341-348`) | No pointer. D.1 is not printed (index row only). |
| `<register>.rows[]` | Pointer row count = `len(rows)`, the number D.1 prints (`s04:320`) | No pointer |
| `active_scan.state` | Card when it has no result (`s04:638-640`) | `findings` when `results[]` has rows, else `unavailable` |
| `active_scan.results[] {target, status, scanned_at, findings_reported, findings[]}` | Host table "Host / Result / Scanned / Findings" (`s04:653-669`) | |
| `results[].target` | "Host" (monospace). Heading "Findings on <target>". | "Host not recorded" / "host not recorded" |
| `results[].status` | `clean` → "Clean" (green). `scanned` → "Scanned" (orange). Other values → printed as sent, with the unavailable icon, and counted apart in the sentence ("with no recognised status"). | "Not recorded" |
| `results[].scanned_at` (Date; `precision: minute` adds the time) | "Scanned", e.g. "01 Oct 2026 09:42" | "Not available (not provided in the assessment data)" |
| `results[].findings_reported` | "Findings": `N`, or "R reported, L listed" | The count of listed findings (`0` when none) |
| `results[].summary_label_source`, `.summary_source` | Label (leading "#" removed) + body under "Findings on …" | Omitted |
| `results[].recommendations_label_source`, `.recommendations_source[]` | Label + bullets | Label "Recommendations" |
| `results[].findings[] {title, severity, description, impact, remediation}` | Table "# / Severity / Finding / Detail". Detail = description + "Impact: …" + "Remediation: …". | Title "Untitled finding". Severity "Not recorded". |
| `email_dns_controls` | Sub-check (see the controls rows below) | "Other checks" row: "Unavailable" + "Not included in the assessment data." |
| `email_dns_controls.controls[].control` | "Control" column | "Unnamed control" |
| `controls[].result` | Result chip (see conditional rules) | "Not recorded" |
| `controls[].line_source` | `Source: “…”` line. The text after "–" is used as the purpose for controls not in the built-in list. | Omitted |
| `controls[].<any field> = {value, …}` (e.g. `dmarc_policy`, `key_strength_bits`) | Line "<Label>: <value>" (`s04:434-438`) | "<Label>: Not available (reason)" |
| `controls[].finding_id` | Links the control to priority actions (DMARC rules) | No action is cited for the DMARC verify line; the conflict check falls back to section-04 actions with "dmarc" in the title |
| `email_dns_controls.guidance_source` | Note under the controls table, verbatim | Omitted |
| `ip_reputation.rows[] {ip_address, isp, country, abuse_score, reports}` | Table "IP address / ISP / Country / Abuse score / Reports". ≤ 30 rows: every row, payload order. More: the 10 (`pol('lists.ip_reputation.top_n', 10)`) highest abuse scores (`ip_order`: held `-1` and blanks last), a "Showing …" line and a pointer to D.1.2 (`s04:474-510`) | A missing cell → "Not available" + footnote mark |
| `ip_reputation.ips_checked` | "IP addresses checked: N" (only when `rows[]` is empty) | Nothing |
| `ip_reputation.summary_source` | Card "What was checked" / clear reason. Only for states other than `findings`. | |
| `https_redirect.result` | "Result" row (`s04:513-518`) | "Not available (not provided in the assessment data)" |
| `https_redirect.narrative_source` | Body paragraph, left out when the sub-check card above already prints it as reason or "What was checked" (`s04:518-521`). In the `clear` / Other-checks row it is the reason. | Omitted |
| `<subcheck>.state_label_source` | `Source: “…”` (leading "#" removed): HTTPS body, and every "Other checks" row | Omitted |
| `<subcheck>.state`, `state_reason`, `reason_code`, `narrative_source`/`summary_source`, `what_checked`, `next_step` | Sub-check card or "Other checks" note (`s04:348-356`, `s04:376-390`) | A missing state counts as `findings` |
| `sections.priority_actions.actions[]` where `linked_sections` contains `vulnerabilities` | "Related priority actions" table: `rank` (else position), `priority` (siren; legend on the heading line), `title`, `required_role`, `estimated_time_reported` (`s04:547-564`) | Block omitted. Null cells: "not provided…" / role "not assigned". |
| `snapshot.assessed_at` | D.1 "Snapshot <date>" | "Not available" |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes (e.g. policy override key) |
|---|---|---|
| "Scanned assets"; `<n> domain(s) and <m> subdomain(s) were scanned` + `; domains are listed before subdomains` (only when both lists have names) + "." | H2 + sentence (`s04:620-623`) | |
| "Finding types by severity" | H2 (`s04:240`) | |
| "Critical", "High", "Medium", "Low" + legend counts | Tier lines + legend (`s04:238`) | |
| "Exploitable weakness with direct impact; act immediately." / "Serious weakness; fix as a priority." / "Weakness that adds risk; fix in planned work." / "Minor weakness; fix when convenient." | Critical / High / Medium / Low tier text (`theme.py:60-65`) | Overridden by `severity_legend_source` for that tier |
| " Count not available (<reason>)." | Tier line (`s04:237`) | |
| `N informational finding type(s) are/is listed below but not counted in the four severity tiers.` | Info note (`s04:219-220`) | |
| `N finding type(s) have/has no recognised severity and are/is not counted in the tiers.` | Info note (`s04:222-223`) | |
| `Finding types in total: N.` | Info note (`s04:227`) | Only with another note sentence |
| `Finding list: Not available (not provided in the assessment data)` | Body (`s04:329`) | |
| Columns "ID", "Severity", "Finding", "Affected domains", "Breach likelihood"; caption "Finding types" | Summary table (`s04:260-262`) | |
| "Breach likelihood. " | Note prefix (`s04:334`) | |
| "Finding details"; columns "#", "Severity", "Finding", "Rationale and affected domains" | H2 + detail table (`s04:312`, `s04:337`) | |
| "Breach likelihood <v>", "ID <id>", "ID not recorded", "Unnamed finding", "<code> (cont.)" | Detail left cell (`s04:118`, `s04:283-287`) | |
| "Rationale: Not available (not provided in the assessment data)" | Detail right cell (`s04:291`) | |
| `Affected domains (showing X of N)` / `Affected domains (N)` / `Affected domains (L listed; count reported: N)` | Host-list label (`s04:296-305`) | |
| `No affected domain recorded` + ` (count reported: N)` + "." | Detail (`s04:293`) | |
| `Asset labels without a domain (<labels>) are shown as recorded in the source.` | Note (`s04:343`) | |
| "Full register", "row count not recorded", "Appendix D", "page reference pending" | Register pointer (`s04:320`, `s04:494-495`, `components.py:422-438`) | Title from `pol('lists.vuln_affected_assets.register_title')` / `pol('lists.ip_reputation.register_title')`, the same as D.1 / D.1.2 |
| "Vulnerability scan results"; `N host(s) scanned: C clean, S with findings reported` + `, U with no recognised status` + "."; `Host results: Not available (not provided in the assessment data)` | H2 + sentence (`s04:637`, `s04:645-651`) | |
| Columns "Host", "Result", "Scanned", "Findings"; "Clean", "Scanned"; "R reported, L listed" | Scan table (`s04:626`, `s04:661`, `s04:668`) | |
| `Where the reported count differs from the findings listed, the source <how>; the difference is not explained by the source data.` — <how> is "lists fewer findings than it counts", "lists more findings than it counts" or "lists fewer findings than it counts for some hosts and more for others" | Note (`s04:673-678`) | |
| `Findings on <target>`; columns "#", "Severity", "Finding", "Detail"; "Informational"; "Impact: "; "Remediation: "; "Untitled finding"; "Recommendations" | Per-host block (`s04:684-709`) | |
| "Email and DNS security controls", "IP reputation", "HTTPS redirect" | H2 titles. Anchors `s04-email-and-dns-security-controls`, `s04-ip-reputation`, `s04-https-redirect`. (`s04:364`, `s04:524-526`) | |
| Control purposes: SPF "Lists the servers allowed to send mail for the domain." · DKIM "Signs outgoing mail so receivers can verify its origin and integrity." · DMARC "Sets how receivers treat mail failing SPF or DKIM; reports spoofing." · DNSSEC "Authenticates DNS responses and protects against DNS cache poisoning." · MTA-STS "Requires encrypted (TLS) delivery for inbound mail." | First line of the control detail (`s04:20-26`) | |
| Columns "Control", "Result", "What it does and what was recorded" | Controls table (`s04:466`) | |
| Result labels: "Missing or invalid", "Redirects to HTTPS", "Does not redirect to HTTPS"; other codes are humanised (`not_enabled` → "Not enabled"); null → "Not recorded" | Control chip, HTTPS "Result", Other-checks text (`s04:18-19`, `s04:47-51`) | |
| "Policy mode (p=)", "Key strength", "<n>-bit" | Control field labels (`s04:31`, `s04:437`) | Other field labels: field name, humanised |
| "Enabled, monitoring only (p=none)" | DMARC chip (`s04:449`) | |
| `Verify the published DMARC policy (p=)` + ` before acting on priority action <rank>` + "." | Control detail (`s04:439-442`) | |
| `The recorded DMARC policy is already p=<mode>, but priority action <rank> (“<title>”) asks to raise it. The two do not agree; verify the published DMARC record before acting.` | Note (`s04:454-456`) | |
| "Not reported"; "No result for this control in the assessment data; not a pass." | Row for a missing SPF/DKIM/DMARC/DNSSEC (`s04:461-465`) | |
| "IP addresses checked: " | IP body (`s04:487`) | |
| Columns "IP address", "ISP", "Country", "Abuse score", "Reports"; "Not available"; footnote marks `* † ‡ § ¶` (doubled after 5) | IP table (`s04:150-175`, `s04:505`) | |
| `The source printed "<label>".`; "Recorded value; its meaning is not confirmed, so it is held for review."; `Recorded value held for review: <reason>.` | IP footnotes (`s04:36`, `s04:163-166`) | |
| `The source printed “-1” for the <columns>` (the columns that carry it, e.g. "abuse score and reports") + ` and labelled this check “<label>”` + `. What -1 means is not confirmed, so the result is held for review, not read as clean.` | IP card reason set by `adjust()` (`s04:589-592`) | |
| `Showing the N highest abuse scores of M IP addresses; D.1.2 lists every row.` | IP body over 30 rows (`s04:492`) | |
| "Result", "Source", `“<label>”` | HTTPS key/value list (`s04:515-516`) | |
| "Other checks"; columns "Check", "Result", "Note"; "Not included in the assessment data."; "Source: “…”."; "What was checked: …"; "Next: …"; "Reason not recorded." | Other-checks table (`s04:376-390`, `s04:540-541`) | |
| "Related priority actions" + severity legend; columns "#", "Priority", "Action", "Required role", "Time"; "Owners, due dates and status are listed with each action in section 02." | Actions block (`s04:557-564`) | |

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| Section state in `not_assessed`/`not_applicable`/`unavailable` | Card, then only the sub-checks that are present (no KPIs, findings, scan or actions). Missing sub-checks get no row. | `__init__.py:205-209`, `s04:726-728` |
| `findings[]` empty and section state `clear` | No severity block, tables or pointer | `s04:325-326` |
| `findings[]` empty, other states | Severity block + info note + "Finding list: Not available (…)" | `s04:327-329` |
| Tier count: the `finding_types_<tier>` metric is a null record | "Not available" + " Count not available (reason)." | `s04:191-192` |
| Tier count: `findings[]` non-empty | Count = findings with that severity. Metrics are ignored, except for QA. | `s04:193-194` |
| Tier count: no findings | Metric value, else NullReason | `s04:195-196` |
| Severity legend entry `critical_high` (or any key spanning tiers) | Ignored. Never a tier, never a KPI. | `s04:17`, `s04:716` |
| Severity `info`/`informational` | Listed with a slate siren. Not counted in the tiers. Info note. | `s04:209`, `s04:218-220` |
| Severity not recognised | Visible word in the Severity column. Note "… no recognised severity …". QA. | `s04:210`, `s04:221-225`, `icons.py:126` |
| Null summary cell in a narrow column (< 110 pt) | "Not available" + superscript, with the reason printed once below | `tables.py` `compact_table` |
| `affected_assets` empty/missing | "No affected domain recorded" (+ count when it is non-zero) | `s04:292-294` |
| `len(affected_assets) < affected_assets_count` | Label "Affected domains (showing X of N)" | `s04:301-303` |
| `len(affected_assets) > affected_assets_count` | Label "Affected domains (L listed; count reported: N)" + QA `data_mismatch` | `s04:297-300` |
| `affected_assets_count` absent | Label "Affected domains (L)" (the listed hosts) | `s04:304-305` |
| Detail row split across pages | The continuation row shows "<finding_type> (cont.)" | `s04:114-121` |
| An affected-asset label contains no "." | Bare-label note | `s04:341-343` |
| D.1 register has more than 30 rows (`D.tier`) | Pointer to D.1. No rows, or ≤ 30 rows: no pointer (D.1 is then an index row only). | `s04:315-320` |
| `scanned_assets` is a NullReason / has no names / is absent | H2 + reason / nothing / nothing | `s04:602-609` |
| `active_scan` state is a no-result state | H2 + state card | `s04:638-640` |
| `active_scan.results[]` empty, state `clear` | H2 + "No findings" card | `s04:643-644` |
| `active_scan.results[]` empty, other states | "Host results: Not available (…)" line; a card above it only when the payload gives a reason (never for `findings`) | `s04:641-646` |
| `findings_reported` ≠ number listed | "R reported, L listed" + note + QA | `s04:660-662`, `s04:670-674` |
| Host with no findings, no summary and no recommendations | No per-host block | `s04:682-683` |
| Sub-check state (missing = `findings`) in `findings`/`partial`/`pending_review` | Full block: H2 + card (none for `findings`; `partial` = banner) + body | `s04:359-367`, `s04:535-536` |
| Sub-check is `clear`, has no result, or is missing | Row in "Other checks". A missing sub-check gets an "Unavailable" row only when the section has a result. | `s04:537-538` |
| Other-checks note text | `_brief` (controls "SPF enabled, …") + reason (or the humanised result if `clear`, else "Reason not recorded.") + Source + "What was checked" (states with a result only) + "Next" | `s04:370-390` |
| Sub-check `clear` without a reason | Reason = `narrative_source`/`summary_source`. If there is no `what_checked` → "What was checked: Not available (not provided in the assessment data)". | `s04:351-355` |
| Control result in `enabled`, `valid`, `redirects_to_https` | Green check + label | `s04:28` |
| Control result in `not_enabled`, `missing`, `missing_or_invalid`, `invalid`, `weak`, `no_redirect` | Red x + label | `s04:29-30` |
| Any other result / null | Not-recorded icon + humanised label | `s04:446-447` |
| DMARC `result: enabled` and policy `none` (`p=` prefix and case ignored) | Orange chip "Enabled, monitoring only (p=none)" | `s04:448-450` |
| DMARC `dmarc_policy` is a null record | Line "Verify the published DMARC policy (p=)…". The action rank comes from the first action linked by `finding_id`; a control without `finding_id` cites no action. | `s04:393-400`, `s04:439-442` |
| DMARC policy `quarantine`/`reject` and a linked action (by `finding_id`, else any section-04 action with "dmarc" in the title) mentions `p=reject`, `"reject"` or `to reject` (or the same for quarantine) at a rank ≤ the recorded one | Conflict note + QA | `s04:409-422`, `s04:452-458` |
| SPF/DKIM/DMARC/DNSSEC absent from `controls[]` | "Not reported" row (never a pass). MTA-STS is not required. | `s04:32`, `s04:460-465` |
| `controls[]` empty | "Control results: Not available (not provided in the assessment data)" | `s04:427-428` |
| `ip_reputation.rows[]` empty | "IP addresses checked: N" only when `ips_checked` is set | `s04:485-487` |
| `ip_reputation.rows[]` over 30 (`D.tier`) | 10 highest abuse scores + "Showing …" line + pointer to D.1.2 | `s04:488-495` |
| An IP cell is `{value: null, …}` | "Not available" + mark. The footnote adds `The source printed "<source_label>".` | `s04:160-164` |
| An IP cell is `{value: x, reason_code}` (value kept) | Value + mark. Footnote: the held-for-review text. | `s04:165-167` |
| An IP row value is `-1` (number or string), or a dict with `value: -1` | `adjust()`: the cell → null record (`sentinel_meaning_unconfirmed`, `source_label "-1"`); a null record with `source_label "-1"` stays. IP state → `pending_review` with the generated reason naming the columns. When the check is already `pending_review` with a `state_reason`, the cells are still replaced and that reason stays. | `s04:568-597` |
| No priority action linked to `vulnerabilities` | No actions block | `s04:548-550` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Tier counts (legend + lines) | Count of `findings[].severity` (case-insensitive) per tier | `s04:179-202` |
| Informational / unknown counts | `findings[]` by severity | `s04:205-228` |
| Affected domains | `affected_assets_count`, else `len(affected_assets)` | `s04:63-65` |
| Finding order | Severity rank, then payload order | `s04:245-247` |
| Scanned-asset counts | `len(domains)`, `len(subdomains)` | `s04:607-623` |
| Clean / with findings / no recognised status | Count of `status == clean` / `status == scanned` / the rest | `s04:647-651` |
| IP order (over 30 rows) | `abuse_score` descending; held `-1` and blanks last | `s04:474-480` |
| Listed findings per host | `len(results[].findings)` | `s04:656` |
| DMARC mode | `dmarc_policy` value, lowercased, `p=` stripped | `s04:403-406` |
| Footnote marks | One symbol per distinct reason | `s04:153-175` |

## Read but never printed

| Field | Why it is read (QA, ordering, ...) |
|---|---|
| `metrics[id=finding_types_{tier}]` | QA `data_mismatch`. Tier count only when there are no findings. |
| `controls[].finding_id` | Matching priority actions |
| `priority_actions.actions[].action_required_source`, `linked_finding_ids`, `action_id` | DMARC conflict detection, filtering, QA detail |
| `ip_reputation.state_label_source` | Sentinel reason text (`adjust`). Also printed in an Other-checks row. |
| Not read at all | `state_label_source` (section), `severity_legend_source[].label`, `findings[].severity_label_source`, `breach_likelihood.{likelihood_type, source_label}`, `controls[].state`, `controls[].status_label_source`, `controls[].review_flags`, `ip_reputation.review_flags`, `https_redirect.review_flags`, `scanned_assets.title_source`, `active_scan.results[].findings[].severity_label_source`, `<register>.columns` |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| `findings` | Findings | No card. Full body. |
| `clear` | No findings | Card (`state_reason` / `empty_state_source.text`, coverage). KPIs, scanned assets, scan, sub-checks and actions print. The findings block is skipped when the list is empty. |
| `partial` | Partial coverage | Banner + full body |
| `pending_review` | Pending review | Card "Result held for review" (e.g. `count_unreconciled` → "Counts do not reconcile; held for review.") + full body |
| `not_assessed` / `not_applicable` / `unavailable` | Not assessed / Not applicable / Unavailable | Card + present sub-checks only |
| `none_identified` | None identified | Card + body |
| Sub-check `findings` | No chip (H2 + body) | Full block |
| Sub-check `partial` / `pending_review` | Banner / card "Result held for review" | Full block |
| Sub-check `clear` / no-result / missing | Chip in the Other-checks "Result" column ("No findings", "Unavailable", …) | Row only |

## QA checks raised

| check id | severity | when |
|---|---|---|
| `data_mismatch` | warn | `finding_types_<tier>` metric ≠ number of findings with that severity (`s04:197-200`) |
| `data_mismatch` | warn | `finding_types` ≠ findings in the 4 tiers (`s04:214-216`) |
| `data_mismatch` | warn | DMARC already at or above the level a linked action asks for (`s04:457`) |
| `data_mismatch` | warn | Active-scan `findings_reported` ≠ findings listed (`s04:670-672`) |
| `data_mismatch` | warn | A finding lists more affected domains than `affected_assets_count` (`s04:297-299`) |
| `unknown_term` | warn | A finding severity is outside critical/high/medium/low/info (`s04:224`) |
| `severity_term` | warn | An unknown severity term is rendered as a siren cell, for findings, actions or D.1 (`icons.py:126`) |
| `state_adjusted` | info | The IP reputation `-1` sentinel moves the sub-check to `pending_review` (`s04:593-595`) |
| `min_width`, `table_header_not_repeated` | warn / error | Shared ([README §9](README.md#9-qa-checks-used-by-every-section)) |

## Appendix D.1 Affected assets by finding and D.1.2 IP reputation (`app_d_evidence_registers.py`)

| Item | Rule | Code |
|---|---|---|
| Source | `d1_register(report)`: `lookup(report, sections.vulnerabilities.assets_register_ref)` → `{state, counts.{rows, memberships}, rows[] {asset_label_source, finding_ids[], finding_count, max_severity}}`. The Section 04 pointer reads the same function. | `app_d:341-348` |
| Register id | `D.1` (first section in `REG_SECS` order). The IP register is `D.1.2`. | `app_d:37-42`, `app_d:697` |
| Title | `pol('lists.vuln_affected_assets.register_title', 'Affected assets by finding')` | `app_d:348` |
| Long-list rule | `tier(rows, rows)`: ≤ 30 rows (`tiers.T1_inline.max_visual_rows`) → no register, index row only, because Section 04 lists every affected domain in its finding details. More → full register. | `app_d:357-358`, `app_d:80-84` |
| No register | The index "Content" reads `state_message(sec, '04', 'affected assets', rows or None)`: for `clear`, `states.register_messages.clear` ("Not required — no affected assets identified."); for a no-result state, `states.register_messages.<state>` (built-in "Not produced."); ≤ 30 rows → "Not required — all N affected assets shown in Section 04."; no rows → "Not produced — no register data in the payload." | `app_d:357-358`, `app_d:655-668` |
| Row sort | `max_severity` (critical → low → other), then `finding_count` descending, then label | `app_d:359-360` |
| Columns | "#", "Highest severity" (siren), "Affected asset" (monospace), "Finding IDs" (comma-joined), "Findings" | `app_d:391-394` |
| Missing cells | Label → "Not available (asset not available)". IDs → "Not available (not provided in the assessment data)". Count → "Not available (reason not recorded)". | `app_d:368-371` |
| Non-host label | Not a host name, `host / ip`, or bare IPv4 / IPv6 address (`_hostlike`) → label + " †". Note "† <pol('register_defaults.invalid_value_marker.note', 'value as provided by source')> (N labels are not complete host names)." | `app_d:329-338`, `app_d:364-366`, `app_d:396-398` |
| Opening lines | H2 "D.1  <title>" + severity legend (counts by `max_severity`). "One row per affected asset, sorted by highest severity, then number of findings, then name. Showing N of N assets." "Unit: affected assets; Findings counts finding types per asset. State: <label of register.state or section state>. Snapshot <assessed_at>." "Back to Section 04 Vulnerabilities, p. n" | `app_d:380-386`, `app_d:171-174` |
| Constant columns | A text column with the same value in every row is dropped and printed as a note "<Column>: <value> (all rows)." | `app_d:185-191`, `app_d:288-290` |
| Closing | "End of register · N rows. N of N affected assets shown; 0 not shown. Totals: M finding memberships; source register memberships X (matches / difference ±d); Section 04 affected-asset counts Y (matches / difference ±d)." | `app_d:372-379`, `app_d:399-401` |
| Computed | M = Σ `finding_count`. X = `counts.memberships`. Y = Σ `_count(finding)` (`affected_assets_count`, else `len(affected_assets)`: the Section 04 number). | `app_d:372-377` |
| D.1.2 source | `sections.vulnerabilities.ip_reputation.rows[]` (after `adjust()`), ordered by `s04.ip_order` | `app_d:406-418` |
| D.1.2 rule | Printed only when the IP check state is `findings` / `partial` / `pending_review` and it has more than 30 rows; Section 04 then shows the first 10 in the same order and points here. | `app_d:417-418` |
| D.1.2 index | `ip_reputation` missing → state "Unavailable", "Not produced — IP reputation is not in the payload." Otherwise `state_message(ip_reputation, '04', 'IP addresses', rows or None)`, e.g. "Not required — all 5 IP addresses shown in Section 04." The link goes to anchor `s04-ip-reputation` when it exists, else to section 04. | `app_d:412-418`, `app_d:676-689` |
| D.1.2 register | H2 "D.1.2  IP reputation". "One row per IP address, sorted by abuse score, highest first; scores held for review and blanks last. Showing N of N IP addresses." Columns "#", "IP address" (monospace), "ISP", "Country", "Abuse score", "Reports". A held `-1` cell prints "-1 (meaning unconfirmed)" (policy `register_columns[abuse_score].sentinel`). Closing "End of register · N rows. N of N IP addresses shown; 0 not shown. Section 04 shows the first 10." | `app_d:419-441` |

## Backend checklist

- MUST: `state`, `summary`, `metrics[]` (`vulnerability_score` unit `percent`, `finding_types`, `finding_types_{critical,high,medium,low}`), `findings[] {finding_id, finding_type, severity (critical/high/medium/low/info), rationale_source, affected_assets_count, affected_assets[], breach_likelihood {value, unit}}`.
- MUST for D.1: `assets_register_ref` → `appendices.d_evidence_registers.<key> {state, counts {rows, memberships}, rows[] {asset_label_source, finding_ids[], finding_count, max_severity}}`.
- MUST sub-checks (send a state + reason even when not run; a missing one prints "Unavailable"): `email_dns_controls {state, controls[] {finding_id, control, result, line_source, dmarc_policy?, key_strength_bits?}, guidance_source}` with all of SPF/DKIM/DMARC/DNSSEC; `ip_reputation {state, ips_checked, rows[] {ip_address, isp, country, abuse_score, reports}}`; `https_redirect {state, result, narrative_source, state_label_source}`.
- Use NullReasons, never `-1`, for unknown abuse scores. A raw `-1` holds the check for review.
- Optional: `severity_legend_source[]` (gives Medium/Low their tier text), `breach_likelihood_legend_source`, `breach_likelihood_note_source`, `coverage_note_source`, `scanned_assets {domains[], subdomains[]}`, `active_scan {state, results[]}`, `review_flags[]`, `what_checked`/`next_step` on sub-checks, priority actions with `linked_sections: ["vulnerabilities"]` + `linked_finding_ids`.
