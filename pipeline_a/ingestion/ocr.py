import fitz
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

def extract_page_with_docling(single_page_pdf_bytes: bytes) -> str:
    try:
        from io import BytesIO
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.base_models import InputFormat, DocumentStream
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        
        opts = PdfPipelineOptions()
        opts.do_ocr = False
        
        stream = DocumentStream(name="page.pdf", stream=BytesIO(single_page_pdf_bytes))
        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
        )
        result = converter.convert(stream)
        md = result.document.export_to_markdown()
        if not md or len(md.strip()) < 20:
            return ""
        return md.strip()
    except Exception as e:
        logger.warning(f"Docling extraction failed: {e}")
        return ""

def extract_text_from_document(file_bytes: bytes, mime_type: str) -> list[Tuple[int, str, str]]:
    """
    Returns a list of (page_no, extractor_name, extracted_text).
    """
    results = []
    settings = get_settings()
    
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
        
    zoom = 200 / 72
    matrix = fitz.Matrix(zoom, zoom)
        
    for page_no in range(1, fitz_doc.page_count + 1):
        fitz_page = fitz_doc[page_no - 1]
        
        if has_extractable_text(fitz_page):
            if settings.USE_DOCLING:
                new_doc = fitz.open()
                new_doc.insert_pdf(fitz_doc, from_page=page_no - 1, to_page=page_no - 1)
                single_page_bytes = new_doc.tobytes()
                new_doc.close()
                
                text = extract_page_with_docling(single_page_bytes)
                if not text:
                    text = str(fitz_page.get_text()).strip()
                    extractor = "pymupdf"
                else:
                    extractor = "docling"
            else:
                text = str(fitz_page.get_text()).strip()
                extractor = "pymupdf"
        else:
            # Scanned/image page -> GPT Vision
            pix = fitz_page.get_pixmap(matrix=matrix)
            img_bytes = pix.tobytes("png")
            text = extract_page_with_vision(img_bytes)
            extractor = "gpt4o_vision"
            
        results.append((page_no, extractor, text))
            
    fitz_doc.close()
    return results
