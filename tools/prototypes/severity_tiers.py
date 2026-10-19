"""Prototype: 4-tier severity block (Critical / High / Medium / Low kept separate),
signal-bar icon + label, counts computed from findings, and the findings table severity cell."""
import json, sys
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Flowable

FIX, FONTS, OUT, VARIANT = sys.argv[1:5]          # VARIANT: claude | mixed (synthetic counts to show all tiers)
for n in ("Light", "Regular", "Medium"):
    pdfmetrics.registerFont(TTFont(f"Poppins-{n}", f"{FONTS}/Poppins-{n}.ttf"))
HEAD, BODY, MUTED, RULE, SURF = map(HexColor, ("#14304F", "#22303F", "#637182", "#D9DFE6", "#F3F6F9"))
SEV = [  # key, label, bars, colour, proposed copy (needs product approval: old legend only had a merged CRITICAL/HIGH line)
    ("critical", "Critical", 4, HexColor("#9C3A24"), "Exploitable weakness with direct impact; act immediately."),
    ("high", "High", 3, HexColor("#DC2626"), "Serious weakness; fix as a priority."),
    ("medium", "Medium", 2, HexColor("#D97706"), "Moderate risk issues that should be addressed."),
    ("low", "Low", 1, HexColor("#1F9D55"), "Minor security concerns with limited impact."),
]
OFF = HexColor("#DDE3EA")
W, H = A4; L = 39.685; CW = W - 2 * L


class Signal(Flowable):
    """4 ascending bars; `bars` filled in colour, the rest light grey — level readable without colour."""
    def __init__(self, bars, colour, h=8.0):
        super().__init__(); self.bars, self.colour, self.h = bars, colour, h
        self.bw, self.gap = h * 0.22, h * 0.14
    def wrap(self, aw, ah):
        return 4 * self.bw + 3 * self.gap, self.h
    def draw(self):
        c = self.canv
        for i in range(4):
            bh = self.h * (0.4 + 0.2 * i)
            c.setFillColor(self.colour if i < self.bars else OFF)
            c.roundRect(i * (self.bw + self.gap), 0, self.bw, bh, self.bw * 0.3, stroke=0, fill=1)


def sev_label(key, size=8.6):
    k, label, bars, col, _ = next(s for s in SEV if s[0] == key)
    st = ParagraphStyle("sl", fontName="Poppins-Regular", fontSize=size, leading=size * 1.4, textColor=BODY)
    t = Table([[Signal(bars, col, h=size * 0.95), Paragraph(label, st)]], colWidths=[size * 1.35, None])
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (1, 0), (1, 0), 5)]))
    return t


def tiles(counts):
    big = ParagraphStyle("big", fontName="Poppins-Medium", fontSize=20, leading=22, textColor=HEAD)
    unit = ParagraphStyle("u", fontName="Poppins-Light", fontSize=7.8, leading=11.25, textColor=MUTED)
    cells = []
    for k, label, bars, col, copy in SEV:
        n = counts.get(k, 0)
        cells.append([sev_label(k, 9.1), Spacer(1, 5),
                      Paragraph(f"{n} <font name='Poppins-Light' size='9.1' color='#637182'>finding type{'s' if n != 1 else ''}</font>", big),
                      Spacer(1, 3), Paragraph(copy, unit)])
    gw = (CW - 3 * 10.5) / 4
    t = Table([cells], colWidths=[gw] * 4)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 10.5), ("TOPPADDING", (0, 0), (-1, -1), 8),
                           ("LINEABOVE", (0, 0), (-1, 0), 0.75, RULE)]))
    return t


class Bar(Flowable):
    """Distribution bar: one segment per tier, width ∝ count; zero tiers keep a 0 tick in the legend, not a sliver."""
    def __init__(self, counts): super().__init__(); self.counts = counts
    def wrap(self, aw, ah): self.aw = aw; return aw, 6
    def draw(self):
        total = sum(self.counts.values()) or 1; x = 0
        for k, _, _, col, _ in SEV:
            w = self.aw * self.counts.get(k, 0) / total
            if w:
                self.canv.setFillColor(col); self.canv.rect(x, 0, w - (1.5 if x + w < self.aw else 0), 6, stroke=0, fill=1)
            x += w


def findings_table(findings):
    cell = ParagraphStyle("c", fontName="Poppins-Light", fontSize=8.6, leading=12, textColor=BODY)
    num = ParagraphStyle("n", parent=cell, alignment=TA_RIGHT)
    th = ParagraphStyle("th", fontName="Poppins-Medium", fontSize=8.6, leading=12, textColor=HEAD)
    thr = ParagraphStyle("thr", parent=th, alignment=TA_RIGHT)
    order = {s[0]: i for i, s in enumerate(SEV)}
    rows = sorted(findings, key=lambda f: (order.get(f["sev"], 9), -f["domains"]))
    data = [[Paragraph(h, s) for h, s in (("Finding", th), ("Severity", th), ("Affected domains", thr), ("Breach likelihood", thr))]]
    data += [[Paragraph(f["name"], cell), sev_label(f["sev"]), Paragraph(str(f["domains"]), num), Paragraph(f["lik"], num)] for f in rows]
    t = Table(data, colWidths=[CW - 90 - 2 * 92, 90, 92, 92], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), SURF), ("LINEBELOW", (0, 0), (-1, 0), 0.75, HEAD),
                           ("LINEBELOW", (0, 1), (-1, -1), 0.5, RULE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("TOPPADDING", (0, 0), (-1, -1), 4.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
                           ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
    return t


def load_findings():
    v = json.load(open(FIX))["sections"]["vulnerabilities"]["findings"]
    out = []
    for f in v:
        sev = str(f.get("severity") or f.get("severity_source") or "").lower()
        out.append({"name": f.get("finding_type") or f.get("title") or f.get("code"), "sev": sev,
                    "domains": f.get("affected_assets_count") or len(f.get("affected_assets") or []),
                    "lik": (f"{f['breach_likelihood']['value']}%" if (f.get("breach_likelihood") or {}).get("value") is not None else "—")})
    return out


findings = load_findings()
if VARIANT == "mixed":   # synthetic: show every tier populated (Claude has no critical/high)
    findings[0]["sev"], findings[1]["sev"], findings[2]["sev"] = "critical", "high", "high"
counts = {}
for f in findings: counts[f["sev"]] = counts.get(f["sev"], 0) + 1

h2 = ParagraphStyle("h2", fontName="Poppins-Medium", fontSize=14, leading=18, textColor=HEAD, spaceAfter=4)
note = ParagraphStyle("note", fontName="Poppins-Light", fontSize=7.8, leading=11.25, textColor=MUTED)
title = "Claude data" if VARIANT == "claude" else "synthetic: first three findings re-graded to show all tiers"
story = [Paragraph(f"Finding types by severity <font name='Poppins-Light' size='9' color='#637182'>({title})</font>", h2),
         Spacer(1, 6), Bar(counts), Spacer(1, 4), tiles(counts), Spacer(1, 18),
         Paragraph("Findings", h2), findings_table(findings), Spacer(1, 6),
         Paragraph("Critical and High are separate tiers. Tier descriptions for Critical and High are proposed copy pending product approval; "
                   "Medium and Low keep the production wording.", note)]
SimpleDocTemplate(OUT, pagesize=A4, leftMargin=L, rightMargin=L, topMargin=56, bottomMargin=56).build(story)
print("ok", counts)
