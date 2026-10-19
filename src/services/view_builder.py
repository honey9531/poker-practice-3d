"""Turn a HandPresenter into table view pieces.

Shared by the live game and by hand-history replay, so both render a hand
identically. Visibility rules live here: opponents' hole cards are only
included once revealed, unless ``reveal_all`` is set (replays of finished hands).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from services.hand_presenter import HandPresenter
from services.table_view import PotView, SeatView
from services.wording import says


@dataclass(frozen=True, slots=True)
class RosterSeat:
    """A seat at the table, independent of whether it is dealt into the hand."""

    seat: int
    name: str
    stack: int  # stack between hands (used for players not dealt in)
    style: str = ""  # opponent style label, "" for the human


def seat_views(
    presenter: HandPresenter,
    roster: Sequence[RosterSeat],
    slots: Mapping[int, int],
    human_seat: int,
    to_act: int | None,
    *,
    reveal_all: bool = False,
) -> tuple[SeatView, ...]:
    p = presenter
    winners = p.winners
    views = []
    for entry in roster:
        seat = entry.seat
        presented = p.seats.get(seat)
        human = seat == human_seat
        if presented is None:
            views.append(
                SeatView(
                    seat=seat, slot=slots[seat], name=entry.name, stack=entry.stack,
                    in_hand=False, busted=entry.stack == 0, is_human=human, style=entry.style,
                )
            )
            continue
        if presented.folded and not reveal_all:
            cards: tuple[str, ...] = ()
        elif human or presented.revealed or reveal_all:
            cards = tuple(c.code for c in presented.hole)
        else:
            cards = ("",) * len(presented.hole)
        views.append(
            SeatView(
                seat=seat,
                slot=slots[seat],
                name=presented.name,
                stack=presented.stack,
                bet=presented.street_bet,
                cards=cards,
                folded=presented.folded,
                all_in=presented.all_in and not p.complete,
                busted=p.complete and presented.stack == 0,
                is_human=human,
                is_dealer=seat == p.button,
                is_small_blind=seat == p.small_blind_seat,
                is_big_blind=seat == p.big_blind_seat,
                to_act=to_act == seat,
                last_action=presented.last_action,
                is_winner=seat in winners,
                won_amount=presented.won,
                hand_label=presented.hand_label if presented.revealed else "",
                best_cards=tuple(c.code for c in presented.best_cards) if seat in winners else (),
                style=entry.style,
            )
        )
    return tuple(views)


def pot_views(presenter: HandPresenter, names: Mapping[int, str]) -> tuple[PotView, ...]:
    return tuple(
        PotView(
            "Main pot" if i == 0 else f"Side pot {i}",
            pot.amount,
            tuple(names[s] for s in sorted(pot.eligible)),
        )
        for i, pot in enumerate(presenter.pots())
    )


def winning_board_cards(presenter: HandPresenter) -> tuple[str, ...]:
    board = {c.code for c in presenter.board}
    return tuple(sorted(c.code for c in presenter.winning_cards() if c.code in board))


def result_message(presenter: HandPresenter) -> str:
    """'Avery wins 1,200 with Two pair, ...' / 'Split pot: ...' once pots are awarded."""
    p = presenter
    if not p.awards:
        return ""
    names = {seat: s.name for seat, s in p.seats.items()}
    main = p.awards[0]
    if len(main.winners) > 1:
        text = "Split pot: " + " and ".join(names[s] for s in main.winners)
    else:
        winner = main.winners[0]
        text = says(names[winner], "wins") + f" {p.seats[winner].won:,}"
    if main.hand_label:
        text += f" with {main.hand_label}"
    side_winners = [s for a in p.awards[1:] for s in a.winners if s not in main.winners]
    for seat in dict.fromkeys(side_winners):
        text += "; " + says(names[seat], "wins") + " a side pot"
    return text
