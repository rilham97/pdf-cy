"""Build data/claude-2026-10-02.json from the old Claude PDF (P2).

usage: python3 -I build_fixture.py <claude.pdf> <tables.json> <out.json>
tables.json comes from parse_tables.py (credential rows already sanitized).
Asserts at the bottom are the regression check (counts + privacy).
"""
import sys, json, re, hashlib, collections
sys.path.insert(0, '/private/tmp/claude-501/-Users-rama-Downloads-Cyberrank-Reference-Pack-2026-10-04/c1a77ec7-4bf4-490d-a6c0-a7596acd8d20/scratchpad/understand/design-template/pylib')
import pymupdf
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[0]))   # tools/extract
from section_layout import restructure  # noqa: E402  (privacy sub-areas -> own sections, item 15)

pdf_path, tables_path, out_path = sys.argv[1:4]
pdf = pymupdf.open(pdf_path)
tables = json.load(open(tables_path))
SHA = hashlib.sha256(open(pdf_path, 'rb').read()).hexdigest()

HEADER_LINES = {"Claude - Cyber Risk Report", "CyberRank", "https://www.cyberrank.ai"}


def page_lines(i):
    """1-based page -> content lines, header/footer removed."""
    out = []
    for ln in pdf[i - 1].get_text().split("\n"):
        s = ln.strip()
        if not s or s in HEADER_LINES or re.match(r"^Generated \d\d\.\d\d\.\d{4} \d+ \| Page$", s):
            continue
        out.append(s)
    return out


def join(lines):
    """Re-flow wrapped lines: no space after '.', '-', '/' when next starts lowercase/digit or with '/'."""
    s = ""
    for ln in lines:
        if not s:
            s = ln
        elif (s[-1] in ".-/" and re.match(r"[a-z0-9]", ln)) or ln.startswith("/"):
            s += ln
        else:
            s += " " + ln
    return re.sub(r"\s+", " ", s).strip()


def between(page_from, page_to, start, end=None, inclusive_start=True):
    lines = [l for p in range(page_from, page_to + 1) for l in page_lines(p)]
    txt = join(lines)
    a = txt.index(start)
    b = txt.index(end, a + len(start)) if end else len(txt)
    return txt[a if inclusive_start else a + len(start):b].strip()


def metric(mid, label, value, unit, state, source_label=None, **kw):
    m = {"id": mid, "label": label, "value": value, "unit": unit, "state": state}
    if source_label is not None:
        m["source_label"] = source_label
    m.update(kw)
    return m


def null_reason(reason_code, note=None, source_label=None, state="unavailable"):
    o = {"value": None, "state": state, "reason_code": reason_code}
    if note:
        o["note"] = note
    if source_label is not None:
        o["source_label"] = source_label
    return o


# ------------------------------------------------------------------ vulnerabilities (p9-14)
vt = join([l for p in range(9, 15) for l in page_lines(p)])
vt = vt[vt.index("<15%") + 4:vt.index("No additional subdomains")]
pat = re.compile(r"^(\S+) (CRITICAL|HIGH|MEDIUM|LOW) (.*) Affected Domains? ?(?:\((\d+)\))?: (.*)$")
chunks = re.split(r"Breach Likelihood: (\d+)%", vt)
findings = []
for n, (chunk, bl) in enumerate(zip(chunks[0::2], chunks[1::2]), 1):
    name, sev, rationale, cnt, doms = pat.match(chunk.strip()).groups()
    domains = [d.strip() for d in doms.split(", ")]
    printed = int(cnt) if cnt else 1
    assert printed == len(domains), (name, printed, len(domains))
    findings.append({
        "finding_id": f"vuln-{n:02d}",
        "finding_type": name,
        "severity": sev.lower(),
        "severity_label_source": sev,
        "rationale_source": rationale,
        "affected_assets_count": printed,
        "affected_assets": domains,
        "breach_likelihood": {"value": int(bl), "unit": "percent", "likelihood_type": "ai_derived_per_finding",
                              "source_label": f"Breach Likelihood: {bl}%"},
    })
assert len(findings) == 17
sev_counts = collections.Counter(f["severity"] for f in findings)

# asset register (asset label -> finding ids), labels verbatim
asset_reg = collections.OrderedDict()
for f in findings:
    for a in f["affected_assets"]:
        asset_reg.setdefault(a, []).append(f["finding_id"])
sev_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
fid_sev = {f["finding_id"]: f["severity"] for f in findings}
vuln_asset_rows = [{
    "asset_label_source": a, "finding_ids": ids, "finding_count": len(ids),
    "max_severity": max((fid_sev[i] for i in ids), key=sev_rank.get),
} for a, ids in asset_reg.items()]

# ------------------------------------------------------------------ credential register (sanitized)
cred_rows = []
for n, r in enumerate(tables["credentials"], 1):
    years = sorted({int(p) for p in r["period"] if p.isdigit()}, reverse=True)
    row = {
        "id": f"cred-{n:04d}",
        "email_domain": r["email_domain"],
        "email_state": {"masked_present": "masked_label_present", "unmasked_present": "unmasked_label_dropped",
                        "unknown_email": "unknown_email"}[r["email_state"]],
        "exposure_period_source": ", ".join(r["period"]),
        "exposure_years": years,
        "exposure_period_has_unknown": "Unknown" in r["period"],
        "exposed_field_categories": r["fields"],
        "breach_source_name": null_reason("not_printed_in_source"),
        "source_page": r["page"],
    }
    if row["email_domain"] is None:
        row.update(email_domain_state="unavailable", email_domain_reason_code="unknown_email_in_source")
    cred_rows.append(row)
year_rows = collections.Counter(y for r in cred_rows for y in r["exposure_years"])
field_rows = collections.Counter(f for r in cred_rows for f in r["exposed_field_categories"])

# ------------------------------------------------------------------ quantum scope register
q_rows = []
for n, r in enumerate(tables["quantum_scope"], 1):
    q_rows.append({
        "id": f"qscope-{n:04d}",
        "subdomain": r["subdomain"],
        "scope_level": "root_aggregate" if r["subdomain"] == "claude.com" else "subdomain",
        "category": r["category"],
        "pre_qc_algorithm": r["pre_qc"],
        "source": r["source"],
        "post_qc_source": r["post_qc"],
        "post_qc_algorithm": None if r["post_qc"] == "—" else r["post_qc"],
        "high": r["high"], "moderate": r["moderate"], "low": r["low"],
        "source_page": r["page"],
    })
    if q_rows[-1]["post_qc_algorithm"] is None:
        q_rows[-1].update(post_qc_algorithm_state="unavailable", post_qc_algorithm_reason_code="dash_in_source")
assert len(q_rows) == 248
root = [r for r in q_rows if r["scope_level"] == "root_aggregate"]
root_tot = tuple(sum(r[k] for r in root) for k in ("high", "moderate", "low"))
assert root_tot == (56, 0, 192), root_tot
subs = collections.OrderedDict()
for r in q_rows:
    subs.setdefault(r["subdomain"], []).append(r)
q_sub_summary = [{
    "subdomain": s,
    "scope_level": rs[0]["scope_level"],
    "rows": len(rs),
    "high": sum(r["high"] for r in rs), "moderate": sum(r["moderate"] for r in rs), "low": sum(r["low"] for r in rs),
    "ml_kem_on_key_exchange": any(r["post_qc_algorithm"] == "ML-KEM" for r in rs),
    "algorithms_absent": sorted({"AES_128", "AES_256", "CHACHA20", "SHA256", "SHA384", "ECDSA", "ECDHE", "RSA",
                                 "CERT_RSA_SIGNATURE"} - {r["pre_qc_algorithm"] for r in rs}),
} for s, rs in subs.items()]
pqc_domains = between(26, 26, "Status: NIST standardized (FIPS 203)", "Scope Breakdown", inclusive_start=False).split()
assert len(pqc_domains) == 25
assert sorted(pqc_domains) == sorted(s["subdomain"] for s in q_sub_summary if s["ml_kem_on_key_exchange"])

