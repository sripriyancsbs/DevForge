from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DeployApplicationRequest(BaseModel):
    image_tag: Optional[str] = Field(None, description="Container image tag to deploy (defaults to latest recorded)")
    environment: Optional[str] = Field("development", description="Target environment name")
    replicas: Optional[int] = Field(1, ge=1, le=10, description="Number of pod replicas")
    port: Optional[int] = Field(None, ge=1, le=65535, description="Application container port override")


class RedeployApplicationRequest(BaseModel):
    image_tag: Optional[str] = Field(None, description="Optional new image tag to rollout")
    replicas: Optional[int] = Field(None, ge=1, le=10, description="Optional new replica count")


class PodStatusDetail(BaseModel):
    name: str
    phase: str
    ready: bool
    restart_count: int = 0
    node_name: Optional[str] = None
    started_at: Optional[str] = None
    message: Optional[str] = None


class KubernetesDeploymentResponse(BaseModel):
    id: int
    application_id: int
    application_name: str
    environment: str
    namespace: str
    deployment_name: str
    service_name: str
    image: str
    image_repository: str
    image_tag: str
    replicas: int
    ready_replicas: int
    status: str
    port: int
    node_port: Optional[int] = None
    service_url: Optional[str] = None
    manifest_yaml: Optional[str] = None
    error_message: Optional[str] = None
    pods: List[PodStatusDetail] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class KubernetesClusterStatus(BaseModel):
    connected: bool
    provider: str = "Local Kubernetes"
    version: Optional[str] = None
    namespace: str = "devforge"
    node_count: int = 0
    nodes: List[Dict[str, Any]] = []
    error: Optional[str] = None
