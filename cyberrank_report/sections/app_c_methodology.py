"""Appendix C: Methodology in brief (redesigned page) + Supply-chain aggregation
(locked page: production page 45 inserted unchanged, no header/footer/watermark).

Wording comes from the payload (*_source fields). The three sub-headings below
are template copy from the production page; the payload does not carry them.
"""
import os
from pathlib import Path

from reportlab.lib.colors import white
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Spacer, Table, TableStyle

from .. import qa, theme as T
from ..page import locked_page, org_name

PIPELINE_TITLE = 'How a rating becomes a risk'
NUMBERS = 'zero one two three four five six seven eight nine ten'.split()
SCALE_TITLE = 'The IISRI rating scale'
# ponytail: the supply-chain page is read from the production PDF in the reference pack.
# Ship it as a package asset (and point this at it) before running outside the pack.
_PACK = Path(__file__).resolve().parents[4]
SUPPLY_CHAIN_PDF = Path(os.environ.get('CYBERRANK_SUPPLY_CHAIN_PDF') or
                        _PACK / '02_PDF_Assessment_Valid/Claude/2026-10-02/Claude - Cyber Risk Report.pdf')
SUPPLY_CHAIN_INDEX = os.environ.get('CYBERRANK_SUPPLY_CHAIN_INDEX', '44')     # 0-based: page 45; parsed softly


