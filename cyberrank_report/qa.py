"""Layout QA: build-time overflow checks + PyMuPDF post-render checks -> JSON.

Build time:  check_min_width() (never-truncate fields), fixed_box() (KeepInFrame
mode='error'), and LayoutError capture (record_layout_error) by build.py.
Post render: check_pdf() -- words outside the content frame, blank/near-empty
pages (the bottom motif does not count as content), heading left at a page foot,
page ending mid-sentence, header repeated on table continuation pages, folio text.
Render time (ReportDoc): word_split -- a word RL had to break by character.
"""
import json
import re
from pathlib import Path

from reportlab.platypus import KeepInFrame

from . import motif, theme as T

ISSUES = []        # build-time issues for the current process


def add(check, severity, detail, once=False, **where):
    """once: skip when the same check + detail is already recorded (code run on every pass)."""
    if once and any(i['check'] == check and i['detail'] == detail for i in ISSUES):
        return
    ISSUES.append({'check': check, 'severity': severity, 'detail': detail, **where})


def check_min_width(flowable, avail, label):
    """Flag a never-truncate field whose longest unbreakable run exceeds the column."""
    mw = getattr(flowable, 'minWidth', None)
    if mw is None:
        return
    need = mw()
    if need > avail + 0.01:
        text = getattr(flowable, 'text', '')
        add('min_width', 'warn', f'{label}: needs {need:.1f} pt, has {avail:.1f} pt; '
            'the longest word will be split by character', text=str(text)[:120])


MASK_CHARS = '*•'
LITERAL_LABELS = ('Unknown Email',)       # source literal, not an account


def check_account_labels(labels):
    """Credential register safety guard. Masking is done upstream and labels print as received, so
    a label without a mask character is flagged here (never re-masked or dropped by the renderer).
    labels: [(row id, label)]. Returns the number flagged; the warning names row ids only."""
    bad = [rid for rid, lab in labels if isinstance(lab, str) and lab.strip() and lab.strip() not in LITERAL_LABELS
           and not any(ch in lab for ch in MASK_CHARS)]
    if bad:
        ids = ', '.join(map(str, bad[:10])) + (f' (+{len(bad) - 10} more)' if len(bad) > 10 else '')
        add('unmasked_account_label', 'warn', f'{len(bad)} credential account label(s) have no mask character; '
            f'printed as received (masking is upstream): {ids}', once=True, count=len(bad))
    return len(bad)


def fixed_box(flowables, width, height, name):
    """Fixed-size box that raises LayoutError on overflow instead of clipping.
    Standalone use: box.wrapOn(canvas, width, height) then box.drawOn(...)."""
    return KeepInFrame(width, height, flowables, mode='error', name=name)


def record_layout_error(exc, where=''):
    add('layout_error', 'error', f'{where}: {exc}'.strip(': '))


# --- post-render --------------------------------------------------------------
_END = re.compile(r'[.:;!?)\]”"\'%]$')


def _content_words(page):
    """Words between header rule and footer band (header/footer text excluded)."""
    return [w for w in page.get_text('words')
            if w[1] >= T.HEADER_H + 1 and w[3] <= T.FOOTER_Y - 1]


def _content_extent(page):
    """Top/bottom of anything painted in the content band (text, vectors, images).
    Vectors inside the motif form's band are the watermark, not content."""
    # ponytail: band filter, so a content vector wholly inside the band is skipped too;
    # its text still counts. Tag the motif (marked content / OCG) if that ever matters.
    motif_top = T.PAGE_H - motif.form_top()
    ys = [(w[1], w[3]) for w in _content_words(page)]
    for d in page.get_drawings():
        r = d['rect']
        if r.y0 >= motif_top - 0.5:
            continue
        if r.y0 >= T.HEADER_H + 2 and r.y1 <= T.FOOTER_Y - 2 and r.x0 >= T.L - 1:
            ys.append((r.y0, r.y1))
    for img in page.get_image_info():
        y0, y1 = img['bbox'][1], img['bbox'][3]
        if y0 >= T.HEADER_H + 2 and y1 <= T.FOOTER_Y - 2:
            ys.append((y0, y1))
    return (min(a for a, _ in ys), max(b for _, b in ys)) if ys else None


