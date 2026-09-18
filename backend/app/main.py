import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.session import engine, Base, SessionLocal
from app.db.seed import seed_database
from app.api.api_v1 import overview, applications, deployments, environments, activity, infrastructure, monitoring

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("devforge")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and seed realistic platform data
    logger.info("Initializing DevForge database tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        seed_database(db)
        logger.info("DevForge database successfully seeded with platform data.")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
    finally:
        db.close()
    yield
    # Shutdown
    logger.info("DevForge API shutting down...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    lifespan=lifespan
)

# Set CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoint
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "DevForge API",
        "environment": settings.ENVIRONMENT,
        "database": "connected"
    }

# Register API Routers
app.include_router(overview.router, prefix=f"{settings.API_V1_STR}/overview", tags=["overview"])
app.include_router(applications.router, prefix=f"{settings.API_V1_STR}/applications", tags=["applications"])
app.include_router(deployments.router, prefix=f"{settings.API_V1_STR}/deployments", tags=["deployments"])
app.include_router(environments.router, prefix=f"{settings.API_V1_STR}/environments", tags=["environments"])
app.include_router(activity.router, prefix=f"{settings.API_V1_STR}/activity", tags=["activity"])
app.include_router(infrastructure.router, prefix=f"{settings.API_V1_STR}/infrastructure", tags=["infrastructure"])
app.include_router(monitoring.router, prefix=f"{settings.API_V1_STR}/monitoring", tags=["monitoring"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.BACKEND_HOST, port=settings.BACKEND_PORT, reload=True)
