"""End-to-end checks of the main window, run offscreen."""

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
qt = pytest.importorskip("farm_dispatcher.qt")
QtCore, QtWidgets = qt.QtCore, qt.QtWidgets

from farm_dispatcher.core.backend import DemoBackend  # noqa: E402
from farm_dispatcher.core.scene import CharacterRef, StackNode  # noqa: E402
from farm_dispatcher.ui.app_settings import AppSettings  # noqa: E402
from farm_dispatcher.ui.main_window import MainWindow  # noqa: E402
from farm_dispatcher.ui.tree_model import NodeTreeModel  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def window(app, tmp_path, monkeypatch):
    # Auto-answer dialogs.
    monkeypatch.setattr(QtWidgets.QMessageBox, "question",
                        lambda *a, **k: QtWidgets.QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning",
                        lambda *a, **k: pytest.fail("unexpected warning: {}".format(a[1:])))
    settings = AppSettings(QtCore.QSettings(str(tmp_path / "settings.ini"), QtCore.QSettings.Format.IniFormat))
    settings.publish_dir = tmp_path / "out"
    w = MainWindow(DemoBackend(), settings=settings)
    w.prefs_combo.setCurrentText("cfx_artist")
    w._on_preference_changed()
    w.seq_edit.setText("seq010")
    w.shot_edit.setText("0050")
    w._load_shot()
    yield w
    w.close()
    w.deleteLater()
    QtWidgets.QApplication.processEvents()


def drag(source: NodeTreeModel, nodes, target_model: NodeTreeModel, target_node):
    indexes = [source.index_for(n) for n in nodes]
    mime = source.mimeData(indexes)
    return target_model.dropMimeData(mime, QtCore.Qt.DropAction.CopyAction, -1, -1,
                                     target_model.index_for(target_node))


def test_load_shot_fills_breakdown(window):
    model = window.breakdown_model
    shot = model.index(0, 0)
    assert model.data(shot) == "seq010.0050"
    assert model.rowCount(shot) == 3
    assert "Frames 101" in window.frames_label.text()


def test_drag_from_breakdown_to_stack(window):
    session = window.session
    stack = session.stacks_root.find_child("Master Stack")
    shot = session.shot_root.children[0]
    assert drag(window.breakdown_model, [shot], window.stack_view.model(), stack)
    assert len(stack.refs()) == 6
    # Breakdown "Stack" column now shows the stack.
    marty = next(c for c in session.characters() if c.name == "Marty")
    index = window.breakdown_model.index_for(marty)
    assert window.breakdown_model.data(index.siblingAtColumn(1)) == "Master Stack"


def test_select_character_and_override(window):
    session = window.session
    stack = session.stacks_root.find_child("Dynamic Stack")
    doc = next(c for c in session.characters() if c.name == "Doc")
    drag(window.breakdown_model, [doc], window.stack_view.model(), stack)
    ref = stack.find_child("Doc")

    window.stack_view.select_node(ref)
    assert window._stack is stack and window._ref is ref
    assert set(window.graph.items_by_name) == {s.name for s in stack.pipeline.steps}

    item = window.graph.items_by_name["do sim hair"]
    item.setSelected(True)
    assert window._step.name == "do sim hair"

    window.properties.value_changed.emit("attributes", "endFrame", 200)
    assert ref.overrides == {"do sim hair": {"endFrame": 200}}
    assert stack.pipeline.step("do sim hair").value("endFrame") == 120

    window._toggle_enable([item])
    assert ref.overrides["do sim hair"]["enable"] is False

    window._on_reset_override("endFrame")
    assert "endFrame" not in ref.overrides["do sim hair"]


def test_render_properties_and_launch(window, tmp_path):
    render = window.session.renders_root.find_child("default")
    window.render_view.select_node(render)
    assert window._render is render
    window.properties.value_changed.emit("submit", "AASamples", 8)
    assert render.step.submit["AASamples"].value == 8

    window._launch()
    (written,) = (tmp_path / "out").glob("submission_*.json")
    data = json.loads(written.read_text())
    assert data["queue"] == "dev"  # DEV is the default farm
    assert data["render_scenes"][0]["farm_render"]["AASamples"] == 8


def test_new_stack_and_delete(window, monkeypatch):
    from farm_dispatcher.ui import main_window

    monkeypatch.setattr(main_window.CreateStackDialog, "ask",
                        classmethod(lambda cls, *a: ("Hero", "Cloth Stack")))
    window._new_stack()
    hero = window.session.stacks_root.find_child("Hero")
    assert isinstance(hero, StackNode) and hero.pipeline.tree == "tree_cloth.json"
    window._remove_node(hero)
    assert window.session.stacks_root.find_child("Hero") is None


def test_rename_through_model(window):
    model = window.stack_view.model()
    stack = window.session.stacks_root.find_child("Cloth Stack")
    assert model.setData(model.index_for(stack), "Cloth hero")
    assert stack.name == "Cloth hero"
    other = window.session.stacks_root.find_child("Static Stack")
    assert not model.setData(model.index_for(other), "Cloth hero")


def test_window_can_be_garbage_collected(app):
    # Strong model -> window references used to crash PySide during collection
    # (this is what happens when a Maya user re-opens the tool).
    import gc

    for _ in range(3):
        w = MainWindow(DemoBackend())
        w.session.set_preference("cfx_artist")
        w._refresh_trees()
        del w
        gc.collect()


def test_refs_cannot_be_renamed(window):
    stack = window.session.stacks()[0]
    doc = next(c for c in window.session.characters() if c.name == "Doc")
    drag(window.breakdown_model, [doc], window.stack_view.model(), stack)
    ref = stack.find_child("Doc")
    assert isinstance(ref, CharacterRef)
    flags = window.stack_view.model().flags(window.stack_view.model().index_for(ref))
    assert not flags & QtCore.Qt.ItemFlag.ItemIsEditable
