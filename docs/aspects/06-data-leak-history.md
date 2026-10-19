# 06 Data breach and leak history

Payload key: `sections.data_leak_history` · Module: [s06_data_leak_history.py](../../cyberrank_report/sections/s06_data_leak_history.py) · Shared rules: [README](README.md)

Every event prints inline in the section (no long-list split yet, whatever the count). Appendix D.3 is an **index
row only** and never has a printed register (`d3_leaks` in
[app_d_evidence_registers.py](../../cyberrank_report/sections/app_d_evidence_registers.py)).

## Layout (top to bottom)

1. Opener and card (shared, README §3). Verdict = `summary`; the module has no `verdict()` or `card()` hook.
2. KPI strip: every `metrics[]` item as sent, then "Last valid event" (when `last_valid_event` is present), then
   "Open events (excludes resolved)" (when an event is resolved).
3. Note "Source: “…”" (source sentence, quoted).
4. *Only when `events[]` is non-empty:*
5. "Events in the period checked (N)" (H2), N = distinct events.
6. Lead sentence: "The rating uses the …" (body text) or a note saying no event is marked / the named event cannot be
   shown as used in the rating (inaccurate, not eligible, resolved or validity `unknown`).
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
| `metrics[]` (Metric) | One KPI tile each, as sent: value + unit, `label`, state chip when `state` ≠ findings (`s06:306,326-327`) | Null value: "Not available" + reason (or "Not applicable" for state `not_applicable`) |
| `metrics[id=events_reported].value` | Tile as above; QA comparison with record counts (`s06:342-347`) | No QA comparison |
| `last_valid_event` — dict `{event_id \| value, source_label, occurred_at?, entity_link?, event_type?}`, a plain event-id string, or a NullReason | Names the rating event: matched to `events[].event_id`, including a record merged away by `canonical_event_id` (it resolves to the kept event) (`s06:104-112`); drives the tile, lead sentence, "Used in rating" status, `adjust()` hold | Key absent: no tile. NullReason / no match: tile "Not available ({reason})", lead note "Event used in the rating: Not available ({reason}). …" |
| `last_valid_event.source_label` | "Source: “…”" note, when `last_reported_source` is absent (`s06:328-330`) | No note |
| `last_reported_source` | "Source: “…”" note, verbatim (wins over `source_label`) | Falls back to `last_valid_event.source_label` |
| `events[]` | Timeline + table rows (non-dict items dropped) (`s06:308`) | Empty: section ends after the KPI strip / source note |
| `events[].event_id` | Lead matching only, also on merged records (`s06:110-111`) | Cannot be the lead by id |
| `events[].canonical_event_id` | Merge key: records sharing it are one row (first kept); printed in "Same event (ID {id}) …" (`s06:115-127,242-245`) | No merging |
| `events[].occurred_at` (Date or NullReason; siblings `occurred_at_state` / `_reason_code` / `_reason`) | Date column head line (`fmt_date`, e.g. 14 Nov 2025); sort key; timeline position; lead sentence date (`s06:268-271,333,336`) | Date cell "Not available ({reason})"; sorted last; not on the timeline; counted in the undated note |
| `events[].disclosed_at` | "Disclosed {date}" under the date (only if it differs from `occurred_at`) (`s06:272-274`) | Line omitted |
| `events[].date_basis` | "Dated by occurrence date / disclosure date / ingestion date" (`occurred_at` / `disclosed_at` / `ingested_at`), else "Dated by {label, lower case}" (`s06:35,275-277`) | Line omitted |
| `events[].age_days_at_assessment` | "{n} days before assessment" (`s06:278-280`) | Line omitted |
| `events[].entity_link` (else `entity`) | Event cell head (medium weight); lead sentence " on {entity}" (`s06:230-232,292`) | "Entity not recorded" (muted); lead sentence without " on …" |
| `events[].event_type` | "  ·  {Type}" after the entity (humanised: `_` → space, first letter upper); lead sentence in lower case (`s06:233-234,291`) | Omitted; lead sentence says "event" |
| `events[].description` → `description_source` → `summary` | Second line of the event cell, first one present (`s06:153-154,235-236`) | Line omitted |
| `events[].scoring_reason` | Muted "Rating: {text}" (`s06:238-239`) | Omitted |
| `events[].source_url` | Live link(s) under the event text (http/https only; merged records' URLs added, de-duplicated) (`s06:248-250`) | If **any** event has a URL: muted "Source not available ({reason})" (reason from `source_url_state/_reason_code/_reason`); else nothing |
| `events[].records_affected` (+ `_state` / `_reason_code` / `_reason` siblings) | "Records affected" head: number + unit (`s06:257-265`) | NullReason cell; column is 96 pt (< 110) so it prints "Not available¹" + footnote (README §5) |
| `events[].records_unit` | Appended to the count in lower case ("12,400 accounts") | Sub-line "unit not recorded" |
| `events[].records_scope` | Sub-line: `organisation` "this organisation only", `aggregate_multi_service` "aggregate across several services", `customer_tenant` "a customer tenant's data", `unknown` "scope not stated", other → humanised value (`s06:253-254,264`) | Omitted |
| `events[].validity_state` | `reported_inaccurate` / `inaccurate` → inaccurate; `resolved` → resolved; `unknown` (policy `validity_values`) → "Validity not confirmed", never counted as valid; any other value ignored (`s06:63-72`) | Event is valid (business answer 2026-10-15) |
| `events[].scoring_eligible` | `true` → "Scoring eligible"; `false` → "Historical" and never the rating event (`s06:75-101`) | "Valid" |
| `snapshot.assessed_at` | Timeline end (dashed line) + legend "Assessment date ({date})" (`s06:337`, `s06:189-217`) | No end line; axis ends at the newest event year |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes (e.g. policy override key) |
|---|---|---|
| "Last valid event" | KPI tile label (`s06:312`) | — |
| "Named event is {not scoring eligible \| resolved \| of unconfirmed validity}; held for review." + chip "Pending review" | Tile when the named event is inaccurate / not eligible / resolved / validity `unknown` (`s06:313-316`) | — |
| "Open events (excludes resolved)" (unit "events") | Tile when ≥ 1 resolved event (`s06:324-325`) | — |
| "Source: “{text}”" | Note (`s06:330`) | — |
| "Events in the period checked ({n})" | H2 (`s06:338`) | — |
| "The rating uses the {date }{event type}{ on entity} (row {n})." / "…; it is not in the event list below." | Lead sentence, body style (`s06:290-300`) | — |
| "The assessment data names the {date }{type}{ on entity}{ (row n)} as the last valid event, but that event is {reported inaccurate \| not scoring eligible} and is not scored. / … but that event is {resolved \| of unconfirmed validity}. No event is shown as used in the rating until this is reviewed." | Lead note (`s06:295-299`) | — |
| "Event used in the rating: Not available ({reason}). The events below are listed without marking one as rating-determining." | Lead note when no lead (`s06:288-289`) | — |
| "{a} source records describe {b} distinct events: records that share an event ID are one event, counted once." | Note (`s06:340-341`) | — |
| Timeline legend "Used in rating", "Scoring eligible", "Historical", "Valid", "Reported inaccurate", "Resolved", "Validity not confirmed" (only kinds present); "Assessment date ({date})"; year ticks | Timeline (`s06:205-217`) | Legend drops " · not scored" |
| "{n} event(s) without a date appear(s) in the table only." | Note (`s06:352-353`) | — |
| "Date", "Event", "Records affected", "Status" | Table head (`s06:354`) | Widths 92 / flex / 96 / 104 pt (`s06:34`) |
| "Disclosed {date}", "Dated by …", "{n} days before assessment" | Date cell sub-lines (`s06:273-280`) | — |
| "Entity not recorded", "Rating: …", "Source not available (…)", "Same event (ID {id}) also reported by {n} other source record(s); counted once." | Event cell (`s06:232-245`) | — |
| "unit not recorded"; scope texts (see `records_scope`) | Records cell (`s06:253-264`) | — |
| Status "Used in rating", "Scoring eligible", "Historical", "Valid", "Reported inaccurate · not scored", "Validity not confirmed", icon + "Resolved" | Status column (`s06:37-45,364-370`) | Text in body colour; colour sits on the timeline marker / Resolved icon |
| "Resolved events were closed by the organisation or an administrator. They stay in the list and the timeline but are not counted as open events." | Note (`s06:359-360`) | — |
| `hold` reason: "The event named as the last valid event is marked reported inaccurate or not scoring eligible, so it cannot be the event used in the rating. Which event, if any, is scored is held for review." | Pending-review card (`s06:137-139,150`) | `reason_code` `lead_event_not_eligible` |
| `hold` reason: "The event named as the last valid event is marked resolved, so it is not shown as the event used in the rating. Which event, if any, is scored is held for review." / "… has validity “unknown”, so it is not shown as …" | Pending-review card (`s06:130-136,150`) | `reason_code` `lead_event_resolved` / `lead_event_unconfirmed` |
| Appendix D index: title "Data leak event details"; content (see Conditional rules) | Index row D.3 (`app_d:615-624,657`) | `lists.data_leak_events.register_title`; `states.register_messages.*` |

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| Status kind, first match: inaccurate → resolved → validity `unknown` → lead and eligible → `scoring_eligible` true / false / absent | "Reported inaccurate · not scored" / "Resolved" / "Validity not confirmed" / "Used in rating" / "Scoring eligible" / "Historical" / "Valid" | `s06:91-101` |
| Eligible | Not inaccurate and `scoring_eligible` is not `false` | `s06:75-77` |
| Lead | `last_valid_event` id (`event_id`, else `value`, or the string) matches the `event_id` of an event or of a record merged into it by `canonical_event_id`; else the `last_valid_event` dict itself if it has `occurred_at`; else none (never inferred) | `s06:104-112` |
| Lead not usable: inaccurate / not scoring eligible / resolved / validity `unknown` (`_not_scored`) | `adjust()` moves the section to `pending_review` via `hold()` (QA `state_adjusted`); tile "Not available" + pending chip; lead note "…as the last valid event, but that event is …" | `s06:80-88,142-150,313-316,295-299` |
| Lead eligible with `occurred_at` | Tile = formatted date | `s06:317-318` |
| Lead missing / lead without date | Tile takes the `last_valid_event` dict's fields (reason, state) → "Not available ({reason})" | `s06:319-320` |
| Lead is not one of the listed events | "; it is not in the event list below" instead of "(row n)" | `s06:293-294` |
| Any event resolved | "Open events" tile (= distinct events − resolved; inaccurate events still count) + resolved note | `s06:322-325,358-360` |
| `last_reported_source` or `last_valid_event.source_label` | "Source: “…”" note | `s06:328-330` |
| `events[]` empty | Stop after KPI strip / source note | `s06:331-332` |
| Sort | `occurred_at` descending; undated last | `s06:333` |
| Records merged by `canonical_event_id` | Merge note | `s06:339-341` |
| `metrics[id=events_reported]` (a number) ≠ distinct events | QA `data_mismatch`: it counts the source records (merge), or it matches neither count. Both numbers already print (tile + heading) | `s06:342-347` |
| ≥ 1 dated event | Timeline | `s06:348-349` |
| Timeline marker | Filled circle; ring for inaccurate / resolved / validity `unknown`; stacked when markers touch. Colours: Used in rating red, Scoring eligible orange, Resolved green (`theme.TONE` resolved → good), others grey | `s06:37-46,195-201,219-224` |
| Timeline year labels | Every year (span ≤ 12), every 2 (≤ 24), else every 5 | `s06:181` |
| `disclosed_at` = `occurred_at` | "Disclosed" line omitted | `s06:273-274` |
| Any event has `source_url` and this one has none | "Source not available (…)" | `s06:240-241` |
| `records_unit` missing / `records_scope` present | "unit not recorded" sub-line / scope sub-line | `s06:264` |
| D.3 index content | `clear` "Not required — no events identified."; `not_assessed` "Not produced — Section 06 was not assessed."; `not_applicable` "Not applicable: {reason}."; `unavailable` "Not produced — data unavailable." (policy texts; built-in default "Not produced."); `none_identified` "Not required — no events identified."; any other state with events "Not required — all {n} event(s) shown in Section 06." — n = distinct events after the `canonical_event_id` merge, any count (Section 06 lists every event) | `app_d:599-612,615-624` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Distinct events | `events[]` merged by `canonical_event_id` (first record kept, others attached); also the D.3 index count | `s06:115-127`; `app_d:619-620` |
| Open events | distinct events − events with `validity_state: resolved` | `s06:322-325` |
| Row number of the lead | position in the date-sorted table | `s06:293` |
| Undated count | events without a parseable `occurred_at` | `s06:350` |
| Timeline span | earliest event year → assessment year + 1; partial dates fall on the 1st of month / Jan | `s06:53-60,172-176` |
| Used by section 01 | Result line "N events" (+ "k resolved", "k reported inaccurate"), or `metrics[id=events_reported]` when `events[]` is empty; aspect score from `metrics[id=data_leak_score]` | `s01:272-274,329-339` |

## Read but never printed

| Field | Why it is read (QA, ordering, ...) |
|---|---|
| `events[].event_id` | Matching `last_valid_event` |
| `events[].validity_state`, `events[].scoring_eligible` | Status kind (only the status words print); `adjust()` hold when the named lead is not usable |
| `metrics[id=events_reported]` | QA comparison with the distinct-event count (also printed as its own tile) |
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
| `state_adjusted` | info | The named last valid event is inaccurate, not scoring eligible, resolved or validity `unknown` → `pending_review` (`s06:142-150`, `sections/__init__.py:171-178`) |
| `data_mismatch` | warn | `events_reported` differs from the distinct-event count: it equals the raw record count (merge by `canonical_event_id`) or matches neither (`s06:342-347`) |

## Backend checklist

- MUST: `state`; `metrics[]` (at least `data_leak_score`, `events_reported` with `unit`); `events[]` (or state
  `not_applicable` with a reason when there are none).
- MUST per event: `event_id`, `occurred_at` (ISO date + `precision`, or a NullReason), `entity_link`, `event_type`,
  `records_affected` (or NullReason siblings), `source_url`.
- MUST to mark the rating event: `last_valid_event` naming an `event_id` that is in `events[]` (else nothing is marked
  "Used in rating"); the id of a record merged by `canonical_event_id` also matches. Naming an inaccurate /
  not-eligible / resolved / validity-`unknown` event holds the section for review.
- Optional: `scoring_eligible`, `scoring_reason`, `validity_state` (`resolved` / `reported_inaccurate` / `unknown`),
  `canonical_event_id`, `disclosed_at`, `date_basis`, `age_days_at_assessment`, `records_unit`, `records_scope`,
  `description` / `description_source`, `last_reported_source` (or `last_valid_event.source_label`), `summary`,
  `intro_source`, `empty_state_source {text, coverage}` for `clear`.
- `snapshot.assessed_at` places the assessment-date line on the timeline.
- `demerit_applied` is never printed; send it for scoring only.
