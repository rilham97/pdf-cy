#!/usr/bin/env python3
"""Appendix B, IISRI rating scale: Platypus component for the Cyber Risk Report.

Usage in the report generator::

    from rating_scale import make_styles, build_rating_scale
    styles = make_styles()                      # registers Poppins on first use
    story += build_rating_scale({"grade": "BB", "state": "assessed", "state_reason": None}, styles)

``rating`` contract (validated; contradictory data raises ValueError, so a stand-in
grade can never be printed):

    grade         "AAA" .. "D" when state == "assessed", otherwise None
    state         "assessed" | "unavailable" | "not_assessed"
    state_reason  str | None   shown only for the two no-grade states

Layout: H1 ('Appendix B  IISRI rating scale'), the one-line methodology intro, a state
panel (no-grade states only), a slim AAA..D spectrum with a "Your rating" pin, then a
compact Grade | Meaning table (grade letter stacked over its mark; colour only as a 5 pt
spine). Every state fits one A4 content frame: the template's 698.9 pt (H1 top 75 pt to
footer - 20 pt) and the stricter 693.9 pt (top 80 pt) are both asserted by the self-check.
Headroom (693.9 pt frame): 37.5 pt graded, 12.5 pt with the default no-grade reason.
A state_reason over about 250 characters (3+ panel lines) pushes the last rows to a
second page; the table header repeats there and nothing is truncated, so keep reasons
to one sentence.

Wording: the ten meanings are the official IISRI text, verbatim from the previous
report's Appendix A (pp. 42-43). Each is split only at its sentence boundary into the
assurance statement (Light ink) and the findings/recommended work (Regular navy).

Accessibility: no text is ever placed on a grade colour (white or ink fails 4.5:1 on
several of them), grade letters and marks are always printed, every text pair is
asserted >= 4.5:1 and every non-text selection cue >= 3:1 at import time.

``python3 rating_scale.py`` runs the fit self-check and builds Rating_Scale_Preview.pdf
(page 1 assessed BB, page 2 unavailable sample) plus 110 dpi PNGs, using the approved
header, light footer band (no network motif) and CYBERRANK outline watermark.
Needs reportlab; the preview also needs pymupdf (SVG footer icons and PNG renders).
"""
from html import escape
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, Paragraph, Spacer, Table, TableStyle

ASSETS = Path(__file__).resolve().parent / 'assets' / 'fonts'

# Document tokens (05_Desain_Terbaru/03-design-tokens/cyberrank-color-tokens.css)
NAVY, INK = '#14304F', '#22303F'
# muted token #637182 (darkened from #6B7A8C, decision 2026-10-14) passes 4.5:1 on white, #F3F6F9 and #EBF5FF
MUTED, CHROME_MUTED = '#637182', '#637182'
PAPER, SURFACE, BORDER = '#FFFFFF', '#F3F6F9', '#D9DFE6'
SAPPHIRE, SAPPHIRE_50, SAPPHIRE_700, AMBER = '#0B7AE8', '#EBF5FF', '#074A8E', '#F5A524'

