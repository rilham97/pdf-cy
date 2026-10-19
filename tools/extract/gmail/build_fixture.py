"""Build data/gmail-2026-10-15.json from the production PDF "Gmail - Cyber Risk Report (1).pdf"
(old openhtmltopdf pipeline, Indonesian-localised edition, report date 15.10.2026, generated 15.10.2026, 410 pages).

usage: .venv/bin/python -I tools/extract/gmail/build_fixture.py <gmail.pdf> data/claude-2026-10-02.json <out.json>

Adapted from tools/extract/build_mock_fixture.py (same helpers and schema, data/report-schema.md). The credential
register (pages 38-391) is parsed by parse_tables.py next to this file. Generic appendices (A about, B rating scale,
C methodology) and generic copy are taken from the Claude fixture after checking the Gmail PDF prints the same text.
Privacy: no email local part, full email, name or credential value is stored; credential rows keep a synthetic id,
the email domain class (gmail.com, one of its subdomains, or 'other_domain'), years and field categories.
The build asserts the JSON holds no '@' and no '*'. Asserts at the bottom are the regression check against the PDF.
"""
import copy
import hashlib
import json
import os
import re
import sys
from collections import Counter

import pymupdf
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))   # tools/extract
from section_layout import restructure  # noqa: E402  (privacy sub-areas -> own sections, item 15)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_tables  # noqa: E402

pdf_path, template_path, out_path = sys.argv[1:4]
pdf = pymupdf.open(pdf_path)
TPL = json.load(open(template_path, encoding='utf-8'))
SHA = hashlib.sha256(open(pdf_path, 'rb').read()).hexdigest()
ORG, DOMAIN = 'Gmail', 'gmail.com'
# Indonesian-localised sample; reports stay English. Display strings hold the English product term, the printed
# Indonesian label is kept in *_source_id (never rendered).
EN = {'Rendah': 'Low', 'Sedang': 'Medium', 'Manufaktur': 'Manufacturing', 'Telekomunikasi': 'Telecommunications'}
HEADER = {f'{ORG} - Cyber Risk Report', 'CyberRank', 'https://www.cyberrank.ai'}
CRED_FIRST, CRED_LAST = parse_tables.FIRST, parse_tables.LAST


def page_lines(i):
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


# the credential pages hold email labels: never read into TEXT
TEXT = {i: join(page_lines(i)) for i in range(1, pdf.page_count + 1) if not CRED_FIRST <= i < CRED_LAST}
TEXT[CRED_LAST] = join(page_lines(CRED_LAST)[page_lines(CRED_LAST).index('Recommended Mitigation Measures'):])
TEXT[CRED_FIRST] = join(page_lines(CRED_FIRST)[:page_lines(CRED_FIRST).index('Status') + 1])
ALL = ' '.join(TEXT[i] for i in sorted(TEXT))
assert '@' not in ALL


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


def date(s, label, sep='.'):
    d, m, y = s.split(sep)
    return {'value': f'{y}-{m}-{d}', 'precision': 'day', 'source_label': label}


def pages(a, b):
    return list(range(a, b + 1))


# --- cover / rating -----------------------------------------------------------------------
P1 = TEXT[1]
REPORT_DATE = find(r'REPORT DATE (\d\d\.\d\d\.\d{4})', P1)
GENERATED = find(r'DATE GENERATED (\d\d\.\d\d\.\d{4})', P1)
SECTOR = find(r'SECTOR (\S+)', P1)
DESCRIPTION = find(r'ORGANIZATION DESCRIPTION (.+?) IISRI', P1)
BAND_LABEL = find(r'IISRI® External Rating (\S+) ', P1)
BAND_TEXT = find(r'IISRI® External Rating \S+ (.+)$', P1)
REM = TEXT[10] + ' ' + TEXT[11]
CUR_GRADE, CUR_SCORE, POOL = re.search(r'PROJECTED RATING (\w+) Score (\d+) / (\d+) · Current State', REM).groups()
PRO_GRADE, PRO_SCORE = re.search(r'> (\w+) Score (\d+) / \d+ · Expected Outcome', REM).groups()

identity = {
    'organisation_name': ORG, 'organisation_id': nr(), 'domain': DOMAIN, 'website_source_label': DOMAIN,
    'sector': EN[SECTOR], 'sector_source_id': SECTOR, 'sector_label_source': 'SECTOR',
    'description_source': DESCRIPTION,
    'logo': nr('asset_not_extracted', 'Cover shows a blank logo tile.'), 'report_title': 'Cyber Risk Report',
    'issuer': {'organisation_name': None, 'state': 'unavailable', 'reason_code': 'not_printed_in_source',
               'note': 'Template field ISSUED BY has no source value.'},
    'review_flags': ['RF-G01'],
}
grade_rows = {r['grade']: r for r in TPL['appendices']['b_rating_scale']['rows']}
rating = {
    'rating_name': 'IISRI® External Rating', 'grade': CUR_GRADE,
    'grade_source': f'badge image p1 (visual read) and "{CUR_GRADE} Score {CUR_SCORE} / {POOL} · Current State" p11',
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
    'timezone': nr(note='PDF CreationDate 2026-10-15T01:00:50Z (UTC offset +00:00); report timezone not printed.'),
    'score_context': nr(),
    'preferences_at_assessment': {'sovereignty_allowed_jurisdictions': ['European Union (EU)'],
                                  'residency_allowed_countries': ['Argentina'], 'source_pages': [16]},
})
snapshot['toggles_at_assessment']['pqc_scan']['note'] = 'Quantum results are present (section 11), so the module ran.'

# --- 01 executive overview ----------------------------------------------------------------
P2 = TEXT[2] + ' ' + TEXT[3]
priv_pct = int(find(r'Privacy (\d+)%', P2))
priv_summary = find(r'Privacy \d+% (.+?) Vulnerability', P2)
vuln_pct = int(find(r'Vulnerability (\d+)%', P2))
cert_n = int(find(r'Certification (\d+) certifications', P2))
leak_n = int(find(r'Data Leak History (\d+) leakes', P2))
leak_summary = find(r'\d+ leakes (.+?\.) ?0% Security Score', P2)
cred_n = int(find(r'Credential Leak (\d+) Found', P2))
cred_years_src = find(r'credential leaks detected from ([\d-]+)', P2)
your, avg, top = (int(x) for x in re.search(r'Your Score (\d+)/100 .*?Sector Average (\d+)/100 .*?Sector Top 10% (\d+)/100',
                                             TEXT[4]).groups())
gap_text = find(r'(You are currently .+?average\.)', TEXT[4].replace('Performance Gap: ', ''))

