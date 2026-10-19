# 14 Fourth-party vendors

Payload key: `sections.fourth_party_vendors` · Module: [s14_fourth_party_vendors.py](../../cyberrank_report/sections/s14_fourth_party_vendors.py) · Shared rules: [README](README.md)

A summary of the connected organisations reported for the assessed organisation. It is an inventory, not a
list of weaknesses. Grades print as sent and are never turned into a severity. The full register is
Appendix **D.6** (see [D-evidence-registers.md](D-evidence-registers.md) for the shared register frame).

**`adjust()` changes the state only in two cases** (QA `state_adjusted` info): an empty list becomes
`none_identified` (never "No findings"), and `clear` / `none_identified` with a non-empty list becomes `findings`.
Everything else stands, so `findings` shows as **Identified** (`theme.INVENTORY`) and a payload `partial`
(genuinely partial coverage) shows as Partial coverage. The payload `summary` / `state_reason` / `reason_code`
are never overwritten: the generated summary is only the `verdict()` fallback, and the data-limits sentence is
its own note at the top of the body.

## Layout (top to bottom)

When `vendors[]` is non-empty (state `findings` → "Identified"):

1. Eyebrow "14 · ASSESSMENT DETAILS", then the H1 `title` or "Fourth-party vendors" with the tree-structure icon, then `intro_source`.
2. Chip "Identified" + verdict = payload `summary`, else the generated summary (`verdict`, `summary`).
   A payload `partial` / `pending_review` adds its card (payload reason + `what_checked`) here.
3. Data-limits note (generated, `banner`): "Ratings are as shown on the report date. How each organisation is connected …".
4. KPI strip of 4 tiles (`s14:218-232`).
5. Caption "Rated organisations by grade (n)…" + grade bar D → AAA (`s14:266-276`). Only printed when at least one vendor is rated.
6. H3 "Needs a look (n of N)" + caption + dense table (`s14:358-362`). Only printed when the list is non-empty.
7. Tier T1 (≤ 30 vendors): H3 "All connected organisations (N)" + dense table. Tier T2/T3: a "Full register" pointer to D.6.1.
8. Note: contract disclaimer (+ alias sentence), kept together with the Appendix C pointer.

When `vendors[]` is empty: card "No connected organisations identified" + the Appendix C pointer only.
In the no-result states, the card is followed by the Appendix C pointer (`build_context`).
The Appendix C "Supply-chain aggregation" pointer prints only when `appendices.c_methodology.supply_chain` is set
and its locked page can be inserted (`app_c.supply_chain_present`).

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `title` | H1 | "Fourth-party vendors" |
| `intro_source` | Intro under H1 | Omitted |
| `state` | Chip (see States; `adjust()` only fixes empty / `clear` lists) | Validation error (exit 1) |
| `summary` | Verdict, in every state, verbatim | Generated summary (`verdict`) |
| `state_reason`, `reason_code` | Card reason in the card states, verbatim (never overwritten) | `none_identified`: "None were found with the methods used. …"; other states: `STATE_REASON_FALLBACK` |
| `what_checked` / `empty_state_source.coverage` | Card "What was checked" in the card states (shared `default_card`, `none_identified` included) | Omitted |
| `next_step` | Card "What happens next" / "How it becomes assessed" | Omitted |
| `vendors[]` (non-dict items skipped) | Everything below. The count N is `len(vendors)`. | Empty list → `none_identified` |
| `vendors[].name` (fallback `vendor_name`) | Organisation cell (bold), sort key, self-reference test, alias-group names | Domain shown in mono, else "Name not recorded" (muted) |
| `vendors[].domain` (str or `{value}`) | Next to or under the name (mono, never truncated); self-reference list in the summary | Omitted |
| `vendors[].category` (str or `{label|value}`) | Sector column: `_` → space, first letter upper (`s13.label`, `sector`) | "Unknown" in every table (owner decision) |
| `vendors[].grade` (AAA–D, str or `{value}`, case-insensitive) | Grade chip "BB  Sufficient" (section). Plain letter in D.6.1. Drives all counts. | Any value outside AAA–D counts as **not rated**: "Not rated" or "Not rated (<reason>)" |
| `vendors[].grade_reason_code` / `grade_reason` / `grade_state` (or a NullReason `grade`) | Reason in "Not rated (<reason>)"; a free-text `grade_reason` counts even without a code | No reason text and code `dash_in_source` / `not_printed_in_source` / `blank_in_source` / none → plain "Not rated" (`not_rated`) |
| `vendors[].risk_band_label_source` | Risk band text exactly as sent (no case change), for rated and unrated vendors | Falls back to `risk_band` |
| `vendors[].risk_band` (code) | Band text fallback (as sent). Also the Needs-a-look band test and grouping. | Rated: "Not available (<reason>)" (T1: "Not available¹" + footnote). Unrated: "Not sent" |
| `vendors[].assessed_membership` | `false` → muted line "Not an assessed member (as reported)" | Nothing |
| `vendors[].assessed_at` (Date) | "Assessed on" column (DD Mon YYYY). The column appears only if **any** vendor has one. Also changes the banner wording. | Cell "Not available (<reason>)" |
| `vendors[].employees` | Profile line: "N employees" | Part omitted |
| `vendors[].revenue_source` | Profile line: "revenue <text> (as printed)" | Part omitted |
| `vendors[].headquarters` | Profile line, verbatim | Part omitted |
| `vendors[].founded` | Profile line: "founded <value>" | Part omitted |
| `vendors[].technologies_count` | Profile line: "N technologies listed" | Part omitted |
| `vendors[].technologies_more_source` | If it contains "+N" with N ≥ 2000: "[k technologies shown, ]2,000+ more (source display limit)" (`s14:176-181`) | `technologies_count` used |
| `identity.organisation_name` | `{org}` in the summary, banner, tiles, card, chips, D.6 text | "this organisation" (shared `page.org_name`) |
| `identity.domain` | Self-reference test only | — |
| `rating.grade` | Tile "Grade of {org} (for reference)" | "Not available" + "Not in the report data." |

