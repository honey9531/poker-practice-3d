"""Heuristic opponents: conservative, balanced and aggressive styles at three difficulties.

One decision procedure, parameterised by a style profile (which hands to play,
how often to bet, bluff and raise, bet sizes) and a difficulty profile (how
accurately hands are evaluated and how much position and pot odds are used).
Every decision passes through :func:`legalize`, so only legal actions leave
this module.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from poker.actions import Action, ActionType, LegalActions
from poker.events import Street

from ai.base import DecisionContext
from ai.hand_strength import draws, equity, equity_vs_range, preflop_strength
from ai.tendencies import describe_range, estimated_range


@dataclass(frozen=True, slots=True)
class StyleProfile:
    name: str
    open_threshold: float  # pre-flop strength needed to enter an unraised pot
    raise_threshold: float  # pre-flop strength to open-raise / 3-bet
    call_margin: float  # extra equity required over pot odds to call (negative = looser)
    value_threshold: float  # post-flop equity to bet/raise for value
    raise_equity: float  # post-flop equity to raise a bet
    bluff_rate: float  # chance to bet with weak hands when checked to
    semi_bluff_rate: float  # chance to bet/raise with a draw
    bet_fraction: float  # typical post-flop bet as a fraction of the pot
    open_size_bb: float  # pre-flop open raise size in big blinds
    push_threshold: float  # pre-flop strength to shove when short-stacked
    steal_rate: float  # chance to raise a playable hand in late position when unraised


@dataclass(frozen=True, slots=True)
class DifficultyProfile:
    name: str
    noise: float  # random error added to strength/equity estimates
    evaluation_budget: int  # hand evaluations per post-flop decision
    uses_position: bool
    uses_pot_odds: bool
    mistake_rate: float  # chance of a passive, sub-optimal choice
    read_weight: float  # hands of evidence the prior range is worth (lower = adapts faster)


STYLES = {
    "conservative": StyleProfile(
        "Conservative", open_threshold=0.37, raise_threshold=0.47, call_margin=0.06,
        value_threshold=0.66, raise_equity=0.8, bluff_rate=0.02, semi_bluff_rate=0.1,
        bet_fraction=0.5, open_size_bb=2.5, push_threshold=0.55, steal_rate=0.05,
    ),
    "balanced": StyleProfile(
        "Balanced", open_threshold=0.29, raise_threshold=0.41, call_margin=0.0,
        value_threshold=0.6, raise_equity=0.74, bluff_rate=0.07, semi_bluff_rate=0.35,
        bet_fraction=0.62, open_size_bb=2.75, push_threshold=0.45, steal_rate=0.3,
    ),
    "aggressive": StyleProfile(
        "Aggressive", open_threshold=0.22, raise_threshold=0.32, call_margin=-0.03,
        value_threshold=0.54, raise_equity=0.66, bluff_rate=0.16, semi_bluff_rate=0.6,
        bet_fraction=0.75, open_size_bb=3.0, push_threshold=0.36, steal_rate=0.55,
    ),
}

DIFFICULTIES = {
    "easy": DifficultyProfile("Easy", noise=0.12, evaluation_budget=240, uses_position=False,
                              uses_pot_odds=False, mistake_rate=0.12, read_weight=12),
    "normal": DifficultyProfile("Normal", noise=0.05, evaluation_budget=480, uses_position=True,
                                uses_pot_odds=True, mistake_rate=0.04, read_weight=6),
    "hard": DifficultyProfile("Hard", noise=0.02, evaluation_budget=800, uses_position=True,
                              uses_pot_odds=True, mistake_rate=0.0, read_weight=4),
}

SHORT_STACK_BB = 12
# A pre-flop raise is "big" (worth estimating the raiser's range) at this size or above.
BIG_RAISE_BB = 12
BIG_CALL_SHARE = 0.2  # ... or when calling costs this share of the stack


@dataclass(frozen=True, slots=True)
class Decision:
    action: Action
    reason: str


def legalize(action: Action, legal: LegalActions) -> Action:
    """Map any intended action onto the closest legal one."""
    kind = action.type
    if kind is ActionType.ALL_IN:
        return action if legal.can_all_in else legalize(Action.call(), legal)
    if kind in (ActionType.BET, ActionType.RAISE):
        if legal.can_bet or legal.can_raise:
            amount = max(legal.min_to, min(legal.max_to, action.amount))
            return Action(ActionType.BET if legal.can_bet else ActionType.RAISE, amount)
        kind = ActionType.CALL
    if kind is ActionType.CALL:
        if legal.can_call:
            return Action.call()
        return Action.check()
    if kind is ActionType.CHECK:
        return Action.check() if legal.can_check else Action.fold()
    # Never fold when checking is free.
    return Action.check() if legal.can_check else Action.fold()


class HeuristicStrategy:
    def __init__(self, style: StyleProfile, difficulty: DifficultyProfile, rng: random.Random) -> None:
        self.style = style
        self.difficulty = difficulty
        self.rng = rng
        self.name = style.name
        self.last_reason = ""

    def decide(self, ctx: DecisionContext) -> Action:
        decision = self.decide_with_reason(ctx)
        self.last_reason = decision.reason
        return decision.action

    def decide_with_reason(self, ctx: DecisionContext) -> Decision:
        if ctx.street is Street.PREFLOP:
            decision = self._preflop(ctx)
        else:
            decision = self._postflop(ctx)
        return Decision(legalize(decision.action, ctx.legal), decision.reason)

    # ---------------------------------------------------------------- helpers

    def _noisy(self, value: float) -> float:
        return max(0.0, min(1.0, value + self.rng.uniform(-self.difficulty.noise, self.difficulty.noise)))

    def _position_bonus(self, ctx: DecisionContext) -> float:
        if not self.difficulty.uses_position or ctx.players_in_hand <= 1:
            return 0.0
        # Later position (acting after more players) is worth a little.
        late = ctx.position / max(1, ctx.players_in_hand - 1)
        return 0.06 * (late - 0.5)

    def _raise_to(self, ctx: DecisionContext, fraction: float) -> int:
        legal = ctx.legal
        pot_after_call = ctx.pot + legal.call_amount
        return legal.current_bet + int(round(pot_after_call * fraction))

    def _mistake(self) -> bool:
        return self.rng.random() < self.difficulty.mistake_rate

    # ---------------------------------------------------------------- pre-flop

    def _preflop(self, ctx: DecisionContext) -> Decision:
        style, legal, bb = self.style, ctx.legal, ctx.big_blind
        strength = self._noisy(preflop_strength(ctx.hole)) + self._position_bonus(ctx)
        # Tighten up against more opponents.
        strength -= 0.012 * max(0, ctx.opponents_in_hand - 1)
        facing = legal.current_bet / bb if bb else 1.0  # size of the bet faced, in big blinds
        label = f"pre-flop strength {strength:.2f}"

        if ctx.effective_stack <= SHORT_STACK_BB * bb:
            if strength >= style.push_threshold:
                return Decision(Action.all_in(), f"short-stacked push ({label})")
            if legal.can_check:
                return Decision(Action.check(), f"short-stacked, free check ({label})")
            if legal.call_amount <= bb and strength >= style.push_threshold - 0.12:
                return Decision(Action.call(), f"short-stacked cheap call ({label})")
            return Decision(Action.fold(), f"short-stacked fold ({label})")

        unraised = facing <= 1.0
        if unraised:
            if strength >= style.raise_threshold and not self._mistake():
                limpers = sum(1 for a in ctx.history if a.action == "call")
                size = (style.open_size_bb + limpers) * bb
                return Decision(Action.raise_to(int(size)), f"open-raise ({label})")
            late = ctx.players_in_hand > 1 and ctx.position >= (ctx.players_in_hand - 1) * 0.6
            if (strength >= style.open_threshold and late and self.difficulty.uses_position
                    and self.rng.random() < style.steal_rate):
                limpers = sum(1 for a in ctx.history if a.action == "call")
                size = (style.open_size_bb + limpers) * bb
                return Decision(Action.raise_to(int(size)), f"late-position raise ({label})")
            if strength >= style.open_threshold:
                return Decision(Action.call() if legal.can_call else Action.check(), f"limp/check ({label})")
            return Decision(Action.check() if legal.can_check else Action.fold(), f"weak hand ({label})")

        aggressor = ctx.last_aggressor
        big = facing >= BIG_RAISE_BB or legal.call_amount >= BIG_CALL_SHARE * legal.stack
        if aggressor is not None and big:
            return self._facing_big_raise(ctx, aggressor)

        # Facing a raise: required strength grows with the raise size.
        pressure = 0.07 * math.log2(max(1.0, facing / 2.5)) if facing > 2.5 else 0.0
        reraise = style.raise_threshold + 0.18 + pressure
        call = style.open_threshold + 0.08 + pressure
        if self.difficulty.uses_pot_odds:
            call -= 0.25 * (0.35 - ctx.pot_odds)  # cheaper calls need less
        if strength >= reraise and not self._mistake():
            return Decision(Action.raise_to(int(legal.current_bet * 3)), f"re-raise ({label})")
        if strength >= call:
            return Decision(Action.call(), f"call raise to {legal.current_bet} ({label})")
        return Decision(Action.fold(), f"fold to raise to {legal.current_bet} ({label})")

    def _facing_big_raise(self, ctx: DecisionContext, aggressor) -> Decision:
        """Call or re-shove against a large raise using the raiser's likely range.

        The range comes from the raiser's public habits this session: an unknown
        player shoving deep is assumed to be strong, but someone who shoves
        every hand is soon called with medium-strong hands.
        """
        style, legal = self.style, ctx.legal
        width = estimated_range(ctx.tendencies.get(aggressor.seat), all_in=aggressor.all_in,
                                prior_weight=self.difficulty.read_weight)
        samples = max(60, self.difficulty.evaluation_budget // 2)
        eq = self._noisy(equity_vs_range(ctx.hole, ctx.board, width, samples, self.rng))
        # Players still in the hand besides the raiser could also hold strong cards.
        needed = ctx.pot_odds + style.call_margin + 0.03 * max(0, ctx.opponents_in_hand - 1)
        label = (f"equity {eq:.0%} against an estimated {describe_range(width)}, "
                 f"pot odds {ctx.pot_odds:.0%}")
        if legal.can_raise and eq >= max(0.6, needed + 0.15) and not self._mistake():
            return Decision(Action.all_in(), f"re-raise all-in: {label}")
        if eq >= needed:
            return Decision(Action.call(), f"call big raise: {label}")
        return Decision(Action.fold(), f"fold to big raise: {label}")

    # ---------------------------------------------------------------- post-flop

    def _equity(self, ctx: DecisionContext) -> float:
        opponents = max(1, ctx.opponents_in_hand)
        samples = max(40, self.difficulty.evaluation_budget // (opponents + 1))
        return self._noisy(equity(ctx.hole, ctx.board, opponents, samples, self.rng))

    def _postflop(self, ctx: DecisionContext) -> Decision:
        style, legal = self.style, ctx.legal
        eq = self._equity(ctx)
        draw = draws(ctx.hole, ctx.board)
        label = f"equity {eq:.0%}"
        if draw.any:
            label += f", {draw.outs}-out draw"

        if legal.can_check:
            if eq >= style.value_threshold and not self._mistake():
                fraction = style.bet_fraction * (1.2 if eq > 0.85 else 1.0)
                return Decision(Action.bet(self._raise_to(ctx, fraction)), f"value bet ({label})")
            if draw.any and ctx.street is not Street.RIVER and self.rng.random() < style.semi_bluff_rate:
                return Decision(Action.bet(self._raise_to(ctx, style.bet_fraction)), f"semi-bluff ({label})")
            bluff_chance = style.bluff_rate * (1.5 if ctx.opponents_in_hand == 1 else 0.6)
            if self.rng.random() < bluff_chance:
                return Decision(Action.bet(self._raise_to(ctx, style.bet_fraction)), f"bluff ({label})")
            return Decision(Action.check(), f"check ({label})")

        # Facing a bet.
        needed = ctx.pot_odds + style.call_margin if self.difficulty.uses_pot_odds else 0.45 + style.call_margin
        if draw.any and ctx.street is not Street.RIVER:
            # Implied odds: a made draw usually wins more later.
            needed -= 0.06
        if eq >= style.raise_equity and legal.can_raise and not self._mistake():
            return Decision(Action.raise_to(self._raise_to(ctx, 0.9)), f"raise for value ({label})")
        if (draw.any and ctx.street is Street.FLOP and legal.can_raise
                and self.rng.random() < style.semi_bluff_rate * 0.3):
            return Decision(Action.raise_to(self._raise_to(ctx, 0.9)), f"semi-bluff raise ({label})")
        if eq >= needed:
            return Decision(Action.call(), f"call: {label} vs pot odds {ctx.pot_odds:.0%}")
        return Decision(Action.fold(), f"fold: {label} vs pot odds {ctx.pot_odds:.0%}")


def create_strategy(style: str, difficulty: str, rng: random.Random) -> HeuristicStrategy:
    try:
        return HeuristicStrategy(STYLES[style], DIFFICULTIES[difficulty], rng)
    except KeyError as exc:
        raise ValueError(f"Unknown style or difficulty: {exc}") from None
