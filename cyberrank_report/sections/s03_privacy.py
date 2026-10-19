"""03 Privacy (demerit rule B): KPI strip, policy (state, source, the 16 assessed criteria A-P,
active issues). Data sovereignty, data residency, legal terms & conditions and security resourcing
are their own sections (07, 08, 09, 12); privacy criterion H 'Data residency' here is policy text
about location / transfer, not the hosting comparison in section 08.

Policy-state rule (U1 Q04): valid_assessed -> score shown; claimed_missing ->
0% shown with its reason; excluded_no_policy -> no score printed (excluded, not
0%). Unknown policy state -> score shown as reported, held for review; a policy state
outside those three -> section pending_review (policy_state_unrecognised).

Synthetic state variants:  python -m cyberrank_report.sections.s03_privacy data.json -o out.pdf
"""
from reportlab.platypus import Table, TableStyle

from .. import components as C
from .. import qa
from .. import theme as T

AREAS = [('A', 'Individual rights'), ('B', 'Consent'), ('C', 'Changes to privacy policy'),
         ('D', 'Security of PII'), ('E', 'Third parties'), ('F', 'Collection of PII'), ('G', 'Disclosure'),
         ('H', 'Data residency'), ('I', 'Cookies'), ('J', 'Complexity and clarity'), ('K', 'Ways of contact'),
         ('L', 'Retention of PII'), ('M', 'PII of children'), ('N', 'Special categories of PII'),
         ('O', 'Automated decision-making and profiling'), ('P', 'Policy introduction')]
POLICY_STATE = {   # label, how the score reads
    'valid_assessed': ('Valid policy, assessed', None),
    'claimed_missing': ('Policy claimed but not found',
                        '0%: a privacy policy is referenced but could not be found or read, so it is scored 0% '
                        'and counts fully against the privacy rating.'),
    'excluded_no_policy': ('No privacy policy (excluded)',
                           'No score: the organisation states it has no privacy policy, so privacy is excluded '
                           'from the rating and the scoring pool is recalibrated. This is not a 0% score.'),
}
NO_RESULT = ('not_assessed', 'not_applicable', 'unavailable')


def _val(v):
    return v.get('value') if isinstance(v, dict) else v


def adjust(data, report):
    """A policy_state outside the three known values cannot be read: hold the section for review."""
    ps = _val((data.get('policy') or {}).get('policy_state'))
    if ps is None or ps in POLICY_STATE:
        return data
    from . import hold
    return hold(data, 'policy_state_unrecognised',
                f'The policy state “{ps}” is not one of the known states (valid and assessed, claimed but not found, '
                'no policy and excluded), so the privacy score cannot be read yet.')


# --- state card ---------------------------------------------------------------
def card(data, ctx):
    policy = data.get('policy') or {}
    if data.get('state') == 'pending_review' and _val(policy.get('policy_state')) is None:
        m = {x.get('id'): x for x in policy.get('metrics') or [] if isinstance(x, dict)}
        kw = {}
        if all(k in m and not C.is_missing(m[k]) for k in ('privacy_score', 'policies_found', 'active_issues')):
            kw['reason'] = (f'The assessment shows a {C.fmt_value(m["privacy_score"])} privacy score with '
                            f'{C.fmt_value(m["policies_found"])} found and '
                            f'{C.fmt_value(m["active_issues"]["value"], "active_issues")}, but it does not record '
                            'the policy state that decides how that score should be read.')
        return {**kw, 'next_step': [
            'If the policy is valid and was assessed, the reported score stands (1 to 100%).',
            'If a policy is claimed but cannot be found or read, 0% stands and counts against the rating.',
            'If the organisation states it has no privacy policy, privacy is excluded from the rating '
            'and no score is shown.']}
    return {}


# --- building blocks ----------------------------------------------------------
def _own_reason(sub):
    """Card reason the payload gives for a sub-object (None when it gives none)."""
    return (sub.get('state_reason') or (C.reason_text(sub) if sub.get('reason_code') else None)
            or sub.get('reason') or sub.get('narrative_source'))


