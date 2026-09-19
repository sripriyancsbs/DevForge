import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.gitops_operation import GitOpsOperation
from app.models.gitops_application import GitOpsApplication
from app.schemas.gitops import (
    GitOpsEnableRequest,
    GitOpsSyncRequest,
    GitOpsRefreshRequest,
    GitOpsApplicationResponse,
    GitOpsOperationResponse,
    GitOpsClusterStatusResponse,
)
from app.services.argocd.argocd_client import argocd_client
from app.services.argocd.application_service import gitops_application_service
from app.services.argocd.sync_service import gitops_sync_service
from app.services.argocd.exceptions import (
    ArgoCDError,
    ArgoCDUnavailableError,
    ArgoCDApplicationNotFoundError
)

logger = logging.getLogger("devforge.api.gitops")
router = APIRouter(prefix="/gitops", tags=["gitops"])

@router.get("/cluster", response_model=GitOpsClusterStatusResponse)
def get_argocd_cluster_status():
    """Probe Argo CD availability, server version, and cluster status."""
    return argocd_client.get_cluster_status()

@router.get("/applications", response_model=List[GitOpsApplicationResponse])
def list_gitops_applications(db: Session = Depends(get_db)):
    """List all GitOps managed applications with live synchronization state."""
    return gitops_application_service.list_gitops_applications(db)

@router.post("/applications/{application_id}/enable", response_model=GitOpsApplicationResponse, status_code=status.HTTP_201_CREATED)
def enable_gitops_for_application(
    application_id: int,
    payload: GitOpsEnableRequest,
    db: Session = Depends(get_db)
):
    """
    Enable GitOps for an application:
    Generates Kustomize topologies, commits manifests, and creates Argo CD Application.
    """
    try:
        app_record = gitops_application_service.enable_gitops(
            application_id=application_id,
            db=db,
            git_repository=payload.git_repository,
            target_revision=payload.target_revision,
            environment=payload.environment,
            auto_sync=payload.auto_sync,
            self_heal=payload.self_heal,
            image_tag=payload.image_tag,
            replicas=payload.replicas,
        )
        data = gitops_application_service.get_gitops_application(application_id, db)
        return data
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to enable GitOps for application {application_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/applications/{application_id}", response_model=GitOpsApplicationResponse)
def get_gitops_application(application_id: int, db: Session = Depends(get_db)):
    """Retrieve GitOps metadata and live Argo CD status for an application."""
    data = gitops_application_service.get_gitops_application(application_id, db)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"GitOps not enabled for application {application_id}")
    return data

@router.post("/applications/{application_id}/sync", response_model=GitOpsOperationResponse)
def sync_gitops_application(
    application_id: int,
    payload: GitOpsSyncRequest = GitOpsSyncRequest(),
    db: Session = Depends(get_db)
):
    """
    Trigger synchronization of an Argo CD application:
    Queues operation for worker or executes synchronously.
    """
    gitops_app = db.query(GitOpsApplication).filter(GitOpsApplication.application_id == application_id).first()
    if not gitops_app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"GitOps not enabled for application {application_id}")

    op = gitops_sync_service.queue_operation(
        gitops_application_id=gitops_app.id,
        operation_type="SYNC",
        db=db,
        revision=payload.revision,
        details="Manual synchronization triggered from DevForge console",
    )

    if not payload.async_execution:
        op = gitops_sync_service.execute_operation(op.id, db)

    return {
        "id": op.id,
        "gitops_application_id": op.gitops_application_id,
        "operation_type": op.operation_type,
        "status": op.status,
        "revision": op.revision,
        "details": op.details,
        "error": op.error,
        "started_at": op.started_at.isoformat() if op.started_at else None,
        "completed_at": op.completed_at.isoformat() if op.completed_at else None,
        "created_at": op.created_at.isoformat(),
    }

@router.post("/applications/{application_id}/refresh", response_model=GitOpsApplicationResponse)
def refresh_gitops_application(
    application_id: int,
    payload: GitOpsRefreshRequest = GitOpsRefreshRequest(),
    db: Session = Depends(get_db)
):
    """
    Trigger hard refresh for an Argo CD application to detect live Git & cluster drift.
    """
    gitops_app = db.query(GitOpsApplication).filter(GitOpsApplication.application_id == application_id).first()
    if not gitops_app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"GitOps not enabled for application {application_id}")

    if payload.async_execution:
        gitops_sync_service.queue_operation(
            gitops_application_id=gitops_app.id,
            operation_type="REFRESH",
            db=db,
            details="Manual hard refresh triggered from DevForge console",
        )
    else:
        try:
            argocd_client.refresh_application(gitops_app.argocd_application_name)
        except Exception as e:
            logger.warning(f"Refresh failed on client: {e}")

    data = gitops_application_service.get_gitops_application(application_id, db)
    return data

@router.get("/applications/{application_id}/status")
def get_gitops_application_status(application_id: int, db: Session = Depends(get_db)):
    """Direct live status endpoint returning sync, health, and drift details."""
    data = gitops_application_service.get_gitops_application(application_id, db)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"GitOps not enabled for application {application_id}")
    return {
        "application_id": data["application_id"],
        "argocd_application_name": data["argocd_application_name"],
        "sync_status": data["sync_status"],
        "health_status": data["health_status"],
        "drift_count": data["drift_count"],
        "drifted_resources": data["drifted_resources"],
        "last_synced_at": data["last_synced_at"],
    }

@router.get("/operations/{operation_id}", response_model=GitOpsOperationResponse)
def get_gitops_operation(operation_id: int, db: Session = Depends(get_db)):
    """Retrieve details and progress status of an asynchronous GitOps operation."""
    op = db.query(GitOpsOperation).filter(GitOpsOperation.id == operation_id).first()
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Operation #{operation_id} not found")
    return {
        "id": op.id,
        "gitops_application_id": op.gitops_application_id,
        "operation_type": op.operation_type,
        "status": op.status,
        "revision": op.revision,
        "details": op.details,
        "error": op.error,
        "started_at": op.started_at.isoformat() if op.started_at else None,
        "completed_at": op.completed_at.isoformat() if op.completed_at else None,
        "created_at": op.created_at.isoformat(),
    }
