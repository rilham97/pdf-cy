"""Component sheet: every component and state card on real interior pages.

python -m cyberrank_report.component_sheet data.json -o output/Component_Sheet.pdf [--locked ext.pdf]
Reads only identity/snapshot from the payload; all other content is synthetic.
"""
import argparse
import json
import sys
from pathlib import Path

from reportlab.platypus import PageBreakIfNotEmpty, Table, TableStyle

from . import components as C
from . import qa
from . import theme as T
from .page import ReportDoc, cover_flowables, identity_from_report, locked_page
from .sections import SectionSpec, render_section

LONG_URL = 'https://support.claude.com/en/articles/10015870-what-certifications-has-anthropic-obtained-iso-27001'
HASH = 'sha256:6bfaaf3db89aa0714f3d4b4821c13ccfa3b3548324535fd81f4a22ceb7182f8d'
HOSTS = 'url6377.updates.claude.com, links.email.claude.com, pubmed.mcp.claude.com, hcls.mcp.claude.com'
PROSE = ('External signals are collected without access to internal systems, so every result describes what '
         'could be observed from the public internet at the time of the check. Counts are reported as observed; '
         'a missing value is shown with its reason and is never treated as zero. Interpretation follows the '
         'IISRI methodology: higher grades mean lower weakness values and therefore lower likelihood.')


def sheet_opener(n, title, intro, state=None, verdict=None):
    return [PageBreakIfNotEmpty()] + C.section_opener(n, title, state, verdict, intro, key=f'cs-{n}',
                                                       group='Component sheet')


def chip_grid(chips, per_row=5):
    rows = [chips[i:i + per_row] + [''] * (per_row - len(chips[i:i + per_row])) for i in range(0, len(chips), per_row)]
    t = Table(rows, colWidths=[T.CW / per_row] * per_row, hAlign='LEFT')
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                           ('TOPPADDING', (0, 0), (-1, -1), 3),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
    return t


def two_up(left, right):
    t = Table([[left, '', right]], colWidths=[T.COL2, T.GUTTER, T.COL2], hAlign='LEFT')
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                           ('RIGHTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 0),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    return t


def typography():
    out = sheet_opener('01', 'Typography and text', 'Poppins Medium for structure, Poppins Light for reading. '
                       'Specimens below use the real paragraph styles from theme.STYLES.')
    out += [C.heading('H1 compact closing statement', 1, style='h1c', toc=False),
            C.heading('H2 section heading, 14/18', 2),
            C.P('Body Light 9.1/13. ' + PROSE),
            C.heading('H3 module heading, 11/14', 3),
            C.P('Intro Light 10.5/14.5 is used once, under the section title.', 'intro'),
            C.heading('H3 compact, 10.5/14', 3, style='h3c'),
            *C.bullets(['Bullets use the body style with an 11 pt hanging indent.',
                        'Prose hyphenates with pyphen (en_US); headings never hyphenate.']),
            C.note('Note / caption Light 7.8/11.25, muted. Used for sources, scope and limits.'),
            C.heading('Technical tokens', 2),
            C.P('tech() wraps only after / . - _ @ and never adds a hyphen or drops characters. '
                'Below: one 164.97 pt column (3-column grid) per token.')]
    cols = [[C.P(lbl, 'card_label', spaceBefore=0), C.tech(v, 'cell_tech')] for lbl, v in
            [('URL', LONG_URL), ('Hash', HASH), ('Host list', HOSTS)]]
    t = Table([cols], colWidths=[T.COL3 + T.GUTTER] * 2 + [T.COL3], hAlign='LEFT')
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                           ('RIGHTPADDING', (0, 0), (0, -1), T.GUTTER), ('RIGHTPADDING', (1, 0), (1, -1), T.GUTTER),
                           ('RIGHTPADDING', (2, 0), (2, -1), 0), ('LINEABOVE', (0, 0), (-1, 0), 0.75, T.RULE),
                           ('TOPPADDING', (0, 0), (-1, -1), 6)]))
    return out + [t]


