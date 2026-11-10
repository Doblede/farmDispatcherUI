"""User settings remembered between sessions (stored with QSettings)."""

from __future__ import annotations

from pathlib import Path

from farm_dispatcher.core import constants as c
from farm_dispatcher.core.config import ConfigPaths
from farm_dispatcher.core.export import default_publish_dir
from farm_dispatcher.qt import QtCore


class AppSettings:
    def __init__(self, qsettings=None):
        self._s = qsettings or QtCore.QSettings("FarmDispatcher", "FarmDispatcher")

    def _get(self, key: str, default: str = "") -> str:
        value = self._s.value(key, default)
        return str(value) if value is not None else default

    # -- config directories --------------------------------------------
    @property
    def config_paths(self) -> ConfigPaths:
        default = ConfigPaths.default()
        return ConfigPaths(
            Path(self._get("config/preferences", str(default.preferences))),
            Path(self._get("config/stacks", str(default.stacks))),
            Path(self._get("config/nodes", str(default.nodes))),
        )

    @config_paths.setter
    def config_paths(self, paths: ConfigPaths) -> None:
        self._s.setValue("config/preferences", str(paths.preferences))
        self._s.setValue("config/stacks", str(paths.stacks))
        self._s.setValue("config/nodes", str(paths.nodes))

    def reset_config_paths(self) -> None:
        for key in ("config/preferences", "config/stacks", "config/nodes"):
            self._s.remove(key)

    # -- farm and output -----------------------------------------------
    @property
    def farm(self) -> str:
        farm = self._get("farm", c.DEFAULT_FARM)
        return farm if farm in c.FARMS else c.DEFAULT_FARM

    @farm.setter
    def farm(self, value: str) -> None:
        self._s.setValue("farm", value)

    @property
    def publish_dir(self) -> Path:
        return Path(self._get("publish_dir", str(default_publish_dir())))

    @publish_dir.setter
    def publish_dir(self, value: Path) -> None:
        self._s.setValue("publish_dir", str(value))

    # -- last used -----------------------------------------------------
    def last(self, key: str) -> str:
        return self._get("last/" + key)

    def set_last(self, key: str, value: str) -> None:
        self._s.setValue("last/" + key, value)