# algorithm groups as printed (p25-26) + risk level read from root aggregate row columns
algo_lines = [
    ("Symmetric cryptography", 84, [("AES_128", 28, ["ALL", "TLS_1_2"], False), ("AES_256", 28, ["ALL"], False), ("CHACHA20", 28, ["ALL"], False)]),
    ("Hash functions", 56, [("SHA256", 28, ["ALL", "TLS_1_2", "TLS_1_3"], False), ("SHA384", 28, ["ALL"], False)]),
    ("Public-key cryptography", 80, [("ECDSA", 24, ["ALL", "TLS_1_2"], False), ("ECDHE", 28, ["ALL", "TLS_1_2"], True), ("RSA", 28, ["ALL", "TLS_1_2"], True)]),
    ("Certificate", 28, [("CERT_RSA_SIGNATURE", 28, ["ALL"], False)]),
]
root_by_algo = {r["pre_qc_algorithm"]: r for r in root}
q_groups = []
for cat, issues, algos in algo_lines:
    rows = []
    for a, cnt, protos, mlkem in algos:
        rr = root_by_algo[a]
        assert rr["high"] + rr["moderate"] + rr["low"] == cnt
        level = "high" if rr["high"] else "moderate" if rr["moderate"] else "low"
        rows.append({"algorithm": a, "findings": cnt, "protocol_labels": protos, "pqc_alternative_available": "ML-KEM" if mlkem else None, "risk_level": level})
        if not mlkem:  # source prints no chip; absence is not "no alternative"
            rows[-1].update(pqc_alternative_available_state="unavailable", pqc_alternative_available_reason_code="not_printed_in_source")
    assert sum(r["findings"] for r in rows) == issues
    q_groups.append({"category": cat, "issues": issues, "domains_source_label": "1 domain", "algorithms": rows})

# ------------------------------------------------------------------ rating scale (p42-43) via column words
scale = []
for pno in (42, 43):  # rows = filled cells of the Rating column
    page = pdf[pno - 1]
    words = page.get_text("words")
    cells = sorted({(round(x["rect"].y0), round(x["rect"].y1)) for x in page.get_drawings()
                    if x.get("fill") and x["rect"].x0 < 45 and 30 < x["rect"].width < 70 and x["rect"].height > 20})
    for top, bot in cells:
        inside = [w for w in words if top < (w[1] + w[3]) / 2 < bot]
        grade = [w[4] for w in inside if w[0] < 85 and re.fullmatch(r"AAA|AA|A|BBB|BB|B|CCC|CC|C|D", w[4])]
        if not grade:
            continue  # header row or empty overflow cell
        meaning = sorted([w for w in inside if 85 < w[0] < 360], key=lambda w: (round(w[1]), w[0]))
        mark = sorted([w for w in inside if w[0] >= 360], key=lambda w: w[0])
        scale.append({"grade": grade[0], "meaning_source": " ".join(w[4] for w in meaning), "mark": " ".join(w[4] for w in mark)})
assert [s["grade"] for s in scale] == ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D"], [s["grade"] for s in scale]
POOL360 = {"AAA": [316, 360], "AA": [281, 315], "A": [246, 280], "BBB": [211, 245]}
for s in scale:
    s["pool360_range"] = POOL360.get(s["grade"])
    if s["pool360_range"] is None:
        s["pool360_range_state"] = "unavailable"
        s["pool360_range_reason"] = "range not verified in reference pack (only BBB..AAA observed for Table360)"
    else:
        s["pool360_range_source"] = "reference pack Pengetahuan_dan_Arsitektur_Cyberrank (Table360, observed UI v2), not printed in this PDF"
    s["is_current_grade"] = s["grade"] == "BB"

# ------------------------------------------------------------------ verbatim copy
desc = between(1, 1, "Claude Code is an AI-powered")
band_desc = between(2, 2, "Main information security", "IISRI® Rating Breakdown")
ai_text = between(24, 24, "It is unlikely this organisation")
about = "This report is generated by IISRI® CyberRank.ai using automated, non-intrusive analysis of publicly accessible information. The assessment does not require access to internal systems and should be interpreted as an external risk signal."  # bold span breaks reading order; transcribed from layout text p41
q_limits = {  # p41, transcribed from layout text (list markers break reading order)
    "title": "Our Post-Quantum Safety Scan Results",
    "scope_and_limitations": {
        "title": "a. Scope and limitations",
        "intro": "We cannot guarantee that a domain or organization is fully quantum-safe based on the results of this assessment because:",
        "items": [
            "Post-quantum cryptography is an evolving field. Cryptographic standards, implementations, and the understanding of quantum computing capabilities continue to develop. Future advances may affect the security of algorithms considered secure today.",
            "This is a non-invasive, external assessment. Unless an internal CyberRank agent is deployed, the scan evaluates only externally observable services and configurations. Internal systems, private networks, and services that are not externally accessible are outside the scope of this assessment.",
        ],
    },
    "post_quantum_readiness": {
        "title": "b. Post-quantum readiness",
        "intro": "A domain can only be considered fully post-quantum ready if it:",
        "items": [
            "Supports post-quantum cryptographic (PQC) algorithms for secure connections; and",
            "Disables legacy TLS versions (TLS 1.0, TLS 1.1, and TLS 1.2).",
        ],
        "closing": "Allowing legacy TLS versions enables clients to establish connections using classical cryptographic algorithms. If an attacker can force or negotiate the use of an older protocol version (a protocol downgrade), the connection may lose the protections provided by post-quantum cryptography.",
    },
}

# ------------------------------------------------------------------ JSON
STATE_ENUM = ["findings", "clear", "not_assessed", "not_applicable", "unavailable", "partial", "pending_review"]

