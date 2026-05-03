import json
from types import SimpleNamespace

from pipeline_b.engines import intent_parser


class FakeOpenAI:
    def __init__(self, api_key=None):
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    def _create(self, **kwargs):
        query = kwargs["messages"][-1]["content"].lower()
        if "hemoglobin < 11" in query:
            payload = {
                "field_name": "hemoglobin",
                "operator": "lt",
                "value": 11.0,
                "confidence": 1.0,
            }
        elif "hb below normal" in query:
            payload = {
                "field_name": "hb",
                "operator": "lt",
                "value": 11.5,
                "confidence": 0.95,
            }
        elif "hgb" in query:
            payload = {
                "field_name": "hgb",
                "operator": "any",
                "value": None,
                "confidence": 0.9,
            }
        elif "low hemoglobin" in query:
            payload = {
                "field_name": "hemoglobin",
                "operator": "lt",
                "value": 11.5,
                "confidence": 0.95,
            }
        else:
            payload = {
                "field_name": "hemoglobin",
                "operator": "any",
                "value": None,
                "confidence": 0.75,
            }

        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(payload))
                )
            ]
        )


def _patch_openai(monkeypatch):
    monkeypatch.setattr(intent_parser, "OpenAI", FakeOpenAI)


def test_parse_low_hemoglobin(monkeypatch):
    _patch_openai(monkeypatch)

    result = intent_parser.parse_retrieval_intent("low hemoglobin")

    assert result.field_name == "hemoglobin"
    assert result.operator == "lt"


def test_parse_hb_below_normal(monkeypatch):
    _patch_openai(monkeypatch)

    result = intent_parser.parse_retrieval_intent("hb below normal")

    assert result.field_name == "hemoglobin"
    assert result.operator == "lt"


def test_parse_explicit_threshold(monkeypatch):
    _patch_openai(monkeypatch)

    result = intent_parser.parse_retrieval_intent("hemoglobin < 11")

    assert result.operator == "lt"
    assert result.value == 11.0


def test_parse_any_operator(monkeypatch):
    _patch_openai(monkeypatch)

    result = intent_parser.parse_retrieval_intent("show records")

    assert result.operator == "any"


def test_field_name_normalized(monkeypatch):
    _patch_openai(monkeypatch)

    result = intent_parser.parse_retrieval_intent("hgb")

    assert result.field_name == "hemoglobin"
