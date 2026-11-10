"""The working state of the tool: the shot breakdown, stacks, renders and overrides.

* The **breakdown** lists the shot's characters (Shot > anim block > character).
* A **stack** runs one pipeline. Each character can be in at most one stack.
* A **render** setup builds a render scene. A character can be in several renders.
* Inside stacks and renders, characters appear as ``CharacterRef`` nodes. A ref
  holds that character's attribute **overrides**, so one character can, say, sim
  more frames than the others in the same stack.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from farm_dispatcher.core import constants as c
from farm_dispatcher.core.backend import Backend, CharacterInfo, ShotInfo
from farm_dispatcher.core.config import ConfigError, ConfigStore
from farm_dispatcher.core.node import Node
from farm_dispatcher.core.pipeline import Attribute, FrameRange, Pipeline, Step, build_pipeline, make_step


# -- node types ------------------------------------------------------------
class ShotNode(Node):
    pass


class AnimBlockNode(Node):
    pass


class CharacterNode(Node):
    """A character in the shot breakdown."""

    def __init__(self, info: CharacterInfo, parent: Optional[Node] = None):
        super().__init__(info.alias, parent)
        self.info = info
        self.stack: Optional[StackNode] = None
        self.renders: List[RenderNode] = []
        if not info.hair_style:
            self.warning = True
            self.tooltip = "No hairstyle in the breakdown"


class StackNode(Node):
    def __init__(self, name: str, stack_type: str, pipeline: Pipeline, parent: Optional[Node] = None):
        super().__init__(name, parent)
        self.stack_type = stack_type
        self.pipeline = pipeline

    def refs(self) -> List["CharacterRef"]:
        return [n for n in self.children if isinstance(n, CharacterRef)]


class RenderNode(Node):
    def __init__(self, name: str, step: Step, parent: Optional[Node] = None):
        super().__init__(name, parent)
        self.step = step

    def refs(self) -> List["CharacterRef"]:
        return [n for n in self.children if isinstance(n, CharacterRef)]


class CharacterRef(Node):
    """A breakdown character placed in a stack or render."""

    def __init__(self, source: CharacterNode, parent: Optional[Node] = None):
        super().__init__(source.name, parent)
        self.source = source
        # {step name: {attribute name: value}}
        self.overrides: Dict[str, Dict[str, Any]] = {}

    @property
    def info(self) -> CharacterInfo:
        return self.source.info


# -- assignment ------------------------------------------------------------
def characters_in(nodes: Iterable[Node]) -> List[CharacterNode]:
    """Expand shots and anim blocks to their characters, without duplicates."""
    found: List[CharacterNode] = []
    for node in nodes:
        for n in node.walk():
            if isinstance(n, CharacterNode) and n not in found:
                found.append(n)
    return found


def assign_to_stack(characters: Iterable[CharacterNode], stack: StackNode) -> List[CharacterRef]:
    """Add characters that are not in a stack yet. Returns the new refs."""
    added = []
    for char in characters:
        if char.stack is None:
            added.append(CharacterRef(char, stack))
            char.stack = stack
    return added


def assign_to_render(characters: Iterable[CharacterNode], render: RenderNode) -> List[CharacterRef]:
    """Add characters that are not in this render yet. Returns the new refs."""
    added = []
    for char in characters:
        if render not in char.renders:
            added.append(CharacterRef(char, render))
            char.renders.append(render)
    return added


def remove_ref(ref: CharacterRef) -> None:
    owner = ref.parent
    if isinstance(owner, StackNode) and ref.source.stack is owner:
        ref.source.stack = None
    elif isinstance(owner, RenderNode) and owner in ref.source.renders:
        ref.source.renders.remove(owner)
    if owner is not None:
        owner.remove_child(ref)


def remove_container(node: Node) -> None:
    """Delete a stack or render setup, releasing its characters."""
    for ref in [n for n in node.children if isinstance(n, CharacterRef)]:
        remove_ref(ref)
    if node.parent is not None:
        node.parent.remove_child(node)


# -- attributes and overrides ----------------------------------------------
@dataclass
class ResolvedAttribute:
    attribute: Attribute
    overridden: bool = False


_FIRST = (c.ENABLE, c.START_FRAME, c.END_FRAME)


def resolve_attributes(step: Step, ref: Optional[CharacterRef] = None) -> List[ResolvedAttribute]:
    """The attributes of a step as seen by one character (or by the stack if ref is None).

    enable / startFrame / endFrame come first, then the rest in definition order.
    """
    overrides = ref.overrides.get(step.name, {}) if ref else {}
    resolved = []
    names = [n for n in _FIRST if n in step.attributes]
    names += [n for n in step.attributes if n not in _FIRST]
    for name in names:
        attr = step.attributes[name].copy()
        if ref is not None:
            # Defaults that come from the character itself.
            if attr.type == c.ATTR_HAIR_COMPONENTS:
                attr.options = list(ref.info.hair_components)
                if not attr.value:
                    attr.value = list(attr.options)
            elif name == c.RIG_CHAR_VAR:
                attr.value = ref.info.variation
        if name in overrides:
            attr.value = overrides[name]
        resolved.append(ResolvedAttribute(attr, name in overrides))
    return resolved


def effective_attributes(step: Step, ref: Optional[CharacterRef] = None) -> Dict[str, Attribute]:
    return {r.attribute.name: r.attribute for r in resolve_attributes(step, ref)}


def set_attribute(step: Step, name: str, value: Any, ref: Optional[CharacterRef] = None) -> None:
    """Set a value on the stack's step, or as an override for one character."""
    if ref is not None:
        ref.overrides.setdefault(step.name, {})[name] = value
    elif name in step.attributes:
        step.attributes[name].value = value
    elif name in step.submit:
        step.submit[name].value = value
    else:
        raise KeyError(name)


