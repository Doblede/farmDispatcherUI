"""Pipeline graph view: shows a stack's steps; pan with the middle mouse, zoom with the wheel."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from farm_dispatcher.core.pipeline import Pipeline
from farm_dispatcher.qt import QAction, QtCore, QtGui, QtWidgets, Qt, Signal, exec_
from farm_dispatcher.ui.node_item import ArrowItem, StepItem


class GraphView(QtWidgets.QGraphicsView):
    step_selected = Signal(object)  # Step or None
    toggle_enable_requested = Signal(list)  # [StepItem]

    def __init__(self, parent=None):
        super().__init__(parent)
        # Parented to the view so Qt deletes it together with the view.
        self._scene = QtWidgets.QGraphicsScene(self)
        self._scene.setSceneRect(-2000, -2000, 4000, 4000)
        self.setScene(self._scene)
        self._scene.selectionChanged.connect(self._on_selection_changed)
        self.items_by_name: Dict[str, StepItem] = {}
        self.setRenderHints(QtGui.QPainter.RenderHint.Antialiasing | QtGui.QPainter.RenderHint.TextAntialiasing)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._pan_start: Optional[QtCore.QPoint] = None
        self._placeholder = "Select a stack to see its pipeline"

    # -- content ---------------------------------------------------------
    def show_pipeline(self, pipeline: Optional[Pipeline], enabled: Callable = lambda step: step.enabled) -> None:
        blocker = QtCore.QSignalBlocker(self._scene)
        self._scene.clear()
        self.items_by_name = {}
        del blocker
        if pipeline is None:
            self.viewport().update()
            return
        for step in pipeline.steps:
            item = StepItem(step, enabled(step))
            self._scene.addItem(item)
            self.items_by_name[step.name] = item
        for step in pipeline.steps:
            for target in step.arrows:
                if target in self.items_by_name:
                    self._scene.addItem(ArrowItem(self.items_by_name[step.name], self.items_by_name[target]))
        self.frame_all()

    def set_placeholder(self, text: str) -> None:
        self._placeholder = text
        self.viewport().update()

    def frame_all(self) -> None:
        if not self.items_by_name:
            return
        rect = QtCore.QRectF()
        for item in self.items_by_name.values():
            rect = rect.united(item.sceneBoundingRect())
        self.resetTransform()
        self.fitInView(rect.adjusted(-40, -40, 40, 40), Qt.AspectRatioMode.KeepAspectRatio)
        if self.transform().m11() > 1.5:
            self.resetTransform()
            self.scale(1.5, 1.5)
            self.centerOn(rect.center())

    def selected_step_items(self) -> List[StepItem]:
        return [i for i in self._scene.selectedItems() if isinstance(i, StepItem)]

    def _on_selection_changed(self):
        items = self.selected_step_items()
        self.step_selected.emit(items[0].step if len(items) == 1 else None)

    # -- painting --------------------------------------------------------
    def drawForeground(self, painter, rect):
        if self.items_by_name:
            return
        painter.save()
        painter.resetTransform()
        painter.setPen(self.palette().color(QtGui.QPalette.ColorRole.PlaceholderText))
        painter.drawText(self.viewport().rect(), Qt.AlignmentFlag.AlignCenter, self._placeholder)
        painter.restore()

    # -- interaction -----------------------------------------------------
    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, StepItem) and not item.isSelected():
            self._scene.clearSelection()
            item.setSelected(True)
        items = self.selected_step_items()
        menu = QtWidgets.QMenu(self)
        toggle = QAction("Toggle enable", menu)
        toggle.setEnabled(bool(items))
        frame = QAction("Frame all  (F)", menu)
        menu.addAction(toggle)
        menu.addAction(frame)
        chosen = exec_(menu, event.globalPos())
        if chosen is toggle:
            self.toggle_enable_requested.emit(items)
        elif chosen is frame:
            self.frame_all()

    def wheelEvent(self, event):
        factor = 1.0015 ** event.angleDelta().y()
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan_start is not None:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._pan_start is not None and event.button() == Qt.MouseButton.MiddleButton:
            self._pan_start = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F:
            self.frame_all()
            event.accept()
            return
        super().keyPressEvent(event)
