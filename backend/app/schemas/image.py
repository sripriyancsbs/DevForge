from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field


class ContainerImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: Optional[int] = None
    application_id: int
    registry: str = "ghcr.io"
    repository: str = ""
    tag: str = "latest"
    digest: Optional[str] = None
    commit_sha: Optional[str] = None
    status: str = "PENDING"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Also include image_* aliases for full compatibility
    image_repository: Optional[str] = None
    image_tag: Optional[str] = None
    image_digest: Optional[str] = None

    @classmethod
    def from_orm_model(cls, img: Any) -> "ContainerImageResponse":
        repo = getattr(img, "image_repository", "")
        tag = getattr(img, "image_tag", "latest")
        digest = getattr(img, "image_digest", None)
        return cls(
            id=getattr(img, "id", None),
            application_id=getattr(img, "application_id", 0),
            registry=getattr(img, "registry", "ghcr.io"),
            repository=repo,
            tag=tag,
            digest=digest,
            commit_sha=getattr(img, "commit_sha", None),
            status=getattr(img, "status", "PENDING"),
            created_at=getattr(img, "created_at", None),
            updated_at=getattr(img, "updated_at", None),
            image_repository=repo,
            image_tag=tag,
            image_digest=digest
        )


class ContainerImageListResponse(BaseModel):
    images: List[ContainerImageResponse]
    total: int
    latest: Optional[ContainerImageResponse] = None
