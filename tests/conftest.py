import pytest

from farm_dispatcher.core.backend import DemoBackend
from farm_dispatcher.core.config import ConfigStore
from farm_dispatcher.core.scene import Session


@pytest.fixture
def config():
    return ConfigStore()


@pytest.fixture
def session(config):
    s = Session(config, DemoBackend())
    s.set_preference("cfx_artist")
    s.load_shot("demo", "seq010", "0050")
    return s


@pytest.fixture(autouse=True)
def _isolate_user_dirs(tmp_path, monkeypatch):
    """Never write statistics or submissions into the real home directory."""
    monkeypatch.setenv("FARM_DISPATCHER_STATS_DIR", str(tmp_path / "stats"))
    monkeypatch.setenv("FARM_DISPATCHER_PUBLISH_DIR", str(tmp_path / "publish"))
