"""15 Cloud infrastructure: providers detected from public DNS / network records.

Inventory module: 'findings' means providers were observed, not risk. An empty
result reads 'not detected with the methods used', never 'no cloud'.
"""

METHODS = {'dns_records': 'DNS records', 'ip_ranges': 'IP ranges', 'mx_records': 'MX records',
           'ns_records': 'NS records'}
NOT_DETECTED = 'No cloud provider detected with the methods used'
CLEAR_REASON = ('Only providers visible in public DNS, IP-range, MX and NS records can be detected. '
                'Services reached through other providers or used only internally are not visible '
                'to this check.')


def _method(code):
    return METHODS.get(code, str(code).replace('_', ' '))


def _methods(data):
    return [_method(m) for m in data.get('detection_methods') or []]


def _scan_date(data, c):
    ls = data.get('last_scanned')
    return c.missing_text(ls) if c.is_missing(ls) else c.fmt_date(ls)


def card(data, ctx):
    c, kw = ctx.c, {}
    if ctx.state == 'clear':           # other states show methods and scan date in the body, or ran no check
        if not (data.get('state_reason') or data.get('reason_code') or
                (data.get('empty_state_source') or {}).get('text')):
            kw['reason'] = CLEAR_REASON      # otherwise the shared default_card reason (payload first)
        if not (data.get('what_checked') or (data.get('empty_state_source') or {}).get('coverage')):
            methods = _methods(data)
            kw['what_checked'] = ([f'Detection methods: {", ".join(methods)}.'] if methods else []) + [
                f'Last scanned: {_scan_date(data, c)} (report assessment date {ctx.identity["assessment_date"]}).']
    if ctx.state == 'not_assessed' and not data.get('next_step'):
        kw['next_step'] = ('Run the cloud infrastructure module for this organisation. Providers are then '
                           'detected from public DNS records, IP ranges, MX records and NS records.')
    return kw


def _kpis(data, ctx):
    c = ctx.c
    items = [m for m in data.get('metrics') or [] if isinstance(m, dict)]
    ls = data.get('last_scanned') or {'value': None, 'reason': 'scan date not recorded'}
    label = f'Last scanned, cloud module\nReport assessed {ctx.identity["assessment_date"]}'
    items.append({**ls, 'label': label, 'unit': None} if c.is_missing(ls) else
                 {'label': label, 'value': c.fmt_date(ls)})
    return items


def _provider_table(providers, ctx, methods):
    """Provider rows; a column missing for every provider collapses into the note under the table."""
    c = ctx.c
    cols = [('Provider', 'provider'), ('Detected by', 'detection_methods'), ('Observed', 'observed_at')]

    def cell(p, key):
        v = p.get(key)
        if key == 'provider':
            return v if v else {'value': None, 'reason': 'provider name not recorded'}
        if c.is_missing(v):
            return v or {'value': None, 'reason': 'not recorded'}
        if key == 'detection_methods':
            return ', '.join(_method(m) for m in (v if isinstance(v, list) else [v]))
        return c.fmt_date(v)

    keep, gone = [], {}
    for label, key in cols:
        vals = [p.get(key) for p in providers]
        if key != 'provider' and all(c.is_missing(v) for v in vals):
            gone.setdefault(c.reason_text(vals[0] or {}), []).append(label.lower())
        else:
            keep.append((label, key))
    t = ctx.t
    widths = None if len(keep) == 1 else [t.COL3] + [(t.CW - t.COL3) / (len(keep) - 1)] * (len(keep) - 1)
    out = [c.compact_table([lbl for lbl, _ in keep], [[cell(p, k) for _, k in keep] for p in providers],
                           widths=widths)]
    notes = [f'Detection methods: {", ".join(methods)}.'] if methods else []
    notes += [f'{" and ".join(labels).capitalize()} per provider: not available ({reason}).'
              for reason, labels in gone.items()]
    if notes:
        out.append(c.note(' '.join(notes)))
    return out


def build(data, ctx):
    c = ctx.c
    providers = [p for p in data.get('providers') or [] if isinstance(p, dict)]
    if ctx.state == 'clear' and not providers:
        return []                      # the clear card carries the message and what was checked
    out = [c.kpi_strip(_kpis(data, ctx))]      # scan date only: no staleness flag (business answer 8)
    out.append(c.heading('Detected providers', 2))
    methods = _methods(data)            # module scope (intro_source), not per-provider evidence
    if providers:
        return out + _provider_table(providers, ctx, methods)
    return out + [c.P(f'{NOT_DETECTED}.', 'body')] + (
        [c.note(f'Detection methods: {", ".join(methods)}.')] if methods else [])
