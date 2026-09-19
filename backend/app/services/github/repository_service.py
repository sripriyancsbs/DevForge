import os
import re
import shutil
import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.github.exceptions import (
    GitHubIntegrationError,
    GitHubConfigurationError,
    GitHubRepositoryConflictError,
    GitOperationError
)
from app.services.github.github_client import GitHubClient, github_client, scrub_credentials

logger = logging.getLogger("devforge.services.repository")


class BaseRepositoryProvider(ABC):
    """Abstract base class for source code repository providers (GitHub, GitLab, Bitbucket)."""

    @abstractmethod
    def check_connection(self) -> Dict[str, Any]:
        """Verify provider authentication and connectivity."""
        pass

    @abstractmethod
    def get_repository(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """Fetch remote repository metadata if it exists."""
        pass

    @abstractmethod
    def create_repository(self, repo_name: str, description: Optional[str] = None, private: bool = True) -> Dict[str, Any]:
        """Create a new remote repository."""
        pass


class GitHubProvider(BaseRepositoryProvider):
    """GitHub implementation of BaseRepositoryProvider."""

    def __init__(self, client: Optional[GitHubClient] = None):
        self.client = client or github_client

    def check_connection(self) -> Dict[str, Any]:
        return self.client.check_connection()

    def get_repository(self, repo_name: str) -> Optional[Dict[str, Any]]:
        return self.client.get_repository(repo_name)

    def create_repository(self, repo_name: str, description: Optional[str] = None, private: bool = True) -> Dict[str, Any]:
        return self.client.create_repository(repo_name, description=description, private=private)


class RepositoryService:
    """
    High-level service managing repository creation and local Git lifecycle.
    Keeps all provider-specific API calls and CLI git operations decoupled from workers.
    """

    def __init__(self, provider: Optional[BaseRepositoryProvider] = None):
        self.provider = provider or GitHubProvider()

    def get_connection_status(self) -> Dict[str, Any]:
        """Check provider connection status."""
        return self.provider.check_connection()

    def ensure_repository(self, repo_name: str, description: Optional[str] = None, allow_existing: bool = False) -> Dict[str, Any]:
        """
        Create the application repository.
        If allow_existing is True (e.g. during retry of a crashed job), reuses existing repository.
        Otherwise raises GitHubRepositoryConflictError if repository already exists.
        """
        existing = self.provider.get_repository(repo_name)
        if existing:
            if allow_existing:
                logger.info(f"Reusing existing repository '{repo_name}' for idempotent retry.")
                return existing
            raise GitHubRepositoryConflictError(repo_name, getattr(self.provider, "client", {}).owner if hasattr(self.provider, "client") else "sripriyancsbs")

        return self.provider.create_repository(repo_name, description=description, private=True)

    def _run_git(self, cmd: list, cwd: Path, token: Optional[str] = None) -> str:
        """Run a git command safely in cwd, scrubbing credentials from any error output."""
        try:
            res = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=45.0,
                check=False
            )
            if res.returncode != 0:
                clean_err = scrub_credentials(res.stderr or res.stdout, token)
                clean_cmd = scrub_credentials(" ".join(cmd), token)
                logger.error(f"Git command failed: {clean_cmd} -> {clean_err}")
                raise GitOperationError(command=clean_cmd, returncode=res.returncode, stderr=clean_err)
            return res.stdout.strip()
        except FileNotFoundError:
            raise GitOperationError(command=cmd[0], returncode=127, stderr="git executable not found on system PATH")
        except subprocess.TimeoutExpired:
            raise GitOperationError(command=cmd[0], returncode=124, stderr="git operation timed out after 45 seconds")

    def initialize_and_push_project(
        self,
        project_dir: Path,
        repo_html_url: str,
        default_branch: str = "main",
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Initialize local Git repository, create initial commit, and push to remote.
        Guarantees that credentials are never written to .git/config on disk.
        """
        if not project_dir.exists() or not project_dir.is_dir():
            raise FileNotFoundError(f"Project directory does not exist: {project_dir}")

        effective_token = (token if token is not None else settings.GITHUB_TOKEN or "").strip()
        if not effective_token:
            raise GitHubConfigurationError("GITHUB_TOKEN is not configured for pushing repository.")

        # 1. Check if git is available
        if not shutil.which("git"):
            raise GitOperationError("git", 127, "git binary is not installed or not in PATH")

        # 2. git init (idempotent)
        git_dir = project_dir / ".git"
        if not git_dir.exists():
            self._run_git(["git", "init", "-b", default_branch], project_dir)
        else:
            # Ensure correct branch name
            self._run_git(["git", "checkout", "-B", default_branch], project_dir)

        # 3. Configure local repository committer identity (avoids global config requirement)
        self._run_git(["git", "config", "user.name", "DevForge IDP"], project_dir)
        self._run_git(["git", "config", "user.email", "idp@devforge.local"], project_dir)

        # 4. git add .
        self._run_git(["git", "add", "."], project_dir)

        # 5. git commit (if changes exist)
        status_output = self._run_git(["git", "status", "--porcelain"], project_dir)
        if status_output:
            self._run_git(["git", "commit", "-m", "Initial application scaffold provisioned by DevForge"], project_dir)

        # 6. Configure remote 'origin' to clean, unauthenticated URL
        # Ensures .git/config on disk NEVER contains credentials
        clean_remote_url = repo_html_url.rstrip("/") + ".git"
        remotes = self._run_git(["git", "remote"], project_dir)
        if "origin" in remotes.split():
            self._run_git(["git", "remote", "set-url", "origin", clean_remote_url], project_dir)
        else:
            self._run_git(["git", "remote", "add", "origin", clean_remote_url], project_dir)

        # 7. Authenticated Push
        # Construct authenticated push target purely for the push command argument
        # Format: https://x-access-token:<TOKEN>@github.com/<owner>/<repo>.git
        # Remote config on disk remains clean.
        auth_push_target = clean_remote_url.replace("https://", f"https://x-access-token:{effective_token}@")

        logger.info(f"Pushing project files from {project_dir} to {clean_remote_url} ({default_branch})...")
        # Do NOT pass '-u' to git push with auth_push_target, because git will save
        # auth_push_target (containing the secret token) into .git/config as the upstream branch URL.
        self._run_git(
            ["git", "push", auth_push_target, f"HEAD:{default_branch}"],
            project_dir,
            token=effective_token
        )

        # Explicitly configure branch upstream tracking to clean remote 'origin'
        self._run_git(
            ["git", "config", f"branch.{default_branch}.remote", "origin"],
            project_dir
        )
        self._run_git(
            ["git", "config", f"branch.{default_branch}.merge", f"refs/heads/{default_branch}"],
            project_dir
        )

        commit_hash = self._run_git(["git", "rev-parse", "--short", "HEAD"], project_dir)
        logger.info(f"Successfully pushed application to {clean_remote_url} (commit {commit_hash})")

        return {
            "pushed": True,
            "branch": default_branch,
            "commit_hash": commit_hash,
            "remote_url": clean_remote_url
        }


repository_service = RepositoryService()
