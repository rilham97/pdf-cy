"""Prototype: three concepts for Section 15 (Cloud infrastructure) built from the new
backend payload shape (summary + detectedProviders + assets[] + evidence[]).

Renders Concepts A, B, and C on real A4 interior pages using Cyberrank theme tokens and
components, tested against both the rich 24-endpoint sample (anthropic.com) and the small
3-endpoint sample (iisri.com).

    .venv/bin/python -I tools/prototypes/cloud_infra_concepts.py <anthropic.json> <out_dir>
"""
import ipaddress
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pymupdf  # noqa: E402
from reportlab.lib.colors import HexColor  # noqa: E402
from reportlab.pdfbase.pdfmetrics import stringWidth  # noqa: E402
from reportlab.platypus import Flowable, PageBreak, Spacer, Table, TableStyle  # noqa: E402

from cyberrank_report import components as C, qa, theme as T  # noqa: E402
from cyberrank_report.page import ReportDoc  # noqa: E402

IISRI_RAW = {
    "summary": {"multiCloud": True, "endpointCount": 3, "providerCount": 2,
                "countries": ["Singapore"], "primaryCompute": "OVH"},
    "scannedAt": "2026-11-18T04:32:52.810Z",
    "assets": [
        {"provider": "OVH", "countryCode": "SG", "ip": "15.235.243.250", "host": "iisri.com", "cname": "",
         "location": "Singapore, Singapore", "services": ["80 HTTP", "443 HTTPS"], "source": "A Record",
         "category": "IaaS / Cloud Compute", "ips": ["15.235.243.250"],
         "asn": "AS16276 OVH SAS OVH Singapore PTE. LTD", "webStatus": "200 OK"},
        {"provider": "OVH", "countryCode": "SG", "ip": "15.235.243.250", "host": "www.iisri.com", "cname": "",
         "location": "Singapore, Singapore", "services": ["80 HTTP", "443 HTTPS"], "source": "A Record",
         "category": "IaaS / Cloud Compute", "ips": ["15.235.243.250"],
         "asn": "AS16276 OVH SAS OVH Singapore PTE. LTD", "webStatus": "200 OK"},
        {"provider": "Azure", "countryCode": "", "ip": "-", "host": "iisri.com", "cname": "",
         "location": "Global Cloud", "services": ["25 SMTP"],
         "source": "MX: iisri-com.mail.protection.outlook.com", "category": "SaaS / Email & Productivity",
         "ips": [], "asn": "Azure Mail", "webStatus": "Active"},
    ],
    "evidence": [
        {"provider": "OVH", "ip": "15.235.243.250", "host": "iisri.com", "location": "Singapore, Singapore",
         "source": "a_record", "detail": "iisri.com → 15.235.243.250 (AS16276 OVH SAS OVH Singapore PTE. LTD)",
         "category": "IaaS / Cloud Compute"},
        {"provider": "OVH", "ip": "15.235.243.250", "host": "www.iisri.com", "location": "Singapore, Singapore",
         "source": "a_record", "detail": "www.iisri.com → 15.235.243.250 (AS16276 OVH SAS OVH Singapore PTE. LTD)",
         "category": "IaaS / Cloud Compute"},
        {"provider": "Azure", "host": "iisri.com", "source": "mx_record",
         "detail": "iisri.com → iisri-com.mail.protection.outlook.com", "category": "SaaS / Email & Productivity"},
    ],
    "detectedProviders": ["OVH", "Azure"],
}

# Quiet structural palette for infrastructure layers (no status red/green/orange overload)
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
SOURCE_LABELS = {'a_record': 'A record', 'cname_record': 'CNAME', 'mx_record': 'MX record', 'ns_record': 'NS record'}

_H2_TIGHT = T.STYLES['h2'].clone('ci_h2_tight', spaceBefore=T.SP_MD, spaceAfter=4)
_H3_TIGHT = T.STYLES['h3c'].clone('ci_h3_tight', spaceBefore=T.SP_SM, spaceAfter=3)
_GRP_STYLE = T.STYLES['dense_head'].clone('ci_grp', textColor=T.NAVY)
_GRP_META = T.STYLES['dense_muted'].clone('ci_grp_meta', alignment=2)
_CELL_SUB = T.STYLES['dense_muted'].clone('ci_sub', fontSize=7.0, leading=9.5)
_CELL_SUB_TECH = T.STYLES['dense_tech'].clone('ci_sub_tech', fontSize=6.7, leading=9.5, textColor=T.MUTED)
_NOTE_NOHY = T.STYLES['note'].clone('ci_note_nohy', hyphenationLang='', embeddedHyphenation=0)


