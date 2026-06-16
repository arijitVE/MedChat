# pipeline_a/llm_extraction/extractor.py — Gemini API call + retry cascade

from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

from pipeline_a.llm_extraction.parser import parse_llm_response, strip_markdown_fences
from shared.logger import get_logger, log_stage
from shared.config import get_settings
from shared.schemas.report import (
    DocumentType,
    ExtractedField,
    LLMExtractionResult,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(document_type: DocumentType) -> str:
    type_to_file = {
        DocumentType.prescription: "prescription_prompt.txt",
    }

    prompt_file = type_to_file.get(document_type)

    if prompt_file:
        prompt_path = _PROMPTS_DIR / prompt_file
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")

    if document_type == DocumentType.lab_report:
        return _LAB_REPORT_PROMPT
    elif document_type == DocumentType.discharge_summary:
        return _DISCHARGE_PROMPT
    elif document_type == DocumentType.radiology:
        return _RADIOLOGY_PROMPT
    else:
        return _GENERIC_PROMPT


_LAB_REPORT_PROMPT = """Respond in JSON format.
You are a medical data extraction AI.
Extract ALL test results from the provided images of a lab report.

Return a JSON object with a single key "fields" containing
an array of every test found. Example:

{
  "fields": [
    {"name": "hb%", "value": "10.5", "unit": "gm/dl",
     "reference_range": "FEMALE: 11.5 - 16.4 gm/dl",
     "collection_date": "30/10/2025"},
    {"name": "rbc count", "value": "3.5", "unit": "10^6/uL",
     "reference_range": "3.00 - 5.50", "collection_date": null},
    {"name": "wbc count", "value": "8400", "unit": "/cmm",
     "reference_range": "4000-11000", "collection_date": null}
  ]
}

Rules:
- The response MUST be a JSON object with key "fields"
- Extract EVERY test — CBC, differential count, ESR, PCV,
  MCV, MCH, MCHC, platelet count, malaria parasite,
  widal test rows — include ALL of them
- Do not skip any test even if value is qualitative
  (e.g. "Not Found") or abnormal
- Use lowercase for field names
- Return null for missing reference_range or collection_date
"""

_DISCHARGE_PROMPT = """You are a medical document extraction system. Extract structured data from the provided images of a discharge summary.

RULES:
- Respond ONLY with valid JSON. No markdown fences. No preamble. No explanation.
- Use lowercase canonical field names.
- Do NOT invent values not present in the text.

Return a JSON object with a single key "fields" containing an array of objects with these fields:
  "name"             — field name (e.g. "diagnosis", "treatment", "medication")
  "value"            — the extracted value or description
  "unit"             — unit if applicable (null otherwise)
  "reference_range"  — null for discharge summaries
  "collection_date"  — admission/discharge date if visible

NOW EXTRACT FROM THE FOLLOWING DOCUMENT IMAGES:
"""

_RADIOLOGY_PROMPT = """You are a medical document extraction system. Extract structured data from the provided images of a radiology report.

RULES:
- Respond ONLY with valid JSON. No markdown fences. No preamble. No explanation.
- Use lowercase canonical field names.
- Do NOT invent values not present in the text.

Return a JSON object with a single key "fields" containing an array of objects with these fields:
  "name"             — field name (e.g. "findings", "impression", "modality")
  "value"            — the extracted value or description
  "unit"             — null for radiology reports
  "reference_range"  — null for radiology reports
  "collection_date"  — study date if visible

NOW EXTRACT FROM THE FOLLOWING DOCUMENT IMAGES:
"""

_GENERIC_PROMPT = """You are a medical document extraction system. Extract structured key-value data from the provided images of a medical document.

RULES:
- Respond ONLY with valid JSON. No markdown fences. No preamble. No explanation.
- Use lowercase canonical field names.
- Do NOT invent values not present in the text.

Return a JSON object with a single key "fields" containing an array of objects with these fields:
  "name"             — field name
  "value"            — extracted value
  "unit"             — unit of measurement if applicable (null otherwise)
  "reference_range"  — reference range if applicable (null otherwise)
  "collection_date"  — relevant date if visible (null otherwise)

NOW EXTRACT FROM THE FOLLOWING DOCUMENT IMAGES:
"""

_STRICT_PREFIX = (
    "CRITICAL INSTRUCTION: Return ONLY a JSON object. "
    "No prose. No markdown. No explanation. No formatting. "
    "Start your response with { and end with }. "
    "Nothing else.\n\n"
)


# ---------------------------------------------------------------------------
# OpenAI API client (lazy init)
# ---------------------------------------------------------------------------

_client: Any = None


def _get_client() -> Any:
    global _client
    if _client is None:
        settings = get_settings()
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def _call_openai(prompt: str, images: list[bytes]) -> str:
    client = _get_client()

    user_content: list[dict[str, Any]] = [
        {"type": "text", "text": "Extract data from these document pages:"}
    ]
    for img_bytes in images:
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"}
        })

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_content}
        ],
        temperature=0.0,
        max_tokens=2000,
        response_format={"type": "json_object"}
    )

    raw_text = response.choices[0].message.content or ""
    return strip_markdown_fences(raw_text)


# ---------------------------------------------------------------------------
# Core extraction with retry cascade
# ---------------------------------------------------------------------------


def extract_fields(
    images: list[bytes],
    document_type: DocumentType,
    job_id: str,
) -> LLMExtractionResult:
    t_start = time.perf_counter()
    base_prompt = _load_prompt(document_type)
    attempt_count = 0
    raw_response = ""
    fields: list[ExtractedField] = []
    fallback_used = False

    # Attempt 1: standard prompt + images
    attempt_count = 1
    try:
        raw_response = _call_openai(base_prompt, images)
        fields = parse_llm_response(raw_response)
    except Exception as exc:
        logger.warning(
            "llm_attempt_failed",
            attempt=1,
            job_id=job_id,
            error=str(exc),
        )
        fields = []

    # Attempt 2: stricter prompt (on parse fail or empty)
    if not fields:
        attempt_count = 2
        try:
            strict_prompt = _STRICT_PREFIX + base_prompt
            raw_response = _call_openai(strict_prompt, images)
            fields = parse_llm_response(raw_response)
        except Exception as exc:
            logger.warning(
                "llm_attempt_failed",
                attempt=2,
                job_id=job_id,
                error=str(exc),
            )
            fields = []

    llm_latency_ms = (time.perf_counter() - t_start) * 1000

    result = LLMExtractionResult(
        fields=fields,
        raw_llm_response=raw_response,
        attempt_count=attempt_count,
        fallback_used=fallback_used,
    )

    log_stage(
        logger,
        stage="llm_extraction",
        job_id=job_id,
        duration_ms=llm_latency_ms,
        status="success" if fields else "error",
        attempt_count=attempt_count,
        field_count=len(fields),
        fallback_used=fallback_used,
        llm_latency_ms=round(llm_latency_ms, 2),
    )

    return result
