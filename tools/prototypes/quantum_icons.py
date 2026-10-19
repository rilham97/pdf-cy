"""Quantum tables with classification icons: category (Phosphor light), risk level (siren), PQC alternative."""
import json, math, re, sys
from reportlab.graphics.shapes import Drawing, Group
from reportlab.graphics.svgpath import SvgPath
from reportlab.graphics import renderPDF
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Flowable

FIX, FONTS, PH, OUT = sys.argv[1:5]
for n in ("Light", "Regular", "Medium"):
    pdfmetrics.registerFont(TTFont(f"Poppins-{n}", f"{FONTS}/Poppins-{n}.ttf"))
HEAD, BODY, MUTED, RULE, SURF, NAVY = map(HexColor, ("#14304F", "#22303F", "#637182", "#D9DFE6", "#F3F6F9", "#074A8E"))
RISK = {"high": ("High", "#DC2626", (40, 90, 140)), "moderate": ("Moderate", "#D97706", (40, 140)), "low": ("Low", "#1F9D55", ())}
CAT_ICON = {"Public-key cryptography": "key", "Symmetric cryptography": "lock-key", "Hash functions": "hash", "Certificate": "certificate"}
W, H = A4; L = 39.685; CW = W - 2 * L


class Ph(Flowable):
    """Phosphor icon (viewBox 256) as recoloured vector."""
    def __init__(self, name, size, color):
        super().__init__(); self.size, self.color = size, color
        self.d = re.search(r'\sd="([^"]+)"', open(f"{PH}/{name}-light.svg").read()).group(1)
    def wrap(self, aw, ah): return self.size, self.size
    def draw(self):
        s = self.size / 256
        g = Group(SvgPath(self.d, fillColor=self.color, strokeColor=None, strokeWidth=0), transform=(s, 0, 0, -s, 0, self.size))
        d = Drawing(self.size, self.size); d.add(g); renderPDF.draw(d, self.canv, 0, 0)


class Siren(Flowable):
    def __init__(self, level, s):
        super().__init__(); self.level, self.s = level, s
    def wrap(self, aw, ah): return self.s, self.s
    def draw(self):
        c, s = self.canv, self.s; _, hx, rays = RISK[self.level]; col = HexColor(hx)
        cx, by = s * .5, s * .06
        c.setFillColor(col); c.roundRect(cx - s * .34, by, s * .68, s * .12, s * .03, stroke=0, fill=1)
        r = s * .24; p = c.beginPath(); p.moveTo(cx - r, by + s * .12); p.lineTo(cx - r, by + s * .3)
        p.arcTo(cx - r, by + s * .3 - r, cx + r, by + s * .3 + r, 180, -180); p.lineTo(cx + r, by + s * .12); p.close()
        c.drawPath(p, stroke=0, fill=1)
        c.setStrokeColor(col); c.setLineWidth(max(.6, s * .075)); c.setLineCap(1)
        for a in rays:
            ux, uy = math.cos(math.radians(a)), math.sin(math.radians(a))
            c.line(cx + ux * s * .36, by + s * .32 + uy * s * .36, cx + ux * s * .52, by + s * .32 + uy * s * .52)


def icon_label(icon, text, style, gap=4, size=None):
    size = size or style.fontSize * 1.15
    t = Table([[icon, Paragraph(text, style)]], colWidths=[size + gap, None])
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return t


cell = ParagraphStyle("c", fontName="Poppins-Light", fontSize=8.6, leading=12, textColor=BODY)
lab = ParagraphStyle("l", fontName="Poppins-Regular", fontSize=8.6, leading=12, textColor=BODY)
mut = ParagraphStyle("m", parent=cell, textColor=MUTED)
num = ParagraphStyle("n", parent=cell, alignment=TA_RIGHT)
th = ParagraphStyle("th", fontName="Poppins-Medium", fontSize=8.6, leading=12, textColor=HEAD)
thr = ParagraphStyle("thr", parent=th, alignment=TA_RIGHT)
style = TableStyle([("BACKGROUND", (0, 0), (-1, 0), SURF), ("LINEBELOW", (0, 0), (-1, 0), 0.75, HEAD),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.5, RULE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)])

