"""11 Quantum security -- overview; the scope register is inline (tier T1) or, in Appendix D
(T2/T3; id RID['s11']), pivoted to one row per scope followed by every scope x algorithm row (<D.n>.2).

The apex row (scope_level 'root_aggregate') aggregates the apex and every subdomain;
it is printed once, labelled, and never added to subdomain totals. Severity words
follow the source scale: High / Moderate / Low.

PQC wording (no negative claim without data): 'No PQC detected' only when PQC was reported
(a non-empty pqc_detected list, or the pqc_scan toggle recorded as on); otherwise 'PQC not
reported'. pqc_scan recorded as off -> the section is not_assessed (pqc_scan_disabled); off together
with quantum results is a data error rejected at load (build.validate).
KPI rule: High / Moderate / Low are the source headline. In the 2026-10 samples the headline equals the
number of scope x algorithm rows at each level (each row counted once at its highest level; Mock
Cyberrank RF-M03, where the apex aggregate row differs); the note states which relation the data
shows, and says so when the headline also equals the apex aggregate row. The apex row is labelled (owner 2026-10-19: printed as 'main domain')
'main domain total' ('headline scope' only when its counts equal the headline); the subdomain-row sum is
printed in a note.
Without scope_level, a row named after the assessed domain whose counts equal the headline is
taken as the apex aggregate, labelled '(inferred)' (QA apex_inferred).
"""
import re

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Table, TableStyle

from .. import components as C
from .. import icons as I
from .. import qa
from .. import theme as T
from .app_d_evidence_registers import (RID, H2T, H3T, ZERO, const_line, fill, gap, group_row, intro, long_list_card,
                                       lookup, pol, register_table, tier)

LIST = 'lists.quantum_scope'
LEVELS = ('high', 'moderate', 'low')
CATEGORY_ICON = {'public-key cryptography': 'public_key', 'symmetric cryptography': 'symmetric',
                 'hash functions': 'hash', 'certificate': 'certificate', 'key exchange': 'public_key'}
NOT_LISTED = 'Not listed'
POST_QC_NOTE = (f'Post-QC “{NOT_LISTED}”: the source prints a dash, so no post-quantum replacement is listed for '
                'that algorithm; the source does not say whether one was checked.')


def _plural(n, word):
    return f'{C.fmt_number(n)} {word}{"" if n == 1 else "s"}'


def _toggle(report):
    t = ((report.get('snapshot') or {}).get('toggles_at_assessment') or {}).get('pqc_scan')
    return t.get('value') if isinstance(t, dict) else t


def adjust(data, report):
    """pqc_scan recorded as off -> not_assessed. Off with results present is rejected at load
    (build.validate), so it never reaches the renderer."""
    if _toggle(report) is not False:
        return data
    from . import hold
    return hold(data, 'pqc_scan_disabled', 'The post-quantum (PQC) scan was switched off when this assessment '
                'was created, so quantum exposure was not assessed. This is not a result of no findings.',
                state='not_assessed')


def _sum(rows, k):
    vals = [r.get(k) for r in rows]
    return None if any(v is None for v in vals) else sum(vals)


def _hml(t, sep=' · '):
    """'High 56 · Moderate 0 · Low 192' with non-breaking spaces inside each pair; missing is 'not available'."""
    return sep.join(f'{lbl}\u00a0{C.fmt_number(v) if v is not None else "not available"}'
                    for lbl, v in zip(('High', 'Moderate', 'Low'), t))


def apex_short(sc):
    """Levels where the subdomain rows add up to more than the apex aggregate (which covers
    them all): impossible in consistent data. [(label, apex, subdomains)]; warns once."""
    if not sc['apex_tot']:
        return []
    out = [(lbl, a, c) for lbl, a, c in zip(('High', 'Moderate', 'Low'), sc['apex_tot'], sc['child_tot'])
           if a is not None and c is not None and c > a]
    if out:
        qa.add('data_mismatch', 'warn', 's11: subdomain rows exceed the apex aggregate: ' +
               ', '.join(f'{lbl} {c} > {a}' for lbl, a, c in out), once=True)
    return out


def _short_text(out):
    return ('Subdomain rows exceed the main domain total that covers them (' +
            ', '.join(f'{lbl} {C.fmt_number(c)} vs {C.fmt_number(a)}' for lbl, a, c in out) +
            '); not explained by the source data')


def fit(text, dense, head=False):
    """Column width that holds `text` on one line (cell or header font) plus padding."""
    st = T.STYLES[('dense' if dense else 'cell') + ('_head' if head else '')]
    return stringWidth(str(text), st.fontName, st.fontSize) + 2 * T.CELL_PAD_H + 1


