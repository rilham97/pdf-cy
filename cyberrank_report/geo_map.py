"""Section 08 data residency map: offline, deterministic, rule-based zoom.

Asset: assets/geo/world_110m_dots.json, Natural Earth 1:110m admin_0 (public domain, see
NaturalEarth-LICENSE.md), projected once to Equal Earth by tools/geo_prep.py. No network, no randomness:
the same payload gives the same page bytes.

Mode (choose()), from the relevant countries = hosting countries + preferred countries:
  C   <= C_MAX countries (one country, or none when IP location lookups failed): table alone, no map.
  A2  the padded bounding box of those countries spans <= A2_MAX_SPAN of the world width: regional zoom
      with a denser dot grid + a mini world locator. The antimeridian is handled by re-centring the
      projection (central meridian lon0) when that gives the narrower box (NZ + US -> Pacific view).
  A3  otherwise: world map with shape badges carrying the ISO country code + up to MAX_INSETS magnifier insets for crowded
      clusters (>= 2 countries within CLUSTER_U) or small countries (<= SMALL_DOTS dots).
Shapes carry the state (greyscale-safe): circle = hosting in a preferred country, square = hosting
outside, open ring = preferred country, navy circle = hosting not compared (no preference), dashed ring
= not placed on the map (unknown location, placeholder 'XX', unresolvable name -- never guessed).
"""
import json
import math
from functools import lru_cache
from pathlib import Path

from reportlab.lib.colors import Color, HexColor, white
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable

from . import theme as T

ASSET_DIR = Path(__file__).resolve().parent / 'assets' / 'geo'
WORLD = json.loads((ASSET_DIR / 'world_110m_dots.json').read_text(encoding='utf-8'))
WB = tuple(WORLD['bbox'])
WORLD_W, WORLD_H = WB[2] - WB[0], WB[3] - WB[1]
ASPECT = WORLD_W / WORLD_H
BY_A2 = {c['a2']: c for c in WORLD['countries'] if c['a2']}

C_MAX = 1              # <= this many relevant countries (0 = location lookups failed): table only
A2_MAX_SPAN = .6       # regional zoom when the padded view is <= 60% of the world width
PAD = .15              # padding around the countries' box (share of its size, at least PAD_MIN units)
PAD_MIN = .06
MAX_ZOOM = 6           # minimum view span = world / MAX_ZOOM (one tiny country never fills the page)
A2_COLS, WORLD_COLS, INSET_PITCH = 150, 112, 3.0
CLUSTER_U = .16        # A3: countries closer than this (projected units, ~15 pt at 500 pt) share an inset
SMALL_DOTS = 2         # a country with <= this many dots on the world grid is 'small'
MAX_INSETS = 2
INSET_ASPECT = 1.9
CAVEAT = 'IP geolocation shows where public systems are hosted, not where all customer data is stored.'

# status markers from theme.status_color; the preferred-country ring is structure (sapphire)
MATCH, OUTSIDE, HOSTING, PREF = (T.status_color('match'), T.status_color('mismatch'),
                                 T.status_color('not_compared'), T.SAPPHIRE)
OFF, LAND = T.UNSCANNED, HexColor('#CBD3DC')
COL = {'match': MATCH, 'mismatch': OUTSIDE, 'hosting': HOSTING, 'pref': PREF}
LEGEND = {'match': 'Hosting in a preferred country', 'mismatch': 'Hosting outside the preferred countries',
          'pref': 'Preferred country', 'hosting': 'Hosting country (not compared)', 'offmap': 'Not placed on the map'}

# --- country resolution ------------------------------------------------------------------------
ALIASES = {'usa': 'US', 'united states': 'US', 'uk': 'GB', 'great britain': 'GB', 'england': 'GB',
           'south korea': 'KR', 'korea': 'KR', 'russia': 'RU', 'czechia': 'CZ', 'turkiye': 'TR', 'türkiye': 'TR',
           'hong kong': 'HK', 'macau': 'MO', 'uae': 'AE', 'vietnam': 'VN', 'holland': 'NL'}
for _c in WORLD['countries']:
    for _n in _c['names']:
        ALIASES.setdefault(_n, _c['a2'])
    if _c['a3']:
        ALIASES.setdefault(_c['a3'].lower(), _c['a2'])
