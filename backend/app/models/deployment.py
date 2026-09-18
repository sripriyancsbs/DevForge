from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.session import Base

def utcnow():
    return datetime.now(timezone.utc)

class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    application_name = Column(String(100), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    commit_hash = Column(String(40), nullable=False)
    commit_message = Column(String(255), nullable=True)
    environment = Column(String(50), nullable=False, index=True)
    status = Column(String(30), nullable=False, index=True)
    duration = Column(String(20), nullable=False, default="45s")
    triggered_by = Column(String(100), nullable=False, default="git-push:main")
    logs = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    # Relationships
    application = relationship("Application", back_populates="deployments")

    __table_args__ = (
        Index("ix_deployments_app_env", "application_id", "environment"),
    )
