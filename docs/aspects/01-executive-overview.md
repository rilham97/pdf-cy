# 01 Executive overview

Payload key: `sections.executive_overview` · Module: [s01_executive_overview.py](../../cyberrank_report/sections/s01_executive_overview.py) · Shared rules: [README](README.md)

Also reads top-level `rating`, `identity`, `snapshot`, `appendices.b_rating_scale`, and every section 03–15
(for the "All aspects" checklist) plus `sections.priority_actions` (for the Next pointer).
No module hooks besides `build` and `build_context` (no `card`, `verdict`, `adjust`).

## Layout (top to bottom)

1. Opener (shared): eyebrow "01 · OVERVIEW AND PRIORITIES", H1 `title`, `intro_source`, verdict row. With state `findings` there is no chip: the row reads "Summary" + `summary`.
2. State card or banner (shared; only for non-`findings` states, see States).
3. Rating panel (boxed, left rule in the grade colour): rating name, big grade + grade-mark chip, risk-band chip | Net score / Point pool / Methodology version; grade scale D…AAA; band description; band-mismatch note; "Meaning of every grade: Appendix B …".
4. "Scope and coverage" (H2): two key/value columns.
5. "Observed targets" (H3) + KPI tiles.
6. Coverage statement (body), method statement (note).
7. "Organisation profile" (H3) + description (note) + "Review flag RF-x: …" notes.
8. "Rating overview" (H2) → "Aspect scores" (H3) with "100% = best", one meter row per scored aspect.
9. "All aspects" (H3): two-column checklist (7 left, 6 right) of sections 03–15: linked name, one result line, state chip.
10. "Sector comparison" (H2): intro, bar rows, key/value rows (or a state card).
11. Next pointer: "**Next**  02 Priority actions, page n  ·  N actions (…)" (kept with block 10, or with block 9 when there is no sector block).

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `summary` | Verdict row text next to "Summary" | Row omitted (no chip for `findings`) |
| `title`, `intro_source` | H1, intro | Title falls back to "Executive overview" |
| `state`, `state_reason`, `reason_code`, `empty_state_source`, `what_checked`, `next_step` | Chip + card (shared) | See States |
| `rating_overview.rating_ref` | Dotted path to the rating object | Defaults to `rating` (`:664`) |
| `rating.rating_name` | Panel label (eyebrow style) | "Rating" (`:182`) |
| `rating.grade` (AAA…D, case-insensitive) | Big grade, highlighted segment of the scale, panel rule colour | "Grade not available" + reason (`:186`) |
| `rating.grade_reason_code` | Reason under "Grade not available" | "Reason not recorded." |
| `rating.grade_mark` | Chip beside the grade | Built-in mark (e.g. BB → "Sufficient") (`:184`) |
| `rating.risk_band` (`low`/`medium`/`high`/`critical`) | Band chip colour; chip text when no label | No chip if also no label (`:174`) |
| `rating.risk_band_label_source` | Band chip text verbatim (e.g. a localised word) | "<Band> risk band" |
| `rating.band_description_source` | Body row under the scale | Row omitted |
| `rating.net`, `rating.pool` | "Net score", "Point pool" values (`fmt_value`: `{value:196, unit:"points"}` → "196 points") | Not available (not provided …) |
| `snapshot.methodology_version` | "Methodology version" → "Version n" (`fmt_version`) | Not available (…) |
| `appendices.b_rating_scale.rows[] {grade, meaning_source}` | Compared with `band_description_source` (whitespace-normalised) | No comparison |
| `appendices.b_rating_scale.title` | Link text "Appendix B <title>" | "IISRI rating scale" |
| `identity.organisation_name` | "Organisation" | Not available (…) |
| `scope_and_coverage.primary_domain` → `identity.domain` | "Primary domain" | Not available (…) |
| `identity.sector` (alias `industry`) | "Sector" (scope block) | Not available (…) |
| `snapshot.assessed_at` | "Assessment date" (`02 Oct 2026`) | Not available (…) |
| `identity.organisation_id` | "Organisation ID" | Not available (…) |
| `snapshot.assessment_id` | "Assessment ID" | Not available (…) |
| `scope_and_coverage.eligible_targets` | "Eligible targets" (`{value:12, unit:"targets"}` → "12 targets") | Not available (…) |
| `scope_and_coverage.coverage_percent` | "Coverage" (`{value:100, unit:"percent"}` → "100%"; a bare number prints without "%") | Not available (…) |
| `scope_and_coverage.observed_targets[]` (Metric) | KPI tiles: value + unit, `label`; chip when `state` ≠ `findings` | Heading + tiles omitted |
| `scope_and_coverage.coverage_statement_source` | Body paragraph, verbatim | Omitted |
| `scope_and_coverage.method_statement_source` | Note, verbatim | Omitted |
| `identity.description_source` | "Organisation profile" note, verbatim | Heading, note and flags omitted |
| `identity.review_flags[]` + top-level `review_flags[] {id, text}` | "Review flag RF-x: <text>" (only with `description_source`) | Omitted |
| `sections.<03–15>.title` | Checklist / meter name (linked) | Registry title |
| `sections.<03–15>.state` | Checklist chip | Missing section → `unavailable`; no state → "State not recorded" |
| `sections.<03–15>.aspect_score` (`{value 0–100, unit:"percent"}` or number) | Meter + "n%" (clamped 0–100); takes precedence over everything | See Conditional rules |
| `sections.<scored>.metrics[]` `privacy_score` (or `policy.metrics[]`), `vulnerability_score`, `credential_score`, `data_leak_score`, `compliance_score` | Meter + "n%" for 03/04/05/06/13 (capped at 100) | Fallback to `aspect_breakdown` |
| `rating_overview.aspect_breakdown[] {section, value, unit}` | Score fallback only when `unit` = `percent` and `section` matches | "Score not available" |
| Section result inputs (03–15) | One result line per aspect | "No result" (see Computed) |
| `sector_comparison` (alias `industry_comparison`) `.state` | No-result → card | — |
| `sector_comparison.intro_source` | Body sentence (first letter capitalised, "." added) | Omitted |
| `sector_comparison.metrics[] {id, label, value, denominator, unit}` | Row: label, bar `value/denominator`, "v / den" (or `fmt_value` without denominator) | Null value → "Not available (…)"; no denominator → no bar |
| `sector_comparison.sector` (alias `industry`) | "Sector" (sector block) | Not available (…) |
| `sector_comparison.performance_gap` | "Performance gap" (string or `{value}` verbatim) | Not available (…) |
| `sector_comparison.cohort {cohort_size, period, percentile_method}` | "Peer cohort": "120 organisations · 2026 Q3 · nearest rank" | No `cohort_size` → Not available (cohort's own reason) |
| `sections.priority_actions.actions[].priority`, `.state`, `.title` | Next pointer count + split; link title | Pointer omitted when 02 is absent |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes |
|---|---|---|
| "Rating" | Panel label fallback | `:182` |
| "Grade not available" | Panel, no valid grade | `:186` |
| Excellent / Very good / Good / Satisfactory / Sufficient / Moderate / Insufficient / Very insufficient / Poor / Very poor | Grade-mark chip fallback | `theme.GRADE_MARK` |
| D C CC CCC B BB BBB A AA AAA | Grade scale labels (worst left) | `theme.GRADE_BAR`, `:139` |
| "<Band> risk band" / "Risk band: <label>" | Band chip | `:176` |
| "Net score", "Point pool", "Methodology version", "Version n" | Panel key/value | `:189`, `text.fmt_version` |
| "Wording as printed in the source; it differs from the {g} definition in Appendix B and is held for review." | Panel note | `:164` |
| "Meaning of every grade: " + "Appendix B <title>, page n" | Panel last row | `:202`, `section_ref :67` |
| "<Reason>: <label>, <label>." (e.g. "Not provided in the assessment data: net score, point pool.") | Under a key/value list when ≥2 nulls share one reason | `kv_block :100` |
| "Scope and coverage", "Organisation", "Primary domain", "Sector", "Assessment date", "Organisation ID", "Assessment ID", "Eligible targets", "Coverage" | Scope block | `:225-233` |
| "Observed targets", "Organisation profile" | H3 | `:238`, `:244` |
| "Review flag {id}: {text}" | Profile notes | `text.flag_notes` |
| "Rating overview", "Aspect scores", "100% = best", "All aspects" | Overview headings | `:541`, `:565`, `:572` |
| "Score not available" | Meter track, no score | `Meter.LABEL :497` |
| "Not compared" | Meter track, `aspect_score` null with `no_preference_set` | `SCORE_LABELS :443` |
| "No result" | Checklist result, muted | `:477` |
| Result phrases (see Computed) | Checklist result lines | `:298-413` |
| "Sector comparison", "Sector comparison: <card title lower-case>" | H2, state card title | `:602`, `:605` |
| "Your score", "Sector average", "Sector top 10%" | Sector row labels by metric `id` (payload `label` ignored for these ids) | `SECTOR_LABELS :597` |
| "Performance gap", "Peer cohort", "organisations" | Sector key/value | `:640-642` |
| "Next", "N action(s) (k high, …)", "not rated", "no actions listed" | Next pointer | `:654-659` |
| "Not available (<reason>)" | Any null value | shared (README §5) |

No long-list policy keys are read directly. Indirect: the vendor "needs a look" count uses
`lists.fourth_party_vendors.top_n` (default 10) via `s14.tier`.

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| `state` = `findings` | No chip; "Summary" + `summary` | `sections/__init__.py:195` |
| `state` no-result and `scope_and_coverage` present | Card, then the scope block only | `build_context :684` |
| `rating.grade` not in AAA…D | "Grade not available" + reason; no segment highlighted; grey panel rule | `:183-187` |
| `risk_band` unknown and no label | No band chip | `:174` |
| No label, or label equals the code (case-insensitive) | "<Band> risk band" | `:176` |
| Label differs from the code | "Risk band: <label>" (colour from code; grey if code unknown) | `:176-177` |
| `band_description_source` present and differs from Appendix B `meaning_source` of that grade | Band text + the "Wording as printed…" note | `:157-166`, `:196-201` |
| ≥2 key/value nulls with the same reason | One collapsed note line instead of per-row "Not available" | `kv_block :100-113` |
| One null | "Not available (<reason>)" in the row | `kv_block` |
| `scope_and_coverage.observed_targets` has dict items | "Observed targets" + tiles | `:236-238` |
| `identity.description_source` present | "Organisation profile" + note + review-flag notes | `:243-245` |
| Aspect has `aspect_score` (number) | Meter + "n%" (0–100 clamp) | `backend_score :446` |
| `aspect_score` null, `reason_code` = `no_preference_set` | Track label "Not compared", no % | `:454` |
| `aspect_score` null, other reason (or non-number) | "Score not available" | `:454` |
| No `aspect_score`, aspect in 03/04/05/06/13 | Score metric; else `aspect_breakdown` percent; else "Score not available". No-result state → "Score not available" | `aspect_score :425` |
| No `aspect_score`, aspect not in 03/04/05/06/13 | Not listed under "Aspect scores" (checklist only) | `aspect_rows :466-468` |
| Privacy `policy.policy_state` = `excluded_no_policy` | Score "Score not available" (never 0%) | `s03._metrics` |
| Section state no-result (and not `_no_preference`) or `_card_only` | Result "No result" | `:464` |
| Checklist chip | `theme.shown_state(state, key)`: `findings` → "Identified" for 12, 13, 14, 15 | `:553` |
| Section page known (previous pass) | Name / ref is a link with ", page n" | `:74-77`, `:486` |
| `sector_comparison` absent | No sector block; Next pointer travels with the checklist | `:677-680` |
| `sector_comparison.state` no-result | H2 + card "Sector comparison: <title>" + reason; nothing else | `:604-605` |
| Metric `id` = `your_score` | Bold label/value, sapphire bar; others grey | `:610-620` |
| Metric value null | Label + "Not available (…)", no bar | `:613-616` |
| `cohort.cohort_size` present | "N organisations · period · method" (empty parts dropped) | `:633-636` |
| `sections.priority_actions` absent/empty | No Next pointer | `:650-651` |
| 02 has actions | "N actions (k high, k medium, …)" in first-seen order; missing priority → "not rated" | `:653-656` |
| 02 has no actions | Shown state label of 02 (e.g. "No findings"); unknown state → "no actions listed" | `:658` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Checklist result format | "<n> <noun> · <qualifier>, <qualifier>"; n bold; singular when n = 1 | `result_markup :473` |
| 03 Privacy | `excluded_no_policy` → "No privacy policy (excluded)"; else metric `active_issues`, else `len(policy.issues)` → "n active privacy issue(s)"; neither → No result | `:298-306` |
| 04 Vulnerabilities | metric `finding_types`, else `len(findings)` → "n finding type(s)" · "k Critical, k High, k Medium, k Low" (zero tiers dropped; tier counts from findings' `severity`, or `finding_types_<tier>` metrics when no list) | `:309-317`, `s04._severity_groups` |
| 05 Credential exposure | Register rows at `register_ref` minus rows whose `email_domain` contains "@" or "*": >0 or state `clear` → "n exposed account record(s)"; 0 rows but a headline (`metrics[found_headline]` or register `counts.headline_found`) → "No register rows listed"; else No result | `:320-326`, `s05.derive` |
| 06 Data leak history | `events[]` merged by `canonical_event_id`, else metric `events_reported`, `clear` → 0. 0 → "0 breach or leak events"; else "n event(s)" · "k resolved, k reported inaccurate" (`validity_state`) | `:329-340` |
| 07 Data sovereignty | `match_state`: "Matches the preference" / "Does not match the preference" / "Cannot be compared" (missing or `unknown`) / "Not compared: no preference set" (no preference) | `:343-345`, `_shared.MATCH` |
| 08 Data residency | Countries from `observed_hosting[] {country_code \| country}` vs `allowed_set`: none resolved but rows → "Hosting countries not identified"; no preference → "n hosting country/countries"; else "x of n hosting countries outside the preference" (x = distinct `mismatch`, payload `match_state` wins over derived) | `:348-359`, `geo_map.entries` |
| 09 Legal terms | `portal_detected` (or a `rows[]` label with "portal") + rows labelled "protect" and "notif"/"breach" (yes/no words) → "k of 2 customer-protection clauses found"; `portal_detected` false → "No login or payment portal detected" | `:362-367`, `s09._clauses` |
| 10 AI risk | metric `ai_issues` (`clear` → 0) → "n AI governance issue(s)" | `:370-376`, `:418` |
| 11 Quantum | metric `high_risk` (`clear` → 0) → "n high-risk finding(s)" | `:420` |
| 12 Resourcing | `privacy_role_evidence`, `security_role_evidence` ∈ `detected`/`not_detected` → "k of 2 privacy and security roles with public evidence" · "g not recorded"; neither recognised → No result | `:379-386` |
| 13 Certifications | Distinct `standard` among non-rejected certificates → "n certification(s)" · "k awaiting approval, k rejected" (`approval_state`; legacy origin `approved` = approved) | `:389-395` |
| 14 Fourth parties | No vendors → "0 connected organisations"; else "n connected organisation(s)" · "k need(s) a look" (s14 "Needs a look" rule) | `:398-405` |
| 15 Cloud | metric `cloud_providers_detected`, else `len(providers)`, `clear` → 0 → "n cloud provider(s)" | `:408-413` |
| Next pointer count | `len(actions)` of the payload and a per-priority split | `next_pointer :647` |
| Band mismatch | whitespace-normalised `band_description_source` ≠ Appendix B `meaning_source` | `band_note :157` |

## Read but never printed

| Field | Why it is read (QA, ordering, ...) |
|---|---|
| `rating_overview.aspect_breakdown[].value` (unit `percent`) | Score fallback only; non-percent values, `aspect`, `state`, `display_label_source`, `summary_label_source`, `secondary`, `review_flags` are ignored |
| `rating_overview.note` | Owner decision: never printed (`:571`) |
| `sector_comparison.note` | Owner decision: never printed (`:643`) |
| `sector_comparison.cohort.cohort_id`, `.state` | Not printed (state/reason only matter when `cohort_size` is missing) |
| `sector_comparison.metrics[].label` for the three known ids | Replaced by the kit labels |
| Demerit ledger | Never printed (`ledger_table :255` exists but is not called) |
| `rating.grade_source`, `grade_table_id`, `stored_vs_calculated`, `review_flags` | Not read by this section |
| `snapshot.score_context` | Not printed |
| `sections.<03–15>` internals | Only to derive the result line / score (see Computed) |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| `findings` | none ("Summary" label beside `summary`) | Full body |
| `clear` | No findings | Card "No findings within the scope and time of this check" + full body |
| `partial` | Partial coverage | Slim banner (reason + coverage) + full body |
| `pending_review` | Pending review | Card "Result held for review" + full body |
| `none_identified` | None identified | Card + full body |
| `not_assessed` / `not_applicable` / `unavailable` | Not assessed / Not applicable / Unavailable | Card replaces body; scope block below when `scope_and_coverage` is present |
| section key absent | Unavailable | Card "Section missing from the report data." only |

## QA checks raised

| check id | severity | when |
|---|---|---|
| `data_mismatch` | warn | Via `s04._severity_groups`: a `finding_types_<tier>` metric differs from the findings carrying that severity |
| `unmapped_field_category` | warn | Via `s05.derive`: a register field category is not in the data-class map |
| `min_width` | warn | A key/value value's unbreakable run is wider than its column |

No check is raised by this module directly; the rest are shared (README §9).

## Backend checklist

- MUST: `rating.grade`, `rating.risk_band` (+ `risk_band_label_source` for localised text), `rating.net`, `rating.pool` (`{value, unit:"points"}`), `snapshot.methodology_version`, `snapshot.assessed_at`, `snapshot.assessment_id`.
- MUST: `identity.organisation_name`, `identity.organisation_id`, `identity.sector`, `scope_and_coverage.primary_domain`, `eligible_targets`, `coverage_percent` as `{value, unit:"percent"}`.
- MUST: `sections.<key>.aspect_score` for every assessed section 03–15 (null + `reason_code`, `no_preference_set` for an uncompared 07/08).
- MUST: a `state` and the result inputs of each section 03–15 (see Computed), and `sections.priority_actions`.
- MUST: `sector_comparison {sector, metrics[] (your_score, sector_average, sector_top_10_percent with denominator), performance_gap, cohort {cohort_size, period, percentile_method}}` or a no-result `state` + reason.
- Optional: `summary`, `intro_source`, `rating.rating_name`, `grade_mark`, `band_description_source`, `observed_targets[]`, `coverage_statement_source`, `method_statement_source`, `identity.description_source` (+ `review_flags`), `sector_comparison.intro_source`, `rating_overview.rating_ref`.
- Every null needs a `reason_code`, otherwise the build stops.
