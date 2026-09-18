"""
Exceptions for DevForge GitHub Integration and Git Operations.
Provides fine-grained, credential-safe error types for failure detection and user reporting.
"""

class GitHubIntegrationError(Exception):
    """Base exception for all GitHub and repository integration errors."""
    def __init__(self, message: str, status_code: int = 500, safe_detail: str = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.safe_detail = safe_detail or message


class GitHubConfigurationError(GitHubIntegrationError):
    """Raised when GitHub token or owner is not configured or malformed."""
    def __init__(self, message: str = "GitHub integration is not configured. GITHUB_TOKEN or GITHUB_OWNER is missing."):
        super().__init__(message, status_code=400)


class GitHubAuthenticationError(GitHubIntegrationError):
    """Raised when GitHub authentication fails (e.g. 401 Bad credentials / expired token)."""
    def __init__(self, message: str = "GitHub authentication failed. Please verify the configured GITHUB_TOKEN."):
        super().__init__(message, status_code=401)


class GitHubPermissionError(GitHubIntegrationError):
    """Raised when the configured token lacks required repository creation/push scopes (e.g. 403 Forbidden)."""
    def __init__(self, message: str = "GitHub permission denied. Ensure GITHUB_TOKEN has 'repo' scope."):
        super().__init__(message, status_code=403)


class GitHubRepositoryConflictError(GitHubIntegrationError):
    """Raised when a repository with the target name already exists under the GitHub owner."""
    def __init__(self, repo_name: str, owner: str):
        message = f"Repository '{owner}/{repo_name}' already exists on GitHub."
        super().__init__(message, status_code=409, safe_detail=message)
        self.repo_name = repo_name
        self.owner = owner


class GitHubRateLimitError(GitHubIntegrationError):
    """Raised when GitHub REST API rate limit is exceeded (e.g. 403 or 429)."""
    def __init__(self, message: str = "GitHub API rate limit exceeded. Please wait before retrying."):
        super().__init__(message, status_code=429)


class GitHubAPIUnavailableError(GitHubIntegrationError):
    """Raised when GitHub API is unreachable, timed out, or returning 5xx server errors."""
    def __init__(self, message: str = "GitHub API is currently unreachable or timed out."):
        super().__init__(message, status_code=503)


class GitOperationError(GitHubIntegrationError):
    """Raised when local Git CLI commands (git init, add, commit, push) fail."""
    def __init__(self, command: str, returncode: int, stderr: str):
        # Scrub any token that might inadvertently appear in command output
        clean_stderr = stderr.replace("\n", " ").strip()
        message = f"Git command '{command}' failed with exit code {returncode}: {clean_stderr}"
        super().__init__(message, status_code=500, safe_detail=f"Git operation '{command}' failed.")
        self.command = command
        self.returncode = returncode
        self.stderr = clean_stderr
