"""01 Executive overview: rating badge + score context, scope and coverage, rating overview
(score meters for the aspects with a system score, then a two-column checklist of every assessed
aspect 03-15 with one result line and its state), sector comparison, then a pointer to 02. The
demerit ledger is never printed. Sector and risk-band strings are rendered
exactly as the payload gives them (the system localises them); colours stay keyed on the enum codes.

Page references to other sections are resolved from the previous multiBuild
pass (doc.anchors_prev) through Deferred; a section that is not in the document
prints its name without a page or link.
"""
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Spacer, Table, TableStyle

from . import DEMERIT_RULES, REGISTRY
from .. import components as c
from .. import theme as T

S = T.STYLES
GRADE_BIG = S['h1'].clone('grade_big', spaceBefore=0, spaceAfter=2, keepWithNext=0)
PANEL_LABEL = S['eyebrow'].clone('panel_label', spaceBefore=0, spaceAfter=3, keepWithNext=0)
NO_RESULT = ('not_assessed', 'not_applicable', 'unavailable')


# --- shared helpers (s02 imports these) ----------------------------------------
class Deferred(Flowable):
    """Flowable built at layout time by make(anchor_pages). anchor_pages is the
    previous pass's {anchor key: page}, so links point only at anchors that exist."""

    def __init__(self, make):
        super().__init__()
        self.make = make

    def _build(self):
        doc = getattr(getattr(self, 'canv', None), '_doctemplate', None)
        self._f = self.make(getattr(doc, 'anchors_prev', None) or {})
        return self._f

    def wrap(self, aw, ah):
        self.width, self.height = self._build().wrapOn(self.canv, aw, ah)
        return self.width, self.height

    def split(self, aw, ah):
        return self._build().splitOn(self.canv, aw, ah)

    def draw(self):
        self._f.drawOn(self.canv, 0, 0)

    def getSpaceBefore(self):
        return (getattr(self, '_f', None) or self._build()).getSpaceBefore()

    def getSpaceAfter(self):
        return (getattr(self, '_f', None) or self._build()).getSpaceAfter()


def assessed():
    return [s for s in REGISTRY if s.group == 'assessment_details']


def spec_for(key):
    return next((s for s in REGISTRY if s.key == key), None)


def section_data(report, spec):
    return (report.get(spec.source) or {}).get(spec.key)


def section_ref(key, report, pages):
    """'08 Credential exposure, page 14' as trusted markup; linked when the anchor exists."""
    spec = spec_for(key)
    if spec is None:
        return c.esc(str(key).replace('_', ' '))
    title = (section_data(report, spec) or {}).get('title') or spec.title
    label = ('Appendix ' if spec.source == 'appendices' else '') + f'{spec.number} {title}'
    page = pages.get(spec.anchor)
    if not page:
        return c.esc(label)
    return f'<a href="#{spec.anchor}" color="{c.hexstr(T.NAVY)}">{c.esc(label)}, page {page}</a>'


def resolve(report, path):
    node = report
    for part in str(path or '').split('.'):
        node = node.get(part) if isinstance(node, dict) else None
    return node


