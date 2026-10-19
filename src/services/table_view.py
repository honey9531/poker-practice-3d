"""Presentation snapshot of the table: exactly what the UI is allowed to show.

Snapshots are immutable and contain no hidden information: an opponent's hole
cards appear only once they are legitimately revealed. The bridge turns these
into Qt properties and models; QML never sees engine objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MAX_SEATS = 6

# Display slots around the table, clockwise from the human at the bottom:
# 0 bottom, 1 lower-left, 2 upper-left, 3 top, 4 upper-right, 5 lower-right.
_SLOT_PATTERNS: dict[int, tuple[int, ...]] = {
    2: (0, 3),
    3: (0, 2, 4),
    4: (0, 1, 3, 5),
    5: (0, 1, 2, 4, 5),
    6: (0, 1, 2, 3, 4, 5),
}


def display_slots(seats: list[int], human_seat: int) -> dict[int, int]:
    """Map table seats to display slots, the human at slot 0, keeping clockwise order."""
    if not 2 <= len(seats) <= MAX_SEATS:
        raise ValueError(f"Between 2 and {MAX_SEATS} seats are supported")
    if human_seat not in seats:
        raise ValueError("Human seat must be one of the seats")
    ordered = sorted(seats)
    start = ordered.index(human_seat)
    clockwise = ordered[start:] + ordered[:start]
    return dict(zip(clockwise, _SLOT_PATTERNS[len(seats)]))


@dataclass(frozen=True, slots=True)
class SeatView:
    seat: int
    slot: int
    name: str
    stack: int
    bet: int = 0  # chips committed on the current street
    cards: tuple[str, ...] = ()  # card codes; "" for a card shown face down
    in_hand: bool = True  # dealt into the current hand
    folded: bool = False
    all_in: bool = False
    busted: bool = False
    is_human: bool = False
    is_dealer: bool = False
    is_small_blind: bool = False
    is_big_blind: bool = False
    to_act: bool = False
    last_action: str = ""  # e.g. "Raise 120"
    is_winner: bool = False
    won_amount: int = 0
    hand_label: str = ""  # e.g. "Two pair, Kings and Nines" at showdown
    best_cards: tuple[str, ...] = ()  # cards forming the shown hand (for highlighting)
    style: str = ""  # opponent style label, e.g. "Aggressive"


@dataclass(frozen=True, slots=True)
class PotView:
    label: str  # "Main pot", "Side pot 1"
    amount: int
    eligible: tuple[str, ...]  # player names


@dataclass(frozen=True, slots=True)
class BetPreset:
    label: str
    amount: int  # raise-to total


@dataclass(frozen=True, slots=True)
class ActionView:
    """Legal actions for the human, mirrored from the engine."""

    step: int  # engine action counter; sent back to reject stale submissions
    can_fold: bool
    can_check: bool
    can_call: bool
    call_amount: int
    can_bet: bool
    can_raise: bool
    can_all_in: bool
    min_to: int
    max_to: int
    stack: int
    committed: int
    presets: tuple[BetPreset, ...] = ()


@dataclass(frozen=True, slots=True)
class AnalysisEntry:
    """One opponent decision, explained after the hand (never during it)."""

    name: str
    street: str
    action: str
    reason: str
    cards: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TableView:
    seats: tuple[SeatView, ...] = ()
    board: tuple[str, ...] = ()
    pots: tuple[PotView, ...] = ()
    total_pot: int = 0  # all chips committed this hand, including current bets
    street: str = ""  # "preflop", "flop", ... "showdown"; "" between hands
    hand_number: int = 0
    small_blind: int = 0
    big_blind: int = 0
    message: str = ""
    actions: ActionView | None = None  # set only when the human is to act
    hand_in_progress: bool = False
    session_active: bool = False
    can_deal: bool = False  # a new hand may be started now
    session_over: bool = False  # the human or every opponent is out of chips
    blind_interval: int = 0  # hands per blind level; 0 = blinds are fixed
    blind_level: int = 0  # 0-based level of the hand on the table
    hands_to_next_level: int = 0  # hands left at this level; 0 = blinds go up next hand
    winning_cards: tuple[str, ...] = field(default=())  # board cards to highlight
    analysis: tuple[AnalysisEntry, ...] = ()  # filled only once the hand is over