q = json.load(open(FIX))["sections"]["quantum_security"]
data = [[Paragraph(h, s) for h, s in (("Category", th), ("Algorithm", th), ("Risk", th), ("Findings", thr), ("Protocols", th), ("PQC alternative", th))]]
for grp in q["findings_by_category"]:
    for i, a in enumerate(grp["algorithms"]):
        cat = icon_label(Ph(CAT_ICON.get(grp["category"], "atom"), 10, NAVY), grp["category"], cell, size=10) if i == 0 else ""
        risk = icon_label(Siren(a["risk_level"], 10), RISK[a["risk_level"]][0], lab, size=10)
        pqc = (icon_label(Ph("shield-check", 10, HexColor("#1F9D55")), str(a["pqc_alternative_available"]), lab, size=10)
               if a.get("pqc_alternative_available") else Paragraph("Not available", mut))
        data.append([cat, Paragraph(a["algorithm"], cell), risk, Paragraph(str(a["findings"]), num),
                     Paragraph(", ".join(a["protocol_labels"]), cell), pqc])
t1 = Table(data, colWidths=[142, 106, 66, 50, CW - 142 - 106 - 66 - 50 - 82, 82], repeatRows=1); t1.setStyle(style)

# scope register (Appendix D uses the dense spec): siren stacked above each count label so 'Moderate' never wraps
dcell = ParagraphStyle("dc", fontName="Poppins-Light", fontSize=7.8, leading=11, textColor=BODY)
dnum = ParagraphStyle("dn", parent=dcell, alignment=TA_RIGHT)
dth = ParagraphStyle("dth", fontName="Poppins-Medium", fontSize=7.8, leading=11, textColor=HEAD)
dthr = ParagraphStyle("dthr", parent=dth, alignment=TA_RIGHT)


def stacked(k):
    t = Table([[Siren(k, 9)], [Paragraph(RISK[k][0], dthr)]])
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "RIGHT"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    return t


hdr = [Paragraph("Subdomain", dth), Paragraph("Category", dth), Paragraph("Algorithm", dth)] + [stacked(k) for k in ("high", "moderate", "low")]
rows = json.load(open(FIX))["appendices"]["d_evidence_registers"]["quantum_scope_register"]["rows"][9:15]
data2 = [hdr] + [[Paragraph(r["subdomain"], dcell),
                  icon_label(Ph(CAT_ICON.get(r["category"], "atom"), 8.5, NAVY), r["category"], dcell, size=8.5),
                  Paragraph(r["pre_qc_algorithm"], dcell), Paragraph(str(r["high"]), dnum),
                  Paragraph(str(r["moderate"]), dnum), Paragraph(str(r["low"]), dnum)] for r in rows]
t2 = Table(data2, colWidths=[CW - 128 - 100 - 3 * 52, 128, 100, 52, 52, 52], repeatRows=1)
t2.setStyle(style); t2.setStyle(TableStyle([('VALIGN', (0, 0), (-1, 0), 'BOTTOM'), ('TOPPADDING', (0, 1), (-1, -1), 3.5), ('BOTTOMPADDING', (0, 1), (-1, -1), 3.5)]))

h2 = ParagraphStyle("h2", fontName="Poppins-Medium", fontSize=14, leading=18, textColor=HEAD, spaceAfter=8)
note = ParagraphStyle("note", fontName="Poppins-Light", fontSize=7.8, leading=11.25, textColor=MUTED)
SimpleDocTemplate(OUT, pagesize=A4, leftMargin=L, rightMargin=L, topMargin=56, bottomMargin=56).build([
    Paragraph("Algorithms found", h2), t1, Spacer(1, 6),
    Paragraph("Category icons: key = public-key, lock = symmetric, # = hash functions, certificate = certificate. "
              "Risk uses the siren (High 3 rays, Moderate 2, Low none). PQC alternative shows a check-shield when an alternative is reported; "
              "'Not available' means the source did not state one.", note),
    Spacer(1, 20), Paragraph("D.5 Quantum scope breakdown (excerpt)", h2), t2])
print("ok")
