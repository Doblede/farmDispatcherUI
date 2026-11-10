"""Loads the JSON configuration: preferences, stack (tree) layouts and node types.

Layout of a config directory::

    preferences/<name>.json   which stacks and render setups an artist starts with
    stacks/<tree>.json        the steps of one pipeline and how they connect
    nodes/<type>.json         default attributes for one step type
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

PACKAGE_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
CONFIG_ENV_VAR = "FARM_DISPATCHER_CONFIG"


class ConfigError(Exception):
    """A config file is missing, unreadable or inconsistent."""


@dataclass
class ConfigPaths:
    preferences: Path
    stacks: Path
    nodes: Path

    @classmethod
    def from_root(cls, root: Path) -> "ConfigPaths":
        root = Path(root)
        return cls(root / "preferences", root / "stacks", root / "nodes")

    @classmethod
    def default(cls) -> "ConfigPaths":
        """The shipped configs, or the directory named by $FARM_DISPATCHER_CONFIG."""
        return cls.from_root(Path(os.environ.get(CONFIG_ENV_VAR) or PACKAGE_CONFIG_DIR))


def _read_json(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        raise ConfigError("Could not read {}: {}".format(path, exc)) from exc


def _json_files(directory: Path) -> Dict[str, Path]:
    """{stem: path} for every .json file in a directory (empty if it is missing)."""
    if not directory.is_dir():
        log.warning("Config directory not found: %s", directory)
        return {}
    return {p.stem: p for p in sorted(directory.glob("*.json")) if p.is_file()}


class ConfigStore:
    """Reads all config files once and serves them from memory."""

    def __init__(self, paths: Optional[ConfigPaths] = None):
        self.paths = paths or ConfigPaths.default()
        self.errors: List[str] = []
        self._preferences: Dict[str, Path] = {}
        self._trees: Dict[str, Path] = {}
        self._tree_cache: Dict[str, dict] = {}
        self._nodes: Dict[str, dict] = {}
        self.reload()

    def reload(self) -> None:
        self.errors = []
        self._preferences = _json_files(self.paths.preferences)
        self._trees = _json_files(self.paths.stacks)
        self._tree_cache = {}
        self._nodes = {}
        for path in _json_files(self.paths.nodes).values():
            try:
                definition = _read_json(path)
                node_type = definition["nodeType"]
            except (ConfigError, KeyError, TypeError) as exc:
                # One broken node file shouldn't stop the tool from opening.
                message = "Skipped node definition {}: {}".format(path.name, exc)
                log.warning(message)
                self.errors.append(message)
                continue
            self._nodes[node_type] = definition

    # -- preferences ---------------------------------------------------
    def preference_names(self) -> List[str]:
        return list(self._preferences)

    def preference(self, name: str) -> dict:
        try:
            return _read_json(self._preferences[name])
        except KeyError:
            raise ConfigError("Unknown preference {!r}".format(name)) from None

    def stack_types(self, preference: str) -> Dict[str, str]:
        """{label: tree file} of the stacks a preference starts with."""
        return dict(self.preference(preference).get("trees", {}))

    def render_setups(self, preference: str) -> Dict[str, dict]:
        return dict(self.preference(preference).get("render", {}))

    # -- trees (stack layouts) -----------------------------------------
    def tree_names(self) -> List[str]:
        return list(self._trees)

    def tree(self, name: str) -> dict:
        key = name[:-5] if name.endswith(".json") else name
        if key not in self._tree_cache:
            try:
                path = self._trees[key]
            except KeyError:
                raise ConfigError(
                    "Stack layout {!r} not found in {}".format(name, self.paths.stacks)
                ) from None
            self._tree_cache[key] = _read_json(path)
        return self._tree_cache[key]

    # -- node types ----------------------------------------------------
    def node_types(self) -> List[str]:
        return list(self._nodes)

    def node_definition(self, node_type: str) -> dict:
        try:
            return self._nodes[node_type]
        except KeyError:
            raise ConfigError(
                "No node definition with nodeType {!r} in {}".format(node_type, self.paths.nodes)
            ) from None
