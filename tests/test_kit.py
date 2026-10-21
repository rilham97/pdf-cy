"""Kit self-check: .venv/bin/python tests/test_kit.py  (also runs under pytest)."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from reportlab.pdfbase.pdfmetrics import stringWidth  # noqa: E402

from cyberrank_report import components as C, qa, theme as T  # noqa: E402
from cyberrank_report.build import build  # noqa: E402
from cyberrank_report.page import ellipsize  # noqa: E402

TOKENS = ['https://support.claude.com/en/articles/10015870-what-certifications-has-anthropic-obtained',
          'sha256:6bfaaf3db89aa0714f3d4b4821c13ccfa3b3548324535fd81f4a22ceb7182f8d',
          'url6377.updates.claude.com, links.email.claude.com, pubmed.mcp.claude.com']


def test_tech_lines_never_drop_or_overflow():
    for tok in TOKENS:
        for width in (40, 90, 165, 515):
            lines = C.tech_lines(tok, width, 'Poppins-Light', 8.6)
            assert ''.join(lines).replace(' ', '') == tok.replace(' ', ''), (tok, width)
            assert all(stringWidth(s, 'Poppins-Light', 8.6) <= width for s in lines), (tok, width)
    # prefers the technical break point over a mid-label cut
    assert C.tech_lines('support.claude.com', 60, 'Poppins-Light', 8.6)[0] == 'support.'


def test_ellipsize():
    assert ellipsize('Claude', 200) == 'Claude'
    long = 'Very Long Organisation Name International Holdings Proprietary Limited'
    out = ellipsize(long, 150)
    assert out.endswith('…') and stringWidth(out, 'Poppins-Medium', 10) <= 150
    assert long.startswith(out[:-1].rstrip()) and not out[:-1].endswith(' ')


def test_missing_is_never_zero():
    assert C.fmt_value({'value': None, 'reason_code': 'no_events'}) == 'Not available (no events to show)'
    assert C.fmt_value({'value': 0, 'unit': 'events'}) == '0 events'
    assert C.fmt_value(43, 'percent') == '43%'
    assert C.fmt_value(1, 'policies') == '1 policy'
    assert C.fmt_date({'value': '2026-10-02', 'precision': 'day'}) == '02 Oct 2026'


def test_build_all_states():
    secs = {}
    for i, st in enumerate(('findings', 'clear', 'not_assessed', 'not_applicable', 'unavailable', 'partial',
                            'pending_review'), start=1):
        secs[f'k{i}'] = {'title': st, 'state': st, 'summary': f'{st} verdict.', 'intro_source': 'Intro.',
                         'metrics': [{'label': 'Score', 'value': None if i % 2 else 50, 'unit': 'percent',
                                      'state': st, 'reason_code': 'not_printed_in_source'}]}
    report = {'identity': {'organisation_name': 'Example Org', 'domain': 'example.com'},
              'snapshot': {'assessed_at': {'value': '2026-10-02'}, 'generated_at': {'value': '2026-10-03'}},
              'sections': secs}
    from cyberrank_report import sections as S
    saved = S.REGISTRY[:]
    S.REGISTRY[:] = [S.SectionSpec(f's{i:02d}', f'k{i}', f'{i:02d}', f'k{i}', 'assessment_details', '_template')
                     for i in range(1, 8)]
    try:
        qa.ISSUES.clear()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'r.pdf'
            total, counts = build(report, out)
            data = json.loads(out.with_suffix('.qa.json').read_text())
    finally:
        S.REGISTRY[:] = saved
    assert total == 9, total                     # cover + contents + 7 sections
    assert counts['error'] == 0, data['issues']


def _render(story):
    """Cover + story through ReportDoc; returns (pdf path, qa issues incl. render-time ones)."""
    from cyberrank_report.page import ReportDoc, cover_flowables
    ident = {'org': 'Example Org', 'domain': 'example.com', 'title': 'Cyber Risk Report',
             'assessment_date': '02 Oct 2026', 'generated_date': '03 Oct 2026', 'issuer': None,
             'issuer_reason': 'not recorded', 'logo': None}
    qa.ISSUES.clear()
    out = Path(tempfile.mkdtemp()) / 'k.pdf'
    doc = ReportDoc(out, ident)
    doc.render(cover_flowables() + story)
    return out, list(qa.ISSUES) + qa.check_pdf(out)


def test_motif_only_page_is_blank():
    # header + footer + bottom motif, no content: the motif must not count as content
    _, issues = _render([C.Anchor('empty')])
    assert any(i['check'] == 'blank_page' and i['page'] == 2 for i in issues), issues


def test_heading_never_left_at_page_foot():
    from reportlab.platypus import Spacer
    from cyberrank_report import theme as T
    rows = [[f'row {i}', i] for i in range(8)]
    out, issues = _render([Spacer(0, T.FRAME_H - 60), C.heading('Orphan candidate', 2),
                           C.keep(C.compact_table(['Name', 'Count'], rows, numeric_cols=(1,)), C.note('Note.'))])
    assert not [i for i in issues if i['check'] == 'heading_at_page_foot'], issues
    import pymupdf
    assert pymupdf.open(out)[2].search_for('Orphan candidate')      # moved to page 3 with its block


def test_narrow_column_split_and_null_footnote():
    nr = {'value': None, 'reason_code': 'not_printed_in_source'}
    t = C.compact_table(['#', 'Effort'], [[1, nr], [2, nr], [3000000, 'x']], widths=[18, 70], numeric_cols=(0,))
    assert 'Not available<super>1</super>' in t._cellvalues[1][1].text
    assert 'Not provided in the assessment data.' in t._cellvalues[-1][0].getPlainText()
    _, issues = _render([t])
    assert any(i['check'] == 'word_split' and '3,000,000' in i['detail'] for i in issues), issues


FIXTURE = Path(__file__).resolve().parents[1] / 'data' / 'claude-2026-10-02.json'


def test_input_validation_rejects_contract_errors():
    from cyberrank_report.build import InputError, validate
    report = json.loads(FIXTURE.read_text(encoding='utf-8'))
    validate(report)                                             # the fixture honours the contract
    sec = report['sections']['vulnerabilities']
    sec['state'] = 'done'                                        # not in the state enum
    sec['metrics'][0].pop('unit')                                # metric without a unit
    sec['findings'][0]['affected_assets_count'] = None           # null without a reason
    try:
        validate(report)
    except InputError as e:
        msg = str(e)
    else:
        raise AssertionError('invalid payload accepted')
    assert msg.startswith('3 input contract error(s)'), msg
    assert 'sections.vulnerabilities.state: state "done"' in msg
    assert 'sections.vulnerabilities.metrics[0]' in msg and 'has no unit' in msg
    assert 'sections.vulnerabilities.findings[0].affected_assets_count: null without a reason' in msg


def test_continued_caption_row_range():
    rows = [[f'row {i}', i] for i in range(1, 81)]
    out, issues = _render([C.heading('Long list', 2), C.compact_table(['Name', 'Count'], rows, numeric_cols=(1,))])
    import pymupdf
    doc = pymupdf.open(out)
    assert doc[2].search_for('Long list') and doc[2].search_for('continued'), doc[2].get_text()[:200]
    text = doc[2].get_text()
    assert 'of 80' in text and 'Rows ' in text, text[:300]
    first = int(text.split('Rows ', 1)[1].split('–', 1)[0])
    assert doc[1].search_for(f'row {first - 1}') and not doc[1].search_for(f'row {first}\n'), first


def test_credential_crosstab_and_caveat():
    from cyberrank_report.page import identity_from_report
    from cyberrank_report.sections import s05_credential_exposure as s05
    report = json.loads(FIXTURE.read_text(encoding='utf-8'))
    sec = report['sections']['credential_exposure']
    d = s05.derive(sec, report, identity_from_report(report))
    assert d['cross']['assessed'] == [18, 11, 0] and d['cross']['unknown_email'] == [1, 0, 0], d['cross']
    assert d['lead'] == 18 and d['lead_recent'] == 1 and d['lead_unknown'] == 3 and d['origin'] == 2
    # buckets by latest year: recent + older + 'Unknown' only = lead (no row labelled 'Unknown' twice)
    assert d['lead_recent'] + sum(d['lead_older'].values()) + d['lead_unknown'] == d['lead']
    label = s05.lead_label(d)
    assert '14 with latest year 2008–2024' in label and '3 with period “Unknown” only' in label, label
    for cross in (d['cross'], {**d['cross'], 'other_domain': [5, 0, 0]}):      # caveat prints whatever the split
        flow = s05.crosstab({**d, 'cross': cross})
        assert any("mailbox provider" in getattr(f, 'getPlainText', lambda: '')() for f in flow)


def test_icons_selftest():
    from cyberrank_report import icons
    icons._selftest()


# --- condition-matrix gaps (fixtures: tests/gap_fixtures.py) ---------------------------------
_GAP = {}


def _gap(vid):
    """Rendered text of one gap variant (cached) and its QA issues."""
    if vid not in _GAP:
        import gap_fixtures as G
        total, counts, text, issues = G.render(Path(tempfile.mkdtemp()) / f'{vid}.pdf', only=[vid])
        assert counts['error'] == 0, [i for i in issues if i['severity'] == 'error']
        _GAP[vid] = (' '.join(text.split()), issues)
    return _GAP[vid]


def _checks(issues):
    return {(i['check'], i['detail'].split(':', 1)[0]) for i in issues}


def _payload_text(report, only):
    """Flattened text + QA issues of a synthetic payload built through validate + build (0 QA errors)."""
    import pymupdf
    from cyberrank_report.build import validate
    qa.ISSUES.clear()
    out = Path(tempfile.mkdtemp()) / 'p.pdf'
    _, counts = build(validate(report), out, only=only)
    issues = json.loads(out.with_suffix('.qa.json').read_text())['issues']
    assert counts['error'] == 0, [i for i in issues if i['severity'] == 'error']
    return ' '.join(' '.join(p.get_text() for p in pymupdf.open(out)).split()), issues


def test_gap_privacy():
    text, issues = _gap('privacy_a')
    assert 'Not recognised (“draft”)' in text and 'Result held for review' in text            # P5
    assert '# No' not in text and 'Neither clause found; counted against the rating.' in text   # P8/P9
    assert 'Not compared: no preference set' in text and 'governed by the laws of Singapore' in text  # P13/P14
    assert 'counted as outside the preferred countries' in text                                # P11/P16
    text, _ = _gap('privacy_b')
    assert 'Reason not recorded' not in text and 'states it has no privacy policy' in text      # P3/P7
    assert 'One clause found; not counted against the rating.' in text
    assert text.count('Not compared: no preference set') >= 2                                   # P14 residency


def test_gap_vulnerabilities():
    text, issues = _gap('vulns_a')
    assert '1 informational finding type is listed below but not counted' in text               # V4
    assert ('data_mismatch', 's04') in _checks(issues)
    assert 'showing 3 of 5' in text and 'No affected domain recorded' in text                   # V6/V8
    assert 'Enabled, monitoring only (p=none)' in text                                          # V12
    assert 'SPF Not reported' in text and 'not a pass' in text                                   # V14
    assert 'IP Reputation — Clean' in text and 'held for review' in text                        # V18
    assert 'Not available' in text and 'The source printed "-1"' in text
    text, _ = _gap('vulns_b')
    assert 'already p=reject' in text and 'do not agree' in text                                # V13


def test_vuln_type_with_several_severities():
    """One finding type at two severities on different domains: listed once per severity, with a note only
    in that case; a repeated finding_id raises QA duplicate_finding_id."""
    import gap_fixtures as G
    hosts = [f'h{i}.{G.DOMAIN}' for i in range(3)]

    def rep(findings):
        return G.report_with(G.section('vulnerabilities', 'Vulnerabilities (multi-severity type)', 'findings',
                                       'Synthetic: one type at two severities.',
                                       metrics=G.vuln_metrics(len(findings)), findings=findings))
    crit, high = G.finding(1, 'critical', 1, hosts[:1]), G.finding(2, 'high', 2, hosts[1:])
    crit['finding_type'] = high['finding_type'] = 'cert_notAfter'
    text, issues = _payload_text(rep([crit, high]), ['s04'])
    assert 'cert_notAfter appears under more than one severity' in text, text
    assert ('duplicate_finding_id', 's04') not in _checks(issues)
    text, issues = _payload_text(rep([G.finding(1, 'critical', 1, hosts[:1]), G.finding(2, 'high', 2, hosts[1:])]),
                                 ['s04'])
    assert 'more than one severity' not in text, text                    # no such case: no note
    high['finding_id'] = crit['finding_id']
    _, issues = _payload_text(rep([crit, high]), ['s04'])
    assert ('duplicate_finding_id', 's04') in _checks(issues), issues


def _demo_variant(mutate, only, check=True):
    """Flattened text + QA issues of data/demo-preview.json after mutate(report), built through validate()
    (check=False: a payload the contract would stop, e.g. a no-result state without a reason)."""
    import pymupdf
    from cyberrank_report.build import validate
    r = json.loads((FIXTURE.parent / 'demo-preview.json').read_text(encoding='utf-8'))
    mutate(r)
    qa.ISSUES.clear()
    out = Path(tempfile.mkdtemp()) / 'v.pdf'
    build(validate(r) if check else r, out, only=only)
    return ' '.join(' '.join(p.get_text() for p in pymupdf.open(out)).split()), list(qa.ISSUES)


def test_s04_scanned_assets_x_of_y():                                  # owner design 2026-10-19
    t = _fixture_text('demo-preview', ['s04'])
    assert 'Scanned assets 12 of 12 scanned domains have at least one finding' in t, t[:2000]
    assert '2 Critical 3 High 4 Medium 3 Low' in t and 'no finding reported' not in t   # zero bucket hidden
    assert 'Expired TLS certificate appears under more than one severity' in t          # vuln-03 + vuln-13
    assert 'Breach likelihood by domain' in t and 'legacy.example.com / 192.0.2.80 4 44%' in t   # per domain, top first
    assert 'Indicates the estimated probability' not in t and 'Breach likelihood 38%' not in t        # no per-finding
    assert 'memberships' not in t and 'asset labels' not in t                                   # KPI tiles hidden
    assert '13 Finding types' in t and '13 finding types Finding types' not in t       # no repeated unit
    from cyberrank_report.sections import s04_vulnerabilities as s04
    hits, partial, outside = s04._scan_hits(
        {'findings': [{'severity': 'low', 'affected_assets': ['a.example.com / 192.0.2.1'], 'affected_assets_count': 2},
                      {'severity': 'high', 'affected_assets': ['A.example.com', 'z.example.org']}]},
        ['a.example.com', 'b.example.com'])
    assert hits == {'a.example.com': 1} and partial and outside == ['z.example.org']
    import copy                                                          # all good: a known 0, positive line
    r = copy.deepcopy(json.loads((FIXTURE.parent / 'demo-preview.json').read_text(encoding='utf-8')))
    v = r['sections']['vulnerabilities']
    v.update(findings=[], state='clear', metrics=[{'id': 'finding_types', 'label': 'Finding types', 'value': 0,
                                                  'unit': 'finding_types'}])
    t, _ = _payload_text(r, ['s04'])
    assert '0 of 12 scanned domains have at least one finding No finding on any scanned domain' in t, t[:1500]
    assert 'Scanned: 1 domain and 11 subdomains.' in t and 'the rest are grey' not in t


def test_s03_review_fixes():                                          # code review 2026-10-19, items 1-4
    def excluded(r):
        p = r['sections']['privacy']
        p['review_flags'] = ['RF-T1']
        r['review_flags'] = [{'id': 'RF-T1', 'text': 'Section flag text.'}, {'id': 'RF-T2', 'text': 'Policy flag text.'}]
        p['policy'].update(state='not_applicable', policy_state={'value': 'excluded_no_policy'}, issues=[],
                           review_flags=['RF-T2'])
    text, _ = _demo_variant(excluded, ['s03'], check=False)      # no reason of its own: the card explains
    assert text.count('No score: the organisation states') == 1, text                         # 1: once
    assert 'Review flag RF-T1: Section flag text.' in text and 'Review flag RF-T2: Policy flag text.' in text  # 2
    assert 'issues reported; issue detail' not in text                                       # 3: excluded count

    def areas(r):
        pol = r['sections']['privacy']['policy']
        pol['issues'] = []
        pol['areas'] = [{'code': c, 'score': 0, 'max_score': 0 if c == 'A' else 10} for c in 'ABCDEFGHIJKLMNOP'] \
            + [{'code': 'Q', 'score': 3}]
    text, issues = _demo_variant(areas, ['s03'])
    assert '0 / 0' in text and ('data_mismatch', 's03') in _checks(issues)                      # 4: 0 printed as sent
    assert ('unknown_term', 's03') in _checks(issues)                                         # 4: code Q not dropped silently
    assert '6 issues reported; issue detail is not provided' in text                          # 3: metric fallback


def test_s04_review_fixes():                                          # code review 2026-10-19, items 6-19
    from cyberrank_report.sections import BY_ID, adjusted
    from cyberrank_report.sections.s04_vulnerabilities import adjust
    assert set(T.SEVERITY_TEXT) == {'critical', 'high', 'medium', 'low'}                       # 19

    def change(r):
        v = r['sections']['vulnerabilities']
        f = v['findings']
        f[0].pop('finding_type')                                                              # 6: ID in both tables
        f[1]['affected_assets_count'] = 1                                                     # 7: 3 listed, 1 counted
        v['scanned_assets']['domains'] = []                                                   # 17
        v['active_scan']['results'] = v['active_scan']['results'][:1]                          # 14: singular
        v['active_scan']['results'][0].update(findings_reported=0, findings=[{'title': 'x', 'severity': 'info'}])
        v['https_redirect'].update(state='partial', what_checked=None)                         # 18
        v['https_redirect'].pop('what_checked')
        v['email_dns_controls']['controls'] = [{'control': 'DMARC', 'result': 'enabled', 'state': 'clear',
                                                'dmarc_policy': {'value': None, 'reason_code': 'not_printed_in_source'}}]
    text, issues = _demo_variant(change, ['s04'])
    assert text.count('vuln-01') >= 3 and 'Unnamed finding' not in text                       # 6
    assert 'Affected domains (3 listed; count reported: 1)' in text                           # 7
    assert 'lists 3 affected domains but affected_assets_count=1' in ' '.join(i['detail'] for i in issues)
    assert 'apex' not in text and 'listed before subdomains' not in text                      # 17
    assert '1 host scanned: 0 clean, 0 with findings reported, 1 with no recognised status' not in text
    assert '1 host scanned: 1 clean' in text                                                  # 14
    assert 'lists more findings than it counts' in text                                       # 12
    assert text.count('HTTP correctly redirects to HTTPS') == 1                               # 18
    assert 'Verify the published DMARC policy (p=).' in text and 'before acting on priority action' not in text  # 11
    assert 'Time (reported)' not in text and 'Related priority actions Critical 0 High 1' in text   # 15/16 legend
    assert 'Full register' not in text                                                        # 8/9: D.1 is T1

    def scan_empty(r):
        r['sections']['vulnerabilities']['active_scan'].update(state='partial', results=[])
    text, _ = _demo_variant(scan_empty, ['s04'])
    assert 'Reason not recorded' not in text and 'Host results: Not available' in text        # 13
    # 10: {value: -1} and a pending_review check with its own reason are both held; the column is named
    ip = {'state': 'findings', 'rows': [{'ip_address': '2001:db8::1', 'abuse_score': {'value': -1}, 'reports': -1}]}
    out = adjust({'ip_reputation': ip}, {})['ip_reputation']
    assert all(out['rows'][0][k]['value'] is None for k in ('abuse_score', 'reports'))
    assert 'for the abuse score and reports' in out['state_reason']
    out = adjust({'ip_reputation': {**ip, 'state': 'pending_review', 'state_reason': 'Own.'}}, {})['ip_reputation']
    assert out['state_reason'] == 'Own.' and out['rows'][0]['reports']['value'] is None
    assert adjusted(BY_ID['s04'], {'ip_reputation': out}, {})['ip_reputation'] == out          # idempotent


def test_d1_registers_follow_the_long_list_rule():                    # code review 2026-10-19, items 8, 20-24
    def big(r):
        reg = r['appendices']['d_evidence_registers']['vulnerability_asset_register']
        reg['rows'] = [{'asset_label_source': f'h{i}.example.com', 'finding_ids': ['vuln-01'], 'finding_count': 1,
                        'max_severity': 'high'} for i in range(31)] + [
            {'asset_label_source': '2001:db8::7', 'finding_ids': [], 'finding_count': 1, 'max_severity': 'low'}]
        reg['counts'] = {'rows': 32, 'memberships': 32}
        ip = r['sections']['vulnerabilities']['ip_reputation']
        ip['rows'] = [{'ip_address': f'198.51.100.{i}', 'isp': 'Example', 'country': 'NL', 'abuse_score': i,
                       'reports': 1} for i in range(35)]
        r['sections']['vulnerabilities']['findings'][0].pop('affected_assets_count')
    text, _ = _demo_variant(big, ['s04', 'appD'])
    assert 'Full register Affected assets by finding · 32 rows' in text                       # 8: same title + count
    assert C._TABLE_HEADS['regD1'][:2] == ['#', 'Highest severity']
    assert 'Showing the 10 highest abuse scores of 35 IP addresses' in text and '198.51.100.34' in text
    d1 = text[text.index('One row per affected asset'):]
    assert '2001:db8::7 †' not in d1 and 'Not available' in d1                                 # 24 / 23
    assert 'Section 04 affected-asset counts 31 (difference +1)' in d1                        # 22: _count fallback
    assert 'One row per IP address' in text and '35 of 35 IP addresses' in text   # 21
    text, _ = _demo_variant(lambda r: r['sections']['vulnerabilities'].pop('ip_reputation'), ['appD'])
    assert 'Not required — all 12 affected assets shown in Section 04' in text                  # 20: T1 index only
    assert 'Not produced — IP reputation is not in the payload.' in text and 'all 0 IP' not in text   # 21


def test_gap_certifications():
    text, issues = _gap('certs')
    assert 'Approved' in text and 'Approved by team' not in text and 'automatically' not in text   # C1-C3
    assert 'Awaiting approval' in text and text.count('Rejected') >= 3                            # C4/C5 (both origins)
    assert 'files.example.com/uploads' in text.replace(' ', '') and 'verified' not in text.lower()
    for word in ('Credit', 'credit', 'Applied after caps', 'Not counted', 'points', 'eligib', 'cap)'):
        assert word not in text, word                                                           # weighting hidden
    assert text.count('Expired') == 1                                                          # C6: flag only
    assert 'expired at assessment' not in text and '31 Jan 2026' in text                        # dates shown, not compared
    assert 'Security + Privacy' in text                                                         # C8
    warned = ' '.join(i['detail'] for i in issues if i['check'] == 'data_mismatch')
    assert 'PCI DSS is rejected' in warned and 'ISO/IEC 27701' not in warned


def test_certifications_review_fixes():                                # code review 2026-10-19 (13)
    import gap_fixtures as G
    nr = G.NR
    r = G.report_with(G.section(
        'certifications', 'Certifications', 'clear', 'Synthetic: review fixes.',
        metrics=[{'id': 'certifications_headline', 'label': 'Certifications', 'value': 4, 'unit': 'certifications'}],
        reference_standards={'items': [{'standard': 'SOC 2', 'description': 'Service controls'}]},
        certificates=[G.cert(1, 'ISO/IEC 27001', 'approved', None, None),           # legacy origin, no state
                      G.cert(2, 'ISO/IEC 27001', 'uploaded', 'approved', None),    # same standard: one certification
                      G.cert(3, 'SOC 2', 'uploaded', 'approved', None, document=nr),
                      G.cert(4, 'OTHER', 'detected', 'pending', None),
                      G.cert(5, 'PCI DSS', 'detected', 'approved', None, expired={'value': True},
                             valid_from=nr, valid_until=nr),
                      G.cert(6, 'ISO 22301', 'detected', 'rejected', None)]))
    r['sections']['priority_actions'] = {'title': 'Priority actions', 'state': 'findings', 'actions': [{
        'action_id': 'act-01', 'rank': 1, 'priority': 'medium', 'title': 'Example action',
        'action_required_source': 'Example action text.'}]}
    text, issues = _payload_text(r, ['s02', 's13', 'appD'])
    assert 'not a confirmation that it is valid' not in text, text                     # 15: legacy shows Approved
    assert ('data_mismatch', 's13') not in _checks(issues), issues                    # 14: 4 standards, 6 records
    assert 'Document in Appendix' not in text and 'missing_document' not in str(issues)  # 16: null document
    assert text.count('(Other (standard not named))') == 2 and '(OTHER)' not in text, text  # 17: 13 + 02
    assert 'SOC 2 also appears among the certificates on record' in text, text         # 18: clear with records
    assert 'Expired Not available (not provided in the assessment data)' in text, text  # 19: reason kept


def test_gap_leaks():
    text, issues = _gap('leaks')
    assert 'Used in rating' not in text and 'Reported inaccurate · not scored' in text          # D3/D4
    assert 'Pending review' in text and 'Named event is not scoring eligible' in text
    assert '406 days before assessment' in text and 'demerit' not in text.lower()                                      # D6
    assert 'aggregate across several services' in text and 'counted once' in text              # D8/D9
    assert 'Events in the period checked (4)' in text
    assert 'Status not recorded' not in text and 'Valid' in text                                 # L2 valid by default
    assert 'Resolved' in text and 'not counted as open events' in text                          # L1
    assert 'Open events (excludes resolved) 3' in text or 'Open events' in text


def test_gap_credentials_and_ai():
    text, _ = _gap('creds_c2')
    assert '40' in text and 'listed: 0 register rows; difference −40' in text                   # C2
    text, _ = _gap('creds_c3')
    assert 'of 5 listed rows are on example.com; all are on other email domains' in text        # C3
    assert 'not a statement that the organisation is unaffected' in text
    text, issues = _gap('ai')
    assert 'Observations recorded for context' in text and 'not reconciled here' in text        # A3/A5
    assert ('data_mismatch', 's10') in _checks(issues)


def _demo():
    return json.loads((FIXTURE.parent / 'demo-preview.json').read_text(encoding='utf-8'))


def _built_text(rep, only):
    import pymupdf
    qa.ISSUES.clear()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / 'r.pdf'
        build(rep, out, only=only)
        text = ' '.join(' '.join(p.get_text() for p in pymupdf.open(out)).split())
    return text, list(qa.ISSUES)


def test_credential_review_fixes():                                      # code review 2026-10-19 (05 / D.2)
    from collections import Counter
    from cyberrank_report.page import identity_from_report
    from cyberrank_report.sections import Ctx, BY_ID, s05_credential_exposure as s05
    rep = _demo()
    sec, ident = rep['sections']['credential_exposure'], identity_from_report(rep)
    rows = rep['appendices']['d_evidence_registers']['credential_register']['rows']
    # D.2 end line: headline equals the rows -> no '±0' difference; D.2.2 precedence follows s05.CLASSES
    rows[0]['exposed_field_categories'] = ['email', 'shoe_size']          # unclassified, ranks second
    text, _ = _built_text(rep, ['s05', 'appD'])
    assert 'source headline 40 (unit not defined by the source)' in text and '±0' not in text, text[-600:]
    assert ('highest class (password, then a category not in the data class map, then sensitive personal data, '
            'then other identity fields)') in text
    # withheld rows and invalid affected domains raise QA with counts only
    rows[1]['email_domain'], rows[2]['affected_domain'] = 'x*@example.com', 'not a host!'
    qa.ISSUES.clear()
    d = s05.derive(sec, rep, ident)
    warn = {i['check']: i['detail'] for i in qa.ISSUES}
    assert d['suppressed'] == 1 and 'x*@' not in warn['mask_policy_violation'], warn
    assert '1 credential register rows' in warn['invalid_affected_domain'] and 'not a host!' not in str(warn)
    # status as received (the D.2.4 column prints it raw too); pointer only where D.2 renders
    assert 'OPEN 1' in s05.status_line({**d, 'rows': [{'status': 'OPEN'}], 'analysed': 1})[0].getPlainText()
    assert s05.register_printed('findings', d) and not s05.register_printed('none_identified', d)
    ctx = Ctx(BY_ID['s05'], rep, ident, 'none_identified', False)
    assert not [f for f in s05.build(sec, ctx) if type(f).__name__ == 'RegisterPointer']
    # latest-year reason follows the rows; lead label names Unknown Email rows
    assert s05.latest_reason({'years': Counter({None: 2})}) == 'Exposure year not given by the source'
    assert s05.latest_reason({'years': Counter({'unknown': 2})}) == s05.UNKNOWN
    cross = {'assessed': [0, 0, 0], 'assessed_subdomain': [0, 0, 0], 'other_domain': [2, 0, 0],
             'unknown_email': [1, 0, 0]}
    assert s05.lead_label({'analysed': 3, 'assessed': 'example.com', 'cross': cross}).endswith(
        'all are on other email domains or Unknown Email')
    # clear card keeps empty_state_source.text; attention prints without mitigations
    ctx = Ctx(BY_ID['s05'], rep, ident, 'clear', False)
    assert s05.card({'empty_state_source': {'text': 'Source says none.'}}, ctx)['reason'] == 'Source says none.'
    alone = s05.mitigations({'attention_source': 'Attention: reset.'}, {'origin': 0, 'cross': cross | {'other_domain': [0, 0, 0]}})
    assert [f.getPlainText() for f in alone] == ['Attention: reset.']


def test_leak_review_fixes():                                            # code review 2026-10-19 (06 / D.3)
    from cyberrank_report.sections import s06_data_leak_history as s06
    rep = _demo()
    sec = rep['sections']['data_leak_history']
    ev = {e['event_id']: e for e in sec['events']}
    # resolved / unknown lead -> held; a merged-away record id resolves through canonical_event_id
    for state, code in (('resolved', 'lead_event_resolved'), ('unknown', 'lead_event_unconfirmed')):
        e = {**ev['leak-01'], 'validity_state': state}
        held = s06.adjust({**sec, 'events': [e]}, rep)
        assert (held['state'], held['reason_code']) == ('pending_review', code), held['state']
        assert s06._kind(e, e) == ('resolved' if state == 'resolved' else 'unknown')
    merged = [{**ev['leak-01'], 'canonical_event_id': 'c1'}, {**ev['leak-03'], 'canonical_event_id': 'c1'}]
    lead = s06._lead({'last_valid_event': {'event_id': 'leak-03'}}, s06.merge_events(merged))
    assert lead is not None and lead['event_id'] == 'leak-01'
    # events_reported matching neither count -> data_mismatch; unknown validity has its own status;
    # D.3 index says every distinct event is in Section 06
    sec['metrics'][1]['value'] = 7
    sec['events'][1]['validity_state'] = 'unknown'
    text, issues = _built_text(rep, ['s06', 'appD'])
    assert any(i['check'] == 'data_mismatch' and 'matches neither' in i['detail'] for i in issues), issues
    assert 'Validity not confirmed' in text and 'Not required — all 3 events shown in Section 06' in text
    assert 'no register data' not in text


def test_gap_quantum():
    text, issues = _gap('quantum_q1')
    assert 'No PQC detected' not in text and 'PQC not reported' in text                         # Q1
    assert 'main domain total (inferred)' in text and ('apex_inferred', 's11') in _checks(issues)  # Q4
    text, _ = _gap('quantum_q2')
    assert 'Not assessed' in text and 'switched off' in text                                    # Q2
    text, _ = _gap('quantum_q5')
    assert 'main domain only (1 scope)' in text and '1 scopes' not in text and 'No PQC detected' in text  # Q5


def test_quantum_review_fixes():                                       # code review 2026-10-19 (11)
    import gap_fixtures as G
    from cyberrank_report.sections import s11_quantum_security as s11
    sub = lambda i: f's{i}.example.com'
    # 1: apex rows count one by one -> 25 apex + 6 subdomain rows is T2, D.4 is produced
    r = G.quantum([G.qrow(i, G.DOMAIN, 1, 0) for i in range(25)] + [G.qrow(25 + i, sub(i % 2), 1, 0) for i in range(6)],
                  (25, 0))
    sec = r['sections']['quantum_security']
    assert s11.scope(sec, r)['tier'] == 'T2'
    # 2/4: T1, headline = rows by level: rows listed below (no D.4), uniform source printed once
    r = G.quantum([G.qrow(1, G.DOMAIN, 1, 0), G.qrow(2, sub(1), 0, 1)], (1, 1))
    text, _ = _payload_text(r, ['s11', 'appD'])
    assert 'every row is listed below' in text and 'Appendix D.4)' not in text, text
    assert 'Source: all rows “standard scan”.' in text and 'all 2 scope rows shown in Section 11' in text, text
    # 3/5/6/11: T2 without an apex row and without a source
    rows = [G.qrow(i, sub(i), 1, 0) for i in range(31)]
    for x in rows:
        x.pop('source')
    r = G.quantum(rows, (31, 0))
    sc = s11.scope(r['sections']['quantum_security'], r)
    assert sc['tier'] == 'T2' and sc['source_note'] is None
    assert not [f for f in s11.breakdown(r['sections']['quantum_security'], sc)
                if getattr(f, 'style', None) is not None and f.style.name == 'note' and not f.getPlainText().strip()]
    text, _ = _payload_text(r, ['s11', 'appD'])
    assert 'Same as main domain' not in text and 'all rows “None”' not in text and 'Source:' not in text, text
    assert 'The main domain total' not in text and 'main domain total, not added' not in text, text
    assert 'no main domain total row; the subdomain total matches the Section 11 headline' in text, text
    # 7/10: one risk-explained row with a missing count; 8: PQC detected without a scope register
    row = {**G.qrow(1, G.DOMAIN, 1, 0), 'moderate': None, 'moderate_reason_code': 'not_printed_in_source',
           'risk_level': 'low', 'risk_note_source': 'Covered by PQC.'}
    import pymupdf
    r = G.quantum([row], (1, 0))
    pdf, issues = _render(s11.risk_adjusted(s11.scope(r['sections']['quantum_security'], r)))
    assert not [i for i in issues if i['severity'] == 'error'], issues
    risk = ' '.join(' '.join(p.get_text() for p in pymupdf.open(pdf)).split())
    assert '1 scope row carries a risk explanation' in risk and 'Moderate not available' in risk, risk
    assert '1 row prints a Risk level' in risk and 'Moderate 0' not in risk, risk
    r = G.quantum([], (1, 0), pqc=[{'algorithm': 'ML-KEM', 'domains': [sub(1), sub(2)]}])
    text, _ = _payload_text(r, ['s11'])
    assert 'Detected on 2 domains.' in text and 'of 0 scopes' not in text and 'holds 0 scopes' not in text, text
    # 9: clear card: source empty-state text / coverage win; generated default is singular
    r = G.quantum([G.qrow(1, G.DOMAIN, 0, 0)], (0, 0))
    r['sections']['quantum_security']['state'] = 'clear'
    text, _ = _payload_text(r, ['s11'])
    assert 'endpoints on 1 scope ' in text + ' ' and '1 scopes' not in text, text
    r['sections']['quantum_security']['empty_state_source'] = {'text': 'Source empty text.', 'coverage': ['Src cov']}
    text, _ = _payload_text(r, ['s11'])
    assert 'Source empty text.' in text and 'Src cov' in text and 'TLS/SSL' not in text, text


def test_gap_new_conditions():                                          # 2026-10-15 samples (N1-N15)
    text, _ = _gap('overview_sector')
    assert 'Sector' in text and 'Telecommunications' in text and 'Industry' not in text           # N1
    assert 'Sector comparison' in text and 'Sector average' in text and 'Sector Average' not in text
    assert 'Telekomunikasi' not in text and 'Sedang' not in text                                  # source ids never printed
    assert 'Medium risk band' in text and 'Net score' not in text                                # N2
    text, _ = _gap('actions_remediation')
    assert '(Issue 9)' in text and 'Projected rating after remediation' in text                   # N3/N4
    assert 'Up 5 grades, from CC (Very insufficient) to A (Good); rating score from 24% to 78%.' in text and 'fresh scan' in text
    assert '360' not in text and '194' not in text and 'Recoverable' not in text     # hidden scoring
    text, _ = _gap('privacy_c')
    assert 'placeholder code “XX”' in text and 'Data Protection Officer (source: Company Website; LinkedIn)' in text
    assert 'compared with the preference set by the report owner/requestor' in text and 'your preference' not in text
    assert 'where you allow' not in text
    text, issues = _gap('vulns_c')
    assert 'Scanned assets' in text and 'Scanned: 1 domain and 5 subdomains.' in text             # N7
    assert 'Vulnerability scan results' in text and '5 reported, 2 listed' in text                # N8
    assert 'Informational' in text and ('data_mismatch', 's04') in _checks(issues)
    text, _ = _gap('vendors_profile')
    assert '5,200 employees' in text and 'revenue 2.2B (as printed)' in text and '573 technologies' in text
    text, _ = _gap('creds_status')
    assert 'Row status as recorded: Open 4, Resolved 2' in text                                   # N10
    text, _ = _gap('ai_missing')
    assert 'Not included in the source report' in text                                            # N11
    text, issues = _gap('quantum_q6')
    assert 'placeholder (“#”)' in text and 'Key exchange' in text and 'NTRU Prime' in text         # N12/N13
    assert 'Risk after PQC coverage' in text and 'Partial coverage' in text                       # N14
    assert 'Affected protocols' in text and 'NTRU Prime available' in text                        # N15
    assert 'source headline: the main domain total' in text and 'differs from the headline' in text  # Q6
    assert 'The subdomain rows sum to' in text


RAW = ("{'value'", "'reason_code'", "{'", 'None')


def test_null_forms_s02_s04_s06():                                     # extractor findings 2026-10-15
    text, _ = _gap('leaks_nulls')
    assert not [m for m in RAW if m in text], text
    assert 'Source not available (left blank in the assessment data)' in text and 'Entity not recorded' in text
    assert 'news.example.net/report-3' in text.replace(' ', '')
    text, _ = _gap('actions_nulls')
    assert not [m for m in RAW if m in text], text
    assert 'Why it matters' not in text and 'Projected rating' not in text and 'Review the retention clause.' in text
    from cyberrank_report.sections.s02_priority_actions import remediation_block
    assert remediation_block({}) == [] and remediation_block({'value': None, 'reason_code': 'x'}) == []
    assert remediation_block({'state': 'findings', 'current': {}, 'projected': {}, 'active_issues': {}}) == []
    text, _ = _gap('vulns_d')
    assert 'Scanned assets Not available (left blank in the assessment data).' in text
    assert 'Recommendations' in text and '(as reported)' not in text and 'Require SMTP authentication.' in text
    assert 'Informational' in text and 'Only informational findings were identified.' in text


def test_remediation_credentials_apart():
    text, _ = _gap('actions_remediation')
    assert '224 (13 privacy + 211 vulnerability)' in text
    assert 'Exposed credentials 40 (counted separately; not part of the active issues)' in text


def test_s02_card_state_cert_action_and_remediation_text():              # code review fixes, 2026-10-19
    from cyberrank_report.sections.s02_priority_actions import action_rows, remediation_block
    rep = json.loads((FIXTURE.parent / 'demo-preview.json').read_text(encoding='utf-8'))
    pa = rep['sections']['priority_actions']
    assert len(action_rows(pa, rep)) == 6                          # 5 payload + certificate review
    rep['sections']['certifications'].update(state='not_assessed', reason_code='module_not_assessed')
    assert len(action_rows(pa, rep)) == 5                          # no Next step in 13: no added action
    qa.ISSUES.clear()
    remediation_block({'current': {'grade': 'BB'}, 'active_issues': {'total': 5, 'privacy': 'two', 'vulnerability': 3}})
    assert not any(i['check'] == 'data_mismatch' and 'active issues' in i['detail'] for i in qa.ISSUES), qa.ISSUES  # text count

    def clear(r):
        r['sections']['certifications'].update(state='not_assessed', reason_code='module_not_assessed')
        r['sections']['priority_actions'] = {'title': 'Priority actions', 'state': 'clear', 'actions': [],
                                             'state_reason': 'Nothing needs action this quarter.'}
    t = _demo_text(clear, ['s02'])
    assert t.count('Nothing needs action this quarter') == 1, t
    t = _demo_text(lambda r: None, ['s02'])
    assert 'Projected Rating After Remediation' in t and 'Estimated improvement upon completion' in t, t


def test_projected_rating_steps():                                     # owner 2026-10-20: no points, staircase
    from cyberrank_report.sections.s02_priority_actions import GradeSteps, grade_walk, remediation_block
    assert grade_walk('BB', 'AA') == ['BB', 'BBB', 'A', 'AA'] and grade_walk('BB', 'BB') == ['BB']
    assert grade_walk('D', 'AAA') == T.GRADE_BAR
    assert grade_walk('AA', 'BB') is None and grade_walk(None, 'AA') is None and grade_walk('BB', 'X') is None
    assert GradeSteps(T.GRADE_BAR).wrap(T.CW, 999)[0] == T.CW                  # D -> AAA fits the width
    has = lambda out, cls: any(isinstance(f, cls) for k in out for f in getattr(k, '_content', [k]))
    qa.ISSUES.clear()
    ri = {'current': {'grade': 'AA', 'score': 300, 'pool': 360}, 'projected': {'grade': 'BB', 'score': 196, 'pool': 360},
          'points_recoverable': 50, 'narrative_source': 'Recover up to 50 points.', 'active_issues': {'total': 3}}
    out = remediation_block(ri)                                                # downward: no staircase, no table
    assert out and not has(out, GradeSteps) and 'Current rating' not in str(out)
    checks = [i['check'] for i in qa.ISSUES]
    assert checks.count('data_mismatch') == 2 and 'hidden_scoring_in_source' in checks, qa.ISSUES
    assert has(remediation_block({'current': {'grade': 'BB'}, 'projected': {'grade': 'BB'}}), GradeSteps)
    assert remediation_block({'current': {'grade': 'BB'}}) == []               # nothing drawable: no block


def test_vendor_technology_display_cap():
    text, _ = _gap('vendors_profile')
    assert '2,000+ more (source display limit)' in text and '2,005' not in text and '573 technologies' in text


def test_s07_resume_states_and_rows():                                  # fourth-party redesign, phase 0
    text, issues = _gap('vendors_self12')
    assert 'Identified' in text and 'Partial coverage' not in text and 'Findings' not in text   # owner: inventory
    assert ('Ratings are as shown on the report date. How each organisation is connected to Example Org is not '
            'reported.') not in text                                       # 2 dates missing: date clause stays
    assert "the date of each organisation's own assessment are not reported" in text
    assert 'Synthetic: 12 organisations.' in text                          # payload summary is never overwritten
    assert text.count('Same name as Example Org') >= 2                     # register row + Needs a look chip
    assert '(Amazon and Aws)' in text and 'not merged' in text            # alias note, no merge
    assert 'Assessed on' in text and '20 Sep 2026' in text                 # phase 1 ready
    assert 'BBB Satisfactory' in text and 'Not an assessed member (as reported)' in text   # rating not hidden
    assert 'Not rated' in text and '(reason not reported)' not in text and '(as reported)' not in text.split('Not an assessed')[0]
    assert 'A detected relationship is not evidence of a contract.' in text
    for word in (' direct', 'Direct', ' hop', 'supplier of', 'Not assessed yet'):
        assert word not in text, word
    text, _ = _gap('vendors_empty')
    assert 'None identified' in text and 'No connected organisations identified' in text
    assert 'No findings' not in text and 'Findings' not in text
    assert 'No fourth-party vendors were discovered.' in text and 'Automated technology discovery.' in text
    text, _ = _gap('vendors_nullreason')
    assert not [m for m in RAW if m in text], text
    assert 'Not rated (the organisation has not been scanned yet)' in text
    assert 'Not rated (reason' not in text and 'Not rated' in text


def test_s07_t2_register():
    import gap_fixtures as G
    import pymupdf
    from cyberrank_report.build import validate
    qa.ISSUES.clear()
    out = Path(tempfile.mkdtemp()) / 't2.pdf'
    total, counts = build(validate(G.vendors_t2()), out, only=['s14', 'appD'])
    assert counts['error'] == 0, json.loads(out.with_suffix('.qa.json').read_text())['issues']
    pages = [p.get_text() for p in pymupdf.open(out)]
    text = ' '.join(' '.join(pages).split())
    sec = ' '.join(' '.join(p for p in pages if 'Needs a look' in p).split())
    assert 'Needs a look' in sec and 'All connected organisations' not in text           # T2: no inline list
    assert 'D.6.1 Connected organisations · 35 organisations' in sec and 'Full register' in sec   # sender's unit
    assert 'Supply-chain aggregation' not in text            # no c_methodology.supply_chain: no pointer to it
    assert 'Not rated (outside the scope of the rating service)' in text
    assert 'End of register · 35 rows' in text and '33 rated + 2 not rated = 35' in text
    assert 'continued' in text and 'Rows ' in text and 'of 35' in text
    assert 'Grade of Example Org (for reference)' in text and 'BB' in text
    reg = ' '.join(' '.join(p for p in pages if 'D.6.1' in p and 'Needs a look' not in p).split())
    assert 'Very insufficient' not in reg and 'Critical' in reg              # register: plain grade, band as sent
    look = sec.split('Needs a look', 1)[1].split('Full register', 1)[0]
    assert 'Org' in look and 'Excellent' not in look and 'Good' not in look   # never the Low band


def test_s14_state_payload_text_and_cells():                            # code review fixes, 2026-10-19
    from cyberrank_report.sections import s14_fourth_party_vendors as s14
    rep = {'identity': {'organisation_name': 'Example Org', 'domain': 'example.com'}}
    v = [{'name': 'A', 'grade': 'BB'}]
    d = s14.adjust({'state': 'findings', 'summary': 'S.', 'state_reason': 'R.', 'vendors': v}, rep)
    assert (d['state'], d['summary'], d['state_reason']) == ('findings', 'S.', 'R.')     # shows 'Identified'
    assert s14.adjust({'state': 'partial', 'vendors': v}, rep)['state'] == 'partial'      # payload partial stands
    assert s14.adjust({'state': 'clear', 'vendors': v}, rep)['state'] == 'findings'
    e = s14.adjust({'state': 'clear', 'summary': 'None.', 'vendors': []}, rep)
    assert e['state'] == 'none_identified' and e['summary'] == 'None.'
    is_self = lambda dom: s14.is_self({'name': 'X', 'domain': dom}, rep)
    assert is_self('example.com') and is_self('www.example.com') and is_self('app.example.com')
    assert not is_self('example.org') and not is_self('notexample.com')
    assert s14.band_text({'grade': None, 'risk_band': 'high'}) == 'high'                  # as sent, even unrated
    assert s14.band_text({'grade': None}) == 'Not sent'
    assert s14.band_text({'grade': 'B', 'risk_band_label_source': 'medium HIGH'}) == 'medium HIGH'
    assert s14.not_rated({'grade': None, 'grade_reason': 'outside scope'}) == 'Not rated (outside scope)'
    assert s14.not_rated({'grade': None}) == 'Not rated' and s14.sector({'category': None}) == 'Unknown'
    assert s14.pointer(rep) == []                                   # no Appendix C supply-chain page


def test_appendices_frame_fixes():                                        # code review fixes, 2026-10-19
    """D without its appendix payload still prints the registers on a page of its own; backlink uses the
    payload title; C counts its steps and names a missing organisation 'this organisation'."""
    import gap_fixtures as G
    import pymupdf
    from cyberrank_report.build import validate
    r = G.vendors_t2()
    del r['appendices']['d_evidence_registers'], r['identity']['organisation_name']
    r['appendices']['c_methodology'] = {'title': 'Methodology', 'is_generic_material': True, 'steps_source': [
        {'n': i, 'title': f'Step {i}', 'text': 'Text.'} for i in (1, 2, 3)]}
    qa.ISSUES.clear()
    out = Path(tempfile.mkdtemp()) / 'frame.pdf'
    total, counts = build(validate(r), out, only=['s14', 'appC', 'appD'])
    assert counts['error'] == 0, json.loads(out.with_suffix('.qa.json').read_text())['issues']
    pages = [' '.join(p.get_text().split()) for p in pymupdf.open(out)]
    text = ' '.join(pages)
    assert 'End of register · 35 rows' in text and 'Section missing' not in text
    assert 'Back to Section 14 Fourth-party vendors (T2, 35 rows)' in text
    assert 'three steps, one pipeline' in text and 'not results for this organisation' in text.replace('- ', '')
    assert 'Grade of this organisation (for reference)' in text and 'Organisation name not available' in text
    c_page = next(i for i, p in enumerate(pages) if 'C · APPENDICES' in p)
    d_page = next(i for i, p in enumerate(pages) if 'D · APPENDICES' in p)
    assert d_page > c_page, (c_page, d_page)                        # D starts on a new page without the locked one


def test_app_d_t1_threshold():
    from cyberrank_report.sections import app_d_evidence_registers as D
    assert D._DEFAULTS['tiers']['T1_inline']['max_visual_rows'] == 30
    assert D.tier(30, 30) == 'T1' and D.tier(31, 31) == 'T2'
    orig = D.pol
    own = {'lists.x.tier_thresholds.T1_max_visual_rows': 5, 'lists.x.tier_thresholds.T2_max_rows': 8}
    D.pol = lambda path, default=None: own.get(path, orig(path, default))
    try:                                                            # a list's own thresholds win
        assert D.tier(6, 6, list_key='x') == 'T2' and D.tier(9, 9, list_key='x') == 'T3' and D.tier(6, 6) == 'T1'
    finally:
        D.pol = orig


def test_rating_scale_and_locked_page_inputs_fail_softly():
    from cyberrank_report import rating_scale as RS
    from cyberrank_report.sections import app_b_rating_scale as B, app_c_methodology as AC
    for rating, grade in (({'grade': {'value': 'bb'}}, 'BB'), ({'grade': ' aa '}, 'AA'),
                          ({'state': 'assessed'}, None), ({'state_reason': 42}, None), ({'grade': 'X'}, None)):
        got = B.rating({'rating': rating})
        assert got['grade'] == grade, (rating, got)
        RS.build_rating_scale(got, T.STYLES)                         # never raises
    assert B.rating({'rating': {'state_reason': 42}})['state_reason'] == B.NO_GRADE_REASON
    orig = AC.SUPPLY_CHAIN_INDEX
    try:
        for bad, why in (('x', 'whole number'), ('-1', 'whole number'), ('99999', 'outside')):
            AC.SUPPLY_CHAIN_INDEX = bad
            found, detail = AC.locked_source()
            assert found is None and (why in detail or 'not found' in detail), detail
    finally:
        AC.SUPPLY_CHAIN_INDEX = orig


def test_breach_label_normalisation():
    from cyberrank_report.sections.s05_credential_exposure import domain_class, field_class
    assert {field_class(x) for x in ('Passwords', 'pass', ' PASSWORD ', 'Historical passwords')} == {'password'}
    assert field_class('Email addresses') == field_class('Usernames') == 'other_identity'
    assert field_class('Dates of birth') == field_class('Password hints') == 'sensitive_personal'
    assert field_class('job.job_company') == 'other_identity' and field_class('origin') == 'service_recorded_only'
    assert field_class('Something new') == 'unclassified'
    for sub in ('mail', 'm', 'pop'):
        assert domain_class({'email_domain': f'{sub}.example.com'}, 'example.com') == 'assessed_subdomain'
    assert domain_class({'email_domain': 'notexample.com'}, 'example.com') == 'other_domain'


def test_null_forms_fixture_sweep():
    """Every scalar of every list item in s02/s04/s06 (gap fixtures) nulled in both documented forms:
    no crash, no raw dict / 'None' in the PDF."""
    import copy
    import gap_fixtures as G
    def nullify(o, form):
        if isinstance(o, list):
            for x in o:
                nullify(x, form)
        elif isinstance(o, dict):
            for k in list(o):
                v = o[k]
                if k in ('value', 'precision', 'unit', 'state', 'reason_code', 'event_id', 'action_id', 'rank') \
                        or k.endswith(('_state', '_reason_code')):
                    continue
                if isinstance(v, (dict, list)) and not (isinstance(v, dict) and 'value' in v):
                    nullify(v, form)
                elif isinstance(v, (str, int, float)) and not isinstance(v, bool) or isinstance(v, dict):
                    if form == 'nr':
                        o[k] = dict(G.NR)
                    else:
                        o[k], o[f'{k}_state'], o[f'{k}_reason_code'] = None, 'unavailable', 'not_printed_in_source'
    for vid, key, lists in (('leaks', 'data_leak_history', ('events',)),
                            ('actions_remediation', 'priority_actions', ('actions',)),
                            ('vulns_c', 'vulnerabilities', ('findings', 'active_scan'))):
        for form in ('nr', 'sib'):
            make = dict((v, m) for v, _, _, m in G.VARIANTS)[vid]
            def mutated(make=make, key=key, lists=lists, form=form):
                r = make()
                for k in lists:
                    nullify(r['sections'][key][k], form)
                return r
            name = f'{vid}_{form}'
            G.VARIANTS.append((name, ['null sweep'], dict((v, s) for v, _, s, _ in G.VARIANTS)[vid], mutated))
            G.UNVALIDATED.add(name)
            text, _ = _gap(name)
            assert not [m for m in RAW if m in text], (name, [text[max(0, text.find(m) - 80):text.find(m) + 40]
                                                            for m in RAW if m in text])


def test_cloud_scan_date_only():                                        # business answer 8
    text, _ = _gap('cloud_old_scan')
    assert '5 Jan 2023' in text, text
    for word in ('stale', 'Stale', 'older than', 'out of date', 'outdated'):
        assert word not in text, word


def test_cloud_clear_card_reason_payload_first():                       # code review fix, 2026-10-19
    from types import SimpleNamespace

    from cyberrank_report.sections import s15_cloud_infrastructure as s15
    ctx = SimpleNamespace(state='clear', c=C, identity={'assessment_date': '02 Oct 2026'})
    assert s15.card({}, ctx)['reason'] == s15.CLEAR_REASON
    for data in ({'reason_code': 'no_cloud_records'}, {'empty_state_source': {'text': 'Nothing seen.'}}):
        assert 'reason' not in s15.card(data, ctx), data              # the shared default_card reason stands


def test_mock_fixture():
    """Mock Cyberrank fixture (production PDF 13 Oct 2026): validates, matches the source counts."""
    from cyberrank_report.build import validate
    r = validate(json.loads((FIXTURE.parent / 'mock-cyberrank-2026-10-13.json').read_text(encoding='utf-8')))
    S = r['sections']
    assert r['rating']['grade'] == 'BB' and r['rating']['net']['value'] == 201
    assert r['identity']['sector'] == 'Manufacturing' and r['identity']['sector_source_id'] == 'Manufaktur'
    assert len(S['priority_actions']['actions']) == 8 and len(S['privacy']['policy']['issues']) == 7
    assert len(S['vulnerabilities']['findings']) == 12 and len(S['fourth_party_vendors']['vendors']) == 3
    assert [m['value'] for m in S['quantum_security']['metrics'][:3]] == [8, 1, 37]
    assert len(r['appendices']['d_evidence_registers']['quantum_scope_register']['rows']) == 46
    assert S['ai_risk_governance']['state'] == 'unavailable' and '@' not in json.dumps(r)


def test_quantum_toggle_conflict():                                     # business answer 7
    import gap_fixtures as G
    from cyberrank_report.build import InputError, validate
    try:
        validate(G.quantum_q2_conflict())
    except InputError as e:
        assert 'PQC scan is recorded as off' in str(e) and 'quantum results' in str(e), str(e)
    else:
        raise AssertionError('pqc_scan false + results accepted')
    validate(G.quantum_q2())                                                 # off without results is fine


def test_sector_alias():
    from cyberrank_report.build import validate
    r = validate({'identity': {'organisation_name': 'Example Org', 'industry': 'Manufaktur'},
                  'sections': {'executive_overview': {'state': 'findings', 'industry_comparison': {
                      'industry': 'Manufaktur', 'metrics': [{'id': 'industry_average', 'value': 1, 'unit': 'points'}]}}}})
    assert r['identity'] == {'organisation_name': 'Example Org', 'sector': 'Manufaktur'}
    sc = r['sections']['executive_overview']['sector_comparison']
    assert sc['sector'] == 'Manufaktur' and sc['metrics'][0]['id'] == 'sector_average'


def test_date_validation():                                                                      # D11
    from cyberrank_report.build import date_error
    assert date_error({'value': '2026-10-02', 'precision': 'day'}) is None
    assert date_error({'value': '2024', 'precision': 'year'}) is None
    assert 'partial date' in date_error({'value': '2024-05'})
    assert 'not an ISO 8601' in date_error('02.10.2026')
    assert 'not a calendar date' in date_error('2026-02-30')
    assert 'too short' in date_error({'value': '2024', 'precision': 'day'})



# --- comparison fixes (comparison/Instagram.md, Gmail.md, Mock_Cyberrank.md, 2026-10-15) ----------------
_FIX_TEXT = {}


def _fixture_text(name, only=None):
    """Flattened text of a fixture built through the CLI path (validate + build), cached per (name, only)."""
    key = (name, tuple(only or ()))
    if key not in _FIX_TEXT:
        import pymupdf
        from cyberrank_report.build import validate
        r = validate(json.loads((FIXTURE.parent / f'{name}.json').read_text(encoding='utf-8')))
        qa.ISSUES.clear()
        out = Path(tempfile.mkdtemp()) / f'{name}.pdf'
        build(r, out, only=only)
        _FIX_TEXT[key] = ' '.join(' '.join(p.get_text() for p in pymupdf.open(out)).split())
    return _FIX_TEXT[key]


def _overview(text):
    a = text.index('Rating overview Aspect')
    return text[a:text.index('Sector comparison', a)]


def test_s01_rating_overview_concept_a():                         # user-approved Concept A, 2026-10-19
    t = _fixture_text('gmail-2026-10-15', ['s01'])
    ov = _overview(t)
    for s in ('Rating overview Aspect scores 100% = best Privacy 56%', 'Certifications 0%',
              'All aspects Privacy 13 active privacy issues Findings',
              'Vulnerabilities 15 finding types · 1 High, 6 Medium, 8 Low Findings',      # zero tiers omitted
              'Credential exposure 5,395 exposed account records',                    # register rows listed
              'Data sovereignty Cannot be compared', 'Data residency 1 of 1 hosting country outside the preference',
              'Legal terms & conditions 0 of 2 customer-protection clauses found',
              'AI risk and governance No result Unavailable', 'Quantum security 30 high-risk findings',
              'Certifications 0 certifications None identified',
              'Fourth-party vendors 0 connected organisations None identified', 'Cloud infrastructure 1 cloud provider'):
        assert s in ov, (s, ov)
    for w in ('Reading order', 'report order', 'own score', 'judged by', '0% 100%', '03 Privacy', '15 Cloud', 'demerit', 'ledger', 'point', 'weighting', 'credit', 'A–J', 'Source', '“'):   # never the ledger / quotes
        assert w.lower() not in ov.lower(), (w, ov)
    ov = _overview(_fixture_text('demo-preview', ['s01']))
    for s in ('13 finding types · 2 Critical, 2 High, 5 Medium, 4 Low', '3 events · 1 resolved', 'Matches the preference',
              '1 of 6 hosting countries outside the preference', '1 of 2 customer-protection clauses found',
              '3 certifications · 1 awaiting approval', '34 connected organisations · 5 need a look', '4 cloud providers'):
        assert s in ov, (s, ov)


def test_about_and_fourth_party_trimmed():                             # owner, 2026-10-19
    t = _fixture_text('demo-preview', ['appA'])
    assert 'Assessment ID' in t and 'Time zone' not in t and 'Methodology version' not in t
    assert 'Report generated on 02.10.2026' in t                          # a_about.closing_source
    t = _fixture_text('instagram-2026-10-02', ['s14', 'appD'])
    assert 'Sector (as reported)' not in t and 'Risk band (as sent)' not in t and 'Sector' in t
    assert 'reason not recorded' not in t and 'Not rated (reason not reported)' not in t


def test_s01_rating_panel_has_no_score_context():                   # owner removed it, 2026-10-19
    for f in ('demo-preview', 'gmail-2026-10-15'):                     # demo carries a score_context value
        t = _fixture_text(f, ['s01'])
        assert 'Score context' not in t and 'Methodology version' not in t and 'Net score' not in t and 'Point pool' not in t, f
        assert 'Sector comparison' in t and '360-point' not in t, f                 # sector note dropped too


def test_s01_rating_overview_grammar_and_missing_scores():
    from cyberrank_report.sections import adjust_report
    from cyberrank_report.sections.s01_executive_overview import NA, aspect_rows, result_markup
    report = adjust_report({
        'identity': {'organisation_name': 'Example Org', 'domain': 'example.com'},
        'snapshot': {'assessed_at': {'value': '2026-10-02'}},
        'sections': {
            'privacy': {'state': 'findings', 'policy': {'policy_state': 'excluded_no_policy', 'metrics': [
                {'id': 'privacy_score', 'value': 40, 'unit': 'percent'}, {'id': 'active_issues', 'value': 2}]}},
            'vulnerabilities': {'state': 'not_assessed', 'reason_code': 'module_not_assessed'},
            'data_leak_history': {'state': 'findings', 'metrics': [{'id': 'data_leak_score', 'value': 60, 'unit': 'percent'}],
                                  'events': [{'event_id': 'e1'}]},
            'data_sovereignty': {'state': 'findings', 'enabled': False, 'observed_jurisdiction': {'value': 'Singapore'},
                                 'allowed_set': []},
            'certifications': {'state': 'clear', 'certificates': []},
            'cloud_infrastructure': {'state': 'clear', 'providers': []}}})
    rows = {r[0].key: r for r in aspect_rows(report, [])}
    assert rows['privacy'][2] == NA and rows['privacy'][3] == ('', 'No privacy policy (excluded)', [])   # never 0%
    assert rows['vulnerabilities'][2] == NA and rows['vulnerabilities'][3] is None                       # 'No result'
    assert rows['data_leak_history'][2:4] == (60, ('1', 'event', []))                                    # singular
    assert rows['data_sovereignty'][3] == ('', 'Not compared: no preference set', [])
    assert rows['certifications'][2] == 0 and rows['certifications'][4] == 'none_identified'          # rule 2026-10-19
    assert rows['cloud_infrastructure'][3] == ('0', 'cloud providers', [])
    assert rows['ai_risk_governance'][2] is None and rows['ai_risk_governance'][4] == 'unavailable'     # never scored
    assert 'No result' in result_markup(None)
    # qualifier and the last two words never part; the qualifier wraps as one unit
    assert result_markup(('3', 'events', ['1 resolved'])).endswith('events&nbsp;· 1&nbsp;resolved')
    assert 'outside&nbsp;the preference' not in result_markup(('1 of 6', 'hosting countries outside the preference', []))
    assert 'the&nbsp;preference' in result_markup(('1 of 6', 'hosting countries outside the preference', []))


def _demo_text(edit, only):
    """Rendered text of demo-preview after edit(report) mutates a copy of it."""
    import copy
    import pymupdf
    rep = copy.deepcopy(json.loads((FIXTURE.parent / 'demo-preview.json').read_text(encoding='utf-8')))
    edit(rep)
    qa.ISSUES.clear()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / 'r.pdf'
        build(rep, out, only=only)
        return ' '.join(' '.join(p.get_text() for p in pymupdf.open(out)).split())


def test_s01_edge_values_and_pointer_counts_02_rows():                  # code review fixes, 2026-10-19
    from cyberrank_report.sections import adjust_report
    from cyberrank_report.sections.s01_executive_overview import aspect_rows
    report = adjust_report({'sections': {
        'privacy': {'state': 'clear'},
        'data_sovereignty': {'state': 'findings', 'enabled': True, 'allowed_set': ['Australia'], 'match_state': 'odd'},
        'vulnerabilities': {'state': 'findings', 'metrics': [{'id': 'vulnerability_score', 'value': -5, 'unit': 'percent'}]},
        'credential_exposure': {'state': 'findings', 'aspect_score': -5}}})
    rows = {r[0].key: r for r in aspect_rows(report, [])}
    assert rows['privacy'][3] == ('0', 'active privacy issues', [])          # clear reads 0, like the others
    assert rows['data_sovereignty'][3] == ('', 'Cannot be compared', [])     # unknown match_state: no KeyError
    assert rows['vulnerabilities'][2] == 0 and rows['credential_exposure'][2] == 0     # both paths clamp 0-100

    def edit(rep):
        rep['identity'].pop('description_source')
        rep['identity']['review_flags'] = ['RF-T1']
        rep['review_flags'] = [{'id': 'RF-T1', 'text': 'Organisation name differs between source pages.'}]
        rep['sections']['executive_overview']['scope_and_coverage']['coverage_percent'] = 87
        rep['sections']['priority_actions']['actions'].append(
            {'rank': 9, 'priority': 'critical', 'title_source': 'Rotate the signing keys',
             'action_required_source': 'Rotate them.', 'linked_sections': []})
    t = _demo_text(edit, ['s01', 's02'])
    assert 'Review flag RF-T1: Organisation name differs' in t and 'Organisation profile' not in t, t
    assert 'Coverage 87%' in t, t
    # 01 counts what 02 prints: 5 payload actions + the critical one + the added certificate action
    assert '7 actions (1 critical, 2 high, 2 medium, 2 low)' in t, t
    assert 'Critical priority' in t and 'Priority not rated' not in t and 'Rotate the signing keys' in t, t


def test_certifications_without_records_are_none_identified():   # business rule 2026-10-19
    from cyberrank_report.sections import BY_ID, adjusted
    qa.ISSUES.clear()
    out = adjusted(BY_ID['s13'], {'title': 'Certifications', 'state': 'clear', 'certificates': [],
                                  'metrics': [{'id': 'compliance_score', 'value': None, 'reason_code': 'x',
                                               'state': 'clear'}]}, {})
    assert out['state'] == 'none_identified', out
    assert [m['value'] for m in out['metrics'] if m['id'] == 'compliance_score'] == [0]
    assert not any('state' in m for m in out['metrics'])
    assert any(i['check'] == 'state_adjusted' and i['severity'] == 'info' for i in qa.ISSUES), qa.ISSUES
    kept = {'state': 'findings', 'certificates': [{'standard': 'SOC 2'}],
            'metrics': [{'id': 'compliance_score', 'value': 68, 'unit': 'percent'}]}
    assert adjusted(BY_ID['s13'], kept, {}) is kept                   # with records the system score stands
    t = _fixture_text('instagram-2026-10-02', ['s13'])
    assert 'None identified' in t and 'No certificates identified' in t and 'No findings' not in t, t


def test_privacy_policy_state_and_sovereignty_verdict():                              # items 2, 3
    for name, n in (('instagram-2026-10-02', 12), ('gmail-2026-10-15', 13), ('mock-cyberrank-2026-10-13', 7)):
        sec = json.loads((FIXTURE.parent / f'{name}.json').read_text(encoding='utf-8'))['sections']['privacy']
        assert sec['policy']['policy_state']['value'] == 'valid_assessed', name
        t = _fixture_text(name, ['s03'])
        assert 'Policy state' not in t and 'Valid policy, assessed' not in t and 'Policy source' in t, name
        t = _fixture_text(name, ['s07'])                     # sovereignty is its own section (item 15)
        assert 'Source verdict “does not match the jurisdictions your organisation accepts' in t, name
        assert 'Review note: the source prints a verdict' in t and 'Cannot be compared' in t, name


def test_credential_action_quotes_source():                                            # item 4
    t = _fixture_text('gmail-2026-10-15', ['s02'])
    assert 'Source: “Force password reset for 15879 affected accounts. Enable multi-factor' in t, t[:300]
    assert 'Note: Verify and reset the accounts behind 3,154 rows on gmail.com' in t
    assert 'Review flag RF-G04: Remediation counts 211 vulnerability findings' in t           # item 11


def test_credential_section_source_vs_payload_counts():                                # item 5
    t = _fixture_text('gmail-2026-10-15', ['s05'])
    assert 'Source metric' not in t                                          # no payload count labelled as source
    assert 'Payload count (prepared from the source rows; not printed by the source)' in t and '3,685' in t
    assert 'Rows with organisation email domain' not in t                   # subdomains counted apart: no false diff
    assert '2021 and before' in t and 'Earlier (' not in t and 'Exposure years as listed' not in t   # fixed buckets
    assert '3685' not in t and '15879 (' not in t                           # formatted numbers in the summary
    t = _fixture_text('instagram-2026-10-02', ['s05'])
    assert '19 dated 2025–2026; 13 with latest year 2015–2024; 109 with period “Unknown” only' in t


def test_no_unsourced_likelihood_sentence():                                           # item 7
    for name in ('instagram-2026-10-02', 'claude-2026-10-02'):
        assert 'AI-derived' not in _fixture_text(name, ['s04']), name


def test_short_rows_never_split_in_row():                                              # item 8
    from cyberrank_report.tables import compact_table
    long = ' '.join(['word'] * 120)
    t = compact_table(['A', 'B'], [['x', long], ['y', long]], widths=[60, T.CW - 60])
    t.wrap(T.CW, 2000)
    h1 = t._rowHeights[0] + t._rowHeights[1]
    assert t.split(T.CW, h1 + 20) and len(t.split(T.CW, h1 + 20)[0]._cellvalues) == 2   # splits between rows
    assert t.split(T.CW, h1 / 2 + 10) == []                                   # never inside the short row 1
    t = _fixture_text('gmail-2026-10-15', ['s06'])
    assert 'Rows 2–2 ' not in t and 'Source: “Last data leak has been reported on 18.08.2026.”' in t   # item 12


def test_control_source_lines_quoted():                                               # Mock item 6
    t = _fixture_text('mock-cyberrank-2026-10-13', ['s04'])
    assert 'Source: “DKIM: Not Enabled – supports email integrity and sender authenticity.”' in t
    assert 'Source: “HTTPS Redirect — Secure”' in t


def test_ai_narrative_printed_in_full():                                               # item 9
    assert 'That view is based on what is publicly visible on instagram.com.' in _fixture_text('instagram-2026-10-02',
                                                                                              ['s10'])


def test_quantum_headline_relation_and_full_scope_rows():                             # item 10
    t = _fixture_text('mock-cyberrank-2026-10-13', ['s11', 'appD'])
    assert 'They equal the number of scope × algorithm rows in the scope breakdown at each level (46 rows' in t
    assert 'The headline is not the main domain total row for cyberrank.site, which sums to High 7 · Moderate 0 · ' \
           'Low 32' in t
    assert 'the main domain total, as scored in the product' not in t and 'headline scope' not in t
    assert '13 findings in category · 2 domains' in t
    assert 'D.4.2 Scope × algorithm rows' in t and 'End of register · 46 scope × algorithm rows' in t and 'X2' not in t


def test_gmail_scan_time_and_source_labels():                                          # item 11
    from cyberrank_report.build import date_error
    assert C.fmt_date({'value': '2026-10-12T18:29', 'precision': 'minute'}) == '12 Oct 2026 18:29'
    assert date_error({'value': '2026-10-12T18:29', 'precision': 'minute'}) is None
    assert 'no time' in date_error({'value': '2026-10-12', 'precision': 'minute'})
    t = _fixture_text('gmail-2026-10-15', ['s04'])
    assert '12 Oct 2026 18:29' in t and 'Executive Summary' in t and 'Top Recommendations' in t
    assert 'Review flag RF-G04' in t


# --- credential register in Appendix D.2.4 (policy option B, 2026-10-15) ------------------------------------
def test_credential_register_d44_prints_labels_as_received():
    report = json.loads(FIXTURE.read_text(encoding='utf-8'))
    rows = report['appendices']['d_evidence_registers']['credential_register']['rows']
    assert len(rows) == 30 and all(r.get('account_label_masked') for r in rows)
    t = _fixture_text('claude-2026-10-02', ['s05', 'appD'])
    for r in rows:                                                   # every label, exactly as delivered
        assert r['account_label_masked'] in t, r['id']
    assert 'Full register D.2 Credential exposure' in t and '30 rows' in t      # one pointer, no repeat line
    assert 'D.2.4 Credential register' in t and 'End of register · 30 rows' in t
    assert 'Account (masked, as delivered) Approximate exposure period Exposed fields' in t
    assert 'Status' not in t.split('D.2.4 Credential register', 1)[1].split('End of register', 1)[0]  # no status
    assert ('End of register · 30 rows. 30 of 30 register rows shown; 0 not shown (none withheld). Totals: '
            'claude.com 29 + other email domains 0 + Unknown Email 1 = 30 rows = Section 05 overview total; '
            'source headline 40') in t
    assert not [i for i in qa.ISSUES if i['check'] == 'unmasked_account_label']


def test_credential_year_buckets_and_affected_domains():                 # owner, 2026-10-19
    from cyberrank_report.page import identity_from_report
    from cyberrank_report.sections import s05_credential_exposure as s05
    report = json.loads((FIXTURE.parent / 'gmail-2026-10-15.json').read_text(encoding='utf-8'))
    d = s05.derive(report['sections']['credential_exposure'], report, identity_from_report(report))
    b = s05.year_buckets(d)
    assert [x for x, _ in b] == ['2026', '2025', '2024', '2023', '2022', '2021 and before', 'Unknown'], b
    assert sum(n for _, n in b) == d['analysed']                       # exclusive buckets
    t = _fixture_text('gmail-2026-10-15', ['s05'])
    assert 'Affected domains' not in t                                 # no affected_domain in the rows: no table
    t = _fixture_text('demo-preview', ['s05', 'appD'])
    assert 'Affected domains Domain Rows With password Latest year example.com 19 4 2026 app.example.com 10' in t
    assert '2026 2025 2024 2023 2022 2021 and before Unknown' in t
    assert 'D.2.3 Rows by affected domain' in t and 'example.com 19 rows' in t       # register grouped by domain
    for w in ('Row-level detail', 'Credential score printed', 'unit not defined by source)', 'Not available'):
        assert w not in t.split('Recommended mitigation')[0], w


def test_credential_register_order_status_and_unmasked_warning():
    from cyberrank_report.sections import s05_credential_exposure as s05
    mk = lambda i, latest, period, label, status=None: {
        'id': f'c{i}', '_latest': latest, 'exposure_period_source': period, 'account_label_masked': label,
        'exposed_field_categories': ['email', 'password'], **({'status': status} if status else {})}
    rows = [mk(1, None, 'Unknown', 'u***@example.com', 'Open'), mk(2, 2019, '2019', 'plainuser@example.com', 'Open'),
            mk(3, 2026, '2026, Unknown', 'n**w@example.com', 'Closed'), mk(4, 2019, '2019', 'Unknown Email'),
            mk(5, None, None, 'x*@example.com')]
    assert [r['id'] for r in s05.register_order(rows)] == ['c3', 'c2', 'c4', 'c1', 'c5']
    tall = mk(6, 2010, '2010', 't***l@example.com')                  # Gmail cred-0261 lists 104 categories
    tall['exposed_field_categories'] = [f'category_{k:03d}' for k in range(400)]
    qa.ISSUES.clear()
    flow, n, flagged = s05.row_register({'rows': rows + [tall]})
    assert (n, flagged) == (6, 1)                                    # 'Unknown Email' is a source literal
    warn = [i for i in qa.ISSUES if i['check'] == 'unmasked_account_label']
    assert len(warn) == 1 and warn[0]['count'] == 1 and 'c2' in warn[0]['detail']
    assert 'plainuser' not in warn[0]['detail']                      # QA names rows, never the label
    out, issues = _render(flow)
    assert not [i for i in issues if i['severity'] == 'error'], issues   # the tall row continues overleaf
    import pymupdf
    text = ' '.join(' '.join(p.get_text() for p in pymupdf.open(out)).split())
    assert 'category_000' in text and 'category_399' in text and 'D.2.4 Credential register · continued' in text
    assert 'plainuser@example.com' in text                           # printed as received, not re-masked
    assert 'Status' in text and 'Not recorded' in text               # a row has a status: column printed
    assert text.index('n**w@example.com') < text.index('plainuser@example.com') < text.index('u***@example.com')


def test_credential_register_long_label_wraps_at_break_points():
    from cyberrank_report.text import tech_lines
    label = 'a' + '*' * 40 + 'z@very-long-subdomain.mail.example-provider.co.id'
    lines = tech_lines(label, 120, T.LIGHT, 7.8)
    assert ''.join(lines) == label and len(lines) > 1
    assert all(stringWidth(x, T.LIGHT, 7.8) <= 120 for x in lines)
    assert all(x[-1] in '@.-' for x in lines[:-1] if stringWidth(x, T.LIGHT, 7.8) < 115), lines


def test_horizontal_grade_bars_run_worst_to_best():
    from cyberrank_report import rating_scale as RS
    assert T.GRADE_BAR[0] == 'D' and T.GRADE_BAR[-1] == 'AAA' and RS.BAR_GRADES == T.GRADE_BAR
    assert RS.END_LABELS == ('Controls provide no assurance', 'All controls adequate, appropriate and effective')
    RS.register_fonts()
    out, _ = _render([RS.Spectrum(selected=RS.GRADES.index('BB'), pin_text='Your rating: BB')])
    import pymupdf
    page = pymupdf.open(out)[1]
    xs = {w[4]: w[0] for w in page.get_text('words') if w[4] in RS.GRADES}
    assert [g for g, _ in sorted(xs.items(), key=lambda kv: kv[1])] == T.GRADE_BAR, xs
    pin = next(w for w in page.get_text('words') if w[4] == 'BB' and w[1] < min(v[1] for v in page.get_text('words')
                                                                                 if v[4] == 'D'))
    assert abs((pin[0] + pin[2]) / 2 - (xs['BB'] + 4)) < 60                   # pin sits over the BB segment
    assert page.search_for('Controls provide no assurance')[0].x0 < page.search_for('All controls adequate')[0].x0


# --- section layout v15 (INTEGRATION_CHECKLIST item 15) ---------------------------------------
LAYOUT = [('s01', '01', 'Executive overview'), ('s02', '02', 'Priority actions'), ('s03', '03', 'Privacy'),
          ('s04', '04', 'Vulnerabilities'), ('s05', '05', 'Credential exposure'),
          ('s06', '06', 'Data breach and leak history'), ('s07', '07', 'Data sovereignty'),
          ('s08', '08', 'Data residency'), ('s09', '09', 'Legal terms & conditions'),
          ('s10', '10', 'AI risk and governance'), ('s11', '11', 'Quantum security'),
          ('s12', '12', 'Security resourcing'), ('s13', '13', 'Certifications'),
          ('s14', '14', 'Fourth-party vendors'), ('s15', '15', 'Cloud infrastructure')]
SUBAREA_MARKERS = ('Accepted jurisdictions', 'Governing law', 'Preferred countries', 'Hosts observed',
                   'Login / Payment Portal', 'Login / payment portal', 'role evidence', 'Against the preference',
                   'Terms and Conditions', 'Security and privacy resourcing')


def test_section_order_follows_ledger():
    from cyberrank_report.sections import DEMERIT_RULES, REGISTRY
    from cyberrank_report.sections.s01_executive_overview import spec_for
    assert [(s.id, s.number, s.title) for s in REGISTRY if s.source == 'sections'] == LAYOUT
    assert [s.number for s in REGISTRY if s.source == 'appendices'] == ['A', 'B', 'C', 'D']
    # ledger A-J -> sections 03..12 (A vulnerabilities 04 and B privacy 03 swap, as in the ledger)
    assert [spec_for(DEMERIT_RULES[r]).number for r in 'ABCDEFGHIJ'] == \
        ['04', '03', '05', '06', '07', '08', '09', '10', '11', '12']


def _layout_report(sid, state):
    """Minimal payload with one of the four new sections in `state` (data present where it can be)."""
    data = {
        's07': {'enabled': True, 'allowed_set': ['Australia'], 'observed_jurisdiction': {'value': 'Singapore'},
                'match_state': 'mismatch', 'verdict_source': 'does not match', 'narrative_source': 'Source narrative.'},
        's08': {'enabled': True, 'allowed_set': ['Australia'], 'match_state': 'mismatch',
                'observed_hosting': [{'country': 'Germany', 'hosts': 3, 'evidence_kind': {'value': 'IP geolocation'}}]},
        's09': {'portal_detected': True, 'rows': [{'label': 'Login / Payment Portal', 'value_source': 'Detected'},
                                                  {'label': 'Protects customer data', 'value_source': '# Yes'},
                                                  {'label': 'Notifies on breach', 'value_source': '# No'}]},
        's12': {'privacy_role_evidence': 'detected', 'security_role_evidence': 'not_detected',
                'neutral_message': 'A privacy role was found; this does not show whether security staff exist.'},
    }[sid]
    from cyberrank_report.sections import BY_ID
    sec = {**data, 'state': state}
    if state in ('not_assessed', 'not_applicable', 'unavailable', 'partial', 'pending_review'):
        sec['reason_code'] = 'not_printed_in_source'
    return {'identity': {'organisation_name': 'Example Org', 'domain': 'example.com'},
            'snapshot': {'assessed_at': {'value': '2026-10-02', 'precision': 'day'},
                         'generated_at': {'value': '2026-10-03', 'precision': 'day'}},
            'sections': {BY_ID[sid].key: sec}}


def test_new_sections_render_in_every_state():
    import pymupdf
    from cyberrank_report.build import validate
    from cyberrank_report.sections import BY_ID
    for sid in ('s07', 's08', 's09', 's12'):
        for st in T.STATES:
            qa.ISSUES.clear()
            out = Path(tempfile.mkdtemp()) / f'{sid}-{st}.pdf'
            total, counts = build(validate(_layout_report(sid, st)), out, only=[sid])
            text = ' '.join(' '.join(p.get_text() for p in pymupdf.open(out)).split())
            assert total and counts['error'] == 0, (sid, st, json.loads(out.with_suffix('.qa.json').read_text()))
            spec = BY_ID[sid]
            assert f'{spec.number} · ASSESSMENT DETAILS'.upper() in text.upper() and spec.title in text, (sid, st)
            assert T.STATE[T.shown_state(st, spec.key)]['label'] in text, (sid, st)
            if st in ('not_assessed', 'not_applicable', 'unavailable', 'clear', 'partial', 'pending_review'):
                assert C.CARD_TITLES[st] in text, (sid, st)                         # state card
            if st == 'findings':                                                    # body + verdict
                assert {'s07': 'Source verdict “does not match”', 's08': '3 hosts',
                        's09': 'One clause found; not counted against the rating.',
                        's12': 'Not detected in the sources checked'}[sid] in text, (sid, text[:600])


def test_security_resourcing_review_fixes():                           # code review 2026-10-19 (12)
    r = _layout_report('s12', 'findings')
    r['sections']['security_resourcing']['security_role_evidence'] = 'maybe'
    text, issues = _payload_text(r, ['s12'])
    assert 'Not recognised (“maybe”)' in text and ('unknown_term', 's12') in _checks(issues), (text, issues)
    r['sections']['security_resourcing']['enabled'] = False
    text, _ = _payload_text(r, ['s12'])
    text = text[text.index('12 · ASSESSMENT DETAILS'):]                     # the cover has its own reason line
    assert 'Not applicable' in text and 'switched off for this assessment' in text, text
    assert 'Reason not recorded' not in text, text


def test_s07_s10_review_fixes():                                       # code review 2026-10-19
    import gap_fixtures as GF
    from cyberrank_report.sections import s07_data_sovereignty as S7, s09_legal_terms as S9, _shared as SH
    text, issues = _gap('pref_edges_a')
    assert ' None' not in text and 'Accepted jurisdictions Australia' in text            # snapshot preference
    assert 'Cannot be compared No governing-law' in text                                  # unknown match word
    assert '4 hosts Hosts observed 1 country Countries identified' in text                # host_count alias, dedupe
    assert 'placeholder code “ZZ”) (not on the map)' in text and 'Reason not recorded' not in text
    assert 'Login / payment portal Not available (not provided' in text and 'Detected' not in text
    text, issues = _gap('pref_edges_b')
    s07, s08 = text[:text.index('08 · ')], text[text.index('08 · '):]
    assert 'Accepted jurisdictions No preference set' in s07 and 'Australia' not in s07   # enabled false
    assert 'Preferred countries No preference set' in s08 and 'New Zealand' not in s08
    assert 'Germany France · 3' in s08 and '· 0' not in s08 and '0 hosts' not in s08      # missing is not zero
    assert 'hosts with unknown location (count not available)' in s08
    assert 'Not available1' in s08 and 'Left blank in the assessment data' in s08         # sibling reason
    assert {i['detail'].split(':')[0] for i in issues if i['check'] == 'state_adjusted'} >= \
        {'Data sovereignty', 'Data residency'}
    text, issues = _gap('pref_edges_c')
    assert 'Not compared: no preference set.' in text and 'Governing law' not in text     # card only
    assert 'clause found' not in text and 'Customer portal terms Detected' in text       # portal unknown
    assert 'Login / payment portal Not available (not provided in the assessment data)' in text
    text, _ = _gap('pref_edges_d')
    assert text.count(GF.SOV_MATCH_TEXT) == 1                                             # reading = summary
    assert '2 signals AI signals observed' in text
    assert 'Findings' not in text[text.index('Areas an AI assessment rates'):]            # context: neutral
    # flowable level: no empty Note, no crash on a NullReason narrative, {value} word gets its icon
    sec = GF.pref_edges_d()['sections']['data_sovereignty']
    assert not [f for f in S7._body(sec) if getattr(getattr(f, 'style', None), 'name', '').startswith('note')]
    S7._body({**sec, 'narrative_source': {'value': None, 'reason_code': 'not_printed_in_source'}})
    assert SH.matched({'match_state': 'partial'}) == 'unknown'
    assert not isinstance(S9._tc_value({'value': 'Yes'}), (dict, str))
    assert S9._portal({'portal_detected': {'value': None, 'reason_code': 'x'}}, []) is None
    assert S9._portal({}, S9._raw({'rows': [{'label': 'Portal URL', 'value_source': 'Detected'}]})) is None


def test_privacy_holds_no_subarea_content_and_alias_lifts_old_shape():
    import gap_fixtures as G
    from cyberrank_report.build import validate
    for name in ('claude-2026-10-02', 'instagram-2026-10-02', 'gmail-2026-10-15', 'mock-cyberrank-2026-10-13'):
        t = _fixture_text(name, ['s03'])
        assert not [m for m in SUBAREA_MARKERS if m in t], (name, [m for m in SUBAREA_MARKERS if m in t])
        secs = json.loads((FIXTURE.parent / f'{name}.json').read_text(encoding='utf-8'))['sections']
        assert not set(secs['privacy']) & {'sovereignty', 'residency', 'terms_conditions', 'resourcing'}, name
        assert {'data_sovereignty', 'data_residency', 'legal_terms', 'security_resourcing'} <= set(secs), name
    old = G.privacy_a()                                           # old nested shape -> own sections at load
    r = validate(old)
    assert 'sovereignty' not in r['sections']['privacy'] and r['sections']['data_sovereignty']['enabled'] is False
    text, _ = _gap('privacy_a')
    priv = text.split('07 · ASSESSMENT DETAILS'.upper())[0]
    assert not [m for m in SUBAREA_MARKERS if m in priv], [m for m in SUBAREA_MARKERS if m in priv]


def test_cross_references_resolve_to_section_pages():
    """Every internal link that names a section ('07 Data sovereignty  p. 9', '05 Credential exposure,
    page 14', 'Section 05, p. 12') lands inside that section (its opener or an anchor in it), and the
    printed page equals the link target."""
    import re

    import pymupdf
    titles = {n: ti for _, n, ti in LAYOUT}
    for name in ('claude-2026-10-02', 'mock-cyberrank-2026-10-13'):
        doc, checked = pymupdf.open(_full_pdf(name)), set()
        openers = {}
        for i, pg in enumerate(doc):
            m = re.search(r'^(\d{2}) · ASSESSMENT DETAILS|^(\d{2}) · OVERVIEW AND PRIORITIES', pg.get_text(), re.M)
            if m:
                openers.setdefault(m.group(1) or m.group(2), i)
        assert [n for n in titles if n not in openers] == [], (name, openers)
        for i, pg in enumerate(doc):
            for ln in pg.get_links():
                if ln.get('kind') != pymupdf.LINK_GOTO:
                    continue
                txt = ' '.join(pg.get_textbox(ln['from']).split())
                in_s01 = openers['01'] <= i < openers['02']
                if in_s01 and txt in titles.values():        # rating overview: the aspect name links too
                    txt = next(n for n, ti in titles.items() if ti == txt) + ' ' + txt
                m = re.match(r'(?:Section )?(\d{2})\b', txt)
                if not m or m.group(1) not in titles or not (txt.startswith('Section') or titles[m.group(1)] in txt
                                                             or (in_s01 and txt == m.group(1))):
                    continue      # e.g. a bare page number in Contents (overview section numbers are checked)
                num = m.group(1)       # the opener, or an anchor inside that section (e.g. IP reputation)
                end = min([v for v in openers.values() if v > openers[num]] + [len(doc)])
                assert openers[num] <= ln['page'] < end, (name, i + 1, txt, ln['page'] + 1, openers[num] + 1)
                printed = re.search(r'(?:p\.|page)\s*(\d+)', txt)
                if printed:
                    assert int(printed.group(1)) == ln['page'] + 1, (name, i + 1, txt)
                checked.add(num)
        assert {'03', '05', '07', '08', '09', '12', '14'} <= checked, (name, sorted(checked))



_FULL = {}


def _full_pdf(name):
    """Full build of a fixture through validate(), cached per name."""
    if name not in _FULL:
        from cyberrank_report.build import validate
        qa.ISSUES.clear()
        out = Path(tempfile.mkdtemp()) / f'{name}.pdf'
        build(validate(json.loads((FIXTURE.parent / f'{name}.json').read_text(encoding='utf-8'))), out)
        _FULL[name] = out
    return _FULL[name]


SPLIT_KEYS = ('data_sovereignty', 'data_residency', 'legal_terms', 'security_resourcing')


def test_section_summaries_split_from_privacy():                    # user decision 2026-10-15, option b
    import re
    for name in ('claude-2026-10-02', 'instagram-2026-10-02', 'gmail-2026-10-15', 'mock-cyberrank-2026-10-13'):
        secs = json.loads((FIXTURE.parent / f'{name}.json').read_text(encoding='utf-8'))['sections']
        priv = secs['privacy']['summary']
        assert len(re.findall(r'[.!?](?:\s|$)', priv)) == 1, (name, priv)      # the policy sentence only
        assert not re.search(r'[Gg]overning law|hosting|portal|Officer|role evidence', priv), (name, priv)
        flat = lambda x: re.sub(r'[-\u00ad\s]', '', x)                       # line-end hyphenation
        t = flat(_fixture_text(name, ['s03', 's07', 's08', 's09', 's12']))
        for key in ('privacy', *SPLIT_KEYS):
            summ = secs[key].get('summary')
            assert summ, (name, key)                                       # system-provided, every section
            assert flat(summ) in t, (name, key)                             # printed under the opener
    from cyberrank_report import sections as S                             # generated verdict = fallback only
    spec = S.BY_ID['s12']
    data = {'state': 'findings', 'privacy_role_evidence': 'detected', 'neutral_message': 'Generated reading.'}
    mod = S.load(spec)
    assert mod.verdict(data, None) == 'Generated reading.'


def test_appendix_d_ids_follow_section_order():                       # user decision 2026-10-15
    import re

    import pymupdf
    from cyberrank_report.sections import BY_ID
    from cyberrank_report.sections.app_d_evidence_registers import RID
    assert RID == {'s04': 'D.1', 's05': 'D.2', 's06': 'D.3', 's11': 'D.4', 's13': 'D.5', 's14': 'D.6'}
    assert [RID[s] for s in sorted(RID, key=lambda s: int(BY_ID[s].number))] == sorted(RID.values())
    doc = pymupdf.open(_full_pdf('claude-2026-10-02'))
    text = '\n'.join(p.get_text() for p in doc)
    index = text.split('Register index', 1)[1].split('Registers that are not required', 1)[0]
    ids = re.findall(r'^(D\.\d(?:\.\d)?)$', index, re.M)
    assert ids == ['D.1', 'D.1.2', 'D.2', 'D.3', 'D.4', 'D.5', 'D.6'], ids
    marks = [t.split()[0] for _, t, _ in doc.get_toc() if re.match(r'D\.\d', t)]
    assert marks == sorted(marks) and marks[0] == 'D.2', marks   # D.1 (28 rows <= 30): index row only
    assert 'D.2.4 lists every register row' in ' '.join(text.split())
    assert not re.search(r'D\.4\.4|D\.5\.[12]', text)                  # old ids gone


def test_every_numbered_section_starts_on_a_new_page():               # user decision 2026-10-15
    import re

    import pymupdf
    from cyberrank_report.sections import REGISTRY
    assert all(s.new_page for s in REGISTRY), [s.id for s in REGISTRY if not s.new_page]
    for name in ('claude-2026-10-02', 'mock-cyberrank-2026-10-13'):
        doc = pymupdf.open(_full_pdf(name))
        seen, tops = [], set()
        for pg in doc:
            heads = re.findall(r'^(\d{2}|[A-D]) · (?:ASSESSMENT DETAILS|OVERVIEW AND PRIORITIES|APPENDICES AND '
                               r'REFERENCES)$', pg.get_text(), re.M)
            assert len(heads) <= 1, (name, pg.number + 1, heads)               # never two sections on a page
            if heads:
                r = pg.search_for(f'{heads[0]} · ')
                tops.add(round(r[0].y0))                                     # opener at the top of the frame
                seen.append(heads[0])
        assert seen == [f'{i:02d}' for i in range(1, 16)] + list('ABCD'), (name, seen)
        assert len(tops) == 1, (name, tops)



# --- vulnerability format, user approval 2026-10-15 (option B, mono tokens, glyph fallback) ----------------
def test_severity_icon_only_cells_keep_searchable_labels():
    import pymupdf
    from cyberrank_report import icons as I
    cells = [C.severity_icon(lv) for lv in ('critical', 'high', 'medium', 'low')]
    assert all(isinstance(c, I.SeverityIcon) for c in cells)
    assert isinstance(C.severity_icon(None), I.IconLabel)            # not rated keeps its visible label
    w = C.head_width('Severity')
    assert max(c.minWidth() for c in cells) + 2 * T.CELL_PAD_H < w < 60   # narrow column, header sets it
    t = C.compact_table(['Finding', 'Severity'], [[f'code_{i}', c] for i, c in enumerate(cells)], widths=[120, w])
    t.wrap(T.CW, 800)
    assert all(abs(h - 21) < 0.01 for h in t._rowHeights[1:]), t._rowHeights   # row height unchanged
    legend = C.severity_legend([('critical', 0), ('high', 2), ('medium', {'value': None}), ('low', 9)])
    quantum = C.severity_legend([('high', 30), ('moderate', 0), ('low', 104)], scale='quantum')   # Gmail D.4
    out, issues = _render([C.heading_legend(C.heading('Finding types by severity', 2), legend), t,
                           C.heading_legend(C.heading('Scope breakdown', 2), quantum)])
    pg = pymupdf.open(out)[1]
    words = pg.get_text('words')
    for code, lv in zip(range(4), ('Critical', 'High', 'Medium', 'Low')):
        row = [w for w in words if w[4] == f'code_{code}'][0]
        hit = [w for w in words if w[4] == lv and abs(w[1] - row[1]) < 3]
        assert hit, (lv, 'hidden label not on the row')
        assert hit[0][2] <= 120 + T.L + w + 1, 'hidden label squeezed inside the column'
    assert 'Not available' in pg.get_text()
    assert not [i for i in issues if i['check'] == 'word_split'], issues          # counts never break ('104')
    raw = b''.join(pg.read_contents() for pg in pymupdf.open(out))
    assert b'3 Tr' in raw                                            # text render mode 3 (invisible)
    assert not [i for i in issues if i['severity'] == 'error'], issues


def test_severity_legend_is_a_boxless_strip_on_the_heading_line():
    """Competitor-style legend: no box, no title, counts as real text, on the H2's line (right-aligned);
    vertical stack only when the one-line strip does not fit."""
    import pymupdf
    legend = C.severity_legend([('critical', 0), ('high', 2), ('medium', 3), ('low', 9)])
    quantum = C.severity_legend([('high', 30), ('moderate', 0), ('low', 104)], scale='quantum')
    squeezed = C.severity_legend([('critical', 0), ('high', 2), ('medium', 3), ('low', 9)])
    long_head = C.heading('A very long register heading that leaves no room for the one-line legend strip', 2)
    out, issues = _render([C.heading_legend(C.heading('Finding types by severity', 2), legend), C.P('Body.'),
                           C.heading_legend(C.heading('Scope breakdown', 2), quantum),
                           C.heading_legend(long_head, squeezed)])
    assert not legend.vertical and not quantum.vertical and squeezed.vertical
    assert legend.height == squeezed.LEAD and squeezed.height == 4 * squeezed.LEAD
    pg = pymupdf.open(out)[1]
    words = pg.get_text('words')
    text = pg.get_text()
    assert 'Findings by severity' not in text and 'Assets by highest severity' not in text   # no title
    head = [w for w in words if w[4] == 'Finding'][0]
    near = [d['rect'] for d in pg.get_drawings() if d['rect'].x0 > head[2] and
            d['rect'].y1 > head[1] - 8 and d['rect'].y0 < head[3] + 8]
    assert near and all(r.width < 12 and r.height < 12 for r in near), ('only sirens, no box/frame', near)
    for lab, num in (('Critical', '0'), ('High', '2'), ('Medium', '3'), ('Low', '9')):
        lw = [w for w in words if w[4] == lab and head[1] <= w[1] and w[3] <= head[3]]
        assert lw, (lab, 'not on the heading line')
        nw = [w for w in words if w[4] == num and head[1] <= w[1] and w[3] <= head[3] and w[0] > lw[0][2]]
        assert nw, (lab, num, 'count missing beside its label')
    assert abs(max(w[2] for w in words if head[1] <= w[1] and w[3] <= head[3]) - (T.L + T.CW)) < 1, 'right-aligned'
    for lab, num in (('High', '30'), ('Moderate', '0'), ('Low', '104')):
        assert lab in text and num in text
    assert not [i for i in issues if i['severity'] == 'error'], issues


def test_quantum_count_headers_are_sirens_with_hidden_words():
    import pymupdf
    from cyberrank_report import icons as I
    heads = [I.SeverityHead(k, 'quantum', T.STYLES['dense_head_num']) for k in ('high', 'moderate', 'low')]
    t = C.compact_table(['Scope', *heads], [['a.example.com', 1, 2, 3]], numeric_cols=(1, 2, 3), dense=True,
                        widths=[200, 40, 40, 40])
    out, _ = _render([t])
    text = pymupdf.open(out)[1].get_text()
    assert all(x in text for x in ('High', 'Moderate', 'Low'))
    assert heads[1].wrap(40, 100)[1] < 12                            # icon only: no word line under it


def test_tech_tokens_use_jetbrains_mono_at_09():
    import pymupdf
    from cyberrank_report.tables import _auto_widths
    from cyberrank_report.text import MonoParagraph
    for name, base in (('tech', 9.1), ('cell_tech', 8.6), ('dense_tech', 7.8)):
        st = T.STYLES[name]
        assert st.fontName == T.MONO == 'JetBrainsMono' and abs(st.fontSize - base * 0.9) < 0.01, name
    tt = C.tech('edge-mqtt.static.instagram.com', 'cell_tech')
    tt.wrap(400, 100)
    assert isinstance(tt._p, MonoParagraph)
    # content-based widths measure technical tokens in the mono face
    host = 'mail-relay.eu-west.example.com'
    w = _auto_widths(['Host', 'Note'], [[host, 'x']], False, T.CW)
    assert w[0] >= stringWidth(host, T.MONO, T.STYLES['cell_tech'].fontSize) + 2 * T.CELL_PAD_H - 0.01
    assert C.tech_lines(host, 60, T.MONO, 7.74)[0].endswith(('.', '-'))    # wrap rules unchanged
    out, _ = _render([C.compact_table(['Host', 'Count'], [[C.tech(host, 'cell_tech'), 1]], widths=[300, 60])])
    pg = pymupdf.open(out)[1]
    spans = [s for b in pg.get_text('dict')['blocks'] for l in b.get('lines', []) for s in l['spans']]
    h = [s for s in spans if host in s['text']][0]
    one = [s for s in spans if s['text'].strip() == '1'][0]
    assert 'JetBrainsMono' in h['font'] and abs(h['origin'][1] - one['origin'][1]) < 0.3   # baselines align


def test_glyph_fallback_math_symbols_cjk_and_missing_warning():
    import pymupdf
    from cyberrank_report import fonts as F
    F.prepare_cjk('小红书')
    m = F.fallback('Π s ∈ N ✓ ✗ 小红书 plain')
    assert '<font name="NotoSansMath">Π</font>' in m and '<font name="NotoSansMath">∈</font>' in m
    assert '<font name="NotoSansSymbols2">✗</font>' in m and '<font name="NotoSansSC">小红书</font>' in m
    assert F.fallback('plain ascii') == 'plain ascii' and F.fallback('a &amp; b<br/>c') == 'a &amp; b<br/>c'
    story = [C.P('R(N) = 1 − (1 − o_N) · Π_{s ∈ suppliers(N)} ✓ ✗'), C.P('Vendor 小红书 (Xiaohongshu)'),
             C.tech('小红书.example.com', 'cell_tech'),
             C.compact_table(['Vendor', 'Mark'], [['小红书', '✓']], widths=[200, 60])]
    qa.ISSUES.clear()
    story.append(C.P('Emoji 😀 here'))              # no font has it: QA warning, at markup time
    miss = [i for i in qa.ISSUES if i['check'] == 'missing_glyph']
    assert len(miss) == 1 and 'U+1F600' in miss[0]['detail'], miss
    out, issues = _render(story)
    doc = pymupdf.open(out)
    text = doc[1].get_text()
    assert text.count('小红书') == 3 and 'Π' in text and '∈' in text and '✓' in text and '✗' in text
    fonts = {f[3].split('+')[-1] for f in doc.get_page_fonts(1)}
    assert {'NotoSansMath-Regular', 'NotoSansSymbols2-Regular'} <= fonts and any('NotoSansSC' in f for f in fonts), fonts
    assert not [i for i in issues if i['check'] == 'missing_glyph'], issues
    assert out.stat().st_size < 400_000                    # CJK subset, not the 10 MB source font


def test_four_reports_vuln_format_checks():
    """Full fixtures: no missing glyph, mono embedded, hidden severity words on the s04 rows."""
    import re

    import pymupdf
    for name in ('claude-2026-10-02', 'mock-cyberrank-2026-10-13'):
        out = _full_pdf(name)
        issues = json.loads(out.with_suffix('.qa.json').read_text())['issues']
        assert not [i for i in issues if i['check'] == 'missing_glyph'], name
        doc = pymupdf.open(out)
        assert any('JetBrainsMono' in f[3] for p in doc for f in p.get_fonts()), name
        page = next(p for p in doc if 'Finding types by severity' in p.get_text())
        words = page.get_text('words')
        for w in [w for w in words if re.fullmatch(r'vuln-\d+', w[4])]:
            assert any(x[4] in ('Critical', 'High', 'Medium', 'Low') and abs(x[1] - w[1]) < 3 for x in words), w


# --- section 08 residency map (geo_map) ----------------------------------------------------------
def _vm(case):
    from cyberrank_report import geo_map as G
    from residency_check import CASES
    sec = next(c[2] for c in CASES if c[0] == case)
    return G.entries(sec['observed_hosting'], sec['allowed_set'], compare=sec['enabled'] is not False)


def test_residency_mode_selection():
    from cyberrank_report import geo_map as G
    from residency_check import CASES
    for key, _, _, mode in CASES:
        assert G.choose(_vm(key))['mode'] == mode, key
    pac = G.choose(_vm('pacific'))                      # US + JP + KR: only the Pacific-centred box fits A2
    assert pac['lon0'] and abs(pac['lon0']) > 90 and G.fit(pac['codes'])[2] - G.fit(pac['codes'])[0] > \
        G.A2_MAX_SPAN * G.WORLD_W
    eu = G.choose(_vm('europe'))
    assert eu['lon0'] == 0 and eu['vp'][2] - eu['vp'][0] >= G.WORLD_W / G.MAX_ZOOM - 1e-9
    one = G.fit(['SG'])                                 # one tiny country: never zoomed past MAX_ZOOM
    assert abs((one[2] - one[0]) - G.WORLD_W / G.MAX_ZOOM) < 1e-9
    multi = G.choose(_vm('multi12'))
    assert multi['insets'] == [['DE', 'IE', 'NL', 'GB', 'FR'], ['SG', 'ID']]   # Europe + SEA clusters, cap 2
    assert 'SG' in G.View(G.choose(_vm('sea3'))['vp'], 0, 0, 0, 500, G.A2_COLS).by


def test_residency_off_map_and_no_preference():
    from cyberrank_report import geo_map as G
    vm = _vm('multi12')
    assert sorted((e['why'], e['hosts']) for e in vm['offmap']) == [('placeholder', 1), ('unknown', 3),
                                                                   ('unresolved', 1)]
    assert 'Atlantis' not in G.relevant(vm) and any('Atlantis' in q for q in vm['qa'])
    assert G.resolve('XX') == ('placeholder', None) and G.resolve('Atlantis') == ('unknown', None)
    assert G.resolve('united states of america') == ('country', 'US') and G.resolve('fr') == ('country', 'FR')
    off = G.offmap_line(vm)
    assert '3 hosts with unknown location' in off and '“XX”' in off and 'unresolved' in off
    nop = _vm('nopref')
    assert not nop['compare'] and {e['kind'] for e in nop['hosted']} == {'hosting'} and not nop['pref']
    assert G.legend_items(nop) == ['hosting']
    vm = G.entries([{'country_code': 'ZZ', 'hosts': 2}, {'country': None, 'reason_code': 'location_unknown',
                                                       'hosts': None, 'hosts_reason_code': 'blank_in_source'}], [])
    assert G.offmap_line(vm) == ('Not placed on the map: 2 hosts with the placeholder code “ZZ”, hosts with '
                                 'unknown location (count not available).'), G.offmap_line(vm)


def test_residency_section_pages():
    import pymupdf
    from residency_check import CASES, build_case
    for key in ('multi12', 'nopref', 'sea2', 'single'):
        sec = next(c[2] for c in CASES if c[0] == key)
        out = Path(tempfile.mkdtemp()) / f'{key}.pdf'
        total, counts = build_case(sec, out)
        rep = json.loads(out.with_suffix('.qa.json').read_text())
        text = ' '.join(' '.join(p.get_text() for p in pymupdf.open(out)).split())
        assert counts['error'] == 0, rep['issues']
        assert 'IP geolocation shows where public systems are hosted, not where all customer data is stored.' in text
        if key == 'multi12':
            assert 'Not placed on the map' in text and 'Atlantis: country name not recognised' in text
            assert any(i['check'] == 'residency_country' and 'Atlantis' in i['detail'] for i in rep['issues'])
        if key == 'nopref':
            assert 'Hosting country (not compared)' in text and 'Not compared: no preference set' in text
        if key == 'single':                                 # mode C: one country -> table only
            assert 'World map' not in text and 'Map zoomed' not in text and 'United States of America (US)' in text
        if key == 'sea2':                                   # two countries now get the regional zoom
            assert 'Map zoomed' in text and 'Singapore (SG)' in text


def _map_page(key):
    import io

    from reportlab.pdfgen.canvas import Canvas

    from cyberrank_report import geo_map as G
    vm = _vm(key)
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=(T.PAGE_W, T.PAGE_H), pageCompression=1, invariant=1)
    y = T.PAGE_H - 60
    for f in G.map_flowables(vm, G.choose(vm)):
        _, h = f.wrap(T.CW, T.PAGE_H)
        f.drawOn(c, T.L, y - h)
        y -= h
    c.showPage()
    c.save()
    return buf.getvalue()


def test_residency_map_deterministic_and_small():
    for key in ('sea3', 'europe', 'pacific', 'multi12', 'nopref'):
        a, b = _map_page(key), _map_page(key)
        assert a == b, key                                   # same payload -> same bytes
        assert len(a) < 60_000, (key, len(a))


def test_residency_square_dash_renders_in_poppler():
    """0.01 pt dash + square cap (mismatch squares) must rasterise in pdftoppm (poppler drops zero dashes)."""
    import shutil
    import subprocess

    from reportlab.pdfgen.canvas import Canvas

    from cyberrank_report import geo_map as G
    if not shutil.which('pdftoppm'):
        return
    out = Path(tempfile.mkdtemp()) / 'dash.pdf'
    c = Canvas(str(out), pagesize=(40, 20))
    c.setLineCap(2)
    c.setLineWidth(3)
    c.setDash([G.SQUARE_DASH, 6 - G.SQUARE_DASH], 0)
    c.line(5, 10, 35, 10)
    c.save()
    pgm = subprocess.run(['pdftoppm', '-r', '144', '-gray', str(out)], capture_output=True, check=True).stdout
    pixels = pgm.split(b'\n', 3)[3]
    assert sum(1 for px in pixels if px < 128) >= 5 * 4, 'square dashes not rendered'


# --- severity column: right after the # / ID column, centred (user decision 2026-10-15) ----------
SEV_HEADS = ('Severity', 'Priority', 'Risk', 'Highest severity', 'Max severity')


def test_severity_column_second_and_centred():
    import pymupdf
    from reportlab.lib.enums import TA_CENTER

    from cyberrank_report import icons as I
    t = C.compact_table(['#', 'Severity', 'Finding'], [[1, C.severity_icon('high'), 'x'], [2, C.severity_icon('low'), 'y']])
    assert t._cellvalues[0][1].style.alignment == TA_CENTER
    assert all(r[1].alignment == 'CENTER' for r in t._cellStyles) and t._cellStyles[1][0].alignment != 'CENTER'
    C._TABLE_HEADS.clear()
    names = ('claude-2026-10-02', 'gmail-2026-10-15', 'instagram-2026-10-02', 'mock-cyberrank-2026-10-13')
    _FULL.clear()
    for name in names:
        _full_pdf(name)
    sev = [h for h in C._TABLE_HEADS.values() if any(x in SEV_HEADS for x in h)]
    assert len(sev) >= 8, sev
    for h in sev:
        j = next(i for i, x in enumerate(h) if x in SEV_HEADS)
        assert j == 1 and h[0] in ('#', 'ID'), h
    covered = {x for h in sev for x in h}
    assert {'Severity', 'Priority', 'Risk'} <= covered, covered    # D.1 'Highest severity': test_d1_registers_follow_the_long_list_rule
    # on the page: siren (its invisible word spans the icon) centred under its centred header
    for name in ('gmail-2026-10-15', 'instagram-2026-10-02'):
        doc = pymupdf.open(_full_pdf(name))
        checked = 0
        for page in doc:
            words = page.get_text('words')
            heads = sorted((w for w in words if w[4] == 'Severity'), key=lambda w: w[1])
            for k, head in enumerate(heads):
                below = heads[k + 1][1] if k + 1 < len(heads) else 1e9
                mid = (head[0] + head[2]) / 2
                for w in words:
                    if w[4] in ('Critical', 'High', 'Medium', 'Low') and head[3] < w[1] < below \
                            and head[0] <= (w[0] + w[2]) / 2 <= head[2]:
                        assert abs((w[0] + w[2]) / 2 - mid) < 1.0, (name, page.number + 1, mid, w)
                        checked += 1
        assert checked >= 15, (name, checked)
    assert I.SeverityIcon                       # icon-only cells keep their hidden word (checked above)


# --- semantic status colours (user decision 2026-10-15: restrained, colour only on the marker) -----------
STATUS_LABELS = {   # printed status label -> tone ('Findings' orange, 'Identified' navy); 'Valid' is ambiguous (DNS vs breach)
    **dict.fromkeys(('No findings', 'Resolved', 'Matches the preference', 'Enabled', 'Redirects to HTTPS',
                     'Approved', 'Approved by team', 'Approved automatically on upload'), 'good'),
    **dict.fromkeys(('Does not match the preference', 'Not enabled', 'Missing or invalid', 'Invalid', 'Weak',
                     'Rejected', 'Expired', 'Does not redirect to HTTPS'),
                    'bad'),
    **dict.fromkeys(('Pending review', 'Partial coverage', 'Unavailable', 'Awaiting approval', 'Cannot be compared',
                     'Enabled, monitoring only (p=none)', 'Not detected in the sources checked'), 'attention'),
    **dict.fromkeys(('Not assessed', 'Not applicable', 'None identified', 'Not compared: no preference set',
                     'Not recorded', 'Not reported', 'State not recorded', 'No PQC detected', 'PQC not reported'),
                    'neutral'),
    'Findings': 'attention', 'Identified': 'identified',
}


def _rgb(c):
    return '#%02X%02X%02X' % tuple(round(v * 255) for v in c)


def _status_markers(pdf):
    """(page, label, icon fill, text colour) for every known status label drawn with an icon to its left.
    The locked production page (no kit footer) is skipped: it is inserted unchanged."""
    import pymupdf
    out = []
    for page in pymupdf.open(pdf):
        if 'Page ' not in page.get_text() or 'Supply-chain aggregation' in page.get_text() and '2 / 2' in page.get_text():
            continue
        icons = [d for d in page.get_drawings() if d.get('fill') and d['rect'].width < 14 and d['rect'].height < 14]
        for b in page.get_text('dict')['blocks']:
            for line in b.get('lines', []):
                for sp in line['spans']:
                    t = sp['text'].strip()
                    hit = [lb for lb in STATUS_LABELS if t == lb or (len(t) >= 14 and lb.startswith(t))]   # wrapped first line
                    if not hit:
                        continue
                    x0, y0, _, y1 = sp['bbox']
                    near = [d for d in icons if 0 <= x0 - d['rect'].x1 <= 6 and d['rect'].y0 < y1 and d['rect'].y1 > y0]
                    if near:
                        d = near[-1]                     # hollow marker (white fill): its ring colour
                        ink = d['color'] if d['fill'] == (1.0, 1.0, 1.0) and d.get('color') else d['fill']
                        out.append((page.number + 1, max(hit, key=len), _rgb(ink), '#%06X' % sp['color']))
    return out


def test_status_colours_are_semantic_and_restrained():
    """Every status marker in the four reports uses its STATUS token (never navy / sapphire, except the
    'Identified' state); its label stays BODY; no text run anywhere is drawn in a status colour."""
    import pymupdf
    hexs = lambda c: '#%02X%02X%02X' % tuple(round(v * 255) for v in c.rgb())
    want = {**{k: hexs(c) for k, c in T.STATUS.items()}, 'identified': hexs(T.NAVY)}
    assert T.STATE['findings']['accent'] == T.STATUS['attention'] and T.STATE['identified']['accent'] == T.NAVY
    assert all(T.STATE[s]['accent'] == T.status_color(s) for s in T.STATES if s != 'findings')
    assert len({T.STATE[s]['bg'] for s in T.STATES}) == 1, 'no status-tinted card fills'
    structure = {hexs(T.NAVY), hexs(T.SAPPHIRE)}
    status_ink = {hexs(c) for c in T.STATUS.values()} - {hexs(T.MUTED)}
    for name in ('claude-2026-10-02', 'gmail-2026-10-15', 'instagram-2026-10-02', 'mock-cyberrank-2026-10-13'):
        pdf = _full_pdf(name)
        marks = _status_markers(pdf)
        assert len(marks) >= 15, (name, len(marks))
        wrong = [m for m in marks if m[2] != want[STATUS_LABELS[m[1]]]]
        assert not wrong, (name, wrong[:10])
        assert not [m for m in marks if m[2] in structure and STATUS_LABELS[m[1]] != 'identified'], name
        assert not [m for m in marks if m[3] != hexs(T.BODY)], (name, [m for m in marks if m[3] != hexs(T.BODY)][:5])
        for page in pymupdf.open(pdf):
            if 'Supply-chain aggregation' in page.get_text() and '2 / 2' in page.get_text():
                continue                                           # locked production page, unchanged
            spans = [sp for b in page.get_text('dict')['blocks'] for ln in b.get('lines', []) for sp in ln['spans']]
            inked = [sp['text'] for sp in spans if '#%06X' % sp['color'] in status_ink and sp['text'].strip()]
            assert not inked, (name, page.number + 1, inked[:5])
    # statuses the four reports do not carry (certificate approval / expiry, breach status, DMARC p=none,
    # no preference): the synthetic gap variants
    import gap_fixtures as G
    out = Path(tempfile.mkdtemp()) / 'status.pdf'
    G.render(out, only=['certs', 'leaks', 'vulns_a', 'privacy_a'])
    marks = _status_markers(out)
    seen = {m[1] for m in marks}
    for lb in ('Approved', 'Awaiting approval', 'Rejected', 'Expired', 'Resolved',
               'Enabled, monitoring only (p=none)', 'Not compared: no preference set'):
        assert lb in seen, (lb, sorted(seen))
    assert not [m for m in marks if m[2] != want[STATUS_LABELS[m[1]]] or m[3] != hexs(T.BODY)], marks



def test_certificate_detected_plus_uploaded_grouped_with_review_action():     # user request 2026-10-16
    import tempfile
    sys.path.insert(0, str(Path(__file__).parent))
    import gap_fixtures as G
    with tempfile.TemporaryDirectory() as tmp:
        _, counts, text, _ = G.render(Path(tmp) / 'c.pdf', only=['certs_mixed'])
    assert counts['error'] == 0, counts
    flat = ' '.join(text.split())
    assert flat.count('ISO/IEC 27001') >= 1 and 'Not detected by the system' in flat, flat
    assert 'System detected [1]' in flat and 'System detected [2]' in flat, flat
    assert 'Review system-detected certificates' in flat and 'Next step:' in flat, flat
    assert 'Added by this report from the certificate records' in flat, flat
    # the two ISO/IEC 27001 records sit together: the standard is printed once in the table
    table = flat[flat.index('Certificates on record'):flat.index('[1] https')]
    assert table.count('ISO/IEC 27001') == 1, table


def test_uploaded_certificate_documents_in_appendix_d5():                 # user decision 2026-10-16
    import pymupdf
    import gap_fixtures as G
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / 'c.pdf'
        _, counts, text, issues = G.render(out, only=['certs_uploaded'])
        doc = pymupdf.open(out)
        imgs = sum(len(p.get_images()) for p in doc)
    flat = ' '.join(text.split())
    assert counts['error'] == 0, counts
    assert 'Document in Appendix D.5' in flat and 'D.5 Uploaded certificate documents' in flat, flat
    assert 'D.5.1 Other (standard not named)' in flat and 'D.5.3 ISO27001' in flat, flat
    assert 'Not shown: D.5.2' in flat and '2 of 3 uploaded documents shown' in flat, flat
    assert imgs >= 2, imgs                                     # PNG + rendered PDF page
    assert any(i['check'] == 'missing_document' for i in issues), issues
    assert 'Approved' in flat and 'automatically' not in flat and 'Approved by team' not in flat


def test_backend_aspect_score_in_rating_overview():                       # owner decision 2026-10-19
    import copy
    import pymupdf
    rep = copy.deepcopy(json.loads((Path(__file__).resolve().parents[1] / 'data/demo-preview.json').read_text()))
    secs = rep['sections']
    secs['data_sovereignty']['aspect_score'] = {'value': 0, 'unit': 'percent'}
    secs['data_residency']['aspect_score'] = {'value': None, 'reason_code': 'no_preference_set'}
    secs['legal_terms']['aspect_score'] = {'value': 140, 'unit': 'percent'}          # capped at 100%
    secs['cloud_infrastructure'].pop('aspect_score', None)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / 'r.pdf'
        build(rep, out, only=['s01'])
        text = ' '.join(' '.join(p.get_text() for p in pymupdf.open(out)).split())
    block = text[text.index('Aspect scores'):text.index('All aspects')]
    assert 'Data sovereignty 0%' in block, block
    assert 'Data residency Not compared' in block, block
    assert 'Legal terms & conditions 100%' in block and '140%' not in block, block
    assert 'Cloud infrastructure' not in block, block
    assert 'demerit' not in text.lower() and 'cap ' not in text.lower(), text

if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
