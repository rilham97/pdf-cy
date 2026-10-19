"""10 AI risk and governance.

When the module was not assessed, the narrative signals are shown as context
only (RF-04): neutral styling, every area carries its own 'Not assessed' chip,
nothing reads as a result. A payload flag is_assessment_result=true is ignored while the
section has no result (QA warns). A narrative conclusion that plays down AI use next to
observed AI signals gets a reconciliation note; the narrative is quoted, never corrected.
"""
import re

from .. import qa
from ..text import val

NO_RESULT = ('not_assessed', 'not_applicable', 'unavailable')
DOWNPLAY = re.compile(r'\b(unlikely|no evidence|does not use|do not use|not use AI|no material)\b', re.I)

SIGNALS = {'ai_infrastructure': 'AI infrastructure', 'ai_hiring': 'AI-related hiring',
           'ai_assistant_mention': 'AI assistant mentioned'}
METHODS = {'csp_header_analysis': 'CSP / header analysis', 'careers_pages': 'Careers pages',
           'public_pages': 'Public pages'}
AREAS = [('annex_iii_high_risk_sector', 'EU AI Act Annex III high-risk sector'),
         ('public_ai_policy', 'Public AI policy'),
         ('privacy_policy_ai_disclosure', 'AI use explained in the privacy policy')]
NEXT_STEP = ('Run the AI risk and governance module for this organisation. It rates the areas listed below; '
             'the observations shown here are then replaced by assessed results.')


def _label(table, code):
    code = val(code)
    return table.get(code) or str(code or '').replace('_', ' ').capitalize() or 'Not recorded'


def card(data, ctx):
    return {} if ctx.state != 'not_assessed' or data.get('next_step') else {'next_step': NEXT_STEP}


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
    signals = [s for s in obs.get('signals_observed') or [] if isinstance(s, dict)]
    rows = _area_rows(obs, ctx)
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


def _area_rows(obs, ctx):
    c, rows = ctx.c, []
    if obs.get('stated_conclusion_source'):
        rows.append(['AI use in the service', obs['stated_conclusion_source'],
                     c.state_chip(ctx.state, dense=True)])
    if rows and obs.get('is_assessment_result') is True and ctx.state not in NO_RESULT:   # narrative, not rated
        rows[0][2] = c.chip('Observation', ctx.t.SLATE_400, dense=True)
    for key, label in AREAS:
        v = obs.get(key)
        if not isinstance(v, dict):
            continue
        text = v.get('source_label') or (c.missing_text(v) if c.is_missing(v) else _label({}, v.get('value')))
        rows.append([label, text, c.state_chip(v.get('state') or ctx.state, dense=True)])
    return rows


def build_context(data, ctx):
    return _observations(data, ctx)


def build(data, ctx):
    c = ctx.c
    items = [m for m in data.get('metrics') or [] if isinstance(m, dict)]
    signals = (data.get('narrative_observation') or {}).get('signals_observed')
    if signals is not None:
        items.append({'label': 'AI signals observed', 'value': len(signals), 'unit': 'signals'})
    return ([c.kpi_strip(items, per_row=3)] if items else []) + _observations(data, ctx)
