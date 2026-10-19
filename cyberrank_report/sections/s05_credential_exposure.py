"""05 Credential exposure -- risk overview; supporting tables and the row register live in Appendix D
(register id RID['s05'] from the registry order).

Long-list policy (lists.credential_exposure), option B (user decision 2026-10-15): Section 05 prints
aggregates and points to Appendix <D.n>.4, which lists every register row -- the account label exactly as
delivered by the Cyberrank system (masked upstream; never re-masked here), the approximate exposure
period, the exposed field categories (names only, never values) and the row status when present.
Labels without a mask character print as received and raise QA 'unmasked_account_label'.
Every count is derived from the register rows (analysed = received - suppressed) and
reconciled against the source headline and the payload metrics; differences print.
Grounded redesign (Verdict_Section08_Credential): the email domain is the account's
mailbox provider, never "where" a credential was exposed, so the caveat always prints;
the Unknown period is its own bucket; the origin flag is a count of its own.
"""
import re
from collections import Counter

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Table, TableStyle

from .. import components as C
from .. import qa
from .. import theme as T
from .app_d_evidence_registers import (RID, H2T, H3T, assessment_year, const_line, fill, gap, intro, long_list_card,
                                       lookup, pol, register_table, signed)

LIST = 'lists.credential_exposure'
DOMAIN_CLASSES = ('assessed', 'assessed_subdomain', 'other_domain', 'unknown_email')
CROSS_COLS = ('Password category listed', 'No password category', 'Fields not reported')
CLASSES = ('password', 'unclassified', 'sensitive_personal', 'other_identity', 'service_recorded_only',
           'none_provided')
OPTIONAL_CLASSES = ('unclassified', 'service_recorded_only')     # <D.n>.2 rows printed only when non-zero
ORIGIN_CLASS_LABEL = 'Origin flag (counted apart from classes)'
CLASS_LABEL = {'password': 'Password category listed',
               'unclassified': 'Category not in the data class map, no password',
               'sensitive_personal': 'Sensitive personal data, no password',
               'other_identity': 'Other identity fields only', 'service_recorded_only': 'Service/URL recorded only',
               'none_provided': 'Fields not reported by source'}
_MAP = {'password': ['password'], 'sensitive_personal': ['ssn', 'dob', 'address', 'phone', 'ip', 'ip1', 'ip2'],
        'other_identity': ['email', 'username', 'name', 'first_name', 'last_name', 'profile_name', 'gender', 'title',
                           'city', 'country', 'district', 'province', 'state', 'zip'],
        'service_recorded': ['origin']}
UNKNOWN = 'Period “Unknown” in source'
CAVEAT = ("The email domain shows the account's mailbox provider, not the service or subdomain where the "
          'credential was obtained.')
CROSS_WN = 78.0      # the four sibling count columns share one width
ZERO_C = T.STYLES['cell_num'].clone('cred_zero', textColor=T.MUTED)
LEAD_C = T.STYLES['cell_head_num'].clone('cred_lead')


def comp(cid):
    return next((x for x in pol(f'{LIST}.overview_components', []) or [] if x.get('id') == cid), {})


def _map():
    return pol(f'{LIST}.data_class_map') or _MAP


