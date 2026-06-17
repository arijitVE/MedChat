import json
import time

from openai import OpenAI

from pipeline_b.schemas.query import ParsedFilter
from shared.config import get_settings
from shared.logger import get_logger


logger = get_logger(__name__)


INTENT_SYSTEM_PROMPT = """
You are a medical query intent parser.
Extract the retrieval filter from the query.

Return JSON:
{
  "field_name": "canonical field name (lowercase)",
  "operator": "lt | gt | eq | lte | gte | any",
  "value": number or null,
  "confidence": 0.0-1.0
}

Rules:
- Use canonical field names: hemoglobin, platelet count, neutrophil, etc.
- "low" / "below normal" / "anemia" → operator: lt, value: reference low
  For hemoglobin: female ref low = 11.5, male = 13.5 → use 11.5 (conservative)
- "high" / "elevated" / "above normal" → operator: gt, value: reference high
- If no threshold implied → operator: any, value: null
- Do NOT query the database — only extract intent.
"""


def _normalize_parsed_field(raw: str) -> str:
    from shared.utils.medical_dict import MEDICAL_SYNONYMS

    return MEDICAL_SYNONYMS.get(raw.strip().lower(), raw.strip().lower())


def parse_retrieval_intent(query: str) -> ParsedFilter:
    t_start = time.time()
    client = OpenAI(api_key=get_settings().OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content or "{}")
    field_name = _normalize_parsed_field(result["field_name"])
    parsed = ParsedFilter(
        field_name=field_name,
        operator=result["operator"],
        value=result["value"],
        raw_query=query,
        confidence=result["confidence"],
    )
    logger.info(
        "intent_parsed",
        field_name=parsed.field_name,
        operator=parsed.operator,
        value=parsed.value,
        confidence=parsed.confidence,
        duration_ms=round((time.time() - t_start) * 1000, 2),
    )
    return parsed
