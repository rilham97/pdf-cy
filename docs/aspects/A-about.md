# A About this report

Payload key: `appendices.a_about` · Module: [app_a_about.py](../../cyberrank_report/sections/app_a_about.py) · Shared rules: [README](README.md)

Reference appendix (`REFERENCE`, `sections/__init__.py:33,188-189`). It has no state chip and no card
unless the state is `not_assessed` / `not_applicable` / `unavailable`. The appendix has three parts: the
payload's static text, the report details, and the legend of state chips.

## Layout (top to bottom)

1. Eyebrow "A · APPENDICES AND REFERENCES", then the H1 `title` or "About this report" (no icon), then `intro_source`.
2. Verdict row only if `summary` is sent. It has no chip, so the text runs full width (`components.py:272-273`).
3. `about_source` paragraph.
4. H3 "Data sources" + one bullet per `data_sources_source[]` item.
5. H3 "Report details" + a key/value list (6 rows).
6. H3 "Reading the result states" + one sentence + a State | Meaning table (9 rows).

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `a_about.title` | H1 | "About this report" |
| `a_about.intro_source` | Intro under H1. It also switches `about_source` to body style. | — |
| `a_about.summary` | Verdict text (no chip) | Omitted |
| `a_about.about_source` | Intro style if `intro_source` is absent, else body style (`app_a:41-43`) | Paragraph omitted |
| `a_about.data_sources_source[]` | Bullets, each `sentence()`d (first letter upper, trailing period added) | H3 + bullets omitted |
| `a_about.state` | Only no-result states matter: the card replaces the body | No chip |
| `identity.organisation_name` | "Organisation" row | "Not available (not provided in the assessment data)" |
| `identity.domain` | "Domain" row | Same |
| `snapshot.assessed_at` (Date) | "Assessment date" row, DD Mon YYYY | Its own null reason, else "not provided in the assessment data" |
| `snapshot.generated_at` (Date) | "Report generated" row | Same |
| `identity.issuer.organisation_name` | "Issued by" row | Reason from `issuer.reason` / `state_reason` / `reason_code` (`app_a:33`), else "reason not recorded" |
| `snapshot.assessment_id` (`{value}` or NullReason) | "Assessment ID" row | NullReason reason, else "not provided in the assessment data" |

When two or more rows share the same null reason, they print "Not available¹" and the reason is printed once
under the list (`tables.py` `key_value_list`).

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes |
|---|---|---|
| "Data sources" | H3 | `app_a:46` |
| "Report details" | H3 | `app_a:47` |
| "Organisation", "Domain", "Assessment date", "Report generated", "Issued by", "Assessment ID" | Key/value labels | `app_a:29-34`. No methodology version or time zone rows (owner decision). |
| "Reading the result states" | H3 | `app_a:48` |
| "Each assessed section shows one of these states next to its verdict." | Body line | `app_a:49` |
| "State", "Meaning" | Table heads (no header fill) | `app_a:50-52` |
| State chip labels: Findings, Identified, No findings, Not assessed, Not applicable, Unavailable, Partial coverage, Pending review, None identified | State column | `theme.STATE_LABELS` |
| "Assessed; weaknesses were reported. The severity marks and scores show how serious they are." | Meaning of `findings` | `STATE_MEANING`, `app_a:4-16` |
| "Assessed; items were found in an inventory or good-news section (priority actions, security roles, certifications, fourth-party vendors, cloud). Not a risk by itself." | `identified` | — |
| "Assessed; nothing was found within the sources and period checked. It does not mean the organisation is safe." | `clear` | — |
| "The module was not run for this report. No result is implied." | `not_assessed` | — |
| "The check does not apply to this organisation." | `not_applicable` | — |
| "The value could not be obtained or used. The reason is printed with it." | `unavailable` | — |
| "Only part of the scope was covered; the results cover the part shown." | `partial` | — |
| "A value exists but its meaning is unclear or contradicted; held for review." | `pending_review` | — |
| "Assessed; nothing was found in an inventory section. Not a statement about risk." | `none_identified` | — |

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| `about_source` set and `intro_source` set | `about_source` in body style | `app_a:41-42` |
| `about_source` set, no `intro_source` | `about_source` in intro style (it plays the opener intro) | `app_a:43` |
| `data_sources_source` empty / absent | No "Data sources" block | `app_a:44-46` |
| A detail value is falsy | Null record `not_printed_in_source`. The issuer uses its own reason fields. | `app_a:27-35` |
| `a_about` missing | "Unavailable" card "Section missing from the report data.", no body | `__init__.py:182-184` |
| `a_about.state` in no-result states | Card replaces the body | `__init__.py:205-209` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Dates | `fmt_date` of `snapshot.assessed_at` / `generated_at` | `app_a:19-20` |

## Read but never printed

| Field | Why it is read |
|---|---|
| Not read at all | `a_about.letter`, `source_pages[]`, `closing_source` |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| none / any result state | — (no chip) | Full body |
| `not_assessed` / `not_applicable` / `unavailable` | Not assessed / Not applicable / Unavailable | Card only |

## QA checks raised

| check id | severity | when |
|---|---|---|
| — | — | Shared checks only |

## Backend checklist

- Send `about_source` (one paragraph) and `data_sources_source[]` (short phrases; the generator adds the capital letter and the period).
- The details come from `identity` and `snapshot`, not from `a_about`. Send `identity.issuer.organisation_name`, or a `reason_code` on `issuer`.
- Send `snapshot.assessment_id` as `{value}`.
- Do not send `state` for this appendix unless the whole appendix should be replaced by a card.