# Breach data-class labels as printed by breach sources ('Passwords', 'Email addresses', 'pass', ...),
# keyed by norm(label). Checked after the policy map. A password category is a password itself
# (hints, PINs, tokens and security answers are secrets, but not passwords: sensitive personal).
LABEL_CLASS = {
    'password': ('passwords', 'pass', 'historical passwords'),
    'sensitive_personal': (
        'account balances', 'balance', 'bank account numbers', 'biometric data', 'credit cards',
        'partial credit card data', 'credit status information', 'cryptocurrency wallet addresses', 'crypto address',
        'dates of birth', 'partial dates of birth', 'places of birth', 'deceased statuses', "driver's licenses",
        'government issued ids', 'passport numbers', 'passport', 'social security numbers', 'physical addresses',
        'address1', 'home address', 'street', 'phone numbers', 'partial phone numbers', 'ip addresses',
        'mac addresses', 'financial transactions', 'payment histories', 'loan information', 'income levels',
        'earnings', 'job job salary', 'living costs', 'home ownership statuses', 'ethnicities', 'ethnic group',
        'religions', 'religion', 'political party', 'sexual orientation', 'sexual fetish', 'eating habits',
        'physical attributes', 'height', 'weight', 'mothers maiden names', 'security questions and answers',
        'auth tokens', 'encrypted keys', 'mnemonic phrases', 'pins', 'password hints', 'hint pass',
        'password strengths', 'private messages', 'chat logs', 'email messages', "family members' names",
        'spouses names', 'family structure', 'kids', 'marital statuses', 'geographic locations', 'licence plates',
        'vehicle details'),
    'other_identity': (
        'email addresses', 'usernames', 'names', 'full name', 'middle name', 'nick', 'genders', 'salutations',
        'job titles', 'employers', 'job job company', 'occupations', 'education levels', 'employment statuses',
        'years of professional experience', 'professional skills', 'job applications', 'spoken languages',
        'nationalities', 'time zones', 'ages', 'age groups', 'avatars', 'profile photos', 'bios',
        'personal descriptions', 'social media profiles', 'instant messenger identities', 'qqmail',
        'homepage urls', 'user website urls', 'website', 'telecommunications carrier', 'phone carrier', 'region',
        'area', 'device information', 'browser user agent details', 'website activity', 'purchases', 'comments',
        'support tickets', 'survey results', 'customer interactions', 'delivery instructions',
        'shipment tracking numbers', 'loyalty program details', 'flights taken', 'appointments'),
}


def norm(cat):
    """'Email addresses' / 'job.job_company' / ' PASS ' -> 'email addresses' / 'job job company' / 'pass'."""
    return re.sub(r'[\s_.]+', ' ', str(cat).strip().lower()).strip()


def field_class(cat):
    """Data class of one field category: the policy map (as printed, then normalised), then the
    breach-label map. A category in neither is 'unclassified' (its own class, never silently sensitive
    personal); derive() warns once per such category."""
    m, n = _map(), norm(cat)
    for cls in ('password', 'sensitive_personal', 'other_identity'):
        if cat in m.get(cls, ()) or n in {norm(x) for x in m.get(cls, ())} or n in LABEL_CLASS[cls]:
            return cls
    if cat in m.get('service_recorded', ()) or n in {norm(x) for x in m.get('service_recorded', ())}:
        return 'service_recorded_only'
    return 'unclassified'


def category_class_label(cat):
    """<D.n>.1 'Data class' cell: the origin category is a flag counted apart, not a class."""
    cls = field_class(cat)
    return ORIGIN_CLASS_LABEL if cls == 'service_recorded_only' else CLASS_LABEL[cls]


def data_class(cats):
    found = {field_class(c) for c in cats}
    return next((c for c in CLASSES if c in found), 'none_provided')


def domain_class(row, assessed):
    """Mailbox-provider class of the account email (no webmail list: open decision 17 closed)."""
    d = str(row.get('email_domain') or '').lower()
    if row.get('email_state') == 'unknown_email' or not d:
        return 'unknown_email'
    if assessed and d == assessed:
        return 'assessed'
    if assessed and d.endswith('.' + assessed):
        return 'assessed_subdomain'
    return 'other_domain'


