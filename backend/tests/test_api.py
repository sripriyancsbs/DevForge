import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.db.session import engine, verify_connection

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# 1. Health Probe & PostgreSQL Connection Check
def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "DevForge" in data["service"]

def test_postgresql_connection():
    # Verify active connection to PostgreSQL
    assert verify_connection() is True
    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_database(), current_user;")).fetchone()
        assert result is not None
        assert result[0] == "devforge_db"
        assert result[1] == "devforge"

# 2. Overview Endpoint
def test_overview_endpoint(client):
    response = client.get("/api/v1/overview")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "recent_deployments" in data
    assert "service_health" in data
    assert "recent_activity" in data
    assert data["metrics"]["applications_count"] >= 0
    assert len(data["metrics"]["metrics_cards"]) == 4

# 3. Application Creation (Valid)
def test_create_application_success(client):
    new_app = {
        "name": "audit-stream-processor",
        "team": "Security & Identity",
        "runtime": "Python 3.12 (FastAPI)",
        "repository_url": "https://github.com/devforge-org/audit-stream-processor",
        "branch": "main",
        "environment": "production",
        "version": "v1.0.0",
        "port": 8000,
        "replicas": 3
    }
    response = client.post("/api/v1/applications", json=new_app)
    # 201 Created or 409 if already created in earlier test run
    assert response.status_code in [201, 409]
    if response.status_code == 201:
        data = response.json()
        app_data = data.get("application", data)
        assert app_data["name"] == "audit-stream-processor"
        assert app_data["slug"] == "audit-stream-processor"
        assert app_data["status"] in ["healthy", "pending"]
        assert app_data["port"] == 8000

# 4. Duplicate Application Conflict (409)
def test_create_application_duplicate_error(client):
    duplicate_app = {
        "name": "payment-gateway", # Already seeded in PostgreSQL
        "team": "Payments",
        "runtime": "Python 3.12 (FastAPI)",
        "repository_url": "https://github.com/devforge-org/payment-gateway",
        "environment": "production"
    }
    response = client.post("/api/v1/applications", json=duplicate_app)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]

# 5. Invalid Application Input Validation (422)
def test_create_application_invalid_name(client):
    invalid_app = {
        "name": "-Invalid_Upper_Case!-",
        "team": "QA",
        "repository_url": "https://github.com/org/app",
        "environment": "production"
    }
    response = client.post("/api/v1/applications", json=invalid_app)
    assert response.status_code == 422
    assert "errors" in response.json() or "detail" in response.json()

def test_create_application_invalid_port(client):
    invalid_app = {
        "name": "invalid-port-service",
        "team": "QA",
        "repository_url": "https://github.com/org/app",
        "port": 99999, # Exceeds 65535
        "environment": "production"
    }
    response = client.post("/api/v1/applications", json=invalid_app)
    assert response.status_code == 422

def test_create_application_invalid_environment(client):
    invalid_app = {
        "name": "invalid-env-service",
        "team": "QA",
        "repository_url": "https://github.com/org/app",
        "environment": "unknown-datacenter" # Disallowed
    }
    response = client.post("/api/v1/applications", json=invalid_app)
    assert response.status_code == 422

# 6. Application Retrieval & Not Found (404)
def test_get_application_by_id_and_slug(client):
    # Retrieve by slug
    response = client.get("/api/v1/applications/payment-gateway")
    assert response.status_code == 200
    data = response.json()
    assert data["application"]["slug"] == "payment-gateway"
    assert "deployments" in data
    assert "health" in data

    # Retrieve by numeric ID
    app_id = data["application"]["id"]
    res_by_id = client.get(f"/api/v1/applications/{app_id}")
    assert res_by_id.status_code == 200
    assert res_by_id.json()["application"]["id"] == app_id

def test_get_application_not_found(client):
    response = client.get("/api/v1/applications/non-existent-service-999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

# 7. Application Filtering
def test_applications_filtering(client):
    # Filter by healthy
    resp_healthy = client.get("/api/v1/applications?status=healthy")
    assert resp_healthy.status_code == 200
    for app_item in resp_healthy.json():
        assert app_item["status"] == "healthy"

    # Filter by production environment
    resp_prod = client.get("/api/v1/applications?environment=production")
    assert resp_prod.status_code == 200
    for app_item in resp_prod.json():
        assert app_item["environment"] == "production"

# 8. Deployments & Validation
def test_deployments_list_and_filter(client):
    response = client.get("/api/v1/deployments")
    assert response.status_code == 200
    deps = response.json()
    assert isinstance(deps, list)
    assert len(deps) > 0

    # Filter by status
    dep_filtered = client.get("/api/v1/deployments?status=healthy")
    assert dep_filtered.status_code == 200
    for d in dep_filtered.json():
        assert d["status"] == "healthy"

def test_trigger_deployment_invalid_app(client):
    payload = {
        "application_id": 99999, # Non-existent app
        "version": "v9.9.9",
        "environment": "production"
    }
    response = client.post("/api/v1/deployments/trigger", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

# 9. Environments List & Retrieval
def test_environments_endpoints(client):
    # List all
    response = client.get("/api/v1/environments")
    assert response.status_code == 200
    envs = response.json()
    assert len(envs) >= 4
    names = [e["slug"] for e in envs]
    assert "production" in names
    assert "staging" in names

    # Single environment
    single = client.get("/api/v1/environments/production")
    assert single.status_code == 200
    assert single.json()["slug"] == "production"

    # Not found environment
    missing = client.get("/api/v1/environments/non-existent-env")
    assert missing.status_code == 404

# 10. Infrastructure, Monitoring, and Activity
def test_infrastructure_endpoint(client):
    response = client.get("/api/v1/infrastructure")
    assert response.status_code == 200
    data = response.json()
    assert "clusters" in data
    assert "datastores" in data
    assert "summary" in data

def test_monitoring_endpoint(client):
    response = client.get("/api/v1/monitoring")
    assert response.status_code == 200
    data = response.json()
    assert "global" in data
    assert "service_metrics" in data

def test_activity_endpoint(client):
    response = client.get("/api/v1/activity")
    assert response.status_code == 200
    activities = response.json()
    assert isinstance(activities, list)
    assert len(activities) > 0
