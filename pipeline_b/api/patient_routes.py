from fastapi import APIRouter, Depends, HTTPException

from pipeline_b.adapters.pipeline_a_adapter import (
    get_all_records_for_patient,
    get_patient_record,
)
from pipeline_b.engines.query_classifier import classify
from pipeline_b.schemas.query import ClassifiedQuery, PersonaType, QueryType, UserQuery
from pipeline_b.services.patient_service import handle_patient_query
from shared.db.session import get_db


router = APIRouter(prefix="/api/patient", tags=["patient"])


@router.post("/query")
async def patient_query(body: UserQuery, db=Depends(get_db)):
    classified = classify(body.text, PersonaType.patient)
    classified.patient_id = body.patient_id
    classified.filters = body.filters
    return handle_patient_query(classified, body.patient_id, db)


@router.get("/records")
async def patient_records(patient_id: str, db=Depends(get_db)):
    records = get_all_records_for_patient(patient_id, db)
    return [
        {
            "job_id": record.job_id,
            "date": record.processed_at,
            "document_type": record.document_type,
            "field_count": len(record.fields),
        }
        for record in records
    ]


@router.get("/report/{job_id}/explain")
async def explain_report(job_id: str, patient_id: str, db=Depends(get_db)):
    record = get_patient_record(patient_id, job_id, db)
    if record is None:
        raise HTTPException(status_code=404, detail="Report not found")

    classified = ClassifiedQuery(
        text="explain my report",
        persona=PersonaType.patient,
        query_type=QueryType.patient_chat,
        confidence=1.0,
        classification_method="rule",
        patient_id=patient_id,
    )
    return handle_patient_query(classified, patient_id, db)
