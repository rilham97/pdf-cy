"""15 Cloud infrastructure: providers and public hosting footprint from DNS / network records.

Inventory module: 'findings' means providers/endpoints were observed, not risk (chip reads
'Identified'). An empty result reads 'not detected with the methods used', never 'no cloud'.

Supports both:
  * New rich endpoint payload (`assets[]`, `detected_providers`/`detectedProviders`,
    `cloud_summary`, `evidence[]`, `last_scanned`/`scannedAt`) -> Concept B layout:
    KPI strip -> Infrastructure footprint by layer (stacked bar + layer table + neutral
    architecture note) -> Endpoints grouped by hosting provider (<= 30 inline, > 30 in Appendix D.7).
  * Legacy provider-only payload (`providers[]`, `metrics[]`, `last_scanned`, `detection_methods[]`)
    -> KPI strip + Detected providers table (unchanged for existing fixtures).
"""
import ipaddress
import re
from collections import Counter, OrderedDict
from functools import cache
from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import FILL_NON_ZERO, Drawing, Group
from reportlab.graphics.svgpath import SvgPath
from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Paragraph, Table, TableStyle

from .. import components as C
from .. import theme as T
from ..fonts import fallback
from . import app_d_evidence_registers as D

METHODS = {'dns_records': 'DNS records', 'ip_ranges': 'IP ranges', 'mx_records': 'MX records',
           'ns_records': 'NS records', 'a_record': 'A records', 'cname_record': 'CNAME records',
           'mx_record': 'MX records', 'ns_record': 'NS records'}
NOT_DETECTED = 'No cloud provider detected with the methods used'
CLEAR_REASON = ('Only providers visible in public DNS, IP-range, MX and NS records can be detected. '
                'Services reached through other providers or used only internally are not visible '
                'to this check.')

# Quiet structural palette for infrastructure layers (no status red/green/orange overload)
LAYER_ORDER = ('IaaS / Cloud Compute', 'Hosting / Infrastructure', 'SaaS / Email & Productivity',
               'DNS / Traffic Management', 'Unresolved / No IP')
LAYER_COLORS = {
    'IaaS / Cloud Compute': T.NAVY,
    'Hosting / Infrastructure': T.SAPPHIRE,
    'SaaS / Email & Productivity': HexColor('#5B89B8'),
    'DNS / Traffic Management': T.SLATE_400,
    'Unresolved / No IP': T.RULE,
}
LAYER_SHORT = {
    'IaaS / Cloud Compute': 'Cloud compute',
    'Hosting / Infrastructure': 'Hosting / own ASN',
    'SaaS / Email & Productivity': 'Email (MX)',
    'DNS / Traffic Management': 'DNS (NS)',
    'Unresolved / No IP': 'Unresolved DNS',
}

_H2_TIGHT = T.STYLES['h2'].clone('s15_h2_tight', spaceAfter=0)
_GRP_META = T.STYLES['dense_muted'].clone('s15_grp_meta', alignment=2)
_CELL_SUB = T.STYLES['dense_muted'].clone('s15_cell_sub', fontSize=7.0, leading=9.5)
_CELL_SUB_TECH = T.STYLES['dense_tech'].clone('s15_cell_sub_tech', fontSize=6.7, leading=9.5, textColor=T.MUTED)
_NOTE_NOHY = T.STYLES['note'].clone('s15_note_nohy', hyphenationLang='', embeddedHyphenation=0)


# --- shared helpers ---------------------------------------------------------------
def _method(code):
    return METHODS.get(code, str(code).replace('_', ' '))


def _methods(data):
    raw = data.get('detection_methods') or []
    if raw:
        return [_method(m) for m in raw]
    # derive from evidence sources when section-level detection_methods is absent
    ev = [e for e in data.get('evidence') or [] if isinstance(e, dict) and e.get('source')]
    seen = list(OrderedDict.fromkeys(_method(e['source']) for e in ev))
    return seen


def _scan_raw(data):
    return data.get('last_scanned') or data.get('scanned_at') or data.get('scannedAt')


def _scan_date(data, c):
    ls = _scan_raw(data)
    if ls is None or c.is_missing(ls):
        return c.missing_text(ls or {'value': None, 'reason': 'scan date not recorded'})
    return c.fmt_date(ls)


def _clean(v):
    s = str(v or '').strip()
    return None if s in ('', '-', '—') else s


