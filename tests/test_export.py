import json

import pytest

from farm_dispatcher.core.export import (
    SubmissionError,
    build_submission,
    default_publish_dir,
    submission_kinds,
    write_submission,
)
from farm_dispatcher.core.scene import set_attribute
from farm_dispatcher.core.statistics import UsageStats


def char(session, alias):
    return next(c for c in session.characters() if c.name == alias)


def test_submission_needs_a_shot(config):
    from farm_dispatcher.core.backend import DemoBackend
    from farm_dispatcher.core.scene import Session

    s = Session(config, DemoBackend())
    s.set_preference("cfx_artist")
    with pytest.raises(SubmissionError):
        build_submission(s, "dev")


def test_submission_format(session):
    session.drop([char(session, "Marty")], session.stacks_root.find_child("Master Stack"))
    sub = build_submission(session, "dev")

    assert sub["format_version"] == 2
    assert (sub["project"], sub["sequence"], sub["shot"], sub["queue"]) == ("demo", "seq010", "0050", "dev")
    assert sub["frame_range"] == [101, 120]

    marty = next(ch for ch in sub["characters"] if ch["alias"] == "Marty")
    assert marty["stack"] == "Master Stack"
    cloth, hair = marty["jobs"]["cloth"], marty["jobs"]["hair"]
    assert cloth["name"] == "demo_seq010_0050_Marty_cloth"
    assert set(cloth["steps"]) >= {"ncache_cloth", "publish_abc_cloth"}
    assert set(hair["steps"]) >= {"ncache_hair", "fur_cache_hair"}
    assert hair["steps"]["ncache_hair"]["startFrame"] == 101
    # Empty paths are filled in by the backend, with forward slashes.
    assert cloth["steps"]["ncache_cloth"]["path"] == "/projects/demo/seq010/0050/cfx/Marty/cloth_sim"
    # Hair components default to all of the character's components.
    assert hair["steps"]["fur_cache_hair"]["selectHairComponent"] == ["head", "eyelashes", "eyebrows"]

    (scene,) = sub["render_scenes"]
    default = session.renders_root.find_child("default")
    assert scene["setup"] == "default"
    assert scene["characters"] == [r.name for r in default.refs()]
    assert cloth["name"] in scene["depends_on"]
    assert scene["farm_render"]["AASamples"] == 4  # submitRender is on


def test_disabled_steps_and_overrides_are_respected(session):
    stack = session.stacks_root.find_child("Dynamic Stack")
    session.drop([char(session, "Doc"), char(session, "Marty")], stack)
    doc = stack.find_child("Doc")
    set_attribute(stack.pipeline.step("do sim hair"), "enable", False, doc)
    set_attribute(stack.pipeline.step("publish .fur cache"), "selectHairComponent", ["head"], doc)

    chars = {c["alias"]: c for c in build_submission(session, "dev")["characters"]}
    assert "ncache_hair" not in chars["Doc"]["jobs"]["hair"]["steps"]
    assert "ncache_hair" in chars["Marty"]["jobs"]["hair"]["steps"]
    assert chars["Doc"]["jobs"]["hair"]["steps"]["fur_cache_hair"]["selectHairComponent"] == ["head"]


def test_nothing_assigned_is_an_error(session):
    for render in session.renders():
        set_attribute(render.step, "enable", False)
    with pytest.raises(SubmissionError, match="Nothing to submit"):
        build_submission(session, "dev")


def test_write_creates_missing_publish_dir(session, tmp_path):
    # The 2017 version failed here because publish/ did not exist.
    target_dir = tmp_path / "does" / "not" / "exist"
    sub = build_submission(session, "dev")
    first = write_submission(sub, target_dir)
    second = write_submission(sub, target_dir)
    assert first != second
    assert json.loads(first.read_text())["shot"] == "0050"
    assert not list(target_dir.glob("*.tmp"))


def test_publish_dir_env_override(tmp_path):
    assert default_publish_dir() == tmp_path / "publish"


def test_submission_kinds(session):
    session.drop([char(session, "Doc")], session.stacks_root.find_child("Cloth Stack"))
    assert submission_kinds(build_submission(session, "dev")) == ["cloth", "render"]


def test_statistics_per_user_and_corruption_safe(tmp_path):
    stats = UsageStats(tmp_path, user="Artist")
    stats.record_open()
    stats.record_launch("hair", "seq0100050")
    stats.record_launch("hair", "seq0100050")
    data = stats.load()
    assert stats.path.name == "artist.json"
    assert data["open_standalone"] == 1
    assert data["hair"] == {"times": 2, "shots": ["seq0100050"]}

    stats.path.write_text("{corrupt")
    stats.record_open("maya")
    assert stats.load()["open_in_maya"] == 1