Profile line (register and T1 table only; parts joined with " · "; null records are dropped, `s14:163-184`):
`<employees> employees · revenue <revenue_source> (as printed) · <headquarters> · founded <founded> · <n> technologies listed`.

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes |
|---|---|---|
| "Ratings are as shown on the report date. How each organisation is connected to {org} and the date of each organisation's own assessment are not reported." | Note at the top of the body (any state with vendors) | `BANNER`, `banner`. If **every** vendor has `assessed_at`: "…connected to {org} is not reported." |
| "No connected organisations reported for {org}." | Verdict for an empty list when the payload has no `summary` | `verdict` |
| "No connected organisations identified" | Card title (`none_identified`) | `card` |
| "None were found with the methods used. This does not show that {org} has no suppliers." | Card reason (`none_identified`) when the payload sends no reason of its own | `card` |
| "Connected organisations reported" | Tile 1 label. Also the relabel of metric `id: fourth_parties`. | `s14:117,221` |
| "organisations" / "organisation" | Tile 1 unit | `UNIT`, `s14:31` |
| "rated" / "{n} not rated" | Tile 2 unit / label | `s14:222` |
| "Lowest grade reported" | Tile 3 label. Unit "{k} organisations". | `s14:226`. No rated vendor: "Not available" + "No organisation is rated." |
| "Grade of {org} (for reference)" | Tile 4 label | `s14:230-231`. Reason when missing: "Not in the report data." |
| "Rated organisations by grade ({n})" + "; {m} not rated, not shown in the bar" | Grade-bar caption | `s14:272-273` |
| Grade letters + counts | Under the bar segments | Grade colours only, no band legend |
| "Needs a look ({n} of {N})" | H3 | `s14:359` |
| "Lowest grades (cut where the risk band changes; never the Low band) and organisations without a rating; worst grade first." | Caption under that H3 | `s14:360-361` |
| "Organisation", "Sector", "Grade", "Why listed", "Assessed on" | Needs-a-look column heads | `s14:313` |
| "Lowest grades", "Not rated", "Same name as {org}" | Hollow grey "Why listed" chips | `s14:301-307` |
| "All connected organisations ({N})" | H3 (T1) | `s14:367` |
| "Organisation", "Sector", "Grade", "Risk band", "Assessed on" | T1 table / D.6.1 heads | `s14:320-322` |
| "Not sent" | Risk band of an unrated vendor when no band was sent | `band_text`. A band that was sent prints as sent. |
| "Not rated", "Not rated (<reason>)" | Grade cell | `s14:65-71` |
| "Grade not available" | — | Not reachable here (the grade is checked before the chip is built) |
| "Name not recorded" | Organisation cell | `s14:192` |
| "Not an assessed member (as reported)" | Muted line in the Organisation cell | `s14:200-201` |
| "Same name as {org}" | Muted line in the Organisation cell (T1 / D.6.1) | `s14:202-203` |
| "employees", "revenue … (as printed)", "founded", "technologies listed", "technologies shown, ", "2,000+ more (source display limit)" | Profile line | `s14:168-183` |
| "A detected relationship is not evidence of a contract." | Note at the end | `NOTE_CONTRACT`, `s14:32` |
| "Some names may refer to the same organisation ({a and b; …}). They are not merged: each is listed and counted with its own rating." | Same note | Only when alias groups are found (`s14:337-340`) |
| "**Supply-chain aggregation**  How fourth-party ratings feed combined supply-chain risk  ·  Appendix C, page N" | Pointer (linked), only when Appendix C has its supply-chain page | `pointer`. Before the page is resolved: "Appendix C, page reference pending". |
| "**Full register**  D.6.1 Connected organisations  ·  N organisations  ·  Appendix D, pages a–b" | T2/T3 pointer | `RegisterPointer` prints the unit sent with the count (default "rows") |

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| Payload state not in `findings`/`clear`/`partial`/`none_identified` | `adjust()` changes nothing | `adjust` |
| `vendors[]` empty, state `findings`/`clear`/`partial` | State `none_identified` (reason code `none_identified` unless the payload sent one). Card + C pointer only. | `adjust`, `build` |
| `vendors[]` non-empty, state `clear`/`none_identified` | State `findings` → "Identified" | `adjust` |
| `vendors[]` non-empty, state `findings` / `partial` | Unchanged ("Identified" / "Partial coverage" + payload card) | `adjust` |
| No payload `summary` | Generated summary as the verdict | `verdict` |
| Every vendor has a non-null `assessed_at` | Data-limits note drops the date clause ("is not reported"). Otherwise the "…and the date of each organisation's own assessment are not reported" form prints. | `banner` |
| Any vendor has `assessed_at` | "Assessed on" column added (Needs a look, T1, D.6.1) | `s14:101-102,313,321-322` |
| ≥ 1 rated vendor | Summary adds "The lowest grade is X (k organisations)." Tile 3 shows the grade. The grade bar prints. | `s14:136-139,223-228,268` |
| Some vendors are unrated | Grade-bar caption adds "; n not rated, not shown in the bar" | `s14:273` |
| A vendor `is_self`: name equals `identity.organisation_name` (case-insensitive), **or** its domain (without `www.`) equals `identity.domain` or is a subdomain of it (example.com ≠ example.org) | Summary sentence, a "Same name as {org}" line and a "Why listed" chip. The vendor is still counted. | `is_self` |
| Domains of 2+ vendors fall in one alias set: {amazon.com, aws.com, aws.amazon.com}, {facebook.com, fb.com}, {google.com, gmail.com} | Alias sentence in the note | `s14:36,91-93` |
| Grade not in AAA–D | Unrated: "Not rated" chip-less cell. Sorted last. Band as sent, else "Not sent". | `grade`, `band_text`, `order` |
| Not rated + a reason text, or a `reason_code` outside the no-reason set | "Not rated (<reason text>)" | `not_rated` |
| `risk_band_label_source` is "—" / "-" / empty and `risk_band` is missing | Band cell = the `risk_band` null record ("Not available (<reason>)") | `s14:61-62` |
| `assessed_membership is False` (`null` does not trigger) | "Not an assessed member (as reported)" | `s14:200` |
| Dense cell and name + domain fit on one line | "Name  domain" on one line; otherwise stacked | `s14:193-198` |
| `technologies_more_source` "+N" with N ≥ 2000 | "[k technologies shown, ]2,000+ more (source display limit)". k = `len(technologies_sample_source)`. | `s14:176-181` |
| Needs a look: which rated vendors | Exclude the Low band (`risk_band == "low"`). With no band, exclude grades A or better. Group the rest (worst first) by band, or by grade when there is no band. Add whole groups while the total ≤ `top_n`. The first group is always taken. If it alone is > `top_n`, regroup it by grade with the same rule. | `s14:279-300` |
| Needs a look: other rows | Then **all** unrated vendors ("Not rated"), then self-references (a chip is added to an existing row, or a new row is created) | `s14:301-307` |
| `top_n` | `pol('lists.fourth_party_vendors.top_n', 10)` | `s14:346` |
| Tier T1: N ≤ `lists.fourth_party_vendors.tier_thresholds.T1_max_visual_rows`, else `tiers.T1_inline.max_visual_rows` (30) | "All connected organisations" table inline. The D.6 index row reads "Not required — all N … shown in Section 14." | `tier`, `app_d.tier(list_key=…)` |
| Tier T2 (and T3, N > `lists.fourth_party_vendors.tier_thresholds.T2_max_rows`, else `tiers.T2_overview_register.max_rows` 1000) | Register pointer. The full list goes in D.6.1. T3 renders as T2 and raises QA `max_tier_exceeded` (policy `max_tier_T2_overflow`); the policy's T3 data file / capped sample is not built (owner decision pending). | `build`, `app_d.tier` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| N reported | `len(vendors)` (each listed name counts once; names are never merged) | `s14:132,221` |
| Rated / not rated | Rated = vendors whose grade is in AAA–D. Not rated = N − rated. | `s14:133-135,222` |
| Lowest grade + k | Worst grade among rated vendors + its count | `s14:137-138,224-225` |
| Sort order | Rated first, worst grade → best, then name (case-insensitive). Unrated last. | `order`, `s14:74-76` |
| Grade-bar segments | Count per grade D…AAA. Width = 24 pt floor + share of the remaining width. | `s14:248-263,270` |
| Needs-a-look rows | See the Conditional rules | `s14:279-308` |
| Summary sentence | "{N} connected organisations reported for {org}: {r} rated, {u} not rated.[ The lowest grade is X (k organisations).][ n of them carries/carry the name of {org} itself (hosts) and is/are counted.]" | `s14:130-145` |
| Tier | `tier(N, N, list_key='fourth_party_vendors')` from the Appendix D policy | `tier` |

