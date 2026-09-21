import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.security import create_access_token, hash_password
from app.db.session import SessionLocal
from app.models.user import User
from app.models.application import Application
from app.models.template import Template
from app.models.activity import Activity
from app.models.provisioning_job import ProvisioningJob
from app.services.provisioning.template_registry import template_registry, CANONICAL_TEMPLATES
from app.services.provisioning.project_generator import project_generator
from app.services.provisioning.service import provisioning_service


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def auth_tokens(db_session: Session):
    roles = ["ADMIN", "OPERATOR", "DEVELOPER", "VIEWER"]
    tokens = {}
    for role in roles:
        username = f"p13_{role.lower()}"
        user = db_session.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                username=username,
                email=f"{username}@devforge.internal",
                hashed_password=hash_password("DevForgeSecret123!"),
                role=role,
                is_active=True
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
        tokens[role] = create_access_token(
            subject=str(user.id),
            username=user.username,
            role=user.role
        )
    return tokens


@pytest.fixture
def test_client():
    with TestClient(app) as c:
        yield c


class TestTemplateRegistry:
    def test_template_registry_discovery(self, db_session):
        templates = template_registry.list_templates(db=db_session)
        assert len(templates) >= 3

        template_ids = [t["template_id"] for t in templates]
        assert "python-fastapi" in template_ids
        assert "node-express" in template_ids
        assert "go-gin" in template_ids

        for tpl in templates:
            assert "name" in tpl
            assert "runtime" in tpl
            assert "framework" in tpl
            assert "version" in tpl
            assert "supported_environments" in tpl
            assert "generated_project_structure" in tpl
            assert "required_variables" in tpl
            assert "is_enabled" in tpl

    def test_template_version_resolution(self, db_session):
        meta_default = template_registry.get_template_metadata("python-fastapi", db=db_session)
        assert meta_default["version"] == "1.0.0"

        meta_explicit = template_registry.get_template_metadata("python-fastapi", version="1.0.0", db=db_session)
        assert meta_explicit["version"] == "1.0.0"

        with pytest.raises(ValueError, match="not found"):
            template_registry.get_template_metadata("python-fastapi", version="99.9.9", db=db_session)

    def test_variable_validation_success(self, db_session):
        validated = template_registry.validate_variables(
            template_id="python-fastapi",
            version="1.0.0",
            variables={
                "application_name": "valid-payment-api",
                "environment": "production",
                "port": 8000,
                "description": "Valid payments gateway"
            },
            db=db_session
        )
        assert validated["application_name"] == "valid-payment-api"
        assert validated["port"] == 8000
        assert validated["environment"] == "production"

    def test_variable_validation_rfc1123_enforcement(self, db_session):
        # Must reject uppercase
        with pytest.raises(ValueError, match="RFC 1123"):
            template_registry.validate_variables(
                "python-fastapi", "1.0.0",
                {"application_name": "Invalid_Upper"}, db=db_session
            )

        # Must reject leading hyphen
        with pytest.raises(ValueError, match="RFC 1123"):
            template_registry.validate_variables(
                "python-fastapi", "1.0.0",
                {"application_name": "-lead-hyphen"}, db=db_session
            )

        # Must reject trailing hyphen
        with pytest.raises(ValueError, match="RFC 1123"):
            template_registry.validate_variables(
                "python-fastapi", "1.0.0",
                {"application_name": "trail-hyphen-"}, db=db_session
            )

    def test_variable_validation_path_traversal_protection(self, db_session):
        with pytest.raises(ValueError, match="traversal"):
            template_registry.validate_variables(
                "python-fastapi", "1.0.0",
                {"application_name": "app/../../etc/passwd"}, db=db_session
            )

        with pytest.raises(ValueError, match="traversal"):
            template_registry.validate_variables(
                "python-fastapi", "1.0.0",
                {"application_name": "..safeapp"}, db=db_session
            )

    def test_variable_validation_injection_protection(self, db_session):
        with pytest.raises(ValueError, match="traversal|character|forbidden|RFC 1123"):
            template_registry.validate_variables(
                "python-fastapi", "1.0.0",
                {"application_name": "safeapp; rm -rf /"}, db=db_session
            )

        with pytest.raises(ValueError, match="traversal|character|forbidden|RFC 1123"):
            template_registry.validate_variables(
                "python-fastapi", "1.0.0",
                {"application_name": "app$(whoami)"}, db=db_session
            )

    def test_variable_validation_port_boundaries(self, db_session):
        with pytest.raises(ValueError, match="port"):
            template_registry.validate_variables(
                "python-fastapi", "1.0.0",
                {"application_name": "my-service", "port": 0}, db=db_session
            )

        with pytest.raises(ValueError, match="port"):
            template_registry.validate_variables(
                "python-fastapi", "1.0.0",
                {"application_name": "my-service", "port": 70000}, db=db_session
            )

    def test_invalid_template_rejection(self, db_session):
        with pytest.raises(ValueError, match="Unsupported template"):
            template_registry.get_template_metadata("non-existent-template", db=db_session)

    def test_disabled_template_rejection(self, db_session):
        # Create a disabled template in DB
        dis_tpl = db_session.query(Template).filter(
            Template.template_id == "test-disabled",
            Template.version == "1.0.0"
        ).first()
        if not dis_tpl:
            dis_tpl = Template(
                template_id="test-disabled",
                name="Disabled Template",
                description="Template for test",
                runtime="python",
                framework="Flask",
                version="1.0.0",
                is_enabled=False
            )
            db_session.add(dis_tpl)
            db_session.commit()
        else:
            dis_tpl.is_enabled = False
            db_session.commit()

        with pytest.raises(ValueError, match="disabled"):
            template_registry.get_template_metadata("test-disabled", version="1.0.0", db=db_session)


