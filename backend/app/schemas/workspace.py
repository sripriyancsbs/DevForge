from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class WorkspaceMemberResponse(BaseModel):
    id: int
    workspace_id: int
    user_id: int
    username: Optional[str] = None
    email: Optional[str] = None
    display_name: Optional[str] = None
    role: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    current_user_role: Optional[str] = None
    member_count: int = 0
    application_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class AddWorkspaceMemberRequest(BaseModel):
    name: Optional[str] = Field(None, description="User full display name")
    username: Optional[str] = Field(None, description="Existing username to add")
    email: str = Field(..., description="User email to create/invite")
    password: Optional[str] = Field(None, description="Initial account password (min 8 chars)")
    confirm_password: Optional[str] = Field(None, description="Password confirmation")
    role: str = Field("VIEWER", description="Assigned role: ADMIN, OPERATOR, DEVELOPER, VIEWER")


class UpdateWorkspaceMemberRequest(BaseModel):
    role: Optional[str] = Field(None, description="Target role: ADMIN, OPERATOR, DEVELOPER, VIEWER")
    status: Optional[str] = Field(None, description="Status: active, disabled")
