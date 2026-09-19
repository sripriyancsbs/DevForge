import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

logger = logging.getLogger("devforge.db")

Base = declarative_base()

def init_postgres_engine():
    db_url = settings.DATABASE_URL
    if not db_url or not db_url.strip():
        raise RuntimeError(
            "FATAL: DATABASE_URL environment variable is not configured. "
            "DevForge strictly requires a PostgreSQL database connection string. "
            "Example: postgresql://devforge:password@postgres:5432/devforge_db"
        )

    # Validate that it is PostgreSQL
    normalized_url = db_url.strip().lower()
    if not (normalized_url.startswith("postgresql://") or normalized_url.startswith("postgresql+psycopg2://") or normalized_url.startswith("postgres://")):
        scheme = db_url.split("://")[0] if "://" in db_url else "unknown"
        raise ValueError(
            f"FATAL: Unsupported database scheme '{scheme}'. "
            "DevForge requires PostgreSQL (postgresql://...). SQLite and other fallbacks are disabled."
        )

    try:
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
        return engine
    except Exception as e:
        safe_url = db_url.split("@")[-1] if "@" in db_url else db_url
        raise RuntimeError(
            f"FATAL: Failed to initialize PostgreSQL engine for target '@{safe_url}'. Error: {e}"
        ) from e