PLACEHOLDERS = {'xx', 'zz', '--', '??', ''}


def resolve(value):
    """ISO alpha-2 or a Natural Earth name -> ('country', a2) | ('placeholder', None) | ('unknown', None).
    Case-insensitive exact match only; never fuzzy, never guessed."""
    v = str(value or '').strip()
    if v.lower() in PLACEHOLDERS:
        return 'placeholder', None
    if len(v) == 2 and v.upper() in BY_A2:
        return 'country', v.upper()
    a2 = ALIASES.get(v.lower())
    return ('country', a2) if a2 in BY_A2 else ('unknown', None)


def name(a2):
    return BY_A2[a2]['name']


def host_count(h):
    """Hosts of one observed_hosting row: `host_count` wins over its alias `hosts`; None = not given."""
    return h.get('host_count', h.get('hosts'))


def entries(rows, preferred, compare=True):
    """Hosting rows + preferred countries -> view model.
    rows: payload observed_hosting[] ({country_code?, country, hosts | host_count, match_state?, reason_code?}).
    Returns {'hosted': [entry], 'pref': [a2], 'pref_only': [a2], 'offmap': [entry], 'qa': [str], 'compare'}.
    entry: {'row', 'a2', 'hosts', 'kind' (match | mismatch | hosting | offmap), 'why' (offmap reason)}."""
    pref, qa = [], []
    for p in preferred or []:
        kind, a2 = resolve(p)
        if a2 and a2 not in pref:
            pref.append(a2)
        elif not a2:
            qa.append(f'preferred country {p!r} not resolved; not drawn on the map')
    compare = compare and bool(pref)
    hosted, offmap = [], []
    for h in rows:
        hosts = host_count(h)
        raw = h.get('country_code') or h.get('country')
        if h.get('reason_code') == 'country_code_placeholder':
            kind, a2 = 'placeholder', None
        elif h.get('reason_code') == 'location_unknown' or raw is None:
            kind, a2 = 'unknown', None
        else:
            kind, a2 = resolve(raw)
            if kind == 'unknown':
                kind = 'unresolved'
                qa.append(f'hosting country {raw!r} not resolved; counted off the map, not guessed')
        if not a2:      # code: the placeholder as sent; reason_code alone means the source's "XX"
            code = (str(raw).strip().upper() if raw is not None else 'XX') if kind == 'placeholder' else None
            offmap.append({'row': h, 'a2': None, 'hosts': hosts, 'kind': 'offmap', 'why': kind, 'raw': raw,
                           'code': code})
            continue
        derived = 'match' if a2 in pref else 'mismatch'
        given = h.get('match_state')
        if compare and given in ('match', 'mismatch') and given != derived:
            qa.append(f'{a2}: payload match_state {given!r} differs from the preference ({derived!r}); payload kept')
        hosted.append({'row': h, 'a2': a2, 'hosts': hosts, 'why': None,
                       'kind': (given if given in ('match', 'mismatch') else derived) if compare else 'hosting'})
    seen = {e['a2'] for e in hosted}
    return {'hosted': hosted, 'pref': pref if compare else [], 'compare': compare, 'offmap': offmap, 'qa': qa,
            'pref_only': [p for p in pref if p not in seen] if compare else []}


def relevant(vm):
    """Numbered order: hosting countries (payload order, first occurrence), then preferred-only."""
    out = []
    for e in vm['hosted']:
        if e['a2'] not in out:
            out.append(e['a2'])
    return out + [p for p in vm['pref_only'] if p not in out]


def kind_of(vm, a2):
    return next((e['kind'] for e in vm['hosted'] if e['a2'] == a2), 'pref')


# --- projection: Equal Earth, re-centred on lon0 when the antimeridian splits the countries ------
A1, A2_, A3, A4 = 1.340264, -0.081106, 0.000893, 0.003796
SQ3 = math.sqrt(3)


def _proj(lon, lat):
    th = math.asin(SQ3 / 2 * math.sin(math.radians(lat)))
    t2, t6 = th * th, th ** 6
    x = 2 * SQ3 * math.radians(lon) * math.cos(th) / (3 * (A1 + 3 * A2_ * t2 + t6 * (7 * A3 + 9 * A4 * t2)))
    return x, th * (A1 + A2_ * t2 + t6 * (A3 + A4 * t2))


