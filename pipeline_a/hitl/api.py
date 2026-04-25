# pipeline_a/hitl/api.py
from typing import Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from shared.db.session import get_db
from pipeline_a.hitl.service import get_hitl_queue

router = APIRouter(prefix="/api/v1/hitl", tags=["hitl"])

class QueueItem(BaseModel):
    job_id: str
    patient_id: str
    document_type: str
    file_name: Optional[str] = None
    status: str
    hitl_required: bool
    hitl_reasons: Optional[Any] = None
    uploaded_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

@router.get("/queue", response_model=list[QueueItem])
def get_queue(db: Session = Depends(get_db)):
    """Reviewer dashboard feed."""
    return get_hitl_queue(db)
