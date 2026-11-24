"""08 Data residency (demerit rule F): where the organisation's public systems are hosted (IP
location), compared with the countries preferred by the report owner/requestor.

Not privacy criterion H 'Data residency' (section 03), which scores what the policy says about
location and transfer.

Two layout modes (100% backward compatible):
- Domain-level mode (when `data_residency.locations[]` or `vulnerabilities.scanned_assets.locations[]`
  is present): Preferred countries row -> headline count + SplitBar proportion bar + G.Marker legend
  -> map (modes A2 / A3) -> vertical country list grouped Outside / Preferred / Hosting countries /
  Location not detected, with Opsi 1 sorted JetBrains Mono domain grids (main -> www. -> A-Z, no
  dead hyperlinks, overflow-safe TechText). When any country exceeds MAX_LINES grid rows, it shows
  '+N more in D.1.3' and Appendix D renders the full D.1.3 register.
- Legacy aggregate mode (when only `observed_hosting[]` is present): KPI strip -> key/value list ->
  map -> compact country table.
"""
from collections import OrderedDict

from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Spacer, Table, TableStyle

from .. import components as C
from .. import geo_map as G
from .. import qa
from .. import theme as T
from . import _shared as S
from .s04_vulnerabilities import SplitBar

TEXT = {
    'no_preference': 'Not compared: no preference set. The hosting locations found are shown without validation.',
    'match': 'All located hosts are in the preferred countries ({allowed}), compared with {owner}.',
    'mismatch': 'Public systems were observed outside the preferred countries ({allowed}), compared with '
                '{owner}, so customer data may be held outside those countries.',
    'unknown': 'Hosting locations could not be compared with {owner} ({allowed}).',
}

MAX_LINES = 5                       # domain grid rows per country before overflowing to D.1.3
REG_ID = 'D.1.3'                    # Appendix D sub-register emitted only when a country overflows MAX_LINES
W_MARK, W_ISO = 16, 24              # country header indent (map marker + ISO-2 code)
PREF_TINT = HexColor('#B1DDC4')     # preferred share when outside hosts exist (35% green so red leads)
UNKNOWN_BAR = HexColor('#7F8EA0')   # not-detected share (>= 3:1 non-text contrast on white)
GROUP_LABELS = {
    'mismatch': 'Outside the preference',
    'match': 'Preferred',
    'hosting': 'Hosting countries',
    'offmap': 'Location not detected',
}
UNDETECTED_LABELS = {
    'location_unknown': 'Location unknown',
    'not_resolved': 'No IP address found',
}
_DOM_STRONG = T.STYLES['dense_tech'].clone('s08_dom_strong', textColor=T.BODY)
_DOM_MUTED = T.STYLES['dense_tech'].clone('s08_dom_muted', textColor=T.MUTED)


# --- shared & domain-location helpers -------------------------------------------------------------
def _hosting(data):
    return [h for h in data.get('observed_hosting') or [] if isinstance(h, dict)]


def _clean_host(v):
    s = str(v or '').strip().rstrip('.')
    return s or None


def locations_of(data, report=None):
    """Per-domain location records from `data_residency.locations[]` or fallback
    `vulnerabilities.scanned_assets.locations[]`."""
    raw = data.get('locations')
    if not raw and isinstance(report, dict):
        sa = ((report.get('sections') or {}).get('vulnerabilities') or {}).get('scanned_assets')
        if isinstance(sa, dict):
            raw = sa.get('locations')
    return [x for x in (raw or []) if isinstance(x, dict) and _clean_host(x.get('host'))]


def _root_domain(hosts, domain=None):
    """Main domain for Opsi 1 ordering (identity.domain when present among hosts, else shortest)."""
    low = [h.lower() for h in hosts if h]
    dom = str(domain or '').strip().lower().rstrip('.')
    if dom and (dom in low or any(h.endswith('.' + dom) for h in low)):
        return dom
    return min(low, key=lambda h: (h.count('.'), len(h), h)) if low else dom


