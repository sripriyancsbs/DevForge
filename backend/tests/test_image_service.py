import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models.application import Application
from app.models.container_image import ContainerImage
from app.services.image.image_service import image_service
from app.services.ci.workflow_generator import workflow_generator


@pytest.fixture
def client():
    return TestClient(app)


def test_get_image_repository_canonical_naming():
    """Verify canonical lowercase repository naming."""
    repo = image_service.get_image_repository("SriPriyaNCSBS", "Inventory-API")
    assert repo == "ghcr.io/sripriyancsbs/inventory-api"

    repo_default = image_service.get_image_repository(None, "MyService")
    assert repo_default.startswith("ghcr.io/")
    assert "myservice" in repo_default


def test_generate_tag_deterministic():
    """Verify tag generation for commit sha vs latest."""
    tag1 = image_service.generate_tag("5e0729a397754b2383c31828cb0df3e3e00fcda9")
    assert tag1 == "sha-5e0729a"

    tag_short = image_service.generate_tag("1234567")
    assert tag_short == "sha-1234567"

    tag_empty = image_service.generate_tag(None)
    assert tag_empty == "latest"


def test_record_initial_image():
    """Verify initial container image record creation in PostgreSQL."""
    db: Session = SessionLocal()
    try:
        app_name = f"test-img-{uuid.uuid4().hex[:6]}"
        app_record = Application(
            name=app_name,
            slug=app_name,
            team="Platform Engineering",
            runtime="Python 3.12 (FastAPI)",
            repository_url=f"https://github.com/sripriyancsbs/{app_name}",
            repository_owner="sripriyancsbs",
            repository_name=app_name,
            environment="production",
            port=8000
        )
        db.add(app_record)
        db.commit()
        db.refresh(app_record)

        img = image_service.record_initial_image(app_record, "abc1234567890", db)
        assert img.id is not None
        assert img.registry == "ghcr.io"
        assert img.image_repository == f"ghcr.io/sripriyancsbs/{app_name}"
        assert img.image_tag == "sha-abc1234"
        assert img.status == "PENDING"
        assert app_record.image_status == "PENDING"
        assert app_record.image_repository == f"ghcr.io/sripriyancsbs/{app_name}"
    finally:
        db.close()


def test_get_application_images_endpoint(client):
    """Test GET /api/v1/applications/{id}/images returns images list."""
    app_name = f"test-api-img-{uuid.uuid4().hex[:6]}"
    res = client.post("/api/v1/applications?sync=true", json={
        "name": app_name,
        "team": "Platform",
        "template": "python-fastapi",
        "environment": "production",
        "port": 8000
    })
    assert res.status_code == 201
    app_id = res.json()["application"]["id"]

    images_res = client.get(f"/api/v1/applications/{app_id}/images")
    assert images_res.status_code == 200
    data = images_res.json()
    assert "images" in data
    assert "total" in data
    assert data["total"] >= 1
    assert data["images"][0]["registry"] == "ghcr.io"
    assert app_name in data["images"][0]["repository"]


def test_get_latest_application_image_endpoint(client):
    """Test GET /api/v1/applications/{id}/images/latest."""
    app_name = f"test-latest-img-{uuid.uuid4().hex[:6]}"
    res = client.post("/api/v1/applications?sync=true", json={
        "name": app_name,
        "team": "Platform",
        "template": "node-service",
        "environment": "staging",
        "port": 3000
    })
    assert res.status_code == 201
    app_id = res.json()["application"]["id"]

    latest_res = client.get(f"/api/v1/applications/{app_id}/images/latest")
    assert latest_res.status_code == 200
    data = latest_res.json()
    assert data["registry"] == "ghcr.io"
    assert app_name in data["repository"]
    assert "tag" in data
    assert data["status"] in ("PENDING", "BUILDING", "PUSHING", "READY")


def test_sync_application_image_endpoint(client):
    """Test POST /api/v1/applications/{id}/images/sync."""
    app_name = f"test-sync-img-{uuid.uuid4().hex[:6]}"
    res = client.post("/api/v1/applications?sync=true", json={
        "name": app_name,
        "team": "Platform",
        "template": "go-microservice",
        "environment": "development",
        "port": 8080
    })
    assert res.status_code == 201
    app_id = res.json()["application"]["id"]

    sync_res = client.post(f"/api/v1/applications/{app_id}/images/sync")
    assert sync_res.status_code == 200
    data = sync_res.json()
    assert data["registry"] == "ghcr.io"
    assert app_name in data["repository"]


def test_image_endpoints_not_found(client):
    """Test 404 for invalid app id."""
    assert client.get("/api/v1/applications/999999/images").status_code == 404
    assert client.get("/api/v1/applications/999999/images/latest").status_code == 404
    assert client.post("/api/v1/applications/999999/images/sync").status_code == 404


def test_workflow_generator_all_templates_contain_ghcr_publishing():
    """Verify all templates generate valid GHCR login, build, tag and push steps."""
    for tpl in ["python-fastapi", "react-vite", "go-microservice", "node-service"]:
        wf = workflow_generator.generate_workflow_yaml(tpl, f"app-{tpl}")
        assert "packages: write" in wf
        assert "docker login ghcr.io" in wf
        assert "ghcr.io/${{ github.repository_owner }}/" in wf
        assert "docker push" in wf
        assert "sha-$SHORT_SHA" in wf
        assert "latest" in wf
