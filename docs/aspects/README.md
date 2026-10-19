# Per-aspect integration guide

For backend engineers and AI agents connecting the Cyberrank backend to this generator. There is one file
per section. Each file lists:

- **From the system:** payload fields and how each one prints.
- **Hardcoded:** text the generator writes itself.
- **Conditional rules:** the if/else branches that decide what prints.
- **Computed:** values the generator derives from the payload.
- **Read but never printed.**
- **States and QA checks.**

Every field's type and shape is in [data/report-schema.md](../../data/report-schema.md), and the design rules
are in [AGENTS.md](../../AGENTS.md). This page covers the rules that apply to **every** section.

| # | Section | Payload key | File |
|---|---|---|---|
| — | Cover, header, footer | `identity`, `snapshot` | [00-cover-and-page-frame.md](00-cover-and-page-frame.md) |
| 01 | Executive overview | `sections.executive_overview` | [01-executive-overview.md](01-executive-overview.md) |
| 02 | Priority actions | `sections.priority_actions` | [02-priority-actions.md](02-priority-actions.md) |
| 03 | Privacy | `sections.privacy` | [03-privacy.md](03-privacy.md) |
| 04 | Vulnerabilities (+ D.1) | `sections.vulnerabilities` | [04-vulnerabilities.md](04-vulnerabilities.md) |
| 05 | Credential exposure (+ D.2) | `sections.credential_exposure` | [05-credential-exposure.md](05-credential-exposure.md) |
| 06 | Data breach and leak history (+ D.3) | `sections.data_leak_history` | [06-data-leak-history.md](06-data-leak-history.md) |
| 07 | Data sovereignty | `sections.data_sovereignty` | [07-data-sovereignty.md](07-data-sovereignty.md) |
| 08 | Data residency | `sections.data_residency` | [08-data-residency.md](08-data-residency.md) |
| 09 | Legal terms & conditions | `sections.legal_terms` | [09-legal-terms.md](09-legal-terms.md) |
| 10 | AI risk and governance | `sections.ai_risk_governance` | [10-ai-risk-governance.md](10-ai-risk-governance.md) |
| 11 | Quantum security (+ D.4) | `sections.quantum_security` | [11-quantum-security.md](11-quantum-security.md) |
| 12 | Security resourcing | `sections.security_resourcing` | [12-security-resourcing.md](12-security-resourcing.md) |
| 13 | Certifications (+ D.5) | `sections.certifications` | [13-certifications.md](13-certifications.md) |
| 14 | Fourth-party vendors (+ D.6) | `sections.fourth_party_vendors` | [14-fourth-party-vendors.md](14-fourth-party-vendors.md) |
| 15 | Cloud infrastructure | `sections.cloud_infrastructure` | [15-cloud-infrastructure.md](15-cloud-infrastructure.md) |
| A | About this report | `appendices.a_about` | [A-about.md](A-about.md) |
| B | IISRI rating scale | `appendices.b_rating_scale` | [B-rating-scale.md](B-rating-scale.md) |
| C | Methodology | `appendices.c_methodology` | [C-methodology.md](C-methodology.md) |
| D | Evidence registers (frame, D.6) | `appendices.d_evidence_registers` | [D-evidence-registers.md](D-evidence-registers.md) |

The order of sections is fixed in `sections.REGISTRY` ([sections/__init__.py](../../cyberrank_report/sections/__init__.py)).
Each section starts on a new page.

## 1. Pipeline (what happens to the payload)

| Step | What it does | Code |
|---|---|---|
| `normalise` | Converts old payload shapes to the current one. Old aliases are `identity.industry`, `sector_comparison.industry`, metric ids `industry_*`, and `sections.privacy.{sovereignty, residency, terms_conditions, resourcing}`, which become their own sections. Values are never translated. | `build.py` `normalise` |
| `validate` | Checks the input contract. On failure it exits with **code 1** and lists every offending path. See §2. | `build.py` `validate` |
| `adjust_report` | Runs each module's `adjust()` hook. A hook can move a section to `pending_review` through `hold()` when the payload contradicts itself. This raises QA `state_adjusted` (info). Section 01 sees the adjusted states. | `sections/__init__.py` |
| render | Calls `render_section` for every section (§3). | `sections/__init__.py` |
| QA | Checks the rendered PDF and writes `<out>.qa.json`. If QA finds an error, the program exits with **code 2**. | `qa.py` |