def _domain_sort_key(host, root):
    """Opsi 1 order: main domain -> www.<main> -> other subdomains A-Z."""
    h = host.lower().rstrip('.')
    if root and h == root:
        return (0, h)
    if root and h == f'www.{root}':
        return (1, h)
    return (2, h)


def _undetected_label(key):
    why, detail = key
    if why == 'country_code_placeholder':
        code = detail or 'XX'
        return f'Placeholder code “{code}”' if code else 'Blank country code'
    if why == 'unresolved':
        return f'{detail}: country name not recognised' if detail else 'Country name not recognised'
    if why in UNDETECTED_LABELS:
        return UNDETECTED_LABELS[why]
    return C.sentence(C.reason_text({'reason_code': why}))[:-1]


def by_country(locations, root_domain=None):
    """Group per-domain records into:
    - hosts: {a2: [sorted unique domain names]}
    - undetected: {(reason_code, detail): [sorted unique domain names]}
    - domain_ips: {(bucket_key, host): [ip strings]} for Appendix D.1.3 register.
    """
    hosts, undetected, domain_ips = {}, OrderedDict(), {}
    all_names = [_clean_host(loc.get('host')) for loc in locations]
    root = _root_domain([h for h in all_names if h], root_domain)

    for loc in locations:
        host = _clean_host(loc.get('host'))
        if not host:
            continue
        ips = [ip for ip in (loc.get('ips') or []) if isinstance(ip, dict)]
        if not ips:
            why = loc.get('reason_code') or 'not_resolved'
            key = (why, None)
            lst = undetected.setdefault(key, [])
            if host not in lst:
                lst.append(host)
            domain_ips.setdefault(('offmap', key, host), [])
            continue
        for ip in ips:
            ip_addr = str(ip.get('ip_address') or ip.get('ip') or '').strip()
            why = ip.get('reason_code')
            raw_cc = str(ip.get('country_code') or ip.get('country') or '').strip()
            if why == 'country_code_placeholder':
                key = ('country_code_placeholder', raw_cc.upper() or 'XX')
                lst = undetected.setdefault(key, [])
                if host not in lst:
                    lst.append(host)
                if ip_addr:
                    domain_ips.setdefault(('offmap', key, host), []).append(ip_addr)
                continue
            if why in ('location_unknown', 'not_resolved'):
                key = (why, None)
                lst = undetected.setdefault(key, [])
                if host not in lst:
                    lst.append(host)
                if ip_addr:
                    domain_ips.setdefault(('offmap', key, host), []).append(ip_addr)
                continue
            kind, a2 = G.resolve(raw_cc) if raw_cc else ('unknown', None)
            if kind == 'country' and a2:
                lst = hosts.setdefault(a2, [])
                if host not in lst:
                    lst.append(host)
                if ip_addr:
                    domain_ips.setdefault(('country', a2, host), []).append(ip_addr)
            elif kind == 'placeholder':
                key = ('country_code_placeholder', raw_cc.upper())
                lst = undetected.setdefault(key, [])
                if host not in lst:
                    lst.append(host)
                if ip_addr:
                    domain_ips.setdefault(('offmap', key, host), []).append(ip_addr)
            else:
                key = ('unresolved', raw_cc) if raw_cc else ('location_unknown', None)
                lst = undetected.setdefault(key, [])
                if host not in lst:
                    lst.append(host)
                if ip_addr:
                    domain_ips.setdefault(('offmap', key, host), []).append(ip_addr)

    for a2 in hosts:
        hosts[a2] = sorted(hosts[a2], key=lambda h: _domain_sort_key(h, root))
    for key in undetected:
        undetected[key] = sorted(undetected[key], key=lambda h: _domain_sort_key(h, root))
    for k, ips in domain_ips.items():
        domain_ips[k] = list(OrderedDict.fromkeys(ips))
    return hosts, undetected, domain_ips


