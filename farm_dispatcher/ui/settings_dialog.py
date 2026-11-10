"""Settings dialog: config directories, output folder and target farm."""

from __future__ import annotations

from pathlib import Path

from farm_dispatcher.core import constants as c
from farm_dispatcher.core.config import ConfigPaths
from farm_dispatcher.core.export import default_publish_dir
from farm_dispatcher.qt import QtGui, QtWidgets
from farm_dispatcher.ui import icon_path
from farm_dispatcher.ui.app_settings import AppSettings


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(620)
        self._settings = settings

        self._prefs = self._path_row()
        self._stacks = self._path_row()
        self._nodes = self._path_row()
        self._publish = self._path_row()

        dirs = QtWidgets.QGroupBox("Configuration folders")
        form = QtWidgets.QFormLayout(dirs)
        form.addRow("Preferences:", self._prefs[0])
        form.addRow("Stack layouts:", self._stacks[0])
        form.addRow("Node types:", self._nodes[0])

        output = QtWidgets.QGroupBox("Submission")
        out_form = QtWidgets.QFormLayout(output)
        out_form.addRow("Write submissions to:", self._publish[0])
        farm_row = QtWidgets.QHBoxLayout()
        self._farm_buttons = {}
        for farm in c.FARMS:
            button = QtWidgets.QRadioButton(farm)
            self._farm_buttons[farm] = button
            farm_row.addWidget(button)
        farm_row.addStretch(1)
        out_form.addRow("Farm:", farm_row)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
            | QtWidgets.QDialogButtonBox.StandardButton.RestoreDefaults
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        buttons.button(QtWidgets.QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(
            self._restore_defaults
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(dirs)
        layout.addWidget(output)
        layout.addWidget(buttons)
        self._load(settings.config_paths, settings.publish_dir, settings.farm)

    def _path_row(self):
        row = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        edit = QtWidgets.QLineEdit()
        browse = QtWidgets.QToolButton()
        browse.setIcon(QtGui.QIcon(icon_path("folder_icon.png")))
        browse.setToolTip("Browse")

        def pick():
            path = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose folder", edit.text())
            if path:
                edit.setText(path)

        browse.clicked.connect(pick)
        layout.addWidget(edit, 1)
        layout.addWidget(browse)
        return row, edit

    def _load(self, paths: ConfigPaths, publish: Path, farm: str) -> None:
        self._prefs[1].setText(str(paths.preferences))
        self._stacks[1].setText(str(paths.stacks))
        self._nodes[1].setText(str(paths.nodes))
        self._publish[1].setText(str(publish))
        self._farm_buttons.get(farm, self._farm_buttons[c.DEFAULT_FARM]).setChecked(True)

    def _restore_defaults(self) -> None:
        self._load(ConfigPaths.default(), default_publish_dir(), c.DEFAULT_FARM)

    def _save(self) -> None:
        paths = ConfigPaths(
            Path(self._prefs[1].text().strip()),
            Path(self._stacks[1].text().strip()),
            Path(self._nodes[1].text().strip()),
        )
        missing = [str(p) for p in (paths.preferences, paths.stacks, paths.nodes) if not p.is_dir()]
        if missing:
            QtWidgets.QMessageBox.warning(self, "Folder not found", "These folders don't exist:\n\n" + "\n".join(missing))
            return
        if paths == ConfigPaths.default():
            self._settings.reset_config_paths()
        else:
            self._settings.config_paths = paths
        self._settings.publish_dir = Path(self._publish[1].text().strip() or str(default_publish_dir()))
        self._settings.farm = next(f for f, b in self._farm_buttons.items() if b.isChecked())
        self.accept()
