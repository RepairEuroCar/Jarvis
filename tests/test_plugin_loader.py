from pathlib import Path

from jarvis.plugins import load_plugins


class DummyJarvis:
    pass


def _create_plugin(dir: Path, name: str, flag: str) -> None:
    plugin = dir / f"{name}.py"
    plugin.write_text(f"def register(j):\n    j.{flag} = True\n")


def test_load_plugins_from_multiple_dirs(tmp_path):
    dir1 = tmp_path / "p1"
    dir2 = tmp_path / "p2"
    dir1.mkdir()
    dir2.mkdir()
    _create_plugin(dir1, "a", "loaded_a")
    _create_plugin(dir2, "b", "loaded_b")

    j = DummyJarvis()
    load_plugins(j, str(dir1), [str(dir2)])
    assert getattr(j, "loaded_a", False)
    assert getattr(j, "loaded_b", False)
