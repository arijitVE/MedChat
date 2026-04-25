# pipeline_a/llm_extraction/extractor.py — Gemini API call + 3-attempt retry cascade
#
# This stage does PARSING ONLY — not reasoning or trend analysis (Pipeline B).
# Implements the exact retry cascade from blueprint Step 6:
#   Attempt 1: standard prompt + full OCR text
#   Attempt 2: stricter prompt (on parse fail or empty)
#   Attempt 3: simplified input (first 500 tokens)
#   Fallback:  regex extraction via fallback.py
#   Last resort: fields=[], fallback_used=True → conflict stage flags HITL

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

from pipeline_a.llm_extraction.fallback import regex_extract
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
    """Load the prompt template for the given document type.

    Falls back to generic extraction prompt if no type-specific template
    exists.

    Args:
        document_type: The document classification.

    Returns:
        Prompt text string.
    """
    # Map DocumentType → prompt file
    type_to_file = {
        DocumentType.prescription: "prescription_prompt.txt",
    }

    prompt_file = type_to_file.get(document_type)

    if prompt_file:
        prompt_path = _PROMPTS_DIR / prompt_file
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")

    # Default prompts for document types without a dedicated template
    if document_type == DocumentType.lab_report:
        return _LAB_REPORT_PROMPT
    elif document_type == DocumentType.discharge_summary:
        return _DISCHARGE_PROMPT
    elif document_type == DocumentType.radiology:
        return _RADIOLOGY_PROMPT
    else:
        return _GENERIC_PROMPT


# ---------------------------------------------------------------------------
# Inline prompt templates (for types without dedicated .txt files)
# ---------------------------------------------------------------------------

_LAB_REPORT_PROMPT = """Respond in JSON format.
You are a medical data extraction AI.
Extract ALL test results from the lab report text provided.

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

_DISCHARGE_PROMPT = """You are a medical document extraction system. Extract structured data from this discharge summary.

RULES:
- Respond ONLY with valid JSON. No markdown fences. No preamble. No explanation.
- Use lowercase canonical field names.
- Do NOT invent values not present in the text.

Return a JSON array of objects with these fields:
  "name"             — field name (e.g. "diagnosis", "treatment", "medication")
  "value"            — the extracted value or description
  "unit"             — unit if applicable (null otherwise)
  "reference_range"  — null for discharge summaries
  "collection_date"  — admission/discharge date if visible

NOW EXTRACT FROM THE FOLLOWING DISCHARGE SUMMARY TEXT:
"""

_RADIOLOGY_PROMPT = """You are a medical document extraction system. Extract structured data from this radiology report.

RULES:
- Respond ONLY with valid JSON. No markdown fences. No preamble. No explanation.
- Use lowercase canonical field names.
- Do NOT invent values not present in the text.

Return a JSON array of objects with these fields:
  "name"             — field name (e.g. "findings", "impression", "modality")
  "value"            — the extracted value or description
  "unit"             — null for radiology reports
  "reference_range"  — null for radiology reports
  "collection_date"  — study date if visible

NOW EXTRACT FROM THE FOLLOWING RADIOLOGY REPORT TEXT:
"""

_GENERIC_PROMPT = """You are a medical document extraction system. Extract structured key-value data from this medical document.

RULES:
- Respond ONLY with valid JSON. No markdown fences. No preamble. No explanation.
- Use lowercase canonical field names.
- Do NOT invent values not present in the text.

Return a JSON array of objects with these fields:
  "name"             — field name
  "value"            — extracted value
  "unit"             — unit of measurement if applicable (null otherwise)
  "reference_range"  — reference range if applicable (null otherwise)
  "collection_date"  — relevant date if visible (null otherwise)

