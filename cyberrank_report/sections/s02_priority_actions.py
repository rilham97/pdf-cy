"""02 Priority actions: KPI strip (actions by priority), then one compact table
row per action in source order: priority chip, title + action + why, effort,
team. Linked sections are referenced (with page), never re-quoted: an action
whose text already appears in a linked section prints a reference instead.
"""
import re

from reportlab.lib.colors import Color, black
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Spacer, TableStyle

from .. import components as c
from .. import theme as T
from . import NO_RESULT, WITH_CARD
from .s01_executive_overview import Deferred, section_data, section_ref, spec_for

LEVELS = ('critical', 'high', 'medium', 'low')      # Critical tile only when an action has it
WHO = (('Owner', 'owner'), ('Due', 'due_at'), ('Status', 'status'))
_MUTED = c.hexstr(T.MUTED)
PRIORITY_W = c.head_width('Priority')     # siren only (legend: the priority tiles above the table)
ACTION_W = T.CW - 24 - PRIORITY_W - 64 - 92      # Action column of the table


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)


def _find(node, finding_id):
    """The object in a section payload whose finding_id matches."""
    if isinstance(node, dict):
        if node.get('finding_id') == finding_id:
            return node
        node = list(node.values())
    if isinstance(node, list):
        for v in node:
            hit = _find(v, finding_id)
            if hit is not None:
                return hit
    return None


def _holder(node, text):
    """Label of the object (e.g. a privacy issue 'Issue 1') whose own string holds `text`."""
    if isinstance(node, dict):
        if node.get('label') and any(isinstance(v, str) and text in v for v in node.values()):
            return node['label']
        node = list(node.values())
    if isinstance(node, list):
        for v in node:
            hit = _holder(v, text)
            if hit:
                return hit
    return None


def _verify_first(action, report):
    """'Verify first' lines for linked findings whose own state is not settled
    (e.g. DMARC enabled but its policy mode was left blank)."""
    out = []
    for fid in action.get('linked_finding_ids') or []:
        for key in action.get('linked_sections') or []:
            spec = spec_for(key)
            hit = _find(section_data(report, spec) or {}, fid) if spec else None
            if not hit or hit.get('state') in ('findings', 'clear', None):
                continue
            name = hit.get('control') or hit.get('finding_type') or hit.get('label') or fid
            gaps = [(k, v) for k, v in hit.items() if isinstance(v, dict) and c.is_missing(v)]
            for k, v in gaps[:1]:
                field = k.replace('_', ' ')
                field = name + field[len(name):] if field.lower().startswith(name.lower()) else f'{name} {field}'
                out.append(f'{field} is not available ({c.reason_text(v)})')
            if not gaps:
                out.append(f'{name}: {c.reason_text(hit)}')
            break
    for key in action.get('linked_sections') or []:
        spec = spec_for(key)
        line = _count_check(section_data(report, spec) or {}) if spec else None
        if line:
            out.append(line)
    return out


def _count_check(sec):
    """A linked section whose headline count is not a unique count (e.g. credential
    exposure: '40 Found' vs 30 register rows): say so before the action quotes the figure."""
    ms = {m.get('count_kind') or m.get('id'): m for m in sec.get('metrics') or [] if isinstance(m, dict)}
    head = ms.get('reported_headline')
    if not head or c.is_missing(head):
        return None
    unit = ' (unit not defined)' if 'unverified' in str(head.get('unit')) else ''
    parts = [f'{c.fmt_number(head["value"])} is the source headline{unit}']
    rows = ms.get('returned_rows')
    if rows and not c.is_missing(rows):
        parts.append(f'{c.fmt_number(rows["value"])} register rows listed')
    uniq = ms.get('unique_accounts')
    if uniq:
        parts.append(f'unique accounts: {c.fmt_value(uniq)}')
    return '; '.join(parts) if len(parts) > 1 else None   # a bare headline needs no caveat


