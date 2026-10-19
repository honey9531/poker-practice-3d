"""GameController + GameBridge driving real hands through the Qt event loop."""

import pytest

from bridge import GameBridge
from services.game_controller import INSTANT, GameController, Timing
from services.game_session import SessionConfig


@pytest.fixture
def wired(qapp):
    bridge = GameBridge()
    controller = GameController(bridge.set_view, timing=INSTANT)
    bridge.attach(controller)
    return bridge, controller


def wait_for_human_or_hand_end(qtbot, bridge, controller):
    qtbot.waitUntil(
        lambda: bridge.property("humanToAct") or (controller.session.hand_over and not controller.busy),
        timeout=5000,
    )


def test_start_session_from_qml_options(wired, qtbot):
    bridge, controller = wired
    ok = bridge.startSession({"opponents": 2, "startingStack": 1000, "smallBlind": 5,
                              "bigBlind": 10, "opponentStyle": "balanced", "difficulty": "easy"})
    assert ok
    wait_for_human_or_hand_end(qtbot, bridge, controller)
    assert bridge.property("handNumber") == 1
    assert bridge.property("players").rowCount() == 3
    assert bridge.property("sessionActive")


def test_invalid_options_report_error(wired, qtbot):
    bridge, _ = wired
    with qtbot.waitSignal(bridge.errorOccurred):
        assert bridge.startSession({"opponents": 9}) is False


def test_play_many_hands_through_bridge(wired, qtbot):
    bridge, controller = wired
    controller.start_session(SessionConfig(opponents=3, seed=13))
    hands = 0
    while hands < 15 and not bridge.property("sessionOver"):
        wait_for_human_or_hand_end(qtbot, bridge, controller)
        if bridge.property("humanToAct"):
            actions = bridge.property("actions")
            kind = "check" if actions["canCheck"] else "call"
            assert bridge.submitAction(kind, 0, actions["step"])
            continue
        hands += 1
        total = sum(controller.session.build_view().seats[i].stack for i in range(4))
        assert total == 4 * 2000
        assert bridge.property("canDeal") or bridge.property("sessionOver")
        if bridge.property("canDeal"):
            assert bridge.deal()
    assert hands >= 5


def test_stale_submission_is_rejected_and_reported(wired, qtbot):
    bridge, controller = wired
    controller.start_session(SessionConfig(opponents=1, seed=3))
    wait_for_human_or_hand_end(qtbot, bridge, controller)
    while not bridge.property("humanToAct"):
        bridge.deal()
        wait_for_human_or_hand_end(qtbot, bridge, controller)
    step = bridge.property("actions")["step"]
    with qtbot.waitSignal(bridge.errorOccurred):
        assert bridge.submitAction("call", 0, step + 5) is False
    assert bridge.property("humanToAct")  # state unchanged


def test_paced_presentation_does_not_block(wired, qtbot):
    bridge, controller = wired
    controller.timing = Timing(scale=0.05)
    controller.start_session(SessionConfig(opponents=2, seed=1))
    # Returns immediately; events are revealed later by the timer.
    assert controller.busy
    wait_for_human_or_hand_end(qtbot, bridge, controller)


def test_new_session_cancels_pending_callbacks(wired, qtbot):
    bridge, controller = wired
    controller.timing = Timing(scale=0.2)
    controller.start_session(SessionConfig(opponents=5, seed=1))
    controller.start_session(SessionConfig(opponents=1, seed=2))
    wait_for_human_or_hand_end(qtbot, bridge, controller)
    assert bridge.property("players").rowCount() == 2
    assert bridge.property("handNumber") == 1


def test_end_session_clears_table(wired, qtbot):
    bridge, controller = wired
    controller.start_session(SessionConfig(opponents=1, seed=2))
    wait_for_human_or_hand_end(qtbot, bridge, controller)
    bridge.endSession()
    assert not bridge.property("sessionActive")
    assert bridge.property("players").rowCount() == 0