def _inv(x, y):
    th = y / A1
    for _ in range(8):                                    # Newton on y(theta)
        t2, t6 = th * th, th ** 6
        th -= (th * (A1 + A2_ * t2 + t6 * (A3 + A4 * t2)) - y) / (A1 + 3 * A2_ * t2 + t6 * (7 * A3 + 9 * A4 * t2))
    t2, t6 = th * th, th ** 6
    lam = x * 3 * (A1 + 3 * A2_ * t2 + t6 * (7 * A3 + 9 * A4 * t2)) / (2 * SQ3 * math.cos(th))
    return math.degrees(lam), math.degrees(math.asin(2 * math.sin(th) / SQ3))


def _wrap(lon):
    return (lon + 180) % 360 - 180


@lru_cache(maxsize=8)
def frame(lon0=0):
    """{a2 or index: {'c': (x, y), 'rings': [...]}} projected with central meridian lon0. Rings are
    unwrapped continuously, so a ring cut by the new seam runs past +-180 on one side only (never inside
    a view: the seam is placed in the widest empty gap)."""
    out = {}
    for k, co in enumerate(WORLD['countries']):
        key = co['a2'] or k
        if not lon0:
            out[key] = {'c': tuple(co['c']), 'rings': co['rings']}
            continue
        lon, lat = _inv(*co['c'])
        rings = []
        for r in co['rings']:
            ll, prev = [], None
            for p in r:
                lo, la = _inv(*p)
                lo = _wrap(lo - lon0)
                if prev is not None:
                    lo += 360 * round((prev - lo) / 360)
                ll.append(_proj(lo, la))
                prev = lo
            rings.append(ll)
        out[key] = {'c': _proj(_wrap(lon - lon0), lat), 'rings': rings}
    return out


@lru_cache(maxsize=8)
def _ring_index(lon0):
    idx = []
    for key, co in frame(lon0).items():
        for r in co['rings']:
            xs, ys = [p[0] for p in r], [p[1] for p in r]
            idx.append((key, r, (min(xs), min(ys), max(xs), max(ys))))
    return idx


def _area(r):
    return abs(0.5 * sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r))))


def focus_points(a2, lon0=0):
    """Label point + rings >= 20% of the largest (drops Alaska, French Guiana; keeps Java)."""
    co = frame(lon0)[a2]
    pts = [co['c']]
    if co['rings']:
        big = max(_area(r) for r in co['rings'])
        pts += [p for r in co['rings'] if _area(r) >= .2 * big for p in r]
    return pts


def fit(codes, lon0=0, aspect=ASPECT, min_w=WORLD_W / MAX_ZOOM):
    """Viewport (x0, y0, x1, y1) around the countries: padded, at least min_w wide (max zoom), at the
    given aspect, clamped inside the world box."""
    pts = [p for a in codes for p in focus_points(a, lon0)]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    w, h = x1 - x0, y1 - y0
    w, h = max(w + 2 * max(PAD * w, PAD_MIN), min_w), h + 2 * max(PAD * h, PAD_MIN)
    w, h = max(w, h * aspect), max(h, w / aspect)
    w, h = min(w, WORLD_W), min(h, WORLD_H)
    cx = min(max((x0 + x1) / 2, WB[0] + w / 2), WB[2] - w / 2)
    cy = min(max((y0 + y1) / 2, WB[1] + h / 2), WB[3] - h / 2)
    return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2


def seam_lon0(codes):
    """Central meridian that puts the seam in the middle of the widest empty longitude gap."""
    lons = sorted({round(_inv(*p)[0], 1) for a in codes for p in focus_points(a)})
    gaps = [((lons[(i + 1) % len(lons)] - lons[i]) % 360 or 360, lons[i]) for i in range(len(lons))]
    g, start = max(gaps, key=lambda t: (t[0], -t[1]))
    return round(_wrap(start + g / 2 + 180))


