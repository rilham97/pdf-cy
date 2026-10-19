"""13 Certifications: certificates on record + commonly referenced standards.

Layout: KPI strip -> certificate table (columns that are missing for EVERY
certificate with one shared reason collapse into a single note, so the table
stays compact and every missing value still prints its reason) -> source
URL(s) -> reference standards (explicitly not evidence about the vendor).

Origin (how the record got here: detected / uploaded) and status (the app's decision:
Awaiting approval / Approved / Rejected; one wording for detected and uploaded) are separate
(U1 Q12); a detected or an uploaded certificate can be rejected. Approval is never called "verified".
Weighting (business answer 2026-10-15: pending 1, approved 2, rejected 0) stays internal: no credit,
points, caps or eligibility are printed; `credit_applied` is read for QA only. Expiry is the
payload flag `expired` (set by the system): dates are shown, never compared.

Also hosts small helpers reused by s06/s14: field(), drop_missing_columns(),
LinkTech, sources_list().
"""
from datetime import date
from urllib.parse import urlsplit
from xml.sax.saxutils import quoteattr

from reportlab.platypus import Table, TableStyle

from .. import icons as I
from .. import qa
from .. import theme as T
from ..text import TechText, _para, val, esc, fmt_date, hexstr, is_missing, reason_text, sentence, tech_lines

ORIGIN = {'detected': 'System detected', 'uploaded': 'Uploaded'}
TEAM_APPROVED = ('approved', 'team_approved')      # legacy origin labels: origin detected + approved by team
PENDING = ('pending', 'pending_approval', 'awaiting_approval')
CATEGORY = {'security': 'Security', 'privacy': 'Privacy', 'both': 'Security + Privacy',
            'security_privacy': 'Security + Privacy', 'security_and_privacy': 'Security + Privacy'}


# --- shared helpers (s06/s14 import these) --------------------------------------
def field(row, key):
    """row[key], or a null record built from the '<key>_state/_reason_code/_reason' siblings."""
    v = row.get(key)
    if v is not None:
        return v
    return {'value': None, 'state': row.get(f'{key}_state'), 'reason_code': row.get(f'{key}_reason_code'),
            'reason': row.get(f'{key}_reason')}


def label(v):
    """Humanised display text for an enum-ish value; null records pass through."""
    if is_missing(v):
        return v
    if isinstance(v, dict):
        v = v.get('label') or v.get('value')
    if isinstance(v, bool):
        return 'Yes' if v else 'No'
    s = str(v).replace('_', ' ').strip()
    return s[:1].upper() + s[1:]


def reason_of(v):
    return reason_text(v) if isinstance(v, dict) else 'reason not recorded'


def drop_missing_columns(columns, rows, keep=(), noun='row', names=None):
    """Drop columns whose cells are ALL missing with ONE shared reason.
    Returns (columns, rows, note); the note names what was dropped and why (or None)."""
    idx, dropped = [], {}
    for j, col in enumerate(columns):
        cells = [r[j] for r in rows]
        reasons = {reason_of(v) for v in cells} if cells and all(is_missing(v) for v in cells) else set()
        if col not in keep and len(reasons) == 1:
            name = (names or {}).get(col, col.lower())
            dropped.setdefault(reasons.pop(), []).extend([name] if isinstance(name, str) else name)
        else:
            idx.append(j)
    note = ' '.join(f'{sentence(join(cols))[:-1]}: not available for any {noun} ({r}).'
                    for r, cols in dropped.items()) or None
    return [columns[j] for j in idx], [[r[j] for j in idx] for r in rows], note


def join(items):
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' and ' + items[-1]


def widths(columns, fixed, flex):
    """Explicit column widths (needed when cells carry markup): fixed by name, `flex` takes the rest."""
    w = [0 if h == flex else fixed.get(h, 0) for h in columns]
    w[columns.index(flex)] = T.CW - sum(w)
    return w


