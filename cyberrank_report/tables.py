"""Compact tables and key/value lists (21 pt rows, 18 pt dense, hairlines only)."""
import itertools
from collections import Counter

from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, FrameBreak, Paragraph, Table, TableStyle

from . import qa, theme as T
from .icons import SeverityIcon
from .text import (M, P, TechText, _is_technical, esc, fmt_value, hexstr, is_missing, missing_text, reason_text,
                   sentence)

_TABLE_HEADS = {}          # ident -> header texts, used by qa header-repeat check
_TABLE_IDS = itertools.count(1)


CAPTION_H = 22.0           # continuation caption block above the repeated header
_CAP_TITLE = T.STYLES['h3c'].clone('cap_title', spaceBefore=0, spaceAfter=0, keepWithNext=0)
_CAP_META = T.STYLES['note_flush'].clone('cap_meta', alignment=TA_RIGHT)


def _rows_range(rowno):
    """'Rows a–b' over the data rows of one part (None entries: header / group / note rows)."""
    nums = [n for n in rowno if n is not None]
    return (nums[0], nums[-1]) if nums else (None, None)


class CompactTable(Table):
    """Table that records which page each (split) part lands on, for QA, and opens every
    continuation part with a caption block: '<title> · continued' on the left, 'Rows a–b
    of N' (+ the open group) on the right, a 0.75 pt heading rule under it, then the
    repeated header (tools/prototypes/continued_table.py).

    rowno: per row, the data-row ordinal (1-based) or None (header, group label, note).
    rowgrp: per row, the group label the row belongs to (registers), else None.
    title: caption title; None -> the last heading drawn before the table's first part.
    RL's split rebuilds parts via self.__class__(...), so this state is copied onto them."""
    rowno = rowgrp = None
    continued = False
    meta = None                # shared by all parts: {'title': str|None, 'total': int}

    def _cap(self):
        return CAPTION_H if self.continued and self.rowno else 0

    def wrap(self, aw, ah):
        w, h = super().wrap(aw, ah - self._cap())
        return w, h + self._cap()

    MIN_TAIL = 3       # a continuation part never carries fewer data rows than this (near-empty spill)

    def _tail_rows(self, parts):
        return sum(1 for n in self.rowno[len(self.rowno) - (len(parts[1]._cellvalues) - self.repeatRows):]
                   if n is not None)

    def _splitRows(self, availHeight, doInRowSplit=False):
        """RL's in-row split ignores NOSPLIT: refuse it when the row it would cut is inside a NOSPLIT
        range, so the table moves on instead (a short row never breaks across pages)."""
        if doInRowSplit and self._nosplitCmds:
            h, n = 0, 0
            for rh in self._rowHeights:
                if h + rh > availHeight:
                    break
                h, n = h + rh, n + 1
            nrows = len(self._rowHeights)
            for _, (_, r0), (_, r1) in self._nosplitCmds:
                if r0 % nrows <= n <= r1 % nrows:
                    return []
        return super()._splitRows(availHeight, doInRowSplit)

    def split(self, aw, ah):
        parts, moved = super().split(aw, ah - self._cap()), False
        if len(parts) == 2 and self.rowno:
            # move rows over until the continuation holds MIN_TAIL data rows, while the first
            # part keeps at least 2 (a lone stray row on either side reads as a spill)
            total = sum(1 for n in self.rowno if n is not None)
            room, moved = ah - self._cap(), False
            while 0 < self._tail_rows(parts) < self.MIN_TAIL and total - self._tail_rows(parts) > 2:
                room -= parts[0]._argH[-1] or 0
                retry = super().split(aw, room)
                if len(retry) != 2 or total - self._tail_rows(retry) < 2:
                    break
                parts = retry
                moved = True
        if len(parts) == 2 and self.rowno:
            head, tail = parts
            r, n = self.repeatRows, len(tail._cellvalues) - self.repeatRows   # in-row split: count from the end
            for attr in ('rowno', 'rowgrp'):
                v = getattr(self, attr) or [None] * len(self._cellvalues)
                setattr(head, attr, v[:len(head._cellvalues)])
                setattr(tail, attr, v[:r] + v[len(v) - n:])
            head.meta = tail.meta = self.meta
            head.continued, tail.continued = self.continued, True
            if moved:      # the shortened first part must not pull the rest up into this frame
                return [head, FrameBreak(), tail]
        return parts

    def draw(self):
        doc = getattr(self.canv, '_doctemplate', None)
        if doc is not None and hasattr(doc, 'table_parts'):
            doc.table_parts.append((self.ident, self.canv.getPageNumber()))
        if self.meta is not None and not self.meta.get('title') and not self.continued:
            self.meta['title'] = getattr(doc, 'last_heading', None)
        super().draw()
        if self._cap():
            self._draw_caption()

    def _draw_caption(self):
        meta = self.meta or {}
        title = esc(meta.get('title') or 'Table')
        a, b = _rows_range(self.rowno[self.repeatRows:])
        rng = f'Rows {a:,}–{b:,} of {meta.get("total", b):,}' if a else ''
        grp = next((g for g in (self.rowgrp or [])[self.repeatRows:self.repeatRows + 1] if g), None)
        if grp:
            rng += f'  ·  {esc(grp)} (cont.)'
        left = M(f'{title} <font name="{T.LIGHT}" color="{hexstr(T.MUTED)}">· continued</font>', _CAP_TITLE)
        right = M(rng, _CAP_META)
        y = self._height
        right.wrap(self._width, CAPTION_H)
        rw = stringWidth(right.getPlainText(), _CAP_META.fontName, _CAP_META.fontSize) + 8
        left.wrap(max(self._width - rw, 60), CAPTION_H)
        left.drawOn(self.canv, 0, y + 6)
        right.drawOn(self.canv, 0, y + 7)
        c = self.canv
        c.saveState()
        c.setStrokeColor(T.HEADING)
        c.setLineWidth(0.75)
        c.line(0, y + 2, self._width, y + 2)
        c.restoreState()


