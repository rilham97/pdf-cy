"""04 Vulnerabilities: KPI strip -> tier definitions + severity legend + findings table (siren only) -> finding details (rationale,
hosts wrapping only between hosts) -> register pointer -> Email & DNS controls -> IP reputation
-> HTTPS redirect -> related actions. Sub-checks carry their own state card. Review flags are
internal; their effects (verification steps, held values) are rendered where they apply.
`python -m cyberrank_report.sections.s04_vulnerabilities data.json out.pdf` renders all states."""
from collections import Counter

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Spacer, Table, TableStyle

from .. import components as C
from .. import icons as I
from .. import qa
from .. import theme as T
from . import app_d_evidence_registers as D

NO_RESULT = ('not_assessed', 'not_applicable', 'unavailable')
SEVERITIES = ('critical', 'high', 'medium', 'low')
GROUPS = ('critical_high',)          # source legend keys spanning tiers: never rendered as a tier
RESULT_LABELS = {'missing_or_invalid': 'Missing or invalid', 'redirects_to_https': 'Redirects to HTTPS',
                 'no_redirect': 'Does not redirect to HTTPS'}          # others: humanised code
CONTROL_PURPOSE = {
    'SPF': 'Lists the servers allowed to send mail for the domain.',
    'DKIM': 'Signs outgoing mail so receivers can verify its origin and integrity.',
    'DMARC': 'Sets how receivers treat mail failing SPF or DKIM; reports spoofing.',
    'DNSSEC': 'Authenticates DNS responses and protects against DNS cache poisoning.',
    'MTA-STS': 'Requires encrypted (TLS) delivery for inbound mail.',
}
# result word -> check (True) / x (False); other words: not-recorded icon. Icon + real text, no colour code.
RESULT_PASS = {**dict.fromkeys(('enabled', 'valid', 'redirects_to_https'), True),
               **dict.fromkeys(('not_enabled', 'missing', 'missing_or_invalid', 'invalid', 'weak', 'no_redirect'),
                               False)}
FIELD_LABELS = {'dmarc_policy': 'Policy mode (p=)', 'key_strength_bits': 'Key strength'}
REQUIRED_CONTROLS = ('SPF', 'DKIM', 'DMARC', 'DNSSEC')   # a missing one prints 'Not reported', never a pass
DMARC_RANK = {'none': 0, 'quarantine': 1, 'reject': 2}
INFO = ('info', 'informational')
KEPT_REASONS = {
    'sentinel_meaning_unconfirmed': 'Recorded value; its meaning is not confirmed, so it is held for review.'}

_CODE = T.STYLES['tech'].clone('v04_code', textColor=T.HEADING)           # finding code: mono 0.9 x 9.1 pt
_CODE_SIREN = T.STYLES['body_flush']                                      # siren sized to the 9.1 pt line
# kit Keep.split ignores the lead's spaceAfter; carry the 6 pt on the table's spaceBefore
_H2_FLUSH = T.STYLES['h2'].clone('v04_h2_flush', spaceAfter=0)
_LINK = T.STYLES['cell_tech'].clone('v04_link', textColor=T.NAVY)
_LEGEND = T.STYLES['note_flush'].clone('v04_legend', hyphenationLang='', embeddedHyphenation=0)


# --- small helpers --------------------------------------------------------------
def _human(code):
    code = C.val(code)
    if code is None:
        return 'Not recorded'
    return RESULT_LABELS.get(code) or C.sentence(str(code).replace('_', ' ')).rstrip('.')


def _fkey(ctx, f):
    return f'{ctx.spec.anchor}-{f.get("finding_id")}'


def _name(f):
    """Finding name in the summary and the details: type, else its ID."""
    return C.val(f.get('finding_type')) or C.val(f.get('finding_id')) or 'Unnamed finding'


def _count(f):
    n = C.val(f.get('affected_assets_count'))
    return len(f['affected_assets']) if n is None and f.get('affected_assets') is not None else n


def _no_orphans(t, short=10):
    """Short tables (<= `short` body rows) never split; longer ones never leave a
    single body row alone on either side of a page break."""
    if len(t._cellvalues) - 1 <= short:
        t.setStyle([('NOSPLIT', (0, 0), (-1, -1))])
    else:
        t.setStyle([('NOSPLIT', (0, 1), (-1, 2)), ('NOSPLIT', (0, -2), (-1, -1))])
    return t


def _broken(text, width, st):
    """Escaped markup for a code / hash token: line breaks only at technical break points
    (/ . - _ @), an unbreakable run split by character, never past `width`."""
    return C.breakable(text, width, st.fontName, st.fontSize)


_SUMMARY_FIXED = [52, C.head_width('Severity'), 98]   # ID, Severity (siren only), Affected domains
_ZERO_PAD = [(f'{s}PADDING', (0, 0), (-1, -1), 0) for s in ('LEFT', 'RIGHT', 'TOP', 'BOTTOM')]


def _num_w(values):
    """'#' column: as wide as its widest number (or the header)."""
    return max([C.head_width('#')] + [C.head_width(v) for v in values])


def _atomic(flowables, width):
    """One-row table: a cell block that never splits (moves whole instead)."""
    return Table([[flowables]], colWidths=[width], hAlign='LEFT', style=_ZERO_PAD)


FINDING_COL = 2          # Finding details: '#', Severity, Finding, Rationale


class _Register(C.CompactTable):
    """RL's in-row split can emit a padding-only remainder row (content fit, bottom padding
    did not) that splits again into duplicate headers; split a little higher instead."""

    def split(self, aw, ah):
        parts = super().split(aw, ah)
        if len(parts) == 2 and not any(parts[1]._cellvalues[self.repeatRows]):
            parts = super().split(aw, ah - 10)
        if len(parts) == 2:      # row continued on the next page: say which finding it belongs to
            code = self._code(parts[0]._cellvalues[-1][FINDING_COL])
            head = parts[1]._cellvalues[self.repeatRows]
            if code and not _has_content(head[FINDING_COL]):
                cont = C.P(f'{code} (cont.)', 'dense_muted')
                cont._v04_code = code      # found again if this remainder splits once more
                head[FINDING_COL] = [cont]
        return parts

    @staticmethod
    def _code(cell):
        return next((getattr(f, '_v04_code', None) for f in cell or [] if hasattr(f, '_v04_code')), None)


def _has_content(cell):
    return bool(cell) if isinstance(cell, (list, tuple)) else cell not in (None, '')


def _table(rows, widths, head, ident, style_extra=()):
    """CompactTable look for rows whose cells hold several flowables. splitByRow=0
    makes RL try the in-row split first, so a part fills the page; by-row first
    re-splits the remainder into the leftover space (header + fragment mid-page)."""
    C._TABLE_HEADS[ident] = list(head)
    t = _Register([[C.P(h, 'cell_head') for h in head]] + rows, colWidths=widths, repeatRows=1,
                  splitByRow=0, splitInRow=1, ident=ident, hAlign='LEFT', spaceBefore=T.STYLES['h2'].spaceAfter)
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), T.CELL_PAD_H), ('RIGHTPADDING', (0, 0), (-1, -1), T.CELL_PAD_H),
        ('TOPPADDING', (0, 0), (-1, 0), T.CELL_PAD_V), ('BOTTOMPADDING', (0, 0), (-1, 0), T.CELL_PAD_V),
        ('TOPPADDING', (0, 1), (-1, -1), 7), ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), T.SURFACE),
        ('LINEBELOW', (0, 1), (-1, -1), T.HAIRLINE, T.RULE), *style_extra]))
    C.center_severity(t)
    return C.numbered(t, [None] + list(range(1, len(rows) + 1)))


