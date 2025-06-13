import pytest

from modules.git_manager import GitManager


@pytest.mark.asyncio
async def test_clone_invalid_url(monkeypatch, tmp_path):
    gm = GitManager(base_dir=tmp_path)
    called = False

    async def fake_run(*args, **kwargs):
        nonlocal called
        called = True
        return "", "", 0

    monkeypatch.setattr(gm, "_run_git_command", fake_run)
    result = await gm.clone(None, "https://example.com/repo.git; rm -rf /")
    assert "Invalid repository URL" in result
    assert not called


@pytest.mark.asyncio
async def test_checkout_invalid_branch(monkeypatch, tmp_path):
    gm = GitManager(base_dir=tmp_path)
    called = False

    async def fake_run(*args, **kwargs):
        nonlocal called
        called = True
        return "", "", 0

    monkeypatch.setattr(gm, "_run_git_command", fake_run)
    result = await gm.checkout(None, "bad&&branch")
    assert "Invalid branch name" in result
    assert not called