def _num_widths(dense, *labels):
    """'#' and High/Moderate/Low widths; numbers and these headers never wrap."""
    hml = fit('99,999', dense)                  # headers are sirens only (legend names them)
    # widest digit for every digit: '31' is narrower than '20' in Poppins (proportional figures)
    return max(fit(re.sub(r'\d', '6', x), dense) for x in ('#', *labels)), hml


def row_levels(rows):
    """(High, Moderate, Low) number of scope x algorithm rows, each counted once at its highest level."""
    out = [0, 0, 0]
    for r in rows:
        i = next((i for i, k in enumerate(LEVELS) if r.get(k)), None)
        if i is not None:
            out[i] += 1
    return tuple(out)


def scope(data, report):
    reg = lookup(report, data.get('scope_register_ref')) or {}
    rows = [r for r in reg.get('rows') or [] if isinstance(r, dict)]
    apex = [r for r in rows if r.get('scope_level') == 'root_aggregate']
    inferred = False
    if rows and not any('scope_level' in r for r in rows):    # no level recorded: infer the apex, never add it
        dom = str((report.get('identity') or {}).get('domain') or '').lower()
        cand = [r for r in rows if str(r.get('subdomain') or '').lower() == dom]
        if dom and cand and tuple(_sum(cand, k) for k in LEVELS) == _headline(data) and len(cand) < len(rows):
            apex, inferred = cand, True
            qa.add('apex_inferred', 'warn', f's11: no scope_level in the register; rows for {dom} match the '
                   'headline and are treated as the apex aggregate', once=True)
    child = [r for r in rows if not any(r is a for a in apex)]
    groups = {}
    for r in child:
        groups.setdefault(str(r.get('subdomain')), []).append(r)
    tot = lambda rs: tuple(_sum(rs, k) for k in LEVELS)
    order = sorted(groups.items(), key=lambda kv: (tuple(-(v or 0) for v in tot(kv[1])), kv[0]))
    pqc = {d: C.val(p.get('algorithm')) for p in data.get('pqc_detected') or [] for d in p.get('domains') or []}
    reported = bool(data.get('pqc_detected')) or _toggle(report) is True
    sources = {r.get('source') for r in rows}
    src = next(iter(sources)) if len(sources) == 1 else None
    head = _headline(data)
    apex_head = bool(apex) and None not in head and head == tot(apex)
    return {'rows': rows, 'row_levels': row_levels(rows), 'head': head, 'apex_head': apex_head,
            'apex_scope': ' (headline scope)' if apex_head else '',
            'apex': apex, 'child': child, 'groups': order, 'pqc': pqc, 'tot': tot,
            'summary': {C.val(s.get('subdomain')): s for s in data.get('scope_summary') or []},
            'child_tot': tot(child), 'apex_tot': tot(apex) if apex else None,
            'apex_name': str(apex[0].get('subdomain')) if apex else None, 'pqc_reported': reported,
            'apex_label': 'main domain total (inferred)' if inferred else 'main domain total',
            # visual rows: every data row (each apex row prints as A1..An) + one label row per group
            'tier': tier(len(rows) + len(groups) + bool(apex), len(rows)),
            'uniform': src is not None,
            # no row carries a source: nothing to say (never 'all rows “None”')
            'source_note': f'all rows “{src}”' if src is not None else None if sources == {None} else 'per row',
            'counts': reg.get('counts') or {},
            'post_qc_missing': sum(1 for r in rows if not r.get('post_qc_algorithm'))}


def _pqc_chip(sc, name, dense=True):
    """PQC status: shield-check + '<alg> detected'; 'No PQC detected' only when PQC was reported,
    else 'PQC not reported' (no negative claim without data)."""
    alg, st = sc['pqc'].get(name), T.STYLES['dense' if dense else 'cell']
    if alg:
        return I.status_label('pqc', f'{alg} detected', 'pqc', style=st)
    if sc['pqc_reported']:
        return I.status_label('not_assessed', 'No PQC detected', 'no_pqc', style=st)
    return I.status_label('unavailable', 'PQC not reported', 'not_recorded', style=st)


def _pqc_w(sc, dense):
    """Column width holding every PQC status label on one line."""
    names = [None] + list(sc['pqc'])
    return max(_pqc_chip(sc, n, dense).wrap(T.CW, 100)[0] for n in names) + 2 * T.CELL_PAD_H + 1


