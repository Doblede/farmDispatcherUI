'''
@author: David De Juan
'''
import os
from PySide import QtCore
from PySide import QtGui


def reloadInterfaceIcons(widget, iconPath, w=None, h=None):
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'icons'))
    pixmap = QtGui.QPixmap(os.path.join(path, iconPath))
    if w:
        pixmap = pixmap.scaledToWidth(w, mode = QtCore.Qt.SmoothTransformation)
    if h:
        pixmap = pixmap.scaledToHeight(h, mode = QtCore.Qt.SmoothTransformation)
    if not widget:
        return pixmap
    if 'QPushButton' in type(widget).__name__:
        tool_icon = QtGui.QIcon()
        tool_icon.addPixmap(pixmap)
        widget.setIcon(tool_icon)
    elif 'QLabel' in type(widget).__name__:
        widget.setPixmap(pixmap)
        
        
def clearLayout(layout):
    while layout.count():
        child = layout.takeAt(0)
        if child.widget() is not None:
            child.widget().deleteLater()
        elif child.layout() is not None:
            clearLayout(child.layout())