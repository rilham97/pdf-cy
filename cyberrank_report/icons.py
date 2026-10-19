"""Report icons: Phosphor Icons 2.1.1 (MIT), REGULAR weight only, drawn as vector paths.

Package module (imports theme + qa from cyberrank_report):
    icons.py                         -> cyberrank_report/icons.py
    svg/*.svg + LICENSE-phosphor.txt -> cyberrank_report/assets/phosphor/

Weight: regular. Its 16/256 stroke is 0.63 pt on the 9.9 pt inline box (8.6 pt text),
matching the Poppins Light stem (0.071 em = 0.61 pt); light (0.46 pt) looked thinner
than the text. Never mix weights. Two shapes are drawn here on the same grid and
stroke: the severity signal bars and the half-filled 'partial' ring.

Text equivalent: icons are fill/stroke paths only (no text objects, so pdftotext never
sees '#'). Every *_label helper prints its label as real text beside the icon and keeps
the style's colour (BODY), never white text on a colour fill. icon() and
severity_signal() return the bare graphic for places whose adjacent text already names
it (a heading, a tile title). SeverityIcon / SeverityHead (tables, detail blocks; option B, 2026-10-15)
draw the siren alone over its word in invisible text (render mode 3), named once by components.severity_legend().

Sizing: in *_label helpers the icon scales with the label's font, so table rows keep
their 21 pt / 18 pt (dense) height. Leave size=None in table cells; an explicit size is
for display use (tiles, openers), centres the icon on the cap height and may make the
row taller.
"""
import itertools
import math
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import FILL_NON_ZERO, _renderPath
from reportlab.graphics.svgpath import SvgPath
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Paragraph

from . import qa, theme as T
from .fonts import fallback
from .text import plain, val

SVG_DIR = Path(__file__).resolve().parent / 'assets' / 'phosphor'
GRID, LIVE = 256, 24   # Phosphor viewBox 0 0 256 256; live area 24..232 (circles touch it)
ICON_EM = 1.15         # inline icon box / font size (9.9 pt at 8.6 pt text)
CAP_MID = 0.35         # Poppins cap height is 0.70 em; icons centre on its middle
GAP_EM = 0.4           # visible gap between icon and label (x font size, or icon size / ICON_EM if larger)

# --- colour (theme tokens) -------------------------------------------------------
SEVERITY = T.SEVERITY     # Critical / High / Medium / Low; quantum 'Moderate' shares Medium
# state -> icon colour (theme.STATE accent = theme.status_color; 'findings' orange, 'identified' navy)
STATE_COLOR = {s: v['accent'] for s, v in T.STATE.items()}

# --- registry: key -> Phosphor regular icon (svg/<name>.svg) or a CUSTOM path ------
ICONS = {
    # aspects (keys = section keys)
    'executive_overview': 'gauge',
    'priority_actions': 'list-checks',
    'privacy': 'eye-slash',
    'vulnerabilities': 'bug',
    'certifications': 'certificate',
    'data_leak_history': 'lock-open',
    'fourth_party_vendors': 'tree-structure',
    'credential_exposure': 'key',
    'cloud_infrastructure': 'cloud',
    'ai_risk_governance': 'brain',
    'quantum_security': 'atom',
    'data_sovereignty': 'scales',
    'data_residency': 'map-pin',
    'legal_terms': 'scroll',
    'security_resourcing': 'users-three',
    # states (circle family)
    'findings': 'warning-circle',
    'clear': 'check-circle',
    'not_assessed': 'minus-circle',
    'not_applicable': 'prohibit',
    'unavailable': 'question',
    'partial': 'half-ring',
    'pending_review': 'hourglass-medium',
    'none_identified': 'ring',
    'identified': 'dot-ring',
    # yes / no clauses
    'yes': 'check',
    'no': 'x',
    # quantum algorithm categories + PQC alternative
    'public_key': 'key',
    'symmetric': 'lock-key',
    'hash': 'hash',
    'certificate': 'certificate',
    'pqc': 'shield-check',
}
# Drawn for this report on Phosphor's grid: regular ring (r 88..104) with the right
# half solid (Harvey ball, filled clockwise from 12). One path, hole wound opposite.
CUSTOM = {'half-ring': 'M128,24A104,104,0,0,1,128,232A104,104,0,0,1,128,24ZM128,40A88,88,0,0,0,128,216Z',
          # empty ring (none identified): same ring, both halves open
          'ring': 'M128,24A104,104,0,0,1,128,232A104,104,0,0,1,128,24ZM128,40A88,88,0,0,0,128,216A88,88,0,0,0,128,40Z',
          # identified: the same ring with a solid centre (something is there; neutral)
          'dot-ring': 'M128,24A104,104,0,0,1,128,232A104,104,0,0,1,128,24ZM128,40A88,88,0,0,0,128,216A88,88,0,0,0,128,40Z'
                      'M128,92A36,36,0,0,1,128,164A36,36,0,0,1,128,92Z'}

