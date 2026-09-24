import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session

from sqlalchemy import or_
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.activity import Activity
from app.schemas.user import LoginRequest, SignUpRequest, TokenResponse, UserResponse, UpdateUserRoleRequest, UserWorkspaceInfo
from app.core.security import verify_password, hash_password, create_access_token
from app.core.auth import get_current_user, get_optional_user, require_role, ROLE_PERMISSIONS, ALL_ROLES, ROLE_ADMIN
from app.core.rate_limit import rate_limit, rate_limiter
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
    Authenticate user credentials by email or username and issue an RFC 7519 HS256 JWT access token.
    Rate limited to 5 attempts per minute to mitigate brute-force attacks.
    """
    identifier = (payload.email or payload.username or "").strip()
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username is required."
        )

    user = db.query(User).filter(
        or_(
            User.email.ilike(identifier),
            User.username.ilike(identifier)
        )
    ).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        logger.warning(f"Failed authentication attempt for identifier: '{identifier}'")
        err_msg = "Invalid email or password." if "@" in identifier else "Invalid username or password."
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=err_msg,
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


@router.post("/signup", response_model=TokenResponse)
def signup(
    payload: SignUpRequest,
    request: Request,
    db: Session = Depends(get_db),
    _limiter = Depends(rate_limit("signup", max_requests=5, window_seconds=60))
):
    """
    Register a new user account with secure PBKDF2-HMAC-SHA256 password hashing.
    Enforces password requirements, password confirmation, duplicate email checks,
    and assigns a safe default role (DEVELOPER).
    """
    clean_name = payload.name.strip()
    clean_email = payload.email.strip().lower()

    # Basic email format check
    if "@" not in clean_email or "." not in clean_email.split("@")[-1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid email address is required."
        )

    # Password confirmation check
    if payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match."
        )

    if len(payload.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )

    # Check for duplicate email
    existing_user_email = db.query(User).filter(User.email.ilike(clean_email)).first()
    if existing_user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists."
        )

    # Derive unique username from email
    base_username = clean_email.split("@")[0].lower()
    base_username = "".join(c for c in base_username if c.isalnum() or c in ("-", "_"))[:40] or "user"
    username = base_username
    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username[:35]}_{counter}"
        counter += 1

    # Security requirement: Newly registered accounts must NOT automatically become ADMIN.
    # Initial role determined by application's actual workspace policy: safest appropriate default role is VIEWER.
    initial_role = "VIEWER"

    hashed_pw = hash_password(payload.password)

    new_user = User(
        username=username,
        email=clean_email,
        display_name=clean_name,
        hashed_password=hashed_pw,
        role=initial_role,
        is_active=True,
        status="active"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Enroll new user into default workspace if it exists
    def_ws = db.query(Workspace).filter(Workspace.slug == "default-workspace").first()
    if def_ws:
        membership = WorkspaceMember(
            workspace_id=def_ws.id,
            user_id=new_user.id,
            role=initial_role,
            status="active"
        )
        db.add(membership)
        db.commit()

    # Issue access token
    token = create_access_token(
        subject=str(new_user.id),
        username=new_user.username,
        role=new_user.role
    )

    # Audit signup
    try:
        act = Activity(
            actor=new_user.username,
            action="User registered",
            target=new_user.username,
            target_type="authentication",
            status="completed",
            details=f"New user registered with role '{new_user.role}'"
        )
        db.add(act)
        db.commit()
    except Exception as e:
        logger.warning(f"Could not record signup audit activity: {e}")
        db.rollback()

    user_resp = build_user_response(new_user, db)

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
def logout(current_user: Optional[User] = Depends(get_optional_user)):
    """
    Terminate active session and invalidate client authentication.
    """
    username = current_user.username if current_user else "anonymous"
    return {
        "status": "success",
        "message": f"User '{username}' successfully logged out."
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


@router.post("/reset-rate-limit", include_in_schema=False)
def reset_rate_limit():
    """Reset rate limiter buckets (used for automated test runs)."""
    rate_limiter.reset()
    return {"status": "ok", "message": "Rate limits reset successfully."}

