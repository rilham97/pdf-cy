"""Parse the sanitized credential register (p36-364) and quantum scope table (p368-370) from the
Instagram PDF (adapted from ../parse_tables.py). Emits JSON to stdout.
Email labels are emitted only masked (prep_mask): as printed when masked, else masked here.

usage: python3 -I parse_tables.py <instagram.pdf> > tables.json
"""
import sys, json
sys.path.insert(0, '/private/tmp/claude-501/-Users-rama-Downloads-Cyberrank-Reference-Pack-2026-10-04/c1a77ec7-4bf4-490d-a6c0-a7596acd8d20/scratchpad/understand/design-template/pylib')
import pymupdf

pdf = pymupdf.open(sys.argv[1])
ORG_DOMAIN = "instagram.com"
CRED_PAGES = range(36, 365)          # 1-based, inclusive



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


def classify(cell):
    """Email cell text -> (email_domain, email_state). Local part and foreign domains are dropped here."""
    if cell.strip().lower() == "unknown email":
        return None, "unknown_email"
    if cell.count("@") != 1:
        raise SystemExit("unexpected email cell shape")
    local, dom = cell.split("@")
    dom = dom.lower().strip()
    if dom == ORG_DOMAIN or dom.endswith("." + ORG_DOMAIN):
        email_domain = dom
    else:
        email_domain = "other_domain"
    return email_domain, ("masked_present" if "*" in local else "unmasked_present")


def words_in(page, ymin, ymax):
    out = []
    for w in page.get_text("words"):
        x0, y0, x1, y1, t = w[:5]
        if ymin < (y0 + y1) / 2 < ymax:
            out.append(((y0 + y1) / 2, 0 if x0 < 237 else 1 if x0 < 350 else 2, x0, t))
    return out


cred_rows = []
for pno in CRED_PAGES:
    page = pdf[pno - 1]
    words = page.get_text("words")
    ymin, ymax = 40, 800
    if pno == CRED_PAGES[0]:
        ymin = [w for w in words if w[4] == "Fields" and w[0] > 350][0][3] + 2
    if pno == CRED_PAGES[-1]:
        ymax = [w for w in words if w[4] == "Recommended"][0][1] - 2
    seps = sorted({round(d["rect"].y0) for d in page.get_drawings()
                   if d["rect"].height < 2 and 30 < d["rect"].x0 < 45 and 150 < d["rect"].width < 250
                   and ymin < d["rect"].y0 < ymax + 20})
    bounds = [ymin] + seps + [ymax]
    frags = words_in(page, ymin, ymax)
    for a, b in zip(bounds, bounds[1:]):
        cell = [f for f in frags if a < f[0] < b]
        if not cell:
            continue
        cols = {}
        for y, ci, x, t in sorted(cell):
            cols.setdefault(ci, []).append(t)
        c0 = " ".join(cols.get(0, []))
        period = [p.strip() for p in " ".join(cols.get(1, [])).split(",") if p.strip()]
        fields = [p.strip() for p in " ".join(cols.get(2, [])).split(",") if p.strip()]
        if not c0:      # row split over a page break: continuation of the previous row
            prev = cred_rows[-1]
            prev["period"] += period
            prev["fields"] += fields
            prev["continued_on_page"] = pno
            continue
        if "@" in c0:
            c0 = "".join(cols[0])          # wrapped address: rejoin without spaces
        email_domain, email_state = classify(c0)
        label, masked_here = prep_mask(c0.strip())
        cred_rows.append({"page": pno, "email_domain": email_domain, "email_state": email_state,
                          "label": label, "masked_here": masked_here,
                          "period": period, "fields": fields})

# ---------- quantum scope: pages 368-370 (a row can break over a page: carried to the next page)
COLS = [130, 225, 340, 400, 445, 478, 525]   # subdomain|category|pre|source|post|high|moderate|low
HALF = 18                                   # row text spans +-13pt around the Pre-QC anchor


def lines_by_col(page, ymin, ymax):
    out = []
    for w in page.get_text("words"):
        x0, y0, x1, y1, t = w[:5]
        if ymin < y0 < ymax:
            out.append(((y0 + y1) / 2, sum(1 for c in COLS if x0 >= c), x0, t))
    return out


q_rows, cur_sub, carry = [], None, []
for pno in (368, 369, 370):
    page = pdf[pno - 1]
    words = page.get_text("words")
    ymin = 40
    if pno == 368:
        ymin = [w for w in words if w[4] == "Subdomain"][0][3] + 4
    stop = [w for w in words if w[4] == "Quantum" and w[0] < 100 and w[1] > ymin]
    ymax = min([w[1] for w in stop] + [800])
    frags = lines_by_col(page, ymin, ymax)
    anchors = sorted({f[0] for f in frags if f[1] == 2})
    used = set()
    for i, a in enumerate(anchors):
        cell = [f for f in frags if a - HALF < f[0] <= a + HALF]
        used.update(cell)
        if i == 0:
            cell = carry + cell
        cols = {}
        for y, ci, x, t in cell if i == 0 and carry else sorted(cell, key=lambda f: (f[0], f[2])):
            cols.setdefault(ci, []).append(t)
        if cols.get(0):
            cur_sub = "".join(cols[0])
        q_rows.append({"page": pno, "subdomain": cur_sub, "category": " ".join(cols.get(1, [])),
                       "pre_qc": " ".join(cols.get(2, [])), "source": " ".join(cols.get(3, [])),
                       "post_qc": "".join(cols.get(4, [])),
                       "high": int(cols[5][0]), "moderate": int(cols[6][0]), "low": int(cols[7][0])})
    carry = sorted((f for f in frags if f not in used and f[0] > anchors[-1]), key=lambda f: (f[0], f[2]))

json.dump({"credentials": cred_rows, "quantum_scope": q_rows}, sys.stdout, ensure_ascii=False)