def _unit_rule(action, report):
    """Credential action (policy unit_rules.priority_action): our reading of the count as register
    rows on the assessed domain that list a password category, never 'N affected accounts'. The
    source sentence is quoted verbatim by the caller; this text prints under it as a note."""
    if 'credential_exposure' not in (action.get('linked_sections') or []):
        return None
    from ..page import identity_from_report
    from .app_d_evidence_registers import fill, pol
    from .s05_credential_exposure import lead_metric
    spec = spec_for('credential_exposure')
    m, d = lead_metric(section_data(report, spec) or {}, report, identity_from_report(report))
    if not m:
        return None
    src = re.split(r'(?<=\.)\s+', c.val(action.get('action_required_source')) or '')
    if not any(re.search(r'\d[\d,]*\s+(?:\w+\s+)?accounts?\b', x) for x in src):
        return None      # the source does not count accounts: nothing to reinterpret
    tpl = pol('lists.credential_exposure.unit_rules.priority_action_text',
              'Verify and reset the accounts behind {N} rows on {assessed_domain} that list a password category.')
    lead = fill(tpl, N=c.fmt_number(m['value']), assessed_domain=d['assessed'] or 'the assessed domain') \
        if m['value'] else None
    return lead


def _who(label, v):
    if c.is_missing(v):
        return f'{label} {c.reason_text(v)}'
    if isinstance(v, dict) and str(v.get('value', ''))[:4].isdigit() and 'precision' in v:
        return f'{label} {c.fmt_date(v)}'
    return f'{label} {c.fmt_value(v)}'


def _shared_gaps(actions):
    """Owner / due / status fields whose nulls share one reason: {field: (text, null on every action)}.
    Rows then print only the assigned values; the reason is stated once under the table."""
    out = {}
    for label, f in WHO:
        nulls = [a[f] for a in actions if f in a and c.is_missing(a[f])]
        reasons = {c.reason_text(v) for v in nulls}
        if nulls and len(reasons) == 1:
            out[f] = (f'{label.lower()} {reasons.pop()}', len(nulls) == len(actions))
    return out


def _action_cell(a, report, pages, shared=()):
    linked = [k for k in a.get('linked_sections') or [] if spec_for(k)]
    refs = ', '.join(section_ref(k, report, pages) for k in linked)
    w, fs = ACTION_W - 2 * T.CELL_PAD_H, T.STYLES['cell'].fontSize
    br = lambda s, font=T.LIGHT, size=fs: c.breakable(s, w, font, size)    # URLs / hashes never overflow
    title = a.get('title') or c.val(a.get('title_source')) or 'Untitled action'     # source wording verbatim
    lines = [f'<font name="{T.MEDIUM}" color="{c.hexstr(T.HEADING)}">{br(title, T.MEDIUM)}</font>']
    text = c.val(a.get('action_required_source'))
    ours = _unit_rule(a, report)
    dup = next((k for k in linked if text and any(text in s for s in _strings(section_data(report, spec_for(k))))),
               None)
    if dup:
        item = _holder(section_data(report, spec_for(dup)), text)
        lines.append(f'Described in {section_ref(dup, report, pages)}' + (f' ({c.esc(item)}).' if item else '.'))
    else:
        miss = a.get('action_required_source') or a.get('action_required')
        lines.append((br(f'Source: “{text}”') if ours else br(text)) if text
                     else c.esc(c.missing_text(miss if isinstance(miss, dict) else None)))
    small = f'<font size="7.8" color="{_MUTED}">'
    if ours:      # our reading of the source count, as a note under the quoted source text
        lines.append(f'{small}Note: {br(ours + " The source counts accounts; the register lists rows, "
                                         "not unique accounts.", size=7.8)}</font>')
    if a.get('derived'):
        lines.append(f'{small}{c.esc(a["derived"])}</font>')
    why = c.val(a.get('why_this_matters_source'))
    if why:      # a null record is omitted, never printed
        lines.append(f'{small}Why it matters: {br(why, size=7.8)}</font>')
    checks = _verify_first(a, report)
    if checks:
        lines += [f'{small}Verify first: {c.esc(c.sentence(x))}</font>' for x in checks]
    who = [_who(k, a.get(f)) for k, f in WHO if f in a and not (f in shared and c.is_missing(a[f]))]
    if who:
        lines.append(small + c.esc('  ·  '.join(who)) + '</font>')
    refs = ', '.join(section_ref(k, report, pages) for k in linked if k != dup)    # no second pointer to `dup`
    if refs:
        lines.append(f'{small}See {refs}</font>')
    return c.M('<br/>'.join(lines), 'cell')


def _cert_review(report, n):
    """Added action (not in the assessment's own list): system-detected certificates awaiting approval."""
    from .s13_certifications import awaiting_review, review_text
    sec = section_data(report, spec_for('certifications')) or {}
    todo = awaiting_review(sec) if sec.get('state') not in NO_RESULT else []    # no Next step in 13 to point to
    if not todo:
        return []
    return [{'rank': n + 1, 'priority': 'low', 'title': 'Review system-detected certificates',
             'action_required_source': review_text(todo), 'linked_sections': ['certifications'],
             'estimated_time': {'value': None, 'reason_code': 'not_tracked'}, 'required_role': 'Cyberrank admin',
             'derived': 'Added by this report from the certificate records; not part of the assessment action list.'}]


