"""14 Fourth-party vendors: a RESUME of the connected organisations reported for the assessed
organisation (fourth-party redesign, phase 0: flat list, no relationship data, no per-organisation dates).

State (adjust): a reported list is `partial` with the data-limits banner (never 'Findings'); an empty list
is the neutral `none_identified` (never 'clear'). Metric states are stripped (a resume has no findings).

Layout: summary (verdict row; one counting rule: organisations) -> tiles (reported, rated / not rated,
lowest grade + count, the assessed organisation's own grade for reference) -> grade distribution bar
(grade colours only) -> "Needs a look" (lowest grades cut where the band changes + not rated + self-
reference, with reason chips) -> T1 (<= 30): every organisation inline; T2: pointer to Appendix <D.n>.1 (id RID['s14']).
Grade chips appear on the section page only; the risk band is printed as plain text "as sent" in the
register, never derived from the grade and never with severity styling.

Organisation fields read (R17 + old-report card): name, domain, category, grade (+ grade_reason[_code]),
risk_band (+ risk_band_label_source), assessed_membership, assessed_at (phase 1, printed when present);
profile: employees, revenue_source, headquarters, founded, technologies_count / technologies_more_source.
"""
import itertools
import re

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, Table, TableStyle

from .. import components as C
from .. import theme as T
from ..text import esc, hexstr, is_missing, plain
from . import BY_ID, hold
from .s13_certifications import field, label, stack, widths

GRADES = list(T.GRADE)                                  # AAA (best) .. D (worst)
UNIT = 'organisations'
NOTE_CONTRACT = 'A detected relationship is not evidence of a contract.'
# reason codes that only say the source printed no rating: the reason itself is not reported
NO_REASON = {None, '', 'dash_in_source', 'not_printed_in_source', 'blank_in_source'}
# ponytail: curated alias domains (names seen in the samples) until the backend sends organisation_id (phase 1)
ALIASES = [{'amazon.com', 'aws.com', 'aws.amazon.com'}, {'facebook.com', 'fb.com'}, {'google.com', 'gmail.com'}]
BANNER = ('Ratings are as shown on the report date. How each organisation is connected to {org}'
          '{dates} are not reported.')
WIDTHS = {'Organisation': 170, 'Sector': 144, 'Grade': 124, 'Risk band': 84,
          'Assessed on': 66, 'Why listed': 92}


def _v(x):
    return x.get('value') if isinstance(x, dict) else x


def org_name(report):
    return ((report.get('identity') or {}).get('organisation_name')) or 'the assessed organisation'


def grade(v):
    """Rating as sent; shown whatever assessed_membership says (membership is printed apart)."""
    g = str(_v(v.get('grade')) or '').upper()
    return g if g in T.GRADE else None


def band_text(v):
    """Risk band as sent (plain text), never derived from the grade."""
    if not grade(v):
        return 'Not sent'
    b = C.val(v.get('risk_band_label_source')) or _v(v.get('risk_band'))
    return str(b).strip().capitalize() if b and str(b).strip() not in ('—', '-') else field(v, 'risk_band')


def not_rated(v):
    """'Not rated', or 'Not rated (<reason>)' when the payload gives a real one."""
    rec = field(v, 'grade')
    rec = rec if isinstance(rec, dict) else {}
    if rec.get('reason_code') in NO_REASON:
        return 'Not rated'
    return f'Not rated ({plain(C.reason_text(rec)).rstrip(".")})'


def order(v):
    g = grade(v)
    return (g is None, -GRADES.index(g) if g else 0, str(v.get('name') or v.get('domain') or '').casefold())


def _host(d):
    return re.sub(r'^www\.', '', str(_v(d) or '').strip().lower())


def is_self(v, report):
    """Name or domain matches the assessed organisation (e.g. detik.net.id in Detik's list)."""
    ident = report.get('identity') or {}
    org, dom = str(ident.get('organisation_name') or '').casefold(), _host(ident.get('domain'))
    name, vd = str(v.get('name') or '').casefold(), _host(v.get('domain'))
    return bool(org and name == org or dom and vd and (vd == dom or vd.split('.')[0] == dom.split('.')[0]))


