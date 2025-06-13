import pytest

from utils.python_dsl import generate_code_from_schema


def test_generate_function_with_loop():
    schema = {
        "type": "Function",
        "name": "demo",
        "args": ["n"],
        "body": [
            {"type": "Loop", "var": "i", "iter": "range(n)", "body": ["print(i)"]}
        ],
    }
    code = generate_code_from_schema(schema)
    assert "def demo" in code
    assert "for i in range(n)" in code


def test_generate_class():
    schema = {
        "type": "Class",
        "name": "Greeter",
        "body": [
            {
                "type": "Function",
                "name": "greet",
                "args": ["self", "name"],
                "body": ["print(name)"],
            }
        ],
    }
    code = generate_code_from_schema(schema)
    assert "class Greeter" in code
    assert "def greet" in code
