from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.activity import Activity
from app.schemas.service_health import ActivityResponse

router = APIRouter()

@router.get("", response_model=List[ActivityResponse])
def list_activity(
    target_type: Optional[str] = None,
    status: Optional[str] = None,
    application: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Activity)
    if target_type and target_type != "all":
        query = query.filter(Activity.target_type == target_type)
    if status and status != "all":
        query = query.filter(Activity.status == status)
    if application and application != "all":
        query = query.filter(Activity.target.ilike(f"%{application}%"))

    return query.order_by(Activity.created_at.desc()).limit(100).all()
