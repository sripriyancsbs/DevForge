from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    application_name = Column(String(100), nullable=False)
    version = Column(String(50), nullable=False)
    commit_hash = Column(String(40), nullable=False)
    commit_message = Column(String(255), nullable=True)
    environment = Column(String(50), nullable=False) # production, staging, development, preview
    status = Column(String(30), nullable=False) # healthy, failed, deploying, rolled_back, pending
    duration = Column(String(20), nullable=False, default="45s")
    triggered_by = Column(String(100), nullable=False, default="git-push:main")
    logs = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="deployments")
