from typing import Optional
from pydantic import BaseModel

class GitHubStatusResponse(BaseModel):
    connected: bool
    owner: str
    authenticated_user: Optional[str] = None
    error: Optional[str] = None
