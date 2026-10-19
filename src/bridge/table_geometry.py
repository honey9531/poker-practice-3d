"""The 3D table's meshes as a QML type (``TableGeometry`` in ``PokerPractice.Bridge``)."""

from __future__ import annotations

from array import array

from PySide6.QtCore import Property, QByteArray, Signal
from PySide6.QtGui import QVector3D
from PySide6.QtQml import QmlElement
from PySide6.QtQuick3D import QQuick3DGeometry

from bridge.registry import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME
from services import table_mesh

__all__ = ["TableGeometry", "QML_IMPORT_NAME", "QML_IMPORT_MAJOR_VERSION"]

_Attribute = QQuick3DGeometry.Attribute


@QmlElement
class TableGeometry(QQuick3DGeometry):
    """One part of the table (``part``: felt, trim, rail or apron).

    Also publishes the table's dimensions so QML lays out cards and chips on
    the same surface the mesh describes.
    """

    partChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._part = ""

    @Property(str, notify=partChanged)
    def part(self) -> str:
        return self._part

    @part.setter
    def part(self, value: str) -> None:
        if value == self._part:
            return
        self._part = value
        self._rebuild()
        self.partChanged.emit()

    @Property(float, constant=True)
    def feltRadius(self) -> float:
        return table_mesh.FELT_RADIUS

    @Property(float, constant=True)
    def straightHalf(self) -> float:
        return table_mesh.STRAIGHT_HALF

    @Property(float, constant=True)
    def outerWidth(self) -> float:
        return table_mesh.OUTER_WIDTH

    @Property(float, constant=True)
    def outerDepth(self) -> float:
        return table_mesh.OUTER_DEPTH

    @Property(float, constant=True)
    def railHeight(self) -> float:
        return table_mesh.TRIM_HEIGHT + table_mesh.RAIL_HEIGHT

    @Property(float, constant=True)
    def apronDepth(self) -> float:
        return table_mesh.APRON_DEPTH

    def _rebuild(self) -> None:
        mesh = table_mesh.build(self._part)
        low, high = mesh.bounds()
        self.clear()
        self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
        self.setStride(table_mesh.STRIDE)
        self.setVertexData(QByteArray(array("f", mesh.vertices).tobytes()))
        self.setIndexData(QByteArray(array("I", mesh.indices).tobytes()))
        self.addAttribute(_Attribute.Semantic.PositionSemantic, 0, _Attribute.ComponentType.F32Type)
        self.addAttribute(_Attribute.Semantic.NormalSemantic, 12, _Attribute.ComponentType.F32Type)
        self.addAttribute(_Attribute.Semantic.TexCoordSemantic, 24, _Attribute.ComponentType.F32Type)
        self.addAttribute(_Attribute.Semantic.IndexSemantic, 0, _Attribute.ComponentType.U32Type)
        self.setBounds(QVector3D(*low), QVector3D(*high))
        self.update()
