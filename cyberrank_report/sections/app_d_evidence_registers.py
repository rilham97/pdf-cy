"""Appendix D -- Detailed evidence registers (+ long-list policy access for s05 / s11).

Opens with an index (one linked row per register D.1..D.6, numbered in section order from the
registry -- see RID; absent registers are index rows only), then each present register: opening block, dense table (header + caption
row repeat on every page, caption says '(continued)' and names the open group), and an
end line that reconciles with the section overview. Thresholds, titles and message
templates come from long_list_policy.json at runtime (CYBERRANK_LONG_LIST_POLICY or
../long-list-rules/long_list_policy.json); built-in defaults apply when it is absent.
"""
import ipaddress
import json
import os
import re
from functools import cache
from pathlib import Path

from reportlab.lib.colors import white
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Image, KeepInFrame, PageBreak, Table, TableStyle

from .. import components as C
from .. import qa
from .. import icons as I
from .. import theme as T
from ..tables import _auto_widths
from ..fonts import report_missing
from ..text import tech_lines
from . import BY_ID, REGISTRY

_POLICY_FILES = [os.environ.get('CYBERRANK_LONG_LIST_POLICY'),
                 Path(__file__).resolve().parents[3] / 'long-list-rules' / 'long_list_policy.json']
_DEFAULTS = {   # used only when the policy file is missing (policy: inline <= 30 rows)
    'tiers': {'T1_inline': {'max_visual_rows': 30}, 'T2_overview_register': {'max_rows': 1000},
              'top_n_default': 10, 'T3_overview_file': {'appendix_sample_rows': 100}},
}
TEXT_ROW_LINES = 12      # text-cell registers: lines per table row before a tall row continues in a new one
REG_SECS = ('s04', 's05', 's06', 's11', 's13', 's14')      # sections with an Appendix D register slot
SEC_NUM = {s: BY_ID[s].number for s in REG_SECS}
# register ids follow the section order of the registry (user decision 2026-10-15): D.1 = first section
# with a register, ... An absent register keeps its slot (index row only), so ids never shift per report.
_ORDER = [s.id for s in REGISTRY]
RID = {s: f'D.{i}' for i, s in enumerate(sorted(REG_SECS, key=_ORDER.index), 1)}
ZERO = T.STYLES['dense_num'].clone('reg_zero', textColor=T.MUTED)
# Lead-ins carry no spaceAfter (the gap moves to the next item's spaceBefore): the kit's
# Keep.split sizes the first table part with _listWrapOn, which ignores spaceAfter, so a
# lead-in with spaceAfter makes the first part too tall and leaves a 1-row stub overleaf.
H2T = T.STYLES['h2'].clone('h2_tight', spaceAfter=0)
H3T = T.STYLES['h3'].clone('h3_tight', spaceAfter=0)
# end-of-register lines carry labels and counts ('Moderate 0'): never hyphenated
END_NOTE = T.STYLES['note'].clone('note_end', **T._NO_HY)


def intro(text, style='body'):
    return C.P(text, style, spaceBefore=4, spaceAfter=0, keepWithNext=1)


def gap(flowable, before=6):
    flowable.spaceBefore = before
    return flowable


@cache
def policy():
    for p in _POLICY_FILES:
        if p and Path(p).is_file():
            return json.loads(Path(p).read_text(encoding='utf-8'))
    return _DEFAULTS


def pol(path, default=None):
    """Value at a dotted path in the policy, else default."""
    v = policy()
    for k in path.split('.'):
        if not isinstance(v, dict) or k not in v:
            return default
        v = v[k]
    return v


def t1_max(list_key=None):
    """Inline maximum: lists.<list_key>.tier_thresholds.T1_max_visual_rows, else the global tier."""
    return pol(f'lists.{list_key}.tier_thresholds.T1_max_visual_rows') or pol('tiers.T1_inline.max_visual_rows', 30)


def tier(visual_rows, data_rows, identity=False, list_key=None):
    """'T1' inline / 'T2' overview + register / 'T3' overview + data file. list_key: the list's own
    tier_thresholds in the policy win over the global tiers."""
    t2 = pol(f'lists.{list_key}.tier_thresholds.T2_max_rows') or pol('tiers.T2_overview_register.max_rows', 1000)
    if identity or data_rows > t2:
        return 'T3'
    return 'T1' if visual_rows <= t1_max(list_key) else 'T2'


def fill(tpl, **kw):
    """Policy template: '{key}' and "{key|'default'}" placeholders; keys may contain '-'."""
    def sub(m):
        v = kw.get(m.group(1))
        return str(v if v not in (None, '') else (m.group(2) or ''))
    return re.sub(r"\{([\w-]+)(?:\|'([^']*)')?\}", sub, tpl)


def signed(n):
    return ('+' if n > 0 else '−' if n < 0 else '±') + C.fmt_number(abs(n))


def lookup(report, ref):
    """Resolve a dotted payload reference such as 'appendices.d_evidence_registers.x'."""
    v = report
    for part in str(ref or '').split('.'):
        v = v.get(part) if isinstance(v, dict) else None
    return v


def assessment_year(report):
    raw = ((report.get('snapshot') or {}).get('assessed_at') or {})
    raw = raw.get('value') if isinstance(raw, dict) else raw
    return int(str(raw)[:4]) if raw else None


