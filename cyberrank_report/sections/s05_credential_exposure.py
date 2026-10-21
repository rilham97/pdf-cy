"""05 Credential exposure -- risk overview; supporting tables and the row register live in Appendix D
(register id RID['s05'] from the registry order).

Long-list policy (lists.credential_exposure), option B (user decision 2026-10-15): Section 05 prints
aggregates and points to Appendix <D.n>.5, which lists every register row -- the account label exactly as
delivered by the Cyberrank system (masked upstream; never re-masked here), the approximate exposure
period, the exposed field categories (names only, never values) and the row status when present.
Labels without a mask character print as received and raise QA 'unmasked_account_label'.
Every count is derived from the register rows (analysed = received - suppressed) and
reconciled against the source headline and the payload metrics; differences print.
Grounded redesign (Verdict_Section08_Credential): the email domain is the account's
mailbox provider, never "where" a credential was exposed, so the caveat always prints;
the Unknown period is its own bucket; the origin flag is a count of its own.
Affected domains (owner request 2026-10-19, like the app's credential view): rows carrying
`affected_domain` (the organisation domain/subdomain the leaked entry is linked to) get a domain table
here and are grouped by domain in <D.n>.5; without it neither prints.
"""
import re
from collections import Counter

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Spacer, Table, TableStyle

from .. import charts
from .. import components as C
from .. import qa
from .. import theme as T
from .app_d_evidence_registers import (RID, H2T, H3T, assessment_year, const_line, fill, gap, group_row, intro,
                                       long_list_card, lookup, pol, register_table, signed)
from .s11_quantum_security import mono

LIST = 'lists.credential_exposure'
DOMAIN_CLASSES = ('assessed', 'assessed_subdomain', 'other_domain', 'unknown_email')
CROSS_COLS = ('With password', 'Without password', 'Password unknown')   # unknown: source lists no fields
CLASSES = ('password', 'unclassified', 'sensitive_personal', 'other_identity', 'service_recorded_only',
           'none_provided')
OPTIONAL_CLASSES = ('unclassified', 'service_recorded_only')     # <D.n>.2 rows printed only when non-zero
ORIGIN_CLASS_LABEL = 'Origin flag (counted apart from classes)'
CLASS_LABEL = {'password': 'Password category listed',
               'unclassified': 'Category not in the data class map, no password',
               'sensitive_personal': 'Sensitive personal data, no password',
               'other_identity': 'Other identity fields only', 'service_recorded_only': 'Service/URL recorded only',
               'none_provided': 'Exposed fields not listed (password unknown)'}
CLASS_RANK_TEXT = {'password': 'password', 'unclassified': 'a category not in the data class map',       # <D.n>.2 intro
                   'sensitive_personal': 'sensitive personal data', 'other_identity': 'other identity fields',
                   'service_recorded_only': 'a recorded service or URL only'}
REGISTER_STATES = ('findings', 'partial', 'pending_review')      # <D.n> prints only in these states
_MAP = {'password': ['password'], 'sensitive_personal': ['ssn', 'dob', 'address', 'phone', 'ip', 'ip1', 'ip2'],
        'other_identity': ['email', 'username', 'name', 'first_name', 'last_name', 'profile_name', 'gender', 'title',
                           'city', 'country', 'district', 'province', 'state', 'zip'],
        'service_recorded': ['origin']}
CAVEAT = "The email domain is the account's mailbox provider, not the site where the credential leaked."
HOST = re.compile(r'[a-z0-9-]+(\.[a-z0-9-]+)+')
INLINE_DOMAINS, TOP_DOMAINS = 30, 10      # long-list rule: <=30 inline, else top 10 + the rest in <D.n>.3
RECENT_YEARS = 5     # year buckets: A .. A-4 one by one, then '<A-5> and before'
CROSS_WN = 78.0      # the four sibling count columns share one width
ZERO_C = T.STYLES['cell_num'].clone('cred_zero', textColor=T.MUTED)
LEAD_C = T.STYLES['cell_head_num'].clone('cred_lead')


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


