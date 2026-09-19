import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.ansible import (
    playbook_service,
    execution_service,
    AnsibleError,
    AnsiblePlaybookNotFoundError,
    AnsibleSecurityError,
)

logger = logging.getLogger("devforge.api.ansible")

router = APIRouter()


class CreateExecutionRequest(BaseModel):
    playbook_name: str = Field(..., description="Name of the approved playbook to execute")
    application_id: Optional[int] = Field(None, description="Optional target Application ID")
    environment_id: str = Field("development", description="Target environment (development, staging, production)")


class ExecutionResponse(BaseModel):
    id: int
    application_id: Optional[int]
    application_name: Optional[str]
    environment_id: str
    playbook_name: str
    status: str
    output: Optional[str]
    error_output: Optional[str]
    return_code: Optional[int]
    duration_seconds: Optional[float]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    updated_at: str


@router.get("/playbooks")
def list_playbooks():
    """List all approved Ansible playbooks and their metadata."""
    return playbook_service.list_playbooks()


@router.post("/executions", status_code=status.HTTP_201_CREATED)
def create_execution(
    request: CreateExecutionRequest,
    db: Session = Depends(get_db)
):
    """
    Queue an approved Ansible playbook execution for asynchronous worker processing.
    Validates that the playbook is on the allowlist and environment is supported.
    """
    try:
        execution = execution_service.create_execution(
            db=db,
            playbook_name=request.playbook_name,
            application_id=request.application_id,
            environment_id=request.environment_id
        )
        return execution.to_dict()
    except (AnsiblePlaybookNotFoundError, AnsibleSecurityError) as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except AnsibleError as app_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(app_err)
        )
    except Exception as e:
        logger.error(f"Error queueing Ansible execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue Ansible execution."
        )


@router.get("/executions")
def list_executions(
    application_id: Optional[int] = Query(None, description="Filter by Application ID"),
    environment_id: Optional[str] = Query(None, description="Filter by Environment"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by Status (PENDING, RUNNING, SUCCESS, FAILED)"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    db: Session = Depends(get_db)
):
    """Query Ansible execution history with optional filtering."""
    executions = execution_service.list_executions(
        db=db,
        application_id=application_id,
        environment_id=environment_id,
        status=status_filter,
        limit=limit
    )
    return [e.to_dict() for e in executions]


@router.get("/executions/{execution_id}")
def get_execution_detail(
    execution_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve detailed status, terminal output, and return code for an execution."""
    try:
        execution = execution_service.get_execution(execution_id, db)
        return execution.to_dict()
    except AnsibleError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ansible execution #{execution_id} not found."
        )


@router.post("/executions/{execution_id}/retry")
def retry_execution(
    execution_id: int,
    db: Session = Depends(get_db)
):
    """Retry a failed or completed Ansible execution by re-queuing it as PENDING."""
    try:
        execution = execution_service.retry_execution(execution_id, db)
        return execution.to_dict()
    except AnsibleError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ansible execution #{execution_id} not found."
        )
