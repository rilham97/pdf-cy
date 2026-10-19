"""Cyberrank bottom watermark: the supply-chain graph.

A quiet watermark layer at the bottom of every page. Body text and tables
may run over it. It replaces the old hand-drawn circuit lines.

Two layers share one triangular lattice:

  field  every organisation Cyberrank can observe from outside. These are
         evenly spaced dots, densest just above the footer separator and
         thinning row by row up to a clean last row.
  graph  one supply chain picked out of that field, in the methodology
         diagram's language. "You", the assessed organisation, is the one
         Amber node. It sits in the text-free strip under the header rule's
         Sapphire/Amber junction on interior pages, and under the
         organisation name on the cover. Vendors are large nodes, sub-vendors
         small ones, and some outer leaves are outlined as "unscanned".

Behind text every mark is lighter than the table hairline #D9DFE6, so text
and tables can run over the motif. The footer band is left untouched.

Every rule is a named constant below; nothing is placed by hand. The graph
is generated from a fixed seed and checked against the rules in __main__.

Coordinates: PDF user space, A4, origin bottom-left, y up, so y is the
height above the page bottom. The template's top-left y is H - y.

Usage (ReportLab canvas, called right after the page background and before
the footer band, rules, text and flowables):

    import motif
    motif.draw_interior_motif(c)            # every interior page
    motif.draw_cover_motif(c, hub_x)        # cover; hub_x = x centre of the org name

Each variant is drawn once per document as a Form XObject and referenced on
every page after that. A 375-page report stores the motif once.

`python3 motif.py` runs the self-check and rewrites motif_interior.svg and
motif_cover.svg next to this file.
"""
import math
import random
from functools import cache

# ------------------------------------------------------------------ page
W, H = 595.2755905511812, 841.8897637795275     # A4
L = 14 * 72 / 25.4                              # content measure L..R (14 mm margins)
R = W - L
CW = R - L
SEP_Y = 48.0              # footer separator centre = top of the #EBF5FF band
SEP_TOP = SEP_Y + 1.0     # the separator is 2 pt
HEADER_JUNCTION_X = R - 116   # the header rule turns Sapphire -> Amber here (439.6)
CONTENT_BOTTOM = 68.0     # text frame bottom (template FOOTER_Y - 20)
SEP_CLEAR = 4.5           # lowest mark edge sits at least this far above the separator
KEEPOUT_MARGIN = 8.0      # around the footer contacts and folio
FOOTER_KEEPOUTS = {       # painted boxes (x0, y0, x1, y1), measured, before the margin
    'contacts': (154.9, 17.9, 412.4, 30.0),
    'folio (Page 888 of 888)': (490.4, 17.6, R, 28.8),
}
COVER_TEXT_BOTTOM = 169.0  # lowest glyph of Cover 02's identity block ('via Cyberrank')
COVER_TEXT_CLEAR = 12.0

# --------------------------------------------------------------- lattice
# Triangular lattice, pointy orientation. Columns split the content measure
# into N_COLS equal steps, so on interior pages the outer columns are
# exactly L and R, and column 31 falls on the header junction (0.08 pt off).
# Neighbouring points are PITCH apart; alternate columns are offset by HALF.
N_COLS = 40
DX = CW / N_COLS                 # 12.898 pt between columns
PITCH = 2 * DX / math.sqrt(3)    # 14.893 pt between neighbours (first-neighbour run)
HALF = PITCH / 2                 # 7.446 pt between dot rows
ROW0 = 58.0                      # hub row: 9 pt above the separator, 10 pt below the text frame
INTERIOR_HUB_COL = 31            # interior You: L + 31 * DX = 439.5, under HEADER_JUNCTION_X
# lattice steps per direction (degrees) -> (columns, half-rows). No 0/180:
# a horizontal run could read as a table hairline or an underline.
STEPS = {30: (1, 1), 60: (1, 3), 90: (0, 2), 120: (-1, 3), 150: (-1, 1),
         210: (-1, -1), 240: (-1, -3), 270: (0, -2), 300: (1, -3), 330: (1, -1)}
STEEP_DIAGONALS = {60, 120, 240, 300}   # 25.8 pt second-neighbour runs
DIAG_MAX_Y = 110.0               # steep diagonals stay below this height (few text lines crossed)
PARALLEL_GAP = 24.0              # parallel runs side by side stay this far apart (no hatching)

