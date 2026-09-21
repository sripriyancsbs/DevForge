from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class LoginRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=1, max_length=120, description="Username or Email")
    email: Optional[str] = Field(None, description="Email address")
    password: str = Field(..., min_length=1, description="Password")


class SignUpRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full Name")
    email: str = Field(..., min_length=3, max_length=120, description="Email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (min 8 characters)")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirm Password")


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