def mailbox(row):
    """The account's mailbox domain as a host name: `email_domain` when it names one, else the part after the
    last '@' of the delivered label (the backend may send only 'other_domain' / 'external'); None otherwise."""
    for v in (row.get('email_domain'), str(row.get('account_label_masked') or '').rpartition('@')[2]):
        v = str(v or '').strip().lower().rstrip('.')
        if HOST.fullmatch(v):
            return v
    return None


def domain_class(row, assessed):
    """Mailbox-provider class of the account email (no webmail list: open decision 17 closed). A mailbox on
    the assessed domain or one of its subdomains (mail.example.com) never counts as another domain, even when
    the backend sent 'other_domain'."""
    if row.get('email_state') == 'unknown_email' or not row.get('email_domain') and mailbox(row) is None:
        return 'unknown_email'
    d = mailbox(row) or ''
    if assessed and d == assessed:
        return 'assessed'
    if assessed and d.endswith('.' + assessed):
        return 'assessed_subdomain'
    return 'other_domain'


MONTH = re.compile(r'\b(\d{4})-(\d{2})(?:-\d{2})?\b')


def latest_month(row):
    """Latest (year, month) the period text gives ('2025-09' or '2026-03-29'); None for years / 'Unknown'."""
    ms = [(int(y), int(m)) for y, m in MONTH.findall(str(row.get('exposure_period_source') or '')) if 1 <= int(m) <= 12]
    return max(ms) if ms else None


def report_month(report):
    raw = (report.get('snapshot') or {}).get('assessed_at') or {}
    raw = raw.get('value') if isinstance(raw, dict) else raw
    m = MONTH.match(str(raw or ''))
    return (int(m.group(1)), int(m.group(2))) if m else None


def row_status(row):
    """'open' / 'resolved' (case-insensitive enum), 'other' for any other text, None when missing. Only
    'resolved' leaves the risk counts; missing and other values count as open (missing is not zero)."""
    v = str(row.get('status') or '').strip().lower()
    return None if not v else v if v in ('open', 'resolved') else 'other'


def affected(row):
    """The row's affected domain as a plain host name, or None (missing, or not a host: never printed)."""
    v = str(row.get('affected_domain') or '').strip().lower().rstrip('.')
    return v if HOST.fullmatch(v) else None


