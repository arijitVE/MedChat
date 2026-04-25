# pipeline_a/llm_extraction/fallback.py — Regex-based extraction (last resort after retries)
#
# Activated only after all 3 LLM attempts fail. Returns partial results —
# even one field is better than none. The conflict stage will flag HITL
# for any document where fallback was used.

from __future__ import annotations

import re
from typing import Optional

from shared.schemas.report import DocumentType, ExtractedField

# ---------------------------------------------------------------------------
# Regex patterns for common medical values
# ---------------------------------------------------------------------------

# Primary pattern: "Field Name: 13.5 g/dL" or "SGPT : 45 IU/L"
# Captures: (field_name, value, unit)
_LAB_VALUE_PATTERN = re.compile(
    r"([\w\s\.]{2,30})"          # field name: 2–30 chars of word chars, spaces, dots
    r"\s*[:=]\s*"                 # separator: colon or equals with optional whitespace
    r"(\d+(?:\.\d+)?)"           # numeric value (int or float)
    r"\s*"                        # optional whitespace
    r"(g/dL|mg/dL|%|mmol/L|IU/L|U/L|mIU/mL|ng/mL|pg/mL|"
    r"cells/µL|cells/cumm|µg/dL|mEq/L|mm/hr|fL|pg|"
    r"×10³/µL|×10⁶/µL|g/L|mg/L|µmol/L|seconds|"
    r"thou/uL|mill/uL|units)",   # known medical units (case-sensitive to avoid false positives)
    re.IGNORECASE,
)

# Prescription pattern: "Tab. Amoxicillin 500mg" or "Cap Pantoprazole 40 mg"
_PRESCRIPTION_PATTERN = re.compile(
    r"(?:tab\.?|cap\.?|syp\.?|inj\.?|drops?)\s+"  # dosage form prefix
    r"([\w\-]+)"                                    # drug name
    r"\s+"
    r"(\d+(?:\.\d+)?)"                              # dosage value
    r"\s*"
    r"(mg|ml|g|mcg|µg|IU|units?)",                  # dosage unit
    re.IGNORECASE,
)

# Simple key-value pattern for discharge summaries and radiology
_KEY_VALUE_PATTERN = re.compile(
    r"([\w\s]{2,40})"           # key: 2–40 chars
    r"\s*[:]\s*"                 # colon separator
    r"([^\n,;]{2,100})",         # value: 2–100 chars, until newline/comma/semicolon
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def regex_extract(
    text: str,
    document_type: DocumentType,
) -> list[ExtractedField]:
    """Extract structured fields from raw text using regex patterns.

    This is the last-resort fallback after all LLM attempts fail. Returns
    partial results — even one field is better than returning nothing and
    forcing a full HITL review with zero data.

    Args:
        text: Raw OCR text to extract from.
        document_type: Determines which regex patterns to prioritise.

    Returns:
        List of ExtractedField objects (may be empty if regex finds nothing).
    """
    if not text or not text.strip():
        return []

    fields: list[ExtractedField] = []
    seen_names: set[str] = set()  # deduplicate

    if document_type == DocumentType.prescription:
        fields.extend(_extract_prescription(text, seen_names))

    # Always try lab value pattern (works across document types)
    fields.extend(_extract_lab_values(text, seen_names))

    # For discharge/radiology/unknown: try generic key-value extraction
    if document_type in (
        DocumentType.discharge_summary,
        DocumentType.radiology,
        DocumentType.unknown,
    ) and not fields:
        fields.extend(_extract_key_values(text, seen_names))

    return fields


# ---------------------------------------------------------------------------
# Internal extraction functions
# ---------------------------------------------------------------------------


def _extract_lab_values(
    text: str,
    seen: set[str],
) -> list[ExtractedField]:
    """Extract lab values matching 'Name: Value Unit' pattern."""
    fields: list[ExtractedField] = []
    for match in _LAB_VALUE_PATTERN.finditer(text):
        name = match.group(1).strip().lower()
        value = match.group(2).strip()
        unit = match.group(3).strip()

        if name and name not in seen and len(name) >= 2:
            seen.add(name)
            fields.append(
                ExtractedField(
                    name=name,
                    value=value,
                    unit=unit,
                )
            )
    return fields


def _extract_prescription(
    text: str,
    seen: set[str],
) -> list[ExtractedField]:
    """Extract prescription drugs matching 'Tab/Cap DrugName Dosage Unit' pattern."""
    fields: list[ExtractedField] = []
    for match in _PRESCRIPTION_PATTERN.finditer(text):
        name = match.group(1).strip().lower()
        value = match.group(2).strip()
        unit = match.group(3).strip()

        if name and name not in seen:
            seen.add(name)
            fields.append(
                ExtractedField(
                    name=name,
                    value=value,
                    unit=unit,
                )
            )
    return fields


def _extract_key_values(
    text: str,
    seen: set[str],
) -> list[ExtractedField]:
    """Extract generic key-value pairs from text."""
    fields: list[ExtractedField] = []
    for match in _KEY_VALUE_PATTERN.finditer(text):
        name = match.group(1).strip().lower()
        value = match.group(2).strip()

        # Filter out noise: keys too short, values that are just whitespace
        if (
            name
            and name not in seen
            and len(name) >= 3
            and len(value) >= 1
            and not name.startswith("page")
            and not name.startswith("date")
        ):
            seen.add(name)
            fields.append(
                ExtractedField(
                    name=name,
                    value=value,
                )
            )
    return fields
