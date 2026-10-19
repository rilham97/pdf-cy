"""02 Priority actions: KPI strip (actions by priority), then one compact table
row per action in source order: priority chip, title + action + why, effort,
team. Linked sections are referenced (with page), never re-quoted: an action
whose text already appears in a linked section prints a reference instead.
"""
import re

from reportlab.platypus import TableStyle

from .. import components as c
from .. import theme as T
from .s01_executive_overview import Deferred, section_data, section_ref, spec_for

LEVELS = ('high', 'medium', 'low')
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
    lines = [f'<font name="{T.MEDIUM}" color="{c.hexstr(T.HEADING)}">{br(a.get("title") or "Untitled action", T.MEDIUM)}'
             '</font>']
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
    todo = awaiting_review(section_data(report, spec_for('certifications')))
    if not todo:
        return []
    return [{'rank': n + 1, 'priority': 'low', 'title': 'Review system-detected certificates',
             'action_required_source': review_text(todo), 'linked_sections': ['certifications'],
             'estimated_time': {'value': None, 'reason_code': 'not_tracked'}, 'required_role': 'Cyberrank admin',
             'derived': 'Added by this report from the certificate records; not part of the assessment action list.'}]


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
    acts = [a for a in data.get('actions') or [] if isinstance(a, dict)]
    acts.sort(key=lambda a: a.get('rank') if isinstance(a.get('rank'), (int, float)) else float('inf'))
    acts += _cert_review(ctx.report, len(acts))
    out = []
    if acts:
        levels = [str(a.get('priority') or '').lower() for a in acts]
        kpis = [{'label': 'Total', 'value': len(acts), 'unit': 'actions'}]
        kpis += [{'label': f'{p.capitalize()} priority', 'value': levels.count(p), 'unit': 'actions', 'severity': p}
                 for p in LEVELS]
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
        out.append(ctx.c.note(' '.join(notes)))
        out += remediation_block(data.get('remediation_impact'), ctx.report)
    else:      # no action rows: say so (the source-order footnote has nothing to qualify)
        why = data.get('state_reason') or (c.reason_text(data) if data.get('reason_code') else None)
        out.append(c.P(c.sentence(why) if why else 'No priority actions are listed in the assessment data.', 'body'))
    return out


def remediation_block(ri, report=None):
    """'Projected rating after remediation' (source p9 of the 2026-10 samples): current and projected
    grade with their scores as printed, the recoverable points and the source's own conditions.
    Values come from the payload only; nothing is projected here. A null record or a block with no
    values draws nothing. Exposed credentials are a separate count, never part of the active issues."""
    if not isinstance(ri, dict) or c.is_missing(ri):
        return []
    v = lambda x, k: c.val((x or {}).get(k)) if isinstance(x, dict) else None
    def side(x):
        g, sc, pool = v(x, 'grade'), v(x, 'score'), v(x, 'pool')
        if not g:
            return {'value': None, 'reason_code': 'not_printed_in_source'}
        return f'{g} · score {c.fmt_number(sc)} / {c.fmt_number(pool)}' if sc is not None and pool else str(g)
    ai = ri.get('active_issues') if isinstance(ri.get('active_issues'), dict) else {}
    n = {k: v(ai, k) for k in ('total', 'privacy', 'vulnerability', 'credentials')}
    pts = c.val(ri.get('points_recoverable'))
    if not any([v(ri.get('current'), 'grade'), v(ri.get('projected'), 'grade'), pts is not None,
                *(x is not None for x in n.values())]):
        return []
    pairs = [('Current rating', side(ri.get('current'))), ('Projected rating', side(ri.get('projected')))]
    if pts is not None:
        pairs.append(('Recoverable', c.fmt_value(pts, 'points')))
    parts = [f'{c.fmt_number(n[k])} {k}' for k in ('privacy', 'vulnerability') if n[k] is not None]
    if n['total'] is not None:
        pairs.append(('Active issues', c.fmt_number(n['total']) + (f' ({" + ".join(parts)})' if parts else '')))
        if parts and len(parts) == 2 and n['privacy'] + n['vulnerability'] != n['total']:
            from .. import qa
            qa.add('data_mismatch', 'warn', f's02: active issues {n["total"]} != privacy {n["privacy"]} + '
                   f'vulnerability {n["vulnerability"]}', once=True)
    if n['credentials'] is not None:
        pairs.append(('Exposed credentials', c.fmt_number(n['credentials']) +
                      (' (counted separately; not part of the active issues)' if n['total'] is not None else '')))
    out = [c.heading(c.val(ri.get('title')) or 'Projected rating after remediation', 2), c.key_value_list(pairs)]
    if c.val(ri.get('narrative_source')):
        out.append(c.P(c.val(ri['narrative_source']), 'body', spaceBefore=6))
    note = ['Projection as reported by the source, not a commitment.']
    if c.val(ri.get('conditional_on_rescan')):
        note.append('Vulnerability fixes count only after a fresh scan confirms them.')
    out.append(c.note(' '.join(note)))
    return [c.keep(*out, *c.flag_notes(ri, report))]