def derive(data, report, identity):
    """All overview numbers from the register rows. Rows whose domain looks like an
    address ('@' or '*') are withheld, never printed (QA mask_policy_violation, counts only)."""
    reg = lookup(report, data.get('register_ref')) or {}
    rows, counts = reg.get('rows') or [], reg.get('counts') or {}
    A, assessed = assessment_year(report), str(identity.get('domain') or '').lower()
    ok = [r for r in rows if not any(ch in str(r.get('email_domain') or '') for ch in '@*')]
    if len(ok) < len(rows):
        qa.add('mask_policy_violation', 'warn', f's05: {len(rows) - len(ok)} credential register rows withheld '
               '(email_domain contains "@" or "*")', once=True)
    bad_dom = sum(1 for r in ok if str(r.get('affected_domain') or '').strip() and affected(r) is None)
    if bad_dom:
        qa.add('invalid_affected_domain', 'warn', f's05: {bad_dom} credential register rows carry an affected_domain '
               'that is not a host name; listed under "Domain not given"', once=True)
    origin_fields = set(_map().get('service_recorded', ()))
    cross = {k: [0, 0, 0] for k in DOMAIN_CLASSES}
    by_class, by_field, years, enriched, unmapped = Counter(), Counter(), Counter(), [], Counter()
    origin = lead = pw_open = 0
    status = Counter()           # row_status -> rows
    years_res, months = Counter(), {}      # resolved rows per year key; (year, month) -> [open, resolved]
    doms = {}                    # affected domain -> {rows, pw, latest, unknown}
    mail = {}                    # (class, mailbox domain or None) -> [with password, without, password unknown]
    for r in ok:
        dc = domain_class(r, assessed)
        st = row_status(r)
        status[st] += 1
        is_open = st != 'resolved'          # resolved rows stay listed and in the totals, out of the risk counts
        ys = [y for y in r.get('exposure_years') or [] if isinstance(y, int)]
        latest = max(ys) if ys else None
        unknown = bool(r.get('exposure_period_has_unknown'))
        cats = sorted(set(r.get('exposed_field_categories') or []))
        cls = data_class(cats)
        cross[dc][0 if cls == 'password' else 2 if not cats else 1] += 1
        if dc != 'unknown_email':
            mail.setdefault((dc, mailbox(r)), [0, 0, 0])[0 if cls == 'password' else 2 if not cats else 1] += 1
        by_class[cls] += 1
        by_field.update(cats)
        unmapped.update(c for c in cats if field_class(c) == 'unclassified')
        origin += bool(origin_fields & set(cats))
        years[latest if latest is not None else 'unknown' if unknown else None] += 1
        years_res[latest if latest is not None else 'unknown' if unknown else None] += not is_open
        ym = latest_month(r)
        if ym:
            months.setdefault(ym, [0, 0])[0 if is_open else 1] += 1
        pw_open += cls == 'password' and is_open
        lead += cls == 'password' and dc in ('assessed', 'assessed_subdomain') and is_open
        g = doms.setdefault(affected(r), {'rows': 0, 'pw': 0, 'res': 0, 'latest': None, 'unknown': False})
        g['rows'] += 1
        g['pw'] += cls == 'password' and is_open
        g['res'] += not is_open
        g['latest'] = max(g['latest'] or 0, latest or 0) or None
        g['unknown'] |= unknown
        enriched.append({**r, '_class': dc, '_latest': latest, '_cls': cls, '_cats': cats, '_dom': affected(r),
                         '_status': st})
    if status['other']:
        qa.add('unknown_row_status', 'warn', f's05: {status["other"]} credential register rows carry a status other '
               'than open / resolved; printed as received and counted as open', once=True)
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
            'lead': lead, 'status': status, 'resolved': status['resolved'], 'years_res': years_res,
            'months': months, 'month_end': report_month(report) or max(months, default=None),
            'open': len(ok) - status['resolved'], 'pw_open': pw_open,
            'origin': origin,
            'pw_rows': by_class['password'], 'latest': max(latest_all) if latest_all else None,
            'unknown_any': sum(bool(r.get('exposure_period_has_unknown')) for r in ok), 'metrics': metrics,
            'domains': doms if any(doms) else {}, 'mail': mail}


def domain_order(d):
    """Assessed domain first, then its subdomains, then other hosts; each by rows (desc); 'not given' last."""
    a = d.get('assessed') or ''
    return sorted(d.get('domains') or {}, key=lambda k: (k is None, k != a, not (a and str(k).endswith('.' + a)),
                                                        -d['domains'][k]['rows'], str(k)))


def pct(n, d):
    return f'{round(100 * n / d)}%' if d else '0%'


def status_line(d):
    """Only what the tiles and the timeline cannot show: rows whose status is missing or not open / resolved
    (values as received), counted as open. Open / resolved counts are in the tiles, so no note for them."""
    by = Counter(row_status(r) for r in d['rows'])
    st = Counter(str(r['status']).strip() for r in d['rows'] if row_status(r) == 'other')     # as received
    if not any(by[k] for k in ('open', 'resolved', 'other')):
        return []
    rows = lambda n: f'{C.fmt_number(n)} row{"s" if n != 1 else ""}'
    parts = [f'{rows(by[None])} without a status'] if by[None] else []
    parts += [f'{rows(n)} with status “{k}”' for k, n in st.most_common()]
    n = by[None] + by['other']
    return [C.note(f'{" and ".join(parts)} count{"" if n != 1 else "s"} as open.')] if parts else []


def none_on_assessed(d):
    """Rows were listed but none is on the assessed domain (or its subdomains)."""
    return d['analysed'] > 0 and not (sum(d['cross']['assessed']) + sum(d['cross']['assessed_subdomain']))


