import uuid
import os
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from shared.db.session import get_db
from shared.db.models.case import Case, Document, Job, Summary, Opinion, Timeline
from shared.schemas.case import CaseCreate, CaseResponse, DocumentResponse, JobResponse
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

from product.auth.middleware import get_current_user

router = APIRouter(
    prefix="/api/v1/cases", 
    tags=["POC Cases"],
    dependencies=[Depends(get_current_user)]
)

@router.post("", response_model=CaseResponse)
def create_case(case_in: CaseCreate, db: Session = Depends(get_db)):
    db_case = Case(
        id=str(uuid.uuid4()),
        title=case_in.title,
        description=case_in.description,
        status="CREATED"
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case

@router.post("/{case_id}/upload", response_model=DocumentResponse)
def upload_file(case_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    file_bytes = file.file.read()
    
    storage_dir = os.path.join(os.getcwd(), "storage", "cases", case_id)
    os.makedirs(storage_dir, exist_ok=True)
    document_id = str(uuid.uuid4())
    storage_path = os.path.join(storage_dir, f"{document_id}_{file.filename}")
    
    with open(storage_path, "wb") as f:
        f.write(file_bytes)
    
    doc = Document(
        id=document_id,
        case_id=case_id,
        file_name=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        status="UPLOADED",
        storage_path=storage_path
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc

@router.post("/{case_id}/process", response_model=JobResponse)
def process_case(case_id: str, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    job = Job(
        id=str(uuid.uuid4()),
        case_id=case_id,
        status="PROCESSING"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    from pipeline_a.worker.tasks import process_case_task
    process_case_task.delay(job.id, case_id)
    
    return job

@router.get("/{case_id}/summary")
def get_summary(case_id: str, db: Session = Depends(get_db)):
    summary = db.query(Summary).filter_by(case_id=case_id).first()
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not generated yet")
    return {"summary": summary.summary}

@router.get("/{case_id}/opinion")
def get_opinion(case_id: str, db: Session = Depends(get_db)):
    opinion = db.query(Opinion).filter_by(case_id=case_id).first()
    if not opinion:
        raise HTTPException(status_code=404, detail="Opinion not generated yet")
    return {"opinion": opinion.opinion}

@router.post("/{case_id}/chat", response_model=ChatResponse)
def chat_with_case(case_id: str, request: ChatRequest, db: Session = Depends(get_db)):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    from pipeline_b.embedding.embedder import embed_single
    from pipeline_b.vector_db.qdrant_client import search
    
    query_vector = embed_single(request.message)
    
    # Retrieve top-k chunks
    chunk_points = search("raw_chunks", query_vector, case_id, limit=5)
    chunk_texts = [p.payload["text"] for p in chunk_points if p.payload]
    
    # Retrieve top-k structured fields
    struct_points = search("structured_medical_data", query_vector, case_id, limit=10)
    struct_texts = [p.payload["text"] for p in struct_points if p.payload]
    
    # Fetch summary & timeline
    summary_obj = db.query(Summary).filter_by(case_id=case_id).first()
    timeline_obj = db.query(Timeline).filter_by(case_id=case_id).first()
    
    summary_text = summary_obj.summary if summary_obj else "No summary available."
    timeline_text = timeline_obj.timeline_json if timeline_obj else "No timeline available."
    
    # Combine prompt
    prompt = f"""You are a medical AI assistant answering questions about a patient's case.
    
    USER QUESTION: {request.message}
    
    Here is the retrieved context from the patient's case:
    
    --- CASE SUMMARY ---
    {summary_text}
    
    --- CASE TIMELINE ---
    {timeline_text}
    
    --- RELEVANT EXTRACTED DATA ---
    {chr(10).join(struct_texts)}
    
    --- RELEVANT DOCUMENT EXCERPTS ---
    {chr(10).join(chunk_texts)}
    
    Answer the user's question accurately and concisely using ONLY the provided context. If the answer is not in the context, state that you do not know.
    """
    
    from openai import OpenAI
    from shared.config import get_settings
    client = OpenAI(api_key=get_settings().OPENAI_API_KEY)
    
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    
    reply = resp.choices[0].message.content or "I was unable to generate a response."
    return ChatResponse(reply=reply)

