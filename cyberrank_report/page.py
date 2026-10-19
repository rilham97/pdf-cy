"""Document template: cover / interior / locked pages, header, footer, watermark,
'Page x of y', outline + named destinations. Ported from the approved template
(build_template.py / drawing_helpers.py); no NumberedCanvas (breaks links).
"""
import re
import struct
import unicodedata
from functools import cache
from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import FILL_NON_ZERO, Drawing, Group
from reportlab.graphics.svgpath import SvgPath
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFontFile
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, IndexingFlowable, KeepTogether, LayoutError,
                                NextPageTemplate, PageBreak, PageBreakIfNotEmpty, PageTemplate, Paragraph, Table)
from reportlab.platypus.doctemplate import _ktAllow

from . import components as C
from . import motif
from . import qa
from . import theme as T
from .fonts import FONT_DIR, report_missing

ASSETS = Path(__file__).resolve().parent / 'assets'
LOGO = ASSETS / 'Cyberrank-logo.png'
CONTACTS = [  # verified against cyberrank.ai footer, 02 Oct 2026 (template)
    ('cyberrank.ai', 'https://www.cyberrank.ai/', 'globe'),
    ('support@cyberrank.ai', 'mailto:support@cyberrank.ai', 'envelope'),
    ('LinkedIn', 'https://www.linkedin.com/company/105646816', 'linkedin'),
]
ELLIPSIS = '…'
HEADER_PREFIX = 'Cyber Risk Report for '
TITLE_X = 196.0


# --- identity -----------------------------------------------------------------
def identity_from_report(report):
    """Display identity for cover/header. Reads only identity + snapshot."""
    ident = report.get('identity') or {}
    snap = report.get('snapshot') or {}
    issuer = ident.get('issuer') or {}
    logo = (ident.get('logo') or {}).get('value')
    return {
        'org': ident.get('organisation_name') or 'Organisation name not available',
        'domain': ident.get('domain') or '',
        'title': ident.get('report_title') or 'Cyber Risk Report',
        'assessment_date': C.fmt_date(snap.get('assessed_at')),
        'generated_date': C.fmt_date(snap.get('generated_at')),
        'issuer': issuer.get('organisation_name'),
        'issuer_reason': C.reason_text(issuer) if not issuer.get('organisation_name') else None,
        'logo': logo if logo and Path(str(logo)).is_file() else None,
    }


# --- drawing primitives (top-down y, as in the template) ----------------------
def _rect(c, x, top, w, h, color):
    c.setFillColor(color)
    c.rect(x, T.PAGE_H - top - h, w, h, fill=1, stroke=0)


def _txt(c, text, x, top, size, font, color, align='left'):
    """Template convention: baseline = top + 0.82 * size."""
    c.setFillColor(color)
    c.setFont(font, size)
    y = T.PAGE_H - top - size * 0.82
    report_missing(text, 'page header / cover', font)      # canvas strings get no per-character fallback
    {'right': c.drawRightString, 'center': c.drawCentredString}.get(align, c.drawString)(x, y, text)


def _clusters(text):
    """Keep combining marks / ZWJ sequences with their base character."""
    groups = []
    for ch in text:
        cp = ord(ch)
        joins = unicodedata.combining(ch) or 0xFE00 <= cp <= 0xFE0F or 0x1F3FB <= cp <= 0x1F3FF
        if groups and (joins or ch == '‍' or groups[-1].endswith('‍')):
            groups[-1] += ch
        else:
            groups.append(ch)
    return groups


def ellipsize(name, width, font=T.MEDIUM, size=10.0):
    """Longest width-safe prefix + ellipsis; prefers a word boundary when that
    keeps >= 60% of the characters. Source data is never modified."""
    measure = lambda s: stringWidth(s, font, size)
    limit = width - 0.05
    if measure(name) <= limit:
        return name
    cl = _clusters(name)
    lo, hi = 0, len(cl)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if measure(''.join(cl[:mid]).rstrip() + ELLIPSIS) <= limit:
            lo = mid
        else:
            hi = mid - 1
    cut = ''.join(cl[:lo])
    sp = cut.rstrip().rfind(' ')
    if sp > 0 and sp >= 0.6 * len(cut):
        cut = cut[:sp]
    return cut.rstrip(' ,;:-–') + ELLIPSIS