# --- data classification helpers --------------------------------------------------
def _clean(v):
    s = str(v or '').strip()
    return None if s in ('', '-', '—') else s


def _ip_kind(ip_str):
    if not ip_str:
        return 'unresolved'
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return 'unresolved'
    if ip in ipaddress.ip_network('100.64.0.0/10'):
        return 'cgnat'
    if ip.is_private or ip.is_loopback or ip.is_link_local:
        return 'private'
    return 'public'


def _is_protocol_record(asset):
    src = str(asset.get('source') or '')
    return src.startswith(('MX:', 'NS:'))


def _is_unresolved(asset):
    return not _clean(asset.get('ip')) and not _is_protocol_record(asset)


def _layer_of(asset):
    if _is_unresolved(asset):
        return 'Unresolved / No IP'
    return asset.get('category') or 'Hosting / Infrastructure'


def _clean_asn(asn):
    """Deduplicate repeated org names emitted by some ASN lookups ('Anthropic, PBC Anthropic, PBC')."""
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
    if src.startswith('MX:'):
        return 'MX'
    if src.startswith('NS:'):
        return 'NS'
    if src.startswith('CNAME:'):
        return 'CNAME'
    return src or 'A Record'


def _source_target(asset):
    src = str(asset.get('source') or '').strip()
    for pfx in ('MX:', 'NS:', 'CNAME:'):
        if src.startswith(pfx):
            return src[len(pfx):].strip()
    return _clean(asset.get('cname'))


def _provider_rows(raw):
    """Build per-provider summary from assets + evidence, keeping detected cloud providers first."""
    detected = list(raw.get('detectedProviders') or [])
    det_set = set(detected)
    ev_sources = {}
    for ev in raw.get('evidence') or []:
        p = ev.get('provider')
        if p:
            ev_sources.setdefault(p, set()).add(SOURCE_LABELS.get(ev.get('source'), ev.get('source') or 'DNS'))

    grouped = OrderedDict()
    for p in detected:
        grouped[p] = []
    for a in raw.get('assets') or []:
        p = a.get('provider') or 'Unidentified'
        grouped.setdefault(p, []).append(a)

    rows = []
    for p, items in grouped.items():
        if not items:
            continue
        cats = list(OrderedDict.fromkeys(_layer_of(a) for a in items))
        locs = list(OrderedDict.fromkeys(_clean(a.get('location')) for a in items if _clean(a.get('location'))))
        asns = list(OrderedDict.fromkeys(_clean_asn(a.get('asn')) for a in items if _clean_asn(a.get('asn'))))
        srcs = sorted(ev_sources.get(p) or {_short_source(a) for a in items})
        resolved = sum(1 for a in items if not _is_unresolved(a))
        rows.append({
            'provider': p,
            'is_cloud': p in det_set,
            'categories': cats,
            'locations': locs,
            'asns': asns,
            'sources': srcs,
            'count': len(items),
            'resolved': resolved,
            'unresolved': len(items) - resolved,
            'items': items,
        })
    return rows


def _fmt_scanned(raw):
    s = str(raw.get('scannedAt') or '')
    return C.fmt_date({'value': s[:10], 'precision': 'day'}) if len(s) >= 10 else 'Not available'


def _verdict(raw, org):
    s = raw.get('summary') or {}
    det = list(raw.get('detectedProviders') or [])
    assets = raw.get('assets') or []
    unresolved = sum(1 for a in assets if _is_unresolved(a))
    countries = s.get('countries') or []
    parts = [f'{len(det)} cloud provider{"s" if len(det) != 1 else ""} detected ({", ".join(det)})'
             f' across {len(assets)} observed endpoints']
    if countries:
        parts[0] += f' in {", ".join(countries)}'
    parts[0] += '.'
    if unresolved:
        parts.append(f'{unresolved} DNS hostnames did not resolve to a public IP during this check.')
    parts.append('Detection shows public provider use, not where all customer data is stored.')
    return ' '.join(parts)