def lead_label(d):
    """KPI / tile label for the lead count: rows, never accounts (their age is in the exposure timeline)."""
    dom = d['assessed'] or 'the assessed domain'
    if none_on_assessed(d):      # a bare 0 would read as good news
        where = ' or '.join(w for k, w in (('other_domain', 'on other email domains'),
                                           ('unknown_email', 'Unknown Email')) if sum(d['cross'][k]))
        return f'of {C.fmt_number(d["analysed"])} listed rows are on {dom}; all are {where}'
    sub = ' or its subdomains' if d['cross']['assessed_subdomain'][0] else ''
    return f'{"open " if d.get("resolved") else ""}rows on {dom}{sub} with a password'


def lead_metric(data, report, identity):
    """Executive-overview tile / priority-action N (unit_rules): rows with a password category on
    the assessed domain. None when there are no register rows."""
    d = derive(data, report, identity)
    if not d['received']:
        return None, d
    return {'value': d['lead'], 'unit': 'rows', 'label': lead_label(d), 'state': data.get('state')}, d


# --- overview modules ------------------------------------------------------------
def kpis(d, ctx):
    """Short tiles only, nothing the tables or the timeline below already show (owner 2026-10-21: no redundant
    info): every listed row, the open share when rows are resolved, the lead count, unique accounts if given."""
    ua = d['metrics'].get('unique_accounts') or {}
    unique = ua.get('value') is not None and ua.get('grain', ua.get('unique_accounts_grain')) == 'account'
    items = [{'label': 'exposed account records', 'value': d['analysed'], 'unit': None}]
    if d['resolved']:        # open rows only in the risk tiles; the total above stays every listed row
        items.append({'label': f'open · {pct(d["resolved"], d["analysed"])} resolved', 'value': d['open'], 'unit': None})
    items.append({'label': lead_label(d), 'value': d['lead'], 'unit': None})
    if unique:      # printed only when the source confirms an account grain
        items.append({**ua, 'label': 'unique accounts', 'unit': None, 'state': None})
    return C.kpi_strip(items, per_row=len(items) if len(items) <= 4 else 3)


def register_printed(state, d):
    """<D.n> is printed (and Section 05 points to it) only for these states with analysed rows."""
    return state in REGISTER_STATES and d['analysed'] > 0


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


def domains_block(d):
    """Affected domains (the app's grouping): rows, rows with a password, latest year per domain.
    Long lists (> INLINE_DOMAINS) show the top TOP_DOMAINS plus one 'other domains' row; all in <D.n>.3."""
    if not d['domains']:
        return []
    keys = domain_order(d)
    named = [k for k in keys if k]
    cut = named[:TOP_DOMAINS] if len(named) > INLINE_DOMAINS else named
    rest = [k for k in named if k not in cut]
    res = bool(d['resolved'])
    rows = [domain_row(k, d['domains'][k], res=res) for k in cut]
    if rest:
        gs = [d['domains'][k] for k in rest]
        g = {'rows': sum(x['rows'] for x in gs), 'pw': sum(x['pw'] for x in gs), 'res': sum(x['res'] for x in gs),
             'latest': max((x['latest'] or 0) for x in gs) or None, 'unknown': any(x['unknown'] for x in gs)}
        rows.append(domain_row(f'{C.fmt_number(len(rest))} other domains', g, plain=True, res=res))
    if None in d['domains']:
        rows.append(domain_row('Domain not given', d['domains'][None], plain=True, res=res))
    cols = domain_cols(res)
    out = [C.heading('Affected domains', 2, style=H2T),
           gap(C.compact_table(cols, rows, numeric_cols=tuple(range(1, len(cols))),
                               widths=[T.CW - (len(cols) - 1) * CROSS_WN] + [CROSS_WN] * (len(cols) - 1)), 6)]
    if rest:
        out.append(C.note(f'All {C.fmt_number(len(named))} domains: Appendix {RID["s05"]}.3.'))
    return out


