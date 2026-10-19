"""08 Data residency (demerit rule F): where the organisation's public systems are hosted (IP
location), compared with the countries preferred by the report owner/requestor.

Not privacy criterion H 'Data residency' (section 03), which scores what the policy says about
location and transfer. Copy follows match_state; a host of unknown location counts as a mismatch
only when its row says so. With no preference set the hosting still prints, marked
'Not compared: no preference set'. KPI strip: hosts observed and countries identified, summed from
the hosting rows (only when every row gives a host count).
"""
from reportlab.pdfbase.pdfmetrics import stringWidth

from .. import components as C
from .. import geo_map as G
from .. import qa
from .. import theme as T
from . import _shared as S

TEXT = {
    'no_preference': 'Not compared: no preference set. The hosting locations found are shown without validation.',
    'match': 'All located hosts are in the preferred countries ({allowed}), compared with {owner}.',
    'mismatch': 'Public systems were observed outside the preferred countries ({allowed}), compared with '
                '{owner}, so customer data may be held outside those countries.',
    'unknown': 'Hosting locations could not be compared with {owner} ({allowed}).',
}


def _hosting(data):
    return [h for h in data.get('observed_hosting') or [] if isinstance(h, dict)]


def adjust(data, report):
    data = S.with_snapshot_pref(data, report, 'residency_allowed_countries')
    out = S.adjust_compared(data, bool(data.get('observed_hosting')),
                            data.get('allowed_set') or data.get('observed_hosting'), 'Data residency')
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
    """Payload metrics, else hosts observed + countries identified from the hosting rows (only when every
    row gives an int host count; countries = distinct resolved ISO codes, placeholders and unresolved
    names not counted)."""
    ms = [m for m in data.get('metrics') or [] if isinstance(m, dict)]
    rows = _hosting(data)
    if ms or not rows or not all(isinstance(G.host_count(h), int) for h in rows):
        return ms
    st = data.get('state')
    countries = {e['a2'] for e in G.entries(rows, [], compare=False)['hosted']}
    return [{'id': 'hosts_observed', 'label': 'Hosts observed', 'value': sum(G.host_count(h) for h in rows),
             'unit': 'hosts', 'state': st},
            {'id': 'countries_identified', 'label': 'Countries identified', 'value': len(countries),
             'unit': 'countries', 'state': st}]


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


def _body(data):
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


def build(data, ctx):
    ms = metrics(data)
    return ([C.kpi_strip(ms)] if ms else []) + _body(data)


def build_context(data, ctx):
    return [] if data.get('_card_only') else _body(data)