# Official IISRI wording, verbatim from the previous report (Appendix A, pp. 42-43).
# (grade, mark, colour token, assurance statement, findings and recommended work)
# Marks follow the IISRI methodology appendix (p. 44); old p. 43 printed 'Very Insufficient'.
SCALE = [
    ('AAA', 'Excellent', '#1F6E43',
     'All information security and/or privacy controls are adequate, appropriate, and effective enough to provide reasonable assurance that security and/or privacy issues are being managed, and objectives are met.',
     None),
    ('AA', 'Very good', '#2E8B57',
     'Almost all information security and/or privacy controls are adequate, appropriate, and effective enough to provide reasonable assurance that security and/or privacy issues are being managed, and objectives are met.',
     None),
    ('A', 'Good', '#5B9E4F',
     'Almost all information security and/or privacy controls are adequate, appropriate, and effective enough to provide reasonable assurance that security and/or privacy issues are being managed, and objectives are met.',
     'A few specific control weaknesses have been noted. Minor additional work on information security and/or privacy is recommended.'),
    ('BBB', 'Satisfactory', '#8FAA3E',
     'Main information security and/or privacy controls are adequate, appropriate, and effective enough to provide reasonable assurance that security and/or privacy issues are being managed, and objectives are met.',
     'A few specific control weaknesses have been noted. Minor additional work on information security and/or privacy is recommended.'),
    ('BB', 'Sufficient', '#C2A526',
     'Main information security and/or privacy controls are adequate, appropriate, and effective enough to provide reasonable assurance that security and/or privacy issues are being managed, and objectives are met.',
     'Some specific control weaknesses have been noted. Major additional work on information security and/or privacy is recommended.'),
    ('B', 'Moderate', '#D8961A',
     'Some information security and/or privacy controls are adequate, appropriate, and effective enough to provide reasonable assurance that security and/or privacy issues are being managed, and objectives are met.',
     'Many specific control weaknesses have been noted. Major additional work on information security and/or privacy is highly recommended.'),
    ('CCC', 'Insufficient', '#D87A2A',
     'Main information security and/or privacy controls are unlikely to provide reasonable assurance that security and/or privacy issues are being managed and objectives are met.',
     'Major work on information security and/or privacy is highly recommended.'),
    ('CC', 'Very insufficient', '#C74A3C',
     'Almost all information security and/or privacy controls are unlikely to provide reasonable assurance that security and/or privacy issues are being managed and objectives are met.',
     'Major work on information security and/or privacy is highly recommended.'),
    ('C', 'Poor', '#9E3038',
     'Almost all information security and/or privacy controls are unlikely to provide reasonable assurance that security and/or privacy issues are being managed and objectives are met.',
     'Major work or completely new program on information security and/or privacy is required.'),
    ('D', 'Very poor', '#6E1F2E',
     'All information security and/or privacy controls are not providing any assurance that security and/or privacy issues are being managed and objectives are met.',
     'Complete new program on information security and/or privacy is required.'),
]
GRADES = [row[0] for row in SCALE]
MARKS = {row[0]: row[1] for row in SCALE}
# Verbatim from the IISRI methodology appendix (old report p. 44).
INTRO = 'Ten grades. Higher grades mean lower weakness values and therefore lower likelihood.'
# Horizontal bars run worst -> best, left -> right (D .. AAA); vertical lists keep AAA first.
BAR_GRADES = GRADES[::-1]
END_LABELS = ('Controls provide no assurance', 'All controls adequate, appropriate and effective')   # left, right
STATE_TEXT = {  # (panel title, default reason) for the states without a grade
    'unavailable': ('Your rating: not available',
                    'An IISRI grade could not be determined for this assessment.'),
    'not_assessed': ('Your rating: not assessed',
                     'This organisation has not been rated against the IISRI scale yet.'),
}


