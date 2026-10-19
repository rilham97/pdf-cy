"""Synthetic variant fixtures for the condition-matrix gaps (Gaps_s03_s05_s06.md,
Gaps_s04_s07_s08_s09_s10_s11.md). Example Org / example.com only: no real names or emails.

    .venv/bin/python -I tests/gap_fixtures.py out.pdf        # render every variant (one sheet)

VARIANTS: (variant id, gap ids, section id(s), report). Each report is a complete minimal payload
(identity, snapshot, the section(s), registers it needs) and passes build.validate().
privacy_a / privacy_b keep the OLD nested shape (sub-areas under sections.privacy) to cover the
load-time alias; privacy_c uses the section layout v15 (own sections 07, 08, 09, 12).
"""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

DOMAIN = 'example.com'
NR = {'value': None, 'state': 'unavailable', 'reason_code': 'not_printed_in_source'}


def base(**snapshot):
    snap = {'assessed_at': {'value': '2026-10-02', 'precision': 'day'},
            'generated_at': {'value': '2026-10-03', 'precision': 'day'},
            'toggles_at_assessment': {'pqc_scan': {'value': None, 'state': 'unavailable',
                                                   'reason_code': 'toggle_snapshot_not_printed'}}}
    snap.update(snapshot)
    return {'identity': {'organisation_name': 'Example Org', 'domain': DOMAIN}, 'snapshot': snap,
            'sections': {}, 'appendices': {'d_evidence_registers': {}}}


def section(key, title, state, summary, **kw):
    return {'title': title, 'state': state, 'summary': summary, **kw, '_key': key}


def report_with(sec, **snapshot):
    r = base(**snapshot)
    sec = dict(sec)
    r['sections'][sec.pop('_key')] = sec
    return r


# --- 03 Privacy ---------------------------------------------------------------------------
def privacy_metrics(score, issues, found):
    return [{'id': 'privacy_score', 'label': 'Privacy Score', 'value': score, 'unit': 'percent', 'state': 'findings'},
            {'id': 'active_issues', 'label': 'Active Issues', 'value': issues, 'unit': 'issues', 'state': 'findings'},
            {'id': 'policies_found', 'label': 'Policies Found', 'value': found, 'unit': 'policies',
             'state': 'findings'}]


def privacy_a():
    """P5 unknown policy_state; P8/P9 T&C '# No' + URL + clause rule; P13/P14 no sovereignty
    preference with a policy quote; P11/P16 unknown location counted as mismatch by the payload."""
    return report_with(section(
        'privacy', 'Privacy (gaps P5, P8/P9, P11/P16, P13/P14)', 'findings',
        'Synthetic: unrecognised policy state, two missing T&C clauses, no sovereignty preference.',
        policy={'state': 'findings', 'policy_state': {'value': 'draft'},
                'policy_source': {'value': 'https://www.example.com/privacy'},
                'metrics': privacy_metrics(55, 2, 1), 'areas': NR},
        terms_conditions={'state': 'findings', 'portal_detected': True, 'rows': [
            {'label': 'Login / Payment Portal', 'value_source': '# Detected'},
            {'label': 'Clause: protects customer data', 'value_source': '# No'},
            {'label': 'Clause: notifies customers on breach', 'value_source': '# No'},
            {'label': 'Terms page', 'value_source': 'https://www.example.com/legal/terms'}]},
        sovereignty={'state': 'findings', 'enabled': False, 'allowed_set': [],
                     'observed_jurisdiction': {'value': 'Singapore'}, 'match_state': 'unknown',
                     'quote_source': 'These terms are governed by the laws of Singapore.'},
        residency={'state': 'findings', 'enabled': True, 'allowed_set': ['Australia'], 'match_state': 'mismatch',
                   'observed_hosting': [
                       {'country': 'Australia', 'hosts': 6, 'evidence_kind': {'value': 'IP geolocation'}},
                       {'country': None, 'hosts': 1, 'state': 'unavailable', 'reason_code': 'location_unknown',
                        'match_state': 'mismatch', 'evidence_kind': {'value': 'IP geolocation'}}]},
        resourcing={'state': 'clear', 'privacy_role_evidence': 'detected', 'security_role_evidence': 'detected'}))


def privacy_b():
    """P7/P3 excluded policy with no state_reason (reason from the payload's policy state; load
    validation rejects this shape, so the variant is rendered unvalidated like the s03 demo);
    P14 residency with no preference but observed hosting; one T&C clause found."""
    return report_with(section(
        'privacy', 'Privacy (gaps P3/P7, P14)', 'findings',
        'Synthetic: no privacy policy (excluded); hosting observed without a residency preference.',
        policy={'state': 'not_applicable', 'policy_state': {'value': 'excluded_no_policy'},
                'policy_source': {'value': None, 'reason_code': 'not_identified'},
                'metrics': [dict(m, reason_code='not_derivable') if m['value'] is None else m
                            for m in privacy_metrics(None, None, 0)]},
        terms_conditions={'state': 'findings', 'portal_detected': True, 'rows': [
            {'label': 'Clause: protects customer data', 'value_source': '# Yes'},
            {'label': 'Clause: notifies customers on breach', 'value_source': '# No'}]},
        sovereignty={'state': 'findings', 'enabled': True, 'allowed_set': ['Australia'],
                     'observed_jurisdiction': {'value': 'Australia'}, 'match_state': 'match'},
        residency={'state': 'findings', 'enabled': False, 'allowed_set': [],
                   'observed_hosting': [{'country': 'Germany', 'hosts': 3,
                                         'evidence_kind': {'value': 'IP geolocation'}}]},
        resourcing={'state': 'clear', 'privacy_role_evidence': 'detected', 'security_role_evidence': 'detected'}))


# --- 04 Vulnerabilities -------------------------------------------------------------------
def finding(i, sev, n, hosts):
    return {'finding_id': f'vuln-{i:02d}', 'finding_type': f'example-check-{i:02d}', 'severity': sev,
            'affected_assets_count': n, 'affected_assets': hosts,
            'breach_likelihood': {'value': 0.2, 'unit': 'probability'},
            'rationale_source': 'Synthetic rationale for the gap fixture.'}


