"""Build data/instagram-2026-10-02.json from the Instagram production PDF (375 pages, old pipeline).
Adapted from ../build_fixture.py (Claude); same payload shape, plus the conditions Claude lacks
(privacy issues + T&C clauses, sovereignty quote, leak events, 35 fourth parties, 0 certificates).

usage: python3 -I build_fixture.py <instagram.pdf> <tables.json> <claude.json> <out.json>
tables.json comes from parse_tables.py (credential rows already sanitized).
claude.json supplies the static appendix copy (methodology, quantum limits), asserted present in this PDF.
Asserts at the bottom are the regression check (counts + privacy).
"""
import sys, json, re, hashlib, collections
sys.path.insert(0, '/private/tmp/claude-501/-Users-rama-Downloads-Cyberrank-Reference-Pack-2026-10-04/c1a77ec7-4bf4-490d-a6c0-a7596acd8d20/scratchpad/understand/design-template/pylib')
import pymupdf
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))   # tools/extract
from section_layout import restructure  # noqa: E402  (privacy sub-areas -> own sections, item 15)

pdf_path, tables_path, claude_path, out_path = sys.argv[1:5]
pdf = pymupdf.open(pdf_path)
tables = json.load(open(tables_path))
CL = json.load(open(claude_path))
SHA = hashlib.sha256(open(pdf_path, 'rb').read()).hexdigest()
ORG, DOMAIN = "Instagram", "instagram.com"

HEADER_LINES = {"Instagram - Cyber Risk Report", "CyberRank", "https://www.cyberrank.ai"}


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


def text(p_from, p_to):
    return join([l for p in range(p_from, p_to + 1) for l in page_lines(p)])


def between(p_from, p_to, start, end=None, inclusive_start=True):
    txt = text(p_from, p_to)
    a = txt.index(start)
    b = txt.index(end, a + len(start)) if end else len(txt)
    return txt[a if inclusive_start else a + len(start):b].strip()


SQUASH = lambda s: re.sub(r"\s+", "", s)
ALL = SQUASH(" ".join(pdf[i].get_text() for i in range(pdf.page_count)))


def printed(s):
    """Assert a transcribed string is in the PDF (whitespace-insensitive)."""
    assert SQUASH(s) in ALL, s[:80]
    return s


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


def day(dmy, sep="-"):
    d, m, y = dmy.split(sep)
    return f"{y}-{m}-{d}"


# ------------------------------------------------------------------ priority actions (p5-11)
at = text(5, 11)
blocks = re.split(r"(HIGH PRIORITY|MEDIUM PRIORITY|LOW PRIORITY) ", at)[1:]
actions = []
for prio, body in zip(blocks[::2], blocks[1::2]):
    m = re.match(r"(\d+)\. (.+?) (\d+ weeks?) Estimated Time: (.+?) Required: Action Required: ?(.+)$", body.strip())
    rank, title, eta, role, rest = int(m.group(1)), m.group(2), m.group(3), m.group(4), m.group(5)
    why = None
    if rest.endswith("Why This Matters:"):   # reading order: action text, why text, label
        rest = rest[:-len("Why This Matters:")].strip()
        cut = rest.index("users.") + len("users.") if "users." in rest else rest.index("spoofing.") + len("spoofing.")
        rest, why = rest[:cut].strip(), rest[cut:].strip()
    cat = title.lower() if title in ("PRIVACY", "SECURITY") else None
    a = {"action_id": f"act-{rank:02d}", "rank": rank, "priority": prio.split()[0].lower(),
         "priority_label_source": prio, "title": title.capitalize() if cat else title}
    if cat:
        a["title_source"] = title
        a["category"] = cat
    a.update({"estimated_time_reported": eta, "required_role": role,
              "owner": null_reason("not_assigned"), "due_at": null_reason("not_assigned"), "status": null_reason("not_tracked"),
              "action_required_source": rest})
    if why:   # issue-based actions print no 'Why This Matters' text: key omitted (a NullReason here renders as a dict)
        a["why_this_matters_source"] = why
    a["linked_sections"] = ["privacy"] if cat else ["credential_exposure"] if "Credentials" in title else ["vulnerabilities"]
    a["linked_finding_ids"] = [f"issue-{rank:02d}"] if cat else ["ctrl-dmarc"] if "DMARC" in title else []
    a["review_flags"] = ["RF-02"] if "Credentials" in title else ["RF-01"] if "DMARC" in title else []
    actions.append(a)
assert len(actions) == 14 and [a["rank"] for a in actions] == list(range(1, 15))
assert actions[12]["action_required_source"] == "Force password reset for 7179 affected accounts. Enable multi-factor authentication (MFA) for all users."
assert actions[13]["why_this_matters_source"] == "Prevents attackers from impersonating your domain in phishing attacks."

# ------------------------------------------------------------------ privacy issues (p12-15)
it = between(12, 15, "ISSUE 1 ", "Terms & Conditions")
issues = [{"issue_id": f"issue-{int(n):02d}", "label": f"Issue {n}", "category": c.lower(), "category_label_source": c, "text": t.strip()}
          for n, c, t in re.findall(r"ISSUE (\d+) (PRIVACY|SECURITY) (.+?)(?= ISSUE \d+ |$)", it)]
assert len(issues) == 12 and [i["category"] for i in issues].count("security") == 2
for i, a in zip(issues, actions[:12]):   # each issue is repeated as a HIGH priority action
    assert i["text"] == a["action_required_source"] and i["category"] == a["category"], i["label"]

sov_quote = between(16, 16, "From their policy", "Jurisdictions you accept", inclusive_start=False)
assert sov_quote.startswith("No governing law")

# ------------------------------------------------------------------ vulnerabilities (p18-22)
vt = text(18, 22)
vt = vt[vt.index("<15%") + 4:vt.index("No additional subdomains")]
pat = re.compile(r"^(\S+) (CRITICAL|HIGH|MEDIUM|LOW) (.*) Affected Domains? ?(?:\((\d+)\))?: (.*)$")
chunks = re.split(r"Breach Likelihood: (\d+)%", vt)
findings = []
for n, (chunk, bl) in enumerate(zip(chunks[0::2], chunks[1::2]), 1):
    name, sev, rationale, cnt, doms = pat.match(chunk.strip()).groups()
    domains = [d.strip() for d in doms.split(", ")]
    printed_n = int(cnt) if cnt else 1
    assert printed_n == len(domains), (name, printed_n, len(domains))
    findings.append({
        "finding_id": f"vuln-{n:02d}", "finding_type": name, "severity": sev.lower(), "severity_label_source": sev,
        "rationale_source": rationale, "affected_assets_count": printed_n, "affected_assets": domains,
        "breach_likelihood": {"value": int(bl), "unit": "percent", "likelihood_type": "ai_derived_per_finding",
                              "source_label": f"Breach Likelihood: {bl}%"},
    })
assert len(findings) == 14
sev_counts = collections.Counter(f["severity"] for f in findings)
assert dict(sev_counts) == {"high": 2, "medium": 3, "low": 9}, sev_counts

asset_reg = collections.OrderedDict()
for f in findings:
    for a in f["affected_assets"]:
        asset_reg.setdefault(a, []).append(f["finding_id"])
sev_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
fid_sev = {f["finding_id"]: f["severity"] for f in findings}
vuln_asset_rows = [{"asset_label_source": a, "finding_ids": ids, "finding_count": len(ids),
                    "max_severity": max((fid_sev[i] for i in ids), key=sev_rank.get)} for a, ids in asset_reg.items()]
