"""Values and text primitives: escaping, missing-value reasons, number/date/unit
formatting, P()/M() paragraph factories, TechText for technical tokens."""
import re
from datetime import date
from xml.sax.saxutils import escape

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Paragraph

from .fonts import fallback
from .theme import MONO, MONO_K, STYLES

# --- values -------------------------------------------------------------------
REASONS = {
    'not_printed_in_source': 'not provided in the assessment data',
    'blank_in_source': 'left blank in the assessment data',
    'sentinel_meaning_unconfirmed': 'value meaning not confirmed; withheld pending review',
    'module_not_assessed': 'this module was not assessed for this report',
    'not_assigned': 'not assigned',
    'toggle_snapshot_not_printed': 'scan setting at assessment time not recorded',
    'not_tracked': 'not tracked by the assessment',
    'asset_not_extracted': 'asset not available',
    'score_context_incomplete': 'score context incomplete',
    'denominator_unavailable': 'cannot be calculated: the number of eligible targets is not available',
    'policy_state_ambiguous': 'policy state not determined; held for review',
    'not_identified': 'not identified',
    'location_unknown': 'location unknown',
    'narrative_overclaim_and_provisional_rule': 'held for review: narrative claims exceed the evidence',
    'count_unreconciled': 'counts do not reconcile; held for review',
    'no_events': 'no events to show',
    'not_derivable': 'cannot be derived from the available data',
    'standard_not_in_credit_table': 'standard not in the credit table',
    'lead_event_not_eligible': 'the event named as last valid is not scoring eligible; held for review',
    'pqc_scan_disabled': 'the post-quantum (PQC) scan was switched off for this assessment',
    'policy_state_unrecognised': 'policy state not recognised; held for review',
    'no_preference_set': 'not compared: no preference set',
    'no_login_or_payment_portal_detected': 'no customer login or payment portal was detected on the public site',
    'country_code_placeholder': 'location not identified (the source printed the placeholder code “XX”)',
    'placeholder_in_source': 'the source printed a placeholder (“#”), not a value',
    'section_not_in_source': 'not included in the source report',
    'connections_not_reported': 'connections and assessment dates not reported',
    'none_identified': 'none identified with the methods used',
    'not_detected': 'not detected by the system',
}
UNITS = {
    'percent': '%', 'finding_types': 'finding types', 'ip_addresses': 'IP addresses',
    'asset_labels': 'asset labels', 'scopes_inferred': 'scopes (inferred)',
    'records_unit_unverified': 'records (unit unverified)',
    'certifications_headline': 'certifications', 'found_headline': 'found (headline)',
}
STATE_REASON_FALLBACK = 'Reason not recorded in the assessment data.'


def plain(v):
    """Printable form of a field: a null record -> 'Not available (reason)', {'value': x} -> x.
    Guards every text path against printing a raw dict."""
    if is_missing(v) and isinstance(v, dict):
        return missing_text(v)
    return v.get('value') if isinstance(v, dict) and 'value' in v else v


def val(v):
    """Scalar of a field: null record -> None, {'value': x} -> x, else v (hashable for keys / sets)."""
    return v.get('value') if isinstance(v, dict) and 'value' in v else v


def esc(text):
    return escape(str(plain(text)))


def hexstr(color):
    return '#' + color.hexval()[2:]


def is_missing(v):
    """True for None and for {'value': None, ...} null records."""
    return v is None or (isinstance(v, dict) and 'value' in v and v['value'] is None)


def reason_text(obj):
    """Reader-facing reason for a null record / state ('reason', 'state_reason' or 'reason_code')."""
    if isinstance(obj, dict):
        if obj.get('reason'):
            return str(obj['reason'])
        if obj.get('state_reason'):
            return str(obj['state_reason'])
        obj = obj.get('reason_code')
    if not obj:
        return 'reason not recorded'
    return REASONS.get(obj, str(obj).replace('_', ' '))


def fmt_version(v):
    """Methodology version as 'Version n' (1, '2', 'v2' -> 'Version 2'); other forms pass through, nulls too."""
    x = v.get('value') if isinstance(v, dict) else v
    if x is None or isinstance(x, bool):
        return v
    m = re.fullmatch(r'(?i)(?:v(?:ersion)?\s*)?(\d+)', str(x).strip())
    return f'Version {m.group(1)}' if m else x


def missing_text(v=None):
    return f'Not available ({reason_text(v)})' if isinstance(v, dict) else 'Not available (reason not recorded)'


def sentence(text):
    text = str(plain(text)).strip()
    text = text[:1].upper() + text[1:]
    return text if text.endswith(('.', '!', '?')) else text + '.'


def fmt_number(n):
    if isinstance(n, bool):
        return 'Yes' if n else 'No'
    if isinstance(n, int):
        return f'{n:,}'
    if isinstance(n, float):
        return f'{n:,.1f}'.rstrip('0').rstrip('.')
    return str(n)


def fmt_unit(unit, n=None):
    unit = val(unit)
    u = UNITS.get(unit, str(unit or '').replace('_', ' '))
    if n == 1 and u.endswith('ies'):
        return u[:-3] + 'y'
    return u[:-1] if n == 1 and u.endswith('s') else u


def fmt_value(v, unit=None):
    """Display string for a scalar or a {'value', 'unit'} record; missing -> reason."""
    if isinstance(v, dict) and 'value' in v:
        unit = unit or v.get('unit')
        if v['value'] is None:
            return missing_text(v)
        v = v['value']
    if v is None:
        return missing_text()
    if unit == 'percent':
        return f'{fmt_number(v)}%'
    return f'{fmt_number(v)} {fmt_unit(unit, v)}'.strip() if unit else fmt_number(v)


