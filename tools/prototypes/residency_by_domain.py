"""Prototype (mock, not wired into the report): Sections 07 / 08 as a vertical country list.

08 Data residency: domain -> country comes from the vulnerability scan (one shared place, proposed
`sections.vulnerabilities.scanned_assets.locations[] {host, ips[] {ip_address, country_code}, reason_code?}`).
Layout: headline (big count + proportion bar, the Section 04 "Scanned assets" pattern) -> map -> country list
grouped OUTSIDE / PREFERRED / LOCATION NOT DETECTED (no preference: HOSTING COUNTRIES / LOCATION NOT
DETECTED). Each country is one line (shape, ISO code, name, domain count) with its domains on a
full-width line under it: full names (copyable, each a link), comma-separated, wrapping only after a comma, so long
subdomains never squeeze a column. No boxes, no table rules; groups are separated by space.
07 Data sovereignty: the same list without bars (countries from the legal terms, not IP based).

Usage: .venv/bin/python -I tools/prototypes/residency_by_domain.py <out.pdf>
Other scripts set LOCATIONS / REGISTER and swap the section bodies the same way main() does.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from reportlab.lib.colors import HexColor  # noqa: E402
from reportlab.pdfbase.pdfmetrics import stringWidth  # noqa: E402
from reportlab.platypus import Spacer, Table, TableStyle  # noqa: E402

from cyberrank_report import components as C  # noqa: E402
from cyberrank_report import geo_map as G  # noqa: E402
from cyberrank_report import theme as T  # noqa: E402
from cyberrank_report.sections import _shared as S  # noqa: E402
from cyberrank_report.sections import s07_data_sovereignty as S07  # noqa: E402
from cyberrank_report.sections import s08_data_residency as S08  # noqa: E402
from cyberrank_report.sections.s04_vulnerabilities import SplitBar  # noqa: E402
MAX_LINES = 5           # domain grid rows per country; past it "+N more" (full list in REGISTER, or every row when None)
REGISTER = 'D.1.3'       # None: the report has no per-domain register (no pointer, every domain inline)
LOCATIONS = []           # the case being rendered: [{host, ips: [{ip_address, country_code, reason_code?}]}]
UNDETECTED = {'location_unknown': 'Location unknown', 'country_code_placeholder': 'Placeholder code “XX”',
              'not_resolved': 'No IP address found'}
GROUP = {'mismatch': 'Outside the preference', 'match': 'Preferred', 'hosting': 'Hosting countries',
         'offmap': 'Location not detected'}
PREF_TINT = HexColor('#B1DDC4')     # preferred share of the headline bar: the 'good' green at 35%, so the red leads
UNKNOWN = HexColor('#7F8EA0')       # not-detected share: >= 3:1 on white (non-text contrast)
W_MARK, W_ISO = 16, 24


# --- data ------------------------------------------------------------------------------------------
def by_country(locations):
    """{a2: [domains]} in scan order and {reason: [domains]} for the domains without a country."""
    hosts, undetected = {}, {}
    for loc in locations:
        if not loc['ips']:
            undetected.setdefault(loc.get('reason_code') or 'not_resolved', []).append(loc['host'])
        for ip in loc['ips']:
            why = ip.get('reason_code')
            if why in UNDETECTED:
                lst = undetected.setdefault(why, [])
            else:
                lst = hosts.setdefault(ip['country_code'], [])
            if loc['host'] not in lst:
                lst.append(loc['host'])
    return hosts, undetected


def hosting_rows(locations):
    """observed_hosting[] (per-country domain counts) as Section 08 receives it, derived here for the mock."""
    hosts, undetected = by_country(locations)
    rows = [{'country_code': a2, 'hosts': len(hs), 'evidence_kind': {'value': 'IP geolocation'}}
            for a2, hs in hosts.items()]
    for why, hs in undetected.items():
        if why != 'not_resolved':
            rows.append({'country': None, 'hosts': len(hs), 'state': 'unavailable', 'reason_code': why})
    return rows


def _domains(hosts, strong):
    """Domains in aligned columns (mono, full names, each a link), as many columns as the widest name allows
    (max 3). At most MAX_LINES grid rows: the last cell then reads '+N more in <register>'. REGISTER None: every
    name, no cut."""
    st = T.STYLES['dense_tech'].clone('dom', textColor=T.BODY if strong else T.MUTED)
    indent = W_MARK + W_ISO
    width = T.CW - indent
    widest = max(stringWidth(h, st.fontName, st.fontSize) for h in hosts) + 12
    k = max(1, min(3, int(width // widest)))
    names = list(hosts)
    if REGISTER and len(names) > k * MAX_LINES:
        keep = k * MAX_LINES - 1
        names = names[:keep] + [None]
    cells = [C.M(f'<a href="https://{C.esc(h)}">{C.esc(h)}</a>', st) if h else
             C.P(f'+{len(hosts) - (len(names) - 1)} more in {REGISTER}', 'dense_muted') for h in names]
    grid = [cells[i:i + k] + [''] * (k - len(cells[i:i + k])) for i in range(0, len(cells), k)]
    t = Table(grid, colWidths=[width / k] * k, hAlign='RIGHT')
    t.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                           ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                           ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    return t


def _row(kind, code, name, n, hosts, strong=False):
    """Country line: shape, ISO code, name, then '<n> domains' (muted) right after the name; domains under it."""
    cnt = '' if n is None else (f'&nbsp;&nbsp;&nbsp;<font color="{C.hexstr(T.MUTED)}">{n} domain'
                                f'{"" if n == 1 else "s"}</font>')
    head = Table([[G.Marker('pref' if kind == 'pref' else kind), C.P(code, 'cell_head'),
                   C.M(C.esc(name) + cnt, 'cell' if kind != 'pref' else 'cell_muted')]],
                 colWidths=[W_MARK, W_ISO, T.CW - W_MARK - W_ISO], hAlign='LEFT')
    head.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                              ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                              ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    parts = [head] + ([_domains(hosts, strong)] if hosts else []) + [Spacer(0, 7)]
    return C.keep(*parts)


def _group_head(kind, n_countries, label=None):
    """Sub-block heading: sentence case at H3 weight, neutral text (colour stays on the row markers)."""
    tail = '' if n_countries is None else f' · {n_countries} {"country" if n_countries == 1 else "countries"}'
    st = T.STYLES['h3'].clone(f'grp_{kind}', spaceBefore=10, spaceAfter=5, keepWithNext=1)
    return C.P(label or (GROUP[kind] + tail), st)


def _headline(hosts, undetected, kind_of, nopref, allowed):
    """Big count + proportion bar, as Section 04 'Scanned assets'."""
    total = len({h for hs in hosts.values() for h in hs} | {h for hs in undetected.values() for h in hs})
    unk = len({h for hs in undetected.values() for h in hs})
    located = total - unk
    grey = f'<font name="{T.LIGHT}" size="12" color="{C.hexstr(T.MUTED)}">'
    if nopref:
        big = C.M(f'{len(hosts)}{grey} hosting {"country" if len(hosts) == 1 else "countries"}</font>', 'kpi_value')
        label = C.P(f'{located} of {total} domains located; no preferred countries set, so nothing is compared',
                    'kpi_label', spaceBefore=2)
        parts = [(located, G.COL['hosting']), (unk, UNKNOWN)]
        legend = [('hosting', f'{located} located'), ('offmap', f'{unk} location not detected')]
    else:
        out = {h for a2, hs in hosts.items() if kind_of(a2) == 'mismatch' for h in hs}
        pref = {h for a2, hs in hosts.items() if kind_of(a2) == 'match' for h in hs} - out
        big = C.M(f'{len(out)}{grey} of {total}</font>', 'kpi_value')
        label = C.P('domains hosted outside the preferred countries', 'kpi_label', spaceBefore=2)
        # full green only when nothing is outside (Section 04 rule); otherwise the good share stays pale
        parts = [(len(out), G.OUTSIDE), (len(pref), PREF_TINT if out else G.COL['match']), (unk, UNKNOWN)]
        legend = [('mismatch', f'{len(out)} outside'), ('match', f'{len(pref)} preferred'),
                  ('offmap', f'{unk} not detected')]
    # drawn markers (G.Marker, as on the map and in the list): every shape the same size
    items = [(kind, txt) for kind, txt in legend if not txt.startswith('0 ')]
    st = T.STYLES['dense_muted']
    cells, widths = [], []
    for kind, txt in items:
        cells += [G.Marker(kind), C.P(txt, st)]
        widths += [12, stringWidth(txt, st.fontName, st.fontSize) + 16]
    leg = Table([cells], colWidths=widths, hAlign='LEFT', spaceBefore=6)
    leg.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                             ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                             ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    top = Table([[[big, label], '', [Spacer(0, 9), SplitBar(parts), leg]]],
                colWidths=[T.COL3, T.GUTTER, T.CW - T.COL3 - T.GUTTER], hAlign='LEFT', spaceAfter=6)
    top.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                             ('RIGHTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 8),
                             ('BOTTOMPADDING', (0, 0), (-1, -1), 10), ('LINEABOVE', (0, 0), (-1, 0), .75, T.RULE)]))
    return top


# --- 08 body ----------------------------------------------------------------------------------------
def residency_body(data):
    allowed = S.allowed(data)
    nopref = data.get('_no_preference') or not allowed
    vm = G.entries(S08._hosting(data), allowed, compare=not nopref)
    pref = set(vm['pref'])
    kind_of = lambda a2: 'hosting' if nopref else 'match' if a2 in pref else 'mismatch'      # noqa: E731
    hosts, undetected = by_country(LOCATIONS)
    out = [C.key_value_list([('Preferred countries', ', '.join(allowed) if allowed else
                              C.P('Not set', 'cell_muted'))]),
           _headline(hosts, undetected, kind_of, nopref, allowed)]
    out += G.map_flowables(vm, G.choose(vm))
    order = sorted(hosts, key=lambda a2: (['mismatch', 'match', 'hosting'].index(kind_of(a2)), -len(hosts[a2])))
    for kind in ('mismatch', 'match', 'hosting'):
        codes = [a2 for a2 in order if kind_of(a2) == kind]
        unused = [a2 for a2 in vm['pref_only']] if kind == 'match' else []
        if not codes and not unused:
            continue
        out.append(_group_head(kind, len(codes)))
        for a2 in codes:
            n = len(hosts[a2])
            out.append(_row(kind, a2, G.name(a2), n, hosts[a2], strong=kind != 'match'))
        for a2 in unused:
            out.append(_row('pref', a2, f'{G.name(a2)} · preferred, no domain hosted', None, []))
    if undetected:
        n_un = len({h for hs in undetected.values() for h in hs})
        out.append(_group_head('offmap', None, f'Location not detected · {n_un} domain{"s" if n_un != 1 else ""}'))
        for why, hs in undetected.items():
            out.append(_row('offmap', '', UNDETECTED[why], len(hs), hs))
    out.append(C.note(f'Location method: IP geolocation of the domains found by the vulnerability scan. {G.CAVEAT}'))
    return out


# --- 07 body ----------------------------------------------------------------------------------------
def sovereignty_body(data):
    allowed = S.allowed(data)
    found = S07.countries(data)
    acc = {G.resolve(a)[1] or a for a in allowed}
    out = [C.key_value_list([('Accepted jurisdictions', ', '.join(allowed) if allowed else C.P('Not set', 'cell_muted'))])]
    if not found:
        out.append(_group_head('offmap', None, 'Governing law / courts'))
        out.append(_row('offmap', '', 'Not found: no governing law or court location in the legal terms', None, []))
        return out
    resolved = [(G.resolve(c)[1] or '', c) for c in found]
    if not allowed:
        out.append(_group_head('hosting', None, 'Governing law / courts found'))
        for a2, name in resolved:
            out.append(_row('hosting', a2, name, None, []))
        return out
    for kind, label in (('mismatch', 'Outside the accepted jurisdictions'), ('match', 'Accepted')):
        rows = [(a2, n) for a2, n in resolved if ((a2 or n) in acc) == (kind == 'match')]
        if rows:
            out.append(_group_head(kind, None, f'{label} · {len(rows)}'))
            for a2, name in rows:
                out.append(_row(kind, a2, name, None, []))
    return out


# --- synthetic cases (example.com / example.net only) ----------------------------------------------
def _loc(host, a2):
    if a2 in UNDETECTED:
        return {'host': host, 'ips': [{'ip_address': None, 'country_code': None, 'reason_code': a2}]}
    return {'host': host, 'ips': [{'ip_address': None, 'country_code': a2}]}


TEN = ([_loc('example.com', 'ID')] + [_loc(f'mta{i:02d}.example.com', 'ID') for i in range(1, 70)]
       + [_loc(f'{s}.example.com', 'MY') for s in ('kl1', 'kl2', 'pay-my', 'vpn-my', 'sso-my')]
       + [_loc(f'{s}.example.com', 'US') for s in ('img', 'cdn', 'files', 'status')]
       + [_loc(f'{s}.example.com', a2) for s, a2 in (('api-sg', 'SG'), ('af-staging', 'CA'), ('backup', 'DE'),
                                                      ('edge-jp', 'JP'), ('mx2', 'NL'), ('mail-eu', 'IE'),
                                                      ('server.monitoring.root', 'AU'))]
       + [_loc(f'{s}.example.com', 'location_unknown') for s in (
           'dev', 'dev.gcp', 'ns3', 'ns4', 'dashboard', 'k8s', 'k8s.gcp', 'master', 'alt711811314892810745',
           'multisend-unsubscribe', '_submission._tcp', 'www.guyz.club', 'psiap-dev.devs')])

CASES = [  # (key, banner, allowed, locations, sovereignty observed)
    ('ten_pref', 'MOCK · 10 countries, preference ID + MY + SG (long subdomain names included)',
     ['ID', 'MY', 'SG'], TEN, ['Indonesia', 'Singapore', 'United States of America']),
    ('ten_nopref', 'MOCK · same data, no preference set', [], TEN, ['Indonesia', 'Singapore']),
]


def report(allowed, locations, found, org='Example Org', domain='example.com'):
    sov = {'state': 'findings', 'enabled': bool(allowed), 'allowed_set': allowed,
           'match_state': 'mismatch' if allowed else None,
           'observed_jurisdiction': found or {'value': None, 'state': 'unavailable', 'reason_code': 'not_identified'}}
    return {'identity': {'organisation_name': org, 'domain': domain},
            'snapshot': {'assessed_at': {'value': '2026-10-02', 'precision': 'day'},
                         'generated_at': {'value': '2026-10-03', 'precision': 'day'}},
            'sections': {'data_sovereignty': {k: v for k, v in sov.items() if v is not None},
                         'data_residency': {'state': 'findings', 'enabled': bool(allowed), 'allowed_set': allowed,
                                            'match_state': 'mismatch' if allowed else None,
                                            'observed_hosting': hosting_rows(locations)}}}


def install():
    """Swap the section bodies (prototype only; the production modules are unchanged on disk)."""
    S08._body = residency_body
    S07._body = sovereignty_body
    S08.metrics = lambda data: []         # the headline carries the counts; no KPI strip above it


def main(out):
    import pymupdf
    from cyberrank_report import qa
    from cyberrank_report.build import build, validate
    install()
    merged = pymupdf.open()
    with tempfile.TemporaryDirectory() as tmp:
        for key, banner, allowed, locs, found in CASES:
            LOCATIONS[:] = locs
            qa.ISSUES.clear()
            p = Path(tmp) / f'{key}.pdf'
            rep = report(allowed, locs, found)
            rep['sections'] = {k: {kk: vv for kk, vv in v.items() if vv is not None} for k, v in rep['sections'].items()}
            build(validate(rep), p, only=['s07', 's08'])
            src = pymupdf.open(p)
            first = len(merged)
            merged.insert_pdf(src, from_page=2)          # skip cover + contents
            merged[first].insert_text((40, 60), banner, fontsize=7, color=(0.39, 0.44, 0.51))
    merged.save(out, garbage=3, deflate=True)
    print(out, len(merged), 'pages')


if __name__ == '__main__':
    main(sys.argv[1])