# --- watermark: glyph outlines as paths (stays out of the text layer) --------
def _glyph_contours(data, glyf, loca, gid):
    a, b = glyf + loca[gid], glyf + loca[gid + 1]
    if a == b:
        return []
    n = struct.unpack_from('>h', data, a)[0]
    if n < 0:
        raise ValueError('composite glyph not supported')
    p = a + 10
    ends = struct.unpack_from(f'>{n}H', data, p)
    p += 2 * n
    p += 2 + struct.unpack_from('>H', data, p)[0]
    flags = []
    while len(flags) <= ends[-1]:
        f = data[p]
        p += 1
        flags.append(f)
        if f & 8:
            flags += [f] * data[p]
            p += 1

    def coords(short, same):
        nonlocal p
        v, out = 0, []
        for f in flags:
            if f & short:
                v += data[p] if f & same else -data[p]
                p += 1
            elif not f & same:
                v += struct.unpack_from('>h', data, p)[0]
                p += 2
            out.append(v)
        return out

    xs, ys = coords(2, 16), coords(4, 32)
    out, s = [], 0
    for e in ends:
        out.append([(xs[i], ys[i], flags[i] & 1) for i in range(s, e + 1)])
        s = e + 1
    return out


@cache
def _watermark_geometry(text='CYBERRANK', size=26.0, tracking=1.0):
    f = TTFontFile(str(FONT_DIR / 'Poppins-SemiBold.ttf'))
    glyf, _ = f.get_table_pos('glyf')
    k = size / f.unitsPerEm
    contours, cursor = [], 0.0
    for ch in text:
        gid = f.charToGlyph[ord(ch)]
        for pts in _glyph_contours(f._ttf_data, glyf, f.glyphPos, gid):
            contours.append([(cursor + x * k, y * k, on) for x, y, on in pts])
        cursor += f.hmetrics[gid][0] * k + tracking
    on = [(x, y) for c in contours for x, y, o in c if o]   # TrueType puts on-curve points at extrema
    x0, x1 = min(x for x, _ in on), max(x for x, _ in on)
    center = (T.HEADER_H + T.FOOTER_Y) / 2
    return contours, center - (x0 + x1) / 2


def _add_contour(path, pts):
    mid = lambda a, b: ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 1)
    i0 = next((i for i, p in enumerate(pts) if p[2]), None)
    if i0 is None:
        start, seq = mid(pts[-1], pts[0]), pts
    else:
        pts = pts[i0:] + pts[:i0]
        start, seq = pts[0], pts[1:]
    path.moveTo(start[0], start[1])
    cur, ctrl = start, None

    def quad(p0, c, p1):
        path.curveTo(p0[0] + 2 / 3 * (c[0] - p0[0]), p0[1] + 2 / 3 * (c[1] - p0[1]),
                     p1[0] + 2 / 3 * (c[0] - p1[0]), p1[1] + 2 / 3 * (c[1] - p1[1]), p1[0], p1[1])

    for p in list(seq) + [start]:
        if p[2]:
            quad(cur, ctrl, p) if ctrl else path.lineTo(p[0], p[1])
            cur, ctrl = p, None
        else:
            if ctrl:
                m = mid(ctrl, p)
                quad(cur, ctrl, m)
                cur = m
            ctrl = p
    path.close()


def draw_watermark(c):
    """'CYBERRANK' Poppins SemiBold 26, stroke-only 0.9 pt #C8D4E1, tracking 1,
    rotated -90 at x=10, visually centred between header rule and footer."""
    contours, origin_top = _watermark_geometry()
    c.saveState()
    c.translate(10, T.PAGE_H - origin_top)
    c.rotate(-90)
    path = c.beginPath()
    for pts in contours:
        _add_contour(path, pts)
    c.setStrokeColor(T.WATERMARK)
    c.setLineWidth(0.9)
    c.drawPath(path, stroke=1, fill=0)
    c.restoreState()


