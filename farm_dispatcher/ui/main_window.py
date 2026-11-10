"""Main window.

Top: the shot breakdown, stacks and render setups; drag characters from the
breakdown into a stack or render. Bottom: the selected stack's pipeline graph and
the settings of the selected step. Settings changed while a character is
selected become overrides for that character only.
"""

from __future__ import annotations

import logging
import random
from typing import List, Optional

from farm_dispatcher.core import constants as c
from farm_dispatcher.core.backend import Backend, ShotNotFound
from farm_dispatcher.core.config import ConfigError, ConfigStore
from farm_dispatcher.core.export import SubmissionError, build_submission, submission_kinds, write_submission
from farm_dispatcher.core.node import Node
from farm_dispatcher.core.pipeline import Step
from farm_dispatcher.core.scene import (
    CharacterNode,
    CharacterRef,
    RenderNode,
    ResolvedAttribute,
    Session,
    StackNode,
    clear_override,
    remove_container,
    remove_ref,
    resolve_attributes,
    set_attribute,
    step_enabled,
)
from farm_dispatcher.core.statistics import UsageStats
from farm_dispatcher.qt import QAction, QtCore, QtGui, QtWidgets, Qt, exec_
from farm_dispatcher.ui import icon_path
from farm_dispatcher.ui.app_settings import AppSettings
from farm_dispatcher.ui.create_stack_dialog import CreateStackDialog
from farm_dispatcher.ui.graph_view import GraphView
from farm_dispatcher.ui.property_editor import PropertyEditor
from farm_dispatcher.ui.settings_dialog import SettingsDialog
from farm_dispatcher.ui.tree_model import NodeTreeModel, name_column
from farm_dispatcher.ui.tree_view import NodeTreeView

log = logging.getLogger(__name__)

LAUNCH_PHRASES = [
    "Wingardium leviosa! The magic is working now on the shot.",
    "Houston, we have sent a shot with no problem!!",
    "Yippee ki yay, shot launched!!",
    "Hakuna matata. Now you can work on another shot!!",
    "Shot launched. I've got a good feeling about this my padawan.",
    "Great Scott!! Another shot launched!",
    "Long life and prosperity to the shot!!",
    "They may take our lives, but they'll never take our shots!!",
    "Hasta la vista, baby.",
    "Just keep simming!!",
    "May the Dispatcher be with you.",
    "You have my Sword, and my Bow, and my Shot!!",
    "Shot sent, I'm the king of the world!",
    "I'm federal agent Jack Bauer. This is the longest sim of my life.",
]


def _stack_column(node: Node) -> str:
    return node.stack.name if isinstance(node, CharacterNode) and node.stack else ""


def _render_column(node: Node) -> str:
    return ", ".join(r.name for r in node.renders) if isinstance(node, CharacterNode) else ""