def hosting_rows_from_locations(locations):
    """Derive `observed_hosting[]` counts from per-domain `locations[]` when not explicitly sent."""
    hosts, undetected, _ = by_country(locations)
    rows = [{'country_code': a2, 'hosts': len(hs), 'evidence_kind': {'value': 'IP geolocation'}}
            for a2, hs in sorted(hosts.items(), key=lambda kv: (-len(kv[1]), G.name(kv[0])))]
    for (why, detail), hs in undetected.items():
        if why == 'not_resolved':
            continue
        if why == 'country_code_placeholder':
            rows.append({'country': None, 'country_code': detail or 'XX', 'hosts': len(hs),
                         'state': 'unavailable', 'reason_code': 'country_code_placeholder'})
        elif why == 'unresolved':
            rows.append({'country': detail, 'hosts': len(hs), 'state': 'unavailable'})
        else:
            rows.append({'country': None, 'hosts': len(hs), 'state': 'unavailable',
                         'reason_code': why or 'location_unknown'})
    return rows


def _grid_cols(names, width, st):
    """Fit 1-3 aligned mono columns according to the widest domain name."""
    widest = max(stringWidth(h, st.fontName, st.fontSize) for h in names) + 12
    return max(1, min(3, int(width // widest)))


def _needs_cap(hosts_map, undetected_map):
    """True when any country or undetected bucket exceeds MAX_LINES grid rows."""
    width = T.CW - (W_MARK + W_ISO)
    for hs in hosts_map.values():
        if hs and len(hs) > _grid_cols(hs, width, _DOM_STRONG) * MAX_LINES:
            return True
    for hs in undetected_map.values():
        if hs and len(hs) > _grid_cols(hs, width, _DOM_MUTED) * MAX_LINES:
            return True
    return False


def has_overflow(report):
    """Used by Appendix D to decide whether to emit the D.1.3 domain-locations register."""
    sec = (report.get('sections') or {}).get('data_residency')
    if not isinstance(sec, dict) or sec.get('_card_only'):
        return False
    locs = sec.get('_locations') or locations_of(sec, report)
    if not locs:
        return False
    root = sec.get('_root_domain') or (report.get('identity') or {}).get('domain')
    hosts, undetected, _ = by_country(locs, root)
    return _needs_cap(hosts, undetected)


def register_data(report):
    """Structured groups & domain rows for Appendix D.1.3, matching Section 08's exact order."""
    sec = (report.get('sections') or {}).get('data_residency') or {}
    locs = sec.get('_locations') or locations_of(sec, report)
    root = sec.get('_root_domain') or (report.get('identity') or {}).get('domain')
    allowed = S.allowed(sec)
    nopref = bool(sec.get('_no_preference') or not allowed)
    hosting = _hosting(sec) or hosting_rows_from_locations(locs)
    vm = G.entries(hosting, allowed, compare=not nopref)
    pref = set(vm['pref'])
    kind_of = lambda a2: 'hosting' if nopref else ('match' if a2 in pref else 'mismatch')  # noqa: E731
    hosts, undetected, domain_ips = by_country(locs, root)
    order = sorted(hosts, key=lambda a2: (['mismatch', 'match', 'hosting'].index(kind_of(a2)),
                                          -len(hosts[a2]), G.name(a2)))
    groups = []
    for kind in ('mismatch', 'match', 'hosting'):
        codes = [a2 for a2 in order if kind_of(a2) == kind]
        if not codes:
            continue
        rows = []
        status = 'Not compared' if nopref else ('Preferred' if kind == 'match' else 'Outside preference')
        for a2 in codes:
            cname = f'{G.name(a2)} ({a2})'
            for h in hosts[a2]:
                ips = ', '.join(domain_ips.get(('country', a2, h), [])) or '—'
                rows.append((h, ips, cname, status))
        groups.append((GROUP_LABELS[kind], rows))
    if undetected:
        rows = []
        for key, hs in undetected.items():
            lbl = _undetected_label(key)
            for h in hs:
                ips = ', '.join(domain_ips.get(('offmap', key, h), [])) or '—'
                rows.append((h, ips, lbl, 'Location not detected'))
        groups.append((GROUP_LABELS['offmap'], rows))
    unique_total = len({h for hs in hosts.values() for h in hs} | {h for hs in undetected.values() for h in hs})
    return groups, unique_total


# --- section hooks --------------------------------------------------------------------------------
def adjust(data, report):
    data = S.with_snapshot_pref(data, report, 'residency_allowed_countries')
    locs = locations_of(data, report)
    if locs:
        dom = (report.get('identity') or {}).get('domain') if isinstance(report, dict) else None
        patch = {'_locations': locs, '_root_domain': dom}
        if not _hosting(data):
            patch['observed_hosting'] = hosting_rows_from_locations(locs)
        data = {**data, **patch}
    if _hosting(data) and S.no_pref(data) and data.get('state') in S.NO_RESULT and not data.get('_card_only'):
        # preference list off but hosts observed (the scan's data, not the preference's): the hosting still
        # prints, marked 'Not compared', whatever no-result state the payload sends; its own card stays
        data = {**data, '_no_preference': True}
    out = S.adjust_compared(data, bool(data.get('observed_hosting') or locs),
                            data.get('allowed_set') or data.get('observed_hosting') or locs, 'Data residency')
    intro = out.get('intro_source')
    if isinstance(intro, str) and 'where you allow data to live' in intro:   # preference = report owner/requestor's
        out = {**out, 'intro_source': intro.replace('where you allow data to live',
                                                    'the countries preferred by the report owner/requestor')}
    return out


card = S.card


def _text(data):
    return TEXT[S.matched(data)].format(allowed=S.join(S.allowed(data)), owner=S.OWNER)


def verdict(data, ctx):
    return None if data.get('_card_only') else _text(data)


def metrics(data):
    """Payload metrics; in domain-grid mode the headline + proportion bar carries the counts, so no
    derived KPI strip is added. In legacy aggregate mode, derive Hosts observed + Countries identified."""
    ms = [m for m in data.get('metrics') or [] if isinstance(m, dict)]
    if ms or data.get('_locations'):
        return ms
    rows = _hosting(data)
    if not rows or not all(isinstance(G.host_count(h), int) for h in rows):
        return ms
    st = data.get('state')
    countries = {e['a2'] for e in G.entries(rows, [], compare=False)['hosted']}
    return [{'id': 'hosts_observed', 'label': 'Hosts observed', 'value': sum(G.host_count(h) for h in rows),
             'unit': 'hosts', 'state': st},
            {'id': 'countries_identified', 'label': 'Countries identified', 'value': len(countries),
             'unit': 'countries', 'state': st}]


# --- domain-grid view (upgraded residency_by_domain) ----------------------------------------------
def _domain_grid(names, strong, cap_rid=None):
    """Aligned 1-3 column mono grid using overflow-safe TechText (no dead hyperlinks)."""
    st = _DOM_STRONG if strong else _DOM_MUTED
    width = T.CW - (W_MARK + W_ISO)
    k = _grid_cols(names, width, st)
    shown = list(names)
    extra = 0
    if cap_rid and len(shown) > k * MAX_LINES:
        keep = k * MAX_LINES - 1
        extra = len(shown) - keep
        shown = shown[:keep]
    cells = [C.TechText(h, st) for h in shown]
    if extra:
        cells.append(C.P(f'+{C.fmt_number(extra)} more in {cap_rid}', 'dense_muted'))
    grid = [cells[i:i + k] + [''] * (k - len(cells[i:i + k])) for i in range(0, len(cells), k)]
    t = Table(grid, colWidths=[width / k] * k, hAlign='RIGHT')
    t.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return t


def _country_row(kind, code, name, n, domains, strong=False, cap_rid=None):
    """Country header line (map shape + ISO-2 + country name + domain count) with its domain grid."""
    cnt = ('' if n is None else
           f'&nbsp;&nbsp;&nbsp;<font color="{C.hexstr(T.MUTED)}">{C.fmt_number(n)} domain'
           f'{"" if n == 1 else "s"}</font>')
    head = Table([[G.Marker('pref' if kind == 'pref' else kind),
                   C.P(code, 'cell_head'),
                   C.M(C.esc(name) + cnt, 'cell' if kind != 'pref' else 'cell_muted')]],
                 colWidths=[W_MARK, W_ISO, T.CW - W_MARK - W_ISO], hAlign='LEFT')
    head.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    parts = [head] + ([_domain_grid(domains, strong, cap_rid=cap_rid)] if domains else []) + [Spacer(0, 7)]
    return C.keep(*parts)


def _group_head(kind, n_countries, label=None):
    """Neutral H3 sub-group heading (colour stays on the map markers)."""
    if label is None:
        if n_countries is None:
            label = GROUP_LABELS[kind]
        elif n_countries == 0:
            label = f'{GROUP_LABELS[kind]} · none hosted'
        else:
            label = f'{GROUP_LABELS[kind]} · {n_countries} {"country" if n_countries == 1 else "countries"}'
    st = T.STYLES['h3'].clone(f's08_grp_{kind}', spaceBefore=10, spaceAfter=5, keepWithNext=1)
    return C.P(label, st)


def _headline(hosts, undetected, kind_of, nopref):
    """Big count + SplitBar proportion bar + drawn G.Marker legend."""
    located_set = {h for hs in hosts.values() for h in hs}
    undet_set = {h for hs in undetected.values() for h in hs}
    all_set = located_set | undet_set
    total = len(all_set)
    unk = len(all_set - located_set)
    located = len(located_set)
    grey = f'<font name="{T.LIGHT}" size="12" color="{C.hexstr(T.MUTED)}">'
    if nopref:
        n_c = len(hosts)
        big = C.M(f'{C.fmt_number(n_c)}{grey} hosting {"country" if n_c == 1 else "countries"}</font>', 'kpi_value')
        label = C.P(f'{C.fmt_number(located)} of {C.fmt_number(total)} domains located; '
                    'no preferred countries set, so nothing is compared', 'kpi_label', spaceBefore=2)
        parts = [(located, G.COL['hosting']), (unk, UNKNOWN_BAR)]
        legend = [('hosting', f'{C.fmt_number(located)} located'),
                  ('offmap', f'{C.fmt_number(unk)} location not detected')]
    else:
        out = {h for a2, hs in hosts.items() if kind_of(a2) == 'mismatch' for h in hs}
        pref = {h for a2, hs in hosts.items() if kind_of(a2) == 'match' for h in hs} - out
        big = C.M(f'{C.fmt_number(len(out))}{grey} of {C.fmt_number(total)}</font>', 'kpi_value')
        label = C.P('domains hosted outside the preferred countries', 'kpi_label', spaceBefore=2)
        # full green only when nothing is outside; otherwise preferred share stays pale so outside leads
        parts = [(len(out), G.OUTSIDE), (len(pref), PREF_TINT if out else G.COL['match']), (unk, UNKNOWN_BAR)]
        legend = [('mismatch', f'{C.fmt_number(len(out))} outside'),
                  ('match', f'{C.fmt_number(len(pref))} preferred'),
                  ('offmap', f'{C.fmt_number(unk)} not detected')]

    items = [(kind, txt) for kind, txt in legend if not txt.startswith('0 ')]
    st = T.STYLES['dense_muted']
    cells, widths = [], []
    for kind, txt in items:
        cells += [G.Marker(kind), C.P(txt, st)]
        widths += [12, stringWidth(txt, st.fontName, st.fontSize) + 16]
    leg = Table([cells], colWidths=widths, hAlign='LEFT', spaceBefore=6) if cells else Spacer(0, 0)
    if cells:
        leg.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
    top = Table([[[big, label], '', [Spacer(0, 9), SplitBar(parts), leg]]],
                colWidths=[T.COL3, T.GUTTER, T.CW - T.COL3 - T.GUTTER], hAlign='LEFT', spaceAfter=6)
    top.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LINEABOVE', (0, 0), (-1, 0), 0.75, T.RULE),
    ]))
    return top, total