def stack(c, head, sub=(), style='cell', strong=False):
    """Cell with a head line and muted sub lines (all plain text, escaped here)."""
    h = esc(head)
    if strong:
        h = f'<font name="{T.MEDIUM}" color="{hexstr(T.HEADING)}">{h}</font>'
    subs = [s for s in ([sub] if isinstance(sub, str) else sub) if s]
    tail = ''.join(f'<br/><font color="{hexstr(T.MUTED)}">{esc(s)}</font>' for s in subs)
    return c.M(h + tail, style)


def _safe_url(url):
    try:
        parts = urlsplit(str(url))
    except ValueError:
        return False
    return parts.scheme in ('http', 'https') and bool(parts.netloc) and not any(ch.isspace() for ch in str(url))


class LinkTech(TechText):
    """TechText whose lines are one live link (http/https only); wraps at / . - _ @."""

    def _para(self, aw):
        lines = tech_lines(self.text, aw, self.style.fontName, self.style.fontSize)
        if not _safe_url(self.text):
            return _para('<br/>'.join(esc(s) for s in lines), self.style)
        a = f'<a href={quoteattr(self.text)} color="{hexstr(T.NAVY)}">'
        return _para('<br/>'.join(f'{a}{esc(s)}</a>' for s in lines), self.style)


def sources_list(c, urls, numbered=False):
    """Source URLs as a label/link list. Returns (ref_of_url, flowables). A single URL
    prints as 'Source' unless `numbered`; several are numbered [1], [2]..."""
    uniq = list(dict.fromkeys(u for u in map(val, urls) if u))
    refs = {u: f'[{i}]' for i, u in enumerate(uniq, start=1)}
    if not uniq:
        return refs, []
    if len(uniq) == 1 and not numbered:
        refs = {}
        return refs, [c.key_value_list([('Source', LinkTech(uniq[0], 'cell_tech'))])]
    return refs, [c.key_value_list([(refs[u], LinkTech(u, 'cell_tech')) for u in uniq])]


# --- section ------------------------------------------------------------------
def _v(x):
    return x.get('value') if isinstance(x, dict) else x


def origin(cert):
    """'detected' / 'uploaded' / other code / None. Legacy 'approved' origins are detected."""
    o = str(_v(cert.get('origin')) or '').lower()
    return 'detected' if o in TEAM_APPROVED else o or None


def approval(cert):
    """'approved' / 'pending' / 'rejected' / other code / None (not recorded)."""
    a = str(_v(cert.get('approval_state')) or '').lower()
    if not a and str(_v(cert.get('origin')) or '').lower() in TEAM_APPROVED:
        return 'approved'
    return 'pending' if a in PENDING else a or None


def std_key(cert):
    """Grouping key; an unnamed standard ('OTHER', blank) never groups with another record."""
    k = str(val(cert.get('standard')) or '').casefold().replace(' ', '')
    return k if k not in ('', 'other') else f'#{cert.get("certificate_id") or id(cert)}'


def std_name(cert):
    s = val(cert.get('standard'))
    if not s:
        return 'Standard not recorded'
    return 'Other (standard not named)' if str(s).strip().casefold() == 'other' else s


def grouped(certs):
    """Records of one standard sit together (first-seen order), detected before uploaded; a standard
    whose records are all rejected goes last (listed for completeness)."""
    first, live = {}, set()
    for i, x in enumerate(certs):
        first.setdefault(std_key(x), i)
        if approval(x) != 'rejected':
            live.add(std_key(x))
    return sorted(certs, key=lambda x: (std_key(x) not in live, first[std_key(x)], origin(x) != 'detected'))


def awaiting_review(data):
    """System-detected records awaiting approval (uploads are approved automatically on upload)."""
    return [x for x in (data or {}).get('certificates') or []
            if isinstance(x, dict) and origin(x) == 'detected' and approval(x) == 'pending']


