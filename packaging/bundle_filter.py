"""Which collected files go into the PyInstaller bundle.

PyInstaller's Qt hooks collect every QML module shipped with PySide6, plus the
libraries they need (QtWebEngine alone is ~200 MB). The app imports only
QtQuick, QtQuick.Controls.Basic, .Effects, .Layouts, .Shapes and .Window, plus
the core QtQuick3D module for the 3D table (not its helpers, effects,
particles, physics or XR); the packaged ``--self-test`` opens every screen, so
anything missing fails it.

Paths may use either separator (Linux ``PySide6/Qt/qml/...``, Windows
``PySide6\\qml\\...``).
"""

from __future__ import annotations

KEEP_QML = (
    "QtQml",  # QtQml, QtQml.Models, QtQml.WorkerScript
    "QtQuick/Controls/Basic",
    "QtQuick/Controls/impl",
    "QtQuick/Templates",
    "QtQuick/Effects",
    "QtQuick/Layouts",
    "QtQuick/Shapes",
    "QtQuick/Window",
)

EXCLUDED_LIBRARIES = (
    "Qt6WebEngine", "Qt6WebChannel", "Qt6WebSockets", "Qt6WebView", "Qt6Pdf",
    "Qt63D", "Qt6Charts", "Qt6DataVisualization", "Qt6Graphs",
    "Qt6Multimedia", "Qt6SpatialAudio", "Qt6TextToSpeech", "Qt6Location", "Qt6Positioning",
    "Qt6Sensors", "Qt6VirtualKeyboard", "Qt6Scxml", "Qt6StateMachine", "Qt6RemoteObjects",
    "Qt6QuickDialogs2", "Qt6QuickTimeline", "Qt6QuickParticles", "Qt6QuickTest", "Qt6Test",
    "Qt6Designer", "Qt6Help", "Qt6Bluetooth", "Qt6Nfc", "Qt6SerialPort", "Qt6Sql",
    "Qt6HttpServer", "Qt6Protobuf", "Qt6Grpc",
    # Qt Quick 3D extras; the 3D table needs only Quick3D, Quick3DRuntimeRender,
    # Quick3DUtils and ShaderTools.
    "Qt6Quick3DAssetImport", "Qt6Quick3DAssetUtils", "Qt6Quick3DEffects", "Qt6Quick3DGlslParser",
    "Qt6Quick3DHelpers", "Qt6Quick3DIblBaker", "Qt6Quick3DParticle", "Qt6Quick3DPhysics",
    "Qt6Quick3DSpatialAudio", "Qt6Quick3DXr",
    # Controls styles other than Basic, and other unused Qt Quick extras.
    "Qt6QuickControls2Imagine", "Qt6QuickControls2FluentWinUI3", "Qt6QuickControls2Material",
    "Qt6QuickControls2Universal", "Qt6QuickControls2Fusion", "Qt6QuickControls2IOS",
    "Qt6QuickControls2MacOS", "Qt6LabsStyleKit", "Qt6WaylandCompositor",
)

EXCLUDED_PLUGIN_DIRS = (
    "sqldrivers", "multimedia", "position", "sensors", "webview", "designer", "qmltooling",
    "sceneparsers", "geometryloaders", "renderers", "texttospeech", "canbus", "assetimporters",
    "renderplugins", "printsupport",
    "platformthemes",  # native desktop themes (GTK on Linux); the app draws its own style
)


def keep(dest: str) -> bool:
    path = dest.replace("\\", "/")
    if "PySide6/" not in path:
        return True  # our own files and Python itself
    if "/translations/" in path:
        return False  # UI is English only
    if "/qml/" in path:
        rel = path.split("/qml/", 1)[1]
        if "/" not in rel:
            return True  # builtins.qmltypes, jsroot.qmltypes
        if rel.startswith("QtQuick/") and rel.count("/") == 1:
            return True  # the QtQuick module itself
        if rel.startswith("QtQuick/Controls/") and rel.count("/") == 2:
            return True  # QtQuick.Controls base plugin
        if rel.startswith("QtQuick3D/") and rel.count("/") == 1:
            return True  # the QtQuick3D module itself, without its submodules
        return rel.startswith(KEEP_QML)
    if "/plugins/" in path:
        plugin_dir = path.split("/plugins/", 1)[1].split("/", 1)[0]
        if plugin_dir in EXCLUDED_PLUGIN_DIRS:
            return False
    name = path.rsplit("/", 1)[-1]
    return not any(pattern in name for pattern in EXCLUDED_LIBRARIES)