def two_up(left, right):
    t = Table([[left, '', right]], colWidths=[T.COL2, T.GUTTER, T.COL2], hAlign='LEFT')
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                           ('RIGHTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 0),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    t.spaceAfter = T.SP_SM
    return t


def _lc(label):
    return label if label[1:2].isupper() else label[:1].lower() + label[1:]


def kv_block(pairs, width=None, label_width=None, dense=False):
    """key_value_list, except null values sharing one reason collapse into a single
    note line ('Not provided in the assessment data: net score, point pool.')."""
    why = lambda v: c.sentence(c.reason_text(v)) if not isinstance(v, Flowable) and c.is_missing(v) else None
    groups = {}
    for k, v in pairs:
        if why(v):
            groups.setdefault(why(v), []).append(k)
    collapse = {r: ks for r, ks in groups.items() if len(ks) > 1}
    keep = [(k, v) for k, v in pairs if why(v) not in collapse]
    out = [c.key_value_list(keep, width=width, label_width=label_width, dense=dense)] if keep else []
    out += [c.P(f'{r.rstrip(".")}: {", ".join(_lc(k) for k in ks)}.', 'note_flush', spaceBefore=4)
            for r, ks in collapse.items()]
    return out


def pointer_line(markup):
    """Sapphire-ruled one-liner, same look as the register pointer."""
    t = Table([[c.M(markup, 'pointer')]], colWidths=[T.CW], hAlign='LEFT')
    t.setStyle(TableStyle([('LINEBEFORE', (0, 0), (0, 0), 2, T.SAPPHIRE),
                           ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                           ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
    t.spaceBefore, t.spaceAfter = T.SP_SM, T.SP_MD
    return t


# --- rating badge -----------------------------------------------------------------
class GradeScale(Flowable):
    """Ten grade segments, D..AAA (worst left, best right); the current grade is taller, outlined and labelled in Medium."""
    GAP, BAR, LABEL = 2.0, 6.0, 9.0

    def __init__(self, grade):
        super().__init__()
        self.grade = grade

    def wrap(self, aw, ah):
        self.width, self.height = aw, self.LABEL + 4 + self.BAR + 3
        return self.width, self.height

    def draw(self):
        cv, grades = self.canv, T.GRADE_BAR
        w = (self.width - self.GAP * (len(grades) - 1)) / len(grades)
        y = self.LABEL + 4
        for i, g in enumerate(grades):
            x, cur = i * (w + self.GAP), g == self.grade
            cv.setFillColor(T.GRADE[g])
            if cur:
                cv.setStrokeColor(T.HEADING)
                cv.setLineWidth(1)
                cv.rect(x, y - 2, w, self.BAR + 5, stroke=1, fill=1)
            else:
                cv.rect(x, y, w, self.BAR, stroke=0, fill=1)
            cv.setFillColor(T.HEADING if cur else T.MUTED)
            cv.setFont(T.MEDIUM if cur else T.LIGHT, S['note'].fontSize)
            cv.drawCentredString(x + w / 2, 1.5, g)


def band_note(rating, report):
    """RF-10: the source's band text vs the Appendix B meaning of the same grade."""
    norm = lambda x: ' '.join(str(x or '').split())
    g = str(rating.get('grade') or '').upper()
    rows = (resolve(report, 'appendices.b_rating_scale') or {}).get('rows') or []
    ref = next((r.get('meaning_source') for r in rows if isinstance(r, dict) and r.get('grade') == g), None)
    if ref and norm(ref) != norm(rating.get('band_description_source')):
        return (f'Wording as printed in the source; it differs from the {g} definition in Appendix B '
                'and is held for review.')
    return None


def band_chip(rating):
    """Risk-band chip: colour from the enum code (`risk_band`), text exactly as the system printed it
    (`risk_band_label_source`, localised, e.g. 'Rendah'); never translated or mapped."""
    band = str(rating.get('risk_band') or '').lower()
    shown = rating.get('risk_band_label_source')
    if band not in T.IMPACT and not shown:
        return []
    text = f'{band.capitalize()} risk band' if not shown or str(shown).lower() == band else f'Risk band: {shown}'
    return [c.chip(text, T.IMPACT.get(band, T.UNSCANNED))]


def rating_panel(rating, snapshot, report, pages):
    g = str(rating.get('grade') or '').upper()
    left = [c.P(rating.get('rating_name') or 'Rating', PANEL_LABEL)]
    if g in T.GRADE:
        left += [c.P(g, GRADE_BIG), c.chip(rating.get('grade_mark') or T.GRADE_MARK[g], T.GRADE[g])]
    else:
        left += [c.P('Grade not available', 'kpi_na', spaceBefore=2),
                 c.P(c.sentence(c.reason_text({'reason_code': rating.get('grade_reason_code')})), 'note_flush')]
    left += band_chip(rating)
    pairs = [('Net score', rating.get('net')), ('Point pool', rating.get('pool')),
             ('Score context', snapshot.get('score_context')),
             ('Methodology version', c.fmt_version(snapshot.get('methodology_version')))]
    pairs = [(k, v if v is not None else {'value': None, 'reason_code': 'not_printed_in_source'}) for k, v in pairs]
    pad = 12
    right_w = T.CW - T.COL3 - pad - T.GUTTER          # right column incl. its right padding
    right = [c.P('Score context', PANEL_LABEL)] + kv_block(pairs, width=right_w - pad, dense=True, label_width=92)
    rows, cmds = [[left, '', right], [GradeScale(g), '', '']], []
    if rating.get('band_description_source'):
        rows.append([c.P(rating['band_description_source'], 'body_flush'), '', ''])
        diff = band_note(rating, report)
        if diff:
            rows.append([c.P(diff, 'note_flush'), '', ''])
            cmds.append(('SPAN', (0, len(rows) - 1), (-1, len(rows) - 1)))
    rows.append([c.M('Meaning of every grade: ' + section_ref('b_rating_scale', report, pages), 'note_flush'), '', ''])
    t = Table(rows, colWidths=[T.COL3 + pad, T.GUTTER, right_w], hAlign='LEFT')
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('SPAN', (0, 1), (-1, 1)), ('SPAN', (0, 2), (-1, 2)), ('SPAN', (0, -1), (-1, -1)),
        ('BOX', (0, 0), (-1, -1), 0.75, T.RULE),
        ('LINEBEFORE', (0, 0), (0, -1), 3, T.GRADE.get(g, T.UNSCANNED)),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (0, -1), pad), ('RIGHTPADDING', (-1, 0), (-1, 0), pad),
        ('RIGHTPADDING', (0, 1), (0, -1), pad),         # spanned rows use their first cell's padding
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 12), ('TOPPADDING', (0, 1), (-1, 1), 6),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 12),
    ] + cmds))
    t.spaceAfter = T.SP_MD
    return t


