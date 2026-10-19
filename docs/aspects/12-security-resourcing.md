# 12 Security resourcing

Payload key: `sections.security_resourcing` · Module: [s12_security_resourcing.py](../../cyberrank_report/sections/s12_security_resourcing.py) · Shared rules: [README](README.md)

Inventory section (`theme.INVENTORY`): payload state `findings` shows the chip "Identified". Demerit rule J. This is not privacy criterion J "Complexity and clarity" (section 03). Old payloads that send `sections.privacy.resourcing` are moved here at load, and their `subtitle_source` becomes `intro_source` (`sections/__init__.py:135-157`). File refs: `s12:` = `s12_security_resourcing.py`, `_shared:` = `sections/_shared.py`.

## Layout (top to bottom)

1. Section opener: "12", title, state chip, verdict, `intro_source` (`__init__.py:192-199`).
2. State card or banner. Only for the states listed under States.
3. KPI strip from `metrics[]`. Printed only when there are metrics, and never in the no-result states (`s12:55-57`).
4. Key/value list with no heading (`s12:43-49`):
   - "Privacy role evidence"
   - "Security role evidence"
   - one "Role found" row per `roles_found[]` entry
5. Message paragraph, printed only when `summary` is also present and differs from the message (`s12:50-51`).

The section has no H2 headings and no Appendix D register.

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `summary` | Opener verdict | Verdict is `neutral_message`, then `narrative_source`. Card-only state: no verdict (`s12:29-30`, `__init__.py:192`) |
| `title` | H1 | "Security resourcing" |
| `intro_source` | Opener intro | Omitted |
| `privacy_role_evidence` (`detected` / `not_detected`, or `{value}`) | "Privacy role evidence" row: icon + "Detected" or "Not detected in the sources checked" (`s12:33-40`) | A null record prints "Not available (<reason>)". Another value prints "Not recognised (“<value>”)" and raises QA `unknown_term` |
| `security_role_evidence` | "Security role evidence" row, same rules | Same |
| `roles_found[].role` | "Role found" row: "<role> (source: <s1>; <s2>)" (`s12:45-48`) | The entry is skipped |
| `roles_found[].sources[]` | Joined with "; " inside "(source: …)". Null items are dropped | Without sources: "<role>" alone |
| `neutral_message` | Opener verdict when there is no `summary`. Otherwise the paragraph after the list, if it differs from `summary` | Falls back to `narrative_source` |
| `narrative_source` | Same use as `neutral_message`, but only when `neutral_message` is absent (`s12:25-26`) | Nothing |
| `metrics[]` | KPI tiles | No strip |
| `state` | Chip and card | Unavailable card "Section missing from the report data." when the section key is absent (`__init__.py:184`) |
| `state_reason` | Card reason (first choice) | `reason_code` text |
| `reason_code` | Card reason text. In `pending_review` it is the card reason: "Held for review: …" (`_shared:67-69`) | Next fallback |
| `reason` | No-result card reason (third choice) (`_shared:71-72`) | `narrative_source` |
| `enabled` | `false` switches the section to `not_applicable` with a card and no body (`_shared:46-48`) | Not switched off |
| `what_checked` / `empty_state_source.coverage` | "What was checked" on the card (clear / partial / pending_review / none_identified) (`__init__.py:125`) | Omitted |
| `empty_state_source.text` | Clear card reason when no `state_reason` or `reason_code` is sent (`__init__.py:123-124`) | No reason line (clear) |
| `next_step` | "What happens next" on the card (`__init__.py:126`) | Omitted |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes (e.g. policy override key) |
|---|---|---|
| "Privacy role evidence", "Security role evidence" | Key/value labels | `s12:44` (`KINDS`) |
| "Detected" (check icon, green) | Evidence value `detected` | `s12:12, 36` |
| "Not detected in the sources checked" (attention icon, not red) | Evidence value `not_detected` | `s12:12, 36`. Status key `not_detected`. A missing role is not treated as a failure |
| "Role found" | Label of each `roles_found` row | `s12:48` |
| "<role> (source: <a>; <b>)" | Value of each `roles_found` row | `s12:48` |
| "Not recognised (“<value>”)" (grey icon) | Evidence value that is neither `detected` nor `not_detected` (same wording as an unknown approval state in 13) | `s12:39-40` |
| "The security resourcing check was switched off for this assessment, so public evidence of privacy and security roles was not looked for." | Card reason when `enabled` is `false` and no `state_reason` is sent | `s12:16-19` |
| "Held for review: <reason text>." | `pending_review` card when `reason_code` is set | `_shared:67-69` |
| Card titles, "What was checked", "What happens next" | State card | Shared (`components.py:282-321`) |

