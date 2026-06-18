# shared/schemas/document.py — Input/output schema for the ingestion layer.
from __future__ import annotations

from pydantic import BaseModel, Field

from shared.schemas.report import DocumentType


class IngestedDocument(BaseModel):
    """Output of the ingestion stage (Stage 1)."""
    case_id: str = Field(
        ...,
        description="Case identifier",
    )
    document_id: str = Field(
        ...,
        description="Document identifier",
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
