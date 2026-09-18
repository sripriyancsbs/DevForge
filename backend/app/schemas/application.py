from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class ApplicationBase(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    team: str = "Payments Core"
    runtime: str = "Python 3.12"
    repository_url: str
    branch: str = "main"
    environment: str = "production"
    version: str = "v1.0.0"
    port: int = 8000
    replicas: int = 2

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    team: Optional[str] = None
    runtime: Optional[str] = None
    repository_url: Optional[str] = None
    branch: Optional[str] = None
    environment: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None
    port: Optional[int] = None
    replicas: Optional[int] = None

class ApplicationResponse(ApplicationBase):
    id: int
    slug: str
    status: str
    last_deployment_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