# ----------------------------------------------------------------- marks
R_LARGE = 2.3      # You and vendors
R_SMALL = 1.3      # sub-vendors, unscanned and field dots
STROKE = 0.6       # every edge and outline: one weight, butt caps
MIN_GAP = 8.0      # clear space around every graph node and edge
UNSCANNED_SHARE = 0.4      # share of childless sub-vendor leaves outlined as unscanned
TABLE_BAND = (CONTENT_BOTTOM, 110.0)   # no rings here: next to 'Low' a ring reads as a status glyph

# ---------------------------------------------------------------- colour
# Solid tints only: no alpha and no ExtGState, so a mark keeps one tone over
# white and over the #EBF5FF band. Tints are mixes of white and INK.
INK = (0xC8, 0xD4, 0xE1)         # the template's CYBERRANK watermark colour
AMBER_TINT = (0xF9, 0xC9, 0x7C)  # Amber #F5A524 at 60%, for You only
HAIRLINE = (0xD9, 0xDF, 0xE6)    # table rule: text-zone marks must be lighter

# ---------------------------------------------------------------- variants
# share: tint strength per mark kind, below / above CONTENT_BOTTOM (the cap
#        that keeps marks behind text lighter than the hairline)
# fade:  (y_full, y_end, end) the strength is 1 up to y_full, then falls
#        linearly to `end` at y_end; a mark is toned by its highest point
# field: share of lattice points kept in each dot row (HALF apart), bottom
#        row first; the rows are evenly spaced, so the last row is clean
# tiers: ((min_len, max_len) pt, children per parent, directions). Tier 1
#        takes absolute angles (no 90: a vertical spoke made the old graph
#        read as a sunburst) and its runs all differ in length. Later tiers
#        take bends relative to the run that reached the parent.
# envelope: half-axes (a, b) of a half-ellipse on the hub; every graph node
#        stays inside, so the graph is highest near You and has no flat top
VARIANTS = {
    'interior': dict(
        seed=28, text_over=True,
        share={'node': (1.0, 0.45), 'edge': (0.75, 0.36), 'field': (0.75, 0.36)},   # lighter behind text/table cells
        fade=(92.0, 124.0, 0.4),
        field=(1.0, 1.0, 0.9, 0.5, 0.42, 0.36, 0.3, 0.26, 0.22),
        tiers=[((36, 96), 4, (30, 60, 120, 150)),
               ((26, 52), 3, (-60, -30, 0, 30, 60)),
               ((15, 30), 2, (-60, -30, 0, 30, 60))],
        envelope=(300.0, 64.0)),
    'cover': dict(
        seed=1, text_over=False,
        share={'node': (1.0, 1.0), 'edge': (0.8, 0.8), 'field': (0.75, 0.75)},
        fade=(96.0, 150.0, 0.38),
        field=(1.0, 1.0, 0.9, 0.55, 0.46, 0.4, 0.35, 0.3, 0.26, 0.23, 0.2),
        tiers=[((36, 110), 4, (30, 60, 120, 150)),
               ((26, 52), 3, (-60, -30, 0, 30, 60)),
               ((15, 30), 2, (-60, -30, 0, 30, 60))],
        envelope=(200.0, 92.0)),
}
INTERIOR_HUB_X = L + INTERIOR_HUB_COL * DX
MAX_SEED_TRIES = 50
GOLDEN = (math.sqrt(5) - 1) / 2  # per-row phase of the field spacing, so rows don't stack


# ------------------------------------------------------------- geometry
def _mix(a, rgb=INK):
    return tuple(round(255 + (c - 255) * a) for c in rgb)


def _hex(rgb):
    return '#%02X%02X%02X' % rgb


