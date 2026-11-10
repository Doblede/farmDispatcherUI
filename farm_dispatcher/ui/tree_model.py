"""Item model that shows a core.node.Node tree in a QTreeView."""

from __future__ import annotations

import itertools
import weakref
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from farm_dispatcher.core.node import Node
from farm_dispatcher.core.scene import AnimBlockNode, CharacterNode, RenderNode, ShotNode, StackNode
from farm_dispatcher.qt import QtCore, QtGui, QtWidgets, Qt, Signal

MIME_TYPE = "application/x-farm-dispatcher-nodes"

# Dragged nodes stay in this process, so the mime data only carries a key into this table.
_drag_payloads: Dict[str, List[Node]] = {}
_drag_counter = itertools.count()

ACCENT = QtGui.QColor(61, 139, 253)
DISABLED = QtGui.QColor(220, 70, 70)

Column = Tuple[str, Callable[[Node], str]]


def name_column(node: Node) -> str:
    return node.name


def _weak(handler):
    """Hold bound methods weakly.

    A strong reference from this (Qt-owned) model back to the window creates a
    cycle that crashes PySide when the garbage collector tears it down.
    """
    if handler is None:
        return lambda: None
    if hasattr(handler, "__self__"):
        return weakref.WeakMethod(handler)
    return lambda: handler


class NodeTreeModel(QtCore.QAbstractItemModel):
    """Read-mostly model over a Node tree.

    ``drop_handler(nodes, target) -> bool`` decides what a drop does;
    ``rename_handler(node, name) -> bool`` handles in-place renames.
    """

    nodes_dropped = Signal()
    node_renamed = Signal(object)

    def __init__(
        self,
        root: Node,
        columns: Sequence[Column],
        drop_handler: Optional[Callable[[List[Node], Node], bool]] = None,
        rename_handler: Optional[Callable[[Node, str], bool]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._root = root
        self._columns = list(columns)
        self._drop_ref = _weak(drop_handler)
        self._rename_ref = _weak(rename_handler)
        style = QtWidgets.QApplication.style()
        self._warning_icon = style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxWarning)

    # -- helpers -------------------------------------------------------
    @property
    def root(self) -> Node:
        return self._root

    def refresh(self) -> None:
        self.beginResetModel()
        self.endResetModel()

    def node(self, index: QtCore.QModelIndex) -> Node:
        if index.isValid():
            node = index.internalPointer()
            if node is not None:
                return node
        return self._root

    def index_for(self, node: Optional[Node]) -> QtCore.QModelIndex:
        if node is None or node is self._root or node.parent is None:
            return QtCore.QModelIndex()
        # Make sure the node still belongs to this tree.
        ancestor = node
        while ancestor is not None and ancestor is not self._root:
            ancestor = ancestor.parent
        if ancestor is None:
            return QtCore.QModelIndex()
        return self.createIndex(node.row(), 0, node)

    # -- structure -----------------------------------------------------
    def index(self, row, column, parent=QtCore.QModelIndex()):
        child = self.node(parent).child(row)
        if child is None or not 0 <= column < len(self._columns):
            return QtCore.QModelIndex()
        return self.createIndex(row, column, child)

    def parent(self, index=QtCore.QModelIndex()):
        if not index.isValid():
            return QtCore.QModelIndex()
        parent = self.node(index).parent
        if parent is None or parent is self._root:
            return QtCore.QModelIndex()
        return self.createIndex(parent.row(), 0, parent)

    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid() and parent.column() != 0:
            return 0
        return len(self.node(parent).children)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self._columns)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self._columns[section][0]
        return None

    # -- data ----------------------------------------------------------
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        node = self.node(index)
        column = index.column()
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return self._columns[column][1](node)
        if column != 0:
            return None
        if role == Qt.ItemDataRole.DecorationRole and node.warning:
            return self._warning_icon
        if role == Qt.ItemDataRole.ToolTipRole:
            return node.tooltip
        if role == Qt.ItemDataRole.FontRole and isinstance(node, (ShotNode, AnimBlockNode)):
            font = QtGui.QFont()
            font.setBold(True)
            return font
        if role == Qt.ItemDataRole.ForegroundRole:
            if isinstance(node, CharacterNode) and node.stack is not None:
                return QtGui.QBrush(ACCENT)
            if isinstance(node, RenderNode) and not node.step.enabled:
                return QtGui.QBrush(DISABLED)
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or not index.isValid() or self._rename_ref() is None:
            return False
        node = self.node(index)
        if not self._rename_ref()(node, str(value)):
            return False
        self.node_renamed.emit(node)
        return True

    def flags(self, index):
        flags = Qt.ItemFlag.ItemIsDropEnabled
        if not index.isValid():
            return flags
        flags |= Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled
        if index.column() == 0 and self._rename_ref() is not None and isinstance(self.node(index), (StackNode, RenderNode)):
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    # -- drag and drop -------------------------------------------------
    def supportedDragActions(self):
        return Qt.DropAction.CopyAction

    def supportedDropActions(self):
        return Qt.DropAction.CopyAction | Qt.DropAction.MoveAction

    def mimeTypes(self):
        return [MIME_TYPE]

    def mimeData(self, indexes):
        nodes: List[Node] = []
        for index in indexes:
            node = self.node(index)
            if index.isValid() and node not in nodes:
                nodes.append(node)
        _drag_payloads.clear()  # only one drag can be in flight
        key = str(next(_drag_counter))
        _drag_payloads[key] = nodes
        mime = QtCore.QMimeData()
        mime.setData(MIME_TYPE, QtCore.QByteArray(key.encode("ascii")))
        return mime

    def canDropMimeData(self, data, action, row, column, parent):
        return self._drop_ref() is not None and data.hasFormat(MIME_TYPE)

    def dropMimeData(self, data, action, row, column, parent):
        if not self.canDropMimeData(data, action, row, column, parent):
            return False
        key = bytes(data.data(MIME_TYPE)).decode("ascii")
        nodes = _drag_payloads.pop(key, [])
        # Dropping between rows counts as dropping on their parent.
        target = self.node(parent)
        if not self._drop_ref()(nodes, target):
            return False
        self.nodes_dropped.emit()
        # Drags only offer CopyAction, so Qt never removes rows from the breakdown.
        return True