def action_rows(data, report):
    """The rows 02 prints, in order: payload actions by rank, then the added certificate action.
    01's Next pointer counts these, so both sections agree."""
    acts = [a for a in (data or {}).get('actions') or [] if isinstance(a, dict)]
    acts.sort(key=lambda a: a.get('rank') if isinstance(a.get('rank'), (int, float)) else float('inf'))
    return acts + _cert_review(report, len(acts))


def _rows(actions, report, pages, shared):
    nr = {'value': None, 'reason_code': 'not_printed_in_source'}
    return [[a.get('rank') if a.get('rank') is not None else i,
             c.severity_icon(a.get('priority')),
             _action_cell(a, report, pages, shared),
             a.get('estimated_time_reported') or a.get('estimated_time') or nr,
             a.get('required_role') or nr] for i, a in enumerate(actions, start=1)]


def _table(actions, report, pages, shared):
    widths = [24, PRIORITY_W, ACTION_W, 64, 92]
    t = c.compact_table(['#', 'Priority', 'Action', 'Effort', 'Team'], _rows(actions, report, pages, shared),
                        numeric_cols=(0,), widths=widths)
    # Short action rows move whole; only a row taller than KEEP_MAX_H may split.
    hs = [max(cell.wrap(w - 2 * T.CELL_PAD_H, T.FRAME_H)[1] for cell, w in zip(row, widths)
              if hasattr(cell, 'wrap')) + 2 * T.CELL_PAD_V for row in t._cellvalues[1:len(actions) + 1]]
    t.setStyle(TableStyle([('NOSPLIT', (0, i), (-1, i)) for i, h in enumerate(hs, 1) if h < T.KEEP_MAX_H]))
    return t


def build(data, ctx):
    acts = action_rows(data, ctx.report)
    out = []
    if acts:
        levels = [str(a.get('priority') or '').lower() for a in acts]
        kpis = [{'label': 'Total', 'value': len(acts), 'unit': 'actions'}]
        kpis += [{'label': f'{p.capitalize()} priority', 'value': levels.count(p), 'unit': 'actions', 'severity': p}
                 for p in LEVELS if p != 'critical' or p in levels]
        unrated = sum(1 for x in levels if x not in LEVELS)
        if unrated:
            kpis.append({'label': 'Priority not rated', 'value': unrated, 'unit': 'actions'})
        shared = _shared_gaps(acts)
        out += [ctx.c.kpi_strip(kpis, per_row=len(kpis)),
                Deferred(lambda pages: _table(acts, ctx.report, pages, shared))]
        notes = [f'{lead}: ' + ', '.join(t for t, every in shared.values() if every == (lead == 'For every action')) + '.'
                 for lead in ('For every action', 'Where not shown')
                 if any(every == (lead == 'For every action') for _, every in shared.values())]
        held = [str(a.get('rank') or i) for i, a in enumerate(acts, 1)
                if a.get('review_flags') and not _verify_first(a, ctx.report)]
        if held:
            notes.append(f'Wording and figures of action{"s" if len(held) > 1 else ""} {", ".join(held)} '
                         'are as reported and held for review.')
        if data.get('note'):
            notes.append(data['note'])
        if notes:
            out.append(ctx.c.note(' '.join(notes)))
        out += remediation_block(data.get('remediation_impact'), ctx.report)
    else:      # no action rows: say so, unless the state card above already gives the reason
        why = data.get('state_reason') or (c.reason_text(data) if data.get('reason_code') else None)
        if not (why and ctx.state in WITH_CARD):
            out.append(c.P(c.sentence(why) if why else 'No priority actions are listed in the assessment data.', 'body'))
    return out


POINTS_TEXT = re.compile(r'\d\s*points?\b|\bout of \d|/\s*\d{3}\b|\b360\b', re.I)    # hidden scoring in source text


def grade_walk(cur, proj):
    """Grades from current up to projected, worst -> best (T.GRADE_BAR). None when either is missing or
    unknown, or the projection is below the current grade: no staircase is drawn then."""
    bar = T.GRADE_BAR
    if cur not in bar or proj not in bar or bar.index(proj) < bar.index(cur):
        return None
    return bar[bar.index(cur):bar.index(proj) + 1]


