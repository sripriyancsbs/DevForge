from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from app.db.session import Base


def utcnow():
    return datetime.now(timezone.utc)


class RemediationPolicy(Base):
    __tablename__ = "remediation_policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    # Target environment: 'all', 'development', 'staging', 'production'
    environment = Column(String(50), nullable=False, default="all", index=True)
    # Action allowlist: KUBERNETES_ROLLOUT_RESTART, KUBERNETES_REDEPLOY, ARGOCD_SYNC, RETRY_TRANSIENT_OPERATION
    action = Column(String(50), nullable=False, index=True)
    enabled = Column(Boolean, nullable=False, default=True)
    max_attempts = Column(Integer, nullable=False, default=3)
    cooldown_seconds = Column(Integer, nullable=False, default=300)
    requires_approval = Column(Boolean, nullable=False, default=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    executions = relationship("RemediationExecution", back_populates="policy")

    __table_args__ = (
        Index("ix_rem_policy_type_env", "event_type", "environment"),
    )


class RemediationEvent(Base):
    __tablename__ = "remediation_events"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    environment_id = Column(String(50), nullable=False, default="development", index=True)
    # Event types: APPLICATION_UNHEALTHY, APPLICATION_UNAVAILABLE, POD_CRASH_LOOP, DEPLOYMENT_FAILED, DEPLOYMENT_STUCK, GITOPS_OUT_OF_SYNC, HIGH_ERROR_RATE
    event_type = Column(String(50), nullable=False, index=True)
    source = Column(String(50), nullable=False, default="kubernetes")  # kubernetes, prometheus, health_probe, argocd, manual
    severity = Column(String(20), nullable=False, default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    # Statuses: DETECTED, EVALUATING, REMEDIATING, VERIFYING, RECOVERED, FAILED, IGNORED, ESCALATED
    status = Column(String(30), nullable=False, default="DETECTED", index=True)
    detected_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    details = Column(Text, nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    application = relationship("Application", back_populates="remediation_events")
    executions = relationship(
        "RemediationExecution",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="desc(RemediationExecution.attempt)"
    )

    __table_args__ = (
        Index("ix_rem_events_app_status", "application_id", "status"),
        Index("ix_rem_events_queue", "status", "created_at"),
        Index("ix_rem_events_app_env", "application_id", "environment_id"),
    )


class RemediationExecution(Base):
    __tablename__ = "remediation_executions"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("remediation_events.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    environment_id = Column(String(50), nullable=False, default="development", index=True)
    policy_id = Column(Integer, ForeignKey("remediation_policies.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(50), nullable=False, index=True)
    # Statuses: PENDING, RUNNING, SUCCESS, FAILED, CANCELLED
    status = Column(String(30), nullable=False, default="PENDING", index=True)
    attempt = Column(Integer, nullable=False, default=1)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    event = relationship("RemediationEvent", back_populates="executions")
    policy = relationship("RemediationPolicy", back_populates="executions")
    application = relationship("Application")

    __table_args__ = (
        Index("ix_rem_exec_event_status", "event_id", "status"),
        Index("ix_rem_exec_app_env", "application_id", "environment_id"),
        Index("ix_rem_exec_created", "created_at"),
    )