report = {
    "meta": {
        "report_schema_version": "cyberrank-report/0.1-draft",
        "fixture_kind": "sample_payload_mapped_from_old_pdf",
        "fixture_note": "Values transcribed from one production PDF (old openhtmltopdf pipeline). Not a backend payload; field names follow Kontrak_Field_Usulan where available.",
        "language": "en",
        "state_enum": STATE_ENUM,
        "source_document": {
            "ref": "P2",
            "file": "02_PDF_Assessment_Valid/Claude/2026-10-02/Claude - Cyber Risk Report.pdf",
            "sha256": SHA,
            "pages": pdf.page_count,
            "pdf_title": pdf.metadata.get("title"),
            "producer": pdf.metadata.get("producer"),
            "creator": pdf.metadata.get("creator"),
            "pdf_created_at": "2026-10-03T01:53:20Z",
            "pdf_modified_at": "2026-09-12T01:10:20Z",
            "template_id": null_reason("not_printed_in_source"),
        },
        "extracted_at": "2026-10-14",
        "sanitisation": {
            "applied": True,
            "rule": "No email local part, full email, personal name, password/token value or personal identifier. Credential rows keep synthetic id, email domain only when equal to assessed organisation domain (else 'external'), exposure period, exposed field categories.",
            "removed_fields": ["credential_register.email_masked"],
            "source_rows_with_unmasked_local_part": sum(1 for r in cred_rows if r["email_state"] == "unmasked_label_dropped"),
            "note": "1 of 29 masked email labels in the source has no masking character in the local part (credential_register email_state 'unmasked_label_dropped'); all local parts are dropped regardless.",
        },
    },
    "identity": {
        "organisation_name": "Claude",
        "organisation_id": null_reason("not_printed_in_source"),
        "domain": "claude.com",
        "website_source_label": "claude.com",
        "sector": "Technology / IT",
        "description_source": desc,
        "logo": {"value": None, "state": "unavailable", "reason_code": "asset_not_extracted", "note": "Old PDF p1 shows an organisation logo image; not carried in fixture."},
        "report_title": "Cyber Risk Report",
        "issuer": {"organisation_name": None, "state": "unavailable", "reason_code": "not_printed_in_source",
                   "note": "Assessing (customer) organisation is not named in the old PDF; its preferences (Australia, New Zealand) are printed in section 03."},
    },
    "snapshot": {
        "assessment_id": null_reason("not_printed_in_source"),
        "snapshot_id": null_reason("not_printed_in_source"),
        "assessed_at": {"value": "2026-10-02", "precision": "day", "source_label": "REPORT DATE 02.10.2026"},
        "generated_at": {"value": "2026-10-03", "precision": "day", "source_label": "DATE GENERATED 03.10.2026"},
        "timezone": null_reason("not_printed_in_source", "PDF metadata CreationDate is 2026-10-03T01:53:20Z (UTC offset +00:00); the report's own timezone is not printed."),
        "methodology_version": null_reason("not_printed_in_source", "Methodology brief (p44-45) cites a July 2026 paper; that is not a version id."),
        "active_version": null_reason("not_printed_in_source"),
        "viewed_version": null_reason("not_printed_in_source"),
        "score_context": null_reason("not_printed_in_source", "Personal (preference-adjusted) vs published baseline cannot be told from the PDF."),
        "toggles_at_assessment": {
            "pqc_scan": {"value": None, "state": "unavailable", "reason_code": "toggle_snapshot_not_printed", "note": "Quantum results are present (section 11), so the module ran."},
            "extended_scan": {"value": None, "state": "unavailable", "reason_code": "toggle_snapshot_not_printed"},
        },
        "preferences_at_assessment": {
            "sovereignty_allowed_jurisdictions": ["Australia"],
            "residency_allowed_countries": ["New Zealand"],
            "source_pages": [7, 8],
        },
    },
    "rating": {
        "rating_name": "IISRI® External Rating",
        "grade": "BB",
        "grade_source": "badge image p2 (visual read; not in PDF text layer)",
        "grade_mark": "Sufficient",
        "risk_band": "low",
        "risk_band_label_source": "Low",
        "band_description_source": band_desc,
        "net": null_reason("not_printed_in_source"),
        "pool": null_reason("not_printed_in_source"),
        "grade_table_id": null_reason("not_printed_in_source"),
        "stored_vs_calculated": null_reason("not_printed_in_source"),
        "review_flags": ["RF-10", "RF-11"],
    },
}

S = {}
S["executive_overview"] = {
    "number": "01", "title": "Executive overview", "group": "overview_and_priorities",
    "state": "partial",
    "state_label_source": None,
    "reason_code": "score_context_incomplete",
    "state_reason": "Grade, risk band, aspect scores and benchmark are printed; net score, pool, score context and assessment id are not.",
    "source_pages": [1, 2, 3, 5],
    "summary": "Claude (claude.com) holds an IISRI external rating of BB with a Low risk band on the 2 October 2026 assessment. Findings are concentrated in vulnerabilities, credential exposure, data sovereignty and residency, and quantum key exchange.",
    "scope_and_coverage": {
        "primary_domain": "claude.com",
        "observed_targets": [
            metric("hosts_observed_residency", "Hosts observed for residency", 29, "hosts", "findings", "United States of America (28 hosts), 1 host with unknown location", count_kind="observed", section="privacy"),
            metric("vuln_asset_labels", "Distinct asset labels in vulnerability findings", len(vuln_asset_rows), "asset_labels", "findings", None, count_kind="distinct_labels_as_printed", section="vulnerabilities", note="Labels as printed; 3 are truncated hostnames (RF-08)."),
            metric("ips_checked", "IP addresses checked for reputation", 2, "ip_addresses", "pending_review", "Checked 2 IP(s) against threat intelligence feeds.", section="vulnerabilities"),
            metric("quantum_scopes", "Scopes in quantum scope breakdown", len(q_sub_summary), "scopes", "findings", None, count_kind="root_aggregate_plus_subdomains", section="quantum_security", note="1 root aggregate (claude.com) + 27 subdomains."),
        ],
        "eligible_targets": null_reason("not_printed_in_source"),
        "coverage_percent": null_reason("denominator_unavailable"),
        "coverage_statement_source": "No additional subdomains or externally exposed assets were identified during this assessment.",
        "method_statement_source": about,
    },
    "rating_overview": {
        "rating_ref": "rating",
        "aspect_breakdown": [
            {"aspect": "privacy", "section": "privacy", "value": 0, "unit": "percent", "state": "pending_review", "display_label_source": "0%", "summary_label_source": "Privacy policy exists with no active risks identified", "review_flags": ["RF-06"]},
            {"aspect": "vulnerability", "section": "vulnerabilities", "value": 43, "unit": "percent", "state": "findings", "display_label_source": "43%", "summary_label_source": "Security improvements needed urgently"},
            {"aspect": "certification", "section": "certifications", "value": 2, "unit": "certifications_headline", "state": "pending_review", "display_label_source": "2 certifications", "summary_label_source": "2 valid certifications verified",
             "secondary": metric("compliance_score", "Compliance Score", 72, "percent", "pending_review", "Compliance Score: 72% (100% = fully certified)"), "review_flags": ["RF-02"]},
            {"aspect": "data_leak_history", "section": "data_leak_history", "value": 0, "unit": "events", "state": "clear", "display_label_source": "0 leakes", "summary_label_source": "No data breaches detected in public records. Excellent security posture.",
             "secondary": metric("leak_free_score", "Security Score", 100, "percent", "clear", "Security Score: 100% (100% = leak-free)"), "review_flags": ["RF-05", "RF-14"]},
            {"aspect": "credential_leak", "section": "credential_exposure", "value": 40, "unit": "found_headline", "state": "findings", "display_label_source": "40 Found", "summary_label_source": "40 credential leaks detected from 2008-2013-2015-2016-2017-2019-2020-2022-2023-2024-2026", "review_flags": ["RF-03"]},
        ],
        "note": "Aspect values use different units and denominators; never average them or compare with the 360-point grade.",
    },
    "sector_comparison": {
        "sector": "Technology / IT",
        "intro_source": "See how your security posture compares to sector peers",
        "metrics": [
            metric("your_score", "Your Score", 53, "points", "findings", "Your Score 53/100", denominator=100),
            metric("sector_average", "Sector Average", 47, "points", "findings", "Industry Average 47/100", denominator=100),
            metric("sector_top_10_percent", "Sector Top 10%", 82, "points", "findings", "Industry Top 10% 82/100", denominator=100),
        ],
        "performance_gap": null_reason("not_printed_in_source"),
        "cohort": {"cohort_id": None, "cohort_size": None, "period": None, "percentile_method": None, "state": "unavailable", "reason_code": "not_printed_in_source"},
        "note": "Your score (out of 100) is not the 360-point IISRI score; no forecast or percentile may be derived.",
    },
}

S["priority_actions"] = {
    "number": "02", "title": "Priority actions", "group": "overview_and_priorities",
    "state": "findings", "state_label_source": "Priority Action Items",
    "source_pages": [6],
    "intro_source": "Recommended actions to improve your IISRI rating, ordered by severity and priority",
    "actions": [
        {"action_id": "act-01", "rank": 1, "priority": "high", "priority_label_source": "HIGH PRIORITY",
         "title": "Reset Compromised Credentials", "estimated_time_reported": "1 week", "required_role": "IT Security team",
         "owner": null_reason("not_assigned"), "due_at": null_reason("not_assigned"), "status": null_reason("not_tracked"),
         "action_required_source": "Force password reset for 40 affected accounts. Enable multi-factor authentication (MFA) for all users.",
         "why_this_matters_source": "Leaked credentials could allow unauthorized access to your systems.",
         "linked_sections": ["credential_exposure"], "linked_finding_ids": [], "review_flags": ["RF-03"]},
        {"action_id": "act-02", "rank": 2, "priority": "medium", "priority_label_source": "MEDIUM PRIORITY",
         "title": "Enhance DMARC Policy to \"Quarantine\"", "estimated_time_reported": "1 week", "required_role": "Email admin",
         "owner": null_reason("not_assigned"), "due_at": null_reason("not_assigned"), "status": null_reason("not_tracked"),
         "action_required_source": "Upgrade DMARC policy from monitoring (p=none) to quarantine (p=quarantine) to actively protect against email spoofing.",
         "why_this_matters_source": "Prevents attackers from impersonating your domain in phishing attacks.",
         "linked_sections": ["vulnerabilities"], "linked_finding_ids": ["ctrl-dmarc"], "review_flags": ["RF-01"]},
    ],
    "note": "Rank is source order, not a stable id. Estimated time is not a due date; required role is not an assigned owner.",
}

