"""The connection to a studio's pipeline.

Everything that depended on the original studio's internal APIs (shot breakdowns,
frame ranges, job naming, output paths) goes through a ``Backend``. The tool ships
with ``DemoBackend`` so it runs anywhere; a studio subclasses ``Backend`` and points
``$FARM_DISPATCHER_BACKEND`` at it, e.g. ``my_studio.dispatch:StudioBackend``.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

BACKEND_ENV_VAR = "FARM_DISPATCHER_BACKEND"


class ShotNotFound(LookupError):
    pass


@dataclass
class CharacterInfo:
    alias: str
    anim_block: str
    short_name: str = ""
    variation: str = "original"
    hair_style: Optional[str] = None
    hair_components: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.short_name = self.short_name or self.alias


@dataclass
class ShotInfo:
    sequence: str
    shot: str
    frame_range: Tuple[int, int]
    characters: List[CharacterInfo]

    @property
    def code(self) -> str:
        return self.sequence + self.shot


class Backend:
    """Override these methods to connect the tool to a real pipeline."""

    def projects(self) -> List[str]:
        raise NotImplementedError

    def load_shot(self, project: str, sequence: str, shot: str) -> ShotInfo:
        """Raise ShotNotFound if the shot does not exist."""
        raise NotImplementedError

    # ``fields`` passed to job_name / output_path may contain:
    # project, sequence, shot, character, description, output_type.

    def job_name(self, job_type: str, fields: Dict[str, str]) -> str:
        """job_type is 'cloth', 'hair' or 'render'."""
        raise NotImplementedError

    def output_path(self, fields: Dict[str, str]) -> str:
        """Where a step writes its output when the artist left the path empty."""
        raise NotImplementedError

    def repository(self, project: str) -> str:
        return project


class DemoBackend(Backend):
    """Stand-in data so the tool can be tried without a studio pipeline."""

    HAIR = ["head", "eyelashes", "eyebrows"]

    def projects(self) -> List[str]:
        return ["demo", "sandbox"]

    def load_shot(self, project: str, sequence: str, shot: str) -> ShotInfo:
        if not (sequence.strip() and shot.strip()):
            raise ShotNotFound("Enter both a sequence and a shot.")

        def char(alias, block, hair=True):
            return CharacterInfo(
                alias=alias,
                anim_block=block,
                hair_style="original" if hair else None,
                hair_components=list(self.HAIR) if hair else [],
            )

        characters = [
            char("Marty", "main"),
            char("Doc", "main"),
            char("genericGirlA", "extraA"),
            char("genericBoyA", "extraA"),
            char("dogGenericA", "extraB"),
            char("genericGirlC", "extraB", hair=False),
        ]
        return ShotInfo(sequence.strip(), shot.strip(), (101, 120), characters)

    def job_name(self, job_type: str, fields: Dict[str, str]) -> str:
        parts = [fields.get(k, "") for k in ("project", "sequence", "shot", "character")]
        return "_".join(p for p in parts + [job_type] if p)

    def output_path(self, fields: Dict[str, str]) -> str:
        return "/projects/{project}/{sequence}/{shot}/cfx/{character}/{name}".format(
            project=fields.get("project", ""),
            sequence=fields.get("sequence", ""),
            shot=fields.get("shot", ""),
            character=fields.get("character") or "shot",
            name=fields.get("description") or fields.get("output_type", ""),
        )

    def repository(self, project: str) -> str:
        return "Demo ({})".format(project)


def load_backend(spec: Optional[str] = None) -> Backend:
    """Instantiate ``module.path:ClassName``, defaulting to $FARM_DISPATCHER_BACKEND."""
    spec = spec or os.environ.get(BACKEND_ENV_VAR)
    if not spec:
        return DemoBackend()
    module_name, _, class_name = spec.partition(":")
    if not class_name:
        raise ValueError("Backend must look like 'package.module:ClassName', got {!r}".format(spec))
    backend_cls = getattr(importlib.import_module(module_name), class_name)
    return backend_cls()