def _common_kpis(raw, mode='full'):
    s = raw.get('summary') or {}
    det = list(raw.get('detectedProviders') or [])
    assets = raw.get('assets') or []
    countries = s.get('countries') or []
    resolved = sum(1 for a in assets if not _is_unresolved(a))
    if mode == 'frontend':
        return [
            {'label': f'Detected cloud providers\n{", ".join(det)}', 'value': len(det), 'unit': 'providers'},
            {'label': f'Observed endpoints\n{resolved} active / resolved', 'value': len(assets), 'unit': 'endpoints'},
            {'label': f'Countries observed\n{", ".join(countries) or "None"}', 'value': len(countries),
             'unit': 'countries'},
            {'label': f'Primary compute\nLast scanned {_fmt_scanned(raw)}', 'value': s.get('primaryCompute') or '—'},
        ]
    return [
        {'label': f'Cloud providers detected\n{", ".join(det)}', 'value': len(det), 'unit': 'providers'},
        {'label': f'Observed endpoints\n{resolved} active, {len(assets) - resolved} unresolved'
                  if len(assets) - resolved else 'All endpoints resolved / active',
         'value': len(assets), 'unit': 'endpoints'},
        {'label': f'Countries observed\n{", ".join(countries) or "None"}', 'value': len(countries),
         'unit': 'countries'},
        {'label': f'Primary compute\nLast scanned {_fmt_scanned(raw)}',
         'value': s.get('primaryCompute') or 'Not identified'},
    ]


def _layer_note(raw):
    """Neutral architectural note replacing the frontend's green 'Multi-Cloud Redundancy Detected' claim."""
    assets = raw.get('assets') or []
    by_layer = OrderedDict()
    for a in assets:
        if _is_unresolved(a):
            continue
        by_layer.setdefault(a.get('category') or 'Hosting / Infrastructure', set()).add(a.get('provider'))
    compute_provs = sorted(by_layer.get('IaaS / Cloud Compute', set()))
    multi_layers = len(by_layer) > 1
    if multi_layers and len(compute_provs) <= 1:
        cp = compute_provs[0] if compute_provs else 'one provider'
        return (f'Architecture note: Multiple providers are used across separate service layers '
                f'(compute, hosting, email, DNS); public cloud compute was observed on {cp} only. '
                'Using different providers for separate layers does not confirm active failover redundancy.')
    if len(compute_provs) > 1:
        return (f'Architecture note: Public cloud compute endpoints were observed on {", ".join(compute_provs)}. '
                'External DNS and IP checks cannot confirm whether workloads fail over between providers.')
    return 'Architecture note: External DNS and IP checks show public hosting only; internal workloads are not visible.'


# --- visual proportion bar (Concept B) -------------------------------------------
class LayerBar(Flowable):
    """Horizontal stacked bar showing endpoint distribution across infrastructure layers (quiet palette)."""
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
        c = self.canv
        x = 0.0
        y_bar = self.height - self.BAR_H
        for i, (layer, n) in enumerate(self.counts):
            w = self.width * n / self.total
            if i == len(self.counts) - 1:
                w = max(0, self.width - x)
            c.setFillColor(LAYER_COLORS.get(layer, T.SLATE_400))
            c.rect(x, y_bar, max(w - 1.2, 1.5), self.BAR_H, stroke=0, fill=1)
            x += w
        # Legend row under bar
        lx = 0.0
        ly = 3.0
        fs = 7.6
        for layer, n in self.counts:
            lbl = f'{LAYER_SHORT.get(layer, layer)}  {n}'
            c.setFillColor(LAYER_COLORS.get(layer, T.SLATE_400))
            c.rect(lx, ly + 0.5, 6, 6, stroke=0, fill=1)
            c.setFont(T.REGULAR, fs)
            c.setFillColor(T.BODY)
            c.drawString(lx + 9, ly, lbl)
            lx += 9 + stringWidth(lbl, T.REGULAR, fs) + 14


