import json

import pytest

from farm_dispatcher.core.config import ConfigError, ConfigPaths, ConfigStore
from farm_dispatcher.core.pipeline import build_pipeline, step_order


def test_shipped_configs_load_without_errors(config):
    assert config.errors == []
    assert set(config.preference_names()) == {"cfx_artist", "static_only"}
    assert "render" in config.node_types()


@pytest.mark.parametrize("tree", ["tree_static", "tree_dynamic", "tree_cloth", "tree_master"])
def test_every_shipped_stack_builds(config, tree):
    pipeline = build_pipeline(config, tree + ".json")
    assert pipeline.steps
    assert all(step.attributes for step in pipeline.steps)


def test_master_stack_order_follows_outputs(config):
    names = [s.name for s in build_pipeline(config, "tree_master").steps]
    assert names[0] == "build cloth workfile"
    assert names[-1] == "create char hair render file"
    assert len(names) == 11


def test_layout_values_override_node_defaults(config):
    pipeline = build_pipeline(config, "tree_cloth")
    # tree_cloth.json sets useClothCache: 0 on the build step
    assert pipeline.step("build cloth workfile").value("useClothCache") == 0


def test_frame_range_applies_to_every_step(config):
    pipeline = build_pipeline(config, "tree_dynamic", frame_range=(1001, 1100))
    for step in pipeline.steps:
        if "startFrame" in step.attributes:
            assert step.value("startFrame") == 1001
            assert step.value("endFrame") == 1100


def test_tree_lookup_is_exact_not_substring(config):
    # The old code matched "tree" against "tree_static.json" by substring.
    with pytest.raises(ConfigError):
        config.tree("tree")


@pytest.mark.parametrize(
    "nodes, message",
    [
        ({"a": {"output": "b"}, "b": {"output": "a"}}, "loop"),
        ({"a": {"output": "c"}, "b": {"output": "c"}, "c": {"output": ""}}, "exactly one"),
        ({"a": {"output": "missing"}}, "unknown step"),
    ],
)
def test_bad_layouts_raise_clear_errors(nodes, message):
    # Previously a layout without an end step crashed with an IndexError.
    with pytest.raises(ConfigError, match=message):
        step_order(nodes)


def test_broken_node_file_is_skipped_not_fatal(tmp_path):
    for sub in ("preferences", "stacks", "nodes"):
        (tmp_path / sub).mkdir()
    (tmp_path / "nodes" / "good.json").write_text(json.dumps({"nodeType": "good"}))
    (tmp_path / "nodes" / "bad.json").write_text("{not json")
    store = ConfigStore(ConfigPaths.from_root(tmp_path))
    assert store.node_types() == ["good"]
    assert len(store.errors) == 1 and "bad.json" in store.errors[0]