def _category(name, dense=False):
    name = C.val(name)
    """Category icon (key / lock-key / hash / certificate) + the category name."""
    key = CATEGORY_ICON.get(str(name or '').lower(), 'quantum_security')
    return I.icon_label(key, str(name or 'Category not recorded'), T.NAVY, dense)


def mono(text, dense=False):
    """Inline JetBrains Mono span for a host / algorithm name inside Poppins markup (escaped)."""
    st = T.STYLES['dense_tech' if dense else 'cell_tech']
    return f'<font name="{st.fontName}" size="{st.fontSize}">{C.esc(text)}</font>'


def _tech(v, dense):
    return C.tech(v, 'dense_tech' if dense else 'cell_tech') if isinstance(v, str) and v else v


def legend(data):
    """Severity legend (heading line) for the icon-only Risk columns and count headers: the source headline."""
    return C.severity_legend(list(zip(LEVELS, _headline(data))), scale='quantum')


def _risk_w(cells):
    """Risk column: header width for sirens only; a visible label (not rated) sets its own width."""
    return max([C.head_width('Risk')] + [c.minWidth() + 2 * T.CELL_PAD_H + 1 for c in cells
                                         if hasattr(c, 'minWidth') and not isinstance(c, I.SeverityIcon)])


def _rated(data):
    return any(a.get('risk_level') in LEVELS for c in data.get('findings_by_category') or []
               for a in c.get('algorithms') or [])


def _hml_heads(dense):
    st = T.STYLES['dense_head_num' if dense else 'cell_head_num']
    return [I.SeverityHead(k, 'quantum', st) for k in LEVELS]


def scope_table(sc, dense=True, title='', ident=None, number_all=False):
    """Row-level register (tier T1 inline, and Appendix <D.n>.2): apex aggregate first (rows A1.., or numbered
    with the rest when number_all), then one group per subdomain."""
    cols = ['#', 'Category', 'Algorithm (pre-QC)', 'Post-QC', *_hml_heads(dense)]
    cols += [] if sc['uniform'] else ['Source']
    head, muted = ('dense_head', 'dense_muted') if dense else ('cell_head', 'cell_muted')
    blocks = ([(sc['apex_name'], sc['apex'], True)] if sc['apex'] else []) + [(s, rs, False) for s, rs in sc['groups']]
    entries, n = [], 0
    for name, rs, is_apex in blocks:
        absent = (sc['summary'].get(name) or {}).get('algorithms_absent') or []
        label = mono(name, dense) + (C.esc(f'  ·  {sc["apex_label"]}{sc["apex_scope"]}') if is_apex else '')
        label += C.esc(f'  ·  {", ".join(absent)} not observed') if absent else ''
        entries.append(('group', group_row(C.M(label, head), _pqc_chip(sc, name, dense), T.CW - 2 * T.CELL_PAD_H),
                        name))
        for i, r in enumerate(sorted(rs, key=lambda r: (-(r.get('high') or 0), str(r.get('category')),
                                                         str(r.get('pre_qc_algorithm')))), 1):
            n += number_all or not is_apex
            entries.append(('row', [C.P(f'A{i}' if is_apex and not number_all else str(n), ZERO),
                                    _category(r['category'], dense) if r.get('category') else {'value': None},
                                    _tech(r.get('pre_qc_algorithm'), dense) or {'value': None},
                                    _tech(r.get('post_qc_algorithm'), dense) or C.P(NOT_LISTED, muted),
                                    *[r.get(k) for k in LEVELS]] + ([] if sc['uniform'] else [r.get('source')])))
    w0, wn = _num_widths(dense, str(n), f'A{len(sc["apex"])}')
    w = [w0, 0, 0, fit(NOT_LISTED, dense) + 8, wn, wn, wn] + ([] if sc['uniform'] else [62])
    rest = T.CW - sum(w)
    w[1], w[2] = rest * 0.53, rest * 0.47
    return register_table(cols, entries, title=title, sec_id='s11', numeric_cols=(0, 4, 5, 6), dense=dense,
                          widths=w, ident=ident)


def _algs(rs):
    return {str(r.get('pre_qc_algorithm')) for r in rs if r.get('pre_qc_algorithm')}


def _differs(rs, apex_algs):
    """'No ECDSA' / '+X' against the apex algorithm set; '' when identical or no apex."""
    if not apex_algs:
        return ''
    a = _algs(rs)
    return ', '.join([f'No {x}' for x in sorted(apex_algs - a)] + [f'+{x}' for x in sorted(a - apex_algs)])