def kpis_and_chips():
    out = sheet_opener('02', 'KPI strip and chips', 'kpi_strip() takes payload metric records as they are. '
                       'A null value prints Not available with its reason; it is never shown as 0.',
                       'findings', 'Example verdict row: the state chip on the left, the one-sentence '
                       'verdict on the right. Every section opener ends with this row.')
    out += [C.heading('KPI strip, four tiles', 2),
            C.kpi_strip([
                {'label': 'Vulnerability score', 'value': 43, 'unit': 'percent', 'state': 'findings'},
                {'label': 'Finding types', 'value': 17, 'unit': 'finding_types', 'state': 'findings'},
                {'label': 'Critical/High finding types', 'value': 0, 'unit': 'finding_types', 'state': 'clear'},
                {'label': 'Eligible targets', 'value': None, 'reason_code': 'denominator_unavailable',
                 'state': 'unavailable'}]),
            C.heading('KPI strip, three tiles', 2),
            C.kpi_strip([
                {'label': 'AI issues', 'value': None, 'unit': 'issues', 'state': 'not_assessed',
                 'reason_code': 'module_not_assessed'},
                {'label': 'Policies found', 'value': 1, 'unit': 'policies', 'state': 'pending_review'},
                {'label': 'Hosts observed', 'value': 29, 'unit': 'hosts', 'state': 'partial'}]),
            C.heading('Severity chips', 2),
            C.P('6 x 6 pt colour square plus text in body colour: no text on saturated fills.'),
            chip_grid([C.severity_chip(s) for s in ('critical', 'high', 'medium', 'low', None)]),
            C.heading('Grade chips', 2),
            chip_grid([C.grade_chip(g) for g in T.GRADE] + [C.grade_chip(None)])]
    return out


FINDINGS = [
    ['ipv4_in_header', 'medium', 22, {'value': 5, 'unit': 'percent'}],
    ['cipherlist_3DES_IDEA', 'medium', 2, {'value': 8, 'unit': 'percent'}],
    ['dkim_not_enabled', 'high', 1, {'value': None, 'reason_code': 'not_printed_in_source'}],
    ['dnssec_missing_or_invalid', 'low', 1, {'value': 3, 'unit': 'percent'}],
    ['tls_weak_key_exchange_ecdhe_rsa', 'critical', 1250, {'value': 31, 'unit': 'percent'}],
]


def tables():
    out = sheet_opener('03', 'Compact tables', 'compact_table(): Light 8.6/12 cells, Medium header on '
                       '#F3F6F9, 4.5/6 pt padding, 21 pt single-line rows, horizontal hairlines only, '
                       'numbers right-aligned, severity as siren only + one legend strip (words hidden as invisible text).')
    rows = [[i, C.severity_icon(s), f, n, b] for i, (f, s, n, b) in enumerate(FINDINGS, 1)]
    levels = [str(s).lower() for _, s, _, _ in FINDINGS]
    out += [C.heading_legend(C.heading('Data table, full width 515.9 pt', 2),
                             C.severity_legend([(k, levels.count(k)) for k in ('critical', 'high', 'medium', 'low')])),
            C.note('Legend on the heading line of the table it explains: no box, no title.'),
            C.compact_table(['#', 'Severity', 'Finding type', 'Affected assets', 'Breach likelihood'], rows,
                            numeric_cols=(0, 3, 4)),
            C.note('A null cell prints its reason (third row). Long identifiers wrap at technical break points.'),
            C.heading('Two short columns, 252.7 pt', 2),
            C.compact_table(['Jurisdiction', 'Hosts'], [['United States of America', 28],
                                                         ['Location unknown', 1]], numeric_cols=(1,)),
            C.heading('Dense register variant, 18 pt rows, header rule instead of fill', 2),
            C.compact_table(['#', 'Max severity', 'Asset', 'Finding ids', 'Findings'],
                            [[1, C.severity_icon('medium', True), 'claude.com / 160.79.104.10', 'vuln-01, vuln-02, vuln-09', 3],
                             [2, C.severity_icon('medium', True), 'support.claude.com', 'vuln-01, vuln-09', 2],
                             [3, C.severity_icon('low', True), HOSTS.split(', ')[2], 'vuln-01', 1]],
                            dense=True, numeric_cols=(0, 4), header_fill=False)]
    return out


