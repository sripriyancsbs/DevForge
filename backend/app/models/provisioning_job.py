from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.session import Base

def utcnow():
    return datetime.now(timezone.utc)

class ProvisioningJob(Base):
    __tablename__ = "provisioning_jobs"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="PENDING", index=True)  # PENDING, PROVISIONING, VALIDATING, READY, FAILED, RETRY
    template = Column(String(100), nullable=False)
    current_step = Column(String(50), nullable=False, default="VALIDATE_CONFIGURATION")  # VALIDATE_CONFIGURATION, PREPARE_WORKSPACE, GENERATE_PROJECT, GENERATE_MANIFEST, GENERATING_CI_WORKFLOW, VALIDATE_PROJECT, CREATING_REPOSITORY, PUSHING_REPOSITORY, COMPLETED
    attempt = Column(Integer, nullable=False, default=1)
    max_attempts = Column(Integer, nullable=False, default=3)
    is_retryable = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    payload_snapshot = Column(Text, nullable=True)  # JSON serialized input
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    application = relationship("Application", back_populates="provisioning_jobs")

    __table_args__ = (
        Index("ix_provisioning_jobs_queue", "status", "created_at"),
    )
