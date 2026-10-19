"""python -m cyberrank_report.build data.json -o out.pdf [--only s04,s13] [--blueprint]

The payload is validated at load (validate(): state enum, null reasons, metric units);
a contract error exits 1 with every offending path.

Assembles cover + contents + registered sections (+ appendices) with multiBuild,
then writes <out>.qa.json. Exit code 2 when QA finds errors.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from reportlab.platypus import LayoutError

from . import components as C
from . import fonts
from . import qa
from . import theme as T
from .page import ReportDoc, cover_flowables, identity_from_report
from .sections import BY_ID, GROUPS, REGISTRY, adjust_report, lift_privacy_subsections, render_section


NO_RESULT_STATES = ('not_assessed', 'not_applicable', 'unavailable')   # must say why
DATE_KEYS = ('valid_from', 'valid_until', 'last_scanned')                # plus every '*_at' key
ISO = re.compile(r'^(\d{4})(?:-(\d{2})(?:-(\d{2})(?:[T ][\d:.]+(?:Z|[+-]\d{2}:?\d{2})?)?)?)?$')
PRECISIONS = ('minute', 'day', 'month', 'year')


def date_error(v):
    """Problem with a date field value (str or {'value', 'precision'}), or None. A date shorter
    than YYYY-MM-DD must state its precision (a placeholder day such as YYYY-01-01 with
    precision 'year' prints as the year only)."""
    rec = v if isinstance(v, dict) else {'value': v}
    raw, prec = rec.get('value'), rec.get('precision')
    if raw is None or not isinstance(raw, str):
        return None if raw is None else f'date is not a string ({raw!r})'
    m = ISO.match(raw.strip())
    if not m:
        return f'"{raw}" is not an ISO 8601 date (YYYY-MM-DD)'
    y, mo, d = (int(x) if x else None for x in m.groups())
    try:
        date(y, mo or 1, d or 1)
    except ValueError:
        return f'"{raw}" is not a calendar date'
    if prec is not None and prec not in PRECISIONS:
        return f'precision "{prec}" is not one of {list(PRECISIONS)}'
    if prec is None and d is None:
        return f'"{raw}" is a partial date without a precision (day / month / year)'
    if isinstance(v, dict) and prec and {'day': d, 'month': mo, 'year': y}.get(prec, d) is None:
        return f'"{raw}" is too short for precision "{prec}"'
    if prec == 'minute' and not re.search(r'[T ]\d{2}:\d{2}', raw):
        return f'"{raw}" has no time (HH:MM) for precision "minute"'
    return None


class InputError(ValueError):
    """The payload breaks the input contract (data/report-schema.md section 1)."""


def validate(report):
    """Contract checks at load; raises InputError listing every problem (path: rule):
    each `state` (and `<field>_state` beside `<field>`) is in the state enum; every null
    carries a reason (`reason_code` on its object, or `<field>_reason_code` / `<field>_reason`
    beside it); a not_assessed / not_applicable / unavailable state says why (reason_code or
    state_reason); every metric has a unit; the PQC scan is not recorded as off while quantum results
    are present. Deprecated `industry` keys are renamed to `sector` first (normalise()).
    A missing value is never silently rendered as 0."""
    if not isinstance(report, dict):
        raise InputError('payload: top level must be a JSON object')
    normalise(report)
    enum = set((report.get('meta') or {}).get('state_enum') or T.STATES)
    errs = []

    def walk(v, path):
        if isinstance(v, list):
            for i, x in enumerate(v):
                if x is None:
                    errs.append(f'{path}[{i}]: null list item has no reason')
                walk(x, f'{path}[{i}]')
            return
        if not isinstance(v, dict):
            return
        for k, x in v.items():
            p = f'{path}.{k}' if path else k
            if (k == 'state' or k.endswith('_state') and k[:-6] in v) and isinstance(x, str) and x not in enum:
                errs.append(f'{p}: state "{x}" is not one of {sorted(enum)}')
            if x is None and not ('reason_code' in v or f'{k}_reason_code' in v or f'{k}_reason' in v):
                errs.append(f'{p}: null without a reason (reason_code, {k}_reason_code or {k}_reason)')
            if (k == 'state' and x in NO_RESULT_STATES
                    and not any(v.get(r) for r in ('reason_code', 'state_reason', 'reason'))):
                errs.append(f'{p}: state "{x}" without a reason (reason_code or state_reason)')
            if (k.endswith('_at') or k in DATE_KEYS) and x is not None:
                bad = date_error(x)
                if bad:
                    errs.append(f'{p}: {bad}')
            if k in ('metrics', 'observed_targets') and isinstance(x, list):
                errs.extend(f'{p}[{i}]: metric "{m.get("id") or m.get("label")}" has no unit'
                            for i, m in enumerate(x) if isinstance(m, dict) and not m.get('unit'))
            walk(x, p)

    walk(report, '')
    errs += _quantum_toggle_errors(report)
    if errs:
        more = f'\n  ... and {len(errs) - 40} more' if len(errs) > 40 else ''
        raise InputError(f'{len(errs)} input contract error(s):\n  ' + '\n  '.join(errs[:40]) + more)
    return report


def normalise(report):
    """Deprecated aliases (in place): privacy sub-areas (terms_conditions, sovereignty, residency,
    resourcing) nested in sections.privacy -> sections.legal_terms / data_sovereignty / data_residency /
    security_resourcing; `industry` -> `sector` (identity, executive_overview
    industry_comparison -> sector_comparison, its `industry` and metric ids industry_* -> sector_*).
    Values are never translated or mapped."""
    ident = report.get('identity')
    if isinstance(ident, dict) and 'industry' in ident:
        ident.setdefault('sector', ident.pop('industry'))
    lift_privacy_subsections(report)      # old nested privacy sub-areas -> their own sections
    eo = (report.get('sections') or {}).get('executive_overview')
    if isinstance(eo, dict) and 'industry_comparison' in eo:
        eo.setdefault('sector_comparison', eo.pop('industry_comparison'))
    sc = (eo or {}).get('sector_comparison') if isinstance(eo, dict) else None
    if isinstance(sc, dict):
        if 'industry' in sc:
            sc.setdefault('sector', sc.pop('industry'))
        for m in sc.get('metrics') or []:
            if isinstance(m, dict) and str(m.get('id', '')).startswith('industry_'):
                m['id'] = 'sector_' + m['id'][len('industry_'):]
    return report


def _quantum_results(sec, report):
    """True when the quantum section carries scan results (not just its envelope)."""
    if not isinstance(sec, dict):
        return False
    if any(sec.get(k) for k in ('findings_by_category', 'pqc_detected', 'scope_summary', 'affected_protocols')):
        return True
    if any(isinstance(m, dict) and m.get('value') is not None for m in sec.get('metrics') or []):
        return True
    reg = report
    for part in str(sec.get('scope_register_ref') or '').split('.'):
        reg = reg.get(part) if isinstance(reg, dict) and part else None
    return bool(isinstance(reg, dict) and reg.get('rows'))


def _quantum_toggle_errors(report):
    """pqc_scan recorded as off while quantum results are present is a data error (business answer
    2026-10-15), not a not_assessed section."""
    t = ((report.get('snapshot') or {}).get('toggles_at_assessment') or {}).get('pqc_scan')
    off = (t.get('value') if isinstance(t, dict) else t) is False
    sec = (report.get('sections') or {}).get('quantum_security')
    if off and _quantum_results(sec, report):
        return ['snapshot.toggles_at_assessment.pqc_scan: the PQC scan is recorded as off but '
                'sections.quantum_security carries quantum results; fix the toggle or remove the results']
    return []


def contents_flowables(specs, report, identity):
    rows, group = [], None
    for s in specs:
        if s.group != group:
            group = s.group
            rows.append(('group', GROUPS[group]))
        title = ((report.get(s.source) or {}).get(s.key) or {}).get('title') or s.title
        rows.append(('entry', s.number, title, s.toc_sub, s.anchor))
    sub = ' / '.join(x for x in (identity['org'], identity['domain'],
                                 f'Assessment {identity["assessment_date"]}') if x)
    return [C.heading('Contents', 1, key='contents'), C.P(sub, 'intro', spaceAfter=T.SP_LG),
            C.Contents(rows)]


def build(report, out, only=None, blueprint=False):
    """Render the report; returns (page_total, qa_counts)."""
    fonts.prepare_cjk(json.dumps(report, ensure_ascii=False))   # CJK subset of the payload, before layout
    identity = identity_from_report(report)
    if not blueprint:
        report = adjust_report(report)
    specs = [s for s in REGISTRY if not only or s.id in only]
    doc = ReportDoc(out, identity, showBoundary=1 if blueprint else 0)
    story = cover_flowables() + contents_flowables(specs, report, identity)
    for s in specs:
        story += render_section(s, report, identity, blueprint)
    total = None
    try:
        total = doc.render(story)
    except LayoutError as e:
        qa.record_layout_error(e, 'build')
    issues = list(qa.ISSUES)
    if total:
        issues += qa.check_pdf(out, locked_pages=[p for p, *_ in doc.locked], table_parts=doc.table_parts,
                               table_heads=C._TABLE_HEADS)
    counts = qa.write_report(Path(out).with_suffix('.qa.json'), out, issues, pages=total,
                             sections=[s.id for s in specs])
    return total, counts


def main(argv=None):
    ap = argparse.ArgumentParser(prog='python -m cyberrank_report.build')
    ap.add_argument('data', type=Path)
    ap.add_argument('-o', '--out', type=Path, required=True)
    ap.add_argument('--only', help='comma-separated section ids, e.g. s04,s13,appD')
    ap.add_argument('--blueprint', action='store_true', help='frame boundaries + payload map per section')
    a = ap.parse_args(argv)
    only = [x.strip() for x in a.only.split(',')] if a.only else None
    bad = [x for x in only or [] if x not in BY_ID]
    if bad:
        ap.error(f'unknown section ids {bad}; known: {", ".join(BY_ID)}')
    try:
        report = validate(json.loads(a.data.read_text(encoding='utf-8')))
        report['_source_dir'] = str(a.data.resolve().parent)     # base for relative document paths
    except json.JSONDecodeError as e:
        ap.exit(1, f'{a.data}: not valid JSON: {e}\n')
    except InputError as e:
        ap.exit(1, f'{a.data}: {e}\n')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    total, counts = build(report, a.out, only, a.blueprint)
    print(f'{a.out}: {total} pages; QA {counts} -> {a.out.with_suffix(".qa.json")}')
    return 2 if counts['error'] or not total else 0


if __name__ == '__main__':
    sys.exit(main())