## 2. Input contract (the build stops if any rule fails)

- Every `state`, and every `<field>_state` next to a `<field>`, must be one of: `findings`, `clear`,
  `partial`, `pending_review`, `not_assessed`, `not_applicable`, `unavailable`, `none_identified`.
  You can override this list with `meta.state_enum`.
- **Every `null` needs a reason.** Put a `reason_code` on the same object, or a `<field>_reason_code` or
  `<field>_reason` next to the field. A `null` list item is always rejected.
- The states `not_assessed`, `not_applicable` and `unavailable` need a `reason_code`, `state_reason` or `reason`.
- Every metric in `metrics[]` or `observed_targets[]` needs a `unit`.
- Every `*_at` field, plus `valid_from`, `valid_until` and `last_scanned`, must be an ISO date (`YYYY-MM-DD`).
  A shorter date needs `precision`, which is one of `minute`, `day`, `month` or `year`.
- If `toggles_at_assessment.pqc_scan` is off, the quantum section must not carry results.

## 3. How every section renders

Order on the page: eyebrow → H1 with the aspect icon → `intro_source` → state chip + verdict → card → body.

| Rule | Detail | Code |
|---|---|---|
| Verdict | `summary` from the payload. If it is missing, the module's `verdict()` writes one. | `render_section` |
| State chip | `theme.shown_state(state, key)` (§4) | `render_section` |
| No-result states (`not_assessed`, `not_applicable`, `unavailable`) | A **card replaces the body**. The module's `build_context()` can add context below the card. | `NO_RESULT` |
| Card states (`clear`, `partial`, `pending_review`, `none_identified`) | A card appears **above** the body. | `WITH_CARD` |
| Card text | Reason: `state_reason`, then the text for `reason_code` (§5). For `clear`, `empty_state_source.text` is also used. "What was checked": `what_checked` or `empty_state_source.coverage`. "Next step": `next_step`. A module's `card()` can override any of these. | `default_card` |
| Reference appendices A, B, C | They get no chip and no card unless their state is a no-result state. | `REFERENCE` |

## 4. States: label, colour, icon

The colour sits only on the icon. The label text stays in body colour. Tokens are in `theme.STATE`.

| Payload state | Chip label | Colour | Icon | Meaning |
|---|---|---|---|---|
| `findings` (risk sections 03–11) | **Findings** | orange `#D97706` | warning-circle | Weaknesses were reported. Severity sirens and scores show how serious they are. |
| `findings` (sections 02, 12, 13, 14, 15 and Appendix D = `theme.INVENTORY`) | **Identified** | navy | ring with a centre dot | Items were found in an inventory or good-news section. Display-only: never send `identified` in the payload. |
| `findings` (section 01) | *(no chip; the verdict prints full width without a label)* | — | — | A summary has no "results present" state. |
| `clear` | No findings | green | check-circle | Nothing was found within the scope and period checked. In 12 it means roles were found and nothing is missing. |
| `none_identified` | None identified | grey | empty ring | An inventory known to be empty. It is not a statement about risk. |
| `partial` | Partial coverage | orange | half ring | Only part of the scope was covered. |
| `pending_review` | Pending review | orange | hourglass | The value exists but is contradicted or ambiguous. |
| `unavailable` | Unavailable | orange | question | The value could not be obtained. |
| `not_assessed` | Not assessed | grey | minus-circle | The module did not run. |
| `not_applicable` | Not applicable | grey | prohibit | The check does not apply. |

Other status markers inside sections (match, enabled, approved, expired, …) map through `theme.TONE` to
good (green), bad (red, genuine failure only), attention (orange) or neutral (grey). An unknown key raises
an error.

