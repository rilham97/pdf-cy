"""Section registry + state dispatch.

A section module ``cyberrank_report/sections/<spec.module>.py`` implements:

    build(data: dict, ctx: Ctx) -> list[Flowable]          # required: the body
    card(data, ctx) -> dict                                 # optional: state_card kwargs
    adjust(data, report) -> dict                            # optional: data with a corrected state
                                                            #   (e.g. pending_review when the payload
                                                            #   contradicts itself); never mutates data
    build_context(data, ctx) -> list[Flowable]              # optional: shown even when
                                                            #   not_assessed / not_applicable / unavailable
    verdict(data, ctx) -> str | None                        # optional: opener verdict when the payload
                                                            #   has no `summary`

render_section() draws the opener (eyebrow, H1, intro, state chip + verdict) and
the state card, then calls build(). Sections never draw their own opener/card.
"""
import importlib
from dataclasses import dataclass, field

from reportlab.platypus import PageBreakIfNotEmpty

from .. import components as C
from .. import theme as T

GROUPS = {
    'overview_and_priorities': 'Overview and priorities',
    'assessment_details': 'Assessment details',
    'appendices_and_references': 'Appendices and references',
}
NO_RESULT = ('not_assessed', 'not_applicable', 'unavailable')   # card replaces the body
WITH_CARD = ('clear', 'partial', 'pending_review', 'none_identified')   # card above the body
REFERENCE = ('appA', 'appB', 'appC')    # reference appendices: no result, so no state chip / card unless no-result


@dataclass(frozen=True)
class SectionSpec:
    id: str              # CLI id: s01..s15, appA..appD
    key: str             # key in report[source]
    number: str          # printed number / letter
    title: str           # fallback when data has no title
    group: str           # GROUPS key
    module: str          # module name in this package
    source: str = 'sections'
    toc_sub: str | None = None
    new_page: bool = True

    @property
    def anchor(self):
        return f'sec-{self.id}'


_A = 'appendices'
REGISTRY = [
    SectionSpec('s01', 'executive_overview', '01', 'Executive overview', 'overview_and_priorities',
                's01_executive_overview', toc_sub='Scope and coverage / rating overview / sector comparison'),
    SectionSpec('s02', 'priority_actions', '02', 'Priority actions', 'overview_and_priorities', 's02_priority_actions'),
    # assessment sections follow the demerit ledger A-J (rule letter in DEMERIT_RULES below)
    SectionSpec('s03', 'privacy', '03', 'Privacy', 'assessment_details', 's03_privacy'),
    SectionSpec('s04', 'vulnerabilities', '04', 'Vulnerabilities', 'assessment_details', 's04_vulnerabilities'),
    SectionSpec('s05', 'credential_exposure', '05', 'Credential exposure', 'assessment_details',
                's05_credential_exposure'),
    SectionSpec('s06', 'data_leak_history', '06', 'Data breach and leak history', 'assessment_details',
                's06_data_leak_history'),
    SectionSpec('s07', 'data_sovereignty', '07', 'Data sovereignty', 'assessment_details', 's07_data_sovereignty'),
    SectionSpec('s08', 'data_residency', '08', 'Data residency', 'assessment_details', 's08_data_residency'),
    SectionSpec('s09', 'legal_terms', '09', 'Legal terms & conditions', 'assessment_details', 's09_legal_terms'),
    SectionSpec('s10', 'ai_risk_governance', '10', 'AI risk and governance', 'assessment_details',
                's10_ai_risk_governance'),
    SectionSpec('s11', 'quantum_security', '11', 'Quantum security', 'assessment_details', 's11_quantum_security'),
    SectionSpec('s12', 'security_resourcing', '12', 'Security resourcing', 'assessment_details',
                's12_security_resourcing'),
    SectionSpec('s13', 'certifications', '13', 'Certifications', 'assessment_details', 's13_certifications'),
    SectionSpec('s14', 'fourth_party_vendors', '14', 'Fourth-party vendors', 'assessment_details',
                's14_fourth_party_vendors'),
    SectionSpec('s15', 'cloud_infrastructure', '15', 'Cloud infrastructure', 'assessment_details',
                's15_cloud_infrastructure'),
    SectionSpec('appA', 'a_about', 'A', 'About this report', 'appendices_and_references', 'app_a_about', _A),
    SectionSpec('appB', 'b_rating_scale', 'B', 'IISRI rating scale', 'appendices_and_references',
                'app_b_rating_scale', _A),   # full-page component: own page
    SectionSpec('appC', 'c_methodology', 'C', 'Methodology and supply-chain aggregation',
                'appendices_and_references', 'app_c_methodology', _A),   # one page, pairs with its locked page
    SectionSpec('appD', 'd_evidence_registers', 'D', 'Detailed evidence registers', 'appendices_and_references',
                'app_d_evidence_registers', _A),
]
BY_ID = {s.id: s for s in REGISTRY}
# demerit ledger rule -> section key (Aturan_Scoring_Teramati_Lengkap: ledger v2 A-J, one cap each)
DEMERIT_RULES = {'A': 'vulnerabilities', 'B': 'privacy', 'C': 'credential_exposure', 'D': 'data_leak_history',
                 'E': 'data_sovereignty', 'F': 'data_residency', 'G': 'legal_terms', 'H': 'ai_risk_governance',
                 'I': 'quantum_security', 'J': 'security_resourcing'}