def _luminance(hex_color):
    channels = [int(hex_color.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    r, g, b = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg):
    """WCAG 2.x contrast ratio between two #RRGGBB colours."""
    hi, lo = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


# Every text/background pair this component paints (>= 4.5:1). Text never sits on a grade colour.
TEXT_PAIRS = {
    'cell text on paper': (INK, PAPER),
    'headings, grade letters, work sentence on paper': (NAVY, PAPER),
    'appendix label (H1, Light) on paper': (SAPPHIRE_700, PAPER),
    'intro and end labels on paper': (MUTED, PAPER),
    'cell text on Your-rating row': (INK, SAPPHIRE_50),
    'grade letter and work sentence on Your-rating row': (NAVY, SAPPHIRE_50),
    'pill and pin text': (PAPER, NAVY),
    'state panel text on surface': (INK, SURFACE),
    'state panel title on surface': (NAVY, SURFACE),
}
# Non-text selection cues (WCAG 1.4.11, >= 3:1 against what they sit next to).
NON_TEXT_PAIRS = {
    'spectrum ring vs its white moat and the page': (NAVY, PAPER),
    'row box vs page': (SAPPHIRE, PAPER),
    'row box vs row fill': (SAPPHIRE, SAPPHIRE_50),
}
for _name, (_fg, _bg) in TEXT_PAIRS.items():
    assert contrast(_fg, _bg) >= 4.5, (_name, contrast(_fg, _bg))
for _name, (_fg, _bg) in NON_TEXT_PAIRS.items():
    assert contrast(_fg, _bg) >= 3.0, (_name, contrast(_fg, _bg))


def register_fonts(asset_dir=ASSETS):
    for weight in ('Light', 'Regular', 'Medium', 'SemiBold'):
        pdfmetrics.registerFont(TTFont(f'Poppins-{weight}', str(Path(asset_dir) / f'Poppins-{weight}.ttf')))


def make_styles():
    """Approved interior styles (registers Poppins if needed). The generator may pass its own
    dict instead; the component reads 'h1', 'intro', 'cell' and 'cell_head'."""
    if 'Poppins-Light' not in pdfmetrics.getRegisteredFontNames():
        register_fonts()

    def s(name, weight, size, leading, color):
        return ParagraphStyle(name, fontName=f'Poppins-{weight}', fontSize=size, leading=leading,
                              textColor=HexColor(color), splitLongWords=False)
    return {
        'h1': s('h1', 'Medium', 23, 26.25, NAVY),
        'intro': s('intro', 'Light', 10.5, 14.5, MUTED),
        'body': s('body', 'Light', 9.1, 13, INK),
        'h3': s('h3', 'Medium', 11, 14, NAVY),
        'note': s('note', 'Light', 7.8, 11.25, MUTED),
        'cell': s('cell', 'Light', 8.6, 12, INK),
        'cell_head': s('cell_head', 'Medium', 8.6, 12, NAVY),
    }


def _pill_size(text, size):
    return pdfmetrics.stringWidth(text, 'Poppins-Medium', size) + 12, size + 6


def _draw_pill(canv, x, y, text, size=7.4):
    """Navy pill with white Medium text; (x, y) is its bottom-left corner."""
    w, h = _pill_size(text, size)
    canv.setFillColor(HexColor(NAVY))
    canv.roundRect(x, y, w, h, h / 2, stroke=0, fill=1)
    canv.setFillColor(white)
    canv.setFont('Poppins-Medium', size)
    canv.drawCentredString(x + w / 2, y + (h - size * 0.7) / 2, text)


class Pill(Flowable):
    def __init__(self, text, size=7.4):
        super().__init__()
        self.text, self.size = text, size
        self.width, self.height = _pill_size(text, size)

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        _draw_pill(self.canv, 0, 0, self.text, self.size)


class Spectrum(Flowable):
    """Slim 10-segment D..AAA bar (worst left, best right): letters and end labels below, optional pin
    above one grade. selected: index into GRADES (AAA first); drawn at its bar position.

    The selected segment is raised and wrapped in a navy ring with a white moat, so the
    cue stays visible on every grade colour (the ring always borders white, 13.4:1).
    """
    GAP, BAR_H, LIFT = 1.5, 8.0, 2.5     # segment gap, bar height, raise of the selected segment
    RING, RING_W = 2.2, 1.2              # ring centreline offset from the raised segment, stroke
    LETTERS_TOP = 23.0                   # end labels (0-10) + gap + letters (12-23)
    PIN_H = 18.5

    def __init__(self, selected=None, pin_text=None):
        super().__init__()
        self.selected, self.pin_text = selected, pin_text
        reach = self.LIFT + self.RING + self.RING_W / 2       # how far the ring extends past the bar
        self.bar_y = self.LETTERS_TOP + 3 + reach             # bottom of a regular segment
        self.top = self.bar_y + self.BAR_H + reach            # top of the ring zone

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        self.height = self.top + (self.PIN_H if self.selected is not None else 0)
        return self.width, self.height

    def draw(self):
        c, bar = self.canv, SCALE[::-1]                   # D (worst) left .. AAA (best) right
        sel = None if self.selected is None else len(SCALE) - 1 - self.selected
        seg = (self.width + self.GAP) / len(SCALE) - self.GAP
        xs = [i * (seg + self.GAP) for i in range(len(SCALE))]
        for i, (_g, _m, color, *_rest) in enumerate(bar):
            if i != sel:
                c.setFillColor(HexColor(color))
                c.rect(xs[i], self.bar_y, seg, self.BAR_H, stroke=0, fill=1)
        if sel is not None:  # drawn last so the moat covers the neighbours' edges
            x, y0, h = xs[sel], self.bar_y - self.LIFT, self.BAR_H + 2 * self.LIFT
            c.setFillColor(white); c.setStrokeColor(HexColor(NAVY)); c.setLineWidth(self.RING_W)
            r = self.RING
            c.roundRect(x - r, y0 - r, seg + 2 * r, h + 2 * r, 2, stroke=1, fill=1)
            c.setFillColor(HexColor(bar[sel][2]))
            c.rect(x, y0, seg, h, stroke=0, fill=1)
        c.setFillColor(HexColor(NAVY)); c.setFont('Poppins-Medium', 8.6)
        for x, (grade, *_rest) in zip(xs, bar):
            c.drawCentredString(x + seg / 2, 14.5, grade)
        c.setFillColor(HexColor(MUTED)); c.setFont('Poppins-Light', 7.8)
        c.drawString(0, 2, END_LABELS[0])
        c.drawRightString(self.width, 2, END_LABELS[1])
        if sel is not None:  # pin, clamped inside the bar width at D and AAA
            cx, tip = xs[sel] + seg / 2, self.top + 1
            w, _h = _pill_size(self.pin_text, 7.4)
            c.setFillColor(HexColor(NAVY))
            p = c.beginPath(); p.moveTo(cx - 3.5, tip + 4); p.lineTo(cx + 3.5, tip + 4); p.lineTo(cx, tip); p.close()
            c.drawPath(p, stroke=0, fill=1)
            _draw_pill(c, min(max(cx - w / 2, 0), self.width - w), tip + 3.5, self.pin_text)


def _check(rating):
    state, grade, reason = rating.get('state'), rating.get('grade'), rating.get('state_reason')
    if state == 'assessed':
        if grade not in GRADES:
            raise ValueError(f'assessed rating needs a grade in {GRADES}, got {grade!r}')
    elif state in STATE_TEXT:
        if grade is not None:
            raise ValueError(f'state {state!r} must not carry a grade (got {grade!r})')
    else:
        raise ValueError(f'unknown rating state {state!r}')
    if reason is not None and not isinstance(reason, str):
        raise ValueError(f'state_reason must be a string or None, got {type(reason).__name__}')
    return state, grade


def build_rating_scale(rating, styles, appendix_label='Appendix B'):
    """Flowables for the IISRI rating scale appendix: H1, intro, optional state panel,
    Spectrum, Table.

    rating = {"grade": "BBB"|None, "state": "assessed"|"unavailable"|"not_assessed",
              "state_reason": str|None}. appendix_label is printed in Light Sapphire-700 before
    the H1 title ('Appendix B  IISRI rating scale'); pass None if the generator numbers H1s itself.
    """
    state, grade = _check(rating)
    sel = GRADES.index(grade) if grade else None
    cell, head = styles['cell'], styles['cell_head']
    letter = ParagraphStyle('grade', parent=head, fontSize=10, leading=12)

    # The appendix letter rides in the H1 (as in the old 'Appendix A. IISRI Rating Scale' title and
    # the Contents entry 'B  IISRI rating scale'), so it costs no height.
    label = (f'<font name="Poppins-Light" color="{SAPPHIRE_700}">{escape(appendix_label)}</font>&nbsp;&nbsp;'
             if appendix_label else '')
    story = [Paragraph(label + 'IISRI rating scale', styles['h1']), Spacer(0, 6),
             Paragraph(INTRO, styles['intro']), Spacer(0, 12)]
    if sel is None:  # explicit state instead of a highlight; never a stand-in grade
        title, default_reason = STATE_TEXT[state]
        reason = escape((rating.get('state_reason') or '').strip() or default_reason)
        panel = Table([[Paragraph(f'<font name="Poppins-Medium" color="{NAVY}">{title}.</font> {reason} '
                                  'No grade is highlighted on the scale below.', cell)]], colWidths=['100%'])
        panel.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor(SURFACE)),
            ('LINEBEFORE', (0, 0), (0, -1), 2, HexColor(NAVY)),
            ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ]))
        story += [panel, Spacer(0, 10)]
    story += [Spectrum(sel, f'Your rating: {grade} · {MARKS[grade]}' if grade else None), Spacer(0, 12)]

    rows = [['', Paragraph('Grade', head), Paragraph('Meaning', head)]]
    for i, (g, mark, _color, assurance, work) in enumerate(SCALE):
        grade_cell = [Paragraph(g, letter), Paragraph(mark, cell)]  # letter over its official mark
        if i == sel:
            grade_cell += [Spacer(0, 3), Pill('Your rating')]
        # assurance statement in Light ink; findings + recommended work in Regular navy so the ask scans
        meaning = assurance + (f' <font name="Poppins-Regular" color="{NAVY}">{work}</font>' if work else '')
        rows.append(['', grade_cell, Paragraph(meaning, cell)])

    # spine | Grade (letter over mark; 84 keeps 'Very insufficient', 67.1 pt, on one line) | Meaning.
    # Stacking the mark under the letter gives Meaning a 412 pt measure: 3-4 lines per grade.
    table = Table(rows, colWidths=[5, 84, None], repeatRows=1)
    cmds = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (0, -1), 0), ('RIGHTPADDING', (0, 0), (0, -1), 0),
        ('LEFTPADDING', (1, 0), (1, -1), 8),
        ('TOPPADDING', (1, 1), (1, -1), 3.6),  # 10 pt letter shares the 8.6 pt first baseline
        ('LINEBELOW', (0, 0), (-1, 0), 0.75, HexColor(NAVY)),
        ('LINEBELOW', (1, 1), (-1, -1), 0.5, HexColor(BORDER)),
        ('LINEBELOW', (0, 1), (0, -2), 1.5, white),  # small white break between spines
    ]
    for i, (_g, _m, color, *_rest) in enumerate(SCALE, start=1):
        cmds.append(('BACKGROUND', (0, i), (0, i), HexColor(color)))
    if sel is not None:
        cmds += [('BACKGROUND', (1, sel + 1), (-1, sel + 1), HexColor(SAPPHIRE_50)),
                 ('BOX', (1, sel + 1), (-1, sel + 1), 0.75, HexColor(SAPPHIRE))]
    table.setStyle(TableStyle(cmds))
    story.append(table)
    return story


