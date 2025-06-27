import asyncio
import os
import re
import subprocess  # Keep for GitManager._run_git_command (uses asyncio.create_subprocess_shell)
from urllib.parse import urlparse

import aiohttp

from utils.http_logging import LoggedClientSession
from utils.logger import get_logger

logger = get_logger().getChild("git_manager")


class GitManager:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir if base_dir else os.getcwd()
        self.session = None  # aiohttp.ClientSession, initialized on demand

    INVALID_PATTERNS = [";", "&&", "\n"]

    def _is_safe(self, value: str) -> bool:
        return not any(p in value for p in self.INVALID_PATTERNS)

    def _validate_repo_url(self, url: str) -> bool:
        if not url or not self._is_safe(url):
            return False
        parsed = urlparse(url)
        if parsed.scheme:
            return parsed.scheme in {"http", "https", "ssh", "git", "file"} and bool(
                parsed.netloc or parsed.path
            )
        return bool(re.match(r"^[\w.@:/+-]+$", url))

    def _validate_branch_name(self, name: str) -> bool:
        if not name or not self._is_safe(name):
            return False
        return re.match(r"^[A-Za-z0-9._/-]+$", name) is not None

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = LoggedClientSession()
        return self.session

    async def health_check(self) -> bool:
        """Check that the git executable is available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "git",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            ok = proc.returncode == 0
            if not ok:
                logger.warning("git --version exited with %s", proc.returncode)
            return ok
        except Exception as exc:  # pragma: no cover - best effort logging
            logger.warning("Git health check failed: %s", exc)
            return False

    async def _run_git_command(self, command_args, cwd=None):
        """Run a git command and capture output with error handling."""
        git_executable = "git"  # Or allow configuration
        full_command = [git_executable] + command_args

        effective_cwd = cwd if cwd else self.base_dir
        if not os.path.isdir(effective_cwd):
            return "", f"Error: Working directory '{effective_cwd}' does not exist.", 1

        try:
            process = await asyncio.create_subprocess_exec(
                *full_command,
                cwd=effective_cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            return (
                stdout.decode().strip(),
                stderr.decode().strip(),
                process.returncode,
            )
        except FileNotFoundError:
            logger.warning("git executable not found")
            return "", "git executable not found", 1
        except Exception as e:
            logger.warning("git command failed: %s", e)
            return "", f"Exception while running git: {e}", 1

    async def init(self, jarvis_instance, repo_path_str=None):
        """Initializes a new Git repository. [repo_subdir]"""
        path = (
            os.path.join(self.base_dir, repo_path_str)
            if repo_path_str
            else self.base_dir
        )
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
        stdout, stderr, returncode = await self._run_git_command(["init"], cwd=path)
        if returncode == 0:
            return f"Git repository initialized at {path}"
        else:
            return f"Error initializing Git repository at {path}:\n{stderr}"

    async def clone(self, jarvis_instance, repo_url, local_path_str=None):
        """Clones a repository. <repo_url> [local_subdir]"""
        if not self._validate_repo_url(repo_url):
            return "Invalid repository URL."

        # If local_path_str is provided, clone into a subdirectory of base_dir
        # If not, git clone will create a dir based on repo name in base_dir
        command = ["clone", repo_url]
        target_dir = (
            self.base_dir
        )  # Clone into base_dir (git creates subdir by default)

        if local_path_str:
            # If local_path_str is an absolute path, use it. Otherwise, join with base_dir.
            if os.path.isabs(local_path_str):
                final_path = local_path_str
            else:
                final_path = os.path.join(self.base_dir, local_path_str)
            command.append(final_path)  # Specify clone directory
            clone_destination_display = final_path
        else:
            # Git will determine the directory name from the URL, created within self.base_dir
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            clone_destination_display = os.path.join(self.base_dir, repo_name)

        stdout, stderr, returncode = await self._run_git_command(
            command, cwd=self.base_dir
        )  # cwd is where git clone runs, not necessarily the final path

        if returncode == 0:
            return (
                f"Repository {repo_url} cloned to {clone_destination_display}\n{stdout}"
            )
        else:
            return f"Error cloning {repo_url}:\n{stderr}"

    async def status(self, jarvis_instance, repo_path_str=None):
        """Gets the status of a Git repository. [repo_subdir]"""
        path = (
            os.path.join(self.base_dir, repo_path_str)
            if repo_path_str
            else self.base_dir
        )
        stdout, stderr, returncode = await self._run_git_command(["status"], cwd=path)
        if returncode == 0:
            return stdout if stdout else "No changes."
        else:
            return f"Error getting Git status for {path}:\n{stderr}"

    async def add(self, jarvis_instance, files=".", repo_path_str=None):
        """Adds files to the Git index. [files_to_add] [repo_subdir]"""
        path = (
            os.path.join(self.base_dir, repo_path_str)
            if repo_path_str
            else self.base_dir
        )
        stdout, stderr, returncode = await self._run_git_command(
            ["add", files], cwd=path
        )
        if returncode == 0:
            return f"Added '{files}' to Git index in {path}."
        else:
            return f"Error adding '{files}' in {path}:\n{stderr}"

    async def commit(self, jarvis_instance, message, repo_path_str=None):
        """Commits staged changes. <message> [repo_subdir]"""
        path = (
            os.path.join(self.base_dir, repo_path_str)
            if repo_path_str
            else self.base_dir
        )
        stdout, stderr, returncode = await self._run_git_command(
            ["commit", "-m", message], cwd=path
        )
        if returncode == 0:
            return f"Commit successful in {path}:\n{stdout}"
        else:
            return f"Error during Git commit in {path}:\n{stderr}"

    async def branch(self, jarvis_instance, branch_name_ops_str, repo_path_str=None):
        """Lists branches, creates a new branch, or deletes a branch. [-d <name>] [<new_branch_name>] [repo_subdir]"""
        path = (
            os.path.join(self.base_dir, repo_path_str)
            if repo_path_str
            else self.base_dir
        )

        parts = branch_name_ops_str.split()
        command = ["branch"]
        action_msg = "Listing branches"

        if not branch_name_ops_str:  # List branches
            pass
        elif len(parts) == 1 and not parts[0].startswith("-"):  # Create branch
            if not self._validate_branch_name(parts[0]):
                return "Invalid branch name."
            command.append(parts[0])
            action_msg = f"Creating branch '{parts[0]}'"
        elif len(parts) == 2 and parts[0] == "-d":  # Delete branch
            if not self._validate_branch_name(parts[1]):
                return "Invalid branch name."
            command.extend(["-d", parts[1]])
            action_msg = f"Deleting branch '{parts[1]}'"
        else:
            return "Usage: git_branch OR git_branch <new_branch_name> OR git_branch -d <branch_to_delete>"

        stdout, stderr, returncode = await self._run_git_command(command, cwd=path)
        if returncode == 0:
            return f"{action_msg} for {path}:\n{stdout if stdout else 'No output.'}"
        else:
            return f"Error with branch operation in {path} for '{branch_name_ops_str}':\n{stderr}"

    async def checkout(self, jarvis_instance, branch_name, repo_path_str=None):
        """Switches to a branch. <branch_name> [repo_subdir]"""
        path = (
            os.path.join(self.base_dir, repo_path_str)
            if repo_path_str
            else self.base_dir
        )
        if not self._validate_branch_name(branch_name):
            return "Invalid branch name."
        stdout, stderr, returncode = await self._run_git_command(
            ["checkout", branch_name], cwd=path
        )
        if returncode == 0:
            return f"Switched to branch '{branch_name}' in {path}.\n{stdout}"
        else:
            return f"Error checking out branch '{branch_name}' in {path}:\n{stderr}"

    async def push(self, jarvis_instance, remote_branch_str, repo_path_str=None):
        """Pushes changes to a remote. [<remote_name> <branch_name>] [repo_subdir] (Defaults: origin main)"""
        path = (
            os.path.join(self.base_dir, repo_path_str)
            if repo_path_str
            else self.base_dir
        )
        parts = remote_branch_str.split()
        remote = parts[0] if len(parts) > 0 else "origin"
        branch = parts[1] if len(parts) > 1 else "main"  # Or get current branch

        if not self._validate_branch_name(branch):
            return "Invalid branch name."

        stdout, stderr, returncode = await self._run_git_command(
            ["push", remote, branch], cwd=path
        )
        if returncode == 0:
            return f"Push successful to {remote}/{branch} from {path}.\n{stdout}"
        else:
            return f"Error during Git push from {path}:\n{stderr}"

    async def pull(self, jarvis_instance, remote_branch_str, repo_path_str=None):
        """Pulls changes from a remote. [<remote_name> <branch_name>] [repo_subdir] (Defaults: origin main)"""
        path = (
            os.path.join(self.base_dir, repo_path_str)
            if repo_path_str
            else self.base_dir
        )
        parts = remote_branch_str.split()
        remote = parts[0] if len(parts) > 0 else "origin"
        branch = parts[1] if len(parts) > 1 else "main"  # Or get current branch

        if not self._validate_branch_name(branch):
            return "Invalid branch name."

        stdout, stderr, returncode = await self._run_git_command(
            ["pull", remote, branch], cwd=path
        )
        if returncode == 0:
            return f"Pull successful from {remote}/{branch} into {path}.\n{stdout}"
        else:
            return f"Error during Git pull into {path}:\n{stderr}"

    async def interactive_commit(self, jarvis_instance, repo_path_str=None):
        """Starts an interactive Git commit session. [repo_subdir]"""
        path = (
            os.path.join(self.base_dir, repo_path_str)
            if repo_path_str
            else self.base_dir
        )
        # This will directly interact with the terminal where Jarvis is running.
        # No easy way to capture stdout/stderr here without complex tty emulation.
        print(
            f"Starting interactive Git commit in {path}. Follow prompts in your terminal."
        )
        try:
            # Use asyncio.create_subprocess_shell for direct terminal interaction
            # This might not work as expected if Jarvis's stdin/stdout are not a real TTY
            # For a CLI app, this is usually fine.
            process = await asyncio.create_subprocess_shell(
                "git commit -v",  # -v for verbose, shows diff
                cwd=path,
                # stdin, stdout, stderr default to parent's, which is what we want here
            )
            await process.wait()
            if process.returncode == 0:
                return "Interactive commit finished successfully."
            else:
                return f"Interactive commit exited with code {process.returncode}."
        except Exception as e:
            return f"Error starting interactive commit: {e}"

    async def view_log(self, jarvis_instance, limit_str="5", repo_path_str=None):
        """Views the Git commit log. [limit] [repo_subdir]"""
        path = (
            os.path.join(self.base_dir, repo_path_str)
            if repo_path_str
            else self.base_dir
        )
        try:
            limit = int(limit_str)
        except ValueError:
            return "Invalid limit for log. Please provide a number."

        stdout, stderr, returncode = await self._run_git_command(
            ["log", "--oneline", f"-n {limit}"], cwd=path
        )
        if returncode == 0:
            return f"Git log for {path} (last {limit} commits):\n{stdout}"
        else:
            return f"Error viewing Git log for {path}:\n{stderr}"

    async def fetch_remote_branches(
        self, jarvis_instance, remote_str="origin", repo_path_str=None
    ):
        """Fetches remote branches. [remote_name] [repo_subdir]"""
        path = (
            os.path.join(self.base_dir, repo_path_str)
            if repo_path_str
            else self.base_dir
        )

        stdout_fetch, stderr_fetch, returncode_fetch = await self._run_git_command(
            ["fetch", remote_str], cwd=path
        )
        if returncode_fetch == 0:
            stdout_branches, stderr_branches, _ = await self._run_git_command(
                ["branch", "-r"], cwd=path
            )
            return f"Fetched from {remote_str} for {path}.\nRemote branches:\n{stdout_branches}"
        else:
            return f"Error fetching from {remote_str} for {path}:\n{stderr_fetch}"

    async def create_pull_request(self, jarvis_instance, pr_args_str):
        """Creates a GitHub Pull Request. <owner>/<repo> <base_branch> <head_branch> [title (in quotes if spaces)] [body (in quotes if spaces)]"""
        parts = pr_args_str.split(maxsplit=4)  # Split up to 5 parts for title and body

        if len(parts) < 3:
            return 'Usage: git_create_pr <owner>/<repo> <base_branch> <head_branch> ["title"] ["body"]'

        repo_full_name = parts[0]
        base = parts[1]
        head = parts[2]
        title = parts[3] if len(parts) > 3 else f"Merge {head} into {base}"
        body_input = parts[4] if len(parts) > 4 else ""

        # Remove surrounding quotes from title and body if present
        title = title.strip('"').strip("'")
        body_input = body_input.strip('"').strip("'")

        final_body = body_input
        if (
            not final_body
        ):  # If body wasn't provided or was empty string after stripping
            user_body = await jarvis_instance.ask_user(
                f"Pull request body (for {head} -> {base}, leave empty for default):"
            )
            final_body = (
                user_body or f"Automated PR: Request to merge {head} into {base}."
            )

        github_token = jarvis_instance.memory.get("github_token")
        if not github_token:
            return "Error: GitHub token not found in memory. Please use 'learn github_token <your_token>'."

        try:
            owner, repo_name = repo_full_name.split("/")
        except ValueError:
            return "Error: Repository name must be in 'owner/repo' format."

        session = await self._get_session()
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        payload = {"title": title, "body": final_body, "base": base, "head": head}

        try:
            async with session.post(api_url, headers=headers, json=payload) as response:
                response_data = await response.json()
                if response.status == 201:  # Created
                    return f"Pull request created successfully: {response_data.get('html_url')}"
                else:
                    return f"Error creating pull request ({response.status}): {response_data.get('message', response_data)}"
        except aiohttp.ClientError as e:
            return f"GitHub API request failed: {e}"
        except Exception as e:
            return f"An unexpected error occurred during PR creation: {e}"

    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            print("GitManager aiohttp session closed.")


# --- Command Wrappers for Jarvis ---
# These functions adapt GitManager methods to Jarvis's command signature (jarvis_instance, args_string)


async def _git_init_cmd(jarvis_instance, args_string):
    """Initializes a Git repo. Usage: git_init [repo_subdir]"""
    return await jarvis_instance.git_manager_instance.init(
        jarvis_instance, args_string if args_string else None
    )


async def _git_clone_cmd(jarvis_instance, args_string):
    """Clones a Git repo. Usage: git_clone <repo_url> [local_subdir]"""
    parts = args_string.split(maxsplit=1)
    if not parts:
        return "Usage: git_clone <repo_url> [local_subdir]"
    repo_url = parts[0]
    local_path = parts[1] if len(parts) > 1 else None
    return await jarvis_instance.git_manager_instance.clone(
        jarvis_instance, repo_url, local_path
    )


async def _git_status_cmd(jarvis_instance, args_string):
    """Shows Git status. Usage: git_status [repo_subdir]"""
    return await jarvis_instance.git_manager_instance.status(
        jarvis_instance, args_string if args_string else None
    )


async def _git_add_cmd(jarvis_instance, args_string):
    """Adds files to index. Usage: git_add <files_pattern | .> [repo_subdir]"""
    parts = args_string.split(maxsplit=1)
    if not parts:
        files_to_add = "."  # Default to add all
    else:
        files_to_add = parts[0]

    repo_subdir = None
    if (
        len(parts) > 1 and files_to_add != "."
    ):  # If files_to_add is ".", the second part is likely repo_subdir
        repo_subdir = parts[1]
    elif len(parts) > 1 and files_to_add == ".":  # if "git_add . my_repo"
        repo_subdir = parts[1]
    elif (
        len(parts) == 1 and files_to_add != "."
    ):  # if "git_add myfile" (files_to_add is "myfile", no repo_subdir)
        pass  # files_to_add is set, repo_subdir is None
    elif len(parts) == 0:  # "git_add" -> files_to_add = "."
        pass

    # A simpler parsing: assume last part MIGHT be repo_subdir if it looks like a path or is specified after files
    # For now, let's assume if two args, second is repo_subdir. If one, it's files.
    # This needs more robust parsing based on user intent or clearer command structure.
    # A common pattern: git_add [repo_subdir] -- <files>
    # For simplicity here: if args_string has two parts, first is files, second is repo_subdir.
    # If one part, it's files, repo_subdir is default.
    # This is not ideal. Let's make it: git_add <files_pattern> [repo_subdir_if_pattern_is_not_last_arg]
    # Or, require repo_subdir as a separate, identifiable parameter if not default.

    # Let's try this logic for `git_add <files> [repo_path]`
    # If args_string is "file.txt my_repo", files="file.txt", repo_path="my_repo"
    # If args_string is ".", files=".", repo_path=None
    # If args_string is "file.txt", files="file.txt", repo_path=None

    # Simpler: User specifies repo_path explicitly if not cwd.
    # git_add <files_pattern>
    # git_add_in <repo_subdir> <files_pattern> (Alternative command)

    # For now, let's assume args_string is primarily files, and repo_path_str is optional and last.
    # This is still ambiguous. The GitManager methods take repo_path_str as the *directory containing* the .git
    # And 'files' is relative to that.

    # Simplest for now: if args_string contains a known subdir, assume it's that. Otherwise files apply to base_dir.
    # This is too complex for simple parsing. Let's require commands to be explicit if repo_subdir is not base_dir.
    # For now, the command handlers will mostly pass args_string as the first logical arg, and an optional second as repo_path.
    # The GitManager methods themselves join repo_path_str with self.base_dir.

    # Let's assume args_string is files, repo_path_str is passed separately to GitManager methods.
    # The command definition should make this clear.
    # git_add <files_to_add_or_.> (operates on default repo_path or specified via a global setting)
    # OR git_add <repo_subdir> <files_to_add_or_.>

    # The current GitManager methods take repo_path_str as an optional final arg.
    # So, the command wrapper needs to parse its args_string to separate `files` from `repo_path_str`.

    _files = "."
    _repo_path = None
    if args_string:
        split_args = args_string.split()
        # Crude check: if the last part looks like a path and isn't just ".", assume it's repo_path
        # This is heuristic. A dedicated repo_path flag would be better.
        if len(split_args) > 1 and (
            os.path.sep in split_args[-1]
            or os.path.exists(
                os.path.join(
                    jarvis_instance.git_manager_instance.base_dir, split_args[-1]
                )
            )
        ):
            # If more than one argument, and the last one is potentially a path
            if split_args[0] != ".":  # e.g. "file.txt myrepo"
                _files = " ".join(split_args[:-1])
                _repo_path = split_args[-1]
            else:  # e.g. ". myrepo"
                _files = "."
                _repo_path = split_args[-1]
        else:  # e.g. "file.txt" or "file1 file2" or "."
            _files = args_string

    return await jarvis_instance.git_manager_instance.add(
        jarvis_instance, _files, _repo_path
    )


async def _git_commit_cmd(jarvis_instance, args_string):
    """Commits staged changes. Usage: git_commit <"message"> [repo_subdir]"""
    parts = args_string.split('"')  # Try to get message in quotes
    message = ""
    repo_subdir = None

    if len(parts) >= 2 and parts[0] == "":  # Starts with "
        message = parts[1]
        if len(parts) > 2:
            repo_subdir_candidate = parts[2].strip()
            if repo_subdir_candidate:
                repo_subdir = repo_subdir_candidate
    elif (
        args_string
    ):  # No quotes, assume first word is message (not ideal for multi-word)
        first_space = args_string.find(" ")
        if first_space != -1:
            message = args_string[:first_space]
            repo_subdir_candidate = args_string[first_space + 1 :].strip()
            if repo_subdir_candidate:
                repo_subdir = repo_subdir_candidate
        else:
            message = args_string

    if not message:
        return 'Usage: git_commit <"message"> [repo_subdir]'
    return await jarvis_instance.git_manager_instance.commit(
        jarvis_instance, message, repo_subdir
    )


async def _git_branch_cmd(jarvis_instance, args_string):
    """Manages branches. Usage: git_branch | git_branch <new_name> | git_branch -d <name_to_delete> [repo_subdir]"""
    # Assume repo_subdir is the last argument if present and looks like a path
    _branch_ops = args_string
    _repo_subdir = None
    parts = args_string.split()
    if len(parts) > 0 and (
        os.path.sep in parts[-1]
        or os.path.exists(
            os.path.join(jarvis_instance.git_manager_instance.base_dir, parts[-1])
        )
    ):
        # Heuristic: if last part looks like a path, it's repo_subdir
        # This is not robust. A flag like --repo-path would be better.
        # For now, let's be simpler: repo_subdir is NOT parsed from here, user must CD or use a more specific command.
        # Or, the GitManager methods always take repo_path_str as the explicit last arg.
        # The wrapper's args_string is split.
        # Let's assume the GitManager method's repo_path_str handles the optional subdir.
        # The command wrapper passes the relevant parts of args_string.
        # Example: "git_branch my_new_branch my_repo_dir"
        # args_string = "my_new_branch my_repo_dir"
        # How to distinguish "my_new_branch" from "my_repo_dir"?

        # Simplification: repo_subdir is the *last* optional argument.
        # The primary git arguments (like branch name) come first.

        split_args = args_string.split()
        if len(split_args) > 0:
            # Check if the last arg is a potential path and not part of branch op (like -d)
            if (
                os.path.sep in split_args[-1]
                or os.path.exists(
                    os.path.join(
                        jarvis_instance.git_manager_instance.base_dir, split_args[-1]
                    )
                )
            ) and not (
                len(split_args) > 1
                and split_args[-2] == "-d"
                and split_args[-1] != "-d"
            ):  # Avoid taking branch name as path for -d case
                _repo_subdir = split_args[-1]
                _branch_ops = " ".join(split_args[:-1])
            else:
                _branch_ops = args_string  # All of it is branch ops
        else:  # "git_branch" alone
            _branch_ops = ""

    return await jarvis_instance.git_manager_instance.branch(
        jarvis_instance, _branch_ops, _repo_subdir
    )


async def _git_checkout_cmd(jarvis_instance, args_string):
    """Switches branches. Usage: git_checkout <branch_name> [repo_subdir]"""
    parts = args_string.split(maxsplit=1)
    if not parts:
        return "Usage: git_checkout <branch_name> [repo_subdir]"
    branch_name = parts[0]
    repo_subdir = parts[1] if len(parts) > 1 else None
    return await jarvis_instance.git_manager_instance.checkout(
        jarvis_instance, branch_name, repo_subdir
    )


async def _git_push_cmd(jarvis_instance, args_string):
    """Pushes to remote. Usage: git_push [remote branch] [repo_subdir] (e.g. origin main)"""
    parts = args_string.split()
    remote_branch_ops = ""
    repo_subdir = None
    # Try to identify repo_subdir if it's the last argument and looks like a path
    if len(parts) > 0 and (
        os.path.sep in parts[-1]
        or os.path.exists(
            os.path.join(jarvis_instance.git_manager_instance.base_dir, parts[-1])
        )
    ):
        if len(parts) > 1:  # at least one git arg and a path
            repo_subdir = parts[-1]
            remote_branch_ops = " ".join(parts[:-1])
        # else: if only one part and it's a path, it's ambiguous. Assume it's remote_branch_ops.
        # This parsing is getting complex. For now, simpler:
    if len(parts) >= 2 and (
        os.path.sep in parts[-1]
        or os.path.exists(
            os.path.join(jarvis_instance.git_manager_instance.base_dir, parts[-1])
        )
    ):  # "origin main myrepo"
        repo_subdir = parts[-1]
        remote_branch_ops = " ".join(parts[:-1])
    elif len(parts) == 1 and (
        os.path.sep in parts[0]
        or os.path.exists(
            os.path.join(jarvis_instance.git_manager_instance.base_dir, parts[0])
        )
    ):  # "myrepo" (ambiguous)
        # Assume default push, and this is repo_subdir
        repo_subdir = parts[0]
        remote_branch_ops = ""  # Defaults to "origin main" in GitManager method
    else:  # "origin main" or "origin" or ""
        remote_branch_ops = args_string

    return await jarvis_instance.git_manager_instance.push(
        jarvis_instance, remote_branch_ops, repo_subdir
    )


async def _git_pull_cmd(jarvis_instance, args_string):
    """Pulls from remote. Usage: git_pull [remote branch] [repo_subdir] (e.g. origin main)"""
    # Similar parsing to push
    parts = args_string.split()
    remote_branch_ops = ""
    repo_subdir = None
    if len(parts) >= 2 and (
        os.path.sep in parts[-1]
        or os.path.exists(
            os.path.join(jarvis_instance.git_manager_instance.base_dir, parts[-1])
        )
    ):
        repo_subdir = parts[-1]
        remote_branch_ops = " ".join(parts[:-1])
    elif len(parts) == 1 and (
        os.path.sep in parts[0]
        or os.path.exists(
            os.path.join(jarvis_instance.git_manager_instance.base_dir, parts[0])
        )
    ):
        repo_subdir = parts[0]
        remote_branch_ops = ""
    else:
        remote_branch_ops = args_string

    return await jarvis_instance.git_manager_instance.pull(
        jarvis_instance, remote_branch_ops, repo_subdir
    )


async def _git_interactive_commit_cmd(jarvis_instance, args_string):
    """Interactive commit. Usage: git_interactive_commit [repo_subdir]"""
    repo_subdir = args_string if args_string else None
    return await jarvis_instance.git_manager_instance.interactive_commit(
        jarvis_instance, repo_subdir
    )


async def _git_log_cmd(jarvis_instance, args_string):
    """Views commit log. Usage: git_log [limit] [repo_subdir]"""
    parts = args_string.split(maxsplit=1)
    limit = "5"  # Default limit
    repo_subdir = None
    if len(parts) == 1:
        try:
            int(parts[0])  # Is it a number (limit)?
            limit = parts[0]
        except ValueError:  # Not a number, so it's repo_subdir
            repo_subdir = parts[0]
    elif len(parts) == 2:
        limit = parts[0]
        repo_subdir = parts[1]
    return await jarvis_instance.git_manager_instance.view_log(
        jarvis_instance, limit, repo_subdir
    )


async def _git_fetch_cmd(jarvis_instance, args_string):
    """Fetches from remote. Usage: git_fetch [remote_name] [repo_subdir]"""
    parts = args_string.split(maxsplit=1)
    remote = "origin"  # Default remote
    repo_subdir = None
    if len(parts) == 1:
        if not (
            os.path.sep in parts[0]
            or os.path.exists(
                os.path.join(jarvis_instance.git_manager_instance.base_dir, parts[0])
            )
        ):
            remote = parts[0]  # If it's not a path, assume it's remote name
        else:
            repo_subdir = parts[0]  # Assume it's a path
    elif len(parts) == 2:
        remote = parts[0]
        repo_subdir = parts[1]
    return await jarvis_instance.git_manager_instance.fetch_remote_branches(
        jarvis_instance, remote, repo_subdir
    )


async def _git_create_pr_cmd(jarvis_instance, args_string):
    """Creates GitHub PR. Usage: git_create_pr <owner>/<repo> <base> <head> [\"title\"] [\"body\"]"""
    # The GitManager method already handles parsing this args_string
    return await jarvis_instance.git_manager_instance.create_pull_request(
        jarvis_instance, args_string
    )


commands = {
    "git_init": _git_init_cmd,
    "git_clone": _git_clone_cmd,
    "git_status": _git_status_cmd,
    "git_add": _git_add_cmd,
    "git_commit": _git_commit_cmd,
    "git_branch": _git_branch_cmd,
    "git_checkout": _git_checkout_cmd,
    "git_push": _git_push_cmd,
    "git_pull": _git_pull_cmd,
    "git_interactive_commit": _git_interactive_commit_cmd,
    "git_log": _git_log_cmd,
    "git_fetch": _git_fetch_cmd,
    "git_create_pr": _git_create_pr_cmd,
}


# Module lifecycle functions
async def load_module(jarvis_instance):
    """Loads the GitManager module."""
    print("Loading Git manager module...")
    if (
        not hasattr(jarvis_instance, "git_manager_instance")
        or jarvis_instance.git_manager_instance is None
    ):
        # base_dir can be configured via Jarvis memory, e.g. jarvis.memory.get("git_default_base_dir")
        jarvis_instance.git_manager_instance = GitManager(
            base_dir=jarvis_instance.memory.get("git_base_dir")
        )

    print(
        f"Git manager module loaded. Base directory: {jarvis_instance.git_manager_instance.base_dir}. Available commands: "
        + ", ".join(commands.keys())
    )


async def close_module(jarvis_instance):
    """Closes resources used by the GitManager module."""
    if (
        hasattr(jarvis_instance, "git_manager_instance")
        and jarvis_instance.git_manager_instance
    ):
        await jarvis_instance.git_manager_instance.close_session()
    print("Git manager module resources closed.")


# ------------------------------------------------------
# CommandDispatcher integration helpers
# ------------------------------------------------------


async def commit(message: str, repo: str | None = None) -> str:
    """Commit staged changes with a message."""
    gm = GitManager()
    return await gm.commit(None, message, repo)


async def push(
    remote: str = "origin", branch: str = "main", repo: str | None = None
) -> str:
    """Push commits to the given remote and branch."""
    gm = GitManager()
    remote_branch = f"{remote} {branch}".strip()
    return await gm.push(None, remote_branch, repo)


from command_dispatcher import CommandDispatcher, default_dispatcher


def register_commands(dispatcher: CommandDispatcher = default_dispatcher) -> None:
    """Register ``git`` commands with ``dispatcher``."""

    dispatcher.register_command_handler("git", "commit", commit)
    dispatcher.register_command_handler("git", "push", push)


register_commands(default_dispatcher)
__all__ = ["GitManager", "commit", "push", "register_commands"]
