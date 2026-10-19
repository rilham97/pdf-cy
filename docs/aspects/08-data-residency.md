# 08 Data residency

Payload key: `sections.data_residency` · Module: [s08_data_residency.py](../../cyberrank_report/sections/s08_data_residency.py) + map [geo_map.py](../../cyberrank_report/geo_map.py) · Shared rules: [README](README.md)

Demerit rule F. Where the public systems are hosted (IP location), compared with the countries preferred by the
report owner/requestor. Not privacy criterion H "Data residency" (section 03, policy text). Helpers:
[_shared.py](../../cyberrank_report/sections/_shared.py) (same no-preference logic as [07](07-data-sovereignty.md)).

**Old payload shape:** `sections.privacy.residency` is moved to `sections.data_residency` at load
(`lift_privacy_subsections`, `sections/__init__.py:136-157`): always removed from `privacy`; moved only when it is
a dict and `data_residency` is absent; `subtitle_source` → `intro_source` when that is empty; a null old object
leaves the section missing ("Unavailable" card).

## Layout (top to bottom)

1. Eyebrow "08 · ASSESSMENT DETAILS", H1 `title` or "Data residency" (map-pin icon), `intro_source` (rewritten, see rules).
2. State chip + verdict: `summary`, else the generated reading.
3. State card (card states and no-result states only).
4. KPI strip: `metrics[]`, else derived "Hosts observed" + "Countries identified" (result states only).
5. Key/value list: ["Hosts observed" only when no hosting rows], "Preferred countries", "Against the preference".
6. Generated reading paragraph (only when `summary` is present).
7. Map (modes A2 / A3 only) with caption, legend and off-map line; A3 adds a second block with up to 2 magnified insets.
8. Country table: (shape) · "Country" · "Hosts" · "Against the preference" · ["Evidence"].
9. "Policy text: “…”" (`quote_source`).
10. One Note: payload `note` · unknown-host-mismatch sentence · "Location method: …" · IP caveat.

Items 7–8 and the "Location method" / caveat sentences print only when `observed_hosting[]` has rows.

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `title` | H1 | "Data residency" |
| `intro_source` | Intro line (phrase rewrite, see rules) | Omitted |
| `state` | Chip, card, body/no-body | Validation error |
| `summary` | Opener verdict, verbatim; switches on the body reading paragraph (`s08:106`) | Generated reading |
| `enabled` | `false` = no preference (`_shared.py:37-38`) | Treated as enabled |
| `allowed_set[]` (alpha-2 codes or names) | "Preferred countries" value as sent, comma-joined; resolved to ISO codes for map/table/derived match (`geo_map.py:90-95`) | "No preference set"; empty = no preference |
| `match_state` | "Against the preference" chip in the key/value list + reading choice | `unknown` → "Cannot be compared" |
| `observed_hosting[].country_code` | Resolves the country (`geo_map.py:100`) | Falls back to `country` |
| `observed_hosting[].country` | Used only when `country_code` is empty; resolved by exact name / alpha-2 / alpha-3 | Row goes off the map |
| `observed_hosting[].host_count` (alias `hosts`; `host_count` wins) | "Hosts" cell; map label totals; off-map counter | Cell "Not available (not tracked by the assessment)" (`s08:71-72`); map uses 0 (see bugs) |
| `observed_hosting[].match_state` (`match`/`mismatch`) | Row chip + map shape; kept even when it disagrees with `allowed_set` (QA warn) | Derived from `allowed_set` (`geo_map.py:113-118`) |
| `observed_hosting[].reason_code` | `country_code_placeholder` / `location_unknown` → off-map row; text from `text.REASONS` | — |
| `observed_hosting[].reason` / `state_reason` | Off-map row label (wins over `reason_code`) (`s08:91`) | — |
| `observed_hosting[].evidence_kind` (`{value}` or NullReason) | "Evidence" column when any row has a value; else "Location method: Not available (<reason>)." | Column dropped; `not_printed_in_source` cell for rows without it |
| `note` | Prepended to the Note, unless it contains "ip location" (any case) (`s08:109`) | — |
| `quote_source` | "Policy text: “<text>”" | Omitted |
| `metrics[]` | KPI strip verbatim; replaces the derived tiles (`s08:54-57`) | Derived tiles |
| `state_reason` / `reason_code` / `reason` / `narrative_source` | Card reason (`_shared.py:70-72`) | "Reason not recorded in the assessment data." |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes |
|---|---|---|
| "Not compared: no preference set. The hosting locations found are shown without validation." | Verdict / reading, no preference | `s08:19` |
| "All located hosts are in the preferred countries ({allowed}), compared with {owner}." | `match` | `s08:20` |
| "Public systems were observed outside the preferred countries ({allowed}), compared with {owner}, so customer data may be held outside those countries." | `mismatch` | `s08:21-22` |
| "Hosting locations could not be compared with {owner} ({allowed})." | `unknown` | `s08:23` |
| {owner} = "the preference set by the report owner/requestor"; empty {allowed} = "No preference set" | Readings, key/value | `_shared.py:11,23` |
| "the countries preferred by the report owner/requestor" | Replaces "where you allow data to live" in `intro_source` | `s08:35-37` |
| "Hosts observed" (+ "Not available (not provided in the assessment data)"), "Preferred countries", "Against the preference" | Key/value labels | `s08:102-104` |
| "Hosts observed" (unit hosts), "Countries identified" (unit countries) | Derived KPI tiles | `s08:59-63` |
| "Country", "Hosts", "Against the preference", "Evidence" | Table heads (first column blank = shape) | `s08:117-118` |
| "<Natural Earth name> (<A2>)" | Country cell (asset name, not payload `country`) | `s08:75`, `geo_map.py:80-81` |
| "None observed" / "Preferred country; no hosts observed" / "–" | Row for a preferred country without hosts | `s08:78-79` |
| "<raw>: country name not recognised (not on the map)" | Off-map row, unresolvable name | `s08:90` |
| "<reason text> (not on the map)", e.g. "Location unknown (not on the map)", "Location not identified (the source printed the placeholder code “XX”) (not on the map)" | Off-map row | `s08:91-92`, `text.py:27,38` |
| "Matches the preference" / "Does not match the preference" / "Cannot be compared" / "Not compared: no preference set" | Chips | `_shared.py:12-15` |
| "A host of unknown location is counted as outside the preferred countries, as recorded in the assessment data." | Note | `s08:88-89` |
| "Location method: <evidence or Not available (…)>." | Note (no Evidence column) | `s08:129` |
| "IP geolocation shows where public systems are hosted, not where all customer data is stored." | Note, always when rows exist | `geo_map.py:46` |
| "Policy text: “…”" | Quote | `_shared.py:34` |
| "Map zoomed to the countries in this section (about N° wide[, centred on the Pacific]); the small map shows where." | A2 caption | `geo_map.py:557-558` |
| "World map; badges show the country code, listed in the table below" + "; lettered frames are magnified under the map." or "." | A3 caption | `geo_map.py:560-561` |
| "Hosting in a preferred country" · "Hosting outside the preferred countries" · "Preferred country" | Legend when compared (all three, always) | `geo_map.py:53, 511-513` |
| "Hosting country (not compared)" | Legend when not compared | `geo_map.py:54` |
| "Ring around a dot = small country" | A2 legend, when a small country is drawn | `geo_map.py:573-577` |
| "Not placed on the map: N host(s) with unknown location, … with the placeholder code “XX”, … with an unresolved country name." | Under legend | `geo_map.py:516-524` |
| "<name> · <hosts>" / "<name> · preferred" | A2 map labels (skipped when no room) | `geo_map.py:606` |
| ISO alpha-2 code in a badge; "A" / "B" inset letters; inset caption = country names | A3 | `geo_map.py:617, 629, 647-648` |
| Card reasons: "Not compared: no preference set. The observed data is shown below without validation." / "Not compared: no preference set." / "Held for review: <reason>." | Card | `_shared.py:16,61,67-69` |

