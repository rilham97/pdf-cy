"""Build data/mock-cyberrank-2026-10-13.json from the production PDF "Mock Cyberrank - Cyber Risk Report"
(old openhtmltopdf pipeline, report date 13.10.2026, generated 15.10.2026, 35 pages).

usage: .venv/bin/python -I tools/extract/build_mock_fixture.py <mock.pdf> data/claude-2026-10-02.json <out.json>

Adapted from build_fixture.py (Claude): same helpers (page_lines / join / metric / null_reason) and
the same schema (data/report-schema.md). The generic appendices (A about, B rating scale, C methodology)
are taken from the Claude fixture after checking that the Mock PDF prints the same text.
Privacy: the Mock PDF prints no email address, person name or credential value; the build asserts the
JSON holds no '@'. Asserts at the bottom are the regression check against the source PDF.
"""
import copy
import hashlib
import json
import re
import sys

import pymupdf
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[0]))   # tools/extract
from section_layout import restructure  # noqa: E402  (privacy sub-areas -> own sections, item 15)

pdf_path, template_path, out_path = sys.argv[1:4]
pdf = pymupdf.open(pdf_path)
TPL = json.load(open(template_path, encoding='utf-8'))
SHA = hashlib.sha256(open(pdf_path, 'rb').read()).hexdigest()
ORG, DOMAIN = 'Mock Cyberrank', 'cyberrank.site'
# The sample is the Indonesian-localised edition; reports stay English. Fixture display strings hold the
# English product term (old English reports in 02_PDF_Assessment_Valid print 'Low' / 'Medium' bands);
# the printed Indonesian label is kept in a *_source_id field for traceability and never rendered.
EN = {'Rendah': 'Low', 'Sedang': 'Medium', 'Manufaktur': 'Manufacturing', 'Telekomunikasi': 'Telecommunications'}
HEADER = {f'{ORG} - Cyber Risk Report', 'CyberRank', 'https://www.cyberrank.ai'}


def page_lines(i):
    """1-based page -> content lines, header/footer removed."""
    out = []
    for ln in pdf[i - 1].get_text().split('\n'):
        s = ln.strip()
        if not s or s in HEADER or re.match(r'^Generated \d\d\.\d\d\.\d{4} \d+ \| Page$', s):
            continue
        out.append(s)
    return out


def join(lines):
    s = ''
    for ln in lines:
        if not s:
            s = ln
        elif (s[-1] in '.-/' and re.match(r'[a-z0-9]', ln)) or ln.startswith('/'):
            s += ln
        else:
            s += ' ' + ln
    return re.sub(r'\s+', ' ', s).strip()


TEXT = {i: join(page_lines(i)) for i in range(1, pdf.page_count + 1)}
ALL = ' '.join(TEXT[i] for i in sorted(TEXT))


def find(pattern, text=ALL, group=1, flags=0):
    m = re.search(pattern, text, flags)
    assert m, pattern
    return m.group(group)


def metric(mid, label, value, unit, state, source_label=None, **kw):
    m = {'id': mid, 'label': label, 'value': value, 'unit': unit, 'state': state}
    if source_label is not None:
        m['source_label'] = source_label
    m.update(kw)
    return m


def nr(reason_code='not_printed_in_source', note=None, source_label=None, state='unavailable'):
    o = {'value': None, 'state': state, 'reason_code': reason_code}
    if note:
        o['note'] = note
    if source_label is not None:
        o['source_label'] = source_label
    return o


def ddmmyyyy(s):
    d, m, y = s.split('.')
    return f'{y}-{m}-{d}'


def date(s, label):
    return {'value': ddmmyyyy(s), 'precision': 'day', 'source_label': label}


# --- cover / rating -----------------------------------------------------------------------
P1 = TEXT[1]
REPORT_DATE = find(r'REPORT DATE (\d\d\.\d\d\.\d{4})', P1)
GENERATED = find(r'DATE GENERATED (\d\d\.\d\d\.\d{4})', P1)
SECTOR = find(r'SECTOR (\S+)', P1)
DESCRIPTION = find(r'ORGANIZATION DESCRIPTION (.+?) IISRI', P1)
BAND_LABEL = find(r'IISRI® External Rating (\S+) ', P1)
BAND_TEXT = find(r'IISRI® External Rating \S+ (.+)$', P1)
REM = TEXT[9]
CUR_GRADE, CUR_SCORE, POOL = re.search(r'CURRENT RATING (\w+) Score (\d+) / (\d+)', REM).groups()
PRO_GRADE, PRO_SCORE = re.search(r'PROJECTED RATING (\w+) Score (\d+) / \d+', REM).groups()

identity = {
    'organisation_name': ORG, 'organisation_id': nr(), 'domain': DOMAIN, 'website_source_label': DOMAIN,
    'sector': EN[SECTOR], 'sector_source_id': SECTOR, 'sector_label_source': 'SECTOR',
    'description_source': DESCRIPTION,
    'logo': nr('asset_not_extracted', 'Cover shows a blank logo tile.'), 'report_title': 'Cyber Risk Report',
    'issuer': {'organisation_name': None, 'state': 'unavailable', 'reason_code': 'not_printed_in_source',
               'note': 'Template field ISSUED BY has no source value.'},
}
grade_rows = {r['grade']: r for r in TPL['appendices']['b_rating_scale']['rows']}
rating = {
    'rating_name': 'IISRI® External Rating', 'grade': CUR_GRADE,
    'grade_source': 'badge image p1 (visual read) and "CURRENT RATING BB" p9',
    'grade_mark': grade_rows[CUR_GRADE]['mark'],
    'risk_band': EN[BAND_LABEL].lower(), 'risk_band_label_source': EN[BAND_LABEL],
    'risk_band_label_source_id': BAND_LABEL, 'band_description_source': BAND_TEXT,
    'net': {'value': int(CUR_SCORE), 'unit': 'points', 'source_label': f'Score {CUR_SCORE} / {POOL} · Current State'},
    'pool': {'value': int(POOL), 'unit': 'points', 'source_label': f'Score {CUR_SCORE} / {POOL}'},
    'grade_table_id': nr(), 'stored_vs_calculated': nr(), 'review_flags': ['RF-M01'],
}