assert [r["asset_label_source"] for r in vuln_asset_rows] == ["instagram.com / 157.240.8.174", "m.instagram.com", "api.instagram.com", "admin.instagram.com"]

# ------------------------------------------------------------------ data leak events (p25-29)
lt = text(25, 29)
HEAD = r"instagram\.com( \(Reported Inaccurate\))? Date: (\d\d-\d\d-\d{4}) Records Affected: ([\d,]+|Unknown) Details: "


def parse_events(txt):
    parts = re.split(HEAD, txt)[1:]
    for inacc, dmy, rec, body in zip(parts[0::4], parts[1::4], parts[2::4], parts[3::4]):
        det, _, src = body.strip().partition(" Source: ")
        yield inacc, dmy, rec, det, src.split(" ")[0] if src else None


lead_txt = lt[lt.index("Last Valid Breach"):lt.index("Historical Breaches")]
hist_txt = lt[lt.index("Historical Breaches"):]
raw_events = [("last_valid", m) for m in parse_events(lead_txt)] + [("historical", m) for m in parse_events(hist_txt)]
events = []
for n, (kind, m) in enumerate(raw_events, 1):
    inacc, dmy, rec, det, src = m
    d, mo, y = dmy.split("-")
    prec = "year" if (d, mo) == ("01", "01") else "month" if d == "01" else "day"
    ev = {"event_id": f"ev-{n:02d}", "entity_link": DOMAIN,
          "entity_label_source": "instagram.com" + (" (Reported Inaccurate)" if inacc else ""),
          "occurred_at": {"value": day(dmy), "precision": prec, "source_label": f"Date: {dmy}"}}
    if prec != "day":
        ev["occurred_at"]["note"] = f"Printed {dmy}; day{'/month' if prec == 'year' else ''} '01' read as a placeholder (RF-08)."
    if inacc:
        ev["validity_state"] = "reported_inaccurate"
        ev["validity_label_source"] = "Reported Inaccurate"
    if kind == "historical":
        ev["scoring_eligible"] = False
        ev["scoring_reason"] = "Listed under Historical Breaches: past breach records for informational purposes, not directly used in current scoring."
    else:
        ev["used_in_rating_label_source"] = "This breach is used in the rating calculation"
    if rec == "Unknown":
        ev["records_affected"] = None
        ev.update(records_affected_state="unavailable", records_affected_reason_code="not_printed_in_source",
                  records_affected_reason="Records affected printed as 'Unknown'.")
    else:
        ev["records_affected"] = int(rec.replace(",", ""))
    ev["records_affected_source"] = rec
    ev["description_source"] = det.strip()
    if src:
        ev["source_url"] = src
    else:
        ev.update(source_url=None, source_url_state="unavailable", source_url_reason_code="not_printed_in_source")
    ev["source_section"] = "last_valid_breach" if kind == "last_valid" else "historical_breaches"
    events.append(ev)
assert len(events) == 9 and len([e for e in events if e.get("validity_state")]) == 3
assert events[0]["occurred_at"]["value"] == "2026-01-07" and events[0]["records_affected"] == 17017213
assert sum(1 for e in events if e["records_affected"] is None) == 1 and sum(1 for e in events if "source_url" in e and e["source_url"] is None) == 1

# ------------------------------------------------------------------ fourth-party vendors (p30-35)
vl = [l for p in range(30, 36) for l in page_lines(p)]
vl = vl[vl.index("35") + 1:]
GR, BD = set("AAA AA A BBB BB B CCC CC C D —".split()), {"Low", "Medium", "High", "Critical", "—"}
starts = [i for i in range(len(vl) - 2) if vl[i + 1] in GR and vl[i + 2] in BD and " " in vl[i]]
vendors, tech_more = [], {}
for k, i in enumerate(starts):
    end = starts[k + 1] if k + 1 < len(starts) else len(vl)
    name, dom = vl[i].rsplit(" ", 1)
    grade, band, prof = vl[i + 1], vl[i + 2], vl[i + 3]
    rest = vl[i + 4:end]
    toks = prof.split(" · ")
    v = {"vendor_id": f"vendor-{k + 1:02d}", "name": name, "domain": dom}
    if grade == "—":
        v.update(grade=None, grade_state="unavailable", grade_reason_code="dash_in_source",
                 grade_reason="No rating printed for this vendor (the source shows '—').",
                 risk_band=None, risk_band_state="unavailable", risk_band_reason_code="dash_in_source",
                 risk_band_label_source="—")
    else:
        v.update(grade=grade, risk_band=band.lower(), risk_band_label_source=band)
    v["category"] = toks[0]
    hq = []
    for t in toks[1:]:
        if re.fullmatch(r"[\d,]+ employees", t):
            v["employees"] = int(t.split()[0].replace(",", ""))
        elif re.fullmatch(r"Founded \d{4}", t):
            v["founded"] = int(t.split()[1])
        elif re.fullmatch(r"[\d.]+[KMB]", t):
            v["revenue_source"] = t
        else:
            hq.append(t)
    assert len(hq) <= 1, (name, hq)
    if hq:
        v["headquarters"] = hq[0]
    tl = [j for j, l in enumerate(rest) if l.startswith("# ")]
    if tl:
        tech = join(rest[tl[0]:])[2:]
        mm = re.match(r"^(.*?)(?: \+(\d+) more)?$", tech)
        sample = [s.strip() for s in mm.group(1).split(", ")]
        v["technologies_count"] = len(sample) + int(mm.group(2) or 0)
        v["technologies_sample_source"] = sample
        if mm.group(2):
            v["technologies_more_source"] = f"+{mm.group(2)} more"
    if rest[:tl[0]] if tl else rest:
        v["description_dropped"] = True    # company blurbs name individuals (founders); not carried (sanitisation)
    v["evidence"] = null_reason("not_printed_in_source", "Discovery method per vendor not printed (section: automated discovery and technology analysis).")
    vendors.append(v)
assert len(vendors) == 35, len(vendors)
rated = [v for v in vendors if v["grade"]]
band_counts = collections.Counter(v["risk_band"] for v in rated)
assert len(rated) == 31 and dict(band_counts) == {"low": 8, "medium": 17, "high": 6}, band_counts
assert next(v for v in vendors if v["name"] == "Amazon")["technologies_more_source"] == "+2000 more"
for v in vendors:
    if v["name"] in ("Carousel", "Fb", "Youtube", "Google", "Amazon"):
        v["review_flags"] = ["RF-13"]

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
    if not r["fields"]:
        row["exposed_fields_blank_in_source"] = True
    if row["email_domain"] is None:
        row.update(email_domain_state="unavailable", email_domain_reason_code="unknown_email_in_source")
    cred_rows.append(row)
year_rows = collections.Counter(y for r in cred_rows for y in r["exposure_years"])
field_rows = collections.Counter(f for r in cred_rows for f in r["exposed_field_categories"])
dom_count = collections.Counter(r["email_domain"] for r in cred_rows)
org_rows = sum(c for d, c in dom_count.items() if d and (d == DOMAIN or d.endswith("." + DOMAIN)))
pw_rows = sum(1 for r in cred_rows if "password" in r["exposed_field_categories"])
unk_rows = sum(1 for r in cred_rows if r["exposure_period_has_unknown"])
blank_rows = sum(1 for r in cred_rows if not r["exposed_field_categories"])
unmasked = sum(1 for r in cred_rows if r["email_state"] == "unmasked_label_dropped")

