"""State machine for a single hand of no-limit Texas Hold'em.

Rules implemented (documented in docs/ARCHITECTURE.md):

* Heads-up the button posts the small blind and acts first pre-flop.
* A player who cannot cover a blind posts what they have and is all-in; the
  amount to call stays the full big blind.
* The minimum bet is the big blind. A raise must increase the current bet by
  at least the largest bet/raise increment of the street. A smaller all-in
  raise does not reopen the betting for players who already acted, unless
  such raises add up to a full raise since they last acted.
* Uncalled chips are returned at the end of every street.
* When at most one player can still bet, live hands are exposed and the
  remaining board is dealt out without further action.
* Odd chips from split pots go to the winners closest to the button's left.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from poker.actions import Action, ActionType, LegalActions
from poker.cards import Card
from poker.deck import Deck
from poker.evaluator import HandValue, best_five
from poker.events import (
    BlindKind,
    BlindPosted,
    BoardDealt,
    CardsExposed,
    HandEnded,
    HandEvent,
    HandStarted,
    HoleCardsDealt,
    PlayerActed,
    PotAwarded,
    ShowdownRevealed,
    Street,
    UncalledBetReturned,
)
from poker.pots import Pot, PotAward, award_pots, build_pots


class HandError(Exception):
    """Base class for rule violations."""


class IllegalActionError(HandError):
    pass


class StaleActionError(HandError):
    """An action was submitted for a decision point that has already passed."""


class HandStateError(HandError):
    pass


@dataclass(frozen=True, slots=True)
class SeatSpec:
    seat: int
    name: str
    stack: int


@dataclass(slots=True)
class PlayerState:
    seat: int
    name: str
    starting_stack: int
    stack: int
    hole: tuple[Card, ...] = ()
    folded: bool = False
    street_bet: int = 0  # chips committed on the current street
    total_bet: int = 0  # chips committed during the whole hand
    acted: bool = False  # has acted since the last bet/raise this street
    acted_at_level: int | None = None  # current bet when the player last acted this street

    @property
    def all_in(self) -> bool:
        return not self.folded and self.stack == 0

    @property
    def can_act(self) -> bool:
        return not self.folded and self.stack > 0


@dataclass(frozen=True, slots=True)
class HandResult:
    went_to_showdown: bool
    board: tuple[Card, ...]
    awards: tuple[PotAward, ...]
    showdown_values: Mapping[int, HandValue]
    final_stacks: Mapping[int, int]
    net: Mapping[int, int]

    @property
    def winners(self) -> frozenset[int]:
        return frozenset(seat for award in self.awards for seat in award.winners)


_NEXT_STREET = {Street.PREFLOP: Street.FLOP, Street.FLOP: Street.TURN, Street.TURN: Street.RIVER}
_BOARD_COUNT = {Street.FLOP: 3, Street.TURN: 1, Street.RIVER: 1}


class HoldemHand:
    """One hand from blinds to pot distribution.

    Construction posts the blinds and deals hole cards. Drive the hand with
    :meth:`act` for the seat in :attr:`to_act` until :attr:`is_complete`.
    """

    def __init__(
        self,
        seats: Sequence[SeatSpec],
        button: int,
        small_blind: int,
        big_blind: int,
        *,
        deck: Deck | None = None,
        rng: random.Random | None = None,
    ) -> None:
        if len(seats) < 2:
            raise HandStateError("A hand needs at least two players")
        if len({s.seat for s in seats}) != len(seats):
            raise HandStateError("Duplicate seat numbers")
        if any(s.stack <= 0 for s in seats):
            raise HandStateError("Every player must have chips")
        if not 0 < small_blind <= big_blind:
            raise HandStateError("Blinds must satisfy 0 < small blind <= big blind")
        if button not in {s.seat for s in seats}:
            raise HandStateError("Button must be on an occupied seat")

        self.players: list[PlayerState] = [
            PlayerState(s.seat, s.name, s.stack, s.stack) for s in sorted(seats, key=lambda s: s.seat)
        ]
        self._by_seat = {p.seat: p for p in self.players}
        self.button = button
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.deck = deck if deck is not None else Deck(rng)
        self.board: list[Card] = []
        self.burned: list[Card] = []
        self.street = Street.PREFLOP
        self.current_bet = 0
        self.min_raise = big_blind  # size of the largest bet/raise increment this street
        self.to_act: int | None = None
        self.action_count = 0  # increments on every accepted action
        self.events: list[HandEvent] = []
        self.result: HandResult | None = None
        self._exposed = False
        self._initial_chips = sum(s.stack for s in seats)
        self._start()

    # ------------------------------------------------------------------ queries

    @property
    def is_complete(self) -> bool:
        return self.result is not None

    def player(self, seat: int) -> PlayerState:
        return self._by_seat[seat]

    @property
    def live_players(self) -> list[PlayerState]:
        return [p for p in self.players if not p.folded]

    @property
    def total_pot(self) -> int:
        """All chips committed this hand, including the current street's bets."""
        return 0 if self.is_complete else sum(p.total_bet for p in self.players)

    def collected_pots(self) -> list[Pot]:
        """Pots from completed streets (current street bets excluded)."""
        if self.is_complete:
            return []
        contributions = {p.seat: p.total_bet - p.street_bet for p in self.players}
        return build_pots(contributions, {p.seat for p in self.live_players})

    def total_chips(self) -> int:
        """Stacks plus chips in the pot; constant for the whole hand."""
        return sum(p.stack for p in self.players) + self.total_pot

    def seats_clockwise_from(self, seat: int) -> list[PlayerState]:
        """Players clockwise starting with the one after ``seat`` (``seat`` last)."""
        seats = [p.seat for p in self.players]
        if seat in self._by_seat:
            start = seats.index(seat) + 1
        else:
            start = next((i for i, s in enumerate(seats) if s > seat), 0)
        return self.players[start:] + self.players[:start]

    def legal_actions(self) -> LegalActions:
        if self.to_act is None:
            raise HandStateError("No player is to act")
        p = self._by_seat[self.to_act]
        to_call = max(0, self.current_bet - p.street_bet)
        call_amount = min(to_call, p.stack)
        max_to = p.street_bet + p.stack
        others_can_act = any(q.can_act for q in self.players if q is not p)
        reopened = (
            p.acted_at_level is None or self.current_bet - p.acted_at_level >= self.min_raise
        )
        can_bet = self.current_bet == 0 and p.stack > 0 and others_can_act
        can_raise = (
            self.current_bet > 0 and p.stack > to_call and others_can_act and reopened
        )
        if can_bet:
            min_to = min(self.big_blind, max_to)
        elif can_raise:
            min_to = min(self.current_bet + self.min_raise, max_to)
        else:
            min_to = 0
        return LegalActions(
            seat=p.seat,
            can_fold=True,
            can_check=to_call == 0,
            can_call=to_call > 0,
            call_amount=call_amount,
            can_bet=can_bet,
            can_raise=can_raise,
            can_all_in=can_bet or can_raise or (to_call > 0 and call_amount == p.stack),
            min_to=min_to,
            max_to=max_to if (can_bet or can_raise) else 0,
            stack=p.stack,
            current_bet=self.current_bet,
            committed=p.street_bet,
        )

    # ------------------------------------------------------------------ actions

    def act(self, seat: int, action: Action, expected_action_count: int | None = None) -> None:
        """Apply ``action`` for ``seat``.

        ``expected_action_count`` (the :attr:`action_count` the caller saw when
        deciding) rejects duplicate or out-of-date submissions.
        """
        if self.is_complete:
            raise HandStateError("The hand is complete")
        if expected_action_count is not None and expected_action_count != self.action_count:
            raise StaleActionError(
                f"Action prepared at step {expected_action_count}, hand is at {self.action_count}"
            )
        if seat != self.to_act:
            raise IllegalActionError(f"Seat {seat} is not to act (seat {self.to_act} is)")

        legal = self.legal_actions()
        action = self._resolve_all_in(action, legal)
        if not legal.allows(action):
            raise IllegalActionError(f"Illegal action {action} for seat {seat}: {legal}")

        p = self._by_seat[seat]
        match action.type:
            case ActionType.FOLD:
                p.folded = True
                added = 0
            case ActionType.CHECK:
                added = 0
            case ActionType.CALL:
                added = legal.call_amount
            case ActionType.BET | ActionType.RAISE:
                added = action.amount - p.street_bet
            case _:
                raise AssertionError(action)

        self._commit(p, added)
        full_raise = False
        if action.type in (ActionType.BET, ActionType.RAISE):
            increment = action.amount - self.current_bet
            if increment >= self.min_raise:
                full_raise = True
                self.min_raise = increment
            self.current_bet = action.amount
            for other in self.players:
                if other is not p:
                    other.acted = False
        p.acted = True
        p.acted_at_level = self.current_bet
        self.action_count += 1
        self.events.append(
            PlayerActed(
                seat=seat,
                street=self.street,
                action=action.type,
                added=added,
                street_total=p.street_bet,
                stack_after=p.stack,
                all_in=p.all_in,
                full_raise=full_raise,
            )
        )

        if len(self.live_players) == 1:
            self._finish_uncontested()
        else:
            self._advance(after=seat)

    def _resolve_all_in(self, action: Action, legal: LegalActions) -> Action:
        if action.type is not ActionType.ALL_IN:
            return action
        if legal.can_call and legal.call_amount == legal.stack:
            return Action.call()
        if legal.can_bet:
            return Action.bet(legal.max_to)
        if legal.can_raise:
            return Action.raise_to(legal.max_to)
        raise IllegalActionError(f"Seat {legal.seat} cannot go all-in now")

    # ------------------------------------------------------------------ flow

    def _start(self) -> None:
        if len(self.players) == 2:
            sb_seat = self.button
            bb_seat = self.seats_clockwise_from(self.button)[0].seat
        else:
            sb_seat = self.seats_clockwise_from(self.button)[0].seat
            bb_seat = self.seats_clockwise_from(sb_seat)[0].seat
        self.events.append(
            HandStarted(
                button=self.button,
                small_blind_seat=sb_seat,
                big_blind_seat=bb_seat,
                small_blind=self.small_blind,
                big_blind=self.big_blind,
                stacks={p.seat: p.stack for p in self.players},
                names={p.seat: p.name for p in self.players},
            )
        )
        self._post_blind(sb_seat, BlindKind.SMALL, self.small_blind)
        self._post_blind(bb_seat, BlindKind.BIG, self.big_blind)
        self.current_bet = self.big_blind

        order = self.seats_clockwise_from(self.button)
        first = {p.seat: self.deck.deal_one() for p in order}
        for p in order:
            p.hole = (first[p.seat], self.deck.deal_one())
        for p in order:
            self.events.append(HoleCardsDealt(p.seat, p.hole))  # type: ignore[arg-type]

        self._advance(after=bb_seat)

    def _post_blind(self, seat: int, kind: BlindKind, amount: int) -> None:
        p = self._by_seat[seat]
        posted = min(amount, p.stack)
        self._commit(p, posted)
        self.events.append(BlindPosted(seat, kind, posted, p.all_in))

    def _commit(self, p: PlayerState, amount: int) -> None:
        if amount < 0 or amount > p.stack:
            raise HandStateError(f"Invalid commitment of {amount} from stack {p.stack}")
        p.stack -= amount
        p.street_bet += amount
        p.total_bet += amount

    def _needs_action(self, p: PlayerState) -> bool:
        return p.can_act and (not p.acted or p.street_bet < self.current_bet)

    def _street_complete(self) -> bool:
        actors = [p for p in self.players if p.can_act]
        if len(actors) <= 1:
            # Nobody left to bet against: only a lone player facing a bet must act.
            return all(p.street_bet >= self.current_bet for p in actors)
        return not any(self._needs_action(p) for p in actors)

    def _advance(self, after: int) -> None:
        """Find the next player to act, or close the street."""
        while True:
            if not self._street_complete():
                self.to_act = next(
                    p.seat for p in self.seats_clockwise_from(after) if self._needs_action(p)
                )
                return
            self.to_act = None
            self._return_uncalled()
            if self.street is Street.RIVER:
                self._showdown()
                return
            betting_possible = sum(p.can_act for p in self.players) >= 2
            if not betting_possible:
                self._expose_live_hands()
            self._deal_street(_NEXT_STREET[self.street])
            if betting_possible:
                after = self.button
            # Otherwise loop: the street is immediately complete and the
            # board runs out to showdown.

    def _expose_live_hands(self) -> None:
        """Turn live hands face up once no more betting can happen (all-in run-out)."""
        if self._exposed:
            return
        self._exposed = True
        for p in self.seats_clockwise_from(self.button):
            if not p.folded:
                self.events.append(CardsExposed(p.seat, p.hole))  # type: ignore[arg-type]

    def _deal_street(self, street: Street) -> None:
        self.burned.append(self.deck.deal_one())
        cards = self.deck.deal(_BOARD_COUNT[street])
        self.board.extend(cards)
        self.street = street
        self.current_bet = 0
        self.min_raise = self.big_blind
        for p in self.players:
            p.street_bet = 0
            p.acted = False
            p.acted_at_level = None
        self.events.append(BoardDealt(street, tuple(cards)))

    def _return_uncalled(self) -> None:
        ranked = sorted(self.players, key=lambda p: p.street_bet, reverse=True)
        top, second = ranked[0], ranked[1]
        excess = top.street_bet - second.street_bet
        if excess > 0:
            top.stack += excess
            top.street_bet -= excess
            top.total_bet -= excess
            self.events.append(UncalledBetReturned(top.seat, excess))

    def _odd_chip_order(self) -> list[int]:
        return [p.seat for p in self.seats_clockwise_from(self.button)]

    def _showdown(self) -> None:
        self.street = Street.SHOWDOWN
        values: dict[int, HandValue] = {}
        for p in self.seats_clockwise_from(self.button):
            if p.folded:
                continue
            value, five = best_five([*p.hole, *self.board])
            values[p.seat] = value
            self.events.append(ShowdownRevealed(p.seat, p.hole, value, five))  # type: ignore[arg-type]
        self._distribute(values, went_to_showdown=True)

    def _finish_uncontested(self) -> None:
        self.to_act = None
        self._return_uncalled()
        self._distribute({}, went_to_showdown=False)

    def _distribute(self, values: dict[int, HandValue], went_to_showdown: bool) -> None:
        pots = build_pots(
            {p.seat: p.total_bet for p in self.players}, {p.seat for p in self.live_players}
        )
        awards = award_pots(pots, values, self._odd_chip_order())
        for award in awards:
            for seat, chips in award.shares.items():
                self._by_seat[seat].stack += chips
            self.events.append(
                PotAwarded(award.pot_index, award.amount, award.winners, award.shares, award.value)
            )
        final = {p.seat: p.stack for p in self.players}
        net = {p.seat: p.stack - p.starting_stack for p in self.players}
        if sum(final.values()) != self._initial_chips:
            raise AssertionError("Chip conservation violated")
        self.result = HandResult(
            went_to_showdown=went_to_showdown,
            board=tuple(self.board),
            awards=tuple(awards),
            showdown_values=values,
            final_stacks=final,
            net=net,
        )
        self.events.append(HandEnded(went_to_showdown, final, net))
