"""Player actions and the set of legal actions offered to the player to act."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"  # convenience request; recorded as the call/bet/raise it amounts to


@dataclass(frozen=True, slots=True)
class Action:
    """``amount`` is the *total* street commitment for BET/RAISE ("raise to").

    It is ignored for the other action types.
    """

    type: ActionType
    amount: int = 0

    @classmethod
    def fold(cls) -> "Action":
        return cls(ActionType.FOLD)

    @classmethod
    def check(cls) -> "Action":
        return cls(ActionType.CHECK)

    @classmethod
    def call(cls) -> "Action":
        return cls(ActionType.CALL)

    @classmethod
    def bet(cls, to: int) -> "Action":
        return cls(ActionType.BET, to)

    @classmethod
    def raise_to(cls, to: int) -> "Action":
        return cls(ActionType.RAISE, to)

    @classmethod
    def all_in(cls) -> "Action":
        return cls(ActionType.ALL_IN)


@dataclass(frozen=True, slots=True)
class LegalActions:
    """What the player to act may do.

    ``call_amount`` is the number of chips a call adds (already capped at the
    stack). ``min_to``/``max_to`` bound the total street commitment of a bet or
    raise (both 0 when neither is allowed); ``max_to`` is the all-in total.
    ``can_all_in`` is false when the whole stack would be an illegal raise
    (betting not reopened, or nobody left to raise against) and calling would
    not use the whole stack.
    """

    seat: int
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
    current_bet: int  # highest street commitment so far
    committed: int  # this player's street commitment

    @property
    def can_bet_or_raise(self) -> bool:
        return self.can_bet or self.can_raise

    def allows(self, action: Action) -> bool:
        match action.type:
            case ActionType.FOLD:
                return self.can_fold
            case ActionType.CHECK:
                return self.can_check
            case ActionType.CALL:
                return self.can_call
            case ActionType.BET:
                return self.can_bet and self.min_to <= action.amount <= self.max_to
            case ActionType.RAISE:
                return self.can_raise and self.min_to <= action.amount <= self.max_to
            case ActionType.ALL_IN:
                return self.can_all_in
        return False
