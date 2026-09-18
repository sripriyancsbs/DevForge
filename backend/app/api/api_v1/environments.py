from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.environment import Environment
from app.schemas.environment import EnvironmentResponse

router = APIRouter()

@router.get("", response_model=List[EnvironmentResponse])
def list_environments(db: Session = Depends(get_db)):
    return db.query(Environment).all()
