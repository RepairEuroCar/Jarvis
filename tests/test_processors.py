import pytest
from jarvis.processors import (
    APIBuilderProcessor,
    RefactorProcessor,
    TestGeneratorProcessor,
)


@pytest.mark.asyncio
async def test_api_builder_from_description():
    proc = APIBuilderProcessor()
    desc = "GET /hello\nPOST /submit"
    result = await proc.process("create api", {"api_description": desc})
    assert "@app.get('/hello')" in result["api_code"]
    assert "@app.post('/submit')" in result["api_code"]


@pytest.mark.asyncio
async def test_refactor_pep8():
    proc = RefactorProcessor()
    src = "def foo():\n    MyVar=1\n    return MyVar\n"
    result = await proc.process("refactor", {"source_code": src})
    assert "my_var" in result["refactored_code"]
    assert "return my_var" in result["refactored_code"]


@pytest.mark.asyncio
async def test_test_generator_docstring():
    proc = TestGeneratorProcessor()
    source = """
def add(a, b):
    \"\"\"
    >>> add(1, 2)
    3
    \"\"\"
    return a + b
"""
    result = await proc.process(
        "generate", {"function_name": "add", "source_code": source}
    )
    assert "add(1, 2) == 3" in result["generated_test"]
