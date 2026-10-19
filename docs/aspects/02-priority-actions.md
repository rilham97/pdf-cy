# 02 Priority actions

Payload key: `sections.priority_actions` · Module: [s02_priority_actions.py](../../cyberrank_report/sections/s02_priority_actions.py) · Shared rules: [README](README.md)

Also reads linked sections (`linked_sections[]`), `sections.certifications.certificates[]`,
`sections.credential_exposure` + its register, and `identity.domain`. No module hooks besides `build`
(no `card`, `verdict`, `adjust`, `build_context`).

## Layout (top to bottom)

1. Opener (shared): eyebrow "02 · OVERVIEW AND PRIORITIES", H1 `title`, `intro_source`, state chip ("Identified" for `findings`) + `summary`.
2. State card or banner (shared; only for non-`findings` states).
3. KPI strip: "Total", "High priority", "Medium priority", "Low priority", optional "Priority not rated" (all in "actions").
4. Action table, columns "#", "Priority" (siren only), "Action", "Effort", "Team"; one row per action, sorted by `rank`. Null Effort/Team cells print "Not available¹" with the reason once under the table.
5. Note paragraph: shared owner/due/status gaps, held-for-review sentence, payload `note`.
6. "Projected rating after remediation" (H2, optional): key/value rows, narrative, note, review flags.

With no actions, 3–6 are replaced by one body sentence.

Action cell, line by line:

1. **Title** (bold).
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
| `actions[].priority` (`high`/`medium`/`low`, also `critical`) | Siren icon; KPI tier count | Visible "Not rated"; unknown word prints as given + QA `severity_term` |
| `actions[].title` | Line 1, bold | "Untitled action" |
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
| `remediation_impact.title` | H2 | "Projected rating after remediation" |
| `remediation_impact.current/projected {grade, score, pool}` | "BB · score 196 / 360" (or the grade alone when score/pool missing) | No grade → "Not available (not provided in the assessment data)"; both missing → "Not available¹" + one footnote |
| `remediation_impact.points_recoverable` | "Recoverable": "94 points" | Row omitted |
| `remediation_impact.active_issues.total/privacy/vulnerability` | "Active issues": "18 (6 privacy + 12 vulnerability)" | Row omitted without `total`; parts omitted when null |
| `remediation_impact.active_issues.credentials` | "Exposed credentials": n (+ separation note) | Row omitted |
| `remediation_impact.narrative_source` | Body paragraph, verbatim | Omitted |
| `remediation_impact.conditional_on_rescan` | Adds the rescan sentence to the note | Sentence omitted |
| `remediation_impact.review_flags[]` + top-level `review_flags[]` | "Review flag RF-x: <text>" | Omitted |
| `sections.certifications.certificates[] {origin, approval_state, standard}` | Generator-added action (see Computed) | No added action |
| `sections.credential_exposure.register_ref` rows, `identity.domain` | N and domain of the unit-rule note | No note |
| Linked section objects `{finding_id, state, control \| finding_type \| label, <null fields>}` | "Verify first" lines | No line |
| Linked section `metrics[]` with `count_kind`/`id` `reported_headline`, `returned_rows`, `unique_accounts` | "Verify first" count caveat | No line |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes |
|---|---|---|
| "Total", "High priority", "Medium priority", "Low priority", "Priority not rated"; unit "action(s)" | KPI strip | `:226-231` |
| "#", "Priority", "Action", "Effort", "Team" | Table header | `:210` |
| "Untitled action" | Action title fallback | `:153` |
| "Described in <ref>." / "Described in <ref> (<label>)." | Line 2 when the text is duplicated | `:161` |
| "Source: “<text>”" | Line 2 when the unit rule applies | `:164` |
| "Note: Verify and reset the accounts behind {N} rows on {assessed_domain} that list a password category. The source counts accounts; the register lists rows, not unique accounts." | Unit-rule note | First sentence: policy key `lists.credential_exposure.unit_rules.priority_action_text`; second sentence fixed (`:168`); "the assessed domain" when no domain (`:123`) |
| "Why it matters: " | Line 5 prefix | `:174` |
| "Verify first: " + "<Name> <field> is not available (<reason>)." / "<Name>: <reason>." | Line 6 | `:75-77` |
| "<N> is the source headline[ (unit not defined)]; <n> register rows listed; unique accounts: <v>." | Line 6 count caveat | `_count_check :87-102` |
| "Owner ", "Due ", "Status ", separator "  ·  " | Line 7 | `WHO :15`, `:180` |
| "See " | Line 8 | `:183` |
| "For every action: <field reason>, …." / "Where not shown: <field reason>, …." (e.g. "owner not assigned") | Note under table | `:235-237` |
| "Wording and figures of action(s) <ranks> are as reported and held for review." | Note under table | `:241` |
| "No priority actions are listed in the assessment data." | Body, no actions | `:249` |
| "Review system-detected certificates", "Cyberrank admin", "Added by this report from the certificate records; not part of the assessment action list.", "{n} system-detected certificate(s) ({standards}) is/are awaiting approval. Check the source, then approve or reject it/each in Cyberrank." | Added action | `_cert_review :187-196`, `s13.review_text :181` |
| "Projected rating after remediation" | H2 fallback | `:285` |
| "Current rating", "Projected rating", "Recoverable", "Active issues", "Exposed credentials" | Remediation key/value | `:272-284` |
| "<grade> · score <s> / <pool>", "points", "(<p> privacy + <v> vulnerability)", "(counted separately; not part of the active issues)" | Remediation values | `:265`, `:274-284` |
| "Projection as reported by the source, not a commitment." | Remediation note, always | `:288` |
| "Vulnerability fixes count only after a fresh scan confirms them." | Remediation note | `:290` |
| "Not available (<reason>)", "Not available¹" | Nulls | shared (README §5) |

