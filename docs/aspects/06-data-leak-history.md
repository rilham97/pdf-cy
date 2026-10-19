# 06 Data breach and leak history

Payload key: `sections.data_leak_history` · Module: [s06_data_leak_history.py](../../cyberrank_report/sections/s06_data_leak_history.py) · Shared rules: [README](README.md)

Every event prints inline in the section. Appendix D.3 is an **index row only** and never has a printed register
(`_absent` in [app_d_evidence_registers.py](../../cyberrank_report/sections/app_d_evidence_registers.py)).

## Layout (top to bottom)

1. Opener and card (shared, README §3). Verdict = `summary`; the module has no `verdict()` or `card()` hook.
2. KPI strip: every `metrics[]` item as sent, then "Last valid event" (when `last_valid_event` is present), then
   "Open events (excludes resolved)" (when an event is resolved).
3. Note "Source: “…”" (source sentence, quoted).
4. *Only when `events[]` is non-empty:*
5. "Events in the period checked (N)" (H2), N = distinct events.
6. Lead sentence: "The rating uses the …" (body text) or a note saying no event is marked / the named event is not scored.
7. Note "{a} source records describe {b} distinct events: …" (only when records were merged).
8. Timeline (year axis, one marker per dated event, legend, dashed "Assessment date (…)" line).
9. Note "{n} event(s) without a date appear(s) in the table only." (only when undated events exist).
10. Table: Date | Event | Records affected | Status.
11. Note on resolved events (only when an event is resolved).