@dataclass
class Ctx:
    """What a section gets besides its own data. ctx.c = components, ctx.t = theme."""
    spec: SectionSpec
    report: dict                    # full payload, read-only (cross references)
    identity: dict                  # display identity (org, domain, dates)
    state: str | None
    blueprint: bool = False
    c: object = field(default=C, repr=False)
    t: object = field(default=T, repr=False)

    @property
    def styles(self):
        return T.STYLES


def load(spec):
    """Section module, or None while it is not implemented yet."""
    try:
        return importlib.import_module(f'{__name__}.{spec.module}')
    except ModuleNotFoundError as e:
        if e.name != f'{__name__}.{spec.module}':
            raise
        return None


def default_card(data, state):
    """state_card kwargs from common payload fields; a module's card() overrides."""
    empty = data.get('empty_state_source') or {}
    reason = data.get('state_reason') or (C.reason_text(data) if data.get('reason_code') else None)
    if state == 'clear':
        reason = reason or empty.get('text')
    checked = data.get('what_checked') or empty.get('coverage') if state in WITH_CARD else None
    return {'reason': reason, 'what_checked': checked, 'next_step': data.get('next_step')}


def adjusted(spec, data, report):
    """Section data after the module's adjust() hook (state corrections the payload implies)."""
    mod = load(spec) if isinstance(data, dict) else None
    return mod.adjust(data, report) if mod and hasattr(mod, 'adjust') else data


# old nested shape (sections.privacy.<sub>) -> own section (sections.<key>); demerit rules E, F, G, J
LIFTED = {'sovereignty': 'data_sovereignty', 'residency': 'data_residency', 'terms_conditions': 'legal_terms',
          'resourcing': 'security_resourcing'}


def lift_privacy_subsections(report):
    """Load-time alias (in place, idempotent): a payload in the old shape keeps its Global360 sub-areas
    under sections.privacy; move each to its own section key. The sub-object's subtitle_source becomes
    the section intro. A key already present at section level wins; a null sub-object stays missing."""
    secs = report.get('sections') if isinstance(report, dict) else None
    priv = secs.get('privacy') if isinstance(secs, dict) else None
    if not isinstance(priv, dict):
        return report
    for old, new in LIFTED.items():
        if old not in priv:
            continue
        sub = priv.pop(old)
        if isinstance(sub, dict) and new not in secs:
            sub = dict(sub)
            if sub.get('subtitle_source') and not sub.get('intro_source'):
                sub['intro_source'] = sub.pop('subtitle_source')
            secs[new] = sub
    return report


