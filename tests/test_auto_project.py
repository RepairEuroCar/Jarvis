import py_compile
from pathlib import Path

from plugins import auto_project


def test_generate_and_compile(tmp_path: Path):
    spec = tmp_path / "spec.txt"
    spec.write_text("- создай функцию foo\n- создай функцию bar", encoding="utf-8")
    out_dir = tmp_path / "proj"
    files = auto_project._generate_and_compile(
        spec.read_text(encoding="utf-8"), str(out_dir)
    )
    assert len(files) == 2
    for f in files:
        assert Path(f).exists(), f"missing {f}"
        py_compile.compile(f, doraise=True)