def alias_groups(vendors):
    hosts = {_host(v.get('domain')): v.get('name') or _host(v.get('domain')) for v in vendors}
    return [[hosts[h] for h in sorted(g) if h in hosts] for g in ALIASES if len(g & hosts.keys()) > 1]


def assessed_on(v):
    a = v.get('assessed_at')
    return C.fmt_date(a) if a is not None and not is_missing(a) else field(v, 'assessed_at')


def has_dates(vendors):
    return any(v.get('assessed_at') is not None and not is_missing(v.get('assessed_at')) for v in vendors)


def _n(n, unit=UNIT):
    return f'{C.fmt_number(n)} {C.fmt_unit(unit, n)}'


# --- state ---------------------------------------------------------------------------------
def adjust(data, report):
    """Resume, not findings: list -> partial + data-limits banner; empty -> none_identified."""
    if data.get('state') not in ('findings', 'clear', 'partial', 'none_identified'):
        return data
    vendors = [v for v in data.get('vendors') or [] if isinstance(v, dict)]
    org = org_name(report)
    metrics = [{**{k: x for k, x in m.items() if k != 'state'},
                **({'label': 'Connected organisations reported'} if m.get('id') == 'fourth_parties' else {})}
               for m in data.get('metrics') or [] if isinstance(m, dict)]
    if not vendors:
        out = hold(data, 'none_identified', f'No connected organisations reported for {org}', 'none_identified')
        return {**out, 'metrics': metrics, 'summary': f'No connected organisations reported for {org}.'}
    dated = all(v.get('assessed_at') is not None and not is_missing(v.get('assessed_at')) for v in vendors)
    banner = BANNER.format(org=org, dates='' if dated else " and the date of each organisation's own assessment")
    if dated:
        banner = banner.replace(' are not reported', ' is not reported')
    out = hold(data, 'connections_not_reported', banner, 'partial')
    return {**out, 'metrics': metrics, 'summary': summary(vendors, report)}


def summary(vendors, report):
    """One counting rule: organisations (each listed name counts once)."""
    org, n = org_name(report), len(vendors)
    rated = [v for v in vendors if grade(v)]
    s = f'{_n(n, "connected organisations")} reported for {org}: {C.fmt_number(len(rated))} rated, ' \
        f'{C.fmt_number(n - len(rated))} not rated.'
    if rated:
        worst = max((grade(v) for v in rated), key=GRADES.index)
        k = sum(1 for v in rated if grade(v) == worst)
        s += f' The lowest grade is {worst} ({_n(k)}).'
    selfs = [v for v in vendors if is_self(v, report)]
    if selfs:
        s += (f' {C.fmt_number(len(selfs))} of them carr{"ies" if len(selfs) == 1 else "y"} the name of {org} '
              f'itself ({", ".join(_host(v.get("domain")) or v.get("name") for v in selfs)}) and '
              f'{"is" if len(selfs) == 1 else "are"} counted.')
    return s


def card(data, ctx):
    if ctx.state != 'none_identified':
        return {}
    org = org_name(ctx.report)
    empty = data.get('empty_state_source') or {}
    return {'title': 'No connected organisations identified',
            'reason': f'None were found with the methods used. This does not show that {org} has no suppliers.',
            'what_checked': empty.get('coverage')}


# --- cells ---------------------------------------------------------------------------------
# ponytail: cap inferred from one sample (Instagram, Amazon '+2000 more'); confirm with the source product.
TECH_DISPLAY_CAP = 2000


def _profile(v):
    """Company profile as printed (2026-10 samples): employees · revenue · headquarters · founded ·
    technologies listed. Revenue keeps the source string (no currency is printed)."""
    parts = []
    v = {k: C.val(x) for k, x in v.items()}      # null records are left out of the profile line
    if v.get('employees') is not None:
        parts.append(f'{C.fmt_number(_v(v["employees"]))} employees')
    if v.get('revenue_source'):
        parts.append(f'revenue {v["revenue_source"]} (as printed)')
    if v.get('headquarters'):
        parts.append(str(v['headquarters']))
    if v.get('founded'):
        parts.append(f'founded {_v(v["founded"])}')
    more = re.search(r'\+\s*([\d,]+)', str(C.val(v.get('technologies_more_source')) or ''))
    more = int(more.group(1).replace(',', '')) if more else None
    if more is not None and more >= TECH_DISPLAY_CAP:      # '+2000 more' is the source's display limit:
        shown = len(v.get('technologies_sample_source') or [])   # the true total is unknown, never 'exactly N'
        parts.append((f'{shown} technologies shown, ' if shown else '') +
                     f'{C.fmt_number(TECH_DISPLAY_CAP)}+ more (source display limit)')
    elif C.val(v.get('technologies_count')) is not None:
        parts.append(f'{C.fmt_number(_v(v["technologies_count"]))} technologies listed')
    return ' · '.join(parts)


