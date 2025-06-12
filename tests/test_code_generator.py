import os
from utils.code_generator import dsl_to_python, write_code


def test_dsl_to_python_simple():
    code = dsl_to_python("создай функцию foo")
    assert "def foo" in code


def test_write_code(tmp_path):
    path = tmp_path / "out.py"
    result = write_code({"dsl": "создай функцию bar", "category": "utility", "path": str(path)})
    assert os.path.isfile(result)
    content = path.read_text(encoding="utf-8")
    assert "def bar" in content
