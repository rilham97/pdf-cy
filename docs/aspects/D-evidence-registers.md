# D Detailed evidence registers (frame + D.6)

Payload key: `appendices.d_evidence_registers` · Module: [app_d_evidence_registers.py](../../cyberrank_report/sections/app_d_evidence_registers.py) · Shared rules: [README](README.md)

This file covers the shared frame: the index, the register ids, the opening / table / closing pattern and
the policy file. It also covers **D.6** (fourth-party vendors). The other registers are documented with
their sections:

| Id | Register | File |
|---|---|---|
| D.1 (+ D.1.2) | Affected assets by finding (+ IP reputation, index row only) | [04-vulnerabilities.md](04-vulnerabilities.md) |
| D.2 (D.2.1–D.2.5) | Credential exposure — supporting tables | [05-credential-exposure.md](05-credential-exposure.md) |
| D.3 | Data leak event details (always an index row only) | [06-data-leak-history.md](06-data-leak-history.md) |
| D.4 (D.4.1–D.4.2) | Quantum scope breakdown | [11-quantum-security.md](11-quantum-security.md) |
| D.5 (D.5.n) | Uploaded certificate documents | [13-certifications.md](13-certifications.md) |
| D.6 (D.6.1) | Fourth-party vendors and technologies | this file + [14-fourth-party-vendors.md](14-fourth-party-vendors.md) |

**Not a reference appendix:** `appD` is not in `REFERENCE` (`__init__.py:33`). It shows a state chip from
`d_evidence_registers.state`; a no-result state adds a card, and the index and registers still follow (they
are built from the section data; only the frame text — title, intro, chip, summary, card — reads the appendix
payload). Like every section it starts on a new page (`new_page`); after Appendix C's locked page, which ends
with a page break, its `PageBreakIfNotEmpty` adds no blank page.

## Layout (top to bottom)