# ------------------------------------------------------------------ quantum scope register (p368-370)
q_rows = []
for n, r in enumerate(tables["quantum_scope"], 1):
    q_rows.append({
        "id": f"qscope-{n:04d}", "subdomain": r["subdomain"],
        "scope_level": "root_aggregate" if r["subdomain"] == DOMAIN else "subdomain",
        "category": r["category"], "pre_qc_algorithm": r["pre_qc"], "source": r["source"],
        "post_qc_source": r["post_qc"], "post_qc_algorithm": None if r["post_qc"] == "—" else r["post_qc"],
        "high": r["high"], "moderate": r["moderate"], "low": r["low"], "source_page": r["page"],
    })
    if q_rows[-1]["post_qc_algorithm"] is None:
        q_rows[-1].update(post_qc_algorithm_state="unavailable", post_qc_algorithm_reason_code="dash_in_source")
assert len(q_rows) == 36
root = [r for r in q_rows if r["scope_level"] == "root_aggregate"]
root_tot = tuple(sum(r[k] for r in root) for k in ("high", "moderate", "low"))
assert root_tot == (8, 0, 28), root_tot
subs = collections.OrderedDict()
for r in q_rows:
    subs.setdefault(r["subdomain"], []).append(r)
ALGOS = {"AES_128", "AES_256", "CHACHA20", "SHA256", "SHA384", "ECDSA", "ECDHE", "RSA", "CERT_RSA_SIGNATURE"}
q_sub_summary = [{
    "subdomain": s, "scope_level": rs[0]["scope_level"], "rows": len(rs),
    "high": sum(r["high"] for r in rs), "moderate": sum(r["moderate"] for r in rs), "low": sum(r["low"] for r in rs),
    "ml_kem_on_key_exchange": any(r["post_qc_algorithm"] == "ML-KEM" for r in rs),
    "algorithms_absent": sorted(ALGOS - {r["pre_qc_algorithm"] for r in rs}),
} for s, rs in subs.items()]
pqc_domains = between(368, 368, "Status: NIST standardized (FIPS 203)", "Scope Breakdown", inclusive_start=False).split()
assert pqc_domains == ["instagram.com", "admin.instagram.com", "m.instagram.com", "api.instagram.com"]
assert sorted(pqc_domains) == sorted(s["subdomain"] for s in q_sub_summary if s["ml_kem_on_key_exchange"])

qt = text(367, 368)
q_groups = []
for cat, algos in (("Symmetric cryptography", ["AES_128", "AES_256", "CHACHA20"]), ("Hash functions", ["SHA256", "SHA384"]),
                   ("Public-key cryptography", ["ECDSA", "ECDHE", "RSA"]), ("Certificate", ["CERT_RSA_SIGNATURE"])):
    issues_n, doms = re.search(re.escape(cat) + r" (\d+) issues · (\d+ domains?)", qt).groups()
    rows = []
    for a in algos:
        mm = re.search(re.escape(a) + r" — (\d+) findings( ML-KEM available)? \(([^)]+)\)", qt)
        cnt, mlkem, protos = int(mm.group(1)), bool(mm.group(2)), mm.group(3).split(", ")
        rr = next(r for r in root if r["pre_qc_algorithm"] == a)
        assert rr["high"] + rr["moderate"] + rr["low"] == cnt
        row = {"algorithm": a, "findings": cnt, "protocol_labels": protos, "pqc_alternative_available": "ML-KEM" if mlkem else None,
               "risk_level": "high" if rr["high"] else "moderate" if rr["moderate"] else "low"}
        if not mlkem:
            row.update(pqc_alternative_available_state="unavailable", pqc_alternative_available_reason_code="not_printed_in_source")
        rows.append(row)
    assert sum(r["findings"] for r in rows) == int(issues_n)
    q_groups.append({"category": cat, "issues": int(issues_n), "domains_source_label": doms, "algorithms": rows})
assert sum(g["issues"] for g in q_groups) == 36 == 8 + 28

# ------------------------------------------------------------------ rating scale (p372-373)
scale = []
for pno in (372, 373):
    page = pdf[pno - 1]
    words = page.get_text("words")
    cells = sorted({(round(x["rect"].y0), round(x["rect"].y1)) for x in page.get_drawings()
                    if x.get("fill") and x["rect"].x0 < 45 and 30 < x["rect"].width < 70 and x["rect"].height > 20})
    for top, bot in cells:
        inside = [w for w in words if top < (w[1] + w[3]) / 2 < bot]
        grade = [w[4] for w in inside if w[0] < 85 and re.fullmatch(r"AAA|AA|A|BBB|BB|B|CCC|CC|C|D", w[4])]
        if not grade:
            continue
        meaning = sorted([w for w in inside if 85 < w[0] < 360], key=lambda w: (round(w[1]), w[0]))
        mark = sorted([w for w in inside if w[0] >= 360], key=lambda w: w[0])
        scale.append({"grade": grade[0], "meaning_source": " ".join(w[4] for w in meaning), "mark": " ".join(w[4] for w in mark)})
assert [s["grade"] for s in scale] == ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D"], [s["grade"] for s in scale]
assert [s["meaning_source"] for s in scale] == [s["meaning_source"] for s in CL["appendices"]["b_rating_scale"]["rows"]]
POOL360 = {"AAA": [316, 360], "AA": [281, 315], "A": [246, 280], "BBB": [211, 245]}
for s in scale:
    s["pool360_range"] = POOL360.get(s["grade"])
    if s["pool360_range"] is None:
        s["pool360_range_state"] = "unavailable"
        s["pool360_range_reason"] = "range not verified in reference pack (only BBB..AAA observed for Table360)"
    else:
        s["pool360_range_source"] = "reference pack Pengetahuan_dan_Arsitektur_Cyberrank (Table360, observed UI v2), not printed in this PDF"
    s["is_current_grade"] = s["grade"] == "CCC"
assert next(s for s in scale if s["grade"] == "CCC")["mark"] == "Insufficient"

# ------------------------------------------------------------------ verbatim copy
desc = between(1, 1, "Instagram is a major social", "IISRI® External Rating")
band_desc = between(1, 1, "Medium Main information", None, inclusive_start=True)[len("Medium "):]
ai_text = between(366, 366, "It is unlikely this organisation")
about = CL["appendices"]["a_about"]["about_source"]   # bold span breaks reading order: check the pieces
for part in re.split(r" IISRI® CyberRank\.ai | accessible ", about):
    printed(part)
q_limits = CL["sections"]["quantum_security"]["scope_and_limitations_source"]
for s in [q_limits["scope_and_limitations"]["intro"], *q_limits["scope_and_limitations"]["items"],
          q_limits["post_quantum_readiness"]["intro"], *q_limits["post_quantum_readiness"]["items"], q_limits["post_quantum_readiness"]["closing"]]:
    printed(s)
meth = CL["appendices"]["c_methodology"]
for s in [meth["headline_source"], meth["copyright_source"], meth["scale_caption_source"], meth["supply_chain"]["text_source"],
          *[c["text"] for c in meth["columns_source"]], *[x["text"] for x in meth["supply_chain"]["variables"] if "_" not in x["text"]]]:   # subscripts (o_N) differ
    printed(s)
perf_gap = "You are currently 35 points below the industry average. The primary gap is in Privacy (48%). Addressing the 12 active privacy risks will significantly improve your competitive position and raise your score above industry average."
for part in perf_gap.split("The primary "):   # label "Performance Gap:" is interleaved
    printed(part)

# ------------------------------------------------------------------ JSON
STATE_ENUM = ["findings", "clear", "not_assessed", "not_applicable", "unavailable", "partial", "pending_review"]

