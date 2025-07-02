import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

import aiohttp

logger = logging.getLogger(__name__)

@dataclass
class GitOperationResult:
    success: bool
    output: str
    command: str
    execution_time: float
    error: Optional[str] = None

@dataclass
class CommitInfo:
    hash: str
    author: str
    message: str
    date: str
    changes: Optional[List[str]] = None

class GitManager:
    def __init__(self, base_dir: Optional[Union[str, Path]] = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.session: Optional[aiohttp.ClientSession] = None
        self.operation_history: List[GitOperationResult] = []
        self._validate_git_installation()

    def _validate_git_installation(self) -> None:
        """Check if git is installed and available"""
        try:
            import shutil
            if not shutil.which("git"):
                raise RuntimeError("Git is not installed or not in PATH")
        except ImportError:
            logger.warning("Could not verify git installation")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def run_git_command(
        self,
        args: List[str],
        cwd: Optional[Union[str, Path]] = None,
        timeout: int = 30
    ) -> GitOperationResult:
        """
        Execute git command with enhanced tracking and error handling
        
        Args:
            args: List of git command arguments
            cwd: Working directory (defaults to base_dir)
            timeout: Command timeout in seconds
            
        Returns:
            GitOperationResult with command results
        """
        start_time = asyncio.get_event_loop().time()
        cwd_path = Path(cwd) if cwd else self.base_dir
        
        if not cwd_path.exists():
            error_msg = f"Directory {cwd_path} does not exist"
            logger.error(error_msg)
            return GitOperationResult(
                success=False,
                output=error_msg,
                command=f"git {' '.join(args)}",
                execution_time=0,
                error=error_msg
            )

        try:
            proc = await asyncio.create_subprocess_exec(
                'git', *args,
                cwd=str(cwd_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                error_msg = f"Command timed out after {timeout} seconds"
                logger.warning(error_msg)
                raise

            output = stdout.decode().strip() if stdout else stderr.decode().strip()
            execution_time = asyncio.get_event_loop().time() - start_time
            
            result = GitOperationResult(
                success=proc.returncode == 0,
                output=output,
                command=f"git {' '.join(args)}",
                execution_time=execution_time,
                error=None if proc.returncode == 0 else output
            )
            
            self.operation_history.append(result)
            logger.debug(f"Git command executed: {args}, success: {result.success}")
            return result
            
        except Exception as e:
            error_msg = f"Git command failed: {str(e)}"
            logger.exception(error_msg)
            result = GitOperationResult(
                success=False,
                output=error_msg,
                command=f"git {' '.join(args)}",
                execution_time=asyncio.get_event_loop().time() - start_time,
                error=str(e)
            )
            self.operation_history.append(result)
            return result

    async def get_repo_status(self) -> Dict[str, Union[str, int, List[str]]]:
        """
        Get detailed repository status including:
        - Current branch
        - Number of changes
        - List of changed files
        - Remote tracking info
        """
        branch_result = await self.run_git_command(["branch", "--show-current"])
        status_result = await self.run_git_command(["status", "--porcelain", "--branch"])
        remote_result = await self.run_git_command(["remote", "-v"])
        
        changed_files = []
        if status_result.success:
            changed_files = [
                line.split(maxsplit=1)[1]
                for line in status_result.output.splitlines()
                if len(line.split(maxsplit=1)) > 1
            ]
        
        return {
            'branch': branch_result.output if branch_result.success else "unknown",
            'changes_count': len(changed_files),
            'changed_files': changed_files,
            'remotes': remote_result.output if remote_result.success else "unknown",
            'clean': len(changed_files) == 0
        }

    async def create_branch(self, name: str, checkout: bool = True) -> GitOperationResult:
        """
        Create new branch
        
        Args:
            name: Branch name
            checkout: Whether to checkout the new branch immediately
            
        Returns:
            GitOperationResult with creation status
        """
        if not name or not name.isprintable():
            raise ValueError("Invalid branch name")
            
        if checkout:
            return await self.run_git_command(["checkout", "-b", name])
        return await self.run_git_command(["branch", name])

    async def get_commit_history(
        self,
        limit: int = 5,
        include_changes: bool = False
    ) -> List[CommitInfo]:
        """
        Get commit history with optional file changes
        
        Args:
            limit: Number of commits to return
            include_changes: Whether to include changed files
            
        Returns:
            List of CommitInfo objects
        """
        format_str = "%H|%an|%ad|%s"  # hash|author|date|subject
        if include_changes:
            result = await self.run_git_command([
                "log",
                f"-{limit}",
                "--pretty=format:" + format_str,
                "--name-only"
            ])
        else:
            result = await self.run_git_command([
                "log",
                f"-{limit}",
                "--pretty=format:" + format_str
            ])
            
        if not result.success:
            return []
            
        commits = []
        current_commit = None
        
        for line in result.output.splitlines():
            if "|" in line:  # This is a commit info line
                if current_commit:
                    commits.append(current_commit)
                    
                hash_, author, date, message = line.split("|", 3)
                current_commit = CommitInfo(
                    hash=hash_,
                    author=author,
                    message=message,
                    date=date,
                    changes=[]
                )
            elif include_changes and line.strip() and current_commit:
                current_commit.changes.append(line.strip())
                
        if current_commit:
            commits.append(current_commit)
            
        return commits

    async def cleanup_branches(
        self,
        main_branch: str = "main",
        dry_run: bool = True
    ) -> Dict[str, Union[int, List[str]]]:
        """
        Cleanup merged branches
        
        Args:
            main_branch: The branch to compare against
            dry_run: Only show what would be deleted
            
        Returns:
            Dictionary with cleanup results
        """
        # First update remote tracking info
        await self.run_git_command(["fetch", "--prune"])
        
        # Get merged branches
        result = await self.run_git_command([
            "branch",
            "--merged",
            main_branch,
            "-r" if main_branch == "origin/" + main_branch else ""
        ])
        
        if not result.success:
            return {"deleted": [], "error": result.output}
            
        branches = [
            b.strip()
            for b in result.output.splitlines()
            if b.strip() and not b.strip().endswith(main_branch)
        ]
        
        deleted = []
        for branch in branches:
            if branch.startswith("origin/"):
                if not dry_run:
                    delete_result = await self.run_git_command(["push", "origin", "--delete", branch[7:]])
                    if delete_result.success:
                        deleted.append(branch)
            else:
                if not dry_run:
                    delete_result = await self.run_git_command(["branch", "-d", branch])
                    if delete_result.success:
                        deleted.append(branch)
        
        return {
            "deleted": deleted,
            "dry_run": dry_run,
            "total_deleted": len(deleted),
            "remaining": len(branches) - len(deleted)
        }

    async def create_pull_request(
        self,
        title: str,
        body: str = "",
        target_branch: str = "main",
        draft: bool = False
    ) -> GitOperationResult:
        """
        Create a pull request using GitHub API
        
        Args:
            title: PR title
            body: PR description
            target_branch: Branch to merge into
            draft: Create as draft PR
            
        Returns:
            GitOperationResult with PR creation status
        """
        # Implementation would use GitHub API
        pass

    async def close(self) -> None:
        """Cleanup resources"""
        if self.session and not self.session.closed:
            await self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        asyncio.get_event_loop().run_until_complete(self.close())

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()