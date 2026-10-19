"""Drives a GameSession at a human pace without blocking the Qt event loop.

All waiting is done with a single-shot QTimer: engine events are revealed one
at a time with short pauses, and opponents "think" before acting. A
generation counter makes callbacks from an abandoned session harmless.
"""

from __future__ import annotations

import logging
import random
from collections.abc import Callable
from dataclasses import dataclass, replace

from PySide6.QtCore import QObject, QTimer, Signal

from poker import HandError
from poker.events import (
    BlindPosted,
    BoardDealt,
    CardsExposed,
    HandEvent,
    HoleCardsDealt,
    PlayerActed,
    PotAwarded,
    ShowdownRevealed,
    UncalledBetReturned,
)
from services.game_session import (
    GameSession,
    SessionConfig,
    SessionError,
    StrategyFactory,
    heuristic_factory,
)
from services.table_view import TableView

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Timing:
    """Pauses in milliseconds. ``scale`` multiplies all of them (0 = instant)."""

    blind: int = 180
    hole_card: int = 110  # roughly matches the QML deal animation
    action: int = 250
    board: int = 650
    uncalled: int = 250
    exposed: int = 450
    showdown: int = 600
    award: int = 1100
    think_min: int = 450
    think_max: int = 1100
    scale: float = 1.0

    def after(self, event: HandEvent) -> int:
        match event:
            case BlindPosted():
                base = self.blind
            case HoleCardsDealt():
                base = self.hole_card
            case PlayerActed():
                base = self.action
            case BoardDealt():
                base = self.board
            case UncalledBetReturned():
                base = self.uncalled
            case CardsExposed():
                base = self.exposed
            case ShowdownRevealed():
                base = self.showdown
            case PotAwarded():
                base = self.award
            case _:
                base = 0
        return int(base * self.scale)

    def think(self, rng: random.Random) -> int:
        return int(rng.randint(self.think_min, self.think_max) * self.scale)


INSTANT = Timing(scale=0.0)
# Without animations events still arrive in order, just with short pauses.
REDUCED_MOTION_SCALE = 0.3


class GameController(QObject):
    viewChanged = Signal()
    errorOccurred = Signal(str)
    handCompleted = Signal()

    def __init__(
        self,
        publish: Callable[[TableView], None],
        *,
        timing: Timing = Timing(),
        strategy_factory: StrategyFactory = heuristic_factory,
        recorder=None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.recorder = recorder  # HistoryRecorder or None
        self._publish_view = publish
        self.timing = timing
        self.strategy_factory = strategy_factory
        self.session: GameSession | None = None
        self.auto_next_hand_ms: int | None = None  # None: wait for the player
        self._generation = 0
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timer)
        self._pending: Callable[[], None] | None = None
        self._rng = random.Random()

    # ---------------------------------------------------------------- commands

    def start_session(self, config: SessionConfig) -> None:
        self._generation += 1
        self._timer.stop()
        self.session = GameSession(config, strategy_factory=self.strategy_factory)
        if self.recorder is not None:
            self.recorder.session_started(self.session)
        self._rng = random.Random(config.seed)
        log.info("Session started: %s", config)
        self.deal()

    def restart_session(self) -> None:
        """Start a fresh session with the same settings (new cards)."""
        if self.session is not None:
            self.start_session(replace(self.session.config, seed=None))

    def set_animations_enabled(self, enabled: bool) -> None:
        if self.timing.scale > 0:
            self.timing = replace(self.timing, scale=1.0 if enabled else REDUCED_MOTION_SCALE)

    def end_session(self) -> None:
        self._generation += 1
        self._timer.stop()
        if self.recorder is not None:
            self.recorder.session_ended()
        self.session = None
        self._publish_view(TableView())

    def deal(self) -> bool:
        """Start the next hand if allowed."""
        session = self.session
        if session is None or not session.can_start_hand:
            return False
        self._timer.stop()
        session.start_hand()
        self._pump()
        return True

    def submit_action(self, kind: str, amount: int, step: int) -> bool:
        session = self.session
        if session is None:
            return False
        try:
            session.apply_human_action(kind, amount, step)
        except (HandError, SessionError) as exc:
            # Stale or duplicate clicks end up here; the view is republished
            # so the controls reflect the real state again.
            log.warning("Rejected action %s %s at step %s: %s", kind, amount, step, exc)
            self.errorOccurred.emit(str(exc))
            self._publish()
            return False
        self._pump()
        return True

    def finish_presentation(self) -> None:
        """Skip remaining pauses (used when animations are turned off mid-hand)."""
        if self.session is not None:
            self._timer.stop()
            self._pump(instant=True)

    # ---------------------------------------------------------------- pacing

    def _schedule(self, delay_ms: int, callback: Callable[[], None]) -> None:
        generation = self._generation

        def guarded() -> None:
            if generation == self._generation:
                callback()

        self._pending = guarded
        self._timer.start(max(0, delay_ms))

    def _on_timer(self) -> None:
        pending, self._pending = self._pending, None
        if pending is not None:
            pending()

    def _pump(self, instant: bool = False) -> None:
        """Advance presentation until something needs to wait."""
        session = self.session
        if session is None:
            return
        while True:
            event = session.next_event()
            if event is None:
                break
            delay = 0 if instant else self.timing.after(event)
            if delay > 0:
                self._publish()
                self._schedule(delay, self._pump)
                return
        self._publish()

        if session.opponent_to_act is not None:
            self._schedule(0 if instant else self.timing.think(self._rng), self._opponent_turn)
        elif session.hand_over:
            self.handCompleted.emit()
            if self.auto_next_hand_ms is not None and session.can_start_hand:
                self._schedule(self.auto_next_hand_ms, self.deal)

    def _opponent_turn(self) -> None:
        session = self.session
        if session is None or session.opponent_to_act is None:
            return
        try:
            session.play_opponent_action()
        except (HandError, SessionError) as exc:  # a strategy bug must not stall the table
            log.exception("Opponent action failed")
            self.errorOccurred.emit(f"Opponent error: {exc}")
            return
        self._pump()

    def _publish(self) -> None:
        if self.session is not None:
            self._publish_view(self.session.build_view())
            self.viewChanged.emit()

    # ---------------------------------------------------------------- queries

    @property
    def busy(self) -> bool:
        """True while events are being revealed or an opponent is thinking."""
        return self._timer.isActive()
