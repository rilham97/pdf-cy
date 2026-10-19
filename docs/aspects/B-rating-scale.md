# B IISRI rating scale

Payload key: `appendices.b_rating_scale` (+ `rating`) · Module: [app_b_rating_scale.py](../../cyberrank_report/sections/app_b_rating_scale.py) → component [rating_scale.py](../../cyberrank_report/rating_scale.py) · Shared rules: [README](README.md)

Reference appendix with no chip (`REFERENCE`). It is a one-page component with the official IISRI wording.
Almost everything is hardcoded. The payload decides only the H1 title, the intro and **which grade is
highlighted** (`rating.grade`).

## Layout (top to bottom)

1. Eyebrow "B · APPENDICES AND REFERENCES", then the H1 `title` or "IISRI rating scale", then `intro_source`.
2. Verdict row only if `summary` is sent (no chip).
3. No-grade states only: a state panel "Your rating: not available. / not assessed." + the reason + "No grade is highlighted on the scale below."
4. Spectrum: 10 colour segments D (left) → AAA (right), with the grade letters and end labels below. When graded, the selected segment is raised with a ring, and a pin above reads "Your rating: BB · Sufficient".
5. Table Grade | Meaning, AAA first → D. Each row has a colour spine, the letter over its mark, and the meaning (an assurance sentence plus a navy work sentence). The selected row gets a light fill, a box and a "Your rating" pill.

The component's own H1 and its official intro sentence (`rating_scale.INTRO`) are dropped (`story[4:]`): only the payload `intro_source` prints.

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `b_rating_scale.title` | H1 | "IISRI rating scale" |
| `b_rating_scale.intro_source` | Intro under H1 | No intro at all (the component's own intro is dropped) |
| `b_rating_scale.summary` | Verdict (no chip) | Omitted |
| `b_rating_scale.state` | Only no-result states matter: the card replaces the body | — |
| `rating.grade` | `AAA`…`D` as a string or `{value}`, any case, surrounding spaces ignored (`app_b` `rating`). It selects the pin, the ring and the row. | No selection. State panel shown. |
| `rating.state` | Used only when the grade is not valid: `not_assessed` → "Your rating: not assessed". **Any other value** (incl. `assessed` without a valid grade) → "Your rating: not available". | "not available" |
| `rating.state_reason` (string) | Reason in the state panel | "The rating was not provided in the assessment data." (`NO_GRADE_REASON`; also for a non-string or blank value) |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes |
|---|---|---|
| "Your rating: not available." / "Your rating: not assessed." | Panel title (bold) | `rating_scale.py:100-105,288` |
| "No grade is highlighted on the scale below." | End of the panel | `rating_scale.py:289` |
| "The rating was not provided in the assessment data." | Default panel reason | `NO_GRADE_REASON`. The component's own default reasons (`STATE_TEXT[…][1]`) are never reached from the report; its titles are. |
| "Your rating: {grade} · {mark}" | Pin above the spectrum | `rating_scale.py:297` |
| "Your rating" | Pill in the selected table row | `rating_scale.py:302-303` |
| "Controls provide no assurance" / "All controls adequate, appropriate and effective" | Left / right end labels of the spectrum | `END_LABELS`, `rating_scale.py:99` |
| "Grade", "Meaning" | Table heads | `rating_scale.py:299` |
| Marks: Excellent, Very good, Good, Satisfactory, Sufficient, Moderate, Insufficient, Very insufficient, Poor, Very poor | Under each letter | `SCALE`, `rating_scale.py:61-92` |
| 10 official IISRI meanings (assurance + work sentence) | Meaning column | Verbatim from the previous report. Never taken from the payload. |
| Grade colours | Spectrum + spines | No text is ever placed on a colour |

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| `rating.grade` in AAA–D (string or `{value}`, any case) | Assessed: pin + ring + highlighted row. No panel. | `app_b` `rating`, `rating_scale.py:297-303,324-326` |
| Grade missing / anything outside AAA–D | Panel + no selection | `app_b` `rating` |
| `rating.state == not_assessed` | Panel "Your rating: not assessed." | `app_b` `rating` |
| `rating.state` anything else (incl. `assessed`, `findings`, `partial`, absent) | Panel "Your rating: not available." | `app_b` `rating` |
| `rating.state_reason` is not a string (e.g. a dict) or blank | Default panel reason (never a crash) | `app_b` `rating` |
| `b_rating_scale` missing | "Unavailable" card "Section missing from the report data.", no scale | `__init__.py:182-184` |
| A reason longer than ~250 characters | Pushes the last rows to a second page (the header repeats) | `rating_scale.py:22-25` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Selected index | `GRADES.index(rating.grade)` | `rating_scale.py:275` |

## Read but never printed

| Field | Why it is read |
|---|---|
| `b_rating_scale.rows[].meaning_source` | Read by Section 01 (`band_note`, `s01_executive_overview.py:157-166`), not here. Section 01 notes when `rating.band_description_source` differs from it. |
| Not read at all | `b_rating_scale.rows[]` (`grade`, `mark`, `is_current_grade`, `pool360_range*`), `old_appendix_label`, `letter`, `rating.grade_mark`, `rating.risk_band*` |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| none / any result state | — (no chip) | Scale (panel when no grade) |
| `not_assessed` / `not_applicable` / `unavailable` (appendix state) | Not assessed / Not applicable / Unavailable | Card only |

## QA checks raised

| check id | severity | when |
|---|---|---|
| — | — | Shared layout checks only (the page is meant to fit one A4 frame) |

## Backend checklist

- Send `rating.grade` as `"BB"` (a `{value}` record or lowercase is accepted too).
- For no grade, send `grade: null` + `reason_code`, `rating.state: not_assessed | unavailable`, and a one-sentence string `state_reason`.
- Send `b_rating_scale.intro_source`. Without it the appendix has no intro.
- The scale text is fixed. Changing the wording needs a code change and owner approval.
