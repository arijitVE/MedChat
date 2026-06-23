# shared/utils/validators.py — Field validation rules (dosage format, frequency patterns)
# Imported wherever field validation is needed across the pipeline.
# All validation rules are centralized here — do not duplicate in stage modules.

from __future__ import annotations

import re

from shared.schemas.report import DocumentType


# ---------------------------------------------------------------------------
# Dosage validation
# ---------------------------------------------------------------------------

# Matches common dosage patterns:
#   "500mg", "500 mg", "0.5mg", "250 mg/5ml", "10mg/kg", "5-10 mg",
#   "500mg-1g", "100,000 IU", "1.5 g", "2.5ml"
_DOSAGE_PATTERN = re.compile(
    r"^\d[\d,.\-/\s]*"           # starts with a digit, allows digit groups
    r"\s*"                        # optional whitespace
    r"[a-zA-Zµ%]"                # unit must start with a letter or µ or %
    r"[a-zA-Zµ/\d%]*"           # rest of unit (allows g/dL, mg/kg, IU, etc.)
    r"$",
    re.IGNORECASE,
)

# Simpler pattern for numeric-only values that are valid dosages (e.g. "500")
_NUMERIC_PATTERN = re.compile(r"^\d[\d,.\-/\s]*$")


def validate_dosage_format(value: str) -> bool:
    """Check whether a value string looks like a valid dosage.

    Accepts patterns like:
        "500mg", "500 mg", "0.5 g", "250mg/5ml", "10mg/kg",
        "5-10 mg", "100,000 IU", "500" (pure numeric)

    Args:
        value: The dosage string to validate.

    Returns:
        True if the value matches a recognized dosage pattern.

    Examples:
        >>> validate_dosage_format("500mg")
        True
        >>> validate_dosage_format("500 mg")
        True
        >>> validate_dosage_format("hello")
        False
    """
    if not value or not value.strip():
        return False
    cleaned = value.strip()
    return bool(_DOSAGE_PATTERN.match(cleaned) or _NUMERIC_PATTERN.match(cleaned))


# ---------------------------------------------------------------------------
# Frequency validation
# ---------------------------------------------------------------------------

# Known canonical frequency patterns (case-insensitive match)
_FREQUENCY_PATTERNS: list[re.Pattern[str]] = [
    # Named frequencies: "once daily", "twice daily", "three times daily", etc.
    re.compile(
        r"^(once|twice|thrice|"
        r"(one|two|three|four|five|six)\s+times?)\s+"
        r"(daily|a\s+day|per\s+day|weekly|a\s+week|per\s+week|monthly)$",
        re.IGNORECASE,
    ),
    # Abbreviation frequencies: OD, BD/BID, TDS/TID, QID, QD, HS, PRN, SOS, STAT
    re.compile(
        r"^(od|bd|bid|tds|tid|qid|qd|hs|prn|sos|stat|"
        r"q\d+h|q\s*\d+\s*h(rs?|ours?)?)$",
        re.IGNORECASE,
    ),
    # Numeric frequency: "1x/day", "2x/day", "3x daily", "1-0-1", "1-1-1", "0-0-1"
    re.compile(
        r"^\d+x\s*/?\s*(day|daily|week|weekly)$",
        re.IGNORECASE,
    ),
    # Indian prescription shorthand: "1-0-1", "1-1-1", "0-0-1", "1-0-0-1"
    re.compile(
        r"^\d+(-\d+){1,3}$",
    ),
    # Relative timing: "before meals", "after meals", "with food", "at bedtime",
    # "in the morning", "at night", "empty stomach"
    re.compile(
        r"^(before|after|with)\s+(meals?|food|breakfast|lunch|dinner)|"
        r"at\s+(bedtime|night)|"
        r"in\s+the\s+(morning|evening)|"
        r"(on\s+)?empty\s+stomach$",
        re.IGNORECASE,
    ),
    # "every X hours/days": "every 6 hours", "every 8 hrs", "every 12h"
    re.compile(
        r"^every\s+\d+\s*(h|hrs?|hours?|days?|weeks?)$",
        re.IGNORECASE,
    ),
]


