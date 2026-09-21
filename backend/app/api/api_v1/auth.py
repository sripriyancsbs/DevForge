import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.activity import Activity
from app.schemas.user import LoginRequest, TokenResponse, UserResponse, UpdateUserRoleRequest, UserWorkspaceInfo
from app.core.security import verify_password, create_access_token
from app.core.auth import get_current_user, require_role, ROLE_PERMISSIONS, ALL_ROLES, ROLE_ADMIN
from app.core.rate_limit import rate_limit
from app.core.config import settings

logger = logging.getLogger("devforge.api.auth")

router = APIRouter()


def build_user_response(user: User, db: Session, active_workspace_id: Optional[int] = None) -> UserResponse:
    """
    Construct full UserResponse with authoritative workspace memberships and active workspace context.
    """
    memberships = (
        db.query(WorkspaceMember, Workspace)
        .join(Workspace, WorkspaceMember.workspace_id == Workspace.id)
        .filter(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.status == "active",
            Workspace.status == "active"
        )
        .order_by(Workspace.id.asc())
        .all()
    )

    workspaces = []
    active_ws = None
    for member, ws in memberships:
        info = UserWorkspaceInfo(
            id=ws.id,
            name=ws.name,
            slug=ws.slug,
            role=member.role
        )
        workspaces.append(info)
        if active_workspace_id and ws.id == active_workspace_id:
            active_ws = info

    if not active_ws and workspaces:
        active_ws = workspaces[0]

    effective_role = active_ws.role if active_ws else (user.role or "VIEWER")

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=getattr(user, "display_name", None) or user.username,
        role=effective_role,
        is_active=user.is_active,
        status=getattr(user, "status", "active"),
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        permissions=ROLE_PERMISSIONS.get(effective_role.upper(), []),
        workspaces=workspaces,
        active_workspace=active_ws
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    _limiter = Depends(rate_limit("login", max_requests=5, window_seconds=60))
):
    """
    Authenticate user credentials and issue an RFC 7519 HS256 JWT access token.
    Rate limited to 5 attempts per minute to mitigate brute-force attacks.
    """
    user = db.query(User).filter(User.username == payload.username.strip()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        logger.warning(f"Failed authentication attempt for username: '{payload.username}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active or getattr(user, "status", "active") == "disabled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated or disabled. Contact system administrator."
        )

    # Issue access token
    token = create_access_token(
        subject=str(user.id),
        username=user.username,
        role=user.role
    )

    # Update last login timestamp
    try:
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as e:
        logger.warning(f"Could not record last_login_at: {e}")
        db.rollback()

    # Audit login
    try:
        act = Activity(
            actor=user.username,
            action="User authenticated",
            target=user.username,
            target_type="authentication",
            status="completed",
            details=f"Successful login with role '{user.role}'"
        )
        db.add(act)
        db.commit()
    except Exception as e:
        logger.warning(f"Could not record login audit activity: {e}")
        db.rollback()

    user_resp = build_user_response(user, db)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_resp
    )


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-Id")
):
    """
    Retrieve authenticated user profile and assigned RBAC permissions.
    """
    active_ws_id = int(x_workspace_id) if x_workspace_id and x_workspace_id.isdigit() else None
    return build_user_response(current_user, db, active_workspace_id=active_ws_id)


@router.get("/roles")
def get_roles():
    """
    Return platform role definitions and RBAC permissions matrix.
    """
    return {
        "roles": ALL_ROLES,
        "permissions": ROLE_PERMISSIONS
    }


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """
    Terminate active session.
    """
    return {
        "status": "success",
        "message": f"User '{current_user.username}' successfully logged out."
    }


@router.get("/users", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ROLE_ADMIN))
):
    """
    List all platform users with roles. Restricted to ADMIN.
    """
    users = db.query(User).order_by(User.id.asc()).all()
    return [build_user_response(u, db) for u in users]


@router.patch("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    payload: UpdateUserRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(ROLE_ADMIN))
):
    """
    Update a user's RBAC role in PostgreSQL.
    Only authorized ADMIN users can perform this operation.
    """
    target_role = payload.role.strip().upper()
    if target_role not in ALL_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{payload.role}'. Must be one of: {ALL_ROLES}"
        )

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )

    old_role = target_user.role
    target_user.role = target_role

    # Sync default-workspace membership role if present
    def_ws = db.query(Workspace).filter(Workspace.slug == "default-workspace").first()
    if def_ws:
        def_member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == def_ws.id,
            WorkspaceMember.user_id == target_user.id
        ).first()
        if def_member:
            def_member.role = target_role

    db.commit()
    db.refresh(target_user)

    # Record audit log
    try:
        act = Activity(
            actor=current_user.username,
            action="User role updated",
            target=target_user.username,
            target_type="rbac",
            status="completed",
            details=f"Role for user '{target_user.username}' changed from '{old_role}' to '{target_role}' by '{current_user.username}'"
        )
        db.add(act)
        db.commit()
    except Exception as e:
        logger.warning(f"Could not record role update audit: {e}")
        db.rollback()

    return build_user_response(target_user, db)


@router.patch("/role")
@router.post("/role")
def reject_self_service_role_change(
    payload: Dict[str, Any] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Self-service role modification is strictly forbidden.
    Users cannot elevate or modify their own privileges.
    """
    logger.warning(f"Security event: User '{current_user.username}' attempted self-service role alteration.")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Self-service role modification is strictly forbidden. Contact a platform administrator."
    )

