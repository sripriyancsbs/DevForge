from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.application import Application
from app.models.deployment import Deployment
from app.models.service_health import ServiceHealth
from app.models.activity import Activity
from app.schemas.overview import OverviewResponse, OverviewMetrics, MetricCard
from app.schemas.deployment import DeploymentResponse
from app.schemas.service_health import ServiceHealthResponse, ActivityResponse

router = APIRouter()

@router.get("", response_model=OverviewResponse)
def get_overview(db: Session = Depends(get_db)):
    apps_count = db.query(Application).count()
    
    # Healthy services calculation
    services = db.query(ServiceHealth).all()
    healthy_services_count = sum(1 for s in services if s.status == "healthy")
    total_services = len(services)
    healthy_str = f"{healthy_services_count} / {total_services} Healthy" if total_services > 0 else "0 / 0 Healthy"

    # Active and Failed deployments
    active_deployments = db.query(Deployment).filter(Deployment.status.in_(["deploying", "building", "pending"])).count()
    failed_deployments = db.query(Deployment).filter(Deployment.status == "failed").count()

    metrics_cards = [
        MetricCard(
            label="Applications",
            value=str(apps_count),
            change="+2 this week",
            status="healthy",
            subtext="Registered services"
        ),
        MetricCard(
            label="Healthy Services",
            value=healthy_str,
            change="98.4% uptime",
            status="healthy" if healthy_services_count == total_services and total_services > 0 else "warning",
            subtext="Active healthchecks passing"
        ),
        MetricCard(
            label="Active Deployments",
            value=str(active_deployments),
            change="In pipeline" if active_deployments > 0 else "Idle",
            status="healthy" if active_deployments == 0 else "neutral",
            subtext="Running build & rollout"
        ),
        MetricCard(
            label="Failed Deployments",
            value=str(failed_deployments),
            change="Requires attention" if failed_deployments > 0 else "All clean",
            status="failed" if failed_deployments > 0 else "healthy",
            subtext="Last 24 hours"
        )
    ]

    metrics = OverviewMetrics(
        applications_count=apps_count,
        healthy_services=healthy_str,
        active_deployments=active_deployments,
        failed_deployments=failed_deployments,
        metrics_cards=metrics_cards
    )

    recent_deployments = db.query(Deployment).order_by(Deployment.created_at.desc()).limit(6).all()
    service_health = db.query(ServiceHealth).order_by(ServiceHealth.cpu_percent.desc()).all()
    recent_activity = db.query(Activity).order_by(Activity.created_at.desc()).limit(8).all()

    return OverviewResponse(
        metrics=metrics,
        recent_deployments=[DeploymentResponse.model_validate(d) for d in recent_deployments],
        service_health=[ServiceHealthResponse.model_validate(s) for s in service_health],
        recent_activity=[ActivityResponse.model_validate(a) for a in recent_activity]
    )
