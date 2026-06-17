import time

from sqlalchemy.orm import Session

from langchain_core.prompts import ChatPromptTemplate

from pipeline_b.adapters.pipeline_a_adapter import get_all_records_for_patient
from pipeline_b.cache.response_cache import get_cached, make_cache_key, set_cache
from pipeline_b.engines.generator import _build_context, _get_llm
from pipeline_b.schemas.output import AnalyticsResult, ChartJSON
from shared.logger import get_logger


logger = get_logger(__name__)


def _generate_analytics_insight(abnormal_fields: list) -> tuple[str, float]:
    if not abnormal_fields:
        return "No abnormal fields were detected in the available records.", 0

    t_start = time.time()
    insight_context = _build_context(abnormal_fields, max_fields=10)
    insight_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a clinical assistant. Summarize key findings. Do not diagnose.",
            ),
            (
                "human",
                "Abnormal findings:\n{context}\n\nProvide a brief clinical summary.",
            ),
        ]
    )
    insight_chain = insight_prompt | _get_llm()
    content = insight_chain.invoke({"context": insight_context}).content
    insight = content if isinstance(content, str) else str(content)
    return insight or "", round((time.time() - t_start) * 1000, 2)


def get_patient_analytics(patient_id: str, db: Session) -> AnalyticsResult:
    cache_key = make_cache_key("analytics", patient_id, "analytics")
    cached = get_cached(cache_key)
    if cached:
        return AnalyticsResult.model_validate({**cached, "cached": True})

    records = get_all_records_for_patient(patient_id, db)
    all_fields = [f for r in records for f in r.fields]

    abnormal = [f for f in all_fields if f.is_abnormal is True]
    normal = [f for f in all_fields if f.is_abnormal is False]

    latest_fields = records[-1].fields if records else []
    numeric_fields = [f for f in latest_fields if f.numeric_value is not None]
    chart = ChartJSON(
        type="bar_chart",
        data={
            "fields": [f.name for f in numeric_fields],
            "values": [f.numeric_value for f in numeric_fields],
            "ref_low": [f.ref_low for f in numeric_fields],
            "ref_high": [f.ref_high for f in numeric_fields],
        },
        meta={
            "patient_id": patient_id,
            "date": records[-1].processed_at.isoformat() if records else "",
        },
    )

    insight, llm_latency_ms = _generate_analytics_insight(abnormal[:10])

    result = AnalyticsResult(
        patient_id=patient_id,
        abnormal_fields=abnormal,
        normal_fields=normal,
        abnormal_count=len(abnormal),
        normal_count=len(normal),
        chart_json=chart,
        ai_insight=insight,
    )
    set_cache(cache_key, result.model_dump(), "analytics")
    logger.info(
        "analytics_complete",
        abnormal_count=len(abnormal),
        normal_count=len(normal),
        llm_latency_ms=llm_latency_ms,
    )
    return result
