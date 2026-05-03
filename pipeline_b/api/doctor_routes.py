from fastapi import APIRouter, Depends

from pipeline_b.engines.query_classifier import classify
from pipeline_b.engines.retriever import retrieve_by_filter
from pipeline_b.engines.trend_analyzer import analyze_trend
from pipeline_b.schemas.query import ParsedFilter, PersonaType, QueryType, UserQuery
from pipeline_b.services.analytics_service import get_patient_analytics
from pipeline_b.services.reasoning_service import handle_reasoning_query
from pipeline_b.services.retrieval_service import handle_retrieval_query
from pipeline_b.services.trend_service import handle_trend_query
from shared.db.session import get_db


router = APIRouter(prefix="/api/doctor", tags=["doctor"])


@router.post("/query")
async def doctor_query(body: UserQuery, db=Depends(get_db)):
    classified = classify(body.text, PersonaType.doctor)
    classified.patient_id = body.patient_id
    classified.filters = body.filters

    if classified.query_type == QueryType.retrieval:
        return handle_retrieval_query(classified, db)
    if classified.query_type == QueryType.reasoning:
        return handle_reasoning_query(classified, body.patient_id, db)
    if classified.query_type == QueryType.trend:
        return handle_trend_query(classified, body.patient_id, db)
    return handle_reasoning_query(classified, body.patient_id, db)


@router.get("/patient/{patient_id}/summary")
async def patient_summary(patient_id: str, db=Depends(get_db)):
    return get_patient_analytics(patient_id, db)


@router.get("/patient/{patient_id}/trend")
async def patient_trend(patient_id: str, field_name: str, db=Depends(get_db)):
    return analyze_trend(patient_id, field_name)


@router.get("/analytics")
async def analytics(
    field_name: str,
    operator: str,
    value: float | None = None,
    db=Depends(get_db),
):
    parsed = ParsedFilter(
        field_name=field_name,
        operator=operator,
        value=value,
        raw_query="",
        confidence=1.0,
    )
    return retrieve_by_filter(parsed)
