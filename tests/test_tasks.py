from codex.tasks import load_tasks, Task


def test_load_default_tasks():
    tasks = load_tasks()
    assert len(tasks) == 6
    assert tasks[0] == Task(
        id="setup-env",
        title="Setup environment",
        description="Install dependencies for Jarvis.",
        module="scripts.setup",
        action="install_dependencies",
        estimated_minutes=10,
    )
    assert tasks[1].id == "run-jarvis"
    assert tasks[2].id == "basic-linter"
    assert tasks[3].id == "generate-tests"
    assert tasks[4].id == "api-docs"
    assert tasks[5].id == "generate-core-tests"


def test_load_custom_tasks(tmp_path):
    data = [
        {
            "id": "t1",
            "title": "Example",
            "description": "Desc",
            "module": "mod",
            "action": "act",
            "estimated_minutes": 5,
        }
    ]
    custom = tmp_path / "tasks.yaml"
    import yaml

    custom.write_text(yaml.safe_dump(data), encoding="utf-8")
    tasks = load_tasks(custom)
    assert len(tasks) == 1
    assert tasks[0].id == "t1"