report = {
    "meta": {
        "report_schema_version": "cyberrank-report/0.1-draft",
        "fixture_kind": "sample_payload_mapped_from_old_pdf",
        "fixture_note": "Values transcribed from one production PDF (old openhtmltopdf pipeline). Not a backend payload; field names follow Kontrak_Field_Usulan where available. Built by tools/extract/instagram/build_fixture.py.",
        "language": "en",
        "state_enum": STATE_ENUM,
        "source_document": {
            "ref": "P-IG",
            "file": "02_PDF_Assessment_Valid/Instagram/2026-10-02/Instagram - Cyber Risk Report.pdf",
            "sha256": SHA,
            "pages": pdf.page_count,
            "pdf_title": pdf.metadata.get("title"),
            "producer": pdf.metadata.get("producer"),
            "creator": pdf.metadata.get("creator"),
            "pdf_created_at": "2026-10-03T01:50:29Z",
            "pdf_modified_at": "2026-09-12T01:10:20Z",
            "template_id": null_reason("not_printed_in_source"),
        },
        "extracted_at": "2026-10-15",
        "sanitisation": {
            "applied": True,
            "rule": "No email local part, full email, personal name, password/token value or personal identifier. Credential rows keep synthetic id, email domain only when equal to the assessed domain or one of its subdomains (else the class 'other_domain'; other domains are never named), exposure period, exposed field categories. Vendor company blurbs (which name founders) are not carried.",
            "removed_fields": ["credential_register.email_masked", "fourth_party_vendors.vendors[].description_source"],
            "source_rows_with_unmasked_local_part": unmasked,
            "note": f"{unmasked} of {len(cred_rows) - 1} email labels in the source have no masking character in the local part (email_state 'unmasked_label_dropped'); all local parts are dropped regardless.",
        },
    },
    "identity": {
        "organisation_name": ORG,
        "organisation_id": null_reason("not_printed_in_source"),
        "domain": DOMAIN,
        "website_source_label": "instagram.com",
        "sector": "Media & Telecom",
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
        "timezone": null_reason("not_printed_in_source", "PDF metadata CreationDate is 2026-10-03T01:50:29Z (UTC offset +00:00); the report's own timezone is not printed."),
        "methodology_version": null_reason("not_printed_in_source", "Methodology brief (p374-375) cites a July 2026 paper; that is not a version id."),
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
            "source_pages": [16],
        },
    },
    "rating": {
        "rating_name": "IISRI® External Rating",
        "grade": "CCC",
        "grade_source": "badge image p1 (visual read; not in PDF text layer)",
        "grade_mark": "Insufficient",
        "risk_band": "medium",
        "risk_band_label_source": "Medium",
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
    "state": "partial", "state_label_source": None,
    "reason_code": "score_context_incomplete",
    "state_reason": "Grade, risk band, aspect scores and benchmark are printed; net score, pool, score context and assessment id are not.",
    "source_pages": [1, 2, 3, 4],
    "summary": "Instagram (instagram.com) holds an IISRI external rating of CCC with a Medium risk band on the 2 October 2026 assessment. Findings span privacy policy issues, vulnerabilities, nine data leak events, credential exposure, fourth-party vendors and quantum key exchange; no certificate was detected.",
    "scope_and_coverage": {
        "primary_domain": DOMAIN,
        "observed_targets": [
            metric("hosts_observed_residency", "Hosts observed for residency", 4, "hosts", "findings", "Australia (4 hosts)", count_kind="observed", section="privacy"),
            metric("vuln_asset_labels", "Distinct asset labels in vulnerability findings", len(vuln_asset_rows), "asset_labels", "findings", None, count_kind="distinct_labels_as_printed", section="vulnerabilities", note="Labels as printed; one combines host and IP ('instagram.com / 157.240.8.174')."),
            metric("ips_checked", "IP addresses checked for reputation", 2, "ip_addresses", "pending_review", "Checked 2 IP(s) against threat intelligence feeds.", section="vulnerabilities"),
            metric("quantum_scopes", "Scopes in quantum scope breakdown", len(q_sub_summary), "scopes", "findings", None, count_kind="root_aggregate_plus_subdomains", section="quantum_security", note="1 root aggregate (instagram.com) + 3 subdomains."),
            metric("fourth_parties", "Fourth-party vendors identified", len(vendors), "organisations", "findings", "35", count_kind="reported", section="fourth_party_vendors"),
        ],
        "eligible_targets": null_reason("not_printed_in_source"),
        "coverage_percent": null_reason("denominator_unavailable"),
        "coverage_statement_source": "No additional subdomains or externally exposed assets were identified during this assessment.",
        "method_statement_source": about,
    },
    "rating_overview": {
        "rating_ref": "rating",
        "aspect_breakdown": [
            {"aspect": "privacy", "section": "privacy", "value": 48, "unit": "percent", "state": "findings", "display_label_source": "48%", "summary_label_source": "Privacy policy exists but has 12 active risks requiring attention"},
            {"aspect": "vulnerability", "section": "vulnerabilities", "value": 8, "unit": "percent", "state": "findings", "display_label_source": "8%", "summary_label_source": "Security improvements needed urgently"},
            {"aspect": "certification", "section": "certifications", "value": 0, "unit": "certifications_headline", "state": "clear", "display_label_source": "0 certifications", "summary_label_source": "Compliance improvements recommended",
             "secondary": metric("compliance_score", "Compliance Score", 0, "percent", "clear", "Compliance Score: 0% (100% = fully certified)")},
            {"aspect": "data_leak_history", "section": "data_leak_history", "value": 9, "unit": "events", "state": "pending_review", "display_label_source": "9 leakes", "summary_label_source": "9 data breaches found in public records. Immediate review and remediation required.",
             "secondary": metric("leak_free_score", "Security Score", 0, "percent", "findings", "Security Score: 0% (100% = leak-free)"), "review_flags": ["RF-03", "RF-05"]},
            {"aspect": "credential_leak", "section": "credential_exposure", "value": 7179, "unit": "found_headline", "state": "findings", "display_label_source": "7179 Found", "summary_label_source": "7179 credential leaks detected from 2008-2012-2013-2014-2015-2016-2017-2018-2019-2020-2021-2022-2024-2025-2026", "review_flags": ["RF-02"]},
        ],
        "note": "Aspect values use different units and denominators; never average them or compare with the 360-point grade.",
    },
    "sector_comparison": {
        "sector": "Media & Telecom",
        "intro_source": "See how your security posture compares to industry peers",
        "metrics": [
            metric("your_score", "Your Score", 14, "points", "findings", "Your Score 14/100", denominator=100),
            metric("sector_average", "Sector Average", 49, "points", "findings", "Industry Average 49/100", denominator=100),
            metric("sector_top_10_percent", "Sector Top 10%", 62, "points", "findings", "Industry Top 10% 62/100", denominator=100),
        ],
        "performance_gap": {"value": perf_gap, "state": "pending_review", "reason_code": "narrative_overclaim_and_provisional_rule",
                            "source_label": "Performance Gap:", "note": "35-point gap matches 49 - 14. 'Primary gap is in Privacy (48%)' while Vulnerability prints 8% (RF-06)."},
        "cohort": {"cohort_id": None, "cohort_size": None, "period": None, "percentile_method": None, "state": "unavailable", "reason_code": "not_printed_in_source"},
        "note": "Your Score /100 is not the 360-point IISRI score; no forecast or percentile may be derived.",
    },
}