def vuln_metrics(total):
    return [{'id': 'finding_types', 'label': 'Finding types', 'value': total, 'unit': 'finding_types',
             'state': 'findings'}]


def vulns_a():
    """V4 informational finding; V6/V8 host list shorter than its count and an empty list;
    V12 DMARC p=none; V14 SPF never reported; V18 IP reputation '-1' with state clear."""
    hosts = [f'h{i}.{DOMAIN}' for i in range(3)]
    return report_with(section(
        'vulnerabilities', 'Vulnerabilities (gaps V4, V6/V8, V12, V14, V18)', 'findings',
        'Synthetic: one Medium, one Low and one Informational finding type.',
        metrics=vuln_metrics(3),
        findings=[finding(1, 'medium', 5, hosts), finding(2, 'low', 2, []), finding(3, 'info', 1, hosts[:1])],
        email_dns_controls={'state': 'findings', 'controls': [
            {'finding_id': 'ctrl-dkim', 'control': 'DKIM', 'result': 'enabled', 'state': 'clear'},
            {'finding_id': 'ctrl-dmarc', 'control': 'DMARC', 'result': 'enabled', 'state': 'partial',
             'dmarc_policy': {'value': 'none'}},
            {'finding_id': 'ctrl-dnssec', 'control': 'DNSSEC', 'result': 'valid', 'state': 'clear'}]},
        ip_reputation={'state': 'clear', 'state_label_source': 'IP Reputation — Clean',
                       'summary_source': 'Checked 1 IP(s) against threat intelligence feeds.', 'ips_checked': 1,
                       'rows': [{'ip_address': '192.0.2.10', 'isp': 'Example Transit', 'country': 'NL',
                                 'abuse_score': -1, 'reports': 0}]},
        https_redirect={'state': 'clear', 'result': 'redirects_to_https'}))


def vulns_b():
    """V13 DMARC already p=reject while a priority action asks to upgrade it."""
    r = report_with(section(
        'vulnerabilities', 'Vulnerabilities (gap V13)', 'findings', 'Synthetic: DMARC contradiction.',
        metrics=vuln_metrics(1), findings=[finding(1, 'low', 1, [f'www.{DOMAIN}'])],
        email_dns_controls={'state': 'findings', 'controls': [
            {'finding_id': 'ctrl-spf', 'control': 'SPF', 'result': 'enabled', 'state': 'clear'},
            {'finding_id': 'ctrl-dkim', 'control': 'DKIM', 'result': 'enabled', 'state': 'clear'},
            {'finding_id': 'ctrl-dmarc', 'control': 'DMARC', 'result': 'enabled', 'state': 'findings',
             'dmarc_policy': {'value': 'reject'}},
            {'finding_id': 'ctrl-dnssec', 'control': 'DNSSEC', 'result': 'valid', 'state': 'clear'}]},
        ip_reputation={'state': 'clear', 'ips_checked': 1, 'state_reason': 'No abuse reports returned.'},
        https_redirect={'state': 'clear', 'result': 'redirects_to_https'}))
    r['sections']['priority_actions'] = {
        'title': 'Priority actions', 'state': 'findings', 'actions': [{
            'action_id': 'act-01', 'rank': 1, 'priority': 'medium', 'title': 'Enhance DMARC Policy to "Quarantine"',
            'action_required_source': 'Upgrade DMARC policy from monitoring (p=none) to quarantine (p=quarantine).',
            'linked_sections': ['vulnerabilities'], 'linked_finding_ids': ['ctrl-dmarc']}]}
    return r


# --- 05 Certifications --------------------------------------------------------------------
def cert(i, std, origin, approval, credit, **kw):
    c = {'certificate_id': f'cert-{i:02d}', 'standard': std, 'origin': origin,
         'approval_state': {'value': approval} if approval else NR,
         'credit_applied': {'value': credit, 'unit': 'points'} if credit is not None else NR,
         'eligibility': {'value': True}, 'valid_from': {'value': '2025-01-01', 'precision': 'day'},
         'valid_until': {'value': '2027-12-31', 'precision': 'day'}, 'category': {'value': 'security'}}
    c.update(kw)
    return c


def certs():
    """C1-C3 origin vs status (legacy 'team_approved', uploaded link, pending); C4/C5 rejected (uploaded and
    detected; credit only in the payload, never printed); C6 expiry from the system flag `expired`
    (dates never compared); C8 both. Weighting / eligibility stay internal (business answer 2026-10-15)."""
    return report_with(section(
        'certifications', 'Certifications (gaps C1–C10)', 'findings',
        'Synthetic: approved, uploaded, pending, rejected and expired certificates.',
        metrics=[{'id': 'certificates_detected', 'label': 'Certificate records', 'value': 7,
                  'unit': 'certificates', 'state': 'findings'}],
        certificates=[
            cert(1, 'ISO/IEC 27001', 'team_approved', None, 40),
            cert(2, 'SOC 2', 'uploaded', 'approved', 20, category={'value': 'both'},
                 file_reference={'value': 'https://files.example.com/uploads/soc2-report.pdf'}),
            cert(3, 'ISO/IEC 27701', 'detected', 'pending', 20, category={'value': 'privacy'}),
            cert(4, 'PCI DSS', 'uploaded', 'rejected', 20),
            cert(5, 'ISO/IEC 27017', 'uploaded', 'approved', 20, expired={'value': True},
                 valid_until={'value': '2026-06-30', 'precision': 'day'}),
            cert(6, 'ISO 22301', 'detected', 'rejected', 0,
                 eligibility={'value': False, 'reason_code': 'standard_not_in_credit_table'}),
            cert(7, 'ISAE 3402', 'detected', 'approved', None, category={'value': 'both'},
                 valid_until={'value': '2026-01-31', 'precision': 'day'}, expired={'value': False})],
        credit_summary={'line_total': 100, 'applied': 90, 'buckets': [
            {'bucket': 'security', 'component': 'auto', 'line': 50, 'applied': 40},
            {'bucket': 'privacy', 'component': 'auto', 'line': 30, 'applied': 30}]}))


