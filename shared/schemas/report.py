# shared/schemas/report.py — Core structured medical schema (medications, dosage, etc.)
# Enums and Pydantic models used across all pipeline stages.
# No raw dict crosses a stage boundary — all inter-stage data uses these models.

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums (exact values from blueprint Step 2)
# ---------------------------------------------------------------------------


class DocumentType(str, Enum):
    """Classification of medical document types."""
    lab_report = "lab_report"
    prescription = "prescription"
    discharge_summary = "discharge_summary"
    radiology = "radiology"
    unknown = "unknown"


class FieldStatus(str, Enum):
    """Status of an extracted field after confidence scoring."""
    auto = "auto"
    hitl = "hitl"
    missing = "missing"


class JobStatus(str, Enum):
    """Processing status of a document job."""
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    hitl_required = "hitl_required"


# ---------------------------------------------------------------------------
# OCR Stage Models (Stage 2 output)
# ---------------------------------------------------------------------------


class OCRWord(BaseModel):
    """A single word extracted by the OCR engine with its confidence and position."""
    text: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="Word-level OCR confidence (0–1)")
    bounding_box: list[dict[str, float]] = Field(
        default_factory=list,
        description="List of vertex coordinates [{x, y}, ...] defining the word bounding box",
    )

    model_config = {"from_attributes": True}


class OCRResult(BaseModel):
    """Aggregated OCR output for an entire document (all pages combined).

    This serves as the raw-text verification anchor against which LLM output
    is matched.
    """
    raw_text: str = Field(..., description="Full concatenated OCR text across all pages")
    words: list[OCRWord] = Field(default_factory=list, description="Per-word OCR extractions")
    avg_confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Mean word-level confidence across all words",
    )
    low_confidence: bool = Field(
        ...,
        description="True if avg_confidence < OCR_CONFIDENCE_THRESHOLD → triggers HITL",
    )

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# LLM Extraction Stage Models (Stage 3 output)
# ---------------------------------------------------------------------------


class ExtractedField(BaseModel):
    """A single field extracted by the LLM from OCR text.

    Represents a raw extraction before normalization or matching.
    """
    name: str = Field(..., description="Field name as extracted by LLM (e.g. 'hemoglobin', 'drug_name')")
    value: str = Field(..., description="Extracted value (e.g. '13.5', 'Amoxicillin')")
    unit: Optional[str] = Field(default=None, description="Unit of measurement if applicable (e.g. 'g/dL')")
    reference_range: Optional[str] = Field(
        default=None,
        description="Normal reference range if present (e.g. '12.0-16.0')",
    )
    collection_date: Optional[str] = Field(
        default=None,
        description="Date the sample was collected or test was performed",
    )

    model_config = {"from_attributes": True}


class LLMExtractionResult(BaseModel):
    """Output of the LLM extraction stage (Gemini API).

    Includes retry metadata so downstream stages and observability can track
    extraction quality.
    """
    fields: list[ExtractedField] = Field(
        default_factory=list,
        description="Structured fields extracted by the LLM",
    )
    raw_llm_response: str = Field(
        default="",
        description="Raw string response from the LLM (for debugging / audit)",
    )
    attempt_count: int = Field(
        ..., ge=1,
        description="Number of LLM attempts made (1–3 before regex fallback)",
    )
    fallback_used: bool = Field(
        ...,
        description="True if regex fallback was activated after all LLM retries failed",
    )

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Normalization Stage Models (Stage 4 output)
# ---------------------------------------------------------------------------


class NormalizedField(BaseModel):
    """A field after normalization: synonym expansion, unit canonicalization,
    value cleaning. Preserves original values alongside normalized versions.
    """
    original_name: str = Field(..., description="Field name as extracted by LLM (pre-normalization)")
    normalized_name: str = Field(..., description="Canonical field name after synonym mapping")
    original_value: str = Field(..., description="Value as extracted by LLM (pre-normalization)")
    normalized_value: str = Field(..., description="Value after cleaning (commas removed, whitespace stripped)")
    unit: Optional[str] = Field(default=None, description="Canonical unit after UNIT_SYNONYMS mapping")
    reference_range: Optional[str] = Field(default=None, description="Preserved from extraction stage")
    collection_date: Optional[str] = Field(default=None, description="Preserved from extraction stage")

    model_config = {"from_attributes": True}


