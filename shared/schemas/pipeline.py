# shared/schemas/pipeline.py — Unified schema for passing data between pipeline stages.
# Cross-stage wrapper types that bundle intermediate results for the orchestrator.

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from shared.schemas.document import IngestedDocument
from shared.schemas.report import (
    DocumentType,
    JobStatus,
    LLMExtractionResult,
    NormalizationResult,
    PipelineAOutput,
    ScoredField,
)


class PipelineContext(BaseModel):
    """Accumulates results across pipeline stages.

    The orchestrator (process_document.py) builds this up progressively:
      ingestion → ocr → llm → normalize → match → score → conflict

    Each stage writes its output into the appropriate field. Downstream stages
    read from previous fields. This avoids passing many positional arguments
    through the call chain.
    """
    # --- Stage 1: Ingestion ---
    ingested_document: Optional[IngestedDocument] = Field(
        default=None,
        description="Output of ingestion stage",
    )

    # --- Stage 2: LLM Extraction ---
    llm_extraction_result: Optional[LLMExtractionResult] = Field(
        default=None,
        description="Output of LLM extraction stage",
    )

    # --- Stage 3: Normalization ---
    normalization_result: Optional[NormalizationResult] = Field(
        default=None,
        description="Output of normalization stage",
    )

    # --- Stage 4: Persistence-ready fields ---
    scored_fields: Optional[list[ScoredField]] = Field(
        default=None,
        description="Output fields ready for persistence",
    )

    # --- Stage 5: Final Output ---
    pipeline_output: Optional[PipelineAOutput] = Field(
        default=None,
        description="Final assembled output of Pipeline A",
    )

    # --- Metadata ---
    job_id: str = Field(..., description="Unique job identifier")
    patient_id: str = Field(..., description="Patient identifier")
    document_type: DocumentType = Field(
        default=DocumentType.unknown,
        description="Detected document type",
    )
    job_status: JobStatus = Field(
        default=JobStatus.pending,
        description="Current job status",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if the pipeline failed at any stage",
    )

    # --- Observability ---
    llm_latency_ms: Optional[float] = Field(default=None, description="LLM stage latency in ms")
    total_pipeline_latency_ms: Optional[float] = Field(
        default=None,
        description="End-to-end pipeline latency in ms",
    )

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    """Response returned by POST /api/v1/documents/upload."""
    job_id: str = Field(..., description="Assigned job ID")
    status: JobStatus = Field(..., description="Initial job status (PENDING)")

    model_config = {"from_attributes": True}


class JobStatusResponse(BaseModel):
    """Response returned by GET /api/v1/documents/{job_id}/status."""
    job_id: str = Field(..., description="Job ID")
    status: JobStatus = Field(..., description="Current job status")
    result: Optional[PipelineAOutput] = Field(
        default=None,
        description="Full pipeline output (present if completed)",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if status is FAILED",
    )

    model_config = {"from_attributes": True}
