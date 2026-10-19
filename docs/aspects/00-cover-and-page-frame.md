# 00 Cover and page frame

Payload keys: `identity`, `snapshot` · Module: [page.py](../../cyberrank_report/page.py) (+ Contents in [build.py](../../cyberrank_report/build.py)) · Shared rules: [README](README.md)

These elements are drawn on the canvas, not in the flowing story: the cover (page 1), the running header and
footer on every interior page, the watermark and the motif. Locked pages (Appendix C) get none of them. Every
payload value goes through `identity_from_report` (`page.py:41-55`), which is also `ctx.identity` for the
sections.

## Layout (top to bottom)

**Cover** (`draw_cover`, `page.py:277-318`):
1. Cyberrank logo (top left).
2. Navy band: amber bar, "Cyber Risk" / "Report" (Inter 54), "Assessment date" + date, "Generated date" + date.
3. "REPORT FOR": optional customer logo (30 × 30), the organisation name (Inter, 28 → 24 → 20 → 17 pt until it fits in ≤ 2 lines), the domain (light mono).
4. "ISSUED BY": the issuer name (Inter 24) + "Assessment organization / via Cyberrank". Without an issuer: "Not available" + a reason sentence.
5. Cover motif (network dots, its hub under the name) + footer band with contacts, **no folio**.

**Contents page** (`build.py:161-172`): H1 "Contents", sub line "{org} / {domain} / Assessment {date}",
then group rows (Overview and priorities · Assessment details · Appendices and references) and entries
(number · title · page).

**Interior page** (`ReportDoc._on_interior`, `page.py:448-452`), drawn under the text in this order: bottom
motif, "CYBERRANK" outline watermark (vertical, left edge), header, footer.
- Header (`draw_header`, `page.py:231-250`): logo · "Cyber Risk Report for {org}" (Inter Medium 10, truncated with "…") with the domain under it · right side "Assessment  {date}" / "Generated  {date}" · sapphire/amber rule.
- Footer (`draw_footer`, `page.py:253-273`): pale band · contacts "cyberrank.ai", "support@cyberrank.ai", "LinkedIn" (icons + links) · "Page {n} of {total}" on the right.

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `identity.organisation_name` | Cover name (never truncated, the size steps down). Header "Cyber Risk Report for {org}" (ellipsised to fit). Contents sub line. PDF title/subject. `ctx.identity['org']`. | "Organisation name not available" (`page.py:47`) |
| `identity.domain` (string) | Cover under the name (mono). Header line 2 (the font shrinks 0.1 pt at a time until it fits; never truncated). Contents sub line. PDF title "(domain)". | Omitted everywhere |
| `identity.report_title` | **PDF metadata title only** ("{title} — {org} ({domain})") | "Cyber Risk Report" |
| `identity.issuer.organisation_name` | Cover "ISSUED BY" name | "Not available" + reason |
| `identity.issuer.reason` / `state_reason` / `reason_code` | Cover reason sentence when the name is missing (`page.py:53,313-315`) | "Reason not recorded." |
| `identity.logo.value` (file path) | Cover customer logo (30 × 30, aspect kept). The name shifts right by 43 pt. | No logo (a missing file is skipped silently) |
| `snapshot.assessed_at` (Date) | Cover "Assessment date". Header "Assessment  {date}". Contents "Assessment {date}". PDF subject. `ctx.identity['assessment_date']` (used by 15). | "Not available" / "Not available (<reason>)" |
| `snapshot.generated_at` (Date) | Cover "Generated date". Header "Generated  {date}". | Same |

