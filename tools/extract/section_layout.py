"""Section layout v15 (user decision 2026-10-15, INTEGRATION_CHECKLIST item 15), shared by the
fixture builders and the one-off data migration:

    sections.privacy.{sovereignty, residency, terms_conditions, resourcing}
        -> sections.data_sovereignty / data_residency / legal_terms / security_resourcing

Each lifted sub-object carries its own `summary` (system-provided, set by the builder); the
renderer's generated verdict() is only the fallback when `summary` is absent.

Order and numbers follow the demerit ledger A-J (01 overview, 02 actions, 03 privacy B,
04 vulnerabilities A, 05 credential C, 06 leaks D, 07 sovereignty E, 08 residency F, 09 legal T&C G,
10 AI H, 11 quantum I, 12 resourcing J, 13 certifications, 14 fourth parties, 15 cloud).

    python3 -I tools/extract/section_layout.py data/*.json      # migrate fixtures in place
"""
import json
import sys

ORDER = [('executive_overview', '01', None), ('priority_actions', '02', None), ('privacy', '03', None),
         ('vulnerabilities', '04', None), ('credential_exposure', '05', None), ('data_leak_history', '06', None),
         ('data_sovereignty', '07', 'Data sovereignty'), ('data_residency', '08', 'Data residency'),
         ('legal_terms', '09', 'Legal terms & conditions'), ('ai_risk_governance', '10', None),
         ('quantum_security', '11', None), ('security_resourcing', '12', 'Security resourcing'),
         ('certifications', '13', None), ('fourth_party_vendors', '14', None), ('cloud_infrastructure', '15', None)]
LIFTED = {'sovereignty': 'data_sovereignty', 'residency': 'data_residency', 'terms_conditions': 'legal_terms',
          'resourcing': 'security_resourcing'}


def privacy_only(summary):
    """The privacy summary's first sentence (the policy). Legacy data only: the builders now write each
    sub-area's sentence into that section's own `summary` (user decision 2026-10-15, option b), so
    the privacy summary is already one sentence and this is a no-op for regenerated fixtures."""
    s = str(summary or '')
    cut = s.find('. ')
    return s[:cut + 1] if cut > 0 else s


def restructure(sections):
    """New sections dict (input not mutated beyond popping the lifted sub-objects from privacy)."""
    secs = dict(sections)
    priv = secs.get('privacy')
    if isinstance(priv, dict):
        priv = dict(priv)
        for old, new in LIFTED.items():
            sub = priv.pop(old, None)
            if isinstance(sub, dict) and new not in secs:
                sub = dict(sub)
                if sub.get('subtitle_source'):
                    sub['intro_source'] = sub.pop('subtitle_source')
                secs[new] = sub
        if any(k in sections['privacy'] for k in LIFTED):
            priv['summary'] = privacy_only(priv.get('summary'))
        secs['privacy'] = priv
    eo = secs.get('executive_overview')
    for m in ((eo or {}).get('scope_and_coverage') or {}).get('observed_targets') or []:
        if m.get('id') == 'hosts_observed_residency' and m.get('section') == 'privacy':
            m['section'] = 'data_residency'
    out = {}
    for key, num, title in ORDER:
        if key not in secs:
            continue
        sec = secs.pop(key)
        if title:      # head fields first, as on the other sections
            sec = {'number': num, 'title': sec.get('title') or title, 'group': 'assessment_details',
                   **{k: v for k, v in sec.items() if k not in ('number', 'title', 'group')}}
        elif 'number' in sec:
            sec['number'] = num
        out[key] = sec
    out.update(secs)      # unknown keys keep their place at the end
    return out


def migrate(path):
    raw = open(path, encoding='utf-8').read()
    indent = len(raw.split('\n', 2)[1]) - len(raw.split('\n', 2)[1].lstrip(' '))
    report = json.loads(raw)
    report['sections'] = restructure(report['sections'])
    open(path, 'w', encoding='utf-8').write(json.dumps(report, ensure_ascii=False, indent=indent) + '\n')


if __name__ == '__main__':
    for p in sys.argv[1:]:
        migrate(p)
        print('migrated', p)
