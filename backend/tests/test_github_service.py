import os
import shutil
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import httpx
import pytest

from app.core.config import settings
from app.services.github.exceptions import (
    GitHubIntegrationError,
    GitHubConfigurationError,
    GitHubAuthenticationError,
    GitHubPermissionError,
    GitHubRepositoryConflictError,
    GitHubRateLimitError,
    GitHubAPIUnavailableError,
    GitOperationError
)
from app.services.github.github_client import GitHubClient, scrub_credentials
from app.services.github.repository_service import RepositoryService, GitHubProvider


# ==============================================================================
# 1. CREDENTIAL SCRUBBING & SECURITY TESTS
# ==============================================================================

def test_scrub_credentials():
    secret_token = "ghp_VerySecretToken1234567890abcdefABCDEF"
    raw_message = f"Failed to push to https://x-access-token:{secret_token}@github.com/owner/repo.git"
    
    scrubbed = scrub_credentials(raw_message, secret_token)
    assert secret_token not in scrubbed
    assert "[REDACTED_TOKEN]" in scrubbed
    assert "https://x-access-token:[REDACTED_TOKEN]@github.com" in scrubbed


def test_scrub_generic_tokens():
    raw = "Error ghp_123456789012345678901234567890123456 and github_pat_11AAAAAAA0123456789_abcdef"
    scrubbed = scrub_credentials(raw)
    assert "ghp_" not in scrubbed
    assert "github_pat_" not in scrubbed
    assert "[REDACTED_TOKEN]" in scrubbed


# ==============================================================================
# 2. GITHUB CLIENT & AUTHENTICATION TESTS
# ==============================================================================

def test_github_client_missing_token():
    client = GitHubClient(token=None, owner="test-owner")
    status = client.check_connection()
    assert status["connected"] is False
    assert status["owner"] == "test-owner"
    assert "GITHUB_TOKEN is not configured" in status["error"]


def test_github_client_auth_success():
    client = GitHubClient(token="ghp_mocktoken123", owner="sripriyancsbs")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"login": "sripriyancsbs", "id": 12345}

    with patch("httpx.Client.get", return_value=mock_resp):
        status = client.check_connection()
        assert status["connected"] is True
        assert status["owner"] == "sripriyancsbs"
        assert status["authenticated_user"] == "sripriyancsbs"
        assert status["error"] is None


def test_github_client_auth_failure_401():
    client = GitHubClient(token="ghp_invalidtoken", owner="sripriyancsbs")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Bad credentials"

    with patch("httpx.Client.get", return_value=mock_resp):
        status = client.check_connection()
        assert status["connected"] is False
        assert "authentication failed" in status["error"].lower()


def test_github_client_permission_denied_403():
    client = GitHubClient(token="ghp_validtoken_no_scopes", owner="sripriyancsbs")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = "Resource not accessible by personal access token"

    with patch("httpx.Client.get", return_value=mock_resp):
        status = client.check_connection()
        assert status["connected"] is False
        assert "permission denied" in status["error"].lower()


def test_github_client_rate_limit():
    client = GitHubClient(token="ghp_ratelimited", owner="sripriyancsbs")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = "API rate limit exceeded for user"

    with patch("httpx.Client.get", return_value=mock_resp):
        status = client.check_connection()
        assert status["connected"] is False
        assert "rate limit exceeded" in status["error"].lower()


def test_github_client_timeout():
    client = GitHubClient(token="ghp_timeouttoken", owner="sripriyancsbs")
    
    with patch("httpx.Client.get", side_effect=httpx.ConnectTimeout("Connection timed out")):
        status = client.check_connection()
        assert status["connected"] is False
        assert "timed out" in status["error"].lower()


def test_github_client_api_unavailable():
    client = GitHubClient(token="ghp_mocktoken", owner="sripriyancsbs")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_resp.text = "Service Unavailable"

    with patch("httpx.Client.get", return_value=mock_resp):
        status = client.check_connection()
        assert status["connected"] is False
        assert "503" in status["error"]


# ==============================================================================
# 3. REPOSITORY CREATION & CONFLICT TESTS
# ==============================================================================

def test_github_create_repository_success():
    client = GitHubClient(token="ghp_validtoken", owner="sripriyancsbs")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {
        "name": "inventory-api",
        "full_name": "sripriyancsbs/inventory-api",
        "html_url": "https://github.com/sripriyancsbs/inventory-api",
        "clone_url": "https://github.com/sripriyancsbs/inventory-api.git",
        "default_branch": "main",
        "private": True
    }

    with patch.object(client, "get_repository", return_value=None), patch("httpx.Client.post", return_value=mock_resp):
        repo = client.create_repository("inventory-api", description="Test repo", private=True)
        assert repo["name"] == "inventory-api"
        assert repo["html_url"] == "https://github.com/sripriyancsbs/inventory-api"
        assert repo["default_branch"] == "main"
        assert repo["private"] is True