def _lines(words):
    lines = {}
    for w in words:
        lines.setdefault((w[5], w[6]), []).append(w)
    return sorted(lines.values(), key=lambda ws: (round(ws[0][3], 1), ws[0][0]))


def check_pdf(pdf_path, *, skip_pages=(1,), locked_pages=(), table_parts=(), table_heads=None,
              near_empty=0.15):
    """Return a list of issues. Pages are 1-based. skip_pages: cover (and similar)."""
    import pymupdf as fitz
    issues = []
    doc = fitz.open(pdf_path)
    total = len(doc)
    skip = set(skip_pages) | set(locked_pages)

    def issue(check, sev, page, detail):
        issues.append({'check': check, 'severity': sev, 'page': page, 'detail': detail})

    first_lines = {}
    for i, page in enumerate(doc, start=1):
        if i not in locked_pages and (abs(page.rect.width - T.PAGE_W) > 0.1 or abs(page.rect.height - T.PAGE_H) > 0.1):
            issue('page_size', 'error', i, f'{page.rect.width:.1f} x {page.rect.height:.1f} pt')
        if i in skip:
            continue
        text = page.get_text()
        if f'Page {i} of {total}' not in text:
            issue('folio', 'error', i, f"missing 'Page {i} of {total}'")
        words = _content_words(page)
        for w in words:
            if (w[0] < T.L - 0.6 or w[2] > T.R + 0.6 or w[1] < T.FRAME_TOP - 3
                    or w[3] > T.FRAME_BOTTOM + 6):
                issue('outside_frame', 'error', i, f'"{w[4]}" at x {w[0]:.1f}-{w[2]:.1f}, y {w[1]:.1f}-{w[3]:.1f}')
        ext = _content_extent(page)
        if ext is None:
            issue('blank_page', 'error', i, 'no content between header and footer')
            continue
        used = (ext[1] - ext[0]) / T.FRAME_H
        if used < near_empty:
            issue('near_empty_page', 'warn', i, f'content uses {used:.0%} of the frame height')
        spans = [s for b in page.get_text('dict')['blocks'] for ln in b.get('lines', []) for s in ln['spans']
                 if s['text'].strip() and s['bbox'][1] >= T.HEADER_H + 1 and s['bbox'][3] <= T.FOOTER_Y - 1]
        low = max((s['bbox'][3] for s in spans), default=0)
        foot = [s for s in spans if 'Medium' in s['font'] and s['size'] >= 10.4 and s['bbox'][3] >= low - 0.5]
        if foot:
            issue('heading_at_page_foot', 'warn', i, f'"{foot[0]["text"][:60]}" is the last text on the page')
        lines = _lines(words)
        if lines:
            first_lines[i] = ' '.join(w[4] for w in lines[0])
            last = ' '.join(w[4] for w in lines[-1])
            nxt = None
            if i + 1 <= total and i + 1 not in skip:
                nl = _lines(_content_words(doc[i]))
                nxt = ' '.join(w[4] for w in nl[0]) if nl else None
            if nxt and not _END.search(last) and nxt[:1].islower():
                issue('page_ends_mid_sentence', 'info', i, f'...{last[-60:]} | {nxt[:40]}...')

    heads = table_heads or {}
    parts = {}
    for ident, pg in table_parts:
        parts.setdefault(ident, [])
        if pg not in parts[ident]:
            parts[ident].append(pg)
    for ident, pages in parts.items():
        head = heads.get(ident) or []
        for pg in pages[1:]:
            page = doc[pg - 1]
            missing = [h for h in head if h and not page.search_for(h)]
            if missing:
                issue('table_header_not_repeated', 'error', pg, f'{ident}: header {missing} not found')
    doc.close()
    return issues


def write_report(json_path, pdf_path, issues, **extra):
    counts = {s: sum(1 for i in issues if i['severity'] == s) for s in ('error', 'warn', 'info')}
    data = {'pdf': str(pdf_path), 'summary': counts, **extra, 'issues': issues}
    Path(json_path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    return counts