def domain_cols(res):
    """Affected-domain columns; with resolved rows: open / resolved (share) / password rows still open."""
    return (['Domain', 'Open', 'Resolved', 'With password (open)', 'Latest year'] if res else
            ['Domain', 'Rows', 'With password', 'Latest year'])


def domain_row(name, g, plain=False, dense=False, res=False):
    num = lambda n, txt=None: C.P(txt or C.fmt_number(n), ZERO_C if n == 0 else 'dense_num' if dense else 'cell_num')
    base = 'dense' if dense else 'cell'
    latest = str(g['latest']) if g['latest'] else 'Unknown' if g['unknown'] else 'Not given'
    counts = ([num(g['rows'] - g['res']), num(g['res'], f'{C.fmt_number(g["res"])} ({pct(g["res"], g["rows"])})'
                                               if g['res'] else None)] if res else [num(g['rows'])])
    return [C.P(C.esc(name), base + '_muted') if plain else C.M(mono(name, dense), base),
            *counts, num(g['pw']), C.P(latest, base + '_num')]


def other_mailboxes(d):
    """Named mailbox domains outside the assessed domain, most rows first: [(domain, [pw, no pw, not reported])]."""
    named = [(n, c) for (k, n), c in d['mail'].items() if k == 'other_domain' and n]
    return sorted(named, key=lambda nc: (-sum(nc[1]), nc[0]))


def crosstab(d):
    """Email domain of the exposed accounts (mailbox provider) x password category listed. Other email domains
    are named, most rows first (owner 2026-10-21); more than INLINE_DOMAINS: the top TOP_DOMAINS plus one
    '{n} other email domains' row, every domain in <D.n>.4."""
    dom = d['assessed']
    cell = lambda n, lead=False: C.P(C.fmt_number(n), LEAD_C if lead and n else ZERO_C if n == 0 else 'cell_num')
    line = lambda name, c, lead=False, tech=False: [C.M(mono(name), 'cell') if tech else name,
                                                    *[cell(n, lead and j == 0) for j, n in enumerate(c)], cell(sum(c))]
    rows = [line(dom or 'Assessed domain', d['cross']['assessed'], lead=True, tech=bool(dom))]
    if sum(d['cross']['assessed_subdomain']):
        rows.append(line(f'Subdomains of {dom}' if dom else 'Subdomains of the assessed domain',
                         d['cross']['assessed_subdomain']))
    others = other_mailboxes(d)
    cut = others[:TOP_DOMAINS] if len(others) > INLINE_DOMAINS else others
    rows += [line(n, c, tech=True) for n, c in cut]
    rest = others[len(cut):]
    if rest:
        rows.append(line(f'{C.fmt_number(len(rest))} other email domains', [sum(c[j] for _, c in rest) for j in range(3)]))
    unnamed = d['mail'].get(('other_domain', None))
    if unnamed:
        rows.append(line('Other email domains, name not given', unnamed))
    if sum(d['cross']['unknown_email']):
        rows.append(line('Unknown Email', d['cross']['unknown_email']))
    tot = [sum(d['cross'][k][j] for k in DOMAIN_CLASSES) for j in range(3)]
    rows.append([C.P('All listed rows', 'cell_head')] + [C.P(C.fmt_number(n), 'cell_head_num')
                                                         for n in tot + [sum(tot)]])
    out = [C.heading('Email domain of exposed accounts', 2, style=H2T),
           gap(C.compact_table(['Account email domain', *CROSS_COLS, 'Total'], rows, numeric_cols=(1, 2, 3, 4),
                               widths=[T.CW - 4 * CROSS_WN] + [CROSS_WN] * 4), 6)]
    if rest:
        out.append(C.note(f'All {C.fmt_number(len(others))} other email domains: Appendix {RID["s05"]}.4.'))
    return out + [C.note(CAVEAT)]


