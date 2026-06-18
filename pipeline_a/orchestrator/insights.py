# pipeline_a/orchestrator/insights.py

import json
from sqlalchemy.orm import Session
from openai import OpenAI

from shared.db.models.case import Timeline, Summary, Opinion
from shared.db.models.extraction import ReportField
from shared.config import get_settings
from shared.logger import get_logger

logger = get_logger(__name__)

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=get_settings().OPENAI_API_KEY)
    return _client

def generate_insights_for_case(case_id: str, db: Session):
    logger.info(f"Generating insights for case {case_id}")
    
    # Fetch all ReportFields for the case
    fields = db.query(ReportField).filter(ReportField.case_id == case_id).all()
    if not fields:
        logger.warning(f"No fields found for case {case_id}, skipping insights.")
        return
        
    # Build Master JSON
    master_json = []
    for f in fields:
        master_json.append({
            "name": f.name,
            "value": f.value,
            "unit": f.unit,
            "reference_range": f.reference_range,
            "collection_date": f.collection_date
        })
        
    master_json_str = json.dumps(master_json, indent=2)
    client = _get_client()
    
    # --- Task 9: Timeline Builder ---
    logger.info("Generating Timeline")
    timeline_prompt = "You are a medical timeline builder. Create a chronological timeline of events, tests, and diagnoses from this structured data. Return only Markdown text. Group by date.\n\n" + master_json_str
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": timeline_prompt}],
        temperature=0.0
    )
    timeline_text = resp.choices[0].message.content or ""
    
    # Clear old
    db.query(Timeline).filter(Timeline.case_id == case_id).delete()
    db.add(Timeline(case_id=case_id, timeline_json=timeline_text))
    
    # --- Task 10: Summary Generator ---
    logger.info("Generating Summary")
    summary_prompt = "You are an expert physician. Write a concise, human-readable medical summary of this case based on the structured data and timeline. Return only Markdown text.\n\nData:\n" + master_json_str + "\n\nTimeline:\n" + timeline_text
    resp = client.chat.completions.create(
        model="gpt-4o",
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
    opinion_prompt = "You are an expert physician. Based on the summary and timeline, provide a Clinical Opinion, Prognosis, and Recommendations. Return only Markdown text.\n\nSummary:\n" + summary_text + "\n\nTimeline:\n" + timeline_text
    resp = client.chat.completions.create(
        model="gpt-4o",
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
            model="gpt-4o",
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
    
    payloads_to_embed = []
    
    if summary_text.strip():
        payloads_to_embed.append({
            "category": "summary",
            "text": f"CASE SUMMARY:\n{summary_text}"
        })
        
    if timeline_text.strip():
        payloads_to_embed.append({
            "category": "timeline",
            "text": f"CASE TIMELINE:\n{timeline_text}"
        })
        
    for category in ["diagnoses", "medications", "lab_results", "procedures"]:
        items = cat_json.get(category, [])
        if items:
            items_str = "\n".join([f"- {item}" for item in items])
            payloads_to_embed.append({
                "category": category,
                "text": f"{category.upper()}:\n{items_str}"
            })
            
    if payloads_to_embed:
        texts_to_embed = [p["text"] for p in payloads_to_embed]
        vectors = embed(texts_to_embed)
        
        points = []
        for i, p_dict in enumerate(payloads_to_embed):
            p_dict["case_id"] = case_id
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vectors[i],
                    payload=p_dict
                )
            )
        upsert_vectors("structured_medical_data", points)
    
    db.commit()
    logger.info(f"Successfully generated insights and embedded structured data for case {case_id}")
