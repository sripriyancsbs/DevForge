import logging
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.core.security import decode_access_token

logger = logging.getLogger("devforge.auth")

ROLE_ADMIN = "ADMIN"
ROLE_OPERATOR = "OPERATOR"
ROLE_DEVELOPER = "DEVELOPER"
ROLE_VIEWER = "VIEWER"

ALL_ROLES = [ROLE_ADMIN, ROLE_OPERATOR, ROLE_DEVELOPER, ROLE_VIEWER]

# Permissions matrix for DevForge capabilities
ROLE_PERMISSIONS = {
    ROLE_ADMIN: [
        "view:all",
        "deploy:view", "deploy:trigger", "deploy:rollback",
        "infra:view", "infra:plan", "infra:apply",
        "ansible:view", "ansible:execute",
        "remediation:view", "remediation:scan", "remediation:approve", "remediation:execute", "remediation:cancel",
        "app:create", "app:delete", "app:manage",
        "templates:view", "templates:use", "templates:manage",
        "settings:manage", "users:manage",
        "workspace:manage", "members:manage"
    ],
    ROLE_OPERATOR: [
        "view:all",
        "deploy:view", "deploy:trigger", "deploy:rollback",
        "infra:view", "infra:plan", "infra:apply",
        "ansible:view", "ansible:execute",
        "remediation:view", "remediation:scan", "remediation:approve", "remediation:execute",
        "templates:view", "templates:use",
        "app:create", "app:manage",
        "workspace:view", "members:view"
    ],
    ROLE_DEVELOPER: [
        "view:all",
        "deploy:view", "deploy:trigger",
        "infra:view",
        "ansible:view",
        "remediation:view",
        "templates:view", "templates:use",
        "app:create", "app:manage",
        "workspace:view", "members:view"
    ],
    ROLE_VIEWER: [
        "view:all",
        "deploy:view",
        "infra:view",
        "ansible:view",
        "remediation:view",
        "templates:view",
        "workspace:view", "members:view"
    ]
}


def extract_token_from_header(authorization: Optional[str]) -> Optional[str]:
    """Extract raw bearer token from Authorization header."""
    if not authorization:
        return None
    parts = authorization.strip().split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    if len(parts) == 1 and not parts[0].lower().startswith("bearer"):
        return parts[0]
    return None


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Authenticate request via Bearer token.
    Raises 401 Unauthorized if missing, invalid, expired, or user deactivated/disabled.
    Backend PostgreSQL database is the sole authoritative source of identity and status.
    """
    token = extract_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, malformed, or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    username = payload.get("username")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token payload.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Authoritative database lookup
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Explicit check for disabled account status
    if getattr(user, "status", "active") == "disabled" or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been disabled or deactivated. Contact system administrator."
        )

    # Track last login timestamp
    try:
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()

    return user


def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication for read endpoints.
    Returns authenticated user if valid token present and user is active, otherwise raises if invalid/disabled.
    Returns None only when no Authorization header was provided.
    """
    token = extract_token_from_header(authorization)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "username" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, malformed, or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    username = payload["username"]
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    if getattr(user, "status", "active") == "disabled" or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been disabled or deactivated."
        )
    return user


class WorkspaceContext:
    def __init__(self, workspace: Workspace, member: WorkspaceMember, user: User, role: str):
        self.workspace = workspace
        self.member = member
        self.user = user
        self.role = role


def get_current_workspace(
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id"),
    x_workspace_slug: Optional[str] = Header(None, alias="X-Workspace-Slug"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> WorkspaceContext:
    """
    Resolve active workspace context and verify authenticated user's workspace membership.
    Enforces that permissions are derived directly from the user's assigned role in the target workspace.
    """
    workspace = None
    if x_workspace_id and x_workspace_id.isdigit():
        workspace = db.query(Workspace).filter(Workspace.id == int(x_workspace_id)).first()
    elif x_workspace_slug:
        workspace = db.query(Workspace).filter(Workspace.slug == x_workspace_slug.strip()).first()
    
    if not workspace:
        # Fall back to user's first active workspace or default-workspace
        membership = db.query(WorkspaceMember).filter(
            WorkspaceMember.user_id == current_user.id,
            WorkspaceMember.status == "active"
        ).first()
        if membership:
            workspace = membership.workspace
        else:
            workspace = db.query(Workspace).filter(Workspace.slug == "default-workspace").first()

    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found."
        )

    # Check that user is an active member of this workspace
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace.id,
        WorkspaceMember.user_id == current_user.id,
        WorkspaceMember.status == "active"
    ).first()

    has_any_ws = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).first() is not None
    if not member and not has_any_ws and workspace.slug == "default-workspace" and getattr(current_user, "role", None):
        member = WorkspaceMember(
            workspace_id=workspace.id,
            user_id=current_user.id,
            role=current_user.role.upper(),
            status="active"
        )
        db.add(member)
        db.commit()
        db.refresh(member)

    if not member:
        logger.warning(
            f"Workspace isolation violation: User '{current_user.username}' attempted to access "
            f"workspace '{workspace.slug}' without active membership."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: You do not have active membership in workspace '{workspace.slug}'."
        )

    return WorkspaceContext(
        workspace=workspace,
        member=member,
        user=current_user,
        role=member.role.upper()
    )