Appendix D: index row "D.3 · Data leak event details · state chip · content · Section 06, p. n".

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `title`, `intro_source`, `summary`, `state`, `state_reason`, `reason_code`, `what_checked`, `next_step`, `empty_state_source {text, coverage}` | Opener / card via `default_card` (README §3) | Shared rules |
| `metrics[]` (Metric) | One KPI tile each, as sent: value + unit, `label`, state chip when `state` ≠ findings (`s06:273,291-292`) | Null value: "Not available" + reason (or "Not applicable" for state `not_applicable`) |
| `metrics[id=events_reported].value` | Tile as above; QA comparison with record counts (`s06:307-311`) | No QA comparison |
| `last_valid_event` — dict `{event_id \| value, source_label, occurred_at?, entity_link?, event_type?}`, a plain event-id string, or a NullReason | Names the rating event: matched to `events[].event_id` (`s06:83-90`); drives the tile, lead sentence, "Used in rating" status, `adjust()` hold | Key absent: no tile. NullReason / no match: tile "Not available ({reason})", lead note "Event used in the rating: Not available ({reason}). …" |
| `last_valid_event.source_label` | "Source: “…”" note, when `last_reported_source` is absent (`s06:293-295`) | No note |
| `last_reported_source` | "Source: “…”" note, verbatim (wins over `source_label`) | Falls back to `last_valid_event.source_label` |
| `events[]` | Timeline + table rows (non-dict items dropped) (`s06:275`) | Empty: section ends after the KPI strip / source note |
| `events[].event_id` | Lead matching only (`s06:89`) | Cannot be the lead by id |
| `events[].canonical_event_id` | Merge key: records sharing it are one row (first kept); printed in "Same event (ID {id}) …" (`s06:93-105,209-212`) | No merging |
| `events[].occurred_at` (Date or NullReason; siblings `occurred_at_state` / `_reason_code` / `_reason`) | Date column head line (`fmt_date`, e.g. 14 Nov 2025); sort key; timeline position; lead sentence date (`s06:235-238,298,301`) | Date cell "Not available ({reason})"; sorted last; not on the timeline; counted in the undated note |
| `events[].disclosed_at` | "Disclosed {date}" under the date (only if it differs from `occurred_at`) (`s06:239-241`) | Line omitted |
| `events[].date_basis` | "Dated by occurrence date / disclosure date / ingestion date" (`occurred_at` / `disclosed_at` / `ingested_at`), else "Dated by {label, lower case}" (`s06:32,242-244`) | Line omitted |
| `events[].age_days_at_assessment` | "{n} days before assessment" (`s06:245-247`) | Line omitted |
| `events[].entity_link` (else `entity`) | Event cell head (medium weight); lead sentence " on {entity}" (`s06:197-199,259`) | "Entity not recorded" (muted); lead sentence without " on …" |
| `events[].event_type` | "  ·  {Type}" after the entity (humanised: `_` → space, first letter upper); lead sentence in lower case (`s06:200-201,258`) | Omitted; lead sentence says "event" |
| `events[].description` → `description_source` → `summary` | Second line of the event cell, first one present (`s06:120-121,202-203`) | Line omitted |
| `events[].scoring_reason` | Muted "Rating: {text}" (`s06:205-206`) | Omitted |
| `events[].source_url` | Live link(s) under the event text (http/https only; merged records' URLs added, de-duplicated) (`s06:215-217`) | If **any** event has a URL: muted "Source not available ({reason})" (reason from `source_url_state/_reason_code/_reason`); else nothing |
| `events[].records_affected` (+ `_state` / `_reason_code` / `_reason` siblings) | "Records affected" head: number + unit (`s06:224-232`) | NullReason cell; column is 96 pt (< 110) so it prints "Not available¹" + footnote (README §5) |
| `events[].records_unit` | Appended to the count in lower case ("12,400 accounts") | Sub-line "unit not recorded" |
| `events[].records_scope` | Sub-line: `organisation` "this organisation only", `aggregate_multi_service` "aggregate across several services", `customer_tenant` "a customer tenant's data", `unknown` "scope not stated", other → humanised value (`s06:220-221,231`) | Omitted |
| `events[].validity_state` | `reported_inaccurate` / `inaccurate` → inaccurate; `resolved` → resolved; any other value ignored (`s06:59-64`) | Event is valid (business answer 2026-10-15) |
| `events[].scoring_eligible` | `true` → "Scoring eligible"; `false` → "Historical" and never the rating event (`s06:67-80`) | "Valid" |
| `snapshot.assessed_at` | Timeline end (dashed line) + legend "Assessment date ({date})" (`s06:302`, `s06:156-184`) | No end line; axis ends at the newest event year |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes (e.g. policy override key) |
|---|---|---|
| "Last valid event" | KPI tile label (`s06:279`) | — |
| "Named event is not scoring eligible; held for review." + chip "Pending review" | Tile when the named event is inaccurate / not eligible (`s06:280-281`) | — |
| "Open events (excludes resolved)" (unit "events") | Tile when ≥ 1 resolved event (`s06:289-290`) | — |
| "Source: “{text}”" | Note (`s06:295`) | — |
| "Events in the period checked ({n})" | H2 (`s06:303`) | — |
| "The rating uses the {date }{event type}{ on entity} (row {n})." / "…; it is not in the event list below." | Lead sentence, body style (`s06:257-267`) | — |
| "The assessment data names the {date }{type}{ on entity}{ (row n)} as the last valid event, but that event is {reported inaccurate \| not scoring eligible} and is not scored. No event is shown as used in the rating until this is reviewed." | Lead note (`s06:262-266`) | — |
| "Event used in the rating: Not available ({reason}). The events below are listed without marking one as rating-determining." | Lead note when no lead (`s06:255-256`) | — |
| "{a} source records describe {b} distinct events: records that share an event ID are one event, counted once." | Note (`s06:305-306`) | — |
| Timeline legend "Used in rating", "Scoring eligible", "Historical", "Valid", "Reported inaccurate", "Resolved" (only kinds present); "Assessment date ({date})"; year ticks | Timeline (`s06:172-184`) | Legend drops " · not scored" |
| "{n} event(s) without a date appear(s) in the table only." | Note (`s06:316-317`) | — |
| "Date", "Event", "Records affected", "Status" | Table head (`s06:318`) | Widths 92 / flex / 96 / 104 pt (`s06:31`) |
| "Disclosed {date}", "Dated by …", "{n} days before assessment" | Date cell sub-lines (`s06:240-247`) | — |
| "Entity not recorded", "Rating: …", "Source not available (…)", "Same event (ID {id}) also reported by {n} other source record(s); counted once." | Event cell (`s06:199-212`) | — |
| "unit not recorded"; scope texts (see `records_scope`) | Records cell (`s06:220-231`) | — |
| Status "Used in rating", "Scoring eligible", "Historical", "Valid", "Reported inaccurate · not scored", icon + "Resolved" | Status column (`s06:34-41,328-334`) | Text in body colour; colour sits on the timeline marker / Resolved icon |
| "Resolved events were closed by the organisation or an administrator. They stay in the list and the timeline but are not counted as open events." | Note (`s06:323-324`) | — |
| `hold` reason: "The event named as the last valid event is marked reported inaccurate or not scoring eligible, so it cannot be the event used in the rating. Which event, if any, is scored is held for review." | Pending-review card (`s06:115-117`) | `reason_code` `lead_event_not_eligible` |
| Appendix D index: title "Data leak event details"; content (see Conditional rules) | Index row D.3 (`app_d:645-646`) | `lists.data_leak_events.register_title`; `states.register_messages.*` |

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| Status kind, first match: inaccurate → resolved → lead and eligible → `scoring_eligible` true / false / absent | "Reported inaccurate · not scored" / "Resolved" / "Used in rating" / "Scoring eligible" / "Historical" / "Valid" | `s06:72-80` |
| Eligible | Not inaccurate and `scoring_eligible` is not `false` | `s06:67-69` |
| Lead | `last_valid_event` id (`event_id`, else `value`, or the string) matches an event's `event_id`; else the `last_valid_event` dict itself if it has `occurred_at`; else none (never inferred) | `s06:83-90` |
| Lead not eligible | `adjust()` moves the section to `pending_review` (QA `state_adjusted`); tile "Not available" + pending chip; lead note "…is not scored…" | `s06:108-117,280-281,262-266` |
| Lead eligible with `occurred_at` | Tile = formatted date | `s06:282-283` |
| Lead missing / lead without date | Tile takes the `last_valid_event` dict's fields (reason, state) → "Not available ({reason})" | `s06:284-285` |
| Lead is not one of the listed events | "; it is not in the event list below" instead of "(row n)" | `s06:260-261` |
| Any event resolved | "Open events" tile (= distinct events − resolved; inaccurate events still count) + resolved note | `s06:287-290,322-324` |
| `last_reported_source` or `last_valid_event.source_label` | "Source: “…”" note | `s06:293-295` |
| `events[]` empty | Stop after KPI strip / source note | `s06:296-297` |
| Sort | `occurred_at` descending; undated last | `s06:298` |
| Records merged by `canonical_event_id` | Merge note; QA `data_mismatch` when `events_reported` equals the raw record count | `s06:304-311` |
| ≥ 1 dated event | Timeline | `s06:312-313` |
| Timeline marker | Filled circle; ring for inaccurate / resolved; stacked when markers touch. Colours: Used in rating red, Scoring eligible orange, Resolved green, others grey (`theme.TONE`) | `s06:34-42,162-168,186-191` |
| Timeline year labels | Every year (span ≤ 12), every 2 (≤ 24), else every 5 | `s06:148` |
| `disclosed_at` = `occurred_at` | "Disclosed" line omitted | `s06:240-241` |
| Any event has `source_url` and this one has none | "Source not available (…)" | `s06:207-208` |
| `records_unit` missing / `records_scope` present | "unit not recorded" sub-line / scope sub-line | `s06:231` |
| D.3 index content | `clear` "Not required — no events identified."; `not_assessed` "Not produced — Section 06 was not assessed."; `not_applicable` "Not applicable: {reason}."; `unavailable` "Not produced — data unavailable." (policy texts; built-in default "Not produced."); `none_identified` "Not required — no events identified."; ≤ 30 events "Not required — all {n} events shown in Section 06."; > 30 "Not produced — no register data in the payload ({n} events in Section 06)." | `app_d:598-616` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Distinct events | `events[]` merged by `canonical_event_id` (first record kept, others attached) | `s06:93-105` |
| Open events | distinct events − events with `validity_state: resolved` | `s06:287-290` |
| Row number of the lead | position in the date-sorted table | `s06:260` |
| Undated count | events without a parseable `occurred_at` | `s06:314` |
| Timeline span | earliest event year → assessment year + 1; partial dates fall on the 1st of month / Jan | `s06:49-56,139-143` |
| Used by section 01 | Result line "N events" (+ "k resolved", "k reported inaccurate"), or `metrics[id=events_reported]` when `events[]` is empty; aspect score from `metrics[id=data_leak_score]` | `s01:272-274,329-339` |

## Read but never printed

| Field | Why it is read (QA, ordering, ...) |
|---|---|
| `events[].event_id` | Matching `last_valid_event` |
| `events[].validity_state`, `events[].scoring_eligible` | Status kind (only the status words print) |
| `metrics[id=events_reported]` | QA merge comparison (also printed as its own tile) |
| Not read at all | `events[].demerit_applied` (hidden scoring), `events[].listed_as`, `events[].rating_use_label_source`, `state_label_source` |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| `findings` | Findings | Full body |
| `clear` | No findings | Card: `state_reason` / `reason_code` / `empty_state_source.text`; "What was checked": `what_checked` / `empty_state_source.coverage`. Body still built: KPI strip (+ source note); events print if any are sent |
| `not_applicable` (schema: no events) | Not applicable | Card only (reason required) |
| `pending_review` (sent, or set by `adjust()`) | Pending review | Card with reason; full body |
| `partial` | Partial coverage | Banner; full body |
| `none_identified` | None identified | Card; full body |
| `unavailable`, `not_assessed` | Unavailable / Not assessed | Card only |

## QA checks raised

| check id | severity | when |
|---|---|---|
| `state_adjusted` | info | The named last valid event is inaccurate or not scoring eligible → `pending_review` (`s06:115`, `sections/__init__.py:171-178`) |
| `data_mismatch` | warn | Records were merged by `canonical_event_id` and `events_reported` equals the raw record count (`s06:307-311`) |

## Backend checklist

- MUST: `state`; `metrics[]` (at least `data_leak_score`, `events_reported` with `unit`); `events[]` (or state
  `not_applicable` with a reason when there are none).
- MUST per event: `event_id`, `occurred_at` (ISO date + `precision`, or a NullReason), `entity_link`, `event_type`,
  `records_affected` (or NullReason siblings), `source_url`.
- MUST to mark the rating event: `last_valid_event` naming an `event_id` that is in `events[]` (else nothing is marked
  "Used in rating"). Naming an inaccurate / not-eligible event holds the section for review.
- Optional: `scoring_eligible`, `scoring_reason`, `validity_state` (`resolved` / `reported_inaccurate`),
  `canonical_event_id`, `disclosed_at`, `date_basis`, `age_days_at_assessment`, `records_unit`, `records_scope`,
  `description` / `description_source`, `last_reported_source` (or `last_valid_event.source_label`), `summary`,
  `intro_source`, `empty_state_source {text, coverage}` for `clear`.
- `snapshot.assessed_at` places the assessment-date line on the timeline.
- `demerit_applied` is never printed; send it for scoring only.
