"""Filesystem locations for bundled resources and writable user data.

Resources (QML, assets) are read-only and live next to the source tree in
development, or inside the PyInstaller bundle (``sys._MEIPASS``) when frozen.
User data (SQLite database, logs) always lives in a per-user writable
directory so that the application never writes into its installation folder.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "PokerPractice"

# Overrides the user-data directory; used by tests and for portable setups.
DATA_DIR_ENV = "POKER_PRACTICE_DATA_DIR"


def resource_root() -> Path:
    """Directory that contains the ``qml/`` and ``assets/`` folders."""
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return Path(bundle_dir)
    # src/services/paths.py -> project root
    return Path(__file__).resolve().parents[2]


def qml_dir() -> Path:
    return resource_root() / "qml"


def assets_dir() -> Path:
    return resource_root() / "assets"


def user_data_dir() -> Path:
    """Per-user writable directory, created on first access."""
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        path = Path(override)
    elif sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        path = Path(base) / APP_DIR_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        path = Path(base) / APP_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_dir() -> Path:
    path = user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
