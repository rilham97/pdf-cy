"""Reusable flowables. Every data string goes through P()/tech() (escaped).

Conventions: missing values are never 0 -- render them with missing_text();
technical tokens (hosts, URLs, hashes) go through tech() so they wrap after
/ . - _ @ and are never hyphenated or truncated.
"""
import itertools

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, KeepTogether, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.flowables import _listWrapOn

from . import icons as I
from . import theme as T
from .tables import (_TABLE_HEADS, CompactTable, center_severity, compact_table, footnote, head_width, key_value_list,  # noqa: F401
                     numbered, table_cell)
from .text import (REASONS, STATE_REASON_FALLBACK, UNITS, M, P, TechText, breakable, bullets, esc,  # noqa: F401
                   flag_notes, fmt_date, fmt_number, fmt_version, fmt_unit, fmt_value, hexstr, is_missing, missing_text, note,
                   plain, reason_text, sentence, tech, tech_lines, val)
from .fonts import fallback
from .theme import STYLES

__all__ = [  # the section-facing API (ctx.c.<name>)
    # text and values
    'P', 'M', 'tech', 'TechText', 'tech_lines', 'breakable', 'note', 'bullets', 'esc', 'hexstr', 'sentence',
    'is_missing', 'reason_text', 'missing_text', 'fmt_value', 'fmt_number', 'fmt_unit', 'fmt_date',
    'REASONS', 'UNITS', 'STATE_REASON_FALLBACK',
    # structure
    'heading', 'Anchor', 'Keep', 'keep', 'section_opener', 'verdict_row',
    # components
    'chip', 'state_chip', 'severity_chip', 'severity_icon', 'severity_legend', 'heading_legend', 'grade_chip', 'Chip', 'state_card', 'coverage_banner',
    'CARD_TITLES', 'kpi_strip', 'compact_table', 'center_severity', 'head_width', 'numbered', 'table_cell', 'footnote', 'key_value_list',
    'CompactTable', 'register_pointer', 'register_anchor', 'RegisterPointer', 'Contents',
]

# --- structure ----------------------------------------------------------------
_KEYS = itertools.count(1)


def heading(text, level=1, key=None, style=None, toc=True):
    """H1/H2 register an outline entry (+ Contents anchor via key); H3 is plain."""
    p = P(text, style or {1: 'h1', 2: 'h2', 3: 'h3'}[level])
    if level in (1, 2) and toc:
        p._toc = (level - 1, str(text), key or f'h{next(_KEYS)}')
    return p


class Anchor(Flowable):
    """Zero-size named destination; doc records its page (see ReportDoc.afterFlowable)."""

    def __init__(self, key, outline=None, level=0):
        super().__init__()
        self._anchor = key
        if outline:
            self._toc = (level, outline, key)
        self.width = self.height = 0

    def wrap(self, aw, ah):
        return 0, 0

    def draw(self):
        pass


class Keep(KeepTogether):
    """KeepTogether that never strands a lead-in and never jumps a whole page for a
    tall block. Short groups (<= KEEP_MAX_H) stay together. Taller groups (e.g. a
    heading + long table) keep the lead-in with the FIRST PART of the last flowable;
    if no part fits, the group moves to the next frame. Also the doc's
    keepTogetherClass, so keepWithNext headings get the same behaviour."""

    def split(self, aw, ah):
        if getattr(self, '_wrapInfo', None) != (aw, ah):
            self.wrap(aw, ah)
        if self._H <= ah or self._H <= T.KEEP_MAX_H or len(self._content) < 2:
            return KeepTogether.split(self, aw, ah)
        *lead, last = self._content
        _, h = _listWrapOn(lead, aw, self.canv)
        room = ah - h - last.getSpaceBefore()
        parts = last.splitOn(self.canv, aw, room) if room > 0 else []
        if parts:
            return lead + parts
        at_top = getattr(getattr(self, '_frame', None), '_atTop', False)
        return list(self._content) if at_top else [self.FrameBreak()] + list(self._content)


def keep(*flowables):
    return Keep([f for f in flowables if f is not None])


