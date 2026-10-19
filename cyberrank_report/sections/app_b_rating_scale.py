"""Appendix B IISRI rating scale: the one-page ladder component (rating_scale.py).

render_section() already draws the eyebrow, H1 and intro, so the component's own
H1 + intro are dropped; its official intro sentence replaces the payload intro.
"""
from .. import rating_scale as RS
from ..theme import STYLES

STATE = {'assessed': 'assessed', 'unavailable': 'unavailable', 'not_assessed': 'not_assessed'}


def rating(report):
    r = report.get('rating') or {}
    grade = r.get('grade') if r.get('grade') in RS.GRADES else None
    if grade:
        return {'grade': grade, 'state': 'assessed', 'state_reason': None}
    return {'grade': None, 'state': STATE.get(r.get('state'), 'unavailable'),
            'state_reason': r.get('state_reason') or 'The rating was not provided in the assessment data.'}


def build(data, ctx):
    story = RS.build_rating_scale(rating(ctx.report), STYLES, appendix_label=None)
    return story[4:]      # [H1, Spacer, intro, Spacer]: the opener draws the H1 and the payload intro
