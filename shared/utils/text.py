# shared/utils/text.py — Text cleaning, normalization helpers
# Used by normalization, matching, and ingestion stages.

from __future__ import annotations

import re


def clean_text(text: str) -> str:
    """Strip, lowercase, and collapse multiple whitespace into single spaces.

    Args:
        text: Raw input text (e.g. from OCR output or LLM response).

    Returns:
        Cleaned text suitable for downstream comparison/matching.

    Examples:
        >>> clean_text("  Hemoglobin   13.5  g/dL  ")
        'hemoglobin 13.5 g/dl'
    """
    if not text:
        return ""
    # Strip leading/trailing whitespace, lowercase everything
    cleaned = text.strip().lower()
    # Collapse multiple whitespace (spaces, tabs, newlines) into single space
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


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


def tokenize_medical_text(text: str) -> list[str]:
    """Split medical text into tokens on whitespace and common delimiters.

    Filters out tokens shorter than 2 characters and deduplicates
    while preserving order.

    Args:
        text: Raw or cleaned medical text.

    Returns:
        Deduplicated list of tokens with length >= 2, in order of first
        appearance.

    Examples:
        >>> tokenize_medical_text("Hb: 13.5 g/dL - Normal")
        ['hb', '13.5', 'dl', 'normal']
    """
    if not text:
        return []
    # Lowercase for consistent comparison
    text = text.strip().lower()
    # Split on whitespace and common medical delimiters: : , ; - / ( ) [ ] | =
    tokens = re.split(r"[\s:,;\-/\(\)\[\]\|=]+", text)
    # Filter minimum length 2, deduplicate preserving order
    seen: set[str] = set()
    result: list[str] = []
    for token in tokens:
        token = token.strip()
        if len(token) >= 2 and token not in seen:
            seen.add(token)
            result.append(token)
    return result


def build_phrase_windows(
    text: str,
    min_n: int = 2,
    max_n: int = 5,
) -> list[str]:
    """Build sliding n-gram word windows over the input text.

    Medical values appear as multi-word spans ("Hb: 13.5 g/dL", "Amox 500mg",
    "BP 120/80"). Single-token matching loses this context. This function
    generates overlapping phrase windows of varying lengths for use by the
    phrase-level fuzzy + semantic matcher.

    Unigrams are appended as fallback after the n-gram windows.
    The final list is deduplicated while preserving order.

    Args:
        text: Input text to generate phrase windows from.
        min_n: Minimum n-gram size (default: 2).
        max_n: Maximum n-gram size (default: 5).

    Returns:
        Deduplicated list of phrase windows (n-grams first, then unigrams).

    Examples:
        >>> build_phrase_windows("Hb 13.5 g/dL normal", min_n=2, max_n=3)
        ['Hb 13.5', '13.5 g/dL', 'g/dL normal', 'Hb 13.5 g/dL', \
'13.5 g/dL normal', 'Hb', '13.5', 'g/dL', 'normal']
    """
    if not text:
        return []
    # Split on whitespace — preserve original casing for matching fidelity
    words = text.split()
    if not words:
        return []

    phrases: list[str] = []

    # N-gram windows (min_n to max_n)
    for n in range(min_n, max_n + 1):
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i : i + n])
            phrases.append(phrase)

    # Append unigrams as fallback
    phrases.extend(words)

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduplicated: list[str] = []
    for phrase in phrases:
        if phrase not in seen:
            seen.add(phrase)
            deduplicated.append(phrase)

    return deduplicated
