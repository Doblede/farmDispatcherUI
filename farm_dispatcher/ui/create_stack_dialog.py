"""Dialog asking for a new stack's name and type."""

from __future__ import annotations

from typing import Iterable, Optional, Tuple

from farm_dispatcher.qt import QtWidgets, exec_


class CreateStackDialog(QtWidgets.QDialog):
    def __init__(self, stack_types: Iterable[str], taken_names: Iterable[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("New stack")
        self._taken = set(taken_names)
        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Hero hair")
        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems(list(stack_types))
        self._error = QtWidgets.QLabel()
        self._error.setStyleSheet("color: #dc4646;")

        self._buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        form = QtWidgets.QFormLayout(self)
        form.addRow("Stack name:", self.name_edit)
        form.addRow("Type of stack:", self.type_combo)
        form.addRow(self._error)
        form.addRow(self._buttons)
        self.name_edit.textChanged.connect(self._validate)
        self._validate()

    def _validate(self) -> None:
        name = self.name_edit.text().strip()
        error = "That name is already used" if name in self._taken else ""
        self._error.setText(error)
        ok = self._buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        ok.setEnabled(bool(name) and not error and self.type_combo.count() > 0)

    @classmethod
    def ask(cls, stack_types, taken_names, parent=None) -> Optional[Tuple[str, str]]:
        dialog = cls(stack_types, taken_names, parent)
        if exec_(dialog) == QtWidgets.QDialog.DialogCode.Accepted:
            return dialog.name_edit.text().strip(), dialog.type_combo.currentText()
        return None
