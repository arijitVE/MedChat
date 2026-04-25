# pipeline_a/confidence/scorer.py

from shared.schemas.report import (
    MatchingResult,
    NormalizationResult,
    OCRResult,
    ScoredField,
    FieldStatus
)
from shared.config import get_settings
from shared.logger import get_logger
from pipeline_a.ocr.confidence import compute_ocr_word_confidence

logger = get_logger(__name__)

def score_fields(
    match: MatchingResult,
    norm: NormalizationResult,
    ocr: OCRResult
) -> list[ScoredField]:
    settings = get_settings()
    scored_fields: list[ScoredField] = []
    
    # We need to map field_name back to the NormalizedField to get original unit, reference_range, etc.
    norm_dict = {f.normalized_name: f for f in norm.fields}
    
    hitl_count = 0
    auto_count = 0
    total_score = 0.0
    
    for fs in match.field_scores:
        normalized_field = norm_dict.get(fs.field_name)
        if not normalized_field:
            continue
            
        # 1. Map field value back to OCR words to get OCR confidence
        ocr_word_conf = compute_ocr_word_confidence(fs.llm_value, ocr.words, threshold=settings.FUZZY_MATCH_THRESHOLD)
        
        # 2. Final Score
        final_score = 0.7 * fs.combined_score + 0.3 * ocr_word_conf
        final_score = round(final_score, 4)
        
        # 3. Status
        if final_score >= settings.FIELD_CONFIDENCE_THRESHOLD:
            status = FieldStatus.auto
            auto_count += 1
            hitl_reason = None
        else:
            status = FieldStatus.hitl
            hitl_count += 1
            hitl_reason = (
                f"Low confidence ({final_score}). "
                f"Combined match: {fs.combined_score:.2f}, OCR: {ocr_word_conf:.2f}"
            )
            
        logger.info(
            "field_scored",
            field_name=fs.field_name,
            final_score=final_score,
            status=status.value
        )
            
        scored = ScoredField(
            name=fs.field_name,
            value=fs.llm_value,
            unit=normalized_field.unit,
            reference_range=normalized_field.reference_range,
            collection_date=normalized_field.collection_date,
            confidence=final_score,
            status=status,
            hitl_reason=hitl_reason
        )
        scored_fields.append(scored)
        total_score += final_score

    avg_final_score = round(total_score / len(scored_fields), 4) if scored_fields else 0.0

    logger.info(
        "confidence_scoring_aggregate",
        stage="confidence_scoring",
        hitl_field_count=hitl_count,
        auto_field_count=auto_count,
        avg_final_score=avg_final_score
    )

    return scored_fields