def year_buckets(d, src='years'):
    """Fixed buckets (owner rule 2026-10-19): the assessment year and the RECENT_YEARS - 1 years before it one by
    one, then '<A - RECENT_YEARS> and before', then 'Unknown' (and 'Not given' when any). A year after the
    assessment year (never seen) gets its own column. Returns [(label, rows)]; the rows sum to the listed rows."""
    years = {y: n for y, n in d[src].items() if isinstance(y, int)}
    A = d['A'] or max((y for y in d['years'] if isinstance(y, int)), default=None)
    if A is None:
        out = []
    else:
        first = A - RECENT_YEARS + 1
        out = [(str(y), n) for y, n in sorted(years.items(), reverse=True) if y > A]
        out += [(str(y), years.get(y, 0)) for y in range(A, first - 1, -1)]
        out.append((f'{first - 1} and before', sum(n for y, n in years.items() if y < first)))
    out.append(('Unknown', d[src]['unknown']))
    if d['years'][None]:
        out.append(('Not given', d[src][None]))
    return out


def by_year(d):
    """Exposure timeline (owner 2026-10-21, concept 3): rows by latest exposure year in the fixed buckets as
    stacked Open / Resolved bars, beside the last 12 months up to the assessment month when any row gives a
    month. No month data: the year bars alone, full width, with exact Open | Resolved | Total columns. No
    status in the payload: one muted tone, never drawn as Open. No caption under the chart (owner)."""
    known = any(d['status'][k] for k in ('open', 'resolved', 'other'))
    res = dict(year_buckets(d, 'years_res'))
    rows = [(label, n - res.get(label, 0), res.get(label, 0)) for label, n in year_buckets(d)]
    head = C.heading('Exposure timeline', 2, style=H2T)
    if not d['months'] or not d['month_end']:
        return [C.keep(head, gap(charts.YearBars(rows, known), 4), Spacer(1, 6))]
    months = [(y, m, *d['months'].get((y, m), [0, 0])) for y, m in charts.last_months(d['month_end'])]
    left_w = T.COL2 - 6
    t = Table([[[charts.YearBars(rows, known, compact=True)], '',
                [C.P('Last 12 months', 'dense_head'), charts.MonthStrip(months, known)]]],
              colWidths=[left_w, T.GUTTER + 12, T.CW - left_w - T.GUTTER - 12], hAlign='LEFT')
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')] +
                          [(k, (0, 0), (-1, -1), 0) for k in ('LEFTPADDING', 'RIGHTPADDING', 'TOPPADDING', 'BOTTOMPADDING')]))
    return [C.keep(head, gap(t, 4), Spacer(1, 6))]


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


def register_order(rows):
    """Old-report order: newest period first (by the latest year a row lists); rows whose period is only
    'Unknown', then rows without a period, last. Stable: the delivered order breaks ties."""
    return sorted(rows, key=lambda r: (r['_latest'] is None, -(r['_latest'] or 0),
                                       not str(r.get('exposure_period_source') or '').strip()))


REG_COLS = ['#', 'Account (masked, as delivered)', 'Approximate exposure period', 'Exposed fields']


def status_cell(r):
    """D.2.5 Status: 'Resolved' with its icon (green, as in 06); other values as received; 'Not recorded'."""
    if row_status(r) == 'resolved':
        from .. import icons as I
        return I.status_label('clear', 'Resolved', 'resolved', dense=True)
    return str(r.get('status') or '').strip() or 'Not recorded'


