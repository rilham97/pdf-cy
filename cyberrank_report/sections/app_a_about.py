"""Appendix A: About this report. Static text from the payload + report details
+ the result-state legend (how to read the chips used throughout the report)."""

STATE_MEANING = {
    'findings': 'Assessed; weaknesses were reported. The severity marks and scores show how serious they are.',
    'identified': 'Assessed; items were found in an inventory or good-news section (priority actions, security '
                  'roles, certifications, fourth-party vendors, cloud). Not a risk by itself.',
    'clear': 'Assessed; nothing was found within the sources and period checked. It does not mean the '
             'organisation is safe.',
    'not_assessed': 'The module was not run for this report. No result is implied.',
    'not_applicable': 'The check does not apply to this organisation.',
    'unavailable': 'The value could not be obtained or used. The reason is printed with it.',
    'partial': 'Only part of the scope was covered; the results cover the part shown.',
    'pending_review': 'A value exists but its meaning is unclear or contradicted; held for review.',
    'none_identified': 'Assessed; nothing was found in an inventory section. Not a statement about risk.',
}


def _date(v, c):
    return v if c.is_missing(v) else c.fmt_date(v)


def _details(ctx):
    c, rep = ctx.c, ctx.report
    ident, snap = rep.get('identity') or {}, rep.get('snapshot') or {}
    issuer = ident.get('issuer') or {}
    absent = {'value': None, 'reason_code': 'not_printed_in_source'}
    return [
        ('Organisation', ident.get('organisation_name') or absent),
        ('Domain', ident.get('domain') or absent),
        ('Assessment date', _date(snap.get('assessed_at') or absent, c)),
        ('Report generated', _date(snap.get('generated_at') or absent, c)),
        ('Issued by', issuer.get('organisation_name') or {'value': None, **issuer}),
        ('Assessment ID', snap.get('assessment_id') or absent),
    ]


def build(data, ctx):
    c = ctx.c
    out = []
    if data.get('about_source'):       # plays the opener intro unless the payload carries one
        out.append(c.P(data['about_source'], 'body') if data.get('intro_source') else
                   c.P(data['about_source'], 'intro', keepWithNext=1))
    sources = data.get('data_sources_source') or []
    if sources:
        out += [c.heading('Data sources', 3)] + c.bullets([c.sentence(s) for s in sources])
    out += [c.heading('Report details', 3), c.key_value_list(_details(ctx))]
    out += [c.heading('Reading the result states', 3),
            c.P('Each assessed section shows one of these states next to its verdict.', 'body'),
            c.compact_table(['State', 'Meaning'],
                            [[c.state_chip(s, dense=True), m] for s, m in STATE_MEANING.items()],
                            widths=[104, ctx.t.CW - 104], dense=True, header_fill=False)]
    if data.get('closing_source'):     # verbatim closing line of the source page
        out.append(c.P(data['closing_source'], 'note'))
    return out