The module has no policy-file overrides.

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| `enabled` is `false` | State becomes `not_applicable`, flag `_card_only`. Opener + card only. Card reason: `state_reason`, else the generator's switched-off sentence (see Hardcoded). `summary` still prints as the verdict | `s12:16-19`, `_shared:46-48` |
| State is a no-result state and neither evidence field has a value | `_card_only`: card only, no body, no generated verdict | `_shared:49-50`, `s12:30, 61` |
| State is a no-result state and an evidence field has a value | Card, then the key/value list and message. No KPI strip | `s12:60-61`, `__init__.py:205-209` |
| `summary` present | Opener shows `summary` | `__init__.py:192` |
| `summary` absent and not `_card_only` | Opener shows `neutral_message`, else `narrative_source` | `s12:29-30` |
| `summary` present, message present, message ≠ `summary` | Message printed as a paragraph after the list | `s12:50-51` |
| Evidence value `detected` | Check icon + "Detected" | `s12:34-36` |
| Evidence value `not_detected` | Attention icon + "Not detected in the sources checked" | `s12:34-36` |
| Evidence value is null / absent | Missing-value cell with the payload reason (shared NullReason rule) | `s12:37-38` |
| Evidence value is any other string | "Not recognised (“<value>”)" + QA `unknown_term` | `s12:39-40` |
| `roles_found[]` item is not a dict or has no `role` | Skipped | `s12:46` |
| `pending_review` with `reason_code` | Card reason "Held for review: <text>." The word "held for review" is not repeated if the reason text already starts with it | `_shared:67-69` |
| `pending_review` without `reason_code`, or `clear` / `partial` / `none_identified` | Card uses the default reason (`state_reason` / `reason_code` / for clear `empty_state_source.text`) | `__init__.py:119-126` |
| Two or more key/value rows share the same null reason | Reason printed once as a footnote | `tables.py:307-311` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Message | `neutral_message` or else `narrative_source` | `s12:25-26` |
| Has role data (for the no-result body) | `privacy_role_evidence` or `security_role_evidence` is truthy | `s12:17` |
| 01 "All aspects" result line | "<n detected> of 2" + "privacy and security roles with public evidence", plus "<k> not recorded" when an evidence value is not `detected`/`not_detected`. No line when neither value is known | `s01_executive_overview.py:379-386` |

## Read but never printed

| Field | Why it is read (QA, ordering, ...) |
|---|---|
| `enabled` | Switch-off rule only |
| `state_label_source` | Not read |
| `review_flags[]` | Not read by this section |
| `aspect_score` | Not read. Section 12 is not in the 01 "Aspect scores" list (`s01_executive_overview.py:272-274`) |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| `findings` | Identified | No card. KPI strip, key/value list, message |
| `clear` (roles found, nothing missing) | No findings | Card "No findings within the scope and time of this check" (reason only if sent, plus "What was checked") + full body |
| `partial` | Partial coverage | Banner (reason + coverage) + full body |
| `pending_review` | Pending review | Card "Result held for review" + "Held for review: …" + full body |
| `none_identified` | None identified | Card "None identified" + full body |
| `not_assessed` / `not_applicable` / `unavailable` | Not assessed / Not applicable / Unavailable | Card. Reason order: `state_reason`, then `reason_code` text, then `reason`, then `narrative_source`. Then the key/value list and message when role evidence exists. No KPI strip |
| any state + `enabled: false` | Not applicable | Card only |

## QA checks raised

| check id | severity | when |
|---|---|---|
| `unknown_term` | warn | An evidence value is neither `detected` nor `not_detected` (`s12:39`) |
| — | — | Shared checks such as `check_min_width` on key/value values still apply (see [README](README.md)) |

## Backend checklist

- MUST send:
  - `state`
  - `privacy_role_evidence` and `security_role_evidence`, each `detected` or `not_detected`. Send `null` with a `reason_code` when the value is unknown; any other value prints "Not recognised (“<value>”)" with a QA warn.
- SHOULD send:
  - `summary`
  - `neutral_message`: neutral copy. The generator never prints a causal claim from the source in its place.
  - `intro_source`
  - `roles_found[] {role, sources[]}`
- For a no-result or `pending_review` state, send `state_reason` or `reason_code`.
- Optional:
  - `metrics[]` (each metric needs a `unit`)
  - `narrative_source` (fallback copy)
  - `what_checked` / `empty_state_source {text, coverage}`
  - `next_step`
  - `enabled: false` (switches the module off)
