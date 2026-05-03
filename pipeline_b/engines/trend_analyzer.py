import time

from openai import OpenAI

from pipeline_b.schemas.output import ChartJSON, TrendPoint, TrendResult
from pipeline_b.vector_db.qdrant_client import get_patient_field_history
from shared.config import get_settings
from shared.logger import get_logger


logger = get_logger(__name__)


def extract_time_series(patient_id: str, field_name: str) -> list[TrendPoint]:
    records = get_patient_field_history(patient_id, field_name)
    numeric_records = [
        record for record in records if record.get("numeric_value") is not None
    ]
    numeric_records = sorted(
        numeric_records,
        key=lambda record: record.get("collection_date") or "",
    )

    return [
        TrendPoint(
            date=record.get("collection_date") or record.get("processed_at") or "",
            value=str(record.get("value")),
            numeric_value=record.get("numeric_value"),
            unit=record.get("unit"),
            is_abnormal=record.get("is_abnormal"),
        )
        for record in numeric_records
    ]


def compute_trend(points: list[TrendPoint]) -> dict:
    if len(points) < 2:
        return {
            "direction": "insufficient_data",
            "percent_change": None,
            "first_value": None,
            "last_value": None,
        }

    first = points[0].numeric_value
    last = points[-1].numeric_value
    if first is None or last is None:
        return {
            "direction": "insufficient_data",
            "percent_change": None,
            "first_value": first,
            "last_value": last,
        }

    pct = (last - first) / first * 100 if first != 0 else None
    if pct is not None and pct > 5:
        direction = "increasing"
    elif pct is not None and pct < -5:
        direction = "decreasing"
    else:
        direction = "stable"

    return {
        "direction": direction,
        "percent_change": pct,
        "first_value": first,
        "last_value": last,
    }


def build_chart_json(
    field_name: str,
    unit: str | None,
    points: list[TrendPoint],
    ref_low: float | None = None,
    ref_high: float | None = None,
) -> ChartJSON:
    return ChartJSON(
        type="line_chart",
        data={
            "x": [p.date for p in points],
            "y": [p.numeric_value for p in points],
        },
        meta={
            "label": field_name,
            "unit": unit,
            "ref_low": ref_low,
            "ref_high": ref_high,
        },
    )


def _generate_trend_insight(context: str) -> str:
    client = OpenAI(api_key=get_settings().OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "Explain this computed lab trend concisely. "
                    "Do not perform calculations or infer from raw data."
                ),
            },
            {"role": "user", "content": context},
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content or ""


def analyze_trend(patient_id: str, field_name: str) -> TrendResult:
    t_start = time.time()
    points = extract_time_series(patient_id, field_name)
    trend_data = compute_trend(points)

    records = get_patient_field_history(patient_id, field_name)
    numeric_records = [
        record for record in records if record.get("numeric_value") is not None
    ]
    ref_low = numeric_records[0].get("ref_low") if numeric_records else None
    ref_high = numeric_records[0].get("ref_high") if numeric_records else None
    unit = points[0].unit if points else None

    chart_json = build_chart_json(field_name, unit, points, ref_low, ref_high)
    context = (
        f"{field_name}: {trend_data['direction']}, "
        f"{trend_data['percent_change']}% change, "
        f"first={trend_data['first_value']}, "
        f"last={trend_data['last_value']}, "
        f"reference={ref_low}-{ref_high}"
    )
    insight = _generate_trend_insight(context)

    result = TrendResult(
        field_name=field_name,
        patient_id=patient_id,
        data_points=points,
        trend_direction=trend_data["direction"],
        percent_change=trend_data["percent_change"],
        chart_json=chart_json,
        insight=insight,
    )
    logger.info(
        "trend_analyzed",
        field_name=field_name,
        patient_id=patient_id,
        data_points_count=len(points),
        trend_direction=result.trend_direction,
        percent_change=result.percent_change,
        duration_ms=round((time.time() - t_start) * 1000, 2),
    )
    return result