class GradeSteps(Flowable):
    """Staircase from the current grade to the projected one (never from D), rising left -> right. Current
    and projected steps carry their own grade tone (light tint, grade-colour border and tread, darker grade
    text and tag), so the reader sees the condition now and the better one ahead; the steps between stay
    pale grey with a thin coloured tread. No scores or points."""
    MAXW, BASE, RISE_MAX, RISE_SUM, TREAD, TAG = 74.0, 26.0, 9.0, 54.0, 3.0, 12.0
    SIZE = T.STYLES['note'].fontSize

    def __init__(self, steps, pcts=(None, None)):
        super().__init__()
        self.steps, self.pcts = steps, pcts                      # rating score % at current / projected

    def wrap(self, aw, ah):
        n = len(self.steps)
        self.w = min(self.MAXW, aw / n)
        self.rise = min(self.RISE_MAX, self.RISE_SUM / max(1, n - 1))
        self.base = self.BASE + (10 if any(p is not None for p in self.pcts) else 0)
        self.lab = 2 * (self.SIZE + 2) + 3                       # grade meaning, two lines at most
        self.width, self.height = aw, self.lab + self.base + (n - 1) * self.rise + self.TAG + 4
        return self.width, self.height

    def _label(self, x, y, text, font, color):
        cv, maxw = self.canv, self.w - 4
        cv.setFont(font, self.SIZE)
        cv.setFillColor(color)
        lines = text.rsplit(' ', 1) if stringWidth(text, font, self.SIZE) > maxw and ' ' in text else [text]
        for i, ln in enumerate(lines):
            cv.drawCentredString(x, y - i * (self.SIZE + 2), ln)

    @staticmethod
    def _mix(col, to, t):
        """col moved a fraction t toward `to` (white = tint, black = shade)."""
        return Color(*(a + (b - a) * t for a, b in zip(col.rgb(), to.rgb())))

    def _tag(self, x, y, text, fill):
        cv, size = self.canv, self.SIZE - 0.5
        tw = stringWidth(text, T.MEDIUM, size) + 10
        cv.setFillColor(fill)
        cv.roundRect(x, y, tw, self.TAG, 3, stroke=0, fill=1)
        cv.setFillColor(T.WHITE)
        cv.setFont(T.MEDIUM, size)
        cv.drawString(x + 5, y + 3.6, text)

    def draw(self):
        cv, n, y0 = self.canv, len(self.steps), self.lab
        for i, g in enumerate(self.steps):
            x, h, end = i * self.w + 1, self.base + i * self.rise, i in (0, n - 1)
            w, col = self.w - 2, T.GRADE[g]
            dark = self._mix(col, black, .38)                   # grade tone dark enough for text
            cv.setFillColor(self._mix(col, T.WHITE, .86) if end else T.SURFACE)
            cv.setStrokeColor(col)
            cv.setLineWidth(1.25)
            cv.rect(x, y0, w, h, stroke=int(end), fill=1)
            tread = self.TREAD + (2 if end else 0)
            cv.setFillColor(col)
            cv.rect(x, y0 + h - tread, w, tread, stroke=0, fill=1)
            cv.setFillColor(dark if end else T.MUTED)
            cv.setFont(T.SEMIBOLD if end else T.LIGHT, 12 if end else 8.5)
            cv.drawCentredString(x + w / 2, y0 + h - (20 if end else 15), g)
            pct = self.pcts[0 if i == 0 else 1] if end else None
            if pct is not None:
                cv.setFont(T.MEDIUM, self.SIZE + .5)
                cv.drawCentredString(x + w / 2, y0 + h - 31, f'{pct}%')
            self._label(x + w / 2, self.lab - self.SIZE - 1, T.GRADE_MARK[g], T.MEDIUM if end else T.LIGHT,
                        dark if end else T.MUTED)
            if end:
                tag = 'Current and projected' if n == 1 else ('Current' if i == 0 else 'Projected')
                self._tag(x, y0 + h + 3, tag, dark)