## Read but never printed

| Field | Why it is read |
|---|---|
| `metrics[]` | `adjust()` strips each metric's `state` and relabels `fourth_parties` to "Connected organisations reported" (`s14:116-118`). The section never prints `metrics`. |
| `vendors[].risk_band` (when `risk_band_label_source` is set) | Needs-a-look Low-band exclusion and grouping |
| `vendors[].technologies_sample_source` | Only its length (k technologies shown) |
| `identity.domain` | Self-reference test |
| Not read at all | `vendors[].vendor_id`, `evidence`, `description_source`, `state_label_source`, `lead_source`, `empty_state_source.title/.text` |

The Section 01 "All aspects" line also reads `vendors[]` (count + "n need(s) a look", using `needs_a_look`,
`s01_executive_overview.py:398-404`).

## States

| Payload state | Chip shown | Body |
|---|---|---|
| `findings` / `clear` / `none_identified` + vendors | Identified | Note + full body |
| `partial` + vendors | Partial coverage | Card (payload reason) + note + full body |
| `findings` / `clear` / `partial` / `none_identified` + no vendors | None identified | Card "No connected organisations identified" + C pointer |
| `pending_review` | Pending review | Card (payload reason) + full body (an empty list prints only the C pointer) |
| `not_assessed` / `not_applicable` / `unavailable` | Not assessed / Not applicable / Unavailable | Card (payload reason) + C pointer |