S["priority_actions"] = {
    "number": "02", "title": "Priority actions", "group": "overview_and_priorities",
    "state": "findings", "state_label_source": "Priority Action Items",
    "source_pages": list(range(5, 12)),
    "intro_source": "Recommended actions to improve your IISRI rating, ordered by severity and priority",
    "actions": actions,
    "note": "Rank is source order, not a stable id. No 'Projected Rating After Remediation' block is printed (remediation_impact omitted). Actions 1-12 repeat privacy issues 1-12 (category as title, text quoted in Section 03); no 'Why This Matters' text is printed for them. Estimated time is not a due date; required role is not an assigned owner.",
}

S["privacy"] = {
    "number": "03", "title": "Privacy", "group": "assessment_details",
    "state": "findings", "state_label_source": "48% PRIVACY SCORE",
    "source_pages": [12, 13, 14, 15, 16, 17],
    "old_section_label": "SECTION 1 OF 8 · PRIVACY",
    "intro_source": "Evaluates privacy posture through publicly available data, privacy policies, technical implementations, and compliance with global standards including GDPR and PPDL.",
    "summary": "One privacy policy was assessed at 48% with 12 active issues (10 privacy, 2 security).",
    "policy": {
        "state": "findings", "state_label_source": "48% Privacy Score",
        "policy_state": null_reason("not_printed_in_source", "One of: valid_assessed | claimed_missing | excluded_no_policy (Q04)."),
        "policy_source": null_reason("not_printed_in_source"),
        "metrics": [
            metric("privacy_score", "Privacy Score", 48, "percent", "findings", "48%"),
            metric("active_issues", "Active Issues", len(issues), "issues", "findings", "12", count_kind="reported"),
            metric("policies_found", "Policies Found", 1, "policies", "findings", "1", count_kind="reported"),
        ],
        "areas": null_reason("not_printed_in_source", "Per-area A-P scores not printed; do not split the total across areas."),
        "issues": issues,
    },
    "terms_conditions": {
        "state": "findings", "state_label_source": "# No",
        "summary": "A login portal was detected and its published terms contain neither the data-protection nor the breach-notification clause.",   # section summary (split from privacy)
        "subtitle_source": "Login / payment portal customer-protection clauses",
        "portal_detected": True,
        "rows": [
            {"label": "Login / Payment Portal", "value_source": "Detected"},
            {"label": "Portal URL", "value_source": "https://instagram.com/auth/login"},
            {"label": "Terms & Conditions", "value_source": "https://help.instagram.com/581066165581870"},
            {"label": "Protects customer data & restricts unauthorised access", "value_source": "# No"},
            {"label": "Notifies customer on incident / data breach", "value_source": "# No"},
        ],
        "clauses": [
            {"clause": "protects_customer_data", "present": False, "value_source": "# No"},
            {"clause": "notifies_on_breach", "present": False, "value_source": "# No"},
        ],
        "narrative_source": "Customers who log in here are not promised data protection or breach notification in the published terms. That is a gap.",
        "review_flags": ["RF-05"],
    },
    "sovereignty": {
        "state": "findings", "state_label_source": "Not identified in published policies",
        "summary": "Governing law could not be identified.",   # section summary (split from privacy)
        "subtitle_source": "Where this supplier says disputes and legal obligations are handled",
        "enabled": True,
        "observed_jurisdiction": null_reason("not_identified", source_label="Not identified in published policies"),
        "allowed_set": ["Australia"],
        "match_state": "unknown",
        "quote_source": sov_quote,
        "rows": [{"label": "Governing law / courts we found", "value_source": "Not identified in published policies"},
                 {"label": "From their policy", "value_source": sov_quote},
                 {"label": "Jurisdictions you accept", "value_source": "Australia"}],
        "narrative_source": "We could not identify a governing-law or court clause in the supplier's published policies, and that does not match the jurisdictions your organisation accepts (Australia). Until that is clear, treat legal location as unresolved.",
    },
    "residency": {
        "state": "findings", "state_label_source": "Australia (4 hosts)",
        "summary": "Observed hosting (Australia) is outside the preferred country.",   # section summary (split from privacy)
        "subtitle_source": "Where this organisation's public systems are hosted, compared with where you allow data to live",
        "enabled": True,
        "observed_hosting": [{"country": "Australia", "hosts": 4, "evidence_kind": null_reason("not_printed_in_source")}],
        "allowed_set": ["New Zealand"],
        "match_state": "mismatch",
        "rows": [{"label": "Where we found their systems", "value_source": "Australia (4 hosts)"},
                 {"label": "Countries you prefer", "value_source": "New Zealand"}],
        "narrative_source": "We found public systems hosted in locations that do not match the countries your organisation prefers (New Zealand). Hosts observed: Australia (4 hosts). That means customer data may sit outside the places you require.",
        "note": "IP location is not proof of where all customer data is stored.",
    },
    "resourcing": {
        "state": "findings", "state_label_source": "Public materials show this organisation has a privacy function.",
        "summary": "A Data Protection Officer is named in the privacy policy.",   # section summary (split from privacy)
        "subtitle_source": "Whether this organisation publicly staffs security or privacy",
        "privacy_role_evidence": "detected",
        "security_role_evidence": None, "security_role_evidence_state": "unavailable", "security_role_evidence_reason_code": "not_printed_in_source",
        "roles_found": [{"role": "Data Protection Officer", "role_label_source": "DATA PROTECTION OFFICER", "sources": ["Privacy Policy"]}],
        "narrative_source": "Public materials show this organisation has a privacy function.",
        "neutral_message": "A Data Protection Officer is named in the privacy policy. No security role is reported either way.",
    },
}

dmarc_flags = ["RF-01"]
S["vulnerabilities"] = {
    "number": "04", "title": "Vulnerabilities", "group": "assessment_details",
    "state": "findings", "state_label_source": "8% VULNERABILITY SCORE",
    "source_pages": [18, 19, 20, 21, 22, 23],
    "old_section_label": "SECTION 2 OF 8 · VULNERABILITY",
    "intro_source": "Covers external security posture including network vulnerabilities, open ports, SSL/TLS configuration, and DNS security controls protecting digital assets.",
    "summary": f"{len(findings)} finding types were reported: {sev_counts['high']} high, {sev_counts['medium']} medium and {sev_counts['low']} low, none critical. Both high findings concern certificate expiry. DKIM is not enabled, DNSSEC is missing or invalid, and the DMARC mode was not printed.",
    "metrics": [
        metric("vulnerability_score", "Vulnerability score", 8, "percent", "findings", "8%"),
        metric("finding_types", "Finding types", len(findings), "finding_types", "findings", None, count_kind="distinct_finding_type"),
        metric("finding_types_critical_high", "Critical/High finding types", sev_counts["critical"] + sev_counts["high"], "finding_types", "findings", None),
        metric("finding_types_medium", "Medium finding types", sev_counts["medium"], "finding_types", "findings", None),
        metric("finding_types_low", "Low finding types", sev_counts["low"], "finding_types", "findings", None),
        metric("asset_memberships", "Finding-asset memberships", sum(f["affected_assets_count"] for f in findings), "memberships", "findings", None, count_kind="membership_not_unique_assets"),
        metric("distinct_asset_labels", "Distinct affected asset labels", len(vuln_asset_rows), "asset_labels", "findings", None, count_kind="distinct_labels_as_printed"),
    ],
    "scanned_assets": null_reason("blank_in_source", "Heading 'List of identified assets and observed security posture:' is printed with no list (RF-16).",
                                  source_label="List of identified assets and observed security posture:"),
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
             "dmarc_policy": null_reason("blank_in_source", "Mode printed empty; p=none in action act-14 is not traceable to this value."), "review_flags": dmarc_flags},
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
            {"ip_address": ip, "isp": null_reason("blank_in_source"), "country": null_reason("blank_in_source"), "abuse_score": null_reason("sentinel_meaning_unconfirmed", source_label="-1"), "reports": {"value": 0, "source_label": "0", "state": "pending_review", "reason_code": "sentinel_meaning_unconfirmed"}}
            for ip in ("157.240.8.174", "2a03:2880:f219:80e5:face:b00c:0:4420")
        ],
        "review_flags": ["RF-07"],
    },
    "https_redirect": {
        "state": "clear", "state_label_source": "# HTTPS Redirect — Secure",
        "result": "redirects_to_https",
        "narrative_source": "HTTP correctly redirects to HTTPS. No insecure patterns detected.",
        "review_flags": ["RF-05"],
    },
    "review_flags": ["RF-16"],
}

