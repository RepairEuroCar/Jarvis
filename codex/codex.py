# codex.py ( улучшенная версия)
#!/usr/bin/env python3
# coding: utf-8

import ast
import asyncio
import importlib
import logging
import os
import signal
import time
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any, Tuple

import aio_pika
import docker
import hydra
import restrictedpython
from anyio import CapacityLimiter, Event, create_task_group
from omegaconf import DictConfig, OmegaConf
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

# Monitoring
from prometheus_client import REGISTRY, Counter, Gauge, Histogram, start_http_server

# Core dependencies
from pydantic import BaseModel, Field, ValidationError, validator

# UI (optional)
from rich.logging import RichHandler
from textual.app import App as TextualApp
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .api_docs import generate_api_docs
from .autotest_generation import generate_autotests

# Internal modules
from .executor import run as run_tests
from .linter_task import run_basic_linter

# Constants
DEFAULT_CONFIG = {
    "agent": {
        "poll_interval": 5.0,
        "max_task_timeout": 60.0,
        "retry_delay": 3.0,
        "max_concurrent_tasks": 10,
        "enable_metrics": True,
        "metrics_port": 8000,
        "enable_tracing": True,
    },
    "rabbitmq": {
        "host": "localhost",
        "port": 5672,
        "queue": "codex_tasks",
    },
    "security": {
        "sandbox_enabled": True,
        "memory_limit_mb": 100,
    },
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RichHandler(rich_tracebacks=True),
        logging.FileHandler("codex_agent.log"),
    ],
)
logger = logging.getLogger("codex_agent")

# Setup tracing
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)
tracer = trace.get_tracer("codex.agent")

# Prometheus metrics
TASKS_EXECUTED = Counter(
    "codex_tasks_executed_total", "Total tasks executed", ["status", "task_type"]
)
TASK_DURATION = Histogram(
    "codex_task_duration_seconds",
    "Task execution time",
    ["task_type"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float("inf")),
)
AGENT_STATE = Gauge("codex_agent_state", "Current agent state", ["state"])


class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class TaskType(Enum):
    CODE_EXECUTION = "code_execution"
    TEST_GENERATION = "test_generation"
    DOC_GENERATION = "doc_generation"
    LINTING = "linting"
    TEST_RUN = "test_run"


class Task(BaseModel):
    id: str = Field(..., description="Unique task identifier")
    description: str = Field("", description="Human-readable task description")
    code: str = Field("", description="Python code to execute")
    file_path: str = Field("", description="Path to file for operations")
    output_path: str = Field("", description="Output directory for results")
    priority: TaskPriority = Field(TaskPriority.MEDIUM, description="Task priority")
    timeout: float = Field(30.0, description="Maximum execution time in seconds")
    type: TaskType = Field(TaskType.CODE_EXECUTION, description="Task type")
    dependencies: list[str] = Field([], description="list of dependent task IDs")

    @validator("code")
    def validate_code(cls, v):
        if v:
            try:
                ast.parse(v)
            except SyntaxError as e:
                raise ValueError(f"Invalid Python code: {e}")
        return v


class TaskResult(BaseModel):
    success: bool
    logs: str
    execution_time: float
    metrics: dict[str, Any] = Field(default_factory=dict)
    output_files: list[str] = Field(default_factory=list)


class AgentState(Enum):
    STOPPED = auto()
    STARTING = auto()
    RUNNING = auto()
    STOPPING = auto()
    MAINTENANCE = auto()


@dataclass
class CodexConfig:
    poll_interval: float = 5.0
    max_task_timeout: float = 60.0
    retry_delay: float = 3.0
    max_concurrent_tasks: int = 10
    enable_metrics: bool = True
    metrics_port: int = 8000
    enable_tracing: bool = True
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_queue: str = "codex_tasks"
    sandbox_enabled: bool = True
    memory_limit_mb: int = 100


class ModuleReloader(FileSystemEventHandler):
    def __init__(self, agent):
        self.agent = agent

    def on_modified(self, event):
        if event.src_path.endswith(".py"):
            module_name = Path(event.src_path).stem
            try:
                module = importlib.import_module(module_name)
                importlib.reload(module)
                logger.info(f"♻️ Reloaded module: {module_name}")
                self.agent.on_module_reload(module_name)
            except Exception as e:
                logger.error(f"Failed to reload module {module_name}: {e}")


class CodexDashboard(TextualApp):
    async def on_mount(self) -> None:
        self.agent = CodexAgent()
        await self.agent.start()

    async def on_shutdown(self) -> None:
        await self.agent.stop()


