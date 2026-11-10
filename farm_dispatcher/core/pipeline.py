"""Pipelines: the ordered steps (build workfile, sim, cache, ...) a stack runs."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from farm_dispatcher.core import constants as c
from farm_dispatcher.core.config import ConfigError, ConfigStore

FrameRange = Tuple[int, int]

DEFAULT_COLOR = [(23, 144, 246, 255), (15, 111, 193, 255)]


@dataclass
class Attribute:
    name: str
    type: str
    value: Any
    options: List[Any] = field(default_factory=list)
    # Extra keys from the node definition (fileType, description, creator, enable, ...).
    meta: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_definition(cls, name: str, definition: dict) -> "Attribute":
        meta = {k: v for k, v in definition.items() if k not in ("attrType", "value", "options")}
        return cls(
            name=name,
            type=definition.get("attrType", c.ATTR_STRING),
            value=copy.deepcopy(definition.get("value")),
            options=list(definition.get("options", [])),
            meta=meta,
        )

    @property
    def editable(self) -> bool:
        return bool(self.meta.get("enable", True))

    def copy(self) -> "Attribute":
        return copy.deepcopy(self)


@dataclass
class Step:
    """One node of a pipeline graph, or a render setup."""

    name: str
    node_type: str
    group: str = ""
    pos: Tuple[float, float] = (0.0, 0.0)
    color: List[Any] = field(default_factory=lambda: list(DEFAULT_COLOR))
    attributes: Dict[str, Attribute] = field(default_factory=dict)
    # Render setups only: farm submission settings.
    submit: Dict[str, Attribute] = field(default_factory=dict)
    # Names of steps to draw arrows to (purely visual).
    arrows: List[str] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)

    @property
    def enabled(self) -> bool:
        attr = self.attributes.get(c.ENABLE)
        return bool(attr.value) if attr else True

    def value(self, name: str, default: Any = None) -> Any:
        attr = self.attributes.get(name)
        return attr.value if attr else default


@dataclass
class Pipeline:
    tree: str
    steps: List[Step]

    def step(self, name: str) -> Optional[Step]:
        return next((s for s in self.steps if s.name == name), None)


def make_step(
    config: ConfigStore, name: str, spec: dict, frame_range: Optional[FrameRange] = None
) -> Step:
    """Build a step from a node definition plus the overrides in ``spec``.

    ``spec`` is an entry of a stack layout or of a preference's render setups.
    Its ``attributeList`` holds plain values that replace the definition defaults.
    """
    node_type = spec["nodeType"]
    definition = config.node_definition(node_type)

    def pick(key, default=None):
        return copy.deepcopy(spec[key] if key in spec else definition.get(key, default))

    overrides = spec.get("attributeList", {})
    attributes = {}
    for attr_name, attr_def in definition.get("attributeList", {}).items():
        attr = Attribute.from_definition(attr_name, attr_def)
        if attr_name in overrides:
            attr.value = copy.deepcopy(overrides[attr_name])
        attributes[attr_name] = attr
    if frame_range:
        if c.START_FRAME in attributes:
            attributes[c.START_FRAME].value = frame_range[0]
        if c.END_FRAME in attributes:
            attributes[c.END_FRAME].value = frame_range[1]

    submit = {
        k: Attribute.from_definition(k, v) for k, v in definition.get(c.SUBMIT_RENDER, {}).items()
    }
    arrows = [a for a in spec.get("outarrow", []) if a]
    return Step(
        name=name,
        node_type=node_type,
        group=pick("group", ""),
        pos=tuple(pick("pos", (0, 0))),
        color=pick("color", DEFAULT_COLOR),
        attributes=attributes,
        submit=submit,
        arrows=arrows,
        inputs=list(spec.get("input", [])),
    )


def step_order(nodes: Dict[str, dict]) -> List[str]:
    """Follow the ``output`` links of a stack layout from first to last step.

    Raises ConfigError if the layout is not a single chain.
    """
    targets = {spec.get("output") for spec in nodes.values()}
    starts = [name for name in nodes if name not in targets]
    if len(starts) != 1:
        raise ConfigError(
            "A stack layout needs exactly one first step (one that no other step outputs to); "
            "found {}".format(starts or "none (the steps form a loop)")
        )
    order: List[str] = []
    name = starts[0]
    while name:
        if name in order:
            raise ConfigError("Step {!r} is part of a loop".format(name))
        if name not in nodes:
            raise ConfigError("Step {!r} outputs to unknown step {!r}".format(order[-1], name))
        order.append(name)
        name = nodes[name].get("output") or ""
    missing = set(nodes) - set(order)
    if missing:
        raise ConfigError("Steps not connected to the chain: {}".format(sorted(missing)))
    return order


def build_pipeline(
    config: ConfigStore, tree: str, frame_range: Optional[FrameRange] = None
) -> Pipeline:
    nodes = config.tree(tree).get("nodes", {})
    if not nodes:
        raise ConfigError("Stack layout {!r} has no steps".format(tree))
    steps = [make_step(config, name, nodes[name], frame_range) for name in step_order(nodes)]
    return Pipeline(tree=tree, steps=steps)