def review_text(todo):
    names = join(list(dict.fromkeys(val(x.get('standard')) or 'standard not recorded' for x in todo)))
    n = len(todo)
    return (f'{n} system-detected certificate{"s" if n > 1 else ""} ({names}) '
            f'{"are" if n > 1 else "is"} awaiting approval. Check the source, then approve or reject '
            f'{"each" if n > 1 else "it"} in Cyberrank.')


def counted(cert):
    """Listed as held for the reference cross-check: every certificate except a rejected one."""
    return approval(cert) != 'rejected'


def _origin_chip(c, cert, ref=''):
    """Origin is a category: plain cell text, no colour. Detected: its source reference [n];
    uploaded: link to the uploaded file."""
    o = cert.get('origin')
    if is_missing(o):
        return field(cert, 'origin')
    text = ' '.join(p for p in (ORIGIN.get(origin(cert)) or label(cert.get('origin_label_source') or o), ref) if p)
    ref = cert.get('file_reference')
    out = [c.P(text, 'cell')]
    if origin(cert) == 'uploaded' and ref and not is_missing(ref):
        out.append(LinkTech(str(_v(ref)), 'dense_tech'))
    if origin(cert) == 'uploaded' and cert.get('document') is not None:
        from .app_d_evidence_registers import RID
        out.append(c.P(f'Document in Appendix {RID["s13"]}', 'note_flush'))
    if len(out) > 1:
        return out
    return text


def _approval(c, cert):
    """Icon + text; never 'verified' (approval is an app decision, not independent verification)."""
    a, st = approval(cert), T.STYLES['cell']
    if a is None:
        return field(cert, 'approval_state')
    if a == 'approved':
        return I.status_label('yes', 'Approved', 'approved', style=st)     # same wording for every origin
    if a == 'pending':
        return I.status_label('pending_review', 'Awaiting approval', 'awaiting_approval', style=st)
    if a == 'rejected':
        return I.status_label('no', 'Rejected', 'rejected', style=st)
    qa.add('unknown_term', 'warn', f's13: approval_state "{a}" is not a known approval state', once=True)
    return I.status_label('not_assessed', f'Not recognised (“{a}”)', 'unknown', style=st)


def _day(v):
    """ISO date (or {'value': ...}) -> date; None when missing or unparseable."""
    try:
        parts = [int(p) for p in str(_v(v))[:10].split('-')]
        return date(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1)
    except (TypeError, ValueError, IndexError):
        return None


def expired(cert):
    """Expiry is the system's flag (`expired` true); never computed from the dates."""
    return _v(cert.get('expired')) is True


def _validity(c, cert):
    """Dates as recorded; 'Expired' (icon + text) only from the payload flag."""
    vf, vu = field(cert, 'valid_from'), field(cert, 'valid_until')
    if is_missing(vu) and is_missing(vf):
        nd = all(isinstance(f, dict) and f.get('reason_code') == 'not_detected' for f in (vf, vu))
        text = 'Not detected by the system' if nd else None
    else:
        day = lambda f: fmt_date(f).replace(' ', ' ')       # a date never wraps inside itself
        if is_missing(vu):
            text = f'From {day(vf)}; end date not available ({reason_of(vu)})'
        else:
            text = f'{day(vf)} – {day(vu)}' if not is_missing(vf) else f'Until {day(vu)}'
    if not expired(cert):
        return vu if text is None else text
    flag = I.status_label('no', 'Expired', 'expired', style=T.STYLES['cell'])
    return [flag, c.P(text, 'cell')] if text else flag


def _num(v):
    v = _v(v)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _check_credit(cert):
    """Internal QA only: a rejected certificate never carries credit. Weighting is never printed."""
    cr = _num(field(cert, 'credit_applied'))
    if approval(cert) == 'rejected' and (cr or 0) > 0:
        qa.add('data_mismatch', 'warn', f's13: {cert.get("standard") or "a certificate"} is rejected but '
               f'credit_applied={cr}', once=True)


