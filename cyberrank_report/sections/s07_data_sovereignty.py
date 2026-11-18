"""07 Data sovereignty (demerit rule E): governing law / courts found in the published policies,
compared with the jurisdictions accepted by the report owner/requestor.

Copy follows match_state, not the source narrative; the source's own verdict is quoted beside it.
With no preference set (enabled false or an empty allowed set) the observed data still prints,
marked 'Not compared: no preference set'. allowed_set absent -> the snapshot preference.
"""
from .. import components as C
from . import _shared as S

TEXT = {
    'no_preference': 'Not compared: no preference set. The governing law found is shown without validation.',
    'match': 'The governing law found is within the accepted jurisdictions ({allowed}), compared with {owner}.',
    'mismatch': 'The governing law found is outside the accepted jurisdictions ({allowed}), compared with '
                '{owner}. Check how disputes and legal obligations would be handled before relying on this supplier.',
    'unknown': 'No governing-law or court clause could be matched in the published policies, so legal location '
               'cannot be compared with {owner} ({allowed}). Treat it as unresolved until confirmed.',
    'not_found': 'No governing law or court location was found in the published legal terms.',
}
NOT_FOUND_CODES = ('not_identified', 'not_found')     # the check ran and found nothing (other nulls keep their reason)


def countries(data):
    """Governing-law / court countries as sent (string, {value}, or a list of them); legal text, not IP."""
    v = data.get('observed_jurisdiction')
    items = v if isinstance(v, list) else [v]
    return [str(S.val(x)).strip() for x in items if not C.is_missing(x) and str(S.val(x) or '').strip()]


def _not_found(data):
    v = data.get('observed_jurisdiction')
    if countries(data):
        return False
    return not isinstance(v, dict) or v.get('reason_code') in NOT_FOUND_CODES


def adjust(data, report):
    data = S.with_snapshot_pref(data, report, 'sovereignty_allowed_jurisdictions')
    if data.get('state') not in S.NO_RESULT and _not_found(data):
        return {**data, '_not_found': True}       # nothing found reads "Not found", never "Not compared"
    return S.adjust_compared(data, bool(countries(data)), data.get('allowed_set') or countries(data),
                             'Data sovereignty')


card = S.card


def _text(data):
    return TEXT[S.matched(data)].format(allowed=S.join(S.allowed(data)), owner=S.OWNER)


def verdict(data, ctx):
    return None if data.get('_card_only') else _text(data)


def _body(data):
    found = data.get('observed_jurisdiction')
    if countries(data):
        found_cell = ', '.join(countries(data))
    elif data.get('_not_found'):
        found_cell = 'Not found'
    else:
        found_cell = C.P(found.get('source_label') if isinstance(found, dict) and found.get('source_label')
                         else C.missing_text(found), 'cell_muted')
    match = S.matched(data)
    pairs = [('Governing law / courts found', found_cell), ('Accepted jurisdictions', S.join(S.allowed(data))),
             ('Against the preference', S.match_chip(match))]
    said = C.val(data.get('verdict_source'))
    if said:      # the source's own verdict, quoted; our reading is the row above it
        pairs.append(('Source result', f'“{said}”'))
    out = [C.key_value_list(pairs)]
    if data.get('summary') and _text(data) != data['summary']:      # the opener carries the summary
        out.append(C.P(_text(data), spaceBefore=6))
    out += S.quote(data)
    told = str(C.val(data.get('narrative_source')) or '').strip()      # a NullReason prints nothing
    src = f'Source text: “{told}”' if told else ''
    why = (f' Review note: the source gives its own result, but no governing-law clause was found, so this '
           f'report shows “{S.MATCH[match][0]}” until the clause is confirmed.'
           if said and match in ('unknown', 'not_found') else '')
    if (src + why).strip():
        out.append(C.note((src + why).strip()))
    return out


def build(data, ctx):
    ms = [m for m in data.get('metrics') or [] if isinstance(m, dict)]
    return ([C.kpi_strip(ms)] if ms else []) + _body(data)


def build_context(data, ctx):
    return [] if data.get('_card_only') else _body(data)
