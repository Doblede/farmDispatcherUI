"""Turns the session into the submission JSON a farm submitter reads.

Format (``format_version`` 2)::

    {
      "format_version": 2,
      "project": "demo", "repository": "...",
      "sequence": "seq010", "shot": "0050", "frame_range": [101, 120],
      "queue": "dev",
      "characters": [
        {"alias": "Marty", "short_name": "Marty", "variation": "original", "hairstyle": "original",
         "jobs": {
           "cloth": {"name": "<job name>", "steps": {"<node type>": {"<attribute>": value, ...}, ...}},
           "hair":  {...}
         }}
      ],
      "render_scenes": [
        {"name": "<job name>", "setup": "default", "path": "...",
         "characters": ["Marty", ...], "depends_on": ["<cloth/hair job names>"],
         "settings": {...}, "farm_render": {...}}      # farm_render only when enabled
      ]
    }
"""

from __future__ import annotations

import datetime
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from farm_dispatcher.core import constants as c
from farm_dispatcher.core.pipeline import Attribute
from farm_dispatcher.core.scene import CharacterRef, Session, StackNode, effective_attributes

FORMAT_VERSION = 2
PUBLISH_ENV_VAR = "FARM_DISPATCHER_PUBLISH_DIR"


class SubmissionError(Exception):
    """The session cannot be submitted (nothing to do, no shot, ...)."""


def default_publish_dir() -> Path:
    env = os.environ.get(PUBLISH_ENV_VAR)
    return Path(env) if env else Path.home() / "farm_dispatcher" / "publish"


def _value(attr: Attribute) -> Any:
    if attr.type == c.ATTR_BOOL:
        return bool(attr.value)
    if attr.type == c.ATTR_HAIR_COMPONENTS:
        return list(attr.value or [])
    return attr.value


def _fields(session: Session, **extra: str) -> Dict[str, str]:
    fields = {"project": session.project, "sequence": session.shot.sequence, "shot": session.shot.shot}
    fields.update({k: v for k, v in extra.items() if v})
    return fields


def _export_steps(session: Session, stack: StackNode, ref: CharacterRef, group: str) -> Dict[str, Any]:
    """{node type: {attribute: value}} for the enabled steps of one group."""
    steps: Dict[str, Any] = {}
    for step in stack.pipeline.steps:
        if step.group != group:
            continue
        attrs = effective_attributes(step, ref)
        if c.ENABLE in attrs and not attrs[c.ENABLE].value:
            continue
        out: Dict[str, Any] = {}
        for name, attr in attrs.items():
            if attr.type == c.ATTR_PATH:
                path = attr.value or session.backend.output_path(_fields(
                    session,
                    character=ref.name,
                    description=attr.meta.get("description", ""),
                    output_type=attr.meta.get("outputType", ""),
                ))
                out[name] = str(path).replace("\\", "/")
            else:
                out[name] = _value(attr)
        steps[step.node_type] = out
    return steps


def export_characters(session: Session) -> List[Dict[str, Any]]:
    characters = []
    for stack in session.stacks():
        for ref in stack.refs():
            info = ref.info
            jobs = {}
            for group in (c.GROUP_CLOTH, c.GROUP_HAIR):
                steps = _export_steps(session, stack, ref, group)
                if steps:
                    name = session.backend.job_name(group, _fields(session, character=info.alias))
                    jobs[group] = {"name": name, "steps": steps}
            characters.append({
                "alias": info.alias,
                "short_name": info.short_name,
                "variation": info.variation,
                "hairstyle": info.hair_style,
                "stack": stack.name,
                "jobs": jobs,
            })
    return characters


def export_renders(session: Session, characters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    jobs_by_alias = {ch["alias"]: [job["name"] for job in ch["jobs"].values()] for ch in characters}
    scenes = []
    for render in session.renders():
        step = render.step
        refs = render.refs()
        if not refs or not step.enabled:
            continue
        description = str(step.value("description") or render.name)
        fields = _fields(session, description=description)
        scene: Dict[str, Any] = {
            "name": session.backend.job_name(c.GROUP_RENDER, fields),
            "setup": render.name,
            "path": session.backend.output_path(fields),
            "characters": [r.info.alias for r in refs],
            "depends_on": [job for r in refs for job in jobs_by_alias.get(r.info.alias, [])],
            "settings": {name: _value(attr) for name, attr in step.attributes.items()},
        }
        if step.value(c.SUBMIT_RENDER) and step.submit:
            scene["farm_render"] = {name: _value(attr) for name, attr in step.submit.items()}
        scenes.append(scene)
    return scenes


def build_submission(session: Session, queue: str) -> Dict[str, Any]:
    if session.shot is None:
        raise SubmissionError("Load a shot first.")
    characters = export_characters(session)
    scenes = export_renders(session, characters)
    if not any(ch["jobs"] for ch in characters) and not scenes:
        raise SubmissionError(
            "Nothing to submit. Drag characters from the breakdown into a stack or render."
        )
    return {
        "format_version": FORMAT_VERSION,
        "project": session.project,
        "repository": session.backend.repository(session.project),
        "sequence": session.shot.sequence,
        "shot": session.shot.shot,
        "frame_range": list(session.shot.frame_range),
        "queue": queue,
        "characters": characters,
        "render_scenes": scenes,
    }


def submission_kinds(submission: Dict[str, Any]) -> List[str]:
    """Which job kinds ('cloth', 'hair', 'render') a submission contains."""
    kinds = [k for k in (c.GROUP_CLOTH, c.GROUP_HAIR)
             if any(k in ch["jobs"] for ch in submission["characters"])]
    if submission["render_scenes"]:
        kinds.append(c.GROUP_RENDER)
    return kinds


def write_submission(submission: Dict[str, Any], directory: Path) -> Path:
    """Write the submission atomically and return its path."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    base = "submission_{}_{}{}_{}".format(
        submission.get("project", ""), submission.get("sequence", ""), submission.get("shot", ""), stamp
    )
    target = directory / (base + ".json")
    n = 1
    while target.exists():
        n += 1
        target = directory / "{}_{}.json".format(base, n)
    fd, tmp = tempfile.mkstemp(dir=str(directory), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(submission, fh, indent=2)
        os.replace(tmp, target)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return target
