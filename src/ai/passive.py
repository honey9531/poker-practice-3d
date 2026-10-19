"""A calling station: checks when it can, otherwise calls. Never bets or folds.

Useful as a predictable baseline opponent and in tests.
"""

from __future__ import annotations

from poker.actions import Action

from ai.base import DecisionContext


class PassiveStrategy:
    name = "Passive"

    def decide(self, ctx: DecisionContext) -> Action:
        if ctx.legal.can_check:
            return Action.check()
        return Action.call()
