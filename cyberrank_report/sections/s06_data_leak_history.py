"""06 Data breach and leak history.

Layout: KPI strip (+ 'Last valid event' tile) -> one sentence naming the event used
in the rating (only when the payload names it; never guessed) -> timeline -> event
table -> sources.
clear / no events: the kit's clear card carries the message; the body is the strip.

Event fields read (R12 + old-report card): event_id, canonical_event_id, entity_link, event_type,
occurred_at, disclosed_at, validity_state, scoring_eligible, scoring_reason,
records_affected, records_unit, records_scope, date_basis, age_days_at_assessment, demerit_applied,
description / description_source, source_url.

Rules: an event without a validity flag is valid (business answer 2026-10-15); validity_state
'unknown' (policy validity_values) is its own neutral status 'Validity not confirmed', never counted
as valid. An event marked reported inaccurate or not scoring eligible is never 'Used in rating' (Q16).
When the payload names an event that is reported inaccurate, not scoring eligible, resolved or of
unconfirmed validity as the last valid event, the section is held for review (adjust()). An event
resolved by the user or an admin (validity_state 'resolved') is listed with a 'Resolved' status (icon,
green as theme.TONE 'resolved'), distinct from 'Reported inaccurate', and is not counted as open: the
'Open events' tile (shown when an event is resolved) counts every listed event except the resolved
ones, and a note states the rule. Events sharing a canonical_event_id are one event (one row, sources
merged); last_valid_event may name any of the merged records.
"""
from datetime import date

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable

from .. import theme as T
from ..text import esc, fmt_date, hexstr, is_missing
from .s13_certifications import LinkTech, field, label, reason_of, stack, widths

NBSP = '\u00a0'
FIXED = {'Date': 92, 'Records affected': 96, 'Status': 104}
BASIS = {'occurred_at': 'occurrence date', 'disclosed_at': 'disclosure date', 'ingested_at': 'ingestion date'}

KINDS = {   # status text / timeline marker colour (theme.status_color)
    'rating': ('Used in rating', T.status_color('used_in_rating')),
    'eligible': ('Scoring eligible', T.status_color('scoring_eligible')),
    'historical': ('Historical', T.status_color('historical')),
    'valid': ('Valid', T.status_color('recorded')),       # a recorded event, not a verdict
    'inaccurate': ('Reported inaccurate · not scored', T.status_color('inaccurate')),
    'resolved': ('Resolved', T.status_color('resolved')),
    'unknown': ('Validity not confirmed', T.status_color('unknown')),
}
HOLLOW = ('inaccurate', 'resolved', 'unknown')       # timeline markers drawn as rings: not counted as valid


def _val(v):
    return v.get('value') if isinstance(v, dict) else v


def _day(v):
    """Date field -> datetime.date (precision month/year -> first day), or None."""
    if is_missing(v):
        return None
    parts = [int(p) for p in str(_val(v))[:10].split('-') if p.isdigit()]
    if not parts:
        return None
    return date(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1)


def _inaccurate(ev):
    return str(_val(ev.get('validity_state')) or '').lower() in ('reported_inaccurate', 'inaccurate')


def _resolved(ev):
    return str(_val(ev.get('validity_state')) or '').lower() == 'resolved'


def _unconfirmed(ev):
    return str(_val(ev.get('validity_state')) or '').lower() == 'unknown'


def _eligible(ev):
    """False when the event is marked inaccurate or not scoring eligible (never scored)."""
    return not (_inaccurate(ev) or _val(ev.get('scoring_eligible')) is False)


def _not_scored(ev):
    """Why a named last valid event cannot be shown as used in the rating, or None."""
    if not _eligible(ev):
        return 'reported inaccurate' if _inaccurate(ev) else 'not scoring eligible'
    if _resolved(ev):
        return 'resolved'
    if _unconfirmed(ev):
        return 'of unconfirmed validity'
    return None


def _kind(ev, lead):
    if _inaccurate(ev):
        return 'inaccurate'
    if _resolved(ev):
        return 'resolved'
    if _unconfirmed(ev):
        return 'unknown'
    if lead is not None and ev is lead and _eligible(ev):
        return 'rating'
    elig = _val(ev.get('scoring_eligible'))
    return 'eligible' if elig is True else 'historical' if elig is False else 'valid'     # no flag: valid


