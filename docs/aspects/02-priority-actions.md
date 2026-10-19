# 02 Priority actions

Payload key: `sections.priority_actions` · Module: [s02_priority_actions.py](../../cyberrank_report/sections/s02_priority_actions.py) · Shared rules: [README](README.md)

Also reads linked sections (`linked_sections[]`), `sections.certifications.certificates[]`,
`sections.credential_exposure` + its register, and `identity.domain`. No module hooks besides `build`
(no `card`, `verdict`, `adjust`, `build_context`).

## Layout (top to bottom)

1. Opener (shared): eyebrow "02 · OVERVIEW AND PRIORITIES", H1 `title`, `intro_source`, state chip ("Identified" for `findings`) + `summary`.
2. State card or banner (shared; only for non-`findings` states).
3. KPI strip: "Total", optional "Critical priority" (only when an action has it), "High priority", "Medium priority", "Low priority", optional "Priority not rated" (all in "actions").
4. Action table, columns "#", "Priority" (siren only), "Action", "Effort", "Team"; one row per action, sorted by `rank` (`action_rows`; 01's Next pointer counts the same rows). Null Effort/Team cells print "Not available¹" with the reason once under the table.
5. Note paragraph: shared owner/due/status gaps, held-for-review sentence, payload `note` (omitted when all are empty).
6. "Projected rating after remediation" (H2, optional; `title` / `title_source` when sent): `caption_source` note, key/value rows, narrative, note, review flags.

With no actions, 3–6 are replaced by one body sentence, or by nothing when the state card above already prints the reason.

Action cell, line by line:

1. **Title** (bold): `title`, else `title_source` verbatim.
2. Action text, or "Described in <section ref> (<item label>)." when that text already appears in a linked section.
3. Muted "Note: …" (credential unit rule, only when it applies).
4. Muted `derived` text (only the generator-added certificate action carries it).
5. Muted "Why it matters: …".
6. Muted "Verify first: …" (one line per check).
7. Muted "Owner …  ·  Due …  ·  Status …".
8. Muted "See <section ref>, <section ref>".

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `title`, `intro_source`, `summary` | H1, intro, verdict | Title "Priority actions"; others omitted |
| `state`, `state_reason`, `reason_code` | Chip/card (shared); body sentence when there are no actions | "No priority actions are listed in the assessment data." |
| `actions[]` (dicts only) | One table row each | No-actions sentence |
| `actions[].rank` | Sort key (numbers first, ascending; others keep order at the end); "#" column | "#" = position after sorting |
| `actions[].priority` (`high`/`medium`/`low`, also `critical`) | Siren icon; KPI tier count ("Critical priority" tile only when present) | Visible "Not rated"; unknown word prints as given + QA `severity_term` |
| `actions[].title` → `title_source` | Line 1, bold (`title_source` verbatim when there is no `title`) | "Untitled action" |
| `actions[].action_required_source` (string or `{value}`) | Line 2 verbatim; wrapped in "Source: “…”" when the unit-rule note applies | "Not available (<reason>)" from `action_required_source` or `action_required` when that is a null record; else "Not available (reason not recorded)" |
| `actions[].why_this_matters_source` | "Why it matters: …" | Line omitted (a null is never printed) |
| `actions[].owner`, `due_at`, `status` | "Owner <v>  ·  Due <date>  ·  Status <v>"; `due_at` with `precision` → `02 Oct 2026` | Null → "Owner <reason>", unless the reason is shared (see Conditional rules); key absent → part omitted |
| `actions[].estimated_time_reported` → `estimated_time` | "Effort" column | "Not available¹" + footnote (default reason `not_printed_in_source`) |
| `actions[].required_role` | "Team" column | "Not available¹" + footnote |
| `actions[].linked_sections[]` (registry keys) | "See <nn Title, page n>" links; duplicate-text check; verify-first; unit rule | Unknown keys ignored; no "See" line |
| `actions[].linked_finding_ids[]` | Looked up in linked sections for "Verify first" | No finding check |
| `actions[].review_flags[]` | Only non-empty-ness: held-for-review sentence | — |
| `actions[].derived` | Muted line, verbatim | Omitted |
| `note` | Appended verbatim to the note under the table | Omitted |
| `remediation_impact.title` → `title_source` | H2, verbatim (e.g. "Projected Rating After Remediation") | "Projected rating after remediation" |
| `remediation_impact.caption_source` | Note under the H2, verbatim | Omitted |
| `remediation_impact.current/projected {grade, score, pool}` | "BB · score 196 / 360" (or the grade alone when score/pool missing) | No grade → "Not available (not provided in the assessment data)"; both missing → "Not available¹" + one footnote |
| `remediation_impact.points_recoverable` | "Recoverable": "94 points" | Row omitted |
| `remediation_impact.active_issues.total/privacy/vulnerability` | "Active issues": "18 (6 privacy + 12 vulnerability)"; a non-number prints as given | Row omitted without `total`; parts omitted when null |
| `remediation_impact.active_issues.credentials` | "Exposed credentials": n (+ separation note) | Row omitted |
| `remediation_impact.narrative_source` | Body paragraph, verbatim | Omitted |
| `remediation_impact.conditional_on_rescan` | Adds the rescan sentence to the note | Sentence omitted |
| `remediation_impact.review_flags[]` + top-level `review_flags[]` | "Review flag RF-x: <text>" | Omitted |
| `sections.certifications.state`, `.certificates[] {origin, approval_state, standard}` | Generator-added action (see Computed) | No added action (also when 13 is `not_assessed`/`not_applicable`/`unavailable`) |
| `sections.credential_exposure.register_ref` rows, `identity.domain` | N and domain of the unit-rule note | No note |
| Linked section objects `{finding_id, state, control \| finding_type \| label, <null fields>}` | "Verify first" lines | No line |
| Linked section `metrics[]` with `count_kind`/`id` `reported_headline`, `returned_rows`, `unique_accounts` | "Verify first" count caveat | No line |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes |
|---|---|---|
| "Total", "Critical priority", "High priority", "Medium priority", "Low priority", "Priority not rated"; unit "action(s)" | KPI strip | `:234-239` |
| "#", "Priority", "Action", "Effort", "Team" | Table header | `:220` |
| "Untitled action" | Action title fallback | `:154` |
| "Described in <ref>." / "Described in <ref> (<label>)." | Line 2 when the text is duplicated | `:162` |
| "Source: “<text>”" | Line 2 when the unit rule applies | `:165` |
| "Note: Verify and reset the accounts behind {N} rows on {assessed_domain} that list a password category. The source counts accounts; the register lists rows, not unique accounts." | Unit-rule note | First sentence: policy key `lists.credential_exposure.unit_rules.priority_action_text`; second sentence fixed (`:169`); "the assessed domain" when no domain (`:124`) |
| "Why it matters: " | Line 5 prefix | `:175` |
| "Verify first: " + "<Name> <field> is not available (<reason>)." / "<Name>: <reason>." | Line 6 | `:76-78` |
| "<N> is the source headline[ (unit not defined)]; <n> register rows listed; unique accounts: <v>." | Line 6 count caveat | `_count_check :88-103` |
| "Owner ", "Due ", "Status ", separator "  ·  " | Line 7 | `WHO :16`, `:181` |
| "See " | Line 8 | `:184` |
| "For every action: <field reason>, …." / "Where not shown: <field reason>, …." (e.g. "owner not assigned") | Note under table | `:243-245` |
| "Wording and figures of action(s) <ranks> are as reported and held for review." | Note under table | `:249` |
| "No priority actions are listed in the assessment data." | Body, no actions | `:259` |
| "Review system-detected certificates", "Cyberrank admin", "Added by this report from the certificate records; not part of the assessment action list.", "{n} system-detected certificate(s) ({standards}) is/are awaiting approval. Check the source, then approve or reject it/each in Cyberrank." | Added action | `_cert_review :188-198`, `s13.review_text :181` |
| "Projected rating after remediation" | H2 fallback | `:297` |
| "Current rating", "Projected rating", "Recoverable", "Active issues", "Exposed credentials" | Remediation key/value | `:282-296` |
| "<grade> · score <s> / <pool>", "points", "(<p> privacy + <v> vulnerability)", "(counted separately; not part of the active issues)" | Remediation values | `:275`, `:284-296` |
| "Projection as reported by the source, not a commitment." | Remediation note, always | `:302` |
| "Vulnerability fixes count only after a fresh scan confirms them." | Remediation note | `:304` |
| "Not available (<reason>)", "Not available¹" | Nulls | shared (README §5) |

Policy overrides: `lists.credential_exposure.unit_rules.priority_action_text` (note text);
`lists.credential_exposure.data_class_map` (which field categories count as "password" for N).

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| No dict in `actions[]` and no certificate awaiting approval | Body: `state_reason` → reason of `reason_code` → "No priority actions are listed in the assessment data." (no KPI, table, notes or remediation block) | `:256-259` |
| …and the state has a card (`clear`, `partial`, `pending_review`, `none_identified`) and a reason | No body sentence: the card already prints the reason | `:258` |
| `sections.certifications` has records with `origin` `detected` (or legacy `approved`/`team_approved`) and `approval_state` `pending`/`pending_approval`/`awaiting_approval` | One low-priority action appended last (rank = payload count + 1) | `_cert_review :188`, `s13.awaiting_review :175` |
| `sections.certifications.state` is `not_assessed`/`not_applicable`/`unavailable` | No added action (13 prints no Next step) | `:192` |
| A priority not in critical/high/medium/low (empty, other) | Extra KPI "Priority not rated" | `:237-239` |
| An action with priority `critical` | "Critical priority" tile before "High priority" | `:235-236` |
| `priority` empty | Visible "Not rated" label in the Priority cell | `icons.severity_cell` |
| `action_required_source` text is a substring of any string inside a linked section's data | "Described in <ref>[ (<label of the object holding it>)]." instead of the text; that section drops out of "See" | `:158-162`, `:182` |
| Linked to `credential_exposure`, its register has rows, a source sentence matches "<number> [word] account(s)", and N > 0 | Text becomes "Source: “…”" + the unit-rule note | `_unit_rule :106-126` |
| N = 0 or no register rows or the source does not count accounts | No note, text plain | `:117-125` |
| Linked finding found and its `state` is not `findings`/`clear`/null | "Verify first" with its first null field, else "<name>: <reason>"; one per finding id | `:65-79` |
| Linked section has a non-null `reported_headline` metric plus `returned_rows` or `unique_accounts` | "Verify first" count caveat; "(unit not defined)" when its `unit` contains "unverified" | `:88-103` |
| Owner/due/status null on several actions with one shared reason | Rows omit that null; note "For every action: …" (null on every action) or "Where not shown: …" | `_shared_gaps :137`, `:179`, `:243-245` |
| Nulls on one field carry different reasons | Each row prints "Owner <reason>" | `:142-145` |
| `due_at` is `{value: "YYYY…", precision}` | Formatted date | `:132-133` |
| Action has `review_flags` and no "Verify first" line | Ranks listed in the held-for-review sentence | `:246-250` |
| No shared gap, held action or `note` | No note paragraph | `:253-254` |
| Row taller than `KEEP_MAX_H` | Row may split across pages; others move whole | `:223-225` |
| `remediation_impact` absent, null record, or with no grade, no points and no active-issue counts | No remediation block | `:268-281` |
| `score` present and `pool` truthy | "<grade> · score s / pool"; else grade only | `:275` |
| `privacy` + `vulnerability` ≠ `total` (all three numbers) | Both printed + QA `data_mismatch`; any non-number → no check | `:288-293` |
| `credentials` present and `total` present | "(counted separately; not part of the active issues)" suffix | `:295-296` |
| `remediation_impact.title` / `title_source` | H2 verbatim (`title` first), else the kit heading; `caption_source` → note under it | `:297-299` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| KPI "Total" | number of rows `action_rows` returns (payload actions + the added certificate action); 01's Next pointer uses the same function | `action_rows :201`, `:234` |
| KPI per tier | count of `priority` (lower-case) = critical (tile only when > 0) / high / medium / low | `:235-236` |
| "#" | `rank`, else 1-based position after sorting | `:211` |
| Unit-rule N | Register rows (from `credential_exposure.register_ref`, minus rows whose `email_domain` contains "@"/"*") on the assessed domain or its subdomains whose field categories map to "password" | `s05.lead_metric :246`, `s05.derive :139` |
| Added certificate action | `rank` n+1, `priority` low, `linked_sections` [certifications], effort null `not_tracked`; none when 13 is a no-result state | `:192-198` |
| Shared gaps | per field: one distinct reason across its nulls; "every" = null on all actions | `:137-146` |
| Remediation "Active issues" parts | `privacy`, `vulnerability` joined with " + " | `:285-287` |

## Read but never printed

| Field | Why it is read (QA, ordering, ...) |
|---|---|
| `actions[].rank` (when non-numeric) | Ordering only (sorted last) |
| `actions[].review_flags[]` | Triggers the held-for-review sentence; flag texts are not printed here |
| `actions[].linked_finding_ids[]` | Verify-first lookup |
| `actions[].action_id`, `priority_label_source`, `category` | Not read (`title_source` is the title fallback) |
| `remediation_impact.state` | Not read |
| Linked sections' strings and metrics | Duplicate-text check, verify-first, unit rule |
| `state_label_source` | Not read |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| `findings` | Identified | Full body |
| `clear` | No findings | Card + full body (with no actions, the reason prints once, in the card) |
| `partial` | Partial coverage | Slim banner + full body |
| `pending_review` | Pending review | Card "Result held for review" + full body |
| `none_identified` | None identified | Card + full body |
| `not_assessed` / `not_applicable` / `unavailable` | Not assessed / Not applicable / Unavailable | Card replaces body (no added certificate action either) |
| section key absent | Unavailable | Card "Section missing from the report data." |

## QA checks raised

| check id | severity | when |
|---|---|---|
| `data_mismatch` | warn | `remediation_impact.active_issues`: privacy + vulnerability ≠ total (all three numbers) |
| `severity_term` | warn | `priority` is not a known severity word |
| `unmapped_field_category` | warn | Via `s05.derive` (unit rule): a credential field category is not in the data-class map |
| `min_width` | warn | A table cell's unbreakable run is wider than its column |

## Backend checklist

- MUST per action: `rank`, `priority` (`critical`/`high`/`medium`/`low`), `title` (or `title_source`), `action_required_source`, `estimated_time_reported`, `required_role`, `linked_sections[]` (registry keys, e.g. `vulnerabilities`).
- MUST per action: `owner`, `due_at`, `status`, either as values or as nulls with a `reason_code` (e.g. `not_assigned`, `not_tracked`). Use one shared reason so the note collapses them.
- Optional per action: `why_this_matters_source`, `linked_finding_ids[]` (ids that exist as `finding_id` in a linked section), `review_flags[]`.
- Optional: `summary`, `intro_source`, `note`, `remediation_impact {title | title_source, caption_source, current/projected {grade, score, pool}, points_recoverable, active_issues {total, privacy, vulnerability, credentials}, conditional_on_rescan, narrative_source, review_flags[]}`.
- With no actions: send `state` + `state_reason` (or `reason_code`), and `actions: []`.
- Do not send the certificate-review action yourself: it is added from `sections.certifications`.
