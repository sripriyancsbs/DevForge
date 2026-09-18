from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

def utcnow():
    return datetime.now(timezone.utc)

class ServiceHealth(Base):
    __tablename__ = "service_health"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=True, index=True)
    service_name = Column(String(100), nullable=False, unique=True, index=True)
    status = Column(String(30), nullable=False, default="healthy", index=True)
    cpu_percent = Column(Float, nullable=False, default=12.4)
    memory_mb = Column(String(30), nullable=False, default="240 MB")
    requests_per_sec = Column(Integer, nullable=False, default=145)
    error_rate = Column(String(20), nullable=False, default="0.01%")
    uptime = Column(String(20), nullable=False, default="99.98%")
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    application = relationship("Application", back_populates="service_health")
