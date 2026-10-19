"""Generate the playing-card SVG artwork in ``assets/cards``.

All artwork is original and fully vector: suit shapes, stroke-drawn rank
glyphs (no fonts, so cards look identical on every system), standard pip
layouts, double-ended court figures and a symmetrical card back.

Usage:
    python tools/generate_cards.py [OUTPUT_DIR]

The SVGs only use features supported by Qt SVG (SVG Tiny 1.2): paths, basic
shapes, groups, transforms and linear/radial gradients.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "assets" / "cards"

# Poker size 63 x 88 mm, at 10 units per mm.
W, H = 630, 880
CORNER = 34

RANKS = "23456789TJQKA"
SUITS = "cdhs"

RED = "#b5232c"
BLACK = "#18181d"
GOLD = "#d4a23c"
GOLD_DARK = "#9a7124"
BLUE = "#2b4c8c"
SKIN = "#f2d2ae"
INK = "#1d1916"
FACE_TOP = "#fdfbf6"
FACE_BOTTOM = "#f3eee3"
EDGE = "#bdb4a3"


def suit_color(suit: str) -> str:
    return RED if suit in "dh" else BLACK


# --------------------------------------------------------------------- suits
# Each suit shape is defined in a 100 x 100 box centred on (50, 50).

SUIT_PATHS = {
    "d": "M50 0 C61 19 77 37 94 50 C77 63 61 81 50 100 C39 81 23 63 6 50 C23 37 39 19 50 0 Z",
    "h": (
        "M50 96 C22 72 2 54 2 31 C2 14 14 3 28 3 C39 3 46 10 50 21 "
        "C54 10 61 3 72 3 C86 3 98 14 98 31 C98 54 78 72 50 96 Z"
    ),
    "s": (
        "M50 0 C78 24 98 41 98 61 C98 76 87 85 74 85 C64 85 57 80 53 72 "
        "C54 85 59 94 68 100 L32 100 C41 94 46 85 47 72 "
        "C43 80 36 85 26 85 C13 85 2 76 2 61 C2 41 22 24 50 0 Z"
    ),
    "c": (
        "M50 4 C63 4 73 14 73 27 C73 34 70 40 65 44 C69 42 73 41 77 41 "
        "C90 41 100 51 100 64 C100 77 90 87 77 87 C66 87 58 81 54 72 "
        "C55 85 60 94 68 100 L32 100 C40 94 45 85 46 72 "
        "C42 81 34 87 23 87 C10 87 0 77 0 64 C0 51 10 41 23 41 "
        "C27 41 31 42 35 44 C30 40 27 34 27 27 C27 14 37 4 50 4 Z"
    ),
}


def suit_shape(suit: str, cx: float, cy: float, size: float, *, flip: bool = False,
               fill: str | None = None) -> str:
    """Suit symbol centred on (cx, cy), ``size`` units wide."""
    scale = size / 100
    rotate = f" rotate(180 {cx:.1f} {cy:.1f})" if flip else ""
    return (
        f'<path transform="{rotate} translate({cx - size / 2:.2f} {cy - size / 2:.2f}) '
        f'scale({scale:.4f})" d="{SUIT_PATHS[suit]}" fill="{fill or suit_color(suit)}"/>'
    )


# -------------------------------------------------------------------- glyphs
# Rank glyphs as monoline strokes in a box 60 wide x 90 tall.

GLYPHS = {
    "A": ["M2 90 L30 2 L58 90", "M13 60 L47 60"],
    "K": ["M6 2 L6 88", "M54 2 L6 56", "M23 40 L56 88"],
    "Q": [
        "M30 2 C51 2 58 22 58 45 C58 68 51 88 30 88 C9 88 2 68 2 45 C2 22 9 2 30 2 Z",
        "M36 64 L58 90",
    ],
    "J": ["M22 2 L56 2", "M44 2 L44 64 C44 81 35 88 23 88 C11 88 4 80 4 68"],
    "2": ["M4 22 C4 9 15 2 30 2 C45 2 56 11 56 25 C56 42 44 52 4 88 L58 88"],
    "3": [
        "M5 12 C11 5 19 2 30 2 C45 2 54 11 54 23 C54 36 44 43 26 43",
        "M26 43 C46 43 57 52 57 66 C57 80 46 88 30 88 C18 88 9 84 3 77",
    ],
    "4": ["M44 88 L44 2 L2 62 L58 62"],
    "5": ["M54 2 L12 2 L8 41 C15 36 22 34 30 34 C47 34 57 45 57 61 C57 78 46 88 29 88 C17 88 8 83 3 76"],
    "6": [
        "M52 8 C46 4 39 2 31 2 C13 2 3 21 3 49 C3 74 13 88 30 88 "
        "C47 88 57 78 57 62 C57 46 47 36 31 36 C18 36 7 43 3 54"
    ],
    "7": ["M2 2 L58 2 L22 88"],
    "8": [
        "M30 42 C16 42 8 35 8 22 C8 10 17 2 30 2 C43 2 52 10 52 22 C52 35 44 42 30 42 Z",
        "M30 42 C46 42 57 51 57 65 C57 79 46 88 30 88 C14 88 3 79 3 65 C3 51 14 42 30 42 Z",
    ],
    "9": [
        "M8 82 C14 86 21 88 29 88 C47 88 57 69 57 41 C57 16 47 2 30 2 "
        "C13 2 3 12 3 28 C3 44 13 54 29 54 C42 54 53 47 57 36"
    ],
    "1": ["M6 16 L20 2 L20 88"],
    "0": ["M24 2 C40 2 46 22 46 45 C46 68 40 88 24 88 C8 88 2 68 2 45 C2 22 8 2 24 2 Z"],
}
GLYPH_WIDTH = {"1": 26, "0": 48}


def rank_glyph(rank: str, x: float, y: float, height: float, color: str) -> str:
    """Rank index with its top-left at (x, y); ``height`` units tall."""
    scale = height / 90
    chars = ["1", "0"] if rank == "T" else [rank]
    parts = []
    offset = 0.0
    # "10" is two glyphs squeezed into roughly one glyph's width.
    squeeze = 0.78 if rank == "T" else 1.0
    for char in chars:
        strokes = "".join(f'<path d="{d}"/>' for d in GLYPHS[char])
        parts.append(f'<g transform="translate({offset:.1f} 0)">{strokes}</g>')
        offset += GLYPH_WIDTH.get(char, 60) + 8
    total = offset - 8
    width_units = total * squeeze
    return (
        f'<g transform="translate({x - width_units * scale / 2:.2f} {y:.2f}) '
        f'scale({scale * squeeze:.4f} {scale:.4f})" fill="none" stroke="{color}" '
        f'stroke-width="{11 / squeeze:.1f}" stroke-linecap="round" stroke-linejoin="round">'
        + "".join(parts)
        + "</g>"
    )


# ------------------------------------------------------------------- layouts

PIP_COLUMNS = {"L": 205, "C": 315, "R": 425}
PIP_TOP, PIP_BOTTOM = 175, 705
PIP_SIZE = 104

# (column, fraction of the pip area from top to bottom)
PIP_LAYOUTS = {
    "2": [("C", 0), ("C", 1)],
    "3": [("C", 0), ("C", 0.5), ("C", 1)],
    "4": [("L", 0), ("R", 0), ("L", 1), ("R", 1)],
    "5": [("L", 0), ("R", 0), ("C", 0.5), ("L", 1), ("R", 1)],
    "6": [("L", 0), ("R", 0), ("L", 0.5), ("R", 0.5), ("L", 1), ("R", 1)],
    "7": [("L", 0), ("R", 0), ("C", 0.25), ("L", 0.5), ("R", 0.5), ("L", 1), ("R", 1)],
    "8": [("L", 0), ("R", 0), ("C", 0.25), ("L", 0.5), ("R", 0.5), ("C", 0.75), ("L", 1), ("R", 1)],
    "9": [("L", 0), ("R", 0), ("L", 1 / 3), ("R", 1 / 3), ("C", 0.5),
          ("L", 2 / 3), ("R", 2 / 3), ("L", 1), ("R", 1)],
    "T": [("L", 0), ("R", 0), ("C", 1 / 6), ("L", 1 / 3), ("R", 1 / 3),
          ("L", 2 / 3), ("R", 2 / 3), ("C", 5 / 6), ("L", 1), ("R", 1)],
}


def pip_positions(rank: str) -> list[tuple[float, float, bool]]:
    """(x, y, flipped) for each pip; pips below the middle point downwards."""
    result = []
    for column, fraction in PIP_LAYOUTS[rank]:
        y = PIP_TOP + (PIP_BOTTOM - PIP_TOP) * fraction
        result.append((PIP_COLUMNS[column], y, fraction > 0.5))
    return result


# ---------------------------------------------------------------- card parts

def card_base(defs_extra: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="tiny" '
        f'viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
        "<defs>"
        f'<linearGradient id="face" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{FACE_TOP}"/><stop offset="1" stop-color="{FACE_BOTTOM}"/>'
        "</linearGradient>"
        f"{defs_extra}"
        "</defs>"
        f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="{CORNER}" ry="{CORNER}" '
        f'fill="url(#face)" stroke="{EDGE}" stroke-width="3"/>'
    )


def indices(rank: str, suit: str) -> str:
    color = suit_color(suit)
    corner = (
        rank_glyph(rank, 62, 38, 84, color)
        + suit_shape(suit, 62, 178, 58)
    )
    return corner + f'<g transform="rotate(180 {W / 2} {H / 2})">{corner}</g>'


def pips(rank: str, suit: str) -> str:
    return "".join(suit_shape(suit, x, y, PIP_SIZE, flip=flip) for x, y, flip in pip_positions(rank))


def ace(suit: str) -> str:
    cx, cy = W / 2, H / 2
    if suit == "s":
        # Ornamental ace of spades.
        rings = (
            f'<circle cx="{cx}" cy="{cy}" r="190" fill="none" stroke="{GOLD}" stroke-width="5"/>'
            f'<circle cx="{cx}" cy="{cy}" r="176" fill="none" stroke="{BLACK}" stroke-width="2"/>'
        )
        dots = "".join(
            f'<circle cx="{cx + 190 * math.cos(a):.1f}" cy="{cy + 190 * math.sin(a):.1f}" r="7" fill="{GOLD}"/>'
            for a in (i * math.pi / 8 for i in range(16))
        )
        return rings + dots + suit_shape("s", cx, cy, 250)
    return suit_shape(suit, cx, cy, 200)


# ---------------------------------------------------------------- court cards

PANEL_X, PANEL_Y = 118, 112
PANEL_W, PANEL_H = W - 2 * PANEL_X, H - 2 * PANEL_Y
HALF_H = PANEL_H / 2

BAND_PATTERNS = {"c": "stripes", "d": "diamonds", "h": "dots", "s": "checks"}


def band_pattern(kind: str, x: float, y: float, w: float, h: float, color: str) -> str:
    """Decoration for the central robe band (differs per suit)."""
    out = []
    if kind == "stripes":
        step = 18
        for i in range(int(h // step) + 1):
            yy = y + i * step
            out.append(f'<rect x="{x}" y="{yy:.1f}" width="{w}" height="6" fill="{color}"/>')
    elif kind == "dots":
        for i in range(int(h // 22) + 1):
            out.append(f'<circle cx="{x + w / 2}" cy="{y + 10 + i * 22:.1f}" r="5" fill="{color}"/>')
    elif kind == "diamonds":
        for i in range(int(h // 26) + 1):
            cy = y + 12 + i * 26
            cx = x + w / 2
            out.append(
                f'<path d="M{cx} {cy - 9:.1f} L{cx + 8} {cy:.1f} L{cx} {cy + 9:.1f} L{cx - 8} {cy:.1f} Z" fill="{color}"/>'
            )
    else:  # checks
        size = w / 3
        for i in range(int(h // size) + 1):
            for j in range(3):
                if (i + j) % 2 == 0:
                    out.append(
                        f'<rect x="{x + j * size:.1f}" y="{y + i * size:.1f}" '
                        f'width="{size:.1f}" height="{min(size, y + h - (y + i * size)):.1f}" fill="{color}"/>'
                    )
    return "".join(out)


def court_half(rank: str, suit: str) -> str:
    """Upper half of a court figure in panel coordinates (0..PANEL_W, 0..HALF_H)."""
    color = suit_color(suit)
    cx = PANEL_W / 2
    # Red suits: red robe, blue sash. Black suits: blue robe, black sash.
    robe = RED if suit in "dh" else BLUE
    secondary = BLUE if suit in "dh" else BLACK
    accent = BLUE if suit in "dh" else RED
    stroke = f'stroke="{INK}" stroke-width="3" stroke-linejoin="round"'
    parts = []

    # Robe and shoulders.
    parts.append(
        f'<path d="M8 {HALF_H} L8 262 C8 228 56 206 118 198 L{PANEL_W - 118} 198 '
        f'C{PANEL_W - 56} 206 {PANEL_W - 8} 228 {PANEL_W - 8} 262 L{PANEL_W - 8} {HALF_H} Z" '
        f'fill="{robe}" {stroke}/>'
    )
    # Sash and inner trim.
    parts.append(
        f'<path d="M70 {HALF_H} L{PANEL_W - 128} 205 L{PANEL_W - 92} 214 L112 {HALF_H} Z" '
        f'fill="{secondary}" {stroke}/>'
    )
    band_x, band_w = cx - 26, 52
    parts.append(f'<rect x="{band_x}" y="200" width="{band_w}" height="{HALF_H - 200}" fill="{GOLD}" {stroke}/>')
    parts.append(band_pattern(BAND_PATTERNS[suit], band_x + 4, 206, band_w - 8, HALF_H - 210, color))

    # Collar.
    parts.append(
        f'<path d="M{cx - 92} 202 C{cx - 60} 236 {cx + 60} 236 {cx + 92} 202 '
        f'C{cx + 60} 186 {cx - 60} 186 {cx - 92} 202 Z" fill="{GOLD}" {stroke}/>'
    )
    for i in range(7):
        x = cx - 66 + i * 22
        parts.append(f'<circle cx="{x}" cy="{210 + (3 - abs(i - 3)) * 3}" r="4" fill="{accent}"/>')

    # Hair / veil behind the head.
    hair = {"K": "#e8e4dc", "Q": "#c98a2a", "J": "#7a4a22"}[rank]
    if rank == "Q":
        parts.append(
            f'<path d="M{cx - 72} 92 C{cx - 96} 140 {cx - 92} 190 {cx - 70} 214 L{cx + 70} 214 '
            f'C{cx + 92} 190 {cx + 96} 140 {cx + 72} 92 Z" fill="{secondary}" {stroke}/>'
        )
    parts.append(
        f'<path d="M{cx - 50} 92 C{cx - 66} 130 {cx - 62} 170 {cx - 44} 190 L{cx + 44} 190 '
        f'C{cx + 62} 170 {cx + 66} 130 {cx + 50} 92 Z" fill="{hair}" {stroke}/>'
    )

    # Face.
    parts.append(f'<ellipse cx="{cx}" cy="138" rx="40" ry="48" fill="{SKIN}" {stroke}/>')
    features = (
        f'<path d="M{cx - 22} 128 C{cx - 17} 123 {cx - 9} 123 {cx - 5} 128" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>'
        f'<path d="M{cx + 5} 128 C{cx + 9} 123 {cx + 17} 123 {cx + 22} 128" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>'
        f'<circle cx="{cx - 13}" cy="133" r="3.2" fill="{INK}"/><circle cx="{cx + 13}" cy="133" r="3.2" fill="{INK}"/>'
        f'<path d="M{cx} 136 L{cx - 5} 152 L{cx + 2} 153" fill="none" stroke="{INK}" stroke-width="2.5" stroke-linecap="round"/>'
    )
    parts.append(features)
    if rank == "K":
        parts.append(
            f'<path d="M{cx - 38} 148 C{cx - 36} 186 {cx - 16} 204 {cx} 206 C{cx + 16} 204 {cx + 36} 186 {cx + 38} 148 '
            f'C{cx + 24} 160 {cx - 24} 160 {cx - 38} 148 Z" fill="{hair}" {stroke}/>'
        )
        parts.append(
            f'<path d="M{cx - 20} 163 C{cx - 10} 157 {cx + 10} 157 {cx + 20} 163" fill="none" stroke="{INK}" stroke-width="3" stroke-linecap="round"/>'
        )
    else:
        parts.append(
            f'<path d="M{cx - 9} 166 C{cx - 4} 170 {cx + 4} 170 {cx + 9} 166" fill="none" stroke="{RED if rank == "Q" else INK}" stroke-width="3" stroke-linecap="round"/>'
        )

    # Headwear.
    if rank == "K":
        parts.append(
            f'<path d="M{cx - 54} 96 L{cx - 58} 36 L{cx - 30} 64 L{cx} 22 L{cx + 30} 64 L{cx + 58} 36 L{cx + 54} 96 Z" '
            f'fill="{GOLD}" {stroke}/>'
        )
        parts.append(f'<rect x="{cx - 56}" y="80" width="112" height="20" fill="{GOLD_DARK}" {stroke}/>')
        for x, c in ((cx - 32, accent), (cx, RED), (cx + 32, accent)):
            parts.append(f'<circle cx="{x}" cy="90" r="6" fill="{c}" stroke="{INK}" stroke-width="2"/>')
        for x, y in ((cx - 58, 36), (cx, 22), (cx + 58, 36)):
            parts.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{GOLD}" {stroke}/>')
    elif rank == "Q":
        parts.append(
            f'<path d="M{cx - 46} 98 L{cx - 48} 62 C{cx - 36} 76 {cx - 24} 76 {cx - 16} 56 '
            f'C{cx - 8} 76 {cx + 8} 76 {cx + 16} 56 C{cx + 24} 76 {cx + 36} 76 {cx + 48} 62 L{cx + 46} 98 Z" '
            f'fill="{GOLD}" {stroke}/>'
        )
        parts.append(f'<rect x="{cx - 48}" y="88" width="96" height="14" fill="{GOLD_DARK}" {stroke}/>')
        for x in (cx - 16, cx + 16):
            parts.append(f'<circle cx="{x}" cy="52" r="7" fill="{color}" stroke="{INK}" stroke-width="2"/>')
        parts.append(f'<circle cx="{cx}" cy="95" r="5" fill="{color}"/>')
    else:  # Jack: brimmed cap with plume
        parts.append(
            f'<path d="M{cx - 62} 100 C{cx - 60} 60 {cx - 30} 46 {cx + 4} 46 C{cx + 40} 46 {cx + 60} 64 {cx + 62} 100 Z" '
            f'fill="{secondary}" {stroke}/>'
        )
        parts.append(f'<rect x="{cx - 66}" y="88" width="132" height="16" rx="6" fill="{GOLD}" {stroke}/>')
        parts.append(
            f'<path d="M{cx + 30} 54 C{cx + 70} 20 {cx + 112} 22 {cx + 128} 40 C{cx + 98} 38 {cx + 70} 50 {cx + 44} 72 Z" '
            f'fill="{color}" {stroke}/>'
        )

    # Held item.
    if rank == "K":
        sx = 60
        parts.append(f'<path d="M{sx - 7} {HALF_H} L{sx - 7} 70 L{sx} 52 L{sx + 7} 70 L{sx + 7} {HALF_H} Z" fill="#dfe3e8" {stroke}/>')
        parts.append(f'<rect x="{sx - 24}" y="222" width="48" height="12" rx="4" fill="{GOLD}" {stroke}/>')
        parts.append(f'<rect x="{sx - 6}" y="234" width="12" height="40" fill="{GOLD_DARK}" {stroke}/>')
    elif rank == "Q":
        fx, fy = PANEL_W - 64, 116
        parts.append(f'<path d="M{fx} {fy} L{fx - 4} 290" fill="none" stroke="#3f6b35" stroke-width="7" stroke-linecap="round"/>')
        for i in range(6):
            a = i * math.pi / 3
            parts.append(
                f'<ellipse cx="{fx + 16 * math.cos(a):.1f}" cy="{fy + 16 * math.sin(a):.1f}" rx="12" ry="12" '
                f'fill="{color}" stroke="{INK}" stroke-width="2.5"/>'
            )
        parts.append(f'<circle cx="{fx}" cy="{fy}" r="9" fill="{GOLD}" stroke="{INK}" stroke-width="2.5"/>')
    else:
        hx = PANEL_W - 58
        parts.append(f'<rect x="{hx - 5}" y="70" width="10" height="{HALF_H - 70}" fill="{GOLD_DARK}" {stroke}/>')
        parts.append(
            f'<path d="M{hx} 26 L{hx + 14} 62 L{hx + 38} 72 L{hx + 14} 84 L{hx} 96 L{hx - 14} 84 L{hx - 38} 72 L{hx - 14} 62 Z" '
            f'fill="#dfe3e8" {stroke}/>'
        )

    # Suit emblem in the panel corner.
    parts.append(suit_shape(suit, 40, 38, 40))
    return "".join(parts)


def court(rank: str, suit: str) -> str:
    color = suit_color(suit)
    half = court_half(rank, suit)
    return (
        f'<rect x="{PANEL_X}" y="{PANEL_Y}" width="{PANEL_W}" height="{PANEL_H}" fill="#fbf6ea"/>'
        f'<g transform="translate({PANEL_X} {PANEL_Y})">{half}</g>'
        f'<g transform="rotate(180 {W / 2} {H / 2}) translate({PANEL_X} {PANEL_Y})">{half}</g>'
        f'<path d="M{PANEL_X} {H / 2} L{W - PANEL_X} {H / 2}" stroke="{GOLD_DARK}" stroke-width="3"/>'
        f'<rect x="{PANEL_X}" y="{PANEL_Y}" width="{PANEL_W}" height="{PANEL_H}" fill="none" '
        f'stroke="{color}" stroke-width="5"/>'
        f'<rect x="{PANEL_X + 8}" y="{PANEL_Y + 8}" width="{PANEL_W - 16}" height="{PANEL_H - 16}" fill="none" '
        f'stroke="{GOLD}" stroke-width="2"/>'
    )


def card_svg(code: str) -> str:
    rank, suit = code[0], code[1]
    if rank == "A":
        body = ace(suit)
    elif rank in "JQK":
        body = court(rank, suit)
    else:
        body = pips(rank, suit)
    return card_base() + body + indices(rank, suit) + "</svg>\n"


# ----------------------------------------------------------------------- back

BACK_BASE = "#6d1a24"
BACK_DARK = "#4e1119"
BACK_LINE = "#c9a45a"


def clip_line(x1, y1, x2, y2, left, top, right, bottom):
    """Liang-Barsky clip of a segment to a rectangle; None if outside."""
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - left), (dx, right - x1), (-dy, y1 - top), (dy, bottom - y1)):
        if p == 0:
            if q < 0:
                return None
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return None
    return x1 + t0 * dx, y1 + t0 * dy, x1 + t1 * dx, y1 + t1 * dy


def back_svg() -> str:
    inset = 30
    left, top, right, bottom = inset, inset, W - inset, H - inset
    cx, cy = W / 2, H / 2
    lines = []
    step = 28
    span = W + H
    # Lattice symmetric about the card centre.
    for k in range(-span // step, span // step + 1):
        c = k * step
        for (x1, y1, x2, y2) in (
            (cx + c - span, cy - span, cx + c + span, cy + span),
            (cx + c + span, cy - span, cx + c - span, cy + span),
        ):
            seg = clip_line(x1, y1, x2, y2, left, top, right, bottom)
            if seg:
                lines.append(f"M{seg[0]:.1f} {seg[1]:.1f} L{seg[2]:.1f} {seg[3]:.1f}")
    lattice = f'<path d="{" ".join(lines)}" stroke="{BACK_LINE}" stroke-opacity="0.35" stroke-width="2" fill="none"/>'
    # Small diamonds at lattice crossings would be too busy; add a dot grid instead.
    dots = []
    for i in range(-20, 21):
        for j in range(-30, 31):
            x = cx + i * step
            y = cy + j * step
            if (i + j) % 2 == 0 and left + 8 < x < right - 8 and top + 8 < y < bottom - 8:
                dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{BACK_LINE}" fill-opacity="0.55"/>')

    petals = "".join(
        f'<ellipse cx="{cx}" cy="{cy - 62}" rx="16" ry="46" transform="rotate({a} {cx} {cy})" '
        f'fill="{BACK_DARK}" stroke="{BACK_LINE}" stroke-width="2.5"/>'
        for a in range(0, 360, 30)
    )
    medallion = (
        f'<ellipse cx="{cx}" cy="{cy}" rx="150" ry="150" fill="{BACK_BASE}" stroke="{BACK_LINE}" stroke-width="4"/>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="136" ry="136" fill="none" stroke="{BACK_LINE}" stroke-width="1.5"/>'
        + petals
        + f'<circle cx="{cx}" cy="{cy}" r="34" fill="{BACK_LINE}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="24" fill="{BACK_DARK}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="10" fill="{BACK_LINE}"/>'
    )
    corner_marks = "".join(
        f'<path d="M{x} {y - 20} L{x + 14} {y} L{x} {y + 20} L{x - 14} {y} Z" fill="{BACK_LINE}"/>'
        for x, y in ((left + 44, top + 44), (right - 44, top + 44), (left + 44, bottom - 44), (right - 44, bottom - 44))
    )
    return (
        card_base(
            f'<radialGradient id="backglow" cx="0.5" cy="0.5" r="0.7">'
            f'<stop offset="0" stop-color="#8a2430"/><stop offset="1" stop-color="{BACK_DARK}"/>'
            "</radialGradient>"
        )
        + f'<rect x="{left}" y="{top}" width="{right - left}" height="{bottom - top}" rx="14" fill="url(#backglow)"/>'
        + lattice
        + "".join(dots)
        + f'<rect x="{left}" y="{top}" width="{right - left}" height="{bottom - top}" rx="14" fill="none" '
        f'stroke="{BACK_LINE}" stroke-width="5"/>'
        + f'<rect x="{left + 14}" y="{top + 14}" width="{right - left - 28}" height="{bottom - top - 28}" rx="8" '
        f'fill="none" stroke="{BACK_LINE}" stroke-width="1.5"/>'
        + corner_marks
        + medallion
        + "</svg>\n"
    )


def all_cards() -> dict[str, str]:
    """File name -> SVG text for the 52 faces and the back."""
    files = {f"{r}{s}.svg": card_svg(f"{r}{s}") for s in SUITS for r in RANKS}
    files["back.svg"] = back_svg()
    return files


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    for name, text in all_cards().items():
        (output / name).write_text(text, encoding="utf-8")
    print(f"Wrote {len(all_cards())} files to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