def adjust_report(report):
    """Shallow copy of the report with every section adjusted (so the s01 rating overview sees the same state)."""
    lift_privacy_subsections(report)
    out = {**report}
    for spec in REGISTRY:
        src = out.get(spec.source)
        if isinstance(src, dict) and isinstance(src.get(spec.key), dict):
            out[spec.source] = {**src, spec.key: adjusted(spec, src[spec.key], report)}
    return out


def hold(data, reason_code, reason, state='pending_review'):
    """Copy of data moved to `state` with its reason (adjust() helper). Idempotent."""
    if data.get('state') == state and data.get('reason_code') == reason_code:
        return data
    from .. import qa
    qa.add('state_adjusted', 'info', f'{data.get("title") or reason_code}: {data.get("state")} -> {state} '
           f'({reason_code})', once=True)
    return {**data, 'state': state, 'reason_code': reason_code, 'state_reason': reason}


def render_section(spec, report, identity, blueprint=False):
    data = (report.get(spec.source) or {}).get(spec.key)
    if spec.id == 'appD' and not data:      # registers come from section data; only the frame reads this payload
        data = {'state': None}
    missing = data is None
    data = data or {'state': 'unavailable', 'state_reason': 'Section missing from the report data.'}
    if not blueprint and not missing:
        data = adjusted(spec, data, report)
    state = data.get('state')
    if spec.id in REFERENCE and state not in NO_RESULT:
        state = None      # a chip row would push one-page appendices (B) onto a second page
    ctx = Ctx(spec, report, identity, state, blueprint)
    mod = None if (blueprint or missing) else load(spec)
    verdict = data.get('summary') or (mod.verdict(data, ctx) if mod and hasattr(mod, 'verdict') else None)
    flow = [PageBreakIfNotEmpty()] if spec.new_page else []
    shown = T.shown_state(state, spec.key)
    if spec.key == 'executive_overview' and state == 'findings':
        shown = None      # a summary has no 'results present' state: chip only for partial / unavailable ...
    flow += C.section_opener(spec.number, data.get('title') or spec.title, shown,
                             verdict=verdict, intro=data.get('intro_source'),
                             key=spec.anchor, group=GROUPS[spec.group], icon=spec.key)
    if state in WITH_CARD or state in NO_RESULT:
        kw = default_card(data, state)
        if mod and hasattr(mod, 'card'):
            kw.update(mod.card(data, ctx))
        flow.append(C.state_card(shown or state, **kw))
    if state in NO_RESULT:
        extra = mod.build_context(data, ctx) if mod and hasattr(mod, 'build_context') else []
        if extra:      # the first context block travels with the card (no short block alone overleaf)
            flow += [C.keep(flow.pop(), extra[0])] + list(extra[1:])
        return flow
    flow += mod.build(data, ctx) if mod else blueprint_body(data, ctx)
    return flow


def blueprint_body(data, ctx):
    """Placeholder body for unimplemented sections: metrics + a map of the payload."""
    out = []
    metrics = [m for m in data.get('metrics') or [] if isinstance(m, dict)]
    if metrics:
        out.append(C.kpi_strip(metrics[:4]))
    rows = []
    for k, v in data.items():
        if k in ('number', 'title', 'group', 'state', 'summary', 'intro_source', 'metrics'):
            continue
        kind = (f'list of {len(v)}' if isinstance(v, list) else f'object, {len(v)} fields'
                if isinstance(v, dict) else C.fmt_value(v) if not isinstance(v, str)
                else v if len(v) <= 140 else f'text, {len(v)} characters')
        rows.append([k, kind])
    out += [C.heading('Blueprint: payload fields', 3),
            C.note(f'Section module "{ctx.spec.module}" not rendered; showing the fields it will draw from.'),
            C.compact_table(['Field', 'Content'], rows, dense=True)]
    return out