def _scope(x):
    cat = x.get('category')
    cat = None if is_missing(cat) else CATEGORY.get(str(_v(cat)).lower()) or label(cat)
    head = ' · '.join(p for p in (val(x.get('standard_full_name')), cat) if p)
    # uploaded certificates carry the issuer and the scope wording from the document (as received)
    extra = [f'{k}: {val(x.get(f))}' for k, f in (('Scope', 'scope_source'), ('Issuer', 'issuer'))
             if val(x.get(f))]
    if not extra:
        return head or field(x, 'standard_full_name')
    return [p for p in [head] + extra if p]


FIXED = {'Standard': 100, 'Origin': 92, 'Status': 140, 'Validity': 110}
NOTE_NAMES = {'Scope': ['scope', 'category']}


def certificates_block(c, data, ctx):
    certs = [x for x in data.get('certificates') or [] if isinstance(x, dict)]
    if not certs:
        return [c.heading('Certificates on record', 2), c.note('No certificate records in the assessment data.')]
    certs = grouped(certs)
    urls = [val(x.get('source_url')) for x in certs]
    # one 'Source' line only when every record shares it; otherwise numbered [n] in the Origin cell
    refs, src = sources_list(c, urls, numbered=len(set(urls)) > 1)

    def ref(x):
        u = val(x.get('source_url'))
        return refs.get(u) or ('[source not recorded]' if refs and origin(x) == 'detected' else '')

    for x in certs:
        _check_credit(x)
    columns = ['Standard', 'Scope', 'Origin', 'Status', 'Validity']
    rows, prev = [], None
    for x in certs:      # a second record of the same standard leaves Standard blank: one certificate, two records
        k = std_key(x)
        same = k == prev
        sc = _scope(x)       # a grouped record keeps only its own Scope / Issuer lines
        if same:
            sc = [l for l in sc if l.startswith(('Scope: ', 'Issuer: '))] if isinstance(sc, list) else ''
        rows.append(['' if same else std_name(x), sc,
                     _origin_chip(c, x, ref(x)), _approval(c, x), _validity(c, x)])
        prev = k
    columns, rows, dropped = drop_missing_columns(columns, rows, keep=('Standard', 'Origin'), noun='certificate',
                                                  names=NOTE_NAMES)
    rest = sum(FIXED[h] for h in columns if h not in ('Standard', 'Scope'))
    if 'Scope' in columns and T.CW - rest < 300:    # crowded: scope moves under the standard
        j = columns.index('Scope')
        rows = [[stack(c, r[0], c.missing_text(r[j]) if is_missing(r[j]) else r[j], 'cell', strong=True)]
                + r[1:j] + r[j + 1:] for r in rows]
        columns = ['Certificate'] + columns[1:j] + columns[j + 1:]
    elif 'Scope' in columns:
        j = columns.index('Scope')
        rows = [r[:j] + [' · '.join(r[j]) if isinstance(r[j], list) else r[j]] + r[j + 1:] for r in rows]
    flex = 'Scope' if 'Scope' in columns else columns[0]
    out = [c.heading('Certificates on record', 2),
           c.compact_table(columns, rows, widths=widths(columns, FIXED, flex))]
    notes = [dropped] if dropped else []
    if any(approval(x) == 'rejected' for x in certs):
        notes.append('Rejected certificates are listed for completeness.')
    if any(is_missing(field(x, 'approval_state')) for x in certs):
        notes.append('A listed certificate is a record of what was found, not a confirmation that it is valid '
                     'or approved.')
    head = next((m for m in data.get('metrics') or [] if isinstance(m, dict) and m.get('unit') == 'certifications_headline'
                 and isinstance(_v(m.get('value')), int)), None)
    if head and _v(head['value']) != len(certs):     # quote the source headline, then what is listed
        notes.append(f'The assessment headline counts {_v(head["value"])} certifications; {len(certs)} certificate '
                     'records are listed here.')
        qa.add('data_mismatch', 'warn', f's13: headline {_v(head["value"])} certifications vs {len(certs)} records',
               once=True)
    if notes:
        out.append(c.note(' '.join(notes)))
    out += src
    todo = awaiting_review(data)
    if todo:
        out.append(c.M(f'<font name="{T.MEDIUM}">Next step:</font> {esc(review_text(todo))}', 'body'))
    return out


