"""Build data/demo-preview.json: a fully SYNTHETIC customer-preview payload (every section in a findings-style
state, all registers long enough for Appendix D) plus two obviously fake certificate documents in
data/demo-assets/.

    .venv/bin/python -I tools/extract/build_demo_fixture.py            # writes data/demo-preview.json
    .venv/bin/python -m cyberrank_report.build data/demo-preview.json -o ../Cyberrank_Cyber_Risk_Report_Demo_Preview.pdf

Data rules (asserted at the bottom): fictional organisation "Northwind Example Ltd"; every domain / URL / email
on RFC 2606 names (example.com / .net / .org); IPs only from the documentation ranges 192.0.2.0/24,
198.51.100.0/24, 203.0.113.0/24; account labels masked like the system (first and last character of the local
part kept); no person names; vendor and cloud names invented. Generated from scratch (no real fixture is read).
The generic product copy (about text, legends, methodology brief, quantum scope text) is the standard
Cyberrank template wording, the same in every report; it is not assessment data.
Deterministic: one fixed-seed Random; no clock reads.
"""
import json
import random
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data' / 'demo-preview.json'
ASSETS = ROOT / 'data' / 'demo-assets'
RNG = random.Random(20261001)

ORG, DOMAIN = 'Northwind Example Ltd', 'example.com'
ASSESSED, GENERATED = '2026-10-01', '2026-10-02'
ASSESSED_D = date.fromisoformat(ASSESSED)


def day(v, label=None):
    d = {'value': v, 'precision': 'day'}
    if label:
        d['source_label'] = label
    return d


def nr(code='not_printed_in_source', state='unavailable', **kw):
    return {'value': None, 'state': state, 'reason_code': code, **kw}


def metric(id_, label, value, unit, state='findings', **kw):
    return {'id': id_, 'label': label, 'value': value, 'unit': unit, 'state': state, **kw}


def sec(number, title, group, state, summary, **kw):
    return {'number': number, 'title': title, 'group': group, 'state': state, 'summary': summary, **kw}


def h(sub):
    return f'{sub}.{DOMAIN}' if sub else DOMAIN


def mask(local):
    return local[0] + '*' * (len(local) - 2) + local[-1]


OV, AD = 'overview_and_priorities', 'assessment_details'

# --- hosts and IPs (documentation ranges only) ------------------------------------------------------------
IP = {'': '203.0.113.10', 'www': '203.0.113.10', 'portal': '203.0.113.24', 'mail': '198.51.100.7',
      'api': '198.51.100.40', 'vpn': '192.0.2.15', 'legacy': '192.0.2.80'}
SUBS = ['www', 'portal', 'mail', 'api', 'vpn', 'dev', 'status', 'cdn', 'files', 'auth', 'legacy']


def asset(sub):
    return f'{h(sub)} / {IP[sub]}' if sub in IP and sub not in ('www',) else h(sub)


# --- 04 vulnerabilities ------------------------------------------------------------------------------------
VULNS = [  # (type, severity, likelihood %, rationale, affected subdomains)
    ('Remote desktop service exposed to the internet', 'critical', 38,
     'A remote desktop service answers on a public address. Exposed remote access services are a common entry '
     'point for brute-force and credential-stuffing attacks and should sit behind a VPN or zero-trust gateway.',
     ['legacy']),
    ('TLS 1.0 enabled', 'high', 22,
     'The server still accepts TLS 1.0, a protocol version with known weaknesses that modern clients no longer '
     'need. Attackers able to force a downgrade can weaken the protection of data in transit.',
     ['legacy', 'vpn', 'files']),
    ('Expired TLS certificate', 'high', 18,
     'The certificate presented by the host has passed its validity date. Browsers show a warning and users '
     'may learn to click through warnings, which makes interception attacks easier.',
     ['status']),
    ('HSTS not enforced', 'medium', 12,
     'The site does not send a Strict-Transport-Security header, so a first visit over plain HTTP can be '
     'intercepted before the redirect to HTTPS takes place.',
     ['', 'www', 'portal', 'files', 'status']),
    ('Outdated jQuery library', 'medium', 11,
     'A JavaScript library version with publicly documented cross-site scripting issues is loaded by the page. '
     'Updating the library removes the known weaknesses.',
     ['www', 'portal']),
    ('Missing Content-Security-Policy header', 'medium', 9,
     'No Content-Security-Policy is set. A policy limits where scripts may load from and reduces the impact '
     'of cross-site scripting.',
     ['', 'www', 'portal', 'auth']),
    ('Weak cipher suites (3DES) offered', 'medium', 8,
     'Legacy 3DES cipher suites are still offered during the TLS handshake. They are vulnerable to '
     'birthday-bound attacks on long-lived connections.',
     ['mail', 'vpn', 'legacy']),
    ('DMARC policy p=none', 'medium', 10,
     'The DMARC record is in monitoring mode only. Spoofed email that fails authentication is still delivered, '
     'which leaves the domain open to phishing and impersonation.',
     ['']),
    ('Server version disclosed in HTTP headers', 'low', 4,
     'The web server announces its product and version in response headers. This helps attackers pick '
     'matching exploits; the header can be suppressed.',
     ['www', 'api', 'dev', 'status', 'legacy']),
    ('Missing X-Content-Type-Options header', 'low', 3,
     'Without the nosniff option, browsers may guess content types, which can turn an uploaded file into '
     'executable content.',
     ['portal', 'files', 'cdn']),
    ('Session cookie without Secure flag', 'low', 5,
     'A session cookie can be sent over an unencrypted connection. Setting the Secure flag keeps it on HTTPS.',
     ['portal']),
    ('DNSSEC not enabled', 'low', 4,
     'The zone is not signed with DNSSEC, so resolvers cannot verify that DNS answers are authentic.',
     ['']),
]
FINDINGS = [{'finding_id': f'vuln-{i:02d}', 'finding_type': t, 'severity': s, 'severity_label_source': s.upper(),
             'rationale_source': r, 'affected_assets_count': len(a), 'affected_assets': [asset(x) for x in a],
             'breach_likelihood': {'value': p, 'unit': 'percent', 'likelihood_type': 'ai_derived_per_finding',
                                   'source_label': f'Breach Likelihood: {p}%'}}
            for i, (t, s, p, r, a) in enumerate(VULNS, start=1)]
SEV_ORDER = ['critical', 'high', 'medium', 'low']
asset_rows = {}
for f in FINDINGS:
    for a in f['affected_assets']:
        asset_rows.setdefault(a, []).append(f)
VULN_ASSETS = [{'asset_label_source': a, 'finding_ids': [f['finding_id'] for f in fs], 'finding_count': len(fs),
                'max_severity': min((f['severity'] for f in fs), key=SEV_ORDER.index)}
               for a, fs in asset_rows.items()]
sev_n = {s: sum(f['severity'] == s for f in FINDINGS) for s in SEV_ORDER}
memberships = sum(len(f['affected_assets']) for f in FINDINGS)


def scan(sub, status, fs=(), reported=None):
    r = {'target': f'https://{h(sub)}', 'status': status, 'scanned_at': {'value': '2026-10-01T09:42',
                                                                          'precision': 'minute'},
         'findings': list(fs)}
    if reported is not None:
        r['findings_reported'] = reported
    return r


def info(title, desc, impact, fix):
    return {'title': title, 'severity': 'info', 'severity_label_source': 'INFO', 'description': desc,
            'impact': impact, 'remediation': fix}


