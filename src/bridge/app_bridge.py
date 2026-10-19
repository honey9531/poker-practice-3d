"""Application-level QObject exposed to QML as the ``App`` singleton."""

from __future__ import annotations

import logging

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot
from PySide6.QtGui import QRhiDriverInfo
from PySide6.QtQml import QmlNamedElement, QmlSingleton, QQmlEngine
from PySide6.QtQuick import QQuickWindow

from bridge.registry import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME, singleton_instance
from services.logging_setup import LOG_FILE_NAME
from services.paths import log_dir, user_data_dir

__all__ = ["AppBridge", "QML_IMPORT_NAME", "QML_IMPORT_MAJOR_VERSION", "is_software_renderer"]

log = logging.getLogger(__name__)

APP_NAME = "Hold'em Practice"
APP_VERSION = "0.1.0"

# Graphics devices that are really the CPU: Mesa's llvmpipe/softpipe (virtual
# machines, remote desktops), SwiftShader, and Windows' Basic Render Driver (WARP).
SOFTWARE_RENDERER_NAMES = ("llvmpipe", "softpipe", "swiftshader", "basic render", "warp", "software")


def is_software_renderer(device_name: str, cpu_device: bool = False) -> bool:
    name = device_name.lower()
    return cpu_device or any(marker in name for marker in SOFTWARE_RENDERER_NAMES)


@QmlNamedElement("App")
@QmlSingleton
class AppBridge(QObject):
    """Static application information and app-wide commands."""

    quitRequested = Signal()
    # An unexpected internal error (already logged): message for the user.
    errorReported = Signal(str)
    softwareRenderingChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._window: QQuickWindow | None = None
        self._software_rendering = False

    @staticmethod
    def create(engine: QQmlEngine) -> "AppBridge":
        return singleton_instance(AppBridge)

    @Property(str, constant=True)
    def name(self) -> str:
        return APP_NAME

    @Property(str, constant=True)
    def version(self) -> str:
        return APP_VERSION

    @Property(str, constant=True)
    def dataDirectory(self) -> str:
        return str(user_data_dir())

    @Property(str, constant=True)
    def logFile(self) -> str:
        return str(log_dir() / LOG_FILE_NAME)

    @Slot()
    def requestQuit(self) -> None:
        self.quitRequested.emit()

    @Property(bool, notify=softwareRenderingChanged)
    def softwareRendering(self) -> bool:
        """True when the window renders on the CPU; the 3D table then uses less detail."""
        return self._software_rendering

    def watch_renderer(self, window: QQuickWindow) -> None:
        """Find out which graphics device ``window`` renders with once it starts."""
        self._window = window
        # Emitted on the render thread: handle it on this object's (the GUI) thread.
        window.sceneGraphInitialized.connect(self._check_renderer, Qt.ConnectionType.QueuedConnection)

    @Slot()
    def _check_renderer(self) -> None:
        rhi = self._window.rhi() if self._window is not None else None
        if rhi is None:  # Qt Quick's software renderer: there is no 3D at all
            log.info("Graphics: Qt Quick software renderer")
            return
        info = rhi.driverInfo()
        name = bytes(info.deviceName).decode(errors="replace")
        software = is_software_renderer(name, info.deviceType == QRhiDriverInfo.DeviceType.CpuDevice)
        log.info("Graphics: %s via %s%s", name, rhi.backendName(), " (software rendering)" if software else "")
        if software != self._software_rendering:
            self._software_rendering = software
            self.softwareRenderingChanged.emit()
