from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="Username")
    password: str = Field(..., min_length=1, description="Password")


class UserWorkspaceInfo(BaseModel):
    id: int
    name: str
    slug: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    display_name: Optional[str] = None
    role: str
    is_active: bool
    status: str = "active"
    created_at: Optional[str] = None
    last_login_at: Optional[str] = None
    permissions: List[str] = []
    workspaces: List[UserWorkspaceInfo] = []
    active_workspace: Optional[UserWorkspaceInfo] = None

    model_config = ConfigDict(from_attributes=True)


class UpdateUserRoleRequest(BaseModel):
    role: str = Field(..., description="Target RBAC role (ADMIN, OPERATOR, DEVELOPER, VIEWER)")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

