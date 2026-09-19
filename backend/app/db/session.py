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
        "CREATE INDEX IF NOT EXISTS ix_applications_image_status ON applications (image_status);"
    ]
    try:
        with engine.begin() as conn:
            for stmt in migration_statements:
                conn.execute(text(stmt))
        logger.info("DevForge PostgreSQL schema migrations (Phase 2, 3, 4 & 5) applied successfully.")
    except Exception as e:
        logger.warning(f"Note on migrations (table may not exist yet if fresh DB): {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
