# 09 Legal terms & conditions

Payload key: `sections.legal_terms` · Module: [s09_legal_terms.py](../../cyberrank_report/sections/s09_legal_terms.py) · Shared rules: [README](README.md)

Demerit rule G: customer-protection clauses in the published terms of a public login / payment portal. Rule G
outcome: portal present and neither clause found = counted against the rating; one or both found = not counted.

**Old payload shape:** `sections.privacy.terms_conditions` is moved to `sections.legal_terms` at load
(`lift_privacy_subsections`, `sections/__init__.py:136-157`): always removed from `privacy`; moved only when it is
a dict and `legal_terms` is absent; `subtitle_source` → `intro_source` when that is empty; a null old object
leaves the section missing ("Unavailable" card).

## Layout (top to bottom)

1. Eyebrow "09 · ASSESSMENT DETAILS", H1 `title` or "Legal terms & conditions" (scroll icon), `intro_source`.
2. State chip + verdict: `summary`, else the rule G outcome line, else `narrative_source`.
3. State card (card states and no-result states only).
4. KPI strip: `metrics[]`, else derived "Customer-protection clauses found (of 2)" (result states only).
5. Key/value list: one row per `rows[]` item (label → yes/no icon, link or text); or a single "Login / payment portal" row.
6. Rule G outcome line (when not already the verdict / summary).
7. `narrative_source` paragraph (when not already the verdict / summary).

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `title` | H1 | "Legal terms & conditions" |
| `intro_source` | Intro line | Omitted |
| `state` | Chip, card, body/no-body | Validation error |
| `summary` | Opener verdict, verbatim; dedupes items 6–7 (`s09:114`) | Generated verdict |
| `enabled` | `false` → `not_applicable`, card only (`_shared.py:70-71`) | Treated as enabled |
| `portal_detected` (bool, yes/no word or `{value}`) | Rule G portal input (wins over the rows) (`s09:66-69`); row "Login / payment portal" when `rows[]` is empty, or when the flag is a NullReason and no row is the portal flag row (`s09:108-112`) | Missing or NullReason: portal read from the portal flag row (row `id: portal_detected` or label exactly "Login / Payment Portal", any case); no such row = unknown, no rule G outcome. A NullReason fallback row prints "Not available (<reason>)" |
| `rows[].id` | `portal_detected` marks the portal flag row (`s09:54-56`) | Matched by label instead |
| `rows[].label` (string or `{value}`) | Key/value label, verbatim; also matched by keyword for the two clauses | "Row label not recorded" (`s09:61`) |
| `rows[].value_source` (else `rows[].value`; string, bool or `{value}`) | Key/value value: see Conditional rules (`s09:40-51`) | Null / NullReason → "Not available (<reason>)" via the key/value list |
| `narrative_source` | Body paragraph; verdict when there is no outcome and no `summary`; card reason fallback | Omitted |
| `metrics[]` | KPI strip verbatim; replaces the derived tile | Derived tile |
| `state_reason` / `reason_code` / `reason` | Card reason (`_shared.py:97-99`), e.g. `no_login_or_payment_portal_detected` → "No customer login or payment portal was detected on the public site." | `narrative_source`, then "Reason not recorded in the assessment data." |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes |
|---|---|---|
| "Neither clause found; counted against the rating." | Verdict or body line, n = 0 | `s09:81` |
| "One clause found; not counted against the rating." | n = 1 | `s09:82` |
| "Both clauses found; not counted against the rating." | n = 2 | `s09:83` |
| "Customer-protection clauses found (of 2)" (unit "clauses": "0 clauses", "1 clause", "2 clauses") | Derived KPI tile | `s09:101-102` |
| "Login / payment portal" + "Detected" / "Not detected" (or "Not available (<reason>)") | Portal row from `portal_detected` (first row) | `s09:108-112` |
| "login / payment portal" | Exact portal flag row label (any case) | `s09:14` |
| "Row label not recorded" | Label of a row without one | `s09:61` |
| "Yes" / "No" | Value text when the source value is a boolean | `icons.py:301-302` |
| Card reasons "Held for review: <reason>." | `pending_review` + `reason_code` | `_shared.py:94-96` |

