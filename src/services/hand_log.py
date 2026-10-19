"""Readable, chronological description of a hand for the history viewer."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from poker.actions import ActionType
from poker.events import (
    BlindKind,
    BlindPosted,
    BoardDealt,
    CardsExposed,
    HandEvent,
    HandStarted,
    PlayerActed,
    PotAwarded,
    ShowdownRevealed,
    Street,
    UncalledBetReturned,
)
from services.wording import says, verb_for


@dataclass(frozen=True, slots=True)
class LogLine:
    street: str  # "preflop", "flop", "turn", "river", "showdown"
    text: str


def _cards(cards) -> str:
    return " ".join(c.code for c in cards)


def describe_events(events: Sequence[HandEvent]) -> list[LogLine]:
    names: dict[int, str] = {}
    street = Street.PREFLOP.value
    lines: list[LogLine] = []
    for event in events:
        match event:
            case HandStarted():
                names = dict(event.names)
                lines.append(LogLine(street, says(names[event.button], "has") + " the button; blinds "
                                             f"{event.small_blind:,}/{event.big_blind:,}"))
            case BlindPosted():
                kind = "small" if event.kind is BlindKind.SMALL else "big"
                suffix = f" and {verb_for(names[event.seat], 'is')} all-in" if event.all_in else ""
                lines.append(LogLine(street, says(names[event.seat], "posts") + f" the {kind} blind {event.amount:,}{suffix}"))
            case PlayerActed():
                who = names[event.seat]
                match event.action:
                    case ActionType.FOLD:
                        text = says(who, "folds")
                    case ActionType.CHECK:
                        text = says(who, "checks")
                    case ActionType.CALL:
                        text = says(who, "calls") + f" {event.added:,}"
                    case ActionType.BET:
                        text = says(who, "bets") + f" {event.street_total:,}"
                    case _:
                        text = says(who, "raises") + f" to {event.street_total:,}"
                if event.all_in:
                    text += " (all-in)"
                lines.append(LogLine(street, text))
            case BoardDealt():
                street = event.street.value
                lines.append(LogLine(street, f"{event.street.value.capitalize()}: {_cards(event.cards)}"))
            case CardsExposed():
                lines.append(LogLine(street, says(names[event.seat], "shows") + f" {_cards(event.cards)} (all-in)"))
            case UncalledBetReturned():
                lines.append(LogLine(street, f"Uncalled {event.amount:,} returned to {names[event.seat]}"))
            case ShowdownRevealed():
                street = Street.SHOWDOWN.value
                lines.append(LogLine(street, says(names[event.seat], "shows") + f" {_cards(event.cards)} — "
                                             f"{event.value.describe()}"))
            case PotAwarded():
                pot = "main pot" if event.pot_index == 0 else f"side pot {event.pot_index}"
                hand = f" with {event.value.describe()}" if event.value is not None and street == "showdown" else ""
                if len(event.winners) > 1:
                    who = " and ".join(names[s] for s in event.winners) + " split"
                else:
                    who = says(names[event.winners[0]], "wins")
                lines.append(LogLine(street, f"{who} the {pot} of {event.amount:,}{hand}"))
    return lines
