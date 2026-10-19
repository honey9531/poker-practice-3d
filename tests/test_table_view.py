import pytest

from bridge import GameBridge, PlayerListModel
from bridge.game_bridge import actions_to_qml
from services.preview import preview_table
from services.table_view import SeatView, display_slots


@pytest.mark.parametrize(
    "seats, human, expected",
    [
        ([0, 1], 0, {0: 0, 1: 3}),
        ([0, 1, 2], 1, {1: 0, 2: 2, 0: 4}),
        ([0, 1, 2, 3], 0, {0: 0, 1: 1, 2: 3, 3: 5}),
        ([0, 1, 2, 3, 4], 2, {2: 0, 3: 1, 4: 2, 0: 4, 1: 5}),
        ([0, 1, 2, 3, 4, 5], 0, {i: i for i in range(6)}),
    ],
)
def test_display_slots_put_human_at_bottom_in_clockwise_order(seats, human, expected):
    assert display_slots(seats, human) == expected


def test_display_slots_preserve_clockwise_order_for_any_human_seat():
    for n in range(2, 7):
        seats = list(range(n))
        for human in seats:
            slots = display_slots(seats, human)
            assert slots[human] == 0
            order = sorted(seats, key=lambda s: (s - human) % n)
            assert [slots[s] for s in order] == sorted(slots.values())


@pytest.mark.parametrize("seats, human", [([0], 0), (list(range(7)), 0), ([0, 1], 5)])
def test_display_slots_reject_invalid_input(seats, human):
    with pytest.raises(ValueError):
        display_slots(seats, human)


def test_preview_hides_opponent_cards_until_showdown():
    live = preview_table(6)
    for seat in live.seats:
        if seat.is_human:
            assert all(seat.cards)
        else:
            assert all(code == "" for code in seat.cards)
    showdown = preview_table(6, showdown=True)
    assert any(all(s.cards) for s in showdown.seats if not s.is_human)


# --- PlayerListModel ----------------------------------------------------------

def seat(i, **changes):
    base = dict(seat=i, slot=i, name=f"P{i}", stack=1000, cards=("", ""))
    base.update(changes)
    return SeatView(**base)


def role(model, name):
    return next(r for r, n in model.roleNames().items() if bytes(n).decode() == name)


def test_model_exposes_camel_case_roles(qapp):
    model = PlayerListModel()
    model.set_seats([seat(0, is_human=True, last_action="Call 20")])
    names = {bytes(n).decode() for n in model.roleNames().values()}
    assert {"name", "stack", "cards", "isHuman", "lastAction", "bestCards", "toAct"} <= names
    index = model.index(0)
    assert model.data(index, role(model, "isHuman")) is True
    assert model.data(index, role(model, "lastAction")) == "Call 20"
    assert model.data(index, role(model, "cards")) == ["", ""]


def test_model_updates_rows_in_place(qapp, qtbot):
    model = PlayerListModel()
    model.set_seats([seat(0), seat(1)])
    resets = []
    changes = []
    model.modelReset.connect(lambda: resets.append(True))
    model.dataChanged.connect(lambda tl, br, roles: changes.append((tl.row(), sorted(roles))))

    model.set_seats([seat(0), seat(1, stack=900, bet=100)])
    assert not resets
    assert changes == [(1, sorted([role(model, "stack"), role(model, "bet")]))]

    changes.clear()
    model.set_seats([seat(0), seat(1, stack=900, bet=100)])  # identical
    assert not changes


def test_model_resets_when_seats_change(qapp):
    model = PlayerListModel()
    model.set_seats([seat(0), seat(1)])
    resets = []
    model.modelReset.connect(lambda: resets.append(True))
    model.set_seats([seat(0), seat(1), seat(2)])
    assert resets and model.rowCount() == 3


# --- GameBridge ---------------------------------------------------------------

def test_bridge_publishes_view(qapp, qtbot):
    bridge = GameBridge()
    view = preview_table(6)
    with qtbot.waitSignal(bridge.viewChanged):
        bridge.set_view(view)
    assert bridge.property("board") == list(view.board)
    assert bridge.property("totalPot") == view.total_pot
    assert bridge.property("handNumber") == 42
    assert bridge.property("humanToAct") is True
    assert [p["label"] for p in bridge.property("pots")] == ["Main pot", "Side pot 1"]
    model = bridge.property("players")
    assert model.rowCount() == 6
    # Rows are ordered by display slot.
    assert [model.seat(r).slot for r in range(6)] == list(range(6))


def test_actions_map_is_empty_when_human_not_to_act():
    assert actions_to_qml(None) == {}
    showdown = preview_table(6, showdown=True)
    assert showdown.actions is None


def test_actions_map_mirrors_legal_actions():
    actions = actions_to_qml(preview_table(6).actions)
    assert actions["step"] == 7
    assert actions["callAmount"] == 360
    assert (actions["minTo"], actions["maxTo"]) == (840, 1960)
    assert actions["canRaise"] and not actions["canBet"] and not actions["canCheck"]
    assert [p["label"] for p in actions["presets"]][0] == "Min"
