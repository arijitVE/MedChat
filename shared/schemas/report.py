# shared/schemas/report.py — Core structured medical schema
# Enums and Pydantic models used across all pipeline stages.
# No raw dict crosses a stage boundary — all inter-stage data uses these models.

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DocumentType(str, Enum):
    """Classification of medical document types."""
    lab_report = "lab_report"
    prescription = "prescription"
    discharge_summary = "discharge_summary"
    radiology = "radiology"
    unknown = "unknown"


class JobStatus(str, Enum):
    """Processing status of a document job."""
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


# ---------------------------------------------------------------------------
# LLM Extraction Stage Models (Stage 1 output)
# ---------------------------------------------------------------------------


class ExtractedField(BaseModel):
    """A single field extracted by the LLM from document images."""
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
    """Output of the LLM extraction stage (GPT-4o Vision)."""
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
        description="Number of LLM attempts made (1 or 2 with strict retry)",
    )
    fallback_used: bool = Field(
        ...,
        description="True if the strict-prefix retry was used",
    )

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Normalization Stage Models (Stage 2 output)
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
    """Output of the normalization stage."""
    fields: list[NormalizedField] = Field(
        default_factory=list,
        description="All fields after normalization",
    )

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Final Output Models (Stage 3 output)
# ---------------------------------------------------------------------------


class ScoredField(BaseModel):
    """A normalized field ready for DB persistence and embedding."""
    name: str = Field(..., description="Canonical (normalized) field name")
    value: str = Field(..., description="Normalized field value")
    unit: Optional[str] = Field(default=None, description="Canonical unit")
    reference_range: Optional[str] = Field(default=None, description="Reference range if available")
    collection_date: Optional[str] = Field(default=None, description="Collection date if available")

    model_config = {"from_attributes": True}


class PipelineAOutput(BaseModel):
    """Final output of Pipeline A for a single document.

    Written to PostgreSQL via upsert. Pipeline B reads
    structured_text_for_embedding — it never imports Pipeline A code directly.
    """
    case_id: str = Field(..., description="Case identifier")
    document_id: str = Field(..., description="Document identifier")
    document_type: DocumentType = Field(..., description="Detected document type")
    scored_fields: list[ScoredField] = Field(
        default_factory=list,
        description="All extracted and normalized fields",
    )
    job_status: JobStatus = Field(
        ...,
        description="Final job status: completed or failed",
    )
    structured_text_for_embedding: str = Field(
        ...,
        description="Flattened text for Pipeline B embedding.",
    )
    llm_latency_ms: Optional[float] = Field(default=None, description="LLM extraction stage latency in ms")
    total_pipeline_latency_ms: Optional[float] = Field(
        default=None,
        description="Total end-to-end pipeline latency in ms",
    )

    model_config = {"from_attributes": True}
