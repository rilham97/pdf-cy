"""Reference section module. Copy to sections/<spec.module>.py and adapt.

Contract (see sections/__init__.py):
  * build(data, ctx) returns the BODY only. The opener (eyebrow, H1, intro,
    state chip + verdict) and the state card are drawn by render_section().
  * Never pass raw data into M(); use P(), tech(), compact_table(), fmt_value().
  * Missing is never 0: fmt_value()/table cells print 'Not available (reason)'.
  * H2 via c.heading(text, 2) (outline entry), H3 via c.heading(text, 3).
  * Short groups: c.keep(...). Big tables: compact_table (header repeats,
    rows split). Full registers live in Appendix D; link with register_pointer.
  * No PageBreak / CondPageBreak in sections. Ever.
"""


def card(data, ctx):
    """Optional: refine the state card. Return kwargs for components.state_card."""
    return {}


def build(data, ctx):
    c = ctx.c
    out = []

    metrics = [m for m in data.get('metrics') or [] if isinstance(m, dict)]
    if metrics:
        out.append(c.kpi_strip(metrics))

    findings = data.get('findings') or []
    if findings:
        out.append(c.heading('Findings', 2))
        out.append(c.P(f'{len(findings)} finding types, ordered as reported.', 'body'))
        rows = [[i, c.severity_chip(f.get('severity')), f.get('finding_type'),
                 f.get('affected_assets_count'),
                 f.get('breach_likelihood') or {'value': None, 'reason_code': 'not_printed_in_source'}]
                for i, f in enumerate(findings, 1)]
        # severity always right after the '#' / ID column
        out.append(c.compact_table(['#', 'Severity', 'Finding', 'Affected assets', 'Breach likelihood'],
                                   rows, numeric_cols=(0, 3, 4)))

    ref = next((v for k, v in data.items() if k.endswith('register_ref') and isinstance(v, str)), None)
    if ref:
        reg = ctx.report
        for part in ref.split('.'):
            reg = (reg or {}).get(part)
        rid = ref.rsplit('.', 1)[-1]
        rows = ((reg or {}).get('counts') or {}).get('rows')
        out.append(c.register_pointer(rid, rows, title=rid.replace('_', ' ').capitalize()))

    if data.get('note'):
        out.append(c.note(data['note']))
    return out