def lists_and_pointers():
    out = sheet_opener('04', 'Key values, pointers and notes', 'key_value_list() for scalar facts, '
                       'register_pointer() to send readers to the full register in Appendix D.')
    out += [C.heading('Key / value list', 2),
            C.key_value_list([
                ('Primary domain', 'claude.com'),
                ('Assessment id', {'value': None, 'reason_code': 'not_printed_in_source'}),
                ('Coverage', {'value': None, 'reason_code': 'denominator_unavailable'}),
                ('Hosts observed for residency', {'value': 29, 'unit': 'hosts'}),
                ('Source document', HASH)]),
            C.heading('Two key / value lists side by side', 2),
            two_up(C.key_value_list([('Grade', C.grade_chip('BB')), ('Risk band', 'Low')], width=T.COL2),
                   C.key_value_list([('Sovereignty allowed', 'Australia'), ('Residency allowed', 'New Zealand')],
                                    width=T.COL2)),
            C.heading('Register pointer', 2),
            C.P('Resolved on the second multiBuild pass from register_anchor() flowables placed around the '
                'register (here: the long table in section 07).'),
            C.register_pointer('demo_asset_register', {'value': 60, 'unit': 'rows'}, title='Asset register'),
            C.register_pointer('missing_register', None, title='Register without anchors'),
            C.note('The second pointer has no anchors in this document, so its page reference stays pending '
                   'and is flagged by review rather than printed as a guess.')]
    return out


def state_cards():
    out = sheet_opener('05', 'State cards', 'One card per state. clear never claims safety; '
                       'not_assessed is neutral grey, unavailable amber, partial a slim banner.')
    out += [C.heading('State chips', 3),
            chip_grid([C.state_chip(s) for s in T.STATES], per_row=4),
            C.heading('clear', 3),
            C.state_card('clear', 'No confirmed data leak events were associated with this organisation '
                         'during the assessed period', ['Data leak databases and public disclosures',
                                                       'Monitored online sources, 2008 to assessment date']),
            C.heading('not_assessed', 3),
            C.state_card('not_assessed', C.reason_text({'reason_code': 'module_not_assessed'}),
                         next_step='Enable the AI risk module for the next assessment; it is scored once '
                                   'evidence has been collected and reviewed.'),
            C.heading('not_applicable', 3),
            C.state_card('not_applicable', 'No customer login or payment portal was found on the public site, '
                         'so published terms are not required to cover that kind of access'),
            C.heading('unavailable', 3),
            C.state_card('unavailable', C.reason_text({'reason_code': 'not_printed_in_source'}),
                         'IP reputation feeds for 2 addresses'),
            C.heading('partial', 3),
            C.state_card('partial', 'Grade, risk band and benchmark are available; net score and assessment '
                         'id are not', 'Coverage 28 of an unknown number of eligible targets'),
            C.heading('pending_review', 3),
            C.state_card('pending_review', 'Headline count (2) and listed certificates (3) do not reconcile',
                         next_step='An analyst confirms the count before the score is published.'),
            C.heading('Reason fallback', 3),
            C.state_card('unavailable')]
    return out


def dispatch_demo(identity):
    """render_section() on synthetic payloads: opener + card come from the dispatcher."""
    report = {'sections': {
        'demo_not_assessed': {'title': 'Dispatcher: not assessed', 'state': 'not_assessed',
                              'reason_code': 'module_not_assessed', 'intro_source': 'render_section() draws the '
                              'opener and the grey card. The body is skipped for no-result states.',
                              'summary': 'AI risk was not assessed for this report.',
                              'next_step': 'Enable the module and re-run the assessment.'},
        'demo_clear': {'title': 'Dispatcher: clear', 'state': 'clear', 'intro_source': 'Clear sections get the '
                       'calm card, then their body (here the reference module sections/_template.py).',
                       'summary': 'No fourth-party vendors were discovered with the methods used.',
                       'empty_state_source': {'text': 'No fourth-party vendors were discovered with the '
                                              'methods used. This does not show that the organisation has no '
                                              'suppliers.', 'coverage': 'DNS, MX and NS records; web assets'},
                       'metrics': [{'label': 'Vendors identified', 'value': 0, 'unit': 'organisations',
                                    'state': 'clear'}]},
    }}
    out = []
    for n, key in (('06', 'demo_not_assessed'), ('07', 'demo_clear')):
        spec = SectionSpec(f'cs{n}', key, n, key, 'assessment_details', '_template')
        out += render_section(spec, report, identity)
    return out


