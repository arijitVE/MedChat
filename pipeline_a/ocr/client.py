# pipeline_a/ocr/client.py — Google Cloud Vision API wrapper (swappable)
#
# The OCR backend is isolated here. To swap to Tesseract or Azure:
# implement the same interface (run_ocr, pdf_to_images) and change the
# import in the orchestrator. Nothing downstream changes.

from __future__ import annotations

import io
from typing import Any

from google.cloud import vision

from shared.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Vision API client (lazy singleton)
# ---------------------------------------------------------------------------

_vision_client: vision.ImageAnnotatorClient | None = None


def _get_vision_client() -> vision.ImageAnnotatorClient:
    """Return a cached Vision API client instance."""
    global _vision_client
    if _vision_client is None:
        _vision_client = vision.ImageAnnotatorClient()
    return _vision_client


# ---------------------------------------------------------------------------
# PDF → images conversion via PyMuPDF
# ---------------------------------------------------------------------------


def pdf_to_images(file_bytes: bytes, dpi: int = 200) -> list[bytes]:
    """Convert each page of a PDF to a PNG image using PyMuPDF.

    Args:
        file_bytes: Raw PDF bytes.
        dpi: Resolution for rasterisation (default 200 — balances quality
             and processing time for medical documents).

    Returns:
        List of PNG image bytes, one per page.

    Raises:
        ValueError: If the PDF cannot be opened or has zero pages.
    """
    import fitz  # PyMuPDF

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Failed to open PDF: {exc}") from exc

    if doc.page_count == 0:
        raise ValueError("PDF has zero pages")

    images: list[bytes] = []
    zoom = dpi / 72  # PyMuPDF default is 72 DPI
    matrix = fitz.Matrix(zoom, zoom)

    for page_num in range(doc.page_count):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=matrix)
        images.append(pix.tobytes("png"))

    doc.close()
    return images


# ---------------------------------------------------------------------------
# Core OCR function
# ---------------------------------------------------------------------------


def run_ocr(image_bytes: bytes) -> Any:
    """Run Google Cloud Vision document_text_detection on a single image.

    Args:
        image_bytes: Raw image bytes (PNG, JPEG, etc.).

    Returns:
        The full Vision API AnnotateImageResponse object.

    Raises:
        RuntimeError: If the Vision API returns an error response.
        Exception: Any underlying API transport error is re-raised with
                   context so the caller (orchestrator) can upsert job
                   status=FAILED.
    """
    client = _get_vision_client()
    image = vision.Image(content=image_bytes)

    try:
        response = client.document_text_detection(image=image)
    except Exception as exc:
        raise RuntimeError(
            f"Google Cloud Vision API call failed: {exc}"
        ) from exc

    # Vision API returns errors in the response object itself
    if response.error.message:
        raise RuntimeError(
            f"Vision API error: {response.error.message} "
            f"(code: {response.error.code})"
        )

    return response


# ---------------------------------------------------------------------------
# Multi-page OCR orchestration
# ---------------------------------------------------------------------------


def run_ocr_on_document(
    file_bytes: bytes,
    mime_type: str,
) -> tuple[list[Any], int]:
    """Run OCR on a full document (PDF or single image).

    Handles PDF-to-image conversion internally. Returns one Vision API
    response per page.

    Args:
        file_bytes: Raw file bytes.
        mime_type: Detected MIME type from the ingestion stage.

    Returns:
        Tuple of (list_of_vision_responses, page_count).

    Raises:
        ValueError: If PDF cannot be processed.
        RuntimeError: If any Vision API call fails.
    """
    if mime_type == "application/pdf":
        page_images = pdf_to_images(file_bytes, dpi=200)
    else:
        page_images = [file_bytes]

    responses: list[Any] = []
    for page_bytes in page_images:
        resp = run_ocr(page_bytes)
        responses.append(resp)

    return responses, len(page_images)
