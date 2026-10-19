"""Hands Python-owned bridge instances to QML singleton factories.

Bridge classes are registered with ``@QmlSingleton``; QML calls their static
``create()`` the first time a singleton is used, which returns the instance
installed here. Instances are created and owned by Python so that services
can be wired up before QML loads.

(``qmlRegisterSingletonInstance`` is deliberately not used: with PySide6 6.12
importing a module registered that way breaks resolution of built-in QtQuick
types such as ``Item`` and ``Rectangle``.)
"""

from __future__ import annotations

from typing import TypeVar

from PySide6.QtCore import QObject
from PySide6.QtQml import QJSEngine

# Read by the PySide6 QML decorators in the module that applies them.
QML_IMPORT_NAME = "PokerPractice.Bridge"
QML_IMPORT_MAJOR_VERSION = 1

T = TypeVar("T", bound=QObject)

_instances: dict[type, QObject] = {}


def install(instance: QObject) -> None:
    """Make ``instance`` the object returned for its class's QML singleton."""
    _instances[type(instance)] = instance


def clear() -> None:
    _instances.clear()


def singleton_instance(cls: type[T]) -> T:
    try:
        instance = _instances[cls]
    except KeyError:
        raise RuntimeError(f"No {cls.__name__} instance installed for QML") from None
    # Keep Python in charge of the lifetime; QML must not delete it.
    QJSEngine.setObjectOwnership(instance, QJSEngine.ObjectOwnership.CppOwnership)
    return instance  # type: ignore[return-value]