def derive(data, report, identity):
    """All overview numbers from the register rows. Rows whose domain looks like an
    address ('@' or '*') are withheld, never printed (mask_policy_violation)."""
    reg = lookup(report, data.get('register_ref')) or {}
    rows, counts = reg.get('rows') or [], reg.get('counts') or {}
    A, assessed = assessment_year(report), str(identity.get('domain') or '').lower()
    ok = [r for r in rows if not any(ch in str(r.get('email_domain') or '') for ch in '@*')]
    origin_fields = set(_map().get('service_recorded', ()))
    cross = {k: [0, 0, 0] for k in DOMAIN_CLASSES}
    by_class, by_field, years, enriched, unmapped = Counter(), Counter(), Counter(), [], Counter()
    lead_recent = lead_unknown = origin = year_and_unknown = 0
    lead_older = Counter()       # lead rows by latest year, older than the recent range
    for r in ok:
        dc = domain_class(r, assessed)
        ys = [y for y in r.get('exposure_years') or [] if isinstance(y, int)]
        latest = max(ys) if ys else None
        unknown = bool(r.get('exposure_period_has_unknown'))
        cats = sorted(set(r.get('exposed_field_categories') or []))
        cls = data_class(cats)
        cross[dc][0 if cls == 'password' else 2 if not cats else 1] += 1
        by_class[cls] += 1
        by_field.update(cats)
        unmapped.update(c for c in cats if field_class(c) == 'unclassified')
        origin += bool(origin_fields & set(cats))
        year_and_unknown += latest is not None and unknown
        years[latest if latest is not None else 'unknown' if unknown else None] += 1
        if cls == 'password' and dc in ('assessed', 'assessed_subdomain'):
            recent = latest is not None and A is not None and latest >= A - 1
            lead_recent += recent
            lead_unknown += latest is None and unknown      # period printed only as 'Unknown'
            if latest is not None and not recent:
                lead_older[latest] += 1
        enriched.append({**r, '_class': dc, '_latest': latest, '_cls': cls, '_cats': cats})
    for cat, n in sorted(unmapped.items()):
        qa.add('unmapped_field_category', 'warn', f'credential field category "{cat}" is not in the data class map '
               f'({n} rows); counted as its own class, not as a password', once=True)
    metrics = {m.get('id'): m for m in data.get('metrics') or [] if isinstance(m, dict)}
    headline = (metrics.get('found_headline') or {}).get('value', counts.get('headline_found'))
    total = counts.get('total_rows')
    latest_all = [r['_latest'] for r in enriched if r['_latest'] is not None]
    return {'A': A, 'assessed': assessed, 'received': len(rows), 'suppressed': len(rows) - len(ok),
            'analysed': len(ok), 'rows': enriched, 'cross': cross, 'by_class': by_class, 'by_field': by_field,
            'years': years, 'headline': headline,
            'total': None if C.is_missing(total) else total.get('value') if isinstance(total, dict) else total,
            'lead': cross['assessed'][0] + cross['assessed_subdomain'][0],
            'lead_recent': lead_recent if A is not None else None, 'lead_unknown': lead_unknown,
            'lead_older': lead_older,
            'origin': origin, 'year_and_unknown': year_and_unknown,
            'pw_rows': by_class['password'], 'latest': max(latest_all) if latest_all else None,
            'unknown_any': sum(bool(r.get('exposure_period_has_unknown')) for r in ok), 'metrics': metrics}


def status_line(d):
    """Row status as recorded (column 'Status' in the 2026-10 samples, e.g. 'Open'): counts only."""
    st = Counter(str(r.get('status')).strip().capitalize() for r in d['rows'] if r.get('status'))
    if not st:
        return []
    parts = ', '.join(f'{k} {C.fmt_number(n)}' for k, n in st.most_common())
    missing = d['analysed'] - sum(st.values())
    tail = f'; {C.fmt_number(missing)} rows without a status' if missing else ''
    return [C.note(f'Row status as recorded: {parts}{tail}. Status is the source\'s per-row flag; it is not a '
                   'confirmation that a password was reset.')]


def none_on_assessed(d):
    """Rows were listed but none is on the assessed domain (or its subdomains)."""
    return d['analysed'] > 0 and not (sum(d['cross']['assessed']) + sum(d['cross']['assessed_subdomain']))


