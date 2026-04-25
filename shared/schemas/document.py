# shared/schemas/document.py — Input/output schema for the ingestion layer.
# IngestedDocument is the first typed contract in the pipeline — every stage
# downstream receives typed Pydantic models, never raw dicts.

from __future__ import annotations

from pydantic import BaseModel, Field

from shared.schemas.report import DocumentType


class IngestedDocument(BaseModel):
    """Output of the ingestion stage (Stage 1).

    Created after MIME validation and document-type detection.
    Carries the raw file bytes forward to the OCR stage.
    """
    job_id: str = Field(
        ...,
        description="Unique job identifier (UUID4 string), generated at ingestion",
    )
    patient_id: str = Field(
        ...,
        description="Patient identifier provided by the caller",
    )
    file_bytes: bytes = Field(
        ...,
        description="Raw file content (PDF or image bytes)",
    )
    mime_type: str = Field(
        ...,
        description="Detected MIME type (e.g. 'application/pdf', 'image/jpeg')",
    )
    document_type: DocumentType = Field(
        ...,
        description="Detected document category based on filename keywords",
    )
    file_name: str = Field(
        default="",
        description="Original filename (used for document type detection and logging)",
    )

    model_config = {"from_attributes": True}