# --- chips --------------------------------------------------------------------
class Chip(Flowable):
    """6 x 6 pt colour square + text (text stays BODY colour for contrast).
    hollow: 1 pt outline instead of a fill (pending_review: same hue as findings)."""
    SQ, GAP = 6.0, 4.0

    def __init__(self, text, color, style='chip', hollow=False):
        super().__init__()
        st = STYLES[style]
        self.text, self.color, self._fs, self._font = str(text), color, st.fontSize, st.fontName
        self.hollow = hollow
        self._p = Paragraph(fallback(esc(text)), st.clone(st.name + '_chip', leftIndent=self.SQ + self.GAP))

    def wrap(self, aw, ah):
        self.width = min(aw, self.SQ + self.GAP + stringWidth(self.text, self._font, self._fs) + 0.5)
        _, self.height = self._p.wrap(self.width, ah)
        return self.width, self.height

    def draw(self):
        self._p.drawOn(self.canv, 0, 0)
        baseline = self.height - self._fs                  # RL first baseline
        y = baseline + self._fs * 0.36 - self.SQ / 2       # centre on x-height
        if self.hollow:     # stroke inside the 6 pt footprint
            self.canv.setStrokeColor(self.color)
            self.canv.setLineWidth(1)
            self.canv.rect(0.5, y + 0.5, self.SQ - 1, self.SQ - 1, stroke=1, fill=0)
        else:
            self.canv.setFillColor(self.color)
            self.canv.rect(0, y, self.SQ, self.SQ, stroke=0, fill=1)

    def minWidth(self):
        return self.SQ + self.GAP + max(stringWidth(w, self._font, self._fs) for w in self.text.split() or [''])


def chip(text, color, dense=False, hollow=False):
    """Colour-square chip: grade and risk band only. States and severities are icon +
    label (state_chip / severity_chip); categories print as plain text."""
    return Chip(text, color, 'chip_dense' if dense else 'chip', hollow)


def state_chip(state, dense=False):
    """State icon (Phosphor regular) + its real-text label."""
    return I.state_label(state, style=STYLES['chip_dense' if dense else 'chip'])


def severity_chip(level, dense=False, scale='standard'):
    """Siren + severity label (Critical / High / Medium / Low; quantum Moderate)."""
    return I.severity_label(level, scale, style=STYLES['chip_dense' if dense else 'chip'])


def severity_icon(level, dense=False, scale='standard'):
    """Table cell / detail block: siren only, its word as invisible text (icons.SeverityIcon). Pair the
    table with severity_legend()."""
    return I.severity_cell(level, scale, STYLES['dense' if dense else 'cell'])


class SeverityLegend(Flowable):
    """Severity legend strip (no box, no title, no frame): siren + label (Regular 8.2) + count (Medium 8.2)
    per level, worst first. One line by default; heading_legend() sets `vertical` (one level per line,
    counts right-aligned) only when the line does not fit beside the heading. Real text: searchable."""
    FS, LEAD, GAP, ITEM_GAP = 8.2, 11, 3, 12

    def __init__(self, counts, scale='standard'):
        super().__init__()
        self.items = [(I.severity_level(lv, scale), 'Not available' if is_missing(n) else fmt_number(n))
                      for lv, n in counts]          # caller states the reason for a missing count
        self.size = round(self.FS * I.SIREN_EM, 2)
        self.icon_w = self.size * (I.SIREN_RIGHT - I.SIREN_PAD) + self.GAP
        self.vertical = False

    def _lw(self, label):
        return stringWidth(label, T.REGULAR, self.FS)

    def _nw(self, num):
        return stringWidth(num, T.MEDIUM, self.FS)

    def row_width(self):
        return sum(self.icon_w + self._lw(lb) + self.GAP + self._nw(n) for (lb, _), n in self.items) \
            + self.ITEM_GAP * (len(self.items) - 1)

    def wrap(self, aw, ah):
        if self.vertical:
            self.width = self.icon_w + max(self._lw(lb) for (lb, _), _ in self.items) + 8 \
                + max(self._nw(n) for _, n in self.items)
        else:
            self.width = self.row_width()
        self.height = self.LEAD * (len(self.items) if self.vertical else 1)
        return self.width, self.height

    def draw(self):
        c, x = self.canv, 0
        for i, ((label, key), num) in enumerate(self.items):
            base = (self.height - self.LEAD * (i + 1) if self.vertical else 0) + self.LEAD - self.FS
            if self.vertical:
                x = 0
            I.Icon(I._siren_layers(key), self.size).drawOn(c, x - self.size * I.SIREN_PAD,
                                                            base - self.size * I.SIREN_BASE)
            x += self.icon_w
            c.setFont(T.REGULAR, self.FS)
            c.setFillColor(T.BODY)
            c.drawString(x, base, label)
            c.setFont(T.MEDIUM, self.FS)
            c.setFillColor(T.HEADING)
            if self.vertical:
                c.drawRightString(self.width, base, num)
            else:
                x += self._lw(label) + self.GAP
                c.drawString(x, base, num)
                x += self._nw(num) + self.ITEM_GAP