def _concept_banner(tag, subtitle):
    """Small neutral header bar showing which prototype concept is on this page."""
    t = Table([[C.M(f'<font name="{T.MEDIUM}" color="{C.hexstr(T.NAVY)}">{C.esc(tag)}</font>  '
                    f'<font color="{C.hexstr(T.MUTED)}">{C.esc(subtitle)}</font>', 'note_flush')]],
              colWidths=[T.CW], hAlign='LEFT', spaceAfter=6)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), T.SURFACE),
        ('LINEBEFORE', (0, 0), (0, 0), 2.5, T.NAVY),
        ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return t


def _opener(raw, org, concept_tag, concept_sub):
    intro = ('Identifies cloud service providers and public hosting infrastructure from DNS '
             '(A, CNAME, MX, NS) and IP/ASN records.')
    return [_concept_banner(concept_tag, concept_sub)] + C.section_opener(
        '15', 'Cloud infrastructure', 'identified', verdict=_verdict(raw, org),
        intro=intro, group='Assessment details', icon='cloud_infrastructure',
    )


# ==================================================================================
# CONCEPT A: Direct Frontend Translation (KPI + Providers + Flat Endpoint Table)
# ==================================================================================
def concept_a(raw, org):
    out = _opener(raw, org, 'CONCEPT A — Direct Frontend Translation',
                  'Closest 1-to-1 match to the web dashboard: KPI strip, provider summary, flat host table.')
    out.append(C.kpi_strip(_common_kpis(raw, 'frontend'), per_row=4))

    provs = _provider_rows(raw)
    cloud_provs = [p for p in provs if p['is_cloud']]
    other_provs = [p for p in provs if not p['is_cloud']]

    out.append(C.P('Detected cloud providers', _H2_TIGHT))
    p_rows = [[p['provider'], ', '.join(p['categories']), p['count'], ', '.join(p['sources'])]
              for p in cloud_provs]
    out.append(C.compact_table(['Provider', 'Category', 'Endpoints', 'Evidence'], p_rows,
                               widths=[105, 195, 68, T.CW - 368], numeric_cols=(2,)))
    note_parts = [_layer_note(raw)]
    if other_provs:
        extra = ', '.join(f'{p["provider"]} ({p["count"]})' for p in other_provs)
        note_parts.append(f'Other hosting entries in the endpoint table: {extra}.')
    out.append(C.P(' '.join(note_parts), _NOTE_NOHY))

    out.append(C.P('Subdomain infrastructure and hosting map', _H2_TIGHT))
    e_rows = []
    for i, a in enumerate(raw.get('assets') or [], 1):
        host = a.get('host') or ''
        src_tag = _short_source(a)
        host_cell = [C.TechText(host, 'dense_tech')]
        if src_tag in ('MX', 'NS'):
            host_cell.append(C.TechText(f'{src_tag}: {_source_target(a) or ""}', _CELL_SUB_TECH))
        elif _clean(a.get('cname')):
            host_cell.append(C.TechText(f'CNAME: {a["cname"]}', _CELL_SUB_TECH))

        ip = _clean(a.get('ip'))
        kind = _ip_kind(ip)
        if not ip:
            ip_cell = C.P('Protocol record' if _is_protocol_record(a) else 'Not resolved', 'dense_muted')
        elif kind in ('private', 'cgnat'):
            ip_cell = [C.TechText(ip, 'dense_tech'), C.P('Non-public IP', _CELL_SUB)]
        else:
            extra_ips = len(a.get('ips') or []) - 1
            ip_cell = ([C.TechText(ip, 'dense_tech'), C.P(f'+{extra_ips} more IPs', _CELL_SUB)]
                       if extra_ips > 0 else C.TechText(ip, 'dense_tech'))

        svcs = ', '.join(a.get('services') or []) or 'None observed'
        asn = _clean_asn(a.get('asn'))
        host_org = [C.P(a.get('provider') or 'Unidentified', 'dense')]
        if asn and asn != a.get('provider'):
            host_org.append(C.P(asn, _CELL_SUB))
        loc = _clean(a.get('location')) or 'Not identified'
        e_rows.append([i, host_cell, ip_cell, svcs, host_org, loc])

    widths = [24, 140, 82, 74, 118, T.CW - 438]
    out.append(C.compact_table(['#', 'Host / Record', 'IP', 'Services', 'Hosting / ASN', 'Location'],
                               e_rows, widths=widths, dense=True, numeric_cols=(0,),
                               title='Subdomain infrastructure and hosting map'))
    out.append(C.P('Policy note: lists above 30 endpoints move the full endpoint map to Appendix D.7.', _NOTE_NOHY))
    return out


