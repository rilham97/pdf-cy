# 11 Quantum security

Payload key: `sections.quantum_security` · Module: [s11_quantum_security.py](../../cyberrank_report/sections/s11_quantum_security.py) · Shared rules: [README](README.md)

Register: Appendix **D.4** (`RID['s11']`), built by `d5_quantum` in [app_d_evidence_registers.py](../../cyberrank_report/sections/app_d_evidence_registers.py). File refs below: `s11:` = `s11_quantum_security.py`, `appD:` = `app_d_evidence_registers.py`.

## Layout (top to bottom)

States `findings` / `partial` / `pending_review` (`s11:588-596`):

1. Section opener: "11", title, state chip, `summary` as verdict, `intro_source` (shared; the module has no `verdict()`).
2. State card / banner (only `partial`, `pending_review`, see States).
3. KPI strip from `metrics` (`s11:313-322`).
4. KPI notes: headline relation, subdomain sum, category total, source notice (`s11:325-366`).
5. "Findings by algorithm" (H2, severity legend on the heading line when rated), intro, table (`s11:369-405`). Omitted when no algorithm rows.
6. "Post-quantum cryptography detected" (H2) with one H3 block per `pqc_detected[]` entry, or "Post-quantum cryptography" (H2) with a one-paragraph statement (`s11:408-457`).
7. "Affected protocols" (H2) table (`s11:460-476`). Omitted when `affected_protocols` is empty.
8. "Risk after PQC coverage" (H2) table (`s11:479-507`). Omitted when no register row has `risk_note_source`.
9. "Scope breakdown" (H2): tier T1 = full inline register; tier T2/T3 = grouped overview + "Full register" pointer to D.4 (`s11:514-553`). No register rows: one line "Scope rows: Not available (not provided in the assessment data)." (`s11:594-595`).
10. "Scope and limitations" (H2) with H3 sub-blocks (`s11:556-570`).

State `clear`: opener, card, then only block 10 (`s11:589-590`). No-result states: opener + card only.

Appendix D.4 (T2/T3 only, `appD:470-500`):

