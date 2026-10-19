# 13 Certifications

Payload key: `sections.certifications` · Module: [s13_certifications.py](../../cyberrank_report/sections/s13_certifications.py) · Shared rules: [README](README.md)

This is an inventory section (`theme.INVENTORY`): payload state `findings` shows the chip "Identified". Uploaded certificate documents print in Appendix **D.5** (`RID['s13']`, `cert_documents` in [app_d_evidence_registers.py](../../cyberrank_report/sections/app_d_evidence_registers.py)). A detected certificate awaiting approval also adds a low-priority action to 02. File refs: `s13:` = `s13_certifications.py`, `appD:` = `app_d_evidence_registers.py`, `s02:` = `s02_priority_actions.py`.

## Layout (top to bottom)

1. Section opener: "13", title, state chip, `summary` as verdict, `intro_source`. The module has no `verdict()`.
2. State card. For `none_identified` the card title is "No certificates identified" (`s13:398-399`).
3. KPI strip from `metrics[]` (`s13:405-407`). Not printed in no-result states.
4. "Certificates on record" (H2) + table (`s13:289-348`). It prints when certificates exist, or when the state is not `clear` / `none_identified` (`s13:408-409`).
5. One combined note line (dropped columns, rejected, unconfirmed status, headline mismatch) (`s13:329-343`).
6. Source URL list: "Source" or "[1]", "[2]", … (`s13:344`).
7. "**Next step:** …" when a detected certificate is awaiting approval (`s13:345-347`).
8. "Commonly referenced standards" (H2): standards table with the note beside it (≤ 10 rows) or above it (`s13:351-377`).

No-result states show the opener, the card and block 8 only (`s13:413-415`).

Appendix D.5 "Uploaded certificate documents" (`appD:558-595`):

1. H2 "D.5  Uploaded certificate documents", two opening lines, "Back to Section 13 Certifications, p. n".
2. "Not shown: …" when any document failed to load.
3. Per document: H3 "D.5.i  <standard>", a meta line, then each page image on its own page, shrunk to fit.
4. End line "End of register · N documents. <shown> of <N> uploaded documents shown."