# ---------------------------------------------------------------------------
# Preview: two pages with the approved header, light footer band and watermark.
# The generator supplies its own chrome; nothing below is needed in production.
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, PageBreak

    OUT = Path(__file__).resolve().parent
    W, H = A4
    MM = 72 / 25.4
    L, R = 14 * MM, W - 14 * MM
    FY = H - 48                     # footer band top, measured from the page top
    CONTENT_TOP = 75                # H1 top in the template's start()
    CONTENT_BOTTOM = FY - 20
    ORG, DOMAIN = 'Claude', 'claude.com'                      # old report p.1
    ASSESSED, GENERATED = '02 Oct 2026', '03 Oct 2026'        # REPORT DATE / DATE GENERATED
    CONTACTS = [('cyberrank.ai', 'https://www.cyberrank.ai/', 'globe.svg'),
                ('support@cyberrank.ai', 'mailto:support@cyberrank.ai', 'envelope.svg'),
                ('LinkedIn', 'https://www.linkedin.com/company/105646816', 'linkedin.svg')]
    # Preview-only design notes, drawn in the 20 pt gap above the footer, outside the component.
    NOTES = {1: 'Design preview, assessed state: BB is the grade printed for Claude in the IISRI External '
                'Rating card of the previous report (p. 2).',
             2: 'Design preview, unavailable state: [sample reason], not Claude’s real status (Claude is '
                'rated BB, see page 1). Remove this note in production.'}
    ICONS = []

    def txt(c, s, x, top, size, font, color, align='left'):
        c.setFillColor(HexColor(color)); c.setFont('Poppins-' + font, size)
        y = H - top - size * .82
        {'left': c.drawString, 'right': c.drawRightString, 'center': c.drawCentredString}[align](x, y, s)

    class NumberedCanvas(rl_canvas.Canvas):
        def __init__(self, *a, **k):
            super().__init__(*a, **k); self._pages = []

        def showPage(self):
            self._pages.append(dict(self.__dict__)); self._startPage()

        def save(self):
            for state in self._pages:
                self.__dict__.update(state)
                txt(self, f'Page {self._pageNumber} of {len(self._pages)}', R, FY + 21, 8, 'Medium', SAPPHIRE_700, 'right')
                super().showPage()
            super().save()

    def chrome(c, doc):
        c.saveState()
        # watermark: outline CYBERRANK, rotated; origin top 338.856 pt as computed by the template
        c.saveState(); c.translate(10, H - 338.856); c.rotate(-90)
        c.setStrokeColor(HexColor('#C8D4E1')); c.setLineWidth(.9)
        t = c.beginText(); t.setTextOrigin(0, 0); t.setFont('Poppins-SemiBold', 26)
        t.setTextRenderMode(1); t.setCharSpace(1); t.textOut('CYBERRANK'); c.drawText(t); c.restoreState()
        # header
        c.drawImage(str(ASSETS / 'Cyberrank-logo.png'), L, H - 8 - 32, width=128, height=32, mask='auto')
        txt(c, f'Cyber Risk Report for {ORG}', 196, 11, 10, 'Medium', SAPPHIRE_700)
        txt(c, DOMAIN, 196, 29, 7.8, 'Regular', CHROME_MUTED)
        txt(c, f'Assessment  {ASSESSED}', R, 13, 7.6, 'Medium', SAPPHIRE_700, 'right')
        txt(c, f'Generated  {GENERATED}', R, 29, 7.6, 'Regular', CHROME_MUTED, 'right')
        c.setLineWidth(2)
        c.setStrokeColor(HexColor(SAPPHIRE)); c.line(L, H - 48, R - 116, H - 48)
        c.setStrokeColor(HexColor(AMBER)); c.line(R - 116, H - 48, R, H - 48)
        # light footer band, plain (no network motif), centred contacts
        c.setFillColor(HexColor(SAPPHIRE_50)); c.rect(0, 0, W, 48, stroke=0, fill=1)
        c.setFillColor(HexColor(SAPPHIRE)); c.rect(0, 47, W - 76, 2, stroke=0, fill=1)
        c.setFillColor(HexColor(AMBER)); c.rect(W - 76, 47, 76, 2, stroke=0, fill=1)
        widths = [pdfmetrics.stringWidth(label, 'Poppins-Regular', 8.2) for label, *_ in CONTACTS]
        x = (W - sum(widths) - 3 * 17 - 2 * 16) / 2 - 14
        for (label, uri, icon), tw in zip(CONTACTS, widths):
            txt(c, label, x + 17, FY + 20.5, 8.2, 'Regular', SAPPHIRE_700)
            ICONS.append((c.getPageNumber(), icon, (x, FY + 18, x + 12, FY + 30)))
            c.linkURL(uri, (x - 2, H - (FY + 34), x + 17 + tw + 2, H - (FY + 15)), relative=0, thickness=0)
            x += 17 + tw + 16
        txt(c, NOTES[c.getPageNumber()], L, FY - 15, 7.5, 'Regular', SAPPHIRE_700)
        c.restoreState()

    styles = make_styles()
    pdf_path = OUT / 'Rating_Scale_Preview.pdf'
    doc = BaseDocTemplate(str(pdf_path), pagesize=A4, title='IISRI rating scale preview',
                          author='Cyberrank', subject='Appendix B component preview')
    frame = Frame(L, H - CONTENT_BOTTOM, R - L, CONTENT_BOTTOM - CONTENT_TOP, 0, 0, 0, 0, id='body')
    doc.addPageTemplates([PageTemplate('content', [frame], onPage=chrome)])

    # Self-check: every grade and both no-grade states fit one page, in this frame and in the
    # stricter 693.9 pt frame (content top 80 pt); contradictory ratings are rejected.
    states = [{'grade': g, 'state': 'assessed'} for g in GRADES] + [{'grade': None, 'state': s} for s in STATE_TEXT]
    for height in (frame._height, CONTENT_BOTTOM - 80):
        for r in states:
            used = sum(f.wrap(frame._width, height)[1] for f in build_rating_scale(r, styles))
            assert used <= height, (r, used, height)
    for bad in ({}, {'state': 'assessed', 'grade': None}, {'state': 'assessed', 'grade': 'bb'},
                {'state': 'unavailable', 'grade': 'BB'}, {'state': 'pending', 'grade': None},
                {'state': 'unavailable', 'grade': None, 'state_reason': 42}):
        try:
            build_rating_scale(bad, styles)
        except ValueError:
            continue
        raise AssertionError(f'accepted invalid rating {bad}')

    story = build_rating_scale({'grade': 'BB', 'state': 'assessed', 'state_reason': None}, styles)
    story += [PageBreak()]
    story += build_rating_scale({'grade': None, 'state': 'unavailable',
                                 'state_reason': '[Sample reason] The external scan did not return enough '
                                                 'evidence to assign a grade.'}, styles)
    doc.build(story, canvasmaker=NumberedCanvas)

    # Footer icons are SVG: place them with PyMuPDF as the template build does.
    import pymupdf
    pdf = pymupdf.open(pdf_path); cache = {}
    for page, icon, rect in ICONS:
        if icon not in cache:
            svg = pymupdf.open(stream=(ASSETS / 'footer-icons' / icon).read_text().replace('currentColor', SAPPHIRE_700).encode(), filetype='svg')
            cache[icon] = pymupdf.open(stream=svg.convert_to_pdf(), filetype='pdf')
        pdf[page - 1].show_pdf_page(pymupdf.Rect(rect), cache[icon], 0)
    tmp = OUT / '_preview.pdf'
    pdf.save(tmp, garbage=2, deflate=True); pdf.close()
    tmp.replace(pdf_path)
    pdf = pymupdf.open(pdf_path)
    assert pdf.page_count == 2, f'expected 2 pages (one per state), got {pdf.page_count}'
    for i, name in enumerate(('Rating_Scale_Preview_p1_graded.png', 'Rating_Scale_Preview_p2_unavailable.png')):
        pdf[i].get_pixmap(dpi=110).save(OUT / name)
    print('built', pdf_path, file=sys.stderr)