# --- icons (Bootstrap SVG path -> vector, recoloured) -------------------------
@cache
def _icon_drawing(name, size=12.0, color=T.NAVY):
    d = re.search(r'\sd="([^"]+)"', (ASSETS / 'icons' / f'{name}.svg').read_text()).group(1)
    s = size / 16
    g = Group(SvgPath(d, fillColor=color, strokeColor=None, strokeWidth=0, fillMode=FILL_NON_ZERO),
              transform=(s, 0, 0, -s, 0, size))
    drawing = Drawing(size, size)
    drawing.add(g)
    return drawing


def draw_background_motif(canvas, doc):
    """Bottom supply-chain watermark (interior pages), under all other marks; one Form XObject.
    Approved to run behind body text and tables: every mark above FRAME_BOTTOM is lighter
    than the #D9DFE6 hairline (motif.self_check). Layout QA ignores it (motif.form_top)."""
    motif.draw_interior_motif(canvas)


# --- header / footer ----------------------------------------------------------
def draw_header(c, ident):
    c.drawImage(ImageReader(str(LOGO)), T.L, T.PAGE_H - 8 - 32, width=128, height=32, mask='auto')
    a_txt, g_txt = f'Assessment  {ident["assessment_date"]}', f'Generated  {ident["generated_date"]}'
    date_left = min(T.R - stringWidth(a_txt, T.MEDIUM, 7.6), T.R - stringWidth(g_txt, T.REGULAR, 7.6))
    title_w = date_left - 10 - TITLE_X
    org_w = title_w - stringWidth(HEADER_PREFIX, T.MEDIUM, 10)
    _txt(c, HEADER_PREFIX + ellipsize(ident['org'], org_w), TITLE_X, 11, 10, T.MEDIUM, T.NAVY)
    dom, dsize = ident['domain'], 7.8
    while dom and stringWidth(dom, T.REGULAR, dsize) > title_w:   # never truncate the domain
        dsize -= 0.1
    if dom:
        _txt(c, dom, TITLE_X, 29 + (7.8 - dsize) * 0.82, dsize, T.REGULAR, T.MUTED)
    _txt(c, a_txt, T.R, 13, 7.6, T.MEDIUM, T.NAVY, 'right')
    _txt(c, g_txt, T.R, 29, 7.6, T.REGULAR, T.MUTED, 'right')
    split = T.R - 116
    c.setLineWidth(2)
    c.setStrokeColor(T.SAPPHIRE)
    c.line(T.L, T.PAGE_H - T.HEADER_H, split, T.PAGE_H - T.HEADER_H)
    c.setStrokeColor(T.AMBER)
    c.line(split, T.PAGE_H - T.HEADER_H, T.R, T.PAGE_H - T.HEADER_H)


def draw_footer(c, page=None, total=None):
    """Footer band + contacts; folio only when page is given (cover has none)."""
    fy = T.FOOTER_Y
    _rect(c, 0, fy, T.PAGE_W, T.FOOTER_H, T.FOOTER_BG)
    _rect(c, 0, fy - 1, T.PAGE_W - 76, 2, T.SAPPHIRE)
    _rect(c, T.PAGE_W - 76, fy - 1, 76, 2, T.AMBER)
    size, icon, igap, gap = 8.2, 12.0, 5.0, 16.0
    widths = [stringWidth(lbl, T.REGULAR, size) for lbl, _, _ in CONTACTS]
    x = (T.PAGE_W - (sum(widths) + 3 * (icon + igap) + 2 * gap)) / 2 - 14
    for (label, uri, name), tw in zip(CONTACTS, widths):
        renderPDF.draw(_icon_drawing(name), c, x, T.PAGE_H - (fy + 18) - icon)
        _txt(c, label, x + icon + igap, fy + 20.5, size, T.REGULAR, T.NAVY)
        c.linkURL(uri, (x - 2, T.PAGE_H - (fy + 34), x + icon + igap + tw + 2, T.PAGE_H - (fy + 15)),
                  relative=0, thickness=0)
        x += icon + igap + tw + gap
    if page:
        _folio(c, page, total)


def _folio(c, page, total):
    _txt(c, f'Page {page} of {total or page}', T.R, T.FOOTER_Y + 21, 8, T.MEDIUM, T.NAVY, 'right')