def numbered(t, rowno, title=None, rowgrp=None):
    """Arm a CompactTable for continuation captions (see CompactTable)."""
    t.rowno, t.rowgrp = rowno, rowgrp
    t.meta = {'title': title, 'total': sum(1 for n in rowno if n is not None)}
    return t


def _plain(v):
    if isinstance(v, Flowable):
        return getattr(v, 'text', '') or ''
    if isinstance(v, list):
        return ' '.join(_plain(x) for x in v)
    return missing_text(v) if is_missing(v) else fmt_value(v) if isinstance(v, dict) else str(v)


def _font_of(v, fs):
    """(font, size) a cell's text is set in: technical tokens (TechText, auto-detected strings) are mono."""
    if isinstance(v, TechText):
        return v.style.fontName, v.style.fontSize
    if isinstance(v, str) and _is_technical(v):
        return T.MONO, round(fs * T.MONO_K, 2)
    return T.LIGHT, fs


def _auto_widths(columns, rows, dense, total=None):
    fs = 7.8 if dense else 8.6
    pad = 2 * T.CELL_PAD_H
    nat, mins = [], []
    for j, col in enumerate(columns):
        texts = [_plain(r[j]) for r in rows] if rows else []
        col = _plain(col)
        nat.append(max([stringWidth(str(col), T.MEDIUM, fs)] +
                       [stringWidth(t, *_font_of(r[j], fs)) for t, r in zip(texts, rows)]) + pad)
        cap = 0.45 * (total or T.CW)        # longer tokens may break at / . - _ @
        mins.append(min(cap, max([stringWidth(w, *_font_of(r[j], fs)) for t, r in zip(texts, rows) for w in t.split()] +
                                 [stringWidth(w, T.MEDIUM, fs) for w in str(col).split()] + [12]) + pad))
        for r in rows:
            if isinstance(r[j], Flowable) and hasattr(r[j], 'minWidth'):
                mins[j] = max(mins[j], r[j].minWidth() + pad)
                nat[j] = max(nat[j], mins[j])
    if total is None:
        total = T.COL2 if len(columns) <= 2 and sum(nat) <= T.COL2 else T.CW
    # keep each header on one line when the table can afford it
    head_mins = [max(m, stringWidth(_plain(c), T.MEDIUM, fs) + pad) for m, c in zip(mins, columns)]
    if sum(head_mins) <= total:
        mins = head_mins
        nat = [max(n, m) for n, m in zip(nat, mins)]
    if sum(nat) <= total:
        extra = total - sum(nat)
        return [n + extra * n / sum(nat) for n in nat]
    if sum(mins) >= total:
        return [m * total / sum(mins) for m in mins]
    flex = [n - m for n, m in zip(nat, mins)]
    room = total - sum(mins)
    return [m + room * f / sum(flex) for m, f in zip(mins, flex)]