def lead_label(d, recency=True):
    """KPI / tile label for the lead count: rows, never accounts; recency as a range."""
    dom = d['assessed'] or 'the assessed domain'
    if none_on_assessed(d):      # a bare 0 would read as good news
        return f'of {C.fmt_number(d["analysed"])} listed rows are on {dom}; all are on other email domains'
    sub = ' or its subdomains' if d['cross']['assessed_subdomain'][0] else ''
    label = fill(comp('kpi_assessed_password').get('label', 'rows on {assessed_domain} listing a password category'),
                 assessed_domain=dom + sub)
    if recency and d['lead_recent'] is not None and d['lead']:
        # buckets by latest year: recent range, older years, period printed only as 'Unknown'
        old = d.get('lead_older') or {}
        parts = [f'{C.fmt_number(d["lead_recent"])} dated {d["A"] - 1}–{d["A"]}']
        if old:
            span = f'{min(old)}–{max(old)}' if min(old) != max(old) else str(min(old))
            parts.append(f'{C.fmt_number(sum(old.values()))} with latest year {span}')
        if d['lead_unknown']:
            parts.append(f'{C.fmt_number(d["lead_unknown"])} with period “Unknown” only')
        label += f' ({"; ".join(parts)})'
    return label


def lead_metric(data, report, identity):
    """Executive-overview tile / priority-action N (unit_rules): rows with a password category on
    the assessed domain. None when there are no register rows."""
    d = derive(data, report, identity)
    if not d['received']:
        return None, d
    return {'value': d['lead'], 'unit': 'rows', 'label': lead_label(d, recency=False), 'state': data.get('state')}, d


# --- overview modules ------------------------------------------------------------
def kpis(d, ctx):
    m = d['metrics']
    ua = m.get('unique_accounts') or {'label': 'Unique accounts', 'value': None,
                                      'reason': comp('kpi_unique_accounts').get('else', 'not confirmed by source')}
    if ua.get('value') is not None and ua.get('grain', ua.get('unique_accounts_grain')) != 'account':
        ua = {**ua, 'value': None, 'reason': 'unique-account count not confirmed by source', 'state': 'unavailable'}
    ua = {**ua, 'label': 'unique accounts', 'state': None}
    head = {'value': d['headline'], 'unit': None,
            'label': f'reported by source (unit not defined by source); {C.fmt_number(d["analysed"])} register rows '
                     'listed', 'reason': 'headline not printed in source'}
    items = [{'label': lead_label(d), 'value': d['lead'], 'unit': 'rows'},
             {'label': comp('kpi_rows_password').get('label', 'rows listing a password category'),
              'value': d['pw_rows'], 'unit': 'rows'},
             {'label': comp('kpi_origin_rows').get('label', 'rows recording a service/URL (origin); value not '
                                                             'provided by source'),
              'value': d['origin'], 'unit': 'rows'},
             head,
             {'label': 'latest exposure year in source', 'value': str(d['latest']) if d['latest'] else None,
              'reason': UNKNOWN},
             ua]
    return C.kpi_strip(items)


