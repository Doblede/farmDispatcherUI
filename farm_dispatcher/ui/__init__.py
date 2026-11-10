"""Qt widgets. Everything here talks to farm_dispatcher.core through a Session."""

from pathlib import Path

ICONS_DIR = Path(__file__).resolve().parent.parent / "icons"


def icon_path(name: str) -> str:
    return str(ICONS_DIR / name)
