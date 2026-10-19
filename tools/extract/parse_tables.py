"""Parse credential register (sanitized) and quantum scope table from the Claude PDF.
Emits JSON to stdout. Email labels are emitted only as masked labels (prep_mask)."""
import sys, json, re
sys.path.insert(0, '/private/tmp/claude-501/-Users-rama-Downloads-Cyberrank-Reference-Pack-2026-10-04/c1a77ec7-4bf4-490d-a6c0-a7596acd8d20/scratchpad/understand/design-template/pylib')
import pymupdf

pdf = pymupdf.open(sys.argv[1])
ORG_DOMAIN = "claude.com"

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


def lines_by_col(page, cols, ymin, ymax):
    """Return list of (y, colidx, text) line fragments."""
    out = []
    for w in page.get_text("words"):
        x0, y0, x1, y1, t = w[:5]
        if not (ymin < y0 < ymax):
            continue
        ci = sum(1 for c in cols if x0 >= c)
        out.append((round((y0 + y1) / 2, 1), ci, x0, t))
    return out

# ---------- credentials: pages 20-21 (idx 19,20)
cred_rows = []
for pi in (19, 20):
    page = pdf[pi]
    ymin = 356 if pi == 19 else 60
    frags = lines_by_col(page, [170, 300], ymin, 790)
    # horizontal separators from drawings
    seps = sorted({round(r.y0) for d in page.get_drawings() for r in [d["rect"]]
                   if r.height < 2 and r.x0 < 40 and r.width > 100 and ymin < r.y0 < 790})
    # merge close seps
    m = []
    for s in seps:
        if not m or s - m[-1] > 4:
            m.append(s)
    bounds = [ymin] + m + [790]
    for a, b in zip(bounds, bounds[1:]):
        cell = [f for f in frags if a < f[0] < b]
        if not cell:
            continue
        cols = {}
        for y, ci, x, t in sorted(cell):
            cols.setdefault(ci, []).append(t)
        c1 = "".join(cols.get(0, [])) if "@" in " ".join(cols.get(0, [])) else " ".join(cols.get(0, []))
        if "@" in c1:
            dom = c1.split("@", 1)[1].lower()
            email_domain = dom if dom == ORG_DOMAIN else "external"
            email_state = "masked_present" if "*" in c1.split("@", 1)[0] else "unmasked_present"
        elif c1.strip().lower() == "unknown email":
            email_domain, email_state = None, "unknown_email"
        else:
            raise SystemExit(f"unexpected col1 on page {pi+1}")
        period = [p.strip() for p in " ".join(cols.get(1, [])).split(",") if p.strip()]
        fields = [p.strip() for p in " ".join(cols.get(2, [])).split(",") if p.strip()]
        label, masked_here = prep_mask(c1.strip())
        cred_rows.append({"page": pi + 1, "email_domain": email_domain, "email_state": email_state,
                          "period": period, "fields": fields, "label": label, "masked_here": masked_here})

# ---------- quantum scope: pages 26-40 (idx 25..39)
COLS = [150, 240, 350, 405, 445, 480, 520]
q_rows = []
cur_sub = None
for pi in range(25, 40):
    page = pdf[pi]
    words = page.get_text("words")
    ymin = 60
    if pi == 25:
        hdr = [w for w in words if w[4] == "Subdomain"]
        ymin = hdr[0][3] + 4
    stop = [w for w in words if w[4] == "Quantum" and w[0] < 100 and w[1] > ymin]
    ymax = min([w[1] for w in stop] + [790])
    frags = lines_by_col(page, COLS, ymin, ymax)
    anchors = sorted({f[0] for f in frags if f[1] == 2})
    # row band = midpoint between anchors
    mids = [ymin] + [(a + b) / 2 for a, b in zip(anchors, anchors[1:])] + [ymax]
    for i, a in enumerate(anchors):
        lo, hi = mids[i], mids[i + 1]
        cell = [f for f in frags if lo < f[0] <= hi]
        cols = {}
        for y, ci, x, t in sorted(cell, key=lambda f: (f[0], f[2])):
            cols.setdefault(ci, []).append(t)
        if cols.get(0):
            cur_sub = "".join(cols[0])
        q_rows.append({
            "page": pi + 1, "subdomain": cur_sub,
            "category": " ".join(cols.get(1, [])),
            "pre_qc": " ".join(cols.get(2, [])),
            "source": " ".join(cols.get(3, [])),
            "post_qc": "".join(cols.get(4, [])),
            "high": int(cols[5][0]), "moderate": int(cols[6][0]), "low": int(cols[7][0]),
        })
# subdomain wrapped across row boundary? (first word of name in row band, continuation below) -> merged by "".join above
json.dump({"credentials": cred_rows, "quantum_scope": q_rows}, sys.stdout, ensure_ascii=False)
