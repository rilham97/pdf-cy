"""One-off: Natural Earth 1:110m admin_0 (public domain) -> compact world asset for the residency map.

Projects to Equal Earth, drops Antarctica, simplifies rings (Douglas-Peucker), drops slivers, and
pre-computes a regular dot grid (cell -> country) for the dot-matrix concept.
Tiny countries absent at 1:110m (Singapore, Monaco, Hong Kong ...) come from ne_50m_admin_0_tiny_countries
(points) and get one dot at their label point. Placement uses Natural Earth LABEL_X/LABEL_Y (visual centre),
not the geometric centroid (Indonesia/USA/France multipolygons would otherwise land in the sea or abroad).
Usage: python3 -I geo_prep.py <ne_110m_admin_0_countries.geojson> <ne_50m_admin_0_tiny_countries.geojson> <out.json>
"""
import json, math, sys
from PIL import Image, ImageDraw

A1, A2, A3, A4 = 1.340264, -0.081106, 0.000893, 0.003796
COLS = 112                       # dot grid columns across the map width
TOL = 0.006                      # simplification tolerance, projected units (~0.5 pt at 480 pt wide)
MIN_AREA = 0.0004                # drop islands smaller than ~(1.8 pt)^2 unless it is the country's only ring


def proj(lon, lat):
    lam, phi = math.radians(lon), math.radians(lat)
    th = math.asin(math.sqrt(3) / 2 * math.sin(phi))
    t2, t6 = th * th, th ** 6
    x = 2 * math.sqrt(3) * lam * math.cos(th) / (3 * (A1 + 3 * A2 * t2 + t6 * (7 * A3 + 9 * A4 * t2)))
    y = th * (A1 + A2 * t2 + t6 * (A3 + A4 * t2))
    return x, y


def rdp(pts, tol):
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    n = math.hypot(dx, dy) or 1e-12
    i, dmax = 0, 0.0
    for k in range(1, len(pts) - 1):
        d = abs(dy * pts[k][0] - dx * pts[k][1] + x2 * y1 - y2 * x1) / n
        if d > dmax:
            i, dmax = k, d
    if dmax <= tol:
        return [pts[0], pts[-1]]
    return rdp(pts[:i + 1], tol)[:-1] + rdp(pts[i:], tol)


def rdp_ring(r, tol):
    # closed ring: start == end, so split at the vertex farthest from the start first
    k = max(range(len(r)), key=lambda i: (r[i][0] - r[0][0]) ** 2 + (r[i][1] - r[0][1]) ** 2)
    return rdp(r[:k + 1], tol)[:-1] + rdp(r[k:], tol)


def area(r):
    return 0.5 * sum(r[i][0] * r[i - 1][1] - r[i - 1][0] * r[i][1] for i in range(len(r)))


def ident(p):
    # ISO_A2 is '-99' for France/Norway/Kosovo in NE; ISO_A2_EH carries the usable code. Still '-99' -> no code.
    a2 = p['ISO_A2_EH'] if p['ISO_A2_EH'] != '-99' else None
    a3 = p['ISO_A3_EH'] if p['ISO_A3_EH'] != '-99' else None
    names = sorted({p[k].lower() for k in ('ADMIN', 'NAME', 'NAME_LONG', 'FORMAL_EN', 'NAME_EN') if p.get(k)})
    return {'a2': a2, 'a3': a3, 'name': p['NAME'], 'names': names}


def main(src, tiny_src, out):
    feats = json.load(open(src))['features']
    countries, raw = [], []
    for f in feats:
        p = f['properties']
        if p['ADMIN'] == 'Antarctica':
            continue
        g = f['geometry']
        polys = [g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']
        outers = [[proj(*pt) for pt in poly[0]] for poly in polys]   # outer rings only: 110m holes are negligible
        raw.append(outers)
        simp = [rdp_ring(r, TOL) for r in outers]
        simp = [r for r in simp if len(r) >= 4]
        big = max(outers, key=lambda r: abs(area(r)))
        keep = [r for r in simp if abs(area(r)) >= MIN_AREA] or [rdp_ring(big, TOL / 3)]
        countries.append({**ident(p), 'c': [round(v, 4) for v in proj(p['LABEL_X'], p['LABEL_Y'])],
                          'rings': [[[round(x, 3), round(y, 3)] for x, y in r] for r in keep]})
    have = {c['a2'] for c in countries}
    for f in json.load(open(tiny_src))['features']:
        p = f['properties']
        if p['ISO_A2_EH'] not in have and p['ISO_A2_EH'] != '-99':
            have.add(p['ISO_A2_EH'])
            countries.append({**ident(p), 'c': [round(v, 4) for v in proj(p['LABEL_X'], p['LABEL_Y'])], 'rings': []})
            raw.append([])
    xs = [x for c in raw for r in c for x, _ in r]
    ys = [y for c in raw for r in c for _, y in r]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    # dot grid: rasterise every country with an index colour, sample cell centres
    S = 400
    img = Image.new('I', (int((x1 - x0) * S) + 1, int((y1 - y0) * S) + 1), 0)
    d = ImageDraw.Draw(img)
    for i, c in enumerate(raw, 1):
        for r in c:
            d.polygon([((x - x0) * S, (y1 - y) * S) for x, y in r], fill=i)
    pitch = (x1 - x0) / COLS
    rows = int((y1 - y0) / pitch)
    for c in countries:
        c['dots'] = []
    for j in range(rows):
        for i in range(COLS):
            x, y = x0 + (i + .5) * pitch, y1 - (j + .5) * pitch
            k = img.getpixel((int((x - x0) * S), int((y1 - y) * S)))
            if k:
                countries[k - 1]['dots'].append([i, j])
    for c, r in zip(countries, raw):         # tiny / sliver countries: one dot at the label point
        if not c['dots'] and x0 <= c['c'][0] <= x1 and y0 <= c['c'][1] <= y1:
            c['dots'] = [[min(COLS - 1, int((c['c'][0] - x0) / pitch)), min(rows - 1, int((y1 - c['c'][1]) / pitch))]]
    json.dump({'source': 'Natural Earth 1:110m admin_0 countries (public domain), Equal Earth, simplified',
               'bbox': [round(v, 4) for v in (x0, y0, x1, y1)], 'cols': COLS, 'rows': rows,
               'countries': countries}, open(out, 'w'), separators=(',', ':'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