# --- severity: siren ---------------------------------------------------------------
# scale -> source term -> (label, siren key). Same key = same icon everywhere.
LEVELS = {
    'standard': {'critical': ('Critical', 'critical'), 'high': ('High', 'high'), 'medium': ('Medium', 'medium'),
                 'low': ('Low', 'low'), 'info': ('Informational', 'info'), 'informational': ('Informational', 'info')},
    'quantum': {'high': ('High', 'high'), 'moderate': ('Moderate', 'medium'), 'low': ('Low', 'low')},  # source terms
}
# Rays are cumulative: Medium 2 (sides), High 3 (+ top), Critical 5 (+ horizontals); Low calm (dome only).
RAYS = {'critical': (0, 40, 90, 140, 180), 'high': (40, 90, 140), 'medium': (40, 140), 'low': (), 'info': ()}
SIREN_COLOR = {**SEVERITY, 'info': T.SLATE_400}
SIREN_EM = 1.12          # largest box whose rays, base on the baseline, stay inside 1 em (row height unchanged)
SIREN_PAD = 0.16         # base edge inset (fraction of the box): flush with the text edge like a live area
SIREN_BASE, SIREN_INK = 0.06, 0.94   # base bottom / painted top (incl. ray cap), fraction of the box
SIREN_RIGHT = 0.5 + 0.52 + 0.075 / 2  # tip of Critical's 0° ray incl. round cap: every tier gets this one box,
                                     # so labels align and the 5-ray siren keeps the same gap as the others


def severity_level(level, scale='standard'):
    """(label, siren key) for a source severity term: Critical 5 rays, High 3, Medium/Moderate 2,
    Low none, Informational none in slate. None / '' -> ('Not rated', None); an unknown term
    keeps its own text, gets the not-rated (outline) siren and a qa warning."""
    term = str(val(level) or '').strip()
    if not term:
        return 'Not rated', None
    hit = LEVELS[scale].get(term.lower())
    if hit:
        return hit
    qa.add('severity_term', 'warn', f'unknown {scale} severity "{term}"; printed as given, not rated')
    return term, None


def _siren_layers(key):
    return [('siren', key, SIREN_COLOR[key] if key else T.MUTED)]


def _draw_siren(c, s, key, color):
    """Siren in an s x s box, origin bottom-left (tools/prototypes/severity_siren.py).
    key None: outlined dome + base, no rays (not rated)."""
    cx, by = s * .5, s * SIREN_BASE
    filled = key is not None
    c.setFillColor(color)
    c.setStrokeColor(color)
    c.setLineWidth(max(.5, s * .06))
    c.roundRect(cx - s * .34, by, s * .68, s * .12, s * .03, stroke=int(not filled), fill=int(filled))
    r, p = s * .24, c.beginPath()
    p.moveTo(cx - r, by + s * .12)
    p.lineTo(cx - r, by + s * .30)
    p.arcTo(cx - r, by + s * .30 - r, cx + r, by + s * .30 + r, 180, -180)
    p.lineTo(cx + r, by + s * .12)
    p.close()
    c.drawPath(p, stroke=int(not filled), fill=int(filled))
    c.setLineWidth(max(.6, s * .075))
    c.setLineCap(1)
    hy = by + s * .32
    for a in RAYS.get(key, ()):
        ux, uy = math.cos(math.radians(a)), math.sin(math.radians(a))
        c.line(cx + ux * s * .36, hy + uy * s * .36, cx + ux * s * .52, hy + uy * s * .52)


