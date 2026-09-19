import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.metrics import (
    normalize_path,
    record_provisioning_metric,
    record_ansible_metric,
    record_deployment_metric,
    record_postgres_health,
    HTTP_REQUESTS_TOTAL,
    HTTP_ERRORS_TOTAL,
)
from app.services.monitoring.observability_service import observability_service

client = TestClient(app)


def test_normalize_path():
    assert normalize_path("/api/v1/applications/1234") == "/api/v1/applications/{id}"
    assert normalize_path("/api/v1/applications/1234/deployment") == "/api/v1/applications/{id}/deployment"
    assert normalize_path("/api/v1/applications/qa-pw-py-1234/images") == "/api/v1/applications/{slug}/images"
    assert normalize_path("/health") == "/health"
    assert normalize_path("/health/") == "/health"


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    content = response.text
    assert "devforge_http_requests_total" in content
    assert "devforge_http_request_duration_seconds" in content
    assert "devforge_postgres_connected" in content


def test_middleware_records_requests_and_errors():
    # Make request to a valid endpoint
    res_ok = client.get("/health")
    assert res_ok.status_code == 200

    # Make request to a nonexistent endpoint to generate 404 error
    res_err = client.get("/api/v1/nonexistent_route_404")
    assert res_err.status_code == 404

    # Scrape metrics again to ensure counters were updated
    res_metrics = client.get("/metrics")
    assert res_metrics.status_code == 200
    text = res_metrics.text
    assert 'endpoint="/health"' in text
    assert 'status="404"' in text


def test_domain_metrics_recorders():
    # Should execute cleanly without raising exceptions
    record_provisioning_metric("python-fastapi", "SUCCESS", 5.2)
    record_provisioning_metric("react-vite", "FAILED")
    record_ansible_metric("health_check", "SUCCESS", 1.8)
    record_deployment_metric("development", "RUNNING")
    record_postgres_health(True, 3)

    metrics_res = client.get("/metrics")
    assert metrics_res.status_code == 200
    text = metrics_res.text
    assert "devforge_provisioning_jobs_total" in text
    assert "devforge_ansible_executions_total" in text
    assert "devforge_deployments_total" in text


def test_api_monitoring_health_endpoint():
    response = client.get("/api/v1/monitoring/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "backend" in data
    assert "worker" in data
    assert "database" in data
    assert "prometheus" in data
    assert "grafana" in data
    assert data["backend"]["port"] == 8000
    assert data["database"]["engine"] == "PostgreSQL 16"


def test_api_monitoring_metrics_summary_endpoint():
    response = client.get("/api/v1/monitoring/metrics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "api" in data
    assert "applications" in data
    assert "provisioning" in data
    assert "deployments" in data
    assert "ansible" in data
    assert "infrastructure" in data
    assert data["applications"]["total"] >= 0
    assert "error_rate_percent" in data["api"]


def test_api_monitoring_services_endpoint():
    response = client.get("/api/v1/monitoring/services")
    assert response.status_code == 200
    services = response.json()
    assert isinstance(services, list)
    assert len(services) >= 5
    components = [s["component"] for s in services]
    assert "backend" in components
    assert "worker" in components
    assert "postgres" in components
    assert "prometheus" in components
    assert "grafana" in components


def test_api_monitoring_alerts_endpoint():
    response = client.get("/api/v1/monitoring/alerts")
    assert response.status_code == 200
    alerts = response.json()
    assert isinstance(alerts, list)


def test_api_monitoring_targets_endpoint():
    response = client.get("/api/v1/monitoring/targets")
    assert response.status_code == 200
    targets = response.json()
    assert isinstance(targets, list)


def test_legacy_monitoring_endpoint():
    response = client.get("/api/v1/monitoring")
    assert response.status_code == 200
    data = response.json()
    assert "global" in data
    assert "service_metrics" in data
    assert len(data["service_metrics"]) >= 3