def long_list_card(data, ctx, clear_text):
    """state_card kwargs shared by long-list sections (policy states.overview_messages)."""
    msgs = pol('states.overview_messages', {}) or {}
    reason = data.get('state_reason') or (C.reason_text(data) if data.get('reason_code') else None)
    if ctx.state == 'clear':
        return {'reason': reason or clear_text}
    if ctx.state == 'unavailable':
        return {'reason': C.sentence(reason or C.STATE_REASON_FALLBACK) + ' This is not a zero result.'}
    if ctx.state == 'partial':
        return {'reason': C.sentence(reason or C.STATE_REASON_FALLBACK) + ' Counts below are lower bounds.'}
    if ctx.state == 'pending_review':
        return {'reason': reason or msgs.get('pending_review_banner')}
    return {}


# --- page references (resolved on the next multiBuild pass) -------------------
class Lazy(Flowable):
    """Builds its flowable at wrap time from doc.anchors_prev (key -> page)."""

    def __init__(self, make):
        super().__init__()
        self.make = make

    def _build(self):
        doc = getattr(getattr(self, 'canv', None), '_doctemplate', None)
        return self.make(getattr(doc, 'anchors_prev', None) or {})

    def wrap(self, aw, ah):
        self._f = self._build()
        self.width, self.height = self._f.wrapOn(self.canv, aw, ah)
        return self.width, self.height

    def split(self, aw, ah):
        return self._build().splitOn(self.canv, aw, ah)

    def draw(self):
        self._f.drawOn(self.canv, 0, 0)

    def getSpaceAfter(self):
        return self._f.getSpaceAfter() if hasattr(self, '_f') else 0


def page_link(prev, key, text):
    """'text, p. n' linked to key when the key resolved on the previous pass."""
    p = prev.get(key)
    if p is None:
        return C.esc(text)
    return f'<a href="#{C.esc(key)}" color="{C.hexstr(T.NAVY)}">{C.esc(text)}, p. {p}</a>'


def pages_link(prev, rid, fallback):
    a, b = prev.get(f'reg:{rid}:start'), prev.get(f'reg:{rid}:end')
    if a is None:
        return C.esc(fallback)
    label = f'p. {a}' if b in (None, a) else f'pp. {a}–{b}'
    return f'<a href="#reg:{C.esc(rid)}:start" color="{C.hexstr(T.NAVY)}">{label}</a>'


# ponytail: payload section titles of the report being built (set by build()); opening() has no report
TITLES = {}


def backlink(sec_id):
    spec = BY_ID.get(sec_id)
    title = TITLES.get(sec_id) or spec.title
    return Lazy(lambda prev: C.M('Back to ' + page_link(prev, spec.anchor, f'Section {spec.number} {title}'),
                                 'note_flush', keepWithNext=1))


# --- dense register table -------------------------------------------------------
def num(v, dense=True):
    """Right-aligned count; zero muted; missing prints its reason."""
    if C.is_missing(v):
        return C.table_cell(v, dense, numeric=True)
    return C.P(C.fmt_number(v), ZERO if v == 0 else 'dense_num' if dense else 'cell_num')


def _constant(columns, rows, numeric_cols):
    """Columns (not '#', not counts) holding one identical value in every row."""
    if len(rows) < 2:
        return []
    plain = lambda v: v if isinstance(v, str) else None
    return [j for j, c in enumerate(columns) if c != '#' and j not in numeric_cols
            and plain(rows[0][j]) and all(plain(r[j]) == rows[0][j] for r in rows)]


