"""Helpers shared by the preference-compared sections (07 Data sovereignty, 08 Data residency)
and the other Global360 sections (09 Legal terms & conditions, 12 Security resourcing).

Namespace note: these are demerit-ledger areas E, F, G, J. Privacy criterion H 'Data residency'
(section 03) is policy text about location / transfer and is a different thing from section 08.
"""
from .. import components as C
from .. import icons as I

NO_RESULT = ('not_assessed', 'not_applicable', 'unavailable')
OWNER = 'the preference set by the report owner/requestor'
MATCH = {'match': ('Matches the preference', True),            # label, yes/no flag, status key
         'mismatch': ('Does not match the preference', False),
         'unknown': ('Cannot be compared', None, 'cannot_compare'),
         'no_preference': ('Not compared: no preference set', None, 'not_compared')}
NOT_COMPARED = 'Not compared: no preference set. The observed data is shown below without validation.'


def val(v):
    return v.get('value') if isinstance(v, dict) else v


def join(items, none='No preference set'):
    return ', '.join(str(i) for i in items or []) or none


def match_chip(state):
    label, flag, *status = MATCH.get(state) or MATCH['unknown']
    return I.yes_no_label(flag, label, status=status[0] if status else None)


def quote(data):
    q = C.val((data or {}).get('quote_source'))
    return [C.P(f'Policy text: “{str(q).strip()}”', 'body', spaceBefore=6)] if q else []


def no_pref(data):
    return data.get('enabled') is False or not data.get('allowed_set')


def adjust_switched_off(data, has_data, why=None):
    """A switched-off module (enabled false) renders as not_applicable; a no-result state without
    data renders its card only (`_card_only`). Otherwise data unchanged. Idempotent."""
    if data.get('_card_only') or data.get('_no_preference'):
        return data
    if data.get('enabled') is False:
        return {**data, 'state': 'not_applicable', 'state_reason': data.get('state_reason') or why,
                '_card_only': True}
    if data.get('state') in NO_RESULT and not has_data:
        return {**data, '_card_only': True}
    return data


def adjust_compared(data, observed, has_data):
    """Sovereignty / residency: with no preference set but data observed, show the data marked
    'Not compared: no preference set' (state not_applicable, `_no_preference`). Idempotent."""
    if data.get('_card_only') or data.get('_no_preference'):
        return data
    if no_pref(data) and observed and data.get('state') not in NO_RESULT:
        return {**data, 'state': 'not_applicable', 'state_reason': NOT_COMPARED, '_no_preference': True}
    return adjust_switched_off(data, has_data, 'Not compared: no preference set.')


def card(data, ctx):
    """Card reason: a pending review names its coded reason (the payload's state_reason is an
    extraction note); a no-result card falls back to the source's own reason or narrative."""
    if data.get('state') == 'pending_review' and data.get('reason_code'):
        why = C.reason_text({'reason_code': data['reason_code']})
        return {'reason': C.sentence(why if why.lower().startswith('held for review') else 'held for review: ' + why)}
    if data.get('state') in NO_RESULT:
        return {'reason': data.get('state_reason') or (C.reason_text(data) if data.get('reason_code') else None)
                or data.get('reason') or data.get('narrative_source')}
    return {}


def matched(data, nopref_key='_no_preference'):
    return 'no_preference' if data.get(nopref_key) else data.get('match_state') or 'unknown'
