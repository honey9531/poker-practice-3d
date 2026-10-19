"""List model of the seats at the table."""

from __future__ import annotations

from dataclasses import fields

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, QObject, Qt

from services.table_view import SeatView


def _camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part.capitalize() for part in rest)


_FIELDS = [f.name for f in fields(SeatView)]
_ROLE_BASE = Qt.ItemDataRole.UserRole + 1
# Role id -> SeatView attribute; QML sees camelCase names (``isHuman``, ``lastAction``).
_ROLES = {_ROLE_BASE + i: name for i, name in enumerate(_FIELDS)}
_ROLE_NAMES = {role: QByteArray(_camel(name).encode()) for role, name in _ROLES.items()}
_ROLE_BY_FIELD = {name: role for role, name in _ROLES.items()}


class PlayerListModel(QAbstractListModel):
    """One row per seat. Updates keep rows stable so QML delegates (and their
    animations) are not recreated when only values change."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._seats: list[SeatView] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self._seats)

    def roleNames(self) -> dict[int, QByteArray]:
        return _ROLE_NAMES

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._seats):
            return None
        seat = self._seats[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return seat.name
        name = _ROLES.get(role)
        if name is None:
            return None
        value = getattr(seat, name)
        return list(value) if isinstance(value, tuple) else value

    def seat(self, row: int) -> SeatView:
        return self._seats[row]

    def set_seats(self, seats: tuple[SeatView, ...] | list[SeatView]) -> None:
        seats = list(seats)
        if [s.seat for s in seats] != [s.seat for s in self._seats]:
            self.beginResetModel()
            self._seats = seats
            self.endResetModel()
            return
        for row, (old, new) in enumerate(zip(self._seats, seats)):
            if old == new:
                continue
            changed = [_ROLE_BY_FIELD[f] for f in _FIELDS if getattr(old, f) != getattr(new, f)]
            self._seats[row] = new
            index = self.index(row)
            self.dataChanged.emit(index, index, changed)
