# 03 Privacy

Payload key: `sections.privacy` · Module: [s03_privacy.py](../../cyberrank_report/sections/s03_privacy.py) · Shared rules: [README](README.md)

Demerit rule B. Covers the published privacy policy only. Sovereignty, residency, legal T&C and resourcing are
sections 07, 08, 09 and 12. A payload in the old nested shape (`privacy.sovereignty` and similar) is lifted at
load time (`sections/__init__.py:140`). Criterion H "Data residency" is policy text, not section 08.

## Layout (top to bottom)

1. Opener (shared, [README §3](README.md#3-how-every-section-renders)): eyebrow "03 · ASSESSMENT DETAILS", H1 `title` (else "Privacy"), `intro_source`, state chip + `summary`. This module has no `verdict()`, so with no `summary` only the chip prints.
2. Section state card: a card state prints it above the body. A no-result state prints the card **instead of** the body. There is no `build_context`, so nothing else prints.
3. KPI strip from the policy metrics.
4. Note that explains the policy state (only for `claimed_missing` or `excluded_no_policy`).
5. H2 "Privacy policy", then one of two blocks. Normally a row with the state chip and a subtitle, then a key/value list. If the policy is missing or has no result, a state card.
6. H3 "Assessed areas (A–P)": two side-by-side tables of 8 rows, then a note listing missing scores. Prints only when `policy.areas` is a list.
7. H3 "Active issues" table. With no issues and a non-zero `active_issues` metric, a one-line note prints instead.

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `title`, `intro_source`, `summary`, `state` | Opener (shared) | Title falls back to "Privacy". No intro or verdict line is printed. |
| `state_reason`, `reason_code`, `what_checked`, `next_step`, `empty_state_source.{text,coverage}` | Section card (shared `default_card`, `__init__.py:119`) | Card reason falls back to "Reason not recorded in the assessment data." |
| `policy` | Whole policy block | H2 + card "Data unavailable" / "Not provided in the assessment data." (`s03:85-86`, `s03:146-148`). An empty object `{}` does the same. |
| `policy.metrics[]` (Metric) | KPI strip, one tile each, in payload order (`s03:112-118`, `s03:188-190`) | Falls back to section-level `metrics[]`. If both are empty, no strip. A null value prints "Not available" + reason. |
| `policy.metrics[id=privacy_score]` | Tile, e.g. "64%" + `label` | See `excluded_no_policy` rule |
| `policy.metrics[id=active_issues]` | Tile, e.g. "6 issues". Its `value` also drives the "issues reported" note (`s03:170`, `s03:179-181`). | No note |
| `policy.metrics[id=policies_found]` | Tile, e.g. "1 policy" | Missing tile |
| `metrics[].label`, `unit`, `state` | Tile label. Unit word via `text.UNITS` or the code with `_` → space, singular when the value is 1. A chip appears when the state is not `findings`. | Empty label |
| `policy.state` | Chip next to the H2 subtitle, or the card state for no-result states (`s03:87-95`) | Treated as `unavailable` |
| `policy.subtitle_source` | Subtitle next to the chip (`s03:94`) | "Published privacy policy: state, source, assessed areas and issues" |
| `policy.policy_state` (value or `{value, source_label, source_page}`) | "Policy state" row: mapped label + optional source quote (`s03:149-158`) | Null record → "Not available (reason)". Key absent → "Not available (reason not recorded)". |
| `policy.policy_state.source_label`, `.source_page` | Appended: `<label> (source p. 2: “…”)`. The page part is left out when there is no `source_page`. | Label only |
| `policy.policy_source` (URL string or `{value}`) | "Policy source" row, in monospace when the value is technical (`s03:159`) | "Not available (not provided in the assessment data)" |
| `policy.policy_version` | "Policy version" row, printed verbatim (`s03:160-161`) | Row omitted |
| `policy.areas` (list of `{code, name?, score, max_score?, score_reason_code?, reason_code?}`) | A–P matrix (`s03:121-142`) | Null record or other non-list: the "Per-area results (A–P)" row prints "Not available (reason)" (`s03:162-163`) |
| `policy.areas[].code` | Matched to A–P without regard to case | A code with no entry → "Not available" (not provided in the assessment data) |
| `policy.areas[].name` | "Area" cell | Built-in name (`AREAS`, `s03:18-22`) |
| `policy.areas[].score`, `.max_score` | "n / max", e.g. "7 / 10" | `score` null → "Not available" + note. `max_score` missing or 0 → 10. |
| `policy.areas[].score_reason_code` (else `reason_code`) | Reason in the note under the matrix | "reason not recorded" |
| `policy.issues[]` `{label, category, text}` | "Active issues" table rows (`s03:169-178`) | No table. Falls back to the count note. |
| `policy.issues[].label` (else `title`) | "Issue" column | "Not available (reason not recorded)" |
| `policy.issues[].category` | "Type" column, first letter capitalised | "Privacy" |
| `policy.issues[].text` (else `description`) | "What was found" column, verbatim | "Not available (not provided in the assessment data)" |
| `policy.state_reason`, `reason_code`, `reason`, `narrative_source`, `next_step` | Policy card when `policy.state` has no result (`s03:88-93`) | Explanation of the policy state, otherwise the kit fallback |
| `policy.reason_code` (state `pending_review`) | Note "Held for review: <reason>." under the list (`s03:96-99`) | No note |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes |
|---|---|---|
| "Valid policy, assessed" / "Policy claimed but not found" / "No privacy policy (excluded)" | "Policy state" value (`s03:23-31`) | Mapped from `valid_assessed` / `claimed_missing` / `excluded_no_policy` |
| "0%: a privacy policy is referenced but could not be found or read, so it is scored 0% and counts fully against the privacy rating." | Note under the KPI strip (`s03:25-27`) | `claimed_missing` |
| "No score: the organisation states it has no privacy policy, so privacy is excluded from the rating and the scoring pool is recalibrated. This is not a 0% score." | Note under the KPI strip. It is also the card reason when `policy.state` has no result (`s03:28-30`). | `excluded_no_policy` |
| `Not recognised (“<value>”); held for review` | "Policy state" value (`s03:152`) | Unknown `policy_state` |
| "Policy state", "Policy source", "Policy version", "Per-area results (A–P)" | Key/value labels (`s03:158-163`) | |
| "Privacy policy" | H2 (`s03:148`, `s03:164`) | |
| "Published privacy policy: state, source, assessed areas and issues" | Default subtitle (`s03:165`) | Override with `policy.subtitle_source` |
| "Not provided in the assessment data." | Card when `policy` is missing (`s03:86`) | |
| "Assessed areas (A–P)" | H3 (`s03:168`) | |
| A–P area names: Individual rights, Consent, Changes to privacy policy, Security of PII, Third parties, Collection of PII, Disclosure, Data residency, Cookies, Complexity and clarity, Ways of contact, Retention of PII, PII of children, Special categories of PII, Automated decision-making and profiling, Policy introduction | Matrix "Area" column (`s03:18-22`) | Used when `areas[].name` is missing |
| Columns "" / "Area" / "Score" | Matrix header (`s03:135`) | |
| "Not available" | Matrix score cell (`s03:131`) | |
| `Not available for <codes>: <reason>` (joined with "; ", ends with ".") | Note under the matrix (`s03:139-141`) | |
| "Active issues"; columns "Issue" / "Type" / "What was found" | H3 + table (`s03:176-178`) | |
| `<N issues> reported; issue detail is not provided in the assessment data.` | Note (`s03:180-181`) | |
| "Held for review: …" | Note (`s03:98-99`) | |
| "excluded from the rating" | KPI tile reason → "Excluded from the rating." (`s03:116`) | |
| "Not applicable" | KPI tile value for an excluded metric (`components.py:387`) | |
| `The assessment shows a <score> privacy score with <n policies> found and <n active issues>, but it does not record the policy state that decides how that score should be read.` | Section card reason (`s03:57-60`) | See card rule |
| Next steps: "If the policy is valid and was assessed, the reported score stands (1 to 100%)." / "If a policy is claimed but cannot be found or read, 0% stands and counts against the rating." / "If the organisation states it has no privacy policy, privacy is excluded from the rating and no score is shown." | Section card "What happens next" (`s03:61-65`) | Same rule |
| `The policy state “<x>” is not one of the known states (valid and assessed, claimed but not found, no policy and excluded), so the privacy score cannot be read yet.` | Section card reason (`s03:45-47`) | Set by `adjust()` |

No `pol(...)` keys are used. The policy file has `lists.privacy_issues`, but this module does not read it, and the issues table is never capped.

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| `policy.policy_state` value not null and not one of the 3 known values | Section moved to `pending_review` (`policy_state_unrecognised`) with the hardcoded reason. The policy block still prints the "Not recognised" label. | `s03:39-47`, `s03:151-152` |
| `policy_state` = `excluded_no_policy` | `privacy_score` and `active_issues` tiles → "Not applicable" + "Excluded from the rating." with no chip. The "No score…" note prints. The "Per-area results" row is left out. | `s03:115-117`, `s03:191-193`, `s03:162` |
| `policy_state` = `claimed_missing` | The "0%…" note prints. The tiles print as sent. The "Per-area results" row is left out. | `s03:191-193`, `s03:162` |
| `policy_state` = `valid_assessed` | No note. Tiles print as sent. | `s03:191` |
| `policy` is null or `{}` | H2 + "Data unavailable" card. No list, matrix or issues. | `s03:85-86` |
| `policy.state` in `not_assessed`/`not_applicable`/`unavailable` | H2 + state card (reason chain: `state_reason` → `reason_code` text → `reason` → `narrative_source` → policy-state explanation). The key/value list prints **after** the card. There is no chip row. | `s03:87-93` |
| `policy.state` is any other state | H2 + chip/subtitle row + key/value list | `s03:94-100` |
| `policy.state` = `pending_review` and `policy.reason_code` set | Note "Held for review: <reason text>." (no doubled prefix if the reason text already starts with "held for review") | `s03:96-99` |
| `policy_state.source_label` present and a label was mapped | Label + ` (source p. N: “…”)` | `s03:154-157` |
| `policy.policy_version` not null | "Policy version" row | `s03:160-161` |
| `areas` is a list | Matrix of 16 rows A–P. Codes outside A–P are ignored. | `s03:121-142`, `s03:167-168` |
| `areas` is not a list and the policy state is not claimed or excluded | "Per-area results (A–P)" row prints the null reason | `s03:162-163` |
| Several key/value nulls share one reason | "Not available" + superscript, with the reason printed once below | `tables.py` `key_value_list` |
| `issues` non-empty | "Active issues" table (every row, no cap) | `s03:171-178` |
| `issues` empty and the `policy.metrics` `active_issues` value is truthy | Note "<N issues> reported; issue detail is not provided…" | `s03:179-181` |
| Section state `pending_review` and `policy_state` value null | Card replaced by `card()`: the reason sentence (only when all 3 metrics `privacy_score`, `policies_found` and `active_issues` have values) + 3 next-step bullets | `s03:51-66` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Excluded tiles | `privacy_score`, `active_issues` → `value: null`, `state: not_applicable` when `excluded_no_policy` | `s03:112-118` (also used by s01) |
| Area score text | `fmt_number(score) / fmt_number(max_score or 10)` | `s03:133` |
| Missing-area note | Area codes grouped by reason text | `s03:124-141` |
| Pending-review card sentence | `fmt_value` of the 3 policy metrics | `s03:56-60` |

## Read but never printed

| Field | Why it is read (QA, ordering, ...) |
|---|---|
| `policy.metrics[id=active_issues].value` | Fallback "issues reported" note when `issues[]` is empty. Also the card sentence. |
| `policy.metrics[id=policies_found]` | Card sentence only (also a tile when sent) |
| `state_label_source`, `policy.state_label_source`, `policy_state.state`, `metrics[].source_label`, `metrics[].count_kind`, `areas.note` | Not read by this module |
| `review_flags[]`, `policy.review_flags[]` | Not read. No review-flag notes print in 03 (unlike 04). |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| `findings` | Findings | No card. Full body. |
| `clear` | No findings | Card "No findings within the scope and time of this check" (reason: `state_reason` or `empty_state_source.text`; "What was checked": `what_checked` or `empty_state_source.coverage`) + full body |
| `partial` | Partial coverage | Banner (`state_reason` + `what_checked`) + full body |
| `pending_review` | Pending review | Card "Result held for review" + full body. `card()` overrides when `policy_state` is null. |
| `not_assessed` / `not_applicable` / `unavailable` | Not assessed / Not applicable / Unavailable | Card only. No KPI strip, no policy block. |
| `none_identified` | None identified | Card + body |
| `policy.state` (sub-block) | Dense chip next to the subtitle, using the raw state | No-result states: H2 + card + key/value list |

## QA checks raised

| check id | severity | when |
|---|---|---|
| `state_adjusted` | info | `adjust()` holds the section because of an unrecognised `policy_state` (`__init__.py:176`) |
| `min_width` | warn | Shared: a table cell is too narrow ([README §9](README.md#9-qa-checks-used-by-every-section)) |

## Backend checklist

- MUST: `state`, `summary`, `policy.state`, `policy.policy_state` (one of `valid_assessed`, `claimed_missing`, `excluded_no_policy`; anything else holds the section), `policy.policy_source` (URL or NullReason), `policy.metrics[]` with ids `privacy_score` (unit `percent`), `active_issues`, `policies_found`.
- MUST for a full section: `policy.areas[]`, the 16 entries A–P `{code, score, max_score}` (or a NullReason with `reason_code`), and `policy.issues[] {label, category, text}`.
- For no-result states: `state_reason` or `reason_code`, and optionally `next_step`.
- Optional: `intro_source`, `policy.policy_version`, `policy_state.{source_label, source_page}`, `policy.subtitle_source`, `areas[].name`, `areas[].score_reason_code`, `empty_state_source` (for `clear`), `what_checked`.
- Do not send `0` for a missing score. Send a NullReason.
