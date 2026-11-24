# 08 Data residency

Payload key: `sections.data_residency` · Module: [s08_data_residency.py](../../cyberrank_report/sections/s08_data_residency.py) + map [geo_map.py](../../cyberrank_report/geo_map.py) · Overflow register: `D.1.3` ([app_d_evidence_registers.py](../../cyberrank_report/sections/app_d_evidence_registers.py)) · Shared rules: [README](README.md)

Demerit rule F. Where the organisation's public systems are hosted (IP location), compared with the countries preferred
by the report owner/requestor. Not privacy criterion H "Data residency" (section 03, policy text). Helpers:
[_shared.py](../../cyberrank_report/sections/_shared.py) (same no-preference logic as [07](07-data-sovereignty.md)).

**Two layout modes (100% backward compatible):**
- **Domain-level mode (recommended):** active whenever `sections.data_residency.locations[]` **or**
  `sections.vulnerabilities.scanned_assets.locations[]` is present. Shows the headline count + `SplitBar` proportion
  bar, map, and vertical country list with JetBrains Mono domain grids sorted by **Opsi 1** (main domain -> `www.` ->
  other subdomains A–Z). If any country overflows `MAX_LINES = 5` grid rows, it prints `+N more in D.1.3`, adds a
  clickable register pointer, and Appendix D emits the full **`D.1.3 Hosting locations by domain`** register.
- **Legacy aggregate mode:** active when only `observed_hosting[]` is sent (no per-domain `locations[]`). Keeps the
  derived KPI strip (`Hosts observed` + `Countries identified`), key/value summary, map, and compact country table.

**Old payload shape:** `sections.privacy.residency` is moved to `sections.data_residency` at load
(`lift_privacy_subsections`, `sections/__init__.py:140-157`): always removed from `privacy`; moved only when it is
a dict and `data_residency` is absent; `subtitle_source` → `intro_source` when that is empty; a null old object
leaves the section missing ("Unavailable" card).

---

## Layout (top to bottom)

### Domain-level mode (when `locations[]` is present)
1. **Opener:** Eyebrow `"08 · ASSESSMENT DETAILS"`, H1 `title` or `"Data residency"` (map-pin icon), `intro_source` (phrase rewritten, see rules).
2. **State chip + verdict:** `summary`, else the generated reading.
3. **State card:** card states and no-result states only.
4. **KPI strip:** `metrics[]` only if explicitly sent by the payload (no derived KPI tiles, because item 6 carries the counts).
5. **Key/value row:** `"Preferred countries"` (comma-joined `allowed_set`, or `"No preference set"`).
6. **Headline + proportion bar:**
   - Compared: `N of M` + `"domains hosted outside the preferred countries"`, `SplitBar` (red outside / green or pale-green preferred / slate undetected), and drawn `G.Marker` legend (omitting `0` items).
   - No preference: `N hosting country/countries` + `"X of Y domains located; no preferred countries set, so nothing is compared"`, `SplitBar` (navy located / slate undetected), and drawn `G.Marker` legend.
7. **Map (modes A2 / A3 only):** caption, legend, off-map summary line, and up to 2 magnified insets in A3. Omitted in mode C (≤ 1 country).
8. **Vertical country list (no table rules, no country flags — uses `G.Marker` shapes + ISO-2 matching the map):**
   - Compared: `"Outside the preference · N countries"` -> `"Preferred · N countries"` (plus unused preferred countries `"<Name> · preferred, no domain hosted"`) -> `"Location not detected · N domains"`.
   - No preference: `"Hosting countries · N countries"` -> `"Location not detected · N domains"`.
   - Under each country header (`marker | ISO-2 | Name   N domains`), an aligned 1–3 column JetBrains Mono domain grid (`C.TechText`, plain copyable text with **no** `https://` hyperlinks, overflow-safe wrapping), sorted **Opsi 1** (`main domain -> www.<main> -> A–Z`).
   - If any country exceeds `MAX_LINES = 5` grid rows (`k * 5` domains), the last cell prints `"+N more in D.1.3"` and a clickable `register_pointer` to `D.1.3` prints below the list.
9. **Quote (optional):** `"Policy text: “…”"` (`quote_source`).
10. **Combined Note:** optional payload `note` (unless mentioning `"ip location"`) · `"Location method: IP geolocation of observed domains."` · IP geolocation caveat.

