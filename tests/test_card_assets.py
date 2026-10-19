"""Generated card artwork: completeness, freshness and renderability."""

import sys
import xml.etree.ElementTree as ET

import pytest
from PySide6.QtSvg import QSvgRenderer

from poker import FULL_DECK
from services.paths import assets_dir

sys.path.insert(0, str(assets_dir().parent / "tools"))
import generate_cards  # noqa: E402

CARDS_DIR = assets_dir() / "cards"
EXPECTED = {f"{card.code}.svg" for card in FULL_DECK} | {"back.svg"}


def test_all_card_files_exist():
    assert {p.name for p in CARDS_DIR.glob("*.svg")} == EXPECTED


def test_committed_assets_match_generator():
    generated = generate_cards.all_cards()
    assert set(generated) == EXPECTED
    stale = [name for name, text in generated.items()
             if (CARDS_DIR / name).read_text(encoding="utf-8") != text]
    assert not stale, f"Run tools/generate_cards.py; stale: {stale[:5]}"


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_svg_is_valid_and_renderable(qapp, name):
    path = CARDS_DIR / name
    root = ET.parse(path).getroot()
    assert root.get("viewBox") == f"0 0 {generate_cards.W} {generate_cards.H}"
    renderer = QSvgRenderer(str(path))
    assert renderer.isValid()


def test_card_proportions_match_poker_size():
    assert generate_cards.W / generate_cards.H == pytest.approx(63 / 88)


def test_every_face_is_unique():
    texts = [(CARDS_DIR / name).read_text(encoding="utf-8") for name in EXPECTED]
    assert len(set(texts)) == len(texts)


@pytest.mark.parametrize("rank", list("23456789T"))
def test_pip_layout_has_one_pip_per_rank_value(rank):
    count = 10 if rank == "T" else int(rank)
    positions = generate_cards.pip_positions(rank)
    assert len(positions) == count
    assert len(set((x, y) for x, y, _ in positions)) == count  # no overlapping pips


@pytest.mark.parametrize("rank", list("234568 9T".replace(" ", "")))
def test_pip_layout_is_point_symmetric(rank):
    """Every pip has a partner rotated 180 degrees about the card centre.

    The seven is the traditional exception: its extra pip sits in the upper half.
    """
    positions = {(round(x, 3), round(y, 3)) for x, y, _ in generate_cards.pip_positions(rank)}
    cx, cy = generate_cards.W / 2, (generate_cards.PIP_TOP + generate_cards.PIP_BOTTOM) / 2
    assert {(round(2 * cx - x, 3), round(2 * cy - y, 3)) for x, y in positions} == positions


def test_seven_has_single_extra_pip_in_upper_half():
    centre = [(x, y) for x, y, _ in generate_cards.pip_positions("7") if x == generate_cards.PIP_COLUMNS["C"]]
    assert len(centre) == 1
    assert centre[0][1] < (generate_cards.PIP_TOP + generate_cards.PIP_BOTTOM) / 2


def test_suit_colours():
    assert generate_cards.suit_color("h") == generate_cards.suit_color("d") == generate_cards.RED
    assert generate_cards.suit_color("s") == generate_cards.suit_color("c") == generate_cards.BLACK
