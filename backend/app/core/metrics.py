import time
import re
from typing import Optional
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    REGISTRY,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# =============================================================================
# 1. HTTP Telemetry Metrics
# =============================================================================

HTTP_REQUESTS_TOTAL = Counter(
    "devforge_http_requests_total",
    "Total HTTP requests processed by the DevForge API",
    ["method", "endpoint", "status"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "devforge_http_request_duration_seconds",
    "HTTP request execution latency in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

HTTP_ERRORS_TOTAL = Counter(
    "devforge_http_errors_total",
    "Total HTTP error responses (4xx and 5xx)",
    ["method", "endpoint", "status"]
)

HTTP_ACTIVE_REQUESTS = Gauge(
    "devforge_http_active_requests",
    "Number of active HTTP requests currently being handled"
)

# =============================================================================
# 2. Domain & Orchestration Metrics
# =============================================================================

APPLICATIONS_TOTAL = Gauge(
    "devforge_applications_total",
    "Total registered applications in DevForge",
    ["environment", "runtime"]
)

PROVISIONING_JOBS_TOTAL = Counter(
    "devforge_provisioning_jobs_total",
    "Total provisioning jobs processed",
    ["template", "status"]
)

PROVISIONING_DURATION_SECONDS = Histogram(
    "devforge_provisioning_duration_seconds",
    "Provisioning job execution duration in seconds",
    ["template"],
    buckets=[1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0]
)

DEPLOYMENTS_TOTAL = Counter(
    "devforge_deployments_total",
    "Total Kubernetes deployments executed",
    ["environment", "status"]
)

ANSIBLE_EXECUTIONS_TOTAL = Counter(
    "devforge_ansible_executions_total",
    "Total Ansible playbook executions executed",
    ["playbook", "status"]
)

ANSIBLE_EXECUTION_DURATION_SECONDS = Histogram(
    "devforge_ansible_execution_duration_seconds",
    "Ansible playbook execution duration in seconds",
    ["playbook"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0]
)

POSTGRES_CONNECTED = Gauge(
    "devforge_postgres_connected",
    "PostgreSQL database connectivity (1=connected, 0=disconnected)"
)

POSTGRES_CONNECTIONS_ACTIVE = Gauge(
    "devforge_postgres_connections_active",
    "Estimated active PostgreSQL client connections"
)

# =============================================================================
# 3. Endpoint Normalization (Prevents Cardinality Explosion)
# =============================================================================

ID_PATTERN = re.compile(r"/\d+(?=/|$)")
SLUG_PATTERN = re.compile(r"/qa-[a-zA-Z0-9_-]+(?=/|$)")
LIFECYCLE_PATTERN = re.compile(r"/lifecycle-app-[a-zA-Z0-9_-]+(?=/|$)")


def normalize_path(path: str) -> str:
    """Normalize dynamic IDs and slugs in paths to static placeholders."""
    p = ID_PATTERN.sub("/{id}", path)
    p = SLUG_PATTERN.sub("/{slug}", p)
    p = LIFECYCLE_PATTERN.sub("/{slug}", p)
    # Remove trailing slash unless root
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]
    return p


# =============================================================================
# 4. Prometheus HTTP Middleware
# =============================================================================

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Exclude metrics endpoint itself from metrics recursion
        path = request.url.path
        if path == "/metrics":
            return await call_next(request)

        method = request.method
        norm_path = normalize_path(path)

        HTTP_ACTIVE_REQUESTS.inc()
        start_time = time.time()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            HTTP_ACTIVE_REQUESTS.dec()

            status_str = str(status_code)
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                endpoint=norm_path,
                status=status_str
            ).inc()

            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                endpoint=norm_path
            ).observe(duration)

            if status_code >= 400:
                HTTP_ERRORS_TOTAL.labels(
                    method=method,
                    endpoint=norm_path,
                    status=status_str
                ).inc()


# =============================================================================
# 5. Helpers for Recording Operational Events
# =============================================================================

def record_provisioning_metric(template: str, status: str, duration_seconds: Optional[float] = None):
    PROVISIONING_JOBS_TOTAL.labels(template=template, status=status).inc()
    if duration_seconds is not None and duration_seconds > 0:
        PROVISIONING_DURATION_SECONDS.labels(template=template).observe(duration_seconds)


def record_deployment_metric(environment: str, status: str):
    DEPLOYMENTS_TOTAL.labels(environment=environment, status=status).inc()


def record_ansible_metric(playbook: str, status: str, duration_seconds: Optional[float] = None):
    ANSIBLE_EXECUTIONS_TOTAL.labels(playbook=playbook, status=status).inc()
    if duration_seconds is not None and duration_seconds > 0:
        ANSIBLE_EXECUTION_DURATION_SECONDS.labels(playbook=playbook).observe(duration_seconds)


def record_postgres_health(is_connected: bool, active_connections: int = 1):
    POSTGRES_CONNECTED.set(1.0 if is_connected else 0.0)
    POSTGRES_CONNECTIONS_ACTIVE.set(float(active_connections))
