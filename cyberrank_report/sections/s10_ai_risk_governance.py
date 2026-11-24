"""10 AI Risk (Section 10, demerit rule H).

Supports two payload shapes:
  * New AI Risk schema (Concept B, owner-approved 2026-11-24):
    - `risk_level` / `riskLevel` (Low / Medium / High / Critical)
    - `use_of_ai` / `useOfAi` ({level: Unlikely|Possible|Likely|Almost certain, position?, quote?, source_url?})
    - `capabilities[]` (e.g. 'LLM text generation', 'Scoring or ranking people')
    - `ai_providers[]` / `aiProviders[]` (optional — shown inside Observed AI use only when non-empty)
    - `high_risk_uses[]` / `highRiskUses[]` (EU AI Act Annex III — section shown only when non-empty)
    - `governance` ({ai_policy, iso_42001} — shown when Use of AI != Unlikely or any control found;
      otherwise collapsed into a calm clear card with What was checked)
  * Legacy `narrative_observation` schema (preserved verbatim for existing payloads and RF-04 context mode).
"""
import re

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Spacer, Table, TableStyle

from .. import components as C
from .. import icons as I
from .. import qa
from .. import theme as T
from ..text import val

NO_RESULT = ('not_assessed', 'not_applicable', 'unavailable')
DOWNPLAY = re.compile(r'\b(unlikely|no evidence|does not use|do not use|not use AI|no material)\b', re.I)

USE_LEVELS = ('Unlikely', 'Possible', 'Likely', 'Almost certain')
RISK_LEVELS = ('Low', 'Medium', 'High', 'Critical')
RISK_COLORS = {
    'Low': T.STATUS['good'],
    'Medium': T.STATUS['attention'],
    'High': T.SEVERITY['high'],
    'Critical': T.SEVERITY['critical'],
}

SIGNALS = {'ai_infrastructure': 'AI infrastructure', 'ai_hiring': 'AI-related hiring',
           'ai_assistant_mention': 'AI assistant mentioned'}
METHODS = {'csp_header_analysis': 'CSP / header analysis', 'careers_pages': 'Careers pages',
           'public_pages': 'Public pages'}
AREAS = [('annex_iii_high_risk_sector', 'EU AI Act Annex III high-risk sector'),
         ('public_ai_policy', 'Public AI policy'),
         ('privacy_policy_ai_disclosure', 'AI use explained in the privacy policy')]
NEXT_STEP = ('Run the AI risk module for this organisation. It evaluates observed AI use, capabilities, '
             'EU AI Act high-risk classification and public AI governance controls.')

_H2_T = T.STYLES['h2'].clone('s10_h2', spaceBefore=T.SP_MD, spaceAfter=5)
_QUOTE = T.STYLES['body'].clone('s10_quote', fontSize=8.6, leading=12.5, spaceAfter=3)
_URL = T.STYLES['cell_tech'].clone('s10_url', textColor=T.NAVY)
_NOTE = T.STYLES['note'].clone('s10_note', hyphenationLang='', embeddedHyphenation=0)
_KPI_MED = T.STYLES['kpi_value'].clone('s10_kpi_med', fontSize=16, leading=20)
_KPI_SUB = T.STYLES['kpi_value'].clone('s10_kpi_sub', fontSize=16, leading=20, textColor=T.HEADING)


# --- new AI Risk payload helpers -------------------------------------------------
def is_structured_ai(data):
    """True when the section carries the structured AI Risk payload (Concept B)."""
    if not isinstance(data, dict):
        return False
    return any(k in data for k in (
        'use_of_ai', 'useOfAi', 'risk_level', 'riskLevel', 'capabilities',
        'ai_providers', 'aiProviders', 'governance', 'high_risk_uses', 'highRiskUses',
    ))


def _norm_level(raw, allowed, default):
    s = str(val(raw) or '').strip()
    for a in allowed:
        if s.lower() == a.lower():
            return a
    return default


def _use_of_ai(data):
    raw = data.get('use_of_ai') or data.get('useOfAi')
    if isinstance(raw, str):
        raw = {'level': raw}
    raw = raw if isinstance(raw, dict) else {}
    return {
        'level': _norm_level(raw.get('level'), USE_LEVELS, 'Unlikely'),
        'position': raw.get('position'),
        'quote': val(raw.get('quote') or raw.get('evidence_quote') or raw.get('evidenceQuote')),
        'source_url': val(raw.get('source_url') or raw.get('sourceUrl') or raw.get('url')),
    }