def require_workspace_role(*allowed_roles):
    """
    Enforces Role-Based Access Control inside the active workspace.
    Derives permissions directly from the user's WorkspaceMember.role in PostgreSQL.
    """
    if len(allowed_roles) == 1 and isinstance(allowed_roles[0], (list, tuple, set)):
        roles = allowed_roles[0]
    elif len(allowed_roles) == 1 and isinstance(allowed_roles[0], str):
        roles = [allowed_roles[0]]
    else:
        roles = allowed_roles
    normalized_allowed = [str(r).upper() for r in roles]

    def role_checker(ws_ctx: WorkspaceContext = Depends(get_current_workspace)) -> WorkspaceContext:
        user_role = (ws_ctx.role or "").upper()
        if user_role not in normalized_allowed:
            logger.warning(
                f"Workspace RBAC failure: User '{ws_ctx.user.username}' with role '{user_role}' "
                f"in workspace '{ws_ctx.workspace.slug}' attempted operation requiring: {normalized_allowed}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Action requires workspace role: {', '.join(normalized_allowed)}. Current role: '{user_role}'."
            )
        return ws_ctx

    return role_checker


def require_role(*allowed_roles):
    """
    FastAPI dependency factory enforcing Role-Based Access Control (RBAC).
    Raises 401 if unauthenticated and 403 if user role lacks permission.
    Supports either require_role(["ADMIN", "OPERATOR"]) or require_role(ROLE_ADMIN, ROLE_OPERATOR).
    """
    if len(allowed_roles) == 1 and isinstance(allowed_roles[0], (list, tuple, set)):
        roles = allowed_roles[0]
    elif len(allowed_roles) == 1 and isinstance(allowed_roles[0], str):
        roles = [allowed_roles[0]]
    else:
        roles = allowed_roles
    normalized_allowed = [str(r).upper() for r in roles]

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = (current_user.role or "").upper()
        if user_role not in normalized_allowed:
            logger.warning(
                f"Authorization failure: User '{current_user.username}' with role '{user_role}' "
                f"attempted to access operation requiring one of: {normalized_allowed}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Action requires one of the following roles: {', '.join(normalized_allowed)}. Current role: '{user_role}'."
            )
        return current_user

    return role_checker


def verify_application_workspace_access(
    application: Any,
    current_user: User,
    db: Session,
    required_roles: Optional[List[str]] = None
) -> WorkspaceMember:
    """
    Verify application-level workspace boundary and authorization.
    Protects against IDOR-style cross-workspace access attempts.
    """
    ws_id = getattr(application, "workspace_id", None)
    def_ws = db.query(Workspace).filter(Workspace.slug == "default-workspace").first()
    if not ws_id and def_ws:
        ws_id = def_ws.id

    if not ws_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application workspace could not be resolved."
        )

    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == ws_id,
        WorkspaceMember.user_id == current_user.id,
        WorkspaceMember.status == "active"
    ).first()

    has_any_ws = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).first() is not None
    if not member and not has_any_ws and def_ws and ws_id == def_ws.id and getattr(current_user, "role", None):
        member = WorkspaceMember(
            workspace_id=def_ws.id,
            user_id=current_user.id,
            role=current_user.role.upper(),
            status="active"
        )
        db.add(member)
        db.commit()
        db.refresh(member)

    if not member:
        logger.warning(
            f"Cross-workspace application IDOR attempt: User '{current_user.username}' "
            f"attempted access to application '{application.name}' in workspace ID {ws_id}."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: You do not have permission to access applications in workspace ID {ws_id}."
        )

    if required_roles:
        normalized_req = [r.upper() for r in required_roles]
        if member.role.upper() not in normalized_req:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Action requires workspace role: {', '.join(normalized_req)}. Current: '{member.role}'."
            )

    return member
