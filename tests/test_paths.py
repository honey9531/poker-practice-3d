import sys

from services import paths


def test_resource_root_contains_qml_and_assets():
    assert (paths.qml_dir() / "Main.qml").is_file()
    assert paths.assets_dir().is_dir()


def test_frozen_bundle_uses_meipass(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert paths.resource_root() == tmp_path
    assert paths.qml_dir() == tmp_path / "qml"


def test_user_data_dir_override_is_created(isolated_data_dir):
    assert not isolated_data_dir.exists()
    assert paths.user_data_dir() == isolated_data_dir
    assert isolated_data_dir.is_dir()
    assert paths.log_dir() == isolated_data_dir / "logs"
    assert paths.log_dir().is_dir()


def test_windows_data_dir_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.delenv(paths.DATA_DIR_ENV)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert paths.user_data_dir() == tmp_path / paths.APP_DIR_NAME


def test_linux_data_dir_uses_xdg(monkeypatch, tmp_path):
    monkeypatch.delenv(paths.DATA_DIR_ENV)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert paths.user_data_dir() == tmp_path / paths.APP_DIR_NAME
