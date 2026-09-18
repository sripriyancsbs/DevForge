from unittest.mock import patch, MagicMock
import pytest

@pytest.fixture(autouse=True)
def mock_repository_service_for_offline_tests(request):
    """
    Ensure all unit & integration tests run offline without requiring
    real GitHub credentials unless explicitly testing GitHub client methods.
    """
    # Don't mock repository_service if the test specifically tests real/mocked GitHubClient
    if "test_github_service" in request.node.nodeid and "test_phase3" not in request.node.nodeid:
        yield None
        return

    with patch("app.services.provisioning.service.repository_service") as mock_repo_svc:
        mock_repo_svc.ensure_repository.side_effect = lambda repo_name, description=None, allow_existing=False: {
            "name": repo_name,
            "full_name": f"sripriyancsbs/{repo_name}",
            "html_url": f"https://github.com/sripriyancsbs/{repo_name}",
            "default_branch": "main",
            "private": True
        }
        mock_repo_svc.initialize_and_push_project.side_effect = lambda project_dir, repo_html_url, default_branch="main", token=None: {
            "pushed": True,
            "branch": default_branch,
            "commit_hash": "9a1f2b4",
            "remote_url": f"{repo_html_url}.git"
        }
        yield mock_repo_svc
