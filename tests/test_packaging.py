"""Packaging: bundle filtering rules and the built-in self-test."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packaging"))
from bundle_filter import keep  # noqa: E402


@pytest.mark.parametrize(
    "dest",
    [
        "qml/Main.qml",
        "assets/cards/As.svg",
        "PySide6/Qt/qml/QtQuick/qmldir",
        "PySide6/Qt/qml/QtQuick/libqtquick2plugin.so",
        "PySide6/Qt/qml/QtQuick/Controls/qmldir",
        "PySide6/Qt/qml/QtQuick/Controls/Basic/Button.qml",
        "PySide6/Qt/qml/QtQuick/Controls/impl/qmldir",
        "PySide6/Qt/qml/QtQuick/Shapes/qmldir",
        "PySide6/Qt/qml/QtQuick/Effects/qmldir",
        "PySide6/Qt/qml/QtQml/WorkerScript/qmldir",
        "PySide6/Qt/qml/builtins.qmltypes",
        "PySide6/Qt/lib/libQt6Quick.so.6",
        "PySide6/Qt/lib/libQt6Svg.so.6",
        "PySide6/Qt/plugins/imageformats/libqsvg.so",
        "PySide6/Qt/plugins/platforms/libqxcb.so",
        r"PySide6\qml\QtQuick\Controls\Basic\Button.qml",
        r"PySide6\Qt6Quick.dll",
        r"PySide6\plugins\platforms\qwindows.dll",
    ],
)
def test_needed_files_are_kept(dest):
    assert keep(dest)


@pytest.mark.parametrize(
    "dest",
    [
        "PySide6/Qt/qml/QtWebEngine/qmldir",
        "PySide6/Qt/qml/QtQuick/Controls/Material/Button.qml",
        "PySide6/Qt/qml/QtQuick/Dialogs/qmldir",
        "PySide6/Qt/qml/QtQuick3D/qmldir",
        "PySide6/Qt/lib/libQt6WebEngineCore.so.6",
        "PySide6/Qt/lib/libQt6QuickControls2Material.so.6",
        "PySide6/Qt/translations/qt_de.qm",
        "PySide6/Qt/plugins/sqldrivers/libqsqlite.so",
        "PySide6/Qt/plugins/platformthemes/libqgtk3.so",
        r"PySide6\Qt6WebEngineCore.dll",
        r"PySide6\qml\QtQuick\Controls\FluentWinUI3\Button.qml",
    ],
)
def test_unused_files_are_dropped(dest):
    assert not keep(dest)


def test_self_test_passes_and_history_persists(tmp_path):
    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "POKER_PRACTICE_DATA_DIR": str(tmp_path)}
    counts = []
    for _ in range(2):
        result = subprocess.run([sys.executable, str(ROOT / "main.py"), "--self-test"],
                                capture_output=True, text=True, env=env, timeout=180)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "Self-test passed" in result.stdout
        line = next(l for l in result.stdout.splitlines() if "hands in database" in l)
        counts.append(int(line.rsplit(":", 1)[1]))
    assert counts[1] > counts[0] > 0
