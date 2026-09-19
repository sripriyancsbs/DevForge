from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ServiceHealthItem(BaseModel):
    status: str
    details: Optional[str] = None
    url: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class SystemHealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: str
    backend: Dict[str, Any]
    worker: Dict[str, Any]
    database: Dict[str, Any]
    kubernetes: Dict[str, Any]
    prometheus: Dict[str, Any]
    grafana: Dict[str, Any]
    argocd: Optional[Dict[str, Any]] = None


class MetricsSummaryResponse(BaseModel):
    api: Dict[str, Any]
    applications: Dict[str, Any]
    provisioning: Dict[str, Any]
    deployments: Dict[str, Any]
    ansible: Dict[str, Any]
    infrastructure: Dict[str, Any]
    gitops: Optional[Dict[str, Any]] = None


class MonitoredServiceItem(BaseModel):
    name: str
    component: str
    tier: str
    endpoint: str
    port: int
    health: str
    latency_ms: Optional[float] = None
    description: str


class AlertRuleItem(BaseModel):
    name: str
    state: str
    severity: str
    summary: str
    description: str
    expression: str