engine = init_postgres_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def verify_connection():
    """Verify that PostgreSQL is reachable and execute a ping test."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("PostgreSQL database connection verified successfully.")
        return True
    except Exception as e:
        safe_url = settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL
        err_msg = (
            f"FATAL: Cannot connect to PostgreSQL database at '@{safe_url}'. "
            f"Details: {e}\n"
            f"Ensure the PostgreSQL service is running and credentials match your configuration."
        )
        logger.error(err_msg)
        raise RuntimeError(err_msg) from e

def run_phase2_migrations():
    """Apply non-destructive schema migrations in PostgreSQL for Phase 2 columns."""
    migration_statements = [
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS template VARCHAR(100);",
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS database_type VARCHAR(50) DEFAULT 'none' NOT NULL;",
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS deployment_strategy VARCHAR(50) DEFAULT 'rolling' NOT NULL;",
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS provisioning_status VARCHAR(30) DEFAULT 'READY' NOT NULL;",
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS provisioning_error TEXT;",
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS generated_path VARCHAR(255);",
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS manifest_yaml TEXT;",
        "CREATE INDEX IF NOT EXISTS ix_applications_template ON applications (template);",
        "CREATE INDEX IF NOT EXISTS ix_applications_provisioning_status ON applications (provisioning_status);",
        """CREATE TABLE IF NOT EXISTS provisioning_jobs (
            id SERIAL PRIMARY KEY,
            application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
            status VARCHAR(30) DEFAULT 'PENDING' NOT NULL,
            template VARCHAR(100) NOT NULL,
            current_step VARCHAR(50) DEFAULT 'VALIDATE_CONFIGURATION' NOT NULL,
            attempt INTEGER DEFAULT 1 NOT NULL,
            max_attempts INTEGER DEFAULT 3 NOT NULL,
            is_retryable BOOLEAN DEFAULT TRUE NOT NULL,
            error_message TEXT,
            payload_snapshot TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ
        );""",
        "CREATE INDEX IF NOT EXISTS ix_provisioning_jobs_app_id ON provisioning_jobs (application_id);",
        "CREATE INDEX IF NOT EXISTS ix_provisioning_jobs_status ON provisioning_jobs (status);",
        "CREATE INDEX IF NOT EXISTS ix_provisioning_jobs_queue ON provisioning_jobs (status, created_at);",
        # Phase 3 Migrations: GitHub Integration repository columns
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS repository_owner VARCHAR(100);",
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS repository_name VARCHAR(100);",
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS repository_default_branch VARCHAR(100) DEFAULT 'main' NOT NULL;",
        # Phase 4 Migrations: CI/CD GitHub Actions columns
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS ci_status VARCHAR(30) DEFAULT 'UNKNOWN' NOT NULL;",
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS ci_workflow VARCHAR(100) DEFAULT 'CI';",
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS ci_run_id VARCHAR(100);",
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS ci_run_url VARCHAR(255);",
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS ci_last_run_at TIMESTAMPTZ;",
        "CREATE INDEX IF NOT EXISTS ix_applications_ci_status ON applications (ci_status);",
        # Phase 5 Migrations: Container Image Management (GHCR)
        """CREATE TABLE IF NOT EXISTS container_images (
            id SERIAL PRIMARY KEY,
            application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
            registry VARCHAR(100) DEFAULT 'ghcr.io' NOT NULL,
            image_repository VARCHAR(255) NOT NULL,
            image_tag VARCHAR(128) NOT NULL,
            image_digest VARCHAR(255),
            commit_sha VARCHAR(100),
            status VARCHAR(30) DEFAULT 'PENDING' NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );""",
        "CREATE INDEX IF NOT EXISTS ix_container_images_app_id ON container_images (application_id);",
        "CREATE INDEX IF NOT EXISTS ix_container_images_repo ON container_images (image_repository);",
        "CREATE INDEX IF NOT EXISTS ix_container_images_status ON container_images (status);",
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS image_repository VARCHAR(255);",
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS image_tag VARCHAR(128);",
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS image_digest VARCHAR(255);",
        "ALTER TABLE applications ADD COLUMN IF NOT EXISTS image_status VARCHAR(30) DEFAULT 'PENDING' NOT NULL;",
        "CREATE INDEX IF NOT EXISTS ix_applications_image_status ON applications (image_status);",
        # Phase 6 Migrations: Kubernetes Deployments
        """CREATE TABLE IF NOT EXISTS kubernetes_deployments (
            id SERIAL PRIMARY KEY,
            application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
            environment VARCHAR(50) DEFAULT 'development' NOT NULL,
            namespace VARCHAR(63) DEFAULT 'devforge' NOT NULL,
            deployment_name VARCHAR(100) NOT NULL,
            service_name VARCHAR(100) NOT NULL,
            image_repository VARCHAR(255) NOT NULL,
            image_tag VARCHAR(128) NOT NULL,
            replicas INTEGER DEFAULT 1 NOT NULL,
            ready_replicas INTEGER DEFAULT 0 NOT NULL,
            status VARCHAR(30) DEFAULT 'PENDING' NOT NULL,
            port INTEGER DEFAULT 8000 NOT NULL,
            node_port INTEGER,
            manifest_yaml TEXT,
            error_message TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );""",
        "CREATE INDEX IF NOT EXISTS ix_k8s_deploy_app_status ON kubernetes_deployments (application_id, status);",
        "CREATE INDEX IF NOT EXISTS ix_k8s_deploy_name_ns ON kubernetes_deployments (deployment_name, namespace);",
        "CREATE INDEX IF NOT EXISTS ix_k8s_deploy_status ON kubernetes_deployments (status);",
        # Phase 7 Migrations: Terraform Infrastructure Runs
        """CREATE TABLE IF NOT EXISTS terraform_runs (
            id SERIAL PRIMARY KEY,
            environment VARCHAR(50) DEFAULT 'development' NOT NULL,
            operation VARCHAR(30) NOT NULL,
            status VARCHAR(30) DEFAULT 'PENDING' NOT NULL,
            plan_output TEXT,
            apply_output TEXT,
            resources_count INTEGER DEFAULT 0 NOT NULL,
            error_message TEXT,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );""",
        "CREATE INDEX IF NOT EXISTS ix_terraform_runs_env_status ON terraform_runs (environment, status);",
        "CREATE INDEX IF NOT EXISTS ix_terraform_runs_status ON terraform_runs (status);",
        # Phase 8 Migrations: Ansible Automation Executions
        """CREATE TABLE IF NOT EXISTS ansible_executions (
            id SERIAL PRIMARY KEY,
            application_id INTEGER REFERENCES applications(id) ON DELETE SET NULL,
            environment_id VARCHAR(50) DEFAULT 'development' NOT NULL,
            playbook_name VARCHAR(100) NOT NULL,
            status VARCHAR(30) DEFAULT 'PENDING' NOT NULL,
            output TEXT,
            error_output TEXT,
            return_code INTEGER,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );""",
        "CREATE INDEX IF NOT EXISTS ix_ansible_executions_app_id ON ansible_executions (application_id);",
        "CREATE INDEX IF NOT EXISTS ix_ansible_executions_status ON ansible_executions (status);",
        "CREATE INDEX IF NOT EXISTS ix_ansible_executions_queue ON ansible_executions (status, created_at);",
        # Phase 10 Migrations: GitOps Applications & Operations (Argo CD)
        """CREATE TABLE IF NOT EXISTS gitops_applications (
            id SERIAL PRIMARY KEY,
            application_id INTEGER UNIQUE NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
            argocd_application_name VARCHAR(100) UNIQUE NOT NULL,
            git_repository VARCHAR(255) NOT NULL,
            git_path VARCHAR(255) NOT NULL,
            target_revision VARCHAR(50) DEFAULT 'main' NOT NULL,
            namespace VARCHAR(63) DEFAULT 'devforge' NOT NULL,
            sync_status VARCHAR(30) DEFAULT 'UNKNOWN' NOT NULL,
            health_status VARCHAR(30) DEFAULT 'UNKNOWN' NOT NULL,
            auto_sync_enabled BOOLEAN DEFAULT FALSE NOT NULL,
            self_heal_enabled BOOLEAN DEFAULT FALSE NOT NULL,
            last_synced_at TIMESTAMPTZ,
            last_sync_revision VARCHAR(100),
            sync_message TEXT,
            manifest_version INTEGER DEFAULT 1 NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );""",
        "CREATE INDEX IF NOT EXISTS ix_gitops_app_id ON gitops_applications (application_id);",
        "CREATE INDEX IF NOT EXISTS ix_gitops_app_name ON gitops_applications (argocd_application_name);",
        "CREATE INDEX IF NOT EXISTS ix_gitops_app_sync_health ON gitops_applications (sync_status, health_status);",
        """CREATE TABLE IF NOT EXISTS gitops_operations (
            id SERIAL PRIMARY KEY,
            gitops_application_id INTEGER NOT NULL REFERENCES gitops_applications(id) ON DELETE CASCADE,
            operation_type VARCHAR(50) NOT NULL,
            status VARCHAR(30) DEFAULT 'PENDING' NOT NULL,
            revision VARCHAR(100),
            details TEXT,
            error TEXT,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );""",
        "CREATE INDEX IF NOT EXISTS ix_gitops_op_app_id ON gitops_operations (gitops_application_id);",
        "CREATE INDEX IF NOT EXISTS ix_gitops_op_status_type ON gitops_operations (status, operation_type);",
        "CREATE INDEX IF NOT EXISTS ix_gitops_op_queue ON gitops_operations (status, created_at);",

        # Phase 11 Migrations: Self-Healing & Automated Remediation
        """CREATE TABLE IF NOT EXISTS remediation_policies (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            environment VARCHAR(50) DEFAULT 'all' NOT NULL,
            action VARCHAR(50) NOT NULL,
            enabled BOOLEAN DEFAULT TRUE NOT NULL,
            max_attempts INTEGER DEFAULT 3 NOT NULL,
            cooldown_seconds INTEGER DEFAULT 300 NOT NULL,
            requires_approval BOOLEAN DEFAULT FALSE NOT NULL,
            description TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );""",
        "CREATE INDEX IF NOT EXISTS ix_rem_policy_name ON remediation_policies (name);",
        "CREATE INDEX IF NOT EXISTS ix_rem_policy_type_env ON remediation_policies (event_type, environment);",
        "CREATE INDEX IF NOT EXISTS ix_rem_policy_action ON remediation_policies (action);",

        """CREATE TABLE IF NOT EXISTS remediation_events (
            id SERIAL PRIMARY KEY,
            application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
            environment_id VARCHAR(50) DEFAULT 'development' NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            source VARCHAR(50) DEFAULT 'kubernetes' NOT NULL,
            severity VARCHAR(20) DEFAULT 'MEDIUM' NOT NULL,
            status VARCHAR(30) DEFAULT 'DETECTED' NOT NULL,
            detected_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
            details TEXT,
            attempts INTEGER DEFAULT 0 NOT NULL,
            resolved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );""",
        "CREATE INDEX IF NOT EXISTS ix_rem_events_app_status ON remediation_events (application_id, status);",
        "CREATE INDEX IF NOT EXISTS ix_rem_events_queue ON remediation_events (status, created_at);",
        "CREATE INDEX IF NOT EXISTS ix_rem_events_app_env ON remediation_events (application_id, environment_id);",
        "CREATE INDEX IF NOT EXISTS ix_rem_events_event_type ON remediation_events (event_type);",

        """CREATE TABLE IF NOT EXISTS remediation_executions (
            id SERIAL PRIMARY KEY,
            event_id INTEGER NOT NULL REFERENCES remediation_events(id) ON DELETE CASCADE,
            application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
            environment_id VARCHAR(50) DEFAULT 'development' NOT NULL,
            policy_id INTEGER REFERENCES remediation_policies(id) ON DELETE SET NULL,
            action VARCHAR(50) NOT NULL,
            status VARCHAR(30) DEFAULT 'PENDING' NOT NULL,
            attempt INTEGER DEFAULT 1 NOT NULL,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            result TEXT,
            error_message TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );""",
        "CREATE INDEX IF NOT EXISTS ix_rem_exec_event_status ON remediation_executions (event_id, status);",
        "CREATE INDEX IF NOT EXISTS ix_rem_exec_app_env ON remediation_executions (application_id, environment_id);",
        "CREATE INDEX IF NOT EXISTS ix_rem_exec_created ON remediation_executions (created_at);",

        # Phase 12 Migrations: User Authentication and RBAC
        """CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            role VARCHAR(20) DEFAULT 'VIEWER' NOT NULL,
            is_active BOOLEAN DEFAULT TRUE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
        );""",
        "CREATE INDEX IF NOT EXISTS ix_users_username ON users (username);",
        "CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);",
        "CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);"
    ]
    try:
        with engine.begin() as conn:
            for stmt in migration_statements:
                conn.execute(text(stmt))

            # Seed default remediation policies if empty
            count = conn.execute(text("SELECT count(*) FROM remediation_policies")).scalar()
            if count == 0:
                baseline_policies = [
                    ("auto_restart_unhealthy", "APPLICATION_UNHEALTHY", "all", "KUBERNETES_ROLLOUT_RESTART", True, 3, 300, False, "Automatically restart Kubernetes deployment when continuous health probes fail"),
                    ("auto_restart_crashloop", "POD_CRASH_LOOP", "all", "KUBERNETES_ROLLOUT_RESTART", True, 3, 300, False, "Perform controlled rolling restart on pod CrashLoopBackOff"),
                    ("gitops_sync_drift", "GITOPS_OUT_OF_SYNC", "all", "ARGOCD_SYNC", True, 2, 180, False, "Request Argo CD reconciliation sync when GitOps drift is detected"),
                    ("retry_transient_deploy", "DEPLOYMENT_FAILED", "development", "RETRY_TRANSIENT_OPERATION", True, 2, 120, False, "Safely retry failed transient deployments in development environment"),
                    ("prod_approval_restart", "APPLICATION_UNHEALTHY", "production", "KUBERNETES_ROLLOUT_RESTART", True, 2, 600, True, "Require manual operator approval for workload restarts in production"),
                ]
                for p_name, p_event, p_env, p_action, p_en, p_att, p_cool, p_appr, p_desc in baseline_policies:
                    conn.execute(
                        text("""INSERT INTO remediation_policies 
                        (name, event_type, environment, action, enabled, max_attempts, cooldown_seconds, requires_approval, description, created_at, updated_at)
                        VALUES (:name, :event_type, :environment, :action, :enabled, :max_attempts, :cooldown_seconds, :requires_approval, :description, NOW(), NOW())
                        ON CONFLICT (name) DO NOTHING;"""),
                        {
                            "name": p_name,
                            "event_type": p_event,
                            "environment": p_env,
                            "action": p_action,
                            "enabled": p_en,
                            "max_attempts": p_att,
                            "cooldown_seconds": p_cool,
                            "requires_approval": p_appr,
                            "description": p_desc,
                        }
                    )
        logger.info("DevForge PostgreSQL schema migrations (Phase 2-12) applied successfully.")
    except Exception as e:
        logger.warning(f"Note on migrations (table may not exist yet if fresh DB): {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