Section 02 gets one extra action row (`s02:187-196, 222`).

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `summary`, `intro_source`, `title` | Opener | No verdict / no intro / "Certifications" |
| `metrics[]` | KPI tiles in payload order. `compliance_score` (percent) is also the 01 aspect score (`s01_executive_overview.py:274`) | No certificates and no numeric `compliance_score`: a "Compliance score 0%" tile is added (`s13:390-395`) |
| `metrics[unit=certifications_headline].value` (int) | Compared with the number of records; prints a note when different (`s13:335-341`) | No check |
| `certificates[].standard` | "Standard" / "Certificate" cell. Also the grouping key (case and spaces ignored) | "Standard not recorded". The value `OTHER` prints "Other (standard not named)" and is never grouped (`s13:151-161`) |
| `certificates[].standard_full_name` | Scope line, first part | Omitted. If nothing else is in the scope cell: missing-value text |
| `certificates[].category` (`security` / `privacy` / `both` / `security_privacy` / `security_and_privacy`) | Scope line: "Security", "Privacy", "Security + Privacy". Other values are humanised (`s13:32-33, 274-276`) | Omitted |
| `certificates[].scope_source`, `.issuer` | Extra scope lines "Scope: …" and "Issuer: …" (`s13:278-279`) | Omitted |
| `certificates[].origin` (`detected` / `uploaded`; legacy `approved` / `team_approved` = detected) | "Origin" cell: "System detected" / "Uploaded" (`s13:29, 137-140, 194-210`) | Null record: "Not available (<reason>)". Unknown code: `origin_label_source` humanised, or the code itself |
| `certificates[].origin_label_source` | Origin text only when `origin` is not a known code | — |
| `certificates[].approval_state` (`pending` / `pending_approval` / `awaiting_approval` / `approved` / `rejected`) | "Status" cell: "Awaiting approval" / "Approved" / "Rejected" (`s13:213-225`) | Missing (and no legacy origin): "Not available (<reason>)" plus the unconfirmed-status note. Unknown value: "Not recognised (“x”)" plus QA `unknown_term` |
| `certificates[].valid_from`, `.valid_until` (ISO date or `{value, precision}`) | "Validity" cell, see rules (`s13:242-257`) | Uses the null reason. Both `not_detected`: "Not detected by the system" |
| `certificates[].expired` (bool or `{value}`) | "Expired" (red icon) above the dates (`s13:237-239, 254-257`) | Not expired. Expiry is never computed from the dates |
| `certificates[].source_url` | Source list ("Source" or numbered links) and "[n]" in the Origin cell (`s13:294-300`) | Detected record shows "[source not recorded]" when other records have URLs |
| `certificates[].file_reference` | Link line under "Uploaded" (`s13:201-204`). Also in the D.5 meta line | Omitted |
| `certificates[].document` (path relative to the JSON file: `.png` / `.jpg` / `.jpeg` / `.pdf`) | "Document in Appendix D.5" under "Uploaded". The file prints in D.5 (`s13:205-207`, `appD:535-555`) | No D.5 entry |
| `certificates[].certificate_id` | Grouping key only for an unnamed standard | Object identity |
| `reference_standards.items[] {standard, description}` | "Commonly referenced standards" table, columns "Standard", "Scope" | Missing-value cell. If there are no items, the block is omitted |
| `reference_standards.is_vendor_evidence` | Truthy: the "Reference list only …" sentence is not printed (`s13:361-362`) | Sentence printed |
| `identity.org` (display identity) | "It is not evidence that <org> holds them." | "the organisation" |
| `state`, `state_reason`, `reason_code`, `what_checked`, `empty_state_source`, `next_step` | State card (default card) | Shared fallbacks |
| `report._source_dir` (set by the loader) | Base folder for `document` paths | Current folder |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes (e.g. policy override key) |
|---|---|---|
| "Certificates on record" | H2 | `s13:292, 327` |
| "No certificate records in the assessment data." | Note when the table block runs with no records | `s13:292` |
| Columns "Standard", "Scope", "Origin", "Status", "Validity"; or "Certificate" (standard + scope stacked) | Certificate table | `s13:304, 318-322` |
| "Standard not recorded", "Other (standard not named)" | Standard cell | `s13:160-161` |
| "Security", "Privacy", "Security + Privacy" | Scope line | `s13:32-33` |
| "Scope: <x>", "Issuer: <x>" | Scope lines | `s13:278` |
| "System detected", "Uploaded" | Origin cell | `s13:29` |
| "Document in Appendix D.5" | Under "Uploaded" | `s13:207` |
| "[n]", "[source not recorded]" | Origin cell suffix | `s13:299-300` |
| "Approved" (same for every origin), "Awaiting approval", "Rejected", "Not recognised (“x”)" | Status cell. Never "verified" | `s13:219-225` |
| "<from> – <until>", "Until <until>", "From <from>; end date not available (<reason>)", "Not detected by the system" | Validity cell (dates as "01 Mar 2025") | `s13:246-253` |
| "Expired" | Validity cell, above the dates | `s13:256` |
| "<Columns>: not available for any certificate (<reason>)." (Scope column is named "scope and category") | Note | `s13:62-76, 286` |
| "Rejected certificates are listed for completeness." | Note | `s13:331` |
| "A listed certificate is a record of what was found, not a confirmation that it is valid or approved." | Note | `s13:333-334` |
| "The assessment headline counts <h> certifications; <n> certificate records are listed here." | Note | `s13:338-339` |
| "Source" / "[1]", "[2]" … + link | Source list (http/https URLs only are live links) | `s13:119-129, 100-116` |
| "**Next step:** <n> system-detected certificate(s) (<standards>) is/are awaiting approval. Check the source, then approve or reject it/each in Cyberrank." | After the source list | `s13:181-186, 347` |
| "standard not recorded" | Inside the Next-step list of names | `s13:182` |
| "Commonly referenced standards"; columns "Standard", "Scope" | H2 + table | `s13:365-367` |
| "Reference list only: standards commonly referenced for organisations of this kind. It is not evidence that <org> holds them." | Beside or above the table | `s13:361-362` |
| " <A and B> also appear(s) among the certificates on record." | Appended | `s13:363-364` |
| "No certificates identified" | Card title, `none_identified` | `s13:399` |
| "No certificate records were found in the sources checked." | Card reason when there is no `state_reason` | `s13:388-389` |
| "Compliance score", 0, percent | Injected KPI tile | `s13:393` |
| 02 row: title "Review system-detected certificates", priority low, Effort "Not available (not tracked by the assessment)", Team "Cyberrank admin", sub-line "Added by this report from the certificate records; not part of the assessment action list.", action text = Next-step text | Section 02 table + its Low-priority KPI | `s02:193-196` |
| D.5: "Uploaded certificate documents" | H2 | `appD:561` (not a policy key) |
| "D.5 shows the <n> certificate document(s) uploaded to Cyberrank, in the order of Section 13, one document per page." / "Shown as uploaded; dates and scope printed on a document are not read into the report data." | D.5 opening | `appD:567-570` |
| "Not shown: D.5.i <standard> (<why>); …." with why = "no file in the assessment data" / "file path not accepted" / "file not found" | D.5 | `appD:543-549, 572, 577` |
| "D.5.i  <standard>"; meta "Issuer: <x> · <file_reference>" | D.5 per document | `appD:581-585` |
| "End of register · <N> documents. <shown> of <N> uploaded documents shown." | D.5 end | `appD:593` |
| Index content: "<shown> of <N> uploaded certificate documents" / "Not required — no uploaded certificate documents in the assessment data." | Appendix D index | `appD:566, 594` |