def _lead(data, events):
    """The event the payload says is used in the rating, else None (never inferred)."""
    lve = data.get('last_valid_event')
    if is_missing(lve) or not isinstance(lve, (dict, str)):
        return None
    ref = (lve.get('event_id') or lve.get('value')) if isinstance(lve, dict) else lve
    hit = next((e for e in events if ref and any(x.get('event_id') == ref for x in [e, *e.get('_also', [])])),
               None)      # a record merged away by canonical_event_id resolves to its kept event
    return hit or (lve if isinstance(lve, dict) and lve.get('occurred_at') else None)


def merge_events(events):
    """One entry per canonical_event_id (first record kept; the others' sources attached)."""
    out, seen = [], {}
    for e in events:
        cid = _val(e.get('canonical_event_id'))
        if cid and cid in seen:
            seen[cid].setdefault('_also', []).append(e)
            continue
        e = dict(e)
        out.append(e)
        if cid:
            seen[cid] = e
    return out


HOLD = {   # reason why -> (reason_code, card text)
    'resolved': ('lead_event_resolved', 'The event named as the last valid event is marked resolved, so it is not '
                 'shown as the event used in the rating. Which event, if any, is scored is held for review.'),
    'of unconfirmed validity': ('lead_event_unconfirmed', 'The event named as the last valid event has validity '
                                '“unknown”, so it is not shown as the event used in the rating. Which event, if '
                                'any, is scored is held for review.'),
}
NOT_ELIGIBLE = ('lead_event_not_eligible', 'The event named as the last valid event is marked reported inaccurate '
                'or not scoring eligible, so it cannot be the event used in the rating. Which event, if any, is '
                'scored is held for review.')


def adjust(data, report):
    """Last valid event that is inaccurate / not scoring eligible / resolved / unconfirmed -> pending_review."""
    from . import hold
    events = merge_events([e for e in data.get('events') or [] if isinstance(e, dict)])
    lead = _lead(data, events)
    why = None if lead is None else _not_scored(lead)
    if why is None:
        return data
    return hold(data, *HOLD.get(why, NOT_ELIGIBLE))


def _details(ev):
    return _val(ev.get('description')) or _val(ev.get('description_source')) or _val(ev.get('summary'))


class Timeline(Flowable):
    """Year axis from the earliest event to the assessment date; one marker per dated
    event (colour = status), stacked when markers would touch."""
    H, R = 60.0, 3.6

    def __init__(self, points, end):
        super().__init__()
        self.points, self.end = points, end          # points: [(date, kind)]

    def wrap(self, aw, ah):
        self.width = aw
        return aw, self.H

    def draw(self):
        cv, w = self.canv, self.width
        days = [d for d, _ in self.points] + ([self.end] if self.end else [])
        y0, y1 = min(days).year, max(days).year + 1
        left, right = 4.0, w - 4.0
        span = (date(y1, 1, 1) - date(y0, 1, 1)).days
        x = lambda d: left + (right - left) * (d - date(y0, 1, 1)).days / span
        ax = 22.0
        cv.setStrokeColor(T.RULE)
        cv.setLineWidth(0.75)
        cv.line(left, ax, right, ax)
        step = 1 if y1 - y0 <= 12 else 2 if y1 - y0 <= 24 else 5
        cv.setFont(T.STYLES['note_flush'].fontName, T.STYLES['note_flush'].fontSize)
        cv.setFillColor(T.MUTED)
        for yr in range(y0, y1 + 1):
            xx = x(date(yr, 1, 1))
            cv.line(xx, ax - 3, xx, ax + 3)
            if (yr - y0) % step == 0 and yr < y1:
                cv.drawString(xx + 2, ax - 12, str(yr))
        if self.end:
            xe = x(self.end)
            cv.setStrokeColor(T.HEADING)
            cv.setDash(1.5, 1.5)
            cv.line(xe, ax - 6, xe, ax + 18)
            cv.setDash()
        last = {}                                    # stack level -> last x
        for d, kind in sorted(self.points):
            xx, lvl = x(d), 0
            while xx - last.get(lvl, -99) < 2 * self.R + 1.5:
                lvl += 1
            last[lvl] = xx
            self._marker(xx, ax + lvl * (2 * self.R + 1.5), kind)
        lx, ly = left, self.H - 8
        nf = T.STYLES['note_flush']
        cv.setFont(nf.fontName, nf.fontSize)
        for kind in [k for k in KINDS if any(k == p for _, p in self.points)]:
            self._marker(lx + self.R, ly + 2.6, kind)
            text = KINDS[kind][0].split(' · ')[0]      # legend names the marker; the table row says 'not scored'
            cv.setFillColor(T.BODY)
            cv.drawString(lx + 2 * self.R + 4, ly, text)
            lx += 2 * self.R + 4 + stringWidth(text, nf.fontName, nf.fontSize) + 14
        if self.end:
            cv.setStrokeColor(T.HEADING)
            cv.setDash(1.5, 1.5)
            cv.line(lx + 3, ly - 2, lx + 3, ly + 7)
            cv.setDash()
            cv.setFillColor(T.BODY)
            cv.drawString(lx + 9, ly, f'Assessment date ({fmt_date(self.end.isoformat())})')

    def _marker(self, xx, yy, kind):
        cv, color = self.canv, KINDS[kind][1]
        cv.setLineWidth(1)
        cv.setStrokeColor(color)
        cv.setFillColor(T.WHITE if kind in HOLLOW else color)
        cv.circle(xx, yy, self.R, stroke=1, fill=1)


