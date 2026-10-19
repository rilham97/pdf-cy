"""Parse the Gmail credential register (pages 38-391) into sanitised rows.

Adapted from tools/extract/parse_tables.py. Rows are bounded by the table's horizontal rules; columns by x.
A row cut by a page break is joined with its continuation. Only the email *domain* is read and classified
(assessed domain, its subdomain, or 'other_domain'); the label is emitted only masked (prep_mask).

A list item that wraps continues on the next line without a comma ("Geographic" / "locations", "job." /
"job_company"); a line ending without a comma is therefore joined with the next one.
usage: python -I parse_tables.py <gmail.pdf>  -> JSON on stdout
"""
import json
import re
import sys

import pymupdf

ORG_DOMAIN = 'gmail.com'
FIRST, LAST = 38, 391                      # 1-based credential pages
COLX = [350, 425, 525]                     # email | period | fields | status



def prep_mask(label):
    """Account label as the system would deliver it. A label the source printed without a mask
    character is masked here (fixture preparation): first and last character of the local part
    kept, the rest replaced with '*', domain kept. Returns (label, masked_here)."""
    if '@' not in label:
        return label, False                  # 'Unknown Email' as printed
    local, dom = label.split('@', 1)
    if '*' in local:
        return label, False
    keep = local[0] + '*' * (len(local) - 2) + local[-1] if len(local) > 2 else local[:1] + '*'
    return keep + '@' + dom, True


def domain_class(dom):
    if dom == ORG_DOMAIN or dom.endswith('.' + ORG_DOMAIN):
        return dom                         # assessed domain or its subdomain, kept as is
    return 'other_domain'


def cells(pdf):
    """[(page, {col: [line, ...]})] per register row. A row cut by a page break is joined: the part without a
    status waits for the next cell; a status-less, email-less tail at a page top extends the previous row."""
    out, pending = [], {}                           # cell cut by a page break (no status yet)
    for pno in range(FIRST, LAST + 1):
        page = pdf[pno - 1]
        words = page.get_text('words')
        ymin = 60
        if pno == FIRST:
            ymin = max(w[3] for w in words if w[4] in ('Status', 'Period')) + 2
        stop = [w[1] for w in words if w[4] == 'Recommended' and w[0] < 100]
        ymax = min(stop + [790])
        frags = [(round(w[1]), sum(w[0] >= c for c in COLX), w[0], w[4]) for w in words if ymin < w[1] < ymax
                 and not re.fullmatch(r'\d\.', w[4])]
        seps = sorted({round(d['rect'].y0) for d in page.get_drawings()
                       if d['rect'].height < 2 and d['rect'].width > 100 and ymin < d['rect'].y0 < ymax})
        bounds = [ymin] + seps + [ymax]
        for k, (a, b) in enumerate(zip(bounds, bounds[1:])):
            cell = sorted(f for f in frags if a < f[0] < b)
            if not cell:
                continue
            tail = k == 0 and not pending and out and not any(f[1] in (0, 3) for f in cell)
            cols, pending = (out[-1][1] if tail else pending), {}
            lines = {}
            for y, ci, x, t in cell:
                lines.setdefault((ci, y), []).append(t)
            for (ci, y), toks in sorted(lines.items(), key=lambda kv: kv[0][1]):
                cols.setdefault(ci, []).append(' '.join(toks))
            if tail:
                continue
            if not cols.get(3):            # row continues on the next page
                pending = cols
                continue
            out.append((pno, cols))
    assert not pending, 'dangling row fragment at end of register'
    return out


def items(lines):
    text = ''
    for ln in lines:
        text = (text + ('' if text.endswith('.') else ' ') + ln.strip()).strip()
    return [p.strip() for p in text.split(',') if p.strip()]


def parse(pdf):
    raw = cells(pdf)
    rows = []
    for pno, cols in raw:
        c0 = ''.join(cols.get(0, [])).replace(' ', '')
        if '@' in c0:
            local, dom = c0.split('@', 1)
            email_domain = domain_class(dom.lower())
            email_state = 'masked_label_present' if '*' in local else 'unmasked_label_dropped'
        elif ' '.join(cols.get(0, [])).lower() == 'unknown email':
            email_domain, email_state = None, 'unknown_email'
        else:
            raise SystemExit(f'unexpected email cell on page {pno}')
        period = [t for ln in cols.get(1, []) for t in ln.replace(',', ' ').split()]
        label, masked_here = prep_mask(c0 if '@' in c0 else ' '.join(cols.get(0, [])))
        rows.append({'page': pno, 'email_domain': email_domain, 'email_state': email_state,
                     'label': label, 'masked_here': masked_here,
                     'period': period, 'fields': items(cols.get(2, [])),
                     'status': ' '.join(cols[3])})
    return rows


if __name__ == '__main__':
    out = parse(pymupdf.open(sys.argv[1]))
    raw = json.dumps([{k: v for k, v in r.items() if k != 'label'} for r in out])
    assert '@' not in raw and '*' not in raw
    assert all(r['label'] == 'Unknown Email' or '*' in r['label'].split('@')[0] for r in out)
    print(json.dumps(out, ensure_ascii=False))
