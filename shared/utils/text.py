# shared/utils/text.py — Text cleaning, normalization helpers
# Used by normalization, matching, and ingestion stages.

from __future__ import annotations

import re


def remove_thousands_separators(value: str) -> str:
    """Remove comma-based thousands separators from a numeric string.

    Handles both international (1,000,000) and Indian (1,50,000) formats.
    Preserves decimal points.

    Args:
        value: A string that may contain comma-separated numbers.

    Returns:
        String with commas removed from numeric portions.

    Examples:
        >>> remove_thousands_separators("1,50,000")
        '150000'
        >>> remove_thousands_separators("1,000,000")
        '1000000'
        >>> remove_thousands_separators("12.5")
        '12.5'
        >>> remove_thousands_separators("hemoglobin")
        'hemoglobin'
    """
    if not value:
        return ""
    # Strip whitespace first
    value = value.strip()
    # Remove commas that appear within digit sequences
    # Handles both "1,50,000" (Indian) and "1,000,000" (international)
    return re.sub(r"(?<=\d),(?=\d)", "", value)