def certs_mixed():
    """One standard with two records (system detected, awaiting approval, validity not detected + the uploaded
    file, approved automatically on upload), a second detected certificate from another source with
    no validity and no expiry flag: grouped rows, numbered sources, Next step + added priority action."""
    nd = {'value': None, 'state': 'unavailable', 'reason_code': 'not_detected'}
    r = report_with(section(
        'certifications', 'Certifications (detected + uploaded, validity not detected)', 'findings',
        'Synthetic: ISO/IEC 27001 detected and uploaded; SOC 2 detected only.',
        metrics=[{'id': 'certificates_detected', 'label': 'Certificate records', 'value': 3,
                  'unit': 'certificates', 'state': 'findings'}],
        certificates=[
            cert(1, 'ISO/IEC 27001', 'detected', 'pending', 20, valid_from=nd, valid_until=nd,
                 source_url=f'https://trust.{DOMAIN}/compliance'),
            cert(2, 'SOC 2', 'detected', 'pending', 20, valid_from=nd, valid_until=nd, category={'value': 'both'},
                 source_url=f'https://www.{DOMAIN}/security'),
            cert(3, 'ISO/IEC 27001', 'uploaded', 'approved', 40,
                 file_reference={'value': 'https://files.example.com/uploads/iso27001-certificate.pdf'})]))
    r['sections']['priority_actions'] = {'title': 'Priority actions', 'state': 'findings', 'actions': [{
            'action_id': 'act-01', 'rank': 1, 'priority': 'medium', 'title': 'Enhance DMARC Policy to "Quarantine"',
            'action_required_source': 'Upgrade DMARC policy from monitoring (p=none) to quarantine (p=quarantine).'}]}
    return r


def certs_uploaded():
    """Shape of the 2026-10-15 Iproteksi sample: three uploaded certificates (two named 'OTHER', one
    ISO 27001) with issuer + scope wording, no validity in the data (only on the document image), and a
    headline of 2 certifications against 3 records. Names are synthetic."""
    nd = {'value': None, 'state': 'unavailable', 'reason_code': 'not_detected'}
    up = lambda i, std, issuer, scope, **kw: cert(i, std, 'uploaded', 'approved', 20, valid_from=nd, valid_until=nd,
                                            category=NR, issuer={'value': issuer}, scope_source={'value': scope},
                                            file_reference={'value': f'https://files.example.com/uploads/cert-{i}.pdf'},
                                            **kw)
    r = report_with(section(
        'certifications', 'Certifications (uploaded: issuer, scope, OTHER, headline 2 vs 3)', 'findings',
        'Synthetic: three uploaded certificates; validity only on the documents.',
        metrics=[{'id': 'certifications_headline', 'label': 'Certifications (headline)', 'value': 2,
                  'unit': 'certifications_headline', 'state': 'findings'}],
        certificates=[up(1, 'OTHER', 'Example Registrar Pvt. Ltd', 'IT Security Solution and Services',
                         document={'value': 'certificate_sample.png'}),
                      up(2, 'OTHER', 'Example Registrar Pvt. Ltd', 'Providing IT Security Solutions and Services',
                         document={'value': 'missing_certificate.pdf'}),
                      up(3, 'ISO27001', 'Example Certification Body', 'IT Security Solution and Services',
                         document={'value': 'certificate_sample.pdf'})]))
    r['_source_dir'] = str(Path(__file__).resolve().parent / 'fixtures')     # D.5 documents (synthetic)
    r['appendices']['d_evidence_registers'] = {'state': 'findings'}
    return r


# --- 06 Data breach and leak history ------------------------------------------------------
def leaks():
    """D3/D4 last valid event reported inaccurate; D6 age + demerit from the payload;
    D8/D9 records unit/scope and two source records of one canonical event; L1 an event resolved by
    the user/admin; L2 an event without any validity flag (valid by default)."""
    ev = lambda i, **kw: {'event_id': f'ev-{i}', 'entity_link': f'portal.{DOMAIN}', 'event_type': 'data_leak',
                          'occurred_at': {'value': '2025-08-22', 'precision': 'day'},
                          'source_url': f'https://news.example.net/report-{i}', **kw}
    return report_with(section(
        'data_leak_history', 'Data breach and leak history (gaps D3/D4, D6, D8/D9, L1, L2)', 'findings',
        'Synthetic: the named last valid event is reported inaccurate; one event appears in two sources.',
        metrics=[{'id': 'events_reported', 'label': 'Leak events', 'value': 5, 'unit': 'events',
                  'state': 'findings'}],
        last_valid_event={'event_id': 'ev-1'},
        events=[ev(1, validity_state='reported_inaccurate', scoring_eligible=False, records_affected=1200,
                   records_unit='accounts', records_scope='organisation'),
                ev(2, canonical_event_id='cev-7', occurred_at={'value': '2024-08-22', 'precision': 'day'},
                   records_affected=5000000, records_unit='records', records_scope='aggregate_multi_service',
                   date_basis='disclosed_at', age_days_at_assessment=406, demerit_applied=0,
                   scoring_eligible=True),
                ev(3, canonical_event_id='cev-7', occurred_at={'value': '2024-08-22', 'precision': 'day'},
                   records_affected=5000000, records_unit='records', scoring_eligible=True),
                ev(4, validity_state='resolved', occurred_at={'value': '2023-03-17', 'precision': 'day'},
                   records_affected=800, records_unit='accounts'),
                ev(5, occurred_at={'value': '2022-05-01', 'precision': 'day'}, records_affected=300,
                   records_unit='accounts')]))


# --- 08 Credential exposure ---------------------------------------------------------------
REF = 'appendices.d_evidence_registers.credential_register'