1. Eyebrow "D · APPENDICES AND REFERENCES", then the H1 `title` or "Detailed evidence registers" (no icon), then `intro_source`.
2. Chip (from the appendix's own `state`) + `summary`.
3. Body line: policy `naming.appendix_d.note` (`app_d:651-652`).
4. H3 "Register index" + an index table with columns D.n · Register · State · Content · Location (`app_d:619-632`).
5. Note: "Registers that are not required appear here only. Page references link to the register."
6. Each **printed** register in id order. Every register follows this pattern:
   - **Opening:** H2 "D.n  Title" (outline entry, anchor `reg-D.n`, optional severity legend on the heading line). A lead sentence (body). Further lines in note style, usually "Unit: … State: … Snapshot {date}." A backlink "Back to Section NN Title, p. N" (`opening`, `app_d:301-313`).
   - **Table:** dense; header row repeats. A page continuation opens with the caption "D.n.m Title · continued / Rows a–b of N". When a plain-text column holds one value in every row, it is removed and printed above the table as "Col: value (all rows)." (`app_d:184-190,207-220,287-289`).
   - **Closing:** "End of register · N {unit}. " followed by the reconciliation text (`closing`, `app_d:316-323`).

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `d_evidence_registers.title` | H1 + Contents entry | "Detailed evidence registers" |
| `d_evidence_registers.intro_source` | Intro | Omitted |
| `d_evidence_registers.state` | Chip / card for the **whole appendix** | No chip (the verdict, if any, runs full width) |
| `d_evidence_registers.summary` | Verdict | Omitted |
| `d_evidence_registers.state_reason` / `reason_code` / `what_checked` / `next_step` | Appendix card (card states) | Fallbacks per README |
| `d_evidence_registers.<register>` (`credential_register`, `quantum_scope_register`, `vulnerability_asset_register`, `pqc_domain_register`) | Per register, via `sections.*.*_ref` | See the section files |
| `sections.<key>.state` | Index "State" chip (`shown_state` with the section key) | "State not recorded" chip |
| `snapshot.assessed_at` | "Snapshot {date}" in each opening | "Not available" |
| **D.6:** `sections.fourth_party_vendors.vendors[]` | D.6.1 rows (same cells as the Section 14 T1 table, see the 14 file) | Index row only |
| **D.6:** `identity.organisation_name` | `{org}` in the D.6 lead | "this organisation" (`page.org_name`) |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes |
|---|---|---|
| "Evidence registers support findings; layout and row caps do not change any score." | Body line | Default for `pol('naming.appendix_d.note')` |
| "Register index" | H3 | `app_d:653` |
| "D.n", "Register", "State", "Content", "Location" | Index heads | `app_d:630` |
| "Registers that are not required appear here only. Page references link to the register." | Note under the index | `app_d:654` |
| "p. a" / "pp. a–b" (linked) | Location of a printed register | `pages_link`, `app_d:162-167`. Before it resolves: "page reference pending". |
| "Section NN, p. N" (linked) | Location of an index-only register | `page_link`, `app_d:154-159`. Before it resolves: "Section NN". |
| "Not available (not provided in the assessment data)" | Index Content when empty | `app_d:628` |
| "Back to Section NN {title}, p. N" | Under each opening | `backlink`. The section's payload `title`, else the registry title (`TITLES`, filled by `build`). |
| "{Title} · continued" / "Rows a–b of N" | Continuation caption | `C.numbered` / `CompactTable` |
| "{Col}: {value} (all rows)." | Constant-column note | `app_d:208,289` |
| "End of register · N {unit}. " | Closing prefix | `app_d:318` |
| Index Content for registers that are not printed (`state_message`, `app_d:598-611`): | | |
| — `clear` | "Not required — no {unit} identified." | Policy `states.register_messages.clear` |
| — `not_assessed` | Policy: "Not produced — Section {nn} was not assessed." | Default "Not produced." |
| — `not_applicable` | Policy: "Not applicable: {reason}." | Default "Not produced." |
| — `unavailable` | Policy: "Not produced — data unavailable." | Default "Not produced." |
| — `none_identified` | "Not required — no {unit} identified." | Hardcoded |
| — count ≤ T1 limit (30; the list's own `tier_thresholds.T1_max_visual_rows` when given) | "Not required — all {count} {unit} shown in Section {nn}." | Hardcoded |
| — no count | "Not produced — no register data in the payload." | Hardcoded |
| — count > limit | "Not produced — no register data in the payload ({count} {unit} in Section {nn})." | Hardcoded |
| **D.6** "Fourth-party vendors and technologies" | Register title (H2 + index) | `pol('lists.fourth_party_vendors.register_title')`, `d6_vendors` |
| **D.6** "D.6.1 lists all {n} connected organisations reported for {org}, sorted by grade, worst first; organisations without a rating last. Showing {n} of {n} organisations." | Lead | `app_d:514-515` |
| **D.6** "Unit: organisations (each listed name counts once; names are not merged). Grade and risk band as sent; the band is not derived from the grade. State: {chip label}. Snapshot {date}." | Second line | `app_d:516-518` |
| **D.6** "D.6.1  Connected organisations" | H3 + table caption title | `app_d:520-523` |
| **D.6** "#", "Organisation", "Sector", "Grade", "Risk band", "Assessed on" | Table heads | `s14:385` |
| **D.6** "A detected relationship is not evidence of a contract." (+ alias sentence) | Note after the table | `s14.notes` |
| **D.6** "End of register · {n} rows. {n} of {n} organisations shown; 0 not shown. Totals: {rated} rated + {n−rated} not rated = {n} = Section 14 count." | Closing | `app_d:525-527` |
| **D.6** "{n} of {n} connected organisations" | Index Content when printed | `app_d:528` |

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| Register ids | `REG_SECS` (s04, s05, s06, s11, s13, s14) are numbered D.1… in `REGISTRY` order. An absent register keeps its slot. | `app_d:36-41` |
| Index order | Sorted numerically: D.1, D.1.2, D.2, … D.6 | `app_d:650` |
| D.1.2 IP reputation | Index row only (`_absent`) | `app_d:675-676` |
| D.3 data leak events | Index row only: "Not required — all N event(s) shown in Section 06" (events counted after the canonical merge) | `d3_leaks`, `app_d:631` |
| A register has a `flow` | Printed after the index. Location = page range. | `app_d:623,655-656` |
| A register has no `flow` | Index row only. Content = `state_message`. Location = the section (or the `s04-ip-reputation` anchor). | `app_d:614-616,624-625` |
| `d_evidence_registers` **missing** or `{}` | No chip, no card; index + registers as usual (H1 = registry title) | `render_section` (`appD` stub `{'state': None}`) |
| `d_evidence_registers.state` in `not_assessed`/`not_applicable`/`unavailable` | Card, then the index + registers (`build_context = build`) | `__init__.py` `render_section` |
| `d_evidence_registers.state` in `clear`/`partial`/`pending_review`/`none_identified` | Card above the index | `__init__.py:200-204` |
| **D.6 printed** only if vendors are non-empty **and** tier ≠ T1 (N > `lists.fourth_party_vendors.tier_thresholds.T1_max_visual_rows`, else the global 30) **and** `state` ∈ `findings`/`partial`/`pending_review` | Full D.6.1 register (table ident `regD61`) | `d6_vendors` |
| D.6 not printed | Index Content via `state_message(sec, '14', 'connected organisations', N, list_key='fourth_party_vendors')`. After `adjust`: empty list → `none_identified` → "Not required — no connected organisations identified."; N ≤ T1 → "Not required — all N connected organisations shown in Section 14." | `d6_vendors` |
| D.6 grade cell | Plain letter (no chip). Unrated: "Not rated[ (<reason>)]" (muted). | `s14:328,388` |
| D.6 sector missing | "Unknown" | `s14:327` |
| D.6 "Assessed on" | The column is present when any vendor has `assessed_at` | `s14:320-322` |

Policy file (optional, `app_d:29-34,61-76`): the path in `CYBERRANK_LONG_LIST_POLICY`, else
`../long-list-rules/long_list_policy.json`, else the built-in `_DEFAULTS`. The frame and D.6 read these keys:
`naming.appendix_d.note`, `lists.<list>.tier_thresholds.T1_max_visual_rows` / `.T2_max_rows` (per list, read first by
`tier(..., list_key=...)` / `t1_max`), else `tiers.T1_inline.max_visual_rows` (30), `tiers.T2_overview_register.max_rows` (1000),
`states.register_messages.*`, `lists.fourth_party_vendors.register_title`, `lists.fourth_party_vendors.top_n` (10).
Templates use `{key}` and `{key|'default'}` placeholders (`fill`, `app_d:86-91`).

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Register ids | Registry order of the sections that have registers | `app_d:38-41` |
| Page ranges | `reg:{rid}:start` / `:end` anchors resolved on the next multiBuild pass | `app_d:162-167,301-323` |
| D.6 rated / not rated | Vendors whose grade is in AAA–D | `app_d:522` |
| D.6 sort | Worst grade first, unrated last, then name | `s14.order` |
| Constant columns | Plain-string columns (not `#`, not numeric) holding one value in ≥ 2 rows | `app_d:184-190` |

## Read but never printed

| Field | Why it is read |
|---|---|
| `d_evidence_registers.*_register` | Read through the sections' `*_ref` paths (see the section files) |
| Not read by the frame | `d_evidence_registers.letter`, `source_pages[]` |

## States

| Payload state (`d_evidence_registers.state`) | Chip shown | Body |
|---|---|---|
| `findings` | **Identified** (blue). `d_evidence_registers` is in `theme.INVENTORY`. | Index + registers |
| `clear` / `partial` / `pending_review` / `none_identified` | No findings / Partial coverage / Pending review / None identified | Card + index + registers |
| `not_assessed` / `not_applicable` / `unavailable` | Not assessed / Not applicable / Unavailable | Card + index + registers |
| object missing / `{}` / absent `state` key | — (no chip) | Index + registers |

Index rows show each **section's** state through `shown_state`. For example, 13 `findings` → Identified, and
14 `findings` → Identified (an empty list → None identified after `adjust`).

## QA checks raised

| check id | severity | when |
|---|---|---|
| `unresolved_reference` | warn | A section pointer to a register (or the Appendix D anchor) did not resolve (`page.py:500-501`) |
| `table_header_not_repeated` | error | A split register lost its repeated header |
| `missing_glyph` | warn | A character in a plain-text register cell has no font (`app_d:241-242`) |
| `missing_document` | warn | D.5 only (see the 13 file) |
| `word_split`, `min_width` | warn / error | Shared |

## Backend checklist

- `appendices.d_evidence_registers` only sets the frame (title, intro, chip, summary). The registers are built from the sections whether it is sent or not.
- Leave `d_evidence_registers.state` out, or know that it prints a chip ("Identified" for `findings`) on the appendix opener.
- Register ids are fixed (D.1–D.6). Do not number registers in the payload.
- D.6 needs no payload register. It is built from `sections.fourth_party_vendors.vendors[]` when there are more than 30 vendors.
- Deploy the policy file only if you need different titles, messages or limits. The defaults match it.