def choose(vm):
    """-> {'mode': 'C' | 'A2' | 'A3', 'codes', 'lon0', 'vp', 'insets': [[a2, ...]]}. Rule-based, deterministic."""
    codes = relevant(vm)
    if len(codes) <= C_MAX:
        return {'mode': 'C', 'codes': codes, 'lon0': 0, 'vp': None, 'insets': []}
    best = (fit(codes), 0)
    alt = seam_lon0(codes)
    if alt:
        vp = fit(codes, alt)
        if vp[2] - vp[0] < best[0][2] - best[0][0] - 1e-6:
            best = (vp, alt)
    vp, lon0 = best
    if vp[2] - vp[0] <= A2_MAX_SPAN * WORLD_W:
        return {'mode': 'A2', 'codes': codes, 'lon0': lon0, 'vp': vp, 'insets': []}
    return {'mode': 'A3', 'codes': codes, 'lon0': 0, 'vp': WB, 'insets': insets(vm, codes)}


def small(a2):
    return len(BY_A2[a2]['dots']) <= SMALL_DOTS


def insets(vm, codes):
    """Single-link clusters (< CLUSTER_U apart) with >= 2 countries, or a small country alone; the
    MAX_INSETS largest (countries, then hosts) in numbered order."""
    groups = []
    for a in codes:
        near = [g for g in groups if any(math.dist(BY_A2[a]['c'], BY_A2[b]['c']) < CLUSTER_U for b in g)]
        groups = [g for g in groups if g not in near] + [[a] + [b for g in near for b in g]]
    hosts = {e['a2']: e['hosts'] or 0 for e in vm['hosted']}
    groups = [sorted(g, key=codes.index) for g in groups if len(g) > 1 or small(g[0])]
    groups.sort(key=lambda g: (-len(g), -sum(hosts.get(a, 0) for a in g), codes.index(g[0])))
    return sorted(groups[:MAX_INSETS], key=lambda g: codes.index(g[0]))