### Legacy aggregate mode (when only `observed_hosting[]` is present)
1–3. Same opener, verdict, and state card.
4. **KPI strip:** `metrics[]`, else derived `"Hosts observed"` + `"Countries identified"` (result states only, when every row has an integer host count).
5. **Key/value list:** `["Hosts observed"` only when no hosting rows`]`, `"Preferred countries"`, `"Against the preference"`.
6. **Generated reading paragraph:** only when `summary` is present and differs from the generated reading.
7. **Map (modes A2 / A3 only):** caption, legend, off-map line, optional A3 insets.
8. **Compact country table:** `(shape) | Country | Hosts | Against the preference | [Evidence]`.
9–10. Quote (`quote_source`) + combined Note (payload `note` · unknown-host-mismatch sentence · `"Location method: …"` · IP caveat).

---

## From the system (payload — dynamic data)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `title` | H1 | `"Data residency"` |
| `intro_source` | Intro line (phrase rewrite, see rules) | Omitted |
| `state` | Chip, card, body/no-body | Validation error |
| `summary` | Opener verdict, verbatim (legacy mode also prints reading in body when different) | Generated reading |
| `enabled` | `false` = no preference (`_shared.py`); preferred list is not printed | Treated as enabled |
| `allowed_set[]` (alpha-2 codes or names) | `"Preferred countries"` value; resolved to ISO codes for map, groups, and comparison | Falls back to `snapshot.preferences_at_assessment.residency_allowed_countries`; else `"No preference set"` |
| `match_state` | Opener reading choice + legacy `"Against the preference"` chip | Missing/unknown → `"Cannot be compared"` |
| `locations[]` *(recommended)* | Switches Section 08 into **domain-level mode** (also auto-read from `sections.vulnerabilities.scanned_assets.locations[]` when absent here). Each item: `{host, ips: [{ip_address?, country_code?, country?, reason_code?}], reason_code?}` | Falls back to `sections.vulnerabilities.scanned_assets.locations[]`, else legacy `observed_hosting[]` mode |
| `locations[].host` | Domain name in JetBrains Mono grid (and `D.1.3` if overflowed) | Item skipped |
| `locations[].ips[]` | List of resolved IPs + country codes for the domain; empty `ips[]` puts domain in `Location not detected` (`not_resolved` or `locations[].reason_code`) | Treated as `not_resolved` (`"No IP address found"`) |
| `locations[].ips[].ip_address` *(alias `ip`)* | Printed in Appendix `D.1.3` `"IP address(es)"` column (not printed inline in Section 08) | `"—"` in `D.1.3` |
| `locations[].ips[].country_code` *(fallback `country`)* | Resolved via `geo_map.resolve()`; placeholders (`XX`, `ZZ`, `--`, `??`) or unresolved names go to `Location not detected` | Goes to `Location not detected` |
| `locations[].ips[].reason_code` | `location_unknown`, `country_code_placeholder`, or `not_resolved` -> groups under `Location not detected` | Country lookup runs on `country_code`/`country` |
| `observed_hosting[]` | Primary hosting rows for map & `s01` executive overview (auto-derived from `locations[]` if omitted when `locations[]` is present!). Legacy mode table rows. | Auto-derived from `locations[]` when `locations[]` exists; else `"Hosts observed: Not available"` |
| `observed_hosting[].country_code` / `country` | Resolves country for map & legacy table (`country_code` wins) | Row goes off the map |
| `observed_hosting[].host_count` *(alias `hosts`)* | Legacy `"Hosts"` cell, legacy derived KPI, map label totals, off-map counter | `"Not available (<reason>)"` via sibling `*_reason_code`/`*_reason` |
| `observed_hosting[].match_state` | Legacy row chip + map shape (kept even if disagreeing with `allowed_set`, with QA warn) | Derived from `allowed_set` |
| `observed_hosting[].evidence_kind` | Legacy `"Evidence"` column or `"Location method: …"` note | Column dropped |
| `note` | Prepended to the bottom Note (unless it contains `"ip location"`, case-insensitive) | Omitted |
| `quote_source` | `"Policy text: “<text>”"` | Omitted |
| `metrics[]` | KPI strip verbatim (replaces derived tiles in legacy mode; adds KPI strip in domain mode only if sent) | Derived tiles in legacy mode; omitted in domain mode |
| `state_reason` / `reason_code` / `reason` / `narrative_source` | State card reason | `"Reason not recorded in the assessment data."` |

---

## Hardcoded in the generator (static copy & chrome)