_NON_PUBLIC_NETS = (
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('100.64.0.0/10'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('fc00::/7'),
    ipaddress.ip_network('fe80::/10'),
)


def _ip_kind(ip_str):
    """Classify an IP address; excludes RFC 5737 documentation ranges used in synthetic demos."""
    if not ip_str:
        return 'unresolved'
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return 'unresolved'
    if ip.version == 4 and ip in ipaddress.ip_network('100.64.0.0/10'):
        return 'cgnat'
    if any(ip.version == net.version and ip in net for net in _NON_PUBLIC_NETS):
        return 'private'
    return 'public'


def _is_protocol_record(asset):
    return str(asset.get('source') or '').strip().startswith(('MX:', 'NS:'))


def is_unresolved(asset):
    return not _clean(asset.get('ip')) and not _is_protocol_record(asset)


def _layer_of(asset):
    if is_unresolved(asset):
        return 'Unresolved / No IP'
    return _clean(asset.get('category')) or 'Hosting / Infrastructure'


def _clean_asn(asn):
    """Deduplicate repeated org names emitted by some ASN lookups ('Org Org')."""
    s = _clean(asn)
    if not s:
        return None
    parts = s.split(' ', 1)
    if len(parts) == 2 and parts[0].startswith('AS'):
        rest = parts[1].strip()
        half = len(rest) // 2
        if len(rest) % 2 == 1 and rest[half] == ' ' and rest[:half] == rest[half + 1:]:
            return f'{parts[0]} {rest[:half]}'
    return s


def _short_source(asset):
    src = str(asset.get('source') or '').strip()
    for pfx in ('MX:', 'NS:', 'CNAME:'):
        if src.startswith(pfx):
            return pfx[:-1]
    return src or 'A Record'


def _source_target(asset):
    src = str(asset.get('source') or '').strip()
    for pfx in ('MX:', 'NS:', 'CNAME:'):
        if src.startswith(pfx):
            return src[len(pfx):].strip()
    return _clean(asset.get('cname'))


def cloud_summary(data):
    s = data.get('cloud_summary')
    return s if isinstance(s, dict) else {}


def detected_providers(data):
    """Ordered list of detected cloud provider names."""
    det = data.get('detected_providers') or data.get('detectedProviders')
    if isinstance(det, list):
        return [str(p) for p in det if p]
    return [str(p['provider']) for p in data.get('providers') or [] if isinstance(p, dict) and p.get('provider')]


def assets_list(data):
    return [a for a in data.get('assets') or [] if isinstance(a, dict)]


def active_assets(data):
    return [a for a in assets_list(data) if not is_unresolved(a)]


def unresolved_assets(data):
    return [a for a in assets_list(data) if is_unresolved(a)]


def endpoint_tier(data):
    """'T1' when active endpoints fit inline (<= 30), else 'T2' (full register in Appendix D.7)."""
    active = active_assets(data)
    return 'T1' if len(active) <= D.t1_max('cloud_endpoints') else 'T2'


def provider_groups(data):
    """Build grouped (group_title, subtitle, active_items) tuples for Concept B & Appendix D.7.
    Detected cloud providers come first, followed by other observed hosting."""
    det = detected_providers(data)
    det_set = set(det)
    grouped = OrderedDict((p, []) for p in det)
    for a in active_assets(data):
        p = _clean(a.get('provider')) or 'Unidentified'
        grouped.setdefault(p, []).append(a)

    groups = []
    for p, items in grouped.items():
        if not items:
            continue
        role = 'Cloud provider' if p in det_set else 'Other observed hosting'
        asns = list(OrderedDict.fromkeys(_clean_asn(a.get('asn')) for a in items if _clean_asn(a.get('asn'))))
        cats = list(OrderedDict.fromkeys(_layer_of(a) for a in items))
        detail = asns[0] if len(asns) == 1 else ', '.join(cats)
        sub = f'{role} · {detail}' if detail else role
        groups.append((p, sub, items))
    return groups


def _architecture_note(data):
    """Neutral architectural note (never claims failover redundancy from layer split alone)."""
    assets = active_assets(data)
    by_layer = OrderedDict()
    for a in assets:
        by_layer.setdefault(_layer_of(a), set()).add(_clean(a.get('provider')) or 'Unidentified')
    compute_provs = sorted(by_layer.get('IaaS / Cloud Compute', set()))
    if len(by_layer) > 1 and len(compute_provs) <= 1:
        cp = compute_provs[0] if compute_provs else 'one provider'
        return (f'Architecture note: Multiple providers are used across separate service layers; '
                f'public cloud compute was observed on {cp} only. Using different providers for separate '
                'layers does not confirm active failover redundancy.')
    if len(compute_provs) > 1:
        return (f'Architecture note: Public cloud compute endpoints were observed on {", ".join(compute_provs)}. '
                'External DNS and IP checks cannot confirm whether workloads fail over between providers.')
    return ('Architecture note: External DNS and IP checks show public hosting only; '
            'internal workloads and private interconnects are not visible.')


# --- section hooks ----------------------------------------------------------------
def verdict(data, ctx):
    """Fallback verdict when payload `summary` is omitted (only for rich asset payloads)."""
    assets = assets_list(data)
    if not assets:
        return None
    det = detected_providers(data)
    cs = cloud_summary(data)
    countries = cs.get('countries') or []
    unres = len(unresolved_assets(data))
    head = (f'{len(det)} cloud provider{"s" if len(det) != 1 else ""} detected'
            + (f' ({", ".join(det)})' if det else '')
            + f' across {len(assets)} observed endpoint{"s" if len(assets) != 1 else ""}')
    if countries:
        head += f' in {", ".join(countries)}'
    parts = [head + '.']
    if unres:
        parts.append(f'{unres} DNS hostname{"s" if unres != 1 else ""} did not resolve to a public IP during this check.')
    parts.append('Detection shows public provider use, not where all customer data is stored.')
    return ' '.join(parts)


def card(data, ctx):
    c, kw = ctx.c, {}
    if ctx.state == 'clear':           # other states show methods and scan date in the body, or ran no check
        if not (data.get('state_reason') or data.get('reason_code') or
                (data.get('empty_state_source') or {}).get('text')):
            kw['reason'] = CLEAR_REASON      # otherwise the shared default_card reason (payload first)
        if not (data.get('what_checked') or (data.get('empty_state_source') or {}).get('coverage')):
            methods = _methods(data)
            kw['what_checked'] = ([f'Detection methods: {", ".join(methods)}.'] if methods else []) + [
                f'Last scanned: {_scan_date(data, c)} (report assessment date {ctx.identity["assessment_date"]}).']
    if ctx.state == 'not_assessed' and not data.get('next_step'):
        kw['next_step'] = ('Run the cloud infrastructure module for this organisation. Providers are then '
                           'detected from public DNS records, IP ranges, MX records and NS records.')
    return kw


# --- visual components (Concept B) ------------------------------------------------
class LayerBar(Flowable):
    """Horizontal stacked proportion bar of endpoints across infrastructure layers."""
    BAR_H = 10.0

    def __init__(self, counts):
        super().__init__()
        self.counts = [(k, n) for k, n in counts if n > 0]
        self.total = sum(n for _, n in self.counts) or 1
        self.spaceBefore = 2
        self.spaceAfter = T.SP_SM

    def wrap(self, aw, ah):
        self.width = aw
        self.height = self.BAR_H + 18
        return self.width, self.height

    def draw(self):
        cv = self.canv
        x = 0.0
        y_bar = self.height - self.BAR_H
        for i, (layer, n) in enumerate(self.counts):
            w = self.width * n / self.total
            if i == len(self.counts) - 1:
                w = max(0.0, self.width - x)
            cv.setFillColor(LAYER_COLORS.get(layer, T.SLATE_400))
            cv.rect(x, y_bar, max(w - 1.2, 1.5), self.BAR_H, stroke=0, fill=1)
            x += w
        lx, ly, fs = 0.0, 3.0, 7.6
        for layer, n in self.counts:
            lbl = f'{LAYER_SHORT.get(layer, layer)}  {n}'
            cv.setFillColor(LAYER_COLORS.get(layer, T.SLATE_400))
            cv.rect(lx, ly + 0.5, 6, 6, stroke=0, fill=1)
            cv.setFont(T.REGULAR, fs)
            cv.setFillColor(T.BODY)
            cv.drawString(lx + 9, ly, lbl)
            lx += 9 + stringWidth(lbl, T.REGULAR, fs) + 14


# --- vector country flags + globe icon (LocationCell) -----------------------------
_GLOBE_SVG = Path(__file__).resolve().parent.parent / 'assets' / 'icons' / 'globe.svg'
_FLAG_BORDER = HexColor('#C8D4E1')
_F_RED = HexColor('#D22630')
_F_NAVY = HexColor('#0A3161')
_F_BLUE = HexColor('#0055A4')
_F_YELLOW = HexColor('#FFCE00')
_F_GREEN = HexColor('#009B3A')
_F_ORANGE = HexColor('#FF8200')
_F_BLACK = HexColor('#1A1A1A')

# Simple horizontal / vertical 3-band and 2-band flags: (orient 'h'|'v', [colors...])
_BAND_FLAGS = {
    'DE': ('h', [_F_BLACK, _F_RED, _F_YELLOW]),
    'NL': ('h', [_F_RED, white, _F_BLUE]),
    'FR': ('v', [_F_BLUE, white, _F_RED]),
    'IT': ('v', [_F_GREEN, white, _F_RED]),
    'IE': ('v', [_F_GREEN, white, _F_ORANGE]),
    'BE': ('v', [_F_BLACK, _F_YELLOW, _F_RED]),
    'ID': ('h', [_F_RED, white]),
    'PL': ('h', [white, _F_RED]),
    'IN': ('h', [_F_ORANGE, white, _F_GREEN]),
    'ES': ('h', [_F_RED, _F_YELLOW, _F_YELLOW, _F_RED]),
    'UA': ('h', [_F_BLUE, _F_YELLOW]),
    'AT': ('h', [_F_RED, white, _F_RED]),
    'LU': ('h', [_F_RED, white, HexColor('#00A1DE')]),
}


@cache
def _globe_drawing(size=8.2, color=T.SAPPHIRE):
    d = re.search(r'\sd="([^"]+)"', _GLOBE_SVG.read_text()).group(1)
    s = size / 16.0
    g = Group(SvgPath(d, fillColor=color, strokeColor=None, strokeWidth=0, fillMode=FILL_NON_ZERO),
              transform=(s, 0, 0, -s, 0, size))
    drawing = Drawing(size, size)
    drawing.add(g)
    return drawing


def _draw_flag(cv, code, x, y, w=10.8, h=7.2):
    """Crisp vector mini-flag for major hosting countries, else a clean ISO-2 pill badge."""
    cv.saveState()
    if code in _BAND_FLAGS:
        orient, cols = _BAND_FLAGS[code]
        n = len(cols)
        for i, col in enumerate(cols):
            cv.setFillColor(col)
            if orient == 'h':
                bh = h / n
                cv.rect(x, y + h - (i + 1) * bh, w, bh, stroke=0, fill=1)
            else:
                bw = w / n
                cv.rect(x + i * bw, y, bw, h, stroke=0, fill=1)
    elif code == 'US':
        cv.setFillColor(white)
        cv.rect(x, y, w, h, stroke=0, fill=1)
        cv.setFillColor(_F_RED)
        sh = h / 7.0
        for i in range(0, 7, 2):
            cv.rect(x, y + h - (i + 1) * sh, w, sh, stroke=0, fill=1)
        cv.setFillColor(_F_NAVY)
        cv.rect(x, y + h * 0.44, w * 0.44, h * 0.56, stroke=0, fill=1)
    elif code == 'CA':
        cv.setFillColor(_F_RED)
        cv.rect(x, y, w, h, stroke=0, fill=1)
        cv.setFillColor(white)
        cv.rect(x + w * 0.25, y, w * 0.50, h, stroke=0, fill=1)
        cv.setFillColor(_F_RED)
        # stylized centre leaf mark
        cx, cy = x + w / 2.0, y + h / 2.0
        p = cv.beginPath()
        p.moveTo(cx, cy + h * 0.28)
        p.lineTo(cx + w * 0.12, cy - h * 0.04)
        p.lineTo(cx + w * 0.04, cy - h * 0.08)
        p.lineTo(cx + w * 0.04, cy - h * 0.24)
        p.lineTo(cx - w * 0.04, cy - h * 0.24)
        p.lineTo(cx - w * 0.04, cy - h * 0.08)
        p.lineTo(cx - w * 0.12, cy - h * 0.04)
        p.close()
        cv.drawPath(p, stroke=0, fill=1)
    elif code == 'SG':
        cv.setFillColor(_F_RED)
        cv.rect(x, y + h / 2.0, w, h / 2.0, stroke=0, fill=1)
        cv.setFillColor(white)
        cv.rect(x, y, w, h / 2.0, stroke=0, fill=1)
        cv.circle(x + w * 0.24, y + h * 0.75, h * 0.17, stroke=0, fill=1)
        cv.setFillColor(_F_RED)
        cv.circle(x + w * 0.29, y + h * 0.75, h * 0.14, stroke=0, fill=1)
    elif code == 'GB':
        cv.setFillColor(_F_NAVY)
        cv.rect(x, y, w, h, stroke=0, fill=1)
        cv.setStrokeColor(white)
        cv.setLineWidth(1.3)
        cv.line(x, y, x + w, y + h)
        cv.line(x, y + h, x + w, y)
        cv.setStrokeColor(_F_RED)
        cv.setLineWidth(0.55)
        cv.line(x, y, x + w, y + h)
        cv.line(x, y + h, x + w, y)
        cv.setFillColor(white)
        cv.rect(x + w * 0.40, y, w * 0.20, h, stroke=0, fill=1)
        cv.rect(x, y + h * 0.36, w, h * 0.28, stroke=0, fill=1)
        cv.setFillColor(_F_RED)
        cv.rect(x + w * 0.44, y, w * 0.12, h, stroke=0, fill=1)
        cv.rect(x, y + h * 0.42, w, h * 0.16, stroke=0, fill=1)
    elif code == 'JP':
        cv.setFillColor(white)
        cv.rect(x, y, w, h, stroke=0, fill=1)
        cv.setFillColor(_F_RED)
        cv.circle(x + w / 2.0, y + h / 2.0, h * 0.28, stroke=0, fill=1)
    elif code == 'CH':
        cv.setFillColor(_F_RED)
        cv.rect(x, y, w, h, stroke=0, fill=1)
        cv.setFillColor(white)
        cv.rect(x + w * 0.41, y + h * 0.20, w * 0.18, h * 0.60, stroke=0, fill=1)
        cv.rect(x + w * 0.28, y + h * 0.38, w * 0.44, h * 0.24, stroke=0, fill=1)
    elif code == 'BR':
        cv.setFillColor(_F_GREEN)
        cv.rect(x, y, w, h, stroke=0, fill=1)
        cv.setFillColor(_F_YELLOW)
        p = cv.beginPath()
        p.moveTo(x + w / 2.0, y + h * 0.86)
        p.lineTo(x + w * 0.86, y + h / 2.0)
        p.lineTo(x + w / 2.0, y + h * 0.14)
        p.lineTo(x + w * 0.14, y + h / 2.0)
        p.close()
        cv.drawPath(p, stroke=0, fill=1)
        cv.setFillColor(_F_NAVY)
        cv.circle(x + w / 2.0, y + h / 2.0, h * 0.20, stroke=0, fill=1)
    elif code in ('AU', 'NZ'):
        cv.setFillColor(_F_NAVY)
        cv.rect(x, y, w, h, stroke=0, fill=1)
        cv.setFillColor(white)
        cv.rect(x + w * 0.18, y + h * 0.50, w * 0.10, h * 0.50, stroke=0, fill=1)
        cv.rect(x, y + h * 0.70, w * 0.46, h * 0.12, stroke=0, fill=1)
        cv.setFillColor(_F_RED)
        cv.rect(x + w * 0.20, y + h * 0.50, w * 0.06, h * 0.50, stroke=0, fill=1)
        cv.rect(x, y + h * 0.73, w * 0.46, h * 0.06, stroke=0, fill=1)
        cv.setFillColor(white if code == 'AU' else _F_RED)
        for sx, sy in ((0.74, 0.72), (0.82, 0.50), (0.68, 0.46), (0.74, 0.26)):
            cv.circle(x + w * sx, y + h * sy, 0.55, stroke=0, fill=1)
    elif code in ('SE', 'FI', 'NO'):
        bg = _F_BLUE if code == 'SE' else (white if code == 'FI' else _F_RED)
        cross = _F_YELLOW if code == 'SE' else (_F_BLUE if code == 'FI' else _F_NAVY)
        cv.setFillColor(bg)
        cv.rect(x, y, w, h, stroke=0, fill=1)
        cv.setFillColor(cross)
        cv.rect(x + w * 0.28, y, w * 0.16, h, stroke=0, fill=1)
        cv.rect(x, y + h * 0.40, w, h * 0.20, stroke=0, fill=1)
    elif code == 'KR':
        cv.setFillColor(white)
        cv.rect(x, y, w, h, stroke=0, fill=1)
        cv.setFillColor(_F_RED)
        cv.circle(x + w / 2.0, y + h * 0.56, h * 0.20, stroke=0, fill=1)
        cv.setFillColor(_F_BLUE)
        cv.circle(x + w / 2.0, y + h * 0.44, h * 0.18, stroke=0, fill=1)
    elif code == 'HK':
        cv.setFillColor(_F_RED)
        cv.rect(x, y, w, h, stroke=0, fill=1)
        cv.setFillColor(white)
        cv.circle(x + w / 2.0, y + h / 2.0, h * 0.20, stroke=0, fill=1)
    else:
        # Clean ISO-2 pill badge for any other valid country code
        cv.setFillColor(T.SURFACE)
        cv.setStrokeColor(T.NAVY)
        cv.setLineWidth(0.45)
        cv.roundRect(x, y, w, h, 1.5, stroke=1, fill=1)
        cv.setFillColor(T.NAVY)
        cv.setFont(T.MEDIUM, 5.1)
        cv.drawCentredString(x + w / 2.0, y + 1.8, code)
        cv.restoreState()
        return
    cv.setStrokeColor(_FLAG_BORDER)
    cv.setLineWidth(0.35)
    cv.rect(x, y, w, h, stroke=1, fill=0)
    cv.restoreState()


class LocationCell(Flowable):
    """Inline vector country flag (or ISO-2 badge / global globe) + location text."""
    FLAG_W, FLAG_H, GAP = 10.8, 7.2, 4.2

    def __init__(self, text, country_code=None, is_global=False, style='dense'):
        super().__init__()
        self.text = str(text)
        code = str(country_code or '').strip().upper()
        self.code = code if (len(code) == 2 and code.isalpha() and code not in ('XX', 'ZZ')) else None
        self.is_global = bool(is_global) and not self.code
        st = T.STYLES[style]
        self._fs, self._font = st.fontSize, st.fontName
        self._icon_w = self.FLAG_W if self.code else (8.2 if self.is_global else 0.0)
        indent = self._icon_w + self.GAP if self._icon_w else 0.0
        self._p = Paragraph(fallback(C.esc(self.text)),
                            st.clone(st.name + '_loc', leftIndent=indent))

    def wrap(self, aw, ah):
        _, self.height = self._p.wrap(aw, ah)
        self.width = aw
        return self.width, self.height

    def draw(self):
        self._p.drawOn(self.canv, 0, 0)
        baseline = self.height - self._fs
        mid_y = baseline + self._fs * 0.35
        if self.code:
            _draw_flag(self.canv, self.code, 0, mid_y - self.FLAG_H / 2.0, self.FLAG_W, self.FLAG_H)
        elif self.is_global:
            renderPDF.draw(_globe_drawing(), self.canv, 0, mid_y - 4.1)

    def minWidth(self):
        pad = self._icon_w + self.GAP if self._icon_w else 0.0
        return pad + max((stringWidth(w, self._font, self._fs) for w in self.text.split()), default=0.0)


def grouped_endpoints_table(groups, title='Endpoints grouped by hosting provider', ident=None):
    """Four-column CompactTable grouped by hosting provider + ASN (reused by Section 15 and Appendix D.7)."""
    widths = [168, 102, 92, T.CW - 362]
    head = [C.P(h, 'dense_head') for h in ('Host / Target', 'IP / Record', 'Services', 'Location')]
    data, rowno, rowgrp = [head], [None], [None]
    cmds = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), T.CELL_PAD_H),
        ('RIGHTPADDING', (0, 0), (-1, -1), T.CELL_PAD_H),
        ('TOPPADDING', (0, 0), (-1, -1), T.DENSE_PAD_V),
        ('BOTTOMPADDING', (0, 0), (-1, -1), T.DENSE_PAD_V),
        ('BACKGROUND', (0, 0), (-1, 0), T.SURFACE),
        ('LINEBELOW', (0, 0), (-1, 0), 0.75, T.HEADING),
    ]
    n = 0
    for grp_title, grp_sub, items in groups:
        r_idx = len(data)
        lbl = C.M(f'<font name="{T.MEDIUM}" color="{C.hexstr(T.NAVY)}">{C.esc(grp_title)}</font>'
                  + (f'  <font color="{C.hexstr(T.MUTED)}">·  {C.esc(grp_sub)}</font>' if grp_sub else ''),
                  'dense')
        cnt = C.P(f'{len(items)} endpoint{"s" if len(items) != 1 else ""}', _GRP_META)
        data.append([lbl, '', '', cnt])
        rowno.append(None)
        rowgrp.append(grp_title)
        cmds += [
            ('SPAN', (0, r_idx), (2, r_idx)),
            ('BACKGROUND', (0, r_idx), (-1, r_idx), T.SURFACE),
            ('TOPPADDING', (0, r_idx), (-1, r_idx), 5),
            ('BOTTOMPADDING', (0, r_idx), (-1, r_idx), 4),
            ('LINEABOVE', (0, r_idx), (-1, r_idx), 0.6, T.RULE),
            ('LINEBELOW', (0, r_idx), (-1, r_idx), 0.5, T.RULE),
            ('NOSPLIT', (0, r_idx), (-1, min(r_idx + 1, r_idx + len(items)))),
        ]
        for a in items:
            n += 1
            host = _clean(a.get('host')) or 'Not recorded'
            host_cell = [C.TechText(host, 'dense_tech')]
            cname = _clean(a.get('cname'))
            if cname:
                host_cell.append(C.TechText(f'CNAME: {cname}', _CELL_SUB_TECH))
            elif _is_protocol_record(a):
                host_cell.append(C.TechText(f'{_short_source(a)}: {_source_target(a) or ""}', _CELL_SUB_TECH))

            ip = _clean(a.get('ip'))
            kind = _ip_kind(ip)
            if not ip:
                ip_cell = C.P(f'{_short_source(a)} record' if _is_protocol_record(a) else 'Not resolved', 'dense_muted')
            elif kind in ('private', 'cgnat'):
                ip_cell = [C.TechText(ip, 'dense_tech'), C.P('Non-public IP in DNS', _CELL_SUB)]
            else:
                ips = [x for x in (a.get('ips') or [ip]) if _clean(x)]
                ip_cell = ([C.TechText(ip, 'dense_tech'), C.P(f'+{len(ips) - 1} more IPs', _CELL_SUB)]
                           if len(ips) > 1 else C.TechText(ip, 'dense_tech'))

            svcs = ', '.join(str(s) for s in (a.get('services') or []) if s) or 'None observed'
            loc = _clean(a.get('location'))
            cc = _clean(a.get('countryCode') or a.get('country_code'))
            if not loc:
                loc_cell = C.P('Not identified', 'dense_muted')
            else:
                is_glob = 'global' in loc.lower() or _is_protocol_record(a)
                loc_cell = LocationCell(loc, country_code=cc, is_global=is_glob)
            r_cur = len(data)
            data.append([host_cell, ip_cell, C.P(svcs, 'dense'), loc_cell])
            rowno.append(n)
            rowgrp.append(grp_title)
            cmds += [
                ('LINEBELOW', (0, r_cur), (-1, r_cur), T.HAIRLINE, T.RULE),
                ('NOSPLIT', (0, r_cur), (-1, r_cur)),
            ]

    kw = {'ident': ident} if ident else {}
    t = C.CompactTable(data, colWidths=widths, repeatRows=1, splitInRow=1, hAlign='LEFT', **kw)
    t.setStyle(TableStyle(cmds))
    t.spaceBefore = 6
    if ident:
        C._TABLE_HEADS[ident] = ['Host / Target', 'IP / Record', 'Services', 'Location']
    return C.numbered(t, rowno, title=title, rowgrp=rowgrp)


