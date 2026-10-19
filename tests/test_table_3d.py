"""The 3D table: renderer detection, the table style setting and the scene.

Headless runs (``QT_QPA_PLATFORM=offscreen``) use Qt Quick's software
renderer, which cannot draw 3D, so the table screen falls back to the 2D
table; the tests of the live 3D scene are then skipped. They run wherever the
platform can render 3D, for example:

    xvfb-run -a env QT_QPA_PLATFORM=xcb python -m pytest tests/test_table_3d.py
"""

import pytest
from PySide6.QtCore import Q_ARG, Q_RETURN_ARG, QMetaObject, QPointF, QUrl
from PySide6.QtGui import QVector3D
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick3D import QQuick3DObject

from bridge.app_bridge import is_software_renderer
from services import table_mesh
from services.application import configure_qt_application, load_ui
from services.paths import qml_dir
from services.preview import preview_table
from services.settings import AppSettings

SEAT_POINTS = [[0.5, 1.04], [0.1, 0.82], [0.1, 0.22], [0.5, 0.03], [0.9, 0.22], [0.9, 0.82]]


@pytest.mark.parametrize(
    ("name", "cpu", "expected"),
    [
        ("Mesa llvmpipe (LLVM 15.0.7, 256 bits)", False, True),
        ("Microsoft Basic Render Driver", False, True),
        ("Google SwiftShader", False, True),
        ("NVIDIA GeForce RTX 3060/PCIe/SSE2", False, False),
        ("Intel(R) UHD Graphics 620", False, False),
        ("AMD Radeon RX 6600", False, False),
        ("", True, True),
    ],
)
def test_software_renderers_are_recognised(name, cpu, expected):
    assert is_software_renderer(name, cpu) is expected


def test_table_style_setting_defaults_and_validation():
    assert AppSettings().table_style == "3d"
    assert AppSettings.from_mapping({"table_style": "2d"}).table_style == "2d"
    assert AppSettings.from_mapping({"table_style": "4d"}).table_style == "3d"
    assert AppSettings.from_mapping({"table_style": 3}).table_style == "3d"
    assert AppSettings.from_mapping(AppSettings(table_style="2d").to_mapping()).table_style == "2d"


# ---------------------------------------------------------------- QML


@pytest.fixture
def ui(qapp, qtbot):
    configure_qt_application()
    context = load_ui(qapp)
    window = context.engine.rootObjects()[0]
    window.resize(1280, 800)
    yield context, window
    window.close()
    context.engine.deleteLater()


def visual_descendants(item):
    for child in item.childItems():
        yield child
        yield from visual_descendants(child)


def find(window, name):
    item = next((i for i in visual_descendants(window.contentItem()) if i.objectName() == name), None)
    assert item is not None, name
    return item


def show_table(ui, qtbot, view=None):
    context, window = ui
    context.game.set_view(view or preview_table(6))
    window.showScreen("table")
    qtbot.wait(1500)  # software-rendered 3D (e.g. under Xvfb) is slow
    return window


def table_3d(window):
    """The live 3D table, or None when the 2D table is shown."""
    return find(window, "table3dLoader").property("item")


def call(obj, method, *args):
    return QMetaObject.invokeMethod(obj, method, Q_RETURN_ARG("QVariant"),
                                    *(Q_ARG("QVariant", a) for a in args))


def test_settings_offer_the_table_style_and_persist_it(ui, qtbot):
    context, window = ui
    window.showScreen("settings")
    qtbot.wait(200)
    assert find(window, "tableStyleSelector").isVisible()
    context.settings.setProperty("tableStyle", "2d")
    assert context.store.load_settings()["table_style"] == "2d"
    context.settings.setProperty("tableStyle", "flat")  # ignored
    assert context.settings.property("tableStyle") == "2d"


def test_without_3d_graphics_the_2d_table_is_shown(ui, qtbot):
    window = show_table(ui, qtbot)
    if table_3d(window) is not None:
        pytest.skip("this platform renders 3D")
    assert find(window, "pokerTable").isVisible()
    assert find(window, "boardCards").isVisible()
    assert ui[0].qml_warnings == []


def test_choosing_the_classic_table_shows_the_2d_table(ui, qtbot):
    context, window = ui
    context.settings.setProperty("tableStyle", "2d")
    show_table(ui, qtbot)
    assert table_3d(window) is None
    assert find(window, "pokerTable").isVisible()
    assert context.qml_warnings == []


# ------------------------------------------------- 3D camera and projection
# Pure QML maths: these run even where the scene itself cannot be drawn.


@pytest.fixture
def table_component(ui):
    context, window = ui
    component = QQmlComponent(context.engine, QUrl.fromLocalFile(str(qml_dir() / "components" / "Table3D.qml")))
    assert component.isReady(), component.errorString()
    created = []

    def make(width, height):
        obj = component.createWithInitialProperties({
            "game": context.game, "seatPoints": SEAT_POINTS,
            "betPoints": SEAT_POINTS, "markerPoints": SEAT_POINTS,
            "width": width, "height": height,
        })
        assert obj is not None, component.errorString()
        created.append(obj)
        return obj

    yield make
    for obj in created:
        obj.deleteLater()