snapshot = copy.deepcopy(TPL['snapshot'])
snapshot.update({
    'assessed_at': date(REPORT_DATE, f'REPORT DATE {REPORT_DATE}'),
    'generated_at': date(GENERATED, f'DATE GENERATED {GENERATED}'),
    'timezone': nr(note='PDF CreationDate 2026-10-15T01:11:43Z (UTC offset +00:00); report timezone not printed.'),
    'score_context': nr(),
    'preferences_at_assessment': {'sovereignty_allowed_jurisdictions': ['European Union (EU)'],
                                  'residency_allowed_countries': ['Argentina'], 'source_pages': [12, 13]},
})
snapshot['toggles_at_assessment']['pqc_scan']['note'] = 'Quantum results are present (section 11), so the module ran.'

# --- 01 executive overview ----------------------------------------------------------------
P2 = TEXT[2] + ' ' + TEXT[3]
priv_pct = int(find(r'Privacy (\d+)%', P2))
vuln_pct = int(find(r'Vulnerability (\d+)%', P2))
cert_n = int(find(r'Certification (\d+) certifications', P2))
leak_n = int(find(r'Data Leak History (\d+) leakes', P2))
cred_n = int(find(r'Credential Leak (\d+) Found', P2))
your, avg, top = (int(x) for x in re.search(r'Your Score (\d+)/100 .*?Sector Average (\d+)/100 .*?Sector Top 10% (\d+)/100',
                                             TEXT[4]).groups())
executive_overview = {
    'number': '01', 'title': 'Executive overview', 'group': 'overview_and_priorities', 'state': 'partial',
    'state_label_source': None, 'reason_code': 'score_context_incomplete',
    'state_reason': 'Grade, risk band, net score (201 / 360), aspect scores and sector benchmark are printed; '
                    'score context and assessment id are not.',
    'source_pages': [1, 2, 3, 4, 9],
    'summary': f'{ORG} ({DOMAIN}) holds an IISRI external rating of {CUR_GRADE} ({EN[BAND_LABEL]} risk band), '
               f'with a net score of {CUR_SCORE} of {POOL} on the 13 Oct 2026 assessment.',
    'scope_and_coverage': {
        'primary_domain': DOMAIN,
        'observed_targets': [
            metric('scanned_subdomains', 'Scanned subdomains', 4, 'subdomains', 'findings',
                   'Scanned Subdomains (4 listed)', count_kind='observed', section='vulnerabilities'),
            metric('hosts_observed_residency', 'Hosts observed for residency', 5, 'hosts', 'findings',
                   'XX (1 host), United States of America (4 hosts)', count_kind='observed', section='privacy'),
        ],
        'eligible_targets': nr(), 'coverage_percent': nr('denominator_unavailable'),
        'coverage_statement_source': 'No additional subdomains or externally exposed assets were identified during '
                                     'this assessment.',
        'method_statement_source': find(r'About This Report (.+?\.) The assessment', TEXT[31]).replace(
            'by using', 'by IISRI® CyberRank.ai using').replace(' IISRI® CyberRank.ai information', ' information'),
    },
    'rating_overview': {
        'rating_ref': 'rating',
        'aspect_breakdown': [
            {'aspect': 'privacy', 'section': 'privacy', 'value': priv_pct, 'unit': 'percent', 'state': 'findings',
             'display_label_source': f'{priv_pct}%',
             'summary_label_source': 'Privacy policy exists but has 7 active risks requiring attention'},
            {'aspect': 'vulnerability', 'section': 'vulnerabilities', 'value': vuln_pct, 'unit': 'percent',
             'state': 'findings', 'display_label_source': f'{vuln_pct}%',
             'summary_label_source': 'Security improvements needed urgently'},
            {'aspect': 'certification', 'section': 'certifications', 'value': cert_n, 'unit': 'certifications',
             'state': 'clear', 'display_label_source': '0 certifications',
             'summary_label_source': 'Compliance improvements recommended',
             'secondary': metric('compliance_score', 'Compliance Score', 0, 'percent', 'clear', '0%')},
            {'aspect': 'data_leak', 'section': 'data_leak_history', 'value': leak_n, 'unit': 'events', 'state': 'clear',
             'display_label_source': '0 leakes',
             'summary_label_source': 'No data breaches detected in public records. Excellent security posture.',
             'secondary': metric('data_leak_score', 'Security Score', 100, 'percent', 'clear', '100%')},
            {'aspect': 'credential', 'section': 'credential_exposure', 'value': cred_n,
             'unit': 'records_unit_unverified', 'state': 'clear', 'display_label_source': '0 Found',
             'summary_label_source': 'No credential leaks detected'},
        ],
        'note': 'Aspect values use different units and denominators; never average them or compare with the '
                'grade directly.',
    },
    'sector_comparison': {
        'sector': EN[SECTOR], 'sector_source_id': SECTOR,
        'intro_source': 'See how your security posture compares to sector peers',
        'metrics': [metric('your_score', 'Your Score', your, 'points', 'findings', f'Your Score {your}/100', denominator=100),
                    metric('sector_average', 'Sector Average', avg, 'points', 'findings', f'Sector Average {avg}/100',
                           denominator=100),
                    metric('sector_top_10_percent', 'Sector Top 10%', top, 'points', 'findings',
                           f'Sector Top 10% {top}/100', denominator=100)],
        'performance_gap': nr(),
        'cohort': {'cohort_id': None, 'cohort_size': None, 'period': None, 'percentile_method': None,
                   'state': 'unavailable', 'reason_code': 'not_printed_in_source'},
        'note': 'Your score (out of 100) is not the 360-point IISRI score; no forecast or percentile may be derived from it.',
    },
}

