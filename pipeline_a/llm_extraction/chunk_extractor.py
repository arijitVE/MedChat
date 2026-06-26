# pipeline_a/llm_extraction/chunk_extractor.py

import time
from typing import List, Tuple, Any, Dict
from shared.llm import get_llm_client, get_text_model

from shared.config import get_settings
from shared.logger import get_logger, log_stage
from pipeline_a.llm_extraction.parser import parse_combined_llm_response, strip_markdown_fences
from shared.schemas.report import ExtractedField

logger = get_logger(__name__)


_CHUNK_PROMPT = """You are a medical document extraction system. Extract structured data from the following text chunk.

RULES FOR "clinical_fields":
- ONLY extract: lab test results, vital signs, medications with dosage, diagnoses.
- DO NOT extract: hospital, lab name, doctor, patient demographics, addresses, report numbers.
- "numeric_value" must be a float or null — never a string.
- "ref_low" and "ref_high" must be floats or null — never range strings.
- Reference range parsing rules:
  - "10 - 45" or "10-45" → ref_low=10.0, ref_high=45.0
  - "UP TO 41" or "< 41" or "UPTO 41" → ref_low=null, ref_high=41.0
  - "> 50" or "ABOVE 50" → ref_low=50.0, ref_high=null
  - Not present → ref_low=null, ref_high=null
- "collection_date" in ISO format YYYY-MM-DD or null.

RULES FOR "document_metadata":
- Extract ONLY: hospital_name, lab_name, doctor_name, patient_name, patient_age, patient_sex, report_number, collection_date.
- All values are strings or null.
- If a field is not found in the text, set it to null — do not guess.
- "collection_date" in ISO format YYYY-MM-DD or null.

Return ONE STRICT JSON object with exactly two top-level keys:
```json
{
  "clinical_fields": [
    {
      "name": "hemoglobin",
      "value": "8.2",
      "numeric_value": 8.2,
      "unit": "g/dL",
      "reference_range": "11.5-16.4",
      "ref_low": 11.5,
      "ref_high": 16.4,
      "collection_date": "2026-04-10"
    }
  ],
  "document_metadata": {
    "hospital_name": "Srivalli Good Life Diagnostic Centre",
    "lab_name": null,
    "doctor_name": "Dr. R. Sharma",
    "patient_name": "Sukla Karmakar",
    "patient_age": "50",
    "patient_sex": "Female",
    "report_number": null,
    "collection_date": "2026-04-10"
  }
}
```

NOW EXTRACT FROM THIS TEXT:
{chunk_text}
"""

_STRICT_PREFIX = (
    "CRITICAL INSTRUCTION: Return ONLY a JSON object. "
    "No prose. No markdown. No explanation. No formatting. "
    "Start your response with { and end with }. "
    "Nothing else.\n\n"
)

def extract_from_chunk(chunk_text: str, case_id: str, chunk_id: str) -> Tuple[List[ExtractedField], Dict[str, Any]]:
    t_start = time.perf_counter()
    client = get_llm_client()
    text_model = get_text_model()
    
    prompt = _CHUNK_PROMPT.replace("{chunk_text}", chunk_text)
    fields: List[ExtractedField] = []
    metadata: Dict[str, Any] = {}
    
    def _call(p: str) -> str:
        resp = client.chat.completions.create(
            model=text_model,
            messages=[{"role": "user", "content": p}],
            temperature=0.0,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        return strip_markdown_fences(resp.choices[0].message.content or "")

    try:
        raw = _call(prompt)
        fields, metadata = parse_combined_llm_response(raw)
    except Exception as exc:
        logger.warning(f"Chunk LLM extraction attempt 1 failed: {exc}")
        
    if not fields:
        try:
            strict_prompt = _STRICT_PREFIX + prompt
            raw = _call(strict_prompt)
            fields, metadata = parse_combined_llm_response(raw)
        except Exception as exc:
            logger.warning(f"Chunk LLM extraction attempt 2 failed: {exc}")
            
    if not fields:
        logger.warning(
            "chunk_extraction_empty",
            case_id=case_id,
            chunk_id=chunk_id,
            message="field_count == 0 after both extraction attempts"
        )
        
    duration = (time.perf_counter() - t_start) * 1000
    log_stage(
        logger,
        stage="chunk_extraction",
        job_id=case_id,
        duration_ms=duration,
        status="success" if fields else "error",
        field_count=len(fields)
    )
    
    return fields, metadata
