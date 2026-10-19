"""QML card and chip components loaded in a real QML engine."""

import pytest
from PySide6.QtCore import QMetaObject, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem

from bridge import ChipsBridge, registry
from poker import FULL_DECK
from services.paths import qml_dir


# Components must outlive the objects they create.
_components: list[QQmlComponent] = []


@pytest.fixture
def engine(qapp):
    registry.install(ChipsBridge())
    engine = QQmlEngine()
    engine.addImportPath(str(qml_dir()))
    yield engine
    _components.clear()
    engine.deleteLater()


def create(engine, body: str) -> QQuickItem:
    source = f'import QtQuick\nimport "components"\n{body}\n'
    component = QQmlComponent(engine)
    # Base URL inside qml/ so the relative "components" import resolves.
    component.setData(source.encode(), QUrl.fromLocalFile(str(qml_dir() / "_test.qml")))
    item = component.create()
    assert item is not None, component.errorString()
    _components.append(component)
    return item


def children_of_type(item, class_name):
    return [c for c in item.findChildren(QQuickItem) if c.inherits(class_name)]


def images(item):
    return children_of_type(item, "QQuickImage")


def is_loaded(image):
    return image.property("progress") == 1.0 and image.implicitWidth() > 0


def test_every_card_image_loads(engine):
    for card in FULL_DECK:
        item = create(engine, f'PlayingCard {{ width: 60; height: 84; card: "{card.code}"; animated: false }}')
        front = item.findChild(QQuickItem, "cardFront")
        assert front.property("source").toString().endswith(f"/{card.code}.svg")
        assert is_loaded(front), card
        assert is_loaded(item.findChild(QQuickItem, "cardBack"))


def test_card_keeps_proportions_in_distorted_box(engine):
    item = create(engine, 'PlayingCard { width: 200; height: 100; card: "As"; animated: false }')
    body_sizes = {(round(i.width()), round(i.height())) for i in images(item)}
    (w, h), = body_sizes
    assert h == 100 and w == pytest.approx(100 * 63 / 88, abs=1)


def test_face_down_and_unknown_cards_show_back(engine):
    item = create(engine, 'PlayingCard { width: 60; height: 84; card: "Kd"; animated: false }')
    assert item.property("showingFace") is True
    item.setProperty("faceUp", False)
    assert item.property("showingFace") is False
    item.setProperty("faceUp", True)
    item.setProperty("card", "")
    assert item.property("showingFace") is False


def test_highlight_and_dim_states(engine):
    item = create(engine, 'PlayingCard { width: 60; height: 84; card: "Kd"; animated: false }')
    overlays = {c.objectName(): c for c in item.findChildren(QQuickItem) if c.objectName()}
    assert overlays["dimOverlay"].opacity() == 0
    assert overlays["highlightRing"].opacity() == 0
    item.setProperty("dimmed", True)
    item.setProperty("highlighted", True)
    assert overlays["dimOverlay"].opacity() > 0
    assert overlays["highlightRing"].opacity() == 1


@pytest.mark.parametrize("amount", [1, 35, 480, 1275, 23480])
def test_chip_pile_represents_amount_exactly(engine, amount):
    item = create(engine, f"ChipPile {{ amount: {amount} }}")
    stacks = item.property("stacks").toVariant()
    assert sum(s["value"] * s["count"] for s in stacks) == amount
    assert all(s["count"] <= 10 for s in stacks)


def test_chip_pile_updates_when_amount_changes(engine):
    item = create(engine, "ChipPile { amount: 25 }")
    first_width = item.width()
    item.setProperty("amount", 1275)
    stacks = item.property("stacks").toVariant()
    assert [s["value"] for s in stacks] == [1000, 100, 25]
    # Row positions children on polish, which needs a window; force it here.
    (row,) = children_of_type(item, "QQuickRow")
    QMetaObject.invokeMethod(row, "forceLayout")
    assert item.width() > first_width
    item.setProperty("amount", 0)
    assert item.property("stacks").toVariant() == []


def test_chip_stack_height_grows_with_count(engine):
    item = create(engine, "ChipStack { count: 1; chipWidth: 40 }")
    single = item.height()
    item.setProperty("count", 10)
    assert item.height() == pytest.approx(single + 9 * item.property("thickness"))


def test_chip_label_hidden_when_too_small(engine):
    item = create(engine, 'PokerChip { width: 24; label: "100" }')
    labels = children_of_type(item, "QQuickText")
    assert labels and not labels[0].isVisible()
    item.setProperty("width", 72)
    assert labels[0].isVisible()