def org_cell(c, v, width, dense, report=None, profile=True):
    """Name (strong) + domain, then (muted) profile, membership and self-reference lines."""
    name, dom = v.get('name') or v.get('vendor_name'), _v(v.get('domain'))
    fs, style = (7.8, 'dense') if dense else (8.6, 'cell')
    if not name:
        head = c.tech(dom, style + '_tech') if dom else c.P('Name not recorded', style + '_muted')
    elif dense and dom and stringWidth(f'{name}  {dom}', T.MEDIUM, fs) <= width - 2 * T.CELL_PAD_H:
        head = c.M(f'<font name="{T.MEDIUM}" color="{hexstr(T.HEADING)}">{esc(name)}</font>  '
                   f'<font color="{hexstr(T.MUTED)}">{esc(dom)}</font>', style + '_tech')
    else:
        lines = c.tech_lines(dom, width - 2 * T.CELL_PAD_H, T.LIGHT, fs) if dom else ()
        head = stack(c, name, lines, style + '_tech', strong=True)      # names are never hyphenated
    extra = [_profile(v) if profile else '']
    if v.get('assessed_membership') is False:
        extra.append('Not an assessed member (as reported)')
    if report is not None and is_self(v, report):
        extra.append(f'Same name as {org_name(report)}')
    extra = ' · '.join(x for x in extra if x)
    return [head, c.P(extra, style + '_muted')] if extra else head


def grade_cell(c, v, dense):
    return c.grade_chip(grade(v), dense=dense) if grade(v) else c.P(not_rated(v), ('dense' if dense else 'cell')
                                                                     + '_muted')


def reason_chips(c, reasons, dense):
    return [c.chip(r, T.SLATE_400, dense, hollow=True) for r in reasons]


# --- section blocks --------------------------------------------------------------------------
def tiles(c, vendors, report):
    n, rated = len(vendors), [v for v in vendors if grade(v)]
    org = org_name(report)
    items = [{'value': n, 'unit': UNIT, 'label': 'Connected organisations reported'},
             {'value': len(rated), 'unit': 'rated', 'label': f'{C.fmt_number(n - len(rated))} not rated'}]
    if rated:
        worst = max((grade(v) for v in rated), key=GRADES.index)
        k = sum(1 for v in rated if grade(v) == worst)
        items.append({'value': worst, 'unit': _n(k), 'label': 'Lowest grade reported'})
    else:
        items.append({'value': None, 'label': 'Lowest grade reported', 'reason': 'no organisation is rated'})
    own = str(_v((report.get('rating') or {}).get('grade')) or '').upper()
    items.append({'value': own, 'label': f'Grade of {org} (for reference)'} if own in T.GRADE else
                 {'value': None, 'label': f'Grade of {org} (for reference)', 'reason': 'not in the report data'})
    return c.kpi_strip(items, per_row=4)


class GradeBar(Flowable):
    """Rated organisations by grade, worst (D) left to best (AAA) right: one segment per grade present, grade colours only, label + count
    below. No band legend (a grade is not a severity)."""
    H, LAB = 8, 18

    def __init__(self, counts):
        super().__init__()
        self.counts = [(g, n) for g, n in counts if n]

    def wrap(self, aw, ah):
        self.width, self.height = aw, self.H + self.LAB + 4
        return self.width, self.height

    def draw(self):
        cv, total = self.canv, sum(n for _, n in self.counts)
        floor = 24                                           # every grade present keeps room for its label
        free = self.width - floor * len(self.counts)
        x, y = 0, self.LAB + 4
        for g, n in self.counts:
            w = floor + free * n / total
            cv.setFillColor(T.GRADE[g])
            cv.rect(x, y, w - 1.5, self.H, stroke=0, fill=1)
            cv.setFillColor(T.BODY)
            cv.setFont(T.REGULAR, 7)
            cv.drawCentredString(x + w / 2, y - 9, g)
            cv.setFillColor(T.MUTED)
            cv.setFont(T.LIGHT, 7)
            cv.drawCentredString(x + w / 2, y - 18, C.fmt_number(n))
            x += w