## 5. Missing values (NullReason)

- **Missing is not zero.** A null prints as `Not available (<reason>)` and never as 0, "safe" or "valid"
  (`text.missing_text`). In narrow table columns (< 110 pt) it prints as `Not available¹`, and each reason
  appears once under the table.
- The reason text comes from the first one found: `reason` → `state_reason` → `text.REASONS[reason_code]` →
  the code with `_` replaced by spaces → "reason not recorded".
- Known `reason_code` values and their text are in `text.REASONS`, for example
  `not_printed_in_source` → "not provided in the assessment data". If you add a new code, add its text there
  too. Otherwise the code itself prints in plain words.
- The product defines one exception: certifications with no records print 0% and the state `none_identified`.

## 6. Text the generator never invents

- Fields ending in `_source` and `*_label_source` print **verbatim**. When the generator interprets a value,
  it adds a separate Note.
- System flags are **printed, never computed**: certificate `expired`, breach `resolved`/inaccurate, match
  states and scores. The generator never compares dates.
- **Hidden scoring:** the demerit ledger, points, caps, credits and certificate weighting are read for QA
  only and **never printed**.
- **Privacy:** account labels arrive masked from the backend and print exactly as received. If a label has
  no `*`, QA raises `unmasked_account_label`. Every `@` address in the PDF must contain `*`, except
  `support@cyberrank.ai`.

## 7. Long lists and the external policy file

- A table with up to 30 rows prints inline. A longer list gets an overview in the section and the full
  register in Appendix D. Register ids follow section order: D.1 vulns, D.2 credentials, D.3 breach,
  D.4 quantum, D.5 certificate documents, D.6 fourth party.
- Some labels and templates read `pol('<path>', default)` from an **optional** policy file:
  `CYBERRANK_LONG_LIST_POLICY`, or `../long-list-rules/long_list_policy.json`. When the file is missing,
  the built-in defaults in the code apply. Each section file names the override keys it uses.

## 8. Environment and assets

| Item | Purpose |
|---|---|
| `CYBERRANK_LONG_LIST_POLICY` | Path to the long-list policy JSON (optional). |
| `CYBERRANK_SUPPLY_CHAIN_PDF`, `CYBERRANK_SUPPLY_CHAIN_INDEX` | The locked production page inserted into Appendix C. If the file is missing or unreadable, or the index is not a whole number inside it, QA raises `locked_page_missing` (error) and a card replaces the page. |
| `identity.logo.value` | Cover logo: a PNG/JPG path relative to the JSON, inside its folder (same rule as certificate documents). |
| `certificates[].document` | Path to an uploaded certificate file (PNG, JPG or PDF), relative to the JSON. It must stay inside the JSON's folder. If it is missing, QA raises `missing_document`. |
| Fonts | Poppins for body text, Inter for the title, JetBrains Mono for technical tokens. If no font has a character, it falls back to Noto Math → Noto Symbols2 → Noto SC (CJK). A character still missing raises QA `missing_glyph` (warn). Arabic and other scripts that need shaping are not supported. |

## 9. QA checks used by every section

| Check | Severity | When |
|---|---|---|
| `state_adjusted` | info | An `adjust()` hook changed a section's state. |
| `data_mismatch` | warn | Two counts in the payload disagree (both are printed). |
| `unknown_term`, `severity_term` | warn | A label is not in the expected vocabulary. |
| `missing_glyph` | warn | No font has a character. |
| `unresolved_reference` | warn | A cross-reference had no target ("page reference pending"). |
| `min_width`, `word_split` | warn / error | A column was too narrow for a token. |
| `layout_error`, `outside_frame`, `blank_page`, `near_empty_page`, `heading_at_page_foot`, `page_ends_mid_sentence`, `table_header_not_repeated`, `folio`, `page_size` | error / warn | Post-render layout checks in `qa.check_pdf`. |

Section-specific checks are listed in each section file.
