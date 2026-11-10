"""Tree view used for the breakdown, stacks and renders panels."""

from __future__ import annotations

from typing import Optional

from farm_dispatcher.core.node import Node
from farm_dispatcher.qt import QtCore, QtWidgets, Qt, Signal


class NodeTreeView(QtWidgets.QTreeView):
    deselected = Signal()
    current_node_changed = Signal(object)
    delete_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setUniformRowHeights(True)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.DoubleClicked
            | QtWidgets.QAbstractItemView.EditTrigger.EditKeyPressed
        )

    def setModel(self, model):
        super().setModel(model)
        self.selectionModel().currentChanged.connect(self._on_current_changed)
        model.modelReset.connect(self.expandAll)

    def current_node(self) -> Optional[Node]:
        index = self.currentIndex()
        return self.model().node(index) if index.isValid() else None

    def select_node(self, node: Optional[Node]) -> None:
        index = self.model().index_for(node)
        if index.isValid():
            self.setCurrentIndex(index)
            self.scrollTo(index)
        else:
            self.clear_current()

    def clear_current(self) -> None:
        self.selectionModel().clearSelection()
        self.selectionModel().setCurrentIndex(
            QtCore.QModelIndex(), QtCore.QItemSelectionModel.SelectionFlag.NoUpdate
        )

    def refresh(self) -> None:
        """Rebuild from the node tree, keeping the current node selected."""
        current = self.current_node()
        blocker = QtCore.QSignalBlocker(self.selectionModel())
        self.model().refresh()
        index = self.model().index_for(current)
        if index.isValid():
            self.setCurrentIndex(index)
        del blocker

    def _on_current_changed(self, current, _previous):
        if current.isValid():
            self.current_node_changed.emit(self.model().node(current))

    def mousePressEvent(self, event):
        if not self.indexAt(event.pos()).isValid():
            self.clear_current()
            self.deselected.emit()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        node = self.current_node()
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and node is not None:
            self.delete_requested.emit(node)
            event.accept()
            return
        super().keyPressEvent(event)