S["privacy"] = {
    "number": "03", "title": "Privacy", "group": "assessment_details",
    "state": "pending_review", "state_label_source": "0% PRIVACY SCORE",
    "reason_code": "policy_state_ambiguous",
    "state_reason": "Score 0% printed with 1 policy found, 0 active issues and the label 'Privacy policy exists with no active risks identified'; policy_state (valid / claimed-missing / excluded) is not in the source.",
    "source_pages": [7, 8],
    "old_section_label": "SECTION 1 OF 8 · PRIVACY",
    "intro_source": "Evaluates privacy posture through publicly available data, privacy policies, technical implementations, and compliance with global standards including GDPR and PPDL.",
    "summary": "One privacy policy was found but its 0% score cannot be interpreted without the policy state.",
    "policy": {
        "state": "pending_review", "state_label_source": "0% Privacy Score",
        "policy_state": null_reason("not_printed_in_source", "One of: valid_assessed | claimed_missing | excluded_no_policy (Q04)."),
        "policy_source": null_reason("not_printed_in_source"),
        "metrics": [
            metric("privacy_score", "Privacy Score", 0, "percent", "pending_review", "0%"),
            metric("active_issues", "Active Issues", 0, "issues", "pending_review", "0", count_kind="reported"),
            metric("policies_found", "Policies Found", 1, "policies", "findings", "1", count_kind="reported"),
        ],
        "areas": null_reason("not_printed_in_source", "Per-area A-P scores not printed; do not split the total across areas."),
        "review_flags": ["RF-06"],
    },
    "terms_conditions": {
        "state": "not_applicable", "state_label_source": "Not detected",
        "summary": "No customer login or payment portal was found on the public site.",   # section summary (split from privacy)
        "subtitle_source": "Login / payment portal customer-protection clauses",
        "portal_detected": False,
        "rows": [{"label": "Login / Payment Portal", "value_source": "Not detected"}],
        "narrative_source": "No customer login or payment portal was found on the public site, so published terms are not required to cover that kind of access.",
    },
    "sovereignty": {
        "state": "findings", "state_label_source": "Not identified in published policies",
        "summary": "Governing law could not be identified against the accepted jurisdiction.",   # section summary (split from privacy)
        "subtitle_source": "Where this supplier says disputes and legal obligations are handled",
        "enabled": True,
        "observed_jurisdiction": null_reason("not_identified", source_label="Not identified in published policies"),
        "allowed_set": ["Australia"],
        "match_state": "unknown",
        "rows": [{"label": "Governing law / courts we found", "value_source": "Not identified in published policies"},
                 {"label": "Jurisdictions you accept", "value_source": "Australia"}],
        "narrative_source": "We could not identify a governing-law or court clause in the supplier's published policies, and that does not match the jurisdictions your organisation accepts (Australia). Until that is clear, treat legal location as unresolved.",
    },
    "residency": {
        "state": "findings", "state_label_source": "United States of America (28 hosts), 1 host with unknown location",
        "summary": "Observed hosting is outside the preferred country.",   # section summary (split from privacy)
        "subtitle_source": "Where this organisation's public systems are hosted, compared with where you allow data to live",
        "enabled": True,
        "observed_hosting": [
            {"country": "United States of America", "hosts": 28, "evidence_kind": null_reason("not_printed_in_source")},
            {"country": None, "hosts": 1, "state": "unavailable", "reason_code": "location_unknown", "source_label": "1 host with unknown location"},
        ],
        "allowed_set": ["New Zealand"],
        "match_state": "mismatch",
        "rows": [{"label": "Where we found their systems", "value_source": "United States of America (28 hosts), 1 host with unknown location"},
                 {"label": "Countries you prefer", "value_source": "New Zealand"}],
        "narrative_source": "We found public systems hosted in locations that do not match the countries your organisation prefers (New Zealand). Hosts observed: United States of America (28 hosts), 1 host with unknown location. That means customer data may sit outside the places you require.",
        "note": "IP location is not proof of where all customer data is stored.",
    },
    "resourcing": {
        "state": "pending_review", "state_label_source": "We found no public sign of a dedicated security or privacy team.",
        "summary": "No public privacy or security role evidence was detected in the sources checked.",   # section summary (split from privacy)
        "reason_code": "narrative_overclaim_and_provisional_rule",
        "state_reason": "Result is 'no public role evidence detected'. Old PDF framed it as a negative with a causal claim; Current Rule J (provisional) gives no demerit with zero flags; ledger not printed.",
        "subtitle_source": "Whether this organisation publicly staffs security or privacy",
        "privacy_role_evidence": "not_detected",
        "security_role_evidence": "not_detected",
        "narrative_source": "We found no public sign of a dedicated security or privacy team. Without that, incidents are more likely to go unnoticed or unmanaged.",
        "neutral_message": "No public privacy or security role evidence was detected in the sources checked. This does not show whether such staff exist.",
        "review_flags": ["RF-05"],
    },
}

