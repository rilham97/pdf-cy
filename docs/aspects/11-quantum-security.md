# 11 Quantum security

Payload key: `sections.quantum_security` · Module: [s11_quantum_security.py](../../cyberrank_report/sections/s11_quantum_security.py) · Shared rules: [README](README.md)

Register: Appendix **D.4** (`RID['s11']`), built by `d5_quantum` in [app_d_evidence_registers.py](../../cyberrank_report/sections/app_d_evidence_registers.py). File refs below: `s11:` = `s11_quantum_security.py`, `appD:` = `app_d_evidence_registers.py`.

## Layout (top to bottom)

States `findings` / `partial` / `pending_review` (`s11:600-608`):

1. Section opener: "11", title, state chip, `summary` as verdict, `intro_source` (shared; the module has no `verdict()`).
2. State card / banner (only `partial`, `pending_review`, see States).
3. KPI strip from `metrics` (`s11:318-327`).
4. KPI notes: headline relation, subdomain sum, category total, source notice (`s11:330-372`).
5. "Findings by algorithm" (H2, severity legend on the heading line when rated), intro, table (`s11:375-411`). Omitted when no algorithm rows.
6. "Post-quantum cryptography detected" (H2) with one H3 block per `pqc_detected[]` entry, or "Post-quantum cryptography" (H2) with a one-paragraph statement (`s11:414-464`).
7. "Affected protocols" (H2) table (`s11:467-483`). Omitted when `affected_protocols` is empty.
8. "Risk after PQC coverage" (H2) table (`s11:486-516`). Omitted when no register row has `risk_note_source`.
9. "Scope breakdown" (H2): tier T1 = full inline register; tier T2/T3 = grouped overview + "Full register" pointer to D.4 (`s11:523-564`). No register rows: one line "Scope rows: Not available (not provided in the assessment data)." (`s11:606-607`).
10. "Scope and limitations" (H2) with H3 sub-blocks (`s11:567-581`).

State `clear`: opener, card, then only block 10 (`s11:601-602`). No-result states: opener + card only.

Appendix D.4 (T2/T3 only, `appD:470-503`):

1. H2 "D.4  Quantum scope breakdown" (title from policy) with severity legend; two opening lines; "Back to Section 11 Quantum security, p. n".
2. H3 "D.4.1  Scopes": pivot table, one row per scope (`s11:256-279`).
3. H3 "D.4.2  Scope × algorithm rows": every register row (`s11:214-241`, `number_all=True`).
4. Post-QC note (when a row has no `post_qc_algorithm`).
5. End line "End of register · N scope × algorithm rows. …" (`appD:316-323`, `s11:287-314`).

## From the system (payload)

