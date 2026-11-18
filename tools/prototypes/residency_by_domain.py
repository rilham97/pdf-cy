"""Prototype (mock, not wired into the report): Section 08 with the hosting countries listed per domain.

Domain -> IP -> country comes from the vulnerability scan (one shared place, proposed
`sections.vulnerabilities.scanned_assets.locations[] {host, ips[] {ip_address, country_code}, reason_code?}`).
Section 08 keeps its map; the country table below it names the domains hosted in each country, and a
second table lists the domains whose location was not detected (IP found but country unknown,
placeholder code "XX", no IP address found). Long domain lists are cut with "+N more" (full list in D.1.3).

Usage: .venv/bin/python -I tools/prototypes/residency_by_domain.py <out.pdf>
Renders only the Section 08 pages (cover and contents dropped) for two synthetic cases.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from reportlab.pdfbase.pdfmetrics import stringWidth  # noqa: E402

from cyberrank_report import components as C  # noqa: E402
from cyberrank_report import geo_map as G  # noqa: E402
from cyberrank_report import theme as T  # noqa: E402
from cyberrank_report.sections import _shared as S  # noqa: E402
from cyberrank_report.sections import s08_data_residency as S08  # noqa: E402

DOMAINS_INLINE = 12      # domains per country printed in the section; the rest -> "+N more" (D.1.3)
REGISTER = 'D.1.3'
UNDETECTED = {           # reason -> (row label, comparison cell)
    'location_unknown': ('IP found, country unknown', 'unknown'),
    'country_code_placeholder': ('Placeholder code “XX”', 'unknown'),
    'not_resolved': ('No IP address found', None),
}


# --- synthetic data (example.com + documentation IPs only) ---------------------------------
def _ip(a2, ip):
    return {'ip_address': ip, 'country_code': a2}


DEMO_LOCATIONS = [
    {'host': 'example.com', 'ips': [_ip('GB', '192.0.2.1'), _ip('GB', '192.0.2.2'), _ip('US', '198.51.100.1')]},
    {'host': 'www.example.com', 'ips': [_ip('GB', '192.0.2.3'), _ip('GB', '192.0.2.4'), _ip('US', '198.51.100.2')]},
    {'host': 'portal.example.com', 'ips': [_ip('GB', '192.0.2.10'), _ip('DE', '198.51.100.10')]},
    {'host': 'mail.example.com', 'ips': [_ip('GB', '192.0.2.20'), _ip('GB', '192.0.2.21')]},
    {'host': 'api.example.com', 'ips': [_ip('GB', '192.0.2.30'), _ip('DE', '198.51.100.11'), _ip('SG', '203.0.113.1')]},
    {'host': 'vpn.example.com', 'ips': [_ip('GB', '192.0.2.15')]},
    {'host': 'status.example.com', 'ips': [_ip('US', '198.51.100.3'), _ip('US', '198.51.100.4')]},
    {'host': 'cdn.example.com', 'ips': [_ip('DE', '198.51.100.12'), _ip('DE', '198.51.100.13'), _ip('US', '198.51.100.5'),
                                        _ip('SG', '203.0.113.2'), _ip('AU', '203.0.113.20'), _ip('AU', '203.0.113.21')]},
    {'host': 'files.example.com', 'ips': [_ip('BR', '203.0.113.50')]},
    {'host': 'auth.example.com', 'ips': [{'ip_address': '203.0.113.60', 'country_code': None,
                                          'reason_code': 'location_unknown'}]},
    {'host': 'legacy.example.com', 'ips': [{'ip_address': '192.0.2.80', 'country_code': 'XX',
                                            'reason_code': 'country_code_placeholder'}]},
    {'host': 'old.example.com', 'ips': [], 'reason_code': 'not_resolved'},
]

# a long list (Gmail-like): one country with many domains, many hosts without a location
LONG_LOCATIONS = (
    [{'host': f'alt{i}.mx.example.net', 'ips': [_ip('US', f'198.51.100.{i + 1}')]} for i in range(46)]
    + [{'host': 'example.net', 'ips': [_ip('US', '198.51.100.100'), _ip('IE', '192.0.2.100')]}]
    + [{'host': f'edge{i}.example.net', 'ips': [{'ip_address': f'203.0.113.{i + 1}', 'country_code': None,
                                                 'reason_code': 'location_unknown'}]} for i in range(18)]
    + [{'host': f'relay{i}.example.net', 'ips': [{'ip_address': f'192.0.2.{i + 1}', 'country_code': 'XX',
                                                  'reason_code': 'country_code_placeholder'}]} for i in range(5)]
    + [{'host': f'_srv{i}._tcp.example.net', 'ips': [], 'reason_code': 'not_resolved'} for i in range(4)]
)


def _hosting_rows(locations):
    """observed_hosting[] as the backend sends it today (per-country counts), derived here only for the mock."""
    by, unknown, xx = {}, 0, 0
    for loc in locations:
        for ip in loc['ips']:
            if ip.get('reason_code') == 'location_unknown':
                unknown += 1
            elif ip.get('reason_code') == 'country_code_placeholder':
                xx += 1
            else:
                by[ip['country_code']] = by.get(ip['country_code'], 0) + 1
    rows = [{'country_code': a2, 'hosts': n, 'evidence_kind': {'value': 'IP geolocation'}} for a2, n in by.items()]
    if xx:
        rows.append({'country': None, 'hosts': xx, 'state': 'unavailable', 'reason_code': 'country_code_placeholder'})
    if unknown:
        rows.append({'country': None, 'hosts': unknown, 'state': 'unavailable', 'reason_code': 'location_unknown',
                     'match_state': 'mismatch'})
    return rows


CASES = [  # (key, banner, allowed, locations)
    ('demo', 'MOCK · Section 08 with domains per country (example.com, 12 domains)',
     ['GB', 'DE', 'IE', 'US', 'SG', 'AU'], DEMO_LOCATIONS),
    ('long', 'MOCK · long lists: 47 domains in one country, 27 not detected (cut at 12, rest in D.1.3)',
     ['AR'], LONG_LOCATIONS),
]
LOCATIONS = []           # the case being rendered (prototype only: read by _body below)


# --- prototype rendering ---------------------------------------------------------------------
def _domains_cell(hosts, extra_note=None):
    """Comma-separated host list (mono, commas in the body face; wraps only after a comma) + '+N more'."""
    mono = T.STYLES['cell_tech']
    shown, rest = hosts[:DOMAINS_INLINE], len(hosts) - DOMAINS_INLINE
    sep = f'<font name="{T.LIGHT}">,</font> '
    text = sep.join(f'<font name="{mono.fontName}" size="{mono.fontSize}">{C.esc(h).replace(" ", chr(160))}</font>'
                    for h in shown)
    if rest > 0:
        text += f'<font color="{C.hexstr(T.MUTED)}">, +{rest} more in {REGISTER}</font>'
    if extra_note:
        text += f'<br/><font color="{C.hexstr(T.MUTED)}">{C.esc(extra_note)}</font>'
    return C.M(text, 'cell')


def _by_country(locations):
    """{a2: [hosts in scan order]}, {a2: ip count}, undetected {reason: [(host, ip)]}."""
    hosts, ips, undetected = {}, {}, {k: [] for k in UNDETECTED}
    for loc in locations:
        if not loc['ips']:
            undetected[loc.get('reason_code') or 'not_resolved'].append((loc['host'], None))
        for ip in loc['ips']:
            why = ip.get('reason_code')
            if why in UNDETECTED:
                undetected[why].append((loc['host'], ip['ip_address']))
                continue
            a2 = ip['country_code']
            ips[a2] = ips.get(a2, 0) + 1
            if loc['host'] not in hosts.setdefault(a2, []):
                hosts[a2].append(loc['host'])
    return hosts, ips, {k: v for k, v in undetected.items() if v}


def _country_table(vm, nopref):
    hosts, ips, _ = _by_country(LOCATIONS)
    multi = {h for a2, hs in hosts.items() for h in hs if sum(h in x for x in hosts.values()) > 1}
    order = {'mismatch': 0, 'match': 1, 'hosting': 1}
    seen, rows = set(), []
    for e in sorted(vm['hosted'], key=lambda e: order.get(e['kind'], 2)):
        a2 = e['a2']
        if a2 in seen:
            continue
        seen.add(a2)
        ds = hosts.get(a2, [])
        rows.append([G.Marker(e['kind']), C.P(f'{G.name(a2)} ({a2})', 'cell'),
                     _domains_cell(ds) if ds else C.P('No domain recorded', 'cell_muted'),
                     ips.get(a2, 0), S.match_chip('no_preference' if nopref else e['kind'])])
    for a2 in vm['pref_only']:
        rows.append([G.Marker('pref'), C.P(f'{G.name(a2)} ({a2})', 'cell'),
                     C.P('No domain hosted here', 'cell_muted'), 'None', C.P('Preferred country', 'cell_muted')])
    labels = [r[4].text if hasattr(r[4], 'text') else C.plain(r[4]) for r in rows]
    mw = max(stringWidth(t, T.LIGHT, 8.6) for t in labels) + 16 + 2 * T.CELL_PAD_H
    cw, hw = 118, 40
    t = C.compact_table(['', 'Country', 'Domains', 'Hosts', 'Against the preference'], rows,
                        widths=[24, cw, T.CW - 24 - cw - hw - mw, hw, mw], numeric_cols=(3,),
                        title='Hosting countries by domain')
    out = [C.heading('Hosting countries by domain', 2), t]
    if multi:
        n = len(multi)
        out.append(C.P(f'{n} domain{"s use servers" if n != 1 else " uses servers"} in more than one country, so '
                       f'{"they appear" if n != 1 else "it appears"} under each country. Hosts = number of IP addresses.',
                       'note_flush', spaceBefore=4))
    return out


def _undetected_table(nopref):
    _, _, undetected = _by_country(LOCATIONS)
    if not undetected:
        return []
    rows, n_dom = [], len({h for v in undetected.values() for h, _ in v})
    for why, items in undetected.items():
        label, cmp_ = UNDETECTED[why]
        hosts = list(dict.fromkeys(f'{h} ({ip})' if ip else h for h, ip in items))
        chip = (S.match_chip('no_preference' if nopref else cmp_) if cmp_
                else C.P('Not hosted', 'cell_muted'))
        rows.append([G.Marker('offmap'), C.P(label, 'cell_muted'), _domains_cell(hosts),
                     sum(1 for _, ip in items if ip) or 'None', chip])
    labels = [r[4].text if hasattr(r[4], 'text') else C.plain(r[4]) for r in rows]
    mw = max(stringWidth(t, T.LIGHT, 8.6) for t in labels) + 16 + 2 * T.CELL_PAD_H
    cw, hw = 118, 40
    t = C.compact_table(['', 'Why', 'Domains', 'Hosts', 'Against the preference'], rows,
                        widths=[24, cw, T.CW - 24 - cw - hw - mw, hw, mw], numeric_cols=(3,),
                        title='Location not detected')
    return [C.heading(f'Location not detected · {n_dom} domain{"s" if n_dom != 1 else ""}', 2), t,
            C.P('These domains are not on the map and not counted in any country.', 'note_flush', spaceBefore=4)]


def _body(data):
    allowed = S.allowed(data)
    hosting = S08._hosting(data)
    nopref = data.get('_no_preference')
    out = [C.key_value_list([('Preferred countries', S.join(allowed)),
                             ('Against the preference', S.match_chip(S.matched(data)))])]
    vm = G.entries(hosting, allowed, compare=not nopref)
    out += G.map_flowables(vm, G.choose(vm))
    out += _country_table(vm, nopref)
    out += _undetected_table(nopref)
    out.append(C.P(f'Full list of domains, IP addresses and countries: Appendix {REGISTER}.', 'note_flush',
                   spaceBefore=6))
    out.append(C.note('Location method: IP geolocation of the hosts found by the vulnerability scan. ' + G.CAVEAT))
    return out


def _report(allowed, locations):
    return {'identity': {'organisation_name': 'Example Org', 'domain': 'example.com'},
            'snapshot': {'assessed_at': {'value': '2026-10-02', 'precision': 'day'},
                         'generated_at': {'value': '2026-10-03', 'precision': 'day'}},
            'sections': {'data_residency': {
                'state': 'findings', 'enabled': True, 'allowed_set': allowed, 'match_state': 'mismatch',
                'observed_hosting': _hosting_rows(locations)}}}


def main(out):
    import pymupdf
    from cyberrank_report import qa
    from cyberrank_report.build import build, validate
    S08._body = _body                     # prototype swap; the production module is unchanged
    merged = pymupdf.open()
    with tempfile.TemporaryDirectory() as tmp:
        for key, banner, allowed, locs in CASES:
            LOCATIONS[:] = locs
            qa.ISSUES.clear()
            p = Path(tmp) / f'{key}.pdf'
            build(validate(_report(allowed, locs)), p, only=['s08'])
            src = pymupdf.open(p)
            first = len(merged)
            merged.insert_pdf(src, from_page=2)          # skip cover + contents
            merged[first].insert_text((40, 60), banner, fontsize=7, color=(0.39, 0.44, 0.51))
    merged.save(out, garbage=3, deflate=True)
    print(out, len(merged), 'pages')


if __name__ == '__main__':
    main(sys.argv[1])
