import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from app.core.config import settings
from app.db.session import engine, Base, SessionLocal, verify_connection, run_phase2_migrations
import app.models  # Ensures all SQLAlchemy models are registered
from app.db.seed import seed_database
from app.api.api_v1 import (
    overview,
    applications,
    deployments,
    environments,
    activity,
    infrastructure,
    monitoring,
    provisioning,
    integrations,
    kubernetes_deployments,
    ansible,
    gitops,
    remediation,
    auth,
    templates,
    workspaces,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("devforge")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Strictly verify PostgreSQL connectivity - fail loudly if unreachable
    logger.info("Verifying PostgreSQL database connectivity...")
    verify_connection()
    
    # 2. Initialize DevForge database schema in PostgreSQL
    logger.info("Creating DevForge tables in PostgreSQL if not present...")
    Base.metadata.create_all(bind=engine)
    run_phase2_migrations()
    
    # 3. Seed initial platform dataset
    db = SessionLocal()
    try:
        seed_database(db)
        logger.info("DevForge PostgreSQL database verified and seeded successfully.")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        raise RuntimeError(f"Database initialization failed: {e}") from e
    finally:
        db.close()

    yield
    logger.info("DevForge API shutting down...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="DevForge Internal Developer Platform (IDP) Core REST API",
    version="0.1.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    lifespan=lifespan
)

# Custom validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = ".".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        errors.append({"field": field, "message": msg})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": errors}
    )

# Production-safe global exception handler (never leaks stack traces or DB details)
@app.exception_handler(Exception)
async def global_unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Internal server error processing {request.method} {request.url.path}: {exc}",
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. The incident has been recorded.",
            "error_code": "INTERNAL_SERVER_ERROR",
            "status": 500
        }
    )

from starlette.responses import Response
from app.core.metrics import (
    PrometheusMiddleware,
    generate_latest,
    CONTENT_TYPE_LATEST,
    record_postgres_health,
)

# Set CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus request instrumentation
app.add_middleware(PrometheusMiddleware)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' *; "
        "frame-ancestors 'none';"
    )
    return response

# Liveness Probe
@app.get("/healthz", tags=["health"])
@app.get("/live", tags=["health"])
def liveness():
    """Liveness probe confirming the API process is alive."""
    return {"status": "alive", "service": "DevForge API"}

# Readiness Probe
@app.get("/ready", tags=["health"])
def readiness():
    """Readiness probe actively verifying PostgreSQL connectivity."""
    try:
        verify_connection()
        record_postgres_health(True)
        return {
            "status": "ready",
            "service": "DevForge API",
            "environment": settings.ENVIRONMENT,
            "database": "connected"
        }
    except Exception as e:
        record_postgres_health(False)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "service": "DevForge API",
                "database": "unavailable"
            }
        )

# Backward-compatible health endpoint
@app.get("/health", tags=["health"])
def health():
    try:
        verify_connection()
        db_status = "connected"
        record_postgres_health(True)
    except Exception as e:
        record_postgres_health(False)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "degraded",
                "service": "DevForge API",
                "database": "disconnected",
                "environment": settings.ENVIRONMENT
            }
        )
    return {
        "status": "healthy",
        "service": "DevForge API",
        "environment": settings.ENVIRONMENT,
        "database": db_status
    }

# Prometheus Metrics Scrape Endpoint
@app.get("/metrics")
def metrics():
    try:
        verify_connection()
        record_postgres_health(True)
    except Exception:
        record_postgres_health(False)
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Register API Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["authentication"])
app.include_router(overview.router, prefix=f"{settings.API_V1_STR}/overview", tags=["overview"])
app.include_router(applications.router, prefix=f"{settings.API_V1_STR}/applications", tags=["applications"])
app.include_router(deployments.router, prefix=f"{settings.API_V1_STR}/deployments", tags=["deployments"])
app.include_router(environments.router, prefix=f"{settings.API_V1_STR}/environments", tags=["environments"])
app.include_router(activity.router, prefix=f"{settings.API_V1_STR}/activity", tags=["activity"])
app.include_router(infrastructure.router, prefix=f"{settings.API_V1_STR}/infrastructure", tags=["infrastructure"])
app.include_router(monitoring.router, prefix=f"{settings.API_V1_STR}/monitoring", tags=["monitoring"])
app.include_router(provisioning.router, prefix=f"{settings.API_V1_STR}/provisioning", tags=["provisioning"])
app.include_router(integrations.router, prefix=f"{settings.API_V1_STR}/integrations", tags=["integrations"])
app.include_router(kubernetes_deployments.router, prefix=settings.API_V1_STR, tags=["kubernetes"])
app.include_router(ansible.router, prefix=f"{settings.API_V1_STR}/ansible", tags=["ansible"])
app.include_router(gitops.router, prefix=settings.API_V1_STR, tags=["gitops"])
app.include_router(remediation.router, prefix=f"{settings.API_V1_STR}/remediation", tags=["remediation"])
app.include_router(remediation.router, prefix=settings.API_V1_STR, tags=["remediation-alias"])
app.include_router(templates.router, prefix=f"{settings.API_V1_STR}/templates", tags=["templates"])
app.include_router(workspaces.router, prefix=f"{settings.API_V1_STR}/workspaces", tags=["workspaces"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.BACKEND_HOST, port=settings.BACKEND_PORT, reload=True)