# ==================================================================================
# CONCEPT B: Architecture-First (Layer Bar + Grouped by Provider & Role)
# ==================================================================================
def _grouped_table(groups, title):
    """CompactTable with navy group-header rows (Provider + ASN + Category), cutting columns to 4."""
    widths = [174, 108, 96, T.CW - 378]
    head = [C.P(h, 'dense_head') for h in ('Host / Target', 'IP / Record', 'Services', 'Location')]
    data = [head]
    rowno = [None]
    rowgrp = [None]
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
            host = a.get('host') or ''
            host_cell = [C.TechText(host, 'dense_tech')]
            if _clean(a.get('cname')):
                host_cell.append(C.TechText(f'CNAME: {a["cname"]}', _CELL_SUB_TECH))
            elif _is_protocol_record(a):
                host_cell.append(C.TechText(f'{_short_source(a)}: {_source_target(a) or ""}', _CELL_SUB_TECH))

            ip = _clean(a.get('ip'))
            kind = _ip_kind(ip)
            if not ip:
                ip_cell = C.P(f'{_short_source(a)} record' if _is_protocol_record(a) else 'Not resolved', 'dense_muted')
            elif kind in ('private', 'cgnat'):
                ip_cell = [C.TechText(ip, 'dense_tech'), C.P('Non-public IP in DNS', _CELL_SUB)]
            else:
                ips = a.get('ips') or [ip]
                ip_cell = ([C.TechText(ip, 'dense_tech'), C.P(f'+{len(ips) - 1} more IPs', _CELL_SUB)]
                           if len(ips) > 1 else C.TechText(ip, 'dense_tech'))

            svcs = ', '.join(a.get('services') or []) or 'None observed'
            loc = _clean(a.get('location')) or 'Not identified'
            r_cur = len(data)
            data.append([host_cell, ip_cell, C.P(svcs, 'dense'), C.P(loc, 'dense')])
            rowno.append(n)
            rowgrp.append(grp_title)
            cmds += [
                ('LINEBELOW', (0, r_cur), (-1, r_cur), T.HAIRLINE, T.RULE),
                ('NOSPLIT', (0, r_cur), (-1, r_cur)),
            ]

    t = C.CompactTable(data, colWidths=widths, repeatRows=1, splitInRow=1, hAlign='LEFT')
    t.setStyle(TableStyle(cmds))
    return C.numbered(t, rowno, title=title, rowgrp=rowgrp)


def concept_b(raw, org):
    out = _opener(raw, org, 'CONCEPT B — Architecture-First (Recommended)',
                  'Layer footprint bar + grouped provider/role tables (eliminates repeated ASNs & cramped columns).')
    out.append(C.kpi_strip(_common_kpis(raw, 'arch'), per_row=4))

    # Layer proportion bar + role matrix
    assets = raw.get('assets') or []
    layer_order = ['IaaS / Cloud Compute', 'Hosting / Infrastructure', 'SaaS / Email & Productivity',
                   'DNS / Traffic Management', 'Unresolved / No IP']
    counts = Counter(_layer_of(a) for a in assets)
    out.append(C.P('Infrastructure footprint by layer', _H2_TIGHT))
    out.append(LayerBar([(k, counts[k]) for k in layer_order if counts[k]]))

    layer_rows = []
    for k in layer_order:
        if not counts[k]:
            continue
        sub = [a for a in assets if _layer_of(a) == k]
        provs = Counter(a.get('provider') or 'Unidentified' for a in sub)
        p_txt = ', '.join(f'{p} ({c})' if len(provs) > 1 else p for p, c in provs.most_common())
        locs = list(OrderedDict.fromkeys(_clean(a.get('location')) for a in sub if _clean(a.get('location'))))
        loc_txt = ', '.join(locs[:3]) + (f' (+{len(locs) - 3})' if len(locs) > 3 else '') if locs else 'Not identified'
        layer_rows.append([LAYER_SHORT.get(k, k), p_txt, loc_txt, len(sub)])
    out.append(C.compact_table(['Layer', 'Providers observed', 'Locations', 'Endpoints'], layer_rows,
                               widths=[108, 178, T.CW - 348, 62], numeric_cols=(3,)))
    out.append(C.P(_layer_note(raw), _NOTE_NOHY))

    # Grouped provider & endpoint table
    out.append(C.P('Endpoints grouped by hosting provider', _H2_TIGHT))
    provs = _provider_rows(raw)
    groups = []
    for p in provs:
        active = [a for a in p['items'] if not _is_unresolved(a)]
        if active:
            role_tag = 'Cloud provider' if p['is_cloud'] else 'Other observed hosting'
            active_cats = list(OrderedDict.fromkeys(_layer_of(a) for a in active))
            asn_txt = p['asns'][0] if len(p['asns']) == 1 else ', '.join(active_cats)
            groups.append((f'{p["provider"]}  ({role_tag})', asn_txt, active))
    unres = [a for a in assets if _is_unresolved(a)]

    out.append(_grouped_table(groups, 'Endpoints grouped by hosting provider'))
    if unres:
        unres_names = ', '.join(a.get('host') for a in unres)
        out.append(C.P(f'Unresolved DNS hostnames ({len(unres)}): {unres_names} — returned no IP address during this scan.',
                       _NOTE_NOHY))
    out.append(C.P('Detection methods: DNS A, CNAME, MX and NS records with ASN/IP geolocation. '
                   'Lists above 30 endpoints place the full grouped register in Appendix D.7.', _NOTE_NOHY))
    return out