def risk_level(data):
    return _norm_level(data.get('risk_level') or data.get('riskLevel'), RISK_LEVELS, 'Low')


def _capabilities(data):
    raw = data.get('capabilities') or data.get('capability_tags') or data.get('capabilityTags') or []
    return [str(x).strip() for x in raw if str(x or '').strip()] if isinstance(raw, list) else []


def _ai_providers(data):
    raw = data.get('ai_providers') or data.get('aiProviders') or []
    return [str(x).strip() for x in raw if str(x or '').strip()] if isinstance(raw, list) else []


def high_risk_uses(data):
    raw = data.get('high_risk_uses') or data.get('highRiskUses') or []
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        cat = str(val(item.get('category') or item.get('title')) or '').strip()
        clause = str(val(item.get('clause') or item.get('reference') or item.get('annex_clause')) or '').strip()
        if not (cat or clause):
            continue
        out.append({
            'category': cat or 'EU AI Act high-risk use',
            'clause': clause or 'Annex III',
            'quote': val(item.get('quote') or item.get('evidence_quote') or item.get('evidenceQuote')),
            'source_url': val(item.get('source_url') or item.get('sourceUrl') or item.get('url')),
        })
    return out


def _governance(data):
    raw = data.get('governance')
    raw = raw if isinstance(raw, dict) else {}

    def item(keys, default_label, default_missing):
        v = next((raw.get(k) for k in keys if raw.get(k) is not None), None)
        if not isinstance(v, dict):
            return {'found': False, 'label': default_label, 'note': default_missing, 'url': None}
        found = bool(v.get('found')) if 'found' in v else bool(v.get('url') or v.get('source_url'))
        url = val(v.get('url') or v.get('source_url') or v.get('sourceUrl'))
        lbl = str(val(v.get('label')) or (f'{default_label} published' if found and default_label == 'AI policy'
                                          else default_label)).strip()
        note = val(v.get('note') or v.get('description'))
        if not found and not note:
            note = default_missing
        return {'found': found, 'label': lbl, 'note': note, 'url': url}

    return {
        'ai_policy': item(('ai_policy', 'aiPolicy'), 'AI policy', "Not found on the vendor's website"),
        'iso_42001': item(('iso_42001', 'iso42001'), 'ISO 42001 certificate',
                          "Not found on the vendor's website or in certification body registers"),
    }


def _url_flow(url, width=320):
    lines = C.tech_lines(str(url), width, _URL.fontName, _URL.fontSize)
    shown = '<br/>'.join(C.esc(ln) for ln in lines)
    return C.M(f'<a href="{C.esc(str(url))}" color="{C.hexstr(T.NAVY)}">{shown}</a>', _URL)


# --- visual primitives (Concept B) ------------------------------------------------
class TagFlow(Flowable):
    """Inline bordered tags wrapping cleanly across lines (capabilities / AI providers)."""
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

    def minWidth(self):
        return max((stringWidth(t, T.REGULAR, self.FS) + 2 * self.PAD_H for t in self.tags), default=0.0)


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
    card_box = Table([[blocks]], colWidths=[T.CW], hAlign='LEFT', spaceBefore=2, spaceAfter=T.SP_SM)
    card_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), T.SURFACE),
        ('LINEBEFORE', (0, 0), (0, -1), 2.5, T.STATUS['attention']),
        ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('NOSPLIT', (0, 0), (-1, -1)),
    ]))
    return card_box


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


