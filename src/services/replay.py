"""Step through a stored hand without touching the live game or the database.

Replays rebuild the table from the recorded events with the same presenter
and view builder as the live game. They are read-only by construction: a
:class:`ReplaySession` only holds decoded events.
"""

from __future__ import annotations

from poker.events import (
    BlindPosted,
    CardsExposed,
    HandEnded,
    HandStarted,
    HoleCardsDealt,
    ShowdownRevealed,
)
from services.hand_presenter import HandPresenter
from services.history import HandRecord
from services.table_view import TableView, display_slots
from services.view_builder import (
    RosterSeat,
    pot_views,
    result_message,
    seat_views,
    winning_board_cards,
)


def _group(event) -> str | None:
    """Consecutive events of the same group are shown as one replay step."""
    if isinstance(event, (HandStarted, BlindPosted, HoleCardsDealt)):
        return "setup"
    if isinstance(event, CardsExposed):
        return "exposed"
    if isinstance(event, ShowdownRevealed):
        return "showdown"
    return None  # every other event is its own step


def checkpoints(events) -> list[int]:
    """Event counts at which a replay pauses (one step per meaningful change)."""
    points = []
    for index, event in enumerate(events):
        following = events[index + 1] if index + 1 < len(events) else None
        if following is not None:
            if isinstance(following, HandEnded):
                continue  # the end of the hand merges into the last visible change
            group = _group(event)
            if group is not None and _group(following) == group:
                continue
        points.append(index + 1)
    return points


class ReplaySession:
    def __init__(self, record: HandRecord, *, reveal_all: bool = False) -> None:
        self.record = record
        self.events = list(record.events)
        self.reveal_all = reveal_all
        self.points = checkpoints(self.events)
        self.position = 0  # index into points
        humans = [p.seat for p in record.players if p.is_human]
        self.human_seat = humans[0] if humans else record.players[0].seat
        self.slots = display_slots([p.seat for p in record.players], self.human_seat)
        self.roster = [RosterSeat(p.seat, p.name, p.starting_stack, p.style) for p in record.players]

    @property
    def steps(self) -> int:
        return len(self.points)

    @property
    def at_end(self) -> bool:
        return self.position >= self.steps - 1

    def seek(self, position: int) -> None:
        self.position = max(0, min(self.steps - 1, position))

    def step(self, delta: int) -> None:
        self.seek(self.position + delta)

    def build_view(self) -> TableView:
        count = self.points[self.position]
        presenter = HandPresenter.from_events(self.events[:count])
        names = {p.seat: p.name for p in self.record.players}
        summary = self.record.summary
        message = result_message(presenter) if presenter.awards else (
            f"Replay · step {self.position + 1} of {self.steps}"
        )
        return TableView(
            seats=seat_views(presenter, self.roster, self.slots, self.human_seat, None,
                             reveal_all=self.reveal_all),
            board=tuple(c.code for c in presenter.board),
            pots=pot_views(presenter, names),
            total_pot=presenter.total_pot(),
            street=presenter.street.value if presenter.street else "",
            hand_number=summary.hand_number,
            small_blind=summary.small_blind,
            big_blind=summary.big_blind,
            message=message,
            actions=None,
            hand_in_progress=not presenter.complete,
            session_active=True,
            winning_cards=winning_board_cards(presenter),
        )