| Field path | Printed as / used for | If missing or null |
|---|---|---|
| `summary` | Opener verdict | No verdict line |
| `intro_source` | Opener intro | Omitted |
| `title` | H1 | "Quantum security" |
| `metrics[]` `{id, label, value, unit, state, reason_code}` | KPI tiles in payload order; ids `high_risk` / `moderate_risk` / `low_risk` get a quantum siren and are the **headline** used by every note and check (`s11:282-284`) | Tile "Not available" + reason sentence; a missing headline id makes the headline "not available" in notes and disables headline comparisons |
| `metrics[id=pqc_detected].unit` | Unit after the value | Unit ending `_inferred` (or empty): label replaced, unit dropped (`s11:321-322`) |
| `metrics[].state` | Small state chip on the tile when not `findings` | — |
| `beta_notice_source` | Note "Source notice: <text>" (`s11:370-371`) | Omitted |
| `findings_by_category[].category` | Category cell: icon + name (first row of the category) (`s11:176-180`) | "Category not recorded" |
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
| `pqc_detected[].domains_count` | "Detected on <n> of <N> scope(s)." ("Detected on <n> domain(s)." when there are no register rows) | `len(domains)` |
| `pqc_detected[].domains[]` | Mono domain grid (≤ 4 columns); also maps scope → PQC chip | No grid |
| `affected_protocols[] {protocol, algorithms[], pqc_source, risk_level}` | "Affected protocols" table | "Protocol not recorded" / "Not listed" / "Not available" / "Not recorded" |
| `scope_register_ref` | Dotted path to the scope register (e.g. `appendices.d_evidence_registers.quantum_scope_register`) | No register: no scope breakdown, no D.4 |
| register `rows[].subdomain` | Group label / Subdomain cell (mono) | Grouped under "None" |
| register `rows[].scope_level` | `root_aggregate` = apex aggregate row(s) | If **no** row has the key: apex inferred (see rules) |
| register `rows[].category` | Category cell (icon + name) | Missing-value cell |
| register `rows[].pre_qc_algorithm` | "Algorithm (pre-QC)" | Missing-value cell |
| register `rows[].post_qc_algorithm` | "Post-QC" | "Not listed" + Post-QC note |
| register `rows[].high` / `moderate` / `low` | Count cells; totals; ordering; "Risk after PQC coverage" Counts cell | Totals and the Counts cell print "not available" (never 0); ordering treats as 0 |
| register `rows[].source` | "Source" column (only when values differ) or one note "Source: all rows “<x>”." (T1 and T2) and "Source: all rows “<x>”" / "per row" in the D.4 opening | No row has one: no "Source:" text anywhere; the T1 / D.4.2 Source column shows "Not available (reason not recorded)" per row. Some rows only: column with missing-value cells, D.4 says "per row" |
| register `rows[].risk_level`, `risk_note_source` | "Risk after PQC coverage" table | Row not in that table |
| register `counts.rows`, `counts.scopes` | Compared in the D.4 end line | No check |
| `scope_summary[].subdomain` + `.algorithms_absent[]` | Group label "  ·  <A, B> not observed" | Omitted |
| `scope_and_limitations_source.{scope_and_limitations, post_quantum_readiness}.{title, intro, items[], closing}` | "Scope and limitations" block | Block omitted |
| `appendices.d_evidence_registers.pqc_domain_register.rows[] {domain, algorithm}` (fixed path) | Count compared with `pqc_detected[].domains` | No check |
| `identity.domain` | Apex inference only | No inference |
| `snapshot.toggles_at_assessment.pqc_scan` (bool or `{value}`) | `false` → not_assessed; `true` → allows "No PQC detected"; reason printed in "PQC not reported" text | "PQC not reported" wording |
| `snapshot.assessed_at` | "Snapshot <date>" in D.4 | Missing-value text |
| `what_checked`, else `empty_state_source.coverage` | Clear card "What was checked" (`__init__.py:125`) | Generator default (see Hardcoded) (`s11:589-596`) |
| `empty_state_source.text` | Clear card reason when no `state_reason` / `reason_code` (`s11:586-588`) | Generator clear text |
| `state_reason`, `reason_code` | Card reason | Fallbacks per state |

## Hardcoded in the generator

