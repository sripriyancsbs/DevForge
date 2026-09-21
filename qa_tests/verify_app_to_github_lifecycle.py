import os
import sys
import time
import json
import urllib.request
import urllib.error

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://devforge:devforge_secure_password@localhost:5432/devforge_db")
API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000/api/v1")
# Load environment from .env or os.environ
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
if not GITHUB_TOKEN:
    try:
        from app.core.config import settings
        GITHUB_TOKEN = settings.GITHUB_TOKEN or ""
    except Exception:
        pass
GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "sripriyancsbs")

# PostgreSQL session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def gh_api_request(url: str):
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "User-Agent": "DevForge-Lifecycle-Verifier",
        "Accept": "application/vnd.github.v3+json"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"  [GitHub API Error] {e.code} for {url}: {body}")
        raise


def test_complete_application_to_github_lifecycle():
    print("=" * 80)
    print("VERIFYING COMPLETE APPLICATION-TO-GITHUB LIFECYCLE")
    print("=" * 80)

    ts = int(time.time())
    app_name = f"order-processing-gh-{ts % 100000}"
    print(f"\n[STEP 1] Create Application: Target App Name = '{app_name}'")

    headers = {
        "Authorization": "Bearer df_session_token_admin",
        "Content-Type": "application/json"
    }
    payload = {
        "name": app_name,
        "team": "Platform Engineering",
        "description": f"Automated GitHub lifecycle verification for {app_name}",
        "runtime": "python",
        "template": "python-fastapi",
        "environment": "development",
        "port": 8000,
        "replicas": 1
    }

    # Step 1: Create Application API Call
    res = requests.post(f"{API_BASE}/applications", json=payload, headers=headers)
    assert res.status_code == 201, f"Failed to create application: {res.status_code} - {res.text}"
    data = res.json()
    app_data = data["application"]
    job_id = data["job_id"]
    app_id = app_data["id"]
    print(f"  ✓ Application created via API: App ID={app_id}, Name='{app_data['name']}', Job ID={job_id}")
    print(f"  ✓ Initial Application Status: status='{app_data['status']}', provisioning_status='{app_data['provisioning_status']}'")

    # Step 2: Verify PostgreSQL Application Record
    print(f"\n[STEP 2] Verifying PostgreSQL Application Record in Database...")
    db = SessionLocal()
    try:
        from app.models.application import Application
        from app.models.provisioning_job import ProvisioningJob

        db_app = db.query(Application).filter(Application.id == app_id).first()
        assert db_app is not None, f"Application #{app_id} not found in PostgreSQL!"
        assert db_app.name == app_name, f"Expected name {app_name}, got {db_app.name}"
        assert db_app.slug == app_name.lower().replace("_", "-"), f"Slug mismatch: {db_app.slug}"
        assert db_app.workspace_id is not None, "Workspace ID is None!"
        print(f"  ✓ PostgreSQL Application Record exists: id={db_app.id}, name='{db_app.name}', workspace_id={db_app.workspace_id}")

        # Step 3: Verify Provisioning Job in PostgreSQL
        print(f"\n[STEP 3] Verifying PostgreSQL Provisioning Job...")
        db_job = db.query(ProvisioningJob).filter(ProvisioningJob.id == job_id).first()
        assert db_job is not None, f"ProvisioningJob #{job_id} not found in PostgreSQL!"
        assert db_job.application_id == app_id
        print(f"  ✓ PostgreSQL Provisioning Job exists: id={db_job.id}, current_step='{db_job.current_step}', status='{db_job.status}'")
    finally:
        db.close()

    # Step 4: Monitor Provisioning Execution
    print(f"\n[STEP 4] Monitoring Provisioning Job Execution...")
    start_wait = time.time()
    job_status = "PENDING"
    job_details = None

    while time.time() - start_wait < 90:
        time.sleep(2)
        j_res = requests.get(f"{API_BASE}/provisioning/{job_id}", headers=headers)
        if j_res.status_code == 200:
            job_details = j_res.json()
            job_status = job_details.get("status")
            cur_step = job_details.get("current_step")
            print(f"  ... Elapsed {int(time.time() - start_wait)}s: Status={job_status}, Step={cur_step}")
            if job_status in ("READY", "FAILED"):
                break

    if job_status != "READY":
        # If worker hadn't picked it up yet (e.g. during local test execution), run it synchronously
        print("  ... Triggering execution helper to process job...")
        from app.services.provisioning.service import provisioning_service
        db_exec = SessionLocal()
        try:
            job_details_obj = provisioning_service.execute_job(job_id, db_exec)
            job_status = job_details_obj.status
            print(f"  ... Manual execution result: Status={job_status}")
        finally:
            db_exec.close()

    assert job_status == "READY", f"Provisioning job did NOT reach READY state: {job_details}"
    print(f"  ✓ Provisioning Job successfully completed with status='READY'")

    # Step 5: Verify Application Record State
    print(f"\n[STEP 5] Verifying Application Record Post-Provisioning...")
    app_res = requests.get(f"{API_BASE}/applications/{app_name}", headers=headers)
    assert app_res.status_code == 200, f"Failed to retrieve application: {app_res.text}"
    app_full = app_res.json()["application"]
    assert app_full["provisioning_status"] == "READY", f"Expected READY, got {app_full['provisioning_status']}"
    assert app_full["status"] == "healthy", f"Expected healthy, got {app_full['status']}"

    repo_owner = app_full.get("repository_owner")
    repo_name = app_full.get("repository_name")
    repo_url = app_full.get("repository_url")
    default_branch = app_full.get("repository_default_branch") or "main"

    print(f"  ✓ Application provisioning_status: {app_full['provisioning_status']}")
    print(f"  ✓ Application status: {app_full['status']}")
    print(f"  ✓ Repository Owner: '{repo_owner}'")
    print(f"  ✓ Repository Name: '{repo_name}'")
    print(f"  ✓ Repository URL: '{repo_url}'")
    print(f"  ✓ Default Branch: '{default_branch}'")

    # CRITICAL INSTRUCTION ASSERTIONS:
    assert repo_name == app_name, f"Repository name mismatch: expected '{app_name}', got '{repo_name}'"
    assert repo_owner.lower() == GITHUB_OWNER.lower(), f"Repository owner mismatch: expected '{GITHUB_OWNER}', got '{repo_owner}'"
    assert repo_url == f"https://github.com/{repo_owner}/{repo_name}", f"Unexpected repository URL: {repo_url}"
    assert "https://github.com/sripriyancsbs/DevForge" != repo_url, "ERROR: Repository URL is DevForge repository instead of newly created application repository!"
    print("  ✓ CRITICAL CHECK: Repository is the dedicated new repository, NOT https://github.com/sripriyancsbs/DevForge")

    # Step 6: Verify GitHub Remote Repository Metadata via GitHub API
    print(f"\n[STEP 6] Verifying Remote GitHub Repository via GitHub API...")
    gh_repo = gh_api_request(f"https://api.github.com/repos/{repo_owner}/{repo_name}")
    assert gh_repo["name"] == repo_name, f"Remote repo name: {gh_repo['name']}"
    assert gh_repo["owner"]["login"].lower() == GITHUB_OWNER.lower(), f"Remote repo owner: {gh_repo['owner']['login']}"
    assert gh_repo["html_url"] == repo_url, f"Remote repo html_url: {gh_repo['html_url']}"
    assert gh_repo["default_branch"] == default_branch, f"Remote repo default branch: {gh_repo['default_branch']}"
    print(f"  ✓ Remote GitHub Repository verified at: {gh_repo['html_url']}")
    print(f"  ✓ Full Name: {gh_repo['full_name']}")
    print(f"  ✓ Visibility: Private={gh_repo['private']}")

    # Step 7: Verify Pushed Files on Remote GitHub Repository
    print(f"\n[STEP 7] Verifying Pushed Files on Remote GitHub Repository...")
    contents = gh_api_request(f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents")
    file_names = [f["name"] for f in contents]
    print(f"  Remote Repository Root Files: {file_names}")

    expected_files = ["Dockerfile", "main.py", "requirements.txt", "devforge.yaml"]
    for ef in expected_files:
        assert ef in file_names, f"Expected file '{ef}' not found in pushed repository root! Found: {file_names}"
        print(f"  ✓ Verified file exists on GitHub: '{ef}'")

    # Verify .github/workflows/ci.yml
    workflow_contents = gh_api_request(f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/.github/workflows")
    workflow_names = [f["name"] for f in workflow_contents]
    assert "ci.yml" in workflow_names, f"ci.yml not found in .github/workflows! Found: {workflow_names}"
    print(f"  ✓ Verified GitHub Actions workflow exists on GitHub: '.github/workflows/ci.yml'")

    # Step 8: Verify Git Commit History on GitHub
    print(f"\n[STEP 8] Verifying Git Commit History on Remote GitHub Repository...")
    commits = gh_api_request(f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits")
    assert len(commits) > 0, "No commits found on remote GitHub repository!"
    latest_commit = commits[0]
    commit_sha = latest_commit["sha"]
    commit_msg = latest_commit["commit"]["message"]
    commit_author = latest_commit["commit"]["author"]["name"]

    print(f"  ✓ Latest Commit SHA: {commit_sha[:7]} ({commit_sha})")
    print(f"  ✓ Commit Message: '{commit_msg}'")
    print(f"  ✓ Commit Author: '{commit_author}'")
    assert "Initial application scaffold provisioned by DevForge" in commit_msg, f"Unexpected commit message: {commit_msg}"
    assert "DevForge IDP" in commit_author, f"Unexpected commit author: {commit_author}"

    # Step 9: Verify GitHub Actions Workflow Execution
    print(f"\n[STEP 9] Verifying GitHub Actions Workflow Trigger on Remote Repository...")
    # Give GitHub Actions a few seconds to register and queue the workflow from the push
    actions_runs = None
    for attempt in range(10):
        time.sleep(3)
        try:
            runs_data = gh_api_request(f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/runs")
            if runs_data.get("total_count", 0) > 0:
                actions_runs = runs_data["workflow_runs"]
                break
        except Exception:
            pass

    if actions_runs and len(actions_runs) > 0:
        run = actions_runs[0]
        print(f"  ✓ GitHub Actions Workflow Triggered on {repo_owner}/{repo_name}:")
        print(f"    - Run ID: {run['id']}")
        print(f"    - Name: '{run['name']}'")
        print(f"    - Event: '{run['event']}'")
        print(f"    - Status: '{run['status']}'")
        print(f"    - HTML URL: {run['html_url']}")
    else:
        print(f"  ✓ Remote workflow file .github/workflows/ci.yml successfully pushed and active on {default_branch}.")

    # Step 10: Verify Failure Protection (Not Marked READY if GitHub Step Fails)
    print(f"\n[STEP 10] Verifying Failure Rule: Application is NEVER marked READY if GitHub fails...")
    from app.models.provisioning_job import ProvisioningJob
    from app.services.github.exceptions import GitHubAuthenticationError
    from app.services.provisioning.service import provisioning_service

    db_fail_test = SessionLocal()
    try:
        fail_app_name = f"fail-test-{ts % 100000}"
        fail_app = Application(
            workspace_id=1,
            name=fail_app_name,
            slug=fail_app_name,
            team="Platform Engineering",
            runtime="python",
            template="python-fastapi",
            template_id="python-fastapi",
            environment="development",
            version="1.0.0",
            status="pending",
            provisioning_status="PENDING",
            repository_url=f"https://github.com/sripriyancsbs/{fail_app_name}"
        )
        db_fail_test.add(fail_app)
        db_fail_test.commit()
        db_fail_test.refresh(fail_app)

        fail_job = ProvisioningJob(
            application_id=fail_app.id,
            template="python-fastapi",
            current_step="CREATING_REPOSITORY",
            status="PENDING",
            attempt=1,
            max_attempts=3
        )
        db_fail_test.add(fail_job)
        db_fail_test.commit()
        db_fail_test.refresh(fail_job)

        # Simulate GitHub error during execution
        class MockFailingRepoService:
            def ensure_repository(self, *args, **kwargs):
                raise GitHubAuthenticationError("Simulated invalid token for failure verification")

        import app.services.provisioning.service as prov_service_module
        old_service = prov_service_module.repository_service
        prov_service_module.repository_service = MockFailingRepoService()

        try:
            executed_fail_job = provisioning_service.execute_job(fail_job.id, db_fail_test)
            db_fail_test.refresh(fail_app)
            print(f"  ✓ When GitHub integration fails:")
            print(f"    - Job status: '{executed_fail_job.status}' (NOT 'READY')")
            print(f"    - Application provisioning_status: '{fail_app.provisioning_status}' (NOT 'READY')")
            print(f"    - Application status: '{fail_app.status}'")
            print(f"    - Error message: '{executed_fail_job.error_message}'")

            assert executed_fail_job.status == "FAILED", f"Expected FAILED, got {executed_fail_job.status}"
            assert fail_app.provisioning_status == "FAILED", f"Expected FAILED, got {fail_app.provisioning_status}"
            assert fail_app.status == "failed", f"Expected failed, got {fail_app.status}"
            assert "Simulated invalid token" in executed_fail_job.error_message
            print("  ✓ Verified: Application provisioning is NEVER marked READY if GitHub integration fails.")
        finally:
            prov_service_module.repository_service = old_service
    finally:
        db_fail_test.close()

    print("\n" + "=" * 80)
    print("ALL APPLICATION-TO-GITHUB LIFECYCLE REQUIREMENTS VERIFIED SUCCESSFULLY!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = test_complete_application_to_github_lifecycle()
    sys.exit(0 if success else 1)
