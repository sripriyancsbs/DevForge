from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.db.session import Base

class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    slug = Column(String(50), nullable=False, unique=True)
    type = Column(String(30), nullable=False) # production, staging, development, preview
    region = Column(String(50), nullable=False, default="us-east-1 (N. Virginia)")
    cluster_endpoint = Column(String(100), nullable=False)
    status = Column(String(30), nullable=False, default="healthy") # healthy, degraded, maintenance
    services_count = Column(Integer, nullable=False, default=0)
    cpu_allocated = Column(String(30), default="16 / 32 vCPUs")
    memory_allocated = Column(String(30), default="32 / 64 GB")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