def _body_domains(data, locs, root_domain=None):
    allowed = S.allowed(data)
    nopref = bool(data.get('_no_preference') or not allowed)
    hosting = _hosting(data) or hosting_rows_from_locations(locs)
    vm = G.entries(hosting, allowed, compare=not nopref)
    for msg in vm['qa']:
        qa.add('residency_country', 'warn', msg, once=True)
    pref = set(vm['pref'])
    kind_of = lambda a2: 'hosting' if nopref else ('match' if a2 in pref else 'mismatch')  # noqa: E731
    hosts, undetected, _ = by_country(locs, root_domain)
    overflow = _needs_cap(hosts, undetected)
    cap_rid = REG_ID if overflow else None

    out = [C.key_value_list([('Preferred countries', S.join(allowed))])]
    headline, total_domains = _headline(hosts, undetected, kind_of, nopref)
    out.append(headline)
    out += G.map_flowables(vm, G.choose(vm))

    order = sorted(hosts, key=lambda a2: (['mismatch', 'match', 'hosting'].index(kind_of(a2)),
                                          -len(hosts[a2]), G.name(a2)))
    for kind in ('mismatch', 'match', 'hosting'):
        codes = [a2 for a2 in order if kind_of(a2) == kind]
        unused = list(vm['pref_only']) if kind == 'match' else []
        if not codes and not unused:
            continue
        out.append(_group_head(kind, len(codes)))
        for a2 in codes:
            out.append(_country_row(kind, a2, G.name(a2), len(hosts[a2]), hosts[a2],
                                    strong=kind != 'match', cap_rid=cap_rid))
        for a2 in unused:
            out.append(_country_row('pref', a2, f'{G.name(a2)} · preferred, no domain hosted', None, []))

    if undetected:
        n_un = len({h for hs in undetected.values() for h in hs})
        out.append(_group_head('offmap', None,
                               f'Location not detected · {C.fmt_number(n_un)} domain{"s" if n_un != 1 else ""}'))
        for key, hs in undetected.items():
            out.append(_country_row('offmap', '', _undetected_label(key), len(hs), hs,
                                    strong=False, cap_rid=cap_rid))

    if overflow:
        out.append(C.register_pointer(REG_ID, {'value': total_domains, 'unit': 'domains'},
                                      title='Hosting locations by domain'))

    out += S.quote(data)
    notes = [data['note']] if data.get('note') and 'ip location' not in data['note'].lower() else []
    notes.append('Location method: IP geolocation of observed domains.')
    notes.append(G.CAVEAT)
    out.append(C.note(' '.join(C.sentence(n) for n in dict.fromkeys(map(C.plain, notes)))))
    return out