dmarc_flags = ["RF-01"]
S["vulnerabilities"] = {
    "number": "04", "title": "Vulnerabilities", "group": "assessment_details",
    "state": "findings", "state_label_source": "43% VULNERABILITY SCORE",
    "source_pages": [9, 10, 11, 12, 13, 14, 15],
    "old_section_label": "SECTION 2 OF 8 · VULNERABILITY",
    "intro_source": "Covers external security posture including network vulnerabilities, open ports, SSL/TLS configuration, and DNS security controls protecting digital assets.",
    "summary": f"{len(findings)} finding types were reported: {sev_counts['medium']} medium and {sev_counts['low']} low, none critical or high. DKIM is not enabled, DNSSEC is missing or invalid, and the DMARC mode was not printed.",
    "metrics": [
        metric("vulnerability_score", "Vulnerability score", 43, "percent", "findings", "43%"),
        metric("finding_types", "Finding types", len(findings), "finding_types", "findings", None, count_kind="distinct_finding_type"),
        metric("finding_types_critical_high", "Critical/High finding types", sev_counts["critical"] + sev_counts["high"], "finding_types", "clear", None),
        metric("finding_types_medium", "Medium finding types", sev_counts["medium"], "finding_types", "findings", None),
        metric("finding_types_low", "Low finding types", sev_counts["low"], "finding_types", "findings", None),
        metric("asset_memberships", "Finding-asset memberships", sum(f["affected_assets_count"] for f in findings), "memberships", "findings", None, count_kind="membership_not_unique_assets"),
        metric("distinct_asset_labels", "Distinct affected asset labels", len(vuln_asset_rows), "asset_labels", "findings", None, count_kind="distinct_labels_as_printed"),
    ],
    "severity_legend_source": [
        {"severity": "critical_high", "label": "CRITICAL/HIGH", "text": "Serious vulnerabilities requiring immediate attention"},
        {"severity": "medium", "label": "MEDIUM", "text": "Moderate risk issues that should be addressed"},
        {"severity": "low", "label": "LOW", "text": "Minor security concerns with limited impact"},
    ],
    "breach_likelihood_legend_source": "Indicates the estimated probability that this vulnerability could lead to a security breach. >=30% represents high risk, 15-29% represents moderate risk, <15% represents lower risk.",
    "findings": findings,
    "assets_register_ref": "appendices.d_evidence_registers.vulnerability_asset_register",
    "coverage_note_source": "Note: No additional subdomains or externally exposed assets were identified during this assessment.",
    "email_dns_controls": {
        "state": "findings", "state_label_source": "Email & DNS Security Controls",
        "controls": [
            {"finding_id": "ctrl-dkim", "control": "DKIM", "result": "not_enabled", "state": "findings", "status_label_source": "Not Enabled", "line_source": "DKIM: Not Enabled – supports email integrity and sender authenticity.", "key_strength_bits": null_reason("not_printed_in_source")},
            {"finding_id": "ctrl-dmarc", "control": "DMARC", "result": "enabled", "state": "partial", "status_label_source": "Enabled ( mode)", "line_source": "DMARC: Enabled ( mode) – visibility into spoofing attempts is present.",
             "dmarc_policy": null_reason("blank_in_source", "Mode printed empty; p=none in action act-02 is not traceable to this value."), "review_flags": dmarc_flags},
            {"finding_id": "ctrl-dnssec", "control": "DNSSEC", "result": "missing_or_invalid", "state": "findings", "status_label_source": "Missing / Invalid", "line_source": "DNSSEC: Missing / Invalid – authenticates DNS responses and protects against DNS cache poisoning."},
        ],
        "guidance_source": "It is recommended to progressively enforce DMARC policies to reduce phishing and impersonation risks. DKIM RSA keys must be at least 2048 bits; 1024-bit keys are flagged as a LOW finding. DNSSEC should be enabled (DS record + RRSIG + valid chain of trust) to prevent DNS spoofing.",
    },
    "ip_reputation": {
        "state": "pending_review", "state_label_source": "IP Reputation — Clean",
        "reason_code": "sentinel_meaning_unconfirmed",
        "summary_source": "Checked 2 IP(s) against threat intelligence feeds.",
        "ips_checked": 2,
        "rows": [
            {"ip_address": "160.79.104.10", "isp": null_reason("blank_in_source"), "country": null_reason("blank_in_source"), "abuse_score": null_reason("sentinel_meaning_unconfirmed", source_label="-1"), "reports": {"value": 0, "source_label": "0", "state": "pending_review", "reason_code": "sentinel_meaning_unconfirmed"}},
            {"ip_address": "2607:6bc0:0:0:0:0:0:10", "isp": null_reason("blank_in_source"), "country": null_reason("blank_in_source"), "abuse_score": null_reason("sentinel_meaning_unconfirmed", source_label="-1"), "reports": {"value": 0, "source_label": "0", "state": "pending_review", "reason_code": "sentinel_meaning_unconfirmed"}},
        ],
        "review_flags": ["RF-07"],
    },
    "https_redirect": {
        "state": "clear", "state_label_source": "# HTTPS Redirect — Secure",
        "result": "redirects_to_https",
        "narrative_source": "HTTP correctly redirects to HTTPS. No insecure patterns detected.",
        "review_flags": ["RF-14"],
    },
    "review_flags": ["RF-08"],
}

certs = []
for n, (std, full) in enumerate([("ISO/IEC 27001", "Information Security Management"), ("SOC 2", "Service Organization Controls"), ("ISO/IEC 42001", "AI management systems")], 1):
    certs.append({
        "certificate_id": f"cert-{n:02d}", "standard": std, "standard_full_name": full,
        "origin": "detected", "origin_label_source": "SYSTEM DETECTED",
        "card_text_source": f"Claude system-detected: {std} ({full})",
        "source_url": "https://support.claude.com/hc/en-us/articles/10015870-what-certifications-has-anthropic-obtained",
        "category": null_reason("not_printed_in_source"),
        "approval_state": null_reason("not_printed_in_source"),
        "valid_from": null_reason("not_printed_in_source"),
        "valid_until": null_reason("not_printed_in_source", "Validity not available; do not show as valid."),
        "eligibility": null_reason("not_printed_in_source"),
        "credit_applied": null_reason("not_printed_in_source"),
    })
S["certifications"] = {
    "number": "05", "title": "Certifications", "group": "assessment_details",
    "state": "pending_review", "state_label_source": "72% COMPLIANCE SCORE",
    "reason_code": "count_unreconciled",
    "state_reason": "Headline prints 2 certifications ('2 valid certifications verified') while 3 detected cards are listed; approval status and validity are not printed.",
    "source_pages": [3, 16, 17],
    "old_section_label": "SECTION 3 OF 8 · CERTIFICATION",
    "intro_source": "Outlines industry certifications and compliance frameworks held by the organization, providing independent validation of security and privacy controls.",
    "summary": "Three certifications were detected on the organisation's public support site: ISO/IEC 27001, SOC 2 and ISO/IEC 42001. Approval status and validity were not reported.",
    "metrics": [
        metric("compliance_score", "Compliance score", 72, "percent", "pending_review", "72%"),
        metric("certifications_headline", "Certifications (headline)", 2, "certifications", "pending_review", "2 certifications", count_kind="reported_headline"),
        metric("certificates_detected", "Detected certificate cards", 3, "certificates", "findings", None, count_kind="cards_listed"),
        metric("certificates_approved", "Approved certificates", None, "certificates", "unavailable", None, reason_code="not_printed_in_source"),
    ],
    "certificates": certs,
    "reference_standards": {
        "is_vendor_evidence": False,
        "title_source": "Commonly Referenced Standards",
        "items": [
            {"standard": "ISO/IEC 27001", "description": "Information Security Management"},
            {"standard": "ISO/IEC 27701", "description": "Privacy Information Management"},
            {"standard": "SOC 2", "description": "Security, Availability, Confidentiality"},
            {"standard": "GDPR", "description": "Data protection and privacy regulation"},
        ],
    },
    "review_flags": ["RF-02"],
}

S["data_leak_history"] = {
    "number": "06", "title": "Data breach and leak history", "group": "assessment_details",
    "state": "clear", "state_label_source": "No Data Leaks Identified",
    "source_pages": [3, 18],
    "old_section_label": "SECTION 4 OF 8 · DATA LEAK HISTORY",
    "intro_source": "Documents publicly known data leak incidents. Historical data leaks are factored into the IISRI® score, with recency and severity both affecting the overall rating.",
    "summary": "No data leak events were found in the sources and period checked.",
    "metrics": [
        metric("data_leak_score", "Data leak score", 100, "percent", "clear", "100%"),
        metric("events_reported", "Leak events", 0, "events", "clear", "0 leakes", count_kind="reported"),
    ],
    "last_valid_event": null_reason("no_events", "No event to show.", state="not_applicable"),
    "events": [],
    "empty_state_source": {"title": "No Data Leaks Identified", "text": "No confirmed data leak events were associated with this organization during the assessed period.",
                           "coverage": "This assessment is based on automated analysis of data leak databases, public disclosures, and monitored online sources."},
    "review_flags": ["RF-05", "RF-14"],
}

S["fourth_party_vendors"] = {
    "number": "07", "title": "Fourth-party vendors", "group": "assessment_details",
    "state": "clear", "state_label_source": "No Fourth-Party Vendors Identified",
    "source_pages": [19],
    "old_section_label": "SECTION 5 OF 8 · FOURTH PARTIES",
    "intro_source": "Identifies fourth-party vendors — the suppliers and service providers used by this vendor — representing extended supply chain risk. Each vendor is assessed for security posture and compliance.",
    "summary": "No fourth-party vendors were discovered with the methods used. This does not show that the organisation has no suppliers.",
    "metrics": [metric("fourth_parties", "Fourth-party vendors", 0, "organisations", "clear", "No Fourth-Party Vendors Identified", count_kind="reported")],
    "vendors": [],
    "empty_state_source": {"title": "No Fourth-Party Vendors Identified", "text": "No fourth-party vendors have been discovered for this organization during the assessed period.",
                           "coverage": "This assessment is based on automated technology discovery and vendor relationship analysis."},
}