| Text or label (exact) | Where it prints | Notes |
|---|---|---|
| `"Not compared: no preference set. The hosting locations found are shown without validation."` | Verdict / reading, no preference | `s08.TEXT` |
| `"All located hosts are in the preferred countries ({allowed}), compared with {owner}."` | Verdict / reading, `match` | `s08.TEXT` |
| `"Public systems were observed outside the preferred countries ({allowed}), compared with {owner}, so customer data may be held outside those countries."` | Verdict / reading, `mismatch` | `s08.TEXT` |
| `"Hosting locations could not be compared with {owner} ({allowed})."` | Verdict / reading, `unknown` | `s08.TEXT` |
| `{owner}` = `"the preference set by the report owner/requestor"`; empty `{allowed}` = `"No preference set"` | Readings, key/value | `_shared.py` |
| `"the countries preferred by the report owner/requestor"` | Replaces `"where you allow data to live"` in `intro_source` | `s08.adjust` |
| `"Preferred countries"` | Key/value label (both modes) | `s08` |
| `"domains hosted outside the preferred countries"` | Domain-mode headline subtitle (compared) | `s08._headline` |
| `"<X> of <Y> domains located; no preferred countries set, so nothing is compared"` | Domain-mode headline subtitle (no preference) | `s08._headline` |
| `"<N> outside"` · `"<N> preferred"` · `"<N> not detected"` · `"<N> located"` · `"<N> location not detected"` | Domain-mode `SplitBar` legend (non-zero items only) | `s08._headline` |
| `"Outside the preference"` · `"Preferred"` · `"Preferred · none hosted"` · `"Hosting countries"` · `"Location not detected"` | Domain-mode H3 group headings | `s08.GROUP_LABELS` |
| `"<Name> · preferred, no domain hosted"` | Unused preferred country row in domain mode | `s08._body_domains` |
| `"Location unknown"` · `"No IP address found"` · `"Placeholder code “<code>”"` | Sub-labels under `Location not detected` | `s08._undetected_label` |
| `"+<N> more in D.1.3"` | Last cell of a country grid when exceeding `MAX_LINES = 5` rows | `s08._domain_grid` |
| `"Hosting locations by domain"` | Register pointer title + Appendix `D.1.3` title | `s08` / `app_d` |
| `"Location method: IP geolocation of observed domains."` | Domain-mode bottom Note | `s08._body_domains` |
| `"IP geolocation shows where public systems are hosted, not where all customer data is stored."` | Bottom Note caveat (both modes when hosting rows exist) | `geo_map.CAVEAT` |
| `"Country"`, `"Hosts"`, `"Against the preference"`, `"Evidence"` | Legacy table headers | `s08._body_legacy` |
| `"Hosts observed"`, `"Countries identified"` | Legacy derived KPI tiles | `s08.metrics` |
| Map captions, legends, off-map counter, A2/A3 labels | Map block | `geo_map.py` |

No `pol()` policy override keys.

---

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| `data_residency.locations[]` or `vulnerabilities.scanned_assets.locations[]` non-empty | **Domain-level mode** (vertical country list + Opsi 1 domain grids); if `observed_hosting[]` is absent, auto-derived from `locations[]` | `s08.adjust`, `s08._body` |
| Both `locations[]` sources absent or empty | **Legacy aggregate mode** (KPI strip + compact country table) | `s08._body_legacy` |
| Domain mode: country has `> k * 5` domains (`k` = 1..3 columns fitted to widest domain) | Truncates that country grid to `k * 5 - 1` domains + `"+N more in D.1.3"`, appends clickable `D.1.3` pointer, and Appendix D renders **`D.1.3 Hosting locations by domain`** | `s08._needs_cap`, `app_d.d13_locations` |
| Domain mode: no country exceeds `k * 5` domains | Every domain prints inline; no truncation and Appendix D omits `D.1.3` (index stays `D.1, D.1.2, D.2..D.7`) | `s08.has_overflow` |
| Domain mode: a domain resolves to IPs in both a preferred and an outside country | Listed under both countries, but counted once under `outside` in the headline `SplitBar` so `outside + preferred + not detected == total unique domains` | `s08._headline` |
| Domain mode: `0` domains outside preference | `SplitBar` preferred segment uses full green (`G.COL['match']`); otherwise pale green (`#B1DDC4`) so red leads | `s08._headline` |
| `allowed_set` absent or null | Taken from `snapshot.preferences_at_assessment.residency_allowed_countries` before all comparison rules | `s08.adjust` |
| (`enabled` false OR `allowed_set` empty) AND hosting/locations present AND result state | State → `not_applicable` (no card) + QA `state_adjusted`; prints `"No preference set"`, navy markers, `"Hosting countries"` | `s08.adjust`, `_shared.adjust_compared` |
| Relevant countries ≤ 1 | Mode C: no map (headline + country list/table only) | `geo_map.choose` |
| Padded view ≤ 60% of world width | Mode A2: regional zoom + mini world locator | `geo_map.choose` |
| Otherwise | Mode A3: world map with ISO-2 badges + up to 2 magnified insets | `geo_map.choose` |