def grade_bar(c, vendors):
    rated = [v for v in vendors if grade(v)]
    if not rated:
        return []
    counts = [(g, sum(1 for v in rated if grade(v) == g)) for g in T.GRADE_BAR]   # worst left
    left = len(vendors) - len(rated)
    head = f'Rated organisations by grade ({C.fmt_number(len(rated))})' + \
        (f'; {C.fmt_number(left)} not rated, not shown in the bar' if left else '')
    bar = GradeBar(counts)
    bar.spaceBefore, bar.spaceAfter = 2, T.SP_MD
    return [c.keep(c.P(head, 'kv_label', keepWithNext=1), bar)]


def needs_a_look(vendors, report, top_n):
    """(organisation, reasons): the lowest grades cut where the risk band (as sent) changes, at most
    top_n unless the worst band alone is larger (then cut where the grade changes), never the Low band
    (no band sent: never A or better); then not rated, then self-references not already listed."""
    def low(v):
        b = str(_v(v.get('risk_band')) or '').lower()
        return b == 'low' if b else GRADES.index(grade(v)) <= GRADES.index('A')
    rated = sorted((v for v in vendors if grade(v) and not low(v)), key=order)
    cut = []

    def take(rows, key):
        out = []
        for _, grp in itertools.groupby(rows, key=key):
            grp = list(grp)
            if out and len(out) + len(grp) > top_n:
                break
            out += grp
        return out
    if rated:
        cut = take(rated, lambda v: str(_v(v.get('risk_band')) or grade(v)).lower())
        if len(cut) > top_n:
            cut = take(cut, grade)
    rows = [(v, ['Lowest grades']) for v in cut]
    rows += [(v, ['Not rated']) for v in sorted((v for v in vendors if not grade(v)), key=order)]
    org = org_name(report)
    for v in sorted(vendors, key=order):
        if is_self(v, report):
            hit = next((r for r in rows if r[0] is v), None)
            hit[1].append(f'Same name as {org}') if hit else rows.append((v, [f'Same name as {org}']))
    return rows


def look_table(c, rows, vendors, dense=False):
    dated = has_dates(vendors)
    cols = ['Organisation', 'Sector', 'Grade', 'Why listed'] + (['Assessed on'] if dated else [])
    w = widths(cols, WIDTHS, 'Organisation')
    data = [[org_cell(c, v, w[0], dense, profile=False), label(field(v, 'category')), grade_cell(c, v, dense),
             reason_chips(c, why, dense)] + ([assessed_on(v)] if dated else []) for v, why in rows]
    return c.compact_table(cols, data, widths=w, dense=dense)


def register_columns(vendors):
    return ['Organisation', 'Sector', 'Grade', 'Risk band'] + \
        (['Assessed on'] if has_dates(vendors) else [])


def register_cells(c, v, cols, w, dense, report, chip=True):
    cells = {'Organisation': org_cell(c, v, w[cols.index('Organisation')], dense, report),
             'Sector': 'Unknown' if C.is_missing(field(v, 'category')) else label(field(v, 'category')),
             'Grade': (grade_cell(c, v, dense) if chip else grade(v) or c.P(not_rated(v), 'dense_muted')),
             'Risk band': band_text(v), 'Assessed on': assessed_on(v) if has_dates([v]) else
             field(v, 'assessed_at')}
    return [cells[h] for h in cols]


def notes(vendors):
    out = [NOTE_CONTRACT]
    groups = alias_groups(vendors)
    if groups:
        out.append('Some names may refer to the same organisation (' +
                   '; '.join(' and '.join(g) for g in groups) +
                   '). They are not merged: each is listed and counted with its own rating.')
    return C.note(' '.join(out))


