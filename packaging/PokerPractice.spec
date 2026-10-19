# PyInstaller specification for Hold'em Practice.
#
# Build from the project root:
#     pyinstaller --noconfirm --clean packaging/PokerPractice.spec
#
# Produces a one-folder build in dist/PokerPractice/ (PokerPractice.exe on
# Windows). One-folder starts much faster than one-file for Qt applications and
# keeps Qt plugins and QML modules where Qt expects them.

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent  # noqa: F821 (provided by PyInstaller)
sys.path.insert(0, str(ROOT / "packaging"))
from bundle_filter import keep  # noqa: E402

block_cipher = None

a = Analysis(  # noqa: F821
    [str(ROOT / "main.py")],
    pathex=[str(ROOT / "src")],
    datas=[
        (str(ROOT / "qml"), "qml"),
        (str(ROOT / "assets"), "assets"),
    ],
    hiddenimports=[
        # Imported lazily by main.py.
        "services.application",
        "services.self_test",
        # Qt modules used only from QML or through plugins.
        "PySide6.QtQuickControls2",
        "PySide6.QtSvg",  # SVG image format plugin for the card artwork
    ],
    excludes=[
        # Not used; keeps the bundle smaller.
        "tkinter",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtWebEngineWidgets",
        "PySide6.Qt3DCore",
        "PySide6.QtMultimedia",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtPdf",
        "PySide6.QtWidgets",
    ],
    noarchive=False,
)

# Drop unused Qt modules, libraries and plugins (see bundle_filter.py).

a.binaries = [entry for entry in a.binaries if keep(entry[0])]
a.datas = [entry for entry in a.datas if keep(entry[0])]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PokerPractice",
    debug=False,
    strip=False,
    upx=False,
    console=False,  # GUI application: no console window
    icon=str(ROOT / "assets" / "icon" / "app.ico"),
    version=str(ROOT / "packaging" / "version_info.txt") if sys.platform == "win32" else None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="PokerPractice",
)