# --- cover (Cover 02 Sapphire Field) ------------------------------------------
def draw_cover(c, ident):
    _rect(c, 0, 0, T.PAGE_W, T.PAGE_H, T.WHITE)
    c.drawImage(ImageReader(str(LOGO)), T.L, T.PAGE_H - 33 - 46, width=184, height=46, mask='auto')
    _rect(c, 0, 115, T.PAGE_W, 389, T.NAVY)
    _rect(c, T.L, 160, 53, 4, T.AMBER)
    _txt(c, 'Cyber Risk', T.L, 205, 54, T.MEDIUM, T.WHITE)
    _txt(c, 'Report', T.L, 271, 54, T.MEDIUM, T.WHITE)
    for x, label, value in [(T.L, 'Assessment date', ident['assessment_date']),
                            (T.L + 297, 'Generated date', ident['generated_date'])]:
        _txt(c, label, x, 415, 8.6, T.REGULAR, T.COVER_LABEL)
        _txt(c, value, x, 436, 11, T.MEDIUM, T.WHITE)
    # REPORT FOR -- name never truncated: step the size down, then let it wrap.
    _txt(c, 'REPORT FOR', T.L, 580, 8.2, T.MEDIUM, T.MUTED)
    x = T.L
    if ident.get('logo'):
        c.drawImage(ImageReader(ident['logo']), T.L, T.PAGE_H - 609 - 30, width=30, height=30,
                    mask='auto', preserveAspectRatio=True)
        x = T.L + 43
    width, box_h = T.L + 297 - 14 - x, 740 - 606
    for size in (28, 24, 20, 17):
        name = C.P(ident['org'], 'h1', fontSize=size, leading=size * 1.15, spaceAfter=7)
        if len(name.breakLines(width).lines) <= 2:
            break
    parts = [name] + ([C.TechText(ident['domain'], C.STYLES['tech'].clone('cover_domain', fontName=T.LIGHT, fontSize=10,
                                                                          leading=13, textColor=T.MUTED))]
                      if ident['domain'] else [])
    _box(c, parts, x, 633.96 - size, width, box_h, 'cover organisation')
    hub_x = x + min(width, stringWidth(ident['org'], T.MEDIUM, size)) / 2   # motif 'You' under the name
    # ISSUED BY -- unknown issuer prints a reason, never a blank.
    ix = T.L + 297
    _txt(c, 'ISSUED BY', ix, 580, 8.2, T.MEDIUM, T.MUTED)
    if ident.get('issuer'):
        parts = [C.P(ident['issuer'], 'h1', fontSize=24, leading=27.6, spaceAfter=6),
                 C.P('Assessment organization\nvia Cyberrank', 'note_flush', fontSize=8.5, leading=14)]
        _box(c, parts, ix, 612 + 24 * 0.82 - 24, T.R - ix, 130, 'cover issuer')
    else:
        parts = [C.P('Not available', 'h1', fontSize=16, leading=19, textColor=T.MUTED, spaceAfter=5),
                 C.P(C.sentence(ident.get('issuer_reason') or 'reason not recorded'), 'note_flush',
                     fontSize=8.5, leading=12.5)]
        _box(c, parts, ix, 633.96 - 16, T.R - ix, 130, 'cover issuer')
    motif.draw_cover_motif(c, hub_x)
    draw_footer(c)


def _box(c, flowables, x, top, w, h, name):
    """Fixed box: overflow is a recorded QA error (then shrunk so the page still renders)."""
    box = qa.fixed_box(flowables, w, h, name)
    try:
        _, bh = box.wrapOn(c, w, h)
    except LayoutError as e:
        qa.record_layout_error(e, name)
        box = qa.fixed_box(flowables, w, h, name)
        box.mode = 'shrink'
        _, bh = box.wrapOn(c, w, h)
    box.drawOn(c, x, T.PAGE_H - top - bh)


# --- flowables ----------------------------------------------------------------
class _PassState(IndexingFlowable):
    """Zero-size page-count/anchor tracker (the PageCount role). Asks multiBuild for another pass until the page
    total and every anchor page (contents, register pointers) are stable."""

    def __init__(self, doc):
        super().__init__()
        self.doc = doc
        self.width = self.height = 0
        self._prev = self._cur = None

    def wrap(self, aw, ah):
        return 0, 0

    def draw(self):
        pass

    def beforeBuild(self):
        self._prev = (self.doc.page_total, dict(self.doc.anchors_prev))
        self.doc.anchors = {}

    def afterBuild(self):
        self.doc.page_total = self.doc.page
        self.doc.anchors_prev = dict(self.doc.anchors)
        self._cur = (self.doc.page_total, self.doc.anchors_prev)

    def isSatisfied(self):
        return self._prev == self._cur