def tier(vendors):
    from .app_d_evidence_registers import pol, tier as t
    return t(len(vendors), len(vendors)), pol('lists.fourth_party_vendors.top_n', 10)


def build(data, ctx):
    c, rep = ctx.c, ctx.report
    vendors = sorted((v for v in data.get('vendors') or [] if isinstance(v, dict)), key=order)
    out = []
    if not vendors:
        return [pointer()]
    out += [tiles(c, vendors, rep), *grade_bar(c, vendors)]
    tr, top_n = tier(vendors)
    look = needs_a_look(vendors, rep, top_n)
    if look:
        out += [c.heading(f'Needs a look ({len(look)} of {len(vendors)})', 3),
                c.P('Lowest grades (cut where the risk band changes; never the Low band) and organisations '
                    'without a rating; worst grade first.', 'note_flush', keepWithNext=1),
                look_table(c, look, vendors, dense=True)]
    if tr == 'T1':
        cols = register_columns(vendors)
        w = widths(cols, {**WIDTHS, 'Sector': 120, 'Risk band': 92}, 'Organisation')
        dense = True                                     # policy: the register is dense
        out += [c.heading(f'All connected organisations ({len(vendors)})', 3),
                c.compact_table(cols, [register_cells(c, v, cols, w, dense, rep) for v in vendors], widths=w,
                                dense=dense)]
    else:
        from .app_d_evidence_registers import RID      # lazy: app_d imports this module
        out.append(c.register_pointer(RID['s14'], {'value': len(vendors), 'unit': UNIT},
                                      title=f'{RID["s14"]}.1 Connected organisations'))
    return out + [c.keep(notes(vendors), pointer())]


def build_context(data, ctx):
    return [pointer()]


# --- Appendix <D.n>.1 (T2) ---------------------------------------------------------------------
def register_entries(c, vendors, report):
    """(columns, widths, entries) for the flat register: '#', plain grade, band as sent."""
    vendors = sorted(vendors, key=order)
    cols = ['#'] + register_columns(vendors)
    fixed = {**WIDTHS, '#': 24, 'Sector': 120, 'Grade': 72, 'Risk band': 92}
    w = widths(cols, fixed, 'Organisation')
    rows = [('row', [str(i)] + register_cells(c, v, cols[1:], w[1:], True, report, chip=False))
            for i, v in enumerate(vendors, 1)]
    return cols, w, rows


# --- pointer to the supply-chain aggregation -------------------------------------------------
class SectionPointer(Flowable):
    """'<title> <text> · Appendix C, page N', linked once the section anchor resolved."""

    def __init__(self, spec, title, text):
        super().__init__()
        self.key, self.where, self.title, self.text = spec.anchor, f'Appendix {spec.number}', title, text

    def _table(self, aw):
        doc = getattr(self.canv, '_doctemplate', None)
        page = (getattr(doc, 'anchors_prev', None) or {}).get(self.key)
        where = esc(f'{self.where}, page {page}' if page else f'{self.where}, page reference pending')
        if page:
            where = f'<a href="#{esc(self.key)}" color="{hexstr(T.NAVY)}">{where}</a>'
        t = Table([[C.M(f'<b>{esc(self.title)}</b>  {esc(self.text)}  ·  {where}', 'pointer')]], colWidths=[aw],
                  hAlign='LEFT')
        t.setStyle(TableStyle([('LINEBEFORE', (0, 0), (0, 0), 2, T.SAPPHIRE),
                               ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                               ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        return t

    def wrap(self, aw, ah):
        self._t = self._table(aw)
        self.width, self.height = self._t.wrapOn(self.canv, aw, ah)
        return self.width, self.height

    def draw(self):
        doc = getattr(self.canv, '_doctemplate', None)
        if doc is not None and hasattr(doc, 'refs'):
            doc.refs.add(self.key)
        self._t.drawOn(self.canv, 0, 0)

    def getSpaceBefore(self):
        return T.SP_SM

    def getSpaceAfter(self):
        return T.SP_MD


def pointer():
    return SectionPointer(BY_ID['appC'], 'Supply-chain aggregation',
                          'How fourth-party ratings feed combined supply-chain risk')
