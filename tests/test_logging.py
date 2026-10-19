import logging

from PySide6.QtCore import qWarning

from services.logging_setup import configure_logging


def test_log_file_receives_python_and_qt_messages(isolated_data_dir):
    log_file = configure_logging()
    assert log_file.parent == isolated_data_dir / "logs"

    logging.getLogger("test").info("python message")
    qWarning("qt message")
    for handler in logging.getLogger().handlers:
        handler.flush()

    text = log_file.read_text(encoding="utf-8")
    assert "python message" in text
    assert "qt message" in text


def test_reconfiguring_does_not_duplicate_handlers():
    configure_logging()
    count = len(logging.getLogger().handlers)
    configure_logging()
    assert len(logging.getLogger().handlers) == count