S["certifications"] = {
    "number": "05", "title": "Certifications", "group": "assessment_details",
    "state": "clear", "state_label_source": "0% COMPLIANCE SCORE",
    "source_pages": [2, 24],
    "old_section_label": "SECTION 3 OF 8 · CERTIFICATION",
    "intro_source": "Outlines industry certifications and compliance frameworks held by the organization, providing independent validation of security and privacy controls.",
    "summary": "No certificate was detected or uploaded for this organisation; the compliance score is 0%. The standards listed below are general references, not evidence held by the organisation.",
    "state_reason": "No certificate records were found in the sources checked.",
    "metrics": [
        metric("compliance_score", "Compliance score", 0, "percent", "clear", "0%"),
        metric("certifications_headline", "Certifications", 0, "certifications", "clear", "0 certifications", count_kind="reported_headline"),
    ],
    "certificates": [],
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
}

inacc = [e for e in events if e.get("validity_state") == "reported_inaccurate"]
S["data_leak_history"] = {
    "number": "06", "title": "Data breach and leak history", "group": "assessment_details",
    "state": "pending_review", "state_label_source": "0% DATA LEAK SCORE",
    "reason_code": "lead_event_not_eligible",
    "state_reason": "The source labels the 7 Jan 2026 event 'Last Valid Breach' and says it is used in the rating calculation, but the same event is marked 'Reported Inaccurate'. Which event, if any, is scored is held for review.",
    "source_pages": [2, 25, 26, 27, 28, 29],
    "old_section_label": "SECTION 4 OF 8 · DATA LEAK HISTORY",
    "intro_source": "Documents publicly known data leak incidents. Historical data leaks are factored into the IISRI® score, with recency and severity both affecting the overall rating.",
    "summary": f"{len(events)} data leak events between 2017 and 2026 are listed: one labelled as the last valid breach and {len(events) - 1} historical records not used in current scoring. {len(inacc)} events, including the one labelled last valid, are marked Reported Inaccurate.",
    "last_reported_source": "Last data leak has been reported on 07.01.2026.",
    "metrics": [
        metric("data_leak_score", "Data leak score", 0, "percent", "findings", "0%"),
        metric("events_reported", "Leak events", len(events), "events", "findings", "9 leakes", count_kind="reported"),
        metric("events_reported_inaccurate", "Events marked Reported Inaccurate", len(inacc), "events", "pending_review", "Reported Inaccurate"),
        metric("events_historical", "Historical events (not used in current scoring)", len(events) - 1, "events", "findings", "Historical Breaches"),
    ],
    "last_valid_event": {"event_id": "ev-01", "state": "pending_review", "reason_code": "lead_event_not_eligible",
                         "source_label": "Last Valid Breach", "note": "Printed as used in the rating calculation and as Reported Inaccurate (RF-03)."},
    "events": events,
    "review_flags": ["RF-03", "RF-05", "RF-08", "RF-15"],
}

S["fourth_party_vendors"] = {
    "number": "07", "title": "Fourth-party vendors", "group": "assessment_details",
    "state": "findings", "state_label_source": "35 fourth-party vendor(s) have been identified",
    "source_pages": list(range(30, 36)),
    "old_section_label": "SECTION 5 OF 8 · FOURTH PARTIES",
    "intro_source": "Identifies fourth-party vendors — the suppliers and service providers used by this vendor — representing extended supply chain risk. Each vendor is assessed for security posture and compliance.",
    "summary": f"{len(vendors)} fourth-party vendors were identified through automated discovery and technology analysis: {len(rated)} rated ({band_counts['low']} Low, {band_counts['medium']} Medium, {band_counts['high']} High risk band) and {len(vendors) - len(rated)} without a rating.",
    "lead_source": "35 fourth-party vendor(s) have been identified through automated discovery and technology analysis.",
    "metrics": [
        metric("fourth_parties", "Fourth-party vendors", len(vendors), "organisations", "findings", "35", count_kind="reported"),
        metric("vendors_rated", "Rated vendors", len(rated), "organisations", "findings", None),
        metric("vendors_unrated", "Vendors without a rating", len(vendors) - len(rated), "organisations", "findings", "—"),
        metric("vendors_high_band", "Vendors in the High risk band", band_counts["high"], "organisations", "findings", None),
    ],
    "vendors": vendors,
    "review_flags": ["RF-13"],
}

years_sorted = sorted(year_rows, reverse=True)
S["credential_exposure"] = {
    "number": "08", "title": "Credential exposure", "group": "assessment_details",
    "state": "findings", "state_label_source": "40% CREDENTIAL SCORE",
    "source_pages": [3, 36] + [364],
    "old_section_label": "SECTION 6 OF 8 · CREDENTIAL LEAK",
    "intro_source": "Identifies credential leaks associated with the organization’s domains found in known data breaches. Exposed credentials represent a direct risk of unauthorized account access.",
    "summary": f"The source reports 7,179 credential exposures (headline) and lists {len(cred_rows):,} register rows spanning 2008 to 2026; {org_rows:,} rows are on the assessed domain or its subdomains and {dom_count['other_domain']:,} on other email domains. {pw_rows:,} rows include a password field category and {unk_rows:,} have an Unknown exposure period. The number of unique or active accounts is not known.",
    "attention_source": "Attention: Historical credential exposures were identified. Password resets and MFA enforcement are recommended.",
    "metrics": [
        metric("credential_score", "Credential score", 40, "percent", "findings", "40%"),
        metric("found_headline", "Found (headline)", 7179, "records_unit_unverified", "findings", "7179 Found", count_kind="reported_headline", note="Unit not defined in source; not unique accounts."),
        metric("returned_rows", "Register rows shown", len(cred_rows), "rows", "findings", None, count_kind="returned_rows"),
        metric("rows_org_domain", "Rows with assessed email domain or its subdomains", org_rows, "rows", "findings", None),
        metric("rows_external_domain", "Rows with other email domains", dom_count["other_domain"], "rows", "findings", None),
        metric("rows_unknown_email", "Rows with Unknown Email", dom_count[None], "rows", "findings", "Unknown Email"),
        metric("rows_with_password", "Rows exposing a password field", pw_rows, "rows", "findings", None),
        metric("rows_period_unknown", "Rows with an Unknown exposure period", unk_rows, "rows", "findings", "Unknown"),
        metric("rows_fields_blank", "Rows with no exposed field printed", blank_rows, "rows", "findings", None),
        metric("unique_accounts", "Unique accounts", None, "accounts", "unavailable", None, reason_code="not_derivable", note="Masked labels are not a dedup key."),
    ],
    "exposure_years_source": "2008-2012-2013-2014-2015-2016-2017-2018-2019-2020-2021-2022-2024-2025-2026",
    "rows_by_exposure_year": [{"year": y, "rows": year_rows[y]} for y in years_sorted],
    "rows_by_field_category": [{"field_category": f, "rows": c} for f, c in sorted(field_rows.items(), key=lambda kv: (-kv[1], kv[0]))],
    "rows_by_email_domain_class": [{"email_domain": d if d else None, "rows": c, **({} if d else {"email_domain_state": "unavailable", "email_domain_reason_code": "unknown_email_in_source"})}
                                   for d, c in sorted(dom_count.items(), key=lambda kv: -kv[1])],
    "aggregation_note": "Year and field counts are row memberships; a row can list several years or fields, so they do not sum to the row total. Other email domains are counted as one class and never named.",
    "breach_source_name": null_reason("not_printed_in_source"),
    "register_ref": "appendices.d_evidence_registers.credential_register",
    "mitigations_source": [
        "Force password resets for all affected accounts",
        "Enable multi-factor authentication across all user access points",
        "Review password hygiene and access policies",
        "Monitor authentication logs for anomalous activity",
    ],
    "review_flags": ["RF-02", "RF-14"],
}
S["credential_exposure"]["source_pages"] = [3] + list(range(36, 365))

