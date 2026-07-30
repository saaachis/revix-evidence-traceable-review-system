"""Render the Revix verdict-card illustration to PNG and JPG."""
from PIL import Image, ImageDraw, ImageFont

S = 3                      # supersample factor
W = 1180                   # logical width
PAD = 44

BG          = (255, 255, 255)
BORDER      = (222, 226, 230)
HEADER      = (15, 110, 99)
INK         = (20, 24, 27)
MUTED       = (110, 119, 129)
FAINT       = (150, 158, 166)
TRACK       = (233, 236, 239)
BAND        = (150, 208, 199)
TEAL        = (15, 110, 99)
TEAL_SOFT   = (232, 244, 242)
AMBER       = (180, 83, 9)
AMBER_SOFT  = (254, 243, 199)
GREEN       = (21, 128, 61)
GREEN_SOFT  = (222, 242, 229)
RED         = (185, 28, 28)
PILL_BG     = (243, 244, 246)
RULE        = (235, 238, 241)

FONTS = {
    "r":  r"C:\Windows\Fonts\segoeui.ttf",
    "b":  r"C:\Windows\Fonts\segoeuib.ttf",
    "sb": r"C:\Windows\Fonts\seguisb.ttf",
    "i":  r"C:\Windows\Fonts\segoeuii.ttf",
}
_cache = {}


def f(style, size):
    key = (style, size)
    if key not in _cache:
        try:
            _cache[key] = ImageFont.truetype(FONTS[style], size * S)
        except OSError:
            _cache[key] = ImageFont.truetype(FONTS["r"], size * S)
    return _cache[key]


img = Image.new("RGB", (W * S, 1500 * S), BG)
d = ImageDraw.Draw(img)


def text(x, y, s, style="r", size=15, fill=INK, anchor="la"):
    d.text((x * S, y * S), s, font=f(style, size), fill=fill, anchor=anchor)


def width_of(s, style="r", size=15):
    return d.textlength(s, font=f(style, size)) / S


def rect(x0, y0, x1, y1, fill=None, outline=None, r=0, w=1):
    box = (x0 * S, y0 * S, x1 * S, y1 * S)
    if r:
        d.rounded_rectangle(box, radius=r * S, fill=fill, outline=outline, width=w * S)
    else:
        d.rectangle(box, fill=fill, outline=outline, width=w * S)


def rule(y, x0=PAD, x1=W - PAD):
    rect(x0, y, x1, y + 1, fill=RULE)


