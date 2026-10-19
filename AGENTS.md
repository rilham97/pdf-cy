# AGENTS.md — Cyberrank report generator

Turns one assessment **payload** (JSON, sent by the Cyberrank backend) into the customer-facing
"Cyber Risk Report" PDF. The report reader is a non-technical customer; the product owner reviews every
visual change. How to install/run and the folder layout: [README.md](README.md). Every payload field:
[data/report-schema.md](data/report-schema.md).

## Pipeline

`build.validate` (contract check at load) → `sections.adjust_report` (state adjustments, QA info
`state_adjusted`) → one module per section in `sections/` builds flowables → `ReportDoc.render`
(multiBuild: Page x of y, TOC, anchors, locked page stamping) → `qa.check_pdf` → `<out>.qa.json`.
Exit 1 = payload contract error, exit 2 = QA error.

## Truth rules (why the report never guesses)

The PDF is evidence shown to customers, so the generator **renders, never infers**:

- **Missing is not zero.** Every null carries a `reason_code`; it prints "Not available (reason)" or a
  state, never 0, "safe" or "valid". The one exception is product-defined: certifications with no
  records show 0% and state `none_identified`.
- **Quote source first.** Source wording, verdicts and headlines print verbatim; our interpretation follows
  as a Note. When counts disagree (headline 2 vs 3 records) print both and raise a QA warn.
- **System flags are rendered, not computed:** certificate `expired`, breach `resolved`/inaccurate,
  match states, scores. Dates are shown, never compared.
- **Never invent a score.** Only aspects with a system percent score show one.
- **Hidden scoring stays hidden.** Demerit ledger, points, caps, credits and certificate weighting
  (pending 1 / approved 2 / rejected 0) are read for QA only and never printed.
- **Exact source terms.** Quantum severity is High / Moderate / Low; vulnerability severity is
  Critical / High / Medium / Low. Full words, no ad-hoc abbreviations.
- **Privacy:** account labels arrive masked from the system and print as received; QA warns
  `unmasked_account_label`. Every '@' address in a PDF except support@cyberrank.ai contains '*'.
  Demo data uses only example.com/.net/.org and documentation IPs (192.0.2/24, 198.51.100/24, 203.0.113/24).

## Design invariants (owner decisions — keep them true in every PDF)

Each was asked for or approved by the product owner; changing one needs their approval.

- Engine: ReportLab Platypus, Word-like flowing story, no HTML/CSS. Page x of y via a PageCount
  IndexingFlowable + multiBuild; a NumberedCanvas would break bookmarks and TOC links.
- Structure is fixed so every report reads the same: 01 Executive overview, 02 Priority actions,
  03 Privacy … 15 Cloud infrastructure (order = `sections.REGISTRY`), Appendices A–D. Every section starts
  on a new page. Appendix D register ids follow section order and never shift between reports
  (D.1 vulns, D.2 credentials, D.3 breach, D.4 quantum, D.5 uploaded certificate documents, D.6 fourth-party).
- Long lists: ≤30 rows inline, longer ones get an overview in the section and the full register in
  Appendix D (`../long-list-rules/long_list_policy.json` when present, built-in defaults otherwise).
  Split tables repeat the header under "<title> · continued / Rows a–b of N" and end with
  "End of register · N rows".
- Severity: four separate tiers, never merged, each with its own colour (Critical #9C3A24, High #DC2626,
  Medium #D97706, Low #1F9D55) and siren marker (5 / 3 / 2 / 0 rays). In tables severity is its own narrow,
  centre-aligned column right after # / ID, icon only (the label is invisible text), with a boxless legend
  strip on the heading line.
- Colour speaks but stays quiet: `theme.STATUS` / `status_color()` — green good, red genuine failure,
  orange attention, grey neutral, blue only for structure. Colour sits on small markers only; label text,
  rows and card backgrounds stay neutral.
- Motif (network dot field) sits at the page bottom **behind** text like a watermark, plus the
  CYBERRANK outline watermark. QA ignores the motif band.
- Appendix C's "Supply-chain aggregation" page is a production page inserted **unchanged** (no overlay,
  header, footer or mask; its own "2 / 2" folio stays). Its source PDF is not in the repo:
  `CYBERRANK_SUPPLY_CHAIN_PDF` / `CYBERRANK_SUPPLY_CHAIN_INDEX`.
- Rating scales run worst (D) on the left to best (AAA) on the right. Methodology version prints as
  "Version n".
- Residency map (`geo_map.py`): mode C table only when ≤1 relevant country (IP country lookups can fail),
  A2 auto-zoom regional, A3 world map with ISO-code badges + insets. Unknown/placeholder countries go to an
  off-map counter, never guessed. Circle = in preference, square = outside, ring = preferred.
- Certificates: status "Approved" for every origin; detected + uploaded records of one standard grouped;
  uploaded documents (`certificates[].document`, path relative to the JSON, must stay inside its folder)
  print one per page in Appendix D.5; a detected certificate awaiting approval adds a "Next step" in
  section 13 and a low-priority action in section 02.
- Fonts: Poppins for all body text; Inter (`T.BRAND_*`) only for the document title — the cover and the running
  header title "Cyber Risk Report for …"; JetBrains Mono at 0.9× for technical tokens; Noto fallbacks for glyphs
  Poppins lacks.

## Gotchas

- Poppins has no zero-width space: inserting ZWSP for line breaks splits tokens mid-word; break technical
  strings with `text.tech_lines` / `components.breakable` instead.
- Poppler drops zero-length dashes with square caps: map squares use a 0.01 pt dash (`geo_map.SQUARE_DASH`).
- `KeepInFrame(0, 0, …, mode='shrink')` fits an image to the room left on the page.
- The payload is input from outside: never pass raw payload strings into markup (`M()`); escape them.

## Working on it

- Change behaviour in the shared function all callers route through, then run
  `.venv/bin/python -I tests/test_kit.py` (every test must print `ok`) and rebuild
  `data/demo-preview.json`. A change is done when tests pass, QA has 0 errors, and you have looked at the
  rendered pages as PNG (overlaps, mid-word header wraps, orphaned headings).
- Synthetic variants for every condition live in `tests/gap_fixtures.py`; add one for each new condition.
- Demo data is generated: edit `tools/extract/build_demo_fixture.py`, not the JSON.
