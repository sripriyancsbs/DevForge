from datetime import datetime, timezone
from typing import List, Optional
import random
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.deployment import Deployment
from app.models.application import Application
from app.models.activity import Activity
from app.schemas.deployment import DeploymentResponse, DeploymentCreate
from app.schemas.application import ALLOWED_ENVIRONMENTS
from app.core.auth import require_role
from app.models.user import User
from app.core.rate_limit import rate_limit

router = APIRouter()

@router.get("", response_model=List[DeploymentResponse])
def list_deployments(
    status_filter: Optional[str] = Query(None, alias="status"),
    environment: Optional[str] = Query(None),
    application_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db)
):
    query = db.query(Deployment)

    if status_filter and status_filter.lower() != "all":
        query = query.filter(Deployment.status == status_filter.lower())

    if environment and environment.lower() != "all":
        query = query.filter(Deployment.environment == environment.lower())

    if application_id:
        query = query.filter(Deployment.application_id == application_id)

    return query.order_by(Deployment.created_at.desc()).all()

@router.get("/{deployment_id}", response_model=DeploymentResponse)
def get_deployment(deployment_id: int, db: Session = Depends(get_db)):
    dep = db.query(Deployment).filter(Deployment.id == deployment_id).first()
    if not dep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment with ID '{deployment_id}' not found."
        )
    return dep

@router.post("/trigger", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
def trigger_deployment(
    payload: DeploymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["DEVELOPER", "OPERATOR", "ADMIN"])),
    _limiter = Depends(rate_limit("deployments_trigger", max_requests=10, window_seconds=60))
):
    app = db.query(Application).filter(Application.id == payload.application_id).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot trigger deployment: Application with ID '{payload.application_id}' not found."
        )

    if payload.environment.lower() not in ALLOWED_ENVIRONMENTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid deployment target environment '{payload.environment}'. Allowed: {', '.join(sorted(ALLOWED_ENVIRONMENTS))}"
        )

    now = datetime.now(timezone.utc)
    random_hex = ''.join(random.choices('0123456789abcdef', k=7))
    new_deployment = Deployment(
        application_id=app.id,
        application_name=app.name,
        version=payload.version,
        commit_hash=random_hex,
        commit_message=payload.commit_message or f"Release {payload.version}",
        environment=payload.environment.lower(),
        status="healthy",
        duration="48s",
        triggered_by=current_user.username,
        logs=(
            f"[00:00:01] Triggered deployment for {app.name} -> {payload.environment}\n"
            f"[00:00:14] CI container lint and test checks passed\n"
            f"[00:00:26] Built multi-arch image tag {payload.version}\n"
            f"[00:00:48] Rolling update complete. Healthcheck status 200 OK."
        ),
        created_at=now
    )
    db.add(new_deployment)

    # Update application version & last_deployment_at
    app.version = payload.version
    app.environment = payload.environment.lower()
    app.last_deployment_at = now
    app.updated_at = now

    # Log activity
    activity = Activity(
        actor=current_user.username,
        action="Deployment completed",
        target=app.name,
        target_type="application",
        status="completed",
        details=f"Deployed {app.name} {payload.version} to {payload.environment}",
        created_at=now
    )
    db.add(activity)

    db.commit()
    db.refresh(new_deployment)
    return new_deployment