class Badge(Flowable):
    """Step number: navy disc, white numeral (contrast 8.6:1)."""
    D = 15.0

    def __init__(self, n):
        super().__init__()
        self.n = str(n)

    def wrap(self, aw, ah):
        return self.D, self.D

    def draw(self):
        c, r = self.canv, self.D / 2
        c.setFillColor(T.NAVY)
        c.circle(r, r, r, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont(T.MEDIUM, 8)
        c.drawCentredString(r, r - 2.9, self.n)


class Tags(Flowable):
    """Signal tags: thin-bordered labels that wrap like words (template: Observe step)."""
    SIZE, PAD, GAP, H = 7.2, 3.0, 2.0, 11.0

    def __init__(self, labels, font, color, border):
        super().__init__()
        self.labels, self.font, self.color, self.border = [str(x) for x in labels], font, color, border

    def _place(self, aw):
        x = y = 0
        out = []
        for s in self.labels:
            w = stringWidth(s, self.font, self.SIZE) + 2 * self.PAD
            if x and x + w > aw:
                x, y = 0, y + self.H + self.GAP
            out.append((x, y, w, s))
            x += w + self.GAP
        return out

    def wrap(self, aw, ah):
        self._spots = self._place(aw)
        self.width = aw
        self.height = (self._spots[-1][1] + self.H) if self._spots else 0
        return aw, self.height

    def draw(self):
        c = self.canv
        c.setLineWidth(0.6)
        c.setStrokeColor(self.border)
        c.setFillColor(self.color)
        c.setFont(self.font, self.SIZE)
        for x, y, w, s in self._spots:
            top = self.height - y
            c.roundRect(x, top - self.H, w, self.H, 1.5, stroke=1, fill=0)
            c.drawString(x + self.PAD, top - self.H + 3.2, s)


class _Block(Table):
    """Layout grid that never splits: it moves to the next page as a whole."""

    def split(self, aw, ah):
        return []


def _col_w(n, gap, ctx):
    return (ctx.t.CW - (n - 1) * gap) / n


def _grid(rows, ctx, gap=None):
    """Layout grid: equal columns with gutters, a rule above each column of the
    first row; later rows align across columns (e.g. callouts)."""
    t = ctx.t
    gap = t.GUTTER if gap is None else gap
    n = len(rows[0])
    w = _col_w(n, gap, ctx)
    data = [[x for i, cell in enumerate(r) for x in ([''] if i else []) + [cell]] for r in rows]
    cmds = [('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]
    cmds += [('LINEABOVE', (2 * i, 0), (2 * i, 0), 0.75, t.RULE) for i in range(n)]
    g = _Block(data, colWidths=[w if j % 2 == 0 else gap for j in range(2 * n - 1)], hAlign='LEFT',
               spaceAfter=t.SP_XS)
    g.setStyle(TableStyle(cmds))
    return g


def _emphasise(text, words, c):
    """Escape the payload text, then bold each `callout_emphasis` phrase (first match, verbatim)."""
    out = c.esc(text)
    for w in words or []:
        e = c.esc(str(w))
        if e and e in out:
            out = out.replace(e, f'<b>{e}</b>', 1)
    return out


def _callout(text, ctx, width, emphasis=None):
    t = ctx.t
    box = Table([[ctx.c.M(_emphasise(text, emphasis, ctx.c), 'dense')]], colWidths=[width], hAlign='LEFT',
                spaceBefore=6)
    box.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), t.SURFACE),
                             ('LINEBEFORE', (0, 0), (0, -1), 2, t.NAVY),
                             ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                             ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
    return box


def _steps(steps, ctx):
    """Four columns: badge, title, text paragraphs (blank line = new paragraph), signal tags, then the
    step's callout directly under its own text (template: callouts are not aligned across columns)."""
    c, t, gap = ctx.c, ctx.t, 12
    w = _col_w(len(steps), gap, ctx)
    top = []
    for s in steps:
        cell = [Badge(s.get('n', '')), c.P(s.get('title') or '', 'h3c', spaceBefore=4, spaceAfter=2)]
        for i, para in enumerate(x for x in str(s.get('text') or '').split('\n\n') if x.strip()):
            cell.append(c.P(para.strip(), 'cell', spaceBefore=4 if i else 0))
        if s.get('signals'):
            cell += [Spacer(1, 6), Tags(s['signals'], t.REGULAR, t.MUTED, t.RULE)]
        if s.get('callout'):
            cell.append(_callout(s['callout'], ctx, w, s.get('callout_emphasis')))
        top.append(cell)
    return _grid([top], ctx, gap)


def _scale(data, ctx):
    """Ten colour segments, D (worst) left to AAA (best) right, labels BELOW them (no text on colour)."""
    c, t = ctx.c, ctx.t
    grades = t.GRADE_BAR
    w = t.CW / len(grades)
    labels = [[c.P(g, 'cell_head', alignment=1), c.P(t.GRADE_MARK[g], 'note_flush', alignment=1,
                                                      hyphenationLang='')] for g in grades]
    ends = data.get('scale_ends_source') or {}
    half = len(grades) // 2
    rows = [[''] * len(grades), labels,
            [c.P(ends.get('bottom') or '', 'note_flush')] + [''] * (half - 1) +
            [c.P(ends.get('top') or '', 'note_flush', alignment=2)] + [''] * (len(grades) - half - 1)]
    tbl = Table(rows, colWidths=[w] * len(grades), rowHeights=[7, None, None], hAlign='LEFT')
    cmds = [('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 1), ('RIGHTPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 1), (-1, 1), 4), ('TOPPADDING', (0, 2), (-1, 2), 1),     # ends sit close to the marks
            ('SPAN', (0, 2), (half - 1, 2)), ('SPAN', (half, 2), (-1, 2))]
    cmds += [('BACKGROUND', (i, 0), (i, 0), t.GRADE[g]) for i, g in enumerate(grades)]
    cmds += [('LINEAFTER', (i, 0), (i, 0), 1.5, white) for i in range(len(grades) - 1)]
    tbl.setStyle(TableStyle(cmds))
    return tbl


def locked_source():
    """(path, 0-based page index) of the supply-chain page, or (None, why it cannot be inserted)."""
    src, raw = SUPPLY_CHAIN_PDF, str(SUPPLY_CHAIN_INDEX).strip()
    if not src.is_file():
        return None, f'supply-chain page source not found: {src}'
    if not raw.isdigit():
        return None, f'CYBERRANK_SUPPLY_CHAIN_INDEX must be a whole number (0-based page), got {raw!r}'
    import pymupdf
    try:
        with pymupdf.open(src) as d:
            pages = d.page_count
    except Exception as e:      # noqa: BLE001 - any unreadable file is the same QA error
        return None, f'supply-chain page source could not be read: {src} ({e})'
    if int(raw) >= pages:
        return None, (f'CYBERRANK_SUPPLY_CHAIN_INDEX {raw} is outside {src.name} '
                      f'({pages} pages, 0-based index 0-{pages - 1})')
    return (src, int(raw)), None


