"""Chip denominations exposed to QML as the ``Chips`` singleton."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QmlNamedElement, QmlSingleton, QQmlEngine

from bridge.registry import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME, singleton_instance
from services.chips import (
    DEFAULT_DENOMINATIONS,
    ChipDenomination,
    breakdown,
    chip_label,
    validate_denominations,
)

__all__ = ["ChipsBridge", "QML_IMPORT_NAME", "QML_IMPORT_MAJOR_VERSION"]


def _as_dict(denomination: ChipDenomination) -> dict:
    return {
        "value": denomination.value,
        "label": chip_label(denomination.value),
        "color": denomination.color,
        "insert": denomination.insert,
        "text": denomination.text,
    }


@QmlNamedElement("Chips")
@QmlSingleton
class ChipsBridge(QObject):
    """Denomination colour scheme plus amount -> chip stacks for display."""

    denominationsChanged = Signal()

    def __init__(
        self,
        denominations: Sequence[ChipDenomination] = DEFAULT_DENOMINATIONS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._denominations: tuple[ChipDenomination, ...] = ()
        self.set_denominations(denominations)

    @staticmethod
    def create(engine: QQmlEngine) -> "ChipsBridge":
        return singleton_instance(ChipsBridge)

    def set_denominations(self, denominations: Sequence[ChipDenomination]) -> None:
        validate_denominations(denominations)
        self._denominations = tuple(sorted(denominations, key=lambda d: d.value))
        self.denominationsChanged.emit()

    @Property("QVariantList", notify=denominationsChanged)
    def denominations(self) -> list[dict]:
        return [_as_dict(d) for d in self._denominations]

    @Slot(int, result="QVariantList")
    def breakdown(self, amount: int) -> list[dict]:
        """Stacks for ``amount``: [{value, label, color, insert, text, count}], largest first."""
        if amount <= 0:
            return []
        return [
            {**_as_dict(denomination), "count": count}
            for denomination, count in breakdown(amount, self._denominations)
        ]