# --- 02 priority actions ------------------------------------------------------------------
act_text = ' '.join(TEXT[p] for p in range(5, 11))
act_text = act_text[:act_text.index('REMEDIATION IMPACT')]
blocks = re.split(r'(HIGH PRIORITY|MEDIUM PRIORITY|LOW PRIORITY) ', act_text)[1:]
raw10 = pdf[9].get_text()
WHY = [re.sub(r'\s+', ' ', w).strip() for w in re.findall(r'\n ([^\n]+)\nWhy This Matters:', raw10)]
actions = []
for prio, body in zip(blocks[::2], blocks[1::2]):
    m = re.match(r'(\d+)\. (.+?) (\d+ weeks?) Estimated Time: (.+?) Required: Action Required: ?(.+)$', body)
    rank, title, eta, role, rest = int(m.group(1)), m.group(2), m.group(3), m.group(4), m.group(5).strip()
    why = None
    if rest.endswith('Why This Matters:'):
        rest = rest[:-len('Why This Matters:')].strip()
        why = next(w for w in WHY if rest.endswith(w))
        rest = rest[:-len(why)].strip()
    cat = title.lower() if title in ('PRIVACY', 'SECURITY') else None
    a = {'action_id': f'act-{rank:02d}', 'rank': rank, 'priority': prio.split()[0].lower(),
         'priority_label_source': prio, 'title': title.capitalize() if cat else title,
         'title_source': title, 'estimated_time_reported': eta, 'required_role': role,
         'owner': nr('not_assigned'), 'due_at': nr('not_assigned'), 'status': nr('not_tracked'),
         'action_required_source': rest}
    if why:
        a['why_this_matters_source'] = why
    a['linked_sections'] = (['privacy'] if cat else ['vulnerabilities'] if 'DMARC' in title
                            else ['credential_exposure'] if 'Credential' in title else [])
    a['linked_finding_ids'] = ['ctrl-dmarc'] if 'DMARC' in title else []
    if cat:
        a['category'] = cat
    if 'Credential' in title:
        a['review_flags'] = ['RF-G02']
    if 'DMARC' in title:
        a['review_flags'] = ['RF-01']
    actions.append(a)
remediation_text = find(r'Projected Rating After Remediation (.+?) CURRENT RATING', REM)
ai_tot, ai_priv, ai_vuln, ai_cred = (int(x) for x in re.search(
    r'(\d+) active issues were identified \((\d+) privacy issues, (\d+) vulnerability findings, (\d+) exposed '
    r'credentials\)', remediation_text).groups())

# --- 03 privacy ---------------------------------------------------------------------------
issues_text = ' '.join(TEXT[p] for p in range(12, 16))
issues = [{'label': f'Issue {n}', 'category': c.lower(), 'text': t.strip()}
          for n, c, t in re.findall(r'ISSUE (\d+) (PRIVACY|SECURITY) (.+?)(?= ISSUE \d+ | Terms & Conditions|$)',
                                    issues_text)]
P15, P16 = TEXT[15], TEXT[16]
portal_url = find(r'Portal URL (\S+)', P15)
tc_narr = find(r'# No (Customers who log in .+?That is a gap\.)', P15)
hosting_src = find(r'Where we found their systems (.+?) Countries you prefer', P16)
HOSTS = [(c, int(n)) for c, n in re.findall(r'([A-Z][A-Za-z ]+?|XX) \((\d+) hosts?\)', hosting_src)]
unk_hosts = int(find(r'(\d+) hosts with unknown location', hosting_src))
roles_src = find(r'What we found (.+?\)) Public materials', P16)
role, srcs = re.match(r'(.+?) \(Source: (.+)\)', roles_src).groups()
res_narr = find(r'(Public materials show .+?function\.)', P16)

# --- 04 vulnerabilities -------------------------------------------------------------------
vt = ' '.join(TEXT[p] for p in range(17, 28))
scan_dom = find(r'Scanned Domains (\S+) Scanned Subdomains', vt).split()
scan_sub = find(r'Scanned Subdomains (.+?) Understanding Security Findings', vt).split()
fstart = vt.index('<15% ') + 5
fend = vt.index('## Vulnerability Scan Results')
findings = []
for i, m in enumerate(re.finditer(r'(\S+) (HIGH|MEDIUM|LOW|CRITICAL) (.+?) Affected Domains?(?: \((\d+)\))?: ?(.+?) '
                                  r'Breach Likelihood: (\d+)%', vt[fstart:fend]), 1):
    name, sev, rat, n, hosts, bl = m.groups()
    hosts = [h.strip() for h in hosts.split(',')]
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
truncated = [h for h in assets if '.' not in h]
for r in asset_rows:
    if r['asset_label_source'] in truncated:
        r['review_flags'] = ['RF-08']

