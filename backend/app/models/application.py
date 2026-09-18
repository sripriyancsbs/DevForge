from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from app.db.session import Base

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    slug = Column(String(120), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    team = Column(String(100), nullable=False, default="Core Platform")
    runtime = Column(String(50), nullable=False, default="Python 3.12")
    repository_url = Column(String(255), nullable=False)
    branch = Column(String(100), nullable=False, default="main")
    environment = Column(String(50), nullable=False, default="production")
    version = Column(String(50), nullable=False, default="v1.0.0")
    status = Column(String(30), nullable=False, default="healthy") # healthy, degraded, failed, deploying, building
    port = Column(Integer, nullable=False, default=8000)
    replicas = Column(Integer, nullable=False, default=2)
    last_deployment_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deployments = relationship("Deployment", back_populates="application", cascade="all, delete-orphan")
