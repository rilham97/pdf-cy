"""Design tokens: geometry, colour, type and spacing. Single source of truth.

Coordinates named *_TOP / *_Y are measured from the TOP of the page (design
units, as in the approved template); convert with ``PAGE_H - y`` for ReportLab.
"""
import pyphen
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle

from . import fonts  # noqa: F401  -- import side effect registers Poppins

# --- Geometry -----------------------------------------------------------------
PAGE_W, PAGE_H = A4                      # 595.276 x 841.890
MM = 72 / 25.4
L = 14 * MM                              # 39.685
R = PAGE_W - L
CW = R - L                               # 515.906 content width
GUTTER = 10.5
COL2 = (CW - GUTTER) / 2                 # 252.703
COL3 = (CW - 2 * GUTTER) / 3             # 164.969
HEADER_H = 48.0
FOOTER_H = 48.0
FOOTER_Y = PAGE_H - FOOTER_H             # 793.890 (top of footer band)
FRAME_TOP = 72.0                         # first content line area
FRAME_BOTTOM = FOOTER_Y - 20.0           # 773.890
FRAME_H = FRAME_BOTTOM - FRAME_TOP       # 701.890
KEEP_MAX_H = FRAME_H / 3                 # blocks taller than this may split

# --- Colour -------------------------------------------------------------------
NAVY = HexColor('#074A8E')               # sapphire-700, brand dark
SAPPHIRE = HexColor('#0B7AE8')
AMBER = HexColor('#F5A524')
HEADING = HexColor('#14304F')
BODY = HexColor('#22303F')
MUTED = HexColor('#637182')               # was #6B7A8C (4.39:1); passes 4.5:1 on white/surface/band
RULE = HexColor('#D9DFE6')
SURFACE = HexColor('#F3F6F9')
FOOTER_BG = HexColor('#EBF5FF')          # sapphire-50
WATERMARK = HexColor('#C8D4E1')
COVER_LABEL = HexColor('#C9E3FF')
WHITE = white
SAPPHIRE_50 = FOOTER_BG
SAPPHIRE_100 = HexColor('#D6EAFF')
AMBER_600 = HexColor('#D18618')
AMBER_700 = HexColor('#A86610')
SLATE_400 = HexColor('#91A5BA')
UNSCANNED = HexColor('#8C98A6')

# Finding severity (siren marker, icons.py): four separate tiers, never merged. Quantum
# 'Moderate' uses Medium. Separate from IMPACT (risk bands / impact tiers).
SEVERITY = {
    'critical': HexColor('#9C3A24'),
    'high': HexColor('#DC2626'),
    'medium': HexColor('#D97706'),
    'low': HexColor('#1F9D55'),
}
# Tier copy for Critical / High (approved by product, 2026-10-15); Medium / Low use the source legend.
SEVERITY_TEXT = {
    'critical': 'Exploitable weakness with direct impact; act immediately.',
    'high': 'Serious weakness; fix as a priority.',
}
IMPACT = {                               # risk bands / impact tiers
    'critical': HexColor('#6E1F2E'),
    'high': HexColor('#C74A3C'),
    'medium': HexColor('#D8961A'),
    'low': HexColor('#2E8B57'),
}
GRADE = {
    'AAA': HexColor('#1F6E43'), 'AA': HexColor('#2E8B57'), 'A': HexColor('#5B9E4F'),
    'BBB': HexColor('#8FAA3E'), 'BB': HexColor('#C2A526'), 'B': HexColor('#D8961A'),
    'CCC': HexColor('#D87A2A'), 'CC': HexColor('#C74A3C'), 'C': HexColor('#9E3038'),
    'D': HexColor('#6E1F2E'),
}
GRADE_BAR = list(GRADE)[::-1]   # horizontal grade bars run worst -> best, left -> right (D .. AAA)
GRADE_MARK = {
    'AAA': 'Excellent', 'AA': 'Very good', 'A': 'Good', 'BBB': 'Satisfactory',
    'BB': 'Sufficient', 'B': 'Moderate', 'CCC': 'Insufficient', 'CC': 'Very insufficient',
    'C': 'Poor', 'D': 'Very poor',
}

