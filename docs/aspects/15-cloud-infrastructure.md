# 15 Cloud infrastructure

Payload key: `sections.cloud_infrastructure` · Module: [s15_cloud_infrastructure.py](../../cyberrank_report/sections/s15_cloud_infrastructure.py) · Shared rules: [README](README.md)

Inventory section. The section lists cloud providers seen in public DNS / IP-range / MX / NS records. Here
`findings` means providers were observed, not risk, so the chip reads **Identified**. An empty result reads
"not detected with the methods used", never "no cloud". There is no long-list register. The scan date is
shown without any staleness flag (business answer 8, `s15:91`).

## Layout (top to bottom)

1. Eyebrow "15 · ASSESSMENT DETAILS", then the H1 `title` or "Cloud infrastructure" with the cloud icon, then `intro_source`.
2. Chip + verdict (`summary`).
3. Card (card states / no-result states).
4. KPI strip: the payload `metrics[]` + a "Last scanned" tile (`s15:42-49`).
5. H2 "Detected providers" (also an outline entry).
6. Providers table (Provider · Detected by · Observed) + a note. **Or** "No cloud provider detected with the methods used." + a methods note.

`clear` with no providers: card only, no body (`s15:89-90`).

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `title` | H1 | "Cloud infrastructure" |
| `intro_source` | Intro under H1 | Omitted |
| `state` | Chip / card / body (see States) | Validation error (exit 1) |
| `summary` | Verdict, verbatim | No verdict text (chip alone) |
| `state_reason` | Card reason. For `clear`: used before the hardcoded text. | `clear`: `CLEAR_REASON`. Other states: `reason_code` text, then `STATE_REASON_FALLBACK`. |
| `reason_code` | Card reason (non-`clear` states) | — |
| `what_checked` / `empty_state_source.coverage` | Card "What was checked" | `clear`: generated list (see below). Other states: omitted. |
| `empty_state_source.text` | — (the `clear` reason is overridden by `s15:31`) | — |
| `next_step` | Card "What happens next" / "How it becomes assessed" | `not_assessed`: hardcoded next step (`s15:36-38`) |
| `metrics[]` (each needs `unit`) | One KPI tile each: value + unit + `label`. A chip is added when the metric `state` ≠ `findings`. | No metric tiles. A null value prints "Not available" + its reason. |
| `last_scanned` (Date) | Last tile: DD Mon YYYY. Also used in the `clear` "What was checked" list. | Tile "Not available" + "Scan date not recorded." (null record: its reason; its `state` adds a chip) |
| `detection_methods[]` (codes, section level) | "Detection methods: DNS records, IP ranges, MX records, NS records." in the note | Note sentence omitted |
| `providers[]` (non-dicts skipped) | One table row each | Empty → "No cloud provider detected with the methods used." |
| `providers[].provider` | Provider column, verbatim | "Not available (provider name not recorded)" |
| `providers[].detection_methods` (list or single code) | "Detected by", comma-joined method names | "Not available (<reason>)". If null for **every** row, the column is dropped and noted. |
| `providers[].observed_at` (Date) | "Observed", DD Mon YYYY | Same column-collapse rule |
| `identity`/`snapshot.assessed_at` (via `ctx.identity`) | "Report assessed {date}" in the tile. "(report assessment date {date})" in the `clear` card. | "Not available" |