vulnerabilities = sec(
    '04', 'Vulnerabilities', AD, 'findings',
    f'{len(FINDINGS)} finding types were reported: {sev_n["critical"]} critical, {sev_n["high"]} high, '
    f'{sev_n["medium"]} medium and {sev_n["low"]} low, across {len(VULN_ASSETS)} affected assets.',
    state_label_source='38% VULNERABILITY SCORE',
    intro_source='Covers external security posture including network vulnerabilities, open services, '
                 'certificates and email security controls.',
    metrics=[metric('vulnerability_score', 'Vulnerability score', 38, 'percent', source_label='38%'),
             metric('finding_types', 'Finding types', len(FINDINGS), 'finding_types',
                    count_kind='distinct_finding_type'),
             *[metric(f'finding_types_{s}', f'{s.capitalize()} finding types', n, 'finding_types')
               for s, n in sev_n.items()],
             metric('asset_memberships', 'Finding-asset memberships', memberships, 'memberships',
                    count_kind='membership_not_unique_assets'),
             metric('distinct_asset_labels', 'Distinct affected asset labels', len(VULN_ASSETS), 'asset_labels',
                    count_kind='distinct_labels_as_printed')],
    scanned_assets={'title_source': 'List of identified assets and observed security posture:',
                    'domains': [DOMAIN], 'subdomains': [h(s) for s in SUBS]},
    severity_legend_source=[
        {'severity': 'critical_high', 'label': 'CRITICAL/HIGH', 'text': 'Serious vulnerabilities requiring immediate attention'},
        {'severity': 'medium', 'label': 'MEDIUM', 'text': 'Moderate risk issues that should be addressed'},
        {'severity': 'low', 'label': 'LOW', 'text': 'Minor security concerns with limited impact'}],
    breach_likelihood_legend_source='Indicates the estimated probability that this vulnerability could lead to a '
                                    'security breach. >=30% represents high risk, 15-29% represents moderate risk, '
                                    '<15% represents lower risk.',
    findings=FINDINGS,
    assets_register_ref='appendices.d_evidence_registers.vulnerability_asset_register',
    active_scan={'state': 'findings', 'results': [
        scan('', 'clean'), scan('www', 'clean'),
        scan('portal', 'scanned', [
            info('Login form served without rate limiting', 'Repeated login attempts were not slowed down.',
                 'Allows password-guessing at scale.', 'Add rate limiting or a progressive delay to the login form.'),
            info('Directory listing enabled on /assets/', 'The web server lists the files of a static folder.',
                 'Reveals file names that may help an attacker map the application.',
                 'Disable automatic directory listing.')], reported=2),
        scan('api', 'scanned', [
            info('API documentation publicly reachable', 'Interactive API documentation is reachable without '
                 'authentication.', 'Gives attackers a precise map of the endpoints.',
                 'Restrict the documentation to authenticated users or internal networks.')], reported=1)]},
    email_dns_controls={'state': 'findings', 'state_label_source': 'Email & DNS Security Controls', 'controls': [
        {'finding_id': 'ctrl-spf', 'control': 'SPF', 'result': 'enabled', 'state': 'clear',
         'status_label_source': 'Enabled', 'line_source': 'SPF: Enabled – authorised sending servers are published.'},
        {'finding_id': 'ctrl-dkim', 'control': 'DKIM', 'result': 'enabled', 'state': 'clear',
         'status_label_source': 'Enabled', 'line_source': 'DKIM: Enabled – supports email integrity and sender authenticity.',
         'key_strength_bits': {'value': 2048, 'unit': 'bits'}},
        {'finding_id': 'ctrl-dmarc', 'control': 'DMARC', 'result': 'enabled', 'state': 'findings',
         'status_label_source': 'Enabled (none mode)',
         'line_source': 'DMARC: Enabled (none mode) – visibility into spoofing attempts is present, but '
                        'failing mail is not blocked.',
         'dmarc_policy': {'value': 'none'}},
        {'finding_id': 'ctrl-dnssec', 'control': 'DNSSEC', 'result': 'missing_or_invalid', 'state': 'findings',
         'status_label_source': 'Missing / Invalid',
         'line_source': 'DNSSEC: Missing / Invalid – authenticates DNS responses and protects against DNS cache poisoning.'}],
        'guidance_source': 'It is recommended to progressively enforce DMARC policies to reduce phishing and '
                           'impersonation risks. DKIM RSA keys must be at least 2048 bits; 1024-bit keys are flagged '
                           'as a LOW finding. DNSSEC should be enabled (DS record + RRSIG + valid chain of trust) to '
                           'prevent DNS spoofing.'},
    ip_reputation={'state': 'findings', 'state_label_source': 'IP Reputation — 1 address reported',
                   'summary_source': 'Checked 5 IP(s) against threat intelligence feeds.', 'ips_checked': 5,
                   'rows': [{'ip_address': ip, 'isp': 'Example Transit Networks', 'country': cc,
                             'abuse_score': score, 'reports': rep}
                            for ip, cc, score, rep in (('203.0.113.10', 'GB', 0, 0), ('203.0.113.24', 'GB', 0, 0),
                                                       ('198.51.100.7', 'DE', 0, 0), ('198.51.100.40', 'US', 0, 0),
                                                       ('192.0.2.80', 'BR', 27, 4))]},
    https_redirect={'state': 'clear', 'state_label_source': '# HTTPS Redirect — Secure', 'result': 'redirects_to_https',
                    'what_checked': 'HTTP to HTTPS redirect on every scanned web host.',
                    'narrative_source': 'HTTP correctly redirects to HTTPS. No insecure patterns detected.'})

# --- 05 credential exposure ----------------------------------------------------------------------------------
LOCALS = ['accounts', 'billing', 'helpdesk', 'payroll', 'reports', 'treasury', 'operations', 'devteam',
          'marketing', 'audit', 'loans', 'invoices', 'support', 'compliance', 'backoffice', 'service',
          'analytics', 'webadmin', 'procurement', 'frontdesk', 'trading', 'ledger', 'claims', 'onboarding',
          'security', 'noreply', 'portaladmin', 'testuser', 'datateam', 'finance', 'records', 'sysops',
          'mobileapp', 'research', 'partners', 'notices', 'cards', 'branch07', 'teller12']
FIELDS = ['email', 'password', 'username', 'phone', 'ip', 'origin', 'name']
cred_rows = []
for i, local in enumerate(LOCALS, start=1):
    dom = DOMAIN if i % 4 else ('mail.example.com' if i % 8 else 'example.net')
    years = sorted(RNG.sample(range(2014, 2027), RNG.randint(1, 4)), reverse=True)
    unknown = i % 6 == 0
    fields = ['email'] + sorted(RNG.sample(FIELDS[1:], RNG.randint(1, 3)), key=FIELDS.index)
    cred_rows.append({
        'id': f'cred-{i:04d}', 'email_domain': dom if dom != 'example.net' else 'external',
        'email_state': 'masked_label_present', 'account_label_masked': f'{mask(local)}@{dom}',
        'exposure_period_source': ', '.join(map(str, years)) + (', Unknown' if unknown else ''),
        'exposure_years': years, 'exposure_period_has_unknown': unknown,
        'exposed_field_categories': fields, 'breach_source_name': nr(),
        'status': 'Resolved' if i % 5 == 0 else 'Open'})
cred_rows.append({'id': f'cred-{len(cred_rows) + 1:04d}', 'email_domain': None, 'email_domain_state': 'unavailable',
                  'email_domain_reason_code': 'unknown_email_in_source', 'email_state': 'unknown_email',
                  'account_label_masked': 'Unknown Email', 'exposure_period_source': 'Unknown', 'exposure_years': [],
                  'exposure_period_has_unknown': True, 'exposed_field_categories': ['password'],
                  'breach_source_name': nr(), 'status': 'Open'})
N_CRED = len(cred_rows)
years_all = sorted({y for r in cred_rows for y in r['exposure_years']}, reverse=True)
by_year = [{'year': y, 'rows': sum(y in r['exposure_years'] for r in cred_rows)} for y in years_all]
by_field = [{'field_category': f, 'rows': n} for f in FIELDS
            if (n := sum(f in r['exposed_field_categories'] for r in cred_rows))]
count = lambda pred: sum(1 for r in cred_rows if pred(r))  # noqa: E731
status_counts = {s: count(lambda r, s=s: r['status'] == s) for s in ('Open', 'Resolved')}

credential_exposure = sec(
    '05', 'Credential exposure', AD, 'findings',
    f'{N_CRED} exposed account records were found for {DOMAIN} and its mail subdomain; '
    f'{status_counts["Open"]} are still open.',
    state_label_source='45% CREDENTIAL SCORE',
    intro_source="Identifies credential leaks associated with the organization's domains in breach "
                 'compilations and monitored online sources.',
    attention_source='Attention: Historical credential exposures were identified. Password resets and '
                     'multi-factor authentication are recommended for the affected accounts.',
    metrics=[metric('credential_score', 'Credential score', 45, 'percent', source_label='45%'),
             metric('found_headline', 'Found (headline)', N_CRED, 'records_unit_unverified',
                    source_label=f'{N_CRED} Found', count_kind='reported_headline'),
             metric('returned_rows', 'Register rows shown', N_CRED, 'rows', count_kind='returned_rows'),
             metric('rows_org_domain', 'Rows with organisation email domain', count(lambda r: r['email_domain'] == DOMAIN), 'rows'),
             metric('rows_org_subdomain', 'Rows with an organisation subdomain email domain',
                    count(lambda r: r['email_domain'] == 'mail.example.com'), 'rows'),
             metric('rows_external_domain', 'Rows with another email domain', count(lambda r: r['email_domain'] == 'external'), 'rows'),
             metric('rows_unknown_email', 'Rows with Unknown Email', count(lambda r: r['email_state'] == 'unknown_email'), 'rows',
                    source_label='Unknown Email'),
             metric('rows_with_password', 'Rows with the field key ‘password’',
                    count(lambda r: 'password' in r['exposed_field_categories']), 'rows'),
             metric('rows_period_unknown', 'Rows with an Unknown exposure period',
                    count(lambda r: r['exposure_period_has_unknown']), 'rows', source_label='Unknown'),
             metric('unique_accounts', 'Unique accounts', None, 'accounts', 'unavailable', reason_code='not_derivable',
                    note='Masked labels are not a dedup key.')],
    exposure_years_source='-'.join(map(str, sorted(years_all))) + '-Unknown',
    rows_by_exposure_year=by_year, rows_by_field_category=by_field,
    aggregation_note='Year and field counts are row memberships; a row can list several years and fields.',
    breach_source_name=nr(), register_ref='appendices.d_evidence_registers.credential_register',
    mitigations_source=['Force password resets for all affected accounts',
                        'Enable multi-factor authentication across all user access points',
                        'Review password hygiene and access policies',
                        'Monitor authentication logs for anomalous activity'])