def creds(rows, headline):
    r = report_with(section(
        'credential_exposure', f'Credential exposure ({"gap C2" if not rows else "gap C3"})', 'findings',
        'Synthetic credential aggregate.', register_ref=REF,
        metrics=[{'id': 'found_headline', 'label': 'Found (headline)', 'value': headline,
                  'unit': 'records_unit_unverified', 'state': 'findings'}]))
    r['appendices']['d_evidence_registers']['credential_register'] = {
        'state': 'findings', 'rows': rows, 'counts': {'returned_rows': len(rows), 'headline_found': headline,
                                                      'total_rows': NR}}
    return r


def creds_c2():
    """C2 headline 40, register empty."""
    return creds([], 40)


def creds_c3():
    """C3 every row on another mailbox provider."""
    rows = [{'id': f'cred-{i:04d}', 'email_domain': 'mail.example.net', 'email_state': 'masked_label_present',
             'exposure_period_source': '2025', 'exposure_years': [2025], 'exposure_period_has_unknown': False,
             'exposed_field_categories': ['email', 'password'], 'breach_source_name': NR} for i in range(1, 6)]
    return creds(rows, 5)


# --- 10 AI risk and governance -------------------------------------------------------------
def ai():
    """A3 'unlikely' conclusion beside observed signals; A5 is_assessment_result=true while not_assessed."""
    return report_with(section(
        'ai_risk_governance', 'AI risk and governance (gaps A3, A5)', 'not_assessed',
        'Synthetic: module not assessed; the payload flags its narrative as a result.',
        reason_code='module_not_assessed',
        narrative_observation={
            'is_assessment_result': True,
            'stated_conclusion_source': 'It is unlikely this organisation uses AI in a material way.',
            'signals_observed': [
                {'signal': 'ai_infrastructure', 'method': 'csp_header_analysis',
                 'example_source': 'CSP destination: api.ai-vendor.example'},
                {'signal': 'ai_hiring', 'method': 'careers_pages', 'example_source': 'AI engineer role advertised'}]}))


# --- 11 Quantum security ------------------------------------------------------------------
QREF = 'appendices.d_evidence_registers.quantum_scope_register'


def qrow(i, sub, high, low, level=True):
    r = {'id': f'q-{i}', 'subdomain': sub, 'category': 'Public-key cryptography', 'pre_qc_algorithm': 'RSA',
         'source': 'standard scan', 'post_qc_algorithm': 'ML-DSA', 'high': high, 'moderate': 0, 'low': low}
    if level:
        r['scope_level'] = 'root_aggregate' if sub == DOMAIN else 'subdomain'
    return r


def quantum(rows, metrics_hl, pqc=None, **snapshot):
    h, l_ = metrics_hl
    sec = section('quantum_security', 'Quantum security', 'findings', 'Synthetic quantum scan.',
                  scope_register_ref=QREF,
                  metrics=[{'id': 'high_risk', 'label': 'High Risk', 'value': h, 'unit': 'findings',
                            'state': 'findings'},
                           {'id': 'moderate_risk', 'label': 'Moderate Risk', 'value': 0, 'unit': 'findings',
                            'state': 'clear'},
                           {'id': 'low_risk', 'label': 'Low Risk', 'value': l_, 'unit': 'findings',
                            'state': 'findings'}],
                  findings_by_category=[{'category': 'Public-key cryptography', 'issues': h + l_, 'algorithms': [
                      {'algorithm': 'RSA', 'risk_level': 'high', 'findings': h, 'protocol_labels': ['TLS'],
                       'pqc_alternative_available': 'ML-DSA'}]}])
    if pqc is not None:
        sec['pqc_detected'] = pqc
    r = report_with(sec, **snapshot)
    r['appendices']['d_evidence_registers']['quantum_scope_register'] = {'state': 'findings', 'rows': rows}
    return r


def quantum_q1():
    """Q1 PQC not reported (toggle unknown, no pqc_detected) + Q4 apex inferred (no scope_level)."""
    rows = [qrow(1, DOMAIN, 4, 6, level=False), qrow(2, f'api.{DOMAIN}', 2, 3, level=False),
            qrow(3, f'www.{DOMAIN}', 2, 3, level=False)]
    r = quantum(rows, (4, 6))
    r['sections']['quantum_security']['title'] = 'Quantum security (gaps Q1, Q4)'
    return r


def quantum_q2():
    """Q2 PQC scan switched off, no quantum results -> not assessed. (Off together with results is a
    data error rejected by build.validate: see quantum_q2_conflict / test_quantum_toggle_conflict.)"""
    return report_with(section('quantum_security', 'Quantum security (gap Q2)', 'findings',
                               'Synthetic: PQC scan switched off.'),
                       toggles_at_assessment={'pqc_scan': {'value': False}})


def quantum_q2_conflict():
    """pqc_scan false + quantum results: must fail validation (never rendered)."""
    return quantum([qrow(1, DOMAIN, 1, 1)], (1, 1), toggles_at_assessment={'pqc_scan': {'value': False}})


def quantum_q5():
    """Q5 apex-only register (grammar: 1 scope, no subdomain rows); PQC reported via the toggle."""
    r = quantum([qrow(1, DOMAIN, 2, 2)], (2, 2), pqc=[],
                toggles_at_assessment={'pqc_scan': {'value': True}})
    r['sections']['quantum_security']['title'] = 'Quantum security (gap Q5, PQC scan on)'
    return r