# --- 02 priority actions ------------------------------------------------------------------
act_text = ' '.join(TEXT[p] for p in range(5, 9))
blocks = re.split(r'(HIGH PRIORITY|MEDIUM PRIORITY|LOW PRIORITY) ', act_text)[1:]
actions = []
for prio, body in zip(blocks[::2], blocks[1::2]):
    m = re.match(r'(\d+)\. (.+?) (\d+ weeks?) Estimated Time: Legal \+ DPO team Required: Action Required: (.+)$', body) or \
        re.match(r'(\d+)\. (.+?) (\d+ weeks?) Estimated Time: (?P<role>.+?) Required: Action Required: (.+)$', body)
    rank, title, eta = int(m.group(1)), m.group(2), m.group(3)
    role = m.groupdict().get('role') or 'Legal + DPO team'
    rest = m.group(m.lastindex)
    why = None
    if 'Why This Matters:' in rest:
        rest, why = (x.strip() for x in rest.split('Why This Matters:', 1))
    rest = re.sub(r'\s*(REMEDIATION IMPACT.*)$', '', rest).strip()
    cat = title.lower() if title in ('PRIVACY', 'SECURITY') else None
    a = {'action_id': f'act-{rank:02d}', 'rank': rank, 'priority': prio.split()[0].lower(),
         'priority_label_source': prio, 'title': title.capitalize() if cat else title,
         'title_source': title, 'estimated_time_reported': eta, 'required_role': role,
         'owner': nr('not_assigned'), 'due_at': nr('not_assigned'), 'status': nr('not_tracked'),
         'action_required_source': rest}
    if why:
        a['why_this_matters_source'] = why
    a['linked_sections'] = ['privacy'] if cat else ['vulnerabilities'] if 'DMARC' in title else []
    a['linked_finding_ids'] = ['ctrl-dmarc'] if 'DMARC' in title else []
    if cat:
        a['category'] = cat
    actions.append(a)
remediation_text = find(r'Projected Rating After Remediation (.+?) CURRENT RATING', REM)
priority_actions = {
    'number': '02', 'title': 'Priority actions', 'group': 'overview_and_priorities', 'state': 'findings',
    'state_label_source': 'Priority Action Items', 'source_pages': [5, 6, 7, 8, 9],
    'intro_source': 'Recommended actions to improve your IISRI rating, ordered by severity and priority',
    'actions': actions,
    'remediation_impact': {
        'state': 'findings', 'title_source': 'Projected Rating After Remediation', 'source_pages': [9],
        'current': {'grade': CUR_GRADE, 'score': int(CUR_SCORE), 'pool': int(POOL)},
        'projected': {'grade': PRO_GRADE, 'score': int(PRO_SCORE), 'pool': int(POOL)},
        'points_recoverable': int(find(r'recover up to (\d+) points', remediation_text)),
        'active_issues': {'total': 43, 'privacy': 7, 'vulnerability': 36},
        'conditional_on_rescan': True, 'narrative_source': remediation_text,
        'caption_source': 'Estimated improvement upon completion of the recommended actions',
    },
    'note': 'Rank is source order, not a stable id. Estimated time is not a due date; required role is not an owner.',
}

# --- 03 privacy ---------------------------------------------------------------------------
issues_text = TEXT[10] + ' ' + TEXT[11]
issues = [{'label': f'Issue {n}', 'category': c.lower(), 'text': t.strip()}
          for n, c, t in re.findall(r'ISSUE (\d+) (PRIVACY|SECURITY) (.+?)(?= ISSUE \d+ | Terms & Conditions|$)',
                                    issues_text)]