# --- Status (semantic, restrained) -------------------------------------------------
# Colour only on the small icon / marker / chip square; label text stays BODY, no tinted fills.
# Red only for genuine failures. Shapes (check, x, minus, hourglass ...) carry the meaning in grayscale.
STATUS = {
    'good': HexColor('#1F9D55'),        # clear, approved, matches, enabled, valid, yes, PQC detected
    'bad': HexColor('#DC2626'),         # does not match, not enabled, missing/invalid, rejected, expired, no
    'attention': HexColor('#D97706'),   # pending review, awaiting approval, partial, cannot be compared
    'neutral': MUTED,                   # not assessed / applicable / compared / recorded, unknown
}
# status key -> tone: the ONE map every status marker reads (status_color). An unknown key raises.
TONE = {
    **dict.fromkeys(('clear', 'approved', 'match', 'enabled', 'valid', 'clean', 'yes', 'pqc', 'passed',
                     'resolved', 'redirects_to_https'), 'good'),
    **dict.fromkeys(('mismatch', 'not_enabled', 'missing', 'invalid', 'missing_or_invalid', 'weak', 'no_redirect',
                     'rejected', 'expired', 'no', 'failed', 'used_in_rating'), 'bad'),
    **dict.fromkeys(('pending_review', 'awaiting_approval', 'partial', 'cannot_compare', 'monitoring_only',
                     'unavailable', 'scoring_eligible', 'not_detected'), 'attention'),
    **dict.fromkeys(('not_assessed', 'not_applicable', 'not_compared', 'not_recorded', 'unknown',
                     'none_identified', 'historical', 'recorded', 'inaccurate', 'no_pqc'), 'neutral'),
}


def status_color(key):
    """Colour of a status marker: STATUS[TONE[key]]. 'findings' is not a status tone (stays NAVY)."""
    return STATUS[TONE[key]]


# --- States -------------------------------------------------------------------
STATES = ('findings', 'clear', 'not_assessed', 'not_applicable', 'unavailable', 'partial', 'pending_review',
          'none_identified')      # payload enum; 'identified' is display-only (shown_state)
STATE_LABELS = {'findings': 'Findings', 'identified': 'Identified', 'clear': 'No findings', 'not_assessed': 'Not assessed',
                'not_applicable': 'Not applicable', 'unavailable': 'Unavailable', 'partial': 'Partial coverage',
                'pending_review': 'Pending review',
                # a list known to be empty where 'No findings' would overclaim (s14: no connected organisations)
                'none_identified': 'None identified'}
# label: chip text; accent: icon + card rule. 'Findings' (weaknesses, as in the old reports) is orange:
# needs attention, severity sirens carry how much. 'Identified' (inventory / good news) is blue: neutral content.
# bg: card fill, SURFACE for every state (no status-tinted backgrounds)
STATE = {s: {'label': lbl, 'accent': {'findings': STATUS['attention'], 'identified': NAVY}.get(s) or status_color(s),
             'bg': SURFACE}
         for s, lbl in STATE_LABELS.items()}
# Sections whose results are an inventory or good news, not weaknesses (owner decision 2026-10-19): the payload
# state 'findings' reads 'Identified' there. 'clear' keeps 'No findings' (in 12 it means roles found, nothing missing).
INVENTORY = frozenset({'priority_actions', 'security_resourcing', 'certifications', 'fourth_party_vendors',
                       'cloud_infrastructure'})


def shown_state(state, section_key=None):
    """The state a chip / card shows for a section: inventory sections never read 'Findings'."""
    return 'identified' if state == 'findings' and section_key in INVENTORY else state
CLEAR_TITLE = 'No findings within the scope and time of this check'

# --- Spacing ------------------------------------------------------------------
SP_XS, SP_SM, SP_MD, SP_LG, SP_XL = 4, 8, 14, 22, 32

