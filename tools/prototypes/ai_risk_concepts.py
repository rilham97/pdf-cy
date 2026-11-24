"""Prototype: three PDF concepts for Section 10 (AI Risk) based on the new customer frontend UI:
  1. Use of AI level (Unlikely / Possible / Likely / Almost certain) + quote & URL
  2. Capability tags (LLM text generation, Scoring or ranking people, ...)
  3. Risk Level (Low / Medium / High / Critical)
  4. AI Providers / Models (optional — omitted when none detected)
  5. AI Governance (AI policy + ISO 42001 certificate with evidence URLs)
  6. High-Risk Use · EU AI Act (Annex III category, clause, quote, URL)

Tests all 3 concepts across 3 scenarios from the frontend screenshots:
  * Scenario 1 (HackerRank): Almost certain, Medium risk, EU AI Act Annex III 4(a) detected, no AI providers
  * Scenario 2 (Atlassian):  Almost certain, Low risk, AI providers (OpenAI, Anthropic), AI policy, no high-risk
  * Scenario 3 (Minimal):    Unlikely, Low risk, no evidence on any optional/governance/high-risk check

    .venv/bin/python -I tools/prototypes/ai_risk_concepts.py <out_dir>
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pymupdf  # noqa: E402
from reportlab.lib.colors import HexColor, white  # noqa: E402
from reportlab.pdfbase.pdfmetrics import stringWidth  # noqa: E402
from reportlab.platypus import Flowable, PageBreak, Spacer, Table, TableStyle  # noqa: E402

from cyberrank_report import components as C, icons as I, qa, theme as T  # noqa: E402
from cyberrank_report.page import ReportDoc  # noqa: E402

USE_LEVELS = ('Unlikely', 'Possible', 'Likely', 'Almost certain')
RISK_LEVELS = ('Low', 'Medium', 'High', 'Critical')
RISK_COLORS = {
    'Low': T.STATUS['good'],
    'Medium': T.STATUS['attention'],
    'High': T.SEVERITY['high'],
    'Critical': T.SEVERITY['critical'],
}
RISK_TINTS = {
    'Low': HexColor('#EAF6EF'),
    'Medium': HexColor('#FEF5E7'),
    'High': HexColor('#FDECEC'),
    'Critical': HexColor('#F7EAE7'),
}

# --- 3 scenarios matching the user's frontend screenshots -------------------------
SCENARIOS = [
    {
        'id': 'hackerrank',
        'org': 'HackerRank (Sample)',
        'domain': 'hackerrank.com',
        'label': 'High-risk AI detected (EU AI Act Annex III)',
        'state': 'findings',
        'use_of_ai': {'level': 'Almost certain', 'position': 0.96,
                      'quote': 'The IDE mirrors a modern developer setup, with inline assistance and a chat panel, '
                               'so that you can see how a candidate works alongside AI.',
                      'source_url': 'https://www.hackerrank.com/products/interview'},
        'capabilities': ['LLM text generation', 'Scoring or ranking people'],
        'risk_level': 'Medium',
        'ai_providers': [],
        'governance': {
            'ai_policy': {'found': True, 'label': 'AI policy published',
                          'url': 'https://www.hackerrank.com/about-us/responsible-ai'},
            'iso_42001': {'found': False, 'label': 'ISO 42001 certificate',
                          'note': "Not found on the vendor's website or in certification body registers"},
        },
        'high_risk_uses': [
            {'category': 'Recruitment, screening & candidate ranking',
             'clause': 'Annex III 4(a)',
             'quote': 'Gives hints without revealing the answer. Ramps up complexity with progressively harder '
                      'questions. Provides a detailed report following the interview. Screening candidates through '
                      'HackerRank has helped us rapidly and accurately identify the skills of candidates.',
             'source_url': 'https://www.hackerrank.com/products/screen'},
        ],
    },
    {
        'id': 'atlassian',
        'org': 'Atlassian (Sample)',
        'domain': 'atlassian.com',
        'label': 'AI providers + AI policy, no EU AI Act high-risk use',
        'state': 'findings',
        'use_of_ai': {'level': 'Almost certain', 'position': 0.96,
                      'quote': 'Join the 350,000+ teams where agents plan, triage, and deliver across the '
                               'Atlassian platform.',
                      'source_url': 'https://www.atlassian.com/'},
        'capabilities': ['LLM text generation'],
        'risk_level': 'Low',
        'ai_providers': ['OpenAI', 'Anthropic'],
        'governance': {
            'ai_policy': {'found': True, 'label': 'AI policy published',
                          'url': 'https://www.atlassian.com/trust/ai'},
            'iso_42001': {'found': False, 'label': 'ISO 42001 certificate',
                          'note': "Not found on the vendor's website or in certification body registers"},
        },
        'high_risk_uses': [],
    },
    {
        'id': 'minimal',
        'org': 'Example Corp (No AI Evidence)',
        'domain': 'example.com',
        'label': 'Unlikely AI use, no evidence across optional & governance checks',
        'state': 'clear',
        'use_of_ai': {'level': 'Unlikely', 'position': 0.10, 'quote': None, 'source_url': None},
        'capabilities': [],
        'risk_level': 'Low',
        'ai_providers': [],
        'governance': {
            'ai_policy': {'found': False, 'label': 'AI policy',
                          'note': "Not found on the vendor's website"},
            'iso_42001': {'found': False, 'label': 'ISO 42001 certificate',
                          'note': "Not found on the vendor's website or in certification body registers"},
        },
        'high_risk_uses': [],
    },
]

_H2_T = T.STYLES['h2'].clone('ai_h2_t', spaceBefore=T.SP_MD, spaceAfter=5)
_H3_T = T.STYLES['h3c'].clone('ai_h3_t', spaceBefore=T.SP_SM, spaceAfter=3)
_LBL = T.STYLES['eyebrow'].clone('ai_lbl', spaceBefore=0, spaceAfter=4, fontSize=7.2, textColor=T.MUTED)
_QUOTE = T.STYLES['body'].clone('ai_quote', fontSize=8.6, leading=12.5, spaceAfter=3)
_URL = T.STYLES['cell_tech'].clone('ai_url', textColor=T.NAVY)
_NOTE = T.STYLES['note'].clone('ai_note', hyphenationLang='', embeddedHyphenation=0)


# --- shared visual primitives ----------------------------------------------------
class UseOfAIBar(Flowable):
    """4-segment confidence bar (Unlikely / Possible / Likely / Almost certain) with position marker."""
    BAR_H = 8.0

    def __init__(self, level, position=None, compact=False):
        super().__init__()
        self.level = level if level in USE_LEVELS else 'Unlikely'
        self.idx = USE_LEVELS.index(self.level)
        self.pos = position if position is not None else (self.idx + 0.5) / 4.0
        self.compact = compact
        self.spaceAfter = 2 if compact else 6

    def wrap(self, aw, ah):
        self.width = aw
        self.height = (self.BAR_H + 6) if self.compact else (self.BAR_H + 16)
        return self.width, self.height

    def draw(self):
        cv = self.canv
        gap = 3.0
        seg_w = (self.width - 3 * gap) / 4.0
        y_bar = self.height - self.BAR_H - 2
        for i, lbl in enumerate(USE_LEVELS):
            x = i * (seg_w + gap)
            active = (i == self.idx)
            cv.setFillColor(T.SAPPHIRE if active else T.SURFACE)
            cv.setStrokeColor(T.SAPPHIRE if active else T.RULE)
            cv.setLineWidth(0.4)
            cv.roundRect(x, y_bar, seg_w, self.BAR_H, 1.5, stroke=1, fill=1)
            if not self.compact:
                cv.setFont(T.MEDIUM if active else T.LIGHT, 7.2)
                cv.setFillColor(T.NAVY if active else T.MUTED)
                cv.drawString(x, 1.5, lbl)
        # Position tick inside the active segment
        tick_x = max(2.0, min(self.width - 2.0, self.pos * self.width))
        cv.setFillColor(T.HEADING)
        cv.roundRect(tick_x - 1.2, y_bar - 2.0, 2.4, self.BAR_H + 4.0, 1.0, stroke=0, fill=1)


class RiskTierStrip(Flowable):
    """4-tier Risk Level selector (Low / Medium / High / Critical) with quiet Cyberrank styling."""
    H = 22.0

    def __init__(self, active_level):
        super().__init__()
        self.active = active_level if active_level in RISK_LEVELS else 'Low'
        self.spaceAfter = 6

    def wrap(self, aw, ah):
        self.width = aw
        self.height = self.H
        return self.width, self.height

    def draw(self):
        cv = self.canv
        gap = 4.0
        w = (self.width - 3 * gap) / 4.0
        for i, lv in enumerate(RISK_LEVELS):
            x = i * (w + gap)
            is_act = (lv == self.active)
            col = RISK_COLORS[lv]
            cv.setFillColor(RISK_TINTS[lv] if is_act else T.SURFACE)
            cv.setStrokeColor(col if is_act else T.RULE)
            cv.setLineWidth(1.2 if is_act else 0.5)
            cv.roundRect(x, 0, w, self.H, 3.0, stroke=1, fill=1)
            if is_act:
                # 6pt colour dot + bold label (quiet contrast, never white-on-bright-fill)
                tw = stringWidth(lv, T.MEDIUM, 8.4)
                dot = 5.0
                sx = x + (w - (dot + 4 + tw)) / 2.0
                cv.setFillColor(col)
                cv.circle(sx + dot / 2.0, self.H / 2.0, dot / 2.0, stroke=0, fill=1)
                cv.setFillColor(T.HEADING)
                cv.setFont(T.MEDIUM, 8.4)
                cv.drawString(sx + dot + 4, self.H / 2.0 - 3.0, lv)
            else:
                cv.setFillColor(T.MUTED)
                cv.setFont(T.LIGHT, 8.2)
                cv.drawCentredString(x + w / 2.0, self.H / 2.0 - 2.8, lv)


class TagFlow(Flowable):
    """Inline bordered pill tags wrapping cleanly across lines (like Appendix C methodology signals)."""
    FS, PAD_H, PAD_V, GAP_X, GAP_Y = 7.6, 7.0, 3.2, 5.0, 4.5

    def __init__(self, tags, accent=T.SAPPHIRE, bg=T.SAPPHIRE_50, text_color=T.NAVY):
        super().__init__()
        self.tags = [str(t) for t in tags if t]
        self.accent, self.bg, self.text_color = accent, bg, text_color
        self._lines = []
        self.spaceAfter = 4

    def wrap(self, aw, ah):
        self.width = aw
        h_box = self.FS + 2 * self.PAD_V
        lines, cur, cx = [], [], 0.0
        for tag in self.tags:
            tw = stringWidth(tag, T.REGULAR, self.FS) + 2 * self.PAD_H
            if cur and cx + tw > aw:
                lines.append(cur)
                cur, cx = [], 0.0
            cur.append((tag, tw))
            cx += tw + self.GAP_X
        if cur:
            lines.append(cur)
        self._lines = lines
        self._h_box = h_box
        self.height = len(lines) * h_box + max(0, len(lines) - 1) * self.GAP_Y
        return self.width, self.height

    def draw(self):
        cv = self.canv
        y = self.height - self._h_box
        for row in self._lines:
            x = 0.0
            for tag, tw in row:
                cv.setFillColor(self.bg)
                cv.setStrokeColor(self.accent)
                cv.setLineWidth(0.55)
                cv.roundRect(x, y, tw, self._h_box, 3.0, stroke=1, fill=1)
                cv.setFillColor(self.text_color)
                cv.setFont(T.REGULAR, self.FS)
                cv.drawString(x + self.PAD_H, y + self.PAD_V + 1.0, tag)
                x += tw + self.GAP_X
            y -= self._h_box + self.GAP_Y


def _concept_banner(tag, sub):
    t = Table([[C.M(f'<font name="{T.MEDIUM}" color="{C.hexstr(T.NAVY)}">{C.esc(tag)}</font>  '
                    f'<font color="{C.hexstr(T.MUTED)}">{C.esc(sub)}</font>', 'note_flush')]],
              colWidths=[T.CW], hAlign='LEFT', spaceAfter=6)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), T.SURFACE),
        ('LINEBEFORE', (0, 0), (0, 0), 2.5, T.NAVY),
        ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return t


def _verdict(sc):
    u = sc['use_of_ai']['level']
    rl = sc['risk_level']
    hr = sc['high_risk_uses']
    gov = sc['governance']
    if u == 'Unlikely' and not hr:
        return (f'AI risk is assessed as {rl}; public signals indicate AI use is unlikely. '
                'No EU AI Act Annex III high-risk use was found on the public website.')
    bits = [f'AI risk is assessed as {rl} with {u.lower()} AI use observed on public pages.']
    if hr:
        clauses = ', '.join(h['clause'] for h in hr)
        bits.append(f'Potential EU AI Act high-risk use identified ({clauses}).')
    else:
        bits.append('No EU AI Act Annex III high-risk use was found on the public website.')
    found_gov = [k for k, v in (('AI policy', gov['ai_policy']), ('ISO 42001', gov['iso_42001'])) if v['found']]
    if found_gov:
        bits.append(f'Public governance evidence found: {", ".join(found_gov)}.')
    return ' '.join(bits)


def _opener(sc, concept_tag, concept_sub):
    intro = ('Evaluates externally observable AI usage, capabilities, EU AI Act high-risk '
             'classification, and published AI governance controls.')
    return [_concept_banner(concept_tag, f'{sc["org"]} · {concept_sub}')] + C.section_opener(
        '10', 'AI Risk', sc['state'], verdict=_verdict(sc), intro=intro,
        group='Assessment details', icon='ai_risk_governance',
    )


def _url_link(url):
    return C.M(f'<a href="{C.esc(url)}" color="{C.hexstr(T.NAVY)}">{C.esc(url)}</a>', _URL)


def _gov_table(gov, width=None):
    rows = []
    for key in ('ai_policy', 'iso_42001'):
        item = gov[key]
        if item['found']:
            st = I.yes_no_label(True, 'Found', style=T.STYLES['chip_dense'])
            ev = _url_link(item['url']) if item.get('url') else C.P(item.get('note') or 'Published', 'cell')
        else:
            st = I.yes_no_label(None, 'Not found', status='not_compared', style=T.STYLES['chip_dense'])
            ev = C.P(item.get('note') or 'Not found on public pages', 'cell_muted')
        rows.append([C.P(item['label'], 'cell'), st, ev])
    w = width or T.CW
    return C.compact_table(['Control', 'Status', 'Public evidence'], rows,
                           widths=[130, 86, w - 216])


def _high_risk_card(hr_list):
    """Orange-accented neutral card for EU AI Act Annex III high-risk uses."""
    blocks = []
    for i, item in enumerate(hr_list):
        if i:
            blocks.append(Spacer(0, 6))
        inner_w = T.CW - 24
        hdr = Table([[C.M(f'<font name="{T.MEDIUM}" color="{C.hexstr(T.HEADING)}">{C.esc(item["category"])}</font>',
                          'cell'),
                      C.M(f'<font name="{T.MEDIUM}" color="{C.hexstr(T.STATUS["attention"])}">{C.esc(item["clause"])}</font>',
                          'dense_num')]],
                    colWidths=[inner_w * 0.76, inner_w * 0.24], hAlign='LEFT')
        hdr.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                                 ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
        blocks.append(hdr)
        if item.get('quote'):
            blocks.append(C.P(f'“{item["quote"]}”', _QUOTE))
        if item.get('source_url'):
            blocks.append(_url_link(item['source_url']))
    card = Table([[blocks]], colWidths=[T.CW], hAlign='LEFT', spaceBefore=2, spaceAfter=T.SP_SM)
    card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), T.SURFACE),
        ('LINEBEFORE', (0, 0), (0, -1), 2.5, T.STATUS['attention']),
        ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('NOSPLIT', (0, 0), (-1, -1)),
    ]))
    return card


def _any_gov(gov):
    return gov['ai_policy']['found'] or gov['iso_42001']['found']


# ==================================================================================
# CONCEPT A: Dashboard Mirror (2-Col Scales + Adaptive Cards)
# ==================================================================================
def concept_a(sc):
    out = _opener(sc, 'CONCEPT A — Dashboard Mirror',
                  'Mirrors frontend 2-column scales; hides absent optional blocks & empty high-risk box.')
    u = sc['use_of_ai']
    left = [C.P('USE OF AI', _LBL), UseOfAIBar(u['level'], u['position'])]
    if u.get('quote'):
        left.append(C.P(f'“{u["quote"]}”', _QUOTE))
    if u.get('source_url'):
        left.append(_url_link(u['source_url']))
        left.append(Spacer(0, 4))
    if sc['capabilities']:
        left.append(TagFlow(sc['capabilities']))

    right = [C.P('RISK LEVEL', _LBL), RiskTierStrip(sc['risk_level'])]
    if sc['ai_providers']:
        right += [Spacer(0, 4), C.P('AI PROVIDERS', _LBL),
                  TagFlow(sc['ai_providers'], accent=T.RULE, bg=T.SURFACE, text_color=T.HEADING)]

    top = Table([[left, '', right]], colWidths=[T.COL2 + 12, T.GUTTER, T.COL2 - 12],
                hAlign='LEFT', spaceAfter=T.SP_MD)
    top.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                             ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                             ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    out.append(top)

    # High-risk EU AI Act: full card ONLY when detected; otherwise 1-line check note
    if sc['high_risk_uses']:
        out.append(C.P('High-risk use · EU AI Act', _H2_T))
        out.append(_high_risk_card(sc['high_risk_uses']))

    # AI Governance: full table when AI use >= Possible OR any control found; else compact line
    if u['level'] != 'Unlikely' or _any_gov(sc['governance']):
        out.append(C.P('AI governance', _H2_T))
        out.append(_gov_table(sc['governance']))
    else:
        out.append(C.P('AI governance and EU AI Act checks: No public AI policy, ISO 42001 certificate, or '
                       'Annex III high-risk use was found on the public website.', _NOTE))

    if not sc['high_risk_uses'] and (u['level'] != 'Unlikely' or _any_gov(sc['governance'])):
        out.append(C.P('EU AI Act high-risk use (Annex III): None found on the vendor\'s website.', _NOTE))
    return out


# ==================================================================================
# CONCEPT B: Editorial Assessment Sheet (Posture Strip + Evidence-Only Sections)
# ==================================================================================
def concept_b(sc):
    out = _opener(sc, 'CONCEPT B — Editorial Assessment Sheet (Recommended)',
                  'Cyberrank-native posture strip + evidence-only sections (empty blocks omitted cleanly).')
    u = sc['use_of_ai']
    hr = sc['high_risk_uses']
    gov = sc['governance']
    gov_found = sum(1 for k in ('ai_policy', 'iso_42001') if gov[k]['found'])

    # Top posture strip (3 balanced columns matching kpi_strip aesthetic)
    col_w = (T.CW - 2 * T.GUTTER) / 3.0
    t1 = [C.P(sc['risk_level'], 'kpi_value', textColor=RISK_COLORS[sc['risk_level']]),
          C.P('AI risk level', 'kpi_label', spaceBefore=2),
          C.P('Scale: Low · Medium · High · Critical', 'note_flush', spaceBefore=2)]
    t2 = [C.P(u['level'], 'kpi_value'),
          C.P('Use of AI', 'kpi_label', spaceBefore=2),
          Spacer(0, 3), UseOfAIBar(u['level'], u['position'], compact=True)]
    if hr:
        t3_val = C.P(hr[0]['clause'], 'kpi_value', textColor=T.STATUS['attention'])
        t3_sub = C.P('EU AI Act high-risk use detected', 'kpi_label', spaceBefore=2)
    else:
        t3_val = C.P('None found', 'kpi_na', textColor=T.HEADING)
        t3_sub = C.P('EU AI Act high-risk use (Annex III)', 'kpi_label', spaceBefore=2)
    t3_foot = C.P(f'Governance: {gov_found} of 2 public controls found', 'note_flush', spaceBefore=3)
    t3 = [t3_val, t3_sub, t3_foot]

    strip = Table([[t1, '', t2, '', t3]], colWidths=[col_w, T.GUTTER, col_w, T.GUTTER, col_w],
                  hAlign='LEFT', spaceAfter=T.SP_MD)
    strip.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LINEABOVE', (0, 0), (0, 0), 0.75, T.RULE),
        ('LINEABOVE', (2, 0), (2, 0), 0.75, T.RULE),
        ('LINEABOVE', (4, 0), (4, 0), 0.75, T.RULE),
    ]))
    out.append(strip)

    # 1. Observed AI Use — ONLY shown when capabilities, providers, or quote exist
    kv_pairs = []
    if sc['capabilities']:
        kv_pairs.append(('Observed capabilities', TagFlow(sc['capabilities'])))
    if sc['ai_providers']:
        kv_pairs.append(('AI providers / models',
                         TagFlow(sc['ai_providers'], accent=T.RULE, bg=T.SURFACE, text_color=T.HEADING)))
    if u.get('quote'):
        ev_cell = [C.P(f'“{u["quote"]}”', _QUOTE)]
        if u.get('source_url'):
            ev_cell.append(_url_link(u['source_url']))
        kv_pairs.append(('Public evidence', ev_cell))
    if kv_pairs:
        out.append(C.P('Observed AI use', _H2_T))
        out.append(C.key_value_list(kv_pairs))

    # 2. High-Risk Use (EU AI Act) — ONLY shown when detected!
    if hr:
        out.append(C.P('High-risk use · EU AI Act', _H2_T))
        out.append(_high_risk_card(hr))

    # 3. AI Governance — shown when AI use >= Possible OR any control found; omitted into note when Unlikely + empty
    if u['level'] != 'Unlikely' or _any_gov(gov):
        out.append(C.P('AI governance', _H2_T))
        out.append(_gov_table(gov))
    else:
        out.append(C.state_card(
            'clear',
            'Public pages show no active AI capabilities, named AI providers, EU AI Act Annex III '
            'high-risk uses, or published AI governance documents (AI policy / ISO 42001).',
            ['Public website pages and product descriptions',
             'EU AI Act Annex III high-risk use indicators',
             'Published AI policy and ISO 42001 certification registers'],
            title='No public AI risk signals observed',
        ))

    out.append(C.P('Scope note: Assessment is based on publicly accessible pages and certification registers; '
                   'internal or private AI tools are not visible to external checks.', _NOTE))
    return out


# ==================================================================================
# CONCEPT C: Compact Compliance Matrix (1-Page Checklist + Evidence Dossier)
# ==================================================================================
def concept_c(sc):
    out = _opener(sc, 'CONCEPT C — Compact Compliance Matrix',
                  'Single aligned GRC checklist table + optional evidence quotes (fastest scan, always 1 page).')
    u = sc['use_of_ai']
    hr = sc['high_risk_uses']
    gov = sc['governance']

    # Compact dual-scale header bar
    bar = Table([[
        [C.P('USE OF AI', _LBL), UseOfAIBar(u['level'], u['position'])],
        '',
        [C.P('AI RISK LEVEL', _LBL), RiskTierStrip(sc['risk_level'])],
    ]], colWidths=[T.COL2 + 12, T.GUTTER, T.COL2 - 12], hAlign='LEFT', spaceAfter=T.SP_SM)
    bar.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                             ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                             ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    out.append(bar)

    # Unified compliance matrix (optional rows omitted when absent!)
    out.append(C.P('AI risk summary', _H2_T))
    rows = []
    if sc['capabilities']:
        rows.append(['Observed capabilities', TagFlow(sc['capabilities']),
                     I.yes_no_label(None, 'Observed', status='not_compared', style=T.STYLES['chip_dense'])])
    if sc['ai_providers']:
        rows.append(['AI providers / models',
                     TagFlow(sc['ai_providers'], accent=T.RULE, bg=T.SURFACE, text_color=T.HEADING),
                     I.yes_no_label(None, 'Identified', status='not_compared', style=T.STYLES['chip_dense'])])
    if hr:
        hr_txt = '; '.join(f'{h["category"]} ({h["clause"]})' for h in hr)
        rows.append(['EU AI Act high-risk use', C.M(f'<b>{C.esc(hr_txt)}</b>', 'cell'),
                     C.state_chip('findings', dense=True)])
    else:
        rows.append(['EU AI Act high-risk use', C.P("None found on the vendor's website", 'cell_muted'),
                     I.yes_no_label(True, 'None found', style=T.STYLES['chip_dense'])])

    for key in ('ai_policy', 'iso_42001'):
        item = gov[key]
        if item['found']:
            detail = _url_link(item['url']) if item.get('url') else C.P('Published', 'cell')
            chip = I.yes_no_label(True, 'Found', style=T.STYLES['chip_dense'])
        else:
            detail = C.P(item.get('note') or 'Not found', 'cell_muted')
            chip = I.yes_no_label(None, 'Not found', status='not_compared', style=T.STYLES['chip_dense'])
        rows.append([item['label'], detail, chip])

    out.append(C.compact_table(['Dimension', 'Finding / Evidence', 'Status'], rows,
                               widths=[128, T.CW - 218, 90]))

    # Supporting quotes — ONLY shown when at least one quote exists!
    ev_pairs = []
    if u.get('quote'):
        cell = [C.P(f'“{u["quote"]}”', _QUOTE)]
        if u.get('source_url'):
            cell.append(_url_link(u['source_url']))
        ev_pairs.append(('AI use evidence', cell))
    for h in hr:
        cell = [C.M(f'<b>{C.esc(h["category"])}</b>  '
                    f'<font color="{C.hexstr(T.STATUS["attention"])}">({C.esc(h["clause"])})</font>', 'cell'),
                C.P(f'“{h["quote"]}”', _QUOTE)]
        if h.get('source_url'):
            cell.append(_url_link(h['source_url']))
        ev_pairs.append(('High-risk use evidence', cell))
    if ev_pairs:
        out.append(C.P('Public evidence excerpts', _H2_T))
        out.append(C.key_value_list(ev_pairs))

    out.append(C.P('Scope note: Derived from public web pages and certification registers; internal AI systems '
                   'are outside external visibility.', _NOTE))
    return out


def main():
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_dir / 'AI_Risk_Concepts.pdf'
    qa.ISSUES.clear()
    ident = {
        'org': 'AI Risk Concepts (A / B / C)',
        'domain': 'hackerrank.com · atlassian.com · example.com',
        'title': 'AI Risk Section Concepts',
        'assessment_date': '24 Nov 2026',
        'generated_date': '24 Nov 2026',
        'issuer': 'Cyberrank',
        'issuer_reason': None,
        'logo': None,
    }
    doc = ReportDoc(out_pdf, ident, subject='Section 10 AI Risk concepts A, B, C')
    doc.pageTemplates = [t for t in doc.pageTemplates if t.id == 'interior'] + [
        t for t in doc.pageTemplates if t.id != 'interior']

    story = []
    pages = [
        # Scenario 1: HackerRank (High-Risk Annex III) — A, B, C
        ('A-hackerrank', concept_a(SCENARIOS[0])),
        ('B-hackerrank', concept_b(SCENARIOS[0])),
        ('C-hackerrank', concept_c(SCENARIOS[0])),
        # Scenario 2: Atlassian (AI Providers + Policy, no High-Risk) — B & A
        ('B-atlassian', concept_b(SCENARIOS[1])),
        # Scenario 3: Minimal / Unlikely (No evidence) — A, B, C
        ('A-minimal', concept_a(SCENARIOS[2])),
        ('B-minimal', concept_b(SCENARIOS[2])),
        ('C-minimal', concept_c(SCENARIOS[2])),
    ]
    for i, (tag, flow) in enumerate(pages):
        if i:
            story.append(PageBreak())
        story.append(C.Anchor(f'p-{tag}', outline=tag))
        story += flow

    total = doc.render(story)
    issues = list(qa.ISSUES) + qa.check_pdf(out_pdf, skip_pages=(), table_parts=doc.table_parts,
                                            table_heads=C._TABLE_HEADS)
    counts = qa.write_report(out_pdf.with_suffix('.qa.json'), out_pdf, issues, pages=total)
    pdf = pymupdf.open(str(out_pdf))
    for i, pg in enumerate(pdf, 1):
        pg.get_pixmap(dpi=130).save(str(out_dir / f'page-{i:02d}.png'))
    pdf.close()
    print(f'{out_pdf}: {total} pages; QA {counts}')
    for iss in json.loads(out_pdf.with_suffix('.qa.json').read_text())['issues']:
        print(' ', iss['severity'], iss['check'], f'p{iss.get("page")}', iss['detail'][:120])


if __name__ == '__main__':
    import json
    main()