quote = find(r'From their policy (.+?) Jurisdictions you accept', TEXT[12])
privacy = {
    'number': '03', 'title': 'Privacy', 'group': 'assessment_details', 'state': 'findings',
    'state_label_source': f'{priv_pct}% PRIVACY SCORE', 'source_pages': [10, 11, 12, 13],
    'old_section_label': 'SECTION 1 OF 8 · PRIVACY',
    'intro_source': find(r'S C O R E (Evaluates privacy posture .+?PPDL\.)', TEXT[10]),
    'summary': f'One privacy policy was assessed at {priv_pct}% with {len(issues)} active issues.',
    'policy': {
        'state': 'findings', 'state_label_source': f'{priv_pct}% Privacy Score',
        'policy_state': nr(note='One of: valid_assessed | claimed_missing | excluded_no_policy (Q04).'),
        'policy_source': nr(),
        'metrics': [metric('privacy_score', 'Privacy Score', priv_pct, 'percent', 'findings', f'{priv_pct}%'),
                    metric('active_issues', 'Active Issues', len(issues), 'issues', 'findings', str(len(issues)),
                           count_kind='reported'),
                    metric('policies_found', 'Policies Found', 1, 'policies', 'findings', '1', count_kind='reported')],
        'areas': nr(note='Per-area A-P scores not printed.'), 'issues': issues,
    },
    'terms_conditions': {
        'state': 'not_applicable', 'reason_code': 'no_login_or_payment_portal_detected',
        'summary': 'No login or payment portal was found.',   # section summary (split from privacy)
        'state_label_source': 'Not detected', 'subtitle_source': 'Login / payment portal customer-protection clauses',
        'portal_detected': False, 'rows': [{'label': 'Login / Payment Portal', 'value_source': 'Not detected'}],
        'narrative_source': find(r'Not detected (No customer login .+?access\.)', TEXT[12]),
    },
    'sovereignty': {
        'state': 'findings', 'state_label_source': 'Not identified in published policies',
        'summary': 'Governing law could not be identified.',   # section summary (split from privacy)
        'subtitle_source': 'Where this supplier says disputes and legal obligations are handled', 'enabled': True,
        'observed_jurisdiction': nr('not_identified', source_label='Not identified in published policies'),
        'allowed_set': ['European Union (EU)'], 'match_state': 'unknown', 'quote_source': quote,
        'rows': [{'label': 'Governing law / courts we found', 'value_source': 'Not identified in published policies'},
                 {'label': 'Jurisdictions you accept', 'value_source': 'European Union (EU)'}],
        'narrative_source': find(r'(We could not identify .+?unresolved\.)', TEXT[12]),
        'review_flags': ['RF-M02'],
    },
    'residency': {
        'state': 'findings', 'state_label_source': 'XX (1 host), United States of America (4 hosts)',
        'summary': 'Hosting is outside the preferred country.',   # section summary (split from privacy)
        'subtitle_source': "Where this organisation's public systems are hosted, compared with where you allow data to live",
        'enabled': True,
        'observed_hosting': [
            {'country': None, 'hosts': 1, 'state': 'unavailable', 'reason_code': 'country_code_placeholder',
             'source_label': 'XX (1 host)', 'evidence_kind': nr()},
            {'country': 'United States of America', 'hosts': 4, 'evidence_kind': nr()}],
        'allowed_set': ['Argentina'], 'match_state': 'mismatch',
        'rows': [{'label': 'Where we found their systems',
                  'value_source': 'XX (1 host), United States of America (4 hosts)'},
                 {'label': 'Countries you prefer', 'value_source': 'Argentina'}],
        'narrative_source': find(r'(We found public systems .+?require\.)', TEXT[13]),
        'note': 'IP location is not proof of where all customer data is stored.',
    },
    'resourcing': {
        'state': 'findings', 'state_label_source': 'Public materials show this organisation has a security function.',
        'summary': 'Public materials show this organisation has a security function.',   # section summary (split from privacy)
        'subtitle_source': 'Whether this organisation publicly staffs security or privacy',
        'privacy_role_evidence': None, 'privacy_role_evidence_reason_code': 'not_printed_in_source',
        'security_role_evidence': 'detected',
        'narrative_source': 'Public materials show this organisation has a security function.',
    },
}

# --- 04 vulnerabilities -------------------------------------------------------------------
vt = ' '.join(TEXT[p] for p in range(14, 19))
scan_dom = find(r'Scanned Domains (\S+) Scanned Subdomains', vt).split()
scan_sub = find(r'Scanned Subdomains (.+?) Understanding Security Findings', vt).split()
fstart = vt.index('<15% ') + 5
fend = vt.index('Note: No additional') if 'Note: No additional' in vt else vt.index(' No additional subdomains')
findings = []
for i, m in enumerate(re.finditer(r'(\S+) (HIGH|MEDIUM|LOW|CRITICAL) (.+?) Affected Domains?(?: \((\d+)\))?: ?(.+?) '
                                  r'Breach Likelihood: (\d+)%', vt[fstart:fend]), 1):
    name, sev, rat, n, hosts, bl = m.groups()
    hosts = [h.strip() for h in hosts.replace('report. cyberrank.site', 'report.cyberrank.site').split(',')]
    findings.append({'finding_id': f'vuln-{i:02d}', 'finding_type': name, 'severity': sev.lower(),
                     'severity_label_source': sev, 'rationale_source': rat.strip(),
                     'affected_assets_count': int(n) if n else 1, 'affected_assets': hosts,
                     'breach_likelihood': {'value': int(bl), 'unit': 'percent',
                                           'likelihood_type': 'ai_derived_per_finding',
                                           'source_label': f'Breach Likelihood: {bl}%'}})
sevs = [f['severity'] for f in findings]
assets = {}
for f in findings:
    for h in f['affected_assets']:
        assets.setdefault(h, []).append(f)
RANK = ['critical', 'high', 'medium', 'low']
asset_rows = [{'asset_label_source': h, 'finding_ids': [f['finding_id'] for f in fs], 'finding_count': len(fs),
               'max_severity': min((f['severity'] for f in fs), key=RANK.index)} for h, fs in assets.items()]
ip_rows = [{'ip_address': ip, 'isp': nr('blank_in_source'), 'country': nr('blank_in_source'),
            'abuse_score': nr('sentinel_meaning_unconfirmed', source_label='-1'),
            'reports': {'value': 0, 'source_label': '0', 'state': 'pending_review',
                        'reason_code': 'sentinel_meaning_unconfirmed'}}
           for ip in re.findall(r'(\S+) -1 0', find(r'Reports (.+)$', TEXT[18]))]
