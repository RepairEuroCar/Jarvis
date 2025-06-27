import os
import subprocess

import openai

import requests
from git import Repo

REPO_PATH = os.getcwd()
BRANCH = os.getenv("GITHUB_HEAD_REF") or subprocess.getoutput(
    "git rev-parse --abbrev-ref HEAD"
)
REPOSITORY = os.getenv("GITHUB_REPOSITORY")
COMMIT_AUTHOR = {"name": "Jarvis Bot", "email": "jarvis@bot.com"}

openai.api_key = os.getenv("OPENAI_API_KEY")


def get_modified_files():
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1"], capture_output=True, text=True
    )
    return [f.strip() for f in result.stdout.splitlines() if f.endswith(".py")]


def fix_code_with_codex(filepath):
    with open(filepath, encoding="utf-8") as f:
        original_code = f.read()

    messages = [
        {
            "role": "system",
            "content": (
                "Ты AI-программист. Исправь ошибки, улучшай стиль, " "не меняй логику."
            ),
        },
        {
            "role": "user",
            "content": f"Вот файл с ошибками:\n\n```python\n{original_code}\n```",
        },
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.1,
    )

    fixed_code = response.choices[0].message.content
    fixed_code = fixed_code.replace("```python", "").replace("```", "").strip()

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(fixed_code)


def create_pull_request():
    token = os.getenv("BOT_PUSH_TOKEN")
    repo = REPOSITORY
    head = BRANCH
    base = "main"

    pr_url = f"https://api.github.com/repos/{repo}/pulls"
    headers = {"Authorization": f"token {token}"}
    data = {
        "title": "🧠 Auto PR: Fixes by Codex",
        "head": head,
        "base": base,
        "body": "Автоматическое исправление и улучшения, предложенные Codex-агентом.",
    }

    response = requests.post(pr_url, json=data, headers=headers)
    if response.status_code in (200, 201):
        print("✅ PR создан:", response.json().get("html_url"))
    elif (
        response.status_code == 422 and "A pull request already exists" in response.text
    ):
        print("ℹ️ PR уже существует")
    else:
        print("❌ Ошибка создания PR:", response.status_code, response.text)


def commit_and_push():
    repo = Repo(REPO_PATH)
    repo.git.add(A=True)
    if repo.is_dirty():
        repo.index.commit("🧹 Auto-fix by Codex", author=COMMIT_AUTHOR)
    origin = repo.remote(name="origin")
    try:
        origin.push(refspec=f"{BRANCH}:{BRANCH}")
    except Exception:
        print("⚠️ Push не удался — создаём PR")
        create_pull_request()
    else:
        print("✔ No changes to commit.")


if __name__ == "__main__":
    files = get_modified_files()
    for file in files:
        print(f"Fixing: {file}")
        fix_code_with_codex(file)
    commit_and_push()

from git import Repo


def run_tests() -> tuple[str, int]:
    """Run the test suite and capture output."""
    process = subprocess.run(["pytest", "-q"], capture_output=True, text=True)
    return process.stdout + process.stderr, process.returncode


def request_patch(logs: str) -> str:
    """Ask OpenAI for a patch to fix failing tests."""
    system_prompt = (
        "You are an automated code fixing agent. "
        "Provide a git diff patch that resolves the failing tests."
    )
    user_prompt = f"Tests failed with the following output:\n\n{logs}\n\nProvide patch:"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )
    return response.choices[0].message.content


def apply_patch(patch: str) -> None:
    """Apply a unified diff patch to the repository."""
    patch_file = "codex_patch.diff"
    with open(patch_file, "w", encoding="utf-8") as f:
        f.write(patch)
    subprocess.run(["git", "apply", patch_file], check=True)


def commit_and_push(message: str) -> None:
    """Commit all changes and push using the bot token."""
    repo = Repo(".")
    repo.git.add(A=True)
    repo.index.commit(message)
    token = os.environ.get("BOT_PUSH_TOKEN")
    if not token:
        print("BOT_PUSH_TOKEN not set; skipping push")
        return
    url = repo.remotes.origin.url
    if url.startswith("https://"):
        url = url.replace("https://", f"https://{token}@")
    repo.git.push(url, repo.head.ref.name)


def main() -> None:
    logs, returncode = run_tests()
    if returncode == 0:
        print("Tests passed; nothing to fix.")
        return
    print("Requesting fix from OpenAI...")
    patch = request_patch(logs)
    apply_patch(patch)
    commit_and_push("Apply fixes from Codex agent")


if __name__ == "__main__":
    main()