def reconciliation(d, ctx):
    lines, unit = [], pol(f'{LIST}.headline_unit', '(unit not defined by the source)')
    if d['headline'] is not None and d['headline'] != d['received']:
        lines.append(fill(pol('reconciliation.source_mismatch', 'Source headline: {headline} {headline_unit}; '
                                                                'listed: {listed} {list_unit}; difference {signed_diff}'
                                                                " — {reason|'not explained by the source data'}."),
                          headline=C.fmt_number(d['headline']), headline_unit=unit, listed=C.fmt_number(d['received']),
                          list_unit=pol(f'{LIST}.list_unit', 'register rows'),
                          signed_diff=signed(d['received'] - d['headline'])))
    if none_on_assessed(d):
        dom = d['assessed'] or 'the assessed domain'
        lines.append(f'None of the {C.fmt_number(d["analysed"])} listed rows is an account on {dom}: they are on '
                     'other mailbox providers or have no email. The 0 on the '
                     'assessed domain describes the listed rows only; it is not a statement that the organisation '
                     'is unaffected.')
    if d['total'] is None:
        if d['received']:
            lines.append(fill(pol('reconciliation.rows_total_unknown', 'Computed over {returned_rows} rows; source total '
                                                                       'not provided — counts are lower bounds.'),
                              returned_rows=C.fmt_number(d['received'])))
    elif d['received'] < d['total']:
        lines.append(fill(pol('reconciliation.rows_received', 'Computed over {returned_rows} of {total_rows} rows; '
                                                              'counts are lower bounds.'),
                          returned_rows=C.fmt_number(d['received']), total_rows=C.fmt_number(d['total'])))
    if d['suppressed']:
        lines.append(fill(pol('reconciliation.suppressed', '{suppressed} rows withheld — {suppression_reason}.'),
                          suppressed=d['suppressed'], suppression_reason='domain text failed the masking check'))
    score = d['metrics'].get('credential_score')
    if score and not C.is_missing(score):
        lines.append(f'Credential score printed by the source: {C.fmt_value(score)}. It is a source value, identical '
                     'across the reports reviewed, and is not used as a result here.')
    split_sub = 'rows_org_subdomain' in d['metrics']     # payload counts subdomains apart
    derived = {'returned_rows': d['received'],
               'rows_org_domain': sum(d['cross']['assessed']) + (0 if split_sub else sum(d['cross']['assessed_subdomain'])),
               'rows_org_subdomain': sum(d['cross']['assessed_subdomain']),
               'rows_external_domain': sum(d['cross']['other_domain']),
               'rows_unknown_email': sum(d['cross']['unknown_email']), 'rows_with_password': d['pw_rows'],
               'rows_period_unknown': d['unknown_any']}
    for mid, v in derived.items():
        m = d['metrics'].get(mid) or {}
        src = m.get('value')
        if src is not None and src != v:
            # only a value the source printed is a 'source metric'; others were prepared with the payload
            kind = ('Source metric' if m.get('source_label') else
                    'Payload count (prepared from the source rows; not printed by the source)')
            why = f' {C.sentence(m["note"])}' if m.get('note') else ''
            lines.append(f'{kind} “{m.get("label", mid)}” is {C.fmt_number(src)}; '
                         f'the register rows give {C.fmt_number(v)} (difference {signed(v - src)}).{why}')
    return [C.note(x) for x in lines]


def crosstab(d):
    """Breakdown (a): email domain of the exposed accounts x password category listed."""
    dom = d['assessed']
    label = {'assessed': f'{dom} (assessed domain)' if dom else 'Assessed domain',
             'assessed_subdomain': f'Subdomains of {dom}' if dom else 'Subdomains of the assessed domain',
             'other_domain': 'Other email domains (counted, not named)',
             'unknown_email': 'Unknown Email (source label)'}
    keys = [k for k in DOMAIN_CLASSES if k != 'assessed_subdomain' or sum(d['cross'][k])]
    cell = lambda n, lead=False: C.P(C.fmt_number(n), LEAD_C if lead and n else ZERO_C if n == 0 else 'cell_num')
    rows = [[label[k], *[cell(n, k == 'assessed' and j == 0) for j, n in enumerate(d['cross'][k])],
             cell(sum(d['cross'][k]))] for k in keys]
    tot = [sum(d['cross'][k][j] for k in DOMAIN_CLASSES) for j in range(3)]
    rows.append([C.P('All listed rows', 'cell_head')] + [C.P(C.fmt_number(n), 'cell_head_num')
                                                         for n in tot + [sum(tot)]])
    listed = (f'Listed rows: {C.fmt_number(d["analysed"])} of {C.fmt_number(d["headline"])} reported. '
              if d['headline'] is not None else f'Listed rows: {C.fmt_number(d["analysed"])}. ')
    return [C.heading('Email domain of exposed accounts', 2, style=H2T),
            intro(listed + 'Each row counts once, by the domain of its email address and by the field categories '
                           'the source lists.'),
            gap(C.compact_table(['Account email domain', *CROSS_COLS, 'Total'], rows, numeric_cols=(1, 2, 3, 4),
                                widths=[T.CW - 4 * CROSS_WN] + [CROSS_WN] * 4), 8),
            C.note(comp('domain_caveat').get('text') or CAVEAT)]