def remediation_block(ri, report=None):
    """'Projected rating after remediation' (source p9 of the 2026-10 samples): one line "Up n grades, from
    BB (Sufficient) to AA (Very good); rating score from 54% to 81%" over a staircase from the current to the
    projected grade, then the active issues and the source's own conditions. The rating score prints only as
    a percent of the pool (score / pool); scores, the pool and recoverable points are never printed (hidden
    scoring) and a source narrative that quotes points is held back.
    Values come from the payload only; nothing is projected here. A null record or a block with no
    printable values draws nothing. Exposed credentials are a separate count, never part of the active issues."""
    if not isinstance(ri, dict) or c.is_missing(ri):
        return []
    from .. import qa
    v = lambda x, k: c.val((x or {}).get(k)) if isinstance(x, dict) else None
    cur, pro = ri.get('current'), ri.get('projected')
    g_cur, g_pro = (str(v(x, 'grade') or '').strip().upper() or None for x in (cur, pro))
    ai = ri.get('active_issues') if isinstance(ri.get('active_issues'), dict) else {}
    n = {k: v(ai, k) for k in ('total', 'privacy', 'vulnerability', 'credentials')}
    num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
    s_cur, s_pro, pts = v(cur, 'score'), v(pro, 'score'), c.val(ri.get('points_recoverable'))
    if num(s_cur) and num(s_pro) and num(pts) and s_pro - s_cur != pts:
        qa.add('data_mismatch', 'warn', f's02: projected score - current score != recoverable points', once=True)
    steps = grade_walk(g_cur, g_pro)
    if steps is None and (g_cur or g_pro):     # missing, unknown or downward: no staircase, no fallback table
        qa.add('data_mismatch', 'warn', f's02: projected rating not drawn (current {g_cur}, projected {g_pro})',
               once=True)
    if not steps and all(x is None for x in n.values()):
        return []
    head = c.val(ri.get('title')) or c.val(ri.get('title_source')) or 'Projected rating after remediation'
    cap = c.val(ri.get('caption_source'))      # source wording, verbatim
    out = [c.heading(head, 2), *([c.note(cap)] if cap else [])]
    # rating score as a percent of the pool (owner 2026-10-21): shows the condition without the pool or points
    pct = lambda x: (min(100, max(0, int(100 * v(x, 'score') / v(x, 'pool') + .5)))
                     if num(v(x, 'score')) and num(v(x, 'pool')) and v(x, 'pool') > 0 else None)
    p_cur, p_pro = pct(cur), pct(pro)
    if steps:
        mark = lambda g: f'<font name="{T.MEDIUM}">{g}</font> ({T.GRADE_MARK[g]})'
        k = len(steps) - 1
        if k:
            line = f'Up {k} grade{"s" if k > 1 else ""}, from {mark(g_cur)} to {mark(g_pro)}'
            line += f'; rating score from {p_cur}% to {p_pro}%.' if None not in (p_cur, p_pro) else '.'
        else:
            line = f'No change in grade projected: {mark(g_cur)}' + (f', rating score {p_cur}%.' if p_cur is not None else '.')
        out += [c.M(line, 'body', spaceAfter=4), GradeSteps(steps, (p_cur, p_pro)), Spacer(1, 6)]
    pairs = []
    parts = [f'{c.fmt_number(n[k])} {k}' for k in ('privacy', 'vulnerability') if n[k] is not None]
    if n['total'] is not None:
        pairs.append(('Active issues', c.fmt_number(n['total']) + (f' ({" + ".join(parts)})' if parts else '')))
        if all(num(n[k]) for k in ('total', 'privacy', 'vulnerability')) and \
                n['privacy'] + n['vulnerability'] != n['total']:          # text counts: no sum check
            qa.add('data_mismatch', 'warn', f's02: active issues {n["total"]} != privacy {n["privacy"]} + '
                   f'vulnerability {n["vulnerability"]}', once=True)
    if n['credentials'] is not None:
        pairs.append(('Exposed credentials', c.fmt_number(n['credentials']) +
                      (' (counted separately; not part of the active issues)' if n['total'] is not None else '')))
    if pairs:
        out.append(c.key_value_list(pairs))
    narrative = c.val(ri.get('narrative_source'))
    if narrative and POINTS_TEXT.search(str(narrative)):
        qa.add('hidden_scoring_in_source', 'warn', 's02: narrative_source quotes points or the point pool; '
               'not printed', once=True)
    elif narrative:
        out.append(c.P(narrative, 'body', spaceBefore=6))
    note = ['Projection as reported by the source, not a commitment.']
    if c.val(ri.get('conditional_on_rescan')):
        note.append('Vulnerability fixes count only after a fresh scan confirms them.')
    out.append(c.note(' '.join(note)))
    return [c.keep(*out, *c.flag_notes(ri, report))]