def point(obj, u, v):
    p = call(obj, "pointAt", [u, v])
    return p.x(), p.y()


@pytest.mark.parametrize("size", [(1280, 634), (1024, 474), (1920, 914), (2560, 900), (900, 700)])
def test_camera_frames_the_whole_table_and_every_seat(table_component, size):
    width, height = size
    table = table_component(width, height)
    radius = table_mesh.OUTER_RADIUS
    outline = [(0.5 + (p.cx + p.nx * radius) / table_mesh.OUTER_WIDTH,
                0.5 + (p.cz + p.nz * radius) / table_mesh.OUTER_DEPTH)
               for p in table_mesh.stadium_outline(12)]
    for u, v in outline + [tuple(p) for p in SEAT_POINTS]:
        x, y = point(table, u, v)
        assert 0 <= x <= width and 0 <= y <= height, (u, v, x, y)
    # Centred left to right, and seen from the human's side: the near edge is wider.
    centre_x, _ = point(table, 0.5, 0.5)
    assert abs(centre_x - width / 2) < 0.5
    near = point(table, 1, 0.9)[0] - point(table, 0, 0.9)[0]
    far = point(table, 1, 0.1)[0] - point(table, 0, 0.1)[0]
    assert near > far
    assert point(table, 0.5, 1.0)[1] > point(table, 0.5, 0.0)[1]
    assert 52 <= table.property("unit") <= 160


def test_unit_grows_with_the_window(table_component):
    small = table_component(1024, 474).property("unit")
    large = table_component(2560, 1300).property("unit")
    assert large > small


# ----------------------------------------------------------- live 3D scene


@pytest.fixture
def scene(ui, qtbot):
    window = show_table(ui, qtbot)
    table = table_3d(window)
    if table is None:
        pytest.skip("3D rendering is not available on this platform (e.g. QT_QPA_PLATFORM=offscreen)")
    return ui[0], window, table


def node(table, name):
    found = table.findChild(QQuick3DObject, name)
    assert found is not None, name
    return found


def test_3d_table_replaces_the_flat_table(scene):
    context, window, table = scene
    assert not find(window, "pokerTable").isVisible()
    assert not find(window, "boardCards").isVisible()
    for slot in range(6):
        seat = find(window, f"seat{slot}")
        assert seat.isVisible() and seat.property("showCards") is False
    assert table.property("lowPower") == context.app_bridge.property("softwareRendering")
    assert context.qml_warnings == []


def test_3d_cards_show_only_what_the_player_may_see(scene):
    context, window, table = scene
    view = preview_table(6)
    human = [node(table, f"holeCard3d_0_{i}") for i in range(2)]
    assert sorted(c.property("card") for c in human) == ["Ah", "Kh"]
    assert all(c.property("showingFace") for c in human)
    opponent = [node(table, f"holeCard3d_1_{i}") for i in range(2)]
    assert all(c.property("card") == "" and not c.property("showingFace") for c in opponent)
    board = [node(table, f"boardCard3d{i}").property("card") for i in range(5)]
    assert board == list(view.board) + [""]


def test_3d_chips_follow_the_bets_and_the_pot(scene):
    context, window, table = scene
    view = preview_table(6)
    by_slot = {seat.slot: seat for seat in view.seats}
    for slot in range(6):
        assert node(table, f"betChips3d_{slot}").property("amount") == by_slot[slot].bet
    assert node(table, "potChips3d").property("amount") == sum(p.amount for p in view.pots)


def test_overlays_line_up_with_the_3d_scene(scene, qtbot):
    """The analytic projection used for nameplates matches Qt Quick 3D's own."""
    context, window, table = scene
    view3d = table.findChild(QQuick3DObject, "tableView3d") or next(
        i for i in visual_descendants(table) if i.objectName() == "tableView3d")
    for name in ["potChips3d", "betChips3d_1", "betChips3d_4", "holeCard3d_0_0"]:
        position = node(table, name).property("scenePosition")
        mapped = QMetaObject.invokeMethod(view3d, "mapFrom3DScene", Q_RETURN_ARG("QVector3D"),
                                          Q_ARG("QVector3D", position))
        ours = call(table, "project", position.x(), position.y(), position.z())
        assert abs(mapped.x() - ours.x()) < 1.0 and abs(mapped.y() - ours.y()) < 1.0, name


def test_switching_to_the_classic_table_while_playing(scene, qtbot):
    context, window, table = scene
    context.settings.setProperty("tableStyle", "2d")
    qtbot.waitUntil(lambda: table_3d(window) is None, timeout=3000)
    assert find(window, "pokerTable").isVisible()
    assert find(window, "seat0").property("showCards") is True
    context.settings.setProperty("tableStyle", "3d")
    qtbot.waitUntil(lambda: table_3d(window) is not None, timeout=5000)
    assert context.qml_warnings == []
