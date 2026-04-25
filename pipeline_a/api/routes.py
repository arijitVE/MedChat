# pipeline_a/api/routes.py
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, Form, HTTPException, File
from sqlalchemy.orm import Session
from pydantic import BaseModel

from shared.db.session import get_db
from shared.db.models.document import upsert_job, DocumentJob
from shared.schemas.report import JobStatus, PipelineAOutput, ScoredField, DocumentType, FieldStatus
from pipeline_a.ingestion import loader
from pipeline_a.worker.tasks import process_document_task
from pipeline_a.hitl import service as hitl_service

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

class UploadResponse(BaseModel):
    job_id: str
    status: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    output: Optional[PipelineAOutput] = None

@router.post("/upload", response_model=UploadResponse)
def upload_document(
    patient_id: str = Form(...),
    document_type: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    file_bytes = file.file.read()
    
    try:
        doc = loader.ingest(file_bytes, file.filename or "", patient_id)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=[{"loc": ["body", "file"], "msg": str(e), "type": "value_error"}]
        )
        
    job_id = doc.job_id
    doc_type = document_type if document_type else doc.document_type.value
    
    upsert_job(
        db, 
        job_id, 
        patient_id=patient_id, 
        document_type=doc_type, 
        status=JobStatus.pending.value,
        file_name=file.filename
    )
    
    process_document_task.delay(job_id, patient_id, file_bytes.hex(), doc_type)
    
    return UploadResponse(job_id=job_id, status=JobStatus.pending.value)


@router.get("/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(DocumentJob).filter(DocumentJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    response = JobStatusResponse(job_id=job.job_id, status=job.status)
    
    if job.status in (JobStatus.completed.value, JobStatus.hitl_required.value):
        from shared.db.models.extraction import ReportField
        fields = db.query(ReportField).filter(ReportField.job_id == job_id).all()
        scored_fields = [
            ScoredField(
                name=f.name,
                value=f.value,
                unit=f.unit,
                reference_range=f.reference_range,
                collection_date=f.collection_date,
                confidence=f.confidence,
                status=FieldStatus(f.status),
                hitl_reason=f.hitl_reason
            ) for f in fields
        ]
        
        response.output = PipelineAOutput(
            job_id=job.job_id,
            patient_id=job.patient_id,
            document_type=DocumentType(job.document_type),
            scored_fields=scored_fields,
            hitl_required=job.hitl_required,
            hitl_reasons=job.hitl_reasons or [],
            job_status=JobStatus(job.status),
            structured_text_for_embedding=job.structured_text_for_embedding or "",
            ocr_latency_ms=job.ocr_latency_ms,
            llm_latency_ms=job.llm_latency_ms
        )
        
    return response


@router.post("/{job_id}/hitl-review", response_model=PipelineAOutput)
def hitl_review(job_id: str, overrides: list[ScoredField], db: Session = Depends(get_db)):
    job = db.query(DocumentJob).filter(DocumentJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    try:
        output = hitl_service.apply_hitl_review(job_id, overrides, db)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=[{"loc": ["body"], "msg": str(e), "type": "value_error"}]
        )
        
    return output