# --- Tables -------------------------------------------------------------------
CELL_PAD_V, CELL_PAD_H = 4.5, 6.0        # 12 leading + 2 x 4.5 = 21 pt row
DENSE_PAD_V = 3.5                        # 11 leading + 2 x 3.5 = 18 pt row
HAIRLINE = 0.5
KV_LABEL_W = 136.0                       # label column of every full-width key/value list
NARROW_COL = 110.0                       # null cells narrower than this print 'Not available' + a footnote

# --- Type ---------------------------------------------------------------------
LIGHT, REGULAR, MEDIUM, SEMIBOLD = 'Poppins-Light', 'Poppins-Regular', 'Poppins-Medium', 'Poppins-SemiBold'
# brand face: the cover and the running header title ('Cyber Risk Report for ...'); body text stays Poppins
BRAND_LIGHT, BRAND_REGULAR, BRAND_MEDIUM = 'Inter-Light', 'Inter-Regular', 'Inter-Medium'
# Technical tokens only (finding codes, hosts, IPs, URLs, hashes, algorithm names, account labels): JetBrains
# Mono at 0.9x the size of the text beside it (its 600-unit advance is wider than Poppins Light).
MONO, MONO_K = fonts.MONO, 0.9

_PYPHEN = pyphen.Pyphen(lang='en_US', left=3, right=3)   # one instance; >= 3 letters each side ('ed.')


def _hyphenate(word):
    """RL hyphenator: pyphen pairs; a compound breaks only at its own hyphen ('multi-|factor')."""
    pairs = _PYPHEN.iterate(word)
    return [(h, t) for h, t in pairs if h.endswith('-')] if '-' in word else pairs


_BASE = dict(
    allowWidows=0, allowOrphans=0,
    hyphenationLang=_hyphenate,
    embeddedHyphenation=1, uriWasteReduce=0.3,
    hyphenationMinWordLength=8,  # no 're-port' / 'rea-son' / 'spe-cific' splits
    splitLongWords=1,           # last resort only; qa word_split / min_width flag it
    spaceShrinkage=0, justifyBreaks=0,
)
_NO_HY = dict(hyphenationLang='', embeddedHyphenation=0, uriWasteReduce=0)


def _ps(name, font, size, leading, color, **kw):
    return ParagraphStyle(name, **{**_BASE, 'fontName': font, 'fontSize': size,
                                   'leading': leading, 'textColor': color, **kw})


