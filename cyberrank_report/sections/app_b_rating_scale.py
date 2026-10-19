"""Appendix B IISRI rating scale: the one-page ladder component (rating_scale.py).

render_section() already draws the eyebrow, H1 and the payload intro (intro_source), so the
component's own H1 and its official intro sentence (RS.INTRO) are dropped: only intro_source prints.
"""
from .. import rating_scale as RS
from ..theme import STYLES

NO_GRADE_REASON = 'The rating was not provided in the assessment data.'


def rating(report):
    """rating.grade as text or {value}, any case; no valid grade -> the payload state when the component
    knows it (unavailable / not_assessed), else unavailable. A non-text state_reason is not printed."""
    r = report.get('rating') or {}
    g = r.get('grade')
    g = str((g.get('value') if isinstance(g, dict) else g) or '').strip().upper()
    if g in RS.GRADES:
        return {'grade': g, 'state': 'assessed', 'state_reason': None}
    reason = r.get('state_reason')
    return {'grade': None, 'state': r.get('state') if r.get('state') in RS.STATE_TEXT else 'unavailable',
            'state_reason': reason.strip() if isinstance(reason, str) and reason.strip() else NO_GRADE_REASON}


def build(data, ctx):
    story = RS.build_rating_scale(rating(ctx.report), STYLES, appendix_label=None)
    return story[4:]      # [H1, Spacer, intro, Spacer]: the opener draws the H1 and the payload intro
