"""Graphics items for the pipeline graph: step nodes and the arrows between them."""

from __future__ import annotations

import math
from typing import List

from farm_dispatcher.core.pipeline import Step
from farm_dispatcher.qt import QtCore, QtGui, QtWidgets, Qt

PADDING_X = 14
HEIGHT = 34
RADIUS = 10
# Layout files were authored for smaller nodes; spread them out to avoid overlaps.
LAYOUT_SCALE = (1.6, 1.25)


class StepItem(QtWidgets.QGraphicsObject):
    """A pipeline step. ``pos`` is its top-centre, matching the layout files."""

    def __init__(self, step: Step, enabled: bool = True):
        super().__init__()
        self.step = step
        self._enabled = enabled
        self.arrows: List[ArrowItem] = []
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._font = QtGui.QFont()
        self._font.setPointSize(10)
        width = QtGui.QFontMetrics(self._font).horizontalAdvance(step.name) + 2 * PADDING_X
        self._rect = QtCore.QRectF(-width / 2, 0, width, HEIGHT)
        self.setPos(step.pos[0] * LAYOUT_SCALE[0], step.pos[1] * LAYOUT_SCALE[1])
        self.setToolTip("{}\n{} ({})".format(step.name, step.node_type, step.group or "no group"))

    # -- state -----------------------------------------------------------
    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.update()

    def top_center(self) -> QtCore.QPointF:
        return self.mapToScene(QtCore.QPointF(0, 0))

    def bottom_center(self) -> QtCore.QPointF:
        return self.mapToScene(QtCore.QPointF(0, HEIGHT))

    # -- painting --------------------------------------------------------
    def boundingRect(self):
        return self._rect.adjusted(-3, -3, 3, 3)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        rgba = self.step.color[0] if self.step.color else (23, 144, 246, 255)
        fill = QtGui.QColor(*rgba)
        if self._enabled:
            painter.setBrush(fill)
            text_color = QtGui.QColor(Qt.GlobalColor.white)
        else:
            painter.setBrush(QtGui.QBrush(QtGui.QColor(150, 150, 150), Qt.BrushStyle.BDiagPattern))
            text_color = QtGui.QColor(110, 110, 110)
        selected = self.isSelected()
        pen = QtGui.QPen(QtGui.QColor(255, 200, 0) if selected else fill.darker(140), 3 if selected else 1.5)
        painter.setPen(pen)
        painter.drawRoundedRect(self._rect, RADIUS, RADIUS)
        painter.setPen(text_color)
        font = QtGui.QFont(self._font)
        font.setStrikeOut(not self._enabled)
        painter.setFont(font)
        painter.drawText(self._rect, Qt.AlignmentFlag.AlignCenter, self.step.name)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for arrow in self.arrows:
                arrow.update_path()
        return super().itemChange(change, value)


class ArrowItem(QtWidgets.QGraphicsPathItem):
    """Arrow from the bottom of one step to the top of another."""

    HEAD = 7.0

    def __init__(self, source: StepItem, target: StepItem):
        super().__init__()
        self.source = source
        self.target = target
        source.arrows.append(self)
        target.arrows.append(self)
        self.setZValue(-1)
        color = QtGui.QColor(140, 140, 140)
        self.setPen(QtGui.QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        self.setBrush(color)
        self.update_path()

    def update_path(self) -> None:
        start = self.source.bottom_center()
        end = self.target.top_center()
        path = QtGui.QPainterPath(start)
        path.lineTo(end)
        dx, dy = end.x() - start.x(), end.y() - start.y()
        if math.hypot(dx, dy) > 1:
            angle = math.atan2(dy, dx)
            for side in (-1, 1):
                a = angle + math.pi + side * math.pi / 7
                path.moveTo(end)
                path.lineTo(end.x() + self.HEAD * math.cos(a), end.y() + self.HEAD * math.sin(a))
        self.setPath(path)
