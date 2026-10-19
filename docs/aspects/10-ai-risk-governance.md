# 10 AI risk and governance

Payload key: `sections.ai_risk_governance` · Module: [s10_ai_risk_governance.py](../../cyberrank_report/sections/s10_ai_risk_governance.py) · Shared rules: [README](README.md)

Demerit rule H. When the module did not run, the narrative signals print as **context only** (RF-04): neutral
styling, nothing reads as a result. The narrative is quoted, never corrected. No `adjust()` and no `verdict()`:
the opener verdict comes from `summary` only. Not part of the old `sections.privacy` shape (no lift).

## Layout (top to bottom)

1. Eyebrow "10 · ASSESSMENT DETAILS", H1 `title` or "AI risk and governance" (brain icon), `intro_source`.
2. State chip + verdict (`summary`; no verdict without it).
3. State card (card states and no-result states only).
4. KPI strip, 3 per row: `metrics[]` + "AI signals observed" (result states only).
5. H2 "Observations recorded for context" (context mode) or "What was observed" (result mode).
6. Context mode only: muted disclaimer paragraph.
7. H3 `subtitle_source` or "Narrative as recorded" + `text_source` in full.
8. H3 "Signals observed" + table "Signal" · "Method" · "Example as recorded".
9. Reconciliation note (conclusion plays down AI use next to observed signals).
10. H3 "Areas an AI assessment rates" (context) / "Areas rated" (result) + table "Area" · "Recorded reading" / "Result" · "Status".

