from datetime import datetime
from typing import List, Optional
import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.deployment import Deployment
from app.models.application import Application
from app.models.activity import Activity
from app.schemas.deployment import DeploymentResponse, DeploymentCreate

router = APIRouter()

@router.get("", response_model=List[DeploymentResponse])
def list_deployments(
    status: Optional[str] = None,
    environment: Optional[str] = None,
    application_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Deployment)

    if status and status.lower() != "all":
        query = query.filter(Deployment.status == status.lower())

    if environment and environment.lower() != "all":
        query = query.filter(Deployment.environment == environment.lower())

    if application_id:
        query = query.filter(Deployment.application_id == application_id)

    return query.order_by(Deployment.created_at.desc()).all()

@router.get("/{deployment_id}", response_model=DeploymentResponse)
def get_deployment(deployment_id: int, db: Session = Depends(get_db)):
    dep = db.query(Deployment).filter(Deployment.id == deployment_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return dep

@router.post("/trigger", response_model=DeploymentResponse)
def trigger_deployment(payload: DeploymentCreate, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == payload.application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    random_hex = ''.join(random.choices('0123456789abcdef', k=7))
    new_deployment = Deployment(
        application_id=app.id,
        application_name=app.name,
        version=payload.version,
        commit_hash=random_hex,
        commit_message=payload.commit_message or f"Release {payload.version}",
        environment=payload.environment,
        status="healthy",
        duration="48s",
        triggered_by="devforge:console",
        logs=f"[00:00:01] Triggered deployment for {app.name} -> {payload.environment}\n[00:00:14] CI Checks passed\n[00:00:26] Built image tag {payload.version}\n[00:00:48] Healthcheck status 200 OK."
    )
    db.add(new_deployment)

    # Update application version & last_deployment_at
    app.version = payload.version
    app.environment = payload.environment
    app.last_deployment_at = datetime.utcnow()

    # Log activity
    activity = Activity(
        actor="devforge:console",
        action="Deployment completed",
        target=app.name,
        target_type="application",
        status="completed",
        details=f"Deployed {app.name} {payload.version} to {payload.environment}"
    )
    db.add(activity)

    db.commit()
    db.refresh(new_deployment)
    return new_deployment