1. H2 "D.4  Quantum scope breakdown" (title from policy) with severity legend; two opening lines; "Back to Section 11 Quantum security, p. n".
2. H3 "D.4.1  Scopes": pivot table, one row per scope (`s11:252-275`).
3. H3 "D.4.2  Scope × algorithm rows": every register row (`s11:210-237`, `number_all=True`).
4. Post-QC note (when a row has no `post_qc_algorithm`).
5. End line "End of register · N scope × algorithm rows. …" (`appD:316-323`, `s11:283-309`).

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `summary` | Opener verdict | No verdict line |
| `intro_source` | Opener intro | Omitted |
| `title` | H1 | "Quantum security" |
| `metrics[]` `{id, label, value, unit, state, reason_code}` | KPI tiles in payload order; ids `high_risk` / `moderate_risk` / `low_risk` get a quantum siren and are the **headline** used by every note and check (`s11:278-280`) | Tile "Not available" + reason sentence; a missing headline id makes the headline "not available" in notes and disables headline comparisons |
| `metrics[id=pqc_detected].unit` | Unit after the value | Unit ending `_inferred` (or empty): label replaced, unit dropped (`s11:316-317`) |
| `metrics[].state` | Small state chip on the tile when not `findings` | — |
| `beta_notice_source` | Note "Source notice: <text>" (`s11:364-365`) | Omitted |
| `findings_by_category[].category` | Category cell: icon + name (first row of the category) (`s11:172-176`) | "Category not recorded" |
| `findings_by_category[].issues` | "<n> findings in category" under the category; summed for the category-total note | `fmt_value` "Not available (…)" + " in category" |
| `findings_by_category[].domains_source_label` | Appended " · <label>" | Omitted |
| `findings_by_category[].algorithms[].algorithm` | Algorithm cell (mono) | "Not available (reason not recorded)" |
| `…algorithms[].risk_level` | Risk siren (`high`/`moderate`/`low`); orders rows; decides "rated" | Not rated; if no algorithm anywhere is rated, the Risk column is dropped |
| `…algorithms[].findings` | Findings cell | Missing-value cell |
| `…algorithms[].protocol_labels[]` | Joined ", " | "Not listed" |
| `…algorithms[].pqc_alternative_available` | PQC chip with the value | "Not available" (reason not printed) |
| `pqc_detected[].algorithm` | H3; chip text "<alg> detected" in register/breakdown | "Algorithm not recorded" |
| `pqc_detected[].algorithm_alias` | " (<alias>)" after the H3 | Omitted |
| `pqc_detected[].purpose`, `.status_source` | Intro "<purpose> · <status>" (leading "Status:" stripped) | Part omitted |
| `pqc_detected[].domains_count` | "Detected on <n> of <N> scopes." | `len(domains)` |
| `pqc_detected[].domains[]` | Mono domain grid (≤ 4 columns); also maps scope → PQC chip | No grid |
| `affected_protocols[] {protocol, algorithms[], pqc_source, risk_level}` | "Affected protocols" table | "Protocol not recorded" / "Not listed" / "Not available" / "Not recorded" |
| `scope_register_ref` | Dotted path to the scope register (e.g. `appendices.d_evidence_registers.quantum_scope_register`) | No register: no scope breakdown, no D.4 |
| register `rows[].subdomain` | Group label / Subdomain cell (mono) | Grouped under "None" |
| register `rows[].scope_level` | `root_aggregate` = apex aggregate row(s) | If **no** row has the key: apex inferred (see rules) |
| register `rows[].category` | Category cell (icon + name) | Missing-value cell |
| register `rows[].pre_qc_algorithm` | "Algorithm (pre-QC)" | Missing-value cell |
| register `rows[].post_qc_algorithm` | "Post-QC" | "Not listed" + Post-QC note |
| register `rows[].high` / `moderate` / `low` | Count cells; totals; ordering | Totals become "not available"; ordering treats as 0 |
| register `rows[].source` | "Source" column (only when values differ) or "Source: all rows “<x>”." | See bugs |
| register `rows[].risk_level`, `risk_note_source` | "Risk after PQC coverage" table | Row not in that table |
| register `counts.rows`, `counts.scopes` | Compared in the D.4 end line | No check |
| `scope_summary[].subdomain` + `.algorithms_absent[]` | Group label "  ·  <A, B> not observed" | Omitted |
| `scope_and_limitations_source.{scope_and_limitations, post_quantum_readiness}.{title, intro, items[], closing}` | "Scope and limitations" block | Block omitted |
| `appendices.d_evidence_registers.pqc_domain_register.rows[] {domain, algorithm}` (fixed path) | Count compared with `pqc_detected[].domains` | No check |
| `identity.domain` | Apex inference only | No inference |
| `snapshot.toggles_at_assessment.pqc_scan` (bool or `{value}`) | `false` → not_assessed; `true` → allows "No PQC detected"; reason printed in "PQC not reported" text | "PQC not reported" wording |
| `snapshot.assessed_at` | "Snapshot <date>" in D.4 | Missing-value text |
| `what_checked` | Clear card "What was checked" | Generator default (see Hardcoded) |
| `state_reason`, `reason_code` | Card reason | Fallbacks per state |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes (e.g. policy override key) |
|---|---|---|
| "PQC detected (unit not confirmed by source)" | KPI label of `pqc_detected` with `_inferred` unit | `s11:317` |
| "High, Moderate and Low are the source headline: the apex aggregate, as scored in the product." | Note lead (headline known) | `s11:329-330` |
| "High, Moderate and Low are the source headline. They equal the number of scope × algorithm rows in the scope breakdown at each level (<n> rows, each counted once at its highest level; every row is listed in Appendix D.4)." | Note | `s11:335-337` |
| " The <apex label> row for <apex> gives the same High, Moderate and Low findings." / " The headline is not the <apex label> row for <apex>, which sums to <HML> findings." | Appended to the note above | `s11:338-343` |
| "The <apex label> row for <apex> matches it and covers the apex and <n> subdomains (<n+1> scopes)." / "… covers the apex only (1 scope); no subdomain rows are listed" | Note | `s11:346-348` |
| "The <apex label> row for <apex> in the scope register sums to <HML>, which differs from the headline; not explained by the source data." | Note | `s11:352-354` |
| "No apex aggregate row is recorded." | Note | `s11:356` |
| " The subdomain rows sum to <HML>; they are not added to the headline." | Appended when subdomains exist | `s11:332` |
| "Subdomain rows exceed the apex aggregate that covers them (<Level> <c> vs <a>, …); not explained by the source data." | Note + D.4 end line | `s11:90-93` |
| "Findings by category total <x>; High + Moderate + Low total <y> (difference <±z>)." | Note | `s11:362-363` |
| "Source notice: " | Prefix of `beta_notice_source` | `s11:365` |
| `<HML>` = "High <n> · Moderate <n> · Low <n>" ("not available" for null) | Everywhere counts are quoted | `s11:67-70` |
| "Findings by algorithm"; columns "#", "Risk", "Category", "Algorithm", "Findings", "Protocols", "PQC alternative" | Section 11 | `s11:390, 403` |
| "Each algorithm counts findings across all scanned scopes. High risk marks key exchange that a quantum computer could break; a PQC alternative is the replacement the source names." | Intro (rated) | `s11:399-400` |
| "Each algorithm counts findings across all scanned scopes; the source prints no risk level per algorithm. A PQC alternative is the replacement the source names." | Intro (not rated) | `s11:401-402` |
| "<n> findings in category" | Category cell sub-line | `s11:377` |
| "Not listed", "Not available", "Not recorded", "Category not recorded", "Protocol not recorded", "Algorithm not recorded" | Empty cells | `s11:37, 176, 383-385, 414, 462-466` |
| "Post-quantum cryptography detected" | H2 when `pqc_detected` has entries | `s11:457` |
| "Detected on <n> of <N> scope(s). Support for PQC does not prove that every connection uses it." | Per PQC block | `s11:421-422` |
| "The source names <n> <alg> domains but the scope register holds <N> scopes; not explained by the source data." | Note | `s11:436-437` |
| "PQC domain register lists <n> domains for <alg>; this section lists <m>." | Note | `s11:440-441` |
| "No <alg \| PQC> observed on <k> of <N> scopes" + mono list | After PQC blocks | `s11:444-447` |
| "Post-quantum cryptography" + "No post-quantum cryptography was detected on the one scope in the register." / "… on any of the <N> scopes." | No `pqc_detected`, PQC reported | `s11:450-451` |
| "PQC not reported: the assessment data lists no post-quantum detection and does not record whether the PQC scan ran (<reason \| scan setting not recorded>). This is not a finding that PQC is absent." | No `pqc_detected`, PQC not reported | `s11:453-455` |
| "<alg> detected" / "No PQC detected" / "PQC not reported" | PQC chips (breakdown, D.4) | `s11:155-163` |
| "Affected protocols"; columns "#", "Risk", "Protocol", "Algorithms", "PQC" | Section 11 | `s11:475-476` |
| "Risk after PQC coverage"; columns "#", "Risk", "Scope", "Algorithm", "Counts", "Source explanation" | Section 11 | `s11:499-503` |
| "<n> scope row(s) carry a risk explanation in the source. The High, Moderate and Low counts stay as reported; the Risk column is the source's assessment after PQC coverage." | Intro | `s11:500-501` |
| "Post-QC: <alg \| Not listed>" | Algorithm cell sub-line | `s11:488` |
| "<n> row(s) print a Risk level that differs from the column holding the count; both are shown as printed." | Note | `s11:505-506` |
| "Scope breakdown"; register columns "#", "Category", "Algorithm (pre-QC)", "Post-QC", High/Moderate/Low sirens, "Source" | T1 inline and D.4.2 | `s11:213-214` |
| "  ·  apex aggregate" / "apex aggregate (inferred)", " (headline scope)", "  ·  <A, B> not observed" | Apex / group label rows | `s11:142, 147, 220-221` |
| "A1", "A2", … | Apex row numbers (inline T1 only) | `s11:227` |
| `POST_QC_NOTE`: "Post-QC “Not listed”: the source prints a dash, so no post-quantum replacement is listed for that algorithm; the source does not say whether one was checked." | After T1 table and D.4.2 | `s11:38-39` |
| "<G> subdomains in <K> groups with identical counts, PQC status and algorithms, ordered by High, then Moderate, then Low findings. Appendix D.4 lists one row per subdomain and every scope × algorithm row (<N>)." | T2 overview intro | `s11:535-537` |
| Columns "Subdomains", sirens, "PQC", "Algorithms vs apex"; cell "<n> subdomains"; "Same as apex"; "No <alg>" / "+<alg>" | T2 overview | `s11:249, 511, 528, 539` |
| "Showing <shown> of <total> subdomains." | T2 note | policy `reconciliation.showing` (`s11:542`) |
| "Apex aggregate (parent, not added to totals): High {h} · Moderate {m} · Low {l}." | T2 note | policy `lists.quantum_scope.overview_components[id=apex_aggregate_note].text` replaces it **only** when the headline equals the apex row (`s11:545-547`) |
| "Source: all rows “<x>”." | T2 note when one source | `s11:550` |
| "Full register  D.4 Quantum scope breakdown · <n> scopes · Appendix D, pages a–b" | T2 pointer | title: policy `lists.quantum_scope.register_title`; top N: `lists.quantum_scope.top_n` → `tiers.top_n_default` → 10 (`s11:526, 552-553`) |
| "Scope rows: Not available (not provided in the assessment data)." | No register rows | `s11:595` |
| "Scope and limitations"; H3 from `title` minus a leading "a. ", else "Scope and limitations" / "Post quantum readiness" | Block 10 | `s11:558, 564` |
| "No quantum-vulnerable algorithms were identified within the scope and period of this assessment." | Clear card reason fallback | `s11:575-576` |
| "TLS/SSL configurations and SSH endpoints on <n> scopes" (or "… in scope"), "Classical algorithms exposed to future quantum attack (key exchange, public-key, symmetric)", "Post-quantum key exchange support (ML-KEM)" | Clear card "What was checked" | `s11:580-584` |
| "The post-quantum (PQC) scan was switched off when this assessment was created, so quantum exposure was not assessed. This is not a result of no findings." | Card reason when `pqc_scan` is false | `s11:57-59` |
| "<reason>. This is not a zero result." / "<reason>. Counts below are lower bounds." | unavailable card / partial banner | `appD:118-121` |
| "Pending review — counts may change before this report is final." | pending_review card without reason | policy `states.overview_messages.pending_review_banner` (`appD:123`) |
| D.4 opening line 1: "D.4.1 lists one row per scope with its post-quantum (PQC) status, ordered by High, then Moderate, then Low findings. The apex aggregate[ (the source headline scope)] comes first; subdomain rows are not added to it. Showing <S> of <S> scopes. D.4.2 lists every scope × algorithm row (<N> of <N>)." | D.4 | `appD:484-487` |
| D.4 opening line 2: "Unit: scopes (D.4.1) and scope × algorithm rows (D.4.2); counts are findings. Source: <all rows “x” \| per row>. State: <label>. Snapshot <date>." | D.4 | `appD:488-489` |
| "D.4.1  Scopes", "D.4.2  Scope × algorithm rows"; pivot columns "#", "Subdomain", "PQC", sirens, "Algorithms vs apex"; apex row "A" + "Reference" | D.4 | `s11:258-265`, `appD:492-494` |
| End line: "End of register · <N> scope × algorithm rows. <S> of <S> scopes shown; 0 not shown (none withheld; all <N> scope × algorithm rows in D.4.2). Totals: over <G> subdomain rows, <x> findings (<HML>) from <C> subdomain × algorithm rows; <apex label>, not added, <HML> — <match>[; <N> scope × algorithm rows by level (highest level per row): <HML>][; source count “rows” is <a>, listed <b>][; <exceed text>]." | D.4 | policy `reconciliation.register_end` (`s11:300-309`, `appD:318-320`) |
| `<match>`: "matches the Section 11 headline" / "differs from the Section 11 headline <HML>, which counts the <N> scope × algorithm rows by level (highest level per row)" / "Section 11 headline is <HML>; difference not explained by the source data" | D.4 end line | `s11:287-294` |
| Index content: "<S> scopes (one row each) and all <N> scope × algorithm rows"; or a `state_message` (e.g. "Not required — all <n> scope rows shown in Section 11.") | Appendix D index | `appD:478-479, 499, 598-611` |

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| `pqc_scan` recorded `false`, no quantum results | State forced to `not_assessed` (`pqc_scan_disabled`), card only | `s11:51-59` |
| `pqc_scan` `false` **and** results (`findings_by_category`, `pqc_detected`, `scope_summary`, `affected_protocols`, a non-null metric, or register rows) | Load error, exit 1 | `build.py:135-157` |
| State `clear` | Card + "Scope and limitations" only; no KPIs, tables or register | `s11:589-590` |
| Clear and no `what_checked` | Default 3 bullets; n = `len(scope_summary)` else scopes in the register | `s11:577-584` |
| Metric id ends `_risk` with level high/moderate/low | Siren tile, quantum scale | `s11:318-320` |
| Headline = rows-by-level (each row at its highest non-zero level) | "They equal the number of scope × algorithm rows…" note (+ apex same / differs) | `s11:333-344` |
| Else headline = apex row totals | "…matches it and covers …" note | `s11:345-348` |
| Else apex present | "…differs from the headline…" note + QA `data_mismatch` | `s11:349-354` |
| Else register rows, no apex | "No apex aggregate row is recorded." | `s11:355-356` |
| Any subdomain-row level total > apex total | Exceed note + QA `data_mismatch` | `s11:77-87, 357-359` |
| Σ `findings_by_category[].issues` ≠ Σ headline (both known, issues > 0) | Category-total note | `s11:360-363` |
| No `scope_level` key on any row, a row's `subdomain` = `identity.domain`, its sums = headline, and it is not every row | Those rows become the apex, label "apex aggregate (inferred)", QA `apex_inferred` | `s11:123-129` |
| Headline (all known) = apex row totals | Label suffix " (headline scope)"; policy apex note text allowed | `s11:140-142, 546` |
| No algorithm carries `risk_level` high/moderate/low | Risk column removed; no legend on "Findings by algorithm"; legend moves to "Scope breakdown" | `s11:394-396, 404, 517` |
| `pqc_detected[]` non-empty or `pqc_scan` true | "PQC reported": chip "No PQC detected" for scopes without PQC; no-PQC paragraph says "was detected" | `s11:137, 161, 450` |
| Neither | Chip "PQC not reported"; paragraph "PQC not reported: …" | `s11:163, 453` |
| `pqc_detected` empty and no register rows | No PQC heading at all | `s11:448-457` |
| `domains_count` (or domain count) > scopes in register | Mismatch note | `s11:434-437` |
| pqc_domain_register has rows and its count for the algorithm ≠ `len(domains)` | Mismatch note | `s11:438-441` |
| Some scopes have no PQC (and a PQC block printed) | "No … observed on k of N scopes" + list; names the algorithm when only one | `s11:442-447` |
| Domain grid columns | `min(4, CW // widest domain)` | `s11:426` |
| `affected_protocols[].risk_level` not high/moderate/low | "Not recorded" in Risk | `s11:465-466` |
| Register row has `risk_level` whose own count column is 0/missing | "…differs from the column holding the count" note | `s11:498, 504-506` |
| All register rows share one non-null `source` | No Source column; T2 note "Source: all rows “x”." (T1: nothing) | `s11:149, 214, 549-550` |
| Tier: visual rows = child rows + subdomain groups + 1 (apex) ≤ 30 → T1; data rows > 1000 → T3; else T2 | T1: full table inline, D.4 index row only. T2/T3: grouped overview + pointer + D.4 (T3 behaves as T2) | `s11:148`, `appD:79-83`, policy `tiers.T1_inline.max_visual_rows`, `tiers.T2_overview_register.max_rows` |
| T2: subdomains with equal totals, PQC algorithm and apex-difference | Collapsed into one row "<n> subdomains" | `s11:523-529` |
| T2: more groups than top N | "Showing x of y subdomains." | `s11:541-543` |
| Apex exists vs not (pivot) | "Same as apex" / differences; no apex → empty cell | `s11:263-264` |
| Apex and ≥ 1 group (pivot) | Apex row never ends a page alone | `s11:273-274` |
| A row has no `post_qc_algorithm` | POST_QC_NOTE after the table | `s11:521, appD:495-496` |
| Text column identical in every row | Column collapsed into "<Col>: <value> (all rows)." | `appD:184-190, 287-289` |
| D.4 built only when register rows exist, tier ≠ T1 and state ∈ findings/partial/pending_review | Else index row with `state_message` | `appD:477-479` |
| Source `counts.rows` / `counts.scopes` ≠ listed | "; source count “rows” is a, listed b" in end line | `s11:295-297` |
| Headline = rows-by-level (not apex) | End-line match text "differs …" and the rows-by-level clause dropped | `s11:289-292` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Headline (H, M, L) | `metrics[id in high_risk, moderate_risk, low_risk].value` | `s11:278-280` |
| Rows by level | Each register row counted once at its first non-zero level of high → moderate → low | `s11:108-115` |
| Apex totals / subdomain totals | Σ `high`/`moderate`/`low` over apex rows / non-apex rows; any null → null | `s11:62-64, 134, 145` |
| Group order | Subdomain totals desc (H, M, L), then name | `s11:135` |
| Row order inside a group | `high` desc, `category`, `pre_qc_algorithm` | `s11:224-225` |
| Algorithms vs apex | Set difference of `pre_qc_algorithm` vs apex set: "No X", "+X" | `s11:244-249` |
| Scopes | Subdomain groups + 1 if apex | `s11:409, appD:481` |
| Algorithm table order | Category by its best-ranked algorithm; algorithms by risk | `s11:370-374` |
| Category / headline differences | Σ issues − Σ headline (signed) | `s11:360-363` |
| Post-QC missing count | Rows without `post_qc_algorithm` | `s11:152` |
| 01 "All aspects" result line | `metrics[high_risk]` as "<n> high-risk finding(s)"; 0 when state clear and metric absent | `s01_executive_overview.py:370-376, 420` |