class _LockedMark(Flowable):
    def __init__(self, path, index):
        super().__init__()
        self._locked = (str(path), index)
        self.width = self.height = 0

    def wrap(self, aw, ah):
        return 0, 0

    def draw(self):
        pass


def locked_page(path, index=0, outline=None):
    """Flowables reserving one page that is later replaced by page `index` of the
    external PDF `path`, fully unchanged: no mask, no header/footer/watermark/motif, no
    kit folio (its own folio stays). Counts in 'Page x of y' and in the Contents."""
    out = [NextPageTemplate('locked'), PageBreakIfNotEmpty()]
    if outline:
        out.append(C.Anchor(f'locked:{Path(path).name}:{index}', outline=outline))
    return out + [_LockedMark(path, index), NextPageTemplate('interior'), PageBreak()]


def _paragraphs(f):
    """Paragraphs a drawn flowable holds (table cells, cards, chips), for word_split."""
    if isinstance(f, (list, tuple)):
        for x in f:
            yield from _paragraphs(x)
    elif isinstance(f, Paragraph):
        yield f
    elif isinstance(f, Table):
        yield from _paragraphs(f._cellvalues)
    else:
        for a in ('_p', '_t', '_content'):
            if hasattr(f, a):
                yield from _paragraphs(getattr(f, a))


def _split_words(p):
    """Words RL broke by character (splitLongWords fallback) in paragraph p."""
    st = p.style
    avail = getattr(p, 'width', 0) - st.leftIndent - st.rightIndent
    words = [w for w in p.getPlainText().split() if stringWidth(w, st.fontName, st.fontSize) > avail]
    return ', '.join(words) or p.getPlainText()[:80]


def _breakable_token(w):
    """URL, host, hash or address: no prose word, so a character break loses no meaning."""
    w = re.sub(r'^\(\d+\)', '', w).lstrip('+(').rstrip('),;')   # '+<hash>' (vs apex), '(22)https://…'
    return ('://' in w or bool(re.fullmatch(r'[0-9a-fA-F:_x-]{16,}', w))
            or (len(w) > 16 and any(ch in w for ch in '/.@_:')))


def cover_flowables():
    """Story start: the cover page (drawn by its page template), then interior pages."""
    return [C.Anchor('cover', outline='Cover'), NextPageTemplate('interior'), PageBreak()]


