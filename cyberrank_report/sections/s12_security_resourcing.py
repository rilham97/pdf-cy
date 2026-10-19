"""12 Security resourcing (demerit rule J): public evidence of privacy and security roles.

Not privacy criterion J 'Complexity and clarity' (section 03). Copy uses neutral_message (RF-05),
never the source's causal claim, plus any roles_found {role, sources[]}; absence of evidence is
not evidence of absence.
"""
from .. import components as C
from .. import icons as I
from .. import qa
from . import _shared as S

ROLE = {'detected': ('Detected', True), 'not_detected': ('Not detected in the sources checked', False)}
KINDS = ('privacy', 'security')


def adjust(data, report):
    return S.adjust_switched_off(data, any(data.get(f'{k}_role_evidence') for k in KINDS),
                                 'The security resourcing check was switched off for this assessment, so public '
                                 'evidence of privacy and security roles was not looked for.')


card = S.card


def _message(data):
    return data.get('neutral_message') or data.get('narrative_source')


def verdict(data, ctx):
    return None if data.get('_card_only') else _message(data)


def _role(v):
    if C.val(v) in ROLE:
        label, flag = ROLE[C.val(v)]      # no public evidence is not a failure (staff may exist): attention
        return I.yes_no_label(flag, label, status=None if flag else 'not_detected')
    if C.is_missing(v):
        return v
    qa.add('unknown_term', 'warn', f's12: role evidence "{C.val(v)}" is not a known value', once=True)    # as s13
    return I.status_label('not_assessed', f'Not recognised (“{C.val(v)}”)', 'unknown')


def _body(data):
    pairs = [(f'{k.capitalize()} role evidence', _role(data.get(f'{k}_role_evidence'))) for k in KINDS]
    for r in data.get('roles_found') or []:      # 'Data Protection Officer (Source: Company Website; LinkedIn)'
        if isinstance(r, dict) and C.val(r.get('role')):
            src = '; '.join(str(C.val(x)) for x in r.get('sources') or [] if C.val(x))
            pairs.append(('Role found', f'{C.val(r["role"])} (source: {src})' if src else C.val(r['role'])))
    out = [C.key_value_list(pairs)]
    if data.get('summary') and _message(data) and _message(data) != data['summary']:     # opener has the summary
        out.append(C.P(_message(data), spaceBefore=6))
    return out


def build(data, ctx):
    ms = [m for m in data.get('metrics') or [] if isinstance(m, dict)]
    return ([C.kpi_strip(ms)] if ms else []) + _body(data)


def build_context(data, ctx):
    return [] if data.get('_card_only') else _body(data)