def unresolved_note(data):
    """Structured neutral callout block for DNS hostnames that returned no IP address."""
    unres = unresolved_assets(data)
    if not unres:
        return None
    names = [_clean(a.get('host')) or 'unnamed' for a in unres]
    n = len(names)
    inner_w = T.CW - 22  # 10 left + 10 right + 2 accent rule
    hdr = Table([[C.P('Unresolved DNS hostnames', 'cell_head'),
                  C.P(f'{n} hostname{"s" if n != 1 else ""}', _GRP_META)]],
                colWidths=[inner_w * 0.72, inner_w * 0.28], hAlign='LEFT')
    hdr.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                             ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                             ('VALIGN', (0, 0), (-1, -1), 'BOTTOM')]))
    sub = C.P('No public IP address was returned for these hostnames during this scan.',
              'note_flush', spaceAfter=5)
    if n <= 8:
        cols = 2 if n > 1 else 1
        cw = (inner_w - (12 if cols == 2 else 0)) / cols
        grid_rows = []
        for i in range(0, n, cols):
            pair = [C.TechText(h, 'dense_tech') for h in names[i:i + cols]]
            if len(pair) < cols:
                pair.append('')
            grid_rows.append(pair)
        col_w = [cw, cw] if cols == 2 else [inner_w]
        hosts_flow = Table(grid_rows, colWidths=col_w, hAlign='LEFT')
        hosts_flow.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 1.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
    else:
        hosts_flow = C.TechText(', '.join(names), 'dense_tech')

    box = Table([[[hdr, sub, hosts_flow]]], colWidths=[T.CW], hAlign='LEFT', spaceBefore=T.SP_SM, spaceAfter=T.SP_XS)
    box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), T.SURFACE),
        ('LINEBEFORE', (0, 0), (0, -1), 2.0, T.SLATE_400),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('NOSPLIT', (0, 0), (-1, -1)),
    ]))
    return box


