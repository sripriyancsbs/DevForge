from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.environment import Environment
from app.schemas.environment import EnvironmentResponse

router = APIRouter()

@router.get("", response_model=List[EnvironmentResponse])
def list_environments(db: Session = Depends(get_db)):
    return db.query(Environment).order_by(Environment.id.asc()).all()

@router.get("/{env_id_or_slug}", response_model=EnvironmentResponse)
def get_environment(env_id_or_slug: str, db: Session = Depends(get_db)):
    if env_id_or_slug.isdigit():
        env = db.query(Environment).filter(Environment.id == int(env_id_or_slug)).first()
    else:
        env = db.query(Environment).filter(Environment.slug == env_id_or_slug.lower()).first()

    if not env:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Environment '{env_id_or_slug}' not found."
        )
    return env