# --- 2026-10-15 production samples (Gmail, Mock Cyberrank): new condition variants -----------------
def overview_sector():
    """N1 sector label + value as given (English display, Indonesian source id kept, never printed);
    N2 risk band display string from the payload, colour from the enum code; net score / pool printed."""
    r = report_with(section(
        'executive_overview', 'Executive overview (N1 sector, N2 band display)', 'findings',
        'Synthetic: sector and risk band rendered as given.',
        scope_and_coverage={'primary_domain': DOMAIN},
        sector_comparison={'sector': 'Telecommunications', 'sector_source_id': 'Telekomunikasi',
                           'intro_source': 'See how your security posture compares to sector peers',
                           'metrics': [{'id': 'your_score', 'label': 'Your Score', 'value': 29, 'unit': 'points',
                                        'denominator': 100},
                                       {'id': 'sector_average', 'label': 'Sector Average', 'value': 64,
                                        'unit': 'points', 'denominator': 100}],
                           'performance_gap': {'value': 'You are 35 points below the sector average.'}}))
    r['identity'].update(sector='Telecommunications', sector_source_id='Telekomunikasi')
    r['rating'] = {'rating_name': 'IISRI External Rating', 'grade': 'CC', 'risk_band': 'medium',
                   'risk_band_label_source': 'Medium', 'risk_band_label_source_id': 'Sedang',
                   'net': {'value': 86, 'unit': 'points'}, 'pool': {'value': 360, 'unit': 'points'}}
    return r


def actions_remediation():
    """N3 actions generated from privacy issues (category as title, text quoted in Section 03);
    N4 projected rating after remediation (values as reported, conditional on a rescan)."""
    issue = 'Vague retention periods: the policy gives no deletion timeline.'
    r = report_with(section(
        'priority_actions', 'Priority actions (N3, N4)', 'findings', 'Synthetic: issue-based actions.',
        actions=[{'action_id': 'act-01', 'rank': 1, 'priority': 'high', 'title': 'Privacy', 'title_source': 'PRIVACY',
                  'category': 'privacy', 'estimated_time_reported': '2 weeks', 'required_role': 'Legal + DPO team',
                  'action_required_source': issue, 'linked_sections': ['privacy']},
                 {'action_id': 'act-02', 'rank': 2, 'priority': 'high', 'title': 'Reset Compromised Credentials',
                  'estimated_time_reported': '1 week', 'required_role': 'IT Security team',
                  'action_required_source': 'Enable multi-factor authentication (MFA) for all users.'}],
        remediation_impact={'state': 'findings', 'current': {'grade': 'CC', 'score': 86, 'pool': 360},
                            'projected': {'grade': 'A', 'score': 280, 'pool': 360}, 'points_recoverable': 194,
                            'active_issues': {'total': 224, 'privacy': 13, 'vulnerability': 211, 'credentials': 40},
                            'conditional_on_rescan': True,
                            'narrative_source': 'Completing the recommended actions is expected to recover up to '
                                                '194 points, conditional on a fresh scan.'}))
    r['sections']['privacy'] = {'title': 'Privacy', 'state': 'findings',
                                'policy': {'issues': [{'label': 'Issue 9', 'category': 'privacy', 'text': issue}]}}
    return r


def privacy_c():
    """N5 placeholder country code XX; N6 roles found with sources; preference enabled -> compared with the
    owner/requestor preference (match). Section layout v15: the sub-areas are their own sections."""
    r = report_with(section(
        'privacy', 'Privacy (N5, N6, preference wording)', 'findings', 'Synthetic: placeholder country, roles found.',
        policy={'state': 'findings', 'policy_state': {'value': 'valid_assessed'},
                'policy_source': {'value': 'https://www.example.com/privacy'}, 'metrics': privacy_metrics(56, 0, 1)}))
    r['sections'].update(
        legal_terms={'state': 'not_applicable', 'reason_code': 'no_login_or_payment_portal_detected',
                     'portal_detected': False},
        data_sovereignty={'state': 'clear', 'enabled': True, 'allowed_set': ['European Union (EU)'],
                          'observed_jurisdiction': {'value': 'European Union (EU)'}, 'match_state': 'match'},
        data_residency={'state': 'findings', 'enabled': True, 'allowed_set': ['Argentina'], 'match_state': 'mismatch',
                        'intro_source': "Where this organisation's public systems are hosted, compared with where you "
                                        'allow data to live',
                        'observed_hosting': [
                            {'country': 'United States of America', 'hosts': 20, 'evidence_kind': NR},
                            {'country': None, 'hosts': 5, 'state': 'unavailable', 'reason_code': 'country_code_placeholder',
                             'source_label': 'XX (5 hosts)', 'evidence_kind': NR},
                            {'country': None, 'hosts': 30, 'state': 'unavailable', 'reason_code': 'location_unknown',
                             'evidence_kind': NR}]},
        security_resourcing={'state': 'findings', 'privacy_role_evidence': 'detected',
                             'security_role_evidence': 'detected',
                             'roles_found': [{'role': 'Data Protection Officer',
                                              'sources': ['Company Website', 'LinkedIn']}]})
    return r


def vulns_c():
    """N7 scanned domains / subdomains list; N8 active scan results (Clean / Scanned, reported vs listed
    counts, informational findings); a High severity finding."""
    subs = [f'{x}.{DOMAIN}' for x in ('m', 'smtp', 'imap', 'mta-sts', 'pop')]
    scan = lambda host, st, n=None, fs=(): {'target': f'https://{host}', 'status': st, 'scanned_at':
                                            {'value': '2026-10-01T18:29', 'precision': 'day'},
                                            'findings': list(fs), **({'findings_reported': n} if n is not None else {})}
    info = lambda t: {'title': t, 'severity': 'info', 'description': 'An SMTP service was detected.',
                      'impact': 'Could be abused if misconfigured.', 'remediation': 'Require authentication.'}
    return report_with(section(
        'vulnerabilities', 'Vulnerabilities (N7, N8, High)', 'findings', 'Synthetic: scanned assets and active scan.',
        metrics=vuln_metrics(2),
        scanned_assets={'domains': [DOMAIN], 'subdomains': subs},
        findings=[finding(1, 'high', 1, [f'm.{DOMAIN}']), finding(2, 'low', 2, subs[:2])],
        active_scan={'state': 'findings', 'results': [
            scan(DOMAIN, 'clean'), scan(f'm.{DOMAIN}', 'clean'),
            scan(f'imap.{DOMAIN}', 'scanned', 5, [info('SMTP Service Detection on Port 25'),
                                                  info('SMTP Commands Enumeration')])]},
        email_dns_controls={'state': 'clear', 'controls': [
            {'finding_id': c, 'control': c.upper(), 'result': 'enabled', 'state': 'clear'}
            for c in ('spf', 'dkim', 'dmarc')] + [{'finding_id': 'dnssec', 'control': 'DNSSEC', 'result': 'valid',
                                                  'state': 'clear'}]},
        https_redirect={'state': 'clear', 'result': 'redirects_to_https'}))