# ==================================================================================
# CONCEPT C: Executive Cluster Rollup (1-Page Compact Overview + Appendix D Register)
# ==================================================================================
def concept_c(raw, org):
    out = _opener(raw, org, 'CONCEPT C — Executive Cluster Rollup',
                  'Deduplicates shared IPs/ASNs into infrastructure clusters so even 24+ endpoints fit on 1 page.')
    out.append(C.kpi_strip(_common_kpis(raw, 'arch'), per_row=4))

    provs = _provider_rows(raw)
    out.append(C.P('Provider role summary', _H2_TIGHT))
    m_rows = []
    for p in provs:
        role = 'Detected cloud' if p['is_cloud'] else 'Own ASN / dedicated'
        cats = ', '.join(LAYER_SHORT.get(c, c) for c in p['categories'])
        locs = ', '.join(p['locations']) if p['locations'] else 'Not identified'
        m_rows.append([p['provider'], role, cats, locs, p['count']])
    out.append(C.compact_table(['Provider', 'Classification', 'Layers', 'Locations', 'Endpoints'], m_rows,
                               widths=[102, 92, 132, T.CW - 384, 58], dense=True, numeric_cols=(4,)))
    out.append(C.P(_layer_note(raw), _NOTE_NOHY))

    # Deduplicate endpoints into clusters, ordered with detected cloud providers first
    out.append(C.P('Hosting clusters (grouped by IP, service and location)', _H2_TIGHT))
    det_set = set(raw.get('detectedProviders') or [])
    clusters = OrderedDict()
    unres_hosts = []
    private_items = []
    ordered_assets = sorted(raw.get('assets') or [], key=lambda a: (0 if a.get('provider') in det_set else 1))
    for a in ordered_assets:
        if _is_unresolved(a):
            unres_hosts.append(a.get('host'))
            continue
        ip = _clean(a.get('ip'))
        if _ip_kind(ip) in ('private', 'cgnat'):
            private_items.append(a)
            continue
        svcs = ', '.join(a.get('services') or []) or 'None'
        loc = _clean(a.get('location')) or 'Not identified'
        target = _source_target(a) or ''
        key = (a.get('provider'), ip or f'{_short_source(a)}: {target}', svcs, loc, _clean_asn(a.get('asn')) or '')
        clusters.setdefault(key, []).append(a)

    c_rows = []
    for (prov, ip_or_rec, svcs, loc, asn), items in clusters.items():
        hosts = ', '.join(a.get('host') for a in items)
        cname_notes = [f'{a["host"]} -> {a["cname"]}' for a in items if _clean(a.get('cname'))]
        host_flow = [C.TechText(hosts, 'dense_tech')]
        if cname_notes:
            host_flow.append(C.TechText('CNAME: ' + '; '.join(cname_notes), _CELL_SUB_TECH))
        prov_flow = [C.P(prov, 'dense')]
        if asn and asn != prov:
            prov_flow.append(C.P(asn, _CELL_SUB))
        c_rows.append([prov_flow, C.TechText(ip_or_rec, 'dense_tech'), svcs, loc, len(items), host_flow])

    out.append(C.compact_table(['Provider / ASN', 'IP / Record', 'Services', 'Location', 'Hosts', 'Observed hostnames'],
                               c_rows, widths=[96, 86, 62, 74, 36, T.CW - 354], dense=True, numeric_cols=(4,),
                               title='Hosting clusters'))

    # Highlight non-standard DNS observations explicitly
    notes = []
    if private_items:
        plist = ', '.join(f'{a["host"]} ({a["ip"]})' for a in private_items)
        notes.append(('Non-public IP addresses in DNS',
                      f'{len(private_items)} hostnames resolved to private or CGNAT addresses: {plist}.'))
    if unres_hosts:
        notes.append(('Unresolved hostnames',
                      f'{len(unres_hosts)} hostnames returned no IP address during this check: '
                      + ', '.join(unres_hosts) + '.'))
    if notes:
        out.append(C.P('Notable DNS observations', _H3_TIGHT))
        out.append(C.key_value_list(notes, dense=True))

    out.append(C.P('Full host-by-host register (with raw A/CNAME/MX/NS evidence lines) links to Appendix D.7.',
                   _NOTE_NOHY))
    return out


