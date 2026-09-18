from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.db.session import Base

class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String(100), nullable=False) # e.g. "alex.sre", "ci-bot", "sarah.dev"
    action = Column(String(100), nullable=False) # "Application created", "Deployment completed", "Deployment failed", etc.
    target = Column(String(100), nullable=False) # e.g. "payments-service", "staging-cluster"
    target_type = Column(String(50), nullable=False, default="application") # application, deployment, environment, config
    status = Column(String(30), nullable=False, default="completed") # completed, failed, warning
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
