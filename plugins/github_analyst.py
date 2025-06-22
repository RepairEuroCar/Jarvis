import os
import tempfile

import aiohttp

from jarvis.commands.registry import CommandCategory, CommandInfo
from jarvis.core.main import RegisteredCommand
from modules.analyzer import AdvancedCodeAnalyzer, _format_report


async def _get_github_token(jarvis):
    token = jarvis.memory.recall("github_token")
    if not token:
        msg = (
            "Error: GitHub token not found in memory. Please use "
            "'remember github_token <token>'."
        )
        return None, msg
    return token, None


async def _gh_get_json(url: str, token: str):
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                return None, f"GitHub API error {resp.status}: {await resp.text()}"
            return await resp.json(), None


def register(jarvis) -> None:
    async def gh_read_issue(event):
        parts = event.text.split()
        if len(parts) < 3:
            return "Usage: gh.read_issue <owner/repo> <number>"
        repo, num = parts[1], parts[2]
        token, err = await _get_github_token(jarvis)
        if err:
            return err
        data, err = await _gh_get_json(
            f"https://api.github.com/repos/{repo}/issues/{num}", token
        )
        if err:
            return err
        title = data.get("title", "")
        body = data.get("body", "")
        state = data.get("state", "")
        return f"Issue #{num} ({state})\nTitle: {title}\n\n{body}"

    async def gh_analyze_pr(event):
        parts = event.text.split()
        if len(parts) < 3:
            return "Usage: gh.analyze_pr <owner/repo> <number>"
        repo, num = parts[1], parts[2]
        token, err = await _get_github_token(jarvis)
        if err:
            return err
        files, err = await _gh_get_json(
            f"https://api.github.com/repos/{repo}/pulls/{num}/files", token
        )
        if err:
            return err
        analyzer = getattr(jarvis, "adv_code_analyzer", None)
        if analyzer is None:
            analyzer = AdvancedCodeAnalyzer(jarvis)
        reports = []
        for f in files:
            raw = f.get("raw_url")
            filename = f.get("filename")
            if not raw or not filename.endswith(".py"):
                continue
            async with aiohttp.ClientSession() as session:
                async with session.get(raw) as resp:
                    if resp.status != 200:
                        continue
                    code = await resp.text()
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=os.path.basename(filename),
            ) as tmp:
                tmp.write(code.encode("utf-8"))
                tmp_path = tmp.name
            report, _ = await analyzer.generate_comprehensive_report(tmp_path)
            os.unlink(tmp_path)
            if report:
                reports.append(_format_report(report, "markdown"))
        if not reports:
            return "No analyzable Python files in PR."
        return "\n\n".join(reports)

    jarvis.commands["gh.read_issue"] = RegisteredCommand(
        info=CommandInfo(
            name="gh.read_issue",
            description="Read a GitHub issue",
            category=CommandCategory.DEVELOPMENT,
            usage="gh.read_issue <owner/repo> <number>",
            aliases=[],
        ),
        handler=gh_read_issue,
    )

    jarvis.commands["gh.analyze_pr"] = RegisteredCommand(
        info=CommandInfo(
            name="gh.analyze_pr",
            description="Analyze a GitHub PR using AdvancedCodeAnalyzer",
            category=CommandCategory.DEVELOPMENT,
            usage="gh.analyze_pr <owner/repo> <number>",
            aliases=[],
        ),
        handler=gh_analyze_pr,
    )