---

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Domain ordering (Opsi 1) | Main domain (`identity.domain` when present, else shortest) -> `www.<main>` -> all other subdomains A–Z, applied inside every country and `Location not detected` bucket | `s08._domain_sort_key` |
| Country ordering (domain mode) | Group priority (`Outside` -> `Preferred` -> `Hosting countries`), then `-len(domains)`, then country name A–Z | `s08._body_domains` |
| Grid columns `k` per country | `max(1, min(3, int(475.9 // (widest_domain_width + 12))))` using JetBrains Mono `dense_tech` | `s08._grid_cols` |
| Headline unique-domain counts | `total = len(located | undetected)`; `outside = domains in any mismatch country`; `preferred = domains in match countries - outside`; `unk = total - len(located)` | `s08._headline` |
| Auto-derived `observed_hosting[]` | When `locations[]` is sent without `observed_hosting[]`, counts unique domains per ISO-2 country + undetected buckets | `s08.hosting_rows_from_locations` |
| Legacy KPIs (`Hosts observed`, `Countries identified`) | Sum of `host_count`/`hosts`; distinct resolved ISO-2 codes (only when `locations[]` is absent and all rows have int counts) | `s08.metrics` |

---

## Example JSON (domain-level mode)

```json
{
  "sections": {
    "data_residency": {
      "state": "findings",
      "title": "Data residency",
      "summary": "Most public systems are hosted in preferred countries; one host is in Brazil, outside the preference, and one host could not be located.",
      "enabled": true,
      "allowed_set": ["GB", "DE", "IE", "US", "SG", "AU"],
      "match_state": "mismatch",
      "observed_hosting": [
        {"country_code": "GB", "hosts": 2, "evidence_kind": {"value": "IP geolocation"}, "match_state": "match"},
        {"country_code": "BR", "hosts": 1, "evidence_kind": {"value": "IP geolocation"}, "match_state": "mismatch"},
        {"country": null, "hosts": 1, "state": "unavailable", "reason_code": "location_unknown"}
      ],
      "locations": [
        {"host": "example.com", "ips": [{"ip_address": "203.0.113.10", "country_code": "GB"}]},
        {"host": "www.example.com", "ips": [{"ip_address": "203.0.113.10", "country_code": "GB"}]},
        {"host": "legacy.example.com", "ips": [{"ip_address": "192.0.2.80", "country_code": "BR"}]},
        {"host": "dev.example.com", "ips": [{"ip_address": null, "country_code": null, "reason_code": "location_unknown"}]},
        {"host": "old.example.com", "ips": [], "reason_code": "not_resolved"}
      ]
    }
  }
}
```

---

## QA checks raised

| check id | severity | when |
|---|---|---|
| `residency_country` | warn | Preferred or hosting country not resolved, or row `match_state` disagrees with `allowed_set` (`geo_map.py`) |
| `state_adjusted` | info | Result state forced to `not_applicable` (`no_preference_set` or `module_switched_off`) (`_shared.py`) |

---

## Backend checklist

- **MUST:** `state`, `enabled`, `allowed_set[]` (ISO alpha-2 preferred; empty = no preference; absent = snapshot fallback), `match_state` (`match` | `mismatch` | `unknown`), `summary`.
- **Recommended (domain-level view):** send `locations[]` on `sections.data_residency` (or shared on `sections.vulnerabilities.scanned_assets.locations[]`), with `{host, ips: [{ip_address, country_code, reason_code?}], reason_code?}`. `observed_hosting[]` can also be sent in sync (or omitted — the generator derives it automatically from `locations[]`).
- **Legacy fallback:** if per-domain data is unavailable, send `observed_hosting[]` with `country_code` (alpha-2) and `host_count`/`hosts` (int, or `null` + `*_reason_code`).
- **Unknown location:** in `locations[]`, send `ips: []` + `reason_code: "not_resolved"`, or an IP with `country_code: null` + `reason_code: "location_unknown"` / `"country_code_placeholder"`.
- **Optional:** `quote_source`, `note`, `metrics[]`, `intro_source`, `title`, `aspect_score` (01), no-result `state_reason`/`reason_code`.
