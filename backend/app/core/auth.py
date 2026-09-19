import logging
from typing import List, Optional
from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
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
        "settings:manage", "users:manage"
    ],
    ROLE_OPERATOR: [
        "view:all",
        "deploy:view", "deploy:trigger", "deploy:rollback",
        "infra:view", "infra:plan", "infra:apply",
        "ansible:view", "ansible:execute",
        "remediation:view", "remediation:scan", "remediation:approve", "remediation:execute",
        "app:create", "app:manage"
    ],
    ROLE_DEVELOPER: [
        "view:all",
        "deploy:view", "deploy:trigger",
        "infra:view",
        "ansible:view",
        "remediation:view",
        "app:create", "app:manage"
    ],
    ROLE_VIEWER: [
        "view:all",
        "deploy:view",
        "infra:view",
        "ansible:view",
        "remediation:view"
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
    Raises 401 Unauthorized if missing, invalid, or expired.
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

    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if not user:
        # Fallback to token payload attributes if user was seeded or session authenticated
        user = User(
            id=int(payload.get("sub", 1)),
            username=username,
            email=f"{username}@devforge.internal",
            role=payload.get("role", ROLE_VIEWER),
            is_active=True
        )

    return user


def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication for read endpoints.
    Returns authenticated user if valid token present, otherwise None.
    """
    token = extract_token_from_header(authorization)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "username" not in payload:
        return None
    username = payload["username"]
    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if not user:
        return User(
            id=int(payload.get("sub", 1)),
            username=username,
            email=f"{username}@devforge.internal",
            role=payload.get("role", ROLE_VIEWER),
            is_active=True
        )
    return user


def require_role(allowed_roles: List[str]):
    """
    FastAPI dependency factory enforcing Role-Based Access Control (RBAC).
    Raises 401 if unauthenticated and 403 if user role lacks permission.
    """
    normalized_allowed = [r.upper() for r in allowed_roles]

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