def vendors_profile():
    """N9 vendor company profile (employees, revenue as printed, headquarters, founded, technologies)."""
    v = lambda i, name, g, band, **kw: {'vendor_id': f'v-{i}', 'name': name, 'domain': f'{name.lower()}.example.net',
                                        'grade': g, 'risk_band': band, 'risk_band_label_source': band.capitalize(),
                                        'category': 'information technology & services', 'evidence': NR, **kw}
    return report_with(section(
        'fourth_party_vendors', 'Fourth-party vendors (N9 profile)', 'findings', 'Synthetic: vendor profiles.',
        vendors=[v(1, 'Alpha', 'AAA', 'low', employees=5200, revenue_source='2.2B', headquarters='Example City, '
                   'Example Country', founded=2009, technologies_count=573),
                 v(2, 'Beta', 'CC', 'high', employees=1500, revenue_source='398M', founded=2001),
                 v(3, 'Gamma', 'A', 'low', technologies_count=2005, technologies_more_source='+2000 more',
                   technologies_sample_source=['A', 'B', 'C', 'D', 'E'])]))


def _org(i, name, g=None, band=None, domain=None, **kw):
    """One connected organisation (s14). g None: not rated (sibling null form, reason given or not)."""
    o = {'vendor_id': f'v-{i}', 'name': name, 'domain': domain or f'{name.lower()}.example.net',
         'grade': g, 'risk_band': band, 'category': 'information technology & services', 'evidence': NR, **kw}
    if g is None:
        o.setdefault('grade_state', 'unavailable')
        o.setdefault('grade_reason_code', 'dash_in_source')
        o['risk_band_state'], o['risk_band_reason_code'] = 'unavailable', 'dash_in_source'
    elif band:
        o['risk_band_label_source'] = band.capitalize()
    return o


GRADE_BANDS = [('AAA', 'low'), ('AA', 'low'), ('A', 'low'), ('BBB', 'medium'), ('BB', 'medium'),
               ('B', 'high'), ('CCC', 'high'), ('CC', 'critical')]


def vendors_t2():
    """35 connected organisations (> 30: T2, top table + Appendix D.6.1); 2 not rated (one with a reason)."""
    orgs = [_org(i, f'Org{i:02d}', *GRADE_BANDS[i % len(GRADE_BANDS)]) for i in range(1, 34)]
    orgs += [_org(34, 'Unrated34'), _org(35, 'Scoped35', grade_reason_code='outside_assessment_scope',
                                         grade_reason='outside the scope of the rating service')]
    r = report_with(section('fourth_party_vendors', 'Fourth-party vendors (T2, 35 rows)', 'findings',
                            'Synthetic: 35 organisations.', vendors=orgs,
                            metrics=[{'id': 'fourth_parties', 'label': 'Fourth-party vendors', 'value': 35,
                                      'unit': 'organisations', 'state': 'findings'}]))
    r['rating'] = {'grade': 'BB'}
    r['appendices']['d_evidence_registers'] = {'title': 'Detailed evidence registers', 'state': 'findings'}
    return r


def vendors_self12():
    """12 organisations: a self-reference (app.example.com, under Example Org's example.com), an alias pair (Amazon / Aws),
    an unrated one without a reason, a rating with assessed_membership false, per-organisation assessed_at."""
    day = lambda d: {'value': d, 'precision': 'day'}
    orgs = [_org(i, f'Org{i:02d}', *GRADE_BANDS[i % len(GRADE_BANDS)], assessed_at=day(f'2026-09-{i:02d}'))
            for i in range(1, 9)]
    orgs += [_org(9, 'Example', 'BBB', 'medium', domain='app.example.com', assessed_at=day('2026-09-20')),
             _org(10, 'Amazon', 'B', 'high', domain='amazon.com', assessed_at=day('2026-09-21')),
             _org(11, 'Aws', 'BBB', 'medium', domain='aws.com', assessed_membership=False,
                  assessed_at={'value': None, 'state': 'unavailable', 'reason_code': 'not_printed_in_source'}),
             _org(12, 'Unrated12', assessed_at={'value': None, 'state': 'unavailable',
                                                'reason_code': 'not_printed_in_source'})]
    return report_with(section('fourth_party_vendors', 'Fourth-party vendors (12, self-reference)', 'findings',
                               'Synthetic: 12 organisations.', vendors=orgs))


def vendors_empty():
    """Empty list sent as clear -> none_identified (never 'No findings')."""
    return report_with(section('fourth_party_vendors', 'Fourth-party vendors (empty)', 'clear',
                               'No fourth-party vendors were discovered.', vendors=[],
                               metrics=[{'id': 'fourth_parties', 'label': 'Fourth-party vendors', 'value': 0,
                                         'unit': 'organisations', 'state': 'clear'}],
                               empty_state_source={'coverage': 'Automated technology discovery.'}))


def vendors_nullreason():
    """Not rated in the NullReason object form, with and without a reason (no raw dict may print)."""
    orgs = [_org(1, 'Rated1', 'CC', 'critical'),
            {**_org(2, 'Nullobj2'), 'grade': {'value': None, 'state': 'unavailable',
                                               'reason_code': 'not_printed_in_source'}},
            {**_org(3, 'Nullobj3'), 'grade': {'value': None, 'state': 'unavailable', 'reason_code': 'not_scanned',
                                               'reason': 'the organisation has not been scanned yet'}},
            {**_org(4, 'Bandnull4', 'B', None), 'risk_band': NR}]
    return report_with(section('fourth_party_vendors', 'Fourth-party vendors (null forms)', 'findings',
                               'Synthetic: null forms.', vendors=orgs))


