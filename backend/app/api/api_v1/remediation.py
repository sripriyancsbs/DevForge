import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.session import get_db
from app.models.application import Application
from app.models.remediation import RemediationPolicy, RemediationEvent, RemediationExecution
from app.schemas.remediation import (
    RemediationPolicyCreate,
    RemediationPolicyResponse,
    RemediationEventCreate,
    RemediationEventResponse,
    RemediationExecutionResponse,
    ApplicationRemediationOverview,
)
from app.services.remediation import remediation_engine, policy_service
from app.core.auth import require_role
from app.models.user import User
from app.core.rate_limit import rate_limit

logger = logging.getLogger("devforge.api.remediation")

router = APIRouter()


# -----------------------------------------------------------------------------
# Remediation Events Endpoints
# -----------------------------------------------------------------------------

@router.get("/events", response_model=List[RemediationEventResponse])
def list_remediation_events(
    application_id: Optional[int] = Query(None, description="Filter by application ID"),
    environment_id: Optional[str] = Query(None, description="Filter by environment"),
    status: Optional[str] = Query(None, description="Filter by status (e.g. DETECTED, RECOVERED, ESCALATED)"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Query recent remediation events across applications and environments."""
    query = db.query(RemediationEvent)
    if application_id is not None:
        query = query.filter(RemediationEvent.application_id == application_id)
    if environment_id:
        query = query.filter(RemediationEvent.environment_id == environment_id)
    if status:
        query = query.filter(RemediationEvent.status == status)

    events = query.order_by(desc(RemediationEvent.created_at)).limit(limit).all()
    return events


@router.get("/events/{event_id}", response_model=RemediationEventResponse)
def get_remediation_event(
    event_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve details and execution attempts for a single remediation event."""
    event = db.query(RemediationEvent).filter(RemediationEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail=f"Remediation event #{event_id} not found.")
    return event


@router.post("/events", response_model=RemediationEventResponse, status_code=status.HTTP_201_CREATED)
def create_remediation_event(
    payload: RemediationEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["OPERATOR", "ADMIN"])),
    _limiter = Depends(rate_limit("remediation_create", max_requests=10, window_seconds=60))
):
    """Manually report or ingest a health failure event."""
    app = db.query(Application).filter(Application.id == payload.application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail=f"Application #{payload.application_id} not found.")

    event = remediation_engine.create_event(
        application_id=payload.application_id,
        environment_id=payload.environment_id,
        event_type=payload.event_type,
        source=payload.source,
        severity=payload.severity,
        details=payload.details or "Manually submitted health event",
        db=db,
    )
    return event


@router.post("/events/{event_id}/retry", response_model=RemediationEventResponse)
def retry_remediation_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["OPERATOR", "ADMIN"])),
):
    """Allow an operator to retry a failed or escalated remediation."""
    try:
        event = remediation_engine.retry_event(event_id, db)
        return event
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/events/{event_id}/approve", response_model=RemediationEventResponse)
def approve_remediation_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["OPERATOR", "ADMIN"])),
    _limiter = Depends(rate_limit("remediation_approve", max_requests=10, window_seconds=60))
):
    """Allow an operator to approve a gated remediation action (e.g. Production rollout)."""
    try:
        event = remediation_engine.approve_event(event_id, db)
        return event
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/events/{event_id}/cancel", response_model=RemediationEventResponse)
def cancel_remediation_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN"])),
):
    """Allow an administrator to cancel an open remediation event."""
    try:
        event = remediation_engine.cancel_event(event_id, db)
        return event
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/scan", status_code=status.HTTP_200_OK)
def trigger_health_scan(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["OPERATOR", "ADMIN"])),
    _limiter = Depends(rate_limit("remediation_scan", max_requests=10, window_seconds=60))
):
    """Trigger an immediate real infrastructure health scan across all applications."""
    detected = remediation_engine.scan_applications_health(db)
    return {
        "status": "success",
        "scanned_at": remediation_engine.record_activity.__defaults__,
        "events_detected_count": len(detected),
        "events": [{"id": e.id, "type": e.event_type, "app_id": e.application_id} for e in detected],
    }


# -----------------------------------------------------------------------------
# Remediation Policies Endpoints
# -----------------------------------------------------------------------------

@router.get("/policies", response_model=List[RemediationPolicyResponse])
def list_policies(
    db: Session = Depends(get_db),
):
    """List all configured remediation policies."""
    return policy_service.list_policies(db)


@router.post("/policies", response_model=RemediationPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: RemediationPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN"])),
):
    """Create a new remediation policy from the predefined allowlist."""
    if payload.action not in policy_service.ALLOWED_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Action '{payload.action}' invalid. Allowed: {list(policy_service.ALLOWED_ACTIONS)}"
        )

    existing = db.query(RemediationPolicy).filter(RemediationPolicy.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Policy with name '{payload.name}' already exists.")

    policy = RemediationPolicy(
        name=payload.name,
        event_type=payload.event_type,
        environment=payload.environment.lower(),
        action=payload.action,
        enabled=payload.enabled,
        max_attempts=payload.max_attempts,
        cooldown_seconds=payload.cooldown_seconds,
        requires_approval=payload.requires_approval,
        description=payload.description,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


# -----------------------------------------------------------------------------
# Application-Scoped Remediation Endpoints
# -----------------------------------------------------------------------------

@router.get("/applications/{application_id}/overview", response_model=ApplicationRemediationOverview)
@router.get("/applications/{application_id}/remediation", response_model=ApplicationRemediationOverview)
def get_application_remediation_overview(
    application_id: int,
    db: Session = Depends(get_db),
):
    """Get full remediation dashboard data scoped to a specific application."""
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail=f"Application #{application_id} not found.")

    events = (
        db.query(RemediationEvent)
        .filter(RemediationEvent.application_id == application_id)
        .order_by(desc(RemediationEvent.created_at))
        .limit(20)
        .all()
    )

    executions = (
        db.query(RemediationExecution)
        .filter(RemediationExecution.application_id == application_id)
        .order_by(desc(RemediationExecution.created_at))
        .all()
    )

    policies = policy_service.list_policies(db)

    active_count = sum(1 for e in events if e.status in ["DETECTED", "EVALUATING", "REMEDIATING", "VERIFYING"])
    successful_count = sum(1 for ex in executions if ex.status == "SUCCESS")
    failed_count = sum(1 for ex in executions if ex.status in ["FAILED", "CANCELLED"])
    last_exec = executions[0] if executions else None

    return ApplicationRemediationOverview(
        application_id=app.id,
        application_name=app.name,
        health_status=app.status or "healthy",
        active_events_count=active_count,
        total_remediations=len(executions),
        successful_remediations=successful_count,
        failed_remediations=failed_count,
        last_remediation=last_exec,
        events=events,
        policies=policies,
    )


@router.get("/applications/{application_id}/remediation/policies", response_model=List[RemediationPolicyResponse])
def get_application_remediation_policies(
    application_id: int,
    db: Session = Depends(get_db),
):
    """List all remediation policies applicable to this application."""
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail=f"Application #{application_id} not found.")
    return policy_service.list_policies(db)