def _build_structured(data, ctx):
    c = ctx.c
    u = _use_of_ai(data)
    rl = risk_level(data)
    caps = _capabilities(data)
    provs = _ai_providers(data)
    hr = high_risk_uses(data)
    gov = _governance(data)
    any_gov = gov['ai_policy']['found'] or gov['iso_42001']['found']

    # 3-column posture strip (owner decision 2026-11-24: text scale captions, no bar, no governance count)
    w_mid = (T.CW - 2 * T.GUTTER) / 3.0 + 24
    w_side = (T.CW - 2 * T.GUTTER - w_mid) / 2.0
    t1 = [c.P(rl, _KPI_MED, textColor=RISK_COLORS[rl]),
          c.P('AI risk level', 'kpi_label', spaceBefore=2),
          c.P('Scale: Low · Medium · High · Critical', 'note_flush', spaceBefore=2)]
    t2 = [c.P(u['level'], _KPI_MED),
          c.P('Use of AI', 'kpi_label', spaceBefore=2),
          c.P('Scale: Unlikely · Possible · Likely · Almost certain', 'note_flush', spaceBefore=2)]
    if hr:
        t3_val = c.P(hr[0]['clause'], _KPI_MED, textColor=T.STATUS['attention'])
        t3_lbl = 'EU AI Act high-risk detected'
    else:
        t3_val = c.P('None found', _KPI_SUB)
        t3_lbl = 'EU AI Act high-risk (Annex III)'
    t3 = [t3_val, c.P(t3_lbl, 'kpi_label', spaceBefore=2)]

    strip = Table([[t1, '', t2, '', t3]], colWidths=[w_side, T.GUTTER, w_mid, T.GUTTER, w_side],
                  hAlign='LEFT', spaceAfter=T.SP_MD)
    strip.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LINEABOVE', (0, 0), (0, 0), 0.75, T.RULE),
        ('LINEABOVE', (2, 0), (2, 0), 0.75, T.RULE),
        ('LINEABOVE', (4, 0), (4, 0), 0.75, T.RULE),
    ]))
    out = [strip]

    # 1. Observed AI use — order: Public evidence -> Observed capabilities -> AI providers (optional)
    ev_w = T.CW - T.KV_LABEL_W - 14
    kv = []
    if u.get('quote'):
        cell = [c.P(f'“{u["quote"]}”', _QUOTE)]
        if u.get('source_url'):
            cell.append(_url_flow(u['source_url'], ev_w))
        kv.append(('Public evidence', cell))
    if caps:
        kv.append(('Observed capabilities', TagFlow(caps)))
    if provs:
        kv.append(('AI providers', TagFlow(provs, accent=T.NAVY, bg=T.SURFACE, text_color=T.HEADING)))
    if kv:
        out.append(c.heading('Observed AI use', 2, style=_H2_T))
        out.append(c.key_value_list(kv))

    # 2. High-risk use · EU AI Act — rendered ONLY when detected
    if hr:
        out.append(c.heading('High-risk use · EU AI Act', 2, style=_H2_T))
        out.append(_high_risk_card(hr))

    # 3. AI governance — table when Use of AI != Unlikely or any control found; else 1 concise line (no repeats)
    if u['level'] != 'Unlikely' or any_gov:
        out.append(c.heading('AI governance', 2, style=_H2_T))
        out.append(_gov_table(gov))
        out.append(c.P('Scope note: Assessment is based on publicly accessible pages and certification registers; '
                       'internal or private AI tools are not visible to external checks.', _NOTE))
    else:
        out.append(c.P('Checked public website pages and certification registers: no AI capabilities, '
                       'AI providers, AI policy, ISO 42001 certificate, or EU AI Act Annex III high-risk use '
                       'was found. Internal or private AI tools are outside external visibility.', _NOTE))
    return out


# --- section hooks ----------------------------------------------------------------
def verdict(data, ctx):
    if not is_structured_ai(data) or ctx.state in NO_RESULT:
        return None
    u = _use_of_ai(data)
    rl = risk_level(data)
    hr = high_risk_uses(data)
    gov = _governance(data)
    if u['level'] == 'Unlikely' and not hr:
        return f'AI risk is assessed as {rl}; public signals indicate AI use is unlikely.'
    bits = [f'AI risk is assessed as {rl} with {u["level"].lower()} AI use observed on public pages.']
    if hr:
        bits.append(f'Potential EU AI Act high-risk use identified ({", ".join(h["clause"] for h in hr)}).')
    else:
        bits.append('No EU AI Act Annex III high-risk use was found on the public website.')
    found_gov = [lbl for lbl, g in (('AI policy', gov['ai_policy']), ('ISO 42001', gov['iso_42001'])) if g['found']]
    if found_gov:
        bits.append(f'Public governance evidence found: {", ".join(found_gov)}.')
    return ' '.join(bits)


def card(data, ctx):
    if ctx.state == 'clear' and is_structured_ai(data):
        if not (data.get('state_reason') or data.get('reason_code') or
                (data.get('empty_state_source') or {}).get('text')):
            return {'skip': True}      # posture strip + concise scope note already carry it without repetition
    return {} if ctx.state != 'not_assessed' or data.get('next_step') else {'next_step': NEXT_STEP}


