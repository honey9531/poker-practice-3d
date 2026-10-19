"""JSON encoding of hand events for storage and replay.

The format is versioned. Decoding validates structure and raises
:class:`RecordError` for anything malformed, so a corrupted row can be skipped
without affecting the rest of the history.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from poker.actions import ActionType
from poker.cards import Card
from poker.evaluator import HandCategory, HandValue
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

FORMAT_VERSION = 1


class RecordError(ValueError):
    """A stored hand could not be decoded."""


def _cards(cards: Sequence[Card]) -> list[str]:
    return [c.code for c in cards]


def _value(value: HandValue | None) -> dict | None:
    if value is None:
        return None
    return {"category": int(value.category), "tiebreak": list(value.tiebreak)}


def _seat_map(mapping) -> dict[str, int]:
    return {str(k): int(v) for k, v in mapping.items()}


def encode_event(event: HandEvent) -> dict[str, Any]:
    match event:
        case HandStarted():
            return {"type": "hand_started", "button": event.button,
                    "sb_seat": event.small_blind_seat, "bb_seat": event.big_blind_seat,
                    "sb": event.small_blind, "bb": event.big_blind,
                    "stacks": _seat_map(event.stacks),
                    "names": {str(k): v for k, v in event.names.items()}}
        case BlindPosted():
            return {"type": "blind", "seat": event.seat, "kind": event.kind.value,
                    "amount": event.amount, "all_in": event.all_in}
        case HoleCardsDealt():
            return {"type": "hole", "seat": event.seat, "cards": _cards(event.cards)}
        case PlayerActed():
            return {"type": "action", "seat": event.seat, "street": event.street.value,
                    "action": event.action.value, "added": event.added,
                    "street_total": event.street_total, "stack_after": event.stack_after,
                    "all_in": event.all_in, "full_raise": event.full_raise}
        case BoardDealt():
            return {"type": "board", "street": event.street.value, "cards": _cards(event.cards)}
        case CardsExposed():
            return {"type": "exposed", "seat": event.seat, "cards": _cards(event.cards)}
        case UncalledBetReturned():
            return {"type": "uncalled", "seat": event.seat, "amount": event.amount}
        case ShowdownRevealed():
            return {"type": "showdown", "seat": event.seat, "cards": _cards(event.cards),
                    "value": _value(event.value), "best_five": _cards(event.best_five)}
        case PotAwarded():
            return {"type": "pot", "index": event.pot_index, "amount": event.amount,
                    "winners": list(event.winners), "shares": _seat_map(event.shares),
                    "value": _value(event.value)}
        case HandEnded():
            return {"type": "ended", "showdown": event.went_to_showdown,
                    "final_stacks": _seat_map(event.final_stacks), "net": _seat_map(event.net)}
    raise TypeError(f"Cannot encode {event!r}")


def _parse_cards(codes) -> tuple[Card, ...]:
    if not isinstance(codes, list):
        raise RecordError("cards must be a list")
    return tuple(Card.from_str(code) for code in codes)


def _parse_value(data) -> HandValue | None:
    if data is None:
        return None
    return HandValue(HandCategory(int(data["category"])), tuple(int(v) for v in data["tiebreak"]))


def _int_map(data) -> dict[int, int]:
    return {int(k): int(v) for k, v in data.items()}


def decode_event(data: dict[str, Any]) -> HandEvent:
    try:
        kind = data["type"]
        match kind:
            case "hand_started":
                return HandStarted(int(data["button"]), int(data["sb_seat"]), int(data["bb_seat"]),
                                   int(data["sb"]), int(data["bb"]), _int_map(data["stacks"]),
                                   {int(k): str(v) for k, v in data["names"].items()})
            case "blind":
                return BlindPosted(int(data["seat"]), BlindKind(data["kind"]), int(data["amount"]),
                                   bool(data["all_in"]))
            case "hole":
                return HoleCardsDealt(int(data["seat"]), _parse_cards(data["cards"]))  # type: ignore[arg-type]
            case "action":
                return PlayerActed(int(data["seat"]), Street(data["street"]), ActionType(data["action"]),
                                   int(data["added"]), int(data["street_total"]), int(data["stack_after"]),
                                   bool(data["all_in"]), bool(data["full_raise"]))
            case "board":
                return BoardDealt(Street(data["street"]), _parse_cards(data["cards"]))
            case "exposed":
                return CardsExposed(int(data["seat"]), _parse_cards(data["cards"]))  # type: ignore[arg-type]
            case "uncalled":
                return UncalledBetReturned(int(data["seat"]), int(data["amount"]))
            case "showdown":
                return ShowdownRevealed(int(data["seat"]), _parse_cards(data["cards"]),  # type: ignore[arg-type]
                                        _parse_value(data["value"]), _parse_cards(data["best_five"]))
            case "pot":
                return PotAwarded(int(data["index"]), int(data["amount"]),
                                  tuple(int(w) for w in data["winners"]), _int_map(data["shares"]),
                                  _parse_value(data["value"]))
            case "ended":
                return HandEnded(bool(data["showdown"]), _int_map(data["final_stacks"]), _int_map(data["net"]))
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise RecordError(f"Malformed {data.get('type', '?') if isinstance(data, dict) else '?'} event: {exc}") from exc
    raise RecordError(f"Unknown event type {kind!r}")


def encode_events(events: Sequence[HandEvent]) -> str:
    return json.dumps({"version": FORMAT_VERSION, "events": [encode_event(e) for e in events]},
                      separators=(",", ":"))


def decode_events(text: str) -> list[HandEvent]:
    try:
        payload = json.loads(text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise RecordError(f"Invalid JSON: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("version") != FORMAT_VERSION:
        raise RecordError("Unsupported history format")
    events = payload.get("events")
    if not isinstance(events, list) or not events:
        raise RecordError("No events")
    decoded = [decode_event(e) if isinstance(e, dict) else _bad(e) for e in events]
    if not isinstance(decoded[0], HandStarted) or not isinstance(decoded[-1], HandEnded):
        raise RecordError("Incomplete hand")
    return decoded


def _bad(item) -> HandEvent:
    raise RecordError(f"Event is not an object: {item!r}")
