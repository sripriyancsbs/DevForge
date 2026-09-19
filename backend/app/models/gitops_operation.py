from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.session import Base

def utcnow():
    return datetime.now(timezone.utc)

class GitOpsOperation(Base):
    """
    SQLAlchemy model tracking asynchronous GitOps tasks processed by the worker:
    ENABLE, SYNC, REFRESH, UPDATE_MANIFEST.
    """
    __tablename__ = "gitops_operations"

    id = Column(Integer, primary_key=True, index=True)
    gitops_application_id = Column(Integer, ForeignKey("gitops_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    operation_type = Column(String(50), nullable=False, index=True)  # ENABLE, SYNC, REFRESH, UPDATE_MANIFEST
    status = Column(String(30), nullable=False, default="PENDING", index=True)  # PENDING, RUNNING, SUCCESS, FAILED
    revision = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    gitops_application = relationship("GitOpsApplication", back_populates="operations")

    __table_args__ = (
        Index("ix_gitops_op_status_type", "status", "operation_type"),
    )