class TestProjectGenerator:
    def test_unresolved_variable_detection(self, tmp_path):
        dummy_dir = tmp_path / "dummy_project"
        dummy_dir.mkdir()
        dummy_manifest = """apiVersion: devforge/v1
kind: ApplicationManifest
metadata:
  name: dummy
  version: "1.0.0"
spec:
  runtime: python
  template: python-fastapi
  port: 8000
"""
        (dummy_dir / "devforge.yaml").write_text(dummy_manifest)
        (dummy_dir / "Dockerfile").write_text("FROM python:3.12-slim")
        (dummy_dir / "requirements.txt").write_text("fastapi>=0.100.0")
        (dummy_dir / "main.py").write_text("PORT = {{UNRESOLVED_PORT}}\nAPP = '{{app_name}}'")

        with pytest.raises(ValueError, match="Unresolved template variables"):
            project_generator.validate_generated_project(
                project_dir=str(dummy_dir),
                application_name="dummy",
                template_id="python-fastapi"
            )

    @pytest.mark.parametrize("tpl_id,expected_files", [
        ("python-fastapi", ["main.py", "requirements.txt", "Dockerfile", ".dockerignore", "README.md", "devforge.yaml", ".github/workflows/ci.yml"]),
        ("node-express", ["server.js", "package.json", "Dockerfile", ".dockerignore", "README.md", "devforge.yaml", ".github/workflows/ci.yml", "test.js"]),
        ("go-gin", ["main.go", "go.mod", "Dockerfile", ".dockerignore", "README.md", "devforge.yaml", ".github/workflows/ci.yml", "main_test.go"])
    ])
    def test_project_generation_all_templates(self, tpl_id, expected_files, tmp_path):
        app_name = f"gen-{tpl_id.replace('-', '')}"
        target_dir = tmp_path / app_name

        result = project_generator.generate_project(
            template_id=tpl_id,
            target_dir=str(target_dir),
            application_name=app_name,
            team="Platform Engineering",
            environment="production",
            database_type="postgresql",
            deployment_strategy="rolling",
            port=8080,
            replicas=2
        )

        assert result.app_name == app_name
        assert target_dir.exists()

        # Check all expected files exist
        for f in expected_files:
            file_path = target_dir / f
            assert file_path.exists(), f"Expected file {f} missing from generated project {tpl_id}"

        # Verify no unresolved tokens remain in any file
        validation_res = project_generator.validate_generated_project(
            project_dir=str(target_dir),
            application_name=app_name,
            template_id=tpl_id
        )
        assert validation_res["valid"] is True