def render_pdf(anthropic_raw, out_pdf):
    qa.ISSUES.clear()
    ident = {
        'org': 'Anthropic (Sample) & IISRI',
        'domain': 'anthropic.com / iisri.com',
        'title': 'Cloud Infrastructure Concepts',
        'assessment_date': '24 Nov 2026',
        'generated_date': '24 Nov 2026',
        'issuer': 'Cyberrank',
        'issuer_reason': None,
        'logo': None,
    }
    doc = ReportDoc(out_pdf, ident, subject='Section 15 Cloud infrastructure design concepts A, B, C')
    # Start directly on interior template (skip cover so page 1 = Concept A)
    doc.pageTemplates = [t for t in doc.pageTemplates if t.id == 'interior'] + [
        t for t in doc.pageTemplates if t.id != 'interior']
    story = []
    pages = [
        ('Concept A — Anthropic (24 endpoints)', concept_a(anthropic_raw, 'Anthropic')),
        ('Concept B — Anthropic (24 endpoints)', concept_b(anthropic_raw, 'Anthropic')),
        ('Concept C — Anthropic (24 endpoints)', concept_c(anthropic_raw, 'Anthropic')),
        ('Concept A — IISRI (3 endpoints)', concept_a(IISRI_RAW, 'IISRI')),
        ('Concept B — IISRI (3 endpoints)', concept_b(IISRI_RAW, 'IISRI')),
        ('Concept C — IISRI (3 endpoints)', concept_c(IISRI_RAW, 'IISRI')),
    ]
    for i, (label, flow) in enumerate(pages):
        if i:
            story.append(PageBreak())
        story.append(C.Anchor(f'p-{i}', outline=label))
        story += flow
    total = doc.render(story)
    issues = list(qa.ISSUES) + qa.check_pdf(out_pdf, skip_pages=(), table_parts=doc.table_parts,
                                            table_heads=C._TABLE_HEADS)
    counts = qa.write_report(out_pdf.with_suffix('.qa.json'), out_pdf, issues, pages=total)
    return total, counts


def main():
    in_json = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = json.loads(in_json.read_text(encoding='utf-8'))
    out_pdf = out_dir / 'Cloud_Infra_Concepts.pdf'
    total, counts = render_pdf(raw, out_pdf)
    pdf = pymupdf.open(str(out_pdf))
    for i, page in enumerate(pdf, 1):
        pix = page.get_pixmap(dpi=130)
        pix.save(str(out_dir / f'page-{i:02d}.png'))
    pdf.close()
    print(f'{out_pdf}: {total} pages; QA {counts}')
    for iss in json.loads(out_pdf.with_suffix('.qa.json').read_text())['issues']:
        print(' ', iss['severity'], iss['check'], f'p{iss.get("page")}', iss['detail'][:120])


if __name__ == '__main__':
    main()
