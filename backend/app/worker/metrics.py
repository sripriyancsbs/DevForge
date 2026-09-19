import time
import logging
from typing import Optional
from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger("devforge.worker.metrics")

WORKER_UP = Gauge(
    "devforge_worker_up",
    "Worker process status (1=up, 0=down)"
)

WORKER_HEARTBEAT = Gauge(
    "devforge_worker_heartbeat_timestamp",
    "Epoch timestamp of worker heartbeat"
)

WORKER_JOBS_PROCESSED_TOTAL = Counter(
    "devforge_worker_jobs_processed_total",
    "Total provisioning jobs processed by worker",
    ["template", "status"]
)

WORKER_JOB_DURATION_SECONDS = Histogram(
    "devforge_worker_job_duration_seconds",
    "Provisioning job execution duration in seconds",
    ["template"],
    buckets=[1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0]
)

WORKER_ANSIBLE_JOBS_TOTAL = Counter(
    "devforge_worker_ansible_jobs_processed_total",
    "Total Ansible jobs processed by worker",
    ["playbook", "status"]
)

WORKER_ANSIBLE_DURATION_SECONDS = Histogram(
    "devforge_worker_ansible_job_duration_seconds",
    "Ansible job execution duration in seconds",
    ["playbook"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0]
)

WORKER_ACTIVE_JOBS = Gauge(
    "devforge_worker_active_jobs",
    "Currently active jobs being executed by worker"
)

_server_started = False


def start_worker_metrics_server(port: int = 8001):
    """Start standalone Prometheus HTTP metrics server on given port."""
    global _server_started
    if _server_started:
        return
    try:
        start_http_server(port)
        WORKER_UP.set(1.0)
        WORKER_HEARTBEAT.set(time.time())
        _server_started = True
        logger.info(f"Worker Prometheus metrics server listening on port {port}")
    except Exception as e:
        logger.warning(f"Could not start worker Prometheus metrics server on port {port}: {e}")


def update_heartbeat():
    WORKER_HEARTBEAT.set(time.time())


def record_worker_job(template: str, status: str, duration: Optional[float] = None):
    WORKER_JOBS_PROCESSED_TOTAL.labels(template=template, status=status).inc()
    if duration is not None and duration > 0:
        WORKER_JOB_DURATION_SECONDS.labels(template=template).observe(duration)


def record_worker_ansible(playbook: str, status: str, duration: Optional[float] = None):
    WORKER_ANSIBLE_JOBS_TOTAL.labels(playbook=playbook, status=status).inc()
    if duration is not None and duration > 0:
        WORKER_ANSIBLE_DURATION_SECONDS.labels(playbook=playbook).observe(duration)