def fmt_date(field):
    """'2026-10-02' or {'value': ..., 'precision': 'minute'|'day'|'month'|'year'} -> '02 Oct 2026'
    ('12 Oct 2026 18:29' for minute precision, the time as recorded; no time-zone conversion)."""
    if is_missing(field):
        return missing_text(field) if isinstance(field, dict) else 'Not available'
    prec = field.get('precision', 'day') if isinstance(field, dict) else 'day'
    raw = field['value'] if isinstance(field, dict) else field
    parts = [int(p) for p in str(raw)[:10].split('-')]
    d = date(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1)
    if prec == 'minute':
        return d.strftime('%d %b %Y ') + str(raw)[11:16]
    return d.strftime({'year': '%Y', 'month': '%b %Y'}.get(prec, '%d %b %Y'))


# --- text ---------------------------------------------------------------------
class MonoParagraph(Paragraph):
    """Paragraph in the mono `tech` styles: JetBrains Mono at MONO_K x the text size sits lower by the size
    difference, so its baseline lines up with the Poppins text in the same row (RL sets the first
    baseline one font size below the top)."""

    def drawOn(self, canvas, x, y, _sW=0):
        fs = self.style.fontSize
        super().drawOn(canvas, x, y - (fs / MONO_K - fs), _sW)


def _para(markup, st):
    return (MonoParagraph if st.fontName == MONO else Paragraph)(fallback(markup, base=st.fontName), st)


def P(text, style='body', **kw):
    """Paragraph from plain data text (escaped). kw overrides the style. Characters Poppins lacks switch
    to the fallback fonts (fonts.fallback) here, in M() and in TechText."""
    st = STYLES[style] if isinstance(style, str) else style
    if kw:
        st = st.clone(st.name + '_x', **kw)
    return _para(esc(text).replace('\n', '<br/>'), st)


def M(markup, style='body', **kw):
    """Paragraph from trusted inline markup (<b>, <font>, <a>). Never pass raw data."""
    st = STYLES[style] if isinstance(style, str) else style
    if kw:
        st = st.clone(st.name + '_x', **kw)
    return _para(markup, st)


_ATOMS = re.compile(r'\s+|[^\s/.\-_@]+[/.\-_@]*|[/.\-_@]+')
TECH_CHARS = '/.-_@'


def tech_lines(text, width, font, size):
    """Greedy line breaks after / . - _ @ or spaces; unbreakable runs split by
    character (no hyphen added). Never drops characters."""
    w = lambda s: stringWidth(s, font, size)
    lines, cur = [], ''
    for atom in _ATOMS.findall(str(text)):
        if atom.isspace():
            cur += ' ' if cur else ''
            continue
        if w(cur + atom) <= width:
            cur += atom
            continue
        if cur.strip():
            lines.append(cur.rstrip())
        while w(atom) > width and len(atom) > 1:
            n = max(1, max(i for i in range(1, len(atom) + 1) if w(atom[:i]) <= width or i == 1))
            lines.append(atom[:n])
            atom = atom[n:]
        cur = atom
    if cur.strip() or not lines:
        lines.append(cur.rstrip())
    return lines


def breakable(text, width, font, size):
    """Escaped markup of running text whose over-wide tokens (URLs, hashes) get line breaks at
    technical break points (tech_lines), so they never run past `width` or split mid-word."""
    return ' '.join('<br/>'.join(esc(x) for x in tech_lines(t, width, font, size))
                    if stringWidth(t, font, size) > width else esc(t) for t in str(plain(text)).split(' '))


class TechText(Flowable):
    """Paragraph for technical tokens: wraps only at technical break points."""

    def __init__(self, text, style='tech'):
        super().__init__()
        self.text = '' if text is None else str(plain(text))
        self.style = STYLES[style] if isinstance(style, str) else style
        self._p = None

    def _para(self, aw):
        lines = tech_lines(self.text, aw, self.style.fontName, self.style.fontSize)
        return _para('<br/>'.join(esc(s) for s in lines), self.style)

    def wrap(self, aw, ah):
        self._p = self._para(aw)
        self.width, self.height = self._p.wrap(aw, ah)
        return self.width, self.height

    def split(self, aw, ah):
        return self._para(aw).split(aw, ah)

    def draw(self):
        self._p.drawOn(self.canv, 0, 0)

    def minWidth(self):
        return max((stringWidth(ch, self.style.fontName, self.style.fontSize) for ch in self.text), default=0)

    def getSpaceBefore(self):
        return self.style.spaceBefore

    def getSpaceAfter(self):
        return self.style.spaceAfter


def tech(text, style='tech'):
    return TechText(text, style)


def _is_technical(s):
    return '://' in s or any(len(t) > 16 and any(c in t for c in TECH_CHARS) for t in s.split())


def note(text):
    return P(text, 'note')


def flag_notes(obj, report):
    """'Review flag RF-G04: <text>' notes for the review flags attached to obj, resolved against
    report['review_flags']; the source value stays printed as recorded next to it."""
    ids = (obj or {}).get('review_flags') if isinstance(obj, dict) else None
    texts = {f.get('id'): f.get('text') for f in (report or {}).get('review_flags') or [] if isinstance(f, dict)}
    return [note(f'Review flag {i}: {texts[i]}') for i in ids or [] if texts.get(i)]


def bullets(items, style='bullet'):
    return [Paragraph(fallback(esc(i)), STYLES[style], bulletText='•') for i in items]
