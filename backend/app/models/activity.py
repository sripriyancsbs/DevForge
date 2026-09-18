from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from app.db.session import Base

def utcnow():
    return datetime.now(timezone.utc)

class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False, index=True)
    target = Column(String(100), nullable=False, index=True)
    target_type = Column(String(50), nullable=False, default="application", index=True)
    status = Column(String(30), nullable=False, default="completed", index=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)

    __table_args__ = (
        Index("ix_activities_target_type_status", "target_type", "status"),
    )
