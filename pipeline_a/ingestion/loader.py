# pipeline_a/ingestion/loader.py — MIME detection, PDF/image parsing → IngestedDocument
#
# Stage 1 of Pipeline A. Accepts raw file bytes, validates MIME type,
# detects document category from filename keywords, returns IngestedDocument.

from __future__ import annotations

import mimetypes
import time
import uuid
from typing import Any

from shared.logger import get_logger, log_stage
from shared.schemas.document import IngestedDocument
from shared.schemas.report import DocumentType

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Supported MIME types — reject anything not in this set
# ---------------------------------------------------------------------------

SUPPORTED_MIME_TYPES: set[str] = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
}

# ---------------------------------------------------------------------------
# Magic byte signatures for MIME detection
# ---------------------------------------------------------------------------

# Ordered list of (prefix_bytes, mime_type). Checked sequentially so more
# specific prefixes should come first if there are overlaps.
_MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"%PDF", "application/pdf"),
    (b"\xff\xd8", "image/jpeg"),
    (b"\x89PNG", "image/png"),
    (b"II*\x00", "image/tiff"),   # little-endian TIFF
    (b"MM\x00*", "image/tiff"),   # big-endian TIFF
]

# ---------------------------------------------------------------------------
# Document type detection keywords
# ---------------------------------------------------------------------------

# Each tuple is (keyword_set, document_type). Checked in order — first match wins.
_DOCTYPE_KEYWORD_MAP: list[tuple[set[str], DocumentType]] = [
    # Order matters: check specific types before generic ones.
    # "report" is very broad — check radiology/discharge/prescription first.
    ({"radiology", "xray", "mri"}, DocumentType.radiology),
    ({"discharge", "summary"}, DocumentType.discharge_summary),
    ({"prescription", "rx"}, DocumentType.prescription),
    ({"lab", "cbc", "blood", "report"}, DocumentType.lab_report),
]


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def detect_mime_type(file_bytes: bytes, file_name: str = "") -> str:
    """Detect MIME type from magic bytes first, falling back to file extension.

    Args:
        file_bytes: Raw file content.
        file_name: Original filename (used only as fallback).

    Returns:
        Detected MIME type string.

    Raises:
        ValueError: If file_bytes is empty.
    """
    if not file_bytes:
        raise ValueError("Cannot detect MIME type: file_bytes is empty")

    # 1. Check magic bytes (authoritative — not spoofable via extension)
    for magic, mime_type in _MAGIC_SIGNATURES:
        if file_bytes[:len(magic)] == magic:
            return mime_type

    # 2. Fallback: extension-based guess
    if file_name:
        guessed, _ = mimetypes.guess_type(file_name)
        if guessed:
            return guessed

    return "application/octet-stream"


def detect_document_type(file_name: str) -> DocumentType:
    """Detect document category from filename keywords.

    Lowercases the filename and checks for keyword matches. First matching
    keyword set wins. Returns DocumentType.unknown if no keywords match.

    Args:
        file_name: Original filename.

    Returns:
        Detected DocumentType enum value.
    """
    if not file_name:
        return DocumentType.unknown

    name_lower = file_name.lower()

    for keywords, doc_type in _DOCTYPE_KEYWORD_MAP:
        if any(kw in name_lower for kw in keywords):
            return doc_type

    return DocumentType.unknown


def ingest(
    file_bytes: bytes,
    file_name: str,
    patient_id: str,
) -> IngestedDocument:
    """Ingest a raw document: validate MIME, detect type, return typed model.

    This is the entry point for Stage 1 of Pipeline A.

    Args:
        file_bytes: Raw file content (PDF or image bytes).
        file_name: Original filename.
        patient_id: Patient identifier provided by the caller.

    Returns:
        IngestedDocument with a fresh UUID4 job_id.

    Raises:
        ValueError: If file_bytes is empty or MIME type is not in the
                    supported set (application/pdf, image/jpeg, image/png,
                    image/tiff). Never proceeds silently on unsupported types.
    """
    t_start = time.perf_counter()
    job_id = str(uuid.uuid4())

    try:
        # --- Step 1: MIME detection (magic bytes first, then extension) ---
        mime_type = detect_mime_type(file_bytes, file_name)

        # --- Step 2: Reject unsupported MIME types ---
        if mime_type not in SUPPORTED_MIME_TYPES:
            raise ValueError(
                f"Unsupported MIME type: {mime_type!r} "
                f"(file: {file_name!r}). "
                f"Supported types: {sorted(SUPPORTED_MIME_TYPES)}"
            )

        # --- Step 3: Detect document type from filename keywords ---
        document_type = detect_document_type(file_name)

        # --- Step 4: Build IngestedDocument ---
        doc = IngestedDocument(
            job_id=job_id,
            patient_id=patient_id,
            file_bytes=file_bytes,
            mime_type=mime_type,
            document_type=document_type,
            file_name=file_name,
        )

        # --- Log success ---
        duration_ms = (time.perf_counter() - t_start) * 1000
        log_stage(
            logger,
            stage="ingestion",
            job_id=job_id,
            duration_ms=duration_ms,
            status="success",
            document_type=document_type.value,
            mime_type=mime_type,
        )

        return doc

    except Exception:
        # --- Log error ---
        duration_ms = (time.perf_counter() - t_start) * 1000
        log_stage(
            logger,
            stage="ingestion",
            job_id=job_id,
            duration_ms=duration_ms,
            status="error",
            document_type="unknown",
            mime_type="unknown",
        )
        raise