def _luminance(rgb):
    """WCAG relative luminance."""
    lin = [(v / 255) / 12.92 if v <= 10 else ((v / 255 + 0.055) / 1.055) ** 2.4 for v in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _seg_dist(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def _cross(a, b, c, d):
    """Proper intersection of segments a-b and c-d (shared ends excluded)."""
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    if {a, b} & {c, d}:
        return False
    return (orient(a, b, c) * orient(a, b, d) < 0) and (orient(c, d, a) * orient(c, d, b) < 0)


def _parallel_clash(P, Q, S, T):
    """True if S-T runs parallel to P-Q, overlaps it lengthwise and is
    closer than PARALLEL_GAP: side-by-side parallels read as hatching."""
    ux, uy = Q[0] - P[0], Q[1] - P[1]
    n = math.hypot(ux, uy)
    ux, uy = ux / n, uy / n
    vx, vy = T[0] - S[0], T[1] - S[1]
    if abs(ux * vy - uy * vx) > 1e-6 * math.hypot(vx, vy):
        return False
    gap = abs((S[0] - P[0]) * uy - (S[1] - P[1]) * ux)
    s0, s1 = sorted(((S[0] - P[0]) * ux + (S[1] - P[1]) * uy, (T[0] - P[0]) * ux + (T[1] - P[1]) * uy))
    return gap < PARALLEL_GAP and s1 > 0 and s0 < n


def build(name, hub_x=INTERIOR_HUB_X):
    """Return the variant's marks as a list of dicts, in paint order.

    kind: 'edge' (x0, y0, x1, y1), 'dot' (x, y, r, filled) or 'ring' (x, y, r);
    role: field / you / vendor / sub / unscanned / edge; color: (r, g, b).

    The graph comes from the variant's seed. If that candidate does not thin
    upward (see _thins_upward), the next seed is tried, so a cover hub moved
    by a longer organisation name still gets a valid graph.
    """
    for attempt in range(MAX_SEED_TRIES):
        marks = _build(name, hub_x, VARIANTS[name]['seed'] + attempt)
        if _thins_upward(marks):
            return marks
    raise ValueError('no graph that thins upward for %s at hub x %.1f' % (name, hub_x))


def _build(name, hub_x, seed):
    v = VARIANTS[name]
    rng = random.Random(seed)
    a_env, b_env = v['envelope']
    pos = lambda k, h: (hub_x + k * DX, ROW0 + h * HALF)
    inside = lambda x, y: (L - 0.01 <= x <= R + 0.01 and ROW0 <= y
                           and ((x - hub_x) / a_env) ** 2 + ((y - ROW0) / b_env) ** 2 <= 1)

    # graph: tiers grown breadth-first from You (lattice index (0, 0))
    you = (0, 0)
    depth, parent, heading, segs = {you: 0}, {}, {you: None}, []
    xy = lambda n: pos(*n)
    frontier = [you]
    for tier, ((lo, hi), n_children, angles) in enumerate(v['tiers']):
        nxt, tier_lengths = [], []
        for p in frontier:
            cone = angles if heading[p] is None else [
                (heading[p] + d) % 360 for d in angles if (heading[p] + d) % 360 in STEPS]
            made = 0
            for a in rng.sample(list(cone), len(cone)):
                if made >= n_children:
                    break
                dk, dh = STEPS[a]
                step = math.hypot(dk * DX, dh * HALF)
                ks = sorted({max(1, round(t / step)) for t in (lo, (lo + hi) / 2, hi)})
                for n in rng.sample(ks, len(ks)):
                    q = (p[0] + dk * n, p[1] + dh * n)
                    P, Q = xy(p), xy(q)
                    if q in depth or not inside(*Q):
                        continue
                    if a in STEEP_DIAGONALS and max(P[1], Q[1]) > DIAG_MAX_Y:
                        continue
                    if tier == 0 and any(abs(n * step - t) < 1 for t in tier_lengths):
                        continue    # first-tier runs all differ in length: no sunburst ring
                    if any(math.dist(Q, xy(m)) < 2 * MIN_GAP for m in depth):
                        continue
                    if any(_seg_dist(xy(m), P, Q) < MIN_GAP for m in depth if m != p):
                        continue
                    if any(_seg_dist(Q, s, t) < MIN_GAP or _cross(P, Q, s, t) for s, t in segs):
                        continue
                    if any(_parallel_clash(P, Q, s, t) for s, t in segs):
                        continue
                    depth[q], parent[q], heading[q] = depth[p] + 1, p, a
                    segs.append((P, Q))
                    nxt.append(q)
                    tier_lengths.append(n * step)
                    made += 1
                    break
        frontier = nxt

    share = v['share']
    y_full, y_end, end = v['fade']
    fade = lambda y: 1.0 if y <= y_full else 1.0 + (end - 1.0) * min(1.0, (y - y_full) / (y_end - y_full))

    def tone(kind, top):
        """A mark is toned by its highest point; behind text it gets the cap."""
        below, above = share[kind]
        return _mix((above if top > CONTENT_BOTTOM else below) * fade(top))

    has_child = set(parent.values())
    radius = lambda n: R_LARGE if depth[n] <= 1 else R_SMALL
    graph = []
    for n, d in depth.items():
        x, y = xy(n)
        r = radius(n)
        if d == 0:
            graph.append(dict(kind='dot', role='you', x=x, y=y, r=r, color=AMBER_TINT))
            continue
        role = 'vendor' if d == 1 else 'sub'
        out_of_tables = not (TABLE_BAND[0] < y + r and y - r < TABLE_BAND[1])
        if role == 'sub' and n not in has_child and rng.random() < UNSCANNED_SHARE and out_of_tables:
            # white fill + outline, drawn inside the R_SMALL footprint
            graph.append(dict(kind='ring', role='unscanned', x=x, y=y, r=r - STROKE / 2,
                              color=tone('node', y + r)))
        else:
            graph.append(dict(kind='dot', role=role, x=x, y=y, r=r, color=tone('node', y + r)))
    edges = []
    for q, p in parent.items():
        (px, py), (qx, qy) = xy(p), xy(q)
        d = math.dist((px, py), (qx, qy))
        ux, uy = (qx - px) / d, (qy - py) / d
        ra, rb = radius(p), radius(q)
        # trimmed to the node outlines: no stubs, no overdraw
        e = dict(kind='edge', role='edge', x0=px + ux * ra, y0=py + uy * ra,
                 x1=qx - ux * rb, y1=qy - uy * rb)
        e['color'] = tone('edge', max(e['y0'], e['y1']) + STROKE / 2)
        edges.append(e)

    # field: evenly spaced dots per row (Bresenham), clear of the graph
    f = v['field']   # density per dot row, bottom first
    field = []
    k_lo, k_hi = math.ceil((L - 0.01 - hub_x) / DX), math.floor((R + 0.01 - hub_x) / DX)
    for h, dens in enumerate(f):
        phase = (h * GOLDEN) % 1
        for k in range(k_lo, k_hi + 1):
            if (k + h) % 2:
                continue
            m = (k - k_lo) // 2
            if math.floor((m + 1) * dens + phase) == math.floor(m * dens + phase):
                continue
            x, y = pos(k, h)
            if any(math.dist((x, y), xy(n)) < MIN_GAP for n in depth):
                continue
            if any(_seg_dist((x, y), s, t) < MIN_GAP for s, t in segs):
                continue
            field.append(dict(kind='dot', role='field', x=x, y=y, r=R_SMALL,
                              color=tone('field', y + R_SMALL)))
    graph.sort(key=lambda m: m['role'] == 'you')   # You painted last
    return field + edges + graph


def _bbox(m):
    """Painted extent (x0, y0, x1, y1) of one mark."""
    if m['kind'] == 'edge':
        w = STROKE / 2
        return (min(m['x0'], m['x1']) - w, min(m['y0'], m['y1']) - w,
                max(m['x0'], m['x1']) + w, max(m['y0'], m['y1']) + w)
    r = m['r'] + (STROKE / 2 if m['kind'] == 'ring' else 0)
    return m['x'] - r, m['y'] - r, m['x'] + r, m['y'] + r


def top_of(marks):
    return max(_bbox(m)[3] for m in marks)


@cache
def form_top(name='interior', hub_x=INTERIOR_HUB_X):
    """Top of the variant's Form XObject bbox (0, 0, W, form_top), pt above the page
    bottom. Layout QA treats vector marks below it as motif, not content."""
    return math.ceil(top_of(build(name, hub_x)))


# ----------------------------------------------------------------- output
def _paint(c, marks):
    c.saveState()
    c.setLineWidth(STROKE)
    c.setLineCap(0)
    for m in marks:
        rgb = [t / 255 for t in m['color']]
        if m['kind'] == 'edge':
            c.setStrokeColorRGB(*rgb)
            c.line(m['x0'], m['y0'], m['x1'], m['y1'])
        elif m['kind'] == 'ring':
            c.setFillColorRGB(1, 1, 1)
            c.setStrokeColorRGB(*rgb)
            c.circle(m['x'], m['y'], m['r'], stroke=1, fill=1)
        else:
            c.setFillColorRGB(*rgb)
            c.circle(m['x'], m['y'], m['r'], stroke=0, fill=1)
    c.restoreState()


def _place(c, name, hub_x):
    """Define the variant's Form XObject once per canvas, then reference it."""
    form = 'CRMotif%s%d' % (name.title(), round(hub_x * 10))
    done = c.__dict__.setdefault('_cr_motif_forms', set())
    if form not in done:
        marks = build(name, hub_x)
        # ReportLab starts every form with its default-font preamble (an empty
        # BT..ET). The motif has no text, so leave it out: paths only.
        preamble, c._preamble = c._preamble, ''
        c.beginForm(form, 0, 0, W, form_top(name, hub_x))
        _paint(c, marks)
        c.endForm()
        c._preamble = preamble
        done.add(form)
    c.doForm(form)


def draw_interior_motif(c):
    """Interior pages: You under the header rule's Sapphire/Amber junction."""
    _place(c, 'interior', INTERIOR_HUB_X)


def draw_cover_motif(c, hub_x):
    """Cover 02: You under the organisation name; hub_x = x centre of that name."""
    _place(c, 'cover', hub_x)


def export_svg(path, name='interior', hub_x=INTERIOR_HUB_X):
    """Standalone SVG, page width x motif height. Place it flush with the page
    bottom; SVG y = height - PDF y."""
    marks = build(name, hub_x)
    top = math.ceil(top_of(marks))
    f = lambda v: ('%.3f' % v).rstrip('0').rstrip('.')
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s" width="%spt" height="%spt">'
           % (f(W), f(top), f(W), f(top)),
           '<title>Cyberrank supply-chain watermark (%s)</title>' % name,
           '<g stroke-width="%s" stroke-linecap="butt">' % f(STROKE)]
    for m in marks:
        col = _hex(m['color'])
        if m['kind'] == 'edge':
            out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s"/>'
                       % (f(m['x0']), f(top - m['y0']), f(m['x1']), f(top - m['y1']), col))
        elif m['kind'] == 'ring':
            out.append('<circle cx="%s" cy="%s" r="%s" fill="#FFFFFF" stroke="%s"/>'
                       % (f(m['x']), f(top - m['y']), f(m['r']), col))
        else:
            out.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>'
                       % (f(m['x']), f(top - m['y']), f(m['r']), col))
    out.append('</g></svg>')
    with open(path, 'w') as fh:
        fh.write('\n'.join(out) + '\n')