years_sorted = sorted(year_rows, reverse=True)
S["credential_exposure"] = {
    "number": "08", "title": "Credential exposure", "group": "assessment_details",
    "state": "findings", "state_label_source": "40% CREDENTIAL SCORE",
    "source_pages": [3, 20, 21, 22],
    "old_section_label": "SECTION 6 OF 8 · CREDENTIAL LEAK",
    "intro_source": "Identifies credential leaks associated with the organization’s domains found in known data breaches. Exposed credentials represent a direct risk of unauthorized account access.",
    "summary": f"The source reports 40 credential exposures (headline) and lists {len(cred_rows)} register rows spanning 2008 to 2026, {sum(1 for r in cred_rows if 'password' in r['exposed_field_categories'])} of which include a password field category. The number of unique or active accounts is not known.",
    "attention_source": "Attention: Historical credential exposures were identified. Password resets and MFA enforcement are recommended.",
    "metrics": [
        metric("credential_score", "Credential score", 40, "percent", "findings", "40%"),
        metric("found_headline", "Found (headline)", 40, "records_unit_unverified", "findings", "40 Found", count_kind="reported_headline", note="Unit not defined in source; not unique accounts."),
        metric("returned_rows", "Register rows shown", len(cred_rows), "rows", "findings", None, count_kind="returned_rows"),
        metric("rows_org_domain", "Rows with organisation email domain", sum(1 for r in cred_rows if r["email_domain"] == "claude.com"), "rows", "findings", None),
        metric("rows_external_domain", "Rows with external email domain", sum(1 for r in cred_rows if r["email_domain"] == "external"), "rows", "clear", None),
        metric("rows_unknown_email", "Rows with Unknown Email", sum(1 for r in cred_rows if r["email_state"] == "unknown_email"), "rows", "findings", "Unknown Email"),
        metric("rows_with_password", "Rows exposing a password field", sum(1 for r in cred_rows if "password" in r["exposed_field_categories"]), "rows", "findings", None),
        metric("rows_period_unknown", "Rows with an Unknown exposure period", sum(1 for r in cred_rows if r["exposure_period_has_unknown"]), "rows", "findings", "Unknown"),
        metric("unique_accounts", "Unique accounts", None, "accounts", "unavailable", None, reason_code="not_derivable", note="Masked labels are not a dedup key."),
    ],
    "exposure_years_source": "2008-2013-2015-2016-2017-2019-2020-2022-2023-2024-2026",
    "rows_by_exposure_year": [{"year": y, "rows": year_rows[y]} for y in years_sorted],
    "rows_by_field_category": [{"field_category": f, "rows": c} for f, c in sorted(field_rows.items(), key=lambda kv: (-kv[1], kv[0]))],
    "aggregation_note": "Year and field counts are row memberships; a row can list several years or fields, so they do not sum to the row total.",
    "breach_source_name": null_reason("not_printed_in_source"),
    "register_ref": "appendices.d_evidence_registers.credential_register",
    "mitigations_source": [
        "Force password resets for all affected accounts",
        "Enable multi-factor authentication across all user access points",
        "Review password hygiene and access policies",
        "Monitor authentication logs for anomalous activity",
    ],
    "review_flags": ["RF-03"],
}

S["cloud_infrastructure"] = {
    "number": "09", "title": "Cloud infrastructure", "group": "assessment_details",
    "state": "findings", "state_label_source": "1 Cloud Providers Detected",
    "source_pages": [23],
    "old_section_label": "SECTION 7 OF 8 · CLOUD INFRASTRUCTURE",
    "intro_source": "Identifies cloud service providers used by the organization through analysis of DNS records, IP ranges, MX records, and NS records. Cloud infrastructure detection reveals the hosting and service provider footprint of the assessed organization.",
    "summary": "One cloud provider, Cloudflare, was detected. Detection shows provider use, not where all customer data is stored.",
    "lead_source": "1 cloud provider(s) have been identified through automated infrastructure analysis.",
    "metrics": [metric("cloud_providers_detected", "Cloud providers detected", 1, "providers", "findings", "1")],
    "detection_methods": ["dns_records", "ip_ranges", "mx_records", "ns_records"],
    "providers": [{"provider": "Cloudflare", "detection_methods": null_reason("not_printed_in_source"), "observed_at": null_reason("not_printed_in_source")}],
    "last_scanned": {"value": "2026-10-02", "precision": "day", "source_label": "Last scanned: 02.10.2026"},
    "note": "Section-level detection_methods come from intro_source (the module description). Per-provider detection method and observed_at are not printed.",
}

S["ai_risk_governance"] = {
    "number": "10", "title": "AI risk and governance", "group": "assessment_details",
    "state": "not_assessed", "state_label_source": "NOT ASSESSED",
    "reason_code": "module_not_assessed",
    "source_pages": [24],
    "old_section_label": "AI RISK & GOVERNANCE · NOT ASSESSED",
    "title_source": "AI Usage & Risk Classification",
    "intro_source": "What we observed about this organisation's use of artificial intelligence, and what that means for customers and the people they serve.",
    "summary": "AI risk was not assessed for this report. The observations below are recorded for context only and are not an assessment result.",
    "narrative_observation": {
        "is_assessment_result": False,
        "subtitle_source": "What we observed about this organisation's use of artificial intelligence",
        "text_source": ai_text,
        "signals_observed": [
            {"signal": "ai_infrastructure", "method": "csp_header_analysis", "example_source": "CSP destination: api.anthropic.com"},
            {"signal": "ai_hiring", "method": "careers_pages", "example_source": "public careers or hiring pages advertise AI-related roles"},
            {"signal": "ai_assistant_mention", "method": "public_pages", "example_source": "public pages mention ai assistant, observed on claude.com"},
        ],
        "stated_conclusion_source": "It is unlikely this organisation uses AI in a material way.",
        "annex_iii_high_risk_sector": {"value": "not_apparent", "state": "not_assessed", "reason_code": "module_not_assessed", "source_label": "They do not appear to fall into an EU Annex III high-risk sector."},
        "public_ai_policy": {"value": "not_found", "state": "not_assessed", "reason_code": "module_not_assessed", "source_label": "We could not find a public AI policy explaining how they use or govern AI."},
        "privacy_policy_ai_disclosure": {"value": "not_clear", "state": "not_assessed", "reason_code": "module_not_assessed", "source_label": "Their privacy policy does not clearly explain AI use to the people whose data may be involved."},
    },
    "metrics": [metric("ai_issues", "AI issues", None, "issues", "not_assessed", "NOT ASSESSED", reason_code="module_not_assessed")],
    "review_flags": ["RF-04"],
}