vulnerabilities = {
    'number': '04', 'title': 'Vulnerabilities', 'group': 'assessment_details', 'state': 'findings',
    'state_label_source': f'{vuln_pct}% VULNERABILITY SCORE', 'source_pages': list(range(14, 20)),
    'old_section_label': 'SECTION 2 OF 8 · VULNERABILITY',
    'intro_source': find(r'S C O R E (Covers external .+?digital assets\.)', TEXT[14]),
    'summary': f'{len(findings)} finding types were reported: {sevs.count("high")} high, {sevs.count("medium")} medium and '
               f'{sevs.count("low")} low, across the main domain and 4 scanned subdomains.',
    'metrics': [
        metric('vulnerability_score', 'Vulnerability score', vuln_pct, 'percent', 'findings', f'{vuln_pct}%'),
        metric('finding_types', 'Finding types', len(findings), 'finding_types', 'findings',
               count_kind='distinct_finding_type'),
        metric('finding_types_critical', 'Critical finding types', sevs.count('critical'), 'finding_types', 'clear'),
        metric('finding_types_high', 'High finding types', sevs.count('high'), 'finding_types', 'findings'),
        metric('finding_types_medium', 'Medium finding types', sevs.count('medium'), 'finding_types', 'findings'),
        metric('finding_types_low', 'Low finding types', sevs.count('low'), 'finding_types', 'findings'),
        metric('asset_memberships', 'Finding-asset memberships', sum(len(f['affected_assets']) for f in findings),
               'memberships', 'findings', count_kind='membership_not_unique_assets'),
        metric('distinct_asset_labels', 'Distinct affected asset labels', len(asset_rows), 'asset_labels', 'findings',
               count_kind='distinct_labels_as_printed'),
    ],
    'scanned_assets': {'title_source': 'List of identified assets and observed security posture:',
                       'domains': scan_dom, 'subdomains': scan_sub},
    'severity_legend_source': copy.deepcopy(TPL['sections']['vulnerabilities']['severity_legend_source']),
    'breach_likelihood_legend_source': TPL['sections']['vulnerabilities']['breach_likelihood_legend_source'],
    'findings': findings,
    'assets_register_ref': 'appendices.d_evidence_registers.vulnerability_asset_register',
    'coverage_note_source': 'Note: No additional subdomains or externally exposed assets were identified during '
                            'this assessment.',
    'email_dns_controls': copy.deepcopy(TPL['sections']['vulnerabilities']['email_dns_controls']),
    'ip_reputation': {'state': 'pending_review', 'state_label_source': 'IP Reputation — Clean',
                      'reason_code': 'sentinel_meaning_unconfirmed',
                      'summary_source': f'Checked {len(ip_rows)} IP(s) against threat intelligence feeds.',
                      'ips_checked': len(ip_rows), 'rows': ip_rows, 'review_flags': ['RF-07']},
    'https_redirect': {'state': 'clear', 'state_label_source': '# HTTPS Redirect — Secure',
                       'result': 'redirects_to_https',
                       'narrative_source': 'HTTP correctly redirects to HTTPS. No insecure patterns detected.'},
}
for k in vulnerabilities['email_dns_controls']['controls']:
    k.pop('review_flags', None)
vulnerabilities['email_dns_controls']['controls'][1]['review_flags'] = ['RF-01']
vulnerabilities['email_dns_controls']['controls'][1]['dmarc_policy']['note'] = (
    'Mode printed empty; p=none in action act-08 is not traceable to this value.')

# --- 05 certifications --------------------------------------------------------------------
certifications = {
    'number': '05', 'title': 'Certifications', 'group': 'assessment_details', 'state': 'clear',
    'state_label_source': '0% COMPLIANCE SCORE', 'source_pages': [2, 20],
    'old_section_label': 'SECTION 3 OF 8 · CERTIFICATION',
    'intro_source': TPL['sections']['certifications']['intro_source'],
    'summary': 'No certificate was detected or uploaded for this organisation; the compliance score is 0%.',
    'state_reason': 'No certificate records were found in the sources checked.',
    'metrics': [metric('compliance_score', 'Compliance score', 0, 'percent', 'clear', '0%'),
                metric('certifications_headline', 'Certifications', cert_n, 'certifications', 'clear',
                       '0 certifications', count_kind='reported_headline')],
    'certificates': [],
    'reference_standards': copy.deepcopy(TPL['sections']['certifications']['reference_standards']),
}

# --- 06 / 07 / 08 / 09 --------------------------------------------------------------------
dl = copy.deepcopy(TPL['sections']['data_leak_history'])
dl.update(source_pages=[2, 21], review_flags=[])
dl.pop('review_flags')
vendor_lines = TEXT[22]
vendors = []
for m in re.finditer(r'(\w+) (\S+\.com) (AAA|AA|A|BBB|BB|B|CCC|CC|C|D) (Low|Medium|High|Critical) (.+?) · ([\d,]+) '
                     r'employees · (\S+) · (.+?) · Founded (\d{4}) (.+?\.\.\.) # (.+?) \+(\d+) more', vendor_lines):
    name, dom, grade, band, cat, emp, rev, hq, founded, desc, sample, more = m.groups()
    sample = [s.strip() for s in sample.split(',')]
    vendors.append({'vendor_id': f'vendor-{len(vendors) + 1:02d}', 'name': name, 'domain': dom, 'grade': grade,
                    'risk_band': band.lower(), 'risk_band_label_source': band, 'category': cat,
                    'assessed_membership': True, 'employees': int(emp.replace(',', '')), 'revenue_source': rev,
                    'headquarters': hq, 'founded': int(founded), 'description_source': desc,
                    'technologies_count': len(sample) + int(more), 'technologies_sample_source': sample,
                    'evidence': nr(note='Discovery method per vendor not printed (section: automated discovery and '
                                        'technology analysis).')})