# ------------------------------------------------------------- self-check
COVER_HUB_X_EXAMPLE = 147.7   # 'Microsoft', Poppins Medium 28 at L + 43: the preview's cover


def _ink_per_band(marks, weighted=False, y0=SEP_TOP, band=30.0):
    """Ink area (pt2) per 30 pt band above the separator, bottom band first;
    weighted=True scales each mark by its darkness."""
    ink = {}
    def add(y, area, color):
        b = int((y - y0) // band)
        ink[b] = ink.get(b, 0) + area * ((1 - sum(color) / 765) if weighted else 1)
    for m in marks:
        if m['kind'] == 'edge':
            length = math.dist((m['x0'], m['y0']), (m['x1'], m['y1']))
            n = max(1, int(length / 0.25))
            for i in range(n):
                add(m['y0'] + (m['y1'] - m['y0']) * (i + 0.5) / n, STROKE * length / n, m['color'])
        elif m['kind'] == 'ring':
            add(m['y'], 2 * math.pi * m['r'] * STROKE, m['color'])
        else:
            add(m['y'], math.pi * m['r'] ** 2, m['color'])
    return [ink.get(b, 0) for b in range(max(ink) + 1)]


def _thins_upward(marks):
    """Ink area and darkness per 30 pt band both fall with height."""
    return all(all(a > b for a, b in zip(seq, seq[1:]))
               for seq in (_ink_per_band(marks), _ink_per_band(marks, weighted=True)))


def self_check():
    import io
    from reportlab.pdfgen.canvas import Canvas
    # the cover hub follows the organisation name: check every plausible centre too
    cases = [('interior', INTERIOR_HUB_X), ('cover', COVER_HUB_X_EXAMPLE)]
    cases += [('cover', x) for x in range(int(L) + 10, 300, 5)]
    for name, hub_x in cases:
        v = VARIANTS[name]
        marks = build(name, hub_x)
        dots = [m for m in marks if m['kind'] != 'edge']
        edges = [m for m in marks if m['kind'] == 'edge']
        you = [m for m in marks if m['role'] == 'you']
        # anchor: one You, on the hub row, below the text frame
        assert len(you) == 1 and abs(you[0]['x'] - hub_x) < 1e-9 and you[0]['y'] == ROW0
        assert you[0]['y'] + R_LARGE < CONTENT_BOTTOM
        if name == 'interior':   # under the header rule's junction; field columns hit L and R
            assert abs(hub_x - HEADER_JUNCTION_X) < 0.1
            xs = [m['x'] for m in marks if m['role'] == 'field']
            assert abs(min(xs) - L) < 1e-6 and abs(max(xs) - R) < 1e-6
        # two node sizes, one stroke
        assert {m['r'] for m in dots if m['kind'] == 'dot'} <= {R_LARGE, R_SMALL}
        assert all(m['r'] == R_SMALL - STROKE / 2 for m in dots if m['kind'] == 'ring')
        # angle system: multiples of 30 deg, never horizontal; no crossings
        for e in edges:
            ang = math.degrees(math.atan2(e['y1'] - e['y0'], e['x1'] - e['x0'])) % 180
            assert min(abs(ang - a) for a in (30, 60, 90, 120, 150)) < 1e-6, ang
            if abs(ang - 60) < 1e-6 or abs(ang - 120) < 1e-6:
                assert max(e['y0'], e['y1']) <= DIAG_MAX_Y, e
        for i, e in enumerate(edges):
            for g in edges[i + 1:]:
                assert not _cross((e['x0'], e['y0']), (e['x1'], e['y1']), (g['x0'], g['y0']), (g['x1'], g['y1']))
        # inside the content measure, clear of the separator and the footer keep-outs
        for m in marks:
            x0, y0, x1, y1 = _bbox(m)
            assert L - R_LARGE - 0.01 <= x0 and x1 <= R + R_LARGE + 0.01, m
            assert y0 >= SEP_TOP + SEP_CLEAR, m
            for bx0, by0, bx1, by1 in FOOTER_KEEPOUTS.values():
                assert (x1 < bx0 - KEEPOUT_MARGIN or x0 > bx1 + KEEPOUT_MARGIN
                        or y1 < by0 - KEEPOUT_MARGIN or y0 > by1 + KEEPOUT_MARGIN), m
        # no outlined ring in the band where table cells sit
        assert not any(TABLE_BAND[0] < m['y'] + R_SMALL and m['y'] - R_SMALL < TABLE_BAND[1]
                       for m in dots if m['kind'] == 'ring')
        # contrast budget: behind text every mark is lighter than the table hairline
        if v['text_over']:
            for m in marks:
                if _bbox(m)[3] > CONTENT_BOTTOM:
                    assert _luminance(m['color']) > _luminance(HAIRLINE), (m, _hex(m['color']))
        else:
            assert top_of(marks) <= COVER_TEXT_BOTTOM - COVER_TEXT_CLEAR, top_of(marks)
        # it thins upward: ink area and darkness per 30 pt band both fall with height
        ink = _ink_per_band(marks)
        assert _thins_upward(marks), (name, [round(x) for x in ink])
        if (name, hub_x) not in cases[:2]:
            continue
        print('%-8s you x %.1f  %d field dots, %d graph nodes, %d edges, top y %.1f, ink pt2 per 30 pt band %s'
              % (name, hub_x, sum(m['role'] == 'field' for m in marks),
                 sum(m['role'] not in ('field', 'edge') for m in marks), len(edges), top_of(marks),
                 [round(x) for x in ink]))

    # forms hold paths only, and every page reuses one XObject
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=(W, H), pageCompression=0)
    for _ in range(3):
        draw_interior_motif(c)
        c.showPage()
    draw_cover_motif(c, COVER_HUB_X_EXAMPLE)
    c.showPage()
    c.save()
    pdf = buf.getvalue().decode('latin-1')
    forms = [s for s in pdf.split('endstream') if '/Subtype /Form' in s]
    assert len(forms) == 2, len(forms)
    for s in forms:
        body = s.split('stream', 1)[1]
        assert ' c\n' in body, 'form stream not readable'   # Bezier circles, uncompressed
        assert ' BT' not in body and 'Tf' not in body and 'Tj' not in body, 'text operator in motif form'
    print('self-check ok')


if __name__ == '__main__':
    import os
    self_check()
    here = os.path.dirname(os.path.abspath(__file__))
    export_svg(os.path.join(here, 'motif_interior.svg'), 'interior')
    export_svg(os.path.join(here, 'motif_cover.svg'), 'cover', COVER_HUB_X_EXAMPLE)