def head_width(text, dense=False):
    """Column width that holds a header word on one line (icon-only columns: the header sets the width)."""
    return stringWidth(str(text), T.MEDIUM, 7.8 if dense else 8.6) + 2 * T.CELL_PAD_H + 1


def table_cell(v, dense=False, numeric=False, marks=None):
    """Flowable for one cell: Flowable passthrough, missing -> reason, numbers right.
    marks (dict reason -> n): print 'Not available' + superscript n instead of the
    full reason; the caller prints footnote(marks) once under the table."""
    base = 'dense' if dense else 'cell'
    if isinstance(v, Flowable) or isinstance(v, list) and v and all(isinstance(x, Flowable) for x in v):
        return v
    if is_missing(v):
        align = {'alignment': TA_RIGHT} if numeric else {}
        if marks is not None:
            n = marks.setdefault(sentence(reason_text(v)), len(marks) + 1)
            return M(f'Not available<super>{n}</super>', base + '_muted', **align)
        return P(missing_text(v), base + '_muted', **align)
    s = fmt_value(v) if isinstance(v, (dict, int, float)) and not isinstance(v, bool) else str(v)
    if numeric:
        return P(s, base + '_num')
    if _is_technical(s):
        return TechText(s, base + '_tech')
    return P(s, base)


def footnote(marks):
    """'1 reason. 2 reason.' paragraph for the markers table_cell(marks=...) printed."""
    return M('<br/>'.join(f'<super>{n}</super> {esc(r)}' for r, n in marks.items()), 'note_flush')


def _note_row(data, cmds, marks, ncols):
    """Footnotes ride in a spanning tail row (no hairline), kept with the last data row."""
    data.append([footnote(marks)] + [''] * (ncols - 1))
    cmds[:] = [(c[0], c[1], (c[2][0], -2), *c[3:]) if c[0] == 'LINEBELOW' and c[2][1] == -1 else c
               for c in cmds]
    cmds += [('SPAN', (0, -1), (-1, -1)), ('NOSPLIT', (0, -2), (-1, -1)), ('TOPPADDING', (0, -1), (-1, -1), 5)]


def _row_h(row, widths):
    """Natural height of one body row (cells are Flowables or lists of Flowables)."""
    def h(c, w):
        if isinstance(c, list):
            return sum(h(x, w) for x in c)
        return c.wrap(w - 2 * T.CELL_PAD_H, T.FRAME_H)[1] if hasattr(c, 'wrap') else 0
    return max((h(c, w) for c, w in zip(row, widths)), default=0)


