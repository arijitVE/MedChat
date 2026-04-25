# pipeline_a/ocr/confidence.py — Aggregates token-level confidence → usable metrics
#
# Two responsibilities:
# 1. aggregate_confidence: compute avg + low_confidence flag from OCR words
# 2. map_field_to_ocr_words: fuzzy-match a field value back to OCR words
#    using rapidfuzz.fuzz.partial_ratio (NOT exact string match)

from __future__ import annotations

from typing import Optional

from rapidfuzz import fuzz

from shared.schemas.report import OCRWord


# ---------------------------------------------------------------------------
# Aggregate confidence
# ---------------------------------------------------------------------------


def aggregate_confidence(
    words: list[OCRWord],
    threshold: float,
) -> tuple[float, bool]:
    """Compute average word confidence and low-confidence flag.

    Args:
        words: List of OCRWord objects from the parser.
        threshold: OCR_CONFIDENCE_THRESHOLD from settings. Words whose
                   average falls below this trigger the HITL flag.

    Returns:
        Tuple of (avg_confidence, low_confidence).
        avg_confidence: Mean of all word confidences (0.0 if no words).
        low_confidence: True if avg_confidence < threshold.

    Examples:
        >>> from shared.schemas.report import OCRWord
        >>> words = [
        ...     OCRWord(text="Hb", confidence=0.95, bounding_box=[]),
        ...     OCRWord(text="13.5", confidence=0.90, bounding_box=[]),
        ... ]
        >>> avg, low = aggregate_confidence(words, threshold=0.85)
        >>> avg
        0.925
        >>> low
        False
    """
    if not words:
        return 0.0, True  # no words = definitely low confidence

    total = sum(w.confidence for w in words)
    avg_confidence = total / len(words)
    low_confidence = avg_confidence < threshold

    return round(avg_confidence, 4), low_confidence


# ---------------------------------------------------------------------------
# Fuzzy field-to-OCR-word mapping
# ---------------------------------------------------------------------------

# Minimum partial_ratio score to consider an OCR word as matching a field value.
# Blueprint specifies >= 80 — do NOT use exact string comparison.
_FUZZY_MATCH_THRESHOLD: int = 80


def map_field_to_ocr_words(
    field_value: str,
    words: list[OCRWord],
    threshold: int = _FUZZY_MATCH_THRESHOLD,
) -> list[OCRWord]:
    """Find OCR words that fuzzy-match a field value.

    Uses rapidfuzz.fuzz.partial_ratio for matching instead of exact string
    comparison. This is critical because formatting differences between
    LLM output and OCR output would silently break exact matching:
        - "13.5" vs "13.50"
        - "Hb" vs "HB"
        - "500mg" vs "500 mg"
        - "Amoxicillin" vs "Amoxcillin" (OCR typo)

    The matched words' confidence values are averaged by the downstream
    confidence scorer (pipeline_a/confidence/scorer.py) to produce the
    ocr_word_conf component of the final score.

    Args:
        field_value: The normalised field value to search for in OCR words.
        words: List of OCRWord objects from the OCR result.
        threshold: Minimum partial_ratio score (0–100) for a match.
                   Default: 80 (from blueprint).

    Returns:
        List of OCRWord objects whose text fuzzy-matches the field value.
        Empty list if no matches found (causes scorer to use 0.5 default).

    Examples:
        >>> from shared.schemas.report import OCRWord
        >>> words = [
        ...     OCRWord(text="13.5", confidence=0.95, bounding_box=[]),
        ...     OCRWord(text="g/dL", confidence=0.88, bounding_box=[]),
        ...     OCRWord(text="Normal", confidence=0.92, bounding_box=[]),
        ... ]
        >>> matched = map_field_to_ocr_words("13.5", words)
        >>> len(matched)
        1
        >>> matched[0].text
        '13.5'
    """
    if not field_value or not words:
        return []

    matched: list[OCRWord] = []
    for word in words:
        score = fuzz.partial_ratio(field_value, word.text)
        if score >= threshold:
            matched.append(word)

    return matched


def compute_ocr_word_confidence(
    field_value: str,
    words: list[OCRWord],
    threshold: int = _FUZZY_MATCH_THRESHOLD,
) -> float:
    """Compute the mean confidence of OCR words matching a field value.

    Convenience wrapper combining map_field_to_ocr_words + mean calculation.
    Returns 0.5 (penalised but not auto-rejected) if no words match.

    Args:
        field_value: The normalised field value.
        words: List of OCRWord objects from the OCR result.
        threshold: Minimum fuzzy match score.

    Returns:
        Mean confidence of matched words, or 0.5 if no matches.
    """
    matched = map_field_to_ocr_words(field_value, words, threshold)
    if not matched:
        return 0.5  # penalised but not auto-rejected (per blueprint)
    return sum(w.confidence for w in matched) / len(matched)
