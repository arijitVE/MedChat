# pipeline_a/ocr/parser.py — Extracts text, tokens, bounding boxes from OCR response
#
# Parses Google Cloud Vision AnnotateImageResponse objects into the
# OCRWord Pydantic model. Isolated from the API client so tests can
# feed synthetic response objects.

from __future__ import annotations

from typing import Any

from shared.schemas.report import OCRWord


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _extract_bounding_box(symbol_or_word: Any) -> list[dict[str, float]]:
    """Extract bounding box vertices from a Vision API word/symbol object.

    Args:
        symbol_or_word: A Vision API Word or Symbol object with a
                        bounding_box.vertices attribute.

    Returns:
        List of {x, y} dicts for each vertex. Returns empty list if
        bounding_box is not available.
    """
    try:
        vertices = symbol_or_word.bounding_box.vertices
        return [
            {
                "x": float(v.x) if v.x else 0.0,
                "y": float(v.y) if v.y else 0.0,
            }
            for v in vertices
        ]
    except (AttributeError, TypeError):
        return []


def _extract_word_text(word: Any) -> str:
    """Reconstruct word text from its constituent symbols.

    Vision API stores text at the symbol level. This concatenates all
    symbols in a word, appending any detected_break characters.

    Args:
        word: A Vision API Word object.

    Returns:
        Reconstructed word text string.
    """
    text = ""
    for symbol in word.symbols:
        text += symbol.text
    return text


def _extract_word_confidence(word: Any) -> float:
    """Extract word-level confidence from a Vision API Word object.

    Falls back to averaging symbol confidences if word-level confidence
    is not available.

    Args:
        word: A Vision API Word object.

    Returns:
        Confidence float between 0.0 and 1.0.
    """
    # Word-level confidence (preferred)
    try:
        if word.confidence is not None and word.confidence > 0:
            return float(word.confidence)
    except AttributeError:
        pass

    # Fallback: average symbol confidences
    try:
        confidences = [
            float(s.confidence)
            for s in word.symbols
            if s.confidence is not None and s.confidence > 0
        ]
        if confidences:
            return sum(confidences) / len(confidences)
    except (AttributeError, TypeError):
        pass

    return 0.0


def parse_vision_response(response: Any) -> tuple[str, list[OCRWord]]:
    """Parse a single Vision API response into full text and word list.

    Iterates through the response's page → block → paragraph → word
    hierarchy to extract every word with its text, confidence, and
    bounding box.

    Args:
        response: A single AnnotateImageResponse from Vision API.

    Returns:
        Tuple of (full_text, list_of_OCRWord).
        full_text is the concatenated text from full_text_annotation.
        list_of_OCRWord contains per-word extractions.
    """
    words: list[OCRWord] = []

    # --- Full text from top-level annotation ---
    full_text = ""
    try:
        if response.full_text_annotation and response.full_text_annotation.text:
            full_text = response.full_text_annotation.text
    except AttributeError:
        pass

    # --- Per-word extraction from page hierarchy ---
    try:
        pages = response.full_text_annotation.pages
    except AttributeError:
        return full_text, words

    for page in pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    word_text = _extract_word_text(word)
                    if not word_text.strip():
                        continue

                    word_confidence = _extract_word_confidence(word)
                    bounding_box = _extract_bounding_box(word)

                    words.append(
                        OCRWord(
                            text=word_text,
                            confidence=min(max(word_confidence, 0.0), 1.0),
                            bounding_box=bounding_box,
                        )
                    )

    return full_text, words


def parse_all_responses(
    responses: list[Any],
) -> tuple[str, list[OCRWord]]:
    """Parse multiple Vision API responses (one per page) into combined output.

    Args:
        responses: List of AnnotateImageResponse objects.

    Returns:
        Tuple of (combined_full_text, combined_word_list).
    """
    all_text_parts: list[str] = []
    all_words: list[OCRWord] = []

    for response in responses:
        page_text, page_words = parse_vision_response(response)
        if page_text:
            all_text_parts.append(page_text)
        all_words.extend(page_words)

    combined_text = "\n".join(all_text_parts)
    return combined_text, all_words
