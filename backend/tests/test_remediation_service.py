import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import pytest

from app.models.application import Application
from app.models.kubernetes_deployment import KubernetesDeployment
from app.models.remediation import RemediationPolicy, RemediationEvent, RemediationExecution
from app.services.remediation import (
    remediation_engine,
    policy_service,
    action_service,
    health_verifier,
    PolicyNotFoundError,
    RemediationCooldownError,
    MaxAttemptsExceededError,
    ApprovalRequiredError,
    ActionExecutionError,
)


def utcnow():
    return datetime.now(timezone.utc)


@pytest.fixture
def test_app(db):
    """Fixture ensuring a test application exists in PostgreSQL."""
    app = db.query(Application).filter(Application.name == "remediation-test-app").first()
    if not app:
        app = Application(
            name="remediation-test-app",
            slug="remediation-test-app",
            description="Test app for automated remediation verification",
            status="healthy",
            runtime="Python 3.11",
            template="fastapi",
            repository_owner="sripriyancsbs",
            repository_name="remediation-test-app",
            repository_url="https://github.com/sripriyancsbs/remediation-test-app",
            port=8000,
            created_at=utcnow(),
        )
        db.add(app)
        db.commit()
        db.refresh(app)

    # Ensure a corresponding KubernetesDeployment record exists
    k8s = db.query(KubernetesDeployment).filter(KubernetesDeployment.application_id == app.id).first()
    if not k8s:
        k8s = KubernetesDeployment(
            application_id=app.id,
            environment="development",
            namespace="devforge",
            deployment_name="devforge-remediation-test-app",
            service_name="devforge-remediation-test-app-svc",
            image_repository="ghcr.io/sripriyancsbs/remediation-test-app",
            image_tag="latest",
            replicas=1,
            ready_replicas=1,
            status="DEPLOYED",
            port=8000,
            created_at=utcnow(),
        )
        db.add(k8s)
    # Clean any stale remediation state for test isolation
    db.query(RemediationExecution).filter(RemediationExecution.application_id == app.id).delete()
    db.query(RemediationEvent).filter(RemediationEvent.application_id == app.id).delete()
    db.commit()

    return app


# =============================================================================
# 1. Policy Evaluation & Safety Tests
# =============================================================================

def test_policy_matching_environment_precedence(db, test_app):
    """Verify policy matching prioritizes exact environment over wildcard 'all'."""
    # Specific policy for staging
    staging_pol = db.query(RemediationPolicy).filter(
        RemediationPolicy.event_type == "POD_CRASH_LOOP",
        RemediationPolicy.environment == "staging"
    ).first()
    if not staging_pol:
        staging_pol = RemediationPolicy(
            name="staging_crashloop_policy",
            event_type="POD_CRASH_LOOP",
            environment="staging",
            action="KUBERNETES_ROLLOUT_RESTART",
            enabled=True,
            max_attempts=2,
            cooldown_seconds=120,
        )
        db.add(staging_pol)
        db.commit()

    ev_staging = RemediationEvent(
        application_id=test_app.id,
        environment_id="staging",
        event_type="POD_CRASH_LOOP",
        status="DETECTED"
    )
    matched = policy_service.match_policy(ev_staging, db)
    assert matched is not None
    assert matched.name == "staging_crashloop_policy"
    assert matched.environment == "staging"


def test_action_allowlist_enforcement(db, test_app):
    """Verify arbitrary or destructive actions outside the allowlist are strictly rejected."""
    policy = RemediationPolicy(
        name="destructive_policy",
        event_type="APPLICATION_UNHEALTHY",
        environment="development",
        action="DELETE_NAMESPACE",  # Prohibited!
        enabled=True,
    )
    event = RemediationEvent(
        application_id=test_app.id,
        environment_id="development",
        event_type="APPLICATION_UNHEALTHY",
        status="DETECTED"
    )

    with pytest.raises(ValueError, match="not in the predefined safe action allowlist"):
        policy_service.evaluate_safety(event, policy, db)


def test_production_environment_approval_requirement(db, test_app):
    """Verify production environment always enforces manual approval gate."""
    policy = RemediationPolicy(
        name="prod_restart",
        event_type="APPLICATION_UNHEALTHY",
        environment="production",
        action="KUBERNETES_ROLLOUT_RESTART",
        enabled=True,
        requires_approval=False,  # Even if policy says false, prod requires approval
    )
    event = RemediationEvent(
        application_id=test_app.id,
        environment_id="production",
        event_type="APPLICATION_UNHEALTHY",
        status="DETECTED"
    )

    with pytest.raises(ApprovalRequiredError, match="requires manual operator approval"):
        policy_service.evaluate_safety(event, policy, db)