def validate_frequency_pattern(value: str) -> bool:
    """Check whether a value string matches a known medication frequency pattern.

    Accepts both formal (\"twice daily\") and abbreviated (\"BID\", \"1-0-1\")
    frequency notations commonly found in Indian prescriptions.

    Args:
        value: The frequency string to validate.

    Returns:
        True if the value matches any recognized frequency pattern.

    Examples:
        >>> validate_frequency_pattern("twice daily")
        True
        >>> validate_frequency_pattern("BID")
        True
        >>> validate_frequency_pattern("1-0-1")
        True
        >>> validate_frequency_pattern("hello world")
        False
    """
    if not value or not value.strip():
        return False
    cleaned = value.strip()
    return any(pattern.match(cleaned) for pattern in _FREQUENCY_PATTERNS)


# ---------------------------------------------------------------------------
# Document-type-aware field validation
# ---------------------------------------------------------------------------

# Critical fields that MUST be present for a given document type.
# Used by the conflict resolver to trigger HITL when critical fields are absent.
_CRITICAL_FIELDS: dict[DocumentType, set[str]] = {
    DocumentType.lab_report: {
        "test name",
        "value",
    },
    DocumentType.prescription: {
        "drug name",
        "dosage",
    },
    DocumentType.discharge_summary: {
        "diagnosis",
        "treatment",
    },
    DocumentType.radiology: {
        "findings",
        "impression",
    },
    DocumentType.unknown: set(),  # No critical fields for unknown type
}

# Fields that expect a dosage-format value
_DOSAGE_FIELDS: set[str] = {
    "dosage",
    "dose",
    "strength",
    "amount",
}

# Fields that expect a frequency-format value
_FREQUENCY_FIELDS: set[str] = {
    "frequency",
    "schedule",
    "timing",
    "interval",
}


def validate_field(
    field_name: str,
    value: str,
    document_type: DocumentType,
) -> bool:
    """Validate a field's value based on its name and the document type.

    Performs context-aware validation:
    - Dosage fields are checked against dosage format patterns.
    - Frequency fields are checked against frequency patterns.
    - All fields must have a non-empty value.
    - Critical fields for the document type are flagged if empty.

    Args:
        field_name: Canonical (normalized) name of the field.
        value: The extracted value to validate.
        document_type: The type of document being processed.

    Returns:
        True if the field value passes all applicable validation rules.
        False if the value is empty, or fails format validation for its
        field type.

    Examples:
        >>> validate_field("dosage", "500mg", DocumentType.prescription)
        True
        >>> validate_field("dosage", "hello", DocumentType.prescription)
        False
        >>> validate_field("frequency", "BID", DocumentType.prescription)
        True
        >>> validate_field("test name", "", DocumentType.lab_report)
        False
    """
    # Rule 1: Value must be non-empty
    if not value or not value.strip():
        return False

    cleaned_name = field_name.strip().lower()
    cleaned_value = value.strip()

    # Rule 2: Dosage fields must pass dosage format validation
    if cleaned_name in _DOSAGE_FIELDS:
        return validate_dosage_format(cleaned_value)

    # Rule 3: Frequency fields must pass frequency pattern validation
    if cleaned_name in _FREQUENCY_FIELDS:
        return validate_frequency_pattern(cleaned_value)

    # Rule 4: For all other fields, a non-empty value is valid
    return True


def is_critical_field(field_name: str, document_type: DocumentType) -> bool:
    """Check if a field is critical for the given document type.

    Critical fields trigger HITL review when absent or invalid.

    Args:
        field_name: Canonical (normalized) name of the field.
        document_type: The type of document being processed.

    Returns:
        True if the field is in the critical set for this document type.

    Examples:
        >>> is_critical_field("drug name", DocumentType.prescription)
        True
        >>> is_critical_field("notes", DocumentType.prescription)
        False
    """
    cleaned_name = field_name.strip().lower()
    critical = _CRITICAL_FIELDS.get(document_type, set())
    return cleaned_name in critical