class NormalizationResult(BaseModel):
    """Output of the normalization stage. Contains all fields with both original
    and normalized representations.
    """
    fields: list[NormalizedField] = Field(
        default_factory=list,
        description="All fields after normalization",
    )

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Matching Stage Models (Stage 5 output)
# ---------------------------------------------------------------------------


class FieldMatchScore(BaseModel):
    """Per-field matching result: how well an LLM-extracted field aligns with
    the OCR text using phrase-window fuzzy + semantic similarity.
    """
    field_name: str = Field(..., description="Normalized field name")
    llm_value: str = Field(..., description="Normalized LLM-extracted value")
    ocr_best_phrase: str = Field(
        ...,
        description="Best-matching OCR phrase window (NOT single token)",
    )
    fuzzy_score: float = Field(
        ..., ge=0.0, le=100.0,
        description="RapidFuzz token_set_ratio score (0–100)",
    )
    semantic_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Cosine similarity from sentence-transformer embeddings (0–1)",
    )
    combined_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="Weighted combination: 0.6 * (fuzzy/100) + 0.4 * semantic",
    )

    model_config = {"from_attributes": True}


class MatchingResult(BaseModel):
    """Output of the matching stage. Contains per-field match scores used by
    the confidence scorer downstream.
    """
    field_scores: list[FieldMatchScore] = Field(
        default_factory=list,
        description="Match scores for each normalized field",
    )

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Confidence / Conflict Stage Models (Stage 6a + 6b output)
# ---------------------------------------------------------------------------


class ScoredField(BaseModel):
    """A fully scored field with confidence, status, and all data needed for
    the embedding text and DB persistence.

    Carries forward unit/reference_range from extraction so the conflict
    resolver can build structured_text_for_embedding without re-querying.
    """
    name: str = Field(..., description="Canonical (normalized) field name")
    value: str = Field(..., description="Normalized field value")
    unit: Optional[str] = Field(default=None, description="Canonical unit")
    reference_range: Optional[str] = Field(default=None, description="Reference range if available")
    collection_date: Optional[str] = Field(default=None, description="Collection date if available")
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Final weighted confidence: 0.7 * combined_match + 0.3 * ocr_word_conf",
    )
    status: FieldStatus = Field(
        ...,
        description="AUTO if confidence >= threshold, HITL otherwise",
    )
    hitl_reason: Optional[str] = Field(
        default=None,
        description="Descriptive reason if status=HITL (includes component scores)",
    )

    model_config = {"from_attributes": True}


class PipelineAOutput(BaseModel):
    """Final output of Pipeline A for a single document.

    Written to PostgreSQL via upsert. Pipeline B reads
    structured_text_for_embedding — it never imports Pipeline A code directly.
    """
    job_id: str = Field(..., description="Unique job identifier (UUID)")
    patient_id: str = Field(..., description="Patient identifier")
    document_type: DocumentType = Field(..., description="Detected document type")
    scored_fields: list[ScoredField] = Field(
        default_factory=list,
        description="All fields with confidence scores and status",
    )
    hitl_required: bool = Field(
        ...,
        description="True if any HITL trigger condition fired",
    )
    hitl_reasons: list[str] = Field(
        default_factory=list,
        description="List of reasons HITL was triggered",
    )
    job_status: JobStatus = Field(
        ...,
        description="Final job status: COMPLETED or HITL_REQUIRED",
    )
    structured_text_for_embedding: str = Field(
        ...,
        description=(
            "Flattened text for Pipeline B embedding. "
            "AUTO fields verbatim, HITL fields tagged [LOW_CONFIDENCE]."
        ),
    )
    ocr_latency_ms: Optional[float] = Field(default=None, description="OCR stage latency in ms")
    llm_latency_ms: Optional[float] = Field(default=None, description="LLM extraction stage latency in ms")
    total_pipeline_latency_ms: Optional[float] = Field(
        default=None,
        description="Total end-to-end pipeline latency in ms",
    )

    model_config = {"from_attributes": True}