Method codes → labels (`METHODS`, `s15:7-8`): `dns_records` "DNS records", `ip_ranges` "IP ranges",
`mx_records` "MX records", `ns_records` "NS records". An unknown code prints with `_` replaced by a space.

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes |
|---|---|---|
| "Only providers visible in public DNS, IP-range, MX and NS records can be detected. Services reached through other providers or used only internally are not visible to this check." | `clear` card reason | `CLEAR_REASON`, `s15:10-12` |
| "Detection methods: {methods}." | `clear` card "What was checked" item 1. Also the note under the table / empty sentence. | `s15:34,78,97` |
| "Last scanned: {date} (report assessment date {date})." | `clear` card "What was checked" item 2 | `s15:35` |
| "Run the cloud infrastructure module for this organisation. Providers are then detected from public DNS records, IP ranges, MX records and NS records." | `not_assessed` card "How it becomes assessed" | `s15:37-38` |
| "Last scanned, cloud module" / "Report assessed {date}" | Two-line label of the last KPI tile | `s15:46` |
| "scan date not recorded" | Tile reason when `last_scanned` is absent | `s15:45` |
| "Detected providers" | H2 | `s15:92` |
| "Provider", "Detected by", "Observed" | Table heads | `s15:55` |
| "provider name not recorded", "not recorded" | Reasons for missing cells | `s15:60,62` |
| "{Labels} per provider: not available ({reason})." | Note for a column that was dropped, e.g. "Detected by and observed per provider: not available (…)." | `s15:79-80` |
| "No cloud provider detected with the methods used." | Body when there are no providers (and the state is not `clear`) | `NOT_DETECTED`, `s15:9,96` |

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| `state == clear` and no providers | Card only (reason + "What was checked"). No KPI strip, no table. | `s15:89-90` |
| `state == clear` | Card reason = `state_reason` or `CLEAR_REASON` (`reason_code` / `empty_state_source.text` are ignored) | `s15:30-31` |
| `clear` and no `what_checked` and no `empty_state_source.coverage` | Generated "What was checked": the methods line (only if `detection_methods` is set) + the "Last scanned" line | `s15:32-35` |
| `state == not_assessed` and no `next_step` | Hardcoded next step | `s15:36-38` |
| Any other state that has a body | KPI strip + H2 + table or empty sentence | `s15:91-97` |
| A provider column (other than Provider) is null for **every** row | Column removed. Its label goes into the note, grouped by the first row's reason. | `s15:67-73,79-80` |
| One column left | Auto widths. Otherwise Provider = 1/3 of the width and the rest is split equally. | `s15:75` |
| `detection_methods` set | "Detection methods: …." starts the note (table) or follows the empty sentence | `s15:78,96-97` |
| `last_scanned` missing / null | Tile "Not available" + reason. A `state` on the null record adds a chip. | `s15:45-48` |
| Metric `state` ≠ `findings` | State chip in that tile (`components.py:403-404`) | — |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Method labels | `METHODS[code]`, else the code with `_` → space | `s15:15-16` |
| Dropped-column note | Groups missing columns by reason text | `s15:67-80` |
| Dates | `fmt_date` (precision-aware, never compared) | `s15:25,48,65` |

No counts are derived. The provider count comes only from your `metrics[]`.

## Read but never printed

| Field | Why it is read |
|---|---|
| `metrics[id=cloud_providers_detected]`, `providers[]` | Section 01 "All aspects" line: "n cloud provider(s)". It uses the metric, else the number of providers, else 0 when `clear` (`s01_executive_overview.py:407-412`). |
| Not read at all | `lead_source`, `state_label_source`, `note`, `metrics[].source_label` |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| `findings` | Identified | KPI + table (or the empty sentence) |
| `clear` | No findings | Card. Body only when providers are present. |
| `partial` | Partial coverage | Banner + body |
| `pending_review` | Pending review | Card + body |
| `none_identified` | None identified | Card + body (KPI + "No cloud provider detected…") |
| `not_assessed` / `not_applicable` / `unavailable` | Not assessed / Not applicable / Unavailable | Card only |

## QA checks raised

| check id | severity | when |
|---|---|---|
| — | — | No section-specific checks. Shared checks only (see README). |

## Backend checklist

- Send `metrics[]` with `id: cloud_providers_detected`, `unit: providers` and the count. The generator never counts providers for the KPI.
- Send `last_scanned` as an ISO date (it is validated). A null needs a `reason_code`.
- Send the section-level `detection_methods[]` as codes (`dns_records`, `ip_ranges`, `mx_records`, `ns_records`).
- Per provider: `provider` (name), `detection_methods` (codes), `observed_at` (Date). If a field is not known, send a NullReason. When it is null for every provider, the column is replaced by a single note.
- For an empty result, use `clear` (card only) and not `findings` with an empty list (that prints a KPI strip + "No cloud provider detected…").
- `summary` is the verdict. Nothing is generated when it is missing.
