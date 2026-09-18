import re
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.application import Application
from app.models.deployment import Deployment
from app.models.service_health import ServiceHealth
from app.models.activity import Activity
from app.schemas.application import ApplicationCreate, ApplicationUpdate, ApplicationResponse
from app.schemas.deployment import DeploymentResponse

router = APIRouter()

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text

@router.get("", response_model=List[ApplicationResponse])
def list_applications(
    search: Optional[str] = None,
    status: Optional[str] = None,
    environment: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Application)

    if search:
        search_fmt = f"%{search.lower()}%"
        query = query.filter(
            (Application.name.ilike(search_fmt)) |
            (Application.description.ilike(search_fmt)) |
            (Application.team.ilike(search_fmt)) |
            (Application.runtime.ilike(search_fmt))
        )

    if status and status.lower() != "all":
        query = query.filter(Application.status == status.lower())

    if environment and environment.lower() != "all":
        query = query.filter(Application.environment == environment.lower())

    return query.order_by(Application.created_at.desc()).all()

@router.get("/{app_id_or_slug}")
def get_application_details(app_id_or_slug: str, db: Session = Depends(get_db)):
    if app_id_or_slug.isdigit():
        app = db.query(Application).filter(Application.id == int(app_id_or_slug)).first()
    else:
        app = db.query(Application).filter(Application.slug == app_id_or_slug).first()

    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    deployments = db.query(Deployment).filter(Deployment.application_id == app.id).order_by(Deployment.created_at.desc()).limit(10).all()
    health = db.query(ServiceHealth).filter(ServiceHealth.service_name == app.name).first()

    return {
        "application": ApplicationResponse.model_validate(app),
        "deployments": [DeploymentResponse.model_validate(d) for d in deployments],
        "health": health
    }

@router.post("", response_model=ApplicationResponse, status_code=201)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    # Verify uniqueness
    existing_name = db.query(Application).filter(Application.name == payload.name).first()
    if existing_name:
        raise HTTPException(status_code=400, detail=f"Application '{payload.name}' already exists.")

    slug = payload.slug or slugify(payload.name)
    existing_slug = db.query(Application).filter(Application.slug == slug).first()
    if existing_slug:
        slug = f"{slug}-{int(datetime.utcnow().timestamp())}"

    new_app = Application(
        name=payload.name,
        slug=slug,
        description=payload.description or f"Self-serviced service provisioned via DevForge IDP.",
        team=payload.team or "Platform Engineering",
        runtime=payload.runtime,
        repository_url=payload.repository_url,
        branch=payload.branch or "main",
        environment=payload.environment or "development",
        version=payload.version or "v1.0.0",
        status="healthy",
        port=payload.port or 8000,
        replicas=payload.replicas or 2,
        last_deployment_at=datetime.utcnow()
    )
    db.add(new_app)
    db.flush()

    # Create initial deployment record
    init_deployment = Deployment(
        application_id=new_app.id,
        application_name=new_app.name,
        version=new_app.version,
        commit_hash="9a1f2b4",
        commit_message="feat: initial service scaffolding and container setup",
        environment=new_app.environment,
        status="healthy",
        duration="42s",
        triggered_by="devforge:creator",
        logs=f"[00:00:01] Provisioning service '{new_app.name}'\n[00:00:15] Synthesizing manifest from template runtime: {new_app.runtime}\n[00:00:25] Assigning internal service DNS {new_app.slug}.internal:{new_app.port}\n[00:00:42] Initial deployment healthy."
    )
    db.add(init_deployment)

    # Create ServiceHealth entry
    service_health = ServiceHealth(
        service_name=new_app.name,
        status="healthy",
        cpu_percent=5.2,
        memory_mb="120 MB",
        requests_per_sec=50,
        error_rate="0.00%",
        uptime="100.00%"
    )
    db.add(service_health)

    # Log Activity
    activity = Activity(
        actor="dev.engineer",
        action="Application created",
        target=new_app.name,
        target_type="application",
        status="completed",
        details=f"Created application {new_app.name} targeting {new_app.environment} with {new_app.runtime}"
    )
    db.add(activity)

    db.commit()
    db.refresh(new_app)
    return new_app

@router.delete("/{app_id}")
def delete_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    app_name = app.name
    db.delete(app)

    # Log activity
    db.add(Activity(
        actor="dev.engineer",
        action="Application deleted",
        target=app_name,
        target_type="application",
        status="completed",
        details=f"Terminated application {app_name}"
    ))

    db.commit()
    return {"message": f"Application '{app_name}' deleted successfully."}
