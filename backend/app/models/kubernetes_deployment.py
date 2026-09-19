from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.session import Base

def utcnow():
    return datetime.now(timezone.utc)

class KubernetesDeployment(Base):
    __tablename__ = "kubernetes_deployments"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    environment = Column(String(50), nullable=False, default="development", index=True)
    namespace = Column(String(63), nullable=False, default="devforge", index=True)
    deployment_name = Column(String(100), nullable=False, index=True)
    service_name = Column(String(100), nullable=False, index=True)
    image_repository = Column(String(255), nullable=False, index=True)
    image_tag = Column(String(128), nullable=False)
    replicas = Column(Integer, nullable=False, default=1)
    ready_replicas = Column(Integer, nullable=False, default=0)
    status = Column(String(30), nullable=False, default="PENDING", index=True)  # PENDING, DEPLOYING, RUNNING, FAILED, STOPPED
    port = Column(Integer, nullable=False, default=8000)
    node_port = Column(Integer, nullable=True)
    manifest_yaml = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    application = relationship("Application", back_populates="kubernetes_deployments")

    __table_args__ = (
        Index("ix_k8s_deploy_app_status", "application_id", "status"),
        Index("ix_k8s_deploy_name_ns", "deployment_name", "namespace"),
    )
