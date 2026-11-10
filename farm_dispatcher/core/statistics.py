"""Usage statistics: how often each artist opens the tool and launches jobs.

Each user writes their own file, so artists sharing a statistics folder never
overwrite each other. Writes are atomic, and a failure is logged rather than
interrupting the artist.
"""

from __future__ import annotations

import datetime
import getpass
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

STATS_ENV_VAR = "FARM_DISPATCHER_STATS_DIR"


def default_stats_dir() -> Path:
    env = os.environ.get(STATS_ENV_VAR)
    return Path(env) if env else Path.home() / ".farm_dispatcher" / "statistics"


def _empty() -> dict:
    return {
        "open_standalone": 0,
        "open_in_maya": 0,
        "cloth": {"times": 0, "shots": []},
        "hair": {"times": 0, "shots": []},
        "render": {"times": 0, "shots": []},
        "last_date": None,
    }


class UsageStats:
    def __init__(self, directory: Optional[Path] = None, user: Optional[str] = None):
        self.directory = Path(directory) if directory else default_stats_dir()
        self.user = (user or getpass.getuser()).lower()

    @property
    def path(self) -> Path:
        return self.directory / "{}.json".format(self.user)

    def load(self) -> dict:
        data = _empty()
        try:
            with open(self.path, encoding="utf-8") as fh:
                stored = json.load(fh)
            if isinstance(stored, dict):
                data.update(stored)
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            log.warning("Statistics file %s unreadable, starting fresh: %s", self.path, exc)
        return data

    def _save(self, data: dict) -> None:
        data["last_date"] = datetime.datetime.now().isoformat(timespec="seconds")
        self.directory.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.directory), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, sort_keys=True, indent=4)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def record_open(self, via: str = "standalone") -> None:
        key = "open_in_maya" if via == "maya" else "open_standalone"
        try:
            data = self.load()
            data[key] = int(data.get(key, 0)) + 1
            self._save(data)
        except OSError as exc:
            log.warning("Could not record statistics: %s", exc)

    def record_launch(self, kind: str, shot: str) -> None:
        """kind is 'cloth', 'hair' or 'render'."""
        try:
            data = self.load()
            entry = data.setdefault(kind, {"times": 0, "shots": []})
            entry["times"] = int(entry.get("times", 0)) + 1
            if shot not in entry.setdefault("shots", []):
                entry["shots"].append(shot)
            self._save(data)
        except OSError as exc:
            log.warning("Could not record statistics: %s", exc)