def severity_legend(counts, scale='standard'):
    """Legend for icon-only severity columns; set it on the heading line with heading_legend().
    counts: [(level, n | null record)], worst first."""
    return SeverityLegend(counts, scale)


class HeadingLegend(Flowable):
    """Heading (H2) with a SeverityLegend right-aligned on its first baseline. The legend stacks
    vertically in the same place only when heading text + gap + one-line legend exceed the width.
    Keeps the heading's outline / Contents entry, spacing and keepWithNext."""

    def __init__(self, head, legend, gap=T.GUTTER * 2):
        super().__init__()
        self.head, self.legend, self.gap = head, legend, gap
        if getattr(head, '_toc', None):
            self._toc = head._toc
        self.spaceBefore, self.spaceAfter = head.getSpaceBefore(), head.getSpaceAfter()
        self.keepWithNext = 1

    def wrap(self, aw, ah):
        st = self.head.style
        text_w = stringWidth(self.head.getPlainText(), st.fontName, st.fontSize)
        self.legend.vertical = text_w + self.gap + self.legend.row_width() > aw
        lw, lh = self.legend.wrap(aw, ah)
        _, self._hh = self.head.wrap(aw - lw - self.gap, ah)
        self._drop = st.fontSize - self.legend.FS    # heading baseline - legend baseline
        self.width, self.height = aw, max(self._hh, self._drop + lh)
        return self.width, self.height

    def draw(self):
        self.head.drawOn(self.canv, 0, self.height - self._hh)
        self.legend.drawOn(self.canv, self.width - self.legend.width, self.height - self._drop - self.legend.height)


def heading_legend(head, legend):
    return HeadingLegend(head, legend)


def grade_chip(grade, with_mark=True, dense=False):
    g = str(grade or '').upper()
    if g not in T.GRADE:
        return chip('Grade not available', T.UNSCANNED, dense)
    return chip(f'{g}  {T.GRADE_MARK[g]}' if with_mark else g, T.GRADE[g], dense)


# --- section opener -----------------------------------------------------------
def section_opener(number, title, state=None, verdict=None, intro=None, *, key=None, group=None, icon=None):
    """Eyebrow (number / group), H1 (with the aspect icon when `icon` is a registry key),
    intro, then a state chip + verdict row."""
    eyebrow = f'{number}  ·  {group}' if group else str(number)
    h1 = (I.icon_heading(icon, title, 1, anchor=key or f'h{next(_KEYS)}') if icon in I.ICONS
          else heading(title, 1, key=key))
    out = [P(eyebrow.upper(), 'eyebrow'), h1]
    if intro:
        out.append(P(intro, 'intro', keepWithNext=1))
    if state or verdict:
        out.append(verdict_row(state, verdict))
    for f in out:              # flat keepWithNext chain: binds to the first body block
        f.keepWithNext = 1
    return out


def verdict_row(state, verdict):
    if state and not verdict:      # nothing to rule off: the chip alone
        c = state_chip(state)
        c.spaceBefore, c.spaceAfter = T.SP_XS, T.SP_MD
        return c
    if state:
        t = Table([[state_chip(state), P(verdict or '', 'verdict')]], colWidths=[104, T.CW - 104],
                  spaceAfter=T.SP_MD, hAlign='LEFT')
    else:          # no chip (01 overview, appendices): the verdict alone, full width; a 'Summary' label adds nothing
        t = Table([[P(verdict or '', 'verdict')]], colWidths=[T.CW], spaceAfter=T.SP_MD, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
        ('TOPPADDING', (0, 0), (0, 0), 9.6),            # chip baseline = verdict baseline
        ('LINEABOVE', (0, 0), (-1, 0), 0.75, T.RULE), ('LINEBELOW', (0, 0), (-1, 0), 0.75, T.RULE),
    ]))
    return t


# --- state cards --------------------------------------------------------------
CARD_TITLES = {
    'findings': 'Findings reported',
    'identified': 'Identified',
    'clear': T.CLEAR_TITLE,
    'not_assessed': 'Not assessed in this report',
    'not_applicable': 'Not applicable for this assessment',
    'unavailable': 'Data unavailable',
    'partial': 'Partial coverage',
    'pending_review': 'Result held for review',
    'none_identified': 'None identified',
}


def _items(v):
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return bullets([str(i) for i in v], 'bullet')
    return [P(v, 'card_body')]


