"""Attribute editor: one widget per attribute type, one code path for reading values back."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from farm_dispatcher.core import constants as c
from farm_dispatcher.core.pipeline import Attribute
from farm_dispatcher.core.scene import ResolvedAttribute
from farm_dispatcher.qt import QAction, QtCore, QtGui, QtWidgets, Qt, Signal, exec_
from farm_dispatcher.ui.tree_model import ACCENT

Emit = Callable[[Any], None]

INT_RANGE = (-1_000_000, 10_000_000)
FLOAT_RANGE = (-1_000_000.0, 1_000_000.0)


def _bool_widget(attr: Attribute, emit: Emit) -> QtWidgets.QWidget:
    w = QtWidgets.QCheckBox()
    w.setChecked(bool(attr.value))
    w.toggled.connect(emit)
    return w


def _int_widget(attr: Attribute, emit: Emit) -> QtWidgets.QWidget:
    w = QtWidgets.QSpinBox()
    w.setRange(*INT_RANGE)
    w.setValue(int(attr.value or 0))
    w.setKeyboardTracking(False)
    w.valueChanged.connect(emit)
    return w


def _float_widget(attr: Attribute, emit: Emit) -> QtWidgets.QWidget:
    w = QtWidgets.QDoubleSpinBox()
    w.setRange(*FLOAT_RANGE)
    w.setDecimals(3)
    w.setSingleStep(0.01)
    w.setValue(float(attr.value or 0.0))
    w.setKeyboardTracking(False)
    w.valueChanged.connect(emit)
    return w


def _list_widget(attr: Attribute, emit: Emit) -> QtWidgets.QWidget:
    w = QtWidgets.QComboBox()
    w.addItems([str(o) for o in attr.options])
    w.setCurrentIndex(max(0, w.findText(str(attr.value))))
    w.textActivated.connect(emit)
    return w


def _components_widget(attr: Attribute, emit: Emit) -> QtWidgets.QWidget:
    box = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    if not attr.options:
        hint = QtWidgets.QLabel("Select a character to choose components")
        hint.setEnabled(False)
        layout.addWidget(hint)
        return box
    selected = set(attr.value or [])
    checks: List[QtWidgets.QCheckBox] = []

    def changed(_=None):
        emit([cb.text() for cb in checks if cb.isChecked()])

    for option in attr.options:
        cb = QtWidgets.QCheckBox(str(option))
        cb.setChecked(option in selected)
        cb.toggled.connect(changed)
        checks.append(cb)
        layout.addWidget(cb)
    return box


def _path_widget(attr: Attribute, emit: Emit) -> QtWidgets.QWidget:
    box = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    edit = QtWidgets.QLineEdit(str(attr.value or ""))
    edit.setPlaceholderText("automatic")
    edit.setReadOnly(not attr.editable)
    edit.setToolTip(attr.meta.get("description", ""))
    browse = QtWidgets.QToolButton()
    browse.setText("…")
    browse.setToolTip("Browse for a file")
    browse.setEnabled(attr.editable)

    def commit():
        emit(edit.text().strip().replace("\\", "/"))

    def pick():
        path, _ = QtWidgets.QFileDialog.getOpenFileName(box, "Choose file", edit.text())
        if path:
            edit.setText(path)
            commit()

    edit.editingFinished.connect(commit)
    browse.clicked.connect(pick)
    layout.addWidget(edit, 1)
    layout.addWidget(browse)
    return box


def _string_widget(attr: Attribute, emit: Emit) -> QtWidgets.QWidget:
    w = QtWidgets.QLineEdit("" if attr.value is None else str(attr.value))
    w.editingFinished.connect(lambda: emit(w.text()))
    return w


WIDGETS: Dict[str, Callable[[Attribute, Emit], QtWidgets.QWidget]] = {
    c.ATTR_BOOL: _bool_widget,
    c.ATTR_INT: _int_widget,
    c.ATTR_FLOAT: _float_widget,
    c.ATTR_LIST: _list_widget,
    c.ATTR_HAIR_COMPONENTS: _components_widget,
    c.ATTR_PATH: _path_widget,
}


class PropertyEditor(QtWidgets.QScrollArea):
    """Shows sections of attributes and reports edits.

    ``value_changed(section, name, value)`` fires on every edit;
    ``reset_requested(name)`` when the artist resets a character override.
    """

    value_changed = Signal(str, str, object)
    reset_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self._labels: Dict[str, QtWidgets.QLabel] = {}
        self.show_message("Select a step or a render to edit its settings")

    def show_message(self, text: str) -> None:
        self._labels = {}
        label = QtWidgets.QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        label.setEnabled(False)
        self.setWidget(label)

    def show_attributes(
        self,
        title: str,
        subtitle: str,
        sections: Sequence[Tuple[str, str, List[ResolvedAttribute]]],
        can_override: bool = False,
    ) -> None:
        """sections: (key, heading, attributes). Keys are passed back in value_changed."""
        self._labels = {}
        page = QtWidgets.QWidget()
        outer = QtWidgets.QVBoxLayout(page)
        heading = QtWidgets.QLabel("<b>{}</b>".format(title))
        heading.setStyleSheet("font-size: 13pt;")
        outer.addWidget(heading)
        if subtitle:
            sub = QtWidgets.QLabel(subtitle)
            sub.setWordWrap(True)
            sub.setEnabled(False)
            outer.addWidget(sub)
        for key, section_title, attrs in sections:
            group = QtWidgets.QGroupBox(section_title)
            form = QtWidgets.QFormLayout(group)
            form.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
            for resolved in attrs:
                attr = resolved.attribute
                label = QtWidgets.QLabel(attr.name)
                self._labels[attr.name] = label
                if can_override:
                    self._make_resettable(label, attr.name)
                    self.mark_overridden(attr.name, resolved.overridden)

                def emit(value, _key=key, _name=attr.name):
                    self.value_changed.emit(_key, _name, value)

                factory = WIDGETS.get(attr.type, _string_widget)
                form.addRow(label, factory(attr, emit))
            outer.addWidget(group)
        outer.addStretch(1)
        self.setWidget(page)

    def mark_overridden(self, name: str, overridden: bool) -> None:
        label = self._labels.get(name)
        if label is None:
            return
        font = label.font()
        font.setBold(overridden)
        label.setFont(font)
        palette = label.palette()
        default = self.palette().color(QtGui.QPalette.ColorRole.WindowText)
        palette.setColor(QtGui.QPalette.ColorRole.WindowText, ACCENT if overridden else default)
        label.setPalette(palette)
        label.setToolTip(
            "Overridden for this character. Right-click to reset." if overridden
            else "Same as the stack. Editing it overrides it for this character only."
        )

    def _make_resettable(self, label: QtWidgets.QLabel, name: str) -> None:
        label.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        def menu(pos):
            m = QtWidgets.QMenu(label)
            reset = QAction("Reset to stack value", m)
            reset.setEnabled(label.font().bold())
            m.addAction(reset)
            if exec_(m, label.mapToGlobal(pos)) is reset:
                self.reset_requested.emit(name)

        label.customContextMenuRequested.connect(menu)
