from enum import Enum

from pydantic import BaseModel


class QueryType(str, Enum):
    retrieval = "retrieval"
    reasoning = "reasoning"
    trend = "trend"
    patient_chat = "patient_chat"


class PersonaType(str, Enum):
    doctor = "doctor"
    patient = "patient"


class UserQuery(BaseModel):
    text: str
    persona: PersonaType
    patient_id: str | None = None
    filters: dict | None = None


class ClassifiedQuery(UserQuery):
    query_type: QueryType
    confidence: float
    classification_method: str


class ParsedFilter(BaseModel):
    """Output of intent_parser - structured retrieval intent."""

    field_name: str
    operator: str
    value: float | None
    raw_query: str
    confidence: float