# --- drawing ------------------------------------------------------------------
@lru_cache(maxsize=None)
def _paths(name):
    """Parsed paths of an icon. Refuses SVGs that would not recolour as one flat fill
    (strokes, transforms, opacity, non-path shapes)."""
    if name in CUSTOM:
        return (SvgPath(CUSTOM[name]),)
    root = ET.parse(SVG_DIR / f'{name}.svg').getroot()
    if root.get('viewBox') != f'0 0 {GRID} {GRID}':
        raise ValueError(f'{name}.svg: unexpected viewBox {root.get("viewBox")}')
    out = []
    for el in root.iter():
        tag = el.tag.rsplit('}', 1)[-1]
        bad = {'stroke', 'transform', 'opacity', 'fill-opacity', 'fill-rule'} & set(el.attrib)
        if bad or tag not in ('svg', 'path'):
            raise ValueError(f'{name}.svg: <{tag}> {sorted(bad)} cannot be recoloured as a flat fill')
        if tag == 'path':
            out.append(SvgPath(el.attrib['d']))
    return tuple(out)


class Icon(Flowable):
    """size x size pt icon drawn straight on the canvas (no Drawing/renderPDF, which
    adds an empty text block per icon). layers: ('path', name, colour) on the y-down
    SVG grid, or ('siren', key, colour) in the y-up box."""

    def __init__(self, layers, size):
        super().__init__()
        self.layers, self.width, self.height = layers, size, size

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c, s = self.canv, self.width / GRID
        for kind, what, color in self.layers:
            c.saveState()
            if kind == 'path':
                c.setFillColor(color)
                c.transform(s, 0, 0, -s, 0, self.width)
                for path in _paths(what):
                    p = c.beginPath()
                    _renderPath(path, (p.moveTo, p.lineTo, p.curveTo, p.close))
                    c.drawPath(p, stroke=0, fill=1, fillMode=FILL_NON_ZERO)
            else:
                _draw_siren(c, self.width, what, color)
            c.restoreState()


def icon(key, size=12.0, color=None):
    """Bare registry icon (Flowable, size x size pt). Colour defaults to the state
    colour for state keys, navy otherwise. Decorative: name it with adjacent text."""
    return Icon([('path', ICONS[key], color or STATE_COLOR.get(key, T.NAVY))], size)


def severity_signal(level, scale='standard', size=12.0):
    """Bare severity siren (Flowable) in the severity colour; not rated = outline, no rays."""
    return Icon(_siren_layers(severity_level(level, scale)[1]), size)


# --- icon + real-text label ---------------------------------------------------
class IconLabel(Flowable):
    """Icon + label Paragraph (wraps with a hanging indent). The icon's live area sits
    flush with the text edge, centred on the first line's cap height (on_baseline:
    standing on the baseline, for the siren). toc=(level, text, key) makes it an
    outline / Contents entry exactly like components.heading. pad / base / ink: the
    icon's side inset, bottom and painted top as fractions of its box."""

    def __init__(self, make_icon, text, style, size=None, on_baseline=False, em=ICON_EM, toc=None,
                 pad=LIVE / GRID, base=LIVE / GRID, ink=1 - LIVE / GRID, right=None):
        super().__init__()
        st = style
        self.text, self._fs, self._font = str(plain(text)), st.fontSize, st.fontName
        self.size = size or round(st.fontSize * em, 2)
        self._pad, self._ink = self.size * pad, self.size * ink
        self._dy = -self.size * base if on_baseline else CAP_MID * st.fontSize - self.size / 2  # icon bottom - baseline
        # gap grows with a display-size icon (tile head), not only with the text
        # right: painted right edge as a fraction of the box when it passes the live area (siren rays)
        edge = self.size * right - self._pad if right else self.size - 2 * self._pad
        self._indent = edge + GAP_EM * max(st.fontSize, self.size / ICON_EM)
        self._p = Paragraph(fallback(escape(self.text)), st.clone(st.name + '_icon', leftIndent=self._indent))
        self._icon = make_icon(self.size)
        self.spaceBefore, self.spaceAfter = st.spaceBefore, st.spaceAfter
        self.keepWithNext = getattr(st, 'keepWithNext', 0)
        if toc:
            self._toc = toc

    def wrap(self, aw, ah):
        self.width = min(aw, self._indent + stringWidth(self.text, self._font, self._fs) + 0.5)
        _, self._ph = self._p.wrap(self.width, ah)
        self._top = max(0.0, self._dy + self._ink - self._fs)   # icon taller than the first line
        self.height = self._top + max(self._ph, self._fs - self._dy)
        return self.width, self.height

    def draw(self):
        y_p = self.height - self._top - self._ph
        self._p.drawOn(self.canv, 0, y_p)
        baseline = y_p + self._ph - self._fs   # RL: first baseline is fontSize below the top
        self._icon.drawOn(self.canv, -self._pad, baseline + self._dy)

    def minWidth(self):
        return self._indent + max(stringWidth(w, self._font, self._fs) for w in self.text.split() or [''])


