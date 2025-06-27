import os
import subprocess
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

