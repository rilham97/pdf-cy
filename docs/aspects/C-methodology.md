# C Methodology and supply-chain aggregation

Payload key: `appendices.c_methodology` · Module: [app_c_methodology.py](../../cyberrank_report/sections/app_c_methodology.py) (+ `locked_page`, [page.py](../../cyberrank_report/page.py)) · Shared rules: [README](README.md)

Reference appendix with no chip (`REFERENCE`). Page 1 is the redesigned "Methodology in brief", built from
the payload `*_source` copy. Page 2 is the production "Supply-chain aggregation" page, inserted **unchanged**
from an external PDF (a locked page). Its contents never come from the payload.

## Layout (top to bottom)

1. Eyebrow "C · APPENDICES AND REFERENCES", then the H1 `title` or "Methodology and supply-chain aggregation", then `intro_source`.
2. Verdict row only if `summary` is sent (no chip).
3. `headline_source` (H2 style, no outline entry), then `lead_source` (intro style).
4. Columns grid: one column per `columns_source[]` item (title + text), with a rule above each.
5. "How a rating becomes a risk   {n} steps, one pipeline" (n = number of steps, in words up to ten) + a steps grid. Each step has a navy numbered badge, a title, text and a signals line, with an optional callout row underneath.
6. "The IISRI rating scale   {scale_caption_source}" + a 10-segment bar D → AAA, the letters and marks below, and the end labels.
7. Note: generic-material sentence + `copyright_source`.
8. The locked supply-chain page (new page). If its source file is missing, an "Unavailable" card prints instead.

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `title` | H1 + Contents entry | "Methodology and supply-chain aggregation" |
| `intro_source` | Intro under H1 | Omitted |
| `summary` | Verdict (no chip) | Omitted |
| `headline_source` | H2-style line | Omitted |
| `lead_source` | Intro-style paragraph | Omitted |
| `columns_source[] {title, text}` | Equal columns (non-dicts skipped) | Grid omitted. A missing title/text prints empty. |
| `steps_source[] {n, title, text, signals[], callout}` | Badge `n`, title, text, signals joined "  ·  " (no-break inside a signal), callout box (second grid row) | Whole pipeline block omitted (sub-heading too). A missing part is skipped. |
| `scale_caption_source` | Muted tail after "The IISRI rating scale" | No tail |
| `scale_ends_source.bottom` / `.top` | Left / right labels under the bar | Empty |
| `is_generic_material` (true) | Adds the generic-material note sentence | Sentence omitted |
| `copyright_source` | Appended to the note | Omitted |
| `supply_chain` (any truthy value) | **Only a switch:** inserts the locked page | No locked page |
| `identity.organisation_name` (via `page.org_name`) | `{org}` in the note | "this organisation" (the shared inline fallback; the cover and header say "Organisation name not available") |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes |
|---|---|---|
| "How a rating becomes a risk" + "{n} steps, one pipeline" | Steps sub-heading + muted tail | `PIPELINE_TITLE`; n = `len(steps_source)` in words (one … ten, digits above), "step" when 1. |
| "The IISRI rating scale" | Scale sub-heading | `app_c:17`. Always printed, even with no payload copy. |
| D, C, CC, CCC, B, BB, BBB, A, AA, AAA + marks (Very poor … Excellent) | Under the scale segments | `theme.GRADE_BAR` / `GRADE_MARK`, `app_c:106-109` |
| "General methodology, the same in every report; figures on the supply-chain page are illustrative and are not results for {org}." | Note | Only when `is_generic_material` (`app_c:173-174`) |
| "Supply-chain aggregation page missing" | Card title | `locked_source()` failed (`_supply_chain_page`) |
| "The supply-chain aggregation page could not be inserted: its source page was not available when this report was built." | Card reason | Same (missing file, bad index or unreadable file) |
| "Supply-chain aggregation" | PDF outline entry, nested under Appendix C | `app_c:138-141` |
| Locked page content (incl. its own "2 / 2" folio) | Inserted page | Taken 1:1 from the source PDF. No header, footer, watermark, motif or kit folio. |

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| `headline_source` / `lead_source` / `columns_source` / `steps_source` empty | That block is omitted | `app_c:157-171` |
| Any step has a `callout` | Second grid row with the callouts aligned (empty cells for steps without one) | `app_c:99-100` |
| `is_generic_material` truthy | Generic-material sentence | `app_c:173-174` |
| Note list empty | No note | `app_c:176-177` |
| `supply_chain` falsy | No locked page. Appendix D still starts on a new page (it has `new_page` like every section; after the locked page its `PageBreakIfNotEmpty` adds no blank page). Section 14 prints no "Supply-chain aggregation" pointer. | `_supply_chain_page`, `supply_chain_present` |
| `supply_chain` truthy and the source file exists | `NextPageTemplate('locked')` + page break + anchor + a reserved blank page. After the build, that page is stamped with page `INDEX` of the source PDF (vector, 1:1, mediabox = source page size; URI links copied). | `app_c:137-142`, `page.py:377-384,513-531` |
| `supply_chain` truthy and the file is missing, unreadable, or `CYBERRANK_SUPPLY_CHAIN_INDEX` is not a whole number / outside the file | QA `locked_page_missing` (**error → exit 2**, detail names the cause) + "Unavailable" card; no section 14 pointer | `locked_source`, `_supply_chain_page` |
| `c_methodology` missing | "Unavailable" card "Section missing from the report data." | `__init__.py:182-184` |
| `c_methodology.state` in no-result states | Card replaces the body (no locked page) | `__init__.py:205-209` |