def _style(dense, style):
    return style or T.STYLES['dense' if dense else 'cell']


def icon_label(key, text, color=None, dense=False, style=None, size=None):
    """'[icon] text' for running content (default style: table cell 8.6/12, dense 7.8/11).
    Category icons pass a structure colour; a status passes T.status_color(<key>) or uses status_label."""
    return IconLabel(lambda s: icon(key, s, color), text, _style(dense, style), size)


def status_label(key, text, status, dense=False, style=None, size=None):
    """'[icon] text' for a status / result: icon `key` in T.status_color(status), label BODY."""
    return icon_label(key, text, T.status_color(status), dense, style, size)


def severity_label(level, scale='standard', dense=False, label=None, style=None, size=None):
    """'[siren] High'. label overrides the printed text; quantum scale prints High /
    Moderate / Low. Table cells: keep size=None (siren base on the baseline, row height
    unchanged)."""
    text, key = severity_level(level, scale)
    return IconLabel(lambda s: Icon(_siren_layers(key), s), label or text, _style(dense, style), size,
                     on_baseline=size is None, em=SIREN_EM, pad=SIREN_PAD, base=SIREN_BASE, ink=SIREN_INK,
                     right=SIREN_RIGHT)


def state_label(state, dense=False, style=None, size=None, label=None):
    """'[state icon] No findings' -- theme.STATE label unless overridden."""
    state = val(state)
    if state not in T.STATE:
        return status_label('not_assessed', label or 'State not recorded', 'not_recorded', dense, style, size)
    return icon_label(state, label or T.STATE[state]['label'], None, dense, style, size)


def yes_no_label(flag, text=None, dense=False, style=None, size=None, status=None):
    """Check / x + 'Yes' / 'No' (or text). Status colour: yes (present, passed) good, no bad;
    `status` overrides where the answer is not a judgement (e.g. 'not_compared').
    None -> 'Not recorded' (minus-circle), never a silent 'No'."""
    if flag is None:
        return status_label('not_assessed', text or 'Not recorded', status or 'not_recorded', dense, style, size)
    return status_label('yes' if flag else 'no', text or ('Yes' if flag else 'No'),
                        status or ('yes' if flag else 'no'), dense, style, size)


def hidden_text(c, text, x, baseline, width, font, size):
    """`text` in text render mode 3 (invisible), squeezed horizontally into `width`: copy, search,
    pdftotext and screen readers get the word, the page shows only what is drawn over it, and the
    word never runs into the next cell's text."""
    t = c.beginText(x, baseline)
    t.setTextRenderMode(3)
    t.setFont(font, size)
    t.setHorizScale(100 * min(1, width / max(stringWidth(text, font, size), 0.01)))
    t.textOut(text)
    c.drawText(t)


class SeverityIcon(Flowable):
    """Siren alone (table cells, detail blocks; option B approved 2026-10-15), standing on the first text
    baseline of the cell like severity_label's siren. Its severity word is drawn first, invisible
    (hidden_text) on the same baseline, so search and pdftotext still find 'High'. The legend
    (components.severity_legend) names the sirens once per table."""

    def __init__(self, level, scale='standard', style=None):
        super().__init__()
        st = style or T.STYLES['cell']
        self.text, self.key = severity_level(level, scale)
        self._font, self._fs, self._lead = st.fontName, st.fontSize, st.leading
        self.size = round(self._fs * SIREN_EM, 2)

    def wrap(self, aw, ah):
        self.width, self.height = self.minWidth(), self._lead
        return self.width, self.height

    def minWidth(self):
        return self.size * (SIREN_RIGHT - SIREN_PAD)

    def draw(self):
        base = self.height - self._fs
        hidden_text(self.canv, self.text, 0, base, self.width, self._font, self._fs)
        Icon(_siren_layers(self.key), self.size).drawOn(self.canv, -self.size * SIREN_PAD,
                                                         base - self.size * SIREN_BASE)


