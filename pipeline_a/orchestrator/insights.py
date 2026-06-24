# pipeline_a/orchestrator/insights.py

import json
from sqlalchemy.orm import Session
from shared.llm import get_llm_client, get_text_model

from shared.db.models.case import Timeline, Summary, Opinion
from shared.db.models.extraction import ReportField
from shared.config import get_settings
from shared.logger import get_logger

logger = get_logger(__name__)


def generate_insights_for_case(case_id: str, db: Session):
    logger.info(f"Generating insights for case {case_id}")
    
    # Fetch all ReportFields for the case
    fields = db.query(ReportField).filter(ReportField.case_id == case_id).all()
    if not fields:
        logger.warning(f"No fields found for case {case_id}, skipping insights.")
        return
        
    from shared.db.models.case import Document
    from shared.utils.abnormal import check_abnormal
    
    doc_map = {
        doc.id: doc 
        for doc in db.query(Document)
            .filter(Document.case_id == case_id).all()
    }

    master_json = []
    for f in fields:
        doc = doc_map.get(f.document_id)
        
        master_json.append({
            "name": f.name,
            "value": f.value,
            "unit": f.unit,
            "reference_range": f.reference_range,
            "collection_date": f.collection_date,
            "document_type": doc.doc_type if doc else "unknown",
            "source_file": doc.file_name if doc else "unknown",
            "is_abnormal": check_abnormal(f.numeric_value, f.reference_range, f.unit),
        })
        
    master_json_str = json.dumps(master_json, indent=2)
    client = get_llm_client()
    text_model = get_text_model()
    
    # --- Task 9: Timeline Builder ---
    logger.info("Generating Timeline")
    timeline_prompt = f"""You are a medical timeline builder.

PATIENT DATA:
{master_json_str}

Create a strict chronological timeline of this patient's medical history.

FORMAT RULES:
- Use ## YYYY-MM-DD as the header for each date
- Under each date, list all events: tests performed, diagnoses made, medications prescribed
- For lab values, include the value, unit, and flag as ⚠️ ABNORMAL if is_abnormal is True
- Group all events with the same date under one header
- Sort chronologically, oldest first
- If collection_date is null for a field, group it under ## Date Unknown at the end

Do not invent dates. Do not summarize — list every data point."""
    resp = client.chat.completions.create(
        model=text_model,
        messages=[{"role": "user", "content": timeline_prompt}],
        temperature=0.0
    )
    timeline_text = resp.choices[0].message.content or ""
    
    # Clear old
    db.query(Timeline).filter(Timeline.case_id == case_id).delete()
    db.add(Timeline(case_id=case_id, timeline_json=timeline_text))
    
    # --- Task 10: Summary Generator ---
    logger.info("Generating Summary")
    summary_prompt = f"""You are an expert physician writing a structured medical case summary.

PATIENT DATA:
{master_json_str}

Write a clinical summary with these exact sections:
## Chief Complaint & Presentation
## Key Diagnoses
## Laboratory Findings
(For each lab value: state the value, unit, reference range, and whether it is ABNORMAL or NORMAL. 
For fields where is_abnormal is True, prefix with ⚠️. 
For fields where is_abnormal is None, use clinical judgment.)
## Medications Prescribed
## Clinical Course & Timeline
## Current Status

RULES:
- Never invent values not present in the data
- Note trends when the same test appears multiple times with different collection_date values
- Use clinical language appropriate for a physician
- If data is insufficient for a section, write "Insufficient data"
- Fields with document_type of lab_report are objective findings; prescription fields are treatments"""
    resp = client.chat.completions.create(
        model=text_model,
        messages=[{"role": "user", "content": summary_prompt}],
        temperature=0.0
    )
    summary_text = resp.choices[0].message.content or ""
    
    db.query(Summary).filter(Summary.case_id == case_id).delete()
    db.add(Summary(case_id=case_id, summary=summary_text))
    
    # Pre-generation check for Opinion
    if not summary_text.strip() or not timeline_text.strip():
        logger.warning(f"Summary or Timeline empty for case {case_id}. Skipping Opinion.")
        db.commit()
        return
        
    # --- Task 11: Opinion Generator ---
    logger.info("Generating Opinion")
    opinion_prompt = f"""You are a senior consultant physician providing a second opinion.

CASE SUMMARY:
{summary_text}

CLINICAL TIMELINE:
{timeline_text}

RAW STRUCTURED DATA:
{master_json_str}

Provide a structured clinical opinion with these exact sections:
## Diagnostic Assessment
Confirm, question, or refine the diagnoses. Note differentials worth considering.

## Critical Findings Requiring Attention
List all fields where is_abnormal is True. Flag any potentially dangerous drug combinations or doses.

## Treatment Evaluation
Assess appropriateness of prescribed medications and their doses.

## Recommendations
Specific, actionable next steps — investigations, referrals, follow-ups.

## Prognosis
Based on available data only.

RULES:
- Clearly distinguish confirmed findings from clinical judgment
- If is_abnormal is True for any field, it must appear in Critical Findings
- If data is insufficient to form an opinion on a section, say so explicitly
- Do not invent findings not present in the data"""
    resp = client.chat.completions.create(
        model=text_model,
        messages=[{"role": "user", "content": opinion_prompt}],
        temperature=0.0
    )
    opinion_text = resp.choices[0].message.content or ""
    
    db.query(Opinion).filter(Opinion.case_id == case_id).delete()
    db.add(Opinion(case_id=case_id, opinion=opinion_text))
    
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
    
    def chunk_text(text: str):
        return splitter.split_text(text)
    
    payloads_to_embed = []
    
    if summary_text.strip():
        for i, chunk in enumerate(chunk_text(summary_text)):
            payloads_to_embed.append({
                "category": f"summary_part_{i}",
                "text": f"CASE SUMMARY (Part {i+1}):\n{chunk}"
            })
            
    if timeline_text.strip():
        for i, chunk in enumerate(chunk_text(timeline_text)):
            payloads_to_embed.append({
                "category": f"timeline_part_{i}",
                "text": f"CASE TIMELINE (Part {i+1}):\n{chunk}"
            })
            
    for category in ["diagnoses", "medications", "lab_results", "procedures"]:
        items = cat_json.get(category, [])
        if items:
            items_str = "\n".join([f"- {item}" for item in items])
            for i, chunk in enumerate(chunk_text(items_str)):
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
            
            # Deterministic ID to prevent duplicate vectors on rerun
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