def supply_chain_present(report):
    """True when Appendix C carries the supply-chain page (pointer target for section 14)."""
    from . import NO_RESULT
    data = (report.get('appendices') or {}).get('c_methodology')
    return (isinstance(data, dict) and bool(data.get('supply_chain')) and data.get('state') not in NO_RESULT
            and locked_source()[0] is not None)


def _supply_chain_page(data, ctx):
    """Production page 45, inserted 1:1 as a locked page (counted in 'Page x of y')."""
    if not data.get('supply_chain'):
        return []
    found, why = locked_source()
    if not found:
        qa.add('locked_page_missing', 'error', why, once=True)
        return [ctx.c.state_card('unavailable', 'The supply-chain aggregation page could not be inserted: '
                                 'its source page was not available when this report was built.',
                                 title='Supply-chain aggregation page missing')]
    # inserted fully unchanged: no mask, no kit folio; its own '2 / 2' folio stays
    flow = locked_page(*found, outline='Supply-chain aggregation')
    for f in flow:                       # nest the outline entry under Appendix C
        if getattr(f, '_toc', None):
            f._toc = (1,) + tuple(f._toc[1:])
    return flow


def _subhead(title, sub, ctx):
    """H2 with a muted Light tail on the same line (template: 'How a rating becomes a risk  four steps')."""
    c, t = ctx.c, ctx.t
    tail = (f'<font name="{t.LIGHT}" size="10" color="{c.hexstr(t.MUTED)}">   {c.esc(sub)}</font>'
            if sub else '')
    return c.M(c.esc(title) + tail, 'h2', spaceBefore=t.SP_SM, spaceAfter=2)


def _scale_head(title, caption, ctx):
    """H2 with the caption on its own muted line underneath (template: rating-scale heading)."""
    c = ctx.c
    out = [c.M(c.esc(title), 'h2', spaceBefore=ctx.t.SP_SM, spaceAfter=0)]
    if caption:
        out.append(c.P(caption, 'note_flush', spaceAfter=5))
    return out


def build(data, ctx):
    c, t = ctx.c, ctx.t
    org = org_name(ctx.report)
    out = []
    if data.get('headline_source'):
        out.append(c.P(data['headline_source'], 'h2', spaceBefore=0))
    if data.get('lead_source'):
        out.append(c.P(data['lead_source'], 'intro', spaceAfter=t.SP_SM))

    cols = [x for x in data.get('columns_source') or [] if isinstance(x, dict)]
    if cols:
        out.append(_grid([[[c.P(x.get('title') or '', 'h3c', spaceBefore=0),
                            c.P(x.get('text') or '', 'cell')] for x in cols]],
                         ctx))

    steps = [s for s in data.get('steps_source') or [] if isinstance(s, dict)]
    if steps:
        n = NUMBERS[len(steps)] if len(steps) < len(NUMBERS) else str(len(steps))
        out.append(_subhead(PIPELINE_TITLE, f'{n} step{"s" if len(steps) != 1 else ""}, one pipeline', ctx))
        out.append(_steps(steps, ctx))
    out.append(c.keep(*_scale_head(SCALE_TITLE, data.get('scale_caption_source'), ctx), _scale(data, ctx)))
    notes = [f'General methodology, the same in every report; figures on the supply-chain page are illustrative '
             f'and are not results for {org}.'] if data.get('is_generic_material') else []
    notes += [data['copyright_source']] if data.get('copyright_source') else []
    if notes:
        out.append(c.P(' '.join(notes), 'note', spaceBefore=t.SP_XS, spaceAfter=0))
    return out + _supply_chain_page(data, ctx)
