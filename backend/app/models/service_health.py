from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime
from app.db.session import Base

class ServiceHealth(Base):
    __tablename__ = "service_health"

    id = Column(Integer, primary_key=True, index=True)
    service_name = Column(String(100), nullable=False, unique=True, index=True)
    status = Column(String(30), nullable=False, default="healthy") # healthy, warning, failed
    cpu_percent = Column(Float, nullable=False, default=12.4)
    memory_mb = Column(String(30), nullable=False, default="240 MB")
    requests_per_sec = Column(Integer, nullable=False, default=145)
    error_rate = Column(String(20), nullable=False, default="0.01%")
    uptime = Column(String(20), nullable=False, default="99.98%")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
