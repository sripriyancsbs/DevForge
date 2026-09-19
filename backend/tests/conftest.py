from unittest.mock import patch, MagicMock
import pytest

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Ensure the test database schema, tables, migrations, and baseline seed data
    are initialized before any test runs. This is critical for fresh CI environments.
    """
    from app.db.session import engine, Base, SessionLocal, run_phase2_migrations
    import app.models  # Register all SQLAlchemy models
    from app.db.seed import seed_database

    try:
        Base.metadata.create_all(bind=engine)
        run_phase2_migrations()
        db = SessionLocal()
        try:
            seed_database(db)
        except Exception:
            pass
        finally:
            db.close()
    except Exception as e:
        print(f"Warning during test database initialization: {e}")


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


@pytest.fixture(autouse=True)
def clean_pending_jobs():
    """
    Ensure worker FIFO queue isolation between tests.
    Any stale unhandled PENDING or RETRY jobs left by earlier tests are marked READY
    so they do not contaminate worker queue acquisition in subsequent tests.
    """
    from app.db.session import SessionLocal
    from app.models.provisioning_job import ProvisioningJob
    db = SessionLocal()
    try:
        db.query(ProvisioningJob).filter(ProvisioningJob.status.in_(["PENDING", "RETRY"])).update({"status": "READY"})
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    yield


@pytest.fixture
def db():
    from app.db.session import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c
