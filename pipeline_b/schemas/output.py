from datetime import datetime

from pydantic import BaseModel

from pipeline_b.schemas.input import ClinicalField


class TrendPoint(BaseModel):
    date: str
    value: str
    numeric_value: float | None
    unit: str | None
    is_abnormal: bool | None


class ChartJSON(BaseModel):
    type: str
    data: dict
    meta: dict


class RetrievalResult(BaseModel):
    records: list[dict]
    total_count: int
    query_interpretation: str
    retrieval_type: str


class ReasoningResult(BaseModel):
    interpretation: str
    clinical_significance: str
    possible_conditions: list[str]
    critical_flags: list[str]
    confidence: float
    citations: list[str] = []
    data_used: list[ClinicalField]
    cached: bool = False


class TrendResult(BaseModel):
    field_name: str
    patient_id: str
    data_points: list[TrendPoint]
    trend_direction: str
    percent_change: float | None
    chart_json: ChartJSON
    insight: str
    cached: bool = False


class PatientChatResult(BaseModel):
    response: str
    simplified_fields: list[dict]
    disclaimer: str
    safety_blocked: bool = False


class AnalyticsResult(BaseModel):
    patient_id: str
    abnormal_fields: list[ClinicalField]
    normal_fields: list[ClinicalField]
    abnormal_count: int
    normal_count: int
    chart_json: ChartJSON
    ai_insight: str
    cached: bool = False


class CachedResponse(BaseModel):
    cache_key: str
    result: dict
    created_at: datetime
    query_type: str