def state_card(state, reason=None, what_checked=None, *, title=None, next_step=None, width=None):
    """Card for a non-findings state. clear never claims 'safe'; non-clear always prints a reason.
    what_checked is ignored for no-result states (not_assessed / not_applicable / unavailable)."""
    st = T.STATE[state]
    if state in ('not_assessed', 'not_applicable', 'unavailable'):
        what_checked = None
    width = width or T.CW
    if state == 'partial':
        return coverage_banner(reason, what_checked, width=width)
    body = [P(title or CARD_TITLES[state], 'card_title')]
    if state != 'clear' or reason:
        body.append(P(sentence(reason) if reason else STATE_REASON_FALLBACK, 'card_body'))
    if what_checked:
        body += [P('What was checked', 'card_label')] + _items(what_checked)
    if next_step:
        label = 'How it becomes assessed' if state == 'not_assessed' else 'What happens next'
        body += [P(label, 'card_label')] + _items(next_step)
    return _card(body, st, width)


def coverage_banner(reason=None, coverage=None, width=None):
    """Slim banner for state 'partial', above the content that is available. No chip:
    the opener's verdict row already shows 'Partial coverage'."""
    st = T.STATE['partial']
    text = sentence(reason) if reason else STATE_REASON_FALLBACK
    if coverage:
        text += ' ' + sentence(coverage)
    t = Table([[P(text, 'card_body')]], colWidths=[width or T.CW], spaceAfter=T.SP_MD, hAlign='LEFT')
    t.setStyle(TableStyle(_card_style(st, pad_v=7)))
    return t


def _card_style(st, pad_v=10):
    return [
        ('BACKGROUND', (0, 0), (-1, -1), st['bg']),
        ('LINEBEFORE', (0, 0), (0, -1), 2.5, st['accent']),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), pad_v), ('BOTTOMPADDING', (0, 0), (-1, -1), pad_v + 1),
    ]


def _card(body, st, width):
    # one row, no splitInRow: a card never breaks across pages
    t = Table([[body]], colWidths=[width], spaceAfter=T.SP_MD, hAlign='LEFT')
    t.setStyle(TableStyle(_card_style(st)))
    return t