def break_control():
    rows = [[f'host-{i:02d}.{"edge." if i % 3 else ""}claude.com', f'vuln-{(i % 9) + 1:02d}',
             (i * 7) % 13 + 1, C.severity_chip(('low', 'medium', 'high')[i % 3], True)] for i in range(60)]
    out = [C.heading('Break control: long register', 2),
           C.P('60 dense rows. The header repeats on every continuation page (repeatRows=1), rows may split '
               '(splitInRow=1), widows and orphans are off, and nothing forces a page break.'),
           C.register_anchor('demo_asset_register', 'start'),
           C.compact_table(['Asset', 'Finding id', 'Count', 'Max severity'], rows, dense=True, numeric_cols=(2,)),
           C.register_anchor('demo_asset_register', 'end'),
           C.heading('Flowing prose', 2)]
    return out + [C.P(PROSE + ' ' + PROSE) for _ in range(3)]


def build(report, out, locked=None):
    qa.ISSUES.clear()
    identity = identity_from_report(report)
    doc = ReportDoc(out, identity, subject='Cyberrank report kit: component sheet')
    rows = [('group', 'Foundation'), ('entry', '01', 'Typography and text', 'H1 / H2 / H3 / intro / body / '
             'note / technical tokens', 'cs-01'),
            ('group', 'Components'), ('entry', '02', 'KPI strip and chips', None, 'cs-02'),
            ('entry', '03', 'Compact tables', None, 'cs-03'),
            ('entry', '04', 'Key values, pointers and notes', None, 'cs-04'),
            ('group', 'States and dispatch'), ('entry', '05', 'State cards', 'clear / not assessed / not '
                                                 'applicable / unavailable / partial / pending review', 'cs-05'),
            ('entry', '06', 'Dispatcher: not assessed', None, 'sec-cs06'),
            ('entry', '07', 'Dispatcher: clear', 'with break-control demo', 'sec-cs07')]
    story = cover_flowables() + [C.heading('Contents', 1, key='contents'),
                                 C.P(f'{identity["org"]} / {identity["domain"]} / Component sheet', 'intro',
                                     spaceAfter=T.SP_LG), C.Contents(rows)]
    story += typography() + kpis_and_chips() + tables() + lists_and_pointers() + state_cards()
    story += dispatch_demo(identity) + break_control()
    if locked:
        story += locked_page(locked, 0, outline='Locked external page')
    total = doc.render(story)
    issues = list(qa.ISSUES) + qa.check_pdf(out, locked_pages=[p for p, *_ in doc.locked],
                                            table_parts=doc.table_parts, table_heads=C._TABLE_HEADS)
    counts = qa.write_report(Path(out).with_suffix('.qa.json'), out, issues, pages=total)
    return total, counts


def main(argv=None):
    ap = argparse.ArgumentParser(prog='python -m cyberrank_report.component_sheet')
    ap.add_argument('data', type=Path)
    ap.add_argument('-o', '--out', type=Path, default=Path('output/Component_Sheet.pdf'))
    ap.add_argument('--locked', type=Path, help='external PDF whose first page is inserted unchanged')
    a = ap.parse_args(argv)
    report = json.loads(a.data.read_text(encoding='utf-8'))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    total, counts = build({'identity': report.get('identity'), 'snapshot': report.get('snapshot')}, a.out, a.locked)
    print(f'{a.out}: {total} pages; QA {counts}')
    return 2 if counts['error'] else 0


if __name__ == '__main__':
    sys.exit(main())
