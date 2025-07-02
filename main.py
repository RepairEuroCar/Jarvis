#!/usr/bin/env python3

import argparse
import asyncio
import logging
import sys
import traceback
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, Optional, List

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("executor.log")],
)
logger = logging.getLogger("codex.executor.main")


class CommandType(Enum):
    RUN = auto()
    REVIEW = auto()
    VALIDATE = auto()


@dataclass
class ExecutionResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[List[str]] = None
    execution_time: float = 0.0


class CodexExecutor:
    def __init__(self):
        self.command_handlers = {
            CommandType.RUN: self._execute_run,
            CommandType.REVIEW: self._execute_review,
            CommandType.VALIDATE: self._execute_validate,
        }
        self.start_time = 0.0

    async def execute(self, command: CommandType, args: Dict[str, Any]) -> ExecutionResult:
        self.start_time = asyncio.get_event_loop().time()

        if command not in self.command_handlers:
            return self._error_result(f"Unknown command: {command}")

        try:
            logger.info(f"Executing command: {command.name}")
            handler = self.command_handlers[command]
            return await handler(args)
        except Exception as e:
            logger.error(f"Command failed: {command.name}", exc_info=True)
            return self._error_result(
                f"Command execution failed: {str(e)}",
                [traceback.format_exc()]
            )

    async def _execute_run(self, args: Dict[str, Any]) -> ExecutionResult:
        from codex.executor import run
        try:
            path = args.get("path", ".")
            verbose = args.get("verbose", False)

            logger.debug(f"Running analysis on path: {path}")
            result = await run(path)

            return ExecutionResult(
                success=True,
                message="Analysis completed successfully",
                data={"path": path, "result": result, "verbose": verbose},
                execution_time=self._calculate_runtime(),
            )
        except Exception as e:
            raise RuntimeError(f"Run command failed: {str(e)}") from e

    async def _execute_review(self, args: Dict[str, Any]) -> ExecutionResult:
        from codex.executor import review_failures
        try:
            since = args.get("since")
            logger.debug(f"Reviewing failures since: {since or 'beginning'}")
            failures = await review_failures(since=since)

            return ExecutionResult(
                success=True,
                message="Failures review completed",
                data={"failures": failures, "count": len(failures)},
                execution_time=self._calculate_runtime(),
            )
        except Exception as e:
            raise RuntimeError(f"Review command failed: {str(e)}") from e

    async def _execute_validate(self, args: Dict[str, Any]) -> ExecutionResult:
        try:
            checks = [
                ("config", Path("config").exists()),
                ("logs", Path("logs").exists()),
                ("output", Path("output").exists()),
            ]
            failed = [name for name, exists in checks if not exists]

            if failed:
                return self._error_result(
                    "Validation failed: missing directories",
                    data={"missing_dirs": failed},
                )

            return ExecutionResult(
                success=True,
                message="Environment validation passed",
                data={"checks": checks},
                execution_time=self._calculate_runtime(),
            )
        except Exception as e:
            raise RuntimeError(f"Validation failed: {str(e)}") from e

    def _calculate_runtime(self) -> float:
        return asyncio.get_event_loop().time() - self.start_time

    def _error_result(
        self,
        message: str,
        error_details: Optional[List[str]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            success=False,
            message=message,
            error=error_details or ["unknown_error"],
            data=data,
            execution_time=self._calculate_runtime(),
        )


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Codex Executor - инструмент для анализа и выполнения кода",
        epilog="Примеры использования:\n"
               "  ./main.py run --path src/\n"
               "  ./main.py review --since 2023-01-01",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Запустить анализ кода")
    run_parser.add_argument("--path", default=".", help="Путь для анализа")
    run_parser.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")

    review_parser = subparsers.add_parser("review", help="Просмотреть ошибки")
    review_parser.add_argument("--since", help="Фильтр по дате (YYYY-MM-DD)")

    subparsers.add_parser("validate", help="Проверить окружение")

    return parser.parse_args()


def format_output(result: ExecutionResult) -> str:
    output = f"[{'SUCCESS' if result.success else 'ERROR'}] {result.message}"

    if result.data:
        if "result" in result.data:
            output += f"\n\nAnalysis results:\n{result.data['result']}"
        elif "failures" in result.data:
            output += f"\n\nFound {result.data['count']} failures:\n"
            output += "\n".join(result.data["failures"])

    if result.error:
        output += f"\n\nErrors:\n{''.join(result.error)}"

    output += f"\n\nExecution time: {result.execution_time:.2f}s"
    return output


async def async_main():
    args = parse_arguments()
    executor = CodexExecutor()

    command_mapping = {
        "run": CommandType.RUN,
        "review": CommandType.REVIEW,
        "validate": CommandType.VALIDATE,
    }

    result = await executor.execute(command_mapping[args.command], vars(args))
    print(format_output(result))

    if not result.success:
        sys.exit(1)


def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.critical(f"Critical failure: {str(e)}", exc_info=True)
        print(f"Critical error: {str(e)}")
        sys.exit(2)


if __name__ == "__main__":
    main()