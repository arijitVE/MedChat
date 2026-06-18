# pipeline_a/llm_extraction/chunk_extractor.py

import time
from typing import List
from openai import OpenAI

from shared.config import get_settings
from shared.logger import get_logger, log_stage
from pipeline_a.llm_extraction.parser import parse_llm_response, strip_markdown_fences
from shared.schemas.report import ExtractedField

logger = get_logger(__name__)

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=get_settings().OPENAI_API_KEY)
    return _client

_CHUNK_PROMPT = """You are a medical document extraction system. Extract structured key-value data from the following text chunk.

RULES:
- Respond ONLY with valid JSON. No markdown fences. No preamble. No explanation.
- Use lowercase canonical field names.
- Do NOT invent values not present in the text.
- Extract these specific clinical domains if present: patient_info, diagnoses, medications, lab_results, procedures, dates, hospital, recommendations.
- For tests and measurements, include 'unit', 'reference_range', and 'collection_date' if available.

Return a JSON object with a single key "fields" containing an array of objects with these fields:
  "name"             — field name (e.g. "diagnosis", "medication", "hemoglobin")
  "value"            — extracted value
  "unit"             — unit of measurement if applicable (null otherwise)
  "reference_range"  — reference range if applicable (null otherwise)
  "collection_date"  — relevant date if visible (null otherwise)

NOW EXTRACT FROM THIS TEXT:
{chunk_text}
"""

_STRICT_PREFIX = (
    "CRITICAL INSTRUCTION: Return ONLY a JSON object. "
    "No prose. No markdown. No explanation. No formatting. "
    "Start your response with { and end with }. "
    "Nothing else.\n\n"
)

def extract_from_chunk(chunk_text: str, case_id: str, chunk_id: str) -> List[ExtractedField]:
    t_start = time.perf_counter()
    client = _get_client()
    
    prompt = _CHUNK_PROMPT.format(chunk_text=chunk_text)
    fields = []
    
    def _call(p):
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": p}],
            temperature=0.0,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        return strip_markdown_fences(resp.choices[0].message.content or "")

    try:
        raw = _call(prompt)
        fields = parse_llm_response(raw)
    except Exception as exc:
        logger.warning(f"Chunk LLM extraction attempt 1 failed: {exc}")
        
    if not fields:
        try:
            strict_prompt = _STRICT_PREFIX + prompt
            raw = _call(strict_prompt)
            fields = parse_llm_response(raw)
        except Exception as exc:
            logger.warning(f"Chunk LLM extraction attempt 2 failed: {exc}")
            
    if not fields:
        logger.warning(
            "chunk_extraction_empty",
            case_id=case_id,
            chunk_id=chunk_id,
            message="field_count == 0 after both extraction attempts"
        )
        
    duration = (time.perf_counter() - t_start) * 1000
    log_stage(
        logger,
        stage="chunk_extraction",
        job_id=case_id,
        duration_ms=duration,
        status="success" if fields else "error",
        field_count=len(fields)
    )
    
    return fields