S["cloud_infrastructure"] = {
    "number": "09", "title": "Cloud infrastructure", "group": "assessment_details",
    "state": "findings", "state_label_source": "1 Cloud Providers Detected",
    "source_pages": [365],
    "old_section_label": "SECTION 7 OF 8 · CLOUD INFRASTRUCTURE",
    "intro_source": "Identifies cloud service providers used by the organization through analysis of DNS records, IP ranges, MX records, and NS records. Cloud infrastructure detection reveals the hosting and service provider footprint of the assessed organization.",
    "summary": "One cloud provider, Azure, was detected. Detection shows provider use, not where all customer data is stored.",
    "lead_source": "1 cloud provider(s) have been identified through automated infrastructure analysis.",
    "metrics": [metric("cloud_providers_detected", "Cloud providers detected", 1, "providers", "findings", "1")],
    "detection_methods": ["dns_records", "ip_ranges", "mx_records", "ns_records"],
    "providers": [{"provider": "Azure", "detection_methods": null_reason("not_printed_in_source"), "observed_at": null_reason("not_printed_in_source")}],
    "last_scanned": {"value": "2026-10-02", "precision": "day", "source_label": "Last scanned: 02.10.2026"},
    "note": "Section-level detection_methods come from intro_source (the module description). Per-provider detection method and observed_at are not printed.",
}

S["ai_risk_governance"] = {
    "number": "10", "title": "AI risk and governance", "group": "assessment_details",
    "state": "not_assessed", "state_label_source": "NOT ASSESSED",
    "reason_code": "module_not_assessed",
    "source_pages": [366],
    "old_section_label": "AI RISK & GOVERNANCE · NOT ASSESSED",
    "title_source": "AI Usage & Risk Classification",
    "intro_source": "What we observed about this organisation's use of artificial intelligence, and what that means for customers and the people they serve.",
    "summary": "AI risk was not assessed for this report. The observations below are recorded for context only and are not an assessment result.",
    "narrative_observation": {
        "is_assessment_result": False,
        "subtitle_source": "What we observed about this organisation's use of artificial intelligence",
        "text_source": ai_text,
        "signals_observed": [],
        "signals_note": "No AI signals are listed in this report.",
        "stated_conclusion_source": "It is unlikely this organisation uses AI in a material way.",
        "annex_iii_high_risk_sector": {"value": "not_apparent", "state": "not_assessed", "reason_code": "module_not_assessed", "source_label": "They do not appear to fall into an EU Annex III high-risk sector."},
        "public_ai_policy": {"value": None, "state": "not_assessed", "reason_code": "not_printed_in_source", "note": "No statement about a public AI policy is printed in this report."},
        "privacy_policy_ai_disclosure": {"value": "not_clear", "state": "not_assessed", "reason_code": "module_not_assessed", "source_label": "Their privacy policy does not clearly explain AI use to the people whose data may be involved."},
    },
    "metrics": [metric("ai_issues", "AI issues", None, "issues", "not_assessed", "NOT ASSESSED", reason_code="module_not_assessed")],
    "review_flags": ["RF-04"],
}

S["quantum_security"] = {
    "number": "11", "title": "Quantum security", "group": "assessment_details",
    "state": "findings", "state_label_source": "Quantum Security Overview",
    "source_pages": list(range(367, 372)),
    "old_section_label": "SECTION 8 OF 8 · QUANTUM SECURITY",
    "intro_source": "Assesses exposure to quantum computing threats by analyzing cryptographic primitives found in TLS/SSL configurations and SSH endpoints. Includes detection of post-quantum cryptography (PQC) algorithms that may already provide protection.",
    "summary": "Across 4 scopes the scan reported 8 high-risk and 28 low-risk findings (apex aggregate). High risk comes from ECDHE and RSA key exchange; ML-KEM was detected on all 4 scopes. Supporting PQC does not prove every connection uses it.",
    "beta_notice_source": "Quantum Vulnerability is currently in beta. You may encounter incomplete data or ongoing changes as we refine the experience.",
    "metrics": [
        metric("high_risk", "High Risk", 8, "findings", "findings", "8", count_kind="root_aggregate"),
        metric("moderate_risk", "Moderate Risk", 0, "findings", "clear", "0", count_kind="root_aggregate"),
        metric("low_risk", "Low Risk", 28, "findings", "findings", "28", count_kind="root_aggregate"),
        metric("pqc_detected", "PQC Detected", 4, "scopes_inferred", "findings", "4", count_kind="reported", note="Unit not labelled in source; equals the 4 ML-KEM domain chips."),
    ],
    "findings_by_category": q_groups,
    "pqc_detected": [{
        "algorithm": "ML-KEM", "algorithm_alias": "CRYSTALS-Kyber", "purpose": "Key exchange / encryption",
        "status_source": "Status: NIST standardized (FIPS 203)", "domains_count": len(pqc_domains), "domains": pqc_domains,
    }],
    "scope_summary": q_sub_summary,
    "scope_register_ref": "appendices.d_evidence_registers.quantum_scope_register",
    "aggregation_note": "Row instagram.com is a root aggregate (each count = root + 3 subdomains). Never add the root row to subdomain rows. Subdomain rows sum to 6 high / 21 low.",
    "scope_and_limitations_source": q_limits,
    "review_flags": ["RF-09", "RF-12"],
}

report["sections"] = S

