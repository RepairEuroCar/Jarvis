import pytest

from jarvis.core.main import Jarvis


@pytest.mark.asyncio
async def test_scheduled_task_runs():
    jarvis = Jarvis()
    called = False

    async def sample_task(j):
        nonlocal called
        called = True

    jarvis.register_scheduled_task(sample_task, 1)
    task = jarvis.sensor_manager.scheduled_tasks[0]
    await jarvis._on_scheduled_tick(task)

    assert called
