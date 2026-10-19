import os
import sys
from pathlib import Path

import pytest

# Must be set before any Qt module creates the application.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtGui import QGuiApplication  # noqa: E402

from services.paths import DATA_DIR_ENV  # noqa: E402


@pytest.fixture(scope="session")
def qapp_cls():
    """pytest-qt: the UI is pure Qt Quick, so no QApplication/widgets."""
    return QGuiApplication


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Never touch the real user-data directory from tests."""
    data_dir = tmp_path / "userdata"
    monkeypatch.setenv(DATA_DIR_ENV, str(data_dir))
    return data_dir
