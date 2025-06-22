# Python Language Overview

This document summarizes key concepts of the Python programming language. It is intended as a quick reference for Jarvis developers and users.

## Running Python code

```
python script.py           # execute a script
python -i script.py        # drop into interactive mode after running
python -m module           # run a module as a script
```

Use `pip install` to add third‑party packages. Virtual environments created with `python -m venv` keep dependencies isolated.

## Basic Syntax

- Indentation defines blocks of code. Use four spaces per level.
- Variables are created by assignment: `name = "Jarvis"`.
- Common data types: integers, floats, strings, lists, tuples, sets and dictionaries.
- Strings support f‑string interpolation: `f"Hello {name}"`.

## Control Flow

- `if`, `elif` and `else` choose between alternatives.
- `for` loops iterate over sequences; `range()` generates a sequence of numbers.
- `while` loops repeat until a condition becomes false.
- Comprehensions produce new lists, sets or dictionaries in a single expression.

## Functions

Declare a function with `def`:

```python
def greet(user: str) -> str:
    """Return a friendly greeting."""
    return f"Hello, {user}!"
```

Default arguments and `*args`/`**kwargs` are supported. Document behaviour in the function's docstring.

## Modules and Packages

- `import module` or `from module import name` brings code from other files.
- Packages are directories with an `__init__.py` file.
- Add runtime dependencies to `requirements.txt` and development tools to
  `dev-requirements.txt` or `pyproject.toml`.

## Classes and Objects

Classes group related data and behaviour:

```python
class Robot:
    def __init__(self, name: str) -> None:
        self.name = name

    def speak(self) -> None:
        print(f"I am {self.name}")
```

Inheritance lets one class extend another.

## Exception Handling

Use `try`, `except`, `else` and `finally` to respond to errors:

```python
try:
    result = risky_call()
except ValueError as exc:
    print(f"Bad value: {exc}")
else:
    print(result)
finally:
    cleanup()
```

## Asynchronous Programming

`async def` defines a coroutine. Use `await` to pause until another coroutine completes:

```python
import asyncio

async def main():
    await asyncio.sleep(1)
    print("Done")

asyncio.run(main())
```

## Code Style

Follow [PEP 8](https://peps.python.org/pep-0008/) for readability. Tools like `flake8` or `black` enforce formatting automatically. Run `scripts/format.sh` to apply the project's style.

## Further Reading

The [official Python documentation](https://docs.python.org/) contains detailed tutorials and library references.
