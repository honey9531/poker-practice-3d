"""What opponents can learn about each other from public play.

Only actions everyone at the table sees are counted (no hole cards), the way
real players notice that someone raises or shoves a lot. Estimates start from
a cautious prior and move towards the observed frequency as hands accumulate.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass, replace

from poker.actions import ActionType
from poker.events import HandEvent, HandStarted, PlayerActed, Street

# An unknown player who shoves deep pre-flop is assumed to hold roughly the top 6 % of hands
# (about tens or better and ace-king); a big non-all-in raise about the top 12 %.
PRIOR_SHOVE_RANGE = 0.06
PRIOR_RAISE_RANGE = 0.12
MIN_RANGE = 0.03


@dataclass(frozen=True, slots=True)
class Tendency:
    hands: int = 0  # hands dealt in
    preflop_raises: int = 0  # hands with a pre-flop bet/raise (all-ins included)
    preflop_all_ins: int = 0  # hands with a pre-flop all-in bet/raise


def update(tendencies: MutableMapping[int, Tendency], events: Sequence[HandEvent]) -> None:
    """Add one completed hand's public actions to ``tendencies``."""
    started = next((e for e in events if isinstance(e, HandStarted)), None)
    if started is None:
        return
    raised: set[int] = set()
    shoved: set[int] = set()
    for event in events:
        if isinstance(event, PlayerActed) and event.street is Street.PREFLOP:
            if event.action in (ActionType.BET, ActionType.RAISE):
                raised.add(event.seat)
                if event.all_in:
                    shoved.add(event.seat)
    for seat in started.stacks:
        t = tendencies.get(seat, Tendency())
        tendencies[seat] = replace(
            t,
            hands=t.hands + 1,
            preflop_raises=t.preflop_raises + (seat in raised),
            preflop_all_ins=t.preflop_all_ins + (seat in shoved),
        )


def estimated_range(tendency: Tendency | None, *, all_in: bool, prior_weight: float) -> float:
    """Fraction of starting hands (strongest first) the aggressor is likely to hold.

    ``prior_weight`` is how many hands of evidence the prior is worth: smaller
    values adapt faster to what the player has actually been doing.
    """
    t = tendency or Tendency()
    prior = PRIOR_SHOVE_RANGE if all_in else PRIOR_RAISE_RANGE
    observed = t.preflop_all_ins if all_in else t.preflop_raises
    estimate = (observed + prior * prior_weight) / (t.hands + prior_weight)
    return max(MIN_RANGE, min(1.0, estimate))


def describe_range(fraction: float) -> str:
    return f"top {round(fraction * 100)}% of hands"


Tendencies = Mapping[int, Tendency]