class CodexAgent:
    def __init__(self, config: CodexConfig = None):
        self.config = config or CodexConfig(**DEFAULT_CONFIG["agent"])
        self.state = AgentState.STOPPED
        self._shutdown_event = Event()
        self._task_limiter = CapacityLimiter(self.config.max_concurrent_tasks)
        self._current_tasks = set()
        self._docker_client = docker.from_env() if self.config.sandbox_enabled else None
        self._observer = None
        self._setup_metrics()

    def _setup_metrics(self):
        if self.config.enable_metrics:
            start_http_server(self.config.metrics_port)
            REGISTRY.unregister(
                REGISTRY._names_to_collectors["python_gc_objects_collected_total"]
            )

    async def start(self):
        if self.state != AgentState.STOPPED:
            logger.warning("Agent already running")
            return

        self.state = AgentState.STARTING
        logger.info("🤖 Starting CodexAgent...")

        self._shutdown_event = Event()
        self._start_module_watcher()
        self._start_metrics_updater()

        try:
            async with create_task_group() as tg:
                tg.start_soon(self._run_loop)
                tg.start_soon(self._consume_rabbitmq_tasks)

                self.state = AgentState.RUNNING
                logger.info("🚀 CodexAgent is ready")
                await self._shutdown_event.wait()
        finally:
            await self.stop()

    async def stop(self):
        self.state = AgentState.STOPING
        logger.info("🛑 Stopping CodexAgent...")

        self._shutdown_event.set()
        if self._observer:
            self._observer.stop()
            self._observer.join()

        for task in self._current_tasks:
            task.cancel()

        await asyncio.gather(*self._current_tasks, return_exceptions=True)
        self._current_tasks.clear()

        self.state = AgentState.STOPPED
        logger.info("CodexAgent stopped")

    def _start_module_watcher(self):
        self._observer = Observer()
        self._observer.schedule(ModuleReloader(self), path=".", recursive=True)
        self._observer.start()

    def _start_metrics_updater(self):
        async def _update_metrics():
            while self.state == AgentState.RUNNING:
                AGENT_STATE.labels(state=self.state.name).set(1)
                await asyncio.sleep(5)

        asyncio.create_task(_update_metrics())

    async def _run_loop(self):
        while self.state == AgentState.RUNNING:
            try:
                task = await self._fetch_next_task()
                if task:
                    await self._process_task(task)
                else:
                    await asyncio.sleep(self.config.poll_interval)
            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                await asyncio.sleep(self.config.retry_delay)

    async def _consume_rabbitmq_tasks(self):
        connection = await aio_pika.connect_robust(
            host=self.config.rabbitmq_host,
            port=self.config.rabbitmq_port,
        )

        channel = await connection.channel()
        queue = await channel.declare_queue(self.config.rabbitmq_queue)

        async for message in queue:
            async with message.process():
                try:
                    task = Task.parse_raw(message.body)
                    await self._process_task(task)
                except ValidationError as e:
                    logger.error(f"Invalid task format: {e}")

    async def _process_task(self, task: Task):
        task_start_time = time.monotonic()
        task_span = tracer.start_as_current_span(f"task.{task.type.value}")

        try:
            async with self._task_limiter:
                task_span.set_attributes(
                    {
                        "task.id": task.id,
                        "task.type": task.type.value,
                        "task.priority": task.priority.name,
                    }
                )

                logger.info(f"📌 Processing task {task.id}: {task.description}")

                if task.type == TaskType.CODE_EXECUTION and task.code:
                    success, logs = await self._execute_code(task)
                elif task.type == TaskType.TEST_GENERATION and task.file_path:
                    success, logs, output_files = await self._generate_tests(task)
                elif task.type == TaskType.DOC_GENERATION and task.file_path:
                    success, logs, output_files = await self._generate_docs(task)
                elif task.type == TaskType.LINTING and task.file_path:
                    success, logs, output_files = await self._run_linter(task)
                elif task.type == TaskType.TEST_RUN and task.file_path:
                    success, logs, output_files = await self._run_tests(task)
                else:
                    raise ValueError(f"Unsupported task type: {task.type}")

                exec_time = time.monotonic() - task_start_time
                result = TaskResult(
                    success=success,
                    logs=logs,
                    execution_time=exec_time,
                    metrics={"memory_usage": 0, "cpu_usage": 0},
                    output_files=output_files if "output_files" in locals() else [],
                )

                if success:
                    await self._mark_task_completed(task.id, result)
                    TASKS_EXECUTED.labels(
                        status="success", task_type=task.type.value
                    ).inc()
                    logger.info(f"✅ Task {task.id} completed in {exec_time:.2f}s")
                else:
                    await self._mark_task_failed(task.id, result)
                    TASKS_EXECUTED.labels(
                        status="failed", task_type=task.type.value
                    ).inc()
                    logger.warning(f"❌ Task {task.id} failed")

                TASK_DURATION.labels(task_type=task.type.value).observe(exec_time)
                task_span.set_status(trace.Status.OK if success else trace.Status.ERROR)

        except asyncio.TimeoutError:
            exec_time = time.monotonic() - task_start_time
            logger.error(f"⏰ Task {task.id} timed out after {exec_time:.2f}s")
            await self._mark_task_failed(task.id, "Timeout exceeded")
            TASKS_EXECUTED.labels(status="timeout", task_type=task.type.value).inc()
            task_span.set_status(trace.Status.ERROR)
        except Exception as e:
            exec_time = time.monotonic() - task_start_time
            logger.error(f"⚠️ Critical error in task {task.id}: {e}", exc_info=True)
            await self._mark_task_failed(task.id, str(e))
            TASKS_EXECUTED.labels(status="error", task_type=task.type.value).inc()
            task_span.record_exception(e)
            task_span.set_status(trace.Status.ERROR)
        finally:
            task_span.end()

    async def _execute_code(self, task: Task) -> Tuple[bool, str]:
        if self.config.sandbox_enabled:
            return await self._run_in_container(task)
        return await self._run_in_process(task)

    async def _generate_tests(self, task: Task) -> Tuple[bool, str, list[str]]:
        try:
            output_files = generate_autotests(task.file_path, task.output_path)
            return True, f"Generated {len(output_files)} test files", output_files
        except Exception as e:
            return False, str(e), []

    async def _generate_docs(self, task: Task) -> Tuple[bool, str, list[str]]:
        try:
            output_path = os.path.join(
                task.output_path, f"{Path(task.file_path).stem}_api.txt"
            )
            output_file = generate_api_docs(Path(task.file_path).stem, output_path)
            return True, f"Generated API docs at {output_file}", [output_file]
        except Exception as e:
            return False, str(e), []

    async def _run_linter(self, task: Task) -> Tuple[bool, str, list[str]]:
        try:
            errors = run_basic_linter(task.file_path)
            output_path = os.path.join(task.output_path, "lint_results.txt")
            with open(output_path, "w") as f:
                f.write("\n".join(errors))
            success = len(errors) == 0
            message = (
                f"Found {len(errors)} linting issues"
                if errors
                else "No linting issues found"
            )
            return success, message, [output_path]
        except Exception as e:
            return False, str(e), []

    async def _run_tests(self, task: Task) -> Tuple[bool, str, list[str]]:
        try:
            test_results = await run_tests(task.file_path)
            output_path = os.path.join(task.output_path, "test_results.json")
            with open(output_path, "w") as f:
                import json

                json.dump(test_results, f)
            success = all(r["passed"] for r in test_results.values())
            return success, "Test run completed", [output_path]
        except Exception as e:
            return False, str(e), []

    async def _run_in_container(self, task: Task) -> Tuple[bool, str]:
        if not self._docker_client:
            raise RuntimeError("Docker sandbox is not available")

        container = await asyncio.to_thread(
            self._docker_client.containers.run,
            "python:3.9-slim",
            f"python -c '{task.code}'",
            detach=True,
            mem_limit=f"{self.config.memory_limit_mb}m",
            network_mode="none",
            cpu_period=100000,
            cpu_quota=50000,
        )

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(container.wait), timeout=task.timeout
            )
            logs = await asyncio.to_thread(container.logs)
            return result["StatusCode"] == 0, logs.decode()
        finally:
            await asyncio.to_thread(container.remove, force=True)

    async def _run_in_process(self, task: Task) -> Tuple[bool, str]:
        try:
            if task.code and not self._validate_code_security(task.code):
                return False, "Code security validation failed"

            exec_globals = {}
            exec(task.code, exec_globals)
            return True, "Execution successful"
        except Exception as e:
            return False, str(e)

    def _validate_code_security(self, code: str) -> bool:
        try:
            restrictedpython.compile_restricted(code, "<string>", "exec")
            return True
        except Exception as e:
            logger.warning(f"Security validation failed: {e}")
            return False

    async def _fetch_next_task(self) -> None | [Task]:
        return None

    async def _mark_task_completed(self, task_id: str, result: TaskResult):
        pass

    async def _mark_task_failed(self, task_id: str, error: str):
        pass

    def on_module_reload(self, module_name: str):
        logger.info(f"Module {module_name} was reloaded - updating functionality")


@hydra.main(config_path="conf", config_name="config")
def main(cfg: DictConfig):
    agent_config = CodexConfig(**OmegaConf.to_container(cfg, resolve=True))
    agent = CodexAgent(agent_config)

    loop = asyncio.get_event_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(agent.stop()))

    try:
        loop.run_until_complete(agent.start())
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        if loop.is_running():
            loop.close()


if __name__ == "__main__":
    if os.getenv("CODEX_DASHBOARD"):
        CodexDashboard.run()
    else:
        main()