fourth_party_vendors = {
    'number': '07', 'title': 'Fourth-party vendors', 'group': 'assessment_details', 'state': 'findings',
    'state_label_source': f'{len(vendors)} fourth-party vendor(s) have been identified', 'source_pages': [22],
    'old_section_label': 'SECTION 5 OF 8 · FOURTH PARTIES',
    'intro_source': TPL['sections']['fourth_party_vendors']['intro_source'],
    'summary': f'{len(vendors)} fourth-party vendors were identified through automated discovery and technology '
               'analysis; one is in the High risk band.',
    'lead_source': f'{len(vendors)} fourth-party vendor(s) have been identified through automated discovery and '
                   'technology analysis.',
    'metrics': [metric('fourth_parties', 'Fourth-party vendors', len(vendors), 'organisations', 'findings',
                       str(len(vendors)), count_kind='reported')],
    'vendors': vendors,
}
credential_exposure = {
    'number': '08', 'title': 'Credential exposure', 'group': 'assessment_details', 'state': 'clear',
    'state_label_source': '100% CREDENTIAL SCORE', 'source_pages': [3, 23],
    'old_section_label': 'SECTION 6 OF 8 · CREDENTIAL LEAK',
    'intro_source': TPL['sections']['credential_exposure']['intro_source'],
    'summary': 'No credential exposure was found for this organisation in the sources checked.',
    'state_reason': f'No known credential leaks found for {ORG}.',
    'metrics': [metric('credential_score', 'Credential score', 100, 'percent', 'clear', '100%'),
                metric('found_headline', 'Found (headline)', cred_n, 'records_unit_unverified', 'clear', '0 Found',
                       count_kind='reported_headline')],
    'register_ref': 'appendices.d_evidence_registers.credential_register',
    'empty_state_source': {'title': 'No credential leaks', 'text': f'No known credential leaks found for {ORG}.'},
}
cloud = copy.deepcopy(TPL['sections']['cloud_infrastructure'])
scanned = find(r'Last scanned: (\d\d\.\d\d\.\d{4})', TEXT[24])
cloud.update(source_pages=[24], providers=[{'provider': find(r'Detected Cloud Providers (\S+)', TEXT[24]),
                                            'detection_methods': nr(), 'observed_at': nr()}],
             last_scanned=date(scanned, f'Last scanned: {scanned}'),
             summary='One cloud provider, Cloudflare, was detected. Detection shows provider use, not risk.')
ai = {'number': '10', 'title': 'AI risk and governance', 'group': 'assessment_details', 'state': 'unavailable',
      'reason_code': 'section_not_in_source', 'source_pages': [],
      'state_reason': 'The source report has no AI usage page (its sections run 1 to 8 without one), so no AI '
                      'observation or result is available for this assessment.',
      'summary': 'AI risk is not covered by this source report.'}

# --- 11 quantum ---------------------------------------------------------------------------
qt = TEXT[25] + ' ' + TEXT[26] + ' ' + TEXT[27]
H, M, L = (int(x) for x in re.search(r'Quantum Security Overview (\d+) High Risk (\d+) Moderate Risk (\d+) Low Risk', qt).groups())
PQC_N = int(find(r'# Partly Quantum Safe (\d+) PQC Detected', qt))
cats = []
for m in re.finditer(r'(Symmetric cryptography|Hash functions|Public-key cryptography|Certificate|Key exchange) '
                     r'(\d+) issues · (\d+ domains?) (.+?)(?= Symmetric cryptography \d| Hash functions \d| '
                     r'Public-key cryptography \d| Certificate \d| Key exchange \d| Post-Quantum Cryptography Detected)',
                     qt):
    cat, n, doms, body = m.groups()
    algs = []
    for a in re.finditer(r'(\S+) — (\d+) findings? (?:(\S+(?: Prime)?) available )?\(([^)]+)\)', body):
        alg, f, alt, protos = a.groups()
        rec = {'algorithm': alg, 'findings': int(f), 'protocol_labels': [p.strip() for p in protos.split(',')],
               'pqc_alternative_available': alt}
        if alt is None:
            rec.update(pqc_alternative_available_state='unavailable',
                       pqc_alternative_available_reason_code='not_printed_in_source')
        algs.append(rec)
    cats.append({'category': cat, 'issues': int(n), 'domains_source_label': doms, 'algorithms': algs})

# scope register: one data row per line carrying the High / Moderate / Low numbers
COLS = [('subdomain', 0, 100), ('category', 100, 165), ('pre', 165, 285), ('source', 285, 335), ('post', 335, 380),
        ('risk', 380, 445), ('high', 445, 475), ('moderate', 475, 525), ('low', 525, 600)]


def col(x):
    return next(n for n, a, b in COLS if a <= x < b)


qrows, current = [], None
for pno in range(27, 31):
    page = pdf[pno - 1]
    words = [w for w in page.get_text('words') if 60 < w[1] < 800]
    if pno == 27:
        words = [w for w in words if w[1] > 240]
    if pno == 30:
        words = [w for w in words if w[1] < [x for x in page.get_text('words') if x[4] == 'Affected'][0][1]]
    anchors = sorted({round(w[1]) for w in words if col(w[0]) == 'high' and w[4].isdigit()})
    if not anchors:
        continue
    cells = {a: {} for a in anchors}
    subs, run = [], []                    # subdomain cells wrap over several lines: one run per name
    for w in sorted((w for w in words if col(w[0]) == 'subdomain'), key=lambda w: w[1]):
        if run and w[1] - run[-1][1] > 16:
            subs.append(run)
            run = []
        run.append(w)
    subs += [run] if run else []
    for run in subs:
        a = min(anchors, key=lambda y: abs(y - run[0][1]))
        cells[a]['subdomain'] = [w[4] for w in run]
    for w in sorted(words, key=lambda w: (w[1], w[0])):
        if col(w[0]) == 'subdomain':
            continue
        a = min(anchors, key=lambda y: abs(y - w[1]))
        cells[a].setdefault(col(w[0]), []).append(w[4])
    for a in anchors:
        c = cells[a]
        if c.get('subdomain'):
            current = ''.join(c['subdomain'])
        risk = c.get('risk') or []
        post = ' '.join(c.get('post') or [])
        post = post.replace('ML- KEM', 'ML-KEM')
        row = {'subdomain': current, 'category': ' '.join(c['category']), 'pre_qc_algorithm': ''.join(c['pre']),
               'source': ' '.join(c['source']), 'post_qc_source': post or '—',
               'post_qc_algorithm': None if post in ('', '—') else post,
               'risk_level': risk[0].lower(), 'high': int(c['high'][0]), 'moderate': int(c['moderate'][0]),
               'low': int(c['low'][0]), 'source_page': pno}
        if row['post_qc_algorithm'] is None:
            row.update(post_qc_algorithm_state='unavailable', post_qc_algorithm_reason_code='dash_in_source')
        if len(risk) > 1:
            row['risk_note_source'] = re.sub(r'(\w)- (\w)', r'\1-\2', ' '.join(risk[1:]))
        qrows.append(row)
