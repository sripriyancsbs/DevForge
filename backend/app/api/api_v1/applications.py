import logging
import re
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.application import Application
from app.models.deployment import Deployment
from app.models.service_health import ServiceHealth
from app.models.activity import Activity
from app.models.provisioning_job import ProvisioningJob
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
    ApplicationProvisioningResponse,
    TEMPLATE_DEFAULTS
)
from app.schemas.deployment import DeploymentResponse
from app.schemas.service_health import ServiceHealthResponse
from app.services.provisioning.template_service import template_service
from app.services.provisioning.project_generator import project_generator
from app.services.provisioning.service import provisioning_service

logger = logging.getLogger("devforge.api.applications")
router = APIRouter()

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text

@router.get("", response_model=List[ApplicationResponse])
def list_applications(
    search: Optional[str] = Query(None, max_length=100),
    status_filter: Optional[str] = Query(None, alias="status", max_length=30),
    environment: Optional[str] = Query(None, max_length=50),
    db: Session = Depends(get_db)
):
    query = db.query(Application)

    if search:
        search_fmt = f"%{search.lower()}%"
        query = query.filter(
            (Application.name.ilike(search_fmt)) |
            (Application.description.ilike(search_fmt)) |
            (Application.team.ilike(search_fmt)) |
            (Application.runtime.ilike(search_fmt)) |
            (Application.slug.ilike(search_fmt))
        )

    if status_filter and status_filter.lower() != "all":
        query = query.filter(Application.status == status_filter.lower())

    if environment and environment.lower() != "all":
        query = query.filter(Application.environment == environment.lower())

    return query.order_by(Application.created_at.desc()).all()


@router.get("/{app_id_or_slug}")
def get_application_details(app_id_or_slug: str, db: Session = Depends(get_db)):
    if app_id_or_slug.isdigit():
        app = db.query(Application).filter(Application.id == int(app_id_or_slug)).first()
    else:
        app = db.query(Application).filter(Application.slug == app_id_or_slug.lower()).first()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{app_id_or_slug}' not found."
        )

    deployments = (
        db.query(Deployment)
        .filter(Deployment.application_id == app.id)
        .order_by(Deployment.created_at.desc())
        .limit(20)
        .all()
    )
    health = db.query(ServiceHealth).filter(
        (ServiceHealth.application_id == app.id) | (ServiceHealth.service_name == app.name)
    ).first()

    return {
        "application": ApplicationResponse.model_validate(app),
        "deployments": [DeploymentResponse.model_validate(d) for d in deployments],
        "health": ServiceHealthResponse.model_validate(health) if health else None
    }


@router.get("/{app_id_or_slug}/manifest")
def get_application_manifest(app_id_or_slug: str, db: Session = Depends(get_db)):
    """Fetch the generated devforge.yaml manifest for an application."""
    if app_id_or_slug.isdigit():
        app = db.query(Application).filter(Application.id == int(app_id_or_slug)).first()
    else:
        app = db.query(Application).filter(Application.slug == app_id_or_slug.lower()).first()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{app_id_or_slug}' not found."
        )

    if not app.manifest_yaml:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No devforge.yaml manifest recorded for application '{app.name}'."
        )

    return Response(content=app.manifest_yaml, media_type="application/x-yaml")


