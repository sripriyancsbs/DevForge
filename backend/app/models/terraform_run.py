from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.db.session import Base


class TerraformRun(Base):
    __tablename__ = "terraform_runs"

    id = Column(Integer, primary_key=True, index=True)
    environment = Column(String(50), default="development", nullable=False, index=True)
    operation = Column(String(30), nullable=False)  # 'plan', 'apply', 'init', 'validate'
    status = Column(String(30), default="PENDING", nullable=False, index=True)  # 'PENDING', 'PLANNING', 'PLAN_READY', 'APPLYING', 'APPLIED', 'FAILED'
    plan_output = Column(Text, nullable=True)
    apply_output = Column(Text, nullable=True)
    resources_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "environment": self.environment,
            "operation": self.operation,
            "status": self.status,
            "plan_output": self.plan_output,
            "apply_output": self.apply_output,
            "resources_count": self.resources_count,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
