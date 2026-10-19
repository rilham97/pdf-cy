# 03 Privacy

Payload key: `sections.privacy` · Module: [s03_privacy.py](../../cyberrank_report/sections/s03_privacy.py) · Shared rules: [README](README.md)

Demerit rule B. Covers the published privacy policy only. Sovereignty, residency, legal T&C and resourcing are
sections 07, 08, 09 and 12. A payload in the old nested shape (`privacy.sovereignty` and similar) is lifted at
load time (`sections/__init__.py:140`). Criterion H "Data residency" is policy text, not section 08.

## Layout (top to bottom)

1. Opener (shared, [README §3](README.md#3-how-every-section-renders)): eyebrow "03 · ASSESSMENT DETAILS", H1 `title` (else "Privacy"), `intro_source`, state chip + `summary`. This module has no `verdict()`, so with no `summary` only the chip prints.
2. Section state card: a card state prints it above the body. A no-result state prints the card **instead of** the body. There is no `build_context`, so nothing else prints.
3. KPI strip from the policy metrics.
4. Review-flag notes for the section: "Review flag RF-xx: …".
5. Note that explains the policy state (only for `claimed_missing` or `excluded_no_policy`). It is left out when
   the policy card below already prints the same text as its reason, so it prints once.
6. H2 "Privacy policy", then one of two blocks. Normally a row with the state chip and a subtitle, then a key/value
   list and the policy's review-flag notes. If the policy is missing or has no result, a state card.
7. H3 "Assessed areas (A–P)": two side-by-side tables of 8 rows, then a note listing missing scores. Prints only when `policy.areas` is a list.
8. H3 "Active issues" table. With no issues and a non-zero `active_issues` metric, a one-line note prints instead.

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `title`, `intro_source`, `summary`, `state` | Opener (shared) | Title falls back to "Privacy". No intro or verdict line is printed. |
| `state_reason`, `reason_code`, `what_checked`, `next_step`, `empty_state_source.{text,coverage}` | Section card (shared `default_card`, `__init__.py:119`) | Card reason falls back to "Reason not recorded in the assessment data." |
| `policy` | Whole policy block | H2 + card "Data unavailable" / "Not provided in the assessment data." (`s03:92-93`, `s03:158-160`). An empty object `{}` does the same. |
| `policy.metrics[]` (Metric) | KPI strip, one tile each, in payload order (`s03:118-124`, `s03:200-202`) | Falls back to section-level `metrics[]`. If both are empty, no strip. A null value prints "Not available" + reason. |
| `policy.metrics[id=privacy_score]` | Tile, e.g. "64%" + `label` | See `excluded_no_policy` rule |
| `policy.metrics[id=active_issues]` | Tile, e.g. "6 issues". Its `value` also drives the "issues reported" note, read through the same metric lookup as the tiles (`_metrics`: section-level fallback, `excluded_no_policy` override) (`s03:182`, `s03:191-193`). | No note |
| `policy.metrics[id=policies_found]` | Tile, e.g. "1 policy" | Missing tile |
| `metrics[].label`, `unit`, `state` | Tile label. Unit word via `text.UNITS` or the code with `_` → space, singular when the value is 1. A chip appears when the state is not `findings`. | Empty label |
| `policy.state` | Chip next to the H2 subtitle, or the card state for no-result states (`s03:94-101`) | Treated as `unavailable` |
| `policy.subtitle_source` | Subtitle next to the chip (`s03:100`) | "Published privacy policy: state, source, assessed areas and issues" |
| `policy.policy_state` (value or `{value, source_label, source_page}`) | "Policy state" row: mapped label + optional source quote (`s03:161-170`) | Null record → "Not available (reason)". Key absent → "Not available (reason not recorded)". |
| `policy.policy_state.source_label`, `.source_page` | Appended: `<label> (source p. 2: “…”)`. The page part is left out when there is no `source_page`. | Label only |
| `policy.policy_source` (URL string or `{value}`) | "Policy source" row, in monospace when the value is technical (`s03:171`) | "Not available (not provided in the assessment data)" |
| `policy.policy_version` | "Policy version" row, printed verbatim (`s03:172-173`) | Row omitted |
| `policy.areas` (list of `{code, name?, score, max_score?, score_reason_code?, reason_code?}`) | A–P matrix (`s03:127-154`) | Null record or other non-list: the "Per-area results (A–P)" row prints "Not available (reason)" (`s03:174-175`) |
| `policy.areas[].code` | Matched to A–P without regard to case. A code outside A–P is not placed in the matrix and raises QA `unknown_term` (`s03:130-132`). | A code with no entry → "Not available" (not provided in the assessment data) |
| `policy.areas[].name` | "Area" cell | Built-in name (`AREAS`, `s03:19-23`) |
| `policy.areas[].score`, `.max_score` | "n / max", e.g. "7 / 10". A `max_score` of 0 (or below) prints as sent ("3 / 0") and raises QA `data_mismatch` (`s03:142-145`). | `score` null → "Not available" + note. `max_score` missing → 10. |
| `policy.areas[].score_reason_code` (else `reason_code`) | Reason in the note under the matrix | "reason not recorded" |
| `policy.issues[]` `{label, category, text}` | "Active issues" table rows, every row (`s03:181-190`) | No table. Falls back to the count note. |
| `policy.issues[].label` (else `title`) | "Issue" column | "Not available (reason not recorded)" |
| `policy.issues[].category` | "Type" column, first letter capitalised | "Privacy" |
| `policy.issues[].text` (else `description`) | "What was found" column, verbatim | "Not available (not provided in the assessment data)" |
| `policy.state_reason`, `reason_code`, `reason`, `narrative_source`, `next_step` | Policy card when `policy.state` has no result (`_own_reason`, `s03:71-74`, `s03:95-99`) | Explanation of the policy state, otherwise the kit fallback |
| `policy.reason_code` (state `pending_review`) | Note "Held for review: <reason>." under the list (`s03:102-105`) | No note |
| `review_flags[]` (ids) + top-level `review_flags[] {id, text}` | Note "Review flag <id>: <text>" under the KPI strip (`s03:203`, `text.py:271`) | Nothing. An id with no text is skipped. |
| `policy.review_flags[]` (ids) | Same notes, under the policy key/value list (or after the policy card) (`s03:176`) | Nothing |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes |
|---|---|---|
| "Valid policy, assessed" / "Policy claimed but not found" / "No privacy policy (excluded)" | "Policy state" value (`s03:24-32`) | Mapped from `valid_assessed` / `claimed_missing` / `excluded_no_policy` |
| "0%: a privacy policy is referenced but could not be found or read, so it is scored 0% and counts fully against the privacy rating." | Note under the KPI strip (`s03:26-28`) | `claimed_missing` |
| "No score: the organisation states it has no privacy policy, so privacy is excluded from the rating and the scoring pool is recalibrated. This is not a 0% score." | Note under the KPI strip, or the card reason when `policy.state` has no result and no reason of its own; never both (`s03:29-31`, `s03:205-207`). | `excluded_no_policy` |
| `Not recognised (“<value>”); held for review` | "Policy state" value (`s03:164`) | Unknown `policy_state` |
| "Policy state", "Policy source", "Policy version", "Per-area results (A–P)" | Key/value labels (`s03:170-175`) | |
| "Privacy policy" | H2 (`s03:160`, `s03:176`) | |
| "Published privacy policy: state, source, assessed areas and issues" | Default subtitle (`s03:177`) | Override with `policy.subtitle_source` |
| "Not provided in the assessment data." | Card when `policy` is missing (`s03:93`) | |
| "Review flag <id>: <text>" | Notes (`text.py:276`) | |
| "Assessed areas (A–P)" | H3 (`s03:180`) | |
| A–P area names: Individual rights, Consent, Changes to privacy policy, Security of PII, Third parties, Collection of PII, Disclosure, Data residency, Cookies, Complexity and clarity, Ways of contact, Retention of PII, PII of children, Special categories of PII, Automated decision-making and profiling, Policy introduction | Matrix "Area" column (`s03:19-23`) | Used when `areas[].name` is missing |
| Columns "" / "Area" / "Score" | Matrix header (`s03:147`) | |
| "Not available" | Matrix score cell (`s03:140`) | |
| `Not available for <codes>: <reason>` (joined with "; ", ends with ".") | Note under the matrix (`s03:151-153`) | |
| "Active issues"; columns "Issue" / "Type" / "What was found" | H3 + table (`s03:188-190`) | |
| `<N issues> reported; issue detail is not provided in the assessment data.` | Note (`s03:192-193`) | |
| "Held for review: …" | Note (`s03:104-105`) | |
| "excluded from the rating" | KPI tile reason → "Excluded from the rating." (`s03:122`) | |
| "Not applicable" | KPI tile value for an excluded metric (`components.py:387`) | |
| `The assessment shows a <score> privacy score with <n policies> found and <n active issues>, but it does not record the policy state that decides how that score should be read.` | Section card reason (`s03:58-61`) | See card rule |
| Next steps: "If the policy is valid and was assessed, the reported score stands (1 to 100%)." / "If a policy is claimed but cannot be found or read, 0% stands and counts against the rating." / "If the organisation states it has no privacy policy, privacy is excluded from the rating and no score is shown." | Section card "What happens next" (`s03:62-66`) | Same rule |
| `The policy state “<x>” is not one of the known states (valid and assessed, claimed but not found, no policy and excluded), so the privacy score cannot be read yet.` | Section card reason (`s03:46-48`) | Set by `adjust()` |

No `pol(...)` keys are used. The issues table is never capped: the policy file pins privacy issues inline
(`tiers.pinned_inline` contains `privacy_issues`; `lists.privacy_issues.register_id` is null), so there is no
Appendix D register for them. Capping them would need an owner decision and a new register slot.

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| `policy.policy_state` value not null and not one of the 3 known values | Section moved to `pending_review` (`policy_state_unrecognised`) with the hardcoded reason. The policy block still prints the "Not recognised" label. | `s03:40-48`, `s03:163-164` |
| `policy_state` = `excluded_no_policy` | `privacy_score` and `active_issues` tiles → "Not applicable" + "Excluded from the rating." with no chip. The "No score…" note prints (see the next rule). The "Per-area results" row is left out. | `s03:121-123`, `s03:205-207`, `s03:174` |
| `policy_state` explanation and `policy.state` is a no-result state with no reason of its own | The explanation prints only as the policy card's reason; the note under the KPI strip is left out | `s03:96`, `s03:206` |
| `policy_state` = `claimed_missing` | The "0%…" note prints. The tiles print as sent. The "Per-area results" row is left out. | `s03:205-207`, `s03:174` |
| `policy_state` = `valid_assessed` | No note. Tiles print as sent. | `s03:205` |
| `policy` is null or `{}` | H2 + "Data unavailable" card. No list, matrix or issues. | `s03:92-93` |
| `policy.state` in `not_assessed`/`not_applicable`/`unavailable` | H2 + state card (reason chain: `state_reason` → `reason_code` text → `reason` → `narrative_source` → policy-state explanation). The key/value list and policy review-flag notes print **after** the card. There is no chip row. | `s03:95-99` |
| `policy.state` is any other state | H2 + chip/subtitle row + key/value list + policy review-flag notes | `s03:100-106` |
| `policy.state` = `pending_review` and `policy.reason_code` set | Note "Held for review: <reason text>." (no doubled prefix if the reason text already starts with "held for review") | `s03:102-105` |
| `policy_state.source_label` present and a label was mapped | Label + ` (source p. N: “…”)` | `s03:166-169` |
| `policy.policy_version` not null | "Policy version" row | `s03:172-173` |
| `areas` is a list | Matrix of 16 rows A–P. Codes outside A–P are not placed in it; QA `unknown_term` names them. | `s03:127-154`, `s03:179-180` |
| `areas[].max_score` is 0 or below | Printed as sent ("n / 0"); QA `data_mismatch` | `s03:142-145` |
| `areas` is not a list and the policy state is not claimed or excluded | "Per-area results (A–P)" row prints the null reason | `s03:174-175` |
| Several key/value nulls share one reason | "Not available" + superscript, with the reason printed once below | `tables.py` `key_value_list` |
| `issues` non-empty | "Active issues" table (every row, no cap; policy `pinned_inline`) | `s03:183-190` |
| `issues` empty and the `active_issues` metric (policy metrics, else section metrics; null when excluded) is truthy | Note "<N issues> reported; issue detail is not provided…" | `s03:182`, `s03:191-193` |
| Section state `pending_review` and `policy_state` value null | Card replaced by `card()`: the reason sentence (only when all 3 metrics `privacy_score`, `policies_found` and `active_issues` have values) + 3 next-step bullets | `s03:52-67` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Excluded tiles | `privacy_score`, `active_issues` → `value: null`, `state: not_applicable` when `excluded_no_policy` | `s03:118-124` (also used by s01) |
| Area score text | `fmt_number(score) / fmt_number(max_score)`; 10 only when `max_score` is absent | `s03:145` |
| Missing-area note | Area codes grouped by reason text | `s03:133-153` |
| Pending-review card sentence | `fmt_value` of the 3 policy metrics | `s03:57-61` |

## Read but never printed

| Field | Why it is read (QA, ordering, ...) |
|---|---|
| `policy.metrics[id=active_issues].value` | Tile, and the fallback "issues reported" note when `issues[]` is empty. Also the card sentence. |
| `policy.metrics[id=policies_found]` | Card sentence only (also a tile when sent) |
| `state_label_source`, `policy.state_label_source`, `policy_state.state`, `metrics[].source_label`, `metrics[].count_kind`, `areas.note` | Not read by this module |

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
| `unknown_term` | warn | `policy.areas[]` holds a code outside A–P (`s03:130-132`) |
| `data_mismatch` | warn | An area's `max_score` is 0 or below (`s03:143-144`) |
| `min_width` | warn | Shared: a table cell is too narrow ([README §9](README.md#9-qa-checks-used-by-every-section)) |

## Backend checklist

- MUST: `state`, `summary`, `policy.state`, `policy.policy_state` (one of `valid_assessed`, `claimed_missing`, `excluded_no_policy`; anything else holds the section), `policy.policy_source` (URL or NullReason), `policy.metrics[]` with ids `privacy_score` (unit `percent`), `active_issues`, `policies_found`.
- MUST for a full section: `policy.areas[]`, the 16 entries A–P `{code, score, max_score}` (or a NullReason with `reason_code`), and `policy.issues[] {label, category, text}`.
- For no-result states: `state_reason` or `reason_code`, and optionally `next_step`.
- Optional: `review_flags[]` / `policy.review_flags[]` (ids resolved against the top-level `review_flags[]`), `intro_source`, `policy.policy_version`, `policy_state.{source_label, source_page}`, `policy.subtitle_source`, `areas[].name`, `areas[].score_reason_code`, `empty_state_source` (for `clear`), `what_checked`.
- Do not send `0` for a missing score. Send a NullReason.