The module has no policy-file overrides.

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| State is `findings` / `clear` / `partial` / `none_identified` and no certificate objects | State becomes `none_identified` (`no_certificate_records`). Metric `state` keys are stripped. A 0% "Compliance score" is prepended unless a numeric one is sent. QA `state_adjusted` | `s13:380-395` |
| Certificates present, or state not `clear` / `none_identified` | Certificate block | `s13:408-409` |
| Records of the same standard | Sorted together (first-seen order, detected before uploaded). The second row has a blank Standard and keeps only its own "Scope:" / "Issuer:" lines | `s13:164-172, 306-314` |
| Every record of a standard is rejected | That standard moves to the end | `s13:170-172` |
| Every record has the same `source_url` | One "Source" link row, no "[n]" | `s13:126-128, 296` |
| `source_url` values differ (absent counts as a value) | Numbered list; detected rows get "[n]" or "[source not recorded]"; uploaded rows without a URL get nothing | `s13:296-300` |
| No URL anywhere | No source list, no "[n]" | `s13:124-125` |
| Origin `uploaded` + `file_reference` | Link line | `s13:203-204` |
| Origin `uploaded` + `document` key not null | "Document in Appendix D.5" + D.5 entry | `s13:205-207`, `appD:563-564` |
| `approval_state` missing but origin is legacy `approved` / `team_approved` | Status "Approved" | `s13:146-147` |
| Unknown `approval_state` | "Not recognised (“x”)" + QA `unknown_term` | `s13:224-225` |
| Both dates missing, both `reason_code: not_detected` | "Not detected by the system" | `s13:245-247` |
| Both dates missing, other reasons | `valid_until` missing-value text | `s13:254-255` |
| Only `valid_until` missing | "From <from>; end date not available (<reason>)" | `s13:250-251` |
| Only `valid_from` missing | "Until <until>" | `s13:253` |
| `expired` is true | "Expired" + the date text (only "Expired" when both dates are missing for a reason other than `not_detected`) | `s13:254-257` |
| A column (except Standard, Origin) is missing in every row with one shared reason | Column dropped + "…: not available for any certificate (<reason>)." note | `s13:315-316` |
| Content width minus (Origin 92 + Status 140 + Validity 110 for the columns kept) < 300 pt | Scope stacked under the standard in a "Certificate" column. With all columns kept this always applies (CW ≈ 516 pt) | `s13:285, 317-322` |
| Else Scope kept | Scope lines joined " · " | `s13:323-325` |
| Any record rejected | "Rejected certificates are listed for completeness." | `s13:330-331` |
| Any record has a missing `approval_state` field | "A listed certificate is a record of what was found…" | `s13:332-334` |
| Headline metric (unit `certifications_headline`, int) ≠ number of records | Headline note + QA `data_mismatch` | `s13:335-341` |
| ≥ 1 record with origin detected and status pending | "Next step:" line in 13 **and** a low-priority action in 02 (rank = last + 1) | `s13:175-178, 345-347`, `s02:187-196` |
| Rejected record with `credit_applied` > 0 | QA `data_mismatch` only | `s13:265-270` |
| `reference_standards.items` empty | No reference block | `s13:353-355` |
| State is `findings` / `partial` / `pending_review` and a non-rejected certificate has the same standard as an item | "… also appear(s) among the certificates on record." | `s13:357-364` |
| More than 10 items, or `is_vendor_evidence` true with no overlap | Stacked: heading, text, full-width table | `s13:368-369` |
| Else | Half-width table with the note beside it, kept on one page | `s13:371-377` |
| No-result state | Card + reference block | `s13:413-415` |
| D.5: no uploaded record with `document` | Index row only | `appD:563-566` |
| D.5: path outside the JSON folder or not .png / .jpg / .jpeg / .pdf | "file path not accepted" + QA `missing_document` | `appD:544-547, 575` |
| D.5: PDF document | Every page rasterised at 150 dpi, one report page each | `appD:552-555` |
| D.5: last page of the last document | Shrunk to leave room for the end line | `appD:589-591` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Origin code | `origin` lower-cased; `approved` / `team_approved` → `detected` | `s13:137-140` |
| Approval code | `approval_state` lower-cased; pending aliases → `pending`; legacy origin → `approved` | `s13:143-148` |
| Standard group key | `standard` case-folded without spaces; `OTHER` or blank → per-record key | `s13:151-154` |
| Row order | Live standards first (first-seen), detected before uploaded | `s13:164-172` |
| Awaiting review | Records with origin detected and approval pending | `s13:175-178` |
| Source references | Distinct `source_url` values in row order → [1], [2]… | `s13:122-123` |
| 0% compliance score | Only when there are no records and no numeric `compliance_score` | `s13:392-394` |
| 01 "All aspects" result line | Distinct standards of non-rejected records ("<n> certification(s)") + "<k> awaiting approval", "<k> rejected" | `s01_executive_overview.py:389-395` |
| 02 KPI counts | The added action counts in "Total" and "Low priority" | `s02:222-228` |