def by_year(d, years_source=None):
    """Breakdown (b): rows by latest exposure year; 'Unknown' is its own bucket."""
    A, n = d['A'], d['analysed']
    # every year printed on its own (the last ten always; older years when they have rows)
    keys = sorted({*(A - k for k in range(10) if A), *(y for y, n in d['years'].items() if isinstance(y, int) and n)},
                  reverse=True)
    yr = [[str(y), d['years'][y]] for y in keys]
    unk = d['years']['unknown']
    yr.append([f'{UNKNOWN} ({round(100 * unk / n) if n else 0}%)', unk])
    if d['years'][None]:
        yr.append(['Period not given by source', d['years'][None]])
    notes = []
    if d['year_and_unknown']:
        n1 = d['year_and_unknown'] == 1
        notes.append(f'{C.fmt_number(d["year_and_unknown"])} {"row lists" if n1 else "rows list"} both a year and '
                     f'“Unknown”; counted under the latest year.')
    left = [C.compact_table(['Latest exposure year', 'Rows'], yr, numeric_cols=(1,), total_width=T.COL2)]
    st = T.STYLES['note_flush']      # the source year list breaks at its hyphens, never inside a year
    right = [C.M(C.breakable(x, T.COL2, st.fontName, st.fontSize), st, spaceAfter=6) for x in
             ['Each row counts once, under the latest year the source gives for it. Rows whose period the '
              f'source prints only as “Unknown” are a separate bucket, not counted as earlier.'] + notes
             + ([f'Exposure years as listed by the source: “{years_source}”.'] if years_source else [])]
    return [C.heading('Rows by latest exposure year', 2, style=H2T),
            intro(f'Exclusive: the buckets sum to the {C.fmt_number(n)} listed rows.'), gap(_two_up(left, right), 8)]


