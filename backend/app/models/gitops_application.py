from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.session import Base

def utcnow():
    return datetime.now(timezone.utc)

class GitOpsApplication(Base):
    """
    SQLAlchemy model representing a GitOps deployment mapped to an Argo CD Application.
    Tracks desired-state Git metadata and live Argo CD sync/health state.
    """
    __tablename__ = "gitops_applications"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    argocd_application_name = Column(String(100), unique=True, nullable=False, index=True)
    git_repository = Column(String(255), nullable=False)
    git_path = Column(String(255), nullable=False)
    target_revision = Column(String(50), nullable=False, default="main")
    namespace = Column(String(63), nullable=False, default="devforge")
    sync_status = Column(String(30), nullable=False, default="UNKNOWN", index=True)
    health_status = Column(String(30), nullable=False, default="UNKNOWN", index=True)
    auto_sync_enabled = Column(Boolean, nullable=False, default=False)
    self_heal_enabled = Column(Boolean, nullable=False, default=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    last_sync_revision = Column(String(100), nullable=True)
    sync_message = Column(Text, nullable=True)
    manifest_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    application = relationship("Application", back_populates="gitops_application")
    operations = relationship(
        "GitOpsOperation",
        back_populates="gitops_application",
        cascade="all, delete-orphan",
        order_by="desc(GitOpsOperation.created_at)"
    )

    __table_args__ = (
        Index("ix_gitops_app_sync_health", "sync_status", "health_status"),
    )
