import re
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.services.github.exceptions import (
    GitHubIntegrationError,
    GitHubConfigurationError,
    GitHubAuthenticationError,
    GitHubPermissionError,
    GitHubRepositoryConflictError,
    GitHubRateLimitError,
    GitHubAPIUnavailableError
)

logger = logging.getLogger("devforge.github.client")

def scrub_credentials(text: str, token: Optional[str] = None) -> str:
    """Scrub sensitive tokens from any message or log output."""
    if not text:
        return ""
    scrubbed = text
    if token and token.strip():
        scrubbed = scrubbed.replace(token.strip(), "[REDACTED_TOKEN]")
    # Redact common PAT prefixes like ghp_, github_pat_
    scrubbed = re.sub(r'gh[pousr]_[A-Za-z0-9_]{10,}', '[REDACTED_TOKEN]', scrubbed)
    scrubbed = re.sub(r'github_pat_[A-Za-z0-9_]{20,}', '[REDACTED_TOKEN]', scrubbed)
    scrubbed = re.sub(r'(x-access-token:)[^@]+(@)', r'\1[REDACTED_TOKEN]\2', scrubbed)
    return scrubbed


class GitHubClient:
    """
    Low-level HTTP client for interacting with the GitHub REST API.
    Guarantees that credentials are never stored in exceptions or logs.
    """
    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None, owner: Optional[str] = None):
        self._token = (token if token is not None else settings.GITHUB_TOKEN or "").strip()
        self.owner = (owner if owner is not None else settings.GITHUB_OWNER or "sripriyancsbs").strip()

    @property
    def has_token(self) -> bool:
        return bool(self._token)

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "DevForge-IDP/0.1.0"
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def check_connection(self) -> Dict[str, Any]:
        """
        Verify GitHub API connectivity and token status.
        Returns a sanitized status dict (never exposing credentials).
        """
        if not self._token:
            return {
                "connected": False,
                "owner": self.owner,
                "error": "GITHUB_TOKEN is not configured in platform environment."
            }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(f"{self.BASE_URL}/user", headers=self._headers())

                if res.status_code == 200:
                    data = res.json()
                    return {
                        "connected": True,
                        "owner": self.owner,
                        "authenticated_user": data.get("login"),
                        "error": None
                    }
                elif res.status_code == 401:
                    return {
                        "connected": False,
                        "owner": self.owner,
                        "error": "GitHub authentication failed: Bad credentials or expired token."
                    }
                elif res.status_code == 403:
                    if "rate limit" in res.text.lower():
                        return {
                            "connected": False,
                            "owner": self.owner,
                            "error": "GitHub API rate limit exceeded."
                        }
                    return {
                        "connected": False,
                        "owner": self.owner,
                        "error": "GitHub permission denied: Token lacks required scopes."
                    }
                else:
                    return {
                        "connected": False,
                        "owner": self.owner,
                        "error": f"GitHub API returned HTTP {res.status_code}."
                    }
        except (httpx.ConnectTimeout, httpx.ReadTimeout):
            return {
                "connected": False,
                "owner": self.owner,
                "error": "GitHub API connection timed out."
            }
        except httpx.RequestError as exc:
            return {
                "connected": False,
                "owner": self.owner,
                "error": f"GitHub API network error: {scrub_credentials(str(exc), self._token)}"
            }

    def get_repository(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """
        Fetch repository metadata if it exists. Returns None if 404 Not Found.
        """
        if not self._token:
            raise GitHubConfigurationError("GITHUB_TOKEN is not configured.")

        url = f"{self.BASE_URL}/repos/{self.owner}/{repo_name}"
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.get(url, headers=self._headers())
                if res.status_code == 200:
                    data = res.json()
                    return {
                        "name": data.get("name"),
                        "full_name": data.get("full_name"),
                        "owner": self.owner,
                        "html_url": data.get("html_url"),
                        "clone_url": data.get("clone_url"),
                        "default_branch": data.get("default_branch", "main"),
                        "private": data.get("private", True)
                    }
                elif res.status_code == 404:
                    return None
                elif res.status_code == 401:
                    raise GitHubAuthenticationError()
                elif res.status_code == 403:
                    if "rate limit" in res.text.lower():
                        raise GitHubRateLimitError()
                    raise GitHubPermissionError()
                else:
                    raise GitHubAPIUnavailableError(f"GitHub API returned HTTP {res.status_code}.")
        except (httpx.ConnectTimeout, httpx.ReadTimeout):
            raise GitHubAPIUnavailableError("GitHub API request timed out.")
        except httpx.RequestError as exc:
            raise GitHubAPIUnavailableError(f"GitHub API network error: {scrub_credentials(str(exc), self._token)}")

    def create_repository(self, name: str, description: Optional[str] = None, private: bool = True) -> Dict[str, Any]:
        """
        Create a new GitHub repository under self.owner with auto_init=False.
        Detects conflicts cleanly without destructive actions.
        """
        if not self._token:
            raise GitHubConfigurationError("GITHUB_TOKEN is not configured in platform environment.")

        # Check if repository already exists (conflict detection & idempotency)
        existing = self.get_repository(name)
        if existing:
            raise GitHubRepositoryConflictError(name, self.owner)

        payload = {
            "name": name,
            "description": description or f"DevForge application: {name}",
            "private": private,
            "auto_init": False,
            "has_issues": True,
            "has_projects": False,
            "has_wiki": False
        }

        # Try user repos endpoint first, fallback to org repos endpoint if needed
        create_url = f"{self.BASE_URL}/user/repos"

        try:
            with httpx.Client(timeout=20.0) as client:
                res = client.post(create_url, headers=self._headers(), json=payload)

                # If 404 or 422 with organization indication, try org repos
                if res.status_code in (404, 422) and self.owner:
                    org_res = client.post(f"{self.BASE_URL}/orgs/{self.owner}/repos", headers=self._headers(), json=payload)
                    if org_res.status_code == 201:
                        res = org_res

                if res.status_code == 201:
                    data = res.json()
                    logger.info(f"Successfully created GitHub repository: {data.get('full_name')}")
                    return {
                        "name": data.get("name"),
                        "full_name": data.get("full_name"),
                        "owner": data.get("owner", {}).get("login", self.owner),
                        "html_url": data.get("html_url"),
                        "clone_url": data.get("clone_url"),
                        "default_branch": data.get("default_branch", "main"),
                        "private": data.get("private", True)
                    }
                elif res.status_code == 422:
                    raise GitHubRepositoryConflictError(name, self.owner)
                elif res.status_code == 401:
                    raise GitHubAuthenticationError()
                elif res.status_code == 403:
                    if "rate limit" in res.text.lower():
                        raise GitHubRateLimitError()
                    raise GitHubPermissionError()
                else:
                    err_msg = scrub_credentials(res.text, self._token)
                    raise GitHubAPIUnavailableError(f"GitHub repository creation failed (HTTP {res.status_code}): {err_msg}")
        except (httpx.ConnectTimeout, httpx.ReadTimeout):
            raise GitHubAPIUnavailableError("GitHub API repository creation timed out.")
        except httpx.RequestError as exc:
            raise GitHubAPIUnavailableError(f"GitHub API network error: {scrub_credentials(str(exc), self._token)}")

    def get_workflow_runs(self, repo_name: str, branch: str = "main") -> List[Dict[str, Any]]:
        """
        Fetch recent GitHub Actions workflow runs for a repository.
        """
        if not self._token:
            raise GitHubConfigurationError("GITHUB_TOKEN is not configured.")

        url = f"{self.BASE_URL}/repos/{self.owner}/{repo_name}/actions/runs"
        params = {"branch": branch, "per_page": 5}
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.get(url, headers=self._headers(), params=params)
                if res.status_code == 200:
                    data = res.json()
                    runs = data.get("workflow_runs", [])
                    cleaned_runs = []
                    for r in runs:
                        cleaned_runs.append({
                            "id": r.get("id"),
                            "name": r.get("name", "CI"),
                            "status": r.get("status"),          # queued, in_progress, completed
                            "conclusion": r.get("conclusion"),  # success, failure, cancelled, timed_out
                            "html_url": r.get("html_url"),
                            "head_branch": r.get("head_branch"),
                            "head_sha": r.get("head_sha"),
                            "created_at": r.get("created_at"),
                            "updated_at": r.get("updated_at")
                        })
                    return cleaned_runs
                elif res.status_code == 404:
                    return []
                elif res.status_code == 401:
                    raise GitHubAuthenticationError()
                elif res.status_code == 403:
                    if "rate limit" in res.text.lower():
                        raise GitHubRateLimitError()
                    raise GitHubPermissionError()
                else:
                    raise GitHubAPIUnavailableError(f"GitHub Actions API returned HTTP {res.status_code}.")
        except (httpx.ConnectTimeout, httpx.ReadTimeout):
            raise GitHubAPIUnavailableError("GitHub Actions API request timed out.")
        except httpx.RequestError as exc:
            raise GitHubAPIUnavailableError(f"GitHub Actions network error: {scrub_credentials(str(exc), self._token)}")

    def get_workflow_run_jobs(self, repo_name: str, run_id: int) -> List[Dict[str, Any]]:
        """
        Fetch jobs and steps for a specific workflow run.
        """
        if not self._token:
            raise GitHubConfigurationError("GITHUB_TOKEN is not configured.")

        url = f"{self.BASE_URL}/repos/{self.owner}/{repo_name}/actions/runs/{run_id}/jobs"
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.get(url, headers=self._headers())
                if res.status_code == 200:
                    data = res.json()
                    jobs = data.get("jobs", [])
                    cleaned_jobs = []
                    for j in jobs:
                        cleaned_jobs.append({
                            "id": j.get("id"),
                            "name": j.get("name"),
                            "status": j.get("status"),
                            "conclusion": j.get("conclusion"),
                            "steps": [
                                {
                                    "name": s.get("name"),
                                    "status": s.get("status"),
                                    "conclusion": s.get("conclusion")
                                }
                                for s in j.get("steps", [])
                            ]
                        })
                    return cleaned_jobs
                elif res.status_code == 404:
                    return []
                else:
                    return []
        except Exception as exc:
            logger.warning(f"Failed to fetch workflow run jobs: {exc}")
            return []

    def get_workflow_job_logs(self, repo_name: str, job_id: int) -> str:
        """
        Fetch logs text for a specific workflow job.
        """
        if not self._token:
            return ""

        url = f"{self.BASE_URL}/repos/{self.owner}/{repo_name}/actions/jobs/{job_id}/logs"
        try:
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                res = client.get(url, headers=self._headers())
                if res.status_code == 200:
                    return res.text
                return ""
        except Exception as exc:
            logger.warning(f"Failed to fetch workflow job logs: {exc}")
            return ""

    def get_package_version(self, package_name: str, version_tag: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Safely check if a package version exists in GHCR via GitHub Packages API.
        Returns None if not accessible or 404/403.
        """
        if not self._token:
            return None

        # Clean package name to lowercase
        pkg = (package_name or "").lower().strip()
        url = f"{self.BASE_URL}/users/{self.owner}/packages/container/{pkg}/versions"
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, headers=self._headers())
                if res.status_code == 200:
                    versions = res.json()
                    if not versions:
                        return None
                    if version_tag:
                        for v in versions:
                            tags = v.get("metadata", {}).get("container", {}).get("tags", [])
                            if version_tag in tags:
                                return {
                                    "id": v.get("id"),
                                    "name": v.get("name"), # digest
                                    "tags": tags,
                                    "updated_at": v.get("updated_at")
                                }
                    # Return latest version
                    latest = versions[0]
                    return {
                        "id": latest.get("id"),
                        "name": latest.get("name"),
                        "tags": latest.get("metadata", {}).get("container", {}).get("tags", []),
                        "updated_at": latest.get("updated_at")
                    }
                return None
        except Exception:
            return None


github_client = GitHubClient()