def reference_block(c, data, ctx):
    ref = data.get('reference_standards') or {}
    items = [i for i in ref.get('items') or [] if isinstance(i, dict)]
    if not items:
        return []
    org = ctx.identity.get('org') or 'the organisation'
    shown = ctx.state in ('findings', 'partial', 'pending_review')   # certificate table is on the page
    held = {str(x.get('standard') or '').casefold().replace(' ', '')
            for x in (data.get('certificates') or [] if shown else []) if isinstance(x, dict) and counted(x)}
    also = [val(i['standard']) for i in items if val(i.get('standard')) and str(i.get('standard') or '').casefold().replace(' ', '') in held]
    text = (f'Reference list only: standards commonly referenced for organisations of this kind. '
            f'It is not evidence that {org} holds them.') if not ref.get('is_vendor_evidence') else ''
    if also:
        text += f' {join(also)} also appear{"s" if len(also) == 1 else ""} among the certificates on record.'
    rows = [[i.get('standard') or field(i, 'standard'), i.get('description') or field(i, 'description')]
            for i in items]
    head = c.heading('Commonly referenced standards', 2)
    if len(rows) > 10 or not text.strip():     # long list: stacked, the table may split
        return [head] + ([c.P(text.strip())] if text.strip() else []) + [c.compact_table(['Standard', 'Scope'], rows)]
    # short list: half-width table with the note beside it (one unsplittable row)
    side = Table([[c.compact_table(['Standard', 'Scope'], rows, total_width=T.COL2), c.P(text.strip(), 'body_flush')]],
                 colWidths=[T.COL2, T.CW - T.COL2], hAlign='LEFT', spaceAfter=T.SP_SM)
    side.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                              ('RIGHTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 0),
                              ('BOTTOMPADDING', (0, 0), (-1, -1), 0), ('LEFTPADDING', (1, 0), (1, 0), 2 * T.GUTTER),
                              ('TOPPADDING', (1, 0), (1, 0), T.CELL_PAD_V)]))
    return [head, side]


def adjust(data, report):
    """Business rule 2026-10-19: no certificate records -> none_identified (never 'No findings'), and the
    compliance score reads 0% when the payload gives none. With records the system's score stands."""
    if data.get('state') not in ('findings', 'clear', 'partial', 'none_identified'):
        return data
    if any(isinstance(x, dict) for x in data.get('certificates') or []):
        return data
    from . import hold
    out = hold(data, 'no_certificate_records', data.get('state_reason') or
               'No certificate records were found in the sources checked.', 'none_identified')
    ms = [{k: v for k, v in m.items() if k != 'state'}      # a metric 'clear' chip would contradict the state
          for m in out.get('metrics') or [] if isinstance(m, dict)]
    if not any(m.get('id') == 'compliance_score' and isinstance(m.get('value'), (int, float)) for m in ms):
        ms = [{'id': 'compliance_score', 'label': 'Compliance score', 'value': 0, 'unit': 'percent'}] + \
             [m for m in ms if m.get('id') != 'compliance_score']
    return {**out, 'metrics': ms}


def card(data, ctx):
    return {'title': 'No certificates identified'} if ctx.state == 'none_identified' else {}


def build(data, ctx):
    c = ctx.c
    out = []
    metrics = [m for m in data.get('metrics') or [] if isinstance(m, dict)]
    if metrics:
        out.append(c.kpi_strip(metrics))
    if data.get('certificates') or ctx.state not in ('clear', 'none_identified'):
        out += certificates_block(c, data, ctx)
    return out + reference_block(c, data, ctx)


def build_context(data, ctx):
    """not_assessed / unavailable: the reference list is generic, so it still shows."""
    return reference_block(ctx.c, data, ctx)