def test_loop_protection_max_attempts(db, test_app):
    """Verify loop protection halts remediation when max attempts is reached."""
    policy = RemediationPolicy(
        name="test_loop_policy",
        event_type="APPLICATION_UNHEALTHY",
        environment="development",
        action="KUBERNETES_ROLLOUT_RESTART",
        max_attempts=3,
        enabled=True,
    )
    event = RemediationEvent(
        application_id=test_app.id,
        environment_id="development",
        event_type="APPLICATION_UNHEALTHY",
        attempts=3,  # Already hit limit
        status="DETECTED"
    )

    with pytest.raises(MaxAttemptsExceededError) as exc_info:
        policy_service.evaluate_safety(event, policy, db)
    assert exc_info.value.attempts == 3
    assert exc_info.value.max_attempts == 3


def test_cooldown_enforcement(db, test_app):
    """Verify cooldown prevents repeated remediation within the configured window."""
    policy = RemediationPolicy(
        name="test_cooldown_policy",
        event_type="APPLICATION_UNHEALTHY",
        environment="development",
        action="KUBERNETES_ROLLOUT_RESTART",
        cooldown_seconds=300,
        enabled=True,
    )
    event = RemediationEvent(
        application_id=test_app.id,
        environment_id="development",
        event_type="APPLICATION_UNHEALTHY",
        attempts=1,
        status="DETECTED"
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # Insert a recent completed execution 30 seconds ago referencing this event
    recent_exec = RemediationExecution(
        event_id=event.id,
        application_id=test_app.id,
        environment_id="development",
        action="KUBERNETES_ROLLOUT_RESTART",
        status="FAILED",
        attempt=1,
        completed_at=utcnow() - timedelta(seconds=30),
    )
    db.add(recent_exec)
    db.commit()

    with pytest.raises(RemediationCooldownError) as exc_info:
        policy_service.evaluate_safety(event, policy, db)
    assert exc_info.value.remaining_seconds > 0


# =============================================================================
# 2. Remediation Engine Lifecycle & Failure Scenarios
# =============================================================================

def test_event_deduplication(db, test_app):
    """Verify duplicate alerts for the same condition update existing event instead of creating new ones."""
    ev1 = remediation_engine.create_event(
        application_id=test_app.id,
        environment_id="development",
        event_type="POD_CRASH_LOOP",
        source="kubernetes",
        severity="HIGH",
        details="First crash detection",
        db=db,
    )

    ev2 = remediation_engine.create_event(
        application_id=test_app.id,
        environment_id="development",
        event_type="POD_CRASH_LOOP",
        source="kubernetes",
        severity="CRITICAL",
        details="Second crash detection: backoff",
        db=db,
    )

    assert ev1.id == ev2.id
    assert ev2.severity == "CRITICAL"
    assert "Second crash" in ev2.details


@patch("app.services.remediation.action_service.kubernetes_client")
@patch("app.services.remediation.health_verifier.kubernetes_client")
def test_successful_remediation_and_recovery(mock_verifier_k8s, mock_action_k8s, db, test_app):
    """Scenario: Application unhealthy -> Action succeeded -> Health verified -> RECOVERED."""
    mock_action_k8s.rollout_restart_deployment.return_value = True
    mock_verifier_k8s.verify_rollout.return_value = (
        True,
        1,
        [{"name": "pod-1", "ready": True, "phase": "Running"}],
        None
    )

    # Create event
    event = RemediationEvent(
        application_id=test_app.id,
        environment_id="development",
        event_type="APPLICATION_UNHEALTHY",
        source="health_probe",
        severity="HIGH",
        status="DETECTED",
        details="Application probe timeout",
        created_at=utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    execution = remediation_engine.process_event(event.id, db)

    assert execution is not None
    assert execution.status == "SUCCESS"
    assert event.status == "RECOVERED"
    assert event.resolved_at is not None
    assert test_app.status == "healthy"


@patch("app.services.remediation.action_service.kubernetes_client")
@patch("app.services.remediation.health_verifier.kubernetes_client")
def test_failed_remediation_and_escalation(mock_verifier_k8s, mock_action_k8s, db, test_app):
    """Scenario: Action fails repeatedly -> Max attempts reached -> ESCALATED."""
    mock_action_k8s.rollout_restart_deployment.return_value = True
    # Verification reports pod in crash loop
    mock_verifier_k8s.verify_rollout.return_value = (
        False,
        0,
        [{"name": "pod-1", "ready": False, "message": "CrashLoopBackOff: exit 1"}],
        "Pods failed to become ready"
    )

    # Create event with attempts = 2 so 3rd attempt will trigger escalation
    event = RemediationEvent(
        application_id=test_app.id,
        environment_id="development",
        event_type="APPLICATION_UNHEALTHY",
        source="kubernetes",
        severity="HIGH",
        status="DETECTED",
        attempts=2,
        details="Persistent startup failure",
        created_at=utcnow(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    execution = remediation_engine.process_event(event.id, db)

    assert execution is not None
    assert execution.status == "FAILED"
    assert event.status == "ESCALATED"
    assert event.attempts == 3


def test_operator_approve_and_cancel_lifecycle(db, test_app):
    """Verify operator manual controls: approve and cancel."""
    event = RemediationEvent(
        application_id=test_app.id,
        environment_id="production",
        event_type="APPLICATION_UNHEALTHY",
        source="kubernetes",
        severity="HIGH",
        status="EVALUATING",
        created_at=utcnow(),
    )
    db.add(event)
    db.commit()

    # Operator approves
    approved = remediation_engine.approve_event(event.id, db)
    assert approved.status == "APPROVED"

    # Operator cancels
    cancelled = remediation_engine.cancel_event(event.id, db)
    assert cancelled.status == "CANCELLED"


# =============================================================================
# 3. REST API Endpoint Tests
# =============================================================================

def test_api_list_events(client, test_app):
    """Test GET /api/v1/remediation/events."""
    resp = client.get(f"/api/v1/remediation/events?application_id={test_app.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_api_get_event_detail(client, test_app, db):
    """Test GET /api/v1/remediation/events/{event_id}."""
    ev = RemediationEvent(
        application_id=test_app.id,
        environment_id="development",
        event_type="APPLICATION_UNAVAILABLE",
        status="DETECTED",
        details="Endpoint unreachable",
    )
    db.add(ev)
    db.commit()

    resp = client.get(f"/api/v1/remediation/events/{ev.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == ev.id
    assert resp.json()["event_type"] == "APPLICATION_UNAVAILABLE"


def test_api_create_manual_event(client, test_app):
    """Test POST /api/v1/remediation/events."""
    payload = {
        "application_id": test_app.id,
        "environment_id": "development",
        "event_type": "HIGH_ERROR_RATE",
        "source": "prometheus",
        "severity": "HIGH",
        "details": "5xx error rate exceeded 5% threshold",
    }
    resp = client.post("/api/v1/remediation/events", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["event_type"] == "HIGH_ERROR_RATE"
    assert data["status"] == "DETECTED"


def test_api_application_remediation_overview(client, test_app):
    """Test GET /api/v1/applications/{application_id}/remediation."""
    resp = client.get(f"/api/v1/applications/{test_app.id}/remediation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["application_id"] == test_app.id
    assert "active_events_count" in data
    assert "total_remediations" in data
    assert "policies" in data


def test_api_application_remediation_policies(client, test_app):
    """Test GET /api/v1/applications/{application_id}/remediation/policies."""
    resp = client.get(f"/api/v1/applications/{test_app.id}/remediation/policies")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_kubernetes_unavailable_resilience(db, test_app):
    """Scenario 11: Kubernetes cluster is unreachable -> remediation fails cleanly without crash."""
    with patch("app.services.remediation.action_service.kubernetes_client.rollout_restart_deployment") as mock_restart:
        from app.services.kubernetes.exceptions import KubernetesClusterUnavailableError
        mock_restart.side_effect = KubernetesClusterUnavailableError("Connection refused to API server")

        ev = RemediationEvent(
            application_id=test_app.id,
            environment_id="development",
            event_type="APPLICATION_UNHEALTHY",
            source="kubernetes",
            severity="HIGH",
            status="DETECTED",
            details="Health check failed",
            created_at=utcnow(),
        )
        db.add(ev)
        db.commit()

        execution = remediation_engine.process_event(ev.id, db)
        assert execution is not None
        assert execution.status == "FAILED"
        assert "Kubernetes rollout restart failed" in execution.error_message


def test_monitoring_unavailable_resilience(db):
    """Scenario 13: Monitoring/Prometheus unreachable -> scan gracefully continues without crash."""
    with patch("app.services.remediation.remediation_engine.kubernetes_client.get_pods_for_application") as mock_pods:
        mock_pods.side_effect = Exception("Prometheus/k8s timeout")
        # Should not raise exception
        detected = remediation_engine.scan_applications_health(db)
        assert isinstance(detected, list)


def test_invalid_remediation_policy(db, test_app):
    """Scenario 14: Invalid or unmapped policy -> event marked IGNORED."""
    ev = RemediationEvent(
        application_id=test_app.id,
        environment_id="development",
        event_type="UNKNOWN_UNSUPPORTED_TYPE",
        source="external",
        severity="LOW",
        status="DETECTED",
        details="Unknown alert",
        created_at=utcnow(),
    )
    db.add(ev)
    db.commit()

    exec_result = remediation_engine.process_event(ev.id, db)
    assert exec_result is None
    assert ev.status == "IGNORED"


def test_api_trigger_scan(client):
    """Test POST /api/v1/remediation/scan."""
    resp = client.post("/api/v1/remediation/scan")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "events_detected_count" in data