# --- rich Concept B body ----------------------------------------------------------
def _rich_kpis(data, ctx):
    c = ctx.c
    cs = cloud_summary(data)
    det = detected_providers(data)
    assets = assets_list(data)
    active_n = len(active_assets(data))
    unres_n = len(assets) - active_n
    countries = cs.get('countries')
    if not isinstance(countries, list):
        countries = list(OrderedDict.fromkeys(
            _clean(a.get('location')).rsplit(',', 1)[-1].strip()
            for a in assets if _clean(a.get('countryCode') or a.get('country_code')) and _clean(a.get('location'))
        ))
    primary = _clean(cs.get('primary_compute') or cs.get('primaryCompute'))
    ls = _scan_raw(data)
    scan_txt = c.missing_text(ls) if (ls is None or c.is_missing(ls)) else c.fmt_date(ls)

    prov_sub = ', '.join(det) if det else 'None detected'
    ep_sub = (f'{active_n} active, {unres_n} unresolved' if unres_n else 'All endpoints resolved / active')
    ctry_sub = ', '.join(countries) if countries else 'None identified'

    items = [
        {'label': f'Cloud providers detected\n{prov_sub}', 'value': len(det), 'unit': 'providers'},
        {'label': f'Observed endpoints\n{ep_sub}', 'value': len(assets), 'unit': 'endpoints'},
        {'label': f'Countries observed\n{ctry_sub}', 'value': len(countries), 'unit': 'countries'},
    ]
    if primary:
        items.append({'label': f'Primary compute\nLast scanned {scan_txt}', 'value': primary})
    else:
        items.append({'label': f'Last scanned, cloud module\nReport assessed {ctx.identity["assessment_date"]}',
                      'value': scan_txt if not (ls is None or c.is_missing(ls)) else None,
                      **({} if not (ls is None or c.is_missing(ls))
                         else (ls if isinstance(ls, dict) else {'reason': 'scan date not recorded'}))})
    return items


