"""Small canvas charts (owner 2026-10-21, credential exposure timeline): linear from 0, a value on every bar,
Open orange (attention), Resolved blue (owner 2026-10-21); a row without a status counts as Open, as in the tiles.
A non-zero count is at least 1 pt wide/tall so a small bucket never vanishes next to a dominant one."""
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable

from . import theme as T
from .text import fmt_number

OPEN, RESOLVED = T.STATUS['attention'], T.NAVY      # owner 2026-10-21: open orange, resolved blue
FS, FSB = 7.8, 7.0
MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()


def _txt(c, x, y, s, font=T.LIGHT, size=FS, color=T.BODY, align='l'):
    c.setFont(font, size)
    c.setFillColor(color)
    {'l': c.drawString, 'r': c.drawRightString, 'c': c.drawCentredString}[align](x, y, s)


def progress(o, r):
    """Bar label (owner 2026-10-21): 'resolved/total' once anything is resolved, else the total."""
    return f'{fmt_number(r)}/{fmt_number(o + r)}' if r else fmt_number(o + r)


def _legend(c, x, y):
    for lab, col in (('Open', OPEN), ('Resolved', RESOLVED)):
        c.setFillColor(col)
        c.rect(x, y, 6, 6, stroke=0, fill=1)
        _txt(c, x + 9, y, lab)
        x += 9 + stringWidth(lab, T.LIGHT, FS) + 12


class YearBars(Flowable):
    """One horizontal stacked bar per year bucket [(label, open, resolved)]. Full width: exact Open | Resolved |
    Total columns. compact: 'resolved/total' (or the total) at the bar end. The colour legend sits on the header line in both."""
    ROW, BAR, LABEL_W, NUM_W = 13.5, 7.5, 78, 54

    def __init__(self, rows, compact=False):
        super().__init__()
        self.rows, self.compact = rows, compact

    def wrap(self, aw, ah):
        self.width, self.height = aw, self.ROW * (len(self.rows) + 1)
        return self.width, self.height

    def draw(self):
        c, W = self.canv, self.width
        cols = [] if self.compact else ['Open', 'Resolved', 'Total']
        bar_w = W - self.LABEL_W - self.NUM_W * len(cols) - (48 if self.compact else 10)
        top = self.height - self.ROW + 4
        _txt(c, 0, top, 'Latest year', T.MEDIUM, color=T.HEADING)
        for i, h in enumerate(cols):
            _txt(c, W - self.NUM_W * (len(cols) - 1 - i), top, h, T.MEDIUM, color=T.HEADING, align='r')
        _legend(c, self.LABEL_W, top)          # what each bar colour means, in every mode
        c.setStrokeColor(T.RULE)
        c.setLineWidth(T.HAIRLINE)
        c.line(0, self.height - self.ROW - 1, W, self.height - self.ROW - 1)
        mx = max((o + r for _, o, r in self.rows), default=0) or 1
        for i, (label, o, r) in enumerate(self.rows):
            y = self.height - self.ROW * (i + 2)
            base = y + (self.ROW - FS) / 2 + 0.5
            _txt(c, 0, base, label)
            x = self.LABEL_W
            for n, col in ((o, OPEN), (r, RESOLVED)):
                if n:
                    w = max(1.0, bar_w * n / mx)
                    c.setFillColor(col)
                    c.rect(x, y + (self.ROW - self.BAR) / 2, w, self.BAR, stroke=0, fill=1)
                    x += w
            t = o + r
            if self.compact:
                _txt(c, x + 4, base, progress(o, r), T.MEDIUM if t else T.LIGHT, color=T.HEADING if t else T.MUTED)
                continue
            vals = [o, r, t]
            for j, n in enumerate(vals):
                bold = j == len(vals) - 1 and n
                _txt(c, W - self.NUM_W * (len(vals) - 1 - j), base, fmt_number(n), T.MEDIUM if bold else T.LIGHT,
                     color=T.MUTED if not n else T.HEADING if bold else T.BODY, align='r')


class MonthStrip(Flowable):
    """Stacked columns per month [(year, month, open, resolved)], Open at the base; 'resolved/total' (or the
    total) above each column, the month under it and the year under its first month (a tick at the year boundary)."""
    TOP, AX = 12, 22

    def __init__(self, months, height=96):
        super().__init__()
        self.months, self.h = months, height

    def wrap(self, aw, ah):
        self.width, self.height = aw, self.h
        return self.width, self.height

    def draw(self):
        c, W, n = self.canv, self.width, len(self.months)
        plot_h, slot = self.h - self.TOP - self.AX, W / n
        bw = min(22, slot * 0.62)
        mx = max((o + r for *_, o, r in self.months), default=0) or 1
        c.setStrokeColor(T.RULE)
        c.setLineWidth(T.HAIRLINE)
        c.line(0, self.AX, W, self.AX)
        prev = None
        for i, (yr, m, o, r) in enumerate(self.months):
            cx, y = slot * (i + 0.5), self.AX
            for v, col in ((o, OPEN), (r, RESOLVED)):
                if v:
                    h = max(1.0, plot_h * v / mx)
                    c.setFillColor(col)
                    c.rect(cx - bw / 2, y, bw, h, stroke=0, fill=1)
                    y += h
            t = o + r
            lab, size = progress(o, r), FSB
            while size > 5 and stringWidth(lab, T.MEDIUM, size) > slot - 1:     # a wide label never hits its neighbour
                size -= 0.5
            _txt(c, cx, y + 2.5, lab, T.MEDIUM if t else T.LIGHT, size, T.HEADING if t else T.MUTED, 'c')
            _txt(c, cx, self.AX - 9, MONTHS[m - 1], size=FSB, align='c')
            if yr != prev:
                _txt(c, cx - slot / 2 + 2, 1, str(yr), T.MEDIUM, FSB, T.MUTED)
                if prev is not None:
                    c.line(cx - slot / 2, self.AX, cx - slot / 2, 0)
                prev = yr


def last_months(end, n=12):
    """[(year, month)] for the n months up to and including end=(year, month), oldest first."""
    y, m = end
    out = []
    for _ in range(n):
        out.append((y, m))
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    return out[::-1]


if __name__ == '__main__':        # self-check of the month window
    assert last_months((2026, 10))[0] == (2025, 11) and last_months((2026, 10))[-1] == (2026, 10)
    assert last_months((2026, 1), 3) == [(2025, 11), (2025, 12), (2026, 1)]
    assert progress(7, 3) == '3/10' and progress(4, 0) == '4' and progress(0, 0) == '0'
    print('ok')