@router.post("", response_model=ApplicationProvisioningResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate,
    sync: bool = Query(False, description="Execute synchronously (useful for automated testing)"),
    db: Session = Depends(get_db)
):
    """
    DevForge Provisioning Execution Model:
    1. Validate request (name uniqueness, slug uniqueness, template validation, runtime compatibility)
    2. Register application record in PostgreSQL with status='pending', provisioning_status='PENDING'
    3. Create persistent ProvisioningJob record in PostgreSQL
    4. Commit database transaction immediately
    5. Return 201 immediately with job_id and PENDING status.
       The background Provisioning Worker executes the job asynchronously.
       (If sync=True, executes provisioning job synchronously).
    """
    # 1. Uniqueness check on name in database
    existing_name = db.query(Application).filter(Application.name == payload.name).first()
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Application with name '{payload.name}' already exists in database."
        )

    slug = slugify(payload.name)
    existing_slug = db.query(Application).filter(Application.slug == slug).first()
    if existing_slug:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Application with slug '{slug}' already exists."
        )

    # 2. Resolve template and defaults
    template_id = payload.template or "python-fastapi"
    try:
        template_service.validate_template(template_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid or incomplete template '{template_id}': {str(e)}"
        )

    defaults = TEMPLATE_DEFAULTS.get(template_id, TEMPLATE_DEFAULTS["python-fastapi"])
    runtime = payload.runtime or defaults["runtime_display"]
    try:
        template_service.validate_runtime_and_template(runtime, template_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Incompatible runtime: {str(e)}"
        )

    port = payload.port or defaults["port"]
    repo_owner = settings.GITHUB_OWNER or "sripriyancsbs"
    repo_name = payload.name
    repo_url = payload.repository_url or f"https://github.com/{repo_owner}/{repo_name}"
    now = datetime.now(timezone.utc)

    # 3. Create Application record in PostgreSQL
    new_app = Application(
        name=payload.name,
        slug=slug,
        description=payload.description or f"Self-serviced service provisioned via DevForge IDP.",
        team=payload.team or "Platform Engineering",
        runtime=runtime,
        template=template_id,
        repository_url=repo_url,
        repository_owner=repo_owner,
        repository_name=repo_name,
        repository_default_branch="main",
        branch=payload.branch or "main",
        environment=payload.environment,
        version=payload.version,
        status="pending",
        port=port,
        replicas=payload.replicas,
        database_type=payload.database_type,
        deployment_strategy=payload.deployment_strategy,
        provisioning_status="PENDING",
        provisioning_error=None,
        generated_path=None,
        manifest_yaml=None,
        last_deployment_at=now,
        created_at=now,
        updated_at=now
    )
    db.add(new_app)
    db.commit()
    db.refresh(new_app)

    # 4. Create persistent Provisioning Job in PostgreSQL
    job = provisioning_service.create_job(db, new_app, payload)

    # 5. Record Activity event
    db.add(Activity(
        actor="platform.user",
        action="Application creation requested",
        target=payload.name,
        target_type="application",
        status="completed",
        details=f"Provisioning job #{job.id} queued using template '{template_id}' with database '{payload.database_type}'",
        created_at=now
    ))
    db.commit()

    # 6. If sync mode requested, execute job immediately
    if sync:
        job = provisioning_service.execute_job(job.id, db)
        db.refresh(new_app)

    return ApplicationProvisioningResponse(
        application=ApplicationResponse.model_validate(new_app),
        provisioning_status=new_app.provisioning_status,
        job_id=job.id,
        generated_path=new_app.generated_path,
        manifest=new_app.manifest_yaml,
        files_generated=[],
        message=(
            f"Application '{new_app.name}' provisioned successfully from template '{template_id}'."
            if new_app.provisioning_status == "READY"
            else f"Application '{new_app.name}' provisioning job #{job.id} queued successfully."
        )
    )


@router.delete("/{app_id}", status_code=status.HTTP_200_OK)
def delete_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID '{app_id}' not found."
        )

    app_name = app.name
    db.delete(app)

    # Log activity
    db.add(Activity(
        actor="platform.user",
        action="Application deleted",
        target=app_name,
        target_type="application",
        status="completed",
        details=f"Terminated application {app_name} and pruned child deployments",
        created_at=datetime.now(timezone.utc)
    ))

    db.commit()
    return {"message": f"Application '{app_name}' deleted successfully."}


@router.post("/{application_id}/provision", response_model=ApplicationProvisioningResponse, status_code=status.HTTP_200_OK)
def trigger_application_provision(
    application_id: int,
    sync: bool = Query(False, description="Execute synchronously (useful for automated testing)"),
    db: Session = Depends(get_db)
):
    """
    Safely trigger or re-trigger provisioning for an application.
    Reuses existing active jobs to avoid duplicate provisioning jobs or duplicate repositories.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application with ID '{application_id}' not found."
        )

    # Check for active job (PENDING, PROVISIONING, RETRY)
    active_job = (
        db.query(ProvisioningJob)
        .filter(
            ProvisioningJob.application_id == app.id,
            ProvisioningJob.status.in_(["PENDING", "PROVISIONING", "RETRY"])
        )
        .order_by(ProvisioningJob.created_at.desc())
        .first()
    )

    if active_job:
        if sync:
            active_job = provisioning_service.execute_job(active_job.id, db)
            db.refresh(app)
        return ApplicationProvisioningResponse(
            application=ApplicationResponse.model_validate(app),
            provisioning_status=app.provisioning_status,
            job_id=active_job.id,
            generated_path=app.generated_path,
            manifest=app.manifest_yaml,
            files_generated=[],
            message=f"Application '{app.name}' has active provisioning job #{active_job.id} ({active_job.status})."
        )

    # If the application has a previous job, retry it
    last_job = (
        db.query(ProvisioningJob)
        .filter(ProvisioningJob.application_id == app.id)
        .order_by(ProvisioningJob.created_at.desc())
        .first()
    )

    if last_job:
        job = provisioning_service.retry_job(last_job.id, db)
    else:
        fake_create = ApplicationCreate(
            name=app.name,
            description=app.description,
            team=app.team,
            runtime=app.runtime,
            template=app.template,
            environment=app.environment,
            database_type=app.database_type,
            deployment_strategy=app.deployment_strategy,
            repository_url=app.repository_url,
            branch=app.branch,
            version=app.version,
            port=app.port,
            replicas=app.replicas
        )
        job = provisioning_service.create_job(db, app, fake_create)

    if sync:
        job = provisioning_service.execute_job(job.id, db)
        db.refresh(app)

    return ApplicationProvisioningResponse(
        application=ApplicationResponse.model_validate(app),
        provisioning_status=app.provisioning_status,
        job_id=job.id,
        generated_path=app.generated_path,
        manifest=app.manifest_yaml,
        files_generated=[],
        message=f"Provisioning triggered for application '{app.name}' (job #{job.id})."
    )