# --- 06 data breach and leak history -------------------------------------------------------------------------


def age(d):
    return (ASSESSED_D - date.fromisoformat(d)).days


EVENTS = [
    {'event_id': 'leak-01', 'entity_link': h('portal'), 'event_type': 'data_leak',
     'occurred_at': day('2025-11-14'), 'disclosed_at': day('2025-11-20'), 'listed_as': 'last_valid_breach',
     'rating_use_label_source': 'This breach is used in the rating calculation', 'scoring_eligible': True,
     'records_affected': 12400, 'records_unit': 'accounts', 'records_scope': 'organisation',
     'date_basis': 'disclosed_at', 'age_days_at_assessment': age('2025-11-20'), 'demerit_applied': 12,
     'description_source': 'A misconfigured storage bucket behind the customer portal exposed account names, '
                           'email addresses and hashed passwords for a limited period before it was closed.',
     'source_url': 'https://news.example.net/2025/11/portal-exposure'},
    {'event_id': 'leak-02', 'entity_link': DOMAIN, 'event_type': 'third_party_breach',
     'occurred_at': day('2024-03-02'), 'listed_as': 'historical', 'scoring_eligible': False,
     'scoring_reason': 'listed under Historical Breaches: not directly used in current scoring',
     'records_affected': 2100000, 'records_unit': 'records', 'records_scope': 'aggregate_multi_service',
     'date_basis': 'occurred_at', 'age_days_at_assessment': age('2024-03-02'), 'demerit_applied': 0,
     'description_source': 'A marketing-automation provider used by several companies reported unauthorised '
                           'access to contact lists; addresses on the organisation domain appear in the aggregate.',
     'source_url': 'https://security-news.example.org/2024/03/marketing-platform-incident'},
    {'event_id': 'leak-03', 'entity_link': h('files'), 'event_type': 'data_leak',
     'occurred_at': day('2023-06-19'), 'validity_state': 'resolved', 'listed_as': 'historical',
     'records_affected': 850, 'records_unit': 'accounts', 'records_scope': 'organisation',
     'date_basis': 'occurred_at', 'age_days_at_assessment': age('2023-06-19'), 'demerit_applied': 0,
     'description_source': 'A shared file link indexed by a search engine exposed a supplier contact sheet. The '
                           'organisation removed the link and marked the event resolved.',
     'source_url': 'https://news.example.net/2023/06/file-share-index'},
]
data_leak_history = sec(
    '06', 'Data breach and leak history', AD, 'findings',
    '3 breach events were found in the sources checked: one is used in the rating, one is historical and one '
    'was marked resolved by the organisation.',
    state_label_source='Last Valid Breach',
    intro_source='Documents publicly known data leak incidents. Historical data leaks are listed for context.',
    metrics=[metric('data_leak_score', 'Data leak score', 55, 'percent', source_label='55%'),
             metric('events_reported', 'Leak events', 3, 'events', source_label='3 leaks', count_kind='reported')],
    last_valid_event={'event_id': 'leak-01', 'source_label': 'Last data leak has been reported on 20.11.2025.'},
    events=EVENTS)

# --- 08 residency / 07 sovereignty ---------------------------------------------------------------------------
PREF = ['GB', 'DE', 'IE', 'US', 'SG', 'AU']
HOSTING = [('GB', 'United Kingdom', 9), ('DE', 'Germany', 4), ('US', 'United States of America', 5),
           ('SG', 'Singapore', 2), ('AU', 'Australia', 2), ('BR', 'Brazil', 1)]
observed_hosting = [{'country_code': cc, 'country': name, 'hosts': n, 'evidence_kind': {'value': 'IP geolocation'},
                     'match_state': 'match' if cc in PREF else 'mismatch'} for cc, name, n in HOSTING]
observed_hosting.append({'country': None, 'hosts': 1, 'state': 'unavailable', 'reason_code': 'location_unknown',
                         'evidence_kind': {'value': 'IP geolocation'}})
hosted = ', '.join(f'{name} ({n} host{"s" if n > 1 else ""})' for _, name, n in HOSTING) + ', 1 host with unknown location'

data_sovereignty = sec(
    '07', 'Data sovereignty', AD, 'clear',
    'The governing law found in the published terms (England and Wales) is within the jurisdictions you accept.',
    state_label_source='United Kingdom (England and Wales)',
    intro_source='Where this supplier says disputes and legal obligations are handled',
    enabled=True, observed_jurisdiction={'value': 'United Kingdom'},
    allowed_set=['United Kingdom', 'European Union (EU)'], match_state='match',
    quote_source='These terms and any dispute arising from them are governed by the laws of England and Wales.',
    rows=[{'label': 'Governing law / courts we found', 'value_source': 'England and Wales (United Kingdom)'},
          {'label': 'Jurisdictions you accept', 'value_source': 'United Kingdom, European Union (EU)'}],
    narrative_source='The terms of service name the courts of England and Wales, which matches the jurisdictions '
                     'your organisation accepts.')

data_residency = sec(
    '08', 'Data residency', AD, 'findings',
    'Most public systems are hosted in preferred countries; one host is in Brazil, outside the preference, and '
    'one host could not be located.',
    state_label_source=hosted,
    intro_source="Where this organisation's public systems are hosted, compared with where you allow data to live",
    enabled=True, observed_hosting=observed_hosting, allowed_set=PREF, match_state='mismatch',
    rows=[{'label': 'Where we found their systems', 'value_source': hosted},
          {'label': 'Countries you prefer', 'value_source': 'United Kingdom, Germany, Ireland, United States, Singapore, Australia'}],
    narrative_source='We found one public system hosted in a country outside the countries you prefer.')

legal_terms = sec(
    '09', 'Legal terms & conditions', AD, 'findings',
    'A customer login portal was found; its terms protect customer data but do not commit to breach notification.',
    state_label_source='Detected', intro_source='Login / payment portal customer-protection clauses',
    portal_detected=True, portal_url=f'https://{h("portal")}/login', terms_found=True,
    rows=[{'label': 'Login / Payment Portal', 'value_source': '# Detected'},
          {'label': 'Clause: protects customer data', 'value_source': '# Yes'},
          {'label': 'Clause: notifies customers on breach', 'value_source': '# No'},
          {'label': 'Terms page', 'value_source': f'https://www.{DOMAIN}/legal/terms'}],
    narrative_source='The portal terms describe how customer data is protected, but we found no clause that '
                     'commits to notifying customers after a breach.')

security_resourcing = sec(
    '12', 'Security resourcing', AD, 'findings',
    'Public materials show a dedicated security function and a named data protection role.',
    state_label_source='Public materials show this organisation has a security and a privacy function.',
    intro_source='Whether this organisation publicly staffs security or privacy',
    privacy_role_evidence='detected', security_role_evidence='detected',
    roles_found=[{'role': 'Data Protection Officer', 'sources': ['Company website (privacy notice)']},
                 {'role': 'Chief Information Security Officer', 'sources': ['Company website', 'Careers page']}],
    narrative_source='Public materials show this organisation has a security function and a data protection officer.')