# --- scope and coverage -----------------------------------------------------------
def scope_block(data, ctx):
    scope = data.get('scope_and_coverage') or {}
    ident, snap = ctx.report.get('identity') or {}, ctx.report.get('snapshot') or {}
    nr = {'value': None, 'reason_code': 'not_printed_in_source'}
    left = [('Organisation', ident.get('organisation_name') or nr),
            ('Primary domain', scope.get('primary_domain') or ident.get('domain') or nr),
            ('Sector', ident.get('sector') or ident.get('industry') or nr),
            ('Assessment date', c.fmt_date(snap.get('assessed_at')) if snap.get('assessed_at') else nr)]
    right = [('Organisation ID', ident.get('organisation_id', nr)),
             ('Assessment ID', snap.get('assessment_id', nr)),
             ('Eligible targets', scope.get('eligible_targets', nr)),
             ('Coverage', scope.get('coverage_percent', nr))]
    out = [c.heading('Scope and coverage', 2),
           two_up(kv_block(left, width=T.COL2, label_width=96),
                  kv_block(right, width=T.COL2, label_width=96))]
    targets = [m for m in scope.get('observed_targets') or [] if isinstance(m, dict)]
    if targets:
        out += [c.heading('Observed targets', 3), c.kpi_strip(targets)]
    if scope.get('coverage_statement_source'):
        out.append(c.P(scope['coverage_statement_source'], 'body'))
    if scope.get('method_statement_source'):
        out.append(c.note(scope['method_statement_source']))
    if ident.get('description_source'):   # long source copy: note type keeps 01 to two pages
        out.append(c.keep(c.heading('Organisation profile', 3), c.note(ident['description_source']),
                          *c.flag_notes(ident, ctx.report)))      # e.g. a source typo, printed as recorded
    return out


def rule_section(rule):
    """Section number for a ledger rule ('E' or 'E Sovereignty' -> '07'), else ''."""
    spec = spec_for(DEMERIT_RULES.get(str(rule or '').strip()[:1].upper()))
    return spec.number if spec else ''


def ledger_table(ledger):
    nr = {'value': None, 'reason_code': 'not_printed_in_source'}
    rows, spans = [], []
    for i, r in enumerate(ledger, start=1):
        nums = [r.get(k, nr) for k in ('flags', 'demerit', 'cap')]
        if all(c.is_missing(v) for v in nums):     # one reason across the numeric cells
            nums, spans = [nums[0], '', ''], spans + [('SPAN', (3, i), (5, i))]
        rows.append([r.get('rule'), rule_section(r.get('rule')), r.get('label') or r.get('check')] + nums)
    t = c.compact_table(['Rule', 'Section', 'Check', 'Flags', 'Demerit', 'Cap'], rows, numeric_cols=(3, 4, 5),
                        widths=[38, 52, T.CW - 90 - 3 * 76, 76, 76, 76])
    t.setStyle(TableStyle(spans))
    return t


