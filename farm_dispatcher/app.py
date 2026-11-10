"""Entry points: ``python -m farm_dispatcher`` standalone, or ``show_in_maya()`` inside Maya."""

from __future__ import annotations

import logging
import sys
from typing import Optional

from farm_dispatcher.core.backend import load_backend
from farm_dispatcher.core.statistics import UsageStats
from farm_dispatcher.qt import QtWidgets, exec_

_maya_window = None  # keeps the Maya instance alive and lets us replace it


def create_window(parent=None, via: str = "standalone"):
    from farm_dispatcher.ui.main_window import MainWindow

    stats = UsageStats()
    stats.record_open(via)
    return MainWindow(load_backend(), stats=stats, parent=parent)


def main(argv: Optional[list] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(argv or sys.argv)
    app.setApplicationName("Farm Dispatcher")
    window = create_window()
    window.show()
    return exec_(app)


def _maya_main_window():
    from maya import OpenMayaUI  # noqa: imported only inside Maya

    try:
        from shiboken6 import wrapInstance
    except ImportError:
        from shiboken2 import wrapInstance
    return wrapInstance(int(OpenMayaUI.MQtUtil.mainWindow()), QtWidgets.QWidget)


def show_in_maya():
    """Open (or re-open) the tool parented to Maya's main window."""
    global _maya_window
    if _maya_window is not None:
        _maya_window.close()
        _maya_window.deleteLater()
    _maya_window = create_window(parent=_maya_main_window(), via="maya")
    _maya_window.show()
    return _maya_window
