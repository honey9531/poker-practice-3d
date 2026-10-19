"""Computer opponents. Strategies only ever see a DecisionContext (no hidden cards)."""

from ai import tendencies
from ai.base import DecisionContext, PublicAction, Strategy, observe
from ai.passive import PassiveStrategy
from ai.strategies import (
    DIFFICULTIES,
    STYLES,
    Decision,
    HeuristicStrategy,
    create_strategy,
    legalize,
)

__all__ = [
    "DecisionContext", "PublicAction", "Strategy", "observe", "PassiveStrategy",
    "DIFFICULTIES", "STYLES", "Decision", "HeuristicStrategy", "create_strategy", "legalize",
    "tendencies",
]