# --- legacy aggregate table view (when only observed_hosting[] is provided) -----------------------
def _hosts_cell(h):
    """Host count, or the null with its own reason (sibling `<field>_reason_code` / `_reason`)."""
    n = G.host_count(h)
    if n is not None:
        return n
    f = 'host_count' if 'host_count' in h else 'hosts'
    return {'value': None, 'reason': h.get(f'{f}_reason'),
            'reason_code': h.get(f'{f}_reason_code') or (None if h.get(f'{f}_reason') else 'not_tracked')}


def _offmap_label(e):
    h, code = e['row'], e.get('code')
    if e['why'] == 'unresolved':
        return f"{e['raw']}: country name not recognised"
    if e['why'] == 'placeholder' and not (h.get('reason') or h.get('state_reason')):
        return (f'Location not identified (the source printed the placeholder code “{code}”)' if code
                else 'Location not identified (blank country code)')
    return C.sentence(C.reason_text(h))[:-1]


def _rows(vm, choice, nopref, notes, with_ev):
    """Table under the map: hosting countries (ISO code as on the map badge), preferred countries with no
    hosts, then the hosts not placed on the map. Key cell = the map shape."""
    ev = lambda h: [h.get('evidence_kind') or {'value': None, 'reason_code': 'not_printed_in_source'}] \
        if with_ev else []                                                                  # noqa: E731
    rows = []
    for e in vm['hosted']:
        rows.append([G.Marker(e['kind']), f"{G.name(e['a2'])} ({e['a2']})", _hosts_cell(e['row']),
                     S.match_chip('no_preference' if nopref else e['kind'])] + ev(e['row']))
    for a2 in vm['pref_only']:
        rows.append([G.Marker('pref'), f'{G.name(a2)} ({a2})', 'None observed',
                     C.P('Preferred country; no hosts observed', 'cell')] + (['–'] if with_ev else []))
    for e in vm['offmap']:
        h = e['row']
        row_match = h.get('match_state')     # payload decides whether an unknown location is a mismatch
        if nopref:
            row_match = 'no_preference'
        elif row_match not in S.MATCH:
            row_match = 'unknown'
        elif row_match == 'mismatch':
            notes.append('A host of unknown location is counted as outside the preferred countries, as '
                         'recorded in the assessment data.')
        rows.append([G.Marker('offmap'), C.P(_offmap_label(e) + ' (not on the map)', 'cell_muted'), _hosts_cell(h),
                     S.match_chip(row_match)] + ev(h))
    return rows


