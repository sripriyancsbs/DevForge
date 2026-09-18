from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class DeploymentBase(BaseModel):
    application_id: int
    application_name: str
    version: str
    commit_hash: str
    commit_message: Optional[str] = None
    environment: str = "production"
    status: str = "deploying"
    duration: str = "45s"
    triggered_by: str = "git-push:main"
    logs: Optional[str] = None

class DeploymentCreate(BaseModel):
    application_id: int
    version: str = "v1.0.1"
    environment: str = "production"
    commit_message: Optional[str] = "Triggered via DevForge platform console"

class DeploymentResponse(DeploymentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
