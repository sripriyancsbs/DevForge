import os
import shutil
from unittest.mock import patch, MagicMock
from pathlib import Path
import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.db.session import SessionLocal
from app.models.application import Application
from app.models.provisioning_job import ProvisioningJob
from app.models.deployment import Deployment
from app.models.service_health import ServiceHealth
from app.models.activity import Activity
from app.services.provisioning.service import provisioning_service
from app.services.provisioning.project_generator import project_generator, get_workspace_root
from app.worker.provisioning_worker import process_one_job
from app.services.github.exceptions import GitHubRepositoryConflictError, GitHubRateLimitError

@pytest.fixture(autouse=True)
def mock_github_repository_service():
    """Mock remote GitHub and git operations for offline worker test runs."""
    with patch("app.services.provisioning.service.repository_service") as mock_repo_svc:
        mock_repo_svc.ensure_repository.side_effect = lambda repo_name, description=None, allow_existing=False: {
            "name": repo_name,
            "html_url": f"https://github.com/sripriyancsbs/{repo_name}",
            "default_branch": "main"
        }
        mock_repo_svc.initialize_and_push_project.side_effect = lambda project_dir, repo_html_url, default_branch="main", token=None: {
            "pushed": True,
            "branch": default_branch,
            "commit_hash": "a1b2c3d",
            "remote_url": f"{repo_html_url}.git"
        }
        yield mock_repo_svc

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(autouse=True)
def cleanup_test_apps():
    yield
    # Cleanup applications and workspace directories created during testing
    db = SessionLocal()
    try:
        test_apps = db.query(Application).filter(Application.name.like("test-worker-%")).all()
        for app_obj in test_apps:
            # Delete isolated directory
            app_dir = get_workspace_root() / f"app_{app_obj.id}"
            if app_dir.exists():
                shutil.rmtree(app_dir, ignore_errors=True)
            db.delete(app_obj)
        db.commit()
    finally:
        db.close()