# --- 03 privacy ----------------------------------------------------------------------------------------------
ISSUES = [
    ('privacy', 'Vague retention periods – the policy does not say how long customer records are kept or when '
                'they are deleted.'),
    ('privacy', 'Cookie use is broad – analytics and advertising cookies are mentioned without listing their '
                'purposes or providers.'),
    ('security', 'No breach notification commitment – the policy does not say whether or when customers are '
                 'told about a personal data breach.'),
    ('privacy', 'International transfers unclear – transfers outside the United Kingdom are mentioned without '
                'naming the safeguards used.'),
    ('privacy', 'Data subject rights incomplete – the right to data portability is not described.'),
    ('security', 'Contact route for privacy requests is a web form only – no postal or email route is given.'),
]
privacy = sec(
    '03', 'Privacy', AD, 'findings',
    f'One privacy policy was assessed at 64% with {len(ISSUES)} active issues.',
    state_label_source='64% PRIVACY SCORE',
    intro_source='Evaluates privacy posture through publicly available data, privacy policies and disclosures.',
    policy={'state': 'findings', 'state_label_source': '64% Privacy Score',
            'policy_state': {'value': 'valid_assessed', 'state': 'findings', 'source_page': 2,
                             'source_label': f'Privacy policy exists but has {len(ISSUES)} active risks requiring attention'},
            'policy_source': {'value': f'https://www.{DOMAIN}/privacy'},
            'metrics': [metric('privacy_score', 'Privacy Score', 64, 'percent', source_label='64%'),
                        metric('active_issues', 'Active Issues', len(ISSUES), 'issues', count_kind='reported'),
                        metric('policies_found', 'Policies Found', 1, 'policies')],
            'areas': nr(note='Per-area A-P scores not printed.'),
            'issues': [{'label': f'Issue {i}', 'category': c, 'text': t} for i, (c, t) in enumerate(ISSUES, start=1)]})

# --- 10 AI ---------------------------------------------------------------------------------------------------
ai_risk_governance = sec(
    '10', 'AI risk and governance', AD, 'findings',
    'AI is used in customer-facing services; no public AI policy was found and the privacy policy explains AI use '
    'only in part.',
    state_label_source='2 AI ISSUES', title_source='AI Usage & Risk Classification',
    intro_source="What we observed about this organisation's use of artificial intelligence",
    metrics=[metric('ai_issues', 'AI issues', 2, 'issues', source_label='2')],
    narrative_observation={
        'is_assessment_result': True,
        'subtitle_source': "What we observed about this organisation's use of artificial intelligence",
        'text_source': 'The organisation appears to use AI in customer-facing services. Its support site embeds a '
                       'chat assistant, its content security policy allows calls to an AI service endpoint, and its '
                       'careers page advertises machine-learning roles. Credit decisioning is listed among its '
                       'services, an area the EU AI Act treats as high risk.',
        'signals_observed': [
            {'signal': 'ai_infrastructure', 'method': 'csp_header_analysis',
             'example_source': 'CSP destination: api.ai-vendor.example.net'},
            {'signal': 'ai_assistant_mention', 'method': 'public_pages',
             'example_source': f'Chat assistant widget on support.{DOMAIN}'},
            {'signal': 'ai_hiring', 'method': 'careers_pages',
             'example_source': 'Careers page advertises a machine-learning engineer role'}],
        'stated_conclusion_source': 'This organisation uses AI in customer-facing services.',
        'annex_iii_high_risk_sector': {'value': 'apparent', 'state': 'findings',
                                       'source_label': 'Credit decisioning is listed among its services (EU AI Act Annex III).'},
        'public_ai_policy': {'value': 'not_found', 'state': 'findings',
                             'source_label': 'We could not find a public AI policy explaining how they use or govern AI.'},
        'privacy_policy_ai_disclosure': {'value': 'partial', 'state': 'partial',
                                         'source_label': 'The privacy policy mentions automated decisions but not the '
                                                         'chat assistant.'}})

# --- 11 quantum ----------------------------------------------------------------------------------------------
ALGOS = [  # category, algorithm, protocols, PQC alternative, base risk
    ('Public-key cryptography', 'RSA_2048', ['TLS_1_2', 'TLS_1_3'], 'ML-DSA', 'high'),
    ('Public-key cryptography', 'ECDSA_P256', ['TLS_1_3'], 'ML-DSA', 'high'),
    ('Key exchange', 'ECDHE_X25519', ['TLS_1_3'], 'ML-KEM', 'high'),
    ('Key exchange', 'DHE_2048', ['TLS_1_2'], 'ML-KEM', 'high'),
    ('Symmetric cryptography', 'AES_128', ['TLS_1_2'], None, 'moderate'),
    ('Symmetric cryptography', 'AES_256', ['TLS_1_3'], None, 'low'),
    ('Hash functions', 'SHA1', ['TLS_1_2'], None, 'moderate'),
    ('Hash functions', 'SHA256', ['TLS_1_2', 'TLS_1_3'], None, 'low'),
]
Q_SUBS = ['www', 'portal', 'mail', 'api', 'vpn', 'files', 'auth', 'status']
ML_KEM = {'www', 'portal', 'api', 'auth'}
q_sub_rows = []
for sub in Q_SUBS:
    for cat, alg, protos, alt, risk in ALGOS:
        if RNG.random() < 0.3:
            continue
        n = RNG.randint(1, 3)
        covered = cat == 'Key exchange' and sub in ML_KEM
        lvl = 'low' if covered else risk
        q_sub_rows.append({'subdomain': h(sub), 'scope_level': 'subdomain', 'category': cat, 'pre_qc_algorithm': alg,
                           'risk_level': lvl, 'post': 'ML-KEM' if covered else None,
                           'high': n * (lvl == 'high'), 'moderate': n * (lvl == 'moderate'), 'low': n * (lvl == 'low')})
apex = []
for cat, alg, protos, alt, risk in ALGOS:
    rs = [r for r in q_sub_rows if r['pre_qc_algorithm'] == alg]
    if rs:
        apex.append({'subdomain': DOMAIN, 'scope_level': 'root_aggregate', 'category': cat, 'pre_qc_algorithm': alg,
                     'risk_level': risk, 'post': 'ML-KEM' if any(r['post'] for r in rs) else None,
                     **{k: sum(r[k] for r in rs) for k in ('high', 'moderate', 'low')}})
q_rows = []
for i, r in enumerate(apex + q_sub_rows, start=1):
    row = {'id': f'qscope-{i:04d}', 'subdomain': r['subdomain'], 'scope_level': r['scope_level'],
           'category': r['category'], 'pre_qc_algorithm': r['pre_qc_algorithm'], 'source': 'standard scan',
           'post_qc_source': r['post'] or '—', 'post_qc_algorithm': r['post'], 'risk_level': r['risk_level'],
           'high': r['high'], 'moderate': r['moderate'], 'low': r['low']}
    if r['post'] is None:
        row.update(post_qc_algorithm_state='unavailable', post_qc_algorithm_reason_code='dash_in_source')
    q_rows.append(row)
HL = {k: sum(r[k] for r in apex) for k in ('high', 'moderate', 'low')}
scopes = [DOMAIN] + [h(s) for s in Q_SUBS]
scope_summary = []
for s in scopes:
    rs = [r for r in q_rows if r['subdomain'] == s]
    scope_summary.append({'subdomain': s, 'scope_level': rs[0]['scope_level'], 'rows': len(rs),
                          **{k: sum(r[k] for r in rs) for k in ('high', 'moderate', 'low')},
                          'ml_kem_on_key_exchange': any(r['post_qc_algorithm'] == 'ML-KEM' for r in rs),
                          'algorithms_absent': [a for _, a, *_ in ALGOS if a not in {r['pre_qc_algorithm'] for r in rs}]})
pqc_domains = [DOMAIN] + [h(s) for s in Q_SUBS if s in ML_KEM]
cats = list(dict.fromkeys(c for c, *_ in ALGOS))
findings_by_category = []
for cat in cats:
    algs = []
    for c, alg, protos, alt, risk in ALGOS:
        a = next((r for r in apex if r['pre_qc_algorithm'] == alg), None)
        if c != cat or not a:
            continue
        x = {'algorithm': alg, 'findings': a['high'] + a['moderate'] + a['low'], 'protocol_labels': protos,
             'pqc_alternative_available': alt, 'risk_level': risk}
        if alt is None:
            x.update(pqc_alternative_available_state='unavailable',
                     pqc_alternative_available_reason_code='not_printed_in_source')
        algs.append(x)
    n_dom = len({r['subdomain'] for r in q_sub_rows if r['category'] == cat})
    findings_by_category.append({'category': cat, 'issues': sum(a['findings'] for a in algs),
                                 'domains_source_label': f'{n_dom} domains', 'algorithms': algs})

