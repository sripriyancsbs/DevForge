import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.activity import Activity
from app.schemas.github import GitHubStatusResponse
from app.services.github.repository_service import repository_service

logger = logging.getLogger("devforge.api.integrations")

router = APIRouter()


@router.get("/github/status", response_model=GitHubStatusResponse, status_code=status.HTTP_200_OK)
def get_github_status(db: Session = Depends(get_db)):
    """
    Check the connectivity, authentication, and permission status of GitHub integration.
    Guarantees credentials (GITHUB_TOKEN) are never returned or leaked.
    """
    res = repository_service.get_connection_status()
    now = datetime.now(timezone.utc)

    # Record Activity audit event
    db.add(Activity(
        actor="platform.user",
        action="GitHub integration checked",
        target=f"github:{res.get('owner', 'sripriyancsbs')}",
        target_type="integration",
        status="completed" if res.get("connected") else "warning",
        details="GitHub connection active" if res.get("connected") else f"GitHub check: {res.get('error', 'disconnected')}",
        created_at=now
    ))
    db.commit()

    return GitHubStatusResponse(
        connected=res.get("connected", False),
        owner=res.get("owner", "sripriyancsbs"),
        authenticated_user=res.get("authenticated_user"),
        error=res.get("error")
    )
