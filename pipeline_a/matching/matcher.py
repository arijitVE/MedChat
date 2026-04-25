# pipeline_a/matching/matcher.py — Phrase-level fuzzy + semantic OCR↔LLM alignment
#
# Stage 5 of Pipeline A. For each normalized LLM field, finds its best anchor
# in the OCR text using:
#   1. Sliding n-gram phrase windows (2–5 words) — NOT single tokens
#   2. RapidFuzz token_set_ratio (catches typos, OCR scan errors)
#   3. Sentence-transformer cosine similarity (synonym-aware matching)
#
# combined_score = 0.6 * (fuzzy_score / 100) + 0.4 * semantic_score
#
# The embedding model is isolated behind _get_embedding_model() so it can be
# swapped from all-MiniLM-L6-v2 (MVP) to medicalai/ClinicalBERT (Phase 2)
# without changing anything else.

from __future__ import annotations

import time
from typing import Any

import numpy as np
from rapidfuzz import fuzz, process
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine_similarity

from shared.logger import get_logger, log_stage
from shared.schemas.report import (
    FieldMatchScore,
    MatchingResult,
    NormalizedField,
    NormalizationResult,
    OCRResult,
)
from shared.utils.text import build_phrase_windows

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Embedding model (lazy singleton)
# ---------------------------------------------------------------------------

_embedding_model: SentenceTransformer | None = None


def _get_embedding_model() -> SentenceTransformer:
    """Return a cached sentence-transformer model instance.

    MVP uses all-MiniLM-L6-v2 (80MB, fast inference).
    Phase 2: swap to medicalai/ClinicalBERT for domain-tuned embeddings.
    This function is the ONLY place the model name appears — nothing else
    changes on swap.

    Returns:
        Loaded SentenceTransformer model.
    """
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


# ---------------------------------------------------------------------------
# Embedding + similarity helpers
# ---------------------------------------------------------------------------


def _embed(texts: list[str]) -> np.ndarray:
    """Embed a batch of text strings using the sentence-transformer model.

    Args:
        texts: List of text strings to encode.

    Returns:
        2D numpy array of shape (len(texts), embedding_dim).
    """
    model = _get_embedding_model()
    return model.encode(texts, convert_to_numpy=True, show_progress_bar=False)