Source words print as sent minus a leading "#" ("# No" → "No"). No `pol()` policy override keys.

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| `enabled` is `false` | State → `not_applicable` (QA `state_adjusted`), card only, no verdict unless `summary` | `s09:21-22`, `_shared.py:70-71`, `s09:91-92` |
| no-result state AND no `rows[]` AND `portal_detected` absent/null | Card only | `s09:17-18`, `_shared.py:72-73` |
| no-result state with rows or `portal_detected` (a NullReason counts) | Card + items 5–7 (no KPI) | `s09:128-129` |
| Value is a NullReason | Left to the key/value list: "Not available (<reason>)" | `s09:43-44` |
| Value (`{value}` unwrapped, "#" stripped) is a bool or one of detected / found / yes / true / not detected / not found / no / false (any case) | Check (yes) or x (no) icon + the source word | `s09:12-13, 45-47` |
| …and the row is the portal flag row | Same icon, neutral grey (a fact, not a verdict: status `not_compared`) | `s09:107` |
| …otherwise | Yes = green, No = red | `icons.py:295-302` |
| Value starts with `http://` or `https://` | Live link in mono text | `s09:48-50` |
| Any other value | Printed as is | `s09:51` |
| Portal = `portal_detected` when it has a value, else the portal flag row (id `portal_detected` / exact label); a label that only contains "portal" (e.g. "Portal URL") is not the flag | Rule G portal flag | `s09:54-56, 66-69` |
| Clause "protects" = first row whose label contains "protect" | Rule G clause 1 | `s09:77` |
| Clause "notifies" = first row with "notif", else first with "breach" | Rule G clause 2 | `s09:77` |
| Portal is not true (false, unknown or a NullReason), or either clause is unrecognised / absent | No outcome line, no derived KPI; verdict falls back to `narrative_source` | `s09:78-79, 93` |
| Portal true and both clauses known | Outcome line by count n = protect + notify | `s09:80-83` |
| `rows[]` empty and `portal_detected` set, or `portal_detected` is a NullReason and no row is the portal flag row | "Login / payment portal" row first: icon + "Detected"/"Not detected", the word as sent when it is not a yes/no word, or "Not available (<reason>)" for a NullReason | `s09:108-112` |
| Outcome differs from `summary` (or from the verdict) | Outcome printed in body | `s09:115-117` |
| `narrative_source` differs from `summary` (or from the verdict) | Narrative printed in body | `s09:118-119` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Clause / portal flags | source word or `{value}` → True/False via YES_WORDS; null → unknown | `s09:33-37` |
| Clauses found n | protect + notify (only when portal true and both known) | `s09:72-83` |
| Rule G outcome line | n = 0 / 1 / 2 | `s09:81-83` |
| Derived KPI | n, unit clauses, state = section state | `s09:96-102` |

## Read but never printed

| Field | Why it is read (QA, ordering, ...) |
|---|---|
| `portal_detected` (as input) | Rule G gate; printed only in its own portal row (see Conditional rules) |
| `enabled` | Switched-off decision |
| `rows[]` / `portal_detected` (in 01) | 01 result line "n of 2 customer-protection clauses found" or "No login or payment portal detected" (`s01_executive_overview.py:363-368`) |
| `aspect_score` | Read by 01 only |
| `portal_url`, `terms_found`, `state_label_source` | Not read at all (schema marks them "not printed"; put the URL in a `rows[]` item to print it) |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| `findings` | Findings | KPI + items 5–7 |
| `clear` | No findings | Card + KPI + items 5–7 |
| `partial` | Partial coverage | Banner + KPI + items 5–7 |
| `pending_review` | Pending review | Card ("Held for review: …") + KPI + items 5–7 |
| `none_identified` | None identified | Card + KPI + items 5–7 |
| `not_applicable` (e.g. no portal) / `not_assessed` / `unavailable` | Not applicable / Not assessed / Unavailable | Card; items 5–7 when rows or `portal_detected` present |
| `enabled: false` | Not applicable | Card only |

## QA checks raised

| check id | severity | when |
|---|---|---|
| `state_adjusted` | info | `enabled: false` moves a state to `not_applicable` ("<title or Legal terms & conditions>: <state> -> not_applicable (module_switched_off)") (`_shared.py:56-62`) |

Shared checks: [README §9](README.md#9-qa-checks-used-by-every-section).

## Backend checklist

- MUST: `state`, `portal_detected` (bool), `summary`, `rows[]` with `label` + `value_source`. For the rule G
  outcome: the portal flag row has `id: portal_detected` or the label "Login / Payment Portal" (needed only when
  `portal_detected` is not sent), the clause labels contain "protect" and "notif" (or "breach"), and the values
  are one of the yes/no words (a leading "#" is fine), booleans, or `{value: …}` of those.
- Portal not known: `portal_detected: null` + `portal_detected_reason_code` (or a NullReason object); it is never
  counted as a portal.
- No portal: `state: not_applicable`, `portal_detected: false`, `reason_code: no_login_or_payment_portal_detected`.
- Optional: `enabled`, `narrative_source`, `metrics[]` (with `unit`), `intro_source`, `title`, a terms-page URL
  as a `rows[]` value (prints as a link), `aspect_score` (01).