Policy overrides: `lists.credential_exposure.unit_rules.priority_action_text` (note text);
`lists.credential_exposure.data_class_map` (which field categories count as "password" for N).

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| No dict in `actions[]` and no certificate awaiting approval | Body: `state_reason` → reason of `reason_code` → "No priority actions are listed in the assessment data." (no KPI, table, notes or remediation block) | `:247-249` |
| `sections.certifications` has records with `origin` `detected` (or legacy `approved`/`team_approved`) and `approval_state` `pending`/`pending_approval`/`awaiting_approval` | One low-priority action appended last (rank = payload count + 1) | `_cert_review :187`, `s13.awaiting_review :175` |
| A priority not in high/medium/low (empty, `critical`, other) | Extra KPI "Priority not rated" | `:229-231` |
| `priority` empty | Visible "Not rated" label in the Priority cell | `icons.severity_cell` |
| `action_required_source` text is a substring of any string inside a linked section's data | "Described in <ref>[ (<label of the object holding it>)]." instead of the text; that section drops out of "See" | `:157-161`, `:181` |
| Linked to `credential_exposure`, its register has rows, a source sentence matches "<number> [word] account(s)", and N > 0 | Text becomes "Source: “…”" + the unit-rule note | `_unit_rule :105-125` |
| N = 0 or no register rows or the source does not count accounts | No note, text plain | `:116-124` |
| Linked finding found and its `state` is not `findings`/`clear`/null | "Verify first" with its first null field, else "<name>: <reason>"; one per finding id | `:64-78` |
| Linked section has a non-null `reported_headline` metric plus `returned_rows` or `unique_accounts` | "Verify first" count caveat; "(unit not defined)" when its `unit` contains "unverified" | `:87-102` |
| Owner/due/status null on several actions with one shared reason | Rows omit that null; note "For every action: …" (null on every action) or "Where not shown: …" | `_shared_gaps :136`, `:178`, `:235-237` |
| Nulls on one field carry different reasons | Each row prints "Owner <reason>" | `:141-144` |
| `due_at` is `{value: "YYYY…", precision}` | Formatted date | `:131-132` |
| Action has `review_flags` and no "Verify first" line | Ranks listed in the held-for-review sentence | `:238-242` |
| Row taller than `KEEP_MAX_H` | Row may split across pages; others move whole | `:213-215` |
| `remediation_impact` absent, null record, or with no grade, no points and no active-issue counts | No remediation block | `:258-271` |
| `score` present and `pool` truthy | "<grade> · score s / pool"; else grade only | `:265` |
| `privacy` + `vulnerability` ≠ `total` (all three present) | Both printed + QA `data_mismatch` | `:278-281` |
| `credentials` present and `total` present | "(counted separately; not part of the active issues)" suffix | `:283-284` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| KPI "Total" | number of actions incl. the added certificate action | `:226` |
| KPI per tier | count of `priority` (lower-case) = high / medium / low | `:227` |
| "#" | `rank`, else 1-based position after sorting | `:201` |
| Unit-rule N | Register rows (from `credential_exposure.register_ref`, minus rows whose `email_domain` contains "@"/"*") on the assessed domain or its subdomains whose field categories map to "password" | `s05.lead_metric :246`, `s05.derive :139` |
| Added certificate action | `rank` n+1, `priority` low, `linked_sections` [certifications], effort null `not_tracked` | `:193-196` |
| Shared gaps | per field: one distinct reason across its nulls; "every" = null on all actions | `:136-145` |
| Remediation "Active issues" parts | `privacy`, `vulnerability` joined with " + " | `:275-277` |