# --- rating overview (concept A, approved 2026-10-19) -------------------------------
# Scores first (the five aspects with a system percent score), then a two-column checklist of every
# assessed aspect: number | name + one result line | state chip. The result line is read from the
# section's own data (the counts its page prints); nothing is computed into a score.
SCORED = {'privacy': 'privacy_score', 'vulnerabilities': 'vulnerability_score',
          'credential_exposure': 'credential_score', 'data_leak_history': 'data_leak_score',
          'certifications': 'compliance_score'}
WORDS = ('no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven',
         'twelve', 'thirteen', 'fourteen', 'fifteen')
HX, MU, NV = c.hexstr(T.HEADING), c.hexstr(T.MUTED), c.hexstr(T.NAVY)
NA = 'na'       # the aspect normally has a score, but none is given in this payload
H2_TIGHT = S['h2'].clone('h2_overview', keepWithNext=0)


def _word(n):
    return WORDS[n] if 0 <= n < len(WORDS) else c.fmt_number(n)


def _int(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _metric(ms, mid):
    return _int(next((m.get('value') for m in ms or [] if isinstance(m, dict) and m.get('id') == mid), None))


def count(n, one, many, qual=()):
    """(number, noun phrase agreeing with n, qualifiers)."""
    return c.fmt_number(n), one if n == 1 else many, list(qual)


def worded(text):
    return '', text, []


def _privacy(sec, report):
    from .s03_privacy import _metrics, _val
    policy = sec.get('policy') or {}
    if _val(policy.get('policy_state')) == 'excluded_no_policy':
        return worded('No privacy policy (excluded)')
    n = _metric(_metrics(sec), 'active_issues')
    issues = [i for i in policy.get('issues') or [] if isinstance(i, dict)]
    n = len(issues) if n is None and issues else n
    return None if n is None else count(n, 'active privacy issue', 'active privacy issues')


def _vulnerabilities(sec, report):
    from .s04_vulnerabilities import _severity_groups
    n = _metric(sec.get('metrics'), 'finding_types')
    if n is None and isinstance(sec.get('findings'), list):
        n = len([f for f in sec['findings'] if isinstance(f, dict)])
    if n is None:
        return None
    tiers = [f'{c.fmt_number(v)} {k.title()}' for k, v, _ in _severity_groups(sec) if _int(v)]   # zero tiers omitted
    return count(n, 'finding type', 'finding types', tiers)


def _credentials(sec, report):
    from .s05_credential_exposure import derive
    from ..page import identity_from_report
    d = derive(sec, report, identity_from_report(report))      # register rows, as the section's pointer counts
    if d['analysed'] or sec.get('state') == 'clear':
        return count(d['analysed'], 'exposed account record', 'exposed account records')
    return worded('No register rows listed') if d['headline'] else None


def _leaks(sec, report):
    from .s06_data_leak_history import _inaccurate, _resolved, merge_events
    events = merge_events([e for e in sec.get('events') or [] if isinstance(e, dict)])
    n = len(events) if events else _metric(sec.get('metrics'), 'events_reported')
    n = 0 if n is None and sec.get('state') == 'clear' else n
    if n is None:
        return None
    if n == 0:
        return '0', 'breach or leak events', []
    qual = [f'{k} {w}' for k, w in ((sum(map(_resolved, events)), 'resolved'),
                                     (sum(map(_inaccurate, events)), 'reported inaccurate')) if k]
    return count(n, 'event', 'events', qual)


def _sovereignty(sec, report):
    from ._shared import MATCH, matched
    return worded(MATCH[matched(sec)][0])


def _residency(sec, report):
    from .. import geo_map as G
    hosting = [h for h in sec.get('observed_hosting') or [] if isinstance(h, dict)]
    vm = G.entries(hosting, sec.get('allowed_set') or [], compare=not sec.get('_no_preference'))
    hosted = list(dict.fromkeys(e['a2'] for e in vm['hosted']))
    if not hosted:
        return worded('Hosting countries not identified') if hosting else None
    if not vm['compare']:
        return count(len(hosted), 'hosting country', 'hosting countries')
    out = len({e['a2'] for e in vm['hosted'] if e['kind'] == 'mismatch'})
    noun = 'hosting country' if len(hosted) == 1 else 'hosting countries'
    return f'{out} of {len(hosted)}', f'{noun} outside the preference', []


def _legal(sec, report):
    from .s09_legal_terms import _clauses, _raw
    n = _clauses(sec, _raw(sec))[0]
    if n is not None:
        return f'{n} of 2', 'customer-protection clauses found', []
    return worded('No login or payment portal detected') if sec.get('portal_detected') is False else None


def _counted(mid, one, many):
    """Result read from one count metric of the section (0 when the section is clear without it)."""
    def read(sec, report):
        n = _metric(sec.get('metrics'), mid)
        n = 0 if n is None and sec.get('state') == 'clear' else n
        return None if n is None else count(n, one, many)
    return read


def _resourcing(sec, report):
    from .s12_security_resourcing import KINDS, ROLE
    ev = [c.val(sec.get(f'{k}_role_evidence')) for k in KINDS]
    if not any(e in ROLE for e in ev):
        return None
    gap = sum(e not in ROLE for e in ev)
    return (f'{ev.count("detected")} of {len(KINDS)}', 'privacy and security roles with public evidence',
            [f'{gap} not recorded'] if gap else [])


def _certifications(sec, report):
    from .s13_certifications import approval, std_key
    certs = [x for x in sec.get('certificates') or [] if isinstance(x, dict)]
    live = [x for x in certs if approval(x) != 'rejected']
    qual = [f'{k} {w}' for k, w in ((sum(approval(x) == 'pending' for x in live), 'awaiting approval'),
                                     (len(certs) - len(live), 'rejected')) if k]
    return count(len({std_key(x) for x in live}), 'certification', 'certifications', qual)


def _vendors(sec, report):
    from .s14_fourth_party_vendors import needs_a_look, tier
    vendors = [v for v in sec.get('vendors') or [] if isinstance(v, dict)]
    if not vendors:
        return count(0, '', 'connected organisations')
    look = len(needs_a_look(vendors, report, tier(vendors)[1]))      # the section's 'Needs a look (n of N)'
    return count(len(vendors), 'connected organisation', 'connected organisations',
                 [f'{look} need{"s" if look == 1 else ""} a look'] if look else [])


def _cloud(sec, report):
    n = _metric(sec.get('metrics'), 'cloud_providers_detected')
    if n is None and isinstance(sec.get('providers'), list):
        n = len([p for p in sec['providers'] if isinstance(p, dict)])
    n = 0 if n is None and sec.get('state') == 'clear' else n
    return None if n is None else count(n, 'cloud provider', 'cloud providers')


RESULTS = {'privacy': _privacy, 'vulnerabilities': _vulnerabilities, 'credential_exposure': _credentials,
           'data_leak_history': _leaks, 'data_sovereignty': _sovereignty, 'data_residency': _residency,
           'legal_terms': _legal, 'ai_risk_governance': _counted('ai_issues', 'AI governance issue',
                                                                 'AI governance issues'),
           'quantum_security': _counted('high_risk', 'high-risk finding', 'high-risk findings'),
           'security_resourcing': _resourcing, 'certifications': _certifications,
           'fourth_party_vendors': _vendors, 'cloud_infrastructure': _cloud}


def aspect_score(key, sec, breakdown):
    """The system's percent score as given (at most 100%), NA when this payload has none. Never computed."""
    if sec.get('state') in NO_RESULT:
        return NA
    if key == 'privacy':
        from .s03_privacy import _metrics
        ms = _metrics(sec)          # excluded_no_policy: no score (not 0%)
    else:
        ms = sec.get('metrics') or []
    m = next((m for m in ms if isinstance(m, dict) and m.get('id') == SCORED[key]), None)
    if m is None and (breakdown.get(key) or {}).get('unit') == 'percent':
        m = breakdown[key]
    v = (m or {}).get('value')
    return min(v, 100) if isinstance(v, (int, float)) and not isinstance(v, bool) else NA


# Backend-computed aspect score (owner decision 2026-10-19: the backend computes every aspect percent, e.g.
# (cap - demerit) / cap x 100, and sends it as sections.<key>.aspect_score; the report never derives one).
SCORE_LABELS = {'no_preference_set': 'Not compared'}      # null aspect_score reason -> track label


def backend_score(sec):
    """sections.<key>.aspect_score: percent (0-100) | a label for a null with a known reason | NA | None (absent)."""
    v = sec.get('aspect_score')
    if v is None:
        return None
    x = v.get('value') if isinstance(v, dict) else v
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return max(0, min(x, 100))
    return SCORE_LABELS.get(v.get('reason_code') if isinstance(v, dict) else None, NA)


def aspect_rows(report, breakdown):
    """[(spec, title, score | NA | None (never scored), result | None (no result), state)] in report order."""
    by = {b.get('section'): b for b in breakdown if isinstance(b, dict)}
    rows = []
    for spec in assessed():
        sec = section_data(report, spec) or {'state': 'unavailable'}
        st = sec.get('state')
        has = not sec.get('_card_only') and (st not in NO_RESULT or sec.get('_no_preference'))
        res = RESULTS[spec.key](sec, report) if has and spec.key in RESULTS else None
        score = backend_score(sec)
        if score is None:
            score = aspect_score(spec.key, sec, by) if spec.key in SCORED else None
        rows.append((spec, sec.get('title') or spec.title, score, res, st))
    return rows


def result_markup(res):
    """<number> <noun phrase> [· qualifier, qualifier]; muted 'No result' (the chip says why). The last two
    words of the phrase never part (no one-word last line); each qualifier wraps as one unit."""
    if res is None:
        return f'<font color="{MU}">No result</font>'
    n, phrase, qual = res
    text = '&nbsp;'.join(c.esc(phrase).rsplit(' ', 1))
    if qual:
        text += '&nbsp;· ' + ', '.join(c.esc(q).replace(' ', '&nbsp;') for q in qual)
    lead = f'<font name="{T.MEDIUM}" color="{HX}">{c.esc(n).replace(" ", "&nbsp;")}</font> ' if n else ''
    return lead + text


def _linked(spec, markup, pages):
    return f'<a href="#{spec.anchor}">{markup}</a>' if pages.get(spec.anchor) else markup


def _num(spec, pages):
    return c.M(_linked(spec, f'<font color="{NV}">{c.esc(spec.number)}</font>', pages), 'cell')


def _name(spec, title, pages):
    return c.M(_linked(spec, c.esc(title), pages), 'cell_head')


class Meter(Flowable):
    """0-100 track: navy fill to the score on a light track; no score -> dashed hairline labelled
    'Score not available' (never reads as 0%)."""
    LABEL = 'Score not available'

    def __init__(self, score, width, h=12):
        super().__init__()
        self.score, self.width, self.height = score, width, h

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        cv, w, mid = self.canv, self.width, self.height / 2 + 1
        if not isinstance(self.score, str):
            cv.setFillColor(T.SAPPHIRE_100)
            cv.roundRect(0, mid - 3, w, 6, 3, stroke=0, fill=1)
            if self.score > 0:
                cv.setFillColor(T.NAVY)
                cv.roundRect(0, mid - 3, max(6, w * self.score / 100), 6, 3, stroke=0, fill=1)
            return
        fs, label = 7.2, self.LABEL if self.score == NA else self.score
        tw = stringWidth(label, T.LIGHT, fs)
        cv.setStrokeColor(T.SLATE_400)
        cv.setLineWidth(0.6)
        cv.setDash(1.5, 2)
        cv.line(tw + 4, mid, w, mid)
        cv.setDash()
        cv.setFillColor(T.MUTED)
        cv.setFont(T.LIGHT, fs)
        cv.drawString(0, mid - fs * 0.36, label)


def _frame(pad_v=0):
    return [('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), pad_v),
            ('BOTTOMPADDING', (0, 0), (-1, -1), pad_v)]


def scores_block(rows, pages):
    scored = [r for r in rows if r[2] is not None]
    mw, other = 230, len(rows) - len(scored)
    data = [[_num(r[0], pages), _name(r[0], r[1], pages), Meter(r[2], mw),
             c.M(f'<font name="{T.MEDIUM}" color="{HX}">{c.fmt_value(r[2], "percent")}</font>', 'cell_num')
             if not isinstance(r[2], str) else ''] for r in scored]
    t = Table(data, colWidths=[24, 170, mw + 12, 44], hAlign='LEFT')
    t.setStyle(TableStyle(_frame(3.5) + [('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    head = Table([[c.P('Aspect scores', 'h3', spaceBefore=0), c.P('0%', 'note_flush'),
                   c.P('100% = best', 'note_flush', alignment=2)]], colWidths=[194, mw / 2, mw / 2], hAlign='LEFT')
    head.setStyle(TableStyle(_frame() + [('VALIGN', (0, 0), (-1, -1), 'BOTTOM')]))
    note = (f'Only {"this aspect has its" if len(scored) == 1 else f"these {_word(len(scored))} aspects have their"} '
            f'own score. The other {_word(other)} have no separate score and are judged by their result below.')
    if any(r[2] == NA for r in scored):
        note += ' “Score not available”: this aspect normally has a score, but none is given in this assessment.'
    # one unsplittable cell: the 'Rating overview' heading and intro (Keep in rating_overview) move with it
    box = Table([[[Spacer(0, 4), head, Spacer(0, 2), t, c.P(note, 'note')]]], colWidths=[T.CW], hAlign='LEFT')
    box.setStyle(TableStyle(_frame()))
    return box


def checklist_block(rows, pages):
    def item(r):
        return [_num(r[0], pages), [_name(r[0], r[1], pages), c.M(result_markup(r[3]), 'dense')],
                c.state_chip(r[4], dense=True)]
    w = [22, T.COL2 - 22 - 92, 92]
    half = (len(rows) + 1) // 2           # 13 aspects: 7 left, 6 right
    cols = []
    for part in (rows[:half], rows[half:]):
        t = Table([item(r) for r in part] or [['', '', '']], colWidths=w, hAlign='LEFT')
        t.setStyle(TableStyle(_frame(5) + [('LINEBELOW', (0, 0), (-1, -1), T.HAIRLINE, T.RULE),
                                           ('LEFTPADDING', (2, 0), (2, -1), 4), ('TOPPADDING', (2, 0), (2, -1), 6)]))
        cols.append(t)
    two = Table([cols], colWidths=[T.COL2 + T.GUTTER, T.COL2], hAlign='LEFT')
    two.setStyle(TableStyle(_frame()))
    two.spaceAfter = T.SP_SM
    return c.keep(c.P('All aspects', 'h3'),
                  c.M(f'<font color="{MU}">Reading order: down the left column, then the right.</font>', 'note_flush'),
                  Spacer(0, 4), two)


def rating_overview(data, ctx, rating):
    ro = data.get('rating_overview') or {}
    rows = aspect_rows(ctx.report, ro.get('aspect_breakdown') or [])
    k = sum(r[2] is not None for r in rows)
    intro = (f'All {len(rows)} aspects in report order. {_word(k).capitalize()} '
             f'{"has its" if k == 1 else "have their"} own score (100% = best); the rest are judged by their result.')
    # the payload's own overview note and the demerit ledger stay internal: never printed (user decisions)
    return [c.keep(c.heading('Rating overview', 2, style=H2_TIGHT), c.P(intro, 'body'),
                   Deferred(lambda pages: scores_block(rows, pages))),
            Deferred(lambda pages: checklist_block(rows, pages))]


# --- sector comparison ------------------------------------------------------------
class Bar(Flowable):
    H = 7.0

    def __init__(self, frac, color):
        super().__init__()
        self.frac, self.color = max(0.0, min(1.0, frac)), color

    def wrap(self, aw, ah):
        self.width, self.height = aw, 12
        return self.width, self.height

    def draw(self):
        y = (12 - self.H) / 2
        self.canv.setFillColor(T.SURFACE)
        self.canv.rect(0, y, self.width, self.H, stroke=0, fill=1)
        self.canv.setFillColor(self.color)
        self.canv.rect(0, y, self.width * self.frac, self.H, stroke=0, fill=1)


SECTOR_LABELS = {'your_score': 'Your score', 'sector_average': 'Sector average',
                 'sector_top_10_percent': 'Sector top 10%'}      # kit labels; source labels stay in the payload


def sector_block(ic):
    out = [c.heading('Sector comparison', 2)]
    st = ic.get('state')
    if st in NO_RESULT:
        return out + [c.state_card(st, c.reason_text(ic), title=f'Sector comparison: {c.CARD_TITLES[st].lower()}')]
    if ic.get('intro_source'):
        out.append(c.P(c.sentence(ic['intro_source']), 'body'))
    rows = []
    for m in [m for m in ic.get('metrics') or [] if isinstance(m, dict)]:
        mine = m.get('id') == 'your_score'
        style = 'cell_head' if mine else 'cell'
        den, v = m.get('denominator'), m.get('value')
        if c.is_missing(m):
            rows.append([c.P(SECTOR_LABELS.get(m.get('id')) or m.get('label') or '', style),
                         c.P(c.missing_text(m), 'cell_muted'), ''])
            continue
        rows.append([c.P(SECTOR_LABELS.get(m.get('id')) or m.get('label') or '', style),
                     Bar(v / den if den else 0, T.SAPPHIRE if mine else T.SLATE_400) if den else '',
                     c.P(f'{c.fmt_number(v)} / {c.fmt_number(den)}' if den else c.fmt_value(m),
                         'cell_head_num' if mine else 'cell_num')])
    if rows:
        t = Table(rows, colWidths=[120, T.CW - 120 - 72, 72], hAlign='LEFT')
        t.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), T.CELL_PAD_H), ('RIGHTPADDING', (0, 0), (-1, -1), T.CELL_PAD_H),
            ('LEFTPADDING', (0, 0), (0, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), T.CELL_PAD_V), ('BOTTOMPADDING', (0, 0), (-1, -1), T.CELL_PAD_V),
            ('LINEBELOW', (0, 0), (-1, -1), T.HAIRLINE, T.RULE), ('LINEABOVE', (0, 0), (-1, 0), T.HAIRLINE, T.RULE),
        ]))
        t.spaceAfter = T.SP_MD
        out.append(t)
    cohort = ic.get('cohort') or {'value': None, 'reason_code': 'not_printed_in_source'}
    if cohort.get('cohort_size') is not None:
        parts = [c.fmt_value(cohort['cohort_size'], 'organisations'), cohort.get('period'),
                 cohort.get('percentile_method')]
        cohort = ' · '.join(str(p) for p in parts if p)
    else:
        cohort = {'value': None, **cohort}
    nr = {'value': None, 'reason_code': 'not_printed_in_source'}
    out += kv_block([('Sector', ic.get('sector') or ic.get('industry') or nr),
                     ('Performance gap', ic.get('performance_gap', nr)),
                     ('Peer cohort', cohort)])
    if ic.get('note'):
        out.append(c.note(ic['note']))
    return out


