from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base


class AnsibleExecution(Base):
    """
    Tracks asynchronous execution of Ansible playbooks within DevForge.
    Enforces status transitions: PENDING -> RUNNING -> SUCCESS / FAILED.
    """
    __tablename__ = "ansible_executions"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True)
    environment_id = Column(String(50), default="development", nullable=False)
    playbook_name = Column(String(100), nullable=False)
    status = Column(String(30), default="PENDING", nullable=False, index=True)
    output = Column(Text, nullable=True)
    error_output = Column(Text, nullable=True)
    return_code = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    application = relationship("Application", backref="ansible_executions", lazy="select")

    def to_dict(self):
        duration_sec = None
        if self.started_at and self.completed_at:
            duration_sec = round((self.completed_at - self.started_at).total_seconds(), 2)

        return {
            "id": self.id,
            "application_id": self.application_id,
            "application_name": self.application.name if self.application else None,
            "environment_id": self.environment_id,
            "playbook_name": self.playbook_name,
            "status": self.status,
            "output": self.output,
            "error_output": self.error_output,
            "return_code": self.return_code,
            "duration_seconds": duration_sec,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
