"""Asynchronous code dataset generator used by Jarvis.

This module provides a small framework for generating synthetic code
examples. The functionality is inspired by the "Modern Python Code
Dataset Generator" snippet. Only a subset is implemented to keep the
implementation lightweight for the test suite.
"""

from __future__ import annotations

REQUIRES = ["aiofiles", "faker", "loguru", "pydantic"]

import json
import random
import re
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import gzip
import shutil

import aiofiles
from faker import Faker
from loguru import logger
from pydantic import BaseModel, Field, validator

from command_dispatcher import CommandDispatcher, default_dispatcher
from core.metrics.module_usage import track_usage

DEFAULT_CHUNK_SIZE = 1000
SUPPORTED_LANGUAGES = ["python"]
COMPRESSION_LEVEL = 3
COMPRESSED_EXTENSION = ".jsonl.gz"


class CodeCategory(str, Enum):
    WEB = "web"
    DATA = "data"
    SYSTEM = "system"
    ALGORITHMS = "algorithms"
    CLASSES = "classes"
    AI = "ai"
    GAMES = "games"


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class CodeExample(BaseModel):
    instruction: str = Field(..., min_length=5, max_length=500)
    code: str = Field(..., min_length=20)
    tests: Optional[str] = None
    docs: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    category: CodeCategory
    difficulty: DifficultyLevel
    language: str = "python"
    dependencies: Optional[List[str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("language")
    def _validate_language(cls, v: str) -> str:
        if v.lower() not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {v}")
        return v.lower()

    @validator("code")
    def _validate_code(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Code cannot be empty")
        return v


class DatasetConfig(BaseModel):
    target_size_gb: float = Field(0.1, gt=0)
    output_dir: Path = Path("./dataset_output")
    validate_code: bool = True
    include_tests: bool = True
    include_docs: bool = False
    min_examples_per_category: int = 10
    max_retries: int = 3
    timeout: int = 300
    chunk_size: int = DEFAULT_CHUNK_SIZE


class BaseCodeGenerator:
    def __init__(self, language: str = "python") -> None:
        self.language = language
        self.faker = Faker()
        Faker.seed(42)
        random.seed(42)

    async def generate_example(self) -> CodeExample:  # pragma: no cover - subclass
        raise NotImplementedError


class PythonCodeGenerator(BaseCodeGenerator):
    def __init__(self) -> None:
        super().__init__("python")

    async def _generate_function(self, category: CodeCategory) -> CodeExample:
        func_name = self.faker.unique.word().lower()
        return_type = random.choice(["int", "str", "bool", "float", "dict", "list"])

        instruction = (
            f"Write a Python function `{func_name}` that returns {return_type}."
        )
        logic_map = {
            "int": "    result = len(str(data))",
            "str": "    result = str(data)",
            "bool": "    result = bool(data)",
            "float": (
                "    try:\n"
                "        result = float(data)\n"
                "    except (TypeError, ValueError):\n"
                "        result = 0.0"
            ),
            "dict": "    result = {'data': data}",
            "list": "    result = [data]",
        }
        logic = logic_map.get(return_type, f"    result = {self._mock_value(return_type)}")
        code = (
            f"def {func_name}(data):\n"
            f'    """Process data and return {return_type}."""\n'
            f"{logic}\n"
            f"    return result\n"
        )
        return CodeExample(
            instruction=instruction,
            code=code,
            category=category,
            difficulty=random.choice(list(DifficultyLevel)),
        )

    def _mock_value(self, t: str) -> str:
        return {
            "int": "0",
            "str": '""',
            "bool": "False",
            "float": "0.0",
            "dict": "{}",
            "list": "[]",
        }[t]

    async def generate_example(self) -> CodeExample:
        category = random.choice(list(CodeCategory))
        return await self._generate_function(category)


class CodeValidator:
    @staticmethod
    async def validate_syntax(code: str, language: str) -> bool:
        if language == "python":
            try:
                compile(code, "<string>", "exec")
                return True
            except SyntaxError:
                return False
        return True

    @staticmethod
    async def check_complexity(code: str) -> Tuple[int, int]:
        lines = code.split("\n")
        complexity = sum(
            1
            for line in lines
            if re.search(r"\b(if|else|for|while|try|except)\b", line)
        )
        return len(lines), complexity


class DatasetBuilder:
    def __init__(self, config: DatasetConfig) -> None:
        self.config = config
        self.generator = PythonCodeGenerator()
        self._setup_directories()

    def _setup_directories(self) -> None:
        self.config.output_dir.mkdir(exist_ok=True, parents=True)
        (self.config.output_dir / "raw").mkdir(exist_ok=True)
        (self.config.output_dir / "compressed").mkdir(exist_ok=True)

    async def _generate_chunk(self, chunk_size: int) -> List[CodeExample]:
        examples: List[CodeExample] = []
        for _ in range(chunk_size):
            example = await self.generator.generate_example()
            if self.config.validate_code:
                if not await CodeValidator.validate_syntax(example.code, "python"):
                    continue
            examples.append(example)
        return examples

    async def _write_chunk(self, examples: List[CodeExample], chunk_num: int) -> int:
        chunk_file = self.config.output_dir / "raw" / f"chunk_{chunk_num}.jsonl"
        async with aiofiles.open(chunk_file, "w") as fh:
            for ex in examples:
                data = (
                    ex.model_dump_json()
                    if hasattr(ex, "model_dump_json")
                    else ex.json()
                )
                await fh.write(data + "\n")

        compressed_dir = self.config.output_dir / "compressed"
        compressed_file = compressed_dir / f"chunk_{chunk_num}{COMPRESSED_EXTENSION}"
        with open(chunk_file, "rb") as src, gzip.open(
            compressed_file, "wb", compresslevel=COMPRESSION_LEVEL
        ) as dst:
            shutil.copyfileobj(src, dst)

        size = compressed_file.stat().st_size
        chunk_file.unlink()
        return size

    async def generate(self) -> None:
        total_size = 0
        chunk_num = 0
        target_bytes = int(self.config.target_size_gb * 1024**3)
        logger.info(
            f"Generating dataset to {self.config.output_dir} "
            f"(~{self.config.target_size_gb} GB)"
        )
        while total_size < target_bytes:
            examples = await self._generate_chunk(self.config.chunk_size)
            size = await self._write_chunk(examples, chunk_num)
            total_size += size
            logger.debug(f"Chunk {chunk_num} size {size} bytes")
            chunk_num += 1
            if self.config.chunk_size <= 10 and total_size >= target_bytes:
                break

        metadata = {
            "chunks": chunk_num,
            "examples_per_chunk": self.config.chunk_size,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "compression": "gzip",
            "compression_level": COMPRESSION_LEVEL,
            "chunk_extension": COMPRESSED_EXTENSION,
            "total_size_bytes": total_size,
        }
        async with aiofiles.open(self.config.output_dir / "metadata.json", "w") as fh:
            await fh.write(json.dumps(metadata, indent=2))
        logger.info("Dataset generation complete")


@track_usage("dataset_generator")
async def generate_dataset(
    output: str, size_gb: float = 0.001, chunk_size: int = 10
) -> str:
    config = DatasetConfig(
        target_size_gb=size_gb, output_dir=Path(output), chunk_size=chunk_size
    )
    builder = DatasetBuilder(config)
    await builder.generate()
    return f"Dataset generated in {output}"


async def read_metadata(output: str | Path) -> Dict[str, Any]:
    output = Path(output)
    metadata_file = output / "metadata.json"
    async with aiofiles.open(metadata_file, "r") as fh:
        metadata = json.loads(await fh.read())

    ext = metadata.get("chunk_extension", COMPRESSED_EXTENSION)
    compressed_dir = output / "compressed"
    chunk_files = list(compressed_dir.glob(f"chunk_*{ext}"))
    if not chunk_files:
        chunk_files = list((output / "raw").glob("chunk_*" + ext))

    size = sum(f.stat().st_size for f in chunk_files)
    metadata["total_size_bytes"] = size
    metadata["chunk_extension"] = ext
    return metadata


def register_commands(dispatcher: CommandDispatcher = default_dispatcher) -> None:
    dispatcher.register_command_handler("dataset", "generate", generate_dataset)


register_commands(default_dispatcher)

__all__ = [
    "generate_dataset",
    "DatasetBuilder",
    "register_commands",
    "read_metadata",
]
