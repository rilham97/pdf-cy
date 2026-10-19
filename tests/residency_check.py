"""Synthetic section 08 payloads for the residency map (mode C / A2 / A3) + a check PDF of their pages.
Usage: .venv/bin/python -I tests/residency_check.py <out.pdf>
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

UNKNOWN = {'country': None, 'hosts': 3, 'state': 'unavailable', 'reason_code': 'location_unknown',
           'source_label': '3 hosts with unknown location'}
XX = {'country': None, 'hosts': 1, 'state': 'unavailable', 'reason_code': 'country_code_placeholder',
      'source_label': 'XX (1 host)'}


def _sec(hosting, allowed, enabled=True):
    return {'state': 'findings', 'enabled': enabled, 'allowed_set': allowed,
            'match_state': 'mismatch' if allowed else None,
            'observed_hosting': [h if isinstance(h, dict) else {'country_code': h[0], 'hosts': h[1]} for h in hosting]}


CASES = [  # (key, title, section, expected mode)
    ('sea2', 'SEA: Singapore + Indonesia hosting, Indonesia preferred (2 countries)',
     _sec([('SG', 9), ('ID', 4)], ['ID']), 'A2'),
    ('single', 'One country only (other lookups failed): US hosting, US preferred',
     _sec([('US', 3)], ['US']), 'C'),
    ('sea3', 'SEA: Singapore + Indonesia + Malaysia hosting, Indonesia preferred',
     _sec([('SG', 9), ('ID', 4), ('MY', 2)], ['ID']), 'A2'),
    ('europe', 'Europe: IE 30, NL 18, DE 42; DE + FR preferred',
     _sec([('IE', 30), ('NL', 18), ('DE', 42)], ['DE', 'FR']), 'A2'),
    ('pacific', 'Antimeridian: US + JP hosting, KR preferred (Pacific-centred)',
     _sec([('US', 12), ('JP', 7)], ['KR']), 'A2'),
    ('multi12', '12 countries + unknown + XX + unresolved name, EU preference',
     _sec([{'country': n, 'hosts': k} for n, k in (
         ('United States of America', 120), ('Germany', 42), ('Ireland', 30), ('Netherlands', 18), ('GB', 12),
         ('Singapore', 9), ('Japan', 7), ('Brazil', 5), ('India', 4), ('Canada', 3), ('Australia', 2),
         ('Indonesia', 2), ('Atlantis', 1))] + [UNKNOWN, XX], ['DE', 'IE', 'NL', 'FR']), 'A3'),
    ('nopref', 'Preference disabled: 4 hosting countries',
     {**_sec([('US', 20), ('DE', 5), ('JP', 3), ('BR', 2), UNKNOWN], [], enabled=False), 'match_state': None},
     'A3'),
]


def report(sec):
    return {'identity': {'organisation_name': 'Example Org', 'domain': 'example.com'},
            'snapshot': {'assessed_at': {'value': '2026-10-02', 'precision': 'day'},
                         'generated_at': {'value': '2026-10-03', 'precision': 'day'}},
            'sections': {'data_residency': {k: v for k, v in sec.items() if v is not None}}}


def build_case(sec, out):
    from cyberrank_report import qa
    from cyberrank_report.build import build, validate
    qa.ISSUES.clear()
    return build(validate(report(sec)), out, only=['s08'])


def main(out):
    import pymupdf
    merged = pymupdf.open()
    with tempfile.TemporaryDirectory() as tmp:
        for key, title, sec, _ in CASES:
            p = Path(tmp) / f'{key}.pdf'
            build_case(sec, p)
            src = pymupdf.open(p)
            merged.insert_pdf(src, from_page=2)          # skip cover + contents
            page = merged[-(len(src) - 2)]
            page.insert_text((40, 60), f'MAP CHECK · {title}', fontsize=7, color=(0.39, 0.44, 0.51))
    merged.save(out, garbage=3, deflate=True)
    print(out, len(merged), 'pages')


if __name__ == '__main__':
    main(sys.argv[1])