def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Compute cosine similarity between two embedding vectors.

    Args:
        vec_a: 1D embedding vector.
        vec_b: 1D embedding vector.

    Returns:
        Cosine similarity score in range [0.0, 1.0]. Clamped to prevent
        floating-point rounding below 0.
    """
    sim = sklearn_cosine_similarity(
        vec_a.reshape(1, -1),
        vec_b.reshape(1, -1),
    )[0][0]
    return float(max(0.0, min(1.0, sim)))


# ---------------------------------------------------------------------------
# Phrase window construction
# ---------------------------------------------------------------------------


def _build_ocr_phrases(raw_text: str) -> list[str]:
    """Build deduplicated phrase windows from OCR raw text.

    Uses build_phrase_windows() from shared.utils.text which generates
    sliding 2–5 word n-grams plus unigrams as fallback, then deduplicates
    while preserving order.

    Args:
        raw_text: Full OCR raw text string.

    Returns:
        Deduplicated list of phrase windows.
    """
    if not raw_text or not raw_text.strip():
        return []
    return build_phrase_windows(raw_text, min_n=2, max_n=5)


# ---------------------------------------------------------------------------
# Field context string construction
# ---------------------------------------------------------------------------


def _build_field_context(field: NormalizedField) -> str:
    """Build the context string for a normalized field.

    Uses the full field context (name + value + unit) for comparison,
    NOT just the bare value. This is critical for semantic matching:
    "hemoglobin 13.5 g/dL" vs "Hb 13.5 g/dL" is synonym-aware,
    while "13.5" vs "13.5" provides no signal.

    Args:
        field: A normalized field from the normalization stage.

    Returns:
        Context string like "hemoglobin 13.5 g/dL".
    """
    parts = [field.normalized_name, field.normalized_value]
    if field.unit:
        parts.append(field.unit)
    return " ".join(parts).strip()


# ---------------------------------------------------------------------------
# Core matching
# ---------------------------------------------------------------------------


def run_matching(
    normalization_result: NormalizationResult,
    ocr_result: OCRResult,
    job_id: str = "",
) -> MatchingResult:
    """Match each normalized LLM field against OCR text using phrase-level
    fuzzy + semantic similarity.

    For each normalized field:
    1. Build field_context = "{normalized_name} {normalized_value} {unit}"
    2. Fuzzy match: rapidfuzz.process.extractOne(field_context, ocr_phrases,
       scorer=token_set_ratio) → (best_phrase, fuzzy_score)
    3. Semantic match: cosine_similarity(embed(field_context), embed(best_phrase))
    4. combined_score = 0.6 * (fuzzy_score / 100) + 0.4 * semantic_score

    Args:
        normalization_result: Output from the normalization stage.
        ocr_result: OCR output containing raw_text and per-word data.
        job_id: Job identifier for structured logging.

    Returns:
        MatchingResult with per-field FieldMatchScore entries.
    """
    t_start = time.perf_counter()

    # --- Step 1: Build OCR phrase windows ---
    ocr_phrases = _build_ocr_phrases(ocr_result.raw_text)
    phrase_window_count = len(ocr_phrases)

    field_scores: list[FieldMatchScore] = []
    fuzzy_scores: list[float] = []
    semantic_scores: list[float] = []

    if not ocr_phrases or not normalization_result.fields:
        # Nothing to match — return empty result
        duration_ms = (time.perf_counter() - t_start) * 1000
        log_stage(
            logger,
            stage="matching",
            job_id=job_id,
            duration_ms=duration_ms,
            status="success",
            phrase_window_count=phrase_window_count,
            avg_fuzzy_score=0.0,
            avg_semantic_score=0.0,
        )
        return MatchingResult(field_scores=[])

    # --- Step 2: Process each normalized field ---
    for field in normalization_result.fields:
        field_context = _build_field_context(field)

        # --- Fuzzy match ---
        fuzzy_result = process.extractOne(
            field_context,
            ocr_phrases,
            scorer=fuzz.token_set_ratio,
        )

        if fuzzy_result is not None:
            best_phrase = fuzzy_result[0]
            fuzzy_score = float(fuzzy_result[1])
        else:
            # No match at all — should only happen with empty phrases
            best_phrase = ""
            fuzzy_score = 0.0

        # --- Semantic match ---
        try:
            embeddings = _embed([field_context, best_phrase])
            semantic_score = _cosine_similarity(embeddings[0], embeddings[1])
        except Exception as exc:
            logger.warning(
                "matching_semantic_failed",
                job_id=job_id,
                field_name=field.normalized_name,
                error=str(exc),
            )
            semantic_score = 0.0

        # --- Combined score ---
        combined_score = 0.6 * (fuzzy_score / 100.0) + 0.4 * semantic_score
        # Clamp to [0.0, 1.0]
        combined_score = max(0.0, min(1.0, combined_score))

        field_scores.append(
            FieldMatchScore(
                field_name=field.normalized_name,
                llm_value=field.normalized_value,
                ocr_best_phrase=best_phrase,
                fuzzy_score=round(fuzzy_score, 2),
                semantic_score=round(semantic_score, 4),
                combined_score=round(combined_score, 4),
            )
        )

        fuzzy_scores.append(fuzzy_score)
        semantic_scores.append(semantic_score)

    # --- Log stage exit ---
    duration_ms = (time.perf_counter() - t_start) * 1000
    avg_fuzzy = sum(fuzzy_scores) / len(fuzzy_scores) if fuzzy_scores else 0.0
    avg_semantic = sum(semantic_scores) / len(semantic_scores) if semantic_scores else 0.0

    log_stage(
        logger,
        stage="matching",
        job_id=job_id,
        duration_ms=duration_ms,
        status="success",
        phrase_window_count=phrase_window_count,
        avg_fuzzy_score=round(avg_fuzzy, 2),
        avg_semantic_score=round(avg_semantic, 4),
    )

    return MatchingResult(field_scores=field_scores)
