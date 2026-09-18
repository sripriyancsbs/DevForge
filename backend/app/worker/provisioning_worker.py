import os
import signal
import sys
import time
import logging
from typing import Optional

from app.db.session import SessionLocal, verify_connection, run_phase2_migrations
from app.services.provisioning.service import provisioning_service
from app.models.provisioning_job import ProvisioningJob

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

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


def process_one_job() -> Optional[ProvisioningJob]:
    """Acquire and process a single job if available. Useful for tests and worker loop."""
    db = SessionLocal()
    try:
        job = provisioning_service.acquire_next_job(db)
        if job:
            logger.info(f"Worker claimed job #{job.id} (App #{job.application_id}, Template: {job.template})")
            processed = provisioning_service.execute_job(job.id, db)
            return processed
        return None
    except Exception as e:
        logger.error(f"Error executing job in worker: {e}")
        return None
    finally:
        db.close()


def run_worker_loop():
    """Continuous polling loop for the DevForge provisioning worker."""
    poll_interval = float(os.getenv("WORKER_POLL_INTERVAL", "1.0"))
    logger.info("Initializing DevForge Provisioning Worker...")
    
    try:
        verify_connection()
        run_phase2_migrations()
        logger.info("Database connectivity and schema migrations verified.")
    except Exception as e:
        logger.error(f"Failed to initialize worker database connection: {e}")
        sys.exit(1)

    logger.info(f"Provisioning worker started. Listening for PENDING/RETRY jobs (poll interval: {poll_interval}s)...")

    while running:
        try:
            job = process_one_job()
            if not job:
                time.sleep(poll_interval)
        except Exception as e:
            logger.error(f"Unexpected error in worker loop: {e}")
            time.sleep(poll_interval)

    logger.info("DevForge Provisioning Worker stopped cleanly.")


if __name__ == "__main__":
    run_worker_loop()