def _meta(state, subtitle):
    """Module sub-line: state chip | subtitle; the subtitle lines up with key/value values."""
    t = Table([[C.state_chip(state, dense=True), C.P(subtitle or '', 'note_flush')]],
              colWidths=[T.KV_LABEL_W + T.CELL_PAD_H, T.CW - T.KV_LABEL_W - T.CELL_PAD_H], hAlign='LEFT',
              spaceAfter=6)
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                           ('RIGHTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 0),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (0, 0), 0.6)]))
    return t


def _module(title, sub, content, default_sub=None, why=None):
    """H2 + chip/subtitle + content. A missing or no-result sub-object becomes its state card.
    The card's reason comes from the payload (state_reason, reason_code, reason, narrative) or
    `why`; the kit fallback 'Reason not recorded' prints only when none of them exists."""
    if not sub:
        return C.keep(C.heading(title, 2), C.state_card('unavailable', 'Not provided in the assessment data.'))
    state = sub.get('state') or 'unavailable'
    if state in NO_RESULT:   # H2 + card (no chip row), same as a missing sub-object
        reason = _own_reason(sub) or why
        return C.keep(C.heading(title, 2),
                      C.state_card(state, reason, sub.get('what_checked'), next_step=sub.get('next_step')),
                      *content)
    subtitle = C.val(sub.get('subtitle_source')) or default_sub or ''
    head = [C.heading(title, 2), _meta(state, subtitle)]
    if state == 'pending_review' and sub.get('reason_code'):
        why = C.reason_text({'reason_code': sub['reason_code']})
        content = content + [C.note(C.sentence(why if why.lower().startswith('held for review')
                                               else 'held for review: ' + why))]
    return C.keep(*head, *content)


def _two_up(left, right):
    t = Table([[left, '', right]], colWidths=[T.COL2, T.GUTTER, T.COL2], hAlign='LEFT', spaceAfter=T.SP_SM)
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                           ('RIGHTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 0),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    return t


# --- policy -------------------------------------------------------------------
def _metrics(data):
    policy = data.get('policy') or {}
    ms = [m for m in policy.get('metrics') or data.get('metrics') or [] if isinstance(m, dict)]
    if _val(policy.get('policy_state')) == 'excluded_no_policy':
        ms = [{**m, 'value': None, 'state': 'not_applicable', 'reason': 'excluded from the rating'}
              if m.get('id') in ('privacy_score', 'active_issues') else m for m in ms]
    return ms


def _areas(areas):
    """16-area A-P matrix (two columns of 8). Scores print as n / max; missing prints its reason."""
    by_code = {str(a.get('code')).upper(): a for a in areas if isinstance(a, dict)}
    unknown = sorted(set(by_code) - {c for c, _ in AREAS})
    if unknown:      # not one of the 16 criteria: not placed in the matrix
        qa.add('unknown_term', 'warn', f's03: area codes outside A–P not shown: {", ".join(unknown)}', once=True)
    rows, missing = [], {}
    for code, name in AREAS:
        a = by_code.get(code) or {'score': None, 'score_reason_code': 'not_printed_in_source'}
        score = a.get('score')
        if score is None:      # short cell; the reason prints once, under the matrix
            why = C.reason_text({'reason_code': a.get('score_reason_code') or a.get('reason_code')})
            missing.setdefault(why, []).append(code)
            cell = C.P('Not available', 'cell_muted', alignment=2)
        else:
            top = a.get('max_score')
            if top is not None and not top > 0:      # printed as sent, never replaced by 10
                qa.add('data_mismatch', 'warn', f's03: area {code} max_score is {top}', once=True)
            cell = f'{C.fmt_number(score)} / {C.fmt_number(10 if top is None else top)}'
        rows.append([code, a.get('name') or name, cell])
    cols = ['', 'Area', 'Score']
    widths = [22, T.COL2 - 22 - 72, 72]
    out = [_two_up(C.compact_table(cols, rows[:8], widths, numeric_cols=(2,)),
                   C.compact_table(cols, rows[8:], widths, numeric_cols=(2,)))]
    if missing:
        out.append(C.note('; '.join(f'Not available for {", ".join(codes)}: {why}' for why, codes in missing.items())
                          + '.'))
    return out


def _policy(data, ctx):
    policy = data.get('policy')
    if policy is None:
        return [_module('Privacy policy', {}, [])]
    ps = policy.get('policy_state')
    label = POLICY_STATE.get(_val(ps), (None,))[0]
    if label is None and _val(ps) is not None:
        label = f'Not recognised (“{_val(ps)}”); held for review'
    areas = policy.get('areas')
    said = ps.get('source_label') if isinstance(ps, dict) and not C.is_missing(ps) else None
    if label and said:      # the source's own words for the state, quoted after our label
        pg = ps.get('source_page')
        label = f'{label} (source{f" p. {pg}" if pg else ""}: “{said}”)'
    pairs = [('Policy state', label or (ps if C.is_missing(ps) else str(_val(ps)))),
             ('Policy source', policy.get('policy_source') or {'value': None, 'reason_code': 'not_printed_in_source'})]
    if policy.get('policy_version') is not None:
        pairs.append(('Policy version', policy['policy_version']))
    if not isinstance(areas, list) and _val(ps) not in ('claimed_missing', 'excluded_no_policy'):
        pairs.append(('Per-area results (A–P)', areas or {'value': None, 'reason_code': 'not_printed_in_source'}))
    out = [_module('Privacy policy', policy, [C.key_value_list(pairs), *C.flag_notes(policy, ctx.report)],
                   'Published privacy policy: state, source, assessed areas and issues',
                   why=POLICY_STATE.get(_val(ps), (None, None))[1])]
    if isinstance(areas, list):
        out.append(C.keep(C.heading('Assessed areas (A–P)', 3), *_areas(areas)))
    issues = [i for i in policy.get('issues') or [] if isinstance(i, dict)]
    count = C.val(next((m.get('value') for m in _metrics(data) if m.get('id') == 'active_issues'), None))
    if issues:
        rows = [[i.get('label') or i.get('title') or C.missing_text(),
                 str(C.val(i.get('category')) or 'privacy').capitalize(),
                 i.get('text') or i.get('description') or {'value': None, 'reason_code': 'not_printed_in_source'}]
                for i in issues]
        out.append(C.keep(C.heading('Active issues', 3),
                          C.compact_table(['Issue', 'Type', 'What was found'], rows,
                                          widths=[170, 66, T.CW - 236])))
    elif count:
        out.append(C.note(f'{C.fmt_value(count, "issues")} reported; issue detail is not provided '
                          'in the assessment data.'))
    return out


# --- section ------------------------------------------------------------------
def build(data, ctx):
    out = []
    metrics = _metrics(data)
    if metrics:
        out.append(C.kpi_strip(metrics))
    out += C.flag_notes(data, ctx.report)
    policy = data.get('policy') or {}
    explain = POLICY_STATE.get(_val(policy.get('policy_state')), (None, None))[1]
    if explain and not (policy.get('state') in NO_RESULT and not _own_reason(policy)):   # else the card says it
        out.append(C.note(explain))
    out += _policy(data, ctx)
    return out


# --- synthetic state variants (design proof + self-check) ----------------------
def _variants(real):
    import copy
    base = copy.deepcopy(real)
    clean = {k: v for k, v in base.items() if k not in ('state_reason', 'reason_code')}
    findings = copy.deepcopy(clean)
    findings.update(state='findings', title='Privacy (synthetic: findings, valid policy)',
                    summary='The privacy policy was assessed at 62% with 3 active issues.')
    findings['policy'].update(
        state='findings', policy_state={'value': 'valid_assessed'},
        policy_source={'value': 'https://www.example.org/legal/privacy-policy?version=2026-06-16'},
        policy_version='Last updated 16 Jun 2026',
        metrics=[{'id': 'privacy_score', 'label': 'Privacy Score', 'value': 62, 'unit': 'percent', 'state': 'findings'},
                 {'id': 'active_issues', 'label': 'Active Issues', 'value': 3, 'unit': 'issues', 'state': 'findings'},
                 {'id': 'policies_found', 'label': 'Policies Found', 'value': 1, 'unit': 'policies',
                  'state': 'findings'}],
        areas=[{'code': c, 'score': (7 + i) % 11, 'max_score': 10} for i, (c, _) in enumerate(AREAS) if c != 'O']
        + [{'code': 'O', 'score': None, 'score_reason_code': 'not_printed_in_source'}],
        issues=[{'label': 'Retention period not stated', 'category': 'privacy',
                 'text': 'The policy does not say how long personal information is kept or how it is deleted.'},
                {'label': 'No breach notification commitment', 'category': 'security',
                 'text': 'No commitment to notify affected people after a security incident was found.'},
                {'label': 'Children\'s data', 'category': 'privacy',
                 'text': 'Age limits are stated, but handling of data collected from minors is not described.'}])

    claimed = copy.deepcopy(clean)
    claimed.update(state='findings', title='Privacy (synthetic: policy claimed but not found)',
                   summary='A privacy policy is referenced but could not be found, so privacy is scored 0%.')
    claimed['policy'].update(state='findings', policy_state={'value': 'claimed_missing'},
                             policy_source={'value': None, 'reason_code': 'not_identified'})
    for m in claimed['policy']['metrics']:
        m['state'] = 'findings'
        if m['id'] == 'policies_found':
            m['value'] = 0

    excluded = copy.deepcopy(claimed)
    excluded.update(title='Privacy (synthetic: no policy, excluded)',
                    summary='The organisation states it has no privacy policy, so privacy is excluded from the '
                            'rating.')
    excluded['policy'].update(state='not_applicable', policy_state={'value': 'excluded_no_policy'})

    clear = copy.deepcopy(findings)
    clear.update(state='clear', title='Privacy (synthetic: clear)',
                 summary='The privacy policy was assessed at 96% with no active issues.',
                 empty_state_source={'text': 'No active privacy issues were identified in the published policy.',
                                     'coverage': ['Published privacy policy, 16 assessed areas (A–P)',
                                                  'Active issues found in the policy text']})
    clear['policy'].update(state='clear', issues=[], areas={'value': None, 'reason_code': 'not_printed_in_source'})
    clear['policy']['metrics'] = [{**m, 'state': 'clear', 'value': {'privacy_score': 96, 'active_issues': 0}
                                   .get(m['id'], m['value'])} for m in findings['policy']['metrics']]

    partial = copy.deepcopy(findings)
    partial.update(state='partial', title='Privacy (synthetic: partial)',
                   state_reason='The per-criterion scores (A–P) did not complete for this assessment',
                   what_checked='Policy state, source, score and active issues are shown',
                   summary='The policy score and issues are available; the per-criterion scores are not.')
    partial['policy']['areas'] = {'value': None, 'reason_code': 'not_printed_in_source'}

    gone = {k: base[k] for k in ('number', 'intro_source')}
    return [('a', base),
            ('b', findings), ('c', claimed), ('d', excluded), ('e', clear), ('f', partial),
            ('g', {**gone, 'state': 'not_assessed', 'title': 'Privacy (synthetic: not assessed)',
                   'reason_code': 'module_not_assessed', 'summary': 'Privacy was not assessed for this report.',
                   'next_step': 'Enable the privacy module and re-run the assessment.'}),
            ('h', {**gone, 'state': 'unavailable', 'title': 'Privacy (synthetic: unavailable)',
                   'state_reason': 'Privacy results could not be retrieved for this assessment.',
                   'summary': 'Privacy results are unavailable for this assessment.'})]


def _demo(argv=None):
    import argparse
    import json
    from pathlib import Path

    from .. import qa
    from ..page import ReportDoc, cover_flowables, identity_from_report
    from . import BY_ID, SectionSpec, render_section

    ap = argparse.ArgumentParser(prog='python -m cyberrank_report.sections.s03_privacy')
    ap.add_argument('data', type=Path)
    ap.add_argument('-o', '--out', type=Path, required=True)
    a = ap.parse_args(argv)
    report = json.loads(a.data.read_text(encoding='utf-8'))
    identity = identity_from_report(report)
    base = BY_ID['s03']
    sections, story = {}, cover_flowables()
    for tag, data in _variants(report['sections']['privacy']):
        sections[f'privacy_{tag}'] = data
        spec = SectionSpec(f's03{tag}', f'privacy_{tag}', base.number, base.title, base.group, base.module)
        story += render_section(spec, {**report, 'sections': sections}, identity)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    doc = ReportDoc(a.out, identity, subject='Section 03 privacy: state variants (synthetic)')
    total = doc.render(story)
    issues = list(qa.ISSUES) + qa.check_pdf(a.out, table_parts=doc.table_parts, table_heads=C._TABLE_HEADS)
    counts = qa.write_report(a.out.with_suffix('.qa.json'), a.out, issues, pages=total)
    text = ''.join(__import__('pymupdf').open(a.out)[i].get_text() for i in range(total))
    assert 'excluded from the rating' in text and 'Not available' in text, 'state copy missing'
    print(f'{a.out}: {total} pages; QA {counts}')
    return 2 if counts['error'] else 0


if __name__ == '__main__':
    raise SystemExit(_demo())