# --- next step --------------------------------------------------------------------
def next_pointer(report, pages):
    spec = spec_for('priority_actions')
    pa = section_data(report, spec) if spec else None
    if not pa:
        return None
    acts = [a for a in pa.get('actions') or [] if isinstance(a, dict)]
    if acts:
        levels = [str(a.get('priority') or 'not rated').lower() for a in acts]
        split = ', '.join(f'{levels.count(p)} {p}' for p in dict.fromkeys(levels))
        what = f'{c.fmt_value(len(acts), "actions")} ({split})'
    else:
        what = T.STATE.get(pa.get('state'), {}).get('label', 'no actions listed')
    return pointer_line(f'<b>Next</b>  {section_ref("priority_actions", report, pages)}  ·  {c.esc(what)}')


# --- module contract --------------------------------------------------------------
def _rating(data, ctx):
    ref = (data.get('rating_overview') or {}).get('rating_ref') or 'rating'
    return resolve(ctx.report, ref) or {}


def build(data, ctx):
    rating = _rating(data, ctx)
    snap = ctx.report.get('snapshot') or {}
    out = [Deferred(lambda pages: rating_panel(rating, snap, ctx.report, pages))]
    out += scope_block(data, ctx)
    out += rating_overview(data, ctx, rating)
    # the Next pointer never starts a page alone: it travels with the whole sector block
    # (short, ~200 pt), or with the block before it when there is none
    nxt = Deferred(lambda pages: next_pointer(ctx.report, pages) or Spacer(0, 0))
    sc = data.get('sector_comparison', data.get('industry_comparison'))
    tail = sector_block(sc) if sc is not None else []
    tail = tail or ([out.pop()] if out else [])
    out.append(c.keep(*tail, nxt))
    return out


def build_context(data, ctx):
    """Unavailable / not assessed overview: still show what was in scope."""
    return scope_block(data, ctx) if data.get('scope_and_coverage') else []