for i, r in enumerate(qrows, 1):
    r['id'] = f'qscope-{i:04d}'
    r['scope_level'] = 'root_aggregate' if r['subdomain'] == DOMAIN else 'subdomain'
qrows = [{k: r[k] for k in ['id', 'subdomain', 'scope_level', *[k for k in r if k not in ('id', 'subdomain', 'scope_level')]]}
         for r in qrows]
pqc_text = TEXT[26] + ' ' + TEXT[27]
pqc = []
for m in re.finditer(r'(ML-KEM|NTRU Prime) \(([^)]+)\) (Key exchange / encryption) (Status: [^)]+\)) (.+?)(?= NTRU Prime \(| Scope Breakdown)',
                     pqc_text):
    alg, alias, purpose, status, doms = m.groups()
    doms = doms.split()
    pqc.append({'algorithm': alg, 'algorithm_alias': alias, 'purpose': purpose, 'status_source': status,
                'domains_count': len(doms), 'domains': doms})
prot_text = find(r'Affected Protocols Protocol Algorithms PQC Risk (.+?) Quantum Vulnerability is currently', TEXT[30])
protocols = [{'protocol': p, 'algorithms': [a.strip() for a in algs.split(',')], 'pqc_source': pq.strip(),
              'risk_level': rk.lower()}
             for p, algs, pq, rk in re.findall(r'(TLS_1_2|TLS_1_0|TLS_1_1|SSH) (.+?) ((?:NTRU Prime|ML-KEM)[^A-Z]*?(?:, (?:NTRU Prime|ML-KEM))? ?available) (Low|Moderate|High)',
                                                prot_text)]
groups = {}
for r in qrows:
    groups.setdefault(r['subdomain'], []).append(r)
scope_summary = [{'subdomain': s, 'scope_level': rs[0]['scope_level'], 'rows': len(rs),
                  'high': sum(r['high'] for r in rs), 'moderate': sum(r['moderate'] for r in rs),
                  'low': sum(r['low'] for r in rs)} for s, rs in groups.items()]
tq = TPL['sections']['quantum_security']
quantum = {
    'number': '11', 'title': 'Quantum security', 'group': 'assessment_details', 'state': 'findings',
    'state_label_source': 'Quantum Security Overview', 'source_pages': list(range(25, 31)),
    'old_section_label': 'SECTION 8 OF 8 · QUANTUM SECURITY', 'intro_source': tq['intro_source'],
    'summary': f'The scan reported {H} high-risk, {M} moderate-risk and {L} low-risk findings across '
               f'{len(groups)} scopes; ML-KEM was detected on {len(pqc[0]["domains"])} scopes and NTRU Prime on '
               f'{len(pqc[1]["domains"])}.',
    'beta_notice_source': tq['beta_notice_source'],
    'metrics': [metric('high_risk', 'High Risk', H, 'findings', 'findings', str(H), count_kind='reported_headline'),
                metric('moderate_risk', 'Moderate Risk', M, 'findings', 'findings', str(M), count_kind='reported_headline'),
                metric('low_risk', 'Low Risk', L, 'findings', 'findings', str(L), count_kind='reported_headline'),
                metric('partly_quantum_safe', 'Partly Quantum Safe', None, 'scopes', 'unavailable', '#',
                       reason_code='placeholder_in_source'),
                metric('pqc_detected', 'PQC Detected', PQC_N, 'scopes_inferred', 'findings', str(PQC_N),
                       count_kind='reported', note='Unit not labelled in source; equals the 4 ML-KEM + 1 NTRU Prime '
                                                   'domain chips.')],
    'findings_by_category': cats, 'pqc_detected': pqc, 'affected_protocols': protocols,
    'scope_summary': scope_summary,
    'scope_register_ref': 'appendices.d_evidence_registers.quantum_scope_register',
    'aggregation_note': f'Row {DOMAIN} is labelled the main domain total. Its rows sum to fewer findings than the '
                        'headline (RF-M03).',
    'scope_and_limitations_source': copy.deepcopy(tq['scope_and_limitations_source']),
    'review_flags': ['RF-M03', 'RF-M04'],
}

# --- appendices ---------------------------------------------------------------------------
app = copy.deepcopy(TPL['appendices'])
app['a_about']['source_pages'] = [31, 33]
app['a_about']['closing_source'] = f'Report generated on {GENERATED}'
rs_text = TEXT[32] + ' ' + TEXT[33]
for r in app['b_rating_scale']['rows']:
    assert ' '.join(r['meaning_source'].split()) in rs_text, r['grade']          # same scale text as Claude
    r['is_current_grade'] = r['grade'] == CUR_GRADE
app['b_rating_scale']['source_pages'] = [32, 33]
for needle in ('One rating for every vendor', 'Supply-chain aggregation', 'R(N) = 1'):
    assert needle in TEXT[34] + TEXT[35], needle
app['c_methodology']['source_pages'] = [34, 35]
for k in ('credential_register',):
    app['d_evidence_registers'].pop(k, None)
