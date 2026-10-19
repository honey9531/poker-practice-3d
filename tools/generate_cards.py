"""Generate the playing-card SVG artwork in ``assets/cards``.

All artwork is original and fully vector, in an antique style: aged
parchment faces with a gold frame and corner flourishes, embossed pips with
gold rims, ornate aces, double-ended court figures robed in their suit's
colours (navy spades, crimson hearts, ruby diamonds, emerald clubs), and four
card backs with gold filigree. Rank indices are stroke-drawn glyphs (no
fonts), so cards look identical on every system.

The backs carry no suit emblem: every card in play shares the back chosen in
Settings, so a face-down card never gives anything away.

Usage:
    python tools/generate_cards.py [OUTPUT_DIR]

The SVGs only use features supported by Qt SVG (SVG Tiny 1.2): paths, basic
shapes, groups, transforms, opacity and linear/radial gradients.
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "assets" / "cards"

# Poker size 63 x 88 mm, at 10 units per mm.
W, H = 630, 880
CORNER = 34

RANKS = "23456789TJQKA"
SUITS = "cdhs"

RED = "#a3161f"
BLACK = "#15151a"
GOLD = "#c9a04a"
GOLD_LIGHT = "#f1d68f"
GOLD_DARK = "#8a6526"
INK = "#2a1c12"
PAPER_EDGE = "#b8a37a"
STAIN = "#9a7436"

# Inner gold frame (indices sit outside it, in the corners).
FRAME_X, FRAME_Y = 104, 30

# Colours per suit: robes and gems of the court cards, gem of the ace.
PALETTES = {
    "s": {"robe": "#2b3d6b", "robe_dark": "#111a33", "gem": "#3f78c8"},
    "h": {"robe": "#9c2129", "robe_dark": "#4f0b10", "gem": "#3f78c8"},
    "d": {"robe": "#b5341f", "robe_dark": "#5c140a", "gem": "#e8b84a"},
    "c": {"robe": "#23643d", "robe_dark": "#0c2f1b", "gem": "#2f9e63"},
}

# Card backs: (base, dark, glow) per style. The names are the setting values.
BACKS = {
    "navy": ("#18223f", "#090e1d", "#2b3c6e"),
    "crimson": ("#5c1219", "#2c060a", "#8e2330"),
    "ruby": ("#7a2412", "#360d05", "#ad4421"),
    "emerald": ("#123a29", "#061a10", "#21583d"),
}


def suit_color(suit: str) -> str:
    return RED if suit in "dh" else BLACK


def gradients() -> str:
    """Shared gradient definitions used by every face."""
    return (
        '<radialGradient id="paper" cx="0.5" cy="0.45" r="0.78">'
        '<stop offset="0" stop-color="#f8f0de"/><stop offset="0.65" stop-color="#efe2c5"/>'
        '<stop offset="1" stop-color="#dcc79c"/></radialGradient>'
        # Embossed pips: light from the top left.
        '<linearGradient id="pipRed" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#e6524f"/><stop offset="0.5" stop-color="#b3181f"/>'
        '<stop offset="1" stop-color="#5e070c"/></linearGradient>'
        '<linearGradient id="pipBlack" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#4d4d58"/><stop offset="0.5" stop-color="#1b1b21"/>'
        '<stop offset="1" stop-color="#030304"/></linearGradient>'
        '<linearGradient id="gold" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{GOLD_LIGHT}"/><stop offset="0.55" stop-color="{GOLD}"/>'
        f'<stop offset="1" stop-color="{GOLD_DARK}"/></linearGradient>'
        '<linearGradient id="skin" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#f6dabb"/><stop offset="1" stop-color="#d9a57c"/></linearGradient>'
    )


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


def suit_fill(suit: str) -> str:
    return "url(#pipRed)" if suit in "dh" else "url(#pipBlack)"


def suit_shape(suit: str, cx: float, cy: float, size: float, *, flip: bool = False,
               fill: str | None = None, rim: float = 0.0) -> str:
    """Suit symbol centred on (cx, cy), ``size`` units wide.

    ``rim`` draws a gold edge of that many units (embossed pips and aces).
    """
    scale = size / 100
    rotate = f"rotate(180 {cx:.1f} {cy:.1f}) " if flip else ""
    edge = (f' stroke="{GOLD}" stroke-width="{rim / scale:.2f}" stroke-linejoin="round"' if rim else "")
    return (
        f'<path transform="{rotate}translate({cx - size / 2:.2f} {cy - size / 2:.2f}) '
        f'scale({scale:.4f})" d="{SUIT_PATHS[suit]}" fill="{fill or suit_fill(suit)}"{edge}/>'
    )


# ----------------------------------------------------------------- ornaments

def scroll(x: float, y: float, sx: float, sy: float, color: str = GOLD, width: float = 2.2) -> str:
    """A gold corner flourish at (x, y); ``sx``/``sy`` (+-1) point it into the card."""
    d = (
        "M0 0 C26 0 46 4 58 16 C66 24 64 36 54 36 C46 36 44 26 52 24 "
        "M0 0 C0 26 4 46 16 58 C24 66 36 64 36 54 C36 46 26 44 24 52 "
        "M10 10 C20 12 26 18 28 28 M18 4 C30 6 36 10 40 18 M4 18 C6 30 10 36 18 40"
    )
    return (
        f'<g transform="translate({x:.1f} {y:.1f}) scale({sx} {sy})">'
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>'
        f'<circle cx="54" cy="30" r="2.6" fill="{color}"/><circle cx="30" cy="54" r="2.6" fill="{color}"/>'
        f'<path d="M-2 -2 L6 -10 L14 -2 L6 6 Z" transform="translate(-3 -3)" fill="{color}"/>'
        "</g>"
    )


def gem(cx: float, cy: float, size: float, color: str) -> str:
    """A faceted cabochon: lozenge with light and dark facets and a gold setting."""
    h, w = size, size * 0.72
    return (
        f'<path d="M{cx} {cy - h} L{cx + w} {cy} L{cx} {cy + h} L{cx - w} {cy} Z" '
        f'fill="{color}" stroke="url(#gold)" stroke-width="{max(1.5, size * 0.16):.1f}"/>'
        f'<path d="M{cx} {cy - h} L{cx + w} {cy} L{cx} {cy} Z" fill="#ffffff" fill-opacity="0.35"/>'
        f'<path d="M{cx} {cy + h} L{cx - w} {cy} L{cx} {cy} Z" fill="#000000" fill-opacity="0.3"/>'
        f'<circle cx="{cx - w * 0.3:.1f}" cy="{cy - h * 0.35:.1f}" r="{size * 0.12:.1f}" fill="#ffffff" fill-opacity="0.8"/>'
    )


def star(cx: float, cy: float, outer: float, inner: float, points: int, fill: str, rotation: float = 0) -> str:
    coords = []
    for i in range(points * 2):
        r = outer if i % 2 == 0 else inner
        a = math.radians(rotation - 90 + i * 180 / points)
        coords.append(f"{cx + r * math.cos(a):.1f} {cy + r * math.sin(a):.1f}")
    return f'<path d="M{" L".join(coords)} Z" fill="{fill}"/>'


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

def svg_open(defs_extra: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.2" baseProfile="tiny" '
        f'viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
        f"<defs>{gradients()}{defs_extra}</defs>"
    )


def paper(code: str) -> str:
    """Aged parchment: warm gradient, darker edges and a few faint stains (seeded per card)."""
    rng = random.Random(code)
    stains = "".join(
        f'<ellipse cx="{rng.uniform(80, W - 80):.0f}" cy="{rng.uniform(80, H - 80):.0f}" '
        f'rx="{rng.uniform(20, 95):.0f}" ry="{rng.uniform(15, 70):.0f}" '
        f'transform="rotate({rng.uniform(0, 180):.0f} {W / 2} {H / 2})" '
        f'fill="{STAIN}" fill-opacity="{rng.uniform(0.02, 0.045):.3f}"/>'
        for _ in range(7)
    )
    return (
        f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="{CORNER}" ry="{CORNER}" fill="url(#paper)"/>'
        + stains
        # Edge wear: darker bands just inside the outline.
        + f'<rect x="12" y="12" width="{W - 24}" height="{H - 24}" rx="{CORNER - 10}" fill="none" '
        f'stroke="{STAIN}" stroke-opacity="0.13" stroke-width="22"/>'
        + f'<rect x="26" y="26" width="{W - 52}" height="{H - 52}" rx="{CORNER - 18}" fill="none" '
        f'stroke="{STAIN}" stroke-opacity="0.05" stroke-width="16"/>'
        + f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="{CORNER}" ry="{CORNER}" fill="none" '
        f'stroke="{PAPER_EDGE}" stroke-width="3"/>'
    )


def frame() -> str:
    """Thin gold frame with flourishes in its corners."""
    left, top, right, bottom = FRAME_X, FRAME_Y, W - FRAME_X, H - FRAME_Y
    return (
        f'<rect x="{left}" y="{top}" width="{right - left}" height="{bottom - top}" rx="10" fill="none" '
        f'stroke="{GOLD}" stroke-opacity="0.7" stroke-width="2"/>'
        f'<rect x="{left + 7}" y="{top + 7}" width="{right - left - 14}" height="{bottom - top - 14}" rx="6" '
        f'fill="none" stroke="{GOLD}" stroke-opacity="0.35" stroke-width="1"/>'
        + scroll(right - 10, top + 10, -1, 1)
        + scroll(left + 10, bottom - 10, 1, -1)
        + scroll(left + 10, top + 10, 1, 1, width=1.6)
        + scroll(right - 10, bottom - 10, -1, -1, width=1.6)
    )


def indices(rank: str, suit: str) -> str:
    color = suit_color(suit)
    corner = (
        rank_glyph(rank, 56, 40, 80, color)
        + suit_shape(suit, 56, 170, 52)
    )
    return corner + f'<g transform="rotate(180 {W / 2} {H / 2})">{corner}</g>'


def embossed(suit: str, cx: float, cy: float, size: float, *, flip: bool = False, rim: float) -> str:
    """A suit symbol with a gold rim, lifted off the paper by a soft shadow."""
    offset = size * 0.035
    return (
        suit_shape(suit, cx + offset, cy + offset * 1.4, size, flip=flip, fill="#3b2a14").replace(
            "/>", ' fill-opacity="0.22"/>')
        + suit_shape(suit, cx, cy, size, flip=flip, rim=rim)
    )


def pips(rank: str, suit: str) -> str:
    return "".join(embossed(suit, x, y, PIP_SIZE, flip=flip, rim=5)
                   for x, y, flip in pip_positions(rank))


def ace(suit: str) -> str:
    """Large embossed suit in a gold cartouche, with a gem at its heart."""
    cx, cy = W / 2, H / 2
    rx, ry = 172, 228
    ticks = "".join(
        f'<circle cx="{cx + (rx + 14) * math.cos(a):.1f}" cy="{cy + (ry + 14) * math.sin(a):.1f}" '
        f'r="{4 if i % 2 else 6}" fill="{GOLD}"/>'
        for i, a in enumerate(j * math.pi / 12 for j in range(24))
    )
    cartouche = (
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{GOLD}" fill-opacity="0.07" '
        f'stroke="url(#gold)" stroke-width="5"/>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="{rx - 14}" ry="{ry - 14}" fill="none" stroke="{GOLD}" '
        f'stroke-opacity="0.6" stroke-width="1.5"/>'
        + ticks
        + "".join(scroll(x, y, sx, sy, width=2.4) for x, y, sx, sy in (
            (cx - 18, cy - ry - 2, -1, -1), (cx + 18, cy - ry - 2, 1, -1),
            (cx - 18, cy + ry + 2, -1, 1), (cx + 18, cy + ry + 2, 1, 1)))
        + gem(cx, cy - ry - 4, 14, PALETTES[suit]["gem"])
        + gem(cx, cy + ry + 4, 14, PALETTES[suit]["gem"])
    )
    size = 250 if suit == "s" else 230
    body = embossed(suit, cx, cy, size, rim=8)
    # Gold inlay inside the suit, as on an ornamental ace.
    inlay_y = cy - (14 if suit in "sc" else 4)
    inlay = (
        star(cx, inlay_y, 46, 12, 4, "url(#gold)")
        + star(cx, inlay_y, 26, 8, 4, GOLD_LIGHT, rotation=45)
        if suit == "s" else ""
    )
    centre = gem(cx, inlay_y, 22 if suit != "s" else 12, PALETTES[suit]["gem"])
    return cartouche + body + inlay + centre


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


HAIR = {"K": "#d8d2c6", "Q": "#3a2215", "J": "#4c2c17"}


def court_half(rank: str, suit: str) -> str:
    """Upper half of a court figure in panel coordinates (0..PANEL_W, 0..HALF_H)."""
    palette = PALETTES[suit]
    cx = PANEL_W / 2
    hair = HAIR[rank]
    stroke = f'stroke="{INK}" stroke-width="2.5" stroke-linejoin="round"'
    line = f'fill="none" stroke="{INK}" stroke-linecap="round"'
    parts = []

    # Golden halo behind the head.
    parts.append(f'<circle cx="{cx}" cy="128" r="112" fill="{GOLD}" fill-opacity="0.16"/>')
    parts.append(f'<circle cx="{cx}" cy="128" r="112" fill="none" stroke="{GOLD}" stroke-opacity="0.45" stroke-width="2"/>')

    # The queen's long hair falls behind her shoulders.
    if rank == "Q":
        parts.append(
            f'<path d="M{cx - 58} 96 C{cx - 96} 150 {cx - 104} 230 {cx - 92} {HALF_H} L{cx + 92} {HALF_H} '
            f'C{cx + 104} 230 {cx + 96} 150 {cx + 58} 96 Z" fill="{hair}" {stroke}/>'
        )

    # Robe and shoulders.
    parts.append(
        f'<path d="M8 {HALF_H} L8 262 C8 228 56 206 118 198 L{PANEL_W - 118} 198 '
        f'C{PANEL_W - 56} 206 {PANEL_W - 8} 228 {PANEL_W - 8} 262 L{PANEL_W - 8} {HALF_H} Z" '
        f'fill="url(#robe)" {stroke}/>'
    )
    # Gold embroidery on the robe.
    for side in (-1, 1):
        x0 = cx + side * 150
        parts.append(
            f'<path d="M{x0:.0f} {HALF_H - 6} C{x0 - side * 6:.0f} 290 {x0 - side * 24:.0f} 262 {x0 - side * 56:.0f} 250 '
            f'M{x0 + side * 24:.0f} {HALF_H - 6} C{x0 + side * 20:.0f} 286 {x0 + side * 4:.0f} 256 {x0 - side * 26:.0f} 236" '
            f'fill="none" stroke="{GOLD}" stroke-width="3" stroke-linecap="round"/>'
        )
    # Sash.
    parts.append(
        f'<path d="M70 {HALF_H} L{PANEL_W - 128} 205 L{PANEL_W - 92} 214 L112 {HALF_H} Z" '
        f'fill="{palette["robe_dark"]}" {stroke}/>'
    )
    # Pauldrons.
    for x in (64, PANEL_W - 64):
        parts.append(f'<ellipse cx="{x}" cy="238" rx="50" ry="26" fill="url(#gold)" {stroke}/>')
        parts.append(f'<ellipse cx="{x}" cy="240" rx="34" ry="14" fill="{palette["robe"]}" stroke="{GOLD_DARK}" stroke-width="2"/>')
        parts.append(gem(x, 240, 8, palette["gem"]))
    # Central band.
    band_x, band_w = cx - 26, 52
    parts.append(f'<rect x="{band_x}" y="200" width="{band_w}" height="{HALF_H - 200}" fill="url(#gold)" {stroke}/>')
    parts.append(band_pattern(BAND_PATTERNS[suit], band_x + 4, 206, band_w - 8, HALF_H - 210, palette["robe_dark"]))

    # Collar: ermine for the king, jewelled gold for the others.
    if rank == "K":
        parts.append(
            f'<path d="M{cx - 108} 206 C{cx - 70} 244 {cx + 70} 244 {cx + 108} 206 '
            f'C{cx + 70} 180 {cx - 70} 180 {cx - 108} 206 Z" fill="#f1ebdd" {stroke}/>'
        )
        for i in range(9):
            x = cx - 84 + i * 21
            parts.append(f'<path d="M{x} {214 + (4 - abs(i - 4)) * 3} l-3 6 l3 -2 l3 2 Z" fill="{INK}"/>')
    else:
        parts.append(
            f'<path d="M{cx - 92} 202 C{cx - 60} 236 {cx + 60} 236 {cx + 92} 202 '
            f'C{cx + 60} 186 {cx - 60} 186 {cx - 92} 202 Z" fill="url(#gold)" {stroke}/>'
        )
        for i in range(7):
            x = cx - 66 + i * 22
            parts.append(f'<circle cx="{x}" cy="{210 + (3 - abs(i - 3)) * 3}" r="4.5" fill="{palette["gem"]}" '
                         f'stroke="{GOLD_DARK}" stroke-width="1.2"/>')

    # Neck and the hair behind the head.
    parts.append(f'<rect x="{cx - 16}" y="170" width="32" height="26" fill="url(#skin)" {stroke}/>')
    parts.append(
        f'<path d="M{cx - 50} 92 C{cx - 66} 130 {cx - 62} 170 {cx - 44} 190 L{cx + 44} 190 '
        f'C{cx + 62} 170 {cx + 66} 130 {cx + 50} 92 Z" fill="{hair}" {stroke}/>'
    )

    # Face.
    parts.append(f'<ellipse cx="{cx}" cy="138" rx="40" ry="48" fill="url(#skin)" {stroke}/>')
    for side in (-1, 1):
        parts.append(f'<ellipse cx="{cx + side * 22}" cy="152" rx="10" ry="6" fill="#e0866f" fill-opacity="0.35"/>')
        ex = cx + side * 14
        parts.append(f'<ellipse cx="{ex}" cy="133" rx="7" ry="4.2" fill="#fbf7ef" stroke="{INK}" stroke-width="1.4"/>')
        parts.append(f'<circle cx="{ex + side * 0.5}" cy="133" r="3" fill="#3a2a1a"/>')
        brow = "#8f8a80" if rank == "K" else hair
        parts.append(f'<path d="M{cx + side * 23} 124 C{cx + side * 17} 119 {cx + side * 10} 119 {cx + side * 5} 123" '
                     f'fill="none" stroke="{brow}" stroke-width="3.4" stroke-linecap="round"/>')
    parts.append(f'<path d="M{cx} 137 L{cx - 5} 152 L{cx + 2} 153" {line} stroke-width="2"/>')
    if rank == "K":
        # Full beard and moustache.
        parts.append(
            f'<path d="M{cx - 39} 146 C{cx - 40} 190 {cx - 18} 214 {cx} 218 C{cx + 18} 214 {cx + 40} 190 {cx + 39} 146 '
            f'C{cx + 26} 158 {cx - 26} 158 {cx - 39} 146 Z" fill="{hair}" {stroke}/>'
        )
        for x in (-22, -10, 2, 14):
            parts.append(f'<path d="M{cx + x} 172 C{cx + x - 2} 186 {cx + x + 2} 198 {cx + x + 4} 206" '
                         f'fill="none" stroke="#a49d90" stroke-width="1.6" stroke-linecap="round"/>')
        parts.append(f'<path d="M{cx - 24} 162 C{cx - 12} 154 {cx} 158 {cx} 158 C{cx} 158 {cx + 12} 154 {cx + 24} 162 '
                     f'C{cx + 12} 166 {cx} 162 {cx} 162 C{cx} 162 {cx - 12} 166 {cx - 24} 162 Z" fill="#bdb6a8" {stroke}/>')
    else:
        lips = "#b4363a" if rank == "Q" else "#9a4a3c"
        parts.append(f'<path d="M{cx - 9} 165 C{cx - 4} 170 {cx + 4} 170 {cx + 9} 165 C{cx + 4} 163 {cx - 4} 163 {cx - 9} 165 Z" '
                     f'fill="{lips}"/>')

    # Headwear.
    if rank == "K":
        parts.append(
            f'<path d="M{cx - 54} 96 L{cx - 60} 34 L{cx - 30} 62 L{cx} 18 L{cx + 30} 62 L{cx + 60} 34 L{cx + 54} 96 Z" '
            f'fill="url(#gold)" {stroke}/>'
        )
        parts.append(f'<rect x="{cx - 58}" y="80" width="116" height="22" rx="3" fill="#f1ebdd" {stroke}/>')
        for x in range(-48, 49, 16):
            parts.append(f'<path d="M{cx + x} 86 l-3 6 l3 -2 l3 2 Z" fill="{INK}"/>')
        for x, y in ((cx - 60, 34), (cx, 18), (cx + 60, 34)):
            parts.append(f'<circle cx="{x}" cy="{y}" r="7" fill="url(#gold)" {stroke}/>')
        parts.append(gem(cx, 56, 13, palette["gem"]))
        parts.append(gem(cx - 30, 72, 7, "#c0262e"))
        parts.append(gem(cx + 30, 72, 7, "#c0262e"))
    elif rank == "Q":
        parts.append(
            f'<path d="M{cx - 48} 98 L{cx - 50} 58 C{cx - 38} 74 {cx - 26} 74 {cx - 18} 50 '
            f'C{cx - 8} 72 {cx + 8} 72 {cx + 18} 50 C{cx + 26} 74 {cx + 38} 74 {cx + 50} 58 L{cx + 48} 98 Z" '
            f'fill="url(#gold)" {stroke}/>'
        )
        parts.append(f'<rect x="{cx - 50}" y="88" width="100" height="14" rx="3" fill="{GOLD_DARK}" {stroke}/>')
        for x in (cx - 18, cx + 18):
            parts.append(f'<circle cx="{x}" cy="46" r="6" fill="url(#gold)" {stroke}/>')
        parts.append(gem(cx, 74, 11, palette["gem"]))
        for x in (cx - 34, cx + 34):
            parts.append(f'<circle cx="{x}" cy="95" r="4" fill="#f7f1e3"/>')
    else:  # Jack: velvet cap with a gold band and a plume
        parts.append(
            f'<path d="M{cx - 62} 100 C{cx - 60} 58 {cx - 30} 44 {cx + 4} 44 C{cx + 40} 44 {cx + 60} 62 {cx + 62} 100 Z" '
            f'fill="{palette["robe_dark"]}" {stroke}/>'
        )
        parts.append(f'<rect x="{cx - 66}" y="88" width="132" height="16" rx="6" fill="url(#gold)" {stroke}/>')
        parts.append(gem(cx, 96, 8, palette["gem"]))
        parts.append(
            f'<path d="M{cx + 30} 54 C{cx + 70} 18 {cx + 112} 20 {cx + 130} 38 C{cx + 98} 36 {cx + 70} 50 {cx + 44} 72 Z" '
            f'fill="{palette["robe"]}" {stroke}/>'
        )
        parts.append(f'<path d="M{cx + 46} 60 C{cx + 76} 36 {cx + 100} 32 {cx + 122} 36" '
                     f'fill="none" stroke="{GOLD}" stroke-width="2" stroke-linecap="round"/>')

    # Held item: the king's sword, the queen's flower, the jack's halberd.
    if rank == "K":
        sx = 60
        parts.append(f'<path d="M{sx - 7} {HALF_H} L{sx - 7} 70 L{sx} 50 L{sx + 7} 70 L{sx + 7} {HALF_H} Z" fill="#e3e6ea" {stroke}/>')
        parts.append(f'<path d="M{sx} 60 L{sx} {HALF_H}" stroke="#a9afb7" stroke-width="2"/>')
        parts.append(f'<rect x="{sx - 26}" y="222" width="52" height="12" rx="5" fill="url(#gold)" {stroke}/>')
        parts.append(f'<rect x="{sx - 6}" y="234" width="12" height="40" fill="{GOLD_DARK}" {stroke}/>')
        parts.append(gem(sx, 228, 6, palette["gem"]))
    elif rank == "Q":
        fx, fy = PANEL_W - 64, 116
        parts.append(f'<path d="M{fx} {fy} L{fx - 4} 290" fill="none" stroke="#3f6b35" stroke-width="7" stroke-linecap="round"/>')
        parts.append(f'<path d="M{fx - 2} 200 C{fx + 20} 186 {fx + 30} 196 {fx + 26} 204 C{fx + 14} 208 {fx + 4} 206 {fx - 2} 200 Z" '
                     f'fill="#4f8a43" stroke="{INK}" stroke-width="1.5"/>')
        for i in range(6):
            a = i * math.pi / 3
            parts.append(
                f'<ellipse cx="{fx + 16 * math.cos(a):.1f}" cy="{fy + 16 * math.sin(a):.1f}" rx="12" ry="12" '
                f'fill="{suit_color(suit) if suit in "dh" else palette["robe"]}" stroke="{INK}" stroke-width="2"/>'
            )
        parts.append(f'<circle cx="{fx}" cy="{fy}" r="9" fill="url(#gold)" stroke="{INK}" stroke-width="2"/>')
    else:
        hx = PANEL_W - 58
        parts.append(f'<rect x="{hx - 5}" y="70" width="10" height="{HALF_H - 70}" fill="#6b4524" {stroke}/>')
        parts.append(
            f'<path d="M{hx} 24 L{hx + 14} 62 L{hx + 38} 72 L{hx + 14} 84 L{hx} 96 L{hx - 14} 84 L{hx - 38} 72 L{hx - 14} 62 Z" '
            f'fill="#e3e6ea" {stroke}/>'
        )
        parts.append(f'<circle cx="{hx}" cy="72" r="6" fill="url(#gold)" {stroke}/>')

    # Suit emblem in the panel corner.
    parts.append(suit_shape(suit, 40, 38, 40, rim=1.6))
    return "".join(parts)


def court(rank: str, suit: str) -> str:
    half = court_half(rank, suit)
    return (
        f'<rect x="{PANEL_X}" y="{PANEL_Y}" width="{PANEL_W}" height="{PANEL_H}" fill="url(#panel)"/>'
        f'<g transform="translate({PANEL_X} {PANEL_Y})">{half}</g>'
        f'<g transform="rotate(180 {W / 2} {H / 2}) translate({PANEL_X} {PANEL_Y})">{half}</g>'
        f'<path d="M{PANEL_X} {H / 2} L{W - PANEL_X} {H / 2}" stroke="{GOLD_DARK}" stroke-width="3"/>'
        f'<rect x="{PANEL_X}" y="{PANEL_Y}" width="{PANEL_W}" height="{PANEL_H}" fill="none" '
        f'stroke="url(#gold)" stroke-width="6"/>'
        f'<rect x="{PANEL_X + 9}" y="{PANEL_Y + 9}" width="{PANEL_W - 18}" height="{PANEL_H - 18}" fill="none" '
        f'stroke="{GOLD}" stroke-width="1.5"/>'
    )


def court_defs(suit: str) -> str:
    palette = PALETTES[suit]
    return (
        '<linearGradient id="robe" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{palette["robe"]}"/><stop offset="1" stop-color="{palette["robe_dark"]}"/>'
        "</linearGradient>"
        '<radialGradient id="panel" cx="0.5" cy="0.5" r="0.7">'
        '<stop offset="0" stop-color="#f6ebd2"/><stop offset="1" stop-color="#dec79a"/></radialGradient>'
    )


def card_svg(code: str) -> str:
    rank, suit = code[0], code[1]
    if rank in "JQK":
        return svg_open(court_defs(suit)) + paper(code) + court(rank, suit) + indices(rank, suit) + "</svg>\n"
    body = ace(suit) if rank == "A" else pips(rank, suit)
    return svg_open() + paper(code) + frame() + body + indices(rank, suit) + "</svg>\n"


# ----------------------------------------------------------------------- backs

def back_svg(style: str) -> str:
    """Dark lacquered back with gold filigree and a suit-neutral star emblem."""
    base, dark, glow = BACKS[style]
    inset = 22
    left, top, right, bottom = inset, inset, W - inset, H - inset
    cx, cy = W / 2, H / 2
    defs = (
        '<radialGradient id="lacquer" cx="0.5" cy="0.5" r="0.72">'
        f'<stop offset="0" stop-color="{glow}"/><stop offset="0.6" stop-color="{base}"/>'
        f'<stop offset="1" stop-color="{dark}"/></radialGradient>'
    )
    out = [svg_open(defs)]
    out.append(f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="{CORNER}" ry="{CORNER}" '
               f'fill="{dark}" stroke="#1a120a" stroke-width="3"/>')
    out.append(f'<rect x="{left}" y="{top}" width="{right - left}" height="{bottom - top}" rx="18" fill="url(#lacquer)"/>')

    # Faint filigree: rays and rings around the centre, kept inside the panel.
    rays = []
    for i in range(48):
        a = i * math.pi / 24
        x2, y2 = cx + 900 * math.cos(a), cy + 900 * math.sin(a)
        r0 = 236
        x1, y1 = cx + r0 * math.cos(a), cy + r0 * math.sin(a)
        # Shorten each ray to the panel border.
        t = min(
            ((right - 16 - x1) / (x2 - x1)) if x2 > x1 else ((left + 16 - x1) / (x2 - x1)) if x2 < x1 else 1,
            ((bottom - 16 - y1) / (y2 - y1)) if y2 > y1 else ((top + 16 - y1) / (y2 - y1)) if y2 < y1 else 1,
        )
        rays.append(f"M{x1:.1f} {y1:.1f} L{x1 + (x2 - x1) * t:.1f} {y1 + (y2 - y1) * t:.1f}")
    out.append(f'<path d="{" ".join(rays)}" stroke="{GOLD}" stroke-opacity="0.16" stroke-width="1.5" fill="none"/>')
    for r, opacity in ((262, 0.25), (282, 0.12)):
        out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{GOLD}" stroke-opacity="{opacity}" stroke-width="2"/>')

    # Gold borders and corner ornaments.
    out.append(f'<rect x="{left}" y="{top}" width="{right - left}" height="{bottom - top}" rx="18" fill="none" '
               f'stroke="url(#gold)" stroke-width="6"/>')
    out.append(f'<rect x="{left + 16}" y="{top + 16}" width="{right - left - 32}" height="{bottom - top - 32}" rx="10" '
               f'fill="none" stroke="{GOLD}" stroke-opacity="0.8" stroke-width="1.6"/>')
    for x, y, sx, sy in ((left + 26, top + 26, 1, 1), (right - 26, top + 26, -1, 1),
                         (left + 26, bottom - 26, 1, -1), (right - 26, bottom - 26, -1, -1)):
        out.append(scroll(x, y, sx * 1.5, sy * 1.5, width=1.8))
    for x, y in ((cx, top + 16), (cx, bottom - 16), (left + 16, cy), (right - 16, cy)):
        out.append(f'<path d="M{x} {y - 12} L{x + 10} {y} L{x} {y + 12} L{x - 10} {y} Z" fill="url(#gold)"/>')

    # Central medallion.
    out.append(f'<circle cx="{cx}" cy="{cy}" r="190" fill="{dark}" fill-opacity="0.55" stroke="url(#gold)" stroke-width="5"/>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="174" fill="none" stroke="{GOLD}" stroke-width="1.5"/>')
    for i in range(16):
        a = i * math.pi / 8
        x, y = cx + 190 * math.cos(a), cy + 190 * math.sin(a)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{7 if i % 2 == 0 else 4.5}" fill="url(#gold)"/>')
    for i in range(8):
        a = i * 45
        out.append(f'<path d="M{cx} {cy - 168} C{cx + 30} {cy - 120} {cx + 22} {cy - 84} {cx} {cy - 62} '
                   f'C{cx - 22} {cy - 84} {cx - 30} {cy - 120} {cx} {cy - 168} Z" transform="rotate({a} {cx} {cy})" '
                   f'fill="none" stroke="{GOLD}" stroke-opacity="0.75" stroke-width="2"/>')
    out.append(star(cx, cy, 150, 34, 8, GOLD, rotation=22.5).replace("/>", ' fill-opacity="0.25"/>'))
    out.append(star(cx, cy, 120, 26, 4, "url(#gold)"))
    out.append(star(cx, cy, 82, 20, 4, "url(#gold)", rotation=45))
    out.append(f'<circle cx="{cx}" cy="{cy}" r="34" fill="{dark}" stroke="url(#gold)" stroke-width="4"/>')
    out.append(gem(cx, cy, 20, glow))
    out.append("</svg>\n")
    return "".join(out)


def all_cards() -> dict[str, str]:
    """File name -> SVG text for the 52 faces and the card backs."""
    files = {f"{r}{s}.svg": card_svg(f"{r}{s}") for s in SUITS for r in RANKS}
    for style in BACKS:
        files[f"back_{style}.svg"] = back_svg(style)
    return files


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    output.mkdir(parents=True, exist_ok=True)
    files = all_cards()
    for name, text in files.items():
        (output / name).write_text(text, encoding="utf-8")
    # Remove artwork the generator no longer produces (e.g. the old single back).
    for stale in output.glob("*.svg"):
        if stale.name not in files:
            stale.unlink()
    print(f"Wrote {len(files)} files to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