| Text or label (exact) | Where it prints | Notes (e.g. policy override key) |
|---|---|---|
| "PQC detected (unit not confirmed by source)" | KPI label of `pqc_detected` with `_inferred` unit | `s11:322` |
| "High, Moderate and Low are the source headline: the main domain total, as scored in the product." | Note lead (headline known) | `s11:334-335` |
| "High, Moderate and Low are the source headline. They equal the number of scope × algorithm rows in the scope breakdown at each level (<n> rows, each counted once at its highest level; every row is listed <below \| in Appendix D.4>)." — "below" at tier T1 (no D.4 register) | Note | `s11:340-343` |
| " The <apex label> row for <apex> gives the same High, Moderate and Low findings." / " The headline is not the <apex label> row for <apex>, which sums to <HML> findings." | Appended to the note above | `s11:344-349` |
| "The <apex label> row for <apex> matches it and covers the main domain and <n> subdomains (<n+1> scopes)." / "… covers the main domain only (1 scope); no subdomain rows are listed" | Note | `s11:352-354` |
| "The <apex label> row for <apex> in the scope register sums to <HML>, which differs from the headline; not explained by the source data." | Note | `s11:358-360` |
| "No apex aggregate row is recorded." | Note | `s11:362` |
| " The subdomain rows sum to <HML>; they are not added to the headline." | Appended when subdomains exist | `s11:337` |
| "Subdomain rows exceed the apex aggregate that covers them (<Level> <c> vs <a>, …); not explained by the source data." | Note + D.4 end line | `s11:90-93` |
| "Findings by category total <x>; High + Moderate + Low total <y> (difference <±z>)." | Note | `s11:368-369` |
| "Source notice: " | Prefix of `beta_notice_source` | `s11:371` |
| `<HML>` = "High <n> · Moderate <n> · Low <n>" ("not available" for null) | Everywhere counts are quoted | `s11:67-70` |
| "Findings by algorithm"; columns "#", "Risk", "Category", "Algorithm", "Findings", "Protocols", "PQC alternative" | Section 11 | `s11:396, 409` |
| "Each algorithm counts findings across all scanned scopes. High risk marks key exchange that a quantum computer could break; a PQC alternative is the replacement the source names." | Intro (rated) | `s11:405-406` |
| "Each algorithm counts findings across all scanned scopes; the source prints no risk level per algorithm. A PQC alternative is the replacement the source names." | Intro (not rated) | `s11:407-408` |
| "<n> findings in category" | Category cell sub-line | `s11:383` |
| "Not listed", "Not available", "Not recorded", "Category not recorded", "Protocol not recorded", "Algorithm not recorded" | Empty cells | `s11:37, 180, 389-391, 420, 469-473` |
| "Post-quantum cryptography detected" | H2 when `pqc_detected` has entries | `s11:464` |
| "Detected on <n> of <N> scope(s). Support for PQC does not prove that every connection uses it." / no register rows: "Detected on <n> domain(s). …" | Per PQC block | `s11:425-430` |
| "The source names <n> <alg> domains but the scope register holds <N> scopes; not explained by the source data." | Note (only when the register has rows) | `s11:442-444` |
| "PQC domain register lists <n> domains for <alg>; this section lists <m>." | Note | `s11:447-448` |
| "No <alg \| PQC> observed on <k> of <N> scopes" + mono list | After PQC blocks | `s11:451-454` |
| "Post-quantum cryptography" + "No post-quantum cryptography was detected on the one scope in the register." / "… on any of the <N> scopes." | No `pqc_detected`, PQC reported | `s11:457-458` |
| "PQC not reported: the assessment data lists no post-quantum detection and does not record whether the PQC scan ran (<reason \| scan setting not recorded>). This is not a finding that PQC is absent." | No `pqc_detected`, PQC not reported | `s11:460-462` |
| "<alg> detected" / "No PQC detected" / "PQC not reported" | PQC chips (breakdown, D.4) | `s11:159-167` |
| "Affected protocols"; columns "#", "Risk", "Protocol", "Algorithms", "PQC" | Section 11 | `s11:482-483` |
| "Risk after PQC coverage"; columns "#", "Risk", "Scope", "Algorithm", "Counts", "Source explanation" | Section 11 | `s11:507-512` |
| "<n> scope row(s) carries/carry a risk explanation in the source. The High, Moderate and Low counts stay as reported; the Risk column is the source's assessment after PQC coverage." | Intro | `s11:508-509` |
| "Post-QC: <alg \| Not listed>" | Algorithm cell sub-line | `s11:495` |
| Counts cell "High <n><br>Moderate <n><br>Low <n>" ("not available" for a missing count) | "Risk after PQC coverage" | `s11:497-498`; column wide enough for the longest line (`s11:502-504`) |
| "<n> row(s) prints/print a Risk level that differs from the column holding the count; both are shown as printed." | Note | `s11:514-515` |
| "Scope breakdown"; register columns "#", "Category", "Algorithm (pre-QC)", "Post-QC", High/Moderate/Low sirens, "Source" | T1 inline and D.4.2 | `s11:217-218` |
| "  ·  apex aggregate" / "main domain total (inferred)", " (headline scope)", "  ·  <A, B> not observed" | Apex / group label rows | `s11:144, 149, 224-225` |
| "A1", "A2", … | Apex row numbers (inline T1 only) | `s11:231` |
| `POST_QC_NOTE`: "Post-QC “Not listed”: the source prints a dash, so no post-quantum replacement is listed for that algorithm; the source does not say whether one was checked." | After T1 table and D.4.2 | `s11:38-39` |
| "<G> subdomains in <K> groups with identical counts, PQC status and algorithms, ordered by High, then Moderate, then Low findings. Appendix D.4 lists one row per subdomain and every scope × algorithm row (<N>)." | T2 overview intro | `s11:545-547` |
| Columns "Subdomains", sirens, "PQC", "Algorithms vs main domain"; cell "<n> subdomains"; "Same as main domain" (only when an apex row exists; else empty); "No <alg>" / "+<alg>" | T2 overview | `s11:253, 520, 538-539, 549` |
| "Showing <shown> of <total> subdomains." | T2 note | policy `reconciliation.showing` (`s11:552`) |
| "Main domain total (parent, not added to subdomain rows): High {h} · Moderate {m} · Low {l}." | T2 note | policy `lists.quantum_scope.overview_components[id=apex_aggregate_note].text` replaces it **only** when the headline equals the apex row (`s11:555-557`) |
| "Source: all rows “<x>”." | T1 note after the table (with the Post-QC note) and T2 note, when every row has the same source | `s11:529-531, 559-560` |
| (no note) | T2 note paragraph is omitted when it has no line (no "Showing", no apex, no uniform source) | `s11:561-562` |
| "Full register  D.4 Quantum scope breakdown · <n> scopes · Appendix D, pages a–b" | T2 pointer | title: policy `lists.quantum_scope.register_title`; top N: `lists.quantum_scope.top_n` → `tiers.top_n_default` → 10 (`s11:536, 563-564`) |
| "Scope rows: Not available (not provided in the assessment data)." | No register rows | `s11:607` |
| "Scope and limitations"; H3 from `title` minus a leading "a. ", else "Scope and limitations" / "Post quantum readiness" | Block 10 | `s11:569, 575` |
| "No quantum-vulnerable algorithms were identified within the scope and period of this assessment." | Clear card reason fallback | `s11:586-587` |
| "TLS/SSL configurations and SSH endpoints on <n> scope(s)" (or "… in scope"), "Classical algorithms exposed to future quantum attack (key exchange, public-key, symmetric)", "Post-quantum key exchange support (ML-KEM)" | Clear card "What was checked" when neither `what_checked` nor `empty_state_source.coverage` is sent | `s11:589-596` |
| "The post-quantum (PQC) scan was switched off when this assessment was created, so quantum exposure was not assessed. This is not a result of no findings." | Card reason when `pqc_scan` is false | `s11:57-59` |
| "<reason>. This is not a zero result." / "<reason>. Counts below are lower bounds." | unavailable card / partial banner | `appD:118-121` |
| "Pending review — counts may change before this report is final." | pending_review card without reason | policy `states.overview_messages.pending_review_banner` (`appD:123`) |
| D.4 opening line 1: "D.4.1 lists one row per scope with its post-quantum (PQC) status, ordered by High, then Moderate, then Low findings.[ The main domain total[ (the source headline scope)] comes first; subdomain rows are not added to it.] Showing <S> of <S> scopes. D.4.2 lists every scope × algorithm row (<N> of <N>)." — the apex sentence only when an apex row exists | D.4 | `appD:484-490` |
| D.4 opening line 2: "Unit: scopes (D.4.1) and scope × algorithm rows (D.4.2); counts are findings.[ Source: <all rows “x” \| per row>.] State: <label>. Snapshot <date>." — no "Source:" when no row has a source | D.4 | `appD:486, 491-492` |
| "D.4.1  Scopes", "D.4.2  Scope × algorithm rows"; pivot columns "#", "Subdomain", "PQC", sirens, "Algorithms vs main domain"; apex row "A" + "Reference" | D.4 | `s11:262-269`, `appD:495-497` |
| End line: "End of register · <N> scope × algorithm rows. <S> of <S> scopes shown; 0 not shown (none withheld; all <N> scope × algorithm rows in D.4.2). Totals: over <G> subdomain rows, <x> findings (<HML>) from <C> subdomain × algorithm rows; <apex label>, not added, <HML> — <match> \| no apex row: no main domain total row; the subdomain total <match>[; <N> scope × algorithm rows by level (highest level per row): <HML>][; source count “rows” is <a>, listed <b>][; <exceed text>]." | D.4 | policy `reconciliation.register_end` (`s11:304-314`, `appD:316-323`) |
| `<match>`: "matches the Section 11 headline" (headline = apex totals, or = subdomain totals when there is no apex row) / "differs from the Section 11 headline <HML>, which counts the <N> scope × algorithm rows by level (highest level per row)" / "differs from the Section 11 headline <HML>; not explained by the source data" | D.4 end line | `s11:291-298` |
| Index content: "<S> scopes (one row each) and all <N> scope × algorithm rows"; or a `state_message`: tier T1 "Not required — all <n> scope rows shown in Section 11."; no register rows "Not produced — no register data in the payload." | Appendix D index | `appD:477-480, 502, 601-614` |

