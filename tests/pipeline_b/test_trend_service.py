from pipeline_b.engines.trend_analyzer import build_chart_json, compute_trend
from pipeline_b.schemas.output import TrendPoint


def _point(date: str, value: float) -> TrendPoint:
    return TrendPoint(
        date=date,
        value=str(value),
        numeric_value=value,
        unit="g/dL",
        is_abnormal=False,
    )


def test_compute_trend_increasing():
    result = compute_trend([_point("2025-01-01", 10.0), _point("2025-02-01", 11.0)])

    assert result["direction"] == "increasing"


def test_compute_trend_decreasing():
    result = compute_trend([_point("2025-01-01", 10.0), _point("2025-02-01", 9.0)])

    assert result["direction"] == "decreasing"


def test_compute_trend_stable():
    result = compute_trend([_point("2025-01-01", 10.0), _point("2025-02-01", 10.4)])

    assert result["direction"] == "stable"


def test_compute_trend_insufficient_data():
    result = compute_trend([_point("2025-01-01", 10.0)])

    assert result["direction"] == "insufficient_data"


def test_percent_change_formula():
    result = compute_trend([_point("2025-01-01", 10.0), _point("2025-02-01", 12.0)])

    assert result["percent_change"] == 20.0


def test_chart_json_structure():
    points = [_point("2025-01-01", 10.0), _point("2025-02-01", 12.0)]

    chart = build_chart_json("hemoglobin", "g/dL", points, 11.5, 16.4)

    assert chart.type == "line_chart"
    assert set(chart.data.keys()) == {"x", "y"}
    assert chart.data["x"] == ["2025-01-01", "2025-02-01"]
    assert chart.data["y"] == [10.0, 12.0]