quantum_security = sec(
    '11', 'Quantum security', AD, 'findings',
    f'The scan reported {HL["high"]} high-risk, {HL["moderate"]} moderate-risk and {HL["low"]} low-risk findings; '
    f'ML-KEM post-quantum key exchange was detected on {len(pqc_domains)} domains.',
    state_label_source='Quantum Security Overview',
    intro_source='Assesses exposure to quantum computing threats by analyzing cryptographic algorithms used '
                 'by public services.',
    beta_notice_source='Quantum Vulnerability is currently in beta. You may encounter incomplete data or ongoing '
                       'changes as we refine the experience.',
    metrics=[metric('high_risk', 'High Risk', HL['high'], 'findings', count_kind='reported_headline'),
             metric('moderate_risk', 'Moderate Risk', HL['moderate'], 'findings', count_kind='reported_headline'),
             metric('low_risk', 'Low Risk', HL['low'], 'findings', count_kind='reported_headline'),
             metric('pqc_detected', 'PQC Detected', len(pqc_domains), 'domains', count_kind='reported')],
    findings_by_category=findings_by_category,
    pqc_detected=[{'algorithm': 'ML-KEM', 'algorithm_alias': 'CRYSTALS-Kyber', 'purpose': 'Key exchange / encryption',
                   'status_source': 'Status: NIST standardized (FIPS 203)', 'domains_count': len(pqc_domains),
                   'domains': pqc_domains}],
    affected_protocols=[
        {'protocol': 'TLS_1_3', 'algorithms': ['ECDSA_P256', 'ECDHE_X25519', 'AES_256', 'SHA256'],
         'pqc_source': 'ML-KEM available', 'risk_level': 'low'},
        {'protocol': 'TLS_1_2', 'algorithms': ['RSA_2048', 'DHE_2048', 'AES_128', 'SHA1'],
         'pqc_source': 'No PQC available on TLS 1.2', 'risk_level': 'high'}],
    scope_summary=scope_summary,
    scope_register_ref='appendices.d_evidence_registers.quantum_scope_register',
    aggregation_note=f'Row {DOMAIN} is the apex aggregate: its rows sum the subdomain rows by algorithm.',
    scope_and_limitations_source={
        'title': 'Our Post-Quantum Safety Scan Results',
        'scope_and_limitations': {
            'title': 'a. Scope and limitations',
            'intro': 'We cannot guarantee that a domain or organization is fully quantum-safe based on the results of '
                     'this assessment because:',
            'items': ['Post-quantum cryptography is an evolving field. Cryptographic standards, implementations, and '
                      'the understanding of quantum computing capabilities continue to develop. Future advances may '
                      'affect the security of algorithms considered secure today.',
                      'This is a non-invasive, external assessment. Unless an internal CyberRank agent is deployed, the '
                      'scan evaluates only externally observable services and configurations. Internal systems, '
                      'private networks, and services that are not externally accessible are outside the scope of '
                      'this assessment.']},
        'post_quantum_readiness': {
            'title': 'b. Post-quantum readiness',
            'intro': 'A domain can only be considered fully post-quantum ready if it:',
            'items': ['Supports post-quantum cryptographic (PQC) algorithms for secure connections; and',
                      'Disables legacy TLS versions (TLS 1.0, TLS 1.1, and TLS 1.2).'],
            'closing': 'Allowing legacy TLS versions enables clients to establish connections using classical '
                       'cryptographic algorithms. If an attacker can force or negotiate the use of an older protocol '
                       'version (a protocol downgrade), the connection may lose the protections provided by '
                       'post-quantum cryptography.'}})

# --- 13 certifications ---------------------------------------------------------------------------------------
ND = nr('not_detected')
CERTS = [
    {'certificate_id': 'cert-01', 'standard': 'ISO/IEC 27001', 'standard_full_name': 'Information Security Management',
     'origin': 'detected', 'origin_label_source': 'SYSTEM DETECTED', 'source_url': f'https://trust.{DOMAIN}/compliance',
     'category': {'value': 'security'}, 'approval_state': {'value': 'pending'}, 'valid_from': ND, 'valid_until': ND,
     'eligibility': {'value': True}, 'credit_applied': {'value': 20, 'unit': 'points'}},
    {'certificate_id': 'cert-02', 'standard': 'ISO/IEC 27001', 'standard_full_name': 'Information Security Management',
     'origin': 'uploaded', 'origin_label_source': 'UPLOADED', 'category': {'value': 'security'},
     'approval_state': {'value': 'approved'}, 'valid_from': day('2025-03-01'), 'valid_until': day('2028-02-29'),
     'issuer': {'value': 'Example Certification Body'},
     'scope_source': {'value': 'Provision of online banking and payment services'},
     'document': {'value': 'demo-assets/demo-certificate-iso27001.pdf'},
     'eligibility': {'value': True}, 'credit_applied': {'value': 40, 'unit': 'points'}},
    {'certificate_id': 'cert-03', 'standard': 'SOC 2', 'standard_full_name': 'Security, Availability, Confidentiality',
     'origin': 'uploaded', 'origin_label_source': 'UPLOADED', 'category': {'value': 'both'},
     'approval_state': {'value': 'approved'}, 'valid_from': day('2026-01-01'), 'valid_until': day('2026-12-31'),
     'issuer': {'value': 'Sample Assurance Partners'},
     'scope_source': {'value': 'Customer portal and payment API (Type II)'},
     'document': {'value': 'demo-assets/demo-certificate-soc2.png'},
     'eligibility': {'value': True}, 'credit_applied': {'value': 40, 'unit': 'points'}},
    {'certificate_id': 'cert-04', 'standard': 'PCI DSS', 'standard_full_name': 'Payment Card Industry Data Security Standard',
     'origin': 'detected', 'origin_label_source': 'SYSTEM DETECTED', 'source_url': f'https://www.{DOMAIN}/security',
     'category': {'value': 'security'}, 'approval_state': {'value': 'approved'}, 'valid_from': day('2025-10-15'),
     'valid_until': day('2026-10-14'), 'expired': {'value': False},
     'eligibility': {'value': True}, 'credit_applied': {'value': 40, 'unit': 'points'}},
]
certifications = sec(
    '13', 'Certifications', AD, 'findings',
    '3 certifications are on record (4 certificate records): ISO/IEC 27001 (detected and uploaded), SOC 2 '
    '(uploaded) and PCI DSS (detected).',
    state_label_source='68% COMPLIANCE SCORE',
    intro_source='Outlines industry certifications and compliance frameworks held by the organisation.',
    metrics=[metric('compliance_score', 'Compliance score', 68, 'percent', source_label='68%'),
             metric('certifications_headline', 'Certifications', 3, 'certifications', source_label='3 certifications',
                    count_kind='reported_headline'),
             metric('certificates_detected', 'Certificate records', len(CERTS), 'certificates', count_kind='cards_listed')],
    certificates=CERTS,
    reference_standards={'is_vendor_evidence': False, 'title_source': 'Commonly Referenced Standards', 'items': [
        {'standard': 'ISO/IEC 27001', 'description': 'Information Security Management'},
        {'standard': 'ISO/IEC 27701', 'description': 'Privacy Information Management'},
        {'standard': 'SOC 2', 'description': 'Security, Availability, Confidentiality'},
        {'standard': 'GDPR', 'description': 'Data protection and privacy regulation'}]})

# --- 14 fourth-party vendors ---------------------------------------------------------------------------------
VENDOR_NAMES = [
    ('Example Cloud Hosting', 'information technology & services'), ('Sample Payments Co', 'financial services'),
    ('Demo Analytics Group', 'information technology & services'), ('Placeholder CRM Systems', 'computer software'),
    ('Example Mail Relay', 'information technology & services'), ('Sample Identity Services', 'computer & network security'),
    ('Example Document Signing', 'computer software'), ('Demo Logistics Partners', 'logistics & supply chain'),
    ('Sample Card Processing', 'financial services'), ('Example Backup Vault', 'information technology & services'),
    ('Demo Marketing Suite', 'marketing & advertising'), ('Example Fraud Screening', 'computer & network security'),
    ('Sample Payroll Bureau', 'human resources'), ('Example Status Pages', 'computer software'),
    ('Demo Help Desk Tools', 'computer software'), ('Sample Content Delivery', 'information technology & services'),
    ('Example Credit Bureau', 'financial services'), ('Demo Survey Platform', 'marketing & advertising'),
    ('Sample Telephony Network', 'telecommunications'), ('Example Code Hosting', 'computer software'),
    ('Demo Office Supplies', 'wholesale'), ('Sample Legal Archive', 'legal services'),
    ('Example Chat Widget', 'computer software'), ('Demo Map Tiles', 'information technology & services'),
    ('Sample Tax Engine', 'financial services'), ('Example Video Meetings', 'telecommunications'),
    ('Demo Print Services', 'printing'), ('Sample HR Portal', 'human resources'),
    ('Example Log Monitoring', 'computer & network security'), ('Demo Courier Network', 'logistics & supply chain'),
    ('Sample Translation Hub', 'translation & localization'), ('Example SMS Gateway', 'telecommunications'),
    ('Demo Font Library', 'design'), ('Sample Data Brokers', 'marketing & advertising'),
]
GRADE_BANDS = [('AAA', 'low'), ('AA', 'low'), ('A', 'low'), ('BBB', 'medium'), ('BB', 'medium'),
               ('B', 'high'), ('CCC', 'high'), ('CC', 'critical')]
