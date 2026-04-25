# pipeline_a/normalization/normalizer.py — Synonym expansion, unit/value canonicalization
#
# Stage 4 of Pipeline A. Canonicalizes field names, values, and units from
# LLM extraction output before comparison in the matching stage.
# This removes 60–70% of false conflicts downstream.
#
# CRITICAL: No synonym maps are defined in this file.
# MEDICAL_SYNONYMS and UNIT_SYNONYMS live in shared/utils/medical_dict.py
# and are imported as read-only configuration.

from __future__ import annotations

import time

from shared.logger import get_logger, log_stage
from shared.schemas.report import (
    DocumentType,
    ExtractedField,
    LLMExtractionResult,
    NormalizedField,
    NormalizationResult,
)
from shared.utils.medical_dict import MEDICAL_SYNONYMS, UNIT_SYNONYMS
from shared.utils.text import remove_thousands_separators
from shared.utils.validators import validate_field

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Individual normalization functions
# ---------------------------------------------------------------------------


def normalize_name(name: str) -> str:
    """Canonicalize a field name using MEDICAL_SYNONYMS.

    Lowercases, strips whitespace, then looks up the canonical name in
    the synonym map. Returns the original (cleaned) name if no mapping
    exists.

    Args:
        name: Raw field name from LLM extraction (e.g. "hgb", "SGPT", "Hb").

    Returns:
        Canonical field name (e.g. "hemoglobin", "alanine aminotransferase").

    Examples:
        >>> normalize_name("hgb")
        'hemoglobin'
        >>> normalize_name("SGPT")
        'alanine aminotransferase'
        >>> normalize_name("hemoglobin")
        'hemoglobin'
        >>> normalize_name("  Hb  ")
        'hemoglobin'
    """
    cleaned = name.strip().lower()
    return MEDICAL_SYNONYMS.get(cleaned, cleaned)


def normalize_unit(unit: str | None) -> str | None:
    """Canonicalize a unit string using UNIT_SYNONYMS.

    Lowercases, strips whitespace, then looks up the canonical unit form.
    Returns the original unit (preserving its original casing) if no
    mapping exists. Returns None if input is None or empty.

    Args:
        unit: Raw unit from LLM extraction (e.g. "g/dl", "cells/cumm", "mg").

    Returns:
        Canonical unit (e.g. "g/dL", "cells/µL", "mg"), or None.

    Examples:
        >>> normalize_unit("g/dl")
        'g/dL'
        >>> normalize_unit("cells/cumm")
        'cells/µL'
        >>> normalize_unit(None)
        >>> normalize_unit("")
    """
    if not unit or not unit.strip():
        return None
    cleaned = unit.strip().lower()
    return UNIT_SYNONYMS.get(cleaned, unit.strip())


def normalize_value(value: str) -> str:
    """Clean a field value: strip whitespace and remove thousands separators.

    Handles both Indian ("1,50,000") and international ("1,000,000") comma
    formats. Preserves decimal points.

    Args:
        value: Raw value from LLM extraction.

    Returns:
        Cleaned value string.

    Examples:
        >>> normalize_value("  1,50,000  ")
        '150000'
        >>> normalize_value("13.5")
        '13.5'
        >>> normalize_value(" 500 ")
        '500'
    """
    if not value:
        return ""
    stripped = value.strip()
    return remove_thousands_separators(stripped)


# ---------------------------------------------------------------------------
# Core normalization pipeline
# ---------------------------------------------------------------------------


def run_normalization(
    llm_result: LLMExtractionResult,
    document_type: DocumentType = DocumentType.unknown,
    job_id: str = "",
) -> NormalizationResult:
    """Normalize all extracted fields: names, values, and units.

    For each ExtractedField in the LLM result:
    1. normalize_name → MEDICAL_SYNONYMS lookup
    2. normalize_value → strip whitespace, remove comma separators
    3. normalize_unit → UNIT_SYNONYMS lookup
    4. Validate field using shared.utils.validators.validate_field
    5. Preserve original values alongside normalized in NormalizedField

    Fields that fail validation are still included in the output (the
    confidence scorer will handle them downstream) but a warning is logged.

    Args:
        llm_result: Output from the LLM extraction stage.
        document_type: Document type for context-aware field validation.
        job_id: Job identifier for structured logging.

    Returns:
        NormalizationResult containing all NormalizedField objects
        with both original and normalized representations.
    """
    t_start = time.perf_counter()
    normalized_fields: list[NormalizedField] = []

    for field in llm_result.fields:
        # --- Step 1: Normalize name ---
        original_name = field.name
        canonical_name = normalize_name(original_name)

        # --- Step 2: Normalize value ---
        original_value = field.value
        canonical_value = normalize_value(original_value)

        # --- Step 3: Normalize unit ---
        canonical_unit = normalize_unit(field.unit)

        # --- Step 4: Validate field ---
        is_valid = validate_field(canonical_name, canonical_value, document_type)
        if not is_valid:
            logger.warning(
                "normalization_field_validation_failed",
                job_id=job_id,
                field_name=canonical_name,
                original_name=original_name,
                value=canonical_value,
            )
            # Still include the field — downstream stages handle confidence

        # --- Step 5: Build NormalizedField (preserving originals) ---
        normalized_fields.append(
            NormalizedField(
                original_name=original_name,
                normalized_name=canonical_name,
                original_value=original_value,
                normalized_value=canonical_value,
                unit=canonical_unit,
                reference_range=field.reference_range,
                collection_date=field.collection_date,
            )
        )

    # --- Log stage exit ---
    duration_ms = (time.perf_counter() - t_start) * 1000
    log_stage(
        logger,
        stage="normalization",
        job_id=job_id,
        duration_ms=duration_ms,
        status="success",
        field_count=len(normalized_fields),
    )

    return NormalizationResult(fields=normalized_fields)