def pivot_table(sc, title, ident, dense=True):
    """<D.n>.1: one row per scope (apex aggregate first), counts and PQC status; the scope x algorithm
    rows follow in <D.n>.2 (scope_table)."""
    apex_algs = _algs(sc['apex'])
    rows = []
    if sc['apex']:
        rows.append(['A', C.M(f'{mono(sc["apex_name"], dense)}<br/><font color="{C.hexstr(T.MUTED)}">{sc["apex_label"]}'
                              f'{sc["apex_scope"]}</font>', 'dense' if dense else 'cell'),
                     _pqc_chip(sc, sc['apex_name'], dense), *sc['apex_tot'],
                     C.P('Reference', 'dense_muted' if dense else 'cell_muted')])
    for i, (s, rs) in enumerate(sc['groups'], 1):
        rows.append([C.P(str(i), ZERO), _tech(s, dense), _pqc_chip(sc, s, dense), *sc['tot'](rs),
                     (_differs(rs, apex_algs) or 'Same as main domain') if apex_algs else ''])
    cols = ['#', 'Subdomain', 'PQC', *_hml_heads(dense), 'Algorithms vs main domain']
    w0, wn = _num_widths(dense, str(len(sc['groups'])), 'A')
    pqc_w = _pqc_w(sc, dense)
    w = [w0, 0, pqc_w, wn, wn, wn, fit(cols[-1], dense, head=True)]
    w[1] = T.CW - sum(w)
    t = register_table(cols, [('row', r) for r in rows], title=title, sec_id='s11', numeric_cols=(0, 3, 4, 5),
                       dense=dense, widths=w, ident=ident,
                       ordinals=([None] if sc['apex'] else []) + list(range(1, len(sc['groups']) + 1)))
    if sc['apex'] and sc['groups']:      # the apex row never ends a page alone
        t.setStyle(TableStyle([('NOSPLIT', (0, 1), (-1, 2))]))
    return t


def _headline(sec):
    m = {x.get('id'): x.get('value') for x in sec.get('metrics') or [] if isinstance(x, dict)}
    return tuple(m.get(k) for k in ('high_risk', 'moderate_risk', 'low_risk'))


def end_line(sec, sc):
    head, scopes = _headline(sec), len(sc['groups']) + bool(sc['apex'])
    if head == (sc['apex_tot'] if sc['apex'] else sc['child_tot']):
        match = 'matches the Section 11 headline'
    elif None not in head and head == sc['row_levels']:
        match = (f'differs from the Section 11 headline {_hml(head)}, which counts the '
                 f'{_plural(len(sc["rows"]), "scope × algorithm row")} by level (highest level per row)')
    else:
        match = f'differs from the Section 11 headline {_hml(head)}; not explained by the source data'
    checks = [f'source count “{k}” is {src}, listed {v}'
              for k, v in (('rows', len(sc['rows'])), ('scopes', scopes))
              for src in [sc['counts'].get(k)] if src is not None and src != v]
    checks += [_short_text(x) for x in [apex_short(sc)] if x]
    parts = [] if match.startswith('matches') else \
        [f'The {"main domain total" if sc["apex"] else "subdomain total"} {match}']
    parts += checks          # differences only (owner 2026-10-21); nothing when everything matches
    return '; '.join(parts) + '.' if parts else ''


# --- overview modules ------------------------------------------------------------
def kpis(data):
    items = []
    for m in data.get('metrics') or []:
        if m.get('id') == 'pqc_detected' and (not m.get('unit') or str(m['unit']).endswith('_inferred')):
            m = {**m, 'unit': None, 'label': 'PQC detected (unit not confirmed by source)'}
        lvl = str(m.get('id') or '').removesuffix('_risk')
        if lvl in LEVELS:          # severity tier tile: siren + source term ('Moderate')
            m = {**m, 'severity': lvl, 'scale': 'quantum'}
        items.append(m)
    return C.kpi_strip(items)