GRADE_W = [4, 6, 6, 6, 5, 3, 2, 1]
vendors = []
for i, (name, cat) in enumerate(VENDOR_NAMES, start=1):
    slug = re.sub(r'[^a-z]', '', name.lower().split(' ', 1)[1])
    tld = ('example.net', 'example.org')[i % 2]
    v = {'vendor_id': f'vendor-{i:02d}', 'name': name, 'domain': f'{slug}.{tld}', 'category': cat,
         'assessed_membership': True, 'assessed_at': day(f'2026-09-{RNG.randint(1, 28):02d}'),
         'evidence': nr(note='Discovery method per vendor not printed.')}
    if i == len(VENDOR_NAMES):            # one organisation without a rating
        v.update(grade=None, grade_state='unavailable', grade_reason_code='not_scanned',
                 grade_reason='the organisation has not been scanned yet', risk_band=None,
                 risk_band_state='unavailable', risk_band_reason_code='not_scanned')
    else:
        g, b = RNG.choices(GRADE_BANDS, weights=GRADE_W)[0]
        v.update(grade=g, risk_band=b, risk_band_label_source=b.capitalize())
    if i <= 6:
        v.update(employees=RNG.choice([180, 420, 1250, 3400, 8700]), revenue_source=RNG.choice(['24M', '96M', '310M', '1.4B']),
                 headquarters='Example City, Example Country', founded=RNG.randint(1998, 2018),
                 technologies_count=RNG.randint(40, 600))
    vendors.append(v)
fourth_party_vendors = sec(
    '14', 'Fourth-party vendors', AD, 'findings',
    f'{len(vendors)} fourth-party vendors were identified through automated discovery.',
    state_label_source=f'{len(vendors)} fourth-party vendor(s) have been identified',
    intro_source='Identifies fourth-party vendors — the suppliers and service providers your supplier relies on.',
    lead_source=f'{len(vendors)} fourth-party vendor(s) have been identified through automated discovery and '
                'vendor relationship analysis.',
    metrics=[metric('fourth_parties', 'Fourth-party vendors', len(vendors), 'organisations', count_kind='reported')],
    vendors=vendors)

# --- 15 cloud ------------------------------------------------------------------------------------------------
cloud_infrastructure = sec(
    '15', 'Cloud infrastructure', AD, 'findings',
    '4 cloud providers were detected from public DNS, IP-range and MX records.',
    state_label_source='4 Cloud Providers Detected',
    intro_source='Identifies cloud service providers used by the organization through analysis of DNS records, '
                 'IP ranges, MX records, and NS records.',
    lead_source='4 cloud provider(s) have been identified through automated infrastructure analysis.',
    metrics=[metric('cloud_providers_detected', 'Cloud providers detected', 4, 'providers', source_label='4')],
    detection_methods=['dns_records', 'ip_ranges', 'mx_records', 'ns_records'],
    providers=[{'provider': p, 'detection_methods': m, 'observed_at': day(ASSESSED)} for p, m in (
        ('Example Cloud A', ['dns_records', 'ip_ranges']), ('Example Cloud B', ['ip_ranges']),
        ('Sample CDN Network', ['dns_records', 'ns_records']), ('Example Mail Services', ['mx_records']))],
    last_scanned=day(ASSESSED, 'Last scanned: 01.10.2026'))

# --- 01 / 02 -------------------------------------------------------------------------------------------------
executive_overview = sec(
    '01', 'Executive overview', OV, 'findings',
    f'{ORG} ({DOMAIN}) holds an IISRI external rating of BB (Sufficient, medium risk band), with 196 of 360 '
    'points. The largest gaps are vulnerabilities and credential exposure.',
    scope_and_coverage={
        'primary_domain': DOMAIN,
        'observed_targets': [metric('scanned_subdomains', 'Scanned subdomains', len(SUBS), 'subdomains',
                                    count_kind='observed', section='vulnerabilities'),
                             metric('hosts_observed_residency', 'Hosts observed for residency',
                                    sum(r['hosts'] for r in observed_hosting), 'hosts', count_kind='observed',
                                    section='data_residency')],
        'eligible_targets': {'value': 12, 'unit': 'targets'}, 'coverage_percent': {'value': 100, 'unit': 'percent'},
        'coverage_statement_source': 'All subdomains discovered from public DNS and certificate records were included.',
        'method_statement_source': 'This report is generated by IISRI® CyberRank.ai using automated, non-intrusive '
                                   'analysis of publicly accessible information.'},
    rating_overview={'rating_ref': 'rating', 'aspect_breakdown': [
        {'aspect': 'privacy', 'section': 'privacy', 'value': 64, 'unit': 'percent', 'state': 'findings',
         'display_label_source': '64%',
         'summary_label_source': f'Privacy policy exists but has {len(ISSUES)} active risks requiring attention'},
        {'aspect': 'vulnerability', 'section': 'vulnerabilities', 'value': 38, 'unit': 'percent', 'state': 'findings',
         'display_label_source': '38%', 'summary_label_source': 'Security improvements needed urgently'},
        {'aspect': 'certification', 'section': 'certifications', 'value': 3, 'unit': 'certifications',
         'state': 'findings', 'display_label_source': '3 certifications',
         'summary_label_source': 'Good compliance posture',
         'secondary': metric('compliance_score', 'Compliance Score', 68, 'percent',
                             source_label='Compliance Score: 68% (100% = fully certified)')},
        {'aspect': 'data_leak', 'section': 'data_leak_history', 'value': 3, 'unit': 'events', 'state': 'findings',
         'display_label_source': '3 leaks', 'summary_label_source': 'Data breaches found in public records',
         'secondary': metric('data_leak_score', 'Security Score', 55, 'percent',
                             source_label='Security Score: 55% (100% = leak-free)')},
        {'aspect': 'credential', 'section': 'credential_exposure', 'value': N_CRED, 'unit': 'records_unit_unverified',
         'state': 'findings', 'display_label_source': f'{N_CRED} Found',
         'summary_label_source': 'Credential leaks detected'}],
        'note': 'Aspect values use different units and denominators; they are not averaged.'},
    sector_comparison={
        'sector': 'Financial services', 'intro_source': 'See how your security posture compares to sector peers',
        'metrics': [metric('your_score', 'Your Score', 58, 'points', denominator=100, source_label='Your Score 58/100'),
                    metric('sector_average', 'Sector Average', 66, 'points', denominator=100,
                           source_label='Sector Average 66/100'),
                    metric('sector_top_10_percent', 'Sector Top 10%', 88, 'points', denominator=100,
                           source_label='Sector Top 10% 88/100')],
        'performance_gap': {'value': 'You are 8 points below the sector average.'},
        'cohort': {'cohort_id': 'demo-financial-services-2026q3', 'cohort_size': 120, 'period': '2026 Q3',
                   'percentile_method': 'nearest rank', 'state': 'findings'},
        'note': 'Your score (out of 100) is not the 360-point IISRI score.'})


def action(n, prio, title, time, role, text, why, sections, ids=(), **kw):
    return {'action_id': f'act-{n:02d}', 'rank': n, 'priority': prio, 'priority_label_source': f'{prio.upper()} PRIORITY',
            'title': title, 'estimated_time_reported': time, 'required_role': role,
            'owner': nr('not_assigned'), 'due_at': nr('not_assigned'), 'status': nr('not_tracked'),
            'action_required_source': text, 'why_this_matters_source': why, 'linked_sections': list(sections),
            'linked_finding_ids': list(ids), **kw}


