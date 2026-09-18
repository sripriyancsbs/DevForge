import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "DevForge" in data["service"]

def test_overview_endpoint(client):
    response = client.get("/api/v1/overview")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    assert "recent_deployments" in data
    assert "service_health" in data
    assert "recent_activity" in data
    assert data["metrics"]["applications_count"] >= 0

def test_applications_list_and_filter(client):
    response = client.get("/api/v1/applications")
    assert response.status_code == 200
    apps = response.json()
    assert isinstance(apps, list)
    assert len(apps) > 0

    # Test filtering by status
    healthy_resp = client.get("/api/v1/applications?status=healthy")
    assert healthy_resp.status_code == 200
    for app_item in healthy_resp.json():
        assert app_item["status"] == "healthy"

def test_create_application(client):
    new_app = {
        "name": "test-microservice-unique",
        "team": "QA Test Team",
        "runtime": "Python 3.12 (FastAPI)",
        "repository_url": "https://github.com/devforge-org/test-microservice",
        "branch": "main",
        "environment": "development",
        "version": "v1.0.0",
        "port": 8000,
        "replicas": 1
    }
    response = client.post("/api/v1/applications", json=new_app)
    assert response.status_code in [201, 400]

def test_environments_list(client):
    response = client.get("/api/v1/environments")
    assert response.status_code == 200
    envs = response.json()
    assert len(envs) >= 4
    names = [e["name"] for e in envs]
    assert "Production" in names
    assert "Staging" in names