## Read but never printed

| Field | Why it is read (QA, ordering, ...) |
|---|---|
| `scope_summary[]` (except `subdomain`, `algorithms_absent`) | Only `len(scope_summary)` for the clear-card count; `rows`, `high`, `moderate`, `low`, `scope_level`, `ml_kem_on_key_exchange` unused |
| `aggregation_note`, `state_label_source` | Not read |
| `metrics[].count_kind` | Not read |
| `findings_by_category[].algorithms[].pqc_alternative_available_state` / `_reason_code` | Not printed ("Not available" without reason) |
| register `rows[].id`, `post_qc_source`, `source_page`, `post_qc_algorithm_state` / `_reason_code` | Not printed |
| register `counts.rows`, `counts.scopes` | Reconciliation in the D.4 end line only when they differ |
| `identity.domain` | Apex inference |
| `pqc_domain_register.rows[]` | Count check note only |
| `snapshot.toggles_at_assessment.pqc_scan` | State adjust + wording choice |

## States

| Payload state | Chip shown | Body |
|---|---|---|
| `findings` | Findings | Full layout |
| `partial` | Partial coverage | Banner "<reason>. Counts below are lower bounds." + full layout |
| `pending_review` | Pending review | Card "Result held for review" (reason: `state_reason` / reason / policy banner) + full layout |
| `clear` | No findings | Card (reason or clear text + "What was checked") + "Scope and limitations" only |
| `not_assessed` (incl. forced by `pqc_scan` false) | Not assessed | Card only (default reason); D.4 index "Not produced — Section 11 was not assessed." |
| `not_applicable` | Not applicable | Card only |
| `unavailable` | Unavailable | Card "<reason>. This is not a zero result." only |
| `none_identified` | None identified | Card "None identified" + full layout (not expected for 11) |

