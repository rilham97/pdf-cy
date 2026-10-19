"""Severity marker concepts side by side: colour vs grayscale, inline (8.6 pt) and large (18 pt)."""
import math, sys
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONTS, OUT = sys.argv[1:3]
for n in ("Light", "Regular", "Medium"):
    pdfmetrics.registerFont(TTFont(f"Poppins-{n}", f"{FONTS}/Poppins-{n}.ttf"))
HEAD, BODY, MUTED, RULE = map(HexColor, ("#14304F", "#22303F", "#637182", "#D9DFE6"))
OFF = HexColor("#DDE3EA")
SEV = [("Critical", 4, "#9C3A24"), ("High", 3, "#DC2626"), ("Medium", 2, "#D97706"), ("Low", 1, "#1F9D55")]


def gray(hexcol):
    c = HexColor(hexcol); y = 0.2126 * c.red + 0.7152 * c.green + 0.0722 * c.blue
    return Color(y, y, y)


def signal(c, x, y, s, n, col):                     # 1 ascending bars (current)
    bw, gap = s * .2, s * .12
    for i in range(4):
        c.setFillColor(col if i < n else OFF)
        c.roundRect(x + i * (bw + gap), y, bw, s * (.4 + .2 * i), bw * .3, stroke=0, fill=1)


def dots(c, x, y, s, n, col):                       # 2 node meter: echoes the supply-chain motif nodes
    r, gap = s * .16, s * .11
    for i in range(4):
        cx = x + r + i * (2 * r + gap)
        if i < n:
            c.setFillColor(col); c.circle(cx, y + s * .45, r, stroke=0, fill=1)
        else:
            c.setStrokeColor(OFF); c.setLineWidth(max(.5, s * .06)); c.circle(cx, y + s * .45, r * .85, stroke=1, fill=0)


def ripple(c, x, y, s, n, col):                     # 3 propagation: core node + rings = how far impact spreads
    cx, cy = x + s * .5, y + s * .45
    c.setFillColor(col); c.circle(cx, cy, s * .11, stroke=0, fill=1)
    c.setLineWidth(max(.55, s * .06))
    for i in range(1, 4):
        c.setStrokeColor(col if i < n else OFF); c.circle(cx, cy, s * (.11 + .13 * i), stroke=1, fill=0)


def harvey(c, x, y, s, n, col):                     # 4 Harvey ball: quarters filled
    cx, cy, r = x + s * .5, y + s * .45, s * .42
    c.setStrokeColor(col); c.setLineWidth(max(.5, s * .06)); c.setFillColor(HexColor("#FFFFFF"))
    c.circle(cx, cy, r, stroke=1, fill=1)
    c.setFillColor(col)
    p = c.beginPath(); p.moveTo(cx, cy); p.arcTo(cx - r, cy - r, cx + r, cy + r, 90, -90 * n); p.close()
    c.drawPath(p, stroke=0, fill=1)


def shape(c, x, y, s, n, col):                      # 5 shape-coded: octagon / triangle / diamond / circle
    cx, cy, r = x + s * .5, y + s * .45, s * .46
    c.setFillColor(col); p = c.beginPath()
    if n == 4:
        pts = [(cx + r * math.cos(math.radians(22.5 + 45 * i)), cy + r * math.sin(math.radians(22.5 + 45 * i))) for i in range(8)]
    elif n == 3:
        pts = [(cx, cy + r), (cx + r * .95, cy - r * .7), (cx - r * .95, cy - r * .7)]
    elif n == 2:
        pts = [(cx, cy + r), (cx + r * .85, cy), (cx, cy - r), (cx - r * .85, cy)]
    else:
        c.circle(cx, cy, r * .78, stroke=0, fill=1); return
    p.moveTo(*pts[0]); [p.lineTo(*q) for q in pts[1:]]; p.close(); c.drawPath(p, stroke=0, fill=1)