## Conditional rules (if / else)

| Condition | What prints | Code |
|---|---|---|
| `pqc_scan` recorded `false`, no quantum results | State forced to `not_assessed` (`pqc_scan_disabled`), card only | `s11:51-59` |
| `pqc_scan` `false` **and** results (`findings_by_category`, `pqc_detected`, `scope_summary`, `affected_protocols`, a non-null metric, or register rows) | Load error, exit 1 | `build.py:135-157` |
| State `clear` | Card + "Scope and limitations" only; no KPIs, tables or register | `s11:601-602` |
| Clear and neither `what_checked` nor `empty_state_source.coverage` | Default 3 bullets; n = `len(scope_summary)` else scopes in the register ("1 scope", "<n> scopes") | `s11:589-596` |
| Clear card reason | `state_reason` / `reason_code` text, else `empty_state_source.text`, else the generator clear text | `s11:586-588`, `appD:115-117` |
| Metric id ends `_risk` with level high/moderate/low | Siren tile, quantum scale | `s11:323-325` |
| Headline = rows-by-level (each row at its highest non-zero level) | "They equal the number of scope × algorithm rows…" note (+ apex same / differs) | `s11:338-350` |
| Else headline = apex row totals | "…matches it and covers …" note | `s11:351-354` |
| Else apex present | "…differs from the headline…" note + QA `data_mismatch` | `s11:355-360` |
| Else register rows, no apex | "No apex aggregate row is recorded." | `s11:361-362` |
| Any subdomain-row level total > apex total | Exceed note + QA `data_mismatch` | `s11:77-87, 363-365` |
| Σ `findings_by_category[].issues` ≠ Σ headline (both known, issues > 0) | Category-total note | `s11:366-369` |
| No `scope_level` key on any row, a row's `subdomain` = `identity.domain`, its sums = headline, and it is not every row | Those rows become the apex, label "main domain total (inferred)", QA `apex_inferred` | `s11:124-130` |
| Headline (all known) = apex row totals | Label suffix " (headline scope)"; policy apex note text allowed | `s11:142-144, 556` |
| No algorithm carries `risk_level` high/moderate/low | Risk column removed; no legend on "Findings by algorithm"; legend moves to "Scope breakdown" | `s11:400-402, 410, 526` |
| `pqc_detected[]` non-empty or `pqc_scan` true | "PQC reported": chip "No PQC detected" for scopes without PQC; no-PQC paragraph says "was detected" | `s11:138, 165, 457` |
| Neither | Chip "PQC not reported"; paragraph "PQC not reported: …" | `s11:167, 460` |
| `pqc_detected` empty and no register rows | No PQC heading at all | `s11:455-464` |
| Register has rows and `domains_count` (or domain count) > scopes in register | Mismatch note | `s11:442-444` |
| `pqc_detected` entries but no register rows | "Detected on <n> domain(s)." — no "of 0 scopes", no mismatch note | `s11:425-427, 442` |
| pqc_domain_register has rows and its count for the algorithm ≠ `len(domains)` | Mismatch note | `s11:445-448` |
| Some scopes have no PQC (and a PQC block printed) | "No … observed on k of N scopes" + list; names the algorithm when only one | `s11:449-454` |
| Domain grid columns | `min(4, CW // widest domain)` | `s11:434` |
| `affected_protocols[].risk_level` not high/moderate/low | "Not recorded" in Risk | `s11:472-473` |
| Register row has `risk_level` whose own count column is 0/missing | "…differs from the column holding the count" note | `s11:506, 513-515` |
| All register rows share one non-null `source` | No Source column; note "Source: all rows “x”." at T1 (after the table) and T2 (policy `lists.quantum_scope.overview_components[id=uniform_source_note]` asks for it at every tier) | `s11:139-140, 152, 218, 529-531, 559-560` |
| No register row has a `source` | `source_note` is empty: no "Source:" in the T2 note or D.4 opening; the Source column stays (missing-value cells) | `s11:153-154, 218`, `appD:486` |
| Tier: visual rows = every register row (each apex row prints as A1…An) + subdomain groups + 1 (apex label row) ≤ 30 → T1; data rows > 1000 → T3; else T2 | T1: full table inline, D.4 index row only. T2/T3: grouped overview + pointer + D.4 (T3 behaves as T2) | `s11:150-151`, `appD:79-83`, policy `tiers.T1_inline.max_visual_rows`, `tiers.T2_overview_register.max_rows` |
| T2: subdomains with equal totals, PQC algorithm and apex-difference | Collapsed into one row "<n> subdomains" | `s11:533-539` |
| T2: more groups than top N | "Showing x of y subdomains." | `s11:551-553` |
| Apex exists vs not (pivot and T2 overview) | "Same as main domain" / differences; no apex → empty cell | `s11:267-268, 538-539` |
| No apex row (D.4) | No apex sentence in the D.4 opening; end line "no main domain total row; the subdomain total <match>" | `appD:484-485`, `s11:291, 312-313` |
| Apex and ≥ 1 group (pivot) | Apex row never ends a page alone | `s11:277-278` |
| A row has no `post_qc_algorithm` | POST_QC_NOTE after the table | `s11:530, appD:498-499` |
| Text column identical in every row | Column collapsed into "<Col>: <value> (all rows)." | `appD:184-190, 287-289` |
| D.4 built only when register rows exist, tier ≠ T1 and state ∈ findings/partial/pending_review | Else index row with `state_message` (row count passed only at T1 with rows, so an inline list never reads "Not produced") | `appD:477-480` |
| Source `counts.rows` / `counts.scopes` ≠ listed | "; source count “rows” is a, listed b" in end line | `s11:299-301` |
| Headline = rows-by-level (not apex) | End-line match text "differs …" and the rows-by-level clause dropped | `s11:293-296` |