Items 5–10 print only when `narrative_observation` is a non-empty object.

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `title` | H1 | "AI risk and governance" |
| `intro_source` | Intro line | Omitted |
| `state` | Chip, card, body/no-body, context vs result mode, chips in the areas table | Validation error |
| `summary` | Opener verdict, verbatim | No verdict (chip alone) |
| `metrics[]` | KPI tiles verbatim (e.g. `ai_issues`) | Only the signals tile (if any) |
| `next_step` | Card "How it becomes assessed" (not_assessed) / "What happens next" | not_assessed: hardcoded NEXT_STEP |
| `state_reason` / `reason_code` / `what_checked` / `empty_state_source` | Card ([README §3](README.md#3-how-every-section-renders)) | Shared fallbacks |
| `narrative_observation.is_assessment_result` | `true` + result state = result mode | Context mode |
| `narrative_observation.subtitle_source` | H3 over the narrative | "Narrative as recorded" |
| `narrative_observation.text_source` | Paragraph, always in full | H3 + paragraph omitted |
| `narrative_observation.signals_observed[].signal` | "Signal" cell, mapped label | Code humanised ("_" → space, capitalised); empty → "Not recorded" |
| `…signals_observed[].method` | "Method" cell, mapped label | Same fallback |
| `…signals_observed[].example_source` | "Example as recorded" cell, verbatim | "Not available (no example recorded)" |
| `narrative_observation.stated_conclusion_source` | First areas row "AI use in the service" (verbatim); downplay check | Row omitted |
| `narrative_observation.{annex_iii_high_risk_sector, public_ai_policy, privacy_policy_ai_disclosure}` (objects) | Areas rows: text = `source_label`, else "Not available (<reason>)" if value null, else value humanised (`not_found` → "Not found"); chip = its `state` | Non-object → row skipped; no `state` → section state chip |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes |
|---|---|---|
| "Run the AI risk and governance module for this organisation. It rates the areas listed below; the observations shown here are then replaced by assessed results." | Card, "How it becomes assessed" (state `not_assessed`, no payload `next_step`) | `s10:24-25, 33-34` |
| "AI signals observed" (unit signals) | KPI tile | `s10:99` |
| "Observations recorded for context" / "What was observed" | H2 | `s10:46` |
| "Recorded during data collection. These observations are not an assessment result: they are not rated, not scored and not counted in the IISRI rating." | Muted paragraph, context mode | `s10:48-50` |
| "Narrative as recorded" | H3 fallback | `s10:54` |
| "Signals observed"; heads "Signal", "Method", "Example as recorded" | Signals block | `s10:56-58` |
| Signal labels: `ai_infrastructure` → "AI infrastructure", `ai_hiring` → "AI-related hiring", `ai_assistant_mention` → "AI assistant mentioned" | Signal cell | `s10:17-18` |
| Method labels: `csp_header_analysis` → "CSP / header analysis", `careers_pages` → "Careers pages", `public_pages` → "Public pages" | Method cell | `s10:19-20` |
| "Not recorded" | Empty signal / method code | `s10:30` |
| "The recorded conclusion (“<conclusion>”) sits beside N AI signal(s) observed above. The assessment data does not explain how the signals were weighed, so the two are shown as recorded and not reconciled here." | Note | `s10:64-66` |
| "Areas an AI assessment rates" / "Areas rated"; heads "Area", "Recorded reading" / "Result", "Status" | Areas block | `s10:68-70` |
| "AI use in the service" | First areas row label | `s10:77` |
| "EU AI Act Annex III high-risk sector", "Public AI policy", "AI use explained in the privacy policy" | Areas row labels | `s10:21-23` |
| "Observation" (grey square chip) | Status of "AI use in the service" in result mode | `s10:79-80` |

No `pol()` policy override keys.

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| `narrative_observation` missing or `{}` | Items 5–10 omitted | `s10:39-41` |
| `is_assessment_result` is not `true` OR state is `not_assessed` / `not_applicable` / `unavailable` | Context mode: H2 "Observations recorded for context", disclaimer, "Areas an AI assessment rates", column "Recorded reading" | `s10:42, 46-50, 68-69` |
| `is_assessment_result` is `true` AND result state | Result mode: H2 "What was observed", "Areas rated", column "Result"; "AI use in the service" chip = "Observation" | `s10:42, 79-80` |
| `is_assessment_result` is `true` AND no-result state | Context mode + QA `data_mismatch` | `s10:43-45` |
| `text_source` set | Narrative H3 + paragraph | `s10:53-54` |
| `signals_observed` has object items | Signals table | `s10:55-60` |
| signals present AND `stated_conclusion_source` matches `unlikely`, `no evidence`, `does not use`, `do not use`, `not use AI`, `no material` (whole words, any case) | Reconciliation note | `s10:15, 62-66` |
| `stated_conclusion_source` set | "AI use in the service" row with section state chip | `s10:76-78` |
| Area value is an object | Area row; text: `source_label` → missing text → humanised value | `s10:81-86` |
| Area has no `state` | Chip uses section state | `s10:86` |
| `signals_observed` key present (even empty list) | "AI signals observed" tile = its length | `s10:97-99` |
| state `not_assessed` and no payload `next_step` | Card gets NEXT_STEP | `s10:33-34` |
| no-result state | Card + items 5–10 (first block kept with the card); no KPI | `__init__.py:205-209`, `s10:90-91` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| AI signals observed | `len(narrative_observation.signals_observed)` | `s10:97-99` |
| Context vs result mode | `is_assessment_result` + section state | `s10:42` |
| Downplay detection | regex on `stated_conclusion_source` | `s10:15, 63` |
| Humanised codes | `code.replace('_', ' ').capitalize()` | `s10:28-30` |

## Read but never printed

| Field | Why it is read (QA, ordering, ...) |
|---|---|
| `narrative_observation.is_assessment_result` | Mode switch + QA `data_mismatch` |
| area `value` when `source_label` is present | Not printed (source label wins) |
| `metrics[id=ai_issues]` (in 01) | 01 result line "N AI governance issue(s)" (`s01_executive_overview.py:418`) |
| `aspect_score` | Read by 01 only |
| `title_source`, `state_label_source` | Not read at all |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| `findings` | Findings | KPI + items 5–10 (result mode only if `is_assessment_result: true`) |
| `clear` | No findings | Card + KPI + items 5–10 |
| `partial` | Partial coverage | Banner + KPI + items 5–10 |
| `pending_review` | Pending review | Card + KPI + items 5–10 |
| `none_identified` | None identified | Card + KPI + items 5–10 |
| `not_assessed` | Not assessed | Card "Not assessed in this report" + reason + "How it becomes assessed" + items 5–10 in context mode |
| `not_applicable` / `unavailable` | Not applicable / Unavailable | Card + items 5–10 in context mode |

## QA checks raised

| check id | severity | when |
|---|---|---|
| `data_mismatch` | warn | `is_assessment_result: true` while the section is `not_assessed` / `not_applicable` / `unavailable` ("s10: is_assessment_result=true while the section is <state>; shown as context only") (`s10:43-45`) |

## Backend checklist

- MUST: `state`; with a result: `summary`, `metrics[]` (`ai_issues`, unit required),
  `narrative_observation.is_assessment_result: true`.
- Not assessed: `state: not_assessed` + `reason_code` (e.g. `module_not_assessed`); keep
  `narrative_observation` with `is_assessment_result: false` and each area object `state: not_assessed`
  (otherwise the area chip shows whatever state you send).
- Optional: `narrative_observation.{subtitle_source, text_source, signals_observed[] {signal, method,
  example_source}, stated_conclusion_source, annex_iii_high_risk_sector, public_ai_policy,
  privacy_policy_ai_disclosure}` (areas as `{value, state, reason_code?, source_label?}`), `next_step`,
  `intro_source`, `title`, `aspect_score` (01).