def compact_table(columns, rows, widths=None, dense=False, numeric_cols=(), *, header_fill=True,
                  total_width=None, title=None):
    """Compact data table: 21 pt single-line rows (18 pt dense), hairlines only,
    header repeats on continuation pages (under a '<title> · continued / Rows a–b of N'
    caption; title defaults to the last heading); a row splits only when taller than KEEP_MAX_H.
    Null cells in columns narrower than NARROW_COL print 'Not available' + a
    superscript; each distinct reason is printed once under the table."""
    base = 'dense' if dense else 'cell'
    pad_v = T.DENSE_PAD_V if dense else T.CELL_PAD_V
    widths = list(widths) if widths else _auto_widths(columns, rows, dense, total_width)
    head = [c if isinstance(c, Flowable) else P(c, base + '_head' + ('_num' if j in numeric_cols else ''))
            for j, c in enumerate(columns)]
    marks = {}
    body = [[table_cell(v, dense, j in numeric_cols, marks if widths[j] < T.NARROW_COL else None)
             for j, v in enumerate(r)] for r in rows]
    for r in body:
        for j, c in enumerate(r):
            qa.check_min_width(c, widths[j] - 2 * T.CELL_PAD_H, f'table column "{_plain(columns[j])}"')
    ident = f'tbl{next(_TABLE_IDS)}'
    _TABLE_HEADS[ident] = [_plain(c) for c in columns]
    data = [head] + body
    cmds = [('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), T.CELL_PAD_H), ('RIGHTPADDING', (0, 0), (-1, -1), T.CELL_PAD_H),
            ('TOPPADDING', (0, 0), (-1, -1), pad_v), ('BOTTOMPADDING', (0, 0), (-1, -1), pad_v),
            ('LINEBELOW', (0, 1), (-1, -1), T.HAIRLINE, T.RULE)]
    cmds += ([('BACKGROUND', (0, 0), (-1, 0), T.SURFACE)] if header_fill
             else [('LINEBELOW', (0, 0), (-1, 0), 0.75, T.HEADING)])
    # a data row never splits across pages unless it is taller than KEEP_MAX_H (then it must)
    cmds += [('NOSPLIT', (0, i), (-1, i)) for i, r in enumerate(body, 1)
             if _row_h(r, widths) + 2 * pad_v < T.KEEP_MAX_H]
    if marks:
        _note_row(data, cmds, marks, len(columns))
    t = CompactTable(data, colWidths=widths, repeatRows=1, splitInRow=1, ident=ident, hAlign='LEFT')
    t.setStyle(TableStyle(cmds))
    center_severity(t)
    return numbered(t, [None] + list(range(1, len(body) + 1)) + [None] * (len(data) - 1 - len(body)), title)


SEVERITY_HEADS = ('Severity', 'Priority', 'Risk', 'Highest severity', 'Max severity')


def _centred(p):
    return Paragraph(p.text, p.style.clone(p.style.name + '_c', alignment=TA_CENTER)) if isinstance(p, Paragraph) else p


def center_severity(t):
    """Severity column (header in SEVERITY_HEADS or any body cell an icon-only siren): the siren and its invisible word are centred in
    the column, the header and any visible word (Informational, Not recorded) too. Every severity table
    puts this column right after its # / ID column."""
    rows = t._cellvalues
    for j in range(len(rows[0])):
        if _plain(rows[0][j]) in SEVERITY_HEADS or any(isinstance(r[j], SeverityIcon) for r in rows[1:]):
            for r in rows:
                r[j] = _centred(r[j])
            t.setStyle(TableStyle([('ALIGN', (j, 0), (j, -1), 'CENTER')]))
    return t


def key_value_list(pairs, width=None, label_width=None, dense=False):
    """Label / value rows with hairlines. Values: scalar, null record, or Flowable.
    Full-width lists always use the kit label column (KV_LABEL_W) so values line up
    across pages; label_width applies only to narrower (COL2 / boxed) lists. A null
    reason shared by several rows prints once, as a trailing note."""
    width = width or T.CW
    fs = 7.8 if dense else 8.6
    if width >= T.CW - 0.5:
        lw = T.KV_LABEL_W
    else:
        lw = label_width or min(max(stringWidth(str(k), T.LIGHT, fs) for k, _ in pairs) + 2 * T.CELL_PAD_H,
                                0.38 * width)
    why = lambda v: sentence(reason_text(v)) if not isinstance(v, Flowable) and is_missing(v) else None
    repeated = {r for r, n in Counter(why(v) for _, v in pairs).items() if r and n > 1}
    marks = {}
    data = [[P(k, 'kv_label' if not dense else 'dense_muted'),
             table_cell(v, dense, marks=marks if why(v) in repeated else None)] for k, v in pairs]
    for _, c in data:
        qa.check_min_width(c, width - lw - 2 * T.CELL_PAD_H, 'key/value value')
    pad_v = T.DENSE_PAD_V if dense else T.CELL_PAD_V
    cmds = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('LEFTPADDING', (1, 0), (1, -1), T.CELL_PAD_H),
        ('RIGHTPADDING', (0, 0), (-1, -1), T.CELL_PAD_H),
        ('TOPPADDING', (0, 0), (-1, -1), pad_v), ('BOTTOMPADDING', (0, 0), (-1, -1), pad_v),
        ('LINEBELOW', (0, 0), (-1, -1), T.HAIRLINE, T.RULE),
        ('LINEABOVE', (0, 0), (-1, 0), T.HAIRLINE, T.RULE),
    ]
    if marks:
        _note_row(data, cmds, marks, 2)
        cmds.append(('LEFTPADDING', (0, -1), (-1, -1), 0))
    t = CompactTable(data, colWidths=[lw, width - lw], splitInRow=1, hAlign='LEFT')
    t.setStyle(TableStyle(cmds))
    return numbered(t, list(range(1, len(pairs) + 1)) + [None] * (len(data) - len(pairs)))
