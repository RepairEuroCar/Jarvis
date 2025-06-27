import logging
from pathlib import Path

from core.config_reloader import ConfigReloader
from jarvis.core.main import Jarvis


def test_detect_yaml_changes(tmp_path: Path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("logging:\n  level: INFO\n", encoding="utf-8")
    reloader = ConfigReloader(str(cfg))
    cfg.write_text("logging:\n  level: DEBUG\n", encoding="utf-8")
    reloader.reload(["logging"])
    assert reloader._data["logging"]["level"] == "DEBUG"
    reloader.stop()


def test_callback_invocation(tmp_path: Path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("logging:\n  level: INFO\n", encoding="utf-8")
    reloader = ConfigReloader(str(cfg))
    called: list[str] = []

    def cb(data: dict) -> None:
        called.append(data.get("level"))

    reloader.subscribe("logging", cb)
    cfg.write_text("logging:\n  level: WARNING\n", encoding="utf-8")
    reloader.reload(["logging"])
    assert called == ["WARNING"]
    reloader.stop()


def test_log_level_update(tmp_path: Path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("logging:\n  level: INFO\n", encoding="utf-8")
    jarvis = Jarvis(config_path=str(cfg))
    assert logging.getLogger().level == logging.INFO

    cfg.write_text("logging:\n  level: DEBUG\n", encoding="utf-8")
    jarvis.config_reloader.reload(["logging"])
    assert logging.getLogger().level == logging.DEBUG
    jarvis.config_reloader.stop()

