from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.orm import relationship
from app.db.session import Base

def utcnow():
    return datetime.now(timezone.utc)

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    slug = Column(String(120), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    team = Column(String(100), nullable=False, default="Platform Engineering", index=True)
    runtime = Column(String(50), nullable=False, default="Python 3.12 (FastAPI)")
    repository_url = Column(String(255), nullable=False)
    repository_owner = Column(String(100), nullable=True)
    repository_name = Column(String(100), nullable=True)
    repository_default_branch = Column(String(100), nullable=False, default="main")
    branch = Column(String(100), nullable=False, default="main")
    environment = Column(String(50), nullable=False, default="production", index=True)
    version = Column(String(50), nullable=False, default="v1.0.0")
    status = Column(String(30), nullable=False, default="healthy", index=True)
    port = Column(Integer, nullable=False, default=8000)
    replicas = Column(Integer, nullable=False, default=2)
    template = Column(String(100), nullable=True, index=True)
    database_type = Column(String(50), nullable=False, default="none")
    deployment_strategy = Column(String(50), nullable=False, default="rolling")
    provisioning_status = Column(String(30), nullable=False, default="READY", index=True)
    provisioning_error = Column(Text, nullable=True)
    generated_path = Column(String(255), nullable=True)
    manifest_yaml = Column(Text, nullable=True)
    last_deployment_at = Column(DateTime(timezone=True), default=utcnow)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    deployments = relationship(
        "Deployment",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="desc(Deployment.created_at)"
    )
    service_health = relationship(
        "ServiceHealth",
        back_populates="application",
        uselist=False,
        cascade="all, delete-orphan"
    )
    provisioning_jobs = relationship(
        "ProvisioningJob",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="desc(ProvisioningJob.created_at)"
    )

    __table_args__ = (
        Index("ix_applications_status_env", "status", "environment"),
    )