app['d_evidence_registers'].update({
    'quantum_scope_register': {'source_pages': list(range(27, 31)), 'state': 'findings',
                               'columns': list(qrows[0]),
                               'counts': {'rows': len(qrows), 'scopes': len(groups),
                                          'root_aggregate_rows': len(groups[DOMAIN])},
                               'rows': qrows},
    'vulnerability_asset_register': {'source_pages': list(range(14, 19)), 'state': 'findings',
                                     'columns': ['asset_label_source', 'finding_ids', 'finding_count', 'max_severity'],
                                     'counts': {'rows': len(asset_rows),
                                                'memberships': sum(r['finding_count'] for r in asset_rows)},
                                     'rows': asset_rows},
    'pqc_domain_register': {'source_pages': [26, 27], 'state': 'findings', 'columns': ['domain', 'algorithm'],
                            'rows': [{'domain': d, 'algorithm': p['algorithm']} for p in pqc for d in p['domains']]},
})

meta = copy.deepcopy(TPL['meta'])
meta.update({
    'fixture_note': 'Values transcribed from the production PDF "Mock Cyberrank - Cyber Risk Report" (old openhtmltopdf '
                    'pipeline). Not a backend payload. Generic appendices reuse the Claude fixture after a text check.',
    'extracted_at': '2026-10-15',
    'source_document': {'ref': 'P-MOCK', 'file': 'Downloads/Mock Cyberrank - Cyber Risk Report.pdf', 'sha256': SHA,
                        'pages': pdf.page_count, 'pdf_title': pdf.metadata['title'], 'producer': pdf.metadata['producer'],
                        'creator': pdf.metadata['creator'], 'pdf_created_at': '2026-10-15T01:11:43Z',
                        'pdf_modified_at': '2026-09-12T01:10:20Z', 'template_id': nr()},
    'sanitisation': {'applied': True, 'rule': 'No email address or local part, person name, password/token value or '
                                              'masked label is stored.',
                     'removed_fields': [], 'source_rows_with_unmasked_local_part': 0,
                     'note': 'The source prints no credential rows and no email address.'},
})
review_flags = [
    {'id': 'RF-01', 'pages': [8, 18], 'ref': 'fixture extraction',
     'text': 'Action 8 recommends moving DMARC from p=none, but the DMARC line prints an empty mode ("Enabled ( mode)").'},
    {'id': 'RF-07', 'pages': [18], 'ref': 'fixture extraction',
     'text': 'IP reputation prints "Clean" while every abuse score is the sentinel -1.'},
    {'id': 'RF-M01', 'pages': [1, 32], 'ref': 'fixture extraction',
     'text': 'Cover band text for BB ("risks", "Moderate additional work") differs from the BB meaning in Appendix A '
             '("issues", "Major additional work").'},
    {'id': 'RF-M02', 'pages': [12], 'ref': 'fixture extraction',
     'text': 'Governing law is printed as "Not identified in published policies" next to a quoted governing-law clause.'},
    {'id': 'RF-M03', 'pages': [25, 27], 'ref': 'fixture extraction',
     'text': 'Headline 8 / 1 / 37 equals the findings-by-category totals; the apex rows of the scope breakdown sum to '
             '7 / 0 / 32.'},
    {'id': 'RF-M04', 'pages': [26, 27], 'ref': 'fixture extraction',
     'text': 'Scope rows print Risk "Low" with "covered by ML-KEM" next to Post-QC "NTRU Prime", and counts in the '
             'High column for rows whose Risk is Low.'},
]

report = {'meta': meta, 'identity': identity, 'snapshot': snapshot, 'rating': rating,
          'sections': {'executive_overview': executive_overview, 'priority_actions': priority_actions,
                       'privacy': privacy, 'vulnerabilities': vulnerabilities, 'certifications': certifications,
                       'data_leak_history': dl, 'fourth_party_vendors': fourth_party_vendors,
                       'credential_exposure': credential_exposure, 'cloud_infrastructure': cloud,
                       'ai_risk_governance': ai, 'quantum_security': quantum},
          'appendices': app, 'review_flags': review_flags}

# --- regression checks against the source PDF ----------------------------------------------
assert pdf.page_count == 35
assert (CUR_GRADE, CUR_SCORE, POOL, PRO_GRADE, PRO_SCORE) == ('BB', '201', '360', 'AAA', '330')
assert BAND_LABEL == 'Rendah' and SECTOR == 'Manufaktur'
assert len(actions) == 8 and [a['priority'] for a in actions].count('high') == 7
assert len(issues) == 7 and [i['category'] for i in issues].count('security') == 2
assert len(findings) == 12 and (sevs.count("high"), sevs.count("medium"), sevs.count("low")) == (1, 4, 7)
assert sum(f["affected_assets_count"] for f in findings) == 36      # = "36 vulnerability findings" (p9)
assert [f['affected_assets_count'] == len(f['affected_assets']) for f in findings] == [True] * 12
assert len(ip_rows) == 4 and len(vendors) == 3 and [v['grade'] for v in vendors] == ['AAA', 'AAA', 'CC']
assert (H, M, L, PQC_N) == (8, 1, 37, 5)
assert sum(c['issues'] for c in cats) == H + M + L == 46 and len(cats) == 5
assert sum(len(c['algorithms']) for c in cats) == 14
assert len(qrows) == 46 and len(groups) == 5, {k: len(v) for k, v in groups.items()}
apex = [r for r in qrows if r['scope_level'] == 'root_aggregate']
assert tuple(sum(r[k] for r in apex) for k in ('high', 'moderate', 'low')) == (7, 0, 32)
assert sum(r['high'] for r in qrows) == 13 and sum(r['moderate'] for r in qrows) == 1
assert [p['domains_count'] for p in pqc] == [4, 1] and len(protocols) == 3
assert sum(1 for r in qrows if r.get('risk_note_source')) == 8
report["sections"] = restructure(report["sections"])
raw = json.dumps(report, ensure_ascii=False)
assert '@' not in raw, 'email-like token in fixture'
json.dump(report, open(out_path, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
open(out_path, 'a').write('\n')
print(out_path, len(raw), 'bytes; checks passed')
