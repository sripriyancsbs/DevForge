from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.session import Base

def utcnow():
    return datetime.now(timezone.utc)

class ContainerImage(Base):
    __tablename__ = "container_images"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    registry = Column(String(100), nullable=False, default="ghcr.io")
    image_repository = Column(String(255), nullable=False, index=True)
    image_tag = Column(String(128), nullable=False)
    image_digest = Column(String(255), nullable=True)
    commit_sha = Column(String(100), nullable=True)
    status = Column(String(30), nullable=False, default="PENDING", index=True)  # PENDING, BUILDING, PUSHING, READY, FAILED
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Relationships
    application = relationship("Application", back_populates="container_images")

    __table_args__ = (
        Index("ix_container_images_app_status", "application_id", "status"),
        Index("ix_container_images_repo_tag", "image_repository", "image_tag"),
    )
