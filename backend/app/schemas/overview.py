from typing import List
from pydantic import BaseModel
from app.schemas.deployment import DeploymentResponse
from app.schemas.service_health import ServiceHealthResponse, ActivityResponse

class MetricCard(BaseModel):
    label: str
    value: str
    change: str
    status: str # healthy, warning, failed, neutral
    subtext: str

class OverviewMetrics(BaseModel):
    applications_count: int
    healthy_services: str
    active_deployments: int
    failed_deployments: int
    metrics_cards: List[MetricCard]

class OverviewResponse(BaseModel):
    metrics: OverviewMetrics
    recent_deployments: List[DeploymentResponse]
    service_health: List[ServiceHealthResponse]
    recent_activity: List[ActivityResponse]