# active scan ('## Vulnerability Scan Results')
scan_txt = vt[fend:vt.index(' No additional subdomains')]
n_results = int(find(r'(\d+) scan results', scan_txt))
results = []
for m in re.finditer(r'(https://\S+) (CLEAN|SCANNED) (?:(\d+) findings )?(\w{3} \d+, \d{4} \d\d:\d\d)(.*?)(?= https://|$)',
                     scan_txt):
    url, status, nrep, when, body = m.groups()
    mon, day, yr, hm = re.match(r'(\w{3}) (\d+), (\d{4}) (\d\d:\d\d)', when).groups()
    mm = '%02d' % (['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].index(mon) + 1)
    r = {'target': url, 'status': status.lower(), 'status_label_source': status,
         'scanned_at': {'value': f'{yr}-{mm}-{int(day):02d}T{hm}', 'precision': 'day', 'source_label': when},
         'findings_reported': int(nrep) if nrep else 0}
    body = body.strip()
    if body:
        r['summary_source'] = find(r'# Executive Summary (.+?) # Top Recommendations', body)
        recs = find(r'# Top Recommendations (.+?) # Detailed Findings', body)
        r['recommendations_source'] = [s.strip() + '.' for s in re.split(r'\.\s+', recs.rstrip('.'))]
        r['findings_listed_label_source'] = find(r'(# Detailed Findings \(\d+\))', body)
        detail = body.split(r['findings_listed_label_source'], 1)[1].strip()
        r['findings'] = [{'title': t.strip(), 'severity': 'info', 'severity_label_source': 'INFO', 'description': d,
                          'impact': im, 'remediation': rm}
                         for t, d, im, rm in re.findall(r'(.+?) INFO Description: (.+?) Impact: (.+?) '
                                                        r'Remediation: (.+?\.)(?= [A-Z][^.:]*? INFO Description:|$)',
                                                        detail)]
    else:
        r['findings'] = []
    results.append(r)
mismatch = [r['target'] for r in results if r['findings_reported'] != len(r['findings'])]
ip_rows = [{'ip_address': ip, 'isp': nr('blank_in_source'), 'country': nr('blank_in_source'),
            'abuse_score': nr('sentinel_meaning_unconfirmed', source_label='-1'),
            'reports': {'value': 0, 'source_label': '0', 'state': 'pending_review',
                        'reason_code': 'sentinel_meaning_unconfirmed'}}
           for ip in re.findall(r'(\S+) -1 0', find(r'Abuse Score Reports (.+?) HTTPS Redirect', vt))]
edc = copy.deepcopy(TPL['sections']['vulnerabilities']['email_dns_controls'])
for k in edc['controls']:
    k.pop('review_flags', None)
edc['controls'][1]['review_flags'] = ['RF-01']
edc['controls'][1]['dmarc_policy']['note'] = 'Mode printed empty; p=none in action act-15 is not traceable to this value.'
assert edc['guidance_source'] in vt
for k in edc['controls']:
    assert k['line_source'].split(' – ')[1].split()[0] in vt
assert 'DKIM: Not Enabled' in vt and 'DMARC: Enabled ( mode)' in vt and 'Missing / Invalid' in vt

# --- 06 data leak history -----------------------------------------------------------------
lt = ' '.join(TEXT[p] for p in range(29, 37))
last_date = find(r'Last data leak has been reported on \.? ?(\d\d\.\d\d\.\d{4})', lt)
hist_at = lt.index('Historical Breaches')
starts = [m.start() for m in re.finditer(r'gmail\.com (?:\(Reported Inaccurate\) )?Date:', lt)]
events = []
for k, st in enumerate(starts):
    chunk = lt[st:starts[k + 1] if k + 1 < len(starts) else len(lt)].strip()
    m = re.match(r'(gmail\.com)( \(Reported Inaccurate\))? Date: (Unknown Date|\d\d-\d\d-\d{4}) Records Affected: '
                 r'(Unknown|[\d,]+) Details: (.+?)(?: Source: (\S+).*)?$', chunk)
    ent, inacc, when, recs, det, src = m.groups()
    i = len(events) + 1
    e = {'event_id': f'leak-{i:02d}', 'entity_link': ent}
    e['occurred_at'] = (nr('unknown_in_source', source_label='Date: Unknown Date') if when == 'Unknown Date'
                        else date(when, f'Date: {when}', '-'))
    if st < hist_at:
        e.update(validity_state='reported_inaccurate', validity_label_source='(Reported Inaccurate)',
                 rating_use_label_source='This breach is used in the rating calculation',
                 listed_as='last_valid_breach', review_flags=['RF-G03'])
        assert inacc
    else:
        assert not inacc
        e.update(scoring_eligible=False, listed_as='historical',
                 scoring_reason='listed under Historical Breaches: not directly used in current scoring')
    e['records_affected'] = (nr('unknown_in_source', source_label='Records Affected: Unknown') if recs == 'Unknown'
                             else int(recs.replace(',', '')))
    e['description_source'] = det.strip()
    e['source_url'] = src or None
    if not src:     # sibling null form: the s06 renderer hashes source_url, a NullReason object crashes it
        e.update(source_url_state='unavailable', source_url_reason_code='not_printed_in_source')
    events.append(e)
src_long = {'https://www.forbes.com/sites/daveywinder/2026/01/25/48-million-gmail-usernames-and-passwords-leaked-online/',
            'https://www.nasdaq.com/articles/massive-data-leak-exposes-183-mln-email-passwords-including-gmail-accounts',
            'https://www.anonymoushackers.net/cybersecurity-news/has-google-ever-been-hacked/',
            'https://www.nucleustechnologies.com/blog/gmail-password-data-breach/'}
assert src_long <= {e['source_url'] for e in events if isinstance(e['source_url'], str)}, \
    {e['source_url'] for e in events if isinstance(e['source_url'], str)}

# --- 08 credentials -----------------------------------------------------------------------
crows = parse_tables.parse(pdf)
reg_rows = []
for i, r in enumerate(crows, 1):
    years = sorted({int(t) for t in r['period'] if t.isdigit()}, reverse=True)
    cats = list(dict.fromkeys(r['fields']))
    row = {'id': f'cred-{i:04d}', 'email_domain': r['email_domain'], 'email_state': r['email_state'],
           'exposure_period_source': ', '.join(r['period']), 'exposure_years': years,
           'exposure_period_has_unknown': 'Unknown' in r['period'], 'exposed_field_categories': cats,
           'breach_source_name': nr(), 'status': r['status'], 'source_page': r['page']}
    if not cats:
        row.update(exposed_field_categories_state='unavailable', exposed_field_categories_reason_code='blank_in_source')
    if r['email_domain'] is None:
        row.update(email_domain_state='unavailable', email_domain_reason_code='unknown_email_in_source')
    reg_rows.append(row)
by_year = Counter(y for r in reg_rows for y in r['exposure_years'])
by_cat = Counter(c for r in reg_rows for c in r['exposed_field_categories'])
dom = Counter(r['email_domain'] for r in reg_rows)
n_org = dom[DOMAIN]
n_sub = sum(n for d, n in dom.items() if d and d != DOMAIN and d != 'other_domain')
n_other, n_unknown = dom['other_domain'], dom[None]
n_pw = sum('password' in r['exposed_field_categories'] for r in reg_rows)
n_unk = sum(r['exposure_period_has_unknown'] for r in reg_rows)
n_unk_only = sum(r['exposure_period_has_unknown'] and not r['exposure_years'] for r in reg_rows)
n_nofields = sum(not r['exposed_field_categories'] for r in reg_rows)
n_unmasked = sum(r['email_state'] == 'unmasked_label_dropped' for r in reg_rows)
n_pwlike = sum(1 for r in reg_rows if {'Passwords', 'pass', 'Historical passwords'} & set(r['exposed_field_categories'])
               and 'password' not in r['exposed_field_categories'])
status_counts = Counter(r['status'] for r in reg_rows)
cred_score = int(find(r'Credential Leak (\d+)% C R E D E N T I A L', TEXT[CRED_FIRST]))
mitig = [find(r'Recommended Mitigation Measures (.+)$', TEXT[CRED_LAST])]
mitig = [s for s in TPL['sections']['credential_exposure']['mitigations_source'] if s in mitig[0]]

# --- 09 cloud / 11 quantum ----------------------------------------------------------------
CT = TEXT[393]
QT = ' '.join(TEXT[p] for p in range(394, 397))
H, M, L = (int(x) for x in re.search(r'Quantum Security Overview (\d+) High Risk (\d+) Moderate Risk (\d+) Low Risk', QT).groups())
PQC_N = int(find(r'# Partly Quantum Safe (\d+) PQC Detected', QT))
cats = []
for m in re.finditer(r'(Symmetric cryptography|Hash functions|Public-key cryptography|Certificate|Key exchange) '
                     r'(\d+) issues · (\d+ domains?) (.+?)(?= Symmetric cryptography \d| Hash functions \d| '
                     r'Public-key cryptography \d| Certificate \d| Key exchange \d| Post-Quantum Cryptography Detected)',
                     QT):
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

COLS = [('subdomain', 0, 100), ('category', 100, 165), ('pre', 165, 285), ('source', 285, 335), ('post', 335, 380),
        ('risk', 380, 445), ('high', 445, 475), ('moderate', 475, 525), ('low', 525, 600)]


def col(x):
    return next(n for n, a, b in COLS if a <= x < b)


RISK_NOTE = 'This finding is covered by ML-KEM, therefore the risk is Low.'
NOTE_WORDS = sum(w[4] == 'covered' for p in range(395, 406) for w in pdf[p - 1].get_text('words'))
qrows, current = [], None
for pno in range(395, 406):
    page = pdf[pno - 1]
    allw = page.get_text('words')
    words = [w for w in allw if 60 < w[1] < 800]
    if pno == 395:
        words = [w for w in words if w[1] > [x for x in allw if x[4] == 'Subdomain'][0][3] + 2]
    if pno == 405:
        words = [w for w in words if w[1] < [x for x in allw if x[4] == 'Affected'][0][1]]
    anchors = sorted({round(w[1]) for w in words if col(w[0]) == 'high' and w[4].isdigit()})
    if not anchors:
        continue
    cells = {a: {} for a in anchors}
    subs, run = [], []
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
        risk = [w for w in c.get('risk') or [] if w in ('Low', 'Moderate', 'High')]
        assert len(risk) == 1, (pno, c.get('risk'))
        post = ' '.join(c.get('post') or []).replace('ML- KEM', 'ML-KEM')
        row = {'subdomain': current, 'category': ' '.join(c['category']), 'pre_qc_algorithm': ''.join(c['pre']),
               'source': ' '.join(c['source']), 'post_qc_source': post or '—',
               'post_qc_algorithm': None if post in ('', '—') else post,
               'risk_level': risk[0].rstrip('.').lower(), 'high': int(c['high'][0]), 'moderate': int(c['moderate'][0]),
               'low': int(c['low'][0]), 'source_page': pno}
        if row['post_qc_algorithm'] is None:
            row.update(post_qc_algorithm_state='unavailable', post_qc_algorithm_reason_code='dash_in_source')
        if row['post_qc_algorithm']:      # wrapped note overlaps the next row: printed text is this sentence
            row['risk_note_source'] = RISK_NOTE
        qrows.append(row)
for i, r in enumerate(qrows, 1):
    r['id'] = f'qscope-{i:04d}'
    r['scope_level'] = 'root_aggregate' if r['subdomain'] == DOMAIN else 'subdomain'
qrows = [{k: r[k] for k in ['id', 'subdomain', 'scope_level', *[k for k in r if k not in ('id', 'subdomain', 'scope_level')]]}
         for r in qrows]
pqc = []
for m in re.finditer(r'(ML-KEM|NTRU Prime) \(([^)]+)\) (Key exchange / encryption) (Status: [^)]+\)) (.+?)(?= NTRU Prime \(| Scope Breakdown)',
                     QT):
    alg, alias, purpose, status, doms = m.groups()
    doms = doms.split()
    pqc.append({'algorithm': alg, 'algorithm_alias': alias, 'purpose': purpose, 'status_source': status,
                'domains_count': len(doms), 'domains': doms})
prot_text = find(r'Affected Protocols Protocol Algorithms PQC Risk (.+?) Quantum Vulnerability is currently', TEXT[405])
protocols = [{'protocol': p, 'algorithms': [a.strip() for a in algs.split(',')], 'pqc_source': pq.strip(),
              'risk_level': rk.lower()}
             for p, algs, pq, rk in re.findall(r'(TLS_1_2|TLS_1_0|TLS_1_1|SSH) (.+?) ((?:NTRU Prime|ML-KEM)[^A-Z]*?(?:, (?:NTRU Prime|ML-KEM))? ?available) (Low|Moderate|High)',
                                               prot_text)]
groups = {}
for r in qrows:
    groups.setdefault(r['subdomain'], []).append(r)
scope_summary = [{'subdomain': s, 'scope_level': rs[0]['scope_level'], 'rows': len(rs),
                  'high': sum(r['high'] for r in rs), 'moderate': sum(r['moderate'] for r in rs),
                  'low': sum(r['low'] for r in rs),
                  'ml_kem_on_key_exchange': any(r['post_qc_algorithm'] == 'ML-KEM' for r in rs),
                  'algorithms_absent': sorted({a['algorithm'] for c in cats for a in c['algorithms']} -
                                              {r['pre_qc_algorithm'] for r in rs})}
                 for s, rs in groups.items()]
apex = groups[DOMAIN]
apex_sum = tuple(sum(r[k] for r in apex) for k in ('high', 'moderate', 'low'))
sub_sum = tuple(sum(r[k] for r in qrows if r['scope_level'] == 'subdomain') for k in ('high', 'moderate', 'low'))

# --- sections -----------------------------------------------------------------------------
n_priv = sum(i['category'] == 'privacy' for i in issues)
n_sec = len(issues) - n_priv
executive_overview = {
    'number': '01', 'title': 'Executive overview', 'group': 'overview_and_priorities', 'state': 'partial',
    'state_label_source': None, 'reason_code': 'score_context_incomplete',
    'state_reason': f'Grade, risk band, net score ({CUR_SCORE} / {POOL}), aspect scores and sector benchmark are printed; '
                    'score context and assessment id are not.',
    'source_pages': [1, 2, 3, 4, 10, 11],
    'summary': f'{ORG} ({DOMAIN}) holds an IISRI external rating of {CUR_GRADE} ({EN[BAND_LABEL]} risk band), '
               f'with a net score of {CUR_SCORE} of {POOL} on the 15 Oct 2026 assessment.',
    'scope_and_coverage': {
        'primary_domain': DOMAIN,
        'observed_targets': [
            metric('scanned_subdomains', 'Scanned subdomains', len(scan_sub), 'subdomains', 'findings',
                   f'Scanned Subdomains ({len(scan_sub)} listed)', count_kind='observed', section='vulnerabilities'),
            metric('hosts_observed_residency', 'Hosts observed for residency', sum(n for _, n in HOSTS) + unk_hosts,
                   'hosts', 'findings', hosting_src, count_kind='observed', section='privacy'),
        ],
        'eligible_targets': nr(), 'coverage_percent': nr('denominator_unavailable'),
        'coverage_statement_source': 'No additional subdomains or externally exposed assets were identified during '
                                     'this assessment.',
        'method_statement_source': TPL['sections']['executive_overview']['scope_and_coverage']['method_statement_source'],
    },
    'rating_overview': {
        'rating_ref': 'rating',
        'aspect_breakdown': [
            {'aspect': 'privacy', 'section': 'privacy', 'value': priv_pct, 'unit': 'percent', 'state': 'findings',
             'display_label_source': f'{priv_pct}%', 'summary_label_source': priv_summary},
            {'aspect': 'vulnerability', 'section': 'vulnerabilities', 'value': vuln_pct, 'unit': 'percent',
             'state': 'findings', 'display_label_source': f'{vuln_pct}%',
             'summary_label_source': 'Security improvements needed urgently'},
            {'aspect': 'certification', 'section': 'certifications', 'value': cert_n, 'unit': 'certifications',
             'state': 'clear', 'display_label_source': '0 certifications',
             'summary_label_source': 'Compliance improvements recommended',
             'secondary': metric('compliance_score', 'Compliance Score', 0, 'percent', 'clear', '0%')},
            {'aspect': 'data_leak', 'section': 'data_leak_history', 'value': leak_n, 'unit': 'events',
             'state': 'pending_review', 'reason_code': 'lead_event_not_eligible',
             'display_label_source': f'{leak_n} leakes', 'summary_label_source': leak_summary,
             'secondary': metric('data_leak_score', 'Security Score', 0, 'percent', 'findings', '0%'),
             'review_flags': ['RF-G03']},
            {'aspect': 'credential', 'section': 'credential_exposure', 'value': cred_n,
             'unit': 'records_unit_unverified', 'state': 'findings', 'display_label_source': f'{cred_n} Found',
             'summary_label_source': f'{cred_n} credential leaks detected from {cred_years_src}',
             'review_flags': ['RF-G02']},
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
        'performance_gap': {'value': avg - your, 'unit': 'points', 'state': 'findings',
                            'source_label': gap_text, 'performance_gap_source': find(
                                r'Performance Gap: (gap is in .+?average\.)', TEXT[4])},
        'cohort': {'cohort_id': None, 'cohort_size': None, 'period': None, 'percentile_method': None,
                   'state': 'unavailable', 'reason_code': 'not_printed_in_source'},
        'note': 'Your Score /100 is not the 360-point IISRI score; no forecast or percentile may be derived from it.',
    },
}
priority_actions = {
    'number': '02', 'title': 'Priority actions', 'group': 'overview_and_priorities', 'state': 'findings',
    'state_label_source': 'Priority Action Items', 'source_pages': pages(5, 11),
    'intro_source': 'Recommended actions to improve your IISRI rating, ordered by severity and priority',
    'actions': actions,
    'remediation_impact': {
        'state': 'findings', 'title_source': 'Projected Rating After Remediation', 'source_pages': [10, 11],
        'current': {'grade': CUR_GRADE, 'score': int(CUR_SCORE), 'pool': int(POOL)},
        'projected': {'grade': PRO_GRADE, 'score': int(PRO_SCORE), 'pool': int(POOL)},
        'points_recoverable': int(find(r'recover up to (\d+) points', remediation_text)),
        'active_issues': {'total': ai_tot, 'privacy': ai_priv, 'vulnerability': ai_vuln, 'credentials': ai_cred},
        'conditional_on_rescan': True, 'narrative_source': remediation_text,
        'caption_source': 'Estimated improvement upon completion of the recommended actions',
        'review_flags': ['RF-G04'],
    },
    'note': 'Rank is source order, not a stable id. Estimated time is not a due date; required role is not an owner.',
}
privacy = {
    'number': '03', 'title': 'Privacy', 'group': 'assessment_details', 'state': 'findings',
    'state_label_source': f'{priv_pct}% PRIVACY SCORE', 'source_pages': pages(12, 16),
    'old_section_label': 'SECTION 1 OF 8 · PRIVACY',
    'intro_source': find(r'S C O R E (Evaluates privacy posture .+?PPDL\.)', TEXT[12]),
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
        'state': 'findings', 'state_label_source': 'Not found',
        'summary': 'A login portal was found without customer-protection terms.',   # section summary (split from privacy)
        'subtitle_source': 'Login / payment portal customer-protection clauses',
        'portal_detected': True, 'portal_url': portal_url, 'terms_found': False,
        'rows': [{'label': 'Login / Payment Portal', 'value_source': 'Detected'},
                 {'label': 'Portal URL', 'value_source': portal_url},
                 {'label': 'Terms & Conditions', 'value_source': 'Not found'},
                 {'label': 'Protects customer data & restricts unauthorised access', 'value_source': '# No'},
                 {'label': 'Notifies customer on incident / data breach', 'value_source': '# No'}],
        'narrative_source': tc_narr,
    },
    'sovereignty': {
        'state': 'findings', 'state_label_source': 'Not identified in published policies',
        'summary': 'Governing law could not be identified.',   # section summary (split from privacy)
        'subtitle_source': 'Where this supplier says disputes and legal obligations are handled', 'enabled': True,
        'observed_jurisdiction': nr('not_identified', source_label='Not identified in published policies'),
        'allowed_set': ['European Union (EU)'], 'match_state': 'unknown',
        'rows': [{'label': 'Governing law / courts we found', 'value_source': 'Not identified in published policies'},
                 {'label': 'Jurisdictions you accept', 'value_source': 'European Union (EU)'}],
        'narrative_source': find(r'(We could not identify .+?unresolved\.)', P16),
    },
    'residency': {
        'state': 'findings', 'state_label_source': hosting_src,
        'summary': 'Hosting is outside the preferred country.',   # section summary (split from privacy)
        'subtitle_source': "Where this organisation's public systems are hosted, compared with where you allow data to live",
        'enabled': True,
        'observed_hosting': [
            ({'country': None, 'hosts': n, 'state': 'unavailable', 'reason_code': 'country_code_placeholder',
              'source_label': f'XX ({n} hosts)', 'evidence_kind': nr()} if c == 'XX' else
             {'country': c, 'hosts': n, 'evidence_kind': nr()}) for c, n in HOSTS] + [
            {'country': None, 'hosts': unk_hosts, 'state': 'unavailable', 'reason_code': 'location_unknown',
             'source_label': f'{unk_hosts} hosts with unknown location'}],
        'allowed_set': ['Argentina'], 'match_state': 'mismatch',
        'rows': [{'label': 'Where we found their systems', 'value_source': hosting_src},
                 {'label': 'Countries you prefer', 'value_source': 'Argentina'}],
        'narrative_source': find(r'(We found public systems .+?require\.)', P16),
        'note': 'IP location is not proof of where all customer data is stored.',
    },
    'resourcing': {
        'state': 'findings', 'state_label_source': res_narr,
        'summary': 'Public materials show this organisation has a privacy function and a security function.',   # section summary (split from privacy)
        'subtitle_source': 'Whether this organisation publicly staffs security or privacy',
        'privacy_role_evidence': 'detected', 'security_role_evidence': 'detected',
        'roles_found': [{'role': role, 'sources': [s.strip() for s in srcs.split(';')]}],
        'roles_found_source': roles_src,
        'narrative_source': res_narr,
        'review_flags': ['RF-G05'],
    },
}
vulnerabilities = {
    'number': '04', 'title': 'Vulnerabilities', 'group': 'assessment_details', 'state': 'findings',
    'state_label_source': f'{vuln_pct}% VULNERABILITY SCORE', 'source_pages': pages(17, 27),
    'old_section_label': 'SECTION 2 OF 8 · VULNERABILITY',
    'intro_source': find(r'S C O R E (Covers external .+?digital assets\.)', TEXT[17]),
    'summary': f'{len(findings)} finding types were reported: {sevs.count("high")} high, {sevs.count("medium")} medium '
               f'and {sevs.count("low")} low, across the apex domain and {len(scan_sub)} scanned subdomains. The active '
               f'scan of {len(results)} hosts reported informational findings only.',
    'metrics': [
        metric('vulnerability_score', 'Vulnerability score', vuln_pct, 'percent', 'findings', f'{vuln_pct}%'),
        metric('finding_types', 'Finding types', len(findings), 'finding_types', 'findings',
               count_kind='distinct_finding_type'),
        metric('finding_types_critical', 'Critical finding types', sevs.count('critical'), 'finding_types', 'clear'),
        metric('finding_types_high', 'High finding types', sevs.count('high'), 'finding_types', 'findings'),
        metric('finding_types_medium', 'Medium finding types', sevs.count('medium'), 'finding_types', 'findings'),
        metric('finding_types_low', 'Low finding types', sevs.count('low'), 'finding_types', 'findings'),
        metric('asset_memberships', 'Finding-asset memberships', sum(len(f['affected_assets']) for f in findings),
               'memberships', 'findings', count_kind='membership_not_unique_assets',
               note=f'The remediation page counts {ai_vuln} vulnerability findings (RF-G04).'),
        metric('distinct_asset_labels', 'Distinct affected asset labels', len(asset_rows), 'asset_labels', 'findings',
               count_kind='distinct_labels_as_printed'),
    ],
    'scanned_assets': {'title_source': 'List of identified assets and observed security posture:',
                       'domains': scan_dom, 'subdomains': scan_sub},
    'severity_legend_source': copy.deepcopy(TPL['sections']['vulnerabilities']['severity_legend_source']),
    'breach_likelihood_legend_source': TPL['sections']['vulnerabilities']['breach_likelihood_legend_source'],
    'findings': findings,
    'assets_register_ref': 'appendices.d_evidence_registers.vulnerability_asset_register',
    'active_scan': {'state': 'findings', 'title_source': '## Vulnerability Scan Results',
                    'results_label_source': f'{n_results} scan results', 'results': results,
                    'review_flags': ['RF-G06']},
    'coverage_note_source': 'Note: No additional subdomains or externally exposed assets were identified during '
                            'this assessment.',
    'email_dns_controls': edc,
    'ip_reputation': {'state': 'pending_review', 'state_label_source': 'IP Reputation — Clean',
                      'reason_code': 'sentinel_meaning_unconfirmed',
                      'summary_source': f'Checked {len(ip_rows)} IP(s) against threat intelligence feeds.',
                      'ips_checked': len(ip_rows), 'rows': ip_rows, 'review_flags': ['RF-07']},
    'https_redirect': {'state': 'clear', 'state_label_source': '# HTTPS Redirect — Secure',
                       'result': 'redirects_to_https',
                       'narrative_source': 'HTTP correctly redirects to HTTPS. No insecure patterns detected.'},
    'review_flags': ['RF-08', 'RF-G04'],
}
certifications = {
    'number': '05', 'title': 'Certifications', 'group': 'assessment_details', 'state': 'clear',
    'state_label_source': '0% COMPLIANCE SCORE', 'source_pages': [2, 28],
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
lead = events[0]
data_leak_history = {
    'number': '06', 'title': 'Data breach and leak history', 'group': 'assessment_details', 'state': 'pending_review',
    'state_label_source': 'Last Valid Breach', 'reason_code': 'lead_event_not_eligible',
    'state_reason': 'The breach named as the last valid breach and "used in the rating calculation" is also marked '
                    '"(Reported Inaccurate)". Which event, if any, is scored is held for review.',
    'source_pages': [2] + pages(29, 36), 'old_section_label': 'SECTION 4 OF 8 · DATA LEAK HISTORY',
    'intro_source': TPL['sections']['data_leak_history']['intro_source'],
    'summary': f'{len(events)} breach records naming {DOMAIN} were listed: one as the last valid breach (marked '
               f'reported inaccurate) and {len(events) - 1} as historical records not directly used in scoring. '
               'Several describe credential compilations rather than a compromise of the organisation.',
    'metrics': [metric('data_leak_score', 'Data leak score', 0, 'percent', 'findings', '0%'),
                metric('events_reported', 'Leak events', leak_n, 'events', 'findings', f'{leak_n} leakes',
                       count_kind='reported'),
                metric('events_listed', 'Breach records listed', len(events), 'events', 'findings',
                       count_kind='returned_rows')],
    'last_valid_event': {'event_id': lead['event_id'],
                         'source_label': f'Last data leak has been reported on {last_date}.'},
    'last_valid_event_title_source': 'Last Valid Breach',
    'historical_title_source': 'Historical Breaches',
    'historical_subtitle_source': 'Past breach records for informational purposes — not directly used in current scoring',
    'events': events,
    'review_flags': ['RF-G03'],
}
fourth_party_vendors = copy.deepcopy(TPL['sections']['fourth_party_vendors'])
fourth_party_vendors['source_pages'] = [37]
assert fourth_party_vendors['empty_state_source']['text'] in TEXT[37]
assert fourth_party_vendors['empty_state_source']['coverage'] in TEXT[37]
credential_exposure = {
    'number': '08', 'title': 'Credential exposure', 'group': 'assessment_details', 'state': 'findings',
    'state_label_source': f'{cred_score}% CREDENTIAL SCORE', 'source_pages': [3, *pages(CRED_FIRST, CRED_LAST)],
    'old_section_label': 'SECTION 6 OF 8 · CREDENTIAL LEAK',
    'intro_source': TPL['sections']['credential_exposure']['intro_source'],
    'summary': f'The source reports {cred_n} (unit not defined by the source) and lists {len(reg_rows)} register rows '
               f'spanning {min(by_year)} to {max(by_year)}, {n_pw} of which include a password field category. '
               'The number of unique or active accounts is not known.',
    'attention_source': find(r'(Attention: .+?recommended\.)', TEXT[CRED_FIRST].replace(
        'Historical credential exposures were identified. Password resets and MFA enforcement Attention: are recommended.',
        'Attention: Historical credential exposures were identified. Password resets and MFA enforcement are recommended.')),
    'metrics': [
        metric('credential_score', 'Credential score', cred_score, 'percent', 'findings', f'{cred_score}%'),
        metric('found_headline', 'Found (headline)', cred_n, 'records_unit_unverified', 'findings', f'{cred_n} Found',
               count_kind='reported_headline', note='Unit not defined in source; not unique accounts.'),
        metric('returned_rows', 'Register rows shown', len(reg_rows), 'rows', 'findings', count_kind='returned_rows'),
        metric('rows_org_domain', 'Rows with organisation email domain', n_org, 'rows', 'findings'),
        metric('rows_org_subdomain', 'Rows with an organisation subdomain email domain', n_sub, 'rows', 'findings'),
        metric('rows_external_domain', 'Rows with another email domain', n_other, 'rows', 'findings'),
        metric('rows_unknown_email', 'Rows with Unknown Email', n_unknown, 'rows', 'findings', 'Unknown Email'),
        metric('rows_with_password', 'Rows exposing a password field', n_pw, 'rows', 'findings'),
        metric('rows_period_unknown', 'Rows with an Unknown exposure period', n_unk, 'rows', 'findings', 'Unknown'),
        metric('rows_no_field_categories', 'Rows with no exposed field listed', n_nofields, 'rows', 'findings'),
        metric('unique_accounts', 'Unique accounts', None, 'accounts', 'unavailable', reason_code='not_derivable',
               note='Masked labels are not a dedup key.'),
    ],
    'exposure_years_source': cred_years_src,
    'rows_by_exposure_year': [{'year': y, 'rows': n} for y, n in sorted(by_year.items(), reverse=True)],
    'rows_by_field_category': [{'field_category': c, 'rows': n} for c, n in by_cat.most_common()],
    'aggregation_note': 'Year and field counts are row memberships; a row can list several years or fields, so they '
                        'do not sum to the row total. Field categories are kept as printed: the source mixes field '
                        'keys (password) with breach data-class labels (Passwords).',
    'breach_source_name': nr(),
    'register_ref': 'appendices.d_evidence_registers.credential_register',
    'mitigations_source': mitig,
    'review_flags': ['RF-G02', 'RF-G07'],
}
cloud = copy.deepcopy(TPL['sections']['cloud_infrastructure'])
assert cloud['intro_source'] in CT
scanned = find(r'Last scanned: (\d\d\.\d\d\.\d{4})', CT)
provider = find(r'Detected Cloud Providers (\S+)', CT)
cloud.update(source_pages=[393], providers=[{'provider': provider, 'detection_methods': nr(), 'observed_at': nr()}],
             last_scanned=date(scanned, f'Last scanned: {scanned}'),
             summary=f'One cloud provider, {provider}, was detected. Detection shows provider use, not where all '
                     'customer data is stored.')
ai = {'number': '10', 'title': 'AI risk and governance', 'group': 'assessment_details', 'state': 'unavailable',
      'reason_code': 'section_not_in_source', 'source_pages': [],
      'state_reason': 'The source report has no AI usage page (its sections run 1 to 8 without one), so no AI '
                      'observation or result is available for this assessment.',
      'summary': 'AI risk is not covered by this source report.'}
tq = TPL['sections']['quantum_security']
assert tq['beta_notice_source'] in TEXT[405] and tq['intro_source'] in QT
for it in tq['scope_and_limitations_source']['scope_and_limitations']['items']:
    assert it in TEXT[406], it
quantum = {
    'number': '11', 'title': 'Quantum security', 'group': 'assessment_details', 'state': 'findings',
    'state_label_source': 'Quantum Security Overview', 'source_pages': pages(394, 406),
    'old_section_label': 'SECTION 8 OF 8 · QUANTUM SECURITY', 'intro_source': tq['intro_source'],
    'summary': f'The scan reported {H} high-risk, {M} moderate-risk and {L} low-risk findings (apex aggregate) across '
               f'{len(groups)} scopes; ML-KEM was detected on {len(pqc[0]["domains"])} scopes.',
    'beta_notice_source': tq['beta_notice_source'],
    'metrics': [metric('high_risk', 'High Risk', H, 'findings', 'findings', str(H), count_kind='reported_headline'),
                metric('moderate_risk', 'Moderate Risk', M, 'findings', 'clear', str(M), count_kind='reported_headline'),
                metric('low_risk', 'Low Risk', L, 'findings', 'findings', str(L), count_kind='reported_headline'),
                metric('partly_quantum_safe', 'Partly Quantum Safe', None, 'scopes', 'unavailable', '#',
                       reason_code='placeholder_in_source'),
                metric('pqc_detected', 'PQC Detected', PQC_N, 'scopes_inferred', 'findings', str(PQC_N),
                       count_kind='reported', note=f'Unit not labelled in source; equals the {PQC_N} ML-KEM domain chips.')],
    'findings_by_category': cats, 'pqc_detected': pqc, 'affected_protocols': protocols,
    'scope_summary': scope_summary,
    'scope_register_ref': 'appendices.d_evidence_registers.quantum_scope_register',
    'aggregation_note': f'Row {DOMAIN} is the apex aggregate: its rows sum to {apex_sum[0]} / {apex_sum[1]} / '
                        f'{apex_sum[2]}, the headline. The {len(groups) - 1} subdomain scopes sum to {sub_sum[0]} / '
                        f'{sub_sum[1]} / {sub_sum[2]} and are already inside the apex aggregate; do not add them.',
    'scope_and_limitations_source': copy.deepcopy(tq['scope_and_limitations_source']),
    'review_flags': ['RF-M04', 'RF-G08'],
}

# --- appendices ---------------------------------------------------------------------------
app = copy.deepcopy(TPL['appendices'])
assert app['a_about']['about_source'].replace('IISRI® CyberRank.ai ', '') in TEXT[406].replace(' IISRI® CyberRank.ai', '')
app['a_about']['source_pages'] = [406, 408]
app['a_about']['closing_source'] = f'Report generated on {GENERATED}'
rs_text = TEXT[407] + ' ' + TEXT[408]
for r in app['b_rating_scale']['rows']:
    assert ' '.join(r['meaning_source'].split()) in rs_text, r['grade']
    r['is_current_grade'] = r['grade'] == CUR_GRADE
app['b_rating_scale']['source_pages'] = [407, 408]
for needle in ('One rating for every vendor', 'Supply-chain aggregation', 'R(N) = 1'):
    assert needle in TEXT[409] + TEXT[410], needle
app['c_methodology']['source_pages'] = [409, 410]
app['d_evidence_registers'].update({
    'credential_register': {
        'source_pages': pages(CRED_FIRST, CRED_LAST), 'state': 'findings',
        'columns': ['id', 'email_domain', 'email_state', 'exposure_period_source', 'exposure_years',
                    'exposure_period_has_unknown', 'exposed_field_categories', 'breach_source_name', 'status',
                    'source_page'],
        'sanitised': True,
        'counts': {'returned_rows': len(reg_rows), 'total_rows': nr(), 'headline_found': cred_n,
                   'status': dict(status_counts)},
        'rows': reg_rows},
    'quantum_scope_register': {'source_pages': pages(395, 405), 'state': 'findings', 'columns': list(qrows[0]),
                               'counts': {'rows': len(qrows), 'scopes': len(groups),
                                          'root_aggregate_rows': len(apex)},
                               'rows': qrows},
    'vulnerability_asset_register': {'source_pages': pages(18, 23), 'state': 'findings',
                                     'columns': ['asset_label_source', 'finding_ids', 'finding_count', 'max_severity'],
                                     'counts': {'rows': len(asset_rows),
                                                'memberships': sum(r['finding_count'] for r in asset_rows)},
                                     'rows': asset_rows},
    'pqc_domain_register': {'source_pages': [395], 'state': 'findings', 'columns': ['domain', 'algorithm'],
                            'rows': [{'domain': d, 'algorithm': p['algorithm']} for p in pqc for d in p['domains']]},
})

meta = copy.deepcopy(TPL['meta'])
meta.update({
    'fixture_note': 'Values transcribed from the production PDF "Gmail - Cyber Risk Report" (old openhtmltopdf '
                    'pipeline, Indonesian-localised edition; English product terms stored, printed labels in '
                    'the _source_id fields). Not a backend payload. Generic appendices reuse the Claude fixture after a text check.',
    'extracted_at': '2026-10-15',
    'source_document': {'ref': 'P-GMAIL', 'file': 'Downloads/Gmail - Cyber Risk Report (1).pdf', 'sha256': SHA,
                        'pages': pdf.page_count, 'pdf_title': pdf.metadata['title'], 'producer': pdf.metadata['producer'],
                        'creator': pdf.metadata['creator'], 'pdf_created_at': '2026-10-15T01:00:50Z',
                        'pdf_modified_at': '2026-09-12T01:10:20Z', 'template_id': nr()},
    'sanitisation': {'applied': True,
                     'rule': 'No email local part, full email, personal name, password/token value or masked label. '
                             'Credential rows keep a synthetic id, the email domain when it is the assessed domain or '
                             "one of its subdomains (else 'other_domain'), exposure period, field categories and the "
                             'row status.',
                     'removed_fields': ['credential_register.email_masked'],
                     'source_rows_with_unmasked_local_part': n_unmasked,
                     'note': f'{n_unmasked} of {len(reg_rows) - n_unknown} email labels in the source have no masking '
                             "character in the local part (email_state 'unmasked_label_dropped'); all local parts are "
                             'dropped regardless. Other email domains are not named.'},
})
review_flags = [
    {'id': 'RF-01', 'pages': [10, 26], 'ref': 'fixture extraction',
     'text': 'Action 15 recommends moving DMARC from p=none, but the DMARC line prints an empty mode ("Enabled ( mode)").'},
    {'id': 'RF-07', 'pages': [26], 'ref': 'fixture extraction',
     'text': 'IP reputation prints "Clean" while every abuse score is the sentinel -1 and ISP / country are blank.'},
    {'id': 'RF-08', 'pages': [19, 23], 'ref': 'fixture extraction',
     'text': f'Affected-asset labels {", ".join(truncated)} are truncated host names (printed as is).'},
    {'id': 'RF-M01', 'pages': [1, 408], 'ref': 'fixture extraction',
     'text': f'Cover band text for {CUR_GRADE} ("risks are being managed") differs from the {CUR_GRADE} meaning in '
             'Appendix A ("issues are being managed").'},
    {'id': 'RF-M04', 'pages': list(range(395, 406)), 'ref': 'fixture extraction',
     'text': 'Scope rows for RSA and ECDHE print Risk "Low" ("covered by ML-KEM") with their count in the High column; '
             f'the {H} High-risk headline equals those rows.'},
    {'id': 'RF-G01', 'pages': [1], 'ref': 'fixture extraction',
     'text': 'Organisation description ends with a stray token ("access. jij"); kept verbatim.'},
    {'id': 'RF-G02', 'pages': [2, 3, 10, *pages(CRED_FIRST, CRED_LAST)], 'ref': 'fixture extraction',
     'text': f'Headline "{cred_n} Found" and action 14 ("{cred_n} affected accounts") vs {len(reg_rows)} register rows; '
             f'{n_other} rows are on other email domains, so the figure is neither rows nor organisation accounts.'},
    {'id': 'RF-G03', 'pages': [29], 'ref': 'fixture extraction',
     'text': 'The Last Valid Breach card says "This breach is used in the rating calculation" for an event marked '
             '"(Reported Inaccurate)". The 17-leak headline counts it with 16 historical records "not directly used in '
             'current scoring", yet the data-leak score is 0%.'},
    {'id': 'RF-G04', 'pages': [10, *pages(18, 25)], 'ref': 'fixture extraction',
     'text': f'Remediation counts {ai_vuln} vulnerability findings; the finding cards hold '
             f'{sum(len(f["affected_assets"]) for f in findings)} finding-asset memberships and the active scan '
             f'{sum(r["findings_reported"] for r in results)} informational findings. '
             f'{ai_tot} active issues = {ai_priv} + {ai_vuln} excludes the {ai_cred} credentials named in the same sentence.'},
    {'id': 'RF-G05', 'pages': [16], 'ref': 'fixture extraction',
     'text': f'Resourcing says the organisation has "a privacy function and a security function" but lists one role '
             f'({role}), a privacy role.'},
    {'id': 'RF-G06', 'pages': [24], 'ref': 'fixture extraction',
     'text': 'Active scan of imap.gmail.com reports "5 findings" and lists "Detailed Findings (3)".'},
    {'id': 'RF-G07', 'pages': pages(CRED_FIRST, CRED_LAST), 'ref': 'fixture extraction',
     'text': f'Field categories mix field keys (password, email) with breach data-class labels (Passwords, Email '
             f'addresses) and variants (pass); {len(by_cat)} distinct categories are kept as printed. {n_pwlike} rows '
             'list a password only under such a label, so a key-only password count misses them.'},
    {'id': 'RF-G08', 'pages': [394, 395], 'ref': 'fixture extraction',
     'text': f'Every category prints "· 1 domain" while the findings cover {len(groups)} scopes '
             f'(e.g. AES_128 — 15 findings).'},
]

report = {'meta': meta, 'identity': identity, 'snapshot': snapshot, 'rating': rating,
          'sections': {'executive_overview': executive_overview, 'priority_actions': priority_actions,
                       'privacy': privacy, 'vulnerabilities': vulnerabilities, 'certifications': certifications,
                       'data_leak_history': data_leak_history, 'fourth_party_vendors': fourth_party_vendors,
                       'credential_exposure': credential_exposure, 'cloud_infrastructure': cloud,
                       'ai_risk_governance': ai, 'quantum_security': quantum},
          'appendices': app, 'review_flags': review_flags}

# --- regression checks against the source PDF ----------------------------------------------
assert pdf.page_count == 410
assert (CUR_GRADE, CUR_SCORE, POOL, PRO_GRADE, PRO_SCORE) == ('CC', '86', '360', 'A', '280')
assert BAND_LABEL == 'Sedang' and SECTOR == 'Telekomunikasi'
assert (your, avg, top) == (29, 64, 99)
assert len(actions) == 15 and [a['priority'] for a in actions].count('high') == 14
assert [a.get('category') for a in actions].count('security') == 3 and len(WHY) == 2
assert all(a.get('why_this_matters_source') for a in actions[13:])
assert len(issues) == 13 == ai_priv and (n_priv, n_sec) == (10, 3)
assert (ai_tot, ai_vuln, ai_cred) == (224, 211, 15879)
assert HOSTS == [('United States of America', 20), ('XX', 5)] and unk_hosts == 30
assert len(scan_sub) == 54 and scan_dom == [DOMAIN]
assert len(findings) == 15 and (sevs.count("high"), sevs.count("medium"), sevs.count("low")) == (1, 6, 8)
assert [f['affected_assets_count'] == len(f['affected_assets']) for f in findings] == [True] * 15
assert sum(f['affected_assets_count'] for f in findings) == 183 and len(asset_rows) == 15
assert len(results) == n_results == 11 and sum(r['status'] == 'clean' for r in results) == 9
assert [(r['findings_reported'], len(r['findings'])) for r in results if r['findings']] == [(5, 3), (2, 2)]
assert mismatch == ['https://imap.gmail.com']
assert len(ip_rows) == 2
assert len(events) == 17 == leak_n and sum(e.get('validity_state') == 'reported_inaccurate' for e in events) == 1
assert sum(isinstance(e['records_affected'], dict) for e in events) == 5
assert sum(e['source_url'] is None for e in events) == 3
assert sum(isinstance(e['occurred_at'], dict) and e['occurred_at'].get('value') is None for e in events) == 1
assert len(reg_rows) == 5395 and n_unknown == 1 and status_counts == {'Open': 5395}
assert (n_org, n_sub, n_other) == (4096, 711, 587) and n_unmasked == 9
assert cred_score == 40 and len(mitig) == 4
assert provider == 'GCP'
assert (H, M, L, PQC_N) == (30, 0, 104, 15)
assert sum(c['issues'] for c in cats) == H + M + L == 134 and len(cats) == 4
assert sum(len(c['algorithms']) for c in cats) == 9
assert len(qrows) == 134 and len(groups) == 15, {k: len(v) for k, v in groups.items()}
assert apex_sum == (H, M, L), apex_sum
assert [p['domains_count'] for p in pqc] == [15] and len(protocols) == 1
assert sum(1 for r in qrows if r.get('risk_note_source')) == NOTE_WORDS == 30
assert {r['risk_level'] for r in qrows} == {'low'}
report["sections"] = restructure(report["sections"])
raw = json.dumps(report, ensure_ascii=False)
assert '@' not in raw and '*' not in raw, 'email-like token in fixture'
json.dump(report, open(out_path, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
open(out_path, 'a').write('\n')
print(out_path, len(raw), 'bytes; checks passed')