def row_register(d):
    """Appendix <D.n>.5: every analysed register row. The label prints AS RECEIVED (masking is upstream);
    QA flags labels without a mask character. Status column only when a row carries one; one value in
    every row collapses into the caption line. With affected domains the rows are grouped by domain
    (domain_order), newest period first inside each group. Returns (flowables, rows printed, labels flagged)."""
    rows = register_order(d['rows'])
    doms = d.get('domains') or {}
    if doms:
        rank = {k: i for i, k in enumerate(domain_order(d))}
        rows = sorted(rows, key=lambda r: rank[r.get('_dom')])      # stable: period order kept inside a group
    flagged = qa.check_account_labels([(r.get('id'), r.get('account_label_masked')) for r in rows])
    statuses = [str(r['status']).strip() for r in rows if str(r.get('status') or '').strip()]
    with_status = bool(statuses)
    dense = T.STYLES['dense']
    sw = lambda t, font=dense.fontName: stringWidth(t, font, dense.fontSize) + 2 * T.CELL_PAD_H + 1
    entries, current = [], object()
    for i, r in enumerate(rows, 1):
        if doms and r.get('_dom') != current:
            current = r.get('_dom')
            g = doms[current]
            name = mono(current, True) if current else 'Domain not given'
            entries.append(('group', group_row(C.M(name, 'dense_head'),
                                               C.P(f'{C.fmt_number(g["rows"])} rows', 'note_flush', alignment=2),
                                               T.CW - 2 * T.CELL_PAD_H), current or 'Domain not given'))
        entries.append(('row', [str(i), str(r.get('account_label_masked') or 'Label not delivered'),
                                str(r.get('exposure_period_source') or 'Period not given by source'),
                                ', '.join(r.get('exposed_field_categories') or []) or 'Not provided by source']
                        + ([status_cell(r)] if with_status else [])))
    w0 = max(24, sw(C.fmt_number(len(rows))))
    mono_st = T.STYLES['dense_tech']        # account labels: JetBrains Mono
    w_acc = min(max([stringWidth(str(r.get('account_label_masked') or ''), mono_st.fontName, mono_st.fontSize)
                     + 2 * T.CELL_PAD_H + 1 for r in rows] + [110]), 170)
    w_per = min(max([sw(str(r.get('exposure_period_source') or '')) for r in rows] + [96]), 150)
    w_st = max([sw(x) for x in statuses] + [sw('Status', T.MEDIUM)] + ([sw('Resolved') + 12] if d.get('resolved') else [])) if with_status else 0
    widths = [w0, w_acc, w_per, T.CW - w0 - w_acc - w_per - w_st] + ([w_st] if with_status else [])
    t = register_table(REG_COLS + (['Status'] if with_status else []), entries, title=f'{RID["s05"]}.5 Credential register',
                       sec_id='s05', numeric_cols=(0,), ident='regD44', widths=widths, text_cells=True, tech_cols=(1,))
    order = ('Grouped by affected domain; inside a group, newest period first' if doms else
             'Sorted by the newest period a row lists')
    lead = intro('One row per register row as delivered by the Cyberrank system. The account label is printed '
                 f'exactly as received (masking is applied upstream, not by this report). {order}; rows whose '
                 'period is only “Unknown” come last. Exposed fields are category names only; no password or '
                 'other value is printed.', 'note_flush')
    return [C.heading(f'{RID["s05"]}.5  Credential register', 3, style=H3T), lead, *const_line(t), t], len(rows), flagged


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
    attention = [C.P(data['attention_source'], 'body')] if data.get('attention_source') else []
    if not (steps or extra):
        return attention      # the source's attention line still prints, without an empty heading
    return [C.keep(C.heading('Recommended mitigation measures', 2), *attention, *C.bullets(steps + extra))]


# --- section contract ------------------------------------------------------------
def card(data, ctx):
    empty = (data.get('empty_state_source') or {}).get('text')      # clear: the source's text wins, as default_card
    return long_list_card(data, ctx, empty or pol('states.overview_messages.clear_credential_exposure',
                                                  'No exposed credentials were identified within the scope and '
                                                  'period of this assessment.'))


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
    out = [kpis(d, ctx)] + reconciliation(d, ctx) + domains_block(d) + crosstab(d)
    out += by_year(d) + status_line(d)
    if register_printed(ctx.state, d):      # same rule as d4_credentials: never a pointer without a target
        out += [C.register_pointer(RID['s05'], {'value': d['analysed'], 'unit': 'rows'},
                                   title=f'{RID["s05"]} {pol(f"{LIST}.register_title", "Credential exposure — supporting tables")}')]
    return out + mitigations(data, d)