def clear_override(step: Step, name: str, ref: CharacterRef) -> None:
    step_overrides = ref.overrides.get(step.name, {})
    step_overrides.pop(name, None)
    if not step_overrides:
        ref.overrides.pop(step.name, None)


def step_enabled(step: Step, ref: Optional[CharacterRef] = None) -> bool:
    if ref is not None and c.ENABLE in ref.overrides.get(step.name, {}):
        return bool(ref.overrides[step.name][c.ENABLE])
    return step.enabled


# -- session ---------------------------------------------------------------
class Session:
    """Everything the main window shows, without any Qt."""

    def __init__(self, config: ConfigStore, backend: Backend):
        self.config = config
        self.backend = backend
        self.project: str = ""
        self.preference: Optional[str] = None
        self.shot: Optional[ShotInfo] = None
        self.shot_root = Node(c.ROOT_SHOT)
        self.stacks_root = Node(c.ROOT_STACKS)
        self.renders_root = Node(c.ROOT_RENDERS)

    @property
    def frame_range(self) -> Optional[FrameRange]:
        return self.shot.frame_range if self.shot else None

    # -- loading -----------------------------------------------------------
    def set_preference(self, name: str) -> None:
        self.preference = name
        self.reset_assignments()

    def load_shot(self, project: str, sequence: str, shot: str) -> ShotInfo:
        info = self.backend.load_shot(project, sequence, shot)
        self.project = project
        self.shot = info
        self.shot_root.clear()
        shot_node = ShotNode("{}.{}".format(info.sequence, info.shot), self.shot_root)
        blocks: Dict[str, AnimBlockNode] = {}
        for char in info.characters:
            block = blocks.get(char.anim_block)
            if block is None:
                block = blocks[char.anim_block] = AnimBlockNode(char.anim_block, shot_node)
            CharacterNode(char, block)
        self.reset_assignments()
        return info

    def clear_shot(self) -> None:
        self.shot = None
        self.shot_root.clear()
        self.reset_assignments()

    def reset_assignments(self) -> None:
        """Rebuild the preference's default stacks and renders and empty them."""
        for char in self.characters():
            char.stack = None
            char.renders = []
        self.stacks_root.clear()
        self.renders_root.clear()
        if not self.preference:
            return
        for label, tree in self.config.stack_types(self.preference).items():
            StackNode(label, label, build_pipeline(self.config, tree, self.frame_range), self.stacks_root)
        for name, spec in self.config.render_setups(self.preference).items():
            render = RenderNode(name, make_step(self.config, name, spec, self.frame_range), self.renders_root)
            if c.ALL_CHARACTERS in render.step.inputs:
                assign_to_render(self.characters(), render)

    # -- queries -----------------------------------------------------------
    def characters(self) -> List[CharacterNode]:
        return characters_in([self.shot_root])

    def stacks(self) -> List[StackNode]:
        return [n for n in self.stacks_root.children if isinstance(n, StackNode)]

    def renders(self) -> List[RenderNode]:
        return [n for n in self.renders_root.children if isinstance(n, RenderNode)]

    def stack_types(self) -> Dict[str, str]:
        """{label: tree file} available in the current preference."""
        return self.config.stack_types(self.preference) if self.preference else {}

    @staticmethod
    def unique_name(root: Node, base: str) -> str:
        taken = {n.name for n in root.children}
        if base not in taken:
            return base
        i = 2
        while "{} {:02d}".format(base, i) in taken:
            i += 1
        return "{} {:02d}".format(base, i)

    # -- editing -----------------------------------------------------------
    def add_stack(self, name: str = "", stack_type: str = "") -> StackNode:
        types = self.stack_types()
        if not types:
            raise ConfigError("The current preference defines no stack types.")
        stack_type = stack_type or next(iter(types))
        if stack_type not in types:
            raise ConfigError("Unknown stack type {!r}".format(stack_type))
        name = self.unique_name(self.stacks_root, name.strip() or "Stack")
        pipeline = build_pipeline(self.config, types[stack_type], self.frame_range)
        return StackNode(name, stack_type, pipeline, self.stacks_root)

    def change_stack_type(self, stack: StackNode, stack_type: str) -> None:
        types = self.stack_types()
        stack.pipeline = build_pipeline(self.config, types[stack_type], self.frame_range)
        stack.stack_type = stack_type

    def add_render(self, name: str = "") -> RenderNode:
        name = self.unique_name(self.renders_root, name.strip() or "Render Scene")
        step = make_step(self.config, name, {"nodeType": c.GROUP_RENDER}, self.frame_range)
        return RenderNode(name, step, self.renders_root)

    def rename(self, node: Node, new_name: str) -> bool:
        new_name = new_name.strip()
        if not new_name or not isinstance(node, (StackNode, RenderNode)) or node.parent is None:
            return False
        if new_name != node.name and node.parent.find_child(new_name):
            return False
        node.name = new_name
        if isinstance(node, RenderNode):
            node.step.name = new_name
        node.parent.resort()
        return True

    def drop(self, nodes: List[Node], target: Node) -> bool:
        """Drag-and-drop from the breakdown onto a stack/render tree."""
        chars = characters_in(nodes)
        if not chars:
            return False
        if isinstance(target, CharacterRef):
            target = target.parent
        if target is self.stacks_root:
            free = [ch for ch in chars if ch.stack is None]
            if not free:
                return False
            target = self.add_stack()
        elif target is self.renders_root:
            target = self.add_render()
        if isinstance(target, StackNode):
            return bool(assign_to_stack(chars, target))
        if isinstance(target, RenderNode):
            return bool(assign_to_render(chars, target))
        return False
