from datetime import datetime, timezone
import json
from typing import List, Dict, Any, Optional
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, UniqueConstraint, Index
from app.db.session import Base

def utcnow():
    return datetime.now(timezone.utc)

class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(String(100), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    runtime = Column(String(50), nullable=False)          # e.g., python, node, go
    framework = Column(String(50), nullable=False)        # e.g., FastAPI, Express, Gin
    version = Column(String(50), nullable=False, default="1.0.0", index=True)
    supported_environments = Column(Text, nullable=False, default='["development", "staging", "production"]')
    generated_project_structure = Column(Text, nullable=False, default='[]')
    required_variables = Column(Text, nullable=False, default='["application_name", "environment", "port"]')
    optional_variables = Column(Text, nullable=False, default='{}')
    default_values = Column(Text, nullable=False, default='{}')
    validation_rules = Column(Text, nullable=False, default='{}')
    is_enabled = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("template_id", "version", name="uq_templates_id_version"),
        Index("ix_templates_lookup", "template_id", "version", "is_enabled"),
    )

    def get_supported_environments(self) -> List[str]:
        try:
            return json.loads(self.supported_environments or '[]')
        except Exception:
            return ["development", "staging", "production"]

    def get_generated_project_structure(self) -> List[str]:
        try:
            return json.loads(self.generated_project_structure or '[]')
        except Exception:
            return []

    def get_required_variables(self) -> List[str]:
        try:
            return json.loads(self.required_variables or '[]')
        except Exception:
            return ["application_name", "environment", "port"]

    def get_optional_variables(self) -> Dict[str, Any]:
        try:
            return json.loads(self.optional_variables or '{}')
        except Exception:
            return {}

    def get_default_values(self) -> Dict[str, Any]:
        try:
            return json.loads(self.default_values or '{}')
        except Exception:
            return {}

    def get_validation_rules(self) -> Dict[str, Any]:
        try:
            return json.loads(self.validation_rules or '{}')
        except Exception:
            return {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "runtime": self.runtime,
            "framework": self.framework,
            "version": self.version,
            "supported_environments": self.get_supported_environments(),
            "generated_project_structure": self.get_generated_project_structure(),
            "required_variables": self.get_required_variables(),
            "optional_variables": self.get_optional_variables(),
            "default_values": self.get_default_values(),
            "validation_rules": self.get_validation_rules(),
            "is_enabled": self.is_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