## QA checks raised

| check id | severity | when |
|---|---|---|
| `state_adjusted` | info | `adjust()` changed the state (`hold`, `__init__.py:171-178`), once per section |
| `max_tier_exceeded` | warn | More vendors than the T2 maximum (policy `max_tier_T2_overflow`); rendered as T2 |
| `unresolved_reference` | warn | Appendix C (Supply-chain pointer, when the payload has the page) or the D.6 register (T2 pointer) is not in the build, e.g. `--only s14` |
| `min_width`, `word_split` | warn / error | A long name or token in a narrow column (shared) |
| `table_header_not_repeated` | error | Shared split-table check |

## Backend checklist

- Send `vendors[]` as the flat list with state `findings` ("Identified"). Send `partial` only when the list
  itself is incomplete. Your `summary` / `state_reason` print verbatim; without a `summary` the generator writes one.
- `grade`: one of AAA, AA, A, BBB, BB, B, CCC, CC, C, D. Anything else prints as unrated. For an unrated
  vendor with a real reason, send `grade: null` + `grade_reason_code` (not `dash_in_source` etc.).
- Send `risk_band` (code `low` / `medium` / …) **and** `risk_band_label_source` (display text, printed exactly
  as sent). The Low band decides who is left out of "Needs a look".
- Send `assessed_at` on every vendor. If even one has it, the column appears. If all have it, the banner is shorter.
- Send `category` (sector). Missing prints "Unknown".
- Send `identity.organisation_name` / `identity.domain`. Vendors with that name, that domain or a subdomain of it are flagged as "Same name as …".
- Send `rating.grade` for the reference tile.
- Send `appendices.c_methodology.supply_chain` to get the Appendix C "Supply-chain aggregation" pointer.
- Above 30 vendors, D.6 prints whether or not `appendices.d_evidence_registers` is sent (see D file).