def notes(data, sc):
    """KPI rule: the headline is the apex aggregate the product scores; the subdomain-row sum is printed."""
    out, head = [], _headline(data)
    known = None not in head
    lead = ('High, Moderate and Low are the source headline: the main domain total, as scored in the product.'
            if known else '')
    n = len(sc['groups'])
    child = f' The subdomain rows sum to {_hml(sc["child_tot"])}; they are not added to the headline.' if n else ''
    if known and sc['rows'] and head == sc['row_levels']:
        # the relation the data shows (Mock RF-M03): rows by level, not necessarily the apex aggregate
        where = 'below' if sc['tier'] == 'T1' else f'in Appendix {RID["s11"]}'     # T1: no D.4 register
        text = (f'High, Moderate and Low are the source headline. They equal the number of scope × algorithm rows '
                f'in the scope breakdown at each level ({_plural(len(sc["rows"]), "row")}, each counted once at '
                f'its highest level; every row is listed {where}).')
        if sc['apex'] and head == sc['apex_tot']:
            text += (f' The {sc["apex_label"]} row for {sc["apex_name"]} gives the same High, Moderate and Low '
                     'findings.')
        elif sc['apex']:
            text += (f' The headline is not the {sc["apex_label"]} row for {sc["apex_name"]}, which sums to '
                     f'{_hml(sc["apex_tot"])} findings.')
        out.append(text + child)
    elif sc['apex'] and head == sc['apex_tot']:
        covers = (f'covers the main domain and {_plural(n, "subdomain")} ({_plural(n + 1, "scope")})' if n else
                  'covers the main domain only (1 scope); no subdomain rows are listed')
        out.append(f'{lead} The {sc["apex_label"]} row for {sc["apex_name"]} matches it and {covers}.{child}')
    elif sc['apex']:
        qa.add('data_mismatch', 'warn', f's11: headline {head} differs from the apex aggregate row '
               f'{sc["apex_tot"]}', once=True)
        out.append(f'{lead} The {sc["apex_label"]} row for {sc["apex_name"]} in the scope register sums to '
                   f'{_hml(sc["apex_tot"])}, which differs from the headline; not explained by the source data.'
                   f'{child}')
    elif sc['rows']:
        out.append(f'{lead} No main domain total row is recorded.{child}'.strip())
    short = apex_short(sc)
    if short:
        out.append(_short_text(short) + '.')
    issues = sum(C.val(c.get('issues')) or 0 for c in data.get('findings_by_category') or [])
    if issues and None not in head and issues != sum(head):
        out.append(f'Findings by category total {C.fmt_number(issues)}; High + Moderate + Low total '
                   f'{C.fmt_number(sum(head))} (difference {issues - sum(head):+,}).')
    if data.get('beta_notice_source'):
        out.append('Source notice: ' + data['beta_notice_source'])
    return [C.note(x) for x in out]


def algorithms(data):
    rank = lambda a: LEVELS.index(a.get('risk_level')) if a.get('risk_level') in LEVELS else 9
    rows = []
    for c in sorted(data.get('findings_by_category') or [],
                    key=lambda c: min([rank(a) for a in c.get('algorithms') or []] or [9])):
        for i, a in enumerate(sorted(c.get('algorithms') or [], key=rank)):
            doms = C.val(c.get('domains_source_label'))      # source label, e.g. '2 domains'
            cat = ([_category(c.get('category')),
                    C.P(f'{C.fmt_value(c.get("issues"), "findings")} in category' + (f' · {doms}' if doms else ''),
                        'dense_muted')] if i == 0 else '')
            alt = C.val(a.get('pqc_alternative_available'))
            rows.append([cat, _tech(a.get('algorithm'), False) or {'value': None},
                         C.severity_icon(a.get('risk_level'), scale='quantum'),
                         a.get('findings'),
                         ', '.join(a.get('protocol_labels') or []) or C.P(NOT_LISTED, 'cell_muted'),
                         I.status_label('pqc', str(alt), 'pqc') if alt else
                         C.P('Not available', 'cell_muted')])
    if not rows:
        return []
    # '#' then Risk (severity column right after the row number), then the category / algorithm
    rows = [[i, r[2], r[0], r[1], *r[3:]] for i, r in enumerate(rows, 1)]
    cols = ['#', 'Risk', 'Category', 'Algorithm', 'Findings', 'Protocols', 'PQC alternative']
    w = [_num_widths(False, str(len(rows)))[0], _risk_w([r[1] for r in rows]), 131,
         max([106] + [r[3].minWidth() + 2 * T.CELL_PAD_H + 1 for r in rows if hasattr(r[3], 'minWidth')]),
         fit('Findings', False, head=True), 0, fit('PQC alternative', False, head=True)]
    rated = _rated(data)
    if not rated:        # the source prints no per-algorithm risk: no column of 'Not rated'
        cols, w, rows = cols[:1] + cols[2:], w[:1] + w[2:], [r[:1] + r[2:] for r in rows]
    w[cols.index('Protocols')] = 0
    w[cols.index('Protocols')] = T.CW - sum(w)
    text = ('Each algorithm counts findings across all scanned scopes. High risk marks key exchange that a '
            'quantum computer could break; a PQC alternative is the replacement the source names.' if rated else
            'Each algorithm counts findings across all scanned scopes; the source prints no risk level per '
            'algorithm. A PQC alternative is the replacement the source names.')
    head = C.heading('Findings by algorithm', 2, style=H2T)
    return [C.heading_legend(head, legend(data)) if rated else head, intro(text),
            gap(C.compact_table(cols, rows, numeric_cols=(0, cols.index('Findings')), widths=w), 8)]


