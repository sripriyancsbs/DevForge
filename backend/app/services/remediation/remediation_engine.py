import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.application import Application
from app.models.kubernetes_deployment import KubernetesDeployment
from app.models.remediation import RemediationPolicy, RemediationEvent, RemediationExecution
from app.models.activity import Activity
from app.services.remediation.policy_service import policy_service
from app.services.remediation.action_service import action_service
from app.services.remediation.health_verifier import health_verifier
from app.services.remediation.exceptions import (
    PolicyNotFoundError,
    RemediationCooldownError,
    MaxAttemptsExceededError,
    ApprovalRequiredError,
    ActionExecutionError,
    ConcurrencyConflictError,
)
from app.services.kubernetes.kubernetes_client import kubernetes_client
from app.core.config import settings

logger = logging.getLogger("devforge.remediation.engine")


def utcnow():
    return datetime.now(timezone.utc)


class RemediationEngine:
    """
    Central orchestration engine for DevForge Self-Healing and Automated Remediation.
    Coordinates:
    - Failure event ingestion and deduplication
    - Deterministic policy matching & environment safety checks
    - Worker-level PostgreSQL row locking (with_for_update(skip_locked=True))
    - Safe idempotent action execution
    - Rigorous post-remediation health verification
    - Application status updates, structured audit trail, and deep-linkable notifications
    """

    def record_activity(
        self,
        db: Session,
        actor: str,
        action: str,
        target: str,
        status: str,
        details: str,
    ) -> Activity:
        """Record an auditable activity entry for self-healing operations."""
        act = Activity(
            actor=actor,
            action=action,
            target=target,
            target_type="remediation",
            status=status,
            details=details,
            created_at=utcnow(),
        )
        db.add(act)
        db.commit()
        return act

    def create_event(
        self,
        application_id: int,
        environment_id: str,
        event_type: str,
        source: str,
        severity: str,
        details: str,
        db: Session,
    ) -> RemediationEvent:
        """
        Record a failure event idempotently.
        If an unresolved event of the same type and environment already exists,
        updates it to prevent alert storms and duplicate processing.
        """
        existing = (
            db.query(RemediationEvent)
            .filter(
                RemediationEvent.application_id == application_id,
                RemediationEvent.environment_id == environment_id,
                RemediationEvent.event_type == event_type,
                RemediationEvent.status.in_(["DETECTED", "EVALUATING", "REMEDIATING", "VERIFYING"]),
            )
            .first()
        )

        if existing:
            existing.details = details
            existing.severity = severity
            existing.updated_at = utcnow()
            db.commit()
            db.refresh(existing)
            logger.info(
                f"Updated existing open remediation event #{existing.id} ({event_type}) for app #{application_id}"
            )
            return existing

        app = db.query(Application).filter(Application.id == application_id).first()
        app_name = app.name if app else f"app-{application_id}"

        event = RemediationEvent(
            application_id=application_id,
            environment_id=environment_id,
            event_type=event_type,
            source=source,
            severity=severity,
            status="DETECTED",
            details=details,
            attempts=0,
            detected_at=utcnow(),
            created_at=utcnow(),
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        logger.info(
            f"Created new remediation event #{event.id}: {event_type} on '{app_name}' [{environment_id}]"
        )

        self.record_activity(
            db=db,
            actor="devforge.monitor",
            action=f"Health event detected: {event_type}",
            target=app_name,
            status="detected",
            details=f"Condition detected on {environment_id} ({source}): {details}",
        )

        return event

    def scan_applications_health(self, db: Session) -> List[RemediationEvent]:
        """
        Periodic health scanning routine run by worker/scheduler:
        Inspects live Kubernetes pods and deployment statuses across active applications.
        Generates remediation events when real failure conditions are detected.
        """
        detected_events = []
        apps = db.query(Application).all()

        for app in apps:
            deployments = (
                db.query(KubernetesDeployment)
                .filter(KubernetesDeployment.application_id == app.id)
                .all()
            )

            for dep in deployments:
                env = dep.environment or "development"
                namespace = dep.namespace or "devforge"

                try:
                    pods = kubernetes_client.get_pods_for_application(app.name, namespace)
                except Exception as e:
                    logger.debug(f"Could not inspect pods for {app.name}: {e}")
                    continue

                # 1. Inspect for Pod CrashLoops
                crash_pods = [p for p in pods if "CrashLoopBackOff" in (p.get("message") or "")]
                if crash_pods:
                    pod_name = crash_pods[0].get("name", "unknown")
                    msg = crash_pods[0].get("message", "Pod crashed repeatedly")
                    ev = self.create_event(
                        application_id=app.id,
                        environment_id=env,
                        event_type="POD_CRASH_LOOP",
                        source="kubernetes",
                        severity="HIGH",
                        details=f"Pod {pod_name} is in CrashLoopBackOff: {msg}",
                        db=db,
                    )
                    detected_events.append(ev)
                    continue

                # 2. Inspect for Pod Unhealthy / not ready
                if dep.status == "DEPLOYED" and dep.replicas > 0:
                    ready_count = sum(1 for p in pods if p.get("ready"))
                    if ready_count == 0 and len(pods) > 0:
                        ev = self.create_event(
                            application_id=app.id,
                            environment_id=env,
                            event_type="APPLICATION_UNHEALTHY",
                            source="kubernetes",
                            severity="HIGH",
                            details=f"Application has 0/{dep.replicas} pods ready in namespace '{namespace}'",
                            db=db,
                        )
                        detected_events.append(ev)
                        continue

                # 3. Inspect for Failed Deployment record
                if dep.status == "FAILED":
                    ev = self.create_event(
                        application_id=app.id,
                        environment_id=env,
                        event_type="DEPLOYMENT_FAILED",
                        source="deployment_controller",
                        severity="MEDIUM",
                        details=dep.error_message or "Deployment marked as FAILED in cluster",
                        db=db,
                    )
                    detected_events.append(ev)

        return detected_events

    def acquire_next_event(self, db: Session) -> Optional[RemediationEvent]:
        """
        Atomically acquire the next queued remediation event using PostgreSQL row locking.
        Skips events that are currently in cooldown to prevent busy polling.
        """
        try:
            candidates = (
                db.query(RemediationEvent)
                .filter(RemediationEvent.status.in_(["DETECTED", "APPROVED"]))
                .order_by(RemediationEvent.created_at.asc())
                .all()
            )

            now = utcnow()
            for cand in candidates:
                # If operator explicitly approved it, bypass cooldown
                if cand.status != "APPROVED":
                    # Check if app/env is in cooldown
                    last_exec = (
                        db.query(RemediationExecution)
                        .filter(
                            RemediationExecution.application_id == cand.application_id,
                            RemediationExecution.environment_id == cand.environment_id,
                            RemediationExecution.status.in_(["SUCCESS", "FAILED", "RUNNING"]),
                        )
                        .order_by(desc(RemediationExecution.created_at))
                        .first()
                    )
                    if last_exec and last_exec.completed_at:
                        policy = policy_service.match_policy(cand, db)
                        cooldown_secs = policy.cooldown_seconds if policy else 300
                        elapsed = (now - last_exec.completed_at).total_seconds()
                        if elapsed < cooldown_secs:
                            # Skip this candidate for now as it's still cooling down
                            continue

                # Lock this candidate specifically
                locked_event = (
                    db.query(RemediationEvent)
                    .filter(RemediationEvent.id == cand.id, RemediationEvent.status.in_(["DETECTED", "APPROVED"]))
                    .with_for_update(skip_locked=True)
                    .first()
                )
                if locked_event:
                    locked_event.status = "EVALUATING"
                    locked_event.updated_at = now
                    db.commit()
                    db.refresh(locked_event)
                    return locked_event

            return None
        except Exception as e:
            logger.error(f"Failed to acquire remediation event with row lock: {e}")
            db.rollback()
            return None

    def process_event(self, event_id: int, db: Session) -> Optional[RemediationExecution]:
        """
        Execute full lifecycle for a claimed remediation event:
        1. Match Policy
        2. Evaluate Safety (cooldown, max attempts, approvals)
        3. Create Execution Record
        4. Execute Safe Action
        5. Verify Health Post-Remediation
        6. Mark RECOVERED or FAILED/ESCALATED
        7. Audit Log & Notifications
        """
        event = db.query(RemediationEvent).filter(RemediationEvent.id == event_id).first()
        if not event:
            logger.warning(f"Remediation event #{event_id} not found.")
            return None

        app = db.query(Application).filter(Application.id == event.application_id).first()
        app_name = app.name if app else f"app-{event.application_id}"

        logger.info(
            f"Processing remediation event #{event.id} ({event.event_type}) for '{app_name}' [{event.environment_id}]"
        )

        # 1. Match policy
        policy = policy_service.match_policy(event, db)
        if not policy:
            logger.info(f"No active policy found for event #{event.id} ({event.event_type}). Marking IGNORED.")
            event.status = "IGNORED"
            event.updated_at = utcnow()
            db.commit()
            self.record_activity(
                db=db,
                actor="devforge.remediation",
                action="Remediation ignored: No policy",
                target=app_name,
                status="ignored",
                details=f"No matching remediation policy found for event '{event.event_type}' on '{event.environment_id}'",
            )
            return None

        # 2. Evaluate Safety & Loop Protection
        try:
            safety = policy_service.evaluate_safety(event, policy, db)
        except MaxAttemptsExceededError as mae:
            logger.warning(f"Remediation loop protection triggered for event #{event.id}: {mae}")
            event.status = "ESCALATED"
            event.updated_at = utcnow()
            db.commit()
            self.record_activity(
                db=db,
                actor="devforge.remediation",
                action="Automatic Remediation Escalated",
                target=app_name,
                status="escalated",
                details=f"Automatic remediation halted: Application remains unhealthy after {mae.attempts} attempts. Manual intervention required.",
            )
            return None
        except RemediationCooldownError as rce:
            logger.info(f"Application '{app_name}' in cooldown ({rce.remaining_seconds}s remaining). Re-queueing event.")
            event.status = "DETECTED"
            event.updated_at = utcnow()
            db.commit()
            return None
        except ApprovalRequiredError as are:
            logger.info(f"Remediation for '{app_name}' requires approval: {are}")
            event.status = "EVALUATING"
            event.details = f"Action '{policy.action}' pending operator approval for environment '{event.environment_id}'"
            event.updated_at = utcnow()
            db.commit()
            self.record_activity(
                db=db,
                actor="devforge.remediation",
                action="Remediation Approval Required",
                target=app_name,
                status="pending_approval",
                details=f"Action '{policy.action}' requires operator sign-off before execution on {event.environment_id}.",
            )
            return None
        except Exception as se:
            logger.error(f"Safety evaluation failed for event #{event.id}: {se}")
            event.status = "FAILED"
            event.updated_at = utcnow()
            db.commit()
            return None

        # Check concurrency
        if policy_service.check_active_concurrency(event.application_id, event.environment_id, db):
            logger.warning(
                f"Another remediation is already executing on '{app_name}' [{event.environment_id}]. Yielding."
            )
            event.status = "DETECTED"
            db.commit()
            return None

        # 3. Create Execution Record
        attempt_number = (event.attempts or 0) + 1
        execution = RemediationExecution(
            event_id=event.id,
            application_id=event.application_id,
            environment_id=event.environment_id,
            policy_id=policy.id,
            action=policy.action,
            status="RUNNING",
            attempt=attempt_number,
            started_at=utcnow(),
            created_at=utcnow(),
        )
        db.add(execution)

        event.status = "REMEDIATING"
        event.attempts = attempt_number
        event.updated_at = utcnow()
        db.commit()
        db.refresh(execution)

        self.record_activity(
            db=db,
            actor="devforge.remediation",
            action=f"Remediation started: {policy.action}",
            target=app_name,
            status="in_progress",
            details=f"Executing policy '{policy.name}' (Action: {policy.action}, Attempt: {attempt_number}/{policy.max_attempts})",
        )

        # 4. Execute Action
        action_result = None
        action_error = None
        try:
            action_result = action_service.execute_action(
                action=policy.action,
                event=event,
                execution=execution,
                db=db,
            )
            execution.result = json.dumps(action_result)
            event.status = "VERIFYING"
            db.commit()
        except ActionExecutionError as aee:
            action_error = str(aee)
            logger.error(f"Action execution failed for event #{event.id}: {action_error}")

        # 5. Verify Health (if action was initiated)
        recovery_confirmed = False
        verifier_details: Dict[str, Any] = {}

        if not action_error:
            self.record_activity(
                db=db,
                actor="devforge.remediation",
                action="Verifying application health",
                target=app_name,
                status="in_progress",
                details=f"Waiting for rollout and health checks to confirm recovery for {app_name}",
            )
            recovery_confirmed, verifier_details = health_verifier.verify_recovery(
                application=app,
                environment=event.environment_id,
                db=db,
                timeout=45,
            )

        # 6. Finalize Outcome
        now = utcnow()
        execution.completed_at = now

        if recovery_confirmed:
            execution.status = "SUCCESS"
            event.status = "RECOVERED"
            event.resolved_at = now
            if app:
                app.status = "healthy"

            db.commit()

            self.record_activity(
                db=db,
                actor="devforge.remediation",
                action="Application Recovered",
                target=app_name,
                status="recovered",
                details=f"Health restored after automated remediation ({policy.action}). All pods verified Ready.",
            )
            logger.info(f"Successfully recovered '{app_name}' via remediation #{execution.id}")
        else:
            execution.status = "FAILED"
            execution.error_message = action_error or verifier_details.get("error", "Health verification failed")

            if attempt_number >= policy.max_attempts:
                event.status = "ESCALATED"
                if app:
                    app.status = "failed"
                db.commit()

                self.record_activity(
                    db=db,
                    actor="devforge.remediation",
                    action="Automatic Remediation Failed",
                    target=app_name,
                    status="escalated",
                    details=f"Application remains unhealthy after {attempt_number} attempts. Manual investigation required.",
                )
                logger.warning(
                    f"Remediation escalated for '{app_name}' after {attempt_number} failed attempts."
                )
            else:
                event.status = "FAILED"
                db.commit()

                self.record_activity(
                    db=db,
                    actor="devforge.remediation",
                    action=f"Remediation attempt #{attempt_number} failed",
                    target=app_name,
                    status="failed",
                    details=f"Remediation action failed or health was not restored. Will retry after cooldown.",
                )

        db.refresh(execution)
        return execution

    def retry_event(self, event_id: int, db: Session) -> RemediationEvent:
        """Allow operator to manually retry a failed or escalated event."""
        event = db.query(RemediationEvent).filter(RemediationEvent.id == event_id).first()
        if not event:
            raise ValueError(f"Remediation event #{event_id} not found.")

        event.status = "DETECTED"
        event.updated_at = utcnow()
        db.commit()
        db.refresh(event)

        app = db.query(Application).filter(Application.id == event.application_id).first()
        app_name = app.name if app else f"app-{event.application_id}"

        self.record_activity(
            db=db,
            actor="operator",
            action="Manual Remediation Retry",
            target=app_name,
            status="re-queued",
            details=f"Operator manually re-queued remediation event #{event.id} ({event.event_type})",
        )
        return event

    def approve_event(self, event_id: int, db: Session) -> RemediationEvent:
        """Allow operator to approve a pending remediation action (e.g. for Production)."""
        event = db.query(RemediationEvent).filter(RemediationEvent.id == event_id).first()
        if not event:
            raise ValueError(f"Remediation event #{event_id} not found.")

        event.status = "APPROVED"
        event.updated_at = utcnow()
        db.commit()
        db.refresh(event)

        app = db.query(Application).filter(Application.id == event.application_id).first()
        app_name = app.name if app else f"app-{event.application_id}"

        self.record_activity(
            db=db,
            actor="operator",
            action="Remediation Approved",
            target=app_name,
            status="approved",
            details=f"Operator approved remediation for event #{event.id} on '{event.environment_id}'",
        )
        return event

    def cancel_event(self, event_id: int, db: Session) -> RemediationEvent:
        """Cancel an open remediation event."""
        event = db.query(RemediationEvent).filter(RemediationEvent.id == event_id).first()
        if not event:
            raise ValueError(f"Remediation event #{event_id} not found.")

        event.status = "CANCELLED"
        event.updated_at = utcnow()
        db.commit()
        db.refresh(event)

        app = db.query(Application).filter(Application.id == event.application_id).first()
        app_name = app.name if app else f"app-{event.application_id}"

        self.record_activity(
            db=db,
            actor="operator",
            action="Remediation Cancelled",
            target=app_name,
            status="cancelled",
            details=f"Operator cancelled remediation event #{event.id}",
        )
        return event


remediation_engine = RemediationEngine()
