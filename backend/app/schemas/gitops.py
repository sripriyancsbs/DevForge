from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class GitOpsEnableRequest(BaseModel):
    git_repository: Optional[str] = Field(None, description="GitOps manifest repository URL")
    target_revision: str = Field("main", description="Git branch or revision to track")
    environment: str = Field("development", description="Target environment overlay")
    auto_sync: bool = Field(False, description="Enable automated Argo CD synchronization")
    self_heal: bool = Field(False, description="Enable Argo CD self-healing drift reconciliation")
    replicas: Optional[int] = Field(None, description="Desired pod replica count")
    image_tag: Optional[str] = Field(None, description="Explicit container image tag")

class GitOpsSyncRequest(BaseModel):
    revision: Optional[str] = Field(None, description="Optional Git revision override for sync")
    async_execution: bool = Field(True, description="Queue operation asynchronously via worker")

class GitOpsRefreshRequest(BaseModel):
    async_execution: bool = Field(False, description="Trigger refresh synchronously or queue")

class GitOpsDriftResource(BaseModel):
    group: str
    kind: str
    name: str
    namespace: str

class GitOpsApplicationResponse(BaseModel):
    id: int
    application_id: int
    application_name: str
    argocd_application_name: str
    git_repository: str
    git_path: str
    target_revision: str
    namespace: str
    sync_status: str
    health_status: str
    auto_sync_enabled: bool
    self_heal_enabled: bool
    last_synced_at: Optional[str] = None
    last_sync_revision: Optional[str] = None
    sync_message: Optional[str] = None
    drift_count: int = 0
    drifted_resources: List[Dict[str, Any]] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class GitOpsOperationResponse(BaseModel):
    id: int
    gitops_application_id: int
    operation_type: str
    status: str
    revision: Optional[str] = None
    details: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str

class GitOpsClusterStatusResponse(BaseModel):
    available: bool
    version: str
    server_url: str
    namespace: str