def _two_up(left, right):
    t = Table([[left, '', right]], colWidths=[T.COL2, T.GUTTER, T.COL2], hAlign='LEFT')
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                           ('RIGHTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 0),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    return t


def by_data_class(d):
    """Appendix <D.n>.2: rows by data class (exclusive, precedence order); the origin flag counts apart."""
    keys = [k for k in CLASSES if k not in OPTIONAL_CLASSES or d['by_class'][k]]
    return register_table(['Data class', 'Rows'], [('row', [CLASS_LABEL[k], d['by_class'][k]]) for k in keys],
                          title=f'{RID["s05"]}.2 Rows by data class', sec_id='s05', numeric_cols=(1,), ident='regD42',
                          dense=True, widths=[T.COL2 - 60, 60])


def episodes_text(data):
    src = data.get('breach_source_name')
    reason = C.reason_text(src) if isinstance(src, dict) else 'not provided in the assessment data'
    return fill(pol('states.overview_messages.unavailable', 'Data unavailable: {reason}. This is not a zero result.'),
                reason=f'episode grouping and breach source names are {reason}')


def pointer_text(report, d):
    return fill(comp('pointer').get('text') or 'Row-level detail: Appendix {register_id} lists all {n} register rows '
                '(account as delivered, masked; approximate exposure period; exposed fields).',
                n=C.fmt_number(d['analysed']), register_id=f'{RID["s05"]}.4')


def register_order(rows):
    """Old-report order: newest period first (by the latest year a row lists); rows whose period is only
    'Unknown', then rows without a period, last. Stable: the delivered order breaks ties."""
    return sorted(rows, key=lambda r: (r['_latest'] is None, -(r['_latest'] or 0),
                                       not str(r.get('exposure_period_source') or '').strip()))


REG_COLS = ['#', 'Account (masked, as delivered)', 'Approximate exposure period', 'Exposed fields']


def row_register(d):
    """Appendix <D.n>.4: every analysed register row. The label prints AS RECEIVED (masking is upstream);
    QA flags labels without a mask character. Status column only when a row carries one; one value in
    every row collapses into the caption line. Returns (flowables, rows printed, labels flagged)."""
    rows = register_order(d['rows'])
    flagged = qa.check_account_labels([(r.get('id'), r.get('account_label_masked')) for r in rows])
    statuses = [str(r['status']).strip() for r in rows if str(r.get('status') or '').strip()]
    with_status = bool(statuses)
    dense = T.STYLES['dense']
    sw = lambda t, font=dense.fontName: stringWidth(t, font, dense.fontSize) + 2 * T.CELL_PAD_H + 1
    entries = [('row', [str(i), str(r.get('account_label_masked') or 'Label not delivered'),
                        str(r.get('exposure_period_source') or 'Period not given by source'),
                        ', '.join(r.get('exposed_field_categories') or []) or 'Not provided by source']
                + ([str(r.get('status') or '').strip() or 'Not recorded'] if with_status else []))
               for i, r in enumerate(rows, 1)]
    w0 = max(24, sw(C.fmt_number(len(rows))))
    mono = T.STYLES['dense_tech']        # account labels: JetBrains Mono
    w_acc = min(max([stringWidth(str(r.get('account_label_masked') or ''), mono.fontName, mono.fontSize)
                     + 2 * T.CELL_PAD_H + 1 for r in rows] + [110]), 170)
    w_per = min(max([sw(str(r.get('exposure_period_source') or '')) for r in rows] + [96]), 150)
    w_st = max([sw(x) for x in statuses] + [sw('Status', T.MEDIUM)]) if with_status else 0
    widths = [w0, w_acc, w_per, T.CW - w0 - w_acc - w_per - w_st] + ([w_st] if with_status else [])
    t = register_table(REG_COLS + (['Status'] if with_status else []), entries, title=f'{RID["s05"]}.4 Credential register',
                       sec_id='s05', numeric_cols=(0,), ident='regD44', widths=widths, text_cells=True, tech_cols=(1,))
    lead = intro('One row per register row as delivered by the Cyberrank system. The account label is printed '
                 'exactly as received (masking is applied upstream, not by this report). Sorted by the newest '
                 'period a row lists; rows whose period is only “Unknown” come last. Exposed fields are category '
                 'names only; no password or other value is printed.', 'note_flush')
    return [C.heading(f'{RID["s05"]}.4  Credential register', 3, style=H3T), lead, *const_line(t), t], len(rows), flagged


def mitigations(data, d):
    steps = list(data.get('mitigations_source') or [])
    extra = []
    if d['origin']:
        extra.append(f'{C.fmt_number(d["origin"])} row{"s" if d["origin"] != 1 else ""} record a service/URL (origin) '
                     'with the credential, a pattern typical of infostealer logs: revoke active sessions and tokens '
                     'for the affected accounts and notify the affected users.')
    if sum(d['cross']['other_domain']):
        extra.append('Rows on other email domains are not accounts the organisation manages; tell the affected '
                     'users rather than resetting them centrally.')
    if not (steps or extra):
        return []
    return [C.keep(C.heading('Recommended mitigation measures', 2),
                   *([C.P(data['attention_source'], 'body')] if data.get('attention_source') else []),
                   *C.bullets(steps + extra))]


# --- section contract ------------------------------------------------------------
def card(data, ctx):
    return long_list_card(data, ctx, pol('states.overview_messages.clear_credential_exposure',
                                         'No exposed credentials were identified within the scope and period of '
                                         'this assessment.'))


def build(data, ctx):
    if ctx.state == 'clear':
        return []
    d = derive(data, ctx.report, ctx.identity)
    if not d['received']:
        if d['headline']:      # headline without rows: keep the headline and reconcile, never a silent 0
            qa.add('data_mismatch', 'warn', f's05: headline {d["headline"]} but 0 register rows', once=True)
            head = {'value': d['headline'], 'unit': None, 'label': 'reported by source (unit not defined by source); '
                                                                   '0 register rows listed'}
            return [C.kpi_strip([head]), *reconciliation(d, ctx),
                    C.P('No register rows are listed in the assessment data, so no breakdown by domain, period or '
                        'data class can be shown.', 'body')]
        return [C.P(f'Register rows: {C.missing_text({"reason_code": "not_printed_in_source"})}.', 'body')]
    out = [kpis(d, ctx)] + reconciliation(d, ctx) + crosstab(d)
    out += by_year(d, C.val(data.get('exposure_years_source'))) + status_line(d)
    out += [C.P(pointer_text(ctx.report, d), 'body', spaceBefore=4),
            C.register_pointer(RID['s05'], {'value': d['analysed'], 'unit': 'rows'},
                               title=f'{RID["s05"]} {pol(f"{LIST}.register_title", "Credential exposure — supporting tables")}')]
    return out + mitigations(data, d)
