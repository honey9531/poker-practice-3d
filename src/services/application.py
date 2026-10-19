"""Builds the Qt application, the QML engine and the bridge objects."""

from __future__ import annotations

import logging
import signal
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine, QQmlError
from PySide6.QtQuickControls2 import QQuickStyle

from bridge import AppBridge, ChipsBridge, GameBridge, registry
from bridge.app_bridge import APP_NAME, APP_VERSION
from bridge.replay_bridge import ReplayBridge
from bridge.settings_bridge import SettingsBridge
from bridge.stats_bridge import HistoryBridge, StatsBridge
from services.database import DB_FILE_NAME, Database, DatabaseError
from services.game_controller import GameController
from services.history import HistoryStore
from services.paths import assets_dir, qml_dir, user_data_dir
from services.recorder import HistoryRecorder
from services.settings import AUTO_DEAL_DELAY_MS, CHIP_SCHEMES, AppSettings

log = logging.getLogger(__name__)

ORGANIZATION = "PokerPractice"
MAIN_QML = "Main.qml"


class QmlLoadError(RuntimeError):
    pass


@dataclass
class AppContext:
    """Everything that must stay alive for the duration of the UI."""

    engine: QQmlApplicationEngine
    app_bridge: AppBridge
    chips: ChipsBridge
    game: GameBridge
    controller: GameController
    db: Database
    store: HistoryStore
    recorder: HistoryRecorder
    settings: SettingsBridge
    stats: StatsBridge
    history: HistoryBridge
    replay: ReplayBridge
    notice: str = ""  # shown once at startup (e.g. database problems)
    qml_warnings: list[str] = field(default_factory=list)

    def shutdown(self) -> None:
        """Close the open session and the database."""
        self.controller.end_session()
        self.db.close()


def configure_qt_application() -> None:
    """Settings that must be applied before the QGuiApplication is created."""
    QCoreApplication.setOrganizationName(ORGANIZATION)
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(APP_VERSION)
    # Basic style: fully customisable and identical on every platform.
    QQuickStyle.setStyle("Basic")


def open_database(path: Path | None = None) -> tuple[Database, str]:
    """Open (or create) the history database; never fails.

    Returns the database and a notice for the user when something went wrong:
    a corrupted file is moved aside and replaced, and an unusable location
    falls back to an in-memory database for this run.
    """
    path = path or user_data_dir() / DB_FILE_NAME
    try:
        db = Database(path)
    except (sqlite3.Error, OSError, DatabaseError) as exc:
        log.exception("Cannot open %s; history will not be saved this time", path)
        return Database(Path(":memory:")), f"Hand history cannot be saved this session ({exc})."
    if db.recovered_from is not None:
        return db, (f"The history database was damaged and has been reset. "
                    f"The old file was kept as {db.recovered_from.name}.")
    return db, ""


def load_ui(app: QGuiApplication, db_path: Path | None = None) -> AppContext:
    """Create services, expose bridge objects to QML and load the main window."""
    app.setWindowIcon(QIcon(str(assets_dir() / "icon" / "app.png")))
    engine = QQmlApplicationEngine()
    db, notice = open_database(db_path)
    store = HistoryStore(db)
    try:
        store.close_open_sessions()
    except sqlite3.Error:
        log.exception("Could not close stale sessions")

    game = GameBridge(engine)
    recorder = HistoryRecorder(store)
    controller = GameController(game.set_view, recorder=recorder, parent=engine)
    stats = StatsBridge(store, lambda: recorder.session_id, parent=engine)
    context = AppContext(
        engine=engine,
        app_bridge=AppBridge(engine),
        chips=ChipsBridge(parent=engine),
        game=game,
        controller=controller,
        db=db,
        store=store,
        recorder=recorder,
        settings=SettingsBridge(store, parent=engine),
        stats=stats,
        history=HistoryBridge(store, parent=engine),
        replay=ReplayBridge(store, parent=engine),
        notice=notice,
    )
    context.settings.recovery_message = notice
    game.attach(controller)
    recorder.on_error = game.errorOccurred.emit
    recorder.on_recorded = stats.refresh

    def apply_settings(settings: AppSettings) -> None:
        context.chips.set_denominations(CHIP_SCHEMES[settings.chip_scheme])
        controller.set_animations_enabled(settings.animations_enabled)
        controller.auto_next_hand_ms = AUTO_DEAL_DELAY_MS if settings.auto_deal else None

    context.settings.subscribe(apply_settings)

    def on_warnings(warnings: list[QQmlError]) -> None:
        for warning in warnings:
            context.qml_warnings.append(warning.toString())

    engine.warnings.connect(on_warnings)
    for bridge in (context.app_bridge, context.chips, game, context.settings, stats,
                   context.history, context.replay):
        registry.install(bridge)
    context.app_bridge.quitRequested.connect(app.quit)

    engine.addImportPath(str(qml_dir()))
    main_qml = qml_dir() / MAIN_QML
    engine.load(QUrl.fromLocalFile(str(main_qml)))
    if not engine.rootObjects():
        details = "\n".join(context.qml_warnings) or "no diagnostics"
        raise QmlLoadError(f"Failed to load {main_qml}:\n{details}")
    log.info("Loaded %s", main_qml)
    return context


def install_exception_hook(context: AppContext) -> None:
    """Log unexpected exceptions and tell the user instead of failing silently.

    Exceptions raised inside Qt callbacks (slots, timers) cannot propagate to
    the caller; without this hook they would only be printed to stderr.
    """

    def hook(exc_type, exc, tb) -> None:
        log.critical("Unhandled exception", exc_info=(exc_type, exc, tb))
        if not issubclass(exc_type, KeyboardInterrupt):
            context.app_bridge.errorReported.emit(f"{exc_type.__name__}: {exc}")

    sys.excepthook = hook


def install_quit_on_signals(app: QGuiApplication) -> QTimer:
    """Quit cleanly on Ctrl+C / SIGTERM.

    Python only runs signal handlers when the interpreter regains control, which
    never happens while Qt's event loop is idle, so a cheap timer wakes it up.
    """

    def handle(signum, _frame) -> None:
        log.info("Received signal %s, quitting", signum)
        app.quit()

    signal.signal(signal.SIGINT, handle)
    signal.signal(signal.SIGTERM, handle)
    timer = QTimer(app)
    timer.timeout.connect(lambda: None)
    timer.start(250)
    return timer


def run(argv: list[str] | None = None) -> int:
    from services.logging_setup import configure_logging

    log_file = configure_logging()
    log.info("Starting %s %s (log: %s)", APP_NAME, APP_VERSION, log_file)

    configure_qt_application()
    app = QGuiApplication(argv if argv is not None else sys.argv)
    try:
        context = load_ui(app)
    except QmlLoadError:
        log.exception("Unable to start the user interface")
        return 1

    install_exception_hook(context)
    install_quit_on_signals(app)
    exit_code = app.exec()
    context.shutdown()
    log.info("Exiting with code %s", exit_code)
    del context
    return exit_code