def creds_status():
    """N10 per-row status column (all 'Open' in the Gmail sample) -> counts only."""
    rows = [{'id': f'cred-{i:04d}', 'email_domain': DOMAIN, 'email_state': 'masked_label_present',
             'exposure_period_source': '2025', 'exposure_years': [2025], 'exposure_period_has_unknown': False,
             'exposed_field_categories': ['email', 'password'], 'breach_source_name': NR,
             'status': 'Open' if i < 5 else 'Resolved'} for i in range(1, 7)]
    r = creds(rows, 6)
    r['sections']['credential_exposure']['title'] = 'Credential exposure (N10 row status)'
    return r


def ai_missing():
    """N11 the source report has no AI section at all (8 sections) -> unavailable, reason stated."""
    return report_with(section('ai_risk_governance', 'AI risk and governance (N11 not in source)', 'unavailable',
                               'AI risk is not covered by this source report.', reason_code='section_not_in_source'))


def quantum_q6():
    """N12 'Partly Quantum Safe' printed as '#'; N13 Key exchange category, NTRU Prime PQC; N14 scope-row
    risk with explanation; N15 affected protocols; Q6 headline (category totals) != apex row (KPI = headline)."""
    rows = [qrow(1, DOMAIN, 2, 4), qrow(2, f'test.{DOMAIN}', 1, 1)]
    rows[0].update(risk_level='low', risk_note_source='This finding is covered by ML-KEM, therefore the risk is Low.')
    rows[1].update(category='Key exchange', pre_qc_algorithm='SSH_HOST_KEY_RSA', risk_level='high',
                   risk_note_source='Partial coverage: NTRU Prime detected, but not on the TLS scope; risk unchanged.')
    r = quantum(rows, (3, 6), pqc=[{'algorithm': 'NTRU Prime', 'algorithm_alias': 'Streamlined NTRU Prime',
                                     'purpose': 'Key exchange / encryption',
                                     'status_source': 'Status: Deployed in OpenSSH (not NIST-selected)',
                                     'domains_count': 1, 'domains': [f'test.{DOMAIN}']}])
    sec = r['sections']['quantum_security']
    sec['title'] = 'Quantum security (N12-N15, Q6)'
    sec['metrics'].append({'id': 'partly_quantum_safe', 'label': 'Partly Quantum Safe', 'value': None, 'unit': 'scopes',
                           'state': 'unavailable', 'reason_code': 'placeholder_in_source', 'source_label': '#'})
    sec['findings_by_category'].append({'category': 'Key exchange', 'issues': 1, 'algorithms': [
        {'algorithm': 'SSH_HOST_KEY_RSA', 'findings': 1, 'protocol_labels': ['SSH'], 'pqc_alternative_available': None,
         'pqc_alternative_available_state': 'unavailable', 'pqc_alternative_available_reason_code': 'not_printed_in_source'}]})
    sec['affected_protocols'] = [{'protocol': 'TLS_1_2', 'algorithms': ['RSA'], 'pqc_source': 'ML-KEM available',
                                  'risk_level': 'low'},
                                 {'protocol': 'SSH', 'algorithms': ['SSH_HOST_KEY_RSA'],
                                  'pqc_source': 'NTRU Prime available', 'risk_level': 'high'}]
    return r


def cloud_old_scan():
    """Business answer 8: a scan years older than the assessment prints its date only, no staleness flag."""
    return report_with(section('cloud_infrastructure', 'Cloud infrastructure (old scan date)', 'findings',
                               'Synthetic: one provider, scanned long before the assessment.',
                               detection_methods=['dns_records'],
                               last_scanned={'value': '2023-01-05', 'precision': 'day'},
                               providers=[{'provider': 'Example Cloud', 'detection_methods': ['dns_records'],
                                           'observed_at': {'value': '2023-01-05', 'precision': 'day'}}]))


def leaks_nulls():
    """Null forms on every event field the renderer reads: NullReason object and '<field>_state/_reason_code'
    siblings (source_url, entity_link, event_type, scoring_reason, records_unit, date_basis...)."""
    sib = lambda k, code='not_printed_in_source': {k: None, f'{k}_state': 'unavailable', f'{k}_reason_code': code}
    ev = lambda i, **kw: {'event_id': f'ev-{i}', 'occurred_at': {'value': '2025-08-22', 'precision': 'day'}, **kw}
    return report_with(section(
        'data_leak_history', 'Data breach and leak history (null forms)', 'findings',
        'Synthetic: null source URLs and texts in both documented forms.',
        last_valid_event={'value': None, 'state': 'unavailable', 'reason_code': 'not_printed_in_source'},
        events=[ev(1, source_url=dict(NR), entity_link=dict(NR), event_type=dict(NR), scoring_reason=dict(NR),
                   description_source=dict(NR), records_affected=10, records_unit=dict(NR), date_basis=dict(NR),
                   canonical_event_id=dict(NR)),
                ev(2, entity_link=f'portal.{DOMAIN}', records_affected=dict(NR), **sib('source_url', 'blank_in_source')),
                ev(3, entity_link=DOMAIN, source_url=f'https://news.example.net/report-3', records_affected=5)]))


def actions_nulls():
    """s02: null 'why it matters' / action text never printed raw; a null remediation_impact draws no block."""
    return report_with(section(
        'priority_actions', 'Priority actions (null forms)', 'findings', 'Synthetic: null texts.',
        actions=[{'action_id': 'act-01', 'rank': 1, 'priority': 'high', 'title': 'Privacy',
                  'action_required_source': 'Review the retention clause.', 'why_this_matters_source': dict(NR)},
                 {'action_id': 'act-02', 'rank': 2, 'priority': 'low', 'title': 'Security',
                  'action_required_source': dict(NR), 'why_this_matters_source': None,
                  'why_this_matters_source_state': 'unavailable',
                  'why_this_matters_source_reason_code': 'not_printed_in_source'}],
        remediation_impact=dict(NR)))