def _layer_block(data, ctx):
    c = ctx.c
    assets = assets_list(data)
    counts = Counter(_layer_of(a) for a in assets)
    ordered = [(k, counts[k]) for k in LAYER_ORDER if counts[k]]
    for k, n in counts.items():
        if k not in LAYER_ORDER and n:
            ordered.append((k, n))

    rows = []
    for k, _ in ordered:
        sub = [a for a in assets if _layer_of(a) == k]
        provs = Counter(_clean(a.get('provider')) or 'Unidentified' for a in sub)
        p_txt = ', '.join(f'{p} ({n})' if len(provs) > 1 else p for p, n in provs.most_common())
        locs = list(OrderedDict.fromkeys(_clean(a.get('location')) for a in sub if _clean(a.get('location'))))
        loc_txt = (', '.join(locs[:3]) + (f' (+{len(locs) - 3})' if len(locs) > 3 else '')
                   if locs else 'Not identified')
        rows.append([LAYER_SHORT.get(k, k), p_txt, loc_txt, len(sub)])

    return [
        c.heading('Infrastructure footprint by layer', 2),
        LayerBar(ordered),
        c.compact_table(['Layer', 'Providers observed', 'Locations', 'Endpoints'], rows,
                        widths=[108, 178, T.CW - 348, 62], numeric_cols=(3,)),
        c.P(_architecture_note(data), _NOTE_NOHY),
    ]