priority_actions = sec(
    '02', 'Priority actions', OV, 'findings',
    '5 recommended actions: 2 high, 2 medium and 1 low priority.',
    state_label_source='Priority Action Items',
    intro_source='Recommended actions to improve your IISRI rating, ordered by severity and impact.',
    actions=[
        action(1, 'high', 'Close the exposed remote desktop service', '1 day', 'IT Security team',
               f'Remove public access to the remote desktop service on {h("legacy")} and place it behind the VPN.',
               'An exposed remote access service is the most common starting point for ransomware.',
               ['vulnerabilities'], ['vuln-01']),
        action(2, 'high', 'Reset Compromised Credentials', '1 week', 'IT Security team',
               'Force password resets for the exposed accounts and enable multi-factor authentication for all users.',
               'Exposed passwords are reused in credential-stuffing attacks against the portal and email.',
               ['credential_exposure']),
        action(3, 'medium', 'Enhance DMARC Policy to "Quarantine"', '2 weeks', 'Email / DNS administrator',
               'Upgrade DMARC policy from monitoring (p=none) to quarantine (p=quarantine).',
               'Spoofed email using the organisation domain is still delivered to recipients.',
               ['vulnerabilities'], ['ctrl-dmarc', 'vuln-08']),
        action(4, 'medium', 'Privacy', '2 weeks', 'Legal + DPO team', ISSUES[0][1],
               'Unclear retention periods weaken the privacy score and customer trust.', ['privacy'],
               title_source='PRIVACY', category='privacy'),
        action(5, 'low', 'Publish an AI use statement', '1 month', 'Legal + Product team',
               'Publish a public AI policy and describe the chat assistant in the privacy policy.',
               'Credit decisioning is a high-risk AI use under the EU AI Act; transparency is expected.',
               ['ai_risk_governance'])],
    remediation_impact={'state': 'findings', 'title_source': 'Projected Rating After Remediation',
                        'current': {'grade': 'BB', 'score': 196, 'pool': 360},
                        'projected': {'grade': 'AA', 'score': 290, 'pool': 360}, 'points_recoverable': 94,
                        'active_issues': {'total': len(ISSUES) + len(FINDINGS), 'privacy': len(ISSUES),
                                          'vulnerability': len(FINDINGS)},
                        'conditional_on_rescan': True,
                        'narrative_source': f'{len(ISSUES) + len(FINDINGS)} active issues were identified '
                                            f'({len(ISSUES)} privacy issues, {len(FINDINGS)} vulnerability findings). '
                                            'Completing the recommended actions is expected to recover up to 94 '
                                            'points, conditional on a fresh scan.',
                        'caption_source': 'Estimated improvement upon completion of the recommended actions'},
    note='Rank is the order of the recommendations. Estimated time is not a due date.')

# --- appendices (generic product copy) ------------------------------------------------------------------------
METHODOLOGY = {
    'letter': 'C', 'title': 'Methodology and supply-chain aggregation', 'is_generic_material': True,
    'note': 'Generic methodology brief; values in its diagrams are illustrative.',
    'headline_source': 'One rating for every vendor. One risk number for your whole supply chain.',
    'lead_source': 'CYBERRANK turns externally observable evidence about an organisation into a single severity rating, '
                   'a normalised risk score, and a combined risk that includes the vendors — and the vendors\' vendors '
                   '— behind it.',
    'columns_source': [
        {'title': 'The problem', 'text': "Attackers reach organisations through their suppliers. Existing tools don't "
                                         'add up: CVSS scores single technical flaws, questionnaires rely on '
                                         'self-reporting, and privacy, AI and quantum exposures have no common scale at all.'},
        {'title': 'The approach', 'text': 'An ISO 31000-aligned model with four explicit steps, from observed weaknesses '
                                          'to supply-chain risk. Every step is reproducible and every number is '
                                          'comparable across organisations and portfolios.'},
        {'title': 'The regulatory fit', 'text': 'Built for the obligations in DORA, NIS2, the GDPR and the AI Act, and '
                                                'aligned with ISO/IEC 27001, 27701 and 42001, NIST SP 800-53 and 800-161, '
                                                'PCI DSS and the NIST CSF.'}],
    'steps_source': [
        {'n': 1, 'title': 'Observe', 'text': "Continuous external signals are collected without touching the "
                                             "organisation's systems.",
         'signals': ['Vulnerabilities', 'Privacy compliance', 'Credential & data leaks', 'Data sovereignty',
                     'Data residency', 'Terms of use', 'AI', 'Quantum'],
         'callout': 'Certified controls earn credits: ISO 27001, ISO 27701, SOC 2, ISAE 3402, PCI DSS. Optional '
                    'questionnaires add a second, bounded evidence channel.'},
        {'n': 2, 'title': 'Rate', 'text': 'Every organisation starts with a full point budget, split evenly between a '
                                          'security bucket and a privacy bucket. Weaknesses deduct capped demerits; '
                                          'certifications add capped credits.',
         'callout': "The net score maps to the IISRI rating, AAA to D. The rating reflects the organisation's own "
                    "posture only — a vendor's weakness never changes it."},
        {'n': 3, 'title': 'Score the risk', 'text': 'Likelihood = threat probability × weakness. Threat probability '
                                                    'comes from sector, size and internet exposure; weakness comes from '
                                                    'the rating. Impact is one of four tiers you assign: Critical, '
                                                    'High, Medium or Low.',
         'callout': 'Risk = normalised likelihood × impact, reported as a score and a band: Low, Medium, High or Critical.'},
        {'n': 4, 'title': 'Combine', 'text': 'Vendors and sub-vendors are discovered automatically and rated with the '
                                             'same pipeline. Their risks are folded into yours, attenuated by distance '
                                             'in the chain.',
         'callout': 'The combined risk shows the cascading exposure that your own rating cannot see.'}],
    'scale_caption_source': 'Ten grades. Higher grades mean lower weakness values and therefore lower likelihood.',
    'scale_ends_source': {'top': 'All controls adequate, appropriate and effective',
                          'bottom': 'Controls provide no assurance'},
    'supply_chain': {'headline_source': 'Your rating describes you. Your combined risk describes your supply chain.',
                     'illustrative_values': {'individual_risk': 'Low', 'combined_risk': 'Medium', 'is_illustrative': True},
                     'note': 'Printed by the locked production page (Appendix C, page 2 of 2).'},
    'copyright_source': 'Copyright © 2026 IISRI. All rights reserved. Full methodology paper: "An Integrated '
                        'Quantitative Methodology for Third-Party Security, Privacy and AI Risk Rating", July 2026. '
                        'Available upon request.',
}

appendices = {
    'a_about': {'letter': 'A', 'title': 'About this report',
                'about_source': 'This report is generated by IISRI® CyberRank.ai using automated, non-intrusive '
                                'analysis of publicly accessible information. The assessment does not require access '
                                'to internal systems and should be interpreted as an external risk signal.',
                'closing_source': 'Report generated on 02.10.2026',
                'data_sources_source': ['automated analysis of data leak databases, public disclosures, and monitored '
                                        'online sources',
                                        'automated technology discovery and vendor relationship analysis',
                                        'analysis of DNS records, IP ranges, MX records, and NS records']},
    'b_rating_scale': {'letter': 'B', 'title': 'IISRI rating scale',
                       'intro_source': 'Reference guide to the standardized rating scale used throughout this report, '
                                       'with descriptions of each grade level and associated risk profile.'},
    'c_methodology': METHODOLOGY,
    'd_evidence_registers': {
        'letter': 'D', 'title': 'Detailed evidence registers', 'state': 'findings',
        'credential_register': {'state': 'findings', 'sanitised': True,
                                'columns': ['id', 'email_domain', 'email_state', 'account_label_masked',
                                            'exposure_period_source', 'exposure_years', 'exposure_period_has_unknown',
                                            'exposed_field_categories', 'breach_source_name', 'status'],
                                'counts': {'returned_rows': N_CRED, 'total_rows': {'value': N_CRED},
                                           'headline_found': N_CRED, 'status': status_counts},
                                'rows': cred_rows},
        'quantum_scope_register': {'state': 'findings',
                                   'columns': ['id', 'subdomain', 'scope_level', 'category', 'pre_qc_algorithm', 'source',
                                               'post_qc_source', 'post_qc_algorithm', 'risk_level', 'high', 'moderate', 'low'],
                                   'counts': {'rows': len(q_rows), 'scopes': len(scopes), 'root_aggregate_rows': len(apex)},
                                   'rows': q_rows},
        'vulnerability_asset_register': {'state': 'findings',
                                         'columns': ['asset_label_source', 'finding_ids', 'finding_count', 'max_severity'],
                                         'counts': {'rows': len(VULN_ASSETS), 'memberships': memberships},
                                         'rows': VULN_ASSETS},
        'pqc_domain_register': {'state': 'findings', 'columns': ['domain', 'algorithm'],
                                'rows': [{'domain': d, 'algorithm': 'ML-KEM'} for d in pqc_domains]}},
}