class MainWindow(QtWidgets.QMainWindow):
    def __init__(
        self,
        backend: Backend,
        settings: Optional[AppSettings] = None,
        stats: Optional[UsageStats] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Farm Dispatcher")
        self.setObjectName("FarmDispatcherMainWindow")
        self.resize(1400, 900)
        self.settings = settings or AppSettings()
        self.stats = stats or UsageStats()
        self.session = Session(ConfigStore(self.settings.config_paths), backend)

        # What the bottom half is showing.
        self._stack: Optional[StackNode] = None
        self._ref: Optional[CharacterRef] = None
        self._step: Optional[Step] = None
        self._render: Optional[RenderNode] = None

        self._build_ui()
        self._load_projects()
        self._load_preferences()
        self._report_config_errors()

    # =====================================================================
    # Layout
    # =====================================================================
    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout(central)
        root.addLayout(self._build_header())
        root.addWidget(self._build_shot_bar())

        top = QtWidgets.QSplitter(Qt.Orientation.Horizontal)
        top.addWidget(self._panel("Breakdown", self._build_breakdown()))
        top.addWidget(self._panel("Stacks", self._build_stacks()))
        top.addWidget(self._panel("Renders", self._build_renders()))
        top.setSizes([500, 350, 350])

        bottom = QtWidgets.QSplitter(Qt.Orientation.Horizontal)
        bottom.addWidget(self._build_graph_panel())
        self.properties = PropertyEditor()
        self.properties.value_changed.connect(self._on_value_changed)
        self.properties.reset_requested.connect(self._on_reset_override)
        bottom.addWidget(self._panel("Settings", self.properties))
        bottom.setSizes([800, 450])

        main = QtWidgets.QSplitter(Qt.Orientation.Vertical)
        main.addWidget(top)
        main.addWidget(bottom)
        main.setSizes([330, 520])
        root.addWidget(main, 1)
        root.addLayout(self._build_footer())
        self.setCentralWidget(central)

    @staticmethod
    def _panel(title: str, widget: QtWidgets.QWidget) -> QtWidgets.QWidget:
        box = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QtWidgets.QLabel("<b>{}</b>".format(title))
        layout.addWidget(label)
        layout.addWidget(widget, 1)
        return box

    def _build_header(self) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel()
        logo = QtGui.QPixmap(icon_path("logo.png"))
        if logo.isNull():
            title.setText("<span style='font-size: 22pt'>Farm Dispatcher</span>")
        else:
            title.setPixmap(logo.scaledToHeight(64, Qt.TransformationMode.SmoothTransformation))
        title.setToolTip("Farm Dispatcher")
        row.addWidget(title)
        row.addStretch(1)
        row.addWidget(QtWidgets.QLabel("Preferences:"))
        self.prefs_combo = QtWidgets.QComboBox()
        self.prefs_combo.setMinimumWidth(160)
        self.prefs_combo.activated.connect(self._on_preference_changed)
        row.addWidget(self.prefs_combo)
        settings_btn = QtWidgets.QToolButton()
        settings_btn.setIcon(QtGui.QIcon(icon_path("config_icon.png")))
        settings_btn.setIconSize(QtCore.QSize(24, 24))
        settings_btn.setAutoRaise(True)
        settings_btn.setToolTip("Settings")
        settings_btn.clicked.connect(self._open_settings)
        row.addWidget(settings_btn)
        return row

    def _build_shot_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QGroupBox()
        row = QtWidgets.QHBoxLayout(bar)
        row.addWidget(QtWidgets.QLabel("Project:"))
        self.project_combo = QtWidgets.QComboBox()
        row.addWidget(self.project_combo)
        row.addSpacing(12)
        row.addWidget(QtWidgets.QLabel("Seq:"))
        self.seq_edit = QtWidgets.QLineEdit(self.settings.last("sequence"))
        self.seq_edit.setMaximumWidth(110)
        self.seq_edit.returnPressed.connect(self._load_shot)
        row.addWidget(self.seq_edit)
        row.addWidget(QtWidgets.QLabel("Shot:"))
        self.shot_edit = QtWidgets.QLineEdit(self.settings.last("shot"))
        self.shot_edit.setMaximumWidth(110)
        self.shot_edit.returnPressed.connect(self._load_shot)
        row.addWidget(self.shot_edit)
        load = QtWidgets.QPushButton("Load")
        load.clicked.connect(self._load_shot)
        row.addWidget(load)
        reset = QtWidgets.QPushButton("Reset")
        reset.setToolTip("Clear the shot and all assignments")
        reset.clicked.connect(self._reset)
        row.addWidget(reset)
        row.addStretch(1)
        self.frames_label = QtWidgets.QLabel()
        row.addWidget(self.frames_label)
        return bar

    def _build_breakdown(self) -> QtWidgets.QWidget:
        self.breakdown_view = NodeTreeView()
        self.breakdown_model = NodeTreeModel(
            self.session.shot_root,
            [("Breakdown", name_column), ("Stack", _stack_column), ("Render", _render_column)],
            parent=self.breakdown_view,
        )
        self.breakdown_view.setModel(self.breakdown_model)
        self.breakdown_view.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.breakdown_view.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragOnly)
        self.breakdown_view.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.breakdown_view.setColumnWidth(0, 220)
        self.breakdown_view.setToolTip("Drag characters, anim blocks or the whole shot into a stack or render")
        return self.breakdown_view

    def _drop_target_view(self, root: Node, on_current) -> NodeTreeView:
        view = NodeTreeView()
        model = NodeTreeModel(root, [(root.name, name_column)], self._on_drop, self._on_rename, parent=view)
        model.nodes_dropped.connect(self._refresh_trees)
        model.node_renamed.connect(self._on_renamed)
        view.setModel(model)
        view.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DropOnly)
        view.setDropIndicatorShown(True)
        view.current_node_changed.connect(on_current)
        view.deselected.connect(self._clear_selection)
        view.delete_requested.connect(self._remove_node)
        view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        return view

    def _build_stacks(self) -> QtWidgets.QWidget:
        self.stack_view = self._drop_target_view(self.session.stacks_root, self._on_stack_node)
        self.stack_view.customContextMenuRequested.connect(self._stack_menu)
        return self.stack_view

    def _build_renders(self) -> QtWidgets.QWidget:
        self.render_view = self._drop_target_view(self.session.renders_root, self._on_render_node)
        self.render_view.customContextMenuRequested.connect(self._render_menu)
        return self.render_view

    def _build_graph_panel(self) -> QtWidgets.QWidget:
        box = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        row = QtWidgets.QHBoxLayout()
        self.selection_label = QtWidgets.QLabel()
        font = self.selection_label.font()
        font.setPointSize(font.pointSize() + 2)
        font.setBold(True)
        self.selection_label.setFont(font)
        row.addWidget(self.selection_label)
        row.addStretch(1)
        self.stack_type_label = QtWidgets.QLabel("Type of stack:")
        row.addWidget(self.stack_type_label)
        self.stack_type_combo = QtWidgets.QComboBox()
        self.stack_type_combo.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.stack_type_combo.activated.connect(self._on_stack_type_changed)
        row.addWidget(self.stack_type_combo)
        layout.addLayout(row)
        self.graph = GraphView()
        self.graph.step_selected.connect(self._on_step_selected)
        self.graph.toggle_enable_requested.connect(self._toggle_enable)
        layout.addWidget(self.graph, 1)
        hint = QtWidgets.QLabel("Middle-drag to pan · wheel to zoom · F to frame · right-click to enable/disable")
        hint.setEnabled(False)
        layout.addWidget(hint)
        self._set_stack_controls_visible(False)
        return box

    def _build_footer(self) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()
        self.farm_label = QtWidgets.QLabel()
        row.addWidget(self.farm_label)
        row.addStretch(1)
        self.launch_btn = QtWidgets.QPushButton("Launch")
        self.launch_btn.setDefault(True)
        self.launch_btn.setMinimumSize(140, 36)
        self.launch_btn.clicked.connect(self._launch)
        row.addWidget(self.launch_btn)
        self._update_farm_label()
        return row

    # =====================================================================
    # Loading
    # =====================================================================
    def _load_projects(self) -> None:
        self.project_combo.clear()
        self.project_combo.addItems(self.session.backend.projects())
        last = self.project_combo.findText(self.settings.last("project"))
        if last >= 0:
            self.project_combo.setCurrentIndex(last)

    def _load_preferences(self) -> None:
        names = self.session.config.preference_names()
        self.prefs_combo.clear()
        self.prefs_combo.addItems(names)
        if not names:
            self.statusBar().showMessage("No preferences found. Check the folders in Settings.")
            return
        last = self.settings.last("preference")
        self.prefs_combo.setCurrentIndex(max(0, self.prefs_combo.findText(last)))
        self._apply_preference(self.prefs_combo.currentText())

    def _apply_preference(self, name: str) -> None:
        try:
            self.session.set_preference(name)
        except ConfigError as exc:
            self._error("Preference problem", str(exc))
        self.settings.set_last("preference", name)
        self._refresh_trees()
        self._clear_selection()

    def _on_preference_changed(self, _index=None) -> None:
        name = self.prefs_combo.currentText()
        if name == self.session.preference:
            return
        if self._has_assignments() and not self._confirm(
            "Change preference",
            "Changing the preference resets all stacks and renders. Continue?",
        ):
            self.prefs_combo.setCurrentText(self.session.preference or "")
            return
        self._apply_preference(name)

    def _report_config_errors(self) -> None:
        if self.session.config.errors:
            self.statusBar().showMessage(" · ".join(self.session.config.errors))

    def _load_shot(self) -> None:
        project = self.project_combo.currentText()
        seq, shot = self.seq_edit.text().strip(), self.shot_edit.text().strip()
        if self._has_assignments() and not self._confirm(
            "Load shot", "Loading a shot resets all stacks and renders. Continue?"
        ):
            return
        try:
            info = self.session.load_shot(project, seq, shot)
        except ShotNotFound as exc:
            self.statusBar().showMessage(str(exc), 5000)
            return
        except ConfigError as exc:
            self._error("Configuration problem", str(exc))
            return
        except Exception as exc:  # backend errors are studio code: report, don't crash
            log.exception("Loading shot failed")
            self._error("Could not load the shot", str(exc))
            return
        for key, value in (("project", project), ("sequence", seq), ("shot", shot)):
            self.settings.set_last(key, value)
        self.frames_label.setText("Frames {} – {}".format(*info.frame_range))
        self._refresh_trees()
        self._clear_selection()
        missing = [ch.name for ch in self.session.characters() if ch.warning]
        message = "Loaded {}.{}: {} characters".format(info.sequence, info.shot, len(info.characters))
        if missing:
            message += " · no hairstyle: " + ", ".join(missing)
        self.statusBar().showMessage(message)

    def _reset(self) -> None:
        if self._has_assignments() and not self._confirm("Reset", "Clear the shot and all assignments?"):
            return
        self.session.clear_shot()
        self.seq_edit.clear()
        self.shot_edit.clear()
        self.frames_label.clear()
        self._refresh_trees()
        self._clear_selection()

    def _has_assignments(self) -> bool:
        return any(s.refs() for s in self.session.stacks())

    # =====================================================================
    # Trees
    # =====================================================================
    def _refresh_trees(self) -> None:
        for view in (self.breakdown_view, self.stack_view, self.render_view):
            view.refresh()
        self.breakdown_view.resizeColumnToContents(1)

    def _on_drop(self, nodes: List[Node], target: Node) -> bool:
        try:
            return self.session.drop(nodes, target)
        except ConfigError as exc:
            self._error("Configuration problem", str(exc))
            return False

    def _on_rename(self, node: Node, name: str) -> bool:
        return self.session.rename(node, name)

    def _on_renamed(self, node: Node) -> None:
        self._refresh_trees()
        if node is self._stack or node is self._render:
            self._update_selection_label()

    def _stack_menu(self, pos) -> None:
        node = self.stack_view.current_node() if self.stack_view.indexAt(pos).isValid() else None
        menu = QtWidgets.QMenu(self)
        actions = {}
        if isinstance(node, CharacterRef):
            actions[menu.addAction("Remove {} from stack".format(node.name))] = lambda: self._remove_node(node)
        elif isinstance(node, StackNode):
            actions[menu.addAction("Rename")] = lambda: self.stack_view.edit(self.stack_view.currentIndex())
            actions[menu.addAction("Delete stack")] = lambda: self._remove_node(node)
        else:
            actions[menu.addAction("New stack…")] = self._new_stack
        chosen = exec_(menu, self.stack_view.viewport().mapToGlobal(pos))
        if chosen in actions:
            actions[chosen]()

    def _render_menu(self, pos) -> None:
        node = self.render_view.current_node() if self.render_view.indexAt(pos).isValid() else None
        menu = QtWidgets.QMenu(self)
        actions = {}
        if isinstance(node, CharacterRef):
            actions[menu.addAction("Remove {} from render".format(node.name))] = lambda: self._remove_node(node)
        elif isinstance(node, RenderNode):
            actions[menu.addAction("Rename")] = lambda: self.render_view.edit(self.render_view.currentIndex())
            actions[menu.addAction("Delete render")] = lambda: self._remove_node(node)
        else:
            actions[menu.addAction("New render")] = self._new_render
        chosen = exec_(menu, self.render_view.viewport().mapToGlobal(pos))
        if chosen in actions:
            actions[chosen]()

    def _new_stack(self) -> None:
        answer = CreateStackDialog.ask(
            self.session.stack_types(), [s.name for s in self.session.stacks()], self
        )
        if answer is None:
            return
        try:
            stack = self.session.add_stack(*answer)
        except ConfigError as exc:
            self._error("Could not create the stack", str(exc))
            return
        self._refresh_trees()
        self.stack_view.select_node(stack)

    def _new_render(self) -> None:
        try:
            render = self.session.add_render()
        except ConfigError as exc:
            self._error("Could not create the render", str(exc))
            return
        self._refresh_trees()
        self.render_view.select_node(render)

    def _remove_node(self, node: Node) -> None:
        if isinstance(node, CharacterRef):
            remove_ref(node)
        elif isinstance(node, (StackNode, RenderNode)):
            if node.children and not self._confirm(
                "Delete", "Delete {} and release its {} character(s)?".format(node.name, len(node.children))
            ):
                return
            remove_container(node)
        else:
            return
        self._refresh_trees()
        self._clear_selection()

    # =====================================================================
    # Selection
    # =====================================================================
    def _clear_selection(self) -> None:
        self._stack = self._ref = self._step = self._render = None
        self.graph.show_pipeline(None)
        self.properties.show_message("Select a step or a render to edit its settings")
        self._set_stack_controls_visible(False)
        self._update_selection_label()

    def _on_stack_node(self, node: Node) -> None:
        self.render_view.clear_current()
        self._render = None
        self._step = None
        self._ref = node if isinstance(node, CharacterRef) else None
        stack = node.parent if self._ref else node
        if not isinstance(stack, StackNode):
            self._clear_selection()
            return
        self._stack = stack
        self._set_stack_controls_visible(True)
        self.stack_type_combo.clear()
        self.stack_type_combo.addItems(list(self.session.stack_types()))
        self.stack_type_combo.setCurrentText(stack.stack_type)
        self.stack_type_combo.setEnabled(self._ref is None)
        self.graph.show_pipeline(stack.pipeline, lambda step: step_enabled(step, self._ref))
        self.properties.show_message("Select a step in the graph to edit its settings")
        self._update_selection_label()

    def _on_render_node(self, node: Node) -> None:
        self.stack_view.clear_current()
        render = node.parent if isinstance(node, CharacterRef) else node
        if not isinstance(render, RenderNode):
            self._clear_selection()
            return
        self._stack = self._ref = self._step = None
        self._render = render
        self.graph.show_pipeline(None)
        self.graph.set_placeholder("Render setups have no pipeline graph")
        self._set_stack_controls_visible(False)
        self._update_selection_label()
        self._show_render_properties()

    def _on_step_selected(self, step: Optional[Step]) -> None:
        self._step = step
        self._show_step_properties()

    def _set_stack_controls_visible(self, visible: bool) -> None:
        self.stack_type_label.setVisible(visible)
        self.stack_type_combo.setVisible(visible)
        if not visible:
            self.graph.set_placeholder("Select a stack to see its pipeline")

    def _update_selection_label(self) -> None:
        if self._ref is not None:
            text = "{}  ›  <span style='color:#3d8bfd'>{}</span>".format(self._stack.name, self._ref.name)
        elif self._stack is not None:
            text = self._stack.name
        elif self._render is not None:
            text = self._render.name
        else:
            text = "Nothing selected"
        self.selection_label.setText(text)

    def _on_stack_type_changed(self, _index=None) -> None:
        if self._stack is None:
            return
        new_type = self.stack_type_combo.currentText()
        if new_type == self._stack.stack_type:
            return
        try:
            self.session.change_stack_type(self._stack, new_type)
        except ConfigError as exc:
            self._error("Could not change the stack type", str(exc))
            return
        self._on_stack_node(self._stack)

    # =====================================================================
    # Properties
    # =====================================================================
    def _show_step_properties(self) -> None:
        if self._step is None:
            self.properties.show_message("Select a step in the graph to edit its settings")
            return
        if self._ref is not None:
            subtitle = "Changes apply to {} only (highlighted values are overridden).".format(self._ref.name)
        else:
            subtitle = "Changes apply to every character in {}.".format(self._stack.name)
        self.properties.show_attributes(
            self._step.name,
            subtitle,
            [("attributes", self._step.node_type, resolve_attributes(self._step, self._ref))],
            can_override=self._ref is not None,
        )

    def _show_render_properties(self) -> None:
        step = self._render.step
        sections = [("attributes", "Render scene", [ResolvedAttribute(a) for a in step.attributes.values()])]
        if step.value(c.SUBMIT_RENDER) and step.submit:
            sections.append(("submit", "Farm render", [ResolvedAttribute(a) for a in step.submit.values()]))
        self.properties.show_attributes(self._render.name, "", sections)

    def _on_value_changed(self, section: str, name: str, value) -> None:
        if self._render is not None:
            set_attribute(self._render.step, name, value)
            if name == c.SUBMIT_RENDER:
                self._show_render_properties()
            if name == c.ENABLE:
                self.render_view.refresh()
            return
        if self._step is None:
            return
        set_attribute(self._step, name, value, self._ref)
        if self._ref is not None:
            self.properties.mark_overridden(name, True)
        if name == c.ENABLE:
            item = self.graph.items_by_name.get(self._step.name)
            if item:
                item.set_enabled(step_enabled(self._step, self._ref))

    def _on_reset_override(self, name: str) -> None:
        if self._step is None or self._ref is None:
            return
        clear_override(self._step, name, self._ref)
        item = self.graph.items_by_name.get(self._step.name)
        if item:
            item.set_enabled(step_enabled(self._step, self._ref))
        self._show_step_properties()

    def _toggle_enable(self, items) -> None:
        for item in items:
            set_attribute(item.step, c.ENABLE, not step_enabled(item.step, self._ref), self._ref)
            item.set_enabled(step_enabled(item.step, self._ref))
        if self._step is not None:
            self._show_step_properties()

    # =====================================================================
    # Settings and launch
    # =====================================================================
    def _update_farm_label(self) -> None:
        self.farm_label.setText("Farm: <b>{}</b>  ·  Output: {}".format(self.settings.farm, self.settings.publish_dir))

    def _open_settings(self) -> None:
        old_paths = self.settings.config_paths
        if exec_(SettingsDialog(self.settings, self)) != QtWidgets.QDialog.DialogCode.Accepted:
            return
        self._update_farm_label()
        if self.settings.config_paths != old_paths:
            self.session.config.paths = self.settings.config_paths
            self.session.config.reload()
            self._load_preferences()
            self._report_config_errors()

    def _launch(self) -> None:
        farm = self.settings.farm
        try:
            submission = build_submission(self.session, c.FARMS[farm])
        except SubmissionError as exc:
            QtWidgets.QMessageBox.information(self, "Nothing to launch", str(exc))
            return
        n_chars = sum(1 for ch in submission["characters"] if ch["jobs"])
        n_scenes = len(submission["render_scenes"])
        if not self._confirm(
            "Launch",
            "Submit {} character(s) and {} render scene(s) for {}.{} to the {} farm?".format(
                n_chars, n_scenes, submission["sequence"], submission["shot"], farm
            ),
        ):
            return
        try:
            path = write_submission(submission, self.settings.publish_dir)
        except OSError as exc:
            log.exception("Writing the submission failed")
            self._error("Launch failed", "Could not write the submission:\n{}".format(exc))
            return
        for kind in submission_kinds(submission):
            self.stats.record_launch(kind, self.session.shot.code)
        self.statusBar().showMessage("Submission written to {}".format(path))
        QtWidgets.QMessageBox.information(
            self, "Launched!", "{}\n\n{}".format(random.choice(LAUNCH_PHRASES), path)
        )

    # =====================================================================
    # Helpers
    # =====================================================================
    def _confirm(self, title: str, text: str) -> bool:
        buttons = QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        answer = QtWidgets.QMessageBox.question(self, title, text, buttons)
        return answer == QtWidgets.QMessageBox.StandardButton.Yes

    def _error(self, title: str, text: str) -> None:
        QtWidgets.QMessageBox.warning(self, title, text)