## Read but never printed

| Field | Why it is read (QA, ordering, ...) |
|---|---|
| `certificates[].credit_applied` | QA: a rejected record must not carry credit. Weighting (pending 1 / approved 2 / rejected 0) is never printed |
| `certificates[].eligibility`, `credit_summary` | Not read (internal weighting) |
| `certificates[].certificate_id` | Grouping key for unnamed standards |
| `certificates[].card_text_source` | Not read |
| `certificates[].origin_label_source` | Only printed when `origin` is not a known code |
| `reference_standards.title_source` | Not read; the heading is fixed |
| `metrics[].count_kind`, `source_label` | Not read |
| `state_label_source` | Not read |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| `findings` | Identified | No card. KPIs, certificate block, reference block |
| `clear` with records | No findings | Card + KPIs + certificate block + reference block. The "also appear" sentence is not added |
| `clear` / `findings` / `partial` without records | None identified (adjusted) | As `none_identified` |
| `none_identified` | None identified | Card "No certificates identified" + KPIs (0% if no score) + reference block |
| `partial` | Partial coverage | Banner + full body |
| `pending_review` | Pending review | Card + full body. With no records: "No certificate records in the assessment data." |
| `not_assessed` / `not_applicable` / `unavailable` | Not assessed / Not applicable / Unavailable | Card + reference block only. The 02 action is still added if pending detected records exist |

## QA checks raised

| check id | severity | when |
|---|---|---|
| `state_adjusted` | info | No certificate records → `none_identified` (`__init__.py:176`) |
| `unknown_term` | warn | `approval_state` is not a known value (`s13:224`) |
| `data_mismatch` | warn | Rejected certificate with `credit_applied` > 0 (`s13:269`) |
| `data_mismatch` | warn | Headline metric (unit `certifications_headline`) ≠ number of records (`s13:340`) |
| `missing_document` | warn | A D.5 document cannot be shown (no file / path not accepted / not found) (`appD:575`) |

## Backend checklist

- MUST: `state`. For each certificate, MUST send:
  - `standard`
  - `origin` (`detected` | `uploaded`)
  - `approval_state` (`pending` | `approved` | `rejected`; uploads arrive `approved`)
  - `valid_from`, `valid_until`: ISO dates, or null with a `reason_code` (`not_detected` when the system found none)
- MUST: `metrics[]` with `compliance_score` (unit `percent`) when the system has a score.
- SHOULD, per certificate:
  - `standard_full_name`
  - `category` (`security` | `privacy` | `both`)
  - `source_url` (detected records)
  - `expired` (system flag; it is never computed)
- SHOULD: `summary`, `intro_source`.
- Uploaded records, optional:
  - `issuer`
  - `scope_source`
  - `file_reference`
  - `document`: a relative path inside the JSON's folder (.png / .jpg / .jpeg / .pdf). Omit the key instead of sending null.
- Optional:
  - a headline metric with unit `certifications_headline`
  - `reference_standards {is_vendor_evidence: false, items[] {standard, description}}`
  - `credit_applied` / `eligibility` (internal, never printed)