def _event_cell(c, ev, any_src):
    """Event text + its source link inside the row (no trailing source list that could
    spill alone onto a page)."""
    ent = _val(ev.get('entity_link')) or _val(ev.get('entity'))
    head = f'<font name="{T.MEDIUM}" color="{hexstr(T.HEADING)}">{esc(ent)}</font>' if ent else \
        f'<font color="{hexstr(T.MUTED)}">Entity not recorded</font>'
    if _val(ev.get('event_type')):
        head += f'  ·  {esc(label(_val(ev["event_type"])))}'
    det = _details(ev)
    body = f'<br/>{esc(det)}' if det else ''
    muted = []
    if _val(ev.get('scoring_reason')):
        muted.append(f'Rating: {_val(ev["scoring_reason"])}')
    if any_src and not _val(ev.get('source_url')):
        muted.append(f'Source not available ({reason_of(field(ev, "source_url"))})')
    also = ev.get('_also') or []
    if also:
        muted.append(f'Same event (ID {_val(ev["canonical_event_id"])}) also reported by {len(also)} other '
                     f'source record{"s" if len(also) != 1 else ""}; counted once.')
    body += ''.join(f'<br/><font color="{hexstr(T.MUTED)}">{esc(m)}</font>' for m in muted)
    cell = c.M(head + body, 'cell')
    links = [LinkTech(u, 'dense_tech') for u in dict.fromkeys(_val(x.get('source_url')) for x in [ev, *also])
             if u]
    return [cell, *links] if links else cell


SCOPES = {'organisation': 'this organisation only', 'aggregate_multi_service': 'aggregate across several services',
          'customer_tenant': "a customer tenant's data", 'unknown': 'scope not stated'}


def _records_cell(c, ev):
    """Count + its unit and scope (a breach total can be multi-service or a customer's tenant)."""
    rec = field(ev, 'records_affected')
    if is_missing(rec):
        return rec
    unit, scope = _val(ev.get('records_unit')), _val(ev.get('records_scope'))
    head = c.fmt_number(_val(rec)) + (f' {str(label(unit)).lower()}' if unit else '')
    subs = ([] if unit else ['unit not recorded']) + ([SCOPES.get(str(scope), label(scope))] if scope else [])
    return stack(c, head.replace(' ', NBSP), subs, 'cell_num') if subs else head


def _date_cell(c, ev):
    occ = field(ev, 'occurred_at')
    if is_missing(occ):
        return c.P(c.missing_text(occ), 'cell_muted')
    disc = ev.get('disclosed_at')
    sub = [f'Disclosed {fmt_date(disc)}'.replace(' ', NBSP).replace(NBSP, ' ', 1)] \
        if not is_missing(disc) and _val(disc) != _val(occ) else []
    basis = _val(ev.get('date_basis'))
    if basis:
        sub.append(f'Dated by {BASIS.get(basis) or str(label(basis)).lower()}')
    age = _val(ev.get('age_days_at_assessment'))
    if age is not None:      # recency as the payload computed it; the demerit stays internal
        sub.append(f'{c.fmt_number(age)} days before assessment')
    return stack(c, fmt_date(occ), sub)


