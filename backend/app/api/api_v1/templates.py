import json
import logging
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.template import Template
from app.models.user import User
from app.models.activity import Activity
from app.core.auth import (
    get_current_user,
    require_role,
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ROLE_DEVELOPER,
    ROLE_VIEWER,
)
from app.schemas.template import (
    TemplateResponse,
    TemplateValidateRequest,
    TemplateValidateResponse,
    TemplatePreviewRequest,
    TemplatePreviewResponse,
    TemplateCreateRequest,
    TemplateUpdateRequest,
)
from app.services.provisioning.template_registry import template_registry

logger = logging.getLogger("devforge.api.templates")

def utcnow():
    return datetime.now(timezone.utc)

router = APIRouter()


@router.get("", response_model=List[TemplateResponse])
def list_templates(
    include_disabled: bool = Query(False, description="Include disabled templates (admin only)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all available application starter templates.
    Accessible to VIEWER, DEVELOPER, OPERATOR, and ADMIN roles.
    """
    # Only admins can view disabled templates
    enabled_only = not (include_disabled and current_user.role == ROLE_ADMIN)
    templates = template_registry.list_templates(db=db, enabled_only=enabled_only)
    return templates


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: str,
    version: Optional[str] = Query(None, description="Optional specific template version"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed metadata and configuration schema for a specific template.
    Accessible to VIEWER, DEVELOPER, OPERATOR, and ADMIN roles.
    """
    try:
        meta = template_registry.get_template_metadata(template_id, version=version, db=db)
        return meta
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{template_id}/validate", response_model=TemplateValidateResponse)
def validate_template_variables(
    template_id: str,
    payload: TemplateValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ROLE_DEVELOPER, ROLE_OPERATOR, ROLE_ADMIN))
):
    """
    Validate variables against template specifications, checking types, lengths,
    RFC 1123 naming, path traversal, and injection characters.
    Requires DEVELOPER, OPERATOR, or ADMIN role.
    """
    try:
        result = template_registry.validate_variables(
            template_id=template_id,
            version=payload.version,
            variables=payload.model_dump(),
            db=db
        )
        return result
    except ValueError as e:
        # Record audit event for validation failure
        db.add(Activity(
            actor=current_user.username,
            action="template.validation_failed",
            target=f"{template_id} ({payload.application_name})",
            target_type="template",
            status="failed",
            details=f"Template variable validation failed: {str(e)}",
            created_at=utcnow()
        ))
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )


@router.post("/{template_id}/preview", response_model=TemplatePreviewResponse)
def preview_template(
    template_id: str,
    payload: TemplatePreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ROLE_DEVELOPER, ROLE_OPERATOR, ROLE_ADMIN))
):
    """
    Lightweight simulation returning expected generated file tree and rendered manifest
    without writing files or initiating provisioning.
    Requires DEVELOPER, OPERATOR, or ADMIN role.
    """
    try:
        preview_data = template_registry.preview_project(
            template_id=template_id,
            version=payload.version,
            variables=payload.model_dump(),
            db=db
        )
        return preview_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: TemplateCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ROLE_ADMIN))
):
    """
    Register a new application starter template or new version.
    Requires ADMIN role.
    """
    existing = (
        db.query(Template)
        .filter(Template.template_id == payload.template_id)
        .filter(Template.version == payload.version)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Template '{payload.template_id}' version '{payload.version}' already exists."
        )

    new_tpl = Template(
        template_id=payload.template_id,
        name=payload.name,
        description=payload.description,
        runtime=payload.runtime,
        framework=payload.framework,
        version=payload.version,
        supported_environments=json.dumps(payload.supported_environments),
        generated_project_structure=json.dumps(payload.generated_project_structure),
        required_variables=json.dumps(payload.required_variables),
        optional_variables=json.dumps(payload.optional_variables),
        default_values=json.dumps(payload.default_values),
        validation_rules=json.dumps(payload.validation_rules),
        is_enabled=payload.is_enabled,
        created_at=utcnow(),
        updated_at=utcnow()
    )
    db.add(new_tpl)
    db.commit()
    db.refresh(new_tpl)

    db.add(Activity(
        actor=current_user.username,
        action="template.created",
        target=f"{new_tpl.name} ({new_tpl.template_id}:{new_tpl.version})",
        target_type="template",
        status="completed",
        details=f"Registered application template '{new_tpl.name}' (version {new_tpl.version})",
        created_at=utcnow()
    ))
    db.commit()

    return new_tpl.to_dict()


@router.patch("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: str,
    payload: TemplateUpdateRequest,
    version: Optional[str] = Query("1.0.0", description="Template version to update"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ROLE_ADMIN))
):
    """
    Update template configuration or toggle enabled/disabled state.
    Requires ADMIN role.
    """
    tpl = (
        db.query(Template)
        .filter(Template.template_id == template_id)
        .filter(Template.version == version)
        .first()
    )
    if not tpl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' version '{version}' not found in database."
        )

    if payload.name is not None:
        tpl.name = payload.name
    if payload.description is not None:
        tpl.description = payload.description
    if payload.is_enabled is not None:
        tpl.is_enabled = payload.is_enabled

    tpl.updated_at = utcnow()
    db.commit()
    db.refresh(tpl)

    state_desc = "enabled" if tpl.is_enabled else "disabled"
    db.add(Activity(
        actor=current_user.username,
        action=f"template.{state_desc}",
        target=f"{tpl.name} ({tpl.template_id}:{tpl.version})",
        target_type="template",
        status="completed",
        details=f"Template '{tpl.name}' was {state_desc} by {current_user.username}",
        created_at=utcnow()
    ))
    db.commit()

    return tpl.to_dict()
