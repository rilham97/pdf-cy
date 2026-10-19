"""Siren severity marker: Critical 5 rays, High 3, Medium 2, Low none (rays are cumulative).
Shows inline table rows, KPI tiles and grayscale, at the sizes the report uses."""
import math, sys
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONTS, OUT = sys.argv[1:3]
for n in ("Light", "Regular", "Medium"):
    pdfmetrics.registerFont(TTFont(f"Poppins-{n}", f"{FONTS}/Poppins-{n}.ttf"))
HEAD, BODY, MUTED, RULE, SURF = map(HexColor, ("#14304F", "#22303F", "#637182", "#D9DFE6", "#F3F6F9"))
SEV = [("critical", "Critical", "#9C3A24"), ("high", "High", "#DC2626"), ("medium", "Medium", "#D97706"), ("low", "Low", "#1F9D55")]
RAYS = {"critical": (0, 40, 90, 140, 180), "high": (40, 90, 140), "medium": (40, 140), "low": ()}


def gray(hx):
    c = HexColor(hx); y = 0.2126 * c.red + 0.7152 * c.green + 0.0722 * c.blue
    return Color(y, y, y)


def siren(c, x, y, s, key, col):
    """Draw in a box s wide x s tall, origin bottom-left."""
    cx, by = x + s * .5, y + s * .06
    c.saveState(); c.setFillColor(col)
    c.roundRect(cx - s * .34, by, s * .68, s * .12, s * .03, stroke=0, fill=1)               # base
    r = s * .24; p = c.beginPath()
    p.moveTo(cx - r, by + s * .12); p.lineTo(cx - r, by + s * .30)
    p.arcTo(cx - r, by + s * .30 - r, cx + r, by + s * .30 + r, 180, -180)
    p.lineTo(cx + r, by + s * .12); p.close(); c.drawPath(p, stroke=0, fill=1)                # dome
    c.setStrokeColor(col); c.setLineWidth(max(.6, s * .075)); c.setLineCap(1)
    hx, hy = cx, by + s * .32
    for a in RAYS[key]:
        ux, uy = math.cos(math.radians(a)), math.sin(math.radians(a))
        c.line(hx + ux * s * .36, hy + uy * s * .36, hx + ux * s * .52, hy + uy * s * .52)
    c.restoreState()


W, H = A4; L = 39.685
c = canvas.Canvas(OUT, pagesize=A4)
c.setFont("Poppins-Medium", 15); c.setFillColor(HEAD); c.drawString(L, H - 50, "Siren severity marker")
c.setFont("Poppins-Light", 8.2); c.setFillColor(MUTED)
c.drawString(L, H - 64, "Rays are cumulative: Medium 2 (sides) → High 3 (+ top) → Critical 5 (+ horizontals). Low: dome only, calm.")

# large row, colour + grayscale
y = H - 140
for g, x0 in ((False, L), (True, L + 270)):
    for i, (k, lab, hx) in enumerate(SEV):
        siren(c, x0 + i * 62, y, 34, k, gray(hx) if g else HexColor(hx))
        c.setFont("Poppins-Regular", 8.2); c.setFillColor(BODY); c.drawCentredString(x0 + i * 62 + 17, y - 12, lab)
c.setFont("Poppins-Light", 7.8); c.setFillColor(MUTED)
c.drawString(L, y + 44, "34 pt · colour"); c.drawString(L + 270, y + 44, "34 pt · grayscale")

# KPI tiles
y = H - 260
c.setFont("Poppins-Medium", 11); c.setFillColor(HEAD); c.drawString(L, y + 40, "In the severity tiles (section 04)")
c.setStrokeColor(RULE); c.setLineWidth(.75); c.line(L, y + 28, W - L, y + 28)
counts = {"critical": 1, "high": 2, "medium": 5, "low": 9}
tw = (W - 2 * L - 3 * 10.5) / 4
for i, (k, lab, hx) in enumerate(SEV):
    x = L + i * (tw + 10.5)
    siren(c, x, y + 6, 13, k, HexColor(hx))
    c.setFont("Poppins-Regular", 9.1); c.setFillColor(BODY); c.drawString(x + 17, y + 9, lab)
    c.setFont("Poppins-Medium", 20); c.setFillColor(HEAD); c.drawString(x, y - 18, str(counts[k]))
    c.setFont("Poppins-Light", 9.1); c.setFillColor(MUTED); c.drawString(x + 15, y - 18, "finding types")

# table rows at 8.6 pt, colour and grayscale
for g, (x0, title) in ((False, (L, "Table rows · 8.6 pt · colour")), (True, (L + 262, "Table rows · 8.6 pt · grayscale"))):
    y = H - 330
    c.setFont("Poppins-Medium", 11); c.setFillColor(HEAD); c.drawString(x0, y, title)
    y -= 22
    c.setFillColor(SURF); c.rect(x0, y - 6, 250, 21, stroke=0, fill=1)
    c.setFont("Poppins-Medium", 8.6); c.setFillColor(HEAD); c.drawString(x0 + 6, y + 1, "Finding"); c.drawString(x0 + 150, y + 1, "Severity")
    c.setStrokeColor(HEAD); c.setLineWidth(.75); c.line(x0, y - 6, x0 + 250, y - 6)
    rows = [("ipv4_in_header", "critical"), ("BREACH", "high"), ("HSTS_time", "high"), ("cert_notAfter", "medium"),
            ("security_headers", "medium"), ("DNS_CAArecord", "low"), ("TLS1_1", "low")]
    for name, k in rows:
        y -= 21
        hx = dict((a, h) for a, _, h in SEV)[k]
        c.setFont("Poppins-Light", 8.6); c.setFillColor(BODY); c.drawString(x0 + 6, y + 1, name)
        siren(c, x0 + 150, y - 1.5, 10.5, k, gray(hx) if g else HexColor(hx))
        c.setFont("Poppins-Regular", 8.6); c.setFillColor(BODY); c.drawString(x0 + 164, y + 1, dict((a, l) for a, l, _ in SEV)[k])
        c.setStrokeColor(RULE); c.setLineWidth(.5); c.line(x0, y - 6, x0 + 250, y - 6)

# dense register 7.8 pt
y = H - 540
c.setFont("Poppins-Medium", 11); c.setFillColor(HEAD); c.drawString(L, y, "Dense register · 7.8 pt")
for i, (k, lab, hx) in enumerate(SEV):
    yy = y - 22 - i * 18
    siren(c, L + 6, yy - 1.5, 9.5, k, HexColor(hx))
    c.setFont("Poppins-Regular", 7.8); c.setFillColor(BODY); c.drawString(L + 19, yy + 1, lab)
    c.setStrokeColor(RULE); c.setLineWidth(.5); c.line(L, yy - 5, L + 250, yy - 5)
c.showPage(); c.save()
print("ok")