def test_github_create_repository_conflict():
    client = GitHubClient(token="ghp_validtoken", owner="sripriyancsbs")
    
    mock_resp = MagicMock()
    mock_resp.status_code = 422
    mock_resp.text = "name already exists on this account"

    with patch.object(client, "get_repository", return_value=None), patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(GitHubRepositoryConflictError) as exc_info:
            client.create_repository("existing-app")
        assert "already exists" in str(exc_info.value)
        assert exc_info.value.repo_name == "existing-app"


def test_repository_service_ensure_repository_conflict():
    mock_provider = MagicMock(spec=GitHubProvider)
    mock_provider.get_repository.return_value = {
        "name": "existing-app",
        "html_url": "https://github.com/sripriyancsbs/existing-app"
    }

    service = RepositoryService(provider=mock_provider)
    
    # Conflict when allow_existing is False
    with pytest.raises(GitHubRepositoryConflictError):
        service.ensure_repository("existing-app", allow_existing=False)

    # Reuses existing when allow_existing is True (e.g. during retry)
    reused = service.ensure_repository("existing-app", allow_existing=True)
    assert reused["name"] == "existing-app"


# ==============================================================================
# 4. GIT CLI LIFECYCLE TESTS (INIT, COMMIT, CONFIG, PUSH)
# ==============================================================================

def test_git_local_lifecycle():
    """Verify local Git init, commit, and safe unauthenticated remote setup."""
    temp_dir = Path(tempfile.mkdtemp(prefix="devforge_git_test_"))
    try:
        # Create a sample file
        (temp_dir / "README.md").write_text("# Test App\nProvisioned by DevForge\n", encoding="utf-8")
        
        service = RepositoryService()

        # Mock the push command so it doesn't attempt real network call
        with patch.object(service, "_run_git") as mock_run_git:
            # Let actual commands run except push
            def fake_run_git(cmd, cwd, token=None):
                if "push" in cmd:
                    return "Everything up-to-date"
                if "rev-parse" in cmd:
                    return "abc1234"
                # For real git commands in temp_dir
                res = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
                if res.returncode != 0:
                    raise GitOperationError(" ".join(cmd), res.returncode, res.stderr)
                return res.stdout.strip()

            mock_run_git.side_effect = fake_run_git

            res = service.initialize_and_push_project(
                project_dir=temp_dir,
                repo_html_url="https://github.com/sripriyancsbs/test-app",
                default_branch="main",
                token="ghp_dummytoken"
            )

            assert res["pushed"] is True
            assert res["branch"] == "main"
            assert res["commit_hash"] == "abc1234"

            # Check that .git exists in workspace
            assert (temp_dir / ".git").exists()

            # Verify that .git/config on disk does NOT contain the token
            git_config_file = temp_dir / ".git" / "config"
            if git_config_file.exists():
                config_content = git_config_file.read_text(encoding="utf-8")
                assert "ghp_dummytoken" not in config_content
                assert "x-access-token" not in config_content
                assert "https://github.com/sripriyancsbs/test-app.git" in config_content
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_git_push_failure_scrubs_token():
    """Verify that if git push fails, the token is scrubbed from the raised error message."""
    temp_dir = Path(tempfile.mkdtemp(prefix="devforge_git_fail_test_"))
    try:
        (temp_dir / "app.py").write_text("print('hello')", encoding="utf-8")
        service = RepositoryService()

        # Initialize local repo first
        subprocess.run(["git", "init", "-b", "main"], cwd=str(temp_dir), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(temp_dir), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.local"], cwd=str(temp_dir), check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=str(temp_dir), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=str(temp_dir), check=True, capture_output=True)

        secret_token = "ghp_VerySecretGitPushToken"

        # Attempt to push to an invalid remote URL that will fail
        with pytest.raises(GitOperationError) as exc_info:
            service.initialize_and_push_project(
                project_dir=temp_dir,
                repo_html_url="https://github.com/sripriyancsbs/non-existent-test-repo-xyz123",
                default_branch="main",
                token=secret_token
            )

        err_msg = str(exc_info.value)
        assert secret_token not in err_msg
        assert "[REDACTED_TOKEN]" in err_msg
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
