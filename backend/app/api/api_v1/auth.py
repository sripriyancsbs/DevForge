import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.activity import Activity
from app.schemas.user import LoginRequest, TokenResponse, UserResponse
from app.core.security import verify_password, create_access_token
from app.core.auth import get_current_user, ROLE_PERMISSIONS, ALL_ROLES
from app.core.rate_limit import rate_limit
from app.core.config import settings

logger = logging.getLogger("devforge.api.auth")

router = APIRouter()


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

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact system administrator."
        )

    # Issue access token
    token = create_access_token(
        subject=str(user.id),
        username=user.username,
        role=user.role
    )

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

    user_resp = UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
        permissions=ROLE_PERMISSIONS.get(user.role.upper(), [])
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_resp
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Retrieve authenticated user profile and assigned RBAC permissions.
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat() if current_user.created_at else None,
        permissions=ROLE_PERMISSIONS.get(current_user.role.upper(), [])
    )


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
