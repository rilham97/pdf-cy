"""09 Legal terms & conditions (demerit rule G): customer-protection clauses in the published terms
of a public login / payment portal.

Source words ('# No') become yes/no icons, URLs links. Rule G (two clauses, portal present):
neither clause found counts against the rating; one or both found does not. The outcome line is
the verdict; the source narrative prints in the body (or as the verdict when there is no outcome).
"""
from .. import components as C
from .. import icons as I
from . import _shared as S

YES_WORDS = {'detected': True, 'found': True, 'yes': True, 'true': True,
             'not detected': False, 'not found': False, 'no': False, 'false': False}
PORTAL_LABEL = 'login / payment portal'


def _has_data(data):
    return data.get('rows') or data.get('portal_detected') is not None


def adjust(data, report):
    return S.adjust_switched_off(data, _has_data(data), name='Legal terms & conditions')


card = S.card


def _word(v):
    """Source word without its markdown residue ('# No' -> 'No')."""
    return str(v).lstrip('#').strip() if isinstance(v, str) else v


def _flag(v):
    w = _word(S.val(v))
    if isinstance(w, bool):
        return w
    return YES_WORDS.get(w.lower()) if isinstance(w, str) else None


def _tc_value(v, status=None):
    """A clause present is good, absent bad; status overrides (a portal is a fact, not a verdict).
    A NullReason stays as is (the key/value list prints 'Not available (reason)')."""
    if C.is_missing(v):
        return v
    w = _word(S.val(v))
    if isinstance(w, bool) or (isinstance(w, str) and w.lower() in YES_WORDS):
        return I.yes_no_label(_flag(w), w if isinstance(w, str) else None, status=status)
    if isinstance(w, str) and w.lower().startswith(('http://', 'https://')):
        from .s13_certifications import LinkTech
        return LinkTech(w, 'cell_tech')
    return w


def _is_portal(r):
    """The portal flag row: id `portal_detected` or the exact label "Login / Payment Portal" (any case)."""
    return r.get('id') == 'portal_detected' or str(C.val(r.get('label')) or '').strip().lower() == PORTAL_LABEL


def _raw(data):
    """(label, value, is the portal flag row) per rows[] item."""
    return [(C.val(r.get('label')) or 'Row label not recorded',
             r.get('value_source') if r.get('value_source') is not None else r.get('value'), _is_portal(r))
            for r in data.get('rows') or [] if isinstance(r, dict)]


def _portal(data, raw):
    """portal_detected (bool, yes/no word or {value}); missing or a NullReason -> the portal row; None = unknown."""
    p = data.get('portal_detected')
    return next((_flag(v) for _, v, is_p in raw if is_p), None) if C.is_missing(p) else _flag(p)


def _clauses(data, raw):
    """(clauses found, rule G outcome line) when a portal is present and both clauses are known."""
    def find(*keys):
        return next((_flag(v) for lbl, v, _ in raw if all(k in str(lbl).lower() for k in keys)), None)
    portal = _portal(data, raw)
    protect, notify = find('protect'), find('notif') if find('notif') is not None else find('breach')
    if portal is not True or protect is None or notify is None:
        return None, None
    n = protect + notify
    return n, ('Neither clause found; counted against the rating.' if n == 0 else
               'One clause found; not counted against the rating.' if n == 1 else
               'Both clauses found; not counted against the rating.')


def _outcome(data):
    return _clauses(data, _raw(data))[1]


def verdict(data, ctx):
    if data.get('_card_only'):
        return None
    return _outcome(data) or data.get('narrative_source')


def metrics(data):
    ms = [m for m in data.get('metrics') or [] if isinstance(m, dict)]
    n = _clauses(data, _raw(data))[0]
    if ms or n is None:
        return ms
    return [{'id': 'clauses_found', 'label': 'Customer-protection clauses found (of 2)', 'value': n,
             'unit': 'clauses', 'state': data.get('state')}]


def _body(data, ctx):
    raw = _raw(data)
    rows = [(lbl, _tc_value(v, 'not_compared' if is_p else None)) for lbl, v, is_p in raw]
    pv = data.get('portal_detected')
    if pv is not None and (not rows or C.is_missing(pv) and not any(p for *_, p in raw)):
        flag = _flag(pv)      # no rows, or a null flag with no portal row: its reason prints ('Not available (…)')
        rows.insert(0, ('Login / payment portal', pv if C.is_missing(pv) else _word(S.val(pv)) if flag is None else
                        I.yes_no_label(flag, 'Detected' if flag else 'Not detected', status='not_compared')))
    out = [C.key_value_list(rows)] if rows else []
    shown = data.get('summary') or verdict(data, ctx)        # what the opener already says
    outcome = _clauses(data, raw)[1]
    if outcome and outcome != shown:
        out.append(C.P(outcome, 'body', spaceBefore=6))
    if data.get('narrative_source') and data['narrative_source'] != shown:
        out.append(C.P(data['narrative_source'], spaceBefore=6))
    return out


def build(data, ctx):
    ms = metrics(data)
    return ([C.kpi_strip(ms)] if ms else []) + _body(data, ctx)


def build_context(data, ctx):
    return [] if data.get('_card_only') else _body(data, ctx)
