import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

logger = logging.getLogger("devforge.db")

Base = declarative_base()

def get_engine():
    db_url = settings.DATABASE_URL
    # If using postgresql, try connecting; if it fails in local dev without docker, fallback to sqlite
    if db_url.startswith("postgresql"):
        try:
            # Test engine creation
            engine = create_engine(db_url, pool_pre_ping=True)
            with engine.connect() as conn:
                logger.info("Connected to PostgreSQL successfully.")
            return engine
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed ({e}). Falling back to local SQLite database.")
            return create_engine("sqlite:///./devforge.db", connect_args={"check_same_thread": False})
    elif db_url.startswith("sqlite"):
        return create_engine(db_url, connect_args={"check_same_thread": False})
    else:
        return create_engine(db_url)

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