No `pol()` policy override keys.

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| (`enabled` false OR `allowed_set` empty) AND `observed_hosting` non-empty AND result state | State → `not_applicable` + card; body prints with "Not compared" chips, navy circles, legend "Hosting country (not compared)"; no KPI strip | `s08:32-33`, `_shared.py:59-60` |
| else `enabled` false | `not_applicable`, card only | `_shared.py:46-48` |
| else no-result state without `allowed_set` and without `observed_hosting` | Card only | `_shared.py:49-50` |
| else no-result state with data | Card + items 5–10, no KPI | `s08:142-143` |
| `intro_source` contains "where you allow data to live" | Phrase replaced | `s08:35-37` |
| `metrics[]` present | Payload tiles | `s08:56` |
| no `metrics[]`, rows present, every row has an int `hosts` | Derived tiles | `s08:56-63` |
| no `observed_hosting` rows | "Hosts observed: Not available (not provided in the assessment data)"; no map, table, method or caveat | `s08:103-104, 110` |
| `summary` present | Reading printed in the body (always) | `s08:106-107` |
| Relevant countries (resolved hosting + preferred-only) ≤ 1 | Mode C: table only, no map | `geo_map.py:36, 240-241` |
| Padded view ≤ 60% of world width (also tried re-centred on the widest gap; narrower wins) | Mode A2: regional map + mini world locator + labels | `geo_map.py:242-250` |
| otherwise | Mode A3: world map with ISO badges; up to 2 insets for clusters (< 0.16 units apart) or countries with ≤ 2 dots | `geo_map.py:251, 258-268` |
| Row `reason_code` = `country_code_placeholder` | Off-map, "placeholder" | `geo_map.py:101-102` |
| Row `reason_code` = `location_unknown` OR no `country_code`/`country` | Off-map, "unknown location" | `geo_map.py:103-104` |
| Code/name is `XX`, `ZZ`, `--`, `??` or empty | Off-map, "placeholder" | `geo_map.py:65, 72-73` |
| Code/name not resolvable | Off-map "country name not recognised" + QA | `geo_map.py:107-109` |
| Compared, row `match_state` match/mismatch | Used as is (QA warn if it differs from `allowed_set`) | `geo_map.py:115-118` |
| Compared, row has no valid `match_state` | match if its ISO code is in resolved `allowed_set`, else mismatch | `geo_map.py:113, 118` |
| `allowed_set` given but none resolvable | Not compared on map/table; row chips "Cannot be compared" | `geo_map.py:96`, `s08:76` |
| Off-map row, not compared | Chip "Not compared: no preference set" | `s08:83-84` |
| Off-map row `match_state` not a known value | Chip "Cannot be compared" | `s08:85-86` |
| Off-map row `match_state` = `mismatch` | Chip "Does not match…" + unknown-host Note sentence | `s08:87-89` |
| Any row has a non-null `evidence_kind` | "Evidence" column (preferred-only rows "–") | `s08:116-118` |
| No row has `evidence_kind` | No column; widths fitted to chip text; "Location method: …" sentence | `s08:121-129` |
| Payload `note` mentions "ip location" | Dropped (caveat replaces it) | `s08:109` |
| Note sentences | De-duplicated, each ended with "." | `s08:133` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Hosts observed (KPI) | sum of `observed_hosting[].hosts` | `s08:59` |
| Countries identified (KPI) | count of distinct `country_code or country` over rows that have one | `s08:62-63` |
| Row ISO code / printed country name | `resolve(country_code or country)` against the Natural Earth asset | `geo_map.py:68-77` |
| Row comparison when not sent | ISO code ∈ resolved `allowed_set` | `geo_map.py:113` |
| Preferred-only rows | resolved `allowed_set` codes with no hosting row | `geo_map.py:121` |
| Map mode, viewport, Pacific centring, insets | see Conditional rules | `geo_map.py:237-268` |
| A2 caption degrees | round(view width / world width × 360) | `geo_map.py:557` |
| Map label host totals | sum of row hosts per country (null → 0) | `geo_map.py:600-601` |
| Off-map counter | sum of hosts per off-map reason (null → 0) | `geo_map.py:517-519` |

