# 04 Vulnerabilities

Payload key: `sections.vulnerabilities` · Module: [s04_vulnerabilities.py](../../cyberrank_report/sections/s04_vulnerabilities.py) · Shared rules: [README](README.md)

Demerit rule A. This section also holds the Email & DNS controls, IP reputation, HTTPS redirect and the active
scan. Its Appendix register D.1 is built in [app_d_evidence_registers.py](../../cyberrank_report/sections/app_d_evidence_registers.py) (`d1_assets`, `app_d:331`).

## Layout (top to bottom)

1. Opener (shared, [README §3](README.md#3-how-every-section-renders)): eyebrow "04 · ASSESSMENT DETAILS", H1 `title` (else "Vulnerabilities"), `intro_source`, state chip + `summary`. There is no `verdict()`.
2. Section state card, for card states and no-result states. With a no-result state, only the sub-checks print after the card (`build_context`, `s04:673-675`).
3. KPI strip (`metrics[]` without the per-tier ids).
4. Review-flag notes: "Review flag RF-xx: …".
5. H2 "Scanned assets": a count sentence, then a grid of host names.
6. H2 "Finding types by severity" with a severity legend on the heading line, then 4 tier lines (Critical, High, Medium, Low), then an informational/unknown note.
7. Findings summary table (no heading of its own; continuation caption "Finding types"), then a breach-likelihood note.
8. H2 "Finding details" with a severity legend, then the detail table, a coverage note and a bare-label note.
9. Register pointer: "Full register  Affected assets by finding · N rows · Appendix D, pages x–y".
10. H2 "Vulnerability scan results": a sentence, a host table, then per host "Findings on <target>" + summary + findings table + "Recommendations".
11. Sub-check blocks in this order: H2 "Email and DNS security controls", H2 "IP reputation", H2 "HTTPS redirect". Only sub-checks in the states `findings`, `partial` or `pending_review` get a block.
12. H2 "Other checks": one row per remaining sub-check (`clear`, a no-result state, or missing).
13. H2 "Related priority actions" + table + note.
14. Appendix D: index rows D.1 and D.1.2, then the D.1 register block (see the D.1 section below).

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `title`, `intro_source`, `summary`, `state`, `state_reason`, `reason_code`, `what_checked`, `next_step`, `empty_state_source` | Opener + section card (shared `default_card`) | Shared fallbacks |
| `metrics[]` (Metric) except ids `finding_types_{critical,high,medium,low,critical_high}` | KPI tiles in payload order, e.g. `vulnerability_score` "38%", `finding_types`, `asset_memberships`, `distinct_asset_labels` (`s04:662-664`) | No strip. A null value prints "Not available" + reason. |
| `metrics[id=finding_types_<tier>]` | Tier count when `findings[]` is empty. A null record → "Not available". Also used for QA. (`s04:184-195`) | With no findings: "Not available" + " Count not available (not provided in the assessment data)." |
| `metrics[id=finding_types]` | "Finding types in total: N." in the info note, and QA (`s04:205-221`) | No total sentence |
| `review_flags[]` (ids) + top-level `review_flags[] {id, text}` | Note "Review flag <id>: <text>" (`s04:665`, `text.py:271`) | Nothing. An id with no text is skipped. |
| `scanned_assets.domains[]`, `.subdomains[]` | "Scanned assets" grid (domains first, then subdomains, in payload order, monospace, 1–4 columns) (`s04:561-584`) | Block omitted. A NullReason prints H2 + "Not available (reason)." |
| `severity_legend_source[] {severity, text}` | Tier line text for `critical`/`high`/`medium`/`low` (`s04:180`, `s04:195`) | Critical/High: hardcoded text. Medium/Low: the label alone. |
| `findings[]` | Summary table + detail table, sorted Critical → High → Medium → Low → other (stable) (`s04:239-241`) | "Finding list: Not available (not provided in the assessment data)" (unless the state is `clear`) |
| `findings[].finding_id` | Summary "ID". Detail "ID …". Link/anchor key. D.1 cross-reference. | Summary blank. Detail "ID not recorded". |
| `findings[].finding_type` | "Finding" (summary, linked to the detail row). Detail code line. (`s04:247`, `s04:278`) | Summary: `finding_id`, else "Unnamed finding". Detail: "Unnamed finding". |
| `findings[].severity` | Siren icon only. The word is invisible text (`s04:250`, `s04:275`). | Unknown term: printed as text + QA |
| `findings[].affected_assets_count` | Summary "Affected domains". Detail label count. | `len(affected_assets)`, else "Not available" + footnote |
| `findings[].affected_assets[]` | Detail host list, monospace, wrapping only between hosts (`s04:260-267`) | "No affected domain recorded (count reported: N)." |
| `findings[].breach_likelihood {value, unit}` | Summary "Breach likelihood" (e.g. "38%"). Detail "Breach likelihood 38%". | NullReason `not_printed_in_source` → "Not available" |
| `findings[].rationale_source` | Detail right column, verbatim | "Rationale: Not available (not provided in the assessment data)" |
| `breach_likelihood_legend_source` | Note "Breach likelihood. <legend>" (`s04:322-326`) | Omitted |
| `breach_likelihood_note_source` | Appended to the same note | Omitted |
| `coverage_note_source` | Note under the details. A leading "Note:" is removed. (`s04:329-331`) | Omitted |
| `assets_register_ref` (dotted path, e.g. `appendices.d_evidence_registers.vulnerability_asset_register`) | Register pointer + D.1 source (`s04:302-311`) | No pointer. D.1 is not printed (index row only). |
| `<register>.counts.rows` | Pointer row count (`s04:310`) | "row count not recorded" |
| `active_scan.state` | Card when it has no result or there are no `results[]` (`s04:599-600`) | Treated as `unavailable` |
| `active_scan.results[] {target, status, scanned_at, findings_reported, findings[]}` | Host table "Host / Result / Scanned / Findings" (`s04:604-620`) | |
| `results[].target` | "Host" (monospace). Heading "Findings on <target>". | "Host not recorded" / "host not recorded" |
| `results[].status` | `clean` → "Clean" (green). `scanned` → "Scanned" (orange). Other values → printed as sent, with the unavailable icon. | "Not recorded" |
| `results[].scanned_at` (Date; `precision: minute` adds the time) | "Scanned", e.g. "01 Oct 2026 09:42" | "Not available (not provided in the assessment data)" |
| `results[].findings_reported` | "Findings": `N`, or "R reported, L listed" | The count of listed findings (`0` when none) |
| `results[].summary_label_source`, `.summary_source` | Label (leading "#" removed) + body under "Findings on …" | Omitted |
| `results[].recommendations_label_source`, `.recommendations_source[]` | Label + bullets | Label "Recommendations (as reported)" |
| `results[].findings[] {title, severity, description, impact, remediation}` | Table "# / Severity / Finding / Detail". Detail = description + "Impact: …" + "Remediation: …". | Title "Untitled finding". Severity "Not recorded". |
| `email_dns_controls` | Sub-check (see the controls rows below) | "Other checks" row: "Unavailable" + "Not included in the assessment data." |
| `email_dns_controls.controls[].control` | "Control" column | "Unnamed control" |
| `controls[].result` | Result chip (see conditional rules) | "Not recorded" |
| `controls[].line_source` | `Source: “…”` line. The text after "–" is used as the purpose for controls not in the built-in list. | Omitted |
| `controls[].<any field> = {value, …}` (e.g. `dmarc_policy`, `key_strength_bits`) | Line "<Label>: <value>" (`s04:421-425`) | "<Label>: Not available (reason)" |
| `controls[].finding_id` | Links the control to priority actions (DMARC rules) | All actions linked to section 04 are used |
| `email_dns_controls.guidance_source` | Note under the controls table, verbatim | Omitted |
| `ip_reputation.rows[] {ip_address, isp, country, abuse_score, reports}` | Table "IP address / ISP / Country / Abuse score / Reports". Every row prints. There is no cap. (`s04:461-480`) | A missing cell → "Not available" + footnote mark |
| `ip_reputation.ips_checked` | "IP addresses checked: N" (only when `rows[]` is empty) | Nothing |
| `ip_reputation.summary_source` | Card "What was checked" / clear reason. Only for states other than `findings`. | |
| `https_redirect.result` | "Result" row (`s04:483-488`) | "Not available (not provided in the assessment data)" |
| `https_redirect.narrative_source` | Body paragraph. In the `clear` / Other-checks row it is the reason. | Omitted |
| `<subcheck>.state_label_source` | `Source: “…”` (leading "#" removed): HTTPS body, and every "Other checks" row | Omitted |
| `<subcheck>.state`, `state_reason`, `reason_code`, `narrative_source`/`summary_source`, `what_checked`, `next_step` | Sub-check card or "Other checks" note (`s04:339-347`, `s04:367-381`) | A missing state counts as `findings` |
| `sections.priority_actions.actions[]` where `linked_sections` contains `vulnerabilities` | "Related priority actions" table: `rank` (else position), `priority` (siren), `title`, `required_role`, `estimated_time_reported` (`s04:514-529`) | Block omitted. Null cells: "not provided…" / role "not assigned". |
| `snapshot.assessed_at` | D.1 "Snapshot <date>" | "Not available" |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes (e.g. policy override key) |
|---|---|---|
| "Scanned assets"; `<n> domain(s) and <m> subdomain(s) were scanned; the apex domain is listed first.` | H2 + sentence (`s04:582-584`) | |
| "Finding types by severity" | H2 (`s04:234`) | |
| "Critical", "High", "Medium", "Low" + legend counts | Tier lines + legend (`s04:232`) | |
| "Exploitable weakness with direct impact; act immediately." / "Serious weakness; fix as a priority." | Critical / High tier text (`theme.py:60-63`) | Overridden by `severity_legend_source` for that tier |
| " Count not available (<reason>)." | Tier line (`s04:231`) | |
| `N informational finding type(s) are/is listed below but not counted in the four severity tiers.` | Info note (`s04:213-214`) | |
| `N finding type(s) have/has no recognised severity and are/is not counted in the tiers.` | Info note (`s04:216-217`) | |
| `Finding types in total: N.` | Info note (`s04:221`) | Only with another note sentence |
| `Finding list: Not available (not provided in the assessment data)` | Body (`s04:320`) | |
| Columns "ID", "Severity", "Finding", "Affected domains", "Breach likelihood"; caption "Finding types" | Summary table (`s04:255-257`) | |
| "Breach likelihood. " | Note prefix (`s04:325`) | |
| "Finding details"; columns "#", "Severity", "Finding", "Rationale and affected domains" | H2 + detail table (`s04:299`, `s04:328`) | |
| "Breach likelihood <v>", "ID <id>", "ID not recorded", "Unnamed finding", "<code> (cont.)" | Detail left cell (`s04:112`, `s04:278-282`) | |
| "Rationale: Not available (not provided in the assessment data)" | Detail right cell (`s04:286`) | |
| `Affected domains (showing X of N)` / `Affected domains (N)` / `Affected domains (count not recorded)` | Host-list label (`s04:291-292`) | |
| `No affected domain recorded` + ` (count reported: N)` + "." | Detail (`s04:288`) | |
| `Asset labels without a domain (<labels>) are shown as recorded in the source.` | Note (`s04:334`) | |
| "Full register", "Affected assets by finding", "row count not recorded", "Appendix D", "page reference pending" | Register pointer (`s04:311`, `components.py:422-438`) | The title is **not** read from the policy file |
| "Vulnerability scan results"; `N hosts scanned: C clean, R with findings reported.` | H2 + sentence (`s04:598`, `s04:602`) | |
| Columns "Host", "Result", "Scanned", "Findings"; "Clean", "Scanned"; "R reported, L listed" | Scan table (`s04:587`, `s04:612`, `s04:619`) | |
| "Where the reported count differs from the findings listed, the source lists fewer findings than it counts; the difference is not explained by the source data." | Note (`s04:624-625`) | |
| `Findings on <target>`; columns "#", "Severity", "Finding", "Detail"; "Informational"; "Impact: "; "Remediation: "; "Untitled finding"; "Recommendations (as reported)" | Per-host block (`s04:635-656`) | |
| "Email and DNS security controls", "IP reputation", "HTTPS redirect" | H2 titles. Anchors `s04-email-and-dns-security-controls`, `s04-ip-reputation`, `s04-https-redirect`. (`s04:355`, `s04:491-493`) | |
| Control purposes: SPF "Lists the servers allowed to send mail for the domain." · DKIM "Signs outgoing mail so receivers can verify its origin and integrity." · DMARC "Sets how receivers treat mail failing SPF or DKIM; reports spoofing." · DNSSEC "Authenticates DNS responses and protects against DNS cache poisoning." · MTA-STS "Requires encrypted (TLS) delivery for inbound mail." | First line of the control detail (`s04:19-25`) | |
| Columns "Control", "Result", "What it does and what was recorded" | Controls table (`s04:453`) | |
| Result labels: "Missing or invalid", "Redirects to HTTPS", "Does not redirect to HTTPS"; other codes are humanised (`not_enabled` → "Not enabled"); null → "Not recorded" | Control chip, HTTPS "Result", Other-checks text (`s04:17-18`, `s04:46-50`) | |
| "Policy mode (p=)", "Key strength", "<n>-bit" | Control field labels (`s04:30`, `s04:424`) | Other field labels: field name, humanised |
| "Enabled, monitoring only (p=none)" | DMARC chip (`s04:436`) | |
| `Verify the published DMARC policy (p=)` + ` before acting on priority action <rank>` + "." | Control detail (`s04:426-429`) | |
| `The recorded DMARC policy is already p=<mode>, but priority action <rank> (“<title>”) asks to raise it. The two do not agree; verify the published DMARC record before acting.` | Note (`s04:441-443`) | |
| "Not reported"; "No result for this control in the assessment data; not a pass." | Row for a missing SPF/DKIM/DMARC/DNSSEC (`s04:448-452`) | |
| "IP addresses checked: " | IP body (`s04:465`) | |
| Columns "IP address", "ISP", "Country", "Abuse score", "Reports"; "Not available"; footnote marks `* † ‡ § ¶` (doubled after 5) | IP table (`s04:144-169`, `s04:475`) | |
| `The source printed "<label>".`; "Recorded value; its meaning is not confirmed, so it is held for review."; `Recorded value held for review: <reason>.` | IP footnotes (`s04:35`, `s04:157-160`) | |
| `The source printed “-1” for the abuse score` + ` and labelled this check “<label>”` + `. What -1 means is not confirmed, so the result is held for review, not read as clean.` | IP card reason set by `adjust()` (`s04:552-553`) | |
| "Result", "Source", `“<label>”` | HTTPS key/value list (`s04:485-486`) | |
| "Other checks"; columns "Check", "Result", "Note"; "Not included in the assessment data."; "Source: “…”."; "What was checked: …"; "Next: …"; "Reason not recorded." | Other-checks table (`s04:367-381`, `s04:507-508`) | |
| "Related priority actions"; columns "#", "Priority", "Action", "Required role", "Time (reported)"; "Owners, due dates and status are listed with each action in section 02." | Actions block (`s04:524-529`) | |

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| Section state in `not_assessed`/`not_applicable`/`unavailable` | Card, then only the sub-checks that are present (no KPIs, findings, scan or actions). Missing sub-checks get no row. | `__init__.py:205-209`, `s04:673-675` |
| `findings[]` empty and section state `clear` | No severity block, tables or pointer | `s04:316-317` |
| `findings[]` empty, other states | Severity block + info note + "Finding list: Not available (…)" | `s04:318-320` |
| Tier count: the `finding_types_<tier>` metric is a null record | "Not available" + " Count not available (reason)." | `s04:185-186` |
| Tier count: `findings[]` non-empty | Count = findings with that severity. Metrics are ignored, except for QA. | `s04:187-188` |
| Tier count: no findings | Metric value, else NullReason | `s04:189-190` |
| Severity legend entry `critical_high` (or any key spanning tiers) | Ignored. Never a tier, never a KPI. | `s04:16`, `s04:663` |
| Severity `info`/`informational` | Listed with a slate siren. Not counted in the tiers. Info note. | `s04:203`, `s04:212-214` |
| Severity not recognised | Visible word in the Severity column. Note "… no recognised severity …". QA. | `s04:204`, `s04:215-219`, `icons.py:126` |
| Null summary cell in a narrow column (< 110 pt) | "Not available" + superscript, with the reason printed once below | `tables.py` `compact_table` |
| `affected_assets` empty/missing | "No affected domain recorded" (+ count when it is non-zero) | `s04:287-289` |
| `len(affected_assets) < affected_assets_count` | Label "Affected domains (showing X of N)" | `s04:291` |
| Detail row split across pages | The continuation row shows "<finding_type> (cont.)" | `s04:108-115` |
| An affected-asset label contains no "." | Bare-label note | `s04:332-334` |
| `assets_register_ref` is a string | Pointer, even when the register has no rows | `s04:303-311` |
| `scanned_assets` is a NullReason / has no names / is absent | H2 + reason / nothing / nothing | `s04:563-570` |
| `active_scan` state is a no-result state, or `results[]` is empty | H2 + state card | `s04:599-600` |
| `findings_reported` ≠ number listed | "R reported, L listed" + note + QA | `s04:611-613`, `s04:621-625` |
| Host with no findings, no summary and no recommendations | No per-host block | `s04:629-630` |
| Sub-check state (missing = `findings`) in `findings`/`partial`/`pending_review` | Full block: H2 + card (none for `findings`; `partial` = banner) + body | `s04:350-358`, `s04:502-503` |
| Sub-check is `clear`, has no result, or is missing | Row in "Other checks". A missing sub-check gets an "Unavailable" row only when the section has a result. | `s04:504-505` |
| Other-checks note text | `_brief` (controls "SPF enabled, …") + reason (or the humanised result if `clear`, else "Reason not recorded.") + Source + "What was checked" (states with a result only) + "Next" | `s04:361-381` |
| Sub-check `clear` without a reason | Reason = `narrative_source`/`summary_source`. If there is no `what_checked` → "What was checked: Not available (not provided in the assessment data)". | `s04:342-346` |
| Control result in `enabled`, `valid`, `redirects_to_https` | Green check + label | `s04:27` |
| Control result in `not_enabled`, `missing`, `missing_or_invalid`, `invalid`, `weak`, `no_redirect` | Red x + label | `s04:28-29` |
| Any other result / null | Not-recorded icon + humanised label | `s04:433-434` |
| DMARC `result: enabled` and policy `none` (`p=` prefix and case ignored) | Orange chip "Enabled, monitoring only (p=none)" | `s04:435-437` |
| DMARC `dmarc_policy` is a null record | Line "Verify the published DMARC policy (p=)…". The action rank comes from the first action linked by `finding_id`. | `s04:426-429` |
| DMARC policy `quarantine`/`reject` and a linked action (by `finding_id`, else any section-04 action with "dmarc" in the title) mentions `p=reject`, `"reject"` or `to reject` (or the same for quarantine) at a rank ≤ the recorded one | Conflict note + QA | `s04:396-409`, `s04:439-445` |
| SPF/DKIM/DMARC/DNSSEC absent from `controls[]` | "Not reported" row (never a pass). MTA-STS is not required. | `s04:31`, `s04:447-452` |
| `controls[]` empty | "Control results: Not available (not provided in the assessment data)" | `s04:414-415` |
| `ip_reputation.rows[]` empty | "IP addresses checked: N" only when `ips_checked` is set | `s04:463-465` |
| An IP cell is `{value: null, …}` | "Not available" + mark. The footnote adds `The source printed "<source_label>".` | `s04:154-158` |
| An IP cell is `{value: x, reason_code}` (value kept) | Value + mark. Footnote: the held-for-review text. | `s04:159-161` |
| An IP row value is `-1` (number or string), or a dict with `value: -1` or `source_label: "-1"` | `adjust()`: scalar `-1` → null record (`sentinel_meaning_unconfirmed`, `source_label "-1"`). IP state → `pending_review` with the generated reason. Skipped if it is already `pending_review` with a `state_reason`. | `s04:533-558` |
| No priority action linked to `vulnerabilities` | No actions block | `s04:515-517` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Tier counts (legend + lines) | Count of `findings[].severity` (case-insensitive) per tier | `s04:173-196` |
| Informational / unknown counts | `findings[]` by severity | `s04:199-222` |
| Affected domains | `affected_assets_count`, else `len(affected_assets)` | `s04:57-59` |
| Finding order | Severity rank, then payload order | `s04:239-241` |
| Scanned-asset counts | `len(domains)`, `len(subdomains)` | `s04:568-584` |
| Clean / with findings | Count of `status == clean` / the rest | `s04:601-602` |
| Listed findings per host | `len(results[].findings)` | `s04:607` |
| DMARC mode | `dmarc_policy` value, lowercased, `p=` stripped | `s04:390-393` |
| Footnote marks | One symbol per distinct reason | `s04:147-169` |

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
| `data_mismatch` | warn | `finding_types_<tier>` metric ≠ number of findings with that severity (`s04:191-194`) |
| `data_mismatch` | warn | `finding_types` ≠ findings in the 4 tiers (`s04:208-210`) |
| `data_mismatch` | warn | DMARC already at or above the level a linked action asks for (`s04:444`) |
| `data_mismatch` | warn | Active-scan `findings_reported` ≠ findings listed (`s04:621-623`) |
| `unknown_term` | warn | A finding severity is outside critical/high/medium/low/info (`s04:218`) |
| `severity_term` | warn | An unknown severity term is rendered as a siren cell, for findings, actions or D.1 (`icons.py:126`) |
| `state_adjusted` | info | The IP reputation `-1` sentinel moves the sub-check to `pending_review` (`s04:555`) |
| `min_width`, `table_header_not_repeated` | warn / error | Shared ([README §9](README.md#9-qa-checks-used-by-every-section)) |

## Appendix D.1 Affected assets by finding (`app_d_evidence_registers.py`)

| Item | Rule | Code |
|---|---|---|
| Source | `lookup(report, sections.vulnerabilities.assets_register_ref)` → `{state, counts.{rows, memberships}, rows[] {asset_label_source, finding_ids[], finding_count, max_severity}}` | `app_d:331-335` |
| Register id | `D.1` (first section in `REG_SECS` order). The IP index row is `D.1.2`. | `app_d:36-41`, `app_d:643` |
| Title | `pol('lists.vuln_affected_assets.register_title', 'Affected assets by finding')` | `app_d:336` |
| No rows | No register. The index "Content" reads `state_message(sec, '04', 'affected assets')`: for `clear`, `states.register_messages.clear` ("Not required — no affected assets identified."); for a no-result state, `states.register_messages.<state>` (built-in "Not produced."); otherwise "Not produced — no register data in the payload." | `app_d:339-340`, `app_d:598-611` |
| Row sort | `max_severity` (critical → low → other), then `finding_count` descending, then label | `app_d:341-342` |
| Columns | "#", "Highest severity" (siren), "Affected asset" (monospace), "Finding IDs" (comma-joined), "Findings" | `app_d:372-375` |
| Missing cells | Label → "Not available (asset not available)". IDs → "Not available (reason not recorded)". Count → "Not available (reason not recorded)". | `app_d:350-352` |
| Non-host label | No match for host / `host / ip` / IPv4 → label + " †". Note "† <pol('register_defaults.invalid_value_marker.note', 'value as provided by source')> (N labels are not complete host names)." | `app_d:328`, `app_d:346-348`, `app_d:377-379` |
| Opening lines | H2 "D.1  <title>" + severity legend (counts by `max_severity`). "One row per affected asset, sorted by highest severity, then number of findings, then name. Showing N of N assets." "Unit: affected assets; Findings counts finding types per asset. State: <label of register.state or section state>. Snapshot <assessed_at>." "Back to Section 04 Vulnerabilities, p. n" | `app_d:361-367`, `app_d:170-173` |
| Constant columns | A text column with the same value in every row is dropped and printed as a note "<Column>: <value> (all rows)." | `app_d:184-190`, `app_d:287-289` |
| Closing | "End of register · N rows. N of N affected assets shown; 0 not shown. Totals: M finding memberships; source register memberships X (matches / difference ±d); Section 04 affected-asset counts Y (matches / difference ±d)." | `app_d:353-360`, `app_d:380-382` |
| Computed | M = Σ `finding_count`. X = `counts.memberships`. Y = Σ `findings[].affected_assets_count`. | `app_d:353-358` |
| Index rows | D.1: state chip, "N of N affected assets", page link. D.1.2 "IP reputation" (`pol('lists.ip_reputation.register_title')`): never a register. Content from `state_message(ip_reputation, '04', 'IP addresses', len(rows))`, e.g. "Not required — all 5 IP addresses shown in Section 04." The link goes to anchor `s04-ip-reputation` when it exists, else to section 04. | `app_d:614-632`, `app_d:642-644` |
| Tiering | None: every row prints, whatever the count | `app_d:331-384` |

## Backend checklist

- MUST: `state`, `summary`, `metrics[]` (`vulnerability_score` unit `percent`, `finding_types`, `finding_types_{critical,high,medium,low}`), `findings[] {finding_id, finding_type, severity (critical/high/medium/low/info), rationale_source, affected_assets_count, affected_assets[], breach_likelihood {value, unit}}`.
- MUST for D.1: `assets_register_ref` → `appendices.d_evidence_registers.<key> {state, counts {rows, memberships}, rows[] {asset_label_source, finding_ids[], finding_count, max_severity}}`.
- MUST sub-checks (send a state + reason even when not run; a missing one prints "Unavailable"): `email_dns_controls {state, controls[] {finding_id, control, result, line_source, dmarc_policy?, key_strength_bits?}, guidance_source}` with all of SPF/DKIM/DMARC/DNSSEC; `ip_reputation {state, ips_checked, rows[] {ip_address, isp, country, abuse_score, reports}}`; `https_redirect {state, result, narrative_source, state_label_source}`.
- Use NullReasons, never `-1`, for unknown abuse scores. A raw `-1` holds the check for review.
- Optional: `severity_legend_source[]` (gives Medium/Low their tier text), `breach_likelihood_legend_source`, `breach_likelihood_note_source`, `coverage_note_source`, `scanned_assets {domains[], subdomains[]}`, `active_scan {state, results[]}`, `review_flags[]`, `what_checked`/`next_step` on sub-checks, priority actions with `linked_sections: ["vulnerabilities"]` + `linked_finding_ids`.