S["quantum_security"] = {
    "number": "11", "title": "Quantum security", "group": "assessment_details",
    "state": "findings", "state_label_source": "Quantum Security Overview",
    "source_pages": list(range(25, 42)),
    "old_section_label": "SECTION 8 OF 8 · QUANTUM SECURITY",
    "intro_source": "Assesses exposure to quantum computing threats by analyzing cryptographic primitives found in TLS/SSL configurations and SSH endpoints. Includes detection of post-quantum cryptography (PQC) algorithms that may already provide protection.",
    "summary": "Across 28 scopes the scan reported 56 high-risk and 192 low-risk findings. High risk comes from ECDHE and RSA key exchange; ML-KEM was detected on 25 of the 28 scopes. Supporting PQC does not prove every connection uses it.",
    "beta_notice_source": "Quantum Vulnerability is currently in beta. You may encounter incomplete data or ongoing changes as we refine the experience.",
    "metrics": [
        metric("high_risk", "High Risk", 56, "findings", "findings", "56", count_kind="root_aggregate"),
        metric("moderate_risk", "Moderate Risk", 0, "findings", "clear", "0", count_kind="root_aggregate"),
        metric("low_risk", "Low Risk", 192, "findings", "findings", "192", count_kind="root_aggregate"),
        metric("pqc_detected", "PQC Detected", 25, "scopes_inferred", "findings", "25", count_kind="reported", note="Unit not labelled in source; equals the 25 ML-KEM domain chips."),
    ],
    "findings_by_category": q_groups,
    "pqc_detected": [{
        "algorithm": "ML-KEM", "algorithm_alias": "CRYSTALS-Kyber", "purpose": "Key exchange / encryption",
        "status_source": "Status: NIST standardized (FIPS 203)", "domains_count": len(pqc_domains), "domains": pqc_domains,
    }],
    "scope_summary": q_sub_summary,
    "scope_register_ref": "appendices.d_evidence_registers.quantum_scope_register",
    "aggregation_note": "Row claude.com is a root aggregate (each count = root + 27 subdomains). Never add the root row to subdomain rows.",
    "scope_and_limitations_source": q_limits,
    "review_flags": ["RF-09", "RF-12"],
}

report["sections"] = S

report["appendices"] = {
    "a_about": {
        "letter": "A", "title": "About this report", "source_pages": [41, 43],
        "about_source": about,
        "closing_source": "Report generated on 03.10.2026",
        "data_sources_source": [
            "automated analysis of data leak databases, public disclosures, and monitored online sources",
            "automated technology discovery and vendor relationship analysis",
            "analysis of DNS records, IP ranges, MX records, and NS records",
        ],
    },
    "b_rating_scale": {
        "letter": "B", "title": "IISRI rating scale", "source_pages": [42, 43],
        "intro_source": "Reference guide to the standardized rating scale used throughout this report, with descriptions of each grade level and associated risk profile.",
        "rows": scale,
        "old_appendix_label": "Appendix A. IISRI® Rating Scale",
    },
    "c_methodology": {
        "letter": "C", "title": "Methodology and supply-chain aggregation", "source_pages": [44, 45],
        "is_generic_material": True,
        "note": "Generic methodology brief appended to the old PDF; values in its diagrams (e.g. Individual risk Low, Combined risk Medium) are illustrative, not Claude results.",
        "headline_source": "One rating for every vendor. One risk number for your whole supply chain.",
        "lead_source": "CYBERRANK turns externally observable evidence about an organisation into a single severity rating, a normalised risk score, and a combined risk that includes the vendors — and the vendors' vendors — behind it.",
        "columns_source": [
            {"title": "The problem", "text": "Attackers reach organisations through their suppliers. Existing tools don't add up: CVSS scores single technical flaws, questionnaires rely on self-reporting, and privacy, AI and quantum exposures have no common scale at all."},
            {"title": "The approach", "text": "An ISO 31000-aligned model with four explicit steps, from observed weaknesses to supply-chain risk. Every step is reproducible and every number is comparable across organisations and portfolios."},
            {"title": "The regulatory fit", "text": "Built for the obligations in DORA, NIS2, the GDPR and the AI Act, and aligned with ISO/IEC 27001, 27701 and 42001, NIST SP 800-53 and 800-161, PCI DSS and the NIST CSF."},
        ],
        "steps_source": [
            {"n": 1, "title": "Observe", "text": "Continuous external signals are collected without touching the organisation's systems.",
             "signals": ["Vulnerabilities", "Privacy compliance", "Credential & data leaks", "Data sovereignty", "Data residency", "Terms of use", "AI", "Quantum"],
             "callout": "Certified controls earn credits: ISO 27001, ISO 27701, SOC 2, ISAE 3402, PCI DSS. Optional questionnaires add a second, bounded evidence channel."},
            {"n": 2, "title": "Rate", "text": "Every organisation starts with a full point budget, split evenly between a security bucket and a privacy bucket. Weaknesses deduct capped demerits; certifications add capped credits.",
             "callout": "The net score maps to the IISRI rating, AAA to D. The rating reflects the organisation's own posture only — a vendor's weakness never changes it."},
            {"n": 3, "title": "Score the risk", "text": "Likelihood = threat probability × weakness. Threat probability comes from sector, size and internet exposure; weakness comes from the rating. Impact is one of four tiers you assign: Critical, High, Medium or Low.",
             "callout": "Risk = normalised likelihood × impact, reported as a score and a band: Low, Medium, High or Critical."},
            {"n": 4, "title": "Combine", "text": "Vendors and sub-vendors are discovered automatically and rated with the same pipeline. Their risks are folded into yours, attenuated by distance in the chain.",
             "callout": "The combined risk shows the cascading exposure that your own rating cannot see."},
        ],
        "scale_caption_source": "Ten grades. Higher grades mean lower weakness values and therefore lower likelihood.",
        "scale_ends_source": {"top": "All controls adequate, appropriate and effective", "bottom": "Controls provide no assurance"},
        "supply_chain": {
            "headline_source": "Your rating describes you. Your combined risk describes your supply chain.",
            "text_source": "Every vendor and sub-vendor is rated with the same pipeline as you are. A weak vendor never lowers your own rating — that stays attributable to your posture. But an exploited vendor can open an attack path into your systems, so the same weakness does enter your combined risk, attenuated by how far away it sits in the chain. The result is two complementary numbers. Read together, they show that an excellent rating does not certify a healthy supply chain.",
            "illustrative_values": {"individual_risk": "Low", "combined_risk": "Medium", "is_illustrative": True},
            "formula_title_source": "Combined risk — the \"at least one adverse event\" composition, applied recursively through the chain",
            "formula": "R(N) = 1 − (1 − o_N) · Π_{s ∈ suppliers(N)} ( 1 − R(s) / (f + d(s))² )",
            "formula_explainer_source": "Every supplier's effective risk R(s) already contains its own suppliers, so the chain unrolls from the outermost leaves inward. Each factor is one party's chance of not causing an incident; one minus the product is the chance that something, somewhere in the chain, goes wrong.",
            "variables": [
                {"symbol": "o_N", "text": "A node's own individual risk score — from its rating, threat probability and impact tier."},
                {"symbol": "R(s)", "text": "A supplier's effective risk, computed the same way from its own suppliers. A leaf with no suppliers has R = o_N."},
                {"symbol": "d(s)", "text": "Hops from the centre: d(s) = d(N) + 1. Each supplier sits one step further out and is damped more."},
                {"symbol": "f", "text": "The transmission fraction you configure. A larger f trusts distance more and shrinks every supplier's contribution."},
                {"symbol": "R(A)", "text": "Your combined risk: the formula evaluated at your own organisation A, the centre of the graph (d = 0)."},
            ],
            "impact_tiers": [
                {"tier": "Critical", "text": "Failure immediately stops a critical service or causes a serious regulatory breach. DORA: critical."},
                {"tier": "High", "text": "Essential, but a temporary loss can be bridged with workarounds. DORA: important."},
                {"tier": "Medium", "text": "Supports normal operations; disruption means inconvenience. The default tier at onboarding."},
                {"tier": "Low", "text": "Minimal or no operational impact."},
            ],
            "reliance_points": [
                {"title": "Standards-grounded", "text": "ISO 31000, ISO/IEC 27001, 27701 and 42001, NIST SP 800-30 and 800-53, DORA and NIS2."},
                {"title": "Certified operator", "text": "an independently audited ISO/IEC 27001 management system; ISO/IEC 42001 certification in progress."},
                {"title": "Human in the loop", "text": "users report inaccuracies and appeal findings; feedback tunes detection confidence over time."},
                {"title": "Honest about limits", "text": "vendor compromises are treated as independent, some detections are heuristic, and the continuous score is primary over the qualitative heat map."},
            ],
            "closing_source": "An organisation's own excellent rating does not certify its supply chain. Only the combined risk does.",
            "dashboard_note_source": "The dashboard shows, for you and every (sub-)vendor, six domains — Security, Privacy, Data leaks, Controls, AI, Quantum — plus the IISRI rating, the individual risk and the combined risk.",
        },
        "copyright_source": "Copyright © 2026 IISRI. All rights reserved. Full methodology paper: \"An Integrated Quantitative Methodology for Third-Party Security, Privacy and AI Risk Rating\", July 2026. Available upon request.",
    },
    "d_evidence_registers": {
        "letter": "D", "title": "Detailed evidence registers", "state": "findings",
        "credential_register": {
            "source_pages": [20, 21], "state": "findings",
            "columns": ["id", "email_domain", "email_state", "exposure_period_source", "exposure_years", "exposure_period_has_unknown", "exposed_field_categories", "breach_source_name", "source_page"],
            "sanitised": True,
            "counts": {"returned_rows": len(cred_rows), "total_rows": null_reason("not_printed_in_source"), "headline_found": 40},
            "rows": cred_rows,
        },
        "quantum_scope_register": {
            "source_pages": list(range(26, 41)), "state": "findings",
            "columns": ["id", "subdomain", "scope_level", "category", "pre_qc_algorithm", "source", "post_qc_source", "post_qc_algorithm", "high", "moderate", "low", "source_page"],
            "counts": {"rows": len(q_rows), "scopes": len(q_sub_summary), "root_aggregate_rows": len(root)},
            "rows": q_rows,
        },
        "vulnerability_asset_register": {
            "source_pages": list(range(9, 15)), "state": "findings",
            "columns": ["asset_label_source", "finding_ids", "finding_count", "max_severity"],
            "counts": {"rows": len(vuln_asset_rows), "memberships": sum(r["finding_count"] for r in vuln_asset_rows)},
            "rows": vuln_asset_rows,
        },
        "pqc_domain_register": {
            "source_pages": [26], "state": "findings",
            "columns": ["domain", "algorithm"],
            "rows": [{"domain": d, "algorithm": "ML-KEM"} for d in pqc_domains],
        },
    },
}