def _lead_note(c, data, lead, events):
    """One sentence naming the rating event; the table row carries the details."""
    if lead is None:
        lve = data.get('last_valid_event')
        return c.note(f'Event used in the rating: {c.missing_text(lve if isinstance(lve, dict) else None)}. '
                      'The events below are listed without marking one as rating-determining.')
    when = '' if is_missing(lead.get('occurred_at')) else fmt_date(lead['occurred_at']) + ' '
    what = 'event' if is_missing(lead.get('event_type')) else str(label(lead['event_type'])).lower()
    where = f' on {_val(lead["entity_link"])}' if _val(lead.get('entity_link')) else ''
    row = next((i for i, e in enumerate(events, 1) if e is lead), None)
    tail = f' (row {row})' if row else '; it is not in the event list below'
    why = _not_scored(lead)
    if why:
        scored = ' and is not scored' if not _eligible(lead) else ''
        return c.note(f'The assessment data names the {when}{what}{where}{tail} as the last valid event, but that '
                      f'event is {why}{scored}. No event is shown as used in the rating until this is reviewed.')
    return c.P(f'The rating uses the {when}{what}{where}{tail}.')


def build(data, ctx):
    c = ctx.c
    out = []
    metrics = [m for m in data.get('metrics') or [] if isinstance(m, dict)]
    lve = data.get('last_valid_event')
    raw = [e for e in data.get('events') or [] if isinstance(e, dict)]
    events = merge_events(raw)
    lead = _lead(data, events)
    if lve is not None:
        tile = {'label': 'Last valid event', 'value': None, 'state': None}
        why = None if lead is None else _not_scored(lead)
        if why:      # never a date for an event that cannot be shown as scored
            tile.update(reason=f'named event is {"not scoring eligible" if not _eligible(lead) else why}; held for '
                               'review', state='pending_review')
        elif lead is not None and not is_missing(lead.get('occurred_at')):
            tile['value'] = fmt_date(lead['occurred_at'])
        else:
            tile.update(lve if isinstance(lve, dict) else {}, label='Last valid event', value=None)
        metrics.append(tile)
    resolved = sum(1 for e in events if _resolved(e))
    if resolved:      # rule: resolved events are listed, never counted as open
        metrics.append({'label': 'Open events (excludes resolved)', 'value': len(events) - resolved,
                        'unit': 'events'})
    if metrics:
        out.append(c.kpi_strip(metrics))
    said = _val(data.get('last_reported_source')) or (lve.get('source_label') if isinstance(lve, dict) else None)
    if said:      # the source's own sentence, quoted; the event table and lead note give our reading
        out.append(c.note(f'Source: “{said.strip()}”'))
    if not events:
        return out
    events.sort(key=lambda e: _day(e.get('occurred_at')) or date.min, reverse=True)
    any_src = any(_val(e.get('source_url')) for e in events)

    dated = [(_day(e.get('occurred_at')), _kind(e, lead)) for e in events]
    end = _day((ctx.report.get('snapshot') or {}).get('assessed_at'))
    out += [c.heading(f'Events in the period checked ({len(events)})', 2), _lead_note(c, data, lead, events)]
    if len(raw) != len(events):
        out.append(c.note(f'{len(raw)} source records describe {len(events)} distinct events: records that share an '
                          'event ID are one event, counted once.'))
    rep_n = next((m.get('value') for m in metrics if m.get('id') == 'events_reported'), None)
    if isinstance(rep_n, (int, float)) and rep_n != len(events):      # both counts print: tile and heading
        from .. import qa
        what = (f'counts {len(raw)} source records; {len(events)} distinct events' if rep_n == len(raw) else
                f'matches neither the {len(raw)} source records nor the {len(events)} distinct events')
        qa.add('data_mismatch', 'warn', f's06: events_reported={rep_n} {what}', once=True)
    if any(d for d, _ in dated):
        out.append(Timeline([(d, k) for d, k in dated if d], end))
    undated = sum(1 for d, _ in dated if not d)
    if undated:
        out.append(c.note(f'{undated} event{"s" if undated != 1 else ""} without a date '
                          f'appear{"" if undated != 1 else "s"} in the table only.'))
    columns = ['Date', 'Event', 'Records affected', 'Status']
    rows = [[_date_cell(c, e), _event_cell(c, e, any_src), _records_cell(c, e), _status(c, e, lead)]
            for e in events]
    out.append(c.compact_table(columns, rows, widths=widths(columns, FIXED, 'Event'), numeric_cols=(2,)))
    if any(_resolved(e) for e in events):
        out.append(c.note('Resolved events were closed by the organisation or an administrator. They stay in the '
                          'list and the timeline but are not counted as open events.'))
    return out


def _status(c, ev, lead):
    """Status words are plain text (the timeline marker carries the colour); 'Resolved' carries its icon."""
    kind = _kind(ev, lead)
    if kind == 'resolved':
        from .. import icons as I
        return I.status_label('clear', 'Resolved', 'resolved')
    return KINDS[kind][0]