def siren(c, x, y, s, n, col):                      # 6 siren / beacon: dome + base, rays = urgency (Low: none)
    cx, by = x + s * .5, y + s * .08
    c.setFillColor(col)
    c.roundRect(cx - s * .34, by, s * .68, s * .12, s * .03, stroke=0, fill=1)          # base
    p = c.beginPath(); r = s * .24
    p.moveTo(cx - r, by + s * .12); p.lineTo(cx - r, by + s * .3)
    p.arcTo(cx - r, by + s * .3 - r, cx + r, by + s * .3 + r, 180, -180)
    p.lineTo(cx + r, by + s * .12); p.close(); c.drawPath(p, stroke=0, fill=1)        # dome
    c.setStrokeColor(col); c.setLineWidth(max(.55, s * .07)); c.setLineCap(1)
    hub = (cx, by + s * .32)
    rays = {4: (90, 40, 140, 0, 180), 3: (90, 40, 140), 2: (90,), 1: ()}[n]
    for a in rays:
        ux, uy = math.cos(math.radians(a)), math.sin(math.radians(a))
        c.line(hub[0] + ux * s * .34, hub[1] + uy * s * .34, hub[0] + ux * s * .5, hub[1] + uy * s * .5)
    c.setLineCap(0)


def lamp(c, x, y, s, n, col):                       # 7 status lamp stack: one lit lamp, position = level (top = Critical)
    w, h = s * .42, s * .96
    lx = x + s * .5 - w / 2
    c.setFillColor(HexColor("#EEF2F6")); c.setStrokeColor(OFF); c.setLineWidth(max(.4, s * .04))
    c.roundRect(lx, y, w, h, w * .3, stroke=1, fill=1)
    r = w * .32
    for i in range(4):                               # i=0 bottom (Low) .. 3 top (Critical)
        cy = y + h * (.14 + .24 * i)
        lit = (i + 1) == n
        c.setFillColor(col if lit else OFF); c.circle(x + s * .5, cy, r, stroke=0, fill=1)


CONCEPTS = [
    ("1  Signal bars", "Current prototype. Close to SecurityScorecard's 3-bar signal.", signal),
    ("2  Node meter", "4 equal nodes, filled = level. Echoes the motif's network nodes; horizontal, not a 'signal'.", dots),
    ("3  Propagation rings", "Core node + rings: how far impact spreads. Ties to supply-chain propagation; unique.", ripple),
    ("4  Harvey ball", "Audit/consulting convention (quarters). Familiar, but often read as 'completeness'.", harvey),
    ("5  Shape-coded", "Octagon / triangle / diamond / circle. Readable without colour; road-sign familiar.", shape),
    ("6  Siren / beacon", "Alarm light; rays = urgency (Critical 4 rays ... Low none). Strong 'alert' meaning; unique.", siren),
    ("7  Status lamp", "Vertical 4-lamp stack, one lit; position = level (top = Critical). Traffic-light idea.", lamp),
]

W, H = landscape(A4)
H = 7 * 92 + 120
c = canvas.Canvas(OUT, pagesize=(W, H))
c.setFont("Poppins-Medium", 15); c.setFillColor(HEAD); c.drawString(36, H - 44, "Severity marker concepts")
c.setFont("Poppins-Light", 8.2); c.setFillColor(MUTED)
c.drawString(36, H - 58, "Each row: inline 8.6 pt with label (colour)  ·  same in grayscale  ·  large 18 pt (colour)  ·  large grayscale")
y0, rowh = H - 92, 92
for r, (name, desc, fn) in enumerate(CONCEPTS):
    y = y0 - r * rowh
    c.setStrokeColor(RULE); c.setLineWidth(.5); c.line(36, y - rowh + 14, W - 36, y - rowh + 14)
    c.setFont("Poppins-Medium", 10.5); c.setFillColor(HEAD); c.drawString(36, y - 4, name)
    c.setFont("Poppins-Light", 7.8); c.setFillColor(MUTED); c.drawString(36, y - 17, desc)
    for g, gx in ((False, 36), (True, 236)):
        for i, (lab, n, hx) in enumerate(SEV):
            yy = y - 38 - i * 12
            col = gray(hx) if g else HexColor(hx)
            fn(c, gx, yy - 1, 8.6, n, col)
            c.setFont("Poppins-Regular", 8.6); c.setFillColor(BODY); c.drawString(gx + 18, yy, lab)
    for g, gx in ((False, 436), (True, 606)):
        for i, (lab, n, hx) in enumerate(SEV):
            fn(c, gx + i * 38, y - 66, 18, n, gray(hx) if g else HexColor(hx))
            c.setFont("Poppins-Light", 6.8); c.setFillColor(MUTED); c.drawString(gx + i * 38, y - 76, lab)
c.showPage(); c.save()
print("ok")
