"""Prototype: five alternative 'Rating overview' concepts, one per A4 page, + a hard-state variant of
the recommended one. Synthetic data (Northwind Example Ltd). Uses the report's own components/tokens.

    .venv/bin/python -I tools/prototypes/rating_overview_concepts.py <out.pdf>
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from reportlab.pdfbase.pdfmetrics import stringWidth           # noqa: E402
from reportlab.platypus import Flowable, PageBreak, Spacer, Table, TableStyle  # noqa: E402

from cyberrank_report import components as c, icons as I, qa, theme as T    # noqa: E402
from cyberrank_report.page import ReportDoc, cover_flowables, identity_from_report  # noqa: E402

H, MU, NV = c.hexstr(T.HEADING), c.hexstr(T.MUTED), c.hexstr(T.NAVY)
NA = 'na'   # an aspect that normally has a score, but none is available in this report

# (section, aspect, score % | None (never scored) | NA, result, state)
# result: (number, noun phrase) | ('', worded comparison) | None (no result: state says why)
DEMO = [
    ('03', 'Privacy', 64, ('6', 'active privacy risks'), 'findings'),
    ('04', 'Vulnerabilities', 38, ('12', 'finding types · 1 Critical, 2 High'), 'findings'),
    ('05', 'Credential exposure', 45, ('40', 'exposed account records'), 'findings'),
    ('06', 'Data breach and leak history', 55, ('3', 'events · 1 resolved'), 'findings'),
    ('07', 'Data sovereignty', None, ('', 'Matches the preference'), 'clear'),
    ('08', 'Data residency', None, ('1 of 6', 'hosting countries outside the preference'), 'findings'),
    ('09', 'Legal terms & conditions', None, ('1 of 2', 'customer-protection clauses found'), 'findings'),
    ('10', 'AI risk and governance', None, ('2', 'AI governance issues'), 'findings'),
    ('11', 'Quantum security', None, ('33', 'high-risk algorithm uses'), 'findings'),
    ('12', 'Security resourcing', None, ('2 of 2', 'security roles with public evidence'), 'clear'),
    ('13', 'Certifications', 68, ('3', 'certifications · 1 awaiting approval'), 'findings'),
    ('14', 'Fourth-party vendors', None, ('34', 'connected organisations · 5 need a look'), 'partial'),
    ('15', 'Cloud infrastructure', None, ('4', 'cloud providers'), 'findings'),
]
HARD = {r[0]: r for r in DEMO}
HARD.update({
    '06': ('06', 'Data breach and leak history', 100, ('0', 'breach or leak events'), 'clear'),
    '09': ('09', 'Legal terms & conditions', None, None, 'not_applicable'),
    '10': ('10', 'AI risk and governance', None, None, 'not_assessed'),
    '13': ('13', 'Certifications', NA, ('0', 'certifications on record'), 'clear'),
})
HARD = [HARD[r[0]] for r in DEMO]
assert [r[0] for r in DEMO] == [f'{i:02d}' for i in range(3, 16)]
assert sum(isinstance(r[2], int) for r in DEMO) == 5

INTRO = 'All 13 aspects in report order. Five have their own score (100% = best); the rest are judged by their result.'


# --- shared atoms -----------------------------------------------------------------
def num(n, style='toc_num'):
    return c.M(f'<font color="{NV}">{n}</font>', style)


def name(t, style='toc_num'):
    return c.M(c.esc(t), style)          # toc_num = Medium 9.1 HEADING


def result(r, style='cell'):
    """The one result grammar: <number> <noun phrase>; worded only for comparisons; no result -> muted
    'No result' (the state chip beside it says why). A ' · ' qualifier wraps as one unit; no one-word last line."""
    if r is None:
        return c.M(f'<font color="{MU}">No result</font>', style)
    n, rest = r
    main, *qual = rest.split(' · ')
    main = c.esc(main).rsplit(' ', 1)
    text = '&nbsp;'.join(main) + ''.join(' · ' + c.esc(q).replace(' ', '&nbsp;') for q in qual)
    lead = f'<font name="{T.MEDIUM}" color="{H}">{c.esc(n)}</font> ' if n else ''
    return c.M(lead + text, style)


def score_text(s, style='cell_num'):
    if isinstance(s, int):
        return c.M(f'<font name="{T.MEDIUM}" color="{H}">{s}%</font>', style)
    if s == NA:
        return c.M(f'<font color="{MU}">Not available</font>', 'dense_muted', alignment=2)
    return c.M(f'<font color="{MU}">–</font>', style)


def chip(st):
    return c.state_chip(st, dense=True)


def frame_cmds(pad_v=0, pad_h=0):
    return [('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), pad_h), ('RIGHTPADDING', (0, 0), (-1, -1), pad_h),
            ('TOPPADDING', (0, 0), (-1, -1), pad_v), ('BOTTOMPADDING', (0, 0), (-1, -1), pad_v)]


NOTE = T.STYLES['note'].clone('note_nohy', hyphenationLang='', embeddedHyphenation=0)


def score_legend(rows):
    na = ' “Not available”: this aspect normally has a score, but none could be given in this report.'
    return c.P('– in the Score column: this aspect has no separate score and is judged by its result. '
               'Scores and results are never added up or averaged.' + (na if any(r[2] == NA for r in rows) else ''),
               NOTE)


class Leader(Flowable):
    """Text followed by dot leaders to the right edge of the cell (contents idiom)."""

    def __init__(self, text, style='toc_num'):
        super().__init__()
        self.text, self.st = text, T.STYLES[style]

    def wrap(self, aw, ah):
        self.width, self.height = aw, self.st.leading
        return aw, self.height

    def draw(self):
        cv, fs = self.canv, self.st.fontSize
        y = self.height - fs           # first baseline, as a Paragraph places it
        cv.setFont(self.st.fontName, fs)
        cv.setFillColor(self.st.textColor)
        cv.drawString(0, y, self.text)
        x = stringWidth(self.text, self.st.fontName, fs) + 6
        cv.setFillColor(T.SLATE_400)
        cv.setFont(T.LIGHT, 8)
        while x < self.width - 8:
            cv.drawString(x, y, '.')
            x += 3.6


class Meter(Flowable):
    """0-100 track. Scored: navy fill to the value. Never scored / n/a: a dashed hairline with a muted
    label on it, so it can never read as 0%."""

    def __init__(self, score, width, h=12, label_never='No separate score', label_na='Score not available'):
        super().__init__()
        self.score, self.width, self.height = score, width, h
        self.labels = label_never, label_na

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        cv, w, mid = self.canv, self.width, self.height / 2 + 1
        if isinstance(self.score, int):
            cv.setFillColor(T.SAPPHIRE_100)
            cv.roundRect(0, mid - 3, w, 6, 3, stroke=0, fill=1)
            cv.setFillColor(T.NAVY)
            cv.roundRect(0, mid - 3, max(6, w * self.score / 100), 6, 3, stroke=0, fill=1)
            return
        label = self.labels[self.score == NA]
        fs = 7.2
        tw = stringWidth(label, T.LIGHT, fs)
        cv.setStrokeColor(T.SLATE_400)
        cv.setLineWidth(0.6)
        cv.setDash(1.5, 2)
        cv.line(tw + 4, mid, w, mid)
        cv.setDash()
        cv.setFillColor(T.MUTED)
        cv.setFont(T.LIGHT, fs)
        cv.drawString(0, mid - fs * 0.36, label)


H2 = T.STYLES['h2'].clone('h2_tight', spaceBefore=2)


def page(eyebrow, body, rows=DEMO, legend=True, intro=INTRO):
    assert stringWidth(intro, T.LIGHT, T.STYLES['body'].fontSize) < T.CW, 'intro must stay one line'
    out = [c.P(eyebrow, 'eyebrow'), c.heading('Rating overview', 2, toc=False, style=H2), c.P(intro, 'body')]
    out += body
    if legend:
        out.append(score_legend(rows))
    return out + [PageBreak()]


# --- A. split view: score meters + two-column checklist ----------------------------
def concept_a(rows=DEMO):
    scored = [r for r in rows if isinstance(r[2], int)]
    mw = 230
    meter_rows = [[num(r[0], 'cell'), name(r[1], 'cell_head'), Meter(r[2], mw), score_text(r[2])] for r in scored]
    t1 = Table(meter_rows, colWidths=[24, 170, mw + 12, 44], hAlign='LEFT')
    t1.setStyle(TableStyle(frame_cmds(3.5) + [('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    head1 = Table([[c.P('Aspect scores', 'h3'), c.P('0%', 'note_flush'),
                    c.P('100% = best', 'note_flush', alignment=2)]],
                  colWidths=[194, mw / 2, mw / 2], hAlign='LEFT')
    head1.setStyle(TableStyle(frame_cmds() + [('VALIGN', (0, 0), (-1, -1), 'BOTTOM')]))

    def item(r):
        cell = [name(r[1], 'cell_head'), result(r[3], 'dense')]
        return [num(r[0], 'cell'), cell, chip(r[4])]
    w = [22, T.COL2 - 22 - 92, 92]
    cols = []
    for part in (rows[:7], rows[7:]):
        t = Table([item(r) for r in part], colWidths=w, hAlign='LEFT')
        t.setStyle(TableStyle(frame_cmds(5) + [('LINEBELOW', (0, 0), (-1, -1), T.HAIRLINE, T.RULE),
                                               ('LEFTPADDING', (2, 0), (2, -1), 4),
                                               ('TOPPADDING', (2, 0), (2, -1), 6)]))
        cols.append(t)
    two = Table([cols], colWidths=[T.COL2 + T.GUTTER, T.COL2], hAlign='LEFT')
    two.setStyle(TableStyle(frame_cmds()))
    note = c.P('Only these five aspects have their own score. The other eight have no separate score '
               'and are judged by their result below.', 'note')
    return [Spacer(0, 4), head1, Spacer(0, 2), t1, note, c.P('All aspects', 'h3'),
            c.M(f'<font color="{MU}">Reading order: down the left column, then the right.</font>', 'note_flush'),
            Spacer(0, 4), two]


# --- B. index list (contents idiom): headline line + result sub-line -------------------
def concept_b(rows=DEMO):
    sw, cw = 60, 104
    data = [[c.P('Section', 'note_flush'), c.P('Aspect and result', 'note_flush'),
             c.P('Score', 'note_flush', alignment=2), c.P('Status', 'note_flush')]]
    for r in rows:
        data.append([num(r[0]), [Leader(r[1]), result(r[3], 'toc_sub')], score_text(r[2], 'toc_num_r'),
                     chip(r[4])])
    t = Table(data, colWidths=[44, T.CW - 44 - sw - cw, sw, cw], hAlign='LEFT')
    t.setStyle(TableStyle(frame_cmds(5.5) + [
        ('LINEBELOW', (0, 0), (-1, 0), 0.75, T.HEADING), ('TOPPADDING', (0, 0), (-1, 0), 0),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('LEFTPADDING', (3, 0), (3, -1), 12), ('RIGHTPADDING', (2, 0), (2, -1), 2),
        ('TOPPADDING', (3, 1), (3, -1), 7)]))
    return [Spacer(0, 6), t]


T.STYLES['toc_num_r'] = T.STYLES['toc_num'].clone('toc_num_r', alignment=2)   # prototype-local style


# --- C. grouped by state band ----------------------------------------------------------
def concept_c(rows=DEMO):
    order = ['findings', 'partial', 'pending_review', 'unavailable', 'clear', 'not_assessed', 'not_applicable']
    data, cmds = [], frame_cmds(4.5)
    for st in order:
        grp = [r for r in rows if r[4] == st]
        if not grp:
            continue
        i = len(data)
        n = len(grp)
        data.append([I.state_label(st, style=T.STYLES['chip'], label=f'{T.STATE_LABELS[st]} · {n} aspect{"s" * (n != 1)}'),
                     '', '', ''])
        cmds += [('SPAN', (0, i), (-1, i)), ('LINEBELOW', (0, i), (-1, i), 0.75, T.HEADING),
                 ('TOPPADDING', (0, i), (-1, i), 0 if i == 0 else 16), ('BOTTOMPADDING', (0, i), (-1, i), 5)]
        for r in grp:
            data.append([num(r[0], 'cell'), name(r[1], 'cell_head'), result(r[3]), score_text(r[2])])
            cmds.append(('LINEBELOW', (0, len(data) - 1), (-1, len(data) - 1), T.HAIRLINE, T.RULE))
    t = Table(data, colWidths=[40, 170, T.CW - 40 - 170 - 48, 48], hAlign='LEFT')
    cmds += [('LEFTPADDING', (0, 0), (0, -1), 0)]
    t.setStyle(TableStyle(cmds))
    head = Table([[c.P('Section', 'note_flush'), c.P('Aspect', 'note_flush'), c.P('Result', 'note_flush'),
                   c.P('Score', 'note_flush', alignment=2)]], colWidths=t._colWidths, hAlign='LEFT')
    head.setStyle(TableStyle(frame_cmds(0)))
    return [Spacer(0, 6), head, Spacer(0, 6), t]


# --- D. score strip: one track per aspect, dashed when there is no score ---------------
def concept_d(rows=DEMO):
    mw = 130
    data = [[c.P('Section', 'note_flush'), c.P('Aspect and result', 'note_flush'),
             c.P('Score  0% to 100% (best)', 'note_flush'), '', c.P('Status', 'note_flush')]]
    for r in rows:
        data.append([num(r[0], 'cell'), [name(r[1], 'cell_head'), result(r[3], 'dense')],
                     Meter(r[2], mw), score_text(r[2]) if isinstance(r[2], int) else '', chip(r[4])])
    w = [40, 0, mw + 8, 38, 98]
    w[1] = T.CW - sum(w)
    t = Table(data, colWidths=w, hAlign='LEFT')
    t.setStyle(TableStyle(frame_cmds(5, 4) + [
        ('LEFTPADDING', (0, 0), (0, -1), 0),
        ('SPAN', (2, 0), (3, 0)), ('TOPPADDING', (2, 1), (2, -1), 5.5), ('TOPPADDING', (4, 1), (4, -1), 6),
        ('LINEBELOW', (0, 0), (-1, 0), 0.75, T.HEADING), ('TOPPADDING', (0, 0), (-1, 0), 0),
        ('LINEBELOW', (0, 1), (-1, -1), T.HAIRLINE, T.RULE), ('LEFTPADDING', (4, 0), (4, -1), 10)]))
    return [Spacer(0, 6), t]


# --- E. two-column card list, fixed 3-line grammar --------------------------------------
def concept_e(rows=DEMO):
    def card(r):
        s = r[2]
        right = (c.M(f'<font color="{MU}">Score</font> <font name="{T.MEDIUM}" color="{H}">{s}%</font>', 'cell_num')
                 if isinstance(s, int) else
                 c.M(f'<font color="{MU}">{"Score not available" if s == NA else "No separate score"}</font>',
                     'dense_num'))
        top = Table([[c.M(f'<font color="{NV}">{r[0]}</font>&nbsp;&nbsp;&nbsp;{c.esc(r[1])}', 'cell_head'), right]],
                    colWidths=[T.COL2 - 96, 96], hAlign='LEFT')
        top.setStyle(TableStyle(frame_cmds() + [('VALIGN', (0, 0), (-1, -1), 'BOTTOM')]))
        body = [top, Spacer(0, 2), result(r[3], 'cell'), Spacer(0, 3), chip(r[4])]
        t = Table([[body]], colWidths=[T.COL2], hAlign='LEFT')
        t.setStyle(TableStyle(frame_cmds() + [('LINEABOVE', (0, 0), (-1, 0), 0.75, T.HEADING),
                                              ('TOPPADDING', (0, 0), (-1, -1), 6),
                                              ('BOTTOMPADDING', (0, 0), (-1, -1), 12)]))
        return t
    left, right = rows[:7], rows[7:] + [None]
    data = [[card(a), card(b) if b else ''] for a, b in zip(left, right)]
    t = Table(data, colWidths=[T.COL2 + T.GUTTER * 2, T.COL2], hAlign='LEFT')
    t.setStyle(TableStyle(frame_cmds()))
    return [Spacer(0, 4), c.M(f'<font color="{MU}">Reading order: down the left column, then the right.</font>',
                              'note_flush'), Spacer(0, 8), t]


def story():
    s = cover_flowables()
    s += page('Concept A · Split view: scores first, then a checklist of all 13', concept_a(), legend=False)
    s += page('Concept B · Index list in the style of the contents', concept_b())
    s += page('Concept C · Grouped by status (section order kept inside each group)', concept_c(),
              intro='All 13 aspects grouped by status, report order inside each group. Five have their own score (100% = best).')
    s += page('Concept D · Score strip on every row; dashed where there is no score', concept_d(), legend=False)
    s += page('Concept E · Two-column card list with a fixed three-line grammar', concept_e(), legend=False)
    s += page('Concept B, harder mix · not assessed, not applicable, clear with 100%, clear with 0',
              concept_b(HARD), rows=HARD)
    s.pop()    # no trailing page break
    return s


if __name__ == '__main__':
    out = sys.argv[1]
    ident = identity_from_report(json.load(open(ROOT / 'data' / 'demo-preview.json')))
    total = ReportDoc(out, ident, subject='Rating overview concepts (synthetic data)').render(story())
    assert total == 7, f'each concept must fit one page: got {total} pages, expected 7'
    issues = [i for i in qa.ISSUES if i['severity'] in ('warn', 'error')]
    assert not issues, issues
    print(out, total, 'pages')