report["appendices"] = {
    "a_about": {
        "letter": "A", "title": "About this report", "source_pages": [371, 373],
        "about_source": about,
        "closing_source": "Report generated on 03.10.2026",
        "data_sources_source": [
            "automated analysis of data leak databases, public disclosures, and monitored online sources",
            "automated technology discovery and vendor relationship analysis",
            "analysis of DNS records, IP ranges, MX records, and NS records",
        ],
    },
    "b_rating_scale": {
        "letter": "B", "title": "IISRI rating scale", "source_pages": [372, 373],
        "intro_source": "Reference guide to the standardized rating scale used throughout this report, with descriptions of each grade level and associated risk profile.",
        "rows": scale,
        "old_appendix_label": "Appendix A. IISRI® Rating Scale",
    },
    "c_methodology": {**meth, "source_pages": [374, 375],
                      "note": "Generic methodology brief appended to the old PDF; values in its diagrams (e.g. Individual risk Low, Combined risk Medium) are illustrative, not Instagram results."},
    "d_evidence_registers": {
        "letter": "D", "title": "Detailed evidence registers", "state": "findings",
        "credential_register": {
            "source_pages": list(range(36, 365)), "state": "findings",
            "columns": ["id", "email_domain", "email_state", "exposure_period_source", "exposure_years", "exposure_period_has_unknown", "exposed_field_categories", "breach_source_name", "source_page"],
            "sanitised": True,
            "counts": {"returned_rows": len(cred_rows), "total_rows": null_reason("not_printed_in_source"), "headline_found": 7179},
            "rows": cred_rows,
        },
        "quantum_scope_register": {
            "source_pages": [368, 369, 370], "state": "findings",
            "columns": ["id", "subdomain", "scope_level", "category", "pre_qc_algorithm", "source", "post_qc_source", "post_qc_algorithm", "high", "moderate", "low", "source_page"],
            "counts": {"rows": len(q_rows), "scopes": len(q_sub_summary), "root_aggregate_rows": len(root)},
            "rows": q_rows,
        },
        "vulnerability_asset_register": {
            "source_pages": list(range(18, 23)), "state": "findings",
            "columns": ["asset_label_source", "finding_ids", "finding_count", "max_severity"],
            "counts": {"rows": len(vuln_asset_rows), "memberships": sum(r["finding_count"] for r in vuln_asset_rows)},
            "rows": vuln_asset_rows,
        },
        "pqc_domain_register": {
            "source_pages": [368], "state": "findings",
            "columns": ["domain", "algorithm"],
            "rows": [{"domain": d, "algorithm": "ML-KEM"} for d in pqc_domains],
        },
    },
}

report["review_flags"] = [
    {"id": "RF-01", "pages": [11, 22], "ref": "Peta_Konten issue 1", "text": "Action 14 recommends moving DMARC from p=none, but the DMARC line prints 'Enabled ( mode)' with an empty mode. Show a verification step unless dmarc_policy is known."},
    {"id": "RF-02", "pages": [3, 11, 36, 364], "ref": "Peta_Konten issue 3", "text": f"'7179 Found' is turned into '7179 affected accounts' in action 13; the register shows {len(cred_rows):,} rows ({dom_count['other_domain']:,} on other email domains, {dom_count[None]} Unknown Email). Unit of 7179 is undefined; unique/active accounts unknown."},
    {"id": "RF-03", "pages": [25], "ref": "Q16", "text": "The 'Last Valid Breach' (07-01-2026, 17,017,213 records) is printed as 'used in the rating calculation' and also labelled '(Reported Inaccurate)'. An inaccurate event cannot be the scored event; held for review."},
    {"id": "RF-04", "pages": [366], "ref": "Peta_Konten issue 5", "text": "AI section is NOT ASSESSED yet concludes material AI use is unlikely and comments on the privacy policy. Keep as observation, not result."},
    {"id": "RF-05", "pages": [2, 15, 23], "ref": "fixture extraction", "text": "Source copy errors kept only in fields ending in _source: '9 leakes', '# HTTPS Redirect — Secure', '# No' (markdown residue on the T&C clause values)."},
    {"id": "RF-06", "pages": [4], "ref": "fixture extraction", "text": "Performance gap text names 'Privacy (48%)' as the primary gap while the Vulnerability aspect prints 8% and the data leak score 0%. The 35-point gap itself equals 49 - 14."},
    {"id": "RF-07", "pages": [23], "ref": "Q11", "text": "Abuse score -1 for both IPs alongside 'Clean'; ISP and Country blank. Sentinel meaning unconfirmed."},
    {"id": "RF-08", "pages": [26, 27, 28, 29], "ref": "fixture extraction", "text": "Event dates 01-01-YYYY (4 events) and 01-MM-YYYY (2 events) are stored with precision 'year' / 'month': day 01 is read as a placeholder. Source labels are kept verbatim."},
    {"id": "RF-09", "pages": [367, 368], "ref": "Peta_Konten C13", "text": "Category headers say '1 domain' while the scope breakdown has 4 scopes; root instagram.com row aggregates root + 3 subdomains."},
    {"id": "RF-10", "pages": [1, 373], "ref": "fixture extraction", "text": "Badge description on p1 ('security and/or privacy risks') differs from the CCC meaning in the rating scale ('security and/or privacy issues')."},
    {"id": "RF-11", "pages": [1], "ref": "R02", "text": "Grade CCC exists only inside the badge image; net score, pool, grade table and score context are not printed."},
    {"id": "RF-12", "pages": [367, 368], "ref": "Peta_Konten C13", "text": "'PQC Detected 4' has no unit; it equals the number of ML-KEM domain chips."},
    {"id": "RF-13", "pages": [31, 33, 34, 35], "ref": "fixture extraction", "text": "Vendor profiles kept as printed but inconsistent: Carousel (carousel.com) and Fb (fb.com) carry blurbs about unrelated companies; Youtube 'Founded 2023' and Google 'Founded 2010' contradict their own blurbs; Amazon '+2000 more' technologies may be a display cap."},
    {"id": "RF-14", "pages": list(range(36, 365)), "ref": "fixture extraction", "text": f"{blank_rows:,} of {len(cred_rows):,} credential rows print no exposed field; {unmasked} rows print an unmasked local part (dropped)."},
    {"id": "RF-15", "pages": [26, 28], "ref": "fixture extraction", "text": "Historical event 01-01-2021 (SocialArks) prints 'Records Affected: Unknown' and no source; the 01-05-2025 record (184,000,000) is a multi-service infostealer collection, not Instagram-only."},
    {"id": "RF-16", "pages": [18], "ref": "fixture extraction", "text": "Heading 'List of identified assets and observed security posture:' is printed with no asset list."},
]

report["sections"] = restructure(report["sections"])
out = json.dumps(report, ensure_ascii=False, indent=2)

# ---------------- regression / privacy checks
assert "@" not in out and "*" not in out, "email material leaked into fixture"
chk = json.loads(out)
assert len(cred_rows) == 6883 and dom_count[None] == 1 and org_rows + dom_count["other_domain"] + dom_count[None] == 6883
assert all(r["email_domain"] in (None, "other_domain") or r["email_domain"] == DOMAIN or r["email_domain"].endswith("." + DOMAIN) for r in cred_rows)
assert set(chk["sections"]) == {"executive_overview", "priority_actions", "privacy", "vulnerabilities", "credential_exposure",
                                "data_leak_history", "data_sovereignty", "data_residency", "legal_terms",
                                "ai_risk_governance", "quantum_security", "security_resourcing", "certifications",
                                "fourth_party_vendors", "cloud_infrastructure"}
assert set(chk) == set(CL) and set(chk["meta"]) == set(CL["meta"]) and set(chk["identity"]) == set(CL["identity"])
assert all("description_source" not in v for v in vendors)


def walk(o, path=""):
    if isinstance(o, dict):
        if "state" in o and isinstance(o["state"], str):
            assert o["state"] in STATE_ENUM, (path, o["state"])
        for k, v in o.items():
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

print("actions", len(actions), "issues", len(issues))
print("findings", len(findings), dict(sev_counts), "asset labels", len(vuln_asset_rows))
print("events", len(events), "inaccurate", len(inacc))
print("vendors", len(vendors), "rated", len(rated), dict(band_counts))
print("cred rows", len(cred_rows), "domains", dict(dom_count), "pw", pw_rows, "unknown period", unk_rows, "blank fields", blank_rows, "unmasked", unmasked)
print("years", dict(sorted(year_rows.items())))
print("fields", dict(field_rows))
print("quantum rows", len(q_rows), "scopes", len(q_sub_summary), "pqc domains", len(pqc_domains))
print("rating scale rows", len(scale), "bytes", len(out))