# --- legacy narrative_observation support (RF-04 context & old payloads) ---------
def _label(table, code):
    code = val(code)
    return table.get(code) or str(code or '').replace('_', ' ').capitalize() or 'Not recorded'


def _observations(data, ctx):
    c = ctx.c
    obs = data.get('narrative_observation') or {}
    if not obs:
        return []
    context_only = obs.get('is_assessment_result') is not True or ctx.state in NO_RESULT
    if obs.get('is_assessment_result') is True and ctx.state in NO_RESULT:
        qa.add('data_mismatch', 'warn', f's10: is_assessment_result=true while the section is {ctx.state}; '
               'shown as context only', once=True)
    out = [c.heading('Observations recorded for context' if context_only else 'What was observed', 2)]
    if context_only:
        out.append(c.P('Recorded during data collection. These observations are not an assessment result: '
                       'they are not rated, not scored and not counted in the IISRI rating.', 'body',
                       textColor=ctx.t.MUTED))
    signals = _signals(obs)
    rows = _area_rows(obs, ctx, context_only)
    if obs.get('text_source'):      # always quoted in full: the tables carry only parts of it
        out += [c.heading(obs.get('subtitle_source') or 'Narrative as recorded', 3), c.P(obs['text_source'])]
    if signals:
        out.append(c.heading('Signals observed', 3))
        out.append(c.compact_table(
            ['Signal', 'Method', 'Example as recorded'],
            [[_label(SIGNALS, s.get('signal')), _label(METHODS, s.get('method')),
              s.get('example_source') or {'value': None, 'reason': 'no example recorded'}] for s in signals]))

    concl = val(obs.get('stated_conclusion_source')) or ''
    if signals and DOWNPLAY.search(concl):
        out.append(c.note(f'The recorded conclusion (“{concl.strip()}”) sits beside {len(signals)} AI signal'
                          f'{"s" if len(signals) != 1 else ""} observed above. The assessment data does not explain '
                          'how the signals were weighed, so the two are shown as recorded and not reconciled here.'))
    if rows:
        out.append(c.heading('Areas an AI assessment rates' if context_only else 'Areas rated', 3))
        out.append(c.compact_table(['Area', 'Recorded reading' if context_only else 'Result', 'Status'], rows,
                                   widths=[150, ctx.t.CW - 150 - 92, 92]))
    return out


def _signals(obs):
    """Signal objects as the table prints them (non-object items are skipped, and not counted)."""
    sig = obs.get('signals_observed')
    return [s for s in sig if isinstance(s, dict)] if isinstance(sig, list) else []


def _area_rows(obs, ctx, context_only):
    """Status chips: the narrative conclusion is never rated ('Observation'); in context mode a result
    state (e.g. findings) is not shown either, so the rows stay neutral under the 'not rated' disclaimer."""
    c, rows = ctx.c, []
    observation = c.chip('Observation', ctx.t.SLATE_400, dense=True)

    def status(state):
        return observation if context_only and state not in NO_RESULT else c.state_chip(state, dense=True)
    if obs.get('stated_conclusion_source'):
        rows.append(['AI use in the service', obs['stated_conclusion_source'],
                     observation if ctx.state not in NO_RESULT else c.state_chip(ctx.state, dense=True)])
    for key, label in AREAS:
        v = obs.get(key)
        if not isinstance(v, dict):
            continue
        text = v.get('source_label') or (c.missing_text(v) if c.is_missing(v) else _label({}, v.get('value')))
        rows.append([label, text, status(v.get('state') or ctx.state)])
    return rows


def build_context(data, ctx):
    return _observations(data, ctx)


def build(data, ctx):
    if is_structured_ai(data):
        return _build_structured(data, ctx)
    c = ctx.c
    items = [m for m in data.get('metrics') or [] if isinstance(m, dict)]
    obs = data.get('narrative_observation') or {}
    if isinstance(obs.get('signals_observed'), list):      # counts the rows the signals table prints
        items.append({'label': 'AI signals observed', 'value': len(_signals(obs)), 'unit': 'signals'})
    return ([c.kpi_strip(items, per_row=3)] if items else []) + _observations(data, ctx)
