# 07 Data sovereignty

Payload key: `sections.data_sovereignty` · Module: [s07_data_sovereignty.py](../../cyberrank_report/sections/s07_data_sovereignty.py) · Shared rules: [README](README.md)

Demerit rule E. Governing law / courts found in the published policies, compared with the jurisdictions
accepted by the report owner/requestor. Helpers shared with 08/09/12 live in
[_shared.py](../../cyberrank_report/sections/_shared.py).

**Old payload shape:** `sections.privacy.sovereignty` is moved to `sections.data_sovereignty` at load
(`lift_privacy_subsections`, `sections/__init__.py:136-157`, called from `build.py:122` and `__init__.py:162`).
The old key is always removed from `privacy`. It is moved only when it is a dict and `sections.data_sovereignty`
is absent (a section-level key wins; the old object is then dropped). Its `subtitle_source` becomes `intro_source`
when `intro_source` is empty. A null old object leaves the section missing ("Unavailable" card,
"Section missing from the report data.", `__init__.py:184`).

## Layout (top to bottom)

1. Eyebrow "07 · ASSESSMENT DETAILS", H1 `title` or "Data sovereignty" (scales icon), `intro_source`.
2. State chip + verdict: `summary`, else the generated reading (see Conditional rules).
3. State card (card states and no-result states only).
4. KPI strip from `metrics[]` (result states only; never derived).
5. Key/value list: "Governing law / courts found", "Accepted jurisdictions", "Against the preference", optional "Source verdict".
6. Generated reading paragraph (only when `summary` is present and the reading is not the same text).
7. "Policy text: “…”" (`quote_source`).
8. Note: "Source text: “…”" (`narrative_source`) + optional review note; no Note when both are empty.

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `title` | H1 | "Data sovereignty" (`__init__.py:197`) |
| `intro_source` | Intro line under H1 | Line omitted |
| `state` | Chip, card, body/no-body (see States) | Validation error (build exit 1) |
| `summary` | Opener verdict, verbatim; also switches on the body reading paragraph when it differs from the reading (`s07:53-54`) | Generated reading used as verdict |
| `enabled` | `false` = no preference: see Conditional rules (`_shared.py:38-39`); the accepted list is then not printed (`_shared.py:42-44`) | Treated as enabled |
| `allowed_set[]` | "Accepted jurisdictions" value, comma-joined (`_shared.py:24-25`); `{allowed}` in the reading | Absent or null: `snapshot.preferences_at_assessment.sovereignty_allowed_jurisdictions` (`_shared.py:47-53`, `s07:22`); none there either, or an empty list: no preference, "No preference set" |
| `observed_jurisdiction` (string or `{value}`) | "Governing law / courts found" value (`s07:45`) | NullReason: its `source_label` if set, else "Not available (<reason>)", muted (`s07:41-43`); a NullReason counts as nothing observed (`s07:23`) |
| `match_state` | "Against the preference" chip + choice of reading (`_shared.py:103-106`) | Missing or any value other than match / mismatch / unknown / no_preference: read as `unknown` → "Cannot be compared" |
| `verdict_source` (string or `{value}`) | Extra row "Source verdict" = “…” (`s07:49-51`) | Row omitted |
| `quote_source` | "Policy text: “<text>”" body paragraph (`_shared.py:33-35`) | Omitted |
| `narrative_source` (string or `{value}`) | Note "Source text: “<text>”" (`s07:56-62`) | Omitted; a NullReason prints nothing |
| `metrics[]` | KPI strip tiles, verbatim (`s07:66-68`) | No strip |
| `state_reason` / `reason_code` / `reason` | Card reason (`_shared.py:97-99`, `__init__.py:122`) | Next fallback; last: `narrative_source`, then "Reason not recorded in the assessment data." |
| `what_checked`, `empty_state_source`, `next_step` | Card extras ([README §3](README.md#3-how-every-section-renders)) | Omitted |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes |
|---|---|---|
| "Not compared: no preference set. The governing law found is shown without validation." | Verdict / reading, no preference | `s07:12` |
| "The governing law found is within the accepted jurisdictions ({allowed}), compared with {owner}." | Verdict / reading, `match` | `s07:13` |
| "The governing law found is outside the accepted jurisdictions ({allowed}), compared with {owner}. Check how disputes and legal obligations would be handled before relying on this supplier." | Verdict / reading, `mismatch` | `s07:14-15` |
| "No governing-law or court clause could be matched in the published policies, so legal location cannot be compared with {owner} ({allowed}). Treat it as unresolved until confirmed." | Verdict / reading, `unknown` | `s07:16-17` |
| {owner} = "the preference set by the report owner/requestor" | Inside the readings | `_shared.py:12` |
| {allowed} / empty value = "No preference set" | Readings, "Accepted jurisdictions" | `_shared.py:24` |
| "Governing law / courts found", "Accepted jurisdictions", "Against the preference", "Source verdict" | Key/value labels | `s07:47-51` |
| "Matches the preference" (check, green) / "Does not match the preference" (x, red) / "Cannot be compared" (neutral) / "Not compared: no preference set" (neutral) | "Against the preference" chip | `_shared.py:13-16` |
| "Policy text: “…”" | Quote paragraph | `_shared.py:35` |
| "Source text: “…”" | Note | `s07:57` |
| " Review note: the source prints a verdict, but no governing-law clause was identified, so this report reads the comparison as “Cannot be compared” until the clause is confirmed." | Note, appended | `s07:58-60` |
| "Not compared: no preference set. The observed data is shown below without validation." | Card reason (no preference, data observed) | `_shared.py:17` |
| "Not compared: no preference set." | Card reason when no preference and nothing observed, or `enabled: false`, and no `state_reason` | `_shared.py:86-88` |
| "Held for review: <reason>." | Card reason, `pending_review` + `reason_code` | `_shared.py:94-96` |

No `pol()` policy override keys.

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| `allowed_set` absent or null | Taken from `snapshot.preferences_at_assessment.sovereignty_allowed_jurisdictions` (when that is a list) before every rule below; s01 sees it too | `s07:22`, `_shared.py:47-53` |
| (`enabled` is `false` OR `allowed_set` empty) AND `observed_jurisdiction` has a value (not null / NullReason) AND state is a result state | State forced to `not_applicable` ("Not applicable" chip + card with the no-preference reason) and the body still prints; "Accepted jurisdictions" = "No preference set" (even when `allowed_set` lists countries); chip "Not compared: no preference set"; reading = no-preference text; QA `state_adjusted` | `s07:21-25`, `_shared.py:83-85` |
| (`enabled` is `false` OR `allowed_set` empty) AND nothing observed AND result state | State forced to `not_applicable`, card only ("Not compared: no preference set." unless `state_reason`); QA `state_adjusted` | `_shared.py:86-87` |
| else `enabled` is `false` (no-result state) | State `not_applicable`, card only (`_card_only`), no verdict unless `summary` | `_shared.py:70-71`, `s07:36`, `s07:72` |
| else state is `not_assessed` / `not_applicable` / `unavailable` and neither `allowed_set` nor `observed_jurisdiction` | Card only | `_shared.py:72-73` |
| else no-result state with data | Card + body (items 5–8), no KPI strip | `__init__.py:205-209`, `s07:71-72` |
| `summary` absent | Verdict = reading for `match_state` (TEXT) | `__init__.py:192`, `s07:35-36` |
| `summary` present and different from the reading | Verdict = `summary`; reading printed as a body paragraph after the key/value list | `s07:53-54` |
| `summary` present and equal to the reading | Printed once (verdict only) | `s07:53` |
| `match_state` not one of match / mismatch / unknown / no_preference | Read as `unknown`: chip "Cannot be compared" and the `unknown` reading (never "None") | `_shared.py:103-106` |
| `observed_jurisdiction` missing / NullReason with `source_label` | `source_label` printed muted | `s07:41-43` |
| `verdict_source` set | "Source verdict" row | `s07:50-51` |
| `verdict_source` set AND comparison is `unknown` | Review note appended to the Source-text note | `s07:58-60` |
| Source text or review note non-empty | Note printed (nothing printed when both are empty) | `s07:56-62` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Comparison key | `no_preference` if `_no_preference`, else `match_state` when it is a known key, else `unknown` | `_shared.py:103-106` |
| No-preference flag `_no_preference` | `enabled is False or not allowed_set`, plus observed data and a result state | `_shared.py:38-39`, `77-88` |
| Accepted list | `", ".join(allowed_set)`; empty while `enabled` is `false` | `_shared.py:24-25`, `42-44` |

The match itself is never computed: `match_state` is printed as sent.

## Read but never printed

| Field | Why it is read (QA, ordering, ...) |
|---|---|
| `enabled` | No-preference / switched-off decision only |
| `allowed_set` while `enabled` is `false` | Not printed ("No preference set" instead) |
| `aspect_score` | Read by 01 (rating overview percent), not here (`s01_executive_overview.py:446`) |
| `match_state` (in 01) | 01 "All aspects" result line = chip label (`s01_executive_overview.py:344-346`) |
| `snapshot.preferences_at_assessment.sovereignty_allowed_jurisdictions` | Fallback for a missing `allowed_set` (then printed as the accepted list) |
| `rows[]`, `state_label_source`, `verdict_source_page`, `number`, `group` | Not read by the renderer at all (schema marks them "not printed") |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| `findings` | Findings | KPI strip + items 5–8 |
| `clear` | No findings | Card "No findings within the scope and time of this check" + KPI + items 5–8 |
| `partial` | Partial coverage | Coverage banner + KPI + items 5–8 |
| `pending_review` | Pending review | Card ("Held for review: …" when `reason_code`) + KPI + items 5–8 |
| `none_identified` | None identified | Card + KPI + items 5–8 |
| `not_assessed` / `not_applicable` / `unavailable` | Not assessed / Not applicable / Unavailable | Card; items 5–8 too when `allowed_set` or `observed_jurisdiction` is present |
| any result state + no preference + jurisdiction observed | Not applicable | Card + items 5–8 marked "Not compared: no preference set" |
| any result state + no preference + nothing observed | Not applicable | Card only |
| `enabled: false` (no-result state) | Not applicable | Card only |

## QA checks raised

| check id | severity | when |
|---|---|---|
| `state_adjusted` | info | A result state is forced to `not_applicable` ("<title or Data sovereignty>: <state> -> not_applicable (no_preference_set)"), or `enabled: false` moves a state ("… (module_switched_off)") (`_shared.py:56-62`) |

Shared checks: [README §9](README.md#9-qa-checks-used-by-every-section).

## Backend checklist

- MUST: `state`, `enabled`, `allowed_set[]` (copy of the owner's accepted jurisdictions; empty = no preference;
  absent = the snapshot preference is used), `observed_jurisdiction` (`{value}` or NullReason with `reason_code`,
  e.g. `not_identified`), `match_state` = `match` | `mismatch` | `unknown` (anything else reads as unknown), `summary`.
- No-result states: `state_reason` or `reason_code`.
- Optional: `title`, `intro_source`, `quote_source`, `verdict_source`, `narrative_source` (string or `{value}`; a
  NullReason prints nothing), `metrics[]` (each with `unit`), `aspect_score` (for 01), `next_step`, `what_checked`.