def _build_rich(data, ctx):
    c = ctx.c
    out = [c.kpi_strip(_rich_kpis(data, ctx), per_row=4)]
    out += _layer_block(data, ctx)

    groups = provider_groups(data)
    active = active_assets(data)
    if endpoint_tier(data) == 'T1':
        if groups:
            out.append(c.heading('Endpoints grouped by hosting provider', 2, style=_H2_TIGHT))
            out.append(grouped_endpoints_table(groups, 'Hosting endpoints'))
        un = unresolved_note(data)
        if un:
            out.append(un)
    else:
        # > 30 active endpoints: keep Section 15 compact with provider summary + pointer to Appendix D.7
        out.append(c.heading('Hosting providers summary', 2))
        s_rows = [[title, sub or '—', len(items)] for title, sub, items in groups]
        out.append(c.compact_table(['Provider', 'ASN / Layer', 'Endpoints'], s_rows,
                                   widths=[172, T.CW - 234, 62], numeric_cols=(2,)))
        un = unresolved_note(data)
        if un:
            out.append(un)
        rid = D.RID.get('s15', 'D.7')
        out.append(c.register_pointer(rid, {'value': len(active), 'unit': 'endpoints'},
                                      title=f'{rid}.1 Cloud infrastructure endpoints'))

    methods = _methods(data)
    if methods:
        out.append(c.P(f'Detection methods: {", ".join(methods)}.', _NOTE_NOHY))
    return out