def score_bar(x, y, w, h, score, lo, hi, band=BAND, dot=TEAL):
    """0-10 track with the confidence band shaded and the score marked."""
    rect(x, y, x + w, y + h, fill=TRACK, r=h // 2)
    rect(x + w * lo / 10, y, x + w * hi / 10, y + h, fill=band, r=h // 2)
    cx = x + w * score / 10
    rect(cx - 1.6, y - 4, cx + 1.6, y + h + 4, fill=dot, r=2)


def fill_bar(x, y, w, h, value, colour):
    rect(x, y, x + w, y + h, fill=TRACK, r=h // 2)
    rect(x, y, x + w * value / 10, y + h, fill=colour, r=h // 2)


def chip(x, y, label, fg, bg, size=12, padx=9, pady=5):
    tw = width_of(label, "sb", size)
    rect(x, y, x + tw + padx * 2, y + size + pady * 2, fill=bg, r=(size + pady * 2) // 2)
    text(x + padx, y + pady - 1, label, "sb", size, fg)
    return tw + padx * 2


# ────────────────────────────────── header ──────────────────────────────────
y = 0
rect(0, 0, W, 78, fill=HEADER)
text(PAD, 20, "Hyundai Creta  SX (O) 1.5 Diesel AT", "b", 22, (255, 255, 255))
text(PAD, 50, "the exact variant, never just \u201cCreta\u201d", "i", 13, (168, 209, 203))
text(W - PAD, 30, "\u20b9 19.2L \u2013 20.4L", "sb", 19, (255, 255, 255), anchor="ra")

y = 78 + 34

# ─────────────────────────────── overall score ──────────────────────────────
text(PAD, y - 4, "7.8", "b", 60, INK)
sw = width_of("7.8", "b", 60)
text(PAD + sw + 8, y + 30, "/ 10", "sb", 20, MUTED)

bar_x = PAD + 200
bar_w = 430
score_bar(bar_x, y + 22, bar_w, 14, 7.8, 7.1, 8.4)
text(bar_x, y + 46, "0", "r", 11, FAINT)
text(bar_x + bar_w, y + 46, "10", "r", 11, FAINT, anchor="ra")
text(bar_x + bar_w * 7.1 / 10, y + 2, "7.1", "sb", 12, TEAL, anchor="ma")
text(bar_x + bar_w * 8.4 / 10, y + 2, "8.4", "sb", 12, TEAL, anchor="ma")

text(W - PAD, y + 10, "we are confident the true score", "r", 14, MUTED, anchor="ra")
text(W - PAD, y + 30, "lies between 7.1 and 8.4", "sb", 14, INK, anchor="ra")

y += 76
text(PAD, y, "412 reviews", "sb", 14, INK)
text(PAD + width_of("412 reviews", "sb", 14) + 8, y, "\u00b7  6 sources  \u00b7  updated 2 days ago", "r", 14, MUTED)

y += 38
rule(y)
y += 24

# ───────────────────────────── weighting control ────────────────────────────
text(PAD, y + 9, "Weighting", "sb", 15, INK)
px = PAD + 96
for label, on in (("Equal", False), ("By source", False), ("By credibility", True)):
    tw = width_of(label, "sb", 14)
    extra = 22 if on else 0
    rect(px, y, px + tw + 30 + extra, y + 36, fill=(TEAL if on else PILL_BG), r=18)
    if on:
        # hand-drawn tick: Segoe UI has no U+2713 glyph
        d.line([((px + 16) * S, (y + 18) * S), ((px + 21) * S, (y + 23) * S),
                ((px + 30) * S, (y + 12) * S)], fill=(255, 255, 255), width=2 * S,
               joint="curve")
    text(px + 15 + extra, y + 9, label, "sb", 14, (255, 255, 255) if on else MUTED)
    px += tw + 40 + extra

text(px + 6, y + 11, "\u2190  flip this and every number below moves", "i", 13, AMBER)

y += 60
rule(y)
y += 26

# ──────────────────────────── disagreement section ──────────────────────────
text(PAD, y, "WHERE OWNERS DISAGREE MOST", "b", 14, INK)
text(W - PAD, y + 1, "topics ordered by disagreement, not by score", "i", 13, MUTED, anchor="ra")
y += 30

COL_BAR = PAD + 330
COL_SCORE = COL_BAR - 22
BARW = 250


def aspect_row(y, name, score, lo, hi, div, tone):
    colour, soft, word = tone
    text(PAD, y + 4, name, "sb", 16, INK)
    text(COL_SCORE, y + 2, f"{score}", "b", 18, INK, anchor="ra")
    score_bar(COL_BAR, y + 9, BARW, 12, score, lo, hi, band=soft, dot=colour)
    text(COL_BAR + BARW + 16, y + 5, f"[ {lo} \u2013 {hi} ]", "r", 13, MUTED)
    chip(COL_BAR + BARW + 108, y + 2, f"{word}  \u00b7  {div}", colour, soft)
    return y + 40


HIGH = (AMBER, AMBER_SOFT, "disagreement")
MID  = (AMBER, AMBER_SOFT, "disagreement")
LOW  = (GREEN, GREEN_SOFT, "agreement")

y = aspect_row(y, "Gearbox and transmission", 6.2, 5.4, 7.1, 0.61, HIGH)

# the explanation callout
rect(PAD, y - 6, W - PAD, y + 62, fill=AMBER_SOFT, r=8)
rect(PAD, y - 6, PAD + 4, y + 62, fill=AMBER, r=2)
text(PAD + 18, y + 4, "71% of this split is explained by transmission type", "sb", 15, (124, 45, 18))
text(PAD + 18, y + 30, "Automatic owners rate it  6.2", "r", 14, (124, 45, 18))
text(PAD + 268, y + 30, "\u00b7", "r", 14, (180, 120, 60))
text(PAD + 290, y + 30, "Manual owners rate it  8.8", "r", 14, (124, 45, 18))
text(W - PAD - 18, y + 30, "34 reviews  \u203a", "sb", 13, AMBER, anchor="ra")
y += 82

y = aspect_row(y, "Service and after-sales", 5.9, 5.1, 6.6, 0.44, MID)
y = aspect_row(y, "Ride and comfort", 8.6, 8.2, 8.9, 0.12, LOW)

y += 6
rule(y)
y += 22

# ───────────────────────────────── mileage ──────────────────────────────────
text(PAD, y + 6, "Real-world mileage", "sb", 16, INK)
text(COL_SCORE, y + 4, "17.2", "b", 18, INK, anchor="ra")
text(COL_SCORE + 6, y + 10, "kmpl", "r", 13, MUTED)
text(COL_BAR + 90, y + 8, "claimed  21.4 kmpl", "r", 14, MUTED)
chip(COL_BAR + BARW + 108, y + 5, "\u2212 19.6 %", RED, (254, 226, 226), size=13)
y += 44
rule(y)
y += 24

# ────────────────────────────── expert vs owner ─────────────────────────────
text(PAD, y, "EXPERTS vs OWNERS", "b", 14, INK)
y += 28
text(PAD, y + 1, "Media", "r", 15, MUTED)
text(PAD + 84, y, "8.9", "sb", 16, INK, anchor="ra")
fill_bar(PAD + 100, y + 4, 420, 13, 8.9, (120, 170, 200))
y += 30
text(PAD, y + 1, "Owners", "r", 15, MUTED)
text(PAD + 84, y, "7.4", "sb", 16, INK, anchor="ra")
fill_bar(PAD + 100, y + 4, 420, 13, 7.4, TEAL)
text(PAD + 560, y - 14, "Widest gap: service and after-sales", "sb", 14, INK)
text(PAD + 560, y + 8, "media 8.5   vs   owners 5.9", "r", 14, MUTED)
y += 40
rule(y)
y += 22

# ───────────────────────────── official record ──────────────────────────────
rect(PAD, y, W - PAD, y + 54, fill=TEAL_SOFT, r=8)
text(PAD + 18, y + 8, "OFFICIAL RECORD", "b", 12, TEAL)
text(PAD + 18, y + 28, "Bharat NCAP  5-star adult / 4-star child", "sb", 14, INK)
text(PAD + 350, y + 28, "\u00b7   1 recall  (2024, fuel pump)", "r", 14, MUTED)
y += 72

text(PAD, y, "Every number on this screen can be clicked to see the exact reviews behind it.",
     "i", 13, MUTED)
y += 26

# ─────────────────────────────── finish ─────────────────────────────────────
H = y + PAD - 20
img = img.crop((0, 0, W * S, int(H * S)))
frame = ImageDraw.Draw(img)
frame.rectangle((0, 0, W * S - 1, int(H * S) - 1), outline=BORDER, width=1 * S)

out = img.resize((W, int(H)), Image.LANCZOS)
out.save(r"F:\personal-github\revix\docs\review-1\assets\verdict-card.png")
out.convert("RGB").save(r"F:\personal-github\revix\docs\review-1\assets\verdict-card.jpg",
                        quality=95, subsampling=0)
print("size:", out.size)
