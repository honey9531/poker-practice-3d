"""Builders for deterministic hands in tests."""

from __future__ import annotations

from poker import FULL_DECK, Deck, HoldemHand, SeatSpec, parse_cards
from poker.cards import Card


def stacked_deck(
    button: int, seats: list[int], holes: dict[int, str], board: str = ""
) -> Deck:
    """Deck that deals ``holes`` (seat -> "AsKd") and then ``board`` (up to 5 cards).

    Dealing order mirrors a real table: one card at a time clockwise from the
    seat left of the button, then burn-and-turn for each street.
    """
    seats = sorted(seats)
    start = next((i for i, s in enumerate(seats) if s > button), 0)
    order = seats[start:] + seats[:start]
    hole_cards = {seat: parse_cards(text) for seat, text in holes.items()}
    board_cards = parse_cards(board)
    used = {c for cards in hole_cards.values() for c in cards} | set(board_cards)
    spare = iter(c for c in FULL_DECK if c not in used)

    top: list[Card] = []
    for index in range(2):
        for seat in order:
            top.append(hole_cards[seat][index] if seat in hole_cards else next(spare))
    for street_cards in (board_cards[:3], board_cards[3:4], board_cards[4:5]):
        if not street_cards:
            break
        top.append(next(spare))  # burn
        top.extend(street_cards)
    return Deck.stacked(top)


def make_hand(
    stacks: list[int] | dict[int, int],
    *,
    button: int = 0,
    sb: int = 5,
    bb: int = 10,
    holes: dict[int, str] | None = None,
    board: str = "",
) -> HoldemHand:
    if isinstance(stacks, list):
        stacks = dict(enumerate(stacks))
    deck = stacked_deck(button, list(stacks), holes or {}, board)
    seats = [SeatSpec(seat, f"P{seat}", stack) for seat, stack in stacks.items()]
    return HoldemHand(seats, button, sb, bb, deck=deck)