# --- KPI strip ----------------------------------------------------------------
def kpi_strip(items, per_row=None):
    """items: dicts with value, unit, label, state (+ reason_code / reason). Fixture
    metric records work as-is. Missing values print 'Not available' + reason."""
    items = list(items)
    if not items:
        return Spacer(0, 0)
    n = per_row or (3 if len(items) in (3, 5, 6, 9) else 4)
    w = (T.CW - (n - 1) * T.GUTTER) / n
    tiles = [_kpi_tile(it) for it in items]
    rows = [tiles[i:i + n] for i in range(0, len(tiles), n)]
    data, cols = [], []
    for r in rows:
        r = r + [''] * (n - len(r))
        data.append(list(itertools.chain.from_iterable((c, '') for c in r))[:-1])
    cols = list(itertools.chain.from_iterable((w, T.GUTTER) for _ in range(n)))[:-1]
    cmds = [('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 12)]
    for ri, r in enumerate(rows):
        for ci in range(len(r)):
            cmds.append(('LINEABOVE', (ci * 2, ri), (ci * 2, ri), 0.75, T.RULE))
    t = Table(data, colWidths=cols, spaceAfter=T.SP_SM, hAlign='LEFT')
    t.setStyle(TableStyle(cmds))
    return t


def _kpi_tile(it):
    unit, val, state = it.get('unit'), it.get('value'), it.get('state')
    out = []
    na = val is None and state == 'not_applicable'     # the headline already says it: no chip
    if val is None:
        out.append(P('Not applicable' if na else 'Not available', 'kpi_na'))
    elif unit == 'percent':
        out.append(P(f'{fmt_number(val)}%', 'kpi_value'))
    else:
        u = fmt_unit(unit, val) if unit else ''
        tail = f'<font name="{T.LIGHT}" size="9.1" color="{hexstr(T.MUTED)}"> {esc(u)}</font>' if u else ''
        out.append(M(esc(fmt_number(val)) + tail, 'kpi_value'))
    if it.get('severity'):       # severity tier: siren + the tier label, never plain text
        lab = I.severity_label(it['severity'], it.get('scale', 'standard'), style=STYLES['kpi_label'],
                               label=it.get('label'))
        lab.spaceBefore = 2
        out.append(lab)
    else:
        out.append(P(it.get('label') or '', 'kpi_label', spaceBefore=2))
    if val is None:
        out.append(P(sentence(reason_text(it)), 'note_flush', spaceBefore=3))
    if state and state != 'findings' and not na:
        out += [Spacer(0, 5), state_chip(state, dense=True)]
    return out


# --- cross references ---------------------------------------------------------
def _doc(flowable):
    return getattr(getattr(flowable, 'canv', None), '_doctemplate', None)


def _pages_label(doc, start_key, end_key):
    """('pages 31–33', True) once the anchors resolved on a previous pass."""
    prev = getattr(doc, 'anchors_prev', {}) if doc else {}
    a, b = prev.get(start_key), prev.get(end_key, prev.get(start_key))
    if a is None:
        return 'page reference pending', False
    return (f'page {a}' if b in (None, a) else f'pages {a}–{b}'), True


class RegisterPointer(Flowable):
    """'Full register in Appendix D, pages x-y' with an internal link. Pages come
    from register_anchor() flowables (resolved by multiBuild on the next pass)."""

    def __init__(self, register_id, rows=None, title=None, where='Appendix D'):
        super().__init__()
        self.rid, self.rows, self.title, self.where = register_id, rows, title, where

    def _table(self, aw):
        start, end = f'reg:{self.rid}:start', f'reg:{self.rid}:end'
        rows = (fmt_value(self.rows, 'rows') if not is_missing(self.rows) else missing_text(self.rows)
                ) if self.rows is not None else 'row count not recorded'
        label, ok = _pages_label(_doc(self), start, end)
        where = f'{esc(self.where)}, {esc(label)}'
        if ok:   # link only to an existing destination (unresolved targets break the PDF)
            where = f'<a href="#{esc(start)}" color="{hexstr(T.NAVY)}">{where}</a>'
        text = f'<b>Full register</b>  {esc(self.title or self.rid)}  ·  {esc(rows)}  ·  {where}'
        t = Table([[M(text, 'pointer')]], colWidths=[aw], hAlign='LEFT')
        t.setStyle(TableStyle([
            ('LINEBEFORE', (0, 0), (0, 0), 2, T.SAPPHIRE),
            ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        return t

    def wrap(self, aw, ah):
        self._t = self._table(aw)
        self.width, self.height = self._t.wrapOn(self.canv, aw, ah)
        return self.width, self.height

    def draw(self):
        doc = _doc(self)
        if doc is not None and hasattr(doc, 'refs'):
            doc.refs.add(f'reg:{self.rid}:start')
        self._t.drawOn(self.canv, 0, 0)

    def getSpaceAfter(self):
        return T.SP_MD

    def getSpaceBefore(self):
        return 4


def register_pointer(register_id, rows=None, title=None, where='Appendix D'):
    return RegisterPointer(register_id, rows, title, where)


def register_anchor(register_id, edge='start'):
    """Place before ('start') and after ('end') the register in the appendix."""
    return Anchor(f'reg:{register_id}:{edge}')


# --- contents -----------------------------------------------------------------
class Contents(Flowable):
    """Numbered contents (template design). rows: ('group', label) or
    ('entry', number, title, sub_or_None, anchor_key). Pages resolve on pass 2."""

    def __init__(self, rows):
        super().__init__()
        self.rows = rows

    def _table(self, aw):
        prev = getattr(_doc(self), 'anchors_prev', {}) or {}
        data, cmds = [], [('VALIGN', (0, 0), (-1, -1), 'TOP'),
                          ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]
        for row in self.rows:
            i = len(data)
            if row[0] == 'group':
                data.append([P(row[1], 'toc_group'), '', ''])
                cmds += [('SPAN', (0, i), (-1, i)), ('LINEBELOW', (0, i), (-1, i), 0.75, T.RULE),
                         ('TOPPADDING', (0, i), (-1, i), 0 if i == 0 else 20),
                         ('BOTTOMPADDING', (0, i), (-1, i), 7)]
                continue
            _, num, title, sub, key = row
            page = prev.get(key)
            link = f'<a href="#{esc(key)}">' if page else ''
            end = '</a>' if page else ''
            cell = [M(f'{link}{esc(title)}{end}', 'toc_title')] + ([P(sub, 'toc_sub')] if sub else [])
            data.append([M(f'{link}{esc(num)}{end}', 'toc_num'), cell,
                         M(f'{link}{page}{end}' if page else '[p.]', 'toc_page')])
            cmds += [('TOPPADDING', (0, i), (-1, i), 5.5), ('BOTTOMPADDING', (0, i), (-1, i), 5.5)]
        t = Table(data, colWidths=[28, aw - 28 - 44, 44], splitInRow=0, hAlign='LEFT')
        t.setStyle(TableStyle(cmds))
        return t

    def wrap(self, aw, ah):
        self._t = self._table(aw)
        self.width, self.height = self._t.wrapOn(self.canv, aw, ah)
        return self.width, self.height

    def split(self, aw, ah):
        return self._table(aw).split(aw, ah)

    def draw(self):
        self._t.drawOn(self.canv, 0, 0)
