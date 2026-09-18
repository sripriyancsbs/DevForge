from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.application import Application
from app.models.deployment import Deployment
from app.models.environment import Environment
from app.models.service_health import ServiceHealth
from app.models.activity import Activity

def seed_database(db: Session):
    # Check if already seeded
    if db.query(Application).count() > 0:
        return

    now = datetime.utcnow()

    # 1. Seed Environments
    environments_data = [
        Environment(
            name="Production",
            slug="production",
            type="production",
            region="us-east-1 (N. Virginia)",
            cluster_endpoint="k8s.prod.devforge.internal",
            status="healthy",
            services_count=10,
            cpu_allocated="38 / 64 vCPUs",
            memory_allocated="96 / 128 GB",
            description="Primary production cluster hosting revenue-critical APIs and customer workloads."
        ),
        Environment(
            name="Staging",
            slug="staging",
            type="staging",
            region="us-east-2 (Ohio)",
            cluster_endpoint="k8s.staging.devforge.internal",
            status="healthy",
            services_count=8,
            cpu_allocated="14 / 32 vCPUs",
            memory_allocated="32 / 64 GB",
            description="Pre-production validation and integration testing environment mirroring production topology."
        ),
        Environment(
            name="Development",
            slug="development",
            type="development",
            region="us-west-2 (Oregon)",
            cluster_endpoint="k8s.dev.devforge.internal",
            status="healthy",
            services_count=6,
            cpu_allocated="8 / 24 vCPUs",
            memory_allocated="18 / 48 GB",
            description="Ephemeral feature branch deployments, team testing, and fast-feedback loop sandbox."
        ),
        Environment(
            name="Preview",
            slug="preview",
            type="preview",
            region="eu-central-1 (Frankfurt)",
            cluster_endpoint="k8s.preview.devforge.internal",
            status="healthy",
            services_count=3,
            cpu_allocated="4 / 16 vCPUs",
            memory_allocated="8 / 32 GB",
            description="Automated PR review environments spun down after pull requests merge."
        ),
    ]
    db.add_all(environments_data)
    db.commit()

    # 2. Seed Applications
    apps_data = [
        Application(
            name="payment-gateway",
            slug="payment-gateway",
            description="PCI-DSS compliant payment processing, Stripe integrations, and settlement dispatch.",
            team="Payments",
            runtime="Python 3.12 (FastAPI)",
            repository_url="https://github.com/devforge-org/payment-gateway",
            branch="main",
            environment="production",
            version="v2.14.0",
            status="healthy",
            port=8000,
            replicas=4,
            last_deployment_at=now - timedelta(minutes=18),
            created_at=now - timedelta(days=90)
        ),
        Application(
            name="auth-service",
            slug="auth-service",
            description="OAuth2/OIDC identity provider, session management, and RBAC policy enforcement engine.",
            team="Security",
            runtime="Go 1.22",
            repository_url="https://github.com/devforge-org/auth-service",
            branch="main",
            environment="production",
            version="v3.1.2",
            status="healthy",
            port=8080,
            replicas=3,
            last_deployment_at=now - timedelta(hours=2),
            created_at=now - timedelta(days=120)
        ),
        Application(
            name="inventory-api",
            slug="inventory-api",
            description="High-throughput real-time inventory ledger and warehouse stock allocation service.",
            team="Supply Chain",
            runtime="Python 3.12 (FastAPI)",
            repository_url="https://github.com/devforge-org/inventory-api",
            branch="main",
            environment="production",
            version="v1.8.5",
            status="degraded",
            port=8000,
            replicas=2,
            last_deployment_at=now - timedelta(hours=5),
            created_at=now - timedelta(days=45)
        ),
        Application(
            name="customer-dashboard",
            slug="customer-dashboard",
            description="Next-generation customer portal React SPA with client telemetry and billing management.",
            team="Frontend Infra",
            runtime="Node.js 20 (Vite)",
            repository_url="https://github.com/devforge-org/customer-dashboard",
            branch="main",
            environment="production",
            version="v4.0.1",
            status="healthy",
            port=80,
            replicas=3,
            last_deployment_at=now - timedelta(minutes=45),
            created_at=now - timedelta(days=60)
        ),
        Application(
            name="event-stream-ingestor",
            slug="event-stream-ingestor",
            description="Kafka event consumer and clickstream processor writing to long-term analytical storage.",
            team="Data Platform",
            runtime="Go 1.22",
            repository_url="https://github.com/devforge-org/event-stream-ingestor",
            branch="main",
            environment="production",
            version="v2.0.4",
            status="healthy",
            port=9092,
            replicas=6,
            last_deployment_at=now - timedelta(days=1),
            created_at=now - timedelta(days=80)
        ),
        Application(
            name="notification-worker",
            slug="notification-worker",
            description="Multi-channel notification dispatcher (Email via SES, SMS via Twilio, Webhooks, Push).",
            team="Core Platform",
            runtime="Python 3.12 (FastAPI)",
            repository_url="https://github.com/devforge-org/notification-worker",
            branch="main",
            environment="staging",
            version="v1.12.0",
            status="failed",
            port=8000,
            replicas=2,
            last_deployment_at=now - timedelta(minutes=32),
            created_at=now - timedelta(days=30)
        ),
        Application(
            name="recommendation-engine",
            slug="recommendation-engine",
            description="Vector search and personalized candidate reranking model inference microservice.",
            team="ML Engineering",
            runtime="Python 3.12",
            repository_url="https://github.com/devforge-org/recommendation-engine",
            branch="develop",
            environment="staging",
            version="v0.9.3",
            status="deploying",
            port=8000,
            replicas=2,
            last_deployment_at=now - timedelta(minutes=3),
            created_at=now - timedelta(days=14)
        ),
        Application(
            name="checkout-service",
            slug="checkout-service",
            description="Shopping cart orchestration, discount validation, and tax calculation backend.",
            team="Payments",
            runtime="Node.js 20",
            repository_url="https://github.com/devforge-org/checkout-service",
            branch="main",
            environment="production",
            version="v2.4.0",
            status="healthy",
            port=3000,
            replicas=4,
            last_deployment_at=now - timedelta(hours=6),
            created_at=now - timedelta(days=110)
        ),
    ]
    db.add_all(apps_data)
    db.commit()

    # 3. Seed Deployments
    payment_app = db.query(Application).filter(Application.slug == "payment-gateway").first()
    auth_app = db.query(Application).filter(Application.slug == "auth-service").first()
    notif_app = db.query(Application).filter(Application.slug == "notification-worker").first()
    rec_app = db.query(Application).filter(Application.slug == "recommendation-engine").first()
    cust_app = db.query(Application).filter(Application.slug == "customer-dashboard").first()
    inv_app = db.query(Application).filter(Application.slug == "inventory-api").first()

    deployments_data = [
        Deployment(
            application_id=rec_app.id,
            application_name="recommendation-engine",
            version="v0.9.3",
            commit_hash="7f3c2a1",
            commit_message="feat(ranking): update cosine similarity score threshold",
            environment="staging",
            status="deploying",
            duration="32s",
            triggered_by="sarah.ml",
            logs="[00:00:01] Pulling base image python:3.12-slim...\n[00:00:12] Running unit test suite (34 passed)...\n[00:00:25] Pushing container to internal registry...\n[00:00:32] Applying rolling update deployment...",
            created_at=now - timedelta(minutes=3)
        ),
        Deployment(
            application_id=payment_app.id,
            application_name="payment-gateway",
            version="v2.14.0",
            commit_hash="c84e190",
            commit_message="fix(stripe): handle idempotency key race condition",
            environment="production",
            status="healthy",
            duration="1m 12s",
            triggered_by="alex.sre",
            logs="[00:00:01] Git checkout commit c84e190\n[00:00:15] Building multi-stage Dockerfile\n[00:00:40] Running database migration check: 0 pending\n[00:01:05] Healthcheck probes responding HTTP 200 on /healthz\n[00:01:12] Deployment succeeded.",
            created_at=now - timedelta(minutes=18)
        ),
        Deployment(
            application_id=notif_app.id,
            application_name="notification-worker",
            version="v1.12.0",
            commit_hash="a19b882",
            commit_message="refactor(sqs): increase batch size from 10 to 50",
            environment="staging",
            status="failed",
            duration="54s",
            triggered_by="ci-pipeline",
            logs="[00:00:01] Triggered by push to staging branch\n[00:00:20] Docker container build finished\n[00:00:45] Healthcheck probe failed: Connection refused to redis-cluster:6379\n[00:00:54] Deployment marked FAILED. Pod entered CrashLoopBackOff.",
            created_at=now - timedelta(minutes=32)
        ),
        Deployment(
            application_id=cust_app.id,
            application_name="customer-dashboard",
            version="v4.0.1",
            commit_hash="99d21bc",
            commit_message="chore: upgrade react-router-dom to v6.22",
            environment="production",
            status="healthy",
            duration="48s",
            triggered_by="dave.frontend",
            logs="[00:00:01] Building Vite production bundle\n[00:00:28] Static assets optimized (gzip size: 218kb)\n[00:00:48] Deployed to Nginx edge pods successfully.",
            created_at=now - timedelta(minutes=45)
        ),
        Deployment(
            application_id=auth_app.id,
            application_name="auth-service",
            version="v3.1.2",
            commit_hash="3e7f00d",
            commit_message="perf: cache public JWKS keys in memory",
            environment="production",
            status="healthy",
            duration="39s",
            triggered_by="elena.sec",
            logs="[00:00:01] Go build binary completed\n[00:00:18] Container scan clean (0 vulnerabilities)\n[00:00:39] Production rollout complete.",
            created_at=now - timedelta(hours=2)
        ),
        Deployment(
            application_id=inv_app.id,
            application_name="inventory-api",
            version="v1.8.4",
            commit_hash="55a2981",
            commit_message="rollback: revert unindexed query on warehouse_skus",
            environment="production",
            status="rolled_back",
            duration="22s",
            triggered_by="alex.sre",
            logs="[00:00:01] Automated rollback initiated due to high p99 latency\n[00:00:10] Reverting image tag to v1.8.4\n[00:00:22] Traffic restored to previous revision.",
            created_at=now - timedelta(hours=5)
        )
    ]
    db.add_all(deployments_data)
    db.commit()

    # 4. Seed Service Health
    health_data = [
        ServiceHealth(
            service_name="payment-gateway",
            status="healthy",
            cpu_percent=14.2,
            memory_mb="340 MB",
            requests_per_sec=420,
            error_rate="0.00%",
            uptime="99.99%"
        ),
        ServiceHealth(
            service_name="auth-service",
            status="healthy",
            cpu_percent=8.5,
            memory_mb="128 MB",
            requests_per_sec=890,
            error_rate="0.01%",
            uptime="100.00%"
        ),
        ServiceHealth(
            service_name="inventory-api",
            status="warning",
            cpu_percent=82.4,
            memory_mb="1,420 MB",
            requests_per_sec=310,
            error_rate="1.42%",
            uptime="99.65%"
        ),
        ServiceHealth(
            service_name="customer-dashboard",
            status="healthy",
            cpu_percent=4.1,
            memory_mb="85 MB",
            requests_per_sec=640,
            error_rate="0.00%",
            uptime="99.99%"
        ),
        ServiceHealth(
            service_name="event-stream-ingestor",
            status="healthy",
            cpu_percent=26.8,
            memory_mb="780 MB",
            requests_per_sec=2150,
            error_rate="0.02%",
            uptime="99.98%"
        ),
        ServiceHealth(
            service_name="notification-worker",
            status="failed",
            cpu_percent=0.0,
            memory_mb="0 MB",
            requests_per_sec=0,
            error_rate="100.00%",
            uptime="94.20%"
        ),
    ]
    db.add_all(health_data)
    db.commit()

    # 5. Seed Activities
    activity_data = [
        Activity(
            actor="alex.sre",
            action="Deployment completed",
            target="payment-gateway",
            target_type="application",
            status="completed",
            details="Successfully deployed version v2.14.0 to production",
            created_at=now - timedelta(minutes=18)
        ),
        Activity(
            actor="ci-pipeline",
            action="Deployment failed",
            target="notification-worker",
            target_type="application",
            status="failed",
            details="Healthcheck timeout on staging cluster: Redis connection refused",
            created_at=now - timedelta(minutes=32)
        ),
        Activity(
            actor="dave.frontend",
            action="Deployment completed",
            target="customer-dashboard",
            target_type="application",
            status="completed",
            details="Deployed release v4.0.1 with React router upgrades",
            created_at=now - timedelta(minutes=45)
        ),
        Activity(
            actor="marcus.lead",
            action="Application created",
            target="recommendation-engine",
            target_type="application",
            status="completed",
            details="Registered new ML inference microservice using Python FastAPI template",
            created_at=now - timedelta(hours=3)
        ),
        Activity(
            actor="alex.sre",
            action="Rollback completed",
            target="inventory-api",
            target_type="application",
            status="warning",
            details="Rolled back v1.8.5 to v1.8.4 due to unindexed database query spike",
            created_at=now - timedelta(hours=5)
        ),
        Activity(
            actor="devops.infra",
            action="Environment created",
            target="preview",
            target_type="environment",
            status="completed",
            details="Provisioned eu-central-1 preview cluster for transient pull request testing",
            created_at=now - timedelta(days=2)
        ),
    ]
    db.add_all(activity_data)
    db.commit()