Environment (read once at import, parsed when the page is built):

| Variable | Meaning | Default |
|---|---|---|
| `CYBERRANK_SUPPLY_CHAIN_PDF` | Path to the source production PDF | A report PDF in the reference pack (`_PACK/02_PDF_Assessment_Valid/…`). It is not shipped in the repo. |
| `CYBERRANK_SUPPLY_CHAIN_INDEX` | 0-based page index in that PDF | `44` (page 45). A non-integer or out-of-range value fails softly: QA `locked_page_missing`. |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Column / step widths | (content width − gutters) / n | `app_c:53-54` |
| Locked page number | Counted in "Page x of y" and the Contents. The page is skipped by the folio and layout QA. | `page.py:475-477`, `build.py:193` |

## Read but never printed

| Field | Why it is read |
|---|---|
| `supply_chain` | Truthiness only. None of its fields (`headline_source`, `text_source`, `illustrative_values`, `formula*`, `variables[]`, `impact_tiers[]`, `reliance_points[]`, `closing_source`, `dashboard_note_source`) are printed. The page is the static production PDF. |
| Not read at all | `note`, `letter`, `source_pages[]` |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| none / any result state | — (no chip) | Full body + locked page |
| `not_assessed` / `not_applicable` / `unavailable` | Not assessed / Not applicable / Unavailable | Card only |

## QA checks raised

| check id | severity | when |
|---|---|---|
| `locked_page_missing` | error | `supply_chain` is set but the page cannot be inserted: `CYBERRANK_SUPPLY_CHAIN_PDF` is not a readable file, or `CYBERRANK_SUPPLY_CHAIN_INDEX` is not a whole number inside it (`locked_source`) |
| `folio`, `page_size`, layout checks | — | **Skipped** on the locked page (`qa.py:111,118`) |
| `unresolved_reference` | warn | Section 14's Appendix C pointer when C is not built |

## Backend checklist

- Send the `*_source` copy. The generator never writes methodology prose, apart from the two sub-headings and the note.
- Send `supply_chain` as a non-empty object (any content). It only switches the locked page on.
- Deploy the production PDF and set `CYBERRANK_SUPPLY_CHAIN_PDF` (+ `CYBERRANK_SUPPLY_CHAIN_INDEX`). Otherwise the build exits 2.
- Send `is_generic_material: true` so the "illustrative, not your results" note prints.
- Any number of `steps_source` items works: the tail counts them.
