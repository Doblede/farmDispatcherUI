"""Qt binding shim.

PySide6 is used when available (standalone, Maya 2025+); otherwise PySide2
(Maya 2022-2024). Import Qt from here, never from PySide directly.
"""

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtGui import QAction

    QT_BINDING = "PySide6"
except ImportError:  # pragma: no cover - depends on the host application
    from PySide2 import QtCore, QtGui, QtWidgets
    from PySide2.QtWidgets import QAction

    QT_BINDING = "PySide2"

Qt = QtCore.Qt
Signal = QtCore.Signal


def exec_(obj, *args):
    """Run a dialog/menu/app event loop: ``exec`` on PySide6, ``exec_`` on PySide2."""
    method = getattr(obj, "exec", None) or getattr(obj, "exec_")
    return method(*args)


__all__ = ["QtCore", "QtGui", "QtWidgets", "QAction", "Qt", "Signal", "QT_BINDING", "exec_"]