Dates print as `DD Mon YYYY`. Minute precision gives "DD Mon YYYY HH:MM" as recorded; no time-zone
conversion (`text.fmt_date`).

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes |
|---|---|---|
| "Cyber Risk" / "Report" | Cover title | `page.py:282-283`. **Not** taken from `report_title`. |
| "Assessment date", "Generated date" | Cover labels | `page.py:284-287` |
| "REPORT FOR", "ISSUED BY" | Cover labels | `page.py:289,307` |
| "Assessment organization" / "via Cyberrank" | Under the issuer name | `page.py:310` (US spelling "organization") |
| "Not available" | Cover issuer when missing | `page.py:313` |
| "reason not recorded" | Issuer reason fallback | `page.py:314` |
| "Organisation name not available" | Org fallback (cover, header, Contents, other modules) | `page.py:47` |
| "Cyber Risk Report for " | Header title prefix | `HEADER_PREFIX`, `page.py:35`. Independent of `report_title`. |
| "Assessment  " / "Generated  " | Header right (two spaces) | `page.py:233` |
| "…" | Header org ellipsis | `ellipsize`, `page.py:86-105` |
| "cyberrank.ai", "support@cyberrank.ai", "LinkedIn" | Footer contacts + links | `CONTACTS`, `page.py:29-33` |
| "Page {n} of {total}" | Footer folio (interior pages) | `page.py:272-273` |
| "CYBERRANK" | Outline watermark (vector paths, not in the text layer) | `page.py:195-208` |
| "Contents" | Contents H1 | `build.py:171` |
| "Assessment {date}" | Contents sub line, joined with " / " | `build.py:169-170` |
| "Overview and priorities", "Assessment details", "Appendices and references" | Contents group rows; also the upper-case eyebrows | `GROUPS`, `__init__.py:26-30` |
| "Scope and coverage / rating overview / sector comparison" | Contents sub line under 01 | `__init__.py:56` |
| "[p.]" | Contents page cell before the anchors resolve | `components.py` `Contents` |
| "Cover" | PDF outline entry | `page.py:419` |
| "Cyberrank" (author), "Cyberrank report generator (ReportLab)" (creator), "External cyber risk assessment of {org}, {date}" (subject), lang "en" | PDF metadata | `page.py:433-436` |

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| `issuer.organisation_name` set | Name + "Assessment organization via Cyberrank" | `page.py:308-311` |
| Issuer name missing | "Not available" + `sentence(issuer reason or "reason not recorded")` | `page.py:312-316` |
| `logo.value` is an existing file (relative to the **working directory**) | Logo drawn, name box narrower | `page.py:45,54,291-294` |
| Org name > 2 lines at 28 pt | Try 24, then 20, then 17 pt | `page.py:296-299` |
| The name or issuer still overflows its fixed box | QA `layout_error`, then shrink-to-fit | `_box`, `page.py:321-331` |
| Header org too wide | Truncated at the longest prefix + "…" (word boundary if ≥ 60% kept) | `page.py:86-105,236-237` |
| Header domain too wide | Font size reduced in 0.1 pt steps (no minimum) | `page.py:238-242` |
| Domain empty | No domain line (cover, header); left out of the Contents / PDF title | `page.py:240,300-302,433` |
| Cover page | No folio, no header | `page.py:318` |
| Locked page (Appendix C) | No motif, watermark, header, footer or folio. Its own "2 / 2" stays. | `page.py:442` |
| Section `title` in the payload | Used for its Contents entry, else the registry title | `build.py:167` |
| Contents page not yet resolved | "[p.]", no link | `components.py` `Contents._table` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Total pages | multiBuild until page count + anchors are stable (`_PassState`) | `page.py:335-361,495-510` |
| Header title width | Space left of the date block − 10 pt | `page.py:233-236` |
| Cover hub position | Centre of the printed name | `page.py:304` |

## Read but never printed

| Field | Why it is read |
|---|---|
| `identity.report_title` | PDF metadata only |
| `identity.logo` | Path check (the image is drawn, the path is not printed) |
| Not read here | `identity.sector`, `organisation_id`, `website_source_label`, `description_source`, `snapshot.timezone`, `methodology_version`, `assessment_id` (printed in Appendix A) |

## States

Not applicable. The page frame has no state. A missing `identity` / `snapshot` uses the fallbacks above.

## QA checks raised

| check id | severity | when |
|---|---|---|
| `layout_error` | error | The cover name or issuer overflows its fixed box (`page.py:326-327`) |
| `missing_glyph` | warn | A header or cover string has a character with no font. Canvas text gets no per-character fallback (`page.py:69`). |
| `folio` | error | An interior page lacks "Page n of total" (cover and locked pages skipped, `qa.py:111,122-124`) |
| `page_size` | error | A non-locked page is not A4 (`qa.py:118-119`) |
| `outside_frame` | error | Body text outside the content frame (header/footer excluded) |

## Backend checklist

- Send `identity.organisation_name` and `identity.domain` (plain strings). Every page header uses them.
- Send `snapshot.assessed_at` and `snapshot.generated_at` as ISO dates with `precision` when not `day`.
- Send `identity.issuer.organisation_name`, or a `reason_code` / `reason` on `issuer`.
- `identity.logo.value` must be a file path readable from the generator's **working directory**. The JSON folder is not used.
- `identity.report_title` does not change the printed title ("Cyber Risk Report" is fixed).
- Keep organisation names to 2 lines at 17 pt in a 283 pt box (240 pt with a logo). Longer names raise `layout_error` (exit 2).
