import time

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from shared.config import get_settings
from shared.logger import get_logger


logger = get_logger(__name__)


DOCTOR_SYSTEM = """You are a clinical decision support assistant.
Interpret lab results for doctors. Use clinical terminology.
Always output valid JSON matching this schema:
{
  "interpretation": "...",
  "clinical_significance": "...",
  "possible_conditions": ["..."],
  "critical_flags": ["..."],
  "confidence": 0.85,
  "citations": []
}
Rules:
- Never make definitive diagnosis — provide differential
- Flag critical values (e.g. Hb < 7 is critical)
- citations is always [] (Phase 3 will populate PubMed refs)
- confidence reflects data quality, not certainty of diagnosis
"""


PATIENT_SYSTEM = """You are a health information assistant.
Explain lab results to patients in simple language (8th grade level).
Always output valid JSON:
{
  "response": "...",
  "simplified_fields": [{"name": "...", "value": "...", "status": "..."}]
}
Rules:
- Never diagnose
- Never recommend or contraindicate medications
- Use plain English: "Your hemoglobin is a bit low" not "Hb 10.5 g/dL"
- Be honest but reassuring
- Always encourage seeing a doctor
"""


DISCLAIMER = (
    "This explanation is for informational purposes only and does not "
    "constitute medical advice. Please consult your doctor for "
    "interpretation and treatment decisions."
)


def _get_llm():
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0.0,
        api_key=get_settings().OPENAI_API_KEY,
    )


def _build_context(fields: list, max_fields: int = 15) -> str:
    sorted_fields = sorted(
        fields,
        key=lambda f: (
            f.is_abnormal is True,
            f.processed_at,
        ),
        reverse=True,
    )[:max_fields]
    lines = []
    for f in sorted_fields:
        status = (
            "ABNORMAL"
            if f.is_abnormal
            else "NORMAL"
            if f.is_abnormal is False
            else "UNKNOWN"
        )
        lines.append(
            f"{f.name}: {f.value} {f.unit or ''} "
            f"(ref: {f.reference_range or 'unknown'}) — {status}"
        )
    return "\n".join(lines)


def generate_doctor_reasoning(
    fields: list,
    query: str,
    max_fields: int = 15,
) -> dict:
    t = time.time()
    context_fields = sorted(
        fields,
        key=lambda f: (
            f.is_abnormal is True,
            f.processed_at,
        ),
        reverse=True,
    )[:max_fields]
    context = _build_context(context_fields, max_fields=max_fields)
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=DOCTOR_SYSTEM),
            ("human", "Patient data:\n{context}\n\nQuestion: {query}"),
        ]
    )
    chain = (
        prompt
        | _get_llm().bind(response_format={"type": "json_object"})
        | JsonOutputParser()
    )
    result = chain.invoke({"context": context, "query": query})
    result["citations"] = []
    logger.info(
        "doctor_reasoning_generated",
        llm_latency_ms=round((time.time() - t) * 1000, 2),
        field_count_used=len(context_fields),
    )
    return result


def generate_patient_explanation(
    fields: list,
    query: str,
) -> dict:
    t = time.time()
    context = _build_context(fields, max_fields=10)
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=PATIENT_SYSTEM),
            ("human", "Patient data:\n{context}\n\nQuestion: {query}"),
        ]
    )
    chain = (
        prompt
        | _get_llm().bind(response_format={"type": "json_object"})
        | JsonOutputParser()
    )
    result = chain.invoke({"context": context, "query": query})
    result["disclaimer"] = DISCLAIMER
    logger.info(
        "patient_explanation_generated",
        llm_latency_ms=round((time.time() - t) * 1000, 2),
    )
    return result