def vulns_d():
    """s04: scanned_assets null with a reason; an active-scan host with informational findings, a summary and
    recommendations_source."""
    info = lambda t: {'title': t, 'severity': 'info', 'severity_label_source': 'INFO',
                      'description': 'An SMTP service was detected.', 'impact': 'Could be abused if misconfigured.',
                      'remediation': 'Require authentication.'}
    return report_with(section(
        'vulnerabilities', 'Vulnerabilities (null scanned assets, recommendations)', 'findings',
        'Synthetic: assets list blank in source.', metrics=vuln_metrics(1),
        scanned_assets={'value': None, 'state': 'unavailable', 'reason_code': 'blank_in_source'},
        findings=[finding(1, 'low', 1, [f'm.{DOMAIN}'])],
        active_scan={'state': 'findings', 'results': [
            {'target': f'https://smtp.{DOMAIN}', 'status': 'scanned', 'findings_reported': 1,
             'scanned_at': {'value': '2026-10-01T18:29', 'precision': 'day'},
             'summary_source': 'Only informational findings were identified.',
             'recommendations_source': ['Require SMTP authentication.', 'Review exposed services regularly.'],
             'findings': [info('SMTP Service Detection on Port 25')]}]}))


PRIVACY_SET = ('s03', 's07', 's08', 's09', 's12')     # privacy + its former sub-areas
UNVALIDATED = {'privacy_b'}     # deliberately breaks the load contract (no-result state without a reason)
VARIANTS = [
    ('privacy_a', ['P5', 'P8/P9', 'P11/P16', 'P13/P14'], PRIVACY_SET, privacy_a),
    ('privacy_b', ['P3/P7', 'P14'], PRIVACY_SET, privacy_b),
    ('vulns_a', ['V4', 'V6/V8', 'V12', 'V14', 'V18'], 's04', vulns_a),
    ('vulns_b', ['V13'], 's04', vulns_b),
    ('certs', ['C1-C3', 'C4/C5', 'C6', 'C8/C9', 'C10'], 's13', certs),
    ('certs_uploaded', ['issuer + scope', 'OTHER', 'headline vs records', 'D.5 documents'], ('s13', 'appD'), certs_uploaded),
    ('certs_mixed', ['detected + uploaded', 'validity not detected', 'review action'], ('s02', 's13'), certs_mixed),
    ('leaks', ['D3/D4', 'D6', 'D8/D9', 'L1 resolved', 'L2 no flag'], 's06', leaks),
    ('creds_c2', ['C2 (s05)'], 's05', creds_c2),
    ('creds_c3', ['C3 (s05)'], 's05', creds_c3),
    ('ai', ['A3', 'A5'], 's10', ai),
    ('quantum_q1', ['Q1', 'Q4'], 's11', quantum_q1),
    ('quantum_q2', ['Q2'], 's11', quantum_q2),
    ('quantum_q5', ['Q5'], 's11', quantum_q5),
    ('overview_sector', ['N1 sector', 'N2 band display'], 's01', overview_sector),
    ('actions_remediation', ['N3 issue actions', 'N4 remediation impact'], 's02', actions_remediation),
    ('privacy_c', ['N5 XX', 'N6 roles found', 'P owner/requestor'], PRIVACY_SET, privacy_c),
    ('vulns_c', ['N7 scanned assets', 'N8 active scan', 'High'], 's04', vulns_c),
    ('vendors_profile', ['N9 vendor profile'], 's14', vendors_profile),
    ('vendors_self12', ['s14 self-reference', 'alias', 'assessed_at'], 's14', vendors_self12),
    ('vendors_empty', ['s14 none identified'], 's14', vendors_empty),
    ('vendors_nullreason', ['s14 null forms'], 's14', vendors_nullreason),
    ('creds_status', ['N10 row status'], 's05', creds_status),
    ('ai_missing', ['N11 not in source'], 's10', ai_missing),
    ('quantum_q6', ['N12-N15', 'Q6'], 's11', quantum_q6),
    ('cloud_old_scan', ['no stale flag'], 's15', cloud_old_scan),
    ('leaks_nulls', ['null forms s06'], 's06', leaks_nulls),
    ('actions_nulls', ['null forms s02'], 's02', actions_nulls),
    ('vulns_d', ['null scanned assets', 'scan recommendations'], 's04', vulns_d),
]


def render(out, only=None):
    """Every variant on its own page(s), one PDF + QA json. Returns (pages, counts, text per variant)."""
    import dataclasses

    import pymupdf

    from cyberrank_report import components as C, qa
    from cyberrank_report.build import validate
    from cyberrank_report.page import ReportDoc, cover_flowables, identity_from_report
    from cyberrank_report.sections import BY_ID, adjust_report, render_section

    qa.ISSUES.clear()
    story = cover_flowables()
    ident = identity_from_report(base())
    for vid, gaps, sid, make in VARIANTS:
        if only and vid not in only:
            continue
        rep = make()
        rep = adjust_report(rep if vid in UNVALIDATED else validate(rep))
        for s in sid if isinstance(sid, tuple) else (sid,):
            spec = dataclasses.replace(BY_ID[s], id=f'{s}-{vid}')      # unique anchor + outline entry
            story += render_section(spec, rep, ident)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = ReportDoc(str(out), ident, subject='Condition-matrix gap variants (synthetic)')
    total = doc.render(story)
    issues = list(qa.ISSUES) + qa.check_pdf(str(out), table_parts=doc.table_parts, table_heads=C._TABLE_HEADS)
    counts = qa.write_report(out.with_suffix('.qa.json'), out, issues, pages=total)
    pdf = pymupdf.open(out)
    return total, counts, ''.join(p.get_text() for p in list(pdf)[1:]), issues      # text without the cover


if __name__ == '__main__':
    total, counts, _, _ = render(sys.argv[1])
    print(f'{sys.argv[1]}: {total} pages; QA {counts}')
    sys.exit(2 if counts['error'] else 0)