def pqc_block(data, sc, report):
    out, scopes = [], len(sc['groups']) + bool(sc['apex'])
    reg = lookup(report, 'appendices.d_evidence_registers.pqc_domain_register') or {}
    algs = []
    for p in data.get('pqc_detected') or []:
        p = {k: C.val(v) for k, v in p.items()}           # null records -> None (never printed raw)
        p['algorithm'] = p.get('algorithm') or 'Algorithm not recorded'
        doms = p.get('domains') or []
        algs.append(str(p.get('algorithm')))
        alias = f' ({p["algorithm_alias"]})' if p.get('algorithm_alias') else ''
        status = re.sub(r'^\s*Status:\s*', '', C.val(p.get('status_source')) or '')
        named = C.val(p.get('domains_count')) or len(doms)
        # no scope register: there is no scope total to compare with
        on = f'{C.fmt_number(named)} of {_plural(scopes, "scope")}' if sc['rows'] else _plural(named, 'domain')
        out += [C.heading(f'{p["algorithm"]}{alias}', 3, style=H3T),
                intro(' · '.join(str(x) for x in (p.get('purpose'), status) if x)),
                intro(f'Detected on {on}. Support for PQC does not prove that every connection uses it.')]
        cells = [C.tech(d, 'dense_tech') for d in doms]      # domain list: plain technical text
        st = T.STYLES['dense_tech']
        widest = max([stringWidth(str(d), st.fontName, st.fontSize) for d in doms] or [0]) + 6
        k = max(1, min(4, int(T.CW // widest)))           # 4 columns when the longest domain fits
        grid = [cells[i:i + k] + [''] * (k - len(cells[i:i + k])) for i in range(0, len(cells), k)]
        if grid:
            t = Table(grid, colWidths=[T.CW / k] * k, hAlign='LEFT', spaceBefore=6, spaceAfter=6)
            t.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                                   ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                                   ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
            out.append(t)
        if sc['rows'] and named > scopes:
            out.append(C.note(f'The source names {named} {p.get("algorithm")} domains '
                              f'but the scope register holds {scopes} scopes; not explained by the source data.'))
        listed = len([r for r in reg.get('rows') or [] if r.get('algorithm') == p.get('algorithm')])
        if reg.get('rows') and listed != len(doms):
            out.append(C.note(f'PQC domain register lists {listed} domains for {p.get("algorithm")}; '
                              f'this section lists {len(doms)}.'))
    missing = [n for n in ([sc['apex_name']] if sc['apex'] else []) + [s for s, _ in sc['groups']] if n not in sc['pqc']]
    if out and missing:
        what = algs[0] if len(algs) == 1 else 'PQC'
        out += [C.P(f'No {what} observed on {len(missing)} of {_plural(scopes, "scope")}', 'card_label', spaceBefore=4,
                    keepWithNext=1),
                C.tech(', '.join(missing), 'cell_tech')]
    if not out and sc['rows']:          # nothing listed: say whether PQC was reported at all
        tog = ((report.get('snapshot') or {}).get('toggles_at_assessment') or {}).get('pqc_scan')
        text = ('No post-quantum cryptography was detected on '
                + ('the one scope in the register.' if scopes == 1 else f'any of the {_plural(scopes, "scope")}.')
                if sc['pqc_reported'] else
                'PQC not reported: the assessment data lists no post-quantum detection and does not record whether '
                f'the PQC scan ran ({C.reason_text(tog) if isinstance(tog, dict) else "scan setting not recorded"}). '
                'This is not a finding that PQC is absent.')
        return [C.heading('Post-quantum cryptography', 2, style=H2T), C.P(text, 'body')]
    return ([C.heading('Post-quantum cryptography detected', 2, style=H2T)] + out) if out else []


def protocols(data):
    """'Affected Protocols' (2026-10 samples): protocol, algorithms, PQC as printed, risk (siren)."""
    rows = [[C.P(str(C.val(p.get('protocol')) or 'Protocol not recorded'), 'cell_head'),
             _tech(', '.join(p.get('algorithms') or []), False) or C.P(NOT_LISTED, 'cell_muted'),
             p.get('pqc_source') or C.P('Not available', 'cell_muted'),
             C.severity_icon(p.get('risk_level'), scale='quantum') if p.get('risk_level') in LEVELS else
             C.P('Not recorded', 'cell_muted')]
            for p in data.get('affected_protocols') or [] if isinstance(p, dict)]
    if not rows:
        return []
    rows = [[i, r[3], *r[:3]] for i, r in enumerate(rows, 1)]          # '#', Risk, then the protocol
    w = [_num_widths(False, str(len(rows)))[0],
         max(_risk_w([r[1] for r in rows]),
             fit('Not recorded', False) if any(not isinstance(r[1], I.SeverityIcon) for r in rows) else 0), 72, 0, 150]
    w[3] = T.CW - sum(w)
    return [C.heading('Affected protocols', 2, style=H2T),
            gap(C.compact_table(['#', 'Risk', 'Protocol', 'Algorithms', 'PQC'], rows, widths=w, numeric_cols=(0,)), 8)]


def risk_adjusted(sc):
    """Scope rows whose printed Risk carries an explanation (PQC coverage): the counts stay as reported."""
    rs = [r for r in sc['rows'] if r.get('risk_note_source')]
    if not rs:
        return []
    def alg(r):
        post = r.get('post_qc_algorithm') or NOT_LISTED
        pre = mono(r['pre_qc_algorithm']) if r.get('pre_qc_algorithm') else 'Not recorded'
        return C.M(f'{pre}<br/><font color="{C.hexstr(T.MUTED)}">'
                   f'Post-QC: {mono(post) if r.get("post_qc_algorithm") else C.esc(post)}</font>', 'cell')

    def counts(r):      # a missing count prints 'not available', never 0
        return C.M(_hml([r.get(k) for k in LEVELS], '<br/>'), 'cell')
    rows = [[i, C.severity_icon(r.get('risk_level'), scale='quantum') if r.get('risk_level') in LEVELS else '',
             C.tech(str(r.get('subdomain')), 'cell_tech'), alg(r), counts(r),
             C.P(r['risk_note_source'], 'cell')] for i, r in enumerate(rs, 1)]
    w = [_num_widths(False, str(len(rows)))[0], C.head_width('Risk'), 104, 104,
         max([fit('Moderate 99', False)] + [fit(x, False) for r in rs              # one line per level
                                            for x in _hml([r.get(k) for k in LEVELS], '\n').split('\n')]), 0]
    w[5] = T.CW - sum(w)
    mixed = sum(1 for r in rs if r.get('risk_level') in LEVELS and not r.get(r['risk_level']))
    out = [C.heading('Risk after PQC coverage', 2, style=H2T),
           intro(f'{_plural(len(rs), "scope row")} carr{"ies" if len(rs) == 1 else "y"} a risk explanation in the '
                 'source. The High, Moderate and Low counts stay as reported; the Risk column is the source\'s '
                 'assessment after PQC coverage.'),
           gap(C.compact_table(['#', 'Risk', 'Scope', 'Algorithm', 'Counts', 'Source explanation'], rows, widths=w,
                               numeric_cols=(0,)), 8)]
    if mixed:
        out.append(C.note(f'{_plural(mixed, "row")} print{"s" if mixed == 1 else ""} a Risk level that differs '
                          'from the column holding the count; both are shown as printed.'))
    return out


def _who(names):
    return C.tech(names[0], 'cell_tech') if len(names) == 1 else f'{len(names)} subdomains'


def breakdown(data, sc):
    """with the legend unless 'Findings by algorithm' already carries it (rated algorithms)."""
    head = C.heading('Scope breakdown', 2, style=H2T)
    out = [head if _rated(data) else C.heading_legend(head, legend(data))]
    if sc['tier'] == 'T1':
        t = scope_table(sc, dense=False, title='Scope breakdown', ident='s11-scope')
        notes = ([f'Source: {sc["source_note"]}.'] if sc['uniform'] else []) + \
            ([POST_QC_NOTE] if sc['post_qc_missing'] else [])      # uniform source: no column, one note
        return out + const_line(t) + [t] + ([C.note(' '.join(notes))] if notes else [])
    # identical subdomains collapse into one line: same counts, PQC status and missing algorithms
    apex_algs, grouped = _algs(sc['apex']), {}
    for s, rs in sc['groups']:
        grouped.setdefault((sc['tot'](rs), sc['pqc'].get(s), _differs(rs, apex_algs)), []).append(s)
    top = pol(f'{LIST}.top_n', pol('tiers.top_n_default', 10))
    items = list(grouped.items())[:top]      # sc['groups'] is already ordered by High, Moderate, Low, name
    rows = [[_who(names), *t, _pqc_chip(sc, names[0], dense=False), diff or ('Same as main domain' if apex_algs else '')]
            for (t, _, diff), names in items]      # no apex row: empty cell, as in the D.4.1 pivot
    _, wn = _num_widths(False, '0')
    w = [0, wn, wn, wn, _pqc_w(sc, False),
         fit('Algorithms vs main domain', False, head=True)]
    w[0] = T.CW - sum(w)
    shown = sum(len(n) for _, n in items)
    text = intro(f'{len(sc["groups"])} subdomains in {len(grouped)} groups with identical counts, PQC status and '
                 f'algorithms, ordered by High, then Moderate, then Low findings. Appendix {RID["s11"]} lists one row per '
                 f'subdomain and every scope × algorithm row ({C.fmt_number(len(sc["rows"]))}).')
    out += [text,
            gap(C.compact_table(['Subdomains', *_hml_heads(False), 'PQC', 'Algorithms vs main domain'], rows,
                                numeric_cols=(1, 2, 3), widths=w), 8)]
    lines = [] if shown == len(sc['groups']) else [
        fill(pol('reconciliation.showing', 'Showing {shown} of {total} {unit}.'), shown=shown,
             total=len(sc['groups']), unit='subdomains')]
    if sc['apex']:
        # owner 2026-10-19: plain 'main domain', not 'apex' (the policy's apex_aggregate_note wording is not used)
        apex_tpl = ('Main domain total' + (' (the headline scope' if sc['apex_head'] else ' (parent')
                    + ', not added to subdomain rows): High {h} · Moderate {m} · Low {l}')
        lines.append(fill(apex_tpl, h=sc['apex_tot'][0], m=sc['apex_tot'][1], l=sc['apex_tot'][2]) + '.')
    if sc['uniform']:
        lines.append(f'Source: {sc["source_note"]}.')
    if lines:
        out.append(C.note(' '.join(lines)))
    return out + [C.register_pointer(RID['s11'], {'value': len(sc['groups']) + bool(sc['apex']), 'unit': 'scopes'},
                                     title=f'{RID["s11"]} {pol(f"{LIST}.register_title", "Quantum scope breakdown")}')]


def limitations(data):
    """The H2 sits inside the first keep(): a keepWithNext heading cannot bind to a container."""
    src, out, h2 = data.get('scope_and_limitations_source') or {}, [], 'Scope and limitations'
    for key in ('scope_and_limitations', 'post_quantum_readiness'):
        b = src.get(key) or {}
        if not b:
            continue
        parts = [] if out else [C.heading(h2, 2)]
        h3 = re.sub(r'^[a-z]\.\s*', '', b.get('title') or key.replace('_', ' ').capitalize())
        parts += [] if h3.lower() == h2.lower() else [C.P(h3, 'h3', spaceBefore=T.SP_SM)]
        parts += [C.P(b['intro'], 'body')] if b.get('intro') else []
        parts += C.bullets(b.get('items') or [])
        parts += [C.P(b['closing'], 'body', spaceBefore=4)] if b.get('closing') else []
        out.append(C.keep(*parts))
    return out


# --- section contract ------------------------------------------------------------
def card(data, ctx):
    empty = data.get('empty_state_source') or {}      # the source's own empty-state text and coverage win
    kw = long_list_card(data, ctx, empty.get('text') or 'No quantum-vulnerable algorithms were identified within '
                                                        'the scope and period of this assessment.')
    if ctx.state == 'clear' and not (data.get('what_checked') or empty.get('coverage')):
        sc = scope(data, ctx.report)
        n = len(data.get('scope_summary') or []) or len(sc['groups']) + bool(sc['apex'])
        kw['what_checked'] = [f'TLS/SSL configurations and SSH endpoints on {_plural(n, "scope")}' if n else
                              'TLS/SSL configurations and SSH endpoints in scope',
                              'Classical algorithms exposed to future quantum attack (key exchange, public-key, '
                              'symmetric)',
                              'Post-quantum key exchange support (ML-KEM)']
    return kw


def build(data, ctx):
    if ctx.state == 'clear':
        return limitations(data)
    sc = scope(data, ctx.report)
    return ([kpis(data)] + notes(data, sc) + algorithms(data) + pqc_block(data, sc, ctx.report) + protocols(data)
            + risk_adjusted(sc)
            + (breakdown(data, sc) if sc['rows'] else
               [C.P(f'Scope rows: {C.missing_text({"reason_code": "not_printed_in_source"})}.', 'body')])
            + limitations(data))
