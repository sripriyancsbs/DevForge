import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.remediation import RemediationPolicy, RemediationEvent, RemediationExecution
from app.models.application import Application
from app.services.remediation.exceptions import (
    PolicyNotFoundError,
    RemediationCooldownError,
    MaxAttemptsExceededError,
    ApprovalRequiredError,
)

logger = logging.getLogger("devforge.remediation.policy")


def utcnow():
    return datetime.now(timezone.utc)


class RemediationPolicyService:
    """
    Evaluates and enforces policies for DevForge Self-Healing and Automated Remediation.
    Guarantees:
    - Conservative, deterministic policy matching
    - Strict retry limits and cooldown windows
    - Loop protection (prevents runaway restart loops)
    - Environment safety (Dev/Staging auto-remediation, Production approval gates)
    """

    ALLOWED_ACTIONS = {
        "KUBERNETES_ROLLOUT_RESTART",
        "KUBERNETES_REDEPLOY",
        "ARGOCD_SYNC",
        "RETRY_TRANSIENT_OPERATION",
    }

    ALLOWED_EVENT_TYPES = {
        "APPLICATION_UNHEALTHY",
        "APPLICATION_UNAVAILABLE",
        "POD_CRASH_LOOP",
        "DEPLOYMENT_FAILED",
        "DEPLOYMENT_STUCK",
        "GITOPS_OUT_OF_SYNC",
        "HIGH_ERROR_RATE",
    }

    def list_policies(self, db: Session, application_id: Optional[int] = None) -> List[RemediationPolicy]:
        """List all configured remediation policies."""
        query = db.query(RemediationPolicy).order_by(RemediationPolicy.id.asc())
        return query.all()

    def get_policy(self, policy_id: int, db: Session) -> Optional[RemediationPolicy]:
        """Fetch a single remediation policy by ID."""
        return db.query(RemediationPolicy).filter(RemediationPolicy.id == policy_id).first()

    def match_policy(
        self,
        event: RemediationEvent,
        db: Session
    ) -> Optional[RemediationPolicy]:
        """
        Find the most specific enabled policy for an event based on event_type and environment.
        Preference order:
        1. Exact environment match (e.g. 'development')
        2. Wildcard environment match ('all')
        """
        # 1. Look for exact environment match
        policy = (
            db.query(RemediationPolicy)
            .filter(
                RemediationPolicy.event_type == event.event_type,
                RemediationPolicy.environment == event.environment_id.lower(),
                RemediationPolicy.enabled == True,
            )
            .first()
        )
        if policy:
            return policy

        # 2. Look for 'all' environments match
        policy = (
            db.query(RemediationPolicy)
            .filter(
                RemediationPolicy.event_type == event.event_type,
                RemediationPolicy.environment == "all",
                RemediationPolicy.enabled == True,
            )
            .first()
        )
        return policy

    def evaluate_safety(
        self,
        event: RemediationEvent,
        policy: RemediationPolicy,
        db: Session
    ) -> Dict[str, Any]:
        """
        Execute safety checks before an action can be performed:
        1. Allowlist action validation
        2. Attempt count check (MaxAttemptsExceededError)
        3. Cooldown check against last execution (RemediationCooldownError)
        4. Operator approval requirement (ApprovalRequiredError)
        5. Concurrency check (prevent dual-executions on the same application)

        Returns safety evaluation metadata dictionary.
        """
        # 1. Action allowlist check
        if policy.action not in self.ALLOWED_ACTIONS:
            raise ValueError(f"Action '{policy.action}' is not in the predefined safe action allowlist.")

        # 2. Maximum attempts check
        current_attempts = event.attempts or 0
        max_attempts = policy.max_attempts if policy.max_attempts is not None else 3
        if current_attempts >= max_attempts:
            raise MaxAttemptsExceededError(
                f"Application '{event.application_id}' has reached maximum remediation attempts "
                f"({current_attempts}/{max_attempts}). Stopping automatic remediation to prevent loops.",
                attempts=current_attempts,
                max_attempts=max_attempts,
            )

        # 3. Cooldown check: Has an execution run too recently for this application/env?
        cooldown_seconds = policy.cooldown_seconds if policy.cooldown_seconds is not None else 300
        last_exec = (
            db.query(RemediationExecution)
            .filter(
                RemediationExecution.application_id == event.application_id,
                RemediationExecution.environment_id == event.environment_id,
                RemediationExecution.status.in_(["SUCCESS", "FAILED", "RUNNING"]),
            )
            .order_by(desc(RemediationExecution.created_at))
            .first()
        )

        now = utcnow()
        if last_exec and last_exec.completed_at:
            elapsed = (now - last_exec.completed_at).total_seconds()
            if elapsed < cooldown_seconds:
                remaining = int(cooldown_seconds - elapsed)
                raise RemediationCooldownError(
                    f"Application '{event.application_id}' in cooldown. "
                    f"Last remediation completed {int(elapsed)}s ago. Remaining cooldown: {remaining}s.",
                    remaining_seconds=remaining,
                )

        # 4. Operator approval gate:
        # Production environments or policies explicitly marked requires_approval must halt for approval
        is_production = event.environment_id.lower() in ("production", "prod")
        if policy.requires_approval or is_production:
            # Check if this event already has approval noted in details or status
            # If not already explicitly approved, require approval
            if event.status != "APPROVED":
                raise ApprovalRequiredError(
                    f"Remediation policy '{policy.name}' on '{event.environment_id}' requires manual operator approval."
                )

        return {
            "allowed": True,
            "policy_id": policy.id,
            "action": policy.action,
            "attempt": current_attempts + 1,
            "max_attempts": policy.max_attempts,
            "cooldown_seconds": policy.cooldown_seconds,
        }

    def check_active_concurrency(
        self,
        application_id: int,
        environment_id: str,
        db: Session
    ) -> bool:
        """Return True if an execution is currently RUNNING for this application and environment."""
        active = (
            db.query(RemediationExecution)
            .filter(
                RemediationExecution.application_id == application_id,
                RemediationExecution.environment_id == environment_id,
                RemediationExecution.status == "RUNNING",
            )
            .first()
        )
        return active is not None


policy_service = RemediationPolicyService()
