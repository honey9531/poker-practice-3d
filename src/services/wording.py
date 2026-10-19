"""Small helpers for player-facing sentences."""

from __future__ import annotations

SECOND_PERSON = "You"

_IRREGULAR = {"has": "have", "is": "are", "does": "do"}


def verb_for(name: str, verb: str) -> str:
    """``verb`` (third person singular) conjugated for ``name``: 'raises' / 'raise'."""
    if name != SECOND_PERSON:
        return verb
    if verb in _IRREGULAR:
        return _IRREGULAR[verb]
    if verb.endswith(("ches", "shes", "sses", "xes")):
        return verb[:-2]
    return verb[:-1] if verb.endswith("s") else verb


def says(name: str, verb: str) -> str:
    """'Avery raises' / 'You raise'."""
    return f"{name} {verb_for(name, verb)}"