_HEAD = dict(keepWithNext=1, **_NO_HY)
# Hyphenation (pyphen) is for body-width prose only: table cells, tile captions, key/value
# lists and flush notes never break a word.
STYLES = {
    'h1':        _ps('h1', MEDIUM, 23, 26.25, HEADING, spaceAfter=6, **_HEAD),
    'h1c':       _ps('h1c', MEDIUM, 15, 17.25, HEADING, spaceBefore=SP_LG, spaceAfter=6, **_HEAD),
    'h2':        _ps('h2', MEDIUM, 14, 18, HEADING, spaceBefore=SP_LG, spaceAfter=6, **_HEAD),
    'h3':        _ps('h3', MEDIUM, 11, 14, HEADING, spaceBefore=SP_MD, spaceAfter=4, **_HEAD),
    'h3c':       _ps('h3c', MEDIUM, 10.5, 14, HEADING, spaceBefore=SP_MD, spaceAfter=4, **_HEAD),
    'eyebrow':   _ps('eyebrow', MEDIUM, 7.8, 11.25, NAVY, spaceBefore=SP_XL, spaceAfter=5, **_HEAD),
    'intro':     _ps('intro', LIGHT, 10.5, 14.5, MUTED, spaceAfter=SP_MD),
    'body':      _ps('body', LIGHT, 9.1, 13, BODY, spaceAfter=6),
    'body_flush': _ps('body_flush', LIGHT, 9.1, 13, BODY),
    'bullet':    _ps('bullet', LIGHT, 9.1, 13, BODY, leftIndent=11, bulletIndent=0,
                     bulletFontName=LIGHT, spaceAfter=3),
    'note':      _ps('note', LIGHT, 7.8, 11.25, MUTED, spaceBefore=4, spaceAfter=6),
    'note_flush': _ps('note_flush', LIGHT, 7.8, 11.25, MUTED, **_NO_HY),
    'tech':      _ps('tech', MONO, round(9.1 * MONO_K, 2), 13, BODY, **_NO_HY),
    # tables
    'cell':      _ps('cell', LIGHT, 8.6, 12, BODY, **_NO_HY),
    'cell_num':  _ps('cell_num', LIGHT, 8.6, 12, BODY, alignment=TA_RIGHT, **_NO_HY),
    'cell_tech': _ps('cell_tech', MONO, round(8.6 * MONO_K, 2), 12, BODY, **_NO_HY),
    'cell_muted': _ps('cell_muted', LIGHT, 8.6, 12, MUTED, **_NO_HY),
    'cell_head': _ps('cell_head', MEDIUM, 8.6, 12, HEADING, **_NO_HY),
    'cell_head_num': _ps('cell_head_num', MEDIUM, 8.6, 12, HEADING, alignment=TA_RIGHT, **_NO_HY),
    'dense':     _ps('dense', LIGHT, 7.8, 11, BODY, **_NO_HY),
    'dense_num': _ps('dense_num', LIGHT, 7.8, 11, BODY, alignment=TA_RIGHT, **_NO_HY),
    'dense_tech': _ps('dense_tech', MONO, round(7.8 * MONO_K, 2), 11, BODY, **_NO_HY),
    'dense_muted': _ps('dense_muted', LIGHT, 7.8, 11, MUTED, **_NO_HY),
    'dense_head': _ps('dense_head', MEDIUM, 7.8, 11, HEADING, **_NO_HY),
    'dense_head_num': _ps('dense_head_num', MEDIUM, 7.8, 11, HEADING, alignment=TA_RIGHT, **_NO_HY),
    # components
    'chip':      _ps('chip', REGULAR, 8.2, 11, BODY, **_NO_HY),
    'chip_dense': _ps('chip_dense', REGULAR, 7.6, 11, BODY, **_NO_HY),
    'kpi_value': _ps('kpi_value', MEDIUM, 20, 24, HEADING, **_NO_HY),
    'kpi_na':    _ps('kpi_na', MEDIUM, 11, 14, MUTED, spaceBefore=5, spaceAfter=5, **_NO_HY),
    'kpi_label': _ps('kpi_label', LIGHT, 7.8, 11, MUTED, **_NO_HY),
    'kv_label':  _ps('kv_label', LIGHT, 8.6, 12, MUTED, **_NO_HY),
    'kv_value':  _ps('kv_value', LIGHT, 8.6, 12, BODY, **_NO_HY),
    'card_title': _ps('card_title', MEDIUM, 10.5, 14, HEADING, spaceAfter=3, **_NO_HY),
    'card_label': _ps('card_label', MEDIUM, 7.8, 11.25, HEADING, spaceBefore=6, spaceAfter=1, **_NO_HY),
    'card_body': _ps('card_body', LIGHT, 9.1, 13, BODY),
    'verdict':   _ps('verdict', LIGHT, 9.6, 13.5, BODY),
    'pointer':   _ps('pointer', LIGHT, 8.2, 12, BODY),
    # contents (template: number Medium 9.1, title Light 9.1, [p.] Light 8.6, sub Light 8.2/12)
    'toc_group': _ps('toc_group', MEDIUM, 10.5, 14, HEADING, **_NO_HY),
    'toc_num':   _ps('toc_num', MEDIUM, 9.1, 13, HEADING, **_NO_HY),
    'toc_title': _ps('toc_title', LIGHT, 9.1, 13, BODY, **_NO_HY),
    'toc_sub':   _ps('toc_sub', LIGHT, 8.2, 12, MUTED, spaceBefore=2, **_NO_HY),
    'toc_page':  _ps('toc_page', LIGHT, 8.6, 13, MUTED, alignment=TA_RIGHT, **_NO_HY),
}