## QA checks raised

| check id | severity | when |
|---|---|---|
| `state_adjusted` | info | `pqc_scan` false moves the section to `not_assessed` (`__init__.py:171-178`) |
| `apex_inferred` | warn | Apex taken from `identity.domain` rows because no row has `scope_level` (`s11:128`) |
| `data_mismatch` | warn | Headline ≠ apex aggregate row and headline ≠ rows-by-level (`s11:350`) |
| `data_mismatch` | warn | Subdomain-row total exceeds the apex total at any level (`s11:85`) |
| `severity_term` | warn | Unknown `risk_level` term in an algorithm / protocol / register cell (`icons.py:126`) |
| (load error, exit 1) | error | `pqc_scan` false with quantum results (`build.py:149-157`) |

## Backend checklist

- MUST: `state`; `metrics[]` with ids `high_risk`, `moderate_risk`, `low_risk` (unit `findings`) — they are the headline every check compares against.
- MUST: `scope_register_ref` pointing at `appendices.d_evidence_registers.quantum_scope_register` with `rows[] {subdomain, scope_level (root_aggregate | subdomain), category, pre_qc_algorithm, post_qc_algorithm (null + reason when the source shows a dash), high, moderate, low, source}`. Without `scope_level` the apex is guessed (QA warn).
- MUST: `snapshot.toggles_at_assessment.pqc_scan` (`true`/`false`); `false` only with no results.
- SHOULD: `findings_by_category[] {category, issues, domains_source_label, algorithms[] {algorithm, findings, protocol_labels[], pqc_alternative_available, risk_level}}`.
- SHOULD: `pqc_detected[] {algorithm, algorithm_alias?, purpose, status_source, domains_count, domains[]}` and the matching `pqc_domain_register`.
- SHOULD: `summary`, `intro_source`, `scope_and_limitations_source`.
- Optional: `metrics[id=pqc_detected]`, `beta_notice_source`, `affected_protocols[]`, register `rows[].risk_level` + `risk_note_source`, register `counts {rows, scopes}`, `scope_summary[].algorithms_absent[]`, `what_checked` (clear).
