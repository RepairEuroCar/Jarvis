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