def _body_legacy(data):
    allowed = S.allowed(data)
    hosting = _hosting(data)
    nopref = data.get('_no_preference')
    match = S.matched(data)
    pairs = [('Preferred countries', S.join(allowed)), ('Against the preference', S.match_chip(match))]
    if not hosting:
        pairs.insert(0, ('Hosts observed', {'value': None, 'reason_code': 'not_printed_in_source'}))
    out = [C.key_value_list(pairs)]
    if data.get('summary') and _text(data) != data['summary']:      # the opener carries the summary
        out.append(C.P(_text(data), spaceBefore=6))
    # the fixed caveat replaces a payload note that says the same (IP location is not proof of storage)
    notes = [data['note']] if data.get('note') and 'ip location' not in data['note'].lower() else []
    if hosting:
        vm = G.entries(hosting, allowed, compare=not nopref)
        for msg in vm['qa']:
            qa.add('residency_country', 'warn', msg, once=True)
        choice = G.choose(vm)
        out += G.map_flowables(vm, choice)
        with_ev = any(not C.is_missing(h.get('evidence_kind')) for h in hosting)
        cols = ['', 'Country', 'Hosts', 'Against the preference'] + \
            (['Evidence'] if with_ev else [])
        rows = _rows(vm, choice, nopref, notes, with_ev)
        widths = None
        if not with_ev:      # match column as wide as its longest chip label: never wraps mid-phrase
            labels = [r[3].text if hasattr(r[3], 'text') else C.plain(r[3]) for r in rows]
            mw = max(stringWidth(t, T.LIGHT, 8.6) for t in labels) + 16 + 2 * T.CELL_PAD_H
            hw = stringWidth('None observed', T.LIGHT, 8.6) + 2 * T.CELL_PAD_H + 2
            widths = [24, T.CW - 24 - hw - mw, hw, mw]
        out.append(C.compact_table(cols, rows, widths, numeric_cols=(2,)))
        if not with_ev:
            ev = next((h['evidence_kind'] for h in hosting if isinstance(h.get('evidence_kind'), dict)), None)
            notes.append(f'Location method: {C.missing_text(ev or {})}.')
        notes.append(G.CAVEAT)
    out += S.quote(data)
    if notes:
        out.append(C.note(' '.join(C.sentence(n) for n in dict.fromkeys(map(C.plain, notes)))))
    return out


def _body(data, ctx=None):
    locs = data.get('_locations') or locations_of(data, ctx.report if ctx else None)
    if locs:
        root = data.get('_root_domain') or (ctx.identity.get('domain') if ctx else None)
        return _body_domains(data, locs, root_domain=root)
    return _body_legacy(data)


def build(data, ctx):
    ms = metrics(data)
    return ([C.kpi_strip(ms)] if ms else []) + _body(data, ctx)


def build_context(data, ctx):
    return [] if data.get('_card_only') else _body(data, ctx)