# --- legacy provider-only body (unchanged for existing payloads) ------------------
def _kpis(data, ctx):
    c = ctx.c
    items = [m for m in data.get('metrics') or [] if isinstance(m, dict)]
    ls = _scan_raw(data) or {'value': None, 'reason': 'scan date not recorded'}
    label = f'Last scanned, cloud module\nReport assessed {ctx.identity["assessment_date"]}'
    items.append({**ls, 'label': label, 'unit': None} if c.is_missing(ls) else
                 {'label': label, 'value': c.fmt_date(ls)})
    return items


def _provider_table(providers, ctx, methods):
    """Provider rows; a column missing for every provider collapses into the note under the table."""
    c = ctx.c
    cols = [('Provider', 'provider'), ('Detected by', 'detection_methods'), ('Observed', 'observed_at')]

    def cell(p, key):
        v = p.get(key)
        if key == 'provider':
            return v if v else {'value': None, 'reason': 'provider name not recorded'}
        if c.is_missing(v):
            return v or {'value': None, 'reason': 'not recorded'}
        if key == 'detection_methods':
            return ', '.join(_method(m) for m in (v if isinstance(v, list) else [v]))
        return c.fmt_date(v)

    keep, gone = [], {}
    for label, key in cols:
        vals = [p.get(key) for p in providers]
        if key != 'provider' and all(c.is_missing(v) for v in vals):
            gone.setdefault(c.reason_text(vals[0] or {}), []).append(label.lower())
        else:
            keep.append((label, key))
    t = ctx.t
    widths = None if len(keep) == 1 else [t.COL3] + [(t.CW - t.COL3) / (len(keep) - 1)] * (len(keep) - 1)
    out = [c.compact_table([lbl for lbl, _ in keep], [[cell(p, k) for _, k in keep] for p in providers],
                           widths=widths)]
    notes = [f'Detection methods: {", ".join(methods)}.'] if methods else []
    notes += [f'{" and ".join(labels).capitalize()} per provider: not available ({reason}).'
              for reason, labels in gone.items()]
    if notes:
        out.append(c.note(' '.join(notes)))
    return out


def build(data, ctx):
    c = ctx.c
    assets = assets_list(data)
    providers = [p for p in data.get('providers') or [] if isinstance(p, dict)]
    if ctx.state == 'clear' and not providers and not assets:
        return []                      # the clear card carries the message and what was checked
    if assets:
        return _build_rich(data, ctx)
    out = [c.kpi_strip(_kpis(data, ctx))]      # scan date only: no staleness flag (business answer 8)
    out.append(c.heading('Detected providers', 2))
    methods = _methods(data)            # module scope (intro_source), not per-provider evidence
    if providers:
        return out + _provider_table(providers, ctx, methods)
    return out + [c.P(f'{NOT_DETECTED}.', 'body')] + (
        [c.note(f'Detection methods: {", ".join(methods)}.')] if methods else [])