def severity_cell(level, scale='standard', style=None):
    """Icon-only siren for a rated level; an unrated / unknown term keeps its visible label
    (an outline siren alone would say nothing)."""
    if severity_level(level, scale)[1] is None:
        return severity_label(level, scale, style=style)
    return SeverityIcon(level, scale, style)


class SeverityHead(Flowable):
    """Count-column header: siren alone, right-aligned with the numbers below, its severity word
    invisible under it (hidden_text) for search / pdftotext. Named by the table's legend."""

    def __init__(self, level, scale='standard', style=None, size=None):
        super().__init__()
        st = style or T.STYLES['dense_head_num']
        self.text, key = severity_level(level, scale)
        self._font, self._fs = st.fontName, st.fontSize
        self.size = size or round(st.fontSize * SIREN_EM, 2)
        self._icon = Icon(_siren_layers(key), self.size)

    def wrap(self, aw, ah):
        self.width, self.height = aw, max(self._fs, self.size * SIREN_INK)
        return self.width, self.height

    def draw(self):
        x = self.width - self.size * SIREN_RIGHT          # painted right edge flush with the numbers
        base = self.size * SIREN_BASE
        hidden_text(self.canv, self.text, x + self.size * SIREN_PAD, 0, self.size * (SIREN_RIGHT - SIREN_PAD),
                    self._font, self._fs)
        self._icon.drawOn(self.canv, x, 0 - base)

    def minWidth(self):
        return self.size * SIREN_RIGHT


_KEYS = itertools.count(1)


def icon_heading(key, text, level=1, anchor=None, style=None, toc=True, size=20.0, color=None):
    """Heading with an aspect icon (section opener). Like components.heading: H1/H2
    register an outline entry + Contents anchor (anchor = the section key)."""
    st = style or T.STYLES[{1: 'h1', 2: 'h2', 3: 'h3'}[level]]
    entry = (level - 1, str(text), anchor or f'ih{next(_KEYS)}') if level in (1, 2) and toc else None
    return IconLabel(lambda s: icon(key, s, color), text, st, size, toc=entry)


# --- self-check: python -m cyberrank_report.icons -----------------------------------
def _contrast(c):
    lin = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c.rgb()]
    return 1.05 / (0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2] + 0.05)


def _selftest():
    from io import BytesIO

    from reportlab.pdfgen.canvas import Canvas

    from . import components as C
    for key in ICONS:
        assert _paths(ICONS[key]), key
    for c in list(SEVERITY.values()) + list(STATE_COLOR.values()) + [T.MUTED]:
        assert _contrast(c) >= 3, (c, _contrast(c))
    n_qa = len(qa.ISSUES)
    assert severity_level('MODERATE', 'quantum') == ('Moderate', 'medium')
    assert severity_level(None) == severity_level(' ') == ('Not rated', None) and len(qa.ISSUES) == n_qa
    assert severity_level('Severe') == ('Severe', None) and len(qa.ISSUES) == n_qa + 1
    del qa.ISSUES[n_qa:]
    cv = Canvas(BytesIO(), pageCompression=0)
    for key in ICONS:
        icon(key, 10).drawOn(cv, 0, 0)
    for lv in ('critical', 'info', None):
        severity_signal(lv, size=10).drawOn(cv, 0, 0)
    cv.showPage()
    assert cv.getpdfdata().count(b' Tf ') <= 1, 'icons must not emit text'   # <= 1: canvas page setup
    for dense, row_h in ((False, 21.0), (True, 18.0)):   # labels keep compact_table row heights
        cells = [severity_label('high', dense=dense), severity_label(None, dense=dense),
                 state_label('partial', dense), yes_no_label(None, dense=dense)]
        t = C.compact_table(['a', 'b', 'c', 'd'], [cells], dense=dense, widths=[110] * 4)
        t.wrap(440, 800)
        assert all(abs(h - row_h) < 0.01 for h in t._rowHeights[1:]), (dense, t._rowHeights)
    return {k: round(_contrast(c), 2) for k, c in SEVERITY.items()}


if __name__ == '__main__':
    print('ok', len(ICONS), 'icons; contrast on white', _selftest())