## Read but never printed

| Field | Why it is read (QA, ordering, ...) |
|---|---|
| `enabled` | No-preference decision |
| `observed_hosting[].country` (when `country_code` present) | Not used; the asset name prints instead |
| `observed_hosting[]` order | Map numbering / table order (first occurrence) |
| `aspect_score` | Read by 01 only (`s01_executive_overview.py:446`) |
| `observed_hosting`, `allowed_set` (in 01) | 01 result line "N of M hosting countries outside the preference" (`s01_executive_overview.py:349-360`) |
| `rows[]`, `state_label_source`, `observed_hosting[].state`, `observed_hosting[].source_label`, `<field>_reason_code` siblings of `hosts` | Not read at all |
| `snapshot.preferences_at_assessment.residency_allowed_countries` | Not read: send the list as `allowed_set` |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| `findings` | Findings | KPI + items 5–10 |
| `clear` | No findings | Card + KPI + items 5–10 |
| `partial` | Partial coverage | Banner + KPI + items 5–10 |
| `pending_review` | Pending review | Card ("Held for review: …") + KPI + items 5–10 |
| `none_identified` | None identified | Card + KPI + items 5–10 |
| `not_assessed` / `not_applicable` / `unavailable` | Not assessed / Not applicable / Unavailable | Card; items 5–10 when `allowed_set` or `observed_hosting` present |
| result state + no preference + hosting rows | Not applicable | Card + body, "Not compared" everywhere |
| `enabled: false` otherwise | Not applicable | Card only |

## QA checks raised

| check id | severity | when |
|---|---|---|
| `residency_country` | warn | A preferred country is not resolved ("preferred country 'X' not resolved; not drawn on the map") (`geo_map.py:95`) |
| `residency_country` | warn | A hosting country is not resolved ("hosting country 'X' not resolved; counted off the map, not guessed") (`geo_map.py:109`) |
| `residency_country` | warn | Row `match_state` disagrees with `allowed_set` ("<A2>: payload match_state … differs from the preference …; payload kept") (`geo_map.py:115-116`) |

## Backend checklist

- MUST: `state`, `enabled`, `allowed_set[]` (ISO alpha-2 preferred; empty = no preference), `match_state`
  (`match` | `mismatch` | `unknown`), `summary`, `observed_hosting[]` with `country_code` (alpha-2) and
  `hosts` (int; also send `hosts` even if you send `host_count`, the KPI reads `hosts` only).
- Unknown location: `country: null` + `reason_code: location_unknown` (or `country_code_placeholder`); add
  `match_state: mismatch` only if the scoring counted it outside.
- Optional: `observed_hosting[].match_state`, `evidence_kind` (`{value: "IP geolocation"}`), `metrics[]`, `note`,
  `quote_source`, `intro_source`, `title`, `aspect_score` (01), no-result `state_reason`/`reason_code`.