report["review_flags"] = [
    {"id": "RF-01", "pages": [6, 14], "ref": "Peta_Konten issue 1", "text": "Action 2 recommends moving DMARC from p=none, but the DMARC line prints 'Enabled ( mode)' with an empty mode. Show a verification step unless dmarc_policy is known."},
    {"id": "RF-02", "pages": [3, 16, 17], "ref": "Peta_Konten issue 2", "text": "Headline '2 certifications' / '2 valid certifications verified' vs 3 detected cards; approval, validity and verification are not printed, so 'valid verified' overclaims."},
    {"id": "RF-03", "pages": [3, 6, 20, 21], "ref": "Peta_Konten issue 3", "text": "'40 Found' is turned into '40 affected accounts' in action 1; the register shows 30 rows incl. 1 Unknown Email. Unit of 40 is undefined; unique/active accounts unknown."},
    {"id": "RF-04", "pages": [24], "ref": "Peta_Konten issue 5", "text": "AI section is NOT ASSESSED yet lists AI infrastructure, hiring and assistant signals and concludes material use is unlikely. Keep as observation, not result."},
    {"id": "RF-05", "pages": [3, 8], "ref": "Peta_Konten issue 7", "text": "Over-reaching narratives: zero breaches -> 'Excellent security posture'; no public team -> 'incidents are more likely to go unnoticed'. Do not carry into new copy."},
    {"id": "RF-06", "pages": [2, 7], "ref": "Pengetahuan privacy state (Q04)", "text": "Privacy 0% printed with 'Privacy policy exists with no active risks identified', 1 policy found, 0 active issues. Policy state cannot be chosen from the PDF."},
    {"id": "RF-07", "pages": [15], "ref": "Q11", "text": "Abuse score -1 for both IPs alongside 'Clean'; ISP and Country blank. Sentinel meaning unconfirmed."},
    {"id": "RF-08", "pages": [9, 10, 11, 12, 26], "ref": "fixture extraction", "text": "Vulnerability asset lists print hyphenated hostnames cut at the hyphen ('assets', 'eap', 'econ'); section 11 prints assets-staging.claude.com, eap-academy.claude.com, econ-index.mcp.claude.com. Kept verbatim, not reconciled."},
    {"id": "RF-09", "pages": [25, 26], "ref": "Peta_Konten C13", "text": "Category headers say '1 domain' while the scope breakdown has 28 scopes; root claude.com row aggregates root + 27 subdomains."},
    {"id": "RF-10", "pages": [2, 42], "ref": "fixture extraction", "text": "Badge description on p2 ('risks', 'Moderate additional work') differs from the BB meaning in the rating scale ('issues', 'Major additional work')."},
    {"id": "RF-11", "pages": [2], "ref": "R02", "text": "Grade BB exists only inside the badge image; net score, pool, grade table and score context are not printed."},
    {"id": "RF-12", "pages": [25, 26], "ref": "Peta_Konten C13", "text": "'PQC Detected 25' has no unit; it equals the number of ML-KEM domain chips."},
    {"id": "RF-13", "pages": [4], "ref": "Pengetahuan PDF order", "text": "Page 4 is blank (layout overflow from the long description). PDF ModDate 2026-09-12 precedes CreationDate 2026-10-03."},
    {"id": "RF-14", "pages": [3, 15], "ref": "fixture extraction", "text": "Source copy errors kept only in fields ending in _source: '0 leakes', '# HTTPS Redirect — Secure'."},
]

report["sections"] = restructure(report["sections"])
out = json.dumps(report, ensure_ascii=False, indent=2)

# ---------------- regression / privacy checks
assert "@" not in out and "*" not in out, "email material leaked into fixture"
chk = json.loads(out)
assert chk["sections"]["credential_exposure"]["metrics"][2]["value"] == 30
assert sum(1 for r in cred_rows if r["email_state"] == "unknown_email") == 1
assert [r["id"] for r in cred_rows if r["email_state"] == "unmasked_label_dropped"] == ["cred-0029"]
assert all(r["email_domain"] in ("claude.com", "external", None) for r in cred_rows)
assert set(chk["sections"]) == {"executive_overview", "priority_actions", "privacy", "vulnerabilities", "credential_exposure",
                                "data_leak_history", "data_sovereignty", "data_residency", "legal_terms",
                                "ai_risk_governance", "quantum_security", "security_resourcing", "certifications",
                                "fourth_party_vendors", "cloud_infrastructure"}


def walk(o, path=""):
    if isinstance(o, dict):
        if "state" in o and isinstance(o["state"], str):
            assert o["state"] in STATE_ENUM, (path, o["state"])
        for k, v in o.items():
            # any null needs a reason: in its own object (NullReason / row-level state+reason_code),
            # or as <key>_state + <key>_reason_code / <key>_reason siblings
            if v is None:
                assert (o.get("reason_code") or o.get("state") == "not_assessed"
                        or (o.get(k + "_state") and (o.get(k + "_reason_code") or o.get(k + "_reason")))), f"bare null {path}.{k}"
            walk(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            assert v is not None, f"bare null {path}[{i}]"
            walk(v, f"{path}[{i}]")


walk(chk)
open(out_path, "w").write(out + "\n")

print("findings", len(findings), dict(sev_counts))
print("vuln asset labels", len(vuln_asset_rows), "memberships", sum(f["affected_assets_count"] for f in findings))
print("cred rows", len(cred_rows), "years", dict(year_rows))
print("fields", dict(field_rows))
print("quantum rows", len(q_rows), "scopes", len(q_sub_summary), "pqc domains", len(pqc_domains))
print("rating scale rows", len(scale))
print("bytes", len(out))
