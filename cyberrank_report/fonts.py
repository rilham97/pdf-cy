"""Register the report fonts once per process: Poppins (text), JetBrains Mono (technical tokens) and the
glyph-fallback chain Noto Sans Math -> Noto Sans Symbols 2 -> Noto Sans SC (CJK, subset per build).
All SIL OFL 1.1; licence files sit next to the fonts in assets/fonts."""
import re
from functools import lru_cache
from html import unescape
from io import BytesIO
from pathlib import Path

from reportlab import rl_config
from reportlab.graphics import shapes
from reportlab.platypus import tables
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = Path(__file__).resolve().parent / 'assets' / 'fonts'
WEIGHTS = ('Light', 'Regular', 'Medium', 'SemiBold')
MONO = 'JetBrainsMono'
MATH, SYMBOLS, CJK = 'NotoSansMath', 'NotoSansSymbols2', 'NotoSansSC'
CJK_SOURCE = FONT_DIR / 'NotoSansSC-Light.ttf'     # static wght 300 instance of the Noto Sans SC VF


def register():
    if 'Poppins-Light' in pdfmetrics.getRegisteredFontNames():
        return
    for w in WEIGHTS:
        pdfmetrics.registerFont(TTFont(f'Poppins-{w}', str(FONT_DIR / f'Poppins-{w}.ttf')))
    # <b> inside Light text maps to Medium; there is no italic cut, so <i> stays upright.
    pdfmetrics.registerFontFamily('Poppins-Light', normal='Poppins-Light', bold='Poppins-Medium',
                                  italic='Poppins-Light', boldItalic='Poppins-Medium')
    pdfmetrics.registerFontFamily('Poppins-Regular', normal='Poppins-Regular', bold='Poppins-Medium',
                                  italic='Poppins-Regular', boldItalic='Poppins-Medium')
    # Inter: brand face for the document title (cover + running header title), owner decision 2026-10-19
    for w in ('Light', 'Regular', 'Medium'):
        pdfmetrics.registerFont(TTFont(f'Inter-{w}', str(FONT_DIR / f'Inter-{w}.ttf')))
    pdfmetrics.registerFontFamily('Inter-Light', normal='Inter-Light', bold='Inter-Medium',
                                  italic='Inter-Light', boldItalic='Inter-Medium')
    for name, file in ((MONO, 'JetBrainsMono-Regular.ttf'), (MATH, 'NotoSansMath-Regular.ttf'),
                       (SYMBOLS, 'NotoSansSymbols2-Regular.ttf')):
        pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))


register()
# Every default font is embedded Poppins, so no unembedded base-14 font is referenced: the canvas
# start-up font (Helvetica), plain-string table cells (Helvetica) and vector drawings (Times-Roman).
rl_config.canvas_basefontname = 'Poppins-Light'
tables.CellStyle.fontname = 'Poppins-Light'
shapes.STATE_DEFAULTS['fontName'] = 'Poppins-Light'


# --- glyph fallback ---------------------------------------------------------------
def _cmap(name):
    return pdfmetrics.getFont(name).face.charToGlyph


BASE = _cmap('Poppins-Light')          # all Poppins weights share one character set
_CJK_DONE = set()                      # characters in the registered Noto Sans SC subset


@lru_cache(maxsize=1)
def _cjk_source_cmap():
    from fontTools.ttLib import TTFont as FT
    return set(FT(str(CJK_SOURCE), lazy=True).getBestCmap())


def covered(ch, font='Poppins-Light'):
    return ch.isspace() or ord(ch) in (BASE if font.startswith('Poppins') else _cmap(font))


def prepare_cjk(text):
    """Register Noto Sans SC as a subset holding the CJK characters of `text` (plus those of earlier calls in
    this process). Call before layout (build.py passes every payload string): a font must not change while
    a document is laid out, so characters met later fall back to nothing and get a missing_glyph warning."""
    need = {ch for ch in str(text) if ord(ch) > 0x2E7F and not covered(ch) and not covered(ch, MATH)
            and not covered(ch, SYMBOLS)} - _CJK_DONE
    need &= {chr(c) for c in _cjk_source_cmap() if chr(c) in need}
    if not need:
        return False
    from fontTools import subset
    from fontTools.ttLib import TTFont as FT
    _CJK_DONE.update(need)
    f = FT(str(CJK_SOURCE))
    s = subset.Subsetter(subset.Options(name_IDs=['*'], name_languages=['*'], notdef_outline=True))
    s.populate(text=''.join(sorted(_CJK_DONE)))
    s.subset(f)
    buf = BytesIO()
    f.save(buf)
    buf.seek(0)
    pdfmetrics.registerFont(TTFont(CJK, buf))
    return True


def fallback_font(ch, base='Poppins-Light'):
    """First font of the chain that has `ch` (None: the base font has it, or nothing has it). Mono text
    falls back to Poppins Light first."""
    if covered(ch, base):
        return None
    for name in (['Poppins-Light'] if not base.startswith('Poppins') else []) + [MATH, SYMBOLS]:
        if covered(ch, name):
            return name
    return CJK if ch in _CJK_DONE else None


_INVISIBLE = {chr(c) for c in (0x200B, 0x200C, 0x200D, 0xFEFF, 0xAD)}   # zero-width / soft hyphen: no glyph needed


def missing(text, font=None):
    """Characters of `text` that no font of the chain can draw (font: text drawn in that one font only,
    no fallback -- canvas strings, plain-string table cells)."""
    if str(text).isascii():
        return []
    return sorted({ch for ch in str(text) if ch not in _INVISIBLE and
                   (not covered(ch, font) if font else not covered(ch) and fallback_font(ch) is None)})


def report_missing(text, where, font=None):
    from . import qa
    for ch in missing(text, font):
        qa.add('missing_glyph', 'warn', f'no font has U+{ord(ch):04X} "{ch}" ({where}); it prints as a blank',
               once=True)


_MARKUP = re.compile(r'(<[^>]*>|&#?\w+;)')


def fallback(markup, where='text', base='Poppins-Light'):
    """Paragraph markup with each run of characters Poppins lacks wrapped in <font name="..."> of the first
    fallback font that has them. Tags and entities are kept; nothing changes for plain Latin text."""
    if markup.isascii():                  # Poppins and JetBrains Mono both cover printable ASCII
        return markup
    out = []
    for part in _MARKUP.split(markup):
        if not part or part[0] == '<':
            out.append(part)
            continue
        ent = part[0] == '&'
        chars = [unescape(part)] if ent else part
        cur, run = None, []
        for ch, src in zip(chars, [part] if ent else part):
            font = fallback_font(ch, base) if len(ch) == 1 else None
            if font is None and len(ch) == 1 and not covered(ch, base):
                report_missing(ch, where)
            if font != cur and run:
                out.append(''.join(run) if cur is None else f'<font name="{cur}">{"".join(run)}</font>')
                run = []
            cur = font
            run.append(src)
        if run:
            out.append(''.join(run) if cur is None else f'<font name="{cur}">{"".join(run)}</font>')
    return ''.join(out)