# --- drawing -----------------------------------------------------------------------------------
def _pip(x, y, r):
    ins, j = False, len(r) - 1
    for i in range(len(r)):
        (xi, yi), (xj, yj) = r[i], r[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            ins = not ins
        j = i
    return ins


class View:
    """Viewport (projected units, central meridian lon0) -> page box with its own dot grid; cells are
    computed by point-in-polygon at this zoom, so a regional view is denser than the world grid."""

    def __init__(self, vp, lon0, x, top, w, cols):
        self.vp, self.lon0, self.x, self.top, self.w = vp, lon0, x, top, w
        self.s = w / (vp[2] - vp[0])
        self.h = (vp[3] - vp[1]) * self.s
        pu = (vp[2] - vp[0]) / cols
        self.pitch = pu * self.s
        rows = int((vp[3] - vp[1]) / pu)
        rings = [t for t in _ring_index(lon0) if t[2][2] >= vp[0] and t[2][0] <= vp[2]
                 and t[2][3] >= vp[1] and t[2][1] <= vp[3]]
        self.cells = {}
        for j in range(rows):
            y = vp[3] - (j + .5) * pu
            band = [t for t in rings if t[2][1] <= y <= t[2][3]]
            for i in range(cols):
                x_ = vp[0] + (i + .5) * pu
                for key, r, b in band:
                    if b[0] <= x_ <= b[2] and _pip(x_, y, r):
                        self.cells[(i, j)] = key
                        break
        self.by = {}
        for k, key in sorted(self.cells.items()):
            self.by.setdefault(key, []).append(k)
        fr = frame(lon0)
        for a2 in sorted(BY_A2):     # tiny / sliver country without a cell: one dot at its label point
            cx, cy = fr[a2]['c']
            if a2 not in self.by and vp[0] <= cx <= vp[2] and vp[1] <= cy <= vp[3]:
                k = (min(cols - 1, int((cx - vp[0]) / pu)), min(rows - 1, int((vp[3] - cy) / pu)))
                old = self.cells.get(k)
                if old in self.by and k in self.by[old]:
                    self.by[old].remove(k)
                self.cells[k] = a2
                self.by[a2] = [k]

    def pt(self, px, py):
        return self.x + (px - self.vp[0]) * self.s, self.top - (self.vp[3] - py) * self.s

    def cell(self, i, j):
        return self.x + (i + .5) * self.pitch, self.top - (j + .5) * self.pitch

    def pos(self, a2):
        lx, ly = self.pt(*frame(self.lon0)[a2]['c'])
        cs = self.by.get(a2)
        if not cs:
            return lx, ly
        return self.cell(*min(cs, key=lambda k: ((self.cell(*k)[0] - lx) ** 2 + (self.cell(*k)[1] - ly) ** 2, k)))

    def is_small(self, a2):
        return len(self.by.get(a2, ())) <= SMALL_DOTS


BADGE_PT = 4.6         # ISO code inside a map badge
SPARSE_MIN = 6         # an outside country with more cells than this gets checkerboard squares
SQUARE_DASH = .01      # square-cap dash length: poppler drops zero-length dashes with square caps


def dot_runs(c, v, keep, width, color, square=False, cell=None):
    """Every cell passing keep(key) (and cell(i, j, key), if given) as dashed row runs: one moveTo/lineTo
    per run of adjacent dots, dash [e, pitch - e]. Round cap + zero dash = dots; square cap + 0.01 pt dash = squares."""
    rows = {}
    for (i, j), key in v.cells.items():
        if keep(key) and (cell is None or cell(i, j, key)):
            rows.setdefault(j, []).append(i)
    if not rows:
        return
    e = SQUARE_DASH if square else 0
    c.setLineCap(2 if square else 1)
    c.setLineWidth(width)
    c.setStrokeColor(color)
    c.setDash([e, v.pitch - e], 0)
    p = c.beginPath()
    for j in sorted(rows):
        xs = sorted(rows[j])
        s = xs[0]
        for a, b in zip(xs, xs[1:] + [None]):
            if b != a + 1:
                x0, y = v.cell(s, j)
                p.moveTo(x0, y)
                p.lineTo(v.cell(a, j)[0] + v.pitch * .5, y)
                s = b
    c.drawPath(p, stroke=1, fill=0)
    c.setDash()


def draw_dots(c, v, vm, halos=False, scale=.56):
    kinds = {e['a2']: e['kind'] for e in vm['hosted']}
    pref = set(vm['pref'])
    d = v.pitch * scale
    c.saveState()
    dot_runs(c, v, lambda a: a not in kinds and a not in pref, d, LAND)
    only_pref = lambda a: a in pref and a not in kinds          # noqa: E731
    dot_runs(c, v, only_pref, d * 1.2, PREF)                    # ring = sapphire dot with a white core
    dot_runs(c, v, only_pref, d * .62, white)
    dot_runs(c, v, lambda a: kinds.get(a) == 'match', d * 1.15, MATCH)
    dot_runs(c, v, lambda a: kinds.get(a) == 'hosting', d * 1.15, HOSTING)
    # outside = red squares, smaller and on a checkerboard over grey land dots so a large country
    # (USA) reads as a red-flecked area, not the loudest block on the page; <= SPARSE_MIN cells stay full
    outside = lambda a: kinds.get(a) == 'mismatch'              # noqa: E731
    n = {}
    for a in v.cells.values():
        n[a] = n.get(a, 0) + 1
    sparse = lambda i, j, a: n[a] <= SPARSE_MIN or (i + j) % 2 == 0  # noqa: E731
    dot_runs(c, v, lambda a: outside(a) and n[a] > SPARSE_MIN, d, LAND)
    dot_runs(c, v, outside, d * .85, OUTSIDE, square=True, cell=sparse)
    if halos:                                                   # small country: ring in its state colour
        for a2 in relevant(vm):
            if a2 in v.by and v.is_small(a2):
                c.setStrokeColor(COL[kinds.get(a2, 'pref')])
                c.setLineWidth(.7)
                c.circle(*v.pos(a2), max(3.6, d * 2), stroke=1, fill=0)
    c.restoreState()
    return d


def marker(c, x, y, kind, s=5.5):
    c.saveState()
    if kind in ('match', 'hosting'):
        c.setFillColor(COL[kind])
        c.circle(x, y, s / 2, stroke=0, fill=1)
    elif kind == 'mismatch':
        c.setFillColor(OUTSIDE)
        c.rect(x - s * .44, y - s * .44, s * .88, s * .88, stroke=0, fill=1)
    elif kind == 'pref':
        c.setStrokeColor(PREF)
        c.setLineWidth(1)
        c.circle(x, y, s / 2 - .5, stroke=1, fill=0)
    else:
        c.setStrokeColor(OFF)
        c.setLineWidth(.8)
        c.setDash(1.2, 1.2)
        c.circle(x, y, s / 2 - .4, stroke=1, fill=0)
    c.restoreState()


def badge(c, x, y, code, kind, r=4.6):
    """Map badge: the state shape with the ISO alpha-2 code inside (grown to fit wide codes like 'MW')."""
    r = max(r, stringWidth(code, T.SEMIBOLD, BADGE_PT) / 2 + 1.3)
    c.saveState()
    c.setStrokeColor(white)
    c.setLineWidth(1.1)
    if kind == 'pref':
        c.setFillColor(white)
        c.circle(x, y, r, stroke=1, fill=1)
        c.setStrokeColor(PREF)
        c.setLineWidth(.9)
        c.circle(x, y, r - .5, stroke=1, fill=0)
        ink = PREF
    else:
        c.setFillColor(COL[kind])
        if kind == 'mismatch':
            c.rect(x - r * .9, y - r * .9, r * 1.8, r * 1.8, stroke=1, fill=1)
        else:
            c.circle(x, y, r, stroke=1, fill=1)
        ink = white
    _txt(c, x, y - 1.7, code, BADGE_PT, T.SEMIBOLD, ink, 'c')
    c.restoreState()


def _txt(c, x, y, s, size, font=T.LIGHT, color=T.MUTED, anchor='l'):
    c.setFont(font, size)
    c.setFillColor(color)
    {'l': c.drawString, 'r': c.drawRightString, 'c': c.drawCentredString}[anchor](x, y, s)
    return stringWidth(s, font, size)


def place_labels(c, v, items, obstacles):
    """Deterministic: 8 directions at growing radii; first pass avoids every dot, second only the
    highlighted ones. A label that finds no room is skipped (the table still lists the country)."""
    hard = [o for o in obstacles if o[0] in ('hi', 'box')]
    boxes = []

    def free(b, obs):
        if not (v.x <= b[0] and b[2] <= v.x + v.w and v.top - v.h <= b[1] and b[3] <= v.top):
            return False
        if any(b[0] < o[2] and o[0] < b[2] and b[1] < o[3] and o[1] < b[3] for o in boxes):
            return False
        for o in obs:
            if o[0] == 'box':
                if b[0] < o[3] and o[1] < b[2] and b[1] < o[4] and o[2] < b[3]:
                    return False
            elif b[0] - o[3] < o[1] < b[2] + o[3] and b[1] - o[3] < o[2] < b[3] + o[3]:
                return False
        return True

    for x, y, t, col in items:
        w, h = stringWidth(t, T.MEDIUM, 6.5) + 4, 9
        done = False
        for obs in (obstacles, hard):
            for r in (5, 11, 18, 28, 40):
                for dx, dy in ((r, -h / 2), (-r - w, -h / 2), (-w / 2, r), (-w / 2, -r - h), (r * .7, r * .7),
                               (-r * .7 - w, r * .7), (r * .7, -r * .7 - h), (-r * .7 - w, -r * .7 - h)):
                    b = (x + dx, y + dy, x + dx + w, y + dy + h)
                    if free(b, obs):
                        boxes.append(b)
                        if r > 5:                       # leader for a label pushed away from its dot
                            c.setStrokeColor(T.MUTED)
                            c.setLineWidth(.4)
                            c.line(x, y, min(max(x, b[0]), b[2]), min(max(y, b[1]), b[3]))
                        c.setFillColor(Color(1, 1, 1, alpha=.9))
                        c.roundRect(b[0], b[1], w, h, 1.5, 0, 1)
                        _txt(c, b[0] + 2, b[1] + 2.4, t, 6.5, T.MEDIUM, col)
                        done = True
                        break
                if done:
                    break
            if done:
                break


def draw_locator(c, vp, lon0, x, y, w):
    """Mini world in the same projection (lon0) with the viewport framed."""
    lv = View(WB, lon0, x, y + w / ASPECT, w, 56)
    c.saveState()
    c.setFillColor(white)
    c.setStrokeColor(T.RULE)
    c.setLineWidth(.5)
    c.rect(x - 2, y - 2, w + 4, lv.h + 4, stroke=1, fill=1)
    dot_runs(c, lv, lambda a: True, lv.pitch * .7, HexColor('#D5DCE4'))
    c.setStrokeColor(PREF)
    c.setLineWidth(.8)
    x0, y0 = lv.pt(vp[0], vp[1])
    x1, y1 = lv.pt(vp[2], vp[3])
    c.rect(x0, y0, x1 - x0, y1 - y0, stroke=1, fill=0)
    c.restoreState()


def legend_items(vm):
    ks = ['match', 'mismatch', 'pref'] if vm['compare'] else ['hosting']
    return ks                      # off-map hosts: own counter line under the legend


def offmap_line(vm):
    """Off-map counter per reason (and placeholder code). A null host count is missing, not zero:
    a group with one prints 'hosts … (count not available)'."""
    n = {}
    for e in vm['offmap']:
        k = (e['why'], e.get('code'))
        n[k] = None if k in n and n[k] is None or e['hosts'] is None else n.get(k, 0) + e['hosts']
    parts = []
    for (why, code), v in n.items():
        what = {'unknown': 'with unknown location',
                'placeholder': f'with the placeholder code “{code}”' if code else 'with a blank country code',
                'unresolved': 'with an unresolved country name'}[why]
        parts.append(f'hosts {what} (count not available)' if v is None else f'{v} host{"s" * (v != 1)} {what}')
    return ('Not placed on the map: ' + ', '.join(parts) + '.') if parts else None


class ResidencyMap(Flowable):
    """A2 or A3 map + legend + off-map counter, full content width. Does not split; A3 insets are a
    second ResidencyMap(part='insets') so the page may break between world map and insets."""

    LEG_H = 12

    def __init__(self, vm, choice, part='map'):
        super().__init__()
        self.vm, self.ch, self.part = vm, choice, part
        self.spaceBefore, self.spaceAfter = 4, 6

    def wrap(self, aw, ah):
        self.width = aw
        if self.part == 'insets':
            n = len(self.ch['insets'])
            self._iw = min(aw * .62, (aw - 10 * (n - 1)) / n)
            self.height = self._iw / INSET_ASPECT + 10
            return aw, self.height
        self._mh = aw / ASPECT                 # A2 viewports keep the world aspect too
        lines = 1 + bool(offmap_line(self.vm))
        self.height = 11 + self._mh + 6 + lines * self.LEG_H
        return aw, self.height

    def draw(self):
        c, vm, ch = self.canv, self.vm, self.ch
        if self.part == 'insets':
            self._draw_insets(c)
            return
        top = self.height - 11
        if ch['mode'] == 'A2':
            cap = (f'Map zoomed to the countries in this section (about {round((ch["vp"][2] - ch["vp"][0]) / WORLD_W * 360)}° '
                   f'wide{", centred on the Pacific" if abs(ch["lon0"]) > 90 else ""}); the small map shows where.')
        else:
            cap = 'World map; badges show the country code, listed in the table below' + \
                  ('; lettered frames are magnified under the map.' if ch['insets'] else '.')
        _txt(c, 0, top + 3, cap, 6.5)
        v = View(ch['vp'], ch['lon0'], 0, top, self.width, A2_COLS if ch['mode'] == 'A2' else WORLD_COLS)
        if ch['mode'] == 'A2':
            self._draw_a2(c, v)
        else:
            self._draw_a3(c, v)
        y = top - v.h - 6 - 7
        x = 0
        for k in legend_items(vm):
            marker(c, x + 3, y + 2.4, k)
            x += 10 + _txt(c, x + 10, y, LEGEND[k], 7) + 12
        if ch['mode'] == 'A2' and any(a in v.by and v.is_small(a) for a in ch['codes']):
            c.setStrokeColor(MATCH if vm['compare'] else HOSTING)
            c.setLineWidth(.7)
            c.circle(x + 3, y + 2.4, 3.6, 1, 0)
            _txt(c, x + 10, y, 'Ring around a dot = small country', 7)
        line = offmap_line(vm)
        if line:
            marker(c, 3, y - self.LEG_H + 2.4, 'offmap')
            _txt(c, 10, y - self.LEG_H, line, 7)

    def _draw_a2(self, c, v):
        vm, ch = self.vm, self.ch
        d = draw_dots(c, v, vm, halos=True)
        hi = set(ch['codes'])
        obstacles = [('hi' if key in hi else 'lo', *v.cell(i, j), d * .7) for (i, j), key in v.cells.items()]
        lw = 92
        lh = lw / ASPECT
        corners = [(v.x + 3, v.top - v.h + 3), (v.x + v.w - lw - 3, v.top - v.h + 3),
                   (v.x + 3, v.top - lh - 3), (v.x + v.w - lw - 3, v.top - lh - 3)]

        def land(cx0, cy0):
            return sum(1 + 5 * (key in hi) for k, key in v.cells.items()
                       if cx0 - 2 <= v.cell(*k)[0] <= cx0 + lw + 2 and cy0 - 2 <= v.cell(*k)[1] <= cy0 + lh + 2)
        lx, ly = min(corners, key=lambda p: land(*p))
        draw_locator(c, ch['vp'], ch['lon0'], lx, ly, lw)
        obstacles.append(('box', lx - 2, ly - 2, lx + lw + 2, ly + lh + 2))
        hosts = {}      # None = a row without a host count: the label prints the name alone
        for e in vm['hosted']:
            a = e['a2']
            hosts[a] = None if a in hosts and hosts[a] is None or e['hosts'] is None else hosts.get(a, 0) + e['hosts']
        items = []
        for a2 in ch['codes']:
            if a2 in v.by:
                k = kind_of(vm, a2)
                t = (name(a2) if hosts[a2] is None else f'{name(a2)} · {hosts[a2]}') if a2 in hosts \
                    else f'{name(a2)} · preferred'
                items.append((*v.pos(a2), t, T.HEADING if k in ('hosting', 'pref') and a2 in hosts else
                              COL[k] if k != 'match' else HexColor('#1F6E43')))
        place_labels(c, v, items, obstacles)

    def _draw_a3(self, c, v):
        vm, ch = self.vm, self.ch
        draw_dots(c, v, vm)
        inset_of = {a: g for g in ch['insets'] for a in g}
        for a2 in ch['codes']:
            if a2 not in inset_of:
                badge(c, *v.pos(a2), a2, kind_of(vm, a2))
        for gi, g in enumerate(ch['insets']):
            ivp = fit(g, 0, INSET_ASPECT, WORLD_W / 12)
            x0, y0 = v.pt(ivp[0], ivp[1])
            x1, y1 = v.pt(ivp[2], ivp[3])
            c.setStrokeColor(T.HEADING)
            c.setLineWidth(.6)
            c.setDash(2, 1.5)
            c.rect(x0, y0, x1 - x0, y1 - y0, 1, 0)
            c.setDash()
            c.setFillColor(T.HEADING)
            c.rect(x0, y1, 8, 8, 0, 1)
            _txt(c, x0 + 4, y1 + 2, 'AB'[gi], 6, T.SEMIBOLD, white, 'c')

    def _draw_insets(self, c):
        vm, ch, iw = self.vm, self.ch, self._iw
        for gi, g in enumerate(ch['insets']):
            ivp = fit(g, 0, INSET_ASPECT, WORLD_W / 12)
            ix = gi * (iw + 10)
            iv = View(ivp, 0, ix, self.height - 4, iw, max(20, int(iw / INSET_PITCH)))
            c.saveState()
            c.setStrokeColor(T.RULE)
            c.setLineWidth(.6)
            c.rect(ix, iv.top - iv.h, iw, iv.h, 1, 0)
            draw_dots(c, iv, vm)
            for a2 in g:
                if a2 in iv.by:
                    badge(c, *iv.pos(a2), a2, kind_of(vm, a2))
            c.setFillColor(T.HEADING)
            c.rect(ix, iv.top - 9, 9, 9, 0, 1)
            _txt(c, ix + 4.5, iv.top - 7, 'AB'[gi], 6, T.SEMIBOLD, white, 'c')
            _txt(c, ix + 12, iv.top - 7, ', '.join(name(a) for a in g), 6.5, T.MEDIUM, T.HEADING)
            c.restoreState()


class Marker(Flowable):
    """Table key cell: the map shape (the country code sits in the next column, as on the map badge)."""

    def __init__(self, kind):
        super().__init__()
        self.kind = kind
        self.width = self.height = 10

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        marker(self.canv, 5, self.height / 2 + .5, self.kind, 6)


def map_flowables(vm, choice):
    if choice['mode'] == 'C':
        return []
    out = [ResidencyMap(vm, choice)]
    if choice['insets']:
        out.append(ResidencyMap(vm, choice, 'insets'))
    return out