NOW EXTRACT FROM THE FOLLOWING MEDICAL DOCUMENT TEXT:
"""

# Stricter prompt used on Attempt 2 (prepended to the standard prompt)
_STRICT_PREFIX = (
    "CRITICAL INSTRUCTION: Return ONLY a JSON array. "
    "No prose. No markdown. No explanation. No formatting. "
    "Start your response with [ and end with ]. "
    "Nothing else.\n\n"
)


# ---------------------------------------------------------------------------
# OpenAI API client (lazy init)
# ---------------------------------------------------------------------------

_client: Any = None


def _get_client() -> Any:
    """Return a cached OpenAI client instance.

    Configures the API key on first call. Uses gpt-4o
    with temperature=0.0 and json_object response format for deterministic parsing.
    """
    global _client
    if _client is None:
        settings = get_settings()
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def _call_openai(prompt: str, text: str) -> str:
    """Call OpenAI API with the given prompt and text.

    Args:
        prompt: System/instruction prompt.
        text: OCR text to extract from (passed as user message).

    Returns:
        Raw response text from the model.

    Raises:
        Exception: Any API error is propagated to the caller for retry handling.
    """
    client = _get_client()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
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


def _truncate_to_tokens(text: str, max_tokens: int = 500) -> str:
    """Truncate text to approximately max_tokens words.

    A rough token ≈ word approximation for the simplified input attempt.

    Args:
        text: Full OCR text.
        max_tokens: Maximum number of whitespace-delimited tokens.

    Returns:
        Truncated text string.
    """
    words = text.split()
    if len(words) <= max_tokens:
        return text
    return " ".join(words[:max_tokens])


def extract_fields(
    ocr_text: str,
    document_type: DocumentType,
    job_id: str,
) -> LLMExtractionResult:
    """Extract structured fields from OCR text using Gemini with retry cascade.

    Implements the exact retry cascade from blueprint Step 6:
      Attempt 1: standard prompt + full OCR text
      Attempt 2: stricter prompt (on parse fail or empty response)
      Attempt 3: simplified input (first 500 tokens)
      Fallback:  regex extraction for common medical patterns
      Last resort: fields=[], fallback_used=True

    Args:
        ocr_text: Full raw OCR text from the document.
        document_type: Detected document type for prompt selection.
        job_id: Job identifier for logging.

    Returns:
        LLMExtractionResult with fields, attempt_count, and fallback_used.
        Never raises — all errors are caught and handled via retry/fallback.
    """
    t_start = time.perf_counter()
    base_prompt = _load_prompt(document_type)
    attempt_count = 0
    raw_response = ""
    fields: list[ExtractedField] = []
    fallback_used = False

    # ---------------------------------------------------------------
    # Attempt 1: standard prompt + full OCR text
    # ---------------------------------------------------------------
    attempt_count = 1
    try:
        raw_response = _call_openai(base_prompt, ocr_text)
        fields = parse_llm_response(raw_response)
    except Exception as exc:
        logger.warning(
            "llm_attempt_failed",
            attempt=1,
            job_id=job_id,
            error=str(exc),
        )
        fields = []

    # ---------------------------------------------------------------
    # Attempt 2: stricter prompt (on parse fail or empty)
    # ---------------------------------------------------------------
    if not fields:
        attempt_count = 2
        try:
            strict_prompt = _STRICT_PREFIX + base_prompt
            raw_response = _call_openai(strict_prompt, ocr_text)
            fields = parse_llm_response(raw_response)
        except Exception as exc:
            logger.warning(
                "llm_attempt_failed",
                attempt=2,
                job_id=job_id,
                error=str(exc),
            )
            fields = []

    # ---------------------------------------------------------------
    # Attempt 3: simplified input (first 500 tokens only)
    # ---------------------------------------------------------------
    if not fields:
        attempt_count = 3
        try:
            simplified_text = _truncate_to_tokens(ocr_text, max_tokens=500)
            strict_prompt = _STRICT_PREFIX + base_prompt
            raw_response = _call_openai(strict_prompt, simplified_text)
            fields = parse_llm_response(raw_response)
        except Exception as exc:
            logger.warning(
                "llm_attempt_failed",
                attempt=3,
                job_id=job_id,
                error=str(exc),
            )
            fields = []

    # ---------------------------------------------------------------
    # Fallback: regex extraction (after all 3 LLM attempts failed)
    # ---------------------------------------------------------------
    if not fields:
        fallback_used = True
        try:
            fields = regex_extract(ocr_text, document_type)
            logger.info(
                "llm_fallback_activated",
                job_id=job_id,
                regex_field_count=len(fields),
            )
        except Exception as exc:
            logger.error(
                "llm_fallback_failed",
                job_id=job_id,
                error=str(exc),
            )
            fields = []

    # ---------------------------------------------------------------
    # Build result and log
    # ---------------------------------------------------------------
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