class ReportDoc(BaseDocTemplate):
    """A4 report. Use doc.render(story) (multiBuild + locked page stamping)."""

    def __init__(self, filename, identity, *, subject=None, **kw):
        self.identity = identity
        self.page_total = None
        self.anchors, self.anchors_prev = {}, {}
        self.locked, self.table_parts, self.refs = [], [], set()
        super().__init__(
            str(filename), pagesize=(T.PAGE_W, T.PAGE_H),
            leftMargin=T.L, rightMargin=T.L, topMargin=T.FRAME_TOP, bottomMargin=T.PAGE_H - T.FRAME_BOTTOM,
            title=f'{identity["title"]} — {identity["org"]}' + (f' ({identity["domain"]})' if identity['domain'] else ''),
            author='Cyberrank', creator='Cyberrank report generator (ReportLab)',
            subject=subject or f'External cyber risk assessment of {identity["org"]}, {identity["assessment_date"]}',
            lang='en', **kw)
        self.keepTogetherClass = C.Keep        # keepWithNext groups use the same rules
        frame = lambda: Frame(T.L, T.PAGE_H - T.FRAME_BOTTOM, T.CW, T.FRAME_H, 0, 0, 0, 0, id='body')
        self.addPageTemplates([
            PageTemplate('cover', [frame()], onPage=self._on_cover),
            PageTemplate('interior', [frame()], onPage=self._on_interior),
            PageTemplate('locked', [frame()], onPage=lambda c, d: None),
        ])

    def _on_cover(self, c, doc):
        draw_cover(c, self.identity)

    def _on_interior(self, c, doc):
        draw_background_motif(c, doc)
        draw_watermark(c)
        draw_header(c, self.identity)
        draw_footer(c, self.page, self.page_total)

    def beforeDocument(self):
        self.locked, self.table_parts, self.refs, self.word_splits = [], [], set(), []
        self.last_heading = None

    def handle_keepWithNext(self, flowables):
        """RL never puts a following KeepTogether into a keepWithNext group (_ktAllow
        rejects containers), so a heading before keep(...) could end a page alone.
        Fold the heading run into that group instead."""
        i = 0
        while i < len(flowables) and flowables[i].getKeepWithNext() and _ktAllow(flowables[i]):
            i += 1
        if not (i and i < len(flowables) and isinstance(flowables[i], KeepTogether)):
            return super().handle_keepWithNext(flowables)
        head, mbe = flowables[:i], getattr(self, '_multiBuildEdits', None)
        for f in head:          # as RL does: no regrouping now, restored for the next pass
            if mbe:
                mbe((setattr, f, 'keepWithNext', f.keepWithNext) if 'keepWithNext' in f.__dict__
                    else (delattr, f, 'keepWithNext'))
            f.__dict__['keepWithNext'] = 0
        flowables[:i + 1] = [self.keepTogetherClass(head + list(flowables[i]._content))]

    def afterFlowable(self, f):
        if getattr(f, '_locked', None):
            self.locked.append((self.page, *f._locked))
        self.word_splits += [(self.page, _split_words(p)) for p in _paragraphs(f)
                             if getattr(p, '_splitLongWordCount', 0)]
        toc = getattr(f, '_toc', None)
        st = getattr(f, 'style', None)
        if toc and isinstance(f, Flowable) and not getattr(f, '_anchor', None):
            self.last_heading = toc[1]
        elif isinstance(f, Paragraph) and st.fontName == T.MEDIUM and st.fontSize >= 10.5 and st.keepWithNext:
            self.last_heading = f.getPlainText()      # H3: plain heading, caption title for a split table
        key = toc[2] if toc else getattr(f, '_anchor', None)
        if not key:
            return
        top = min(T.PAGE_H, self.frame._y + f.getSpaceAfter() + getattr(f, 'height', 0) + 6)
        self.canv.bookmarkHorizontalAbsolute(key, top)
        self.anchors[key] = self.page
        if toc:
            self.canv.addOutlineEntry(toc[1], key, level=toc[0])

    def render(self, story):
        """multiBuild until page refs settle, then stamp locked external pages."""
        # _PassState reads doc.page after each pass, so its position does not matter;
        # first (not last) so it can never open an empty trailing page.
        self.multiBuild([_PassState(self)] + list(story))
        for key in sorted(self.refs - set(self.anchors)):
            qa.add('unresolved_reference', 'warn', f'no anchor for {key}; printed as pending')
        for page, words in sorted(set(self.word_splits)):
            # URLs / hashes / addresses are character-breakable by design: a warning, not an error
            tech = all(_breakable_token(w) for w in words.split(', '))
            qa.add('word_split', 'warn' if tech else 'error',
                   f'split mid-word by character ({"technical token" if tech else "column too narrow"}): {words}',
                   page=page)
        if self.locked:
            stamp_locked_pages(self.filename, self.locked)
        return self.page_total


def stamp_locked_pages(pdf_path, locked):
    """Draw each external page 1:1 (vector, as a form XObject) onto its blank reserved page.
    locked: (page_no, path, index)."""
    import pymupdf as fitz
    pdf = fitz.open(pdf_path)
    for page_no, path, index in locked:
        src = fitz.open(path)
        target = pdf[page_no - 1]
        r = src[index].rect      # the page keeps the source's own box: drawn 1:1 at 0,0, not centred on A4
        target.set_mediabox(fitz.Rect(0, 0, r.width, r.height))
        target.show_pdf_page(target.rect, src, index)
        for link in src[index].get_links():
            if link.get('kind') == fitz.LINK_URI:
                target.insert_link({'kind': fitz.LINK_URI, 'from': link['from'], 'uri': link['uri']})
        src.close()
    tmp = Path(pdf_path).with_suffix('.stamp.pdf')
    pdf.save(tmp, garbage=3, deflate=True)
    pdf.close()
    tmp.replace(pdf_path)