def test_async_application_creation(client):
    """
    Verify POST /api/v1/applications returns immediately without blocking.
    Response should contain job_id and PENDING status.
    """
    app_name = "test-worker-async-service"
    payload = {
        "name": app_name,
        "runtime": "python",
        "template": "python-fastapi",
        "environment": "staging",
        "port": 8000,
        "replicas": 2,
        "database_type": "postgresql",
        "deployment_strategy": "rolling"
    }

    response = client.post("/api/v1/applications", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["provisioning_status"] == "PENDING"
    assert "job_id" in data
    assert data["job_id"] is not None
    job_id = data["job_id"]
    app_id = data["application"]["id"]

    # Verify database state
    db = SessionLocal()
    try:
        app_record = db.query(Application).filter(Application.id == app_id).first()
        assert app_record is not None
        assert app_record.status == "pending"
        assert app_record.provisioning_status == "PENDING"

        job_record = db.query(ProvisioningJob).filter(ProvisioningJob.id == job_id).first()
        assert job_record is not None
        assert job_record.status == "PENDING"
        assert job_record.current_step == "VALIDATE_CONFIGURATION"
        assert job_record.attempt == 1
        assert job_record.application_id == app_id
    finally:
        db.close()


def test_polling_endpoint(client):
    """
    Verify GET /api/v1/provisioning/{job_id} returns accurate job state and current step.
    """
    app_name = "test-worker-poll-service"
    payload = {
        "name": app_name,
        "runtime": "go",
        "template": "go-microservice",
        "environment": "production",
        "port": 8080
    }
    create_res = client.post("/api/v1/applications", json=payload)
    assert create_res.status_code == 201
    job_id = create_res.json()["job_id"]
    app_id = create_res.json()["application"]["id"]

    # Poll by job ID
    poll_res = client.get(f"/api/v1/provisioning/{job_id}")
    assert poll_res.status_code == 200
    job_data = poll_res.json()
    assert job_data["id"] == job_id
    assert job_data["application_id"] == app_id
    assert job_data["status"] == "PENDING"
    assert job_data["current_step"] == "VALIDATE_CONFIGURATION"

    # Poll by application ID
    by_app_res = client.get(f"/api/v1/provisioning/by-app/{app_id}")
    assert by_app_res.status_code == 200
    assert by_app_res.json()["id"] == job_id

    # Non-existent job
    not_found_res = client.get("/api/v1/provisioning/999999")
    assert not_found_res.status_code == 404


def test_worker_row_locking_and_execution(client):
    """
    Verify worker acquires job using SELECT ... FOR UPDATE SKIP LOCKED
    and executes all steps to completion in isolated workspace.
    """
    app_name = "test-worker-lifecycle-service"
    payload = {
        "name": app_name,
        "runtime": "react",
        "template": "react-vite",
        "environment": "development",
        "port": 3000
    }
    create_res = client.post("/api/v1/applications", json=payload)
    assert create_res.status_code == 201
    job_id = create_res.json()["job_id"]
    app_id = create_res.json()["application"]["id"]

    # 1. Acquire job with row lock
    db = SessionLocal()
    try:
        acquired_job = provisioning_service.acquire_next_job(db)
        assert acquired_job is not None
        assert acquired_job.id == job_id
        assert acquired_job.status == "PROVISIONING"
        assert acquired_job.started_at is not None

        # Try to acquire again concurrently - should return None because job is already claimed
        second_acquire = provisioning_service.acquire_next_job(db)
        # Should either be None or another unacquired job, but not this job
        if second_acquire:
            assert second_acquire.id != job_id
    finally:
        db.close()

    # 2. Execute job
    db = SessionLocal()
    try:
        finished_job = provisioning_service.execute_job(job_id, db)
        assert finished_job.status == "READY"
        assert finished_job.current_step == "COMPLETED"
        assert finished_job.completed_at is not None
        assert finished_job.error_message is None

        # Verify isolated workspace location: .devforge/generated/app_{app_id}
        expected_dir = get_workspace_root() / f"app_{app_id}"
        assert expected_dir.exists()
        assert (expected_dir / "package.json").exists()
        assert (expected_dir / "Dockerfile").exists()
        assert (expected_dir / "devforge.yaml").exists()

        # Verify manifest content
        with open(expected_dir / "devforge.yaml", "r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f)
            assert manifest["apiVersion"] == "devforge/v1"
            assert manifest["spec"]["port"] == 3000

        # Verify Application record updated
        app_record = db.query(Application).filter(Application.id == app_id).first()
        assert app_record.provisioning_status == "READY"
        assert app_record.status == "healthy"
        assert app_record.generated_path == f".devforge/generated/app_{app_id}"
        assert app_record.manifest_yaml is not None

        # Verify Deployment created
        deployment = db.query(Deployment).filter(Deployment.application_id == app_id).first()
        assert deployment is not None
        assert deployment.status == "healthy"

        # Verify ServiceHealth created
        health = db.query(ServiceHealth).filter(ServiceHealth.application_id == app_id).first()
        assert health is not None
        assert health.status == "healthy"
    finally:
        db.close()


def test_worker_process_one_job_helper(client):
    """
    Verify process_one_job() helper claims and provisions a pending job in a single call.
    """
    app_name = "test-worker-helper-service"
    payload = {
        "name": app_name,
        "runtime": "node",
        "template": "node-service",
        "environment": "production",
        "port": 3000
    }
    create_res = client.post("/api/v1/applications", json=payload)
    assert create_res.status_code == 201
    job_id = create_res.json()["job_id"]
    app_id = create_res.json()["application"]["id"]

    processed = process_one_job()
    assert processed is not None
    assert processed.id == job_id
    assert processed.status == "READY"

    # Workspace verified
    workspace = get_workspace_root() / f"app_{app_id}"
    assert workspace.exists()
    assert (workspace / "server.js").exists()


def test_idempotent_regeneration(client):
    """
    Verify that executing a job when the isolated workspace already exists is safe and idempotent.
    """
    app_name = "test-worker-idempotent-service"
    payload = {
        "name": app_name,
        "runtime": "python",
        "template": "python-fastapi",
        "port": 8000
    }
    create_res = client.post("/api/v1/applications", json=payload)
    job_id = create_res.json()["job_id"]
    app_id = create_res.json()["application"]["id"]

    db = SessionLocal()
    try:
        # Run 1
        job1 = provisioning_service.execute_job(job_id, db)
        assert job1.status == "READY"

        # Run 2 (Idempotency test)
        job2 = provisioning_service.execute_job(job_id, db)
        assert job2.status == "READY"

        target_dir = get_workspace_root() / f"app_{app_id}"
        assert target_dir.exists()
        assert (target_dir / "main.py").exists()
    finally:
        db.close()


def test_non_retryable_failure_handling(client):
    """
    Verify that non-retryable errors fail fast without looping through 3 attempts.
    """
    db = SessionLocal()
    try:
        # Manually create application and job with corrupted/invalid template
        app_record = Application(
            name="test-worker-fail-fast",
            slug="test-worker-fail-fast",
            runtime="Python 3.12 (FastAPI)",
            template="unsupported-nonexistent-template",
            repository_url="https://github.com/devforge-org/test-worker-fail-fast",
            environment="staging",
            status="pending",
            provisioning_status="PENDING"
        )
        db.add(app_record)
        db.commit()
        db.refresh(app_record)

        job = ProvisioningJob(
            application_id=app_record.id,
            status="PENDING",
            template="unsupported-nonexistent-template",
            current_step="VALIDATE_CONFIGURATION",
            attempt=1,
            max_attempts=3,
            is_retryable=True
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        failed_job = provisioning_service.execute_job(job.id, db)
        assert failed_job.status == "FAILED"
        assert failed_job.is_retryable is False
        assert failed_job.attempt == 1  # Did not spin 3 times for a non-retryable error
        assert "Unsupported template" in failed_job.error_message

        # Application record updated to FAILED
        db.refresh(app_record)
        assert app_record.provisioning_status == "FAILED"
        assert app_record.status == "failed"
    finally:
        db.close()


def test_retry_provisioning_job_api(client):
    """
    Verify POST /api/v1/provisioning/{job_id}/retry resets a FAILED job to PENDING.
    """
    db = SessionLocal()
    try:
        app_record = Application(
            name="test-worker-retry-api",
            slug="test-worker-retry-api",
            runtime="Python 3.12 (FastAPI)",
            template="python-fastapi",
            repository_url="https://github.com/devforge-org/test-worker-retry-api",
            environment="staging",
            status="failed",
            provisioning_status="FAILED",
            provisioning_error="Simulated network interruption during provisioning"
        )
        db.add(app_record)
        db.commit()
        db.refresh(app_record)

        job = ProvisioningJob(
            application_id=app_record.id,
            status="FAILED",
            template="python-fastapi",
            current_step="GENERATE_PROJECT",
            attempt=1,
            max_attempts=3,
            is_retryable=True,
            error_message="Simulated network interruption during provisioning"
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
    finally:
        db.close()

    # Call retry API
    retry_res = client.post(f"/api/v1/provisioning/{job_id}/retry")
    assert retry_res.status_code == 200
    retried_data = retry_res.json()
    assert retried_data["status"] == "PENDING"
    assert retried_data["attempt"] == 2
    assert retried_data["error_message"] is None

    # Now the worker can execute it successfully
    db = SessionLocal()
    try:
        finished = provisioning_service.execute_job(job_id, db)
        assert finished.status == "READY"
        assert finished.current_step == "COMPLETED"
    finally:
        db.close()


def test_sync_execution_flag(client):
    """
    Verify that ?sync=true runs synchronous provisioning immediately for test suites.
    """
    app_name = "test-worker-sync-flag"
    payload = {
        "name": app_name,
        "runtime": "python",
        "template": "python-fastapi",
        "environment": "development",
        "port": 8000
    }
    res = client.post("/api/v1/applications?sync=true", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["provisioning_status"] == "READY"
    assert data["generated_path"] is not None
    assert (get_workspace_root() / f"app_{data['application']['id']}").exists()


def test_phase3_provisioning_state_machine_steps(client):
    """
    Verify complete Phase 3 workflow:
    PENDING -> VALIDATING -> GENERATING_PROJECT -> GENERATING_MANIFEST ->
    VALIDATING_PROJECT -> CREATING_REPOSITORY -> PUSHING_REPOSITORY -> READY
    and verify repository metadata is stored in PostgreSQL.
    """
    app_name = "test-worker-phase3-lifecycle"
    payload = {
        "name": app_name,
        "runtime": "python",
        "template": "python-fastapi",
        "environment": "production",
        "port": 8000
    }
    create_res = client.post("/api/v1/applications", json=payload)
    assert create_res.status_code == 201
    job_id = create_res.json()["job_id"]
    app_id = create_res.json()["application"]["id"]

    db = SessionLocal()
    try:
        # Step through execution
        job = provisioning_service.acquire_next_job(db)
        assert job.id == job_id

        finished_job = provisioning_service.execute_job(job.id, db)
        assert finished_job.status == "READY"
        assert finished_job.current_step == "COMPLETED"

        # Verify repository metadata in Application table
        app_record = db.query(Application).filter(Application.id == app_id).first()
        assert app_record.repository_owner == "sripriyancsbs"
        assert app_record.repository_name == app_name
        assert app_record.repository_url == f"https://github.com/sripriyancsbs/{app_name}"
        assert app_record.repository_default_branch == "main"

        # Verify Activity logs recorded GitHub events
        activities = db.query(Activity).filter(Activity.target.like(f"%{app_name}%")).all()
        actions = [a.action for a in activities]
        assert "GitHub repository created" in actions
        assert "Git repository initialized" in actions
        assert "Initial commit created" in actions
        assert "Repository push started" in actions
        assert "Repository push completed" in actions
    finally:
        db.close()


def test_github_transient_failure_and_retry(client, mock_github_repository_service):
    """
    Verify that transient GitHub errors (e.g. rate limit) cause the job to enter RETRY,
    and subsequent retry successfully completes to READY.
    """
    app_name = "test-worker-transient-retry"
    payload = {
        "name": app_name,
        "runtime": "go",
        "template": "go-microservice",
        "port": 8080
    }
    create_res = client.post("/api/v1/applications", json=payload)
    job_id = create_res.json()["job_id"]
    app_id = create_res.json()["application"]["id"]

    # First attempt: raise transient rate limit error
    mock_github_repository_service.ensure_repository.side_effect = GitHubRateLimitError("GitHub API rate limit exceeded")

    db = SessionLocal()
    try:
        job = provisioning_service.execute_job(job_id, db)
        assert job.status == "RETRY"
        assert job.attempt == 2
        assert "rate limit exceeded" in job.error_message.lower()

        # Application remains pending/retrying
        app_record = db.query(Application).filter(Application.id == app_id).first()
        assert app_record.provisioning_status == "PENDING"

        # Second attempt: reset mock to succeed
        mock_github_repository_service.ensure_repository.side_effect = lambda repo_name, description=None, allow_existing=False: {
            "name": repo_name,
            "html_url": f"https://github.com/sripriyancsbs/{repo_name}",
            "default_branch": "main"
        }

        success_job = provisioning_service.execute_job(job_id, db)
        assert success_job.status == "READY"
        assert success_job.current_step == "COMPLETED"

        db.refresh(app_record)
        assert app_record.provisioning_status == "READY"
        assert app_record.repository_url == f"https://github.com/sripriyancsbs/{app_name}"
    finally:
        db.close()


def test_github_non_retryable_conflict_failure(client, mock_github_repository_service):
    """
    Verify that non-retryable conflict errors (repository already exists)
    fail immediately without spinning through max retries.
    """
    app_name = "test-worker-conflict-fail"
    payload = {
        "name": app_name,
        "runtime": "python",
        "template": "python-fastapi",
        "port": 8000
    }
    create_res = client.post("/api/v1/applications", json=payload)
    job_id = create_res.json()["job_id"]
    app_id = create_res.json()["application"]["id"]

    mock_github_repository_service.ensure_repository.side_effect = GitHubRepositoryConflictError(app_name, "sripriyancsbs")

    db = SessionLocal()
    try:
        failed_job = provisioning_service.execute_job(job_id, db)
        assert failed_job.status == "FAILED"
        assert failed_job.is_retryable is False
        assert failed_job.attempt == 1
        assert "already exists" in failed_job.error_message

        # Application marked as FAILED
        app_record = db.query(Application).filter(Application.id == app_id).first()
        assert app_record.provisioning_status == "FAILED"

        # Activity recorded
        activity = db.query(Activity).filter(
            Activity.action == "GitHub repository provisioning failed",
            Activity.target == app_name
        ).first()
        assert activity is not None
        assert activity.status == "failed"
    finally:
        db.close()


def test_security_token_never_persisted_or_exposed(client):
    """
    Verify security requirements:
    1. GITHUB_TOKEN never appears in Application or ProvisioningJob tables.
    2. GITHUB_TOKEN never appears in API responses.
    """
    app_name = "test-worker-security-check"
    payload = {
        "name": app_name,
        "runtime": "react",
        "template": "react-vite",
        "port": 3000
    }
    res = client.post("/api/v1/applications?sync=true", json=payload)
    assert res.status_code == 201
    resp_text = res.text

    # No token fields in API response
    assert "github_token" not in resp_text.lower()
    assert "access_token" not in resp_text.lower()

    # Check database table columns
    db = SessionLocal()
    try:
        app_record = db.query(Application).filter(Application.name == app_name).first()
        assert not hasattr(app_record, "github_token")
        assert not hasattr(app_record, "access_token")
        assert not hasattr(app_record, "secret")

        job_record = db.query(ProvisioningJob).filter(ProvisioningJob.application_id == app_record.id).first()
        assert not hasattr(job_record, "github_token")
        if job_record.payload_snapshot:
            assert "token" not in job_record.payload_snapshot.lower()
    finally:
        db.close()


def test_reprovision_application_endpoint(client):
    """
    Verify POST /api/v1/applications/{id}/provision triggers reprovisioning safely.
    """
    app_name = "test-worker-reprovision-ep"
    payload = {
        "name": app_name,
        "runtime": "python",
        "template": "python-fastapi",
        "port": 8000
    }
    create_res = client.post("/api/v1/applications", json=payload)
    app_id = create_res.json()["application"]["id"]

    reprov_res = client.post(f"/api/v1/applications/{app_id}/provision?sync=true")
    assert reprov_res.status_code == 200
    data = reprov_res.json()
    assert data["provisioning_status"] == "READY"
    assert data["application"]["id"] == app_id