_MARKS = ('*', '\u2020', '\u2021', '\u00a7', '\u00b6')


def _footnoted(rows, numeric=()):
    """Null / held-for-review cells -> 'Not available n'; returns (rows, footnote paragraph or None)."""
    notes = {}

    def cell(v, j):
        if not (isinstance(v, dict) and 'value' in v and (C.is_missing(v) or v.get('reason_code'))):
            return v
        if C.is_missing(v):
            why = C.sentence(C.reason_text(v))
            if v.get('source_label') not in (None, ''):
                why += f' The source printed "{v["source_label"]}".'
            text, st = 'Not available', 'cell_muted'
        else:
            why = KEPT_REASONS.get(v.get('reason_code')) or f'Recorded value held for review: {C.reason_text(v)}.'
            text, st = C.fmt_value(v), 'cell'
        n = notes.setdefault(why, _MARKS[len(notes) % len(_MARKS)] * (len(notes) // len(_MARKS) + 1))
        mark = f'<super>{C.esc(n)}</super>'      # symbol, not digit: '0' + '3' would read as '03'
        body = f'{C.esc(text)}\u00a0{mark}'      # marker always after the value, as a superscript
        return C.M(body, st, alignment=2 if j in numeric else 0)

    out = [[cell(v, j) for j, v in enumerate(r)] for r in rows]
    text = '<br/>'.join(f'<super>{C.esc(n)}</super> {C.esc(w)}' for w, n in notes.items())
    return out, C.M(text, 'note_flush') if notes else None


# --- severity tiers ------------------------------------------------------------
def _severity_groups(data):
    """[(key, count|null record, legend text)] for the four tiers Critical, High, Medium, Low,
    never merged. Counts come from each finding's own severity; a source legend entry that
    spans tiers (e.g. 'critical_high') lends its text to no tier (Critical / High use the
    theme copy)."""
    findings = data.get('findings') or []
    metrics = {m.get('id'): m for m in data.get('metrics') or [] if isinstance(m, dict)}
    legend = {C.val(i.get('severity')): i.get('text') for i in data.get('severity_legend_source') or []}
    out = []
    for key in SEVERITIES:
        counted = sum(1 for f in findings if str(f.get('severity')).lower() == key)
        m = metrics.get(f'finding_types_{key}')
        if m is not None and C.is_missing(m):
            n = m
        elif findings:
            n = counted
        else:      # no finding list: the metric is the only count; never a silent 0
            n = m['value'] if m is not None else {'value': None, 'reason_code': 'not_printed_in_source'}
        if m and not C.is_missing(m) and m['value'] != counted:
            qa.add('data_mismatch', 'warn', f's04: metric finding_types_{key}={m["value"]} but '
                   f'{counted} findings carry that severity' + ('' if findings else ' (finding list empty)'),
                   once=True)
        out.append((key, n, legend.get(key) or T.SEVERITY_TEXT.get(key)))
    return out


def _info_note(data):
    """Informational finding types sit outside the four tiers: say so, and flag a total that
    no longer adds up (QA data_mismatch)."""
    findings = data.get('findings') or []
    n_info = sum(1 for f in findings if str(f.get('severity')).lower() in INFO)
    other = [f for f in findings if str(f.get('severity')).lower() not in (*SEVERITIES, *INFO)]
    total = next((m.get('value') for m in data.get('metrics') or [] if isinstance(m, dict)
                  and m.get('id') == 'finding_types'), None)
    tiers = sum(1 for f in findings if str(f.get('severity')).lower() in SEVERITIES)
    if isinstance(total, int) and findings and total != tiers:
        qa.add('data_mismatch', 'warn', f's04: finding_types={total} but the four severity tiers hold {tiers}'
               + (f' ({n_info} informational)' if n_info else ''), once=True)
    parts = []
    if n_info:
        parts.append(f'{n_info} informational finding type{"s are" if n_info != 1 else " is"} listed below but '
                     'not counted in the four severity tiers.')
    if other:
        parts.append(f'{len(other)} finding type{"s have" if len(other) != 1 else " has"} no recognised severity '
                     'and {} not counted in the tiers.'.format('are' if len(other) != 1 else 'is'))
        qa.add('unknown_term', 'warn', 's04: severity not recognised: '
               + ', '.join(sorted({str(C.val(f.get("severity")) or 'not recorded') for f in other})), once=True)
    if parts and isinstance(total, int):
        parts.append(f'Finding types in total: {total}.')
    return [C.note(' '.join(parts))] if parts else []


def _severity_block(data):
    """H2 with the severity legend on its line (right), then the tier definitions at full width: the
    findings table and the finding details below show the siren alone (option B, approved 2026-10-15)."""
    groups = _severity_groups(data)
    lines = []
    for key, cnt, text in groups:
        why = f' Count not available ({C.reason_text(cnt)}).' if isinstance(cnt, dict) else ''
        lines.append(f'<font name="{T.MEDIUM}" color="{C.hexstr(T.HEADING)}">{key.title()}</font>  '
                     f'{C.esc(C.sentence(text) if text else "")}{C.esc(why)}')
    return [C.heading_legend(C.heading('Finding types by severity', 2), C.severity_legend([(k, n) for k, n, _ in groups])),
            C.M('<br/>'.join(lines), _LEGEND, spaceAfter=T.SP_MD)]


def _multi_tier_note(data):
    """One finding type can carry different severities on different domains (one record per type and
    severity, as in the app). Only then: say why a type is listed more than once. Every record needs its own
    finding_id (links to the details use it): a repeated ID raises QA duplicate_finding_id."""
    findings = [f for f in data.get('findings') or [] if isinstance(f, dict)]
    ids = [C.val(f.get('finding_id')) for f in findings if C.val(f.get('finding_id')) is not None]
    dup = sorted({str(i) for i in ids if ids.count(i) > 1})
    if dup:
        qa.add('duplicate_finding_id', 'warn', f's04: finding_id repeated: {", ".join(dup)}', once=True)
    tiers = {}
    for f in findings:
        sev = str(C.val(f.get('severity'))).lower()
        if sev in SEVERITIES:
            tiers.setdefault(_name(f), set()).add(sev)
    multi = [n for n in dict.fromkeys(_name(f) for f in findings) if len(tiers.get(n, ())) > 1]
    if not multi:
        return []
    names = multi[0] if len(multi) == 1 else ', '.join(multi[:-1]) + ' and ' + multi[-1]
    one = len(multi) == 1
    return [C.note(f'{names} {"appears" if one else "appear"} under more than one severity: the severity depends '
                   f'on the affected domain, so {"it is" if one else "each is"} listed once per severity.')]


# owner 2026-10-20: internal reconciliation counts, read for QA only (the headline already gives the domains)
HIDDEN_KPIS = ('asset_memberships', 'distinct_asset_labels')


# --- breach likelihood by domain -------------------------------------------------
LIKELIHOOD_INLINE = 10      # rows shown in the section when the register is long (all rows in D.1)


def _by_domain(ctx):
    """Breach likelihood is one value per domain (owner, 2026-10-20), sent on the affected-asset register rows
    (`rows[].breach_likelihood`, the same rows as D.1). Highest likelihood first; up to 30 rows inline, a longer
    register shows the top 10 here and every row in D.1. No row carries a likelihood: say so (never 0)."""
    _, _, rows, _ = D.d1_register(ctx.report)
    if not rows:
        return []
    head = C.heading('Breach likelihood by domain', 2)
    if not any('breach_likelihood' in r for r in rows):
        return [C.keep(head, C.P(C.sentence(C.missing_text({'reason_code': 'not_printed_in_source'})), 'body'))]
    rank = {k: i for i, k in enumerate(SEVERITIES)}

    def lik(r):
        v = C.val(r.get('breach_likelihood'))
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    rows = sorted(rows, key=lambda r: (lik(r) is None, -(lik(r) or 0),
                                       rank.get(str(r.get('max_severity')).lower(), 9),
                                       -(r.get('finding_count') or 0), str(r.get('asset_label_source'))))
    shown = rows if D.tier(len(rows), len(rows)) == 'T1' else rows[:LIKELIHOOD_INLINE]
    body = [[str(i), C.severity_icon(r.get('max_severity')),
             C.tech(str(r.get('asset_label_source')), 'cell_tech') if r.get('asset_label_source')
             else {'value': None, 'reason_code': 'asset_not_extracted'},
             r.get('finding_count') if r.get('finding_count') is not None
             else {'value': None, 'reason_code': 'not_printed_in_source'},
             r.get('breach_likelihood') if r.get('breach_likelihood') is not None
             else {'value': None, 'reason_code': 'not_printed_in_source'}]
            for i, r in enumerate(shown, 1)]
    num_w, sev_w, n_w, l_w = _num_w(range(1, len(shown) + 1)), C.head_width('Severity'), 74, 98
    out = [C.heading_legend(head, C.severity_legend([(k, [str(r.get('max_severity') or '').lower()
                                                         for r in rows].count(k)) for k in SEVERITIES])),
           C.compact_table(['#', 'Severity', 'Domain', 'Findings', 'Breach likelihood'], body,
                           widths=[num_w, sev_w, T.CW - num_w - sev_w - n_w - l_w, n_w, l_w],
                           numeric_cols=(0, 3, 4), title='Breach likelihood by domain')]
    if len(shown) < len(rows):
        out.append(C.note(f'Showing the {len(shown)} domains with the highest breach likelihood of {len(rows)}; '
                          f'every domain is listed in Appendix {D.RID["s04"]}.'))
    return out


# --- findings -------------------------------------------------------------------
def _ordered(findings):
    rank = {s: i for i, s in enumerate(SEVERITIES)}
    return sorted(findings, key=lambda f: rank.get(str(C.val(f.get('severity'))).lower(), len(rank)))


def _summary_table(findings, ctx):
    rows = []
    for f in findings:
        code = _broken(_name(f), T.CW - sum(_SUMMARY_FIXED) - 2 * T.CELL_PAD_H, _LINK)
        rows.append([C.P(C.val(f.get('finding_id')) or '', 'cell_muted'),
                     C.severity_icon(f.get('severity')),
                     C.M(f'<a href="#{C.esc(_fkey(ctx, f))}">{code}</a>', _LINK),
                     _count(f) if _count(f) is not None else {'value': None, 'reason_code': 'not_printed_in_source'}])
    fixed = _SUMMARY_FIXED
    return _no_orphans(C.compact_table(['ID', 'Severity', 'Finding', 'Affected domains'], rows,
                                       widths=fixed[:2] + [T.CW - sum(fixed)] + fixed[2:], numeric_cols=(3,),
                                       title='Finding types'))


def _hosts(label, hosts):
    """Label line + comma-separated host list (JetBrains Mono; owner: commas, not middle dots) that wraps
    only after a comma (inner spaces are non-breaking). One paragraph, so the label never ends a page alone."""
    mono = T.STYLES['dense_tech']
    text = f'<font name="{T.LIGHT}" size="{T.STYLES["dense"].fontSize}">,</font> '.join(
        C.esc(h).replace(' ', '\u00a0') for h in hosts)
    head = f'<font name="{T.MEDIUM}" color="{C.hexstr(T.HEADING)}">{C.esc(label)}</font>'
    return C.M(f'{head}<br/><font name="{mono.fontName}" size="{mono.fontSize}">{text}</font>', 'dense', spaceBefore=5)


def _detail_table(findings, ctx):
    rows, sirens = [], []
    lw = T.COL3 - 2 * T.CELL_PAD_H
    for i, f in enumerate(findings, 1):
        siren = I.severity_cell(f.get('severity'), style=_CODE_SIREN)    # own column, after '#'
        sirens.append(siren)
        code = C.M(f'<a name="{C.esc(_fkey(ctx, f))}"/>'
                   + _broken(_name(f), lw, _CODE), _CODE)
        left = _atomic([
            code, Spacer(0, 3),
            C.P(f'ID {C.val(f.get("finding_id")) or "not recorded"}', 'dense_muted')], T.COL3 - 2 * T.CELL_PAD_H)
        left._v04_code = _name(f)
        hosts, n = f.get('affected_assets'), _count(f)
        right = [C.P(f['rationale_source'], 'cell') if f.get('rationale_source') else
                 C.P(f'Rationale: {C.missing_text({"reason_code": "not_printed_in_source"})}', 'cell_muted')]
        if not hosts:
            right.append(C.P('No affected domain recorded' + (f' (count reported: {C.fmt_number(n)})' if n else '')
                             + '.', 'dense_muted', spaceBefore=5))
        else:
            rep = C.val(f.get('affected_assets_count'))
            if rep is not None and len(hosts) > rep:      # more listed than counted: print both
                qa.add('data_mismatch', 'warn', f's04: finding {C.val(f.get("finding_id"))} lists {len(hosts)} '
                       f'affected domains but affected_assets_count={rep}', once=True)
                label = f'Affected domains ({len(hosts)} listed; count reported: {C.fmt_number(rep)})'
            elif rep:
                label = (f'Affected domains (showing {len(hosts)} of {C.fmt_number(rep)})' if len(hosts) < rep
                         else f'Affected domains ({C.fmt_number(rep)})')
            else:
                label = f'Affected domains ({len(hosts)})'
            right.append(_hosts(label, hosts))
        rows.append([C.P(str(i), 'cell_muted'), siren, [left], right])   # list cell: RL's in-row split skips bare Flowables
    num_w = _num_w(range(1, len(findings) + 1))
    sev_w = max([C.head_width('Severity')] + [s.minWidth() + 2 * T.CELL_PAD_H + 1 for s in sirens
                                              if not isinstance(s, I.SeverityIcon)])
    return _table(rows, [num_w, sev_w, T.COL3, T.CW - T.COL3 - num_w - sev_w],
                  ['#', 'Severity', 'Finding', 'Rationale and affected domains'], f'{ctx.spec.anchor}-details')


def _register_pointer(data, ctx):
    """Pointer to D.1, only when D.1 prints (same rows, title and tier rule as the register)."""
    key, _, rows, title = D.d1_register(ctx.report)
    if not rows or D.tier(len(rows), len(rows)) == 'T1':
        return []
    return [C.register_pointer(key, {'value': len(rows), 'unit': 'rows'}, title=title)]


def _findings_body(data, ctx):
    findings = _ordered(data.get('findings') or [])
    if not findings and ctx.state == 'clear':
        return []
    out = _severity_block(data) + _info_note(data) + _multi_tier_note(data)
    if not findings:
        return out + [C.P(f'Finding list: {C.missing_text({"reason_code": "not_printed_in_source"})}', 'body')]
    out.append(_summary_table(findings, ctx))
    sev_legend = C.severity_legend([(k, n) for k, n, _ in _severity_groups(data)])     # on the heading line
    out += [C.heading_legend(C.heading('Finding details', 2, style=_H2_FLUSH), sev_legend), _detail_table(findings, ctx)]
    cov = data.get('coverage_note_source')
    if cov:
        out.append(C.note(C.sentence(cov.split(':', 1)[1] if cov.lower().startswith('note:') else cov)))
    bare = list(dict.fromkeys(h for f in findings for h in f.get('affected_assets') or [] if '.' not in h))
    if bare:
        out.append(C.note(f'Asset labels without a domain ({", ".join(bare)}) are shown as recorded in the source.'))
    return out + _register_pointer(data, ctx)


# --- sub-modules (own state each) -----------------------------------------------
def _card_kw(obj, state):
    reason = obj.get('state_reason') or (C.reason_text(obj) if obj.get('reason_code') else None)
    detail = obj.get('narrative_source') or obj.get('summary_source')
    if state == 'clear' and not reason:
        reason, detail = detail, None
    checked = obj.get('what_checked') or detail
    if state == 'clear' and not checked:      # clear always says what was checked, or why it cannot
        checked = C.missing_text({'reason_code': 'not_printed_in_source'})
    return {'reason': reason, 'what_checked': checked, 'next_step': obj.get('next_step')}


FULL = ('findings', 'partial', 'pending_review')     # sub-checks that get heading + card + body


def _module(title, obj, body, ctx):
    state = obj.get('state') or 'findings'
    out = [C.heading(title, 2, key=f"s04-{title.lower().replace(' ', '-')}")]   # Appendix D links here
    if state != 'findings':
        out.append(C.state_card(state, **_card_kw(obj, state)))
    return [C.keep(*(out + body(obj, ctx)))]   # short module: one unit


def _brief(obj):
    """One-line result for the 'Other checks' row (controls / redirect outcome)."""
    ctl = ', '.join(f'{k.get("control")} {_human(k.get("result")).lower()}' for k in obj.get('controls') or [])
    return C.sentence(ctl) if ctl else None


def _other_row(title, obj):
    if obj is None:    # missing is never silent inside an assessed section
        return [C.P(title, 'cell'), C.state_chip('unavailable'), C.P('Not included in the assessment data.', 'cell')]
    state = obj.get('state') or 'findings'
    kw = _card_kw(obj, state)
    res = C.sentence(_human(obj['result'])) if obj.get('result') else None
    said = str(C.val(obj.get('state_label_source')) or '').lstrip('#').strip()   # e.g. 'HTTPS Redirect — Secure'
    parts = [_brief(obj), C.sentence(kw['reason']) if kw['reason'] else
             (res if state == 'clear' else C.sentence(C.reason_text(None))),
             f'Source: “{said}”.' if said else None]
    if state not in NO_RESULT and kw['what_checked']:
        parts.append(f'What was checked: {C.sentence(kw["what_checked"])}')
    if kw['next_step']:
        parts.append(f'Next: {C.sentence(kw["next_step"])}')
    return [C.P(title, 'cell'), C.state_chip(state), C.P(' '.join(p for p in parts if p), 'cell')]


_ANY = object()


def _linked_actions(ctx, finding_id=_ANY):
    """Actions linked to section 04; with finding_id, only those citing it (None cites nothing)."""
    acts = ((ctx.report.get('sections') or {}).get('priority_actions') or {}).get('actions') or []
    return [a for a in acts if ctx.spec.key in (a.get('linked_sections') or [])
            and (finding_id is _ANY or finding_id is not None and finding_id in (a.get('linked_finding_ids') or []))]


def _dmarc_mode(k):
    v = k.get('dmarc_policy')
    v = v.get('value') if isinstance(v, dict) else v
    return str(v).lower().removeprefix('p=').strip() if v else None


def _dmarc_conflict(k, ctx):
    """(action, mode) when a priority action asks to raise DMARC to a policy already recorded."""
    mode = _dmarc_mode(k)
    if DMARC_RANK.get(mode) is None:
        return None
    acts = _linked_actions(ctx, k.get('finding_id')) or [a for a in _linked_actions(ctx)
                                                         if 'dmarc' in str(a.get('title')).lower()]
    for a in acts:
        text = f'{a.get("title")} {a.get("action_required_source") or ""}'.lower()
        target = next((t for t in ('reject', 'quarantine') if f'p={t}' in text or f'"{t}"' in text
                       or f'to {t}' in text), None)
        if target and DMARC_RANK[mode] >= DMARC_RANK[target]:
            return a, mode
    return None


def _controls_body(obj, ctx):
    controls = obj.get('controls') or []
    if not controls:
        return [C.P(f'Control results: {C.missing_text({"reason_code": "not_printed_in_source"})}', 'body')]
    rows, notes = [], []
    for k in controls:
        name = k.get('control') or 'Unnamed control'
        purpose = CONTROL_PURPOSE.get(str(name).upper()) or (C.val(k.get('line_source')) or '').partition('–')[2].strip()
        lines = [C.esc(C.sentence(purpose))] if purpose else []
        for field, v in k.items():
            if isinstance(v, dict) and 'value' in v:
                label = FIELD_LABELS.get(field) or C.sentence(field.replace('_', ' ')).rstrip('.')
                val = f'{v["value"]}-bit' if field == 'key_strength_bits' and not C.is_missing(v) else C.fmt_value(v)
                lines.append(f'<font color="{C.hexstr(T.MUTED)}">{C.esc(label)}: {C.esc(val)}</font>')
                if field == 'dmarc_policy' and C.is_missing(v):
                    acts = _linked_actions(ctx, k.get('finding_id'))
                    tail = f' before acting on priority action {acts[0].get("rank")}' if acts else ''
                    lines.append(C.esc(f'Verify the published DMARC policy (p=){tail}.'))
        if C.val(k.get('line_source')):      # the source's own line, quoted under our reading
            lines.append(f'<font color="{C.hexstr(T.MUTED)}">Source: “{C.esc(C.val(k["line_source"]))}”</font>')
        res = C.val(k.get('result'))
        chip = I.yes_no_label(RESULT_PASS.get(res), _human(res), style=T.STYLES['chip'],
                              status=None if res in RESULT_PASS else 'unknown')
        if str(name).upper() == 'DMARC' and k.get('result') == 'enabled' and _dmarc_mode(k) == 'none':
            chip = I.status_label('partial', 'Enabled, monitoring only (p=none)', 'monitoring_only',
                                  style=T.STYLES['chip'])
        hit = _dmarc_conflict(k, ctx) if str(name).upper() == 'DMARC' else None
        if hit:
            a, mode = hit
            notes.append(f'The recorded DMARC policy is already p={mode}, but priority action {a.get("rank")} '
                         f'(“{a.get("title")}”) asks to raise it. The two do not agree; verify the published DMARC '
                         'record before acting.')
            qa.add('data_mismatch', 'warn', f's04: DMARC p={mode} but action {a.get("action_id")} asks to upgrade',
                   once=True)
        rows.append([C.P(name, 'cell_head'), chip, C.M('<br/>'.join(lines) or C.esc(C.missing_text()), 'cell')])
    names = {str(k.get('control') or '').upper() for k in controls}
    for name in REQUIRED_CONTROLS:
        if name not in names:
            rows.append([C.P(name, 'cell_head'), I.yes_no_label(None, 'Not reported', style=T.STYLES['chip']),
                         C.M(C.esc(C.sentence(CONTROL_PURPOSE[name])) + f'<br/><font color="{C.hexstr(T.MUTED)}">'
                             'No result for this control in the assessment data; not a pass.</font>', 'cell')])
    out = [_no_orphans(C.compact_table(['Control', 'Result', 'What it does and what was recorded'], rows,
                                       widths=[64, 118, T.CW - 182]))]
    out += [C.note(n) for n in notes]
    if obj.get('guidance_source'):
        out.append(C.note(obj['guidance_source']))
    return out


def ip_order(rows):
    """IP rows by abuse score, highest first; held (-1) and blank scores last (policy lists.ip_reputation.sort)."""
    def key(r):
        n = C.val(r.get('abuse_score'))
        ok = isinstance(n, (int, float)) and not isinstance(n, bool) and not _is_sentinel(r.get('abuse_score'))
        return (0, -n) if ok else (1, 0)
    return sorted([r for r in rows if isinstance(r, dict)], key=key)


def _ip_body(obj, ctx):
    rows = [r for r in obj.get('rows') or [] if isinstance(r, dict)]
    if not rows:      # the state card carries the summary; add the count only when recorded
        n = obj.get('ips_checked')
        return [C.P(f'IP addresses checked: {C.fmt_value(n)}', 'body')] if n is not None else []
    total, head, tail = len(rows), [], []
    if D.tier(total, total) != 'T1':      # long list: top rows here, every row in D.1.2 (same order)
        rid = f'{D.RID["s04"]}.2'
        rows = ip_order(rows)[:D.pol('lists.ip_reputation.top_n', 10)]
        head = [C.P(f'Showing the {len(rows)} highest abuse scores of {total} IP addresses; {rid} lists every row.',
                    'body')]
        tail = [C.register_pointer(rid, {'value': total, 'unit': 'rows'},
                                   title=D.pol('lists.ip_reputation.register_title', 'IP reputation'))]
    cols = ['ip_address', 'isp', 'country', 'abuse_score', 'reports']
    table, notes = _footnoted([[r.get(c, {'value': None, 'reason_code': 'not_printed_in_source'}) for c in cols]
                               for r in rows], numeric=(3, 4))
    table = [[C.tech(C.val(r[0]), 'cell_tech') if isinstance(C.val(r[0]), str) else r[0], *r[1:]] for r in table]
    if notes:      # footnotes ride in a spanning tail row, kept with the last data row
        table.append([notes] + [''] * (len(cols) - 1))
    st = T.STYLES['cell_tech']      # IP column fits the longest address (full IPv6 is 39 characters)
    ip_w = max([170] + [stringWidth(str(C.val(r.get('ip_address')) or ''), st.fontName, st.fontSize) + 2 * T.CELL_PAD_H + 1
                        for r in rows])
    t = _no_orphans(C.compact_table(['IP address', 'ISP', 'Country', 'Abuse score', 'Reports'], table,
                                    widths=[ip_w, 282 - ip_w, 82, 76, T.CW - 440], numeric_cols=(3, 4)))
    if notes:
        t.setStyle([('SPAN', (0, -1), (-1, -1)), ('NOSPLIT', (0, -3), (-1, -1)),
                    ('TOPPADDING', (0, -1), (-1, -1), 5), ('LINEBELOW', (0, -1), (-1, -1), T.HAIRLINE, T.WHITE)])
    return head + [t] + tail


def _https_body(obj, ctx):
    said = str(C.val(obj.get('state_label_source')) or '').lstrip('#').strip()
    pairs = [('Result', _human(obj['result']) if obj.get('result') else
              {'value': None, 'reason_code': 'not_printed_in_source'})] + ([('Source', f'“{said}”')] if said else [])
    out = [C.key_value_list(pairs, width=T.COL2)]
    st, told = obj.get('state') or 'findings', obj.get('narrative_source')
    if told and st != 'findings' and told in _card_kw(obj, st).values():      # the card above already prints it
        told = None
    return out + ([C.P(told, 'body', spaceBefore=6)] if told else [])


SUBCHECKS = (('Email and DNS security controls', 'email_dns_controls', _controls_body),
             ('IP reputation', 'ip_reputation', _ip_body),
             ('HTTPS redirect', 'https_redirect', _https_body))


def _submodules(data, ctx, required):
    """Findings / partial / pending_review sub-checks get a full block; clear, no-result and
    missing ones collapse into one 'Other checks' table (no near-empty spill pages)."""
    out, rows = [], []
    for title, key, body in SUBCHECKS:
        obj = data.get(key)
        if obj is not None and (obj.get('state') or 'findings') in FULL:
            out += _module(title, obj, body, ctx)
        elif obj is not None or required:
            rows.append(_other_row(title, obj))
    if rows:      # travels with the module before it: never a short table alone on a page
        other = [C.heading('Other checks', 2),
                 _no_orphans(C.compact_table(['Check', 'Result', 'Note'], rows, widths=[150, 104, T.CW - 254]))]
        out += [C.keep(out.pop() if out else other.pop(0), *other)]
    return out


# --- next steps -----------------------------------------------------------------
def _actions(ctx):
    acts = _linked_actions(ctx)
    if not acts:
        return []
    rows = [[a.get('rank') if a.get('rank') is not None else i, C.severity_icon(a.get('priority')),
             a.get('title') or {'value': None, 'reason_code': 'not_printed_in_source'},
             a.get('required_role') or {'value': None, 'reason_code': 'not_assigned'},
             a.get('estimated_time_reported') or {'value': None, 'reason_code': 'not_printed_in_source'}]
            for i, a in enumerate(acts, 1)]
    num_w = _num_w(r[0] for r in rows)
    prio = [str(C.val(a.get('priority')) or '').lower() for a in acts]
    return [C.heading_legend(C.heading('Related priority actions', 2),
                             C.severity_legend([(k, prio.count(k)) for k in SEVERITIES])),
            _no_orphans(C.compact_table(['#', 'Priority', 'Action', 'Required role', 'Time'], rows,
                                        widths=[num_w, C.head_width('Priority'),
                                                T.CW - 210 - num_w - C.head_width('Priority'), 120, 90],
                                        numeric_cols=(0,))),
            C.note('Owners, due dates and status are listed with each action in section 02.')]


# --- contract -------------------------------------------------------------------
def _is_sentinel(v):
    if isinstance(v, dict):
        return str(v.get('source_label')).strip() == '-1' or v.get('value') == -1
    return v == -1 or str(v).strip() == '-1'


def adjust(data, report):
    """IP reputation rows carrying the '-1' sentinel: the meaning is unconfirmed, so the check is
    held for review (never 'No findings' / 'Clean') and the source label is printed."""
    ip = data.get('ip_reputation')
    rows = [r for r in (ip or {}).get('rows') or [] if isinstance(r, dict)]
    cols = list(dict.fromkeys(k for r in rows for k, v in r.items() if _is_sentinel(v)))
    if not cols:
        return data
    held = {'value': None, 'state': 'pending_review', 'reason_code': 'sentinel_meaning_unconfirmed',
            'source_label': '-1'}
    fixed = [{k: (held if _is_sentinel(v) and C.val(v) is not None else v)    # scalar or {value: -1}; nulls stay
              for k, v in r.items()} for r in rows]
    if ip.get('state') == 'pending_review' and ip.get('state_reason'):      # the source's own reason stays
        return {**data, 'ip_reputation': {**ip, 'rows': fixed}}
    label = ip.get('state_label_source')
    names = [k.replace('_', ' ') for k in cols]
    names = ' and '.join(filter(None, [', '.join(names[:-1]), names[-1]]))
    why = (f'The source printed “-1” for the {names}' + (f' and labelled this check “{label}”' if label else '')
           + '. What -1 means is not confirmed, so the result is held for review, not read as clean.')
    if ip.get('state') != 'pending_review':
        qa.add('state_adjusted', 'info', f's04 IP reputation: {ip.get("state")} -> pending_review '
               '(sentinel_meaning_unconfirmed)', once=True)
    return {**data, 'ip_reputation': {**ip, 'rows': fixed, 'state': 'pending_review',
                                      'reason_code': 'sentinel_meaning_unconfirmed', 'state_reason': why}}


class SplitBar(Flowable):
    """Stacked bar: one segment per (count, colour), widths in proportion to their sum."""
    H, GAP = 9.0, 1.0

    def __init__(self, parts):
        super().__init__()
        self.parts = [(n, c) for n, c in parts if n]

    def wrap(self, aw, ah):
        self.width, self.height = aw, self.H
        return self.width, self.height

    def draw(self):
        total, x = sum(n for n, _ in self.parts) or 1, 0.0
        for n, color in self.parts:
            w = self.width * n / total
            self.canv.setFillColor(color)
            self.canv.rect(x, 0, max(0.5, w - self.GAP), self.H, stroke=0, fill=1)
            x += w


def _host(label):
    """'portal.example.com / 192.0.2.10' -> 'portal.example.com' (the scanned-list form)."""
    return str(C.val(label) or '').split(' / ')[0].strip().lower().rstrip('.')


def _scan_hits(data, names):
    """{scanned host: index of its worst severity} from the hosts each finding lists, plus whether some
    finding lists fewer hosts than it counts (then the hit count is a lower bound) and hosts that findings
    name but the scanned list does not."""
    worst, partial, scanned = {}, False, set(names)
    for f in (x for x in data.get('findings') or [] if isinstance(x, dict)):
        lst = [h for h in f.get('affected_assets') or [] if _host(h)]
        partial |= (_count(f) or 0) > len(lst)
        sev = str(C.val(f.get('severity')) or '').lower()
        rank = SEVERITIES.index(sev) if sev in SEVERITIES else len(SEVERITIES)
        for h in map(_host, lst):
            worst[h] = min(worst.get(h, rank), rank)
    return ({h: r for h, r in worst.items() if h in scanned}, partial,
            sorted(h for h in worst if h not in scanned))


def _scanned_assets(data):
    """Scanned assets (owner design 2026-10-19): 'X of Y scanned domains have at least one finding' as the
    headline, a bar split by each domain's worst severity, then the domain grid: affected domains first with
    their worst-severity siren, the rest muted. Counts come from the hosts the findings list; no host list
    in any finding -> plain scope line (never a false 0 of Y)."""
    sa = data.get('scanned_assets')
    if C.is_missing(sa) and isinstance(sa, dict):      # null record: say why the list is not shown
        return [C.keep(C.heading('Scanned assets', 2), C.P(C.sentence(C.missing_text(sa)), 'body'))]
    if not isinstance(sa, dict):
        return []
    doms, subs = list(sa.get('domains') or []), list(sa.get('subdomains') or [])
    if not doms and not subs:
        return []
    names = list(dict.fromkeys(_host(n) for n in doms + subs if _host(n)))
    plural = lambda n, w: f'{C.fmt_number(n)} {w}{"" if n == 1 else "s"}'
    scope = 'Scanned: ' + ' and '.join(plural(len(x), w) for x, w in ((doms, 'domain'), (subs, 'subdomain')) if x) + '.'
    finds = [f for f in data.get('findings') or [] if isinstance(f, dict)]
    # no finding at all is a known 0 (all good); findings without any host list are an unknown X
    listed = not finds or any(f.get('affected_assets') for f in finds)
    hits, partial, outside = _scan_hits(data, names) if listed else ({}, False, [])
    out = [C.heading('Scanned assets', 2)]
    if listed:
        n, total = len(hits), len(names)
        head = C.M(f'{C.fmt_number(n)}<font name="{T.LIGHT}" size="12" color="{C.hexstr(T.MUTED)}"> of '
                   f'{C.fmt_number(total)}</font>', 'kpi_value')
        label = C.P(('At least ' if partial else '') + ('scanned domain has' if total == 1 else
                    'scanned domains have') + ' at least one finding', 'kpi_label', spaceBefore=2)
        by = Counter(hits.values())
        parts = [(by[i], T.SEVERITY[s]) for i, s in enumerate(SEVERITIES)] + \
                [(by[len(SEVERITIES)], T.SLATE_400), (total - n, T.RULE)]
        legend = [I.severity_label(s, dense=True, label=f'{C.fmt_number(by[i])} {s.capitalize()}')
                  for i, s in enumerate(SEVERITIES) if by[i]]
        legend += [C.P(f'{C.fmt_number(by[len(SEVERITIES)])} severity not recorded', 'dense_muted')] * bool(by[len(SEVERITIES)])
        legend += [C.P(f'{C.fmt_number(total - n)} no finding reported', 'dense_muted')] * bool(total - n and n)
        if not n:      # all good: a full green bar and one positive line, not an empty-looking grey track
            parts = [(total, T.STATUS['good'])]
            legend = [I.status_label('clear', 'No finding on any scanned domain', 'clear', dense=True)]
        dn = T.STYLES['dense']        # items packed left: each column fits its text (+ siren) and a gap
        lw = [stringWidth(getattr(x, 'text', '') or x.getPlainText(), dn.fontName, dn.fontSize) + 30 for x in legend]
        lw[-1] = max(lw[-1], T.CW - T.COL3 - T.GUTTER - sum(lw[:-1]))
        leg = Table([legend], colWidths=lw, hAlign='LEFT')
        leg.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                                 ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
        top = Table([[[head, label], '', [Spacer(0, 9), SplitBar(parts), Spacer(0, 6), leg]]],
                    colWidths=[T.COL3, T.GUTTER, T.CW - T.COL3 - T.GUTTER], hAlign='LEFT', spaceAfter=8)
        top.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                                 ('RIGHTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 8),
                                 ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                                 ('LINEABOVE', (0, 0), (-1, 0), 0.75, T.RULE)]))
        out.append(top)
    order = sorted(names, key=lambda h: hits.get(h, 99))          # affected first, worst first; stable
    st = T.STYLES['dense_tech']
    muted = st.clone('scan_muted', textColor=T.MUTED)
    siren_w = 14 if hits else 0
    widest = max(stringWidth(h, st.fontName, st.fontSize) for h in order) + 8 + siren_w
    k = max(1, min(4, int(T.CW // widest)))
    cells = [I.severity_label(SEVERITIES[hits[h]], dense=True, label=h, style=st)
             if h in hits and hits[h] < len(SEVERITIES) else C.P(C.esc(h), st if h in hits or not hits else muted)
             for h in order]
    grid = [cells[i:i + k] + [''] * (k - len(cells[i:i + k])) for i in range(0, len(cells), k)]
    t = Table(grid, colWidths=[T.CW / k] * k, hAlign='LEFT', spaceAfter=4)
    t.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                           ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                           ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    clean = len(names) - len(hits)
    note = scope + (' Domains with a finding come first, marked by their highest severity; the rest are grey.'
                    if hits and clean else ' Each domain is marked by its highest severity.' if hits else '')
    if outside:
        note += (f' {plural(len(outside), "host")} named in the findings {"is" if len(outside) == 1 else "are"} '
                 'not in the scanned list.')
    return out + [t, C.P(note, 'note_flush', spaceAfter=6)]


SCAN_STATUS = {'clean': ('clear', 'Clean'), 'scanned': ('findings', 'Scanned')}


def _active_scan(data, ctx):
    """'Vulnerability Scan Results' (active scan per host): status as printed (Clean / Scanned), scan time,
    reported vs listed finding counts, then the listed findings of each host. Informational findings
    are not a severity tier."""
    sc = data.get('active_scan')
    if not isinstance(sc, dict):
        return []
    res = [r for r in sc.get('results') or [] if isinstance(r, dict)]
    out = [C.heading('Vulnerability scan results', 2)]
    state = sc.get('state') or ('findings' if res else 'unavailable')
    if state in NO_RESULT:
        return out + [C.state_card(state, **_card_kw(sc, state))]
    if not res:      # a result state without host rows: a card only with a reason the payload gives
        kw = _card_kw(sc, state)
        if state == 'clear':
            return out + [C.state_card(state, **kw)]
        none = C.P(f'Host results: {C.missing_text({"reason_code": "not_printed_in_source"})}', 'body')
        return out + ([C.state_card(state, **kw)] if kw['reason'] and state != 'findings' else []) + [none]
    status = [str(C.val(r.get('status'))).lower() for r in res]
    clean, found = status.count('clean'), status.count('scanned')
    other = len(res) - clean - found
    out.append(C.P(f'{len(res)} host{"s" if len(res) != 1 else ""} scanned: {clean} clean, {found} with findings '
                   'reported' + (f', {other} with no recognised status' if other else '') + '.', 'body'))
    rows, mismatch = [], []
    for r in res:
        st = C.val(r.get('status'))
        key, word = SCAN_STATUS.get(str(st).lower(), ('unavailable', str(st or 'Not recorded')))
        listed = len(r.get('findings') or [])
        rep = C.val(r.get('findings_reported'))
        if rep is None:
            cnt = str(listed) if listed else '0'
        elif rep != listed:
            cnt = f'{rep} reported, {listed} listed'
            mismatch.append((r.get('target'), rep > listed))
        else:
            cnt = str(rep)
        rows.append([C.tech(str(C.val(r.get('target')) or 'Host not recorded'), 'cell_tech'), I.state_label(key, label=word, style=T.STYLES['cell']),
                     C.fmt_date(r['scanned_at']) if r.get('scanned_at') else {'value': None, 'reason_code': 'not_printed_in_source'},
                     cnt])
    out.append(_no_orphans(C.compact_table(['Host', 'Result', 'Scanned', 'Findings'], rows,
                                           widths=[T.CW - 340, 110, 110, 120])))
    if mismatch:
        qa.add('data_mismatch', 'warn', f's04: active scan finding counts differ from the listed findings for '
               f'{", ".join(str(t) for t, _ in mismatch)}', once=True)
        fewer = {d for _, d in mismatch}
        how = ('lists fewer findings than it counts' if fewer == {True} else
               'lists more findings than it counts' if fewer == {False} else
               'lists fewer findings than it counts for some hosts and more for others')
        out.append(C.note(f'Where the reported count differs from the findings listed, the source {how}; '
                          'the difference is not explained by the source data.'))
    for r in res:
        fs = [f for f in r.get('findings') or [] if isinstance(f, dict)]
        recs = [C.val(x) for x in r.get('recommendations_source') or [] if C.val(x)]
        if not fs and not C.val(r.get('summary_source')) and not recs:
            continue
        frows = []
        for f in fs:
            sev = str(C.val(f.get('severity')) or '').lower()
            lines = [C.esc(C.val(f.get('description')) or '')]
            for k, lbl in (('impact', 'Impact'), ('remediation', 'Remediation')):
                if C.val(f.get(k)):
                    lines.append(f'<font color="{C.hexstr(T.MUTED)}">{lbl}: {C.esc(C.val(f[k]))}</font>')
            frows.append([len(frows) + 1,
                          'Informational' if sev in INFO else C.severity_icon(sev) if sev in SEVERITIES
                          else C.P(str(sev or 'Not recorded').capitalize(), 'cell'),
                          C.P(C.val(f.get('title')) or 'Untitled finding', 'cell_head'),
                          C.M('<br/>'.join(x for x in lines if x), 'cell')])
        # siren-only cells fit the header; a visible word (Informational, unknown term) sets the width
        sev_w = max([C.head_width('Severity')] + [(x[1].minWidth() + 2 * T.CELL_PAD_H + 1) if hasattr(x[1], 'minWidth')
                                                 else C.head_width(x[1]) for x in frows if not isinstance(x[1], I.SeverityIcon)])
        head = [C.P(f'Findings on {C.val(r.get("target")) or "host not recorded"}', 'h3')]
        word = lambda k, d: str(C.val(r.get(k)) or d).lstrip('#').strip()      # source label, '# ' removed
        if C.val(r.get('summary_source')):
            if C.val(r.get('summary_label_source')):
                head.append(C.P(word('summary_label_source', ''), 'card_label', keepWithNext=1))
            head.append(C.P(C.val(r['summary_source']), 'body'))
        tail = ([C.P(word('recommendations_label_source', 'Recommendations'), 'card_label',
                     spaceBefore=4, keepWithNext=1), *C.bullets(recs)] if recs else [])
        num_w = _num_w(range(1, len(frows) + 1))
        body = [_no_orphans(C.compact_table(['#', 'Severity', 'Finding', 'Detail'], frows, numeric_cols=(0,),
                                            widths=[num_w, sev_w, 150, T.CW - 150 - sev_w - num_w]))] if frows else []
        out += [C.keep(*head, *body)] + tail
    return out


def build(data, ctx):
    metrics = [m for m in data.get('metrics') or [] if isinstance(m, dict)
               and str(m.get('id', '')).removeprefix('finding_types_') not in (*SEVERITIES, *GROUPS)
               and m.get('id') not in HIDDEN_KPIS]
    out = [C.kpi_strip(metrics)] if metrics else []
    out += C.flag_notes(data, ctx.report)      # counts the source prints elsewhere and does not reconcile
    out += _scanned_assets(data)
    out += _by_domain(ctx)
    out += _findings_body(data, ctx)
    out += _active_scan(data, ctx)
    out += _submodules(data, ctx, required=True)
    return out + _actions(ctx)


def build_context(data, ctx):
    """Section not assessed / unavailable: still show sub-checks that have their own result."""
    return _submodules(data, ctx, required=False)


# --- state variants demo (synthetic copies of the fixture section) --------------
def _variants(base):
    import copy

    def v(name, **kw):
        d = copy.deepcopy(base)
        d.update(kw, title=f'Vulnerabilities: {name}')
        if 'findings' in kw and 'metrics' not in kw:      # keep metrics consistent with the subset
            d['metrics'] = [dict(m, value=len(d['findings'])) if m['id'] == 'finding_types' else m
                            for m in base['metrics'] if m['id'] in ('vulnerability_score', 'finding_types')]
        return name, d

    m0 = [{'id': 'finding_types', 'label': 'Finding types', 'value': 0, 'unit': 'finding_types', 'state': 'clear'},
          {'id': 'vulnerability_score', 'label': 'Vulnerability score', 'value': None, 'unit': 'percent',
           'state': 'unavailable', 'reason_code': 'not_printed_in_source'}]
    hosts = [f'svc-{i:03d}.edge.example.com' for i in range(260)]     # long row: forces an in-row split
    many = dict(copy.deepcopy(base['findings'][0]), affected_assets=hosts, affected_assets_count=len(hosts))
    ok = lambda c, r='enabled': {'control': c, 'result': r, 'state': 'clear'}  # noqa: E731
    return [
        v('findings, alternate sub-checks', findings=[many] + base['findings'][-2:],
          summary='Synthetic: 3 finding types; sub-checks in other states.',
          email_dns_controls={'state': 'findings', 'controls': [
              ok('SPF'), {'control': 'DKIM', 'result': 'weak', 'state': 'findings',
                          'key_strength_bits': {'value': 1024, 'unit': 'bits'}},
              {'control': 'DMARC', 'result': 'enabled', 'state': 'clear', 'dmarc_policy': {'value': 'reject'}},
              ok('DNSSEC', 'valid')]},
          ip_reputation={'state': 'findings', 'rows': [
              {'ip_address': '203.0.113.7', 'isp': 'Example Transit', 'country': 'NL', 'abuse_score': 87,
               'reports': 14}]},
          https_redirect={'state': 'findings', 'result': 'no_redirect',
                          'narrative_source': 'HTTP requests are served without a redirect to HTTPS.'}),
        v('clear', state='clear', findings=[], metrics=m0,
          summary='No finding types were reported for the hosts scanned.',
          empty_state_source={'text': 'No vulnerability finding types were reported for the 28 observed hosts.',
                              'coverage': ['TLS configuration and cipher suites', 'HTTP security headers',
                                           'DNS records (CAA, DNSSEC)']},
          email_dns_controls={'state': 'clear', 'controls': [ok(k) for k in ('SPF', 'DKIM', 'DMARC')]},
          ip_reputation={'state': 'clear', 'summary_source': 'Checked 2 IP(s) against threat intelligence feeds.',
                         'state_reason': 'No abuse reports were returned for the IPs checked.'}),
        v('partial', state='partial', findings=base['findings'][:4],
          summary='Synthetic: 4 finding types on the hosts covered.',
          state_reason='TLS checks completed for 20 of 28 observed hosts',
          what_checked='Header and DNS checks covered all hosts.',
          ip_reputation={'state': 'unavailable', 'state_reason': 'The threat intelligence feed did not respond.'}),
        v('pending review', state='pending_review', findings=base['findings'][:2], reason_code='count_unreconciled',
          summary='Synthetic: 2 finding types, counts held for review.',
          email_dns_controls={'state': 'unavailable', 'reason_code': 'not_printed_in_source'}),
        v('not assessed', state='not_assessed', reason_code='module_not_assessed', findings=[],
          summary='Vulnerability scanning was not part of this assessment.',
          next_step='Enable external vulnerability scanning for the next assessment cycle.',
          email_dns_controls=None, ip_reputation=None),
        v('unavailable', state='unavailable', findings=[], state_reason='The scanner returned no data for this window',
          summary='No vulnerability result is available for this assessment.',
          email_dns_controls=None, ip_reputation=None, https_redirect=None),
        v('not applicable', state='not_applicable', findings=[], summary='No external attack surface in scope.',
          state_reason='No internet-facing hosts were in scope', email_dns_controls=None, ip_reputation=None,
          https_redirect=None),
    ]


def demo(src, out):
    """Render every state variant into one PDF, run QA, assert no errors."""
    import dataclasses
    import json
    from pathlib import Path

    from ..build import contents_flowables
    from ..page import ReportDoc, cover_flowables, identity_from_report
    from . import BY_ID, render_section
    report = json.loads(Path(src).read_text(encoding='utf-8'))
    specs = []
    for i, (name, d) in enumerate(_variants(report['sections']['vulnerabilities'])):
        key = f'vulnerabilities__v{i}'
        report['sections'][key] = d
        specs.append(dataclasses.replace(BY_ID['s04'], id=f's04v{i}', key=key))
    identity = identity_from_report(report)
    doc = ReportDoc(str(out), identity)
    story = cover_flowables() + contents_flowables(specs, report, identity)
    for s in specs:
        story += render_section(s, report, identity)
    total = doc.render(story)
    issues = list(qa.ISSUES) + qa.check_pdf(str(out), table_parts=doc.table_parts, table_heads=C._TABLE_HEADS)
    counts = qa.write_report(Path(out).with_suffix('.qa.json'), out, issues, pages=total)
    print(f'{out}: {total} pages; QA {counts}')
    assert counts['error'] == 0, issues
    return total


if __name__ == '__main__':
    import sys
    demo(*sys.argv[1:3])