def register_table(columns, entries, *, title, sec_id, numeric_cols=(), widths=None, dense=True, ident,
                   ordinals=None, text_cells=False, tech_cols=()):
    """entries: ('row', [cells]) or ('group', flowable, label). Cells: plain values or
    flowables. Group rows span all columns and stay with their first two rows. A part that
    continues on a new page opens with '<title> · continued / Rows a–b of N (· group (cont.))'
    (CompactTable). Constant text columns collapse into t.const_note ('Col: value (all rows)').
    ordinals: per data row, the number its '#' cell shows (None: not counted, e.g. the apex
    aggregate), so 'Rows a–b of N' matches the printed numbers.
    text_cells: body cells are plain strings pre-wrapped at technical break points (tech_lines), not
    Paragraphs -- the only way a register of thousands of rows (credential register) splits over pages in reasonable time.
    tech_cols: columns of technical tokens (hosts, account labels): JetBrains Mono (`*_tech` style)."""
    base = 'dense' if dense else 'cell'
    pad_v = T.DENSE_PAD_V if dense else T.CELL_PAD_V
    data_rows = [e[1] for e in entries if e[0] == 'row']
    drop = _constant(columns, data_rows, numeric_cols)
    const_note = ' · '.join(f'{columns[j]}: {data_rows[0][j]} (all rows)' for j in drop)
    if drop:
        keep = [j for j in range(len(columns)) if j not in drop]
        if widths:
            extra = sum(widths[j] for j in drop)
            sev = {j for j in keep if any(isinstance(r[j], I.SeverityIcon) for r in data_rows)}
            wide = next(j for j in keep[1:] + keep if j not in sev)   # first text column after '#' absorbs it
            widths = [widths[j] + (extra if j == wide else 0) for j in keep]
        columns = [columns[j] for j in keep]
        numeric_cols = tuple(k for k, j in enumerate(keep) if j in numeric_cols)
        tech_cols = tuple(k for k, j in enumerate(keep) if j in tech_cols)
        entries = [('row', [e[1][j] for j in keep]) if e[0] == 'row' else e for e in entries]
        data_rows = [e[1] for e in entries if e[0] == 'row']
    widths = widths or _auto_widths(columns, data_rows, dense, T.CW)
    head = [c if isinstance(c, Flowable) else C.P(c, base + '_head' + ('_num' if j in numeric_cols else ''))
            for j, c in enumerate(columns)]
    data, rowno, rowgrp, starts, current, n, joins = [head], [None], [None], [], None, 0, []
    for e in entries:
        if e[0] == 'group':
            starts.append(len(data))
            data.append([e[1]] + [''] * (len(columns) - 1))
            current = e[2]
            rowno.append(None)
            rowgrp.append(None)
            continue
        n += 1
        if text_cells:
            # a tall row goes in chunks of TEXT_ROW_LINES lines (the later chunks carry no '#' and no rule
            # above), so it can continue overleaf: RL's in-row split of string cells overflows the frame
            sts = [T.STYLES[base + ('_tech' if j in tech_cols else '')] for j in range(len(e[1]))]
            flow = [isinstance(v, Flowable) for v in e[1]]      # a one-line flowable (status icon) passes through
            lines = [[v] if f else tech_lines(C.missing_text(v) if C.is_missing(v) else str(v),
                                              widths[j] - 2 * T.CELL_PAD_H, sts[j].fontName, sts[j].fontSize)
                     for j, (v, f) in enumerate(zip(e[1], flow))]
            for x, st, f in zip(e[1], sts, flow):      # plain-string cells get no per-character fallback
                if not f:
                    report_missing(x, f'{title} (plain-text register cell)', st.fontName)
            for a in range(0, max(map(len, lines)), TEXT_ROW_LINES):
                if a:
                    joins.append(len(data))
                data.append([(x[0] if not a else '') if f else '\n'.join(x[a:a + TEXT_ROW_LINES])
                             for x, f in zip(lines, flow)])
                rowno.append(None if a else ordinals[n - 1] if ordinals else n)
                rowgrp.append(current)
            continue
        data.append([v if isinstance(v, Flowable) else num(v, dense) if j in numeric_cols
                     else C.tech(v, base + '_tech') if j in tech_cols and isinstance(v, str)
                     else C.table_cell(v, dense) for j, v in enumerate(e[1])])
        rowno.append(ordinals[n - 1] if ordinals else n)
        rowgrp.append(current)
    last = len(data) - 1
    cmds = [('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), T.CELL_PAD_H), ('RIGHTPADDING', (0, 0), (-1, -1), T.CELL_PAD_H),
            ('TOPPADDING', (0, 0), (-1, -1), pad_v), ('BOTTOMPADDING', (0, 0), (-1, -1), pad_v),
            ('VALIGN', (0, 0), (-1, 0), 'BOTTOM'),
            ('BACKGROUND', (0, 0), (-1, 0), T.SURFACE),
            ('LINEBELOW', (0, 1), (-1, -1), T.HAIRLINE, T.RULE)]
    for g in starts:   # a group label stays with its first two rows
        cmds += [('SPAN', (0, g), (-1, g)), ('LINEABOVE', (0, g), (-1, g), 0.75, T.SLATE_400),
                 ('NOSPLIT', (0, g), (-1, min(g + 2, last)))]
    for e in [g - 1 for g in starts[1:]] + [last]:   # and no page starts with one stray row
        if e - 1 >= 1:
            cmds.append(('NOSPLIT', (0, e - 1), (-1, e)))
    if text_cells:
        st = T.STYLES[base]
        cmds += [('FONT', (0, 1), (-1, -1), st.fontName, st.fontSize, st.leading),
                 ('TEXTCOLOR', (0, 1), (-1, -1), st.textColor)]
        mono = T.STYLES[base + '_tech']
        cmds += [('FONT', (j, 1), (j, -1), mono.fontName, mono.fontSize, mono.leading) for j in tech_cols]
        cmds += [('ALIGN', (j, 1), (j, -1), 'RIGHT') for j in numeric_cols]
        for r in joins:
            cmds += [('LINEBELOW', (0, r - 1), (-1, r - 1), T.HAIRLINE, white),
                     ('BOTTOMPADDING', (0, r - 1), (-1, r - 1), 0), ('TOPPADDING', (0, r), (-1, r), 0)]
    t = C.CompactTable(data, colWidths=widths, repeatRows=1, splitInRow=0 if text_cells else 1, ident=ident,
                       hAlign='LEFT')
    t.setStyle(TableStyle(cmds))
    C.center_severity(t)
    t.spaceBefore, t.const_note = 6, const_note
    C._TABLE_HEADS[ident] = [getattr(c, 'text', c) for c in columns if c]
    return C.numbered(t, rowno, title, rowgrp)


def const_line(t):
    """Note for the columns register_table collapsed (empty list when none)."""
    return [C.P(t.const_note + '.', 'note_flush', spaceBefore=4, keepWithNext=1)] if t.const_note else []


def group_row(left, right, width):
    """Spanning group label: left flowable + right flowable (chip / note)."""
    t = Table([[left, right]], colWidths=[width * 0.62, width * 0.38], hAlign='LEFT')
    t.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                           ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                           ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    return t


def opening(rid, title, sec_id, lines, key, legend=None):
    """Register opening block: anchors, H2, sort/showing sentence, unit/state/as-of line, backlink.
    legend: a severity legend set on the heading line (right)."""
    # heading first: _listWrapOn skips zero-height anchors before clearing atTop, so leading
    # anchors would hide the heading's spaceBefore from Keep's estimate
    h2 = C.heading(f'{rid}  {title}', 2, key=f'reg-{rid}', style=H2T)
    head = [C.heading_legend(h2, legend) if legend else h2, C.register_anchor(rid, 'start')]
    lines = [x for x in lines if x]        # owner 2026-10-21: only what the tables cannot say (no unit/state/as-of line)
    text = [intro(lines[0])] + [C.P(x, 'note_flush', keepWithNext=1) for x in lines[1:]] if lines else []
    head += [C.register_anchor(k, 'start') for k in key]
    head += text + [backlink(sec_id)]
    for f in head:
        f.keepWithNext = 1
    return head


def closing(rid, key, text, rows=None, unit='rows'):
    """End line: 'End of register · N rows', then the reconciliation text."""
    head = f'End of register · {C.fmt_number(rows)} {unit}. ' if rows is not None else ''
    text = re.sub(r'^End of [^—]*— ', '', text)      # the policy template repeats the register id
    text = (head + text[:1].upper() + text[1:]).strip()      # differences only; nothing when all is consistent
    # end anchors go just before the end line and travel with it: after it, on a full page, they would
    # open a blank page (the line's spaceAfter leaves no room even for a zero-height flowable)
    return [C.keep(*[C.register_anchor(k, 'end') for k in [rid, *key]], C.P(text, END_NOTE, spaceBefore=6))]


# --- registers --------------------------------------------------------------------
SEV_ORDER = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
HOSTLIKE = re.compile(r'^([a-z0-9-]+\.)+[a-z]{2,}( / [0-9a-f.:]+)?$|^[0-9.]+$', re.I)


def _hostlike(label):
    """A complete host name, 'host / IP', or a bare IPv4 / IPv6 address."""
    try:
        ipaddress.ip_address(label)
        return True
    except ValueError:
        return bool(HOSTLIKE.match(label))


def d1_register(report):
    """(anchor key, register, rows, title) of the D.1 affected-asset register; the Section 04 pointer reads
    the same rows and title."""
    sec = (report.get('sections') or {}).get('vulnerabilities') or {}
    key = str(sec.get('assets_register_ref') or '').rsplit('.', 1)[-1] or 'vulnerability_asset_register'
    reg = lookup(report, sec.get('assets_register_ref')) or {}
    rows = [r for r in reg.get('rows') or [] if isinstance(r, dict)]
    return key, reg, rows, pol('lists.vuln_affected_assets.register_title', 'Affected assets by finding')


def d1_assets(report, as_of):
    from .s04_vulnerabilities import _count
    sec = (report.get('sections') or {}).get('vulnerabilities') or {}
    key, reg, rows, title = d1_register(report)
    rid = RID['s04']
    info = {'rid': rid, 'state': reg.get('state') or sec.get('state'), 'sec': 's04', 'title': title}
    if not rows or tier(len(rows), len(rows)) == 'T1':      # <= 30 rows: Section 04 lists every asset
        return {**info, 'content': state_message(sec, SEC_NUM['s04'], 'affected assets', len(rows) or None)}
    lik = any('breach_likelihood' in r for r in rows)      # one likelihood per domain (Section 04 table)

    def pct(r):
        v = C.val(r.get('breach_likelihood'))
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    rows = sorted(rows, key=lambda r: ((pct(r) is None, -(pct(r) or 0)) if lik else ()) + (
        SEV_ORDER.get(str(r.get('max_severity')).lower(), 9), -(r.get('finding_count') or 0),
        str(r.get('asset_label_source'))))
    flagged = 0
    entries = []
    for i, r in enumerate(rows, 1):
        label = str(r.get('asset_label_source') or '')
        if label and not _hostlike(label):
            label, flagged = label + ' †', flagged + 1
        entries.append(('row', [str(i), C.severity_icon(r.get('max_severity'), dense=True),
                                label or {'value': None, 'reason_code': 'asset_not_extracted'},
                                ', '.join(r.get('finding_ids') or [])
                                or {'value': None, 'reason_code': 'not_printed_in_source'},
                                r.get('finding_count')]
                       + ([r.get('breach_likelihood') if r.get('breach_likelihood') is not None
                           else {'value': None, 'reason_code': 'not_printed_in_source'}] if lik else [])))
    members = sum(r.get('finding_count') or 0 for r in rows)
    src = [f for f in sec.get('findings') or [] if isinstance(f, dict)]
    sec_total = sum(_count(f) or 0 for f in src)      # same count as the Section 04 tables
    checks = [(f'source register memberships {C.fmt_number(reg["counts"]["memberships"])}',
               reg['counts']['memberships']) if (reg.get('counts') or {}).get('memberships') is not None else None,
              (f'Section {SEC_NUM["s04"]} affected-asset counts {C.fmt_number(sec_total)}', sec_total) if src else None]
    rec = '; '.join(f'{t} ({"matches" if v == members else "difference " + signed(members - v)})'
                    for t, v in filter(None, checks))
    flow = opening(rid, title, 's04', [
        f'One row per affected asset, sorted by {"breach likelihood, then " if lik else ""}highest severity, '
        f'then number of findings, then name.'], [key],
        legend=C.severity_legend([(k, [str(r.get('max_severity') or '').lower() for r in rows].count(k))
                                  for k in SEV_ORDER]))
    sev_w = max([C.head_width('Highest severity', dense=True)] +
                [e[1][1].minWidth() + 2 * T.CELL_PAD_H + 1 for e in entries if not isinstance(e[1][1], I.SeverityIcon)])
    asset_w = max([150] + [stringWidth(str(e[1][2]), T.MONO, T.STYLES['dense_tech'].fontSize) + 2 * T.CELL_PAD_H + 1
                           for e in entries if isinstance(e[1][2], str)])
    lw = 74 if lik else 0
    t = register_table(['#', 'Highest severity', 'Affected asset', 'Finding IDs', 'Findings']
                       + (['Breach likelihood'] if lik else []), entries,
                       title=f'{rid} {title}', sec_id='s04', numeric_cols=(0, 4, 5) if lik else (0, 4), ident='regD1',
                       widths=[26, sev_w, min(asset_w, 180 if lik else 200),
                               T.CW - 26 - min(asset_w, 180 if lik else 200) - 74 - sev_w - lw, 74] + ([lw] if lik else []),
                       tech_cols=(2,))
    flow += const_line(t) + [t]
    if flagged:
        flow.append(C.note(f'† {pol("register_defaults.invalid_value_marker.note", "value as provided by source")}'
                           f' ({flagged} labels are not complete host names).'))
    diff = '; '.join(x for x in rec.split('; ') if 'difference' in x) if rec else ''
    flow += closing(rid, [key], f'Finding memberships {C.fmt_number(members)}: {diff}.' if diff else '',
                    rows=len(rows))
    info.update(flow=flow, content=f'{len(rows)} of {len(rows)} affected assets')
    return info


def d12_ip(report, as_of):
    """<D.1>.2: every IP reputation row when the list is over the inline limit; Section 04 then shows the top
    rows in the same order (s04.ip_order) and points here."""
    from . import s04_vulnerabilities as s04
    ipr = ((report.get('sections') or {}).get('vulnerabilities') or {}).get('ip_reputation')
    rid, title = f'{RID["s04"]}.2', pol('lists.ip_reputation.register_title', 'IP reputation')
    info = {'rid': rid, 'title': title, 'sec': 's04', 'anchor': 's04-ip-reputation',
            'state': ipr.get('state') if isinstance(ipr, dict) else 'unavailable'}
    if not isinstance(ipr, dict):
        return {**info, 'content': 'Not produced — IP reputation is not in the payload.'}
    rows = s04.ip_order(ipr.get('rows') or [])
    if not rows or tier(len(rows), len(rows)) == 'T1' or (ipr.get('state') or 'findings') not in s04.FULL:
        return {**info, 'content': state_message(ipr, SEC_NUM['s04'], 'IP addresses', len(rows) or None)}
    n = len(rows)
    flow = opening(rid, title, 's04', [
        'One row per IP address, sorted by abuse score, highest first; scores held for review and blanks last.'], [])

    def cell(v, numeric):
        if isinstance(v, dict) and v.get('reason_code') == 'sentinel_meaning_unconfirmed':   # policy: label + caveat
            return C.P(f'{v.get("source_label") or "-1"} (meaning unconfirmed)', 'dense_num' if numeric else 'dense')
        return v if v is not None else {'value': None, 'reason_code': 'not_printed_in_source'}

    entries = [('row', [str(i), C.val(r.get('ip_address')) or {'value': None, 'reason_code': 'not_printed_in_source'},
                        *(cell(r.get(c), c in ('abuse_score', 'reports'))
                          for c in ('isp', 'country', 'abuse_score', 'reports'))])
               for i, r in enumerate(rows, 1)]
    t = register_table(['#', 'IP address', 'ISP', 'Country', 'Abuse score', 'Reports'], entries,
                       title=f'{rid} {title}', sec_id='s04', numeric_cols=(0, 4, 5), ident='regD12', tech_cols=(1,))
    flow += const_line(t) + [t]
    flow += closing(rid, [], '', rows=n)
    info.update(flow=flow, content=f'{n} of {n} IP addresses')
    return info


def d23_domains(s05, d, sec, rid):
    """<D.n>.3: every affected domain (rows, rows with a password, latest year) when the rows carry one;
    otherwise the episode/source message."""
    if not d['domains']:
        return [C.heading(f'{rid}.3  Exposure episodes and sources', 3, style=H3T), C.P(s05.episodes_text(sec), 'body')]
    keys = s05.domain_order(d)
    if sum(1 for k in keys if k) <= s05.INLINE_DOMAINS:      # Section 05 shows every domain: no second copy
        return [C.heading(f'{rid}.3  Rows by affected domain', 3, style=H3T),
                C.P(f'All {C.fmt_number(len(keys))} domains are listed in Section {SEC_NUM["s05"]}.', 'body')]
    res = bool(d['resolved'])
    entries = [('row', [str(i), *s05.domain_row(k or 'Domain not given', d['domains'][k], plain=not k, dense=True,
                                                res=res)])
               for i, k in enumerate(keys, 1)]
    cols, n = s05.domain_cols(res), len(s05.domain_cols(res)) - 1
    t = register_table(['#', *cols], entries, title=f'{rid}.3 Rows by affected domain', sec_id='s05',
                       numeric_cols=(0, *range(2, n + 2)), ident='regD43',
                       widths=[28, T.CW - 28 - n * s05.CROSS_WN] + [s05.CROSS_WN] * n)
    return [C.heading(f'{rid}.3  Rows by affected domain', 3, style=H3T), *const_line(t), t]


def d24_mailboxes(s05, d, rid):
    """<D.n>.4: every account email domain (mailbox provider) by name: the assessed domain, each of its
    subdomains, then other domains by rows; unnamed and 'Unknown Email' rows last."""
    order = {'assessed': 0, 'assessed_subdomain': 1, 'other_domain': 2}
    named = sorted(((k, n, c) for (k, n), c in d['mail'].items() if n),
                   key=lambda x: (order[x[0]], -sum(x[2]), x[1]))
    num = lambda n: C.P(C.fmt_number(n), s05.ZERO_C if n == 0 else 'dense_num')
    entries = [('row', [str(i), C.M(s05.mono(n, True), 'dense'), *map(num, c), num(sum(c))])
               for i, (_, n, c) in enumerate(named, 1)]
    extra = [('Other email domains, name not given', d['mail'].get(('other_domain', None))),
             ('Unknown Email', d['cross']['unknown_email'] if sum(d['cross']['unknown_email']) else None)]
    entries += [('row', [str(len(entries) + i), C.P(name, 'dense_muted'), *map(num, c), num(sum(c))])
                for i, (name, c) in enumerate([x for x in extra if x[1]], 1)]
    if len(s05.other_mailboxes(d)) <= s05.INLINE_DOMAINS and not sum(d['cross']['assessed_subdomain']):
        return [C.heading(f'{rid}.4  Rows by email domain', 3, style=H3T),     # Section 05 shows every one
                C.P(f'All email domains are listed in Section {SEC_NUM["s05"]}.', 'body')]
    t = register_table(['#', 'Account email domain', *s05.CROSS_COLS, 'Total'], entries,
                       title=f'{rid}.4 Rows by email domain', sec_id='s05', numeric_cols=(0, 2, 3, 4, 5), ident='regD44',
                       widths=[28, T.CW - 28 - 4 * s05.CROSS_WN] + [s05.CROSS_WN] * 4)
    return [C.heading(f'{rid}.4  Rows by email domain', 3, style=H3T), *const_line(t), t]


def d4_credentials(report, identity, as_of):
    from . import s05_credential_exposure as s05
    sec = (report.get('sections') or {}).get('credential_exposure') or {}
    title = pol('lists.credential_exposure.register_title', 'Credential exposure — supporting tables')
    rid = RID['s05']
    info = {'rid': rid, 'state': sec.get('state'), 'sec': 's05', 'title': title}
    d = s05.derive(sec, report, identity)
    if not s05.register_printed(sec.get('state'), d):      # same rule as the Section 05 pointer
        return {**info, 'content': state_message(sec, SEC_NUM['s05'], 'exposed credentials')}
    key = str(sec.get('register_ref') or '').rsplit('.', 1)[-1] or 'credential_register'
    partial = d['analysed'] != d['received'] or (d['total'] is not None and d['total'] != d['received'])
    flow = opening(rid, title, 's05', [
        (f'Showing {C.fmt_number(d["analysed"])} of {C.fmt_number(d["received"])} register rows'
         + (f' ({C.fmt_number(d["total"])} in the source).' if d['total'] is not None else '.')) if partial else ''],
        [key])
    cats = sorted(d['by_field'].items(), key=lambda kv: (-kv[1], kv[0]))
    labels = pol('lists.credential_exposure.field_labels', {}) or {}
    entries = [('row', [str(i), labels.get(k, k), s05.category_class_label(k), n,
                        f'{round(100 * n / d["analysed"])}%'])
               for i, (k, n) in enumerate(cats, 1)]
    t41 = register_table(['#', 'Field category', 'Data class', 'Rows', 'Share of rows'], entries,
                         title=f'{rid}.1 Rows by exposed field category', sec_id='s05', numeric_cols=(0, 3, 4),
                         ident='regD41')
    flow += [C.heading(f'{rid}.1  Rows by exposed field category', 3, style=H3T), *const_line(t41), t41,
             C.note(pol('reconciliation.non_exclusive_note',
                        'A row can count in several categories; column total exceeds row total.'))]
    src = {x.get('field_category'): x.get('rows') for x in sec.get('rows_by_field_category') or []}
    diff = [f'{k} (source {src.get(k, "not listed")}, rows {d["by_field"].get(k, 0)})'
            for k in sorted(set(src) | set(d['by_field'])) if src and src.get(k) != d['by_field'].get(k)]
    if diff:
        flow.append(C.note('Source field-category counts differ from the register rows: ' + '; '.join(diff) + '.'))
    flow += [C.heading(f'{rid}.2  Rows by data class', 3, style=H3T),
             intro('Exclusive: each row counts once, in its highest class ('      # order = s05.CLASSES
                   + ', then '.join(s05.CLASS_RANK_TEXT[k] for k in s05.CLASSES if k in s05.CLASS_RANK_TEXT
                                    and (k not in s05.OPTIONAL_CLASSES or d['by_class'][k]))
                   + '). The origin flag is counted apart, below.', 'note_flush'),
             s05.by_data_class(d),
             C.note(f'Service/URL recorded (origin), counted apart from the classes: {C.fmt_number(d["origin"])} '
                    f'row{"s" if d["origin"] != 1 else ""}; the value itself is not provided by the source.'),
             *d23_domains(s05, d, sec, rid), *d24_mailboxes(s05, d, rid)]
    reg_flow, printed, flagged = s05.row_register(d)
    flow += reg_flow
    notes = ([f'{C.fmt_number(d["suppressed"])} not shown (mask policy violation)'] if d['suppressed'] else []) + \
        ([f'{C.fmt_number(flagged)} label{"s" if flagged != 1 else ""} without a mask character printed as received']
         if flagged else []) + \
        ([f'source headline {C.fmt_number(d["headline"])}, difference {signed(printed - d["headline"])}, not explained '
          'by the source data'] if d['headline'] is not None and printed != d['headline'] else [])
    flow += closing(rid, [key], '; '.join(notes) + '.' if notes else '', rows=printed)
    info.update(flow=flow, content=f'Aggregates and all {C.fmt_number(printed)} of {C.fmt_number(d["received"])} '
                                   'register rows')
    return info


def d5_quantum(report, as_of):
    from . import s11_quantum_security as s11
    sec = (report.get('sections') or {}).get('quantum_security') or {}
    title = pol('lists.quantum_scope.register_title', 'Quantum scope breakdown')
    rid = RID['s11']
    info = {'rid': rid, 'state': sec.get('state'), 'sec': 's11', 'title': title}
    sc = s11.scope(sec, report)
    if not sc['rows'] or sc['tier'] == 'T1' or sec.get('state') not in ('findings', 'partial', 'pending_review'):
        # T1 (inline in Section 11) passes the row count; no rows -> 'no register data'
        return {**info, 'content': state_message(sec, SEC_NUM['s11'], 'scope rows',
                                                 len(sc['rows']) if sc['rows'] and sc['tier'] == 'T1' else None)}
    key = str(sec.get('scope_register_ref') or '').rsplit('.', 1)[-1] or 'quantum_scope_register'
    scopes = len(sc['groups']) + bool(sc['apex'])
    n_rows = C.fmt_number(len(sc['rows']))
    apex = (f' The main domain total{sc["apex_scope"].replace("(", "(the source ")} comes first; subdomain rows are '
            'not added to it.') if sc['apex'] else ''
    src = f' Source: {sc["source_note"]}.' if sc['source_note'] else ''      # omitted when no row has one
    flow = opening(rid, title, 's11', [
        f'{rid}.1 lists one row per scope with its post-quantum (PQC) status, ordered by High, then Moderate, then '
        f'Low findings.{apex}{src}'],
        [key, 'pqc_domain_register'], legend=s11.legend(sec))      # names the siren-only count headers
    t = s11.pivot_table(sc, title=f'{rid}.1 {title}', ident='regD5')
    flow += [C.keep(C.heading(f'{rid}.1  Scopes', 3, style=H3T), *const_line(t), t)]
    t2 = s11.scope_table(sc, dense=True, title=f'{rid}.2 Scope × algorithm rows', ident='regD52', number_all=True)
    flow += [C.heading(f'{rid}.2  Scope × algorithm rows', 3, style=H3T), *const_line(t2), t2]
    if sc['post_qc_missing']:
        flow.append(C.note(s11.POST_QC_NOTE))
    flow += closing(rid, [key, 'pqc_domain_register'], s11.end_line(sec, sc), rows=len(sc['rows']),
                    unit='scope × algorithm rows')
    info.update(flow=flow, content=f'{scopes} scopes (one row each) and all {n_rows} scope × algorithm rows')
    return info


def d6_vendors(report, sec, as_of):
    """<D.n>.1: flat register of every connected organisation (T2 only; T1 prints them in Section 14)."""
    from . import s14_fourth_party_vendors as s14
    vendors = [v for v in sec.get('vendors') or [] if isinstance(v, dict)]
    title = pol('lists.fourth_party_vendors.register_title', 'Fourth-party vendors and technologies')
    rid = RID['s14']
    info = {'rid': rid, 'state': sec.get('state'), 'sec': 's14', 'title': title}
    if not vendors or s14.tier(vendors)[0] == 'T1' or sec.get('state') not in ('findings', 'partial', 'pending_review'):
        return {**info, 'content': state_message(sec, SEC_NUM['s14'], 'connected organisations', len(vendors),
                                                 list_key='fourth_party_vendors')}
    org, n = s14.org_name(report), len(vendors)
    flow = opening(rid, title, 's14', [
        f'{rid}.1 lists all {n} connected organisations reported for {org}, sorted by grade, worst first; '
        f'organisations without a rating last.'], ['fourth_party_register'])
    cols, w, entries = s14.register_entries(C, vendors, report)
    t = register_table(cols, entries, title=f'{rid}.1 Connected organisations', sec_id='s14', numeric_cols=(0,),
                       widths=w, ident='regD61')
    flow += [C.heading(f'{rid}.1  Connected organisations', 3, style=H3T), *const_line(t), t,
             s14.notes(vendors)]
    flow += closing(rid, ['fourth_party_register'], '', rows=n)
    info.update(flow=flow, content=f'{n} of {n} connected organisations')
    return info


DOC_TYPES = {'.png', '.jpg', '.jpeg', '.pdf'}


def document_pages(report, ref):
    """Page images of an uploaded certificate document: [(path or PNG bytes, w, h)], or (None, reason).
    Paths resolve against the JSON file's folder and must stay inside it (the payload is input)."""
    import io

    from reportlab.lib.utils import ImageReader
    raw = C.val(ref)
    if not raw:
        return None, 'no file in the assessment data'
    base = Path(report.get('_source_dir') or '.').resolve()
    p = (base / str(raw)).resolve()
    if base not in p.parents or p.suffix.lower() not in DOC_TYPES:
        return None, 'file path not accepted'
    if not p.is_file():
        return None, 'file not found'
    if p.suffix.lower() != '.pdf':
        return [(str(p), *ImageReader(str(p)).getSize())], None
    import pymupdf
    with pymupdf.open(p) as d:
        pngs = [pg.get_pixmap(dpi=150).tobytes('png') for pg in d]
    return [(io.BytesIO(b), *ImageReader(io.BytesIO(b)).getSize()) for b in pngs], None


def cert_documents(report, sec):
    """<D.n>: uploaded certificate documents, one page each (Section 13 stays a compact table)."""
    from . import s13_certifications as s13
    rid, title = RID['s13'], 'Uploaded certificate documents'
    info = {'rid': rid, 'state': sec.get('state'), 'sec': 's13', 'title': title}
    docs = [x for x in s13.grouped([x for x in sec.get('certificates') or [] if isinstance(x, dict)])
            if s13.origin(x) == 'uploaded' and s13.has_document(x)]
    if not docs:
        return {**info, 'content': 'Not required — no uploaded certificate documents in the assessment data.'}
    flow = opening(rid, title, 's13', [
        f'{rid} shows the {len(docs)} certificate document{"s" if len(docs) > 1 else ""} uploaded to Cyberrank, '
        f'in the order of Section {SEC_NUM["s13"]}, one document per page.',
        'Shown as uploaded; dates and scope printed on a document are not read into the report data.'], [])
    loaded = [(i, x, *document_pages(report, x.get('document'))) for i, x in enumerate(docs, 1)]
    missing = [f'{rid}.{i} {s13.std_name(x)} ({why})' for i, x, pages, why in loaded if not pages]
    for i, x, pages, why in loaded:
        if not pages:
            qa.add('missing_document', 'warn', f'{rid}.{i}: certificate document not shown ({why})')
    if missing:        # stated up front, no page of its own
        flow.append(C.P('Not shown: ' + '; '.join(missing) + '.', 'note_flush', keepWithNext=1))
    loaded = [t for t in loaded if t[2]]
    shown = 0
    for i, x, pages, _ in loaded:
        meta = ' · '.join(p for p in (C.val(x.get('issuer')) and f'Issuer: {C.val(x.get("issuer"))}',
                                      C.val(x.get('file_reference'))) if p)
        head = [C.heading(f'{rid}.{i}  {s13.std_name(x)}', 3, key=f'reg-{rid}.{i}', style=H3T)]
        if meta:
            head.append(C.P(meta, 'note_flush', keepWithNext=1))
        for j, (img, w, h) in enumerate(pages):
            pic = Image(img, width=T.CW, height=T.CW * h / w)
            # one page per document page: shrinks to the room left under the heading
            last = shown == len(loaded) - 1 and j == len(pages) - 1      # leaves room for the end line
            flow += ([PageBreak()] if shown or j else []) + (head if j == 0 else []) + \
                [KeepInFrame(0, T.FRAME_H - 90 if last else 0, [pic], mode='shrink', hAlign='CENTER')]
        shown += 1
    flow += closing(rid, [], f'{shown} of {len(docs)} shown.' if shown != len(docs) else '', rows=len(docs),
                    unit='documents')
    info.update(flow=flow, content=f'{shown} of {len(docs)} uploaded certificate documents')
    return info


def state_message(sec, nn, unit, count=None, list_key=None):
    """Index text for a register that is not printed (policy states.register_messages)."""
    st, msgs = sec.get('state'), pol('states.register_messages', {}) or {}
    if st == 'clear':
        return fill(msgs.get('clear', 'Not required — no {unit} identified.'), unit=unit)
    if st in ('not_assessed', 'not_applicable', 'unavailable', 'failed'):
        return fill(msgs.get(st, 'Not produced.'), nn=nn, reason=C.reason_text(sec))
    if st == 'none_identified':
        return f'Not required — no {unit} identified.'
    if count is not None and count <= t1_max(list_key):
        return f'Not required — all {count} {unit} shown in Section {nn}.'
    if count is None:
        return 'Not produced — no register data in the payload.'
    return f'Not produced — no register data in the payload ({count} {unit} in Section {nn}).'


def d3_leaks(sec):
    """<D.n> data leak events: index row only. Section 06 lists every distinct event inline (merged by
    canonical_event_id), so the row never claims register data is missing."""
    from .s06_data_leak_history import merge_events
    n = len(merge_events([e for e in sec.get('events') or [] if isinstance(e, dict)]))
    info = _absent(RID['s06'], 'Data leak event details', sec, 's06', 'data_leak_events', n, 'events')
    if n and sec.get('state') not in ('not_assessed', 'not_applicable', 'unavailable', 'failed'):
        info['content'] = f'Not required — all {n} event{"s" if n != 1 else ""} shown in Section {SEC_NUM["s06"]}.'
    return info


def _absent(rid, title, sec, sid, list_key, count, unit, anchor=None):
    return {'rid': rid, 'title': pol(f'lists.{list_key}.register_title', title), 'state': sec.get('state'),
            'content': state_message(sec, SEC_NUM[sid], unit, count), 'sec': sid, 'anchor': anchor}


def _index(regs):
    def make(prev):
        rows = []
        for r in regs:
            where = (pages_link(prev, r['rid'], 'page reference pending') if r.get('flow')
                     else page_link(prev, r['anchor'] if r.get('anchor') in prev else BY_ID[r['sec']].anchor,
                                    f'Section {SEC_NUM[r["sec"]]}'))
            rows.append([r['rid'], r['title'], C.state_chip(T.shown_state(r['state'], BY_ID[r['sec']].key), dense=True) if r.get('state') else
                         C.state_chip(None, dense=True),
                         r.get('content') or C.missing_text({'reason_code': 'not_printed_in_source'}),
                         C.M(where, 'dense')])
        return C.compact_table(['D.n', 'Register', 'State', 'Content', 'Location'], rows, dense=True,
                               widths=[32, 168, 84, T.CW - 360, 76])
    return Lazy(make)


def build(data, ctx):
    """Index + every register, built from the section data (the appendix payload only sets the frame)."""
    c, rep = ctx.c, ctx.report
    TITLES.clear()
    TITLES.update({s.id: (rep.get(s.source) or {}).get(s.key, {}).get('title') for s in REGISTRY
                   if isinstance((rep.get(s.source) or {}).get(s.key), dict)})
    as_of = c.fmt_date((rep.get('snapshot') or {}).get('assessed_at'))
    secs = rep.get('sections') or {}
    dl, fp = secs.get('data_leak_history') or {}, secs.get('fourth_party_vendors') or {}
    regs = [d1_assets(rep, as_of), d12_ip(rep, as_of),
            d3_leaks(dl),
            d6_vendors(rep, fp, as_of),
            d4_credentials(rep, ctx.identity, as_of), d5_quantum(rep, as_of),
            cert_documents(rep, secs.get('certifications') or {})]
    regs.sort(key=lambda r: [int(x) for x in r['rid'][2:].split('.')])     # D.1, D.1.2, D.2, ...
    out = [c.P(pol('naming.appendix_d.note', 'Evidence registers support findings; layout and row caps do not '
                                             'change any score.'), 'body'),
           c.heading('Register index', 3), _index(regs),
           c.note('Registers that are not required appear here only. Page references link to the register.')]
    for r in regs:
        out += r.get('flow') or []
    return out


build_context = build      # no-result appendix state: the card, then the registers all the same
