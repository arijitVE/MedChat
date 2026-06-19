import fitz
import pdfplumber
import base64
import time
import io
from typing import Tuple
from openai import OpenAI
from shared.config import get_settings
from shared.logger import get_logger

logger = get_logger(__name__)

from shared.llm import get_llm_client, get_vision_model

def has_extractable_text(page: fitz.Page) -> bool:
    text = str(page.get_text()).strip()
    return len(text) > 50

def extract_page_with_vision(image_bytes: bytes) -> str:
    client = get_llm_client()
    vision_model = get_vision_model()
    base_prompt = """Extract ALL visible text.
Preserve:
- headings
- tables
- line breaks
- dates
- bullet points
Do NOT summarize.
Do NOT infer.
Return Markdown."""
    
    img_b64 = base64.b64encode(image_bytes).decode('utf-8')
    
    def _call(prompt):
        resp = client.chat.completions.create(
            model=vision_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                ]}
            ],
            temperature=0.0,
            max_tokens=2000,
        )
        return resp.choices[0].message.content or ""
        
    try:
        text = _call(base_prompt).strip()
    except Exception as e:
        logger.warning(f"Vision OCR attempt 1 failed: {e}")
        text = ""
        
    if not text:
        strict_prompt = "CRITICAL INSTRUCTION: Return ONLY the raw markdown text extracted from the image. Do not explain. Do not wrap in markdown fences unless it's a table.\n\n" + base_prompt
        try:
            text = _call(strict_prompt).strip()
        except Exception as e:
            logger.error(f"Vision OCR attempt 2 failed: {e}")
            text = ""
            
    return text

def extract_text_from_document(file_bytes: bytes, mime_type: str) -> list[Tuple[int, str, str]]:
    """
    Returns a list of (page_no, extractor_name, extracted_text).
    """
    results = []
    
    if mime_type != "application/pdf":
        # It's an image
        text = extract_page_with_vision(file_bytes)
        results.append((1, "gpt4o_vision", text))
        return results
        
    # It's a PDF
    try:
        fitz_doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Failed to open PDF with fitz: {e}")
        
    plumber_doc = None
    try:
        plumber_doc = pdfplumber.open(io.BytesIO(file_bytes))
    except Exception as e:
        logger.warning(f"Failed to open PDF with pdfplumber: {e}")
        
    zoom = 200 / 72
    matrix = fitz.Matrix(zoom, zoom)
        
    for page_no in range(1, fitz_doc.page_count + 1):
        fitz_page = fitz_doc[page_no - 1]
        
        if has_extractable_text(fitz_page):
            text = str(fitz_page.get_text()).strip()
            extractor = "pymupdf"
            
            # Use pdfplumber fallback if PyMuPDF text is garbled/short, or if we want table extraction
            if plumber_doc:
                plumber_page = plumber_doc.pages[page_no - 1]
                plumber_text = plumber_page.extract_text() or ""
                tables = plumber_page.extract_tables()
                
                if tables or len(plumber_text.strip()) > len(text) + 50:
                    text = plumber_text
                    if tables:
                        for table in tables:
                            text += "\n" + "\n".join([" | ".join(str(cell) for cell in row if cell) for row in table if any(row)])
                    extractor = "pdfplumber"
                    
            results.append((page_no, extractor, text.strip()))
        else:
            # Scanned/image page -> GPT Vision
            pix = fitz_page.get_pixmap(matrix=matrix)
            img_bytes = pix.tobytes("png")
            text = extract_page_with_vision(img_bytes)
            results.append((page_no, "gpt4o_vision", text))
            
    fitz_doc.close()
    if plumber_doc:
        plumber_doc.close()
        
    return results
