import os
import signal
import sys
import time
import logging
from typing import Optional, Any

from app.db.session import SessionLocal, verify_connection, run_phase2_migrations
from app.services.provisioning.service import provisioning_service
from app.models.provisioning_job import ProvisioningJob
from app.models.ansible_execution import AnsibleExecution
from app.services.ansible import execution_service as ansible_execution_service

from app.worker.metrics import (
    start_worker_metrics_server,
    update_heartbeat,
    record_worker_job,
    record_worker_ansible,
    WORKER_ACTIVE_JOBS,
    WORKER_UP,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [devforge.worker] %(message)s"
)
logger = logging.getLogger("devforge.worker")

running = True

def handle_exit(signum, frame):
    global running
    logger.info(f"Received shutdown signal ({signum}). Gracefully stopping worker...")
    running = False
    try:
        WORKER_UP.set(0.0)
    except Exception:
        pass

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


def process_one_job() -> Optional[ProvisioningJob]:
    """Acquire and process a single provisioning job if available. Useful for tests and worker loop."""
    db = SessionLocal()
    try:
        job = provisioning_service.acquire_next_job(db)
        if job:
            WORKER_ACTIVE_JOBS.inc()
            start_t = time.time()
            logger.info(f"Worker claimed job #{job.id} (App #{job.application_id}, Template: {job.template})")
            try:
                processed = provisioning_service.execute_job(job.id, db)
                duration = time.time() - start_t
                status = processed.status if processed else "UNKNOWN"
                record_worker_job(job.template, status, duration)
                return processed
            finally:
                WORKER_ACTIVE_JOBS.dec()
        return None
    except Exception as e:
        logger.error(f"Error executing job in worker: {e}")
        return None
    finally:
        db.close()


def process_one_ansible_job() -> Optional[AnsibleExecution]:
    """Acquire and process a single queued Ansible execution job if available."""
    db = SessionLocal()
    try:
        execution = ansible_execution_service.acquire_next_execution(db)
        if execution:
            WORKER_ACTIVE_JOBS.inc()
            start_t = time.time()
            logger.info(f"Worker claimed Ansible execution #{execution.id} (Playbook: {execution.playbook_name})")
            try:
                processed = ansible_execution_service.execute_job(execution.id, db)
                duration = time.time() - start_t
                status = processed.status if processed else "UNKNOWN"
                record_worker_ansible(execution.playbook_name, status, duration)
                return processed
            finally:
                WORKER_ACTIVE_JOBS.dec()
        return None
    except Exception as e:
        logger.error(f"Error executing Ansible job in worker: {e}")
        return None
    finally:
        db.close()


def process_one_gitops_job() -> Optional[Any]:
    """Acquire and process a single queued GitOps operation if available."""
    db = SessionLocal()
    try:
        from app.services.argocd.sync_service import gitops_sync_service
        operation = gitops_sync_service.acquire_next_operation(db)
        if operation:
            WORKER_ACTIVE_JOBS.inc()
            start_t = time.time()
            logger.info(f"Worker claimed GitOps operation #{operation.id} ({operation.operation_type})")
            try:
                processed = gitops_sync_service.execute_operation(operation.id, db)
                duration = time.time() - start_t
                status = processed.status if processed else "UNKNOWN"
                record_worker_job(f"gitops_{operation.operation_type.lower()}", status, duration)
                return processed
            finally:
                WORKER_ACTIVE_JOBS.dec()
        return None
    except Exception as e:
        logger.error(f"Error executing GitOps job in worker: {e}")
        return None
    finally:
        db.close()


def process_one_remediation_event() -> Optional[Any]:
    """Acquire and process a single queued remediation event if available."""
    db = SessionLocal()
    try:
        from app.services.remediation import remediation_engine
        event = remediation_engine.acquire_next_event(db)
        if event:
            WORKER_ACTIVE_JOBS.inc()
            start_t = time.time()
            logger.info(f"Worker claimed remediation event #{event.id} ({event.event_type} on app #{event.application_id})")
            try:
                processed = remediation_engine.process_event(event.id, db)
                duration = time.time() - start_t
                status = processed.status if processed else "COMPLETED"
                record_worker_job(f"remediation_{event.event_type.lower()}", status, duration)
                return processed
            finally:
                WORKER_ACTIVE_JOBS.dec()
        return None
    except Exception as e:
        logger.error(f"Error executing remediation event in worker: {e}")
        return None
    finally:
        db.close()


def run_worker_loop():
    """Continuous polling loop for the DevForge provisioning, Ansible automation, GitOps, and Self-Healing worker."""
    poll_interval = float(os.getenv("WORKER_POLL_INTERVAL", "1.0"))
    metrics_port = int(os.getenv("WORKER_METRICS_PORT", "8001"))
    health_scan_interval = float(os.getenv("HEALTH_SCAN_INTERVAL", "15.0"))
    logger.info("Initializing DevForge Worker (Provisioning, Ansible, GitOps & Self-Healing)...")
    
    # Start Prometheus metrics server
    start_worker_metrics_server(metrics_port)

    try:
        verify_connection()
        run_phase2_migrations()
        logger.info("Database connectivity and schema migrations verified.")
    except Exception as e:
        logger.error(f"Failed to initialize worker database connection: {e}")
        sys.exit(1)

    logger.info(f"Worker started. Listening for PENDING/RETRY jobs (poll interval: {poll_interval}s, metrics: :{metrics_port})...")

    last_scan_t = 0.0

    while running:
        try:
            update_heartbeat()

            # Periodic real health scanning for automated detection
            now = time.time()
            if now - last_scan_t > health_scan_interval:
                scan_db = SessionLocal()
                try:
                    from app.services.remediation import remediation_engine
                    remediation_engine.scan_applications_health(scan_db)
                except Exception as se:
                    logger.debug(f"Remediation health scan notice: {se}")
                finally:
                    scan_db.close()
                last_scan_t = now

            job = process_one_job()
            ansible_job = process_one_ansible_job()
            gitops_job = process_one_gitops_job()
            rem_job = process_one_remediation_event()
            if not job and not ansible_job and not gitops_job and not rem_job:
                time.sleep(poll_interval)
        except Exception as e:
            logger.error(f"Unexpected error in worker loop: {e}")
            time.sleep(poll_interval)

    logger.info("DevForge Worker stopped cleanly.")


if __name__ == "__main__":
    run_worker_loop()

