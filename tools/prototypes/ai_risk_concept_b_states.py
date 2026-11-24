"""Prototype: Concept B (Editorial Assessment Sheet) across all 4 real state combinations
for Section 10 (AI Risk):

  Page 1 — Case 1: No AI usage (`Unlikely`, no capabilities/providers/high-risk/governance)
  Page 2 — Case 2: Has AI usage + AI providers/models, NO Annex III high-risk (Atlassian)
  Page 3 — Case 3: Has AI usage + ISO 42001 (no AI policy), NO Annex III, NO providers (Cursor)
  Page 4 — Case 4: Full case — Has AI usage + AI providers/models + Annex III high-risk (HackerRank + models)

    .venv/bin/python -I tools/prototypes/ai_risk_concept_b_states.py <out_dir>
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pymupdf  # noqa: E402
from reportlab.lib.colors import HexColor  # noqa: E402
from reportlab.pdfbase.pdfmetrics import stringWidth  # noqa: E402
from reportlab.platypus import Flowable, PageBreak, Spacer, Table, TableStyle  # noqa: E402

from cyberrank_report import components as C, icons as I, qa, theme as T  # noqa: E402
from cyberrank_report.page import ReportDoc  # noqa: E402

USE_LEVELS = ('Unlikely', 'Possible', 'Likely', 'Almost certain')
RISK_COLORS = {
    'Low': T.STATUS['good'],
    'Medium': T.STATUS['attention'],
    'High': T.SEVERITY['high'],
    'Critical': T.SEVERITY['critical'],
}
_H2_T = T.STYLES['h2'].clone('aib_h2', spaceBefore=T.SP_MD, spaceAfter=5)
_QUOTE = T.STYLES['body'].clone('aib_quote', fontSize=8.6, leading=12.5, spaceAfter=3)
_URL = T.STYLES['cell_tech'].clone('aib_url', textColor=T.NAVY)
_NOTE = T.STYLES['note'].clone('aib_note', hyphenationLang='', embeddedHyphenation=0)
_KPI_MED = T.STYLES['kpi_value'].clone('aib_kpi_med', fontSize=16, leading=20)
_KPI_SUB_OK = T.STYLES['kpi_value'].clone('aib_kpi_ok', fontSize=16, leading=20, textColor=T.HEADING)

CASES = [
    {
        'id': 'case1_no_ai',
        'banner': 'CASE 1 — Tidak punya AI usage (Unlikely, tidak ada bukti governance / Annex III)',
        'org': 'Example Corp (No AI Usage)',
        'domain': 'example.com',
        'state': 'clear',
        'use_of_ai': {'level': 'Unlikely', 'position': 0.10, 'quote': None, 'source_url': None},
        'capabilities': [],
        'risk_level': 'Low',
        'ai_providers': [],
        'ai_models': [],
        'governance': {
            'ai_policy': {'found': False, 'label': 'AI policy', 'note': "Not found on the vendor's website"},
            'iso_42001': {'found': False, 'label': 'ISO 42001 certificate',
                          'note': "Not found on the vendor's website or in certification body registers"},
        },
        'high_risk_uses': [],
    },
    {
        'id': 'case2_ai_no_annex_with_providers',
        'banner': 'CASE 2 — Punya AI usage + AI providers/models, TANPA EU AI Act Annex III (Atlassian)',
        'org': 'Atlassian (Sample)',
        'domain': 'atlassian.com',
        'state': 'findings',
        'use_of_ai': {'level': 'Almost certain', 'position': 0.96,
                      'quote': 'Join the 350,000+ teams where agents plan, triage, and deliver across the '
                               'Atlassian platform.',
                      'source_url': 'https://www.atlassian.com/'},
        'capabilities': ['LLM text generation'],
        'risk_level': 'Low',
        'ai_providers': ['OpenAI', 'Anthropic'],
        'ai_models': ['GPT-4o', 'Claude 3.5 Sonnet'],
        'governance': {
            'ai_policy': {'found': True, 'label': 'AI policy published',
                          'url': 'https://www.atlassian.com/trust/ai'},
            'iso_42001': {'found': False, 'label': 'ISO 42001 certificate',
                          'note': "Not found on the vendor's website or in certification body registers"},
        },
        'high_risk_uses': [],
    },
    {
        'id': 'case3_ai_no_annex_no_providers',
        'banner': 'CASE 3 — Punya AI usage + ISO 42001, TANPA Annex III & TANPA AI providers (Cursor)',
        'org': 'Cursor (Sample)',
        'domain': 'cursor.com',
        'state': 'findings',
        'use_of_ai': {'level': 'Almost certain', 'position': 0.90,
                      'quote': 'No training on your data by Cursor or LLM providers.',
                      'source_url': 'https://cursor.com/enterprise'},
        'capabilities': ['LLM text generation'],
        'risk_level': 'Low',
        'ai_providers': [],
        'ai_models': [],
        'governance': {
            'ai_policy': {'found': False, 'label': 'AI policy', 'note': "Not found on the vendor's website"},
            'iso_42001': {'found': True, 'label': 'ISO 42001 certificate',
                          'note': 'Registry listing',
                          'url': 'https://integrator.schellman.com/public/v2/certificate?search=Anysphere%2C%20Inc'},
        },
        'high_risk_uses': [],
    },
    {
        'id': 'case4_full_with_annex_and_providers',
        'banner': 'CASE 4 — Full: Punya AI usage + AI providers/models + EU AI Act Annex III High-Risk',
        'org': 'HackerRank (Sample)',
        'domain': 'hackerrank.com',
        'state': 'findings',
        'use_of_ai': {'level': 'Almost certain', 'position': 0.96,
                      'quote': 'The IDE mirrors a modern developer setup, with inline assistance and a chat panel, '
                               'so that you can see how a candidate works alongside AI.',
                      'source_url': 'https://www.hackerrank.com/products/interview'},
        'capabilities': ['LLM text generation', 'Scoring or ranking people'],
        'risk_level': 'Medium',
        'ai_providers': ['OpenAI', 'Anthropic'],
        'ai_models': [],
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
]


class UseOfAIBar(Flowable):
    BAR_H = 7.0

    def __init__(self, level, position=None):
        super().__init__()
        self.level = level if level in USE_LEVELS else 'Unlikely'
        self.idx = USE_LEVELS.index(self.level)
        self.pos = position if position is not None else (self.idx + 0.5) / 4.0
        self.spaceAfter = 2

    def wrap(self, aw, ah):
        self.width = aw
        self.height = self.BAR_H + 5
        return self.width, self.height

    def draw(self):
        cv = self.canv
        gap = 3.0
        seg_w = (self.width - 3 * gap) / 4.0
        y_bar = 2.0
        for i in range(4):
            x = i * (seg_w + gap)
            active = (i == self.idx)
            cv.setFillColor(T.SAPPHIRE if active else T.SURFACE)
            cv.setStrokeColor(T.SAPPHIRE if active else T.RULE)
            cv.setLineWidth(0.4)
            cv.roundRect(x, y_bar, seg_w, self.BAR_H, 1.5, stroke=1, fill=1)
        tick_x = max(2.0, min(self.width - 2.0, self.pos * self.width))
        cv.setFillColor(T.HEADING)
        cv.roundRect(tick_x - 1.2, y_bar - 1.8, 2.4, self.BAR_H + 3.6, 1.0, stroke=0, fill=1)


class TagFlow(Flowable):
    FS, PAD_H, PAD_V, GAP_X, GAP_Y = 7.6, 7.0, 3.0, 5.0, 4.0

    def __init__(self, tags, accent=T.SAPPHIRE, bg=T.SAPPHIRE_50, text_color=T.NAVY):
        super().__init__()
        self.tags = [str(t) for t in tags if t]
        self.accent, self.bg, self.text_color = accent, bg, text_color
        self._lines = []
        self.spaceAfter = 2

    def wrap(self, aw, ah):
        self.width = aw
        self._h_box = self.FS + 2 * self.PAD_V
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
        self.height = len(lines) * self._h_box + max(0, len(lines) - 1) * self.GAP_Y
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
                cv.drawString(x + self.PAD_H, y + self.PAD_V + 0.8, tag)
                x += tw + self.GAP_X
            y -= self._h_box + self.GAP_Y


def _banner(text):
    t = Table([[C.M(f'<font name="{T.MEDIUM}" color="{C.hexstr(T.NAVY)}">CONCEPT B</font>  '
                    f'<font color="{C.hexstr(T.MUTED)}">{C.esc(text)}</font>', 'note_flush')]],
              colWidths=[T.CW], hAlign='LEFT', spaceAfter=6)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), T.SURFACE),
        ('LINEBEFORE', (0, 0), (0, 0), 2.5, T.NAVY),
        ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return t


def _url_flow(url, width=320):
    """Breakable clickable URL in JetBrains Mono (never splits mid-word or overflows)."""
    lines = C.tech_lines(url, width, _URL.fontName, _URL.fontSize)
    shown = '<br/>'.join(C.esc(ln) for ln in lines)
    return C.M(f'<a href="{C.esc(url)}" color="{C.hexstr(T.NAVY)}">{shown}</a>', _URL)


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
        bits.append(f'Potential EU AI Act high-risk use identified ({", ".join(h["clause"] for h in hr)}).')
    else:
        bits.append('No EU AI Act Annex III high-risk use was found on the public website.')
    found_gov = [lbl for lbl, g in (('AI policy', gov['ai_policy']), ('ISO 42001', gov['iso_42001'])) if g['found']]
    if found_gov:
        bits.append(f'Public governance evidence found: {", ".join(found_gov)}.')
    return ' '.join(bits)


def _high_risk_card(hr_list):
    blocks = []
    inner_w = T.CW - 24
    for i, item in enumerate(hr_list):
        if i:
            blocks.append(Spacer(0, 6))
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
            blocks.append(_url_flow(item['source_url'], inner_w))
    card = Table([[blocks]], colWidths=[T.CW], hAlign='LEFT', spaceBefore=2, spaceAfter=T.SP_SM)
    card.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), T.SURFACE),
        ('LINEBEFORE', (0, 0), (0, -1), 2.5, T.STATUS['attention']),
        ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('NOSPLIT', (0, 0), (-1, -1)),
    ]))
    return card


def _gov_table(gov):
    ev_w = T.CW - 216 - 12
    rows = []
    for key in ('ai_policy', 'iso_42001'):
        item = gov[key]
        if item['found']:
            st = I.yes_no_label(True, 'Found', style=T.STYLES['chip_dense'])
            parts = []
            if item.get('note'):
                parts.append(C.P(item['note'], 'cell'))
            if item.get('url'):
                parts.append(_url_flow(item['url'], ev_w))
            ev = parts if len(parts) > 1 else (parts[0] if parts else C.P('Published', 'cell'))
        else:
            st = I.yes_no_label(None, 'Not found', status='not_compared', style=T.STYLES['chip_dense'])
            ev = C.P(item.get('note') or 'Not found on public pages', 'cell_muted')
        rows.append([C.P(item['label'], 'cell'), st, ev])
    return C.compact_table(['Control', 'Status', 'Public evidence'], rows, widths=[130, 86, T.CW - 216])


def build_concept_b(sc):
    intro = ('Evaluates externally observable AI usage, capabilities, AI providers/models, '
             'EU AI Act high-risk classification, and published AI governance controls.')
    out = [_banner(sc['banner'])] + C.section_opener(
        '10', 'AI Risk', sc['state'], verdict=_verdict(sc), intro=intro,
        group='Assessment details', icon='ai_risk_governance',
    )
    u = sc['use_of_ai']
    hr = sc['high_risk_uses']
    gov = sc['governance']
    gov_found = sum(1 for k in ('ai_policy', 'iso_42001') if gov[k]['found'])
    any_gov = gov_found > 0

    # Top posture strip — balanced heights across all 3 tiles
    col_w = (T.CW - 2 * T.GUTTER) / 3.0
    risk_col = RISK_COLORS[sc['risk_level']]
    t1 = [C.P(sc['risk_level'], _KPI_MED, textColor=risk_col),
          C.P('AI risk level', 'kpi_label', spaceBefore=2),
          C.P('Scale: Low · Medium · High · Critical', 'note_flush', spaceBefore=2)]
    t2 = [C.P(u['level'], _KPI_MED),
          C.P('Use of AI', 'kpi_label', spaceBefore=2),
          Spacer(0, 3), UseOfAIBar(u['level'], u['position'])]
    if hr:
        t3_val = C.P(hr[0]['clause'], _KPI_MED, textColor=T.STATUS['attention'])
        t3_lbl = 'EU AI Act high-risk detected'
    else:
        t3_val = C.P('None found', _KPI_SUB_OK)
        t3_lbl = 'EU AI Act high-risk (Annex III)'
    t3 = [t3_val,
          C.P(t3_lbl, 'kpi_label', spaceBefore=2),
          C.P(f'Governance: {gov_found} of 2 public controls found', 'note_flush', spaceBefore=2)]

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

    # 1. Observed AI use — ONLY rendered when capabilities or quote exist
    ev_w = T.CW - T.KV_LABEL_W - 14
    kv = []
    if sc['capabilities']:
        kv.append(('Observed capabilities', TagFlow(sc['capabilities'])))
    if u.get('quote'):
        cell = [C.P(f'“{u["quote"]}”', _QUOTE)]
        if u.get('source_url'):
            cell.append(_url_flow(u['source_url'], ev_w))
        kv.append(('Public evidence', cell))
    if kv:
        out.append(C.P('Observed AI use', _H2_T))
        out.append(C.key_value_list(kv))

    # 2. AI providers & models — dedicated, clearly visible block ONLY when detected!
    provs = sc.get('ai_providers') or []
    models = sc.get('ai_models') or []
    if provs or models:
        out.append(C.P('AI providers and models', _H2_T))
        pm_kv = []
        if provs:
            pm_kv.append(('Detected AI providers',
                          TagFlow(provs, accent=T.NAVY, bg=T.SURFACE, text_color=T.HEADING)))
        if models:
            pm_kv.append(('Detected AI models',
                          TagFlow(models, accent=T.SLATE_400, bg=T.SURFACE, text_color=T.BODY)))
        out.append(C.key_value_list(pm_kv))

    # 3. High-risk use · EU AI Act — ONLY rendered when detected!
    if hr:
        out.append(C.P('High-risk use · EU AI Act', _H2_T))
        out.append(_high_risk_card(hr))

    # 4. AI governance — full table when AI use >= Possible OR any control exists; else calm clear card
    if u['level'] != 'Unlikely' or any_gov:
        out.append(C.P('AI governance', _H2_T))
        out.append(_gov_table(gov))
    else:
        out.append(C.state_card(
            'clear',
            'Public pages show no active AI capabilities, named AI providers or models, '
            'EU AI Act Annex III high-risk uses, or published AI governance documents '
            '(AI policy / ISO 42001).',
            ['Public website pages and product descriptions',
             'Third-party AI provider and model references',
             'EU AI Act Annex III high-risk use indicators',
             'Published AI policy and ISO 42001 certification registers'],
            title='No public AI risk signals observed',
        ))

    out.append(C.P('Scope note: Assessment is based on publicly accessible pages and certification registers; '
                   'internal or private AI tools are not visible to external checks.', _NOTE))
    return out


def main():
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_dir / 'Concept_B_All_States.pdf'
    qa.ISSUES.clear()
    ident = {
        'org': 'AI Risk — Concept B (4 States)',
        'domain': 'example.com · atlassian.com · cursor.com · hackerrank.com',
        'title': 'AI Risk Concept B States',
        'assessment_date': '24 Nov 2026',
        'generated_date': '24 Nov 2026',
        'issuer': 'Cyberrank',
        'issuer_reason': None,
        'logo': None,
    }
    doc = ReportDoc(out_pdf, ident, subject='Section 10 AI Risk Concept B — all 4 conditional states')
    doc.pageTemplates = [t for t in doc.pageTemplates if t.id == 'interior'] + [
        t for t in doc.pageTemplates if t.id != 'interior']
    story = []
    for i, sc in enumerate(CASES):
        if i:
            story.append(PageBreak())
        story.append(C.Anchor(sc['id'], outline=sc['banner']))
        story += build_concept_b(sc)
    total = doc.render(story)
    issues = list(qa.ISSUES) + qa.check_pdf(out_pdf, skip_pages=(), table_parts=doc.table_parts,
                                            table_heads=C._TABLE_HEADS)
    counts = qa.write_report(out_pdf.with_suffix('.qa.json'), out_pdf, issues, pages=total)
    pdf = pymupdf.open(str(out_pdf))
    for i, pg in enumerate(pdf, 1):
        pg.get_pixmap(dpi=130).save(str(out_dir / f'concept_b_case-{i}.png'))
    pdf.close()
    print(f'{out_pdf}: {total} pages; QA {counts}')
    for iss in json.loads(out_pdf.with_suffix('.qa.json').read_text())['issues']:
        print(' ', iss['severity'], iss['check'], f'p{iss.get("page")}', iss['detail'][:120])


if __name__ == '__main__':
    main()