REPORT = {
    'meta': {'report_schema_version': 'cyberrank-report/0.1-draft', 'fixture_kind': 'synthetic_demo',
             'fixture_note': 'Fully synthetic customer-preview payload generated by tools/extract/build_demo_fixture.py. '
                             'Fictional organisation; RFC 2606 domains and documentation IP ranges only.',
             'language': 'en',
             'state_enum': ['findings', 'clear', 'not_assessed', 'not_applicable', 'unavailable', 'partial', 'pending_review'],
             'sanitisation': {'applied': True, 'rule': 'Synthetic data; account labels masked like the system '
                                                       '(first and last character of the local part kept).',
                              'removed_fields': [], 'source_rows_with_unmasked_local_part': 0}},
    'identity': {'organisation_name': ORG, 'organisation_id': {'value': 'org-demo-0001'}, 'domain': DOMAIN,
                 'website_source_label': f'www.{DOMAIN}', 'sector': 'Financial services',
                 'description_source': f'{ORG} is a fictional retail bank and payments provider used to demonstrate '
                                       'the Cyberrank Cyber Risk Report. All data in this report is synthetic.',
                 'logo': nr('asset_not_extracted', note='Demo report: no logo.'), 'report_title': 'Cyber Risk Report',
                 'issuer': {'organisation_name': 'Example Group Procurement', 'state': 'findings'}},
    'snapshot': {'assessment_id': {'value': 'demo-assessment-0001'}, 'snapshot_id': {'value': 'demo-snapshot-0001'},
                 'assessed_at': day(ASSESSED, 'REPORT DATE 01.10.2026'),
                 'generated_at': day(GENERATED, 'DATE GENERATED 02.10.2026'),
                 'timezone': {'value': 'UTC'}, 'methodology_version': {'value': 1},
                 'active_version': nr(), 'viewed_version': nr(), 'score_context': {'value': 'Current state'},
                 'toggles_at_assessment': {'pqc_scan': {'value': True}, 'extended_scan': {'value': True}},
                 'preferences_at_assessment': {'sovereignty_allowed_jurisdictions': ['United Kingdom', 'European Union (EU)'],
                                               'residency_allowed_countries': PREF}},
    'rating': {'rating_name': 'IISRI® External Rating', 'grade': 'BB', 'grade_mark': 'Sufficient', 'risk_band': 'medium',
               'risk_band_label_source': 'Medium',
               'band_description_source': 'Main information security and/or privacy controls are adequate, but some '
                                          'specific control weaknesses have been noted.',
               'net': {'value': 196, 'unit': 'points', 'source_label': 'Score 196 / 360'},
               'pool': {'value': 360, 'unit': 'points', 'source_label': 'Score 196 / 360'},
               'grade_table_id': nr(), 'stored_vs_calculated': nr()},
    'sections': {'executive_overview': executive_overview, 'priority_actions': priority_actions, 'privacy': privacy,
                 'vulnerabilities': vulnerabilities, 'credential_exposure': credential_exposure,
                 'data_leak_history': data_leak_history, 'data_sovereignty': data_sovereignty,
                 'data_residency': data_residency, 'legal_terms': legal_terms, 'ai_risk_governance': ai_risk_governance,
                 'quantum_security': quantum_security, 'security_resourcing': security_resourcing,
                 'certifications': certifications, 'fourth_party_vendors': fourth_party_vendors,
                 'cloud_infrastructure': cloud_infrastructure},
    'appendices': appendices,
    'review_flags': [],
}


# --- certificate documents (obviously fake) ------------------------------------------------------------------
def certificate_page(doc, standard, issuer, scope, number, valid):
    import pymupdf
    page = doc.new_page(width=842, height=595)                        # A4 landscape
    page.draw_rect(pymupdf.Rect(24, 24, 818, 571), color=(0.08, 0.19, 0.31), width=3)
    page.draw_rect(pymupdf.Rect(34, 34, 808, 561), color=(0.6, 0.65, 0.7), width=0.8)
    lines = [(70, 'SAMPLE', 40, (0.75, 0.1, 0.1)),
             (120, 'SAMPLE — demonstration document, not a real certificate', 16, (0.75, 0.1, 0.1)),
             (185, 'Certificate of Registration', 28, (0.08, 0.19, 0.31)),
             (235, 'This is to certify that the management system of', 13, (0.2, 0.2, 0.2)),
             (270, ORG, 22, (0.08, 0.19, 0.31)),
             (305, f'has been assessed against {standard}', 14, (0.2, 0.2, 0.2)),
             (335, f'Scope: {scope}', 12, (0.2, 0.2, 0.2)),
             (385, f'Certificate number: {number}    Valid: {valid}', 12, (0.2, 0.2, 0.2)),
             (415, f'Issued by: {issuer} (fictional)', 12, (0.2, 0.2, 0.2)),
             (500, 'SAMPLE — demonstration document, not a real certificate', 11, (0.75, 0.1, 0.1))]
    for y, text, size, colour in lines:
        w = pymupdf.get_text_length(text, fontname='helv', fontsize=size)
        page.insert_text(((842 - w) / 2, y), text, fontname='helv', fontsize=size, color=colour)
    return page


def write_documents():
    import pymupdf
    ASSETS.mkdir(parents=True, exist_ok=True)
    meta = {'title': 'SAMPLE certificate (demonstration only)', 'author': '', 'subject': '', 'keywords': '',
            'creator': 'build_demo_fixture.py', 'producer': 'pymupdf', 'creationDate': 'D:20261001000000Z',
            'modDate': 'D:20261001000000Z'}
    doc = pymupdf.open()
    certificate_page(doc, 'ISO/IEC 27001:2022', 'Example Certification Body',
                     'Provision of online banking and payment services', 'DEMO-ISO-0001', '01 Mar 2025 – 29 Feb 2028')
    doc.set_metadata(meta)
    doc.save(ASSETS / 'demo-certificate-iso27001.pdf', garbage=4, deflate=True, no_new_id=True)
    doc = pymupdf.open()
    page = certificate_page(doc, 'SOC 2 Type II', 'Sample Assurance Partners',
                            'Customer portal and payment API', 'DEMO-SOC2-0002', '01 Jan 2026 – 31 Dec 2026')
    page.get_pixmap(dpi=110).save(ASSETS / 'demo-certificate-soc2.png')


# --- privacy / synthetic-data guard ----------------------------------------------------------------------------
DOC_NETS = ('192.0.2.', '198.51.100.', '203.0.113.')
ALLOWED_HOST = re.compile(r'(^|\.)example\.(com|net|org)$')


def check(text):
    emails = re.findall(r'[\w.*•+-]+@[\w.-]+', text)
    bad = [e for e in emails if e != 'support@cyberrank.ai' and '*' not in e]
    assert not bad, f'unmasked addresses: {bad}'
    assert all(ALLOWED_HOST.search(e.split('@')[1]) for e in emails), emails
    ips = re.findall(r'\b\d{1,3}(?:\.\d{1,3}){3}\b', text)
    assert all(ip.startswith(DOC_NETS) for ip in ips), [ip for ip in ips if not ip.startswith(DOC_NETS)]
    hosts = set(re.findall(r'\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b', text.lower()))
    other = {x for x in hosts if not ALLOWED_HOST.search(x) and x != 'cyberrank.ai' and not x.endswith(('.pdf', '.png'))}
    assert not other, f'non-example domains: {sorted(other)}'


# Backend-computed aspect scores for the aspects without a score metric (synthetic values that follow
# the demo's own results: governing law matches, a host outside the preference, a clause present,
# a high-risk quantum finding, no resourcing demerit).
for key, pct in (('data_sovereignty', 100), ('data_residency', 0), ('legal_terms', 100),
                 ('quantum_security', 0), ('security_resourcing', 100)):
    REPORT['sections'][key]['aspect_score'] = {'value': pct, 'unit': 'percent'}


if __name__ == '__main__':
    write_documents()
    text = json.dumps(REPORT, indent=1, ensure_ascii=False) + '\n'
    check(text)
    assert len(cred_rows) > 30 and len(q_rows) > 30 and len(vendors) > 30
    OUT.write_text(text, encoding='utf-8')
    print(f'{OUT}: {len(cred_rows)} credential rows, {len(q_rows)} quantum rows, {len(vendors)} vendors, '
          f'{len(FINDINGS)} vulnerability types')
    sys.exit(0)