class TestTemplateAPIAndRBAC:
    def test_viewer_can_list_and_get_templates(self, test_client, auth_tokens):
        headers = {"Authorization": f"Bearer {auth_tokens['VIEWER']}"}

        res = test_client.get("/api/v1/templates", headers=headers)
        assert res.status_code == 200
        tpls = res.json()
        assert len(tpls) >= 3

        res_single = test_client.get("/api/v1/templates/python-fastapi", headers=headers)
        assert res_single.status_code == 200
        assert res_single.json()["template_id"] == "python-fastapi"

    def test_viewer_cannot_mutate_templates(self, test_client, auth_tokens):
        headers = {"Authorization": f"Bearer {auth_tokens['VIEWER']}"}

        # Try create template
        res_create = test_client.post(
            "/api/v1/templates",
            headers=headers,
            json={
                "template_id": "malicious-template",
                "name": "Malicious",
                "runtime": "python",
                "framework": "fastapi"
            }
        )
        assert res_create.status_code == 403

    def test_developer_can_validate_and_preview(self, test_client, auth_tokens):
        headers = {"Authorization": f"Bearer {auth_tokens['DEVELOPER']}"}

        res_val = test_client.post(
            "/api/v1/templates/node-express/validate",
            headers=headers,
            json={
                "application_name": "dev-order-service",
                "environment": "staging",
                "port": 3000
            }
        )
        assert res_val.status_code == 200
        assert res_val.json()["valid"] is True

        res_preview = test_client.post(
            "/api/v1/templates/node-express/preview",
            headers=headers,
            json={
                "application_name": "dev-order-service",
                "environment": "staging",
                "port": 3000
            }
        )
        assert res_preview.status_code == 200
        data = res_preview.json()
        assert data["application_name"] == "dev-order-service"
        assert "server.js" in data["files"]
        assert len(data["key_generated_components"]) > 0

    def test_admin_can_create_and_manage_templates(self, test_client, auth_tokens):
        headers = {"Authorization": f"Bearer {auth_tokens['ADMIN']}"}

        new_id = f"custom-admin-api-{os.getpid()}"
        res_create = test_client.post(
            "/api/v1/templates",
            headers=headers,
            json={
                "template_id": new_id,
                "name": "Custom Admin API",
                "description": "Internal administrative microservice template",
                "runtime": "python",
                "framework": "FastAPI",
                "version": "1.0.0",
                "supported_environments": ["development", "production"],
                "generated_project_structure": ["main.py", "Dockerfile"],
                "required_variables": ["application_name", "port"],
                "is_enabled": True
            }
        )
        assert res_create.status_code == 201
        created = res_create.json()
        assert created["template_id"] == new_id

        # Update / toggle enabled
        res_patch = test_client.patch(
            f"/api/v1/templates/{new_id}?version=1.0.0",
            headers=headers,
            json={"is_enabled": False}
        )
        assert res_patch.status_code == 200
        assert res_patch.json()["is_enabled"] is False


class TestProvisioningServicePhase13:
    def test_application_creation_stores_template_metadata_and_audits(self, test_client, auth_tokens, db_session):
        app_name = f"audit-app-{os.getpid()}"
        # Ensure clean state
        existing = db_session.query(Application).filter(Application.name == app_name).first()
        if existing:
            db_session.delete(existing)
            db_session.commit()

        headers = {"Authorization": f"Bearer {auth_tokens['DEVELOPER']}"}
        res = test_client.post(
            "/api/v1/applications?sync=true",
            headers=headers,
            json={
                "name": app_name,
                "team": "Platform Engineering",
                "environment": "production",
                "runtime": "node",
                "template": "node-express",
                "template_id": "node-express",
                "template_version": "1.0.0",
                "repository_url": f"https://github.com/sripriyancsbs/{app_name}",
                "branch": "main",
                "port": 3000,
                "replicas": 2,
                "database_type": "none",
                "deployment_strategy": "rolling"
            }
        )
        assert res.status_code == 201

        app = db_session.query(Application).filter(Application.name == app_name).first()
        assert app is not None
        assert app.template_id == "node-express"
        assert app.template_version == "1.0.0"

        # Check job template version
        job = db_session.query(ProvisioningJob).filter(ProvisioningJob.application_id == app.id).first()
        assert job is not None
        assert job.template_version == "1.0.0"

        # Check audit activities logged
        audits = (
            db_session.query(Activity)
            .filter(Activity.target.like(f"%{app_name}%"))
            .order_by(Activity.created_at.desc())
            .all()
        )
        assert len(audits) >= 1
