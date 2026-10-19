"""Prototype: table that, when split across pages, re-opens with a caption block
('<title> · continued' + 'Rows a–b of N') above the repeated column header."""
import json, sys
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph, Table,
                                TableStyle, Spacer, Flowable)
from reportlab.platypus.doctemplate import FrameBreak

FIX, FONTS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
for n in ("Light", "Regular", "Medium"):
    pdfmetrics.registerFont(TTFont(f"Poppins-{n}", f"{FONTS}/Poppins-{n}.ttf"))

HEAD, BODY, MUTED, RULE, SURF, NAVY = map(HexColor, ("#14304F", "#22303F", "#637182", "#D9DFE6", "#F3F6F9", "#074A8E"))
W, H = A4
L = 39.685
CW = W - 2 * L
cell = ParagraphStyle("cell", fontName="Poppins-Light", fontSize=7.8, leading=11, textColor=BODY)
num = ParagraphStyle("num", parent=cell, alignment=TA_RIGHT)
th = ParagraphStyle("th", fontName="Poppins-Medium", fontSize=7.8, leading=11, textColor=HEAD)
thr = ParagraphStyle("thr", parent=th, alignment=TA_RIGHT)
cap = ParagraphStyle("cap", fontName="Poppins-Medium", fontSize=10.5, leading=14, textColor=HEAD)
capm = ParagraphStyle("capm", fontName="Poppins-Light", fontSize=7.8, leading=11.25, textColor=MUTED, alignment=TA_RIGHT)


class Caption(Flowable):
    """Table caption block: title left, meta right, 0.75 pt navy rule under it."""
    def __init__(self, title, meta):
        super().__init__(); self.title, self.meta = title, meta
    def wrap(self, aw, ah):
        self.aw = aw; return aw, 22
    def draw(self):
        c = self.canv
        t = Paragraph(self.title, cap); t.wrap(self.aw, 20); t.drawOn(c, 0, 6)
        p = Paragraph(self.meta, capm); p.wrap(self.aw, 20); p.drawOn(c, 0, 7)


class ContinuedTable(Table):
    """Table whose continuation parts draw their own '<title> · continued  Rows a–b of N'
    caption above the repeated header. Table.split() rebuilds parts via self.__class__(...),
    so extra state is copied onto the parts after the split."""
    caption, total, first_row, continued = "", 0, 1, False
    CAP = 22

    def _cap(self):
        return self.CAP if self.continued else 0

    def wrap(self, aw, ah):
        w, h = super().wrap(aw, ah - self._cap())
        return w, h + self._cap()

    def split(self, aw, ah):
        parts = super().split(aw, ah - self._cap())
        if len(parts) != 2:
            return parts
        head, tail = parts
        n_head = len(head._cellvalues) - self.repeatRows
        head.caption = tail.caption = self.caption
        head.total = tail.total = self.total
        head.first_row, head.continued = self.first_row, self.continued
        tail.first_row, tail.continued = self.first_row + n_head, True
        return [head, FrameBreak(), tail]

    def draw(self):
        super().draw()
        if self.continued:
            last = self.first_row + len(self._cellvalues) - self.repeatRows - 1
            cap_ = Caption(f"{self.caption} <font name='Poppins-Light' color='#637182'>· continued</font>",
                           f"Rows {self.first_row:,}–{last:,} of {self.total:,}")
            cap_.wrap(self._width, self.CAP); cap_.drawOn(self.canv, 0, self._height)


def register_table(title, rows):
    keys = [("Subdomain", "subdomain"), ("Category", "category"), ("Pre-QC algorithm", "pre_qc_algorithm"),
            ("Source", "source"), ("High", "high"), ("Moderate", "moderate"), ("Low", "low")]
    counts = {"high", "moderate", "low"}
    # a column with one value for every row is noise: state it once in the caption instead
    const = [(h, k) for h, k in keys if k not in counts and len({r[k] for r in rows}) == 1]
    keys = [x for x in keys if x not in const]
    note = " · ".join(f"{h}: {rows[0][k]} (all rows)" for h, k in const)
    sw = lambda t, f="Poppins-Light": pdfmetrics.stringWidth(str(t), f, 7.8) + 12   # 6 pt padding each side
    widths = [max([sw(h, "Poppins-Medium")] + [sw(r[k]) for r in rows]) for h, k in keys]   # natural, one line
    ci = [i for i, (_, k) in enumerate(keys) if k in counts]
    for i in ci: widths[i] = max(widths[j] for j in ci)   # sibling count columns share one width
    widths[0] += CW - sum(widths)          # slack goes to the identifier column
    assert widths[0] >= sw(max((r["subdomain"] for r in rows), key=sw)), "identifier column would wrap"
    data = [[Paragraph(h, thr if k in counts else th) for h, k in keys]]
    for r in rows:
        data.append([Paragraph(str(r[k]), num if k in counts else cell) for _, k in keys])
    t = ContinuedTable(data, colWidths=widths, repeatRows=1, splitInRow=1)
    t.caption, t.total = title, len(rows)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SURF),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, HEAD),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return [Caption(title, f"{len(rows):,} rows" + (f" · {note}" if note else "")), t,
            Paragraph(f"End of register · {len(rows):,} rows", ParagraphStyle("end", parent=capm, alignment=0, spaceBefore=6))]


def on_page(c, doc):
    c.saveState()
    c.setFillColor(HexColor("#EBF5FF")); c.rect(0, 0, W, 48, stroke=0, fill=1)
    c.setFillColor(HexColor("#0B7AE8")); c.rect(0, 47, W - 76, 2, stroke=0, fill=1)
    c.setFillColor(HexColor("#F5A524")); c.rect(W - 76, 47, 76, 2, stroke=0, fill=1)
    c.setFont("Poppins-Medium", 8); c.setFillColor(NAVY); c.drawRightString(W - L, 20.5, f"Page {doc.page}")
    c.setFont("Poppins-Medium", 10); c.drawString(L, H - 30, "Appendix D  Detailed evidence registers"); c.restoreState()


rows = json.load(open(FIX))["appendices"]["d_evidence_registers"]["quantum_scope_register"]["rows"]
doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=L, rightMargin=L, topMargin=64, bottomMargin=86)
doc.addPageTemplates([PageTemplate("p", [Frame(L, 86, CW, H - 64 - 86, 0, 0, 0, 0)], onPage=on_page)])
doc.build([Paragraph("D.5  Quantum scope breakdown", ParagraphStyle("h2", fontName="Poppins-Medium", fontSize=14, leading=18, textColor=HEAD, spaceAfter=10)),
           *register_table("Table D.5  Quantum scope breakdown", rows)])
print("ok", doc.page, "pages")
