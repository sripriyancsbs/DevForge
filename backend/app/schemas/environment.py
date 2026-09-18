from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class EnvironmentBase(BaseModel):
    name: str
    slug: str
    type: str
    region: str
    cluster_endpoint: str
    status: str
    services_count: int
    cpu_allocated: str
    memory_allocated: str
    description: Optional[str] = None

class EnvironmentResponse(EnvironmentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
