from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CaseCreate(BaseModel):
    title: str
    description: Optional[str] = None

class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    title: Optional[str]
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    case_id: str
    file_name: str
    mime_type: str
    doc_type: str
    status: str
    uploaded_at: datetime

class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    case_id: str
    status: str
    progress: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