## Read but never printed

| Field | Why it is read (QA, ordering, ...) |
|---|---|
| `actions[].rank` (when non-numeric) | Ordering only (sorted last) |
| `actions[].review_flags[]` | Triggers the held-for-review sentence; flag texts are not printed here |
| `actions[].linked_finding_ids[]` | Verify-first lookup |
| `actions[].action_id`, `priority_label_source`, `title_source`, `category` | Not read |
| `remediation_impact.title_source`, `caption_source`, `state` | Not read (heading uses `title`) |
| Linked sections' strings and metrics | Duplicate-text check, verify-first, unit rule |
| `state_label_source` | Not read |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| `findings` | Identified | Full body |
| `clear` | No findings | Card + full body (with no actions, `state_reason` prints in the card and again as the body sentence) |
| `partial` | Partial coverage | Slim banner + full body |
| `pending_review` | Pending review | Card "Result held for review" + full body |
| `none_identified` | None identified | Card + full body |
| `not_assessed` / `not_applicable` / `unavailable` | Not assessed / Not applicable / Unavailable | Card replaces body (no added certificate action either) |
| section key absent | Unavailable | Card "Section missing from the report data." |

## QA checks raised

| check id | severity | when |
|---|---|---|
| `data_mismatch` | warn | `remediation_impact.active_issues`: privacy + vulnerability ≠ total |
| `severity_term` | warn | `priority` is not a known severity word |
| `unmapped_field_category` | warn | Via `s05.derive` (unit rule): a credential field category is not in the data-class map |
| `min_width` | warn | A table cell's unbreakable run is wider than its column |

## Backend checklist

- MUST per action: `rank`, `priority` (`high`/`medium`/`low`), `title`, `action_required_source`, `estimated_time_reported`, `required_role`, `linked_sections[]` (registry keys, e.g. `vulnerabilities`).
- MUST per action: `owner`, `due_at`, `status`, either as values or as nulls with a `reason_code` (e.g. `not_assigned`, `not_tracked`). Use one shared reason so the note collapses them.
- Optional per action: `why_this_matters_source`, `linked_finding_ids[]` (ids that exist as `finding_id` in a linked section), `review_flags[]`.
- Optional: `summary`, `intro_source`, `note`, `remediation_impact {title, current/projected {grade, score, pool}, points_recoverable, active_issues {total, privacy, vulnerability, credentials}, conditional_on_rescan, narrative_source, review_flags[]}`.
- With no actions: send `state` + `state_reason` (or `reason_code`), and `actions: []`.
- Do not send the certificate-review action yourself: it is added from `sections.certifications`.
