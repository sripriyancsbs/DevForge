from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class RemediationPolicyBase(BaseModel):
    name: str
    event_type: str
    environment: str = "all"
    action: str
    enabled: bool = True
    max_attempts: int = 3
    cooldown_seconds: int = 300
    requires_approval: bool = False
    description: Optional[str] = None


class RemediationPolicyCreate(RemediationPolicyBase):
    pass


class RemediationPolicyResponse(RemediationPolicyBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RemediationExecutionResponse(BaseModel):
    id: int
    event_id: int
    application_id: int
    environment_id: str
    policy_id: Optional[int] = None
    action: str
    status: str
    attempt: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RemediationEventCreate(BaseModel):
    application_id: int
    environment_id: str = "development"
    event_type: str
    source: str = "manual"
    severity: str = "MEDIUM"
    details: Optional[str] = None


class RemediationEventResponse(BaseModel):
    id: int
    application_id: int
    environment_id: str
    event_type: str
    source: str
    severity: str
    status: str
    detected_at: Optional[datetime] = None
    details: Optional[str] = None
    attempts: int = 0
    resolved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    executions: List[RemediationExecutionResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ApplicationRemediationOverview(BaseModel):
    application_id: int
    application_name: str
    health_status: str
    active_events_count: int
    total_remediations: int
    successful_remediations: int
    failed_remediations: int
    last_remediation: Optional[RemediationExecutionResponse] = None
    events: List[RemediationEventResponse] = []
    policies: List[RemediationPolicyResponse] = []
