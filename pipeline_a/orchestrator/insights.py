# pipeline_a/orchestrator/insights.py

import json
from datetime import datetime
from sqlalchemy.orm import Session
from shared.llm import get_llm_client, get_text_model

from shared.db.models.case import Document
from shared.db.models.extraction import OCRPage
from shared.config import get_settings
from shared.logger import get_logger
from shared.db.mongo import get_collection

logger = get_logger(__name__)


def get_narrative_text(case_id: str, db: Session) -> str:
    """Query ocr_pages and documents from MySQL, sort by document order and page number."""
    docs = db.query(Document).filter(Document.case_id == case_id).order_by(Document.uploaded_at).all()
    if not docs:
        return ""
        
    doc_map = {d.id: d for d in docs}
    doc_ids = list(doc_map.keys())
    
    pages = db.query(OCRPage).filter(OCRPage.document_id.in_(doc_ids)).all()
    # Sort pages in Python by document index then page_no
    doc_order = {d_id: i for i, d_id in enumerate(doc_ids)}
    pages.sort(key=lambda p: (doc_order.get(p.document_id, 999), p.page_no))
    
    lines = []
    for p in pages:
        d = doc_map.get(p.document_id)
        dtype = d.doc_type if d else "unknown"
        lines.append(f"--- DOCUMENT: {dtype} | PAGE {p.page_no} ---\n{p.extracted_text}\n")
        
    return "\n".join(lines)


def get_abnormal_fields_text(case_id: str) -> str:
    """Fetch abnormal clinical fields from MongoDB and format trend strings."""
    doc = get_collection("case_clinical_fields").find_one({"case_id": case_id})
    if not doc or not doc.get("fields"):
        return "No abnormal findings detected."
        
    abnormals = [f for f in doc["fields"] if f.get("is_abnormal") is True]
    if not abnormals:
        return "No abnormal findings detected."
        
    lines = []
    for f in abnormals:
        name = f.get("name", "unknown")
        val = f.get("value", "")
        unit = f.get("unit") or ""
        r_low = f.get("ref_low")
        r_high = f.get("ref_high")
        num_val = f.get("numeric_value")
        
        direction = "ABNORMAL"
        if num_val is not None and r_low is not None and num_val < r_low:
            direction = "LOW"
        elif num_val is not None and r_high is not None and num_val > r_high:
            direction = "HIGH"
            
        ref_str = f"{r_low}–{r_high}" if r_low is not None and r_high is not None else f"high: {r_high}" if r_high is not None else f"low: {r_low}" if r_low is not None else "unknown"
        unit_str = f" {unit}" if unit else ""
        lines.append(f"- {name}: {val}{unit_str} ({direction}, reference: {ref_str})")
        
    return "\n".join(lines)


def get_metadata_text(case_id: str) -> str:
    """Format case metadata from MongoDB."""
    doc = get_collection("case_metadata").find_one({"case_id": case_id})
    if not doc:
        return "Patient & Institution metadata unknown."
        
    p_name = doc.get("patient_name") or "Unknown"
    p_age = doc.get("patient_age") or "?"
    p_sex = doc.get("patient_sex") or "?"
    h_name = doc.get("hospital_name")
    d_name = doc.get("doctor_name")
    c_date = doc.get("collection_date")
    
    parts = [f"Patient: {p_name} | Age: {p_age} | Sex: {p_sex}"]
    if h_name:
        parts.append(f"Hospital: {h_name}")
    if d_name:
        parts.append(f"Doctor: {d_name}")
    if c_date:
        parts.append(f"Report Date: {c_date}")
        
    return "\n".join(parts)


