"""The table state exposed to QML as the ``Game`` singleton."""

from __future__ import annotations

from dataclasses import asdict

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlNamedElement, QmlSingleton, QQmlEngine

from bridge.player_model import PlayerListModel
from bridge.registry import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME, singleton_instance
from services import blinds
from services.game_session import SessionConfig, SessionError
from services.table_view import ActionView, TableView

__all__ = ["GameBridge", "QML_IMPORT_NAME", "QML_IMPORT_MAJOR_VERSION"]


def actions_to_qml(actions: ActionView | None, hand_number: int = 0) -> dict:
    """Legal actions as a QML map; empty when the human is not to act.

    ``key`` identifies the decision point across hands (the engine's step
    counter restarts every hand).
    """
    if actions is None:
        return {}
    data = asdict(actions)
    data["presets"] = [{"label": p.label, "amount": p.amount} for p in actions.presets]
    return {
        "key": f"{hand_number}:{data['step']}",
        "step": data["step"],
        "canFold": data["can_fold"],
        "canCheck": data["can_check"],
        "canCall": data["can_call"],
        "callAmount": data["call_amount"],
        "canBet": data["can_bet"],
        "canRaise": data["can_raise"],
        "canAllIn": data["can_all_in"],
        "minTo": data["min_to"],
        "maxTo": data["max_to"],
        "stack": data["stack"],
        "committed": data["committed"],
        "presets": data["presets"],
    }


@QmlNamedElement("Game")
@QmlSingleton
class GameBridge(QObject):
    """Publishes :class:`TableView` snapshots and forwards player commands to
    the game controller. Holds no poker rules."""

    viewChanged = Signal()
    errorOccurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._players = PlayerListModel(self)
        self._view = TableView()
        self._actions: dict = {}
        self._controller = None

    def attach(self, controller) -> None:
        """Connect the GameController that executes commands."""
        self._controller = controller
        controller.errorOccurred.connect(self.errorOccurred)

    # ---------------------------------------------------------------- commands

    @Slot("QVariantMap", result=bool)
    def startSession(self, options: dict) -> bool:
        try:
            config = SessionConfig(
                opponents=int(options.get("opponents", 3)),
                starting_stack=int(options.get("startingStack", 2000)),
                small_blind=int(options.get("smallBlind", 10)),
                big_blind=int(options.get("bigBlind", 20)),
                opponent_style=str(options.get("opponentStyle", "mixed")),
                difficulty=str(options.get("difficulty", "normal")),
                blind_increase_every=int(options.get("blindIncreaseEvery", 0)),
            )
            config.validate()
        except (SessionError, ValueError, TypeError) as exc:
            self.errorOccurred.emit(str(exc))
            return False
        self._controller.start_session(config)
        return True

    @Slot(str, int, int, result=bool)
    def submitAction(self, kind: str, amount: int, step: int) -> bool:
        return self._controller.submit_action(kind, amount, step)

    @Slot(result=bool)
    def deal(self) -> bool:
        return self._controller.deal()

    @Slot(int, int, int, result="QStringList")
    def blindPreview(self, small_blind: int, big_blind: int, levels: int) -> list[str]:
        """The first ``levels`` blind levels, e.g. ["10/20", "20/40", ...]."""
        return [f"{sb:,}/{bb:,}" for sb, bb in (blinds.blinds_at(level, small_blind, big_blind)
                                               for level in range(max(0, levels)))]

    @Slot()
    def restartSession(self) -> None:
        self._controller.restart_session()

    @Slot()
    def endSession(self) -> None:
        self._controller.end_session()

    # ---------------------------------------------------------------- state

    @staticmethod
    def create(engine: QQmlEngine) -> "GameBridge":
        return singleton_instance(GameBridge)

    @property
    def view(self) -> TableView:
        return self._view

    def set_view(self, view: TableView) -> None:
        """Publish a new snapshot (rows update in place)."""
        self._view = view
        self._actions = actions_to_qml(view.actions, view.hand_number)
        self._players.set_seats(sorted(view.seats, key=lambda s: s.slot))
        self.viewChanged.emit()

    @Property(QObject, constant=True)
    def players(self) -> PlayerListModel:
        return self._players

    @Property("QStringList", notify=viewChanged)
    def board(self) -> list[str]:
        return list(self._view.board)

    @Property("QStringList", notify=viewChanged)
    def winningCards(self) -> list[str]:
        return list(self._view.winning_cards)

    @Property("QVariantList", notify=viewChanged)
    def pots(self) -> list[dict]:
        return [
            {"label": p.label, "amount": p.amount, "eligible": list(p.eligible)}
            for p in self._view.pots
        ]

    @Property(int, notify=viewChanged)
    def totalPot(self) -> int:
        return self._view.total_pot

    @Property(str, notify=viewChanged)
    def street(self) -> str:
        return self._view.street

    @Property(int, notify=viewChanged)
    def handNumber(self) -> int:
        return self._view.hand_number

    @Property(int, notify=viewChanged)
    def smallBlind(self) -> int:
        return self._view.small_blind

    @Property(int, notify=viewChanged)
    def bigBlind(self) -> int:
        return self._view.big_blind

    @Property(str, notify=viewChanged)
    def message(self) -> str:
        return self._view.message

    @Property("QVariantMap", notify=viewChanged)
    def actions(self) -> dict:
        return self._actions

    @Property(bool, notify=viewChanged)
    def humanToAct(self) -> bool:
        return self._view.actions is not None

    @Property(bool, notify=viewChanged)
    def handInProgress(self) -> bool:
        return self._view.hand_in_progress

    @Property(bool, notify=viewChanged)
    def sessionActive(self) -> bool:
        return self._view.session_active

    @Property("QVariantList", notify=viewChanged)
    def analysis(self) -> list[dict]:
        return [
            {"name": a.name, "street": a.street, "action": a.action, "reason": a.reason, "cards": list(a.cards)}
            for a in self._view.analysis
        ]

    @Property(bool, notify=viewChanged)
    def canDeal(self) -> bool:
        return self._view.can_deal

    @Property(bool, notify=viewChanged)
    def sessionOver(self) -> bool:
        return self._view.session_over

    @Property(int, notify=viewChanged)
    def blindInterval(self) -> int:
        """Hands per blind level; 0 when blinds are fixed."""
        return self._view.blind_interval

    @Property(int, notify=viewChanged)
    def blindLevel(self) -> int:
        return self._view.blind_level

    @Property(int, notify=viewChanged)
    def handsToNextLevel(self) -> int:
        """Hands left at this level; 0 means the blinds go up next hand."""
        return self._view.hands_to_next_level
