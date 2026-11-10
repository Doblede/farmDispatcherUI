from farm_dispatcher.core.scene import (
    CharacterRef,
    clear_override,
    effective_attributes,
    remove_container,
    remove_ref,
    resolve_attributes,
    set_attribute,
    step_enabled,
)


def char(session, alias):
    return next(c for c in session.characters() if c.name == alias)


def test_loading_a_shot_builds_breakdown_and_default_render(session):
    shot = session.shot_root.children[0]
    assert shot.name == "seq010.0050"
    assert [b.name for b in shot.children] == ["extraA", "extraB", "main"]
    assert {c.name for c in session.characters()} == {
        "Doc", "Marty", "genericBoyA", "genericGirlA", "dogGenericA", "genericGirlC",
    }
    default = session.renders_root.find_child("default")
    # "input": ["ALL CHARACTERS"] puts everyone in the default render
    assert len(default.refs()) == 6
    assert all(default in c.renders for c in session.characters())


def test_shot_frame_range_reaches_stacks_and_renders(session):
    stack = session.stacks()[0]
    assert stack.pipeline.steps[-1].value("startFrame") == 101
    assert session.renders()[0].step.value("endFrame") == 120


def test_character_lacking_hairstyle_is_flagged(session):
    assert char(session, "genericGirlC").warning
    assert not char(session, "Marty").warning


def test_drop_shot_on_stack_adds_each_character_once(session):
    stack = session.stacks_root.find_child("Static Stack")
    assert session.drop([session.shot_root.children[0]], stack)
    assert len(stack.refs()) == 6
    # A character already in a stack can't go into a second one.
    other = session.stacks_root.find_child("Cloth Stack")
    assert not session.drop([char(session, "Marty")], other)


def test_drop_on_stacks_root_creates_a_new_stack(session):
    before = len(session.stacks())
    session.drop([char(session, "Doc")], session.stacks_root)
    assert len(session.stacks()) == before + 1
    assert char(session, "Doc").stack is not None


def test_drop_on_render_root_creates_render_with_full_settings(session):
    session.drop([char(session, "Doc")], session.renders_root)
    new = session.renders_root.find_child("Render Scene")
    # Previously a render made by dropping had no attributes and broke the export.
    assert new.step.attributes["enable"].value
    assert "AASamples" in new.step.submit


def test_remove_ref_frees_the_character(session):
    stack = session.stacks()[0]
    session.drop([char(session, "Doc")], stack)
    remove_ref(stack.refs()[0])
    assert char(session, "Doc").stack is None
    assert session.drop([char(session, "Doc")], session.stacks()[1])


def test_remove_container_releases_all_characters(session):
    render = session.renders_root.find_child("default")
    remove_container(render)
    assert all(not c.renders for c in session.characters())
    assert render not in session.renders()


def test_override_only_affects_that_character(session):
    stack = session.stacks_root.find_child("Dynamic Stack")
    session.drop([char(session, "Doc"), char(session, "Marty")], stack)
    doc, marty = sorted(stack.refs(), key=lambda r: r.name)
    step = stack.pipeline.step("do sim hair")

    set_attribute(step, "endFrame", 150, doc)
    assert effective_attributes(step, doc)["endFrame"].value == 150
    assert effective_attributes(step, marty)["endFrame"].value == 120
    assert step.value("endFrame") == 120

    overridden = {r.attribute.name for r in resolve_attributes(step, doc) if r.overridden}
    assert overridden == {"endFrame"}

    clear_override(step, "endFrame", doc)
    assert effective_attributes(step, doc)["endFrame"].value == 120
    assert doc.overrides == {}


def test_enable_override_per_character(session):
    stack = session.stacks()[0]
    session.drop([char(session, "Doc")], stack)
    ref = stack.refs()[0]
    step = stack.pipeline.steps[0]
    set_attribute(step, "enable", False, ref)
    assert not step_enabled(step, ref)
    assert step_enabled(step)


def test_hair_components_default_to_the_characters_components(session):
    stack = session.stacks_root.find_child("Dynamic Stack")
    session.drop([char(session, "Marty")], stack)
    step = stack.pipeline.step("publish .fur cache")
    attr = effective_attributes(step, stack.refs()[0])["selectHairComponent"]
    assert attr.options == ["head", "eyelashes", "eyebrows"]
    assert attr.value == attr.options


def test_rename_keeps_names_unique(session):
    a, b = session.stacks()[:2]
    assert not session.rename(a, b.name)
    assert session.rename(a, "Hero sims")
    assert a.name == "Hero sims"


def test_changing_preference_resets_assignments(session):
    session.drop([session.shot_root], session.stacks()[0])
    session.set_preference("static_only")
    assert [s.name for s in session.stacks()] == ["Static Stack"]
    assert all(c.stack is None for c in session.characters())
    assert not any(isinstance(n, CharacterRef) for s in session.stacks() for n in s.children)