def generate_insights_for_case(case_id: str, db: Session):
    logger.info(f"Generating insights for case {case_id}")
    
    master_doc = get_collection("case_clinical_fields").find_one({"case_id": case_id})
    master_fields = master_doc.get("fields", []) if master_doc else []
    if not master_fields:
        logger.warning(f"No clinical fields found for case {case_id}, continuing with narrative text.")
        
    metadata_text = get_metadata_text(case_id)
    abnormal_text = get_abnormal_fields_text(case_id)
    narrative_text = get_narrative_text(case_id, db)
    
    docs = db.query(Document.doc_type).filter(Document.case_id == case_id).distinct().all()
    doc_types = [d[0] for d in docs if d[0]]
    doc_types_str = ", ".join(doc_types) if doc_types else "unknown"
    
    master_json_str = json.dumps(master_fields, indent=2)
    client = get_llm_client()
    text_model = get_text_model()
    
    # --- Task 9: Timeline Builder ---
    logger.info("Generating Timeline")
    timeline_prompt = f"""You are a medical timeline builder.

PATIENT & INSTITUTION:
{metadata_text}

STRUCTURED CLINICAL DATA:
{master_json_str}

NARRATIVE TEXT FROM DOCUMENTS:
{narrative_text[:8000]}

Create a strict chronological timeline of this patient's medical history.

FORMAT RULES:
- Use ## YYYY-MM-DD as the header for each date
- Under each date, list all events: tests performed, diagnoses made, medications prescribed
- For lab values, include the value, unit, and flag as ⚠️ ABNORMAL if abnormal
- Group all events with the same date under one header
- Sort chronologically, oldest first
- If collection_date is null for a field, group it under ## Date Unknown at the end

Do not invent dates. Do not summarize — list key data points."""

    resp = client.chat.completions.create(
        model=text_model,
        messages=[{"role": "user", "content": timeline_prompt}],
        temperature=0.0
    )
    timeline_text = resp.choices[0].message.content or ""
    
    # --- Task 10: Summary Generator ---
    logger.info("Generating Summary")
    summary_prompt = f"""You are an expert physician writing a structured medical case summary.

PATIENT & INSTITUTION:
{metadata_text}

STRUCTURED CLINICAL DATA:
{master_json_str}

ABNORMAL FINDINGS:
{abnormal_text}

NARRATIVE TEXT FROM DOCUMENTS:
{narrative_text[:8000]}

CASE TIMELINE:
{timeline_text}

Write a clinical summary with these exact sections:
## Chief Complaint & Presentation
## Key Diagnoses
## Laboratory Findings
## Medications Prescribed
## Clinical Course & Timeline
## Current Status

RULES:
- Never invent values not present in the data
- Note trends when the same test appears multiple times
- Use clinical language appropriate for a physician
- If data is insufficient for a section, write "Insufficient data"
"""

    resp = client.chat.completions.create(
        model=text_model,
        messages=[{"role": "user", "content": summary_prompt}],
        temperature=0.0
    )
    summary_text = resp.choices[0].message.content or ""
    
    # Pre-generation check for Opinion
    if not summary_text.strip() or not timeline_text.strip():
        logger.warning(f"Summary or Timeline empty for case {case_id}. Skipping Opinion.")
        opinion_text = "Insufficient data to generate clinical opinion."
    else:
        logger.info("Generating Opinion")
        opinion_prompt = f"""You are a senior consultant physician providing a clinical opinion.

PATIENT & INSTITUTION:
{metadata_text}

DOCUMENT TYPES IN THIS CASE:
{doc_types_str}

CASE SUMMARY:
{summary_text}

CASE TIMELINE:
{timeline_text}

ABNORMAL FINDINGS:
{abnormal_text}

Provide a structured clinical opinion with these exact sections:
## Diagnostic Assessment
Confirm, question, or refine the diagnoses. Note differentials worth considering.

## Critical Findings Requiring Attention
List all abnormal findings and potential risks.

## Treatment Evaluation
Assess appropriateness of prescribed medications.

## Recommendations
Specific, actionable next steps — investigations, referrals, follow-ups.

## Prognosis
Based on available data only.

RULES:
- Clearly distinguish confirmed findings from clinical judgment
- If data is insufficient to form an opinion on a section, say so explicitly
- Do not invent findings not present in the data"""

        resp = client.chat.completions.create(
            model=text_model,
            messages=[{"role": "user", "content": opinion_prompt}],
            temperature=0.0
        )
        opinion_text = resp.choices[0].message.content or ""
        
    now = datetime.utcnow()
    get_collection("case_insights").update_one(
        {"case_id": case_id},
        {"$set": {
            "case_id": case_id,
            "timeline": timeline_text,
            "summary": summary_text,
            "opinion": opinion_text,
            "updated_at": now
        }},
        upsert=True
    )
    
    # --- Task 12: Embed Structured Medical Data ---
    logger.info("Embedding structured_medical_data")
    categorize_prompt = "You are a data structurer. Given this medical JSON array, group the fields into exactly four JSON arrays: 'diagnoses', 'medications', 'lab_results', 'procedures'. Return ONLY valid JSON with those 4 keys, and string arrays as values. Do not hallucinate.\n\n" + master_json_str
    try:
        resp_cat = client.chat.completions.create(
            model=text_model,
            messages=[{"role": "user", "content": categorize_prompt}],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        cat_content = resp_cat.choices[0].message.content or "{}"
        cat_json = json.loads(cat_content)
    except Exception as e:
        logger.error(f"Failed to categorize medical data: {e}")
        cat_json = {"diagnoses": [], "medications": [], "lab_results": [], "procedures": []}
        
    import sys
    from pathlib import Path
    root_dir = str(Path(__file__).resolve().parent.parent.parent)
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
        
    from pipeline_b.vector_db.qdrant_client import ensure_collections_exist, upsert_vectors
    from pipeline_b.embedding.embedder import embed
    from qdrant_client.models import PointStruct
    import uuid
    
    ensure_collections_exist()
    
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    
    def split_chunks(text: str):
        return splitter.split_text(text)
    
    payloads_to_embed = []
    
    if summary_text.strip():
        for i, chunk in enumerate(split_chunks(summary_text)):
            payloads_to_embed.append({
                "category": f"summary_part_{i}",
                "text": f"CASE SUMMARY (Part {i+1}):\n{chunk}"
            })
            
    if timeline_text.strip():
        for i, chunk in enumerate(split_chunks(timeline_text)):
            payloads_to_embed.append({
                "category": f"timeline_part_{i}",
                "text": f"CASE TIMELINE (Part {i+1}):\n{chunk}"
            })
            
    for category in ["diagnoses", "medications", "lab_results", "procedures"]:
        items = cat_json.get(category, [])
        if items:
            items_str = "\n".join([f"- {item}" for item in items if isinstance(item, (str, int, float)) or (isinstance(item, dict) and item.get("name"))])
            if items_str.strip():
                for i, chunk in enumerate(split_chunks(items_str)):
                    payloads_to_embed.append({
                        "category": f"{category}_part_{i}",
                        "text": f"{category.upper()} (Part {i+1}):\n{chunk}"
                    })
            
    if payloads_to_embed:
        texts_to_embed = [p["text"] for p in payloads_to_embed]
        vectors = embed(texts_to_embed)
        
        points = []
        for i, p_dict in enumerate(payloads_to_embed):
            p_dict["case_id"] = case_id
            hash_str = f"{case_id}_{p_dict['category']}_{i}"
            deterministic_id = str(uuid.uuid5(uuid.NAMESPACE_OID, hash_str))
            
            points.append(
                PointStruct(
                    id=deterministic_id,
                    vector=vectors[i],
                    payload=p_dict
                )
            )
        upsert_vectors("structured_medical_data", points)
    
    db.commit()
    logger.info(f"Successfully generated insights and embedded structured data for case {case_id}")
