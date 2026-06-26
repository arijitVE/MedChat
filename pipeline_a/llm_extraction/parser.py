# pipeline_a/llm_extraction/parser.py — Validates + parses LLM JSON into Pydantic models
#
# Handles the messy reality of LLM output: markdown fences, trailing commas,
# preamble text before JSON, etc. Returns [] on validation failure instead
# of raising — the retry cascade handles recovery.

from __future__ import annotations

import json
import re
from typing import Any

from shared.logger import get_logger
from shared.schemas.report import ExtractedField

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Markdown fence stripping
# ---------------------------------------------------------------------------


def strip_markdown_fences(raw: str) -> str:
    """Remove markdown code fences from LLM response.

    Handles common LLM output patterns:
      ```json ... ```, ```JSON ... ```, ``` ... ```

    Also strips any preamble text before the first [ or { character.

    Args:
        raw: Raw LLM response string.

    Returns:
        Cleaned string with fences removed.
    """
    if not raw:
        return ""

    cleaned = raw.strip()

    # Remove ```json ... ``` or ``` ... ``` fences
    cleaned = re.sub(
        r"```(?:json|JSON)?\s*\n?",
        "",
        cleaned,
    )
    cleaned = cleaned.strip()

    # If there's preamble text before JSON, find the first [ or {
    first_bracket = -1
    for i, ch in enumerate(cleaned):
        if ch in ("[", "{"):
            first_bracket = i
            break

    if first_bracket > 0:
        cleaned = cleaned[first_bracket:]

    # Trim any trailing text after the last ] or }
    last_bracket = -1
    for i in range(len(cleaned) - 1, -1, -1):
        if cleaned[i] in ("]", "}"):
            last_bracket = i
            break

    if last_bracket > 0:
        cleaned = cleaned[: last_bracket + 1]

    return cleaned.strip()


# ---------------------------------------------------------------------------
# JSON parsing with fallback strategies
# ---------------------------------------------------------------------------


def _try_parse_json(raw: str) -> Any | None:
    """Attempt to parse JSON, handling common LLM quirks.

    Args:
        raw: Cleaned JSON string.

    Returns:
        Parsed JSON object or None on failure.
    """
    if not raw:
        return None

    # Attempt 1: direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Attempt 2: fix trailing commas (common LLM mistake)
    try:
        fixed = re.sub(r",\s*([}\]])", r"\1", raw)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_llm_response(raw: str) -> list[ExtractedField]:
    """Parse raw LLM response into validated ExtractedField objects.

    Steps:
    1. Strip markdown fences and preamble
    2. Parse JSON (with trailing comma fix)
    3. Normalise to a list of dicts
    4. Validate each dict against ExtractedField Pydantic model
    5. Return valid fields (skip invalid ones with warning log)

    Returns [] on complete parse failure — never raises. The retry
    cascade in extractor.py handles recovery on empty results.

    Args:
        raw: Raw string response from the LLM.

    Returns:
        List of validated ExtractedField objects. May be empty.
    """
    if not raw or not raw.strip():
        return []

    # Step 1: strip fences
    cleaned = strip_markdown_fences(raw)

    # Step 2: parse JSON
    parsed = _try_parse_json(cleaned)
    if parsed is None:
        logger.warning(
            "llm_json_parse_failed",
            raw_length=len(raw),
            cleaned_preview=cleaned[:200],
        )
        return []

    # Step 3: normalise to list of dicts
    items: list[dict[str, Any]]
    if isinstance(parsed, dict):
        # Single object → wrap in list
        # Handle {"fields": [...]} wrapper pattern
        if "fields" in parsed and isinstance(parsed["fields"], list):
            items = parsed["fields"]
        else:
            items = [parsed]
    elif isinstance(parsed, list):
        items = parsed
    else:
        logger.warning(
            "llm_unexpected_json_type",
            json_type=type(parsed).__name__,
        )
        return []

    return _validate_fields(items)


def _to_float(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _validate_fields(items: list[dict[str, Any]]) -> list[ExtractedField]:
    fields: list[ExtractedField] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            logger.warning("llm_field_not_dict", index=i, type=type(item).__name__)
            continue

        if "name" not in item or "value" not in item:
            logger.warning(
                "llm_field_missing_required",
                index=i,
                keys=list(item.keys()),
            )
            continue

        try:
            field = ExtractedField(
                name=str(item.get("name", "")).strip(),
                value=str(item.get("value", "")).strip(),
                unit=str(item["unit"]).strip() if item.get("unit") else None,
                reference_range=(
                    str(item["reference_range"]).strip()
                    if item.get("reference_range")
                    else None
                ),
                collection_date=(
                    str(item["collection_date"]).strip()
                    if item.get("collection_date")
                    else None
                ),
                numeric_value=_to_float(item.get("numeric_value")),
                ref_low=_to_float(item.get("ref_low")),
                ref_high=_to_float(item.get("ref_high")),
            )
            if field.name and field.value:
                fields.append(field)
            else:
                logger.warning(
                    "llm_field_empty_name_or_value",
                    index=i,
                    name=field.name,
                    value=field.value,
                )
        except Exception as exc:
            logger.warning(
                "llm_field_validation_failed",
                index=i,
                error=str(exc),
                item=item,
            )
            continue

    return fields


def parse_combined_llm_response(raw: str) -> tuple[list[ExtractedField], dict[str, Any]]:
    """Parse unified extraction response containing clinical_fields and document_metadata."""
    if not raw or not raw.strip():
        return [], {}

    cleaned = strip_markdown_fences(raw)
    parsed = _try_parse_json(cleaned)
    if not isinstance(parsed, dict):
        logger.warning("combined_llm_json_not_dict", preview=cleaned[:200])
        return [], {}

    clinical_raw = parsed.get("clinical_fields")
    if isinstance(clinical_raw, list):
        fields = _validate_fields(clinical_raw)
    else:
        logger.warning("combined_llm_missing_clinical_fields")
        fields = []

    meta_raw = parsed.get("document_metadata")
    metadata: dict[str, Any] = {}
    if isinstance(meta_raw, dict):
        for k, v in meta_raw.items():
            if v is not None and str(v).strip() not in ("", "null", "None"):
                metadata[k] = str(v).strip()
            else:
                metadata[k] = None
    else:
        logger.warning("combined_llm_missing_document_metadata")

    return fields, metadata