## Computed by the generator

| Value | Formula / source fields | Code |
|---|---|---|
| Headline (H, M, L) | `metrics[id in high_risk, moderate_risk, low_risk].value` | `s11:282-284` |
| Rows by level | Each register row counted once at its first non-zero level of high → moderate → low | `s11:109-116` |
| Apex totals / subdomain totals | Σ `high`/`moderate`/`low` over apex rows / non-apex rows; any null → null | `s11:62-64, 135, 147` |
| Group order | Subdomain totals desc (H, M, L), then name | `s11:136` |
| Row order inside a group | `high` desc, `category`, `pre_qc_algorithm` | `s11:228-229` |
| Algorithms vs main domain | Set difference of `pre_qc_algorithm` vs apex set: "No X", "+X" | `s11:248-253` |
| Scopes | Subdomain groups + 1 if apex | `s11:415, appD:482` |
| Algorithm table order | Category by its best-ranked algorithm; algorithms by risk | `s11:376-380` |
| Category / headline differences | Σ issues − Σ headline (signed) | `s11:366-369` |
| Post-QC missing count | Rows without `post_qc_algorithm` | `s11:156` |
| "#" column width | Widest label ("#", the last row number, "A<n>") measured with every digit as the widest Poppins digit, so "20" never splits | `s11:102-106` |
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
| `apex_inferred` | warn | Apex taken from `identity.domain` rows because no row has `scope_level` (`s11:129`) |
| `data_mismatch` | warn | Headline ≠ apex aggregate row and headline ≠ rows-by-level (`s11:356`) |
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
