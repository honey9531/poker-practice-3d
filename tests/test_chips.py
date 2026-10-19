import random

import pytest

from bridge import ChipsBridge
from services.chips import (
    DEFAULT_DENOMINATIONS,
    ChipDenomination,
    breakdown,
    chip_label,
    validate_denominations,
)


def total(stacks):
    return sum(d.value * n for d, n in stacks)


@pytest.mark.parametrize(
    "amount, expected",
    [
        (0, []),
        (1, [(1, 1)]),
        (35, [(25, 1), (5, 2)]),
        (1275, [(1000, 1), (100, 2), (25, 3)]),
        (23480, [(5000, 4), (1000, 3), (100, 4), (25, 3), (5, 1)]),
    ],
)
def test_breakdown_examples(amount, expected):
    assert [(d.value, n) for d, n in breakdown(amount)] == expected


def test_breakdown_always_sums_to_amount():
    rng = random.Random(4)
    for _ in range(2000):
        amount = rng.randint(0, 1_000_000)
        stacks = breakdown(amount)
        assert total(stacks) == amount
        values = [d.value for d, _ in stacks]
        assert values == sorted(values, reverse=True)
        assert all(n > 0 for _, n in stacks)


def test_breakdown_rejects_negative_amounts():
    with pytest.raises(ValueError):
        breakdown(-1)


@pytest.mark.parametrize(
    "values",
    [[], [5, 25], [1, 5, 5], [1, 0]],
)
def test_invalid_denomination_sets(values):
    with pytest.raises(ValueError):
        validate_denominations([ChipDenomination(v, "#fff", "#000", "#000") for v in values])


@pytest.mark.parametrize(
    "value, label",
    [(1, "1"), (25, "25"), (500, "500"), (1000, "1K"), (2500, "2.5K"), (5000, "5K"), (1_000_000, "1M")],
)
def test_chip_labels(value, label):
    assert chip_label(value) == label


def test_default_denominations_have_distinct_colors():
    colors = [d.color for d in DEFAULT_DENOMINATIONS]
    assert len(set(colors)) == len(colors)


def test_bridge_exposes_denominations_and_breakdown(qapp):
    bridge = ChipsBridge()
    denominations = bridge.property("denominations")
    assert [d["value"] for d in denominations] == [1, 5, 25, 100, 500, 1000, 5000]
    stacks = bridge.breakdown(1275)
    assert [(s["value"], s["count"], s["label"]) for s in stacks] == [
        (1000, 1, "1K"), (100, 2, "100"), (25, 3, "25")
    ]
    assert bridge.breakdown(0) == []


def test_bridge_signals_scheme_changes(qapp, qtbot):
    bridge = ChipsBridge()
    custom = [ChipDenomination(1, "#ffffff", "#000000", "#000000"),
              ChipDenomination(10, "#123456", "#ffffff", "#ffffff")]
    with qtbot.waitSignal(bridge.denominationsChanged):
        bridge.set_denominations(custom)
    assert [s["value"] for s in bridge.breakdown(23)] == [10, 1]
