import uuid
import os
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, Response
from sqlalchemy.orm import Session

from shared.db.session import get_db
from shared.db.models.case import Case, Document, Job
from shared.schemas.case import CaseCreate, CaseResponse, DocumentResponse, JobResponse, CaseDetailResponse
from pydantic import BaseModel
from shared.db.mongo import get_collection

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

@router.get("", response_model=List[CaseResponse])
def list_cases(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    cases = db.query(Case).filter(Case.user_id == str(current_user.user_id)).order_by(Case.created_at.desc()).all()
    return cases

@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_case(case_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    case = db.get(Case, case_id)
    if not case or str(case.user_id) != str(current_user.user_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.post("", response_model=CaseResponse)
def create_case(case_in: CaseCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    db_case = Case(
        id=str(uuid.uuid4()),
        title=case_in.title,
        description=case_in.description,
        status="CREATED",
        user_id=str(current_user.user_id)
    )
    db.add(db_case)
    db.commit()
    db.refresh(db_case)
    return db_case

@router.post("/{case_id}/upload", response_model=DocumentResponse)
def upload_file(case_id: str, file: UploadFile = File(...), db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    case = db.get(Case, case_id)
    if not case or str(case.user_id) != str(current_user.user_id):
        raise HTTPException(status_code=404, detail="Case not found")
        
    ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/tiff"}
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")
        
    existing_doc = db.query(Document).filter_by(case_id=case_id, file_name=file.filename, status="PROCESSED").first()
    if existing_doc:
        return existing_doc
        
    file_bytes = file.file.read()
    
    from storage.backend import get_storage
    storage = get_storage()
    
    document_id = str(uuid.uuid4())
    storage_key = storage.upload_file(file_bytes, case_id, document_id, file.filename)
    
    filename_lower = file.filename.lower()
    if "lab" in filename_lower or "blood" in filename_lower or "report" in filename_lower:
        doc_type = "lab_report"
    elif "rx" in filename_lower or "prescription" in filename_lower or "med" in filename_lower:
        doc_type = "prescription"
    elif "discharge" in filename_lower or "summary" in filename_lower:
        doc_type = "discharge_summary"
    elif "xray" in filename_lower or "mri" in filename_lower or "ct" in filename_lower or "radiology" in filename_lower:
        doc_type = "radiology"
    else:
        doc_type = "unknown"

    doc = Document(
        id=document_id,
        case_id=case_id,
        file_name=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        doc_type=doc_type,
        status="UPLOADED",
        storage_path=storage_key
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc

@router.get("/{case_id}/documents/{document_id}/download")
def download_document(case_id: str, document_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    case = db.get(Case, case_id)
    if not case or str(case.user_id) != str(current_user.user_id):
        raise HTTPException(status_code=404, detail="Case not found")
    doc = db.get(Document, document_id)
    if not doc or doc.case_id != case_id:
        raise HTTPException(status_code=404, detail="Document not found")
        
    from storage.backend import get_storage
    storage = get_storage()
    try:
        file_bytes = storage.download_file(doc.storage_path)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found in storage: {str(e)}")
        
    return Response(
        content=file_bytes,
        media_type=doc.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{doc.file_name}"'}
    )

@router.post("/{case_id}/process", response_model=JobResponse)
def process_case(case_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    case = db.get(Case, case_id)
    if not case or str(case.user_id) != str(current_user.user_id):
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
    from shared.config import get_settings
    
    if get_settings().USE_CELERY:
        process_case_task.delay(job.id, case_id)
    else:
        def background_processing():
            process_case_task.apply(args=[job.id, case_id])
        background_tasks.add_task(background_processing)
    
    return job

@router.get("/{case_id}/jobs/{job_id}", response_model=JobResponse)
def get_job_status(case_id: str, job_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    job = db.get(Job, job_id)
    if not job or job.case_id != case_id:
        raise HTTPException(status_code=404, detail="Job not found for this case")
    case = db.get(Case, case_id)
    if not case or str(case.user_id) != str(current_user.user_id):
        raise HTTPException(status_code=404, detail="Case not found")
    return job

@router.get("/{case_id}/status")
def get_case_status(case_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    case = db.get(Case, case_id)
    if not case or str(case.user_id) != str(current_user.user_id):
        raise HTTPException(status_code=404, detail="Case not found")
        
    job = db.query(Job).filter_by(case_id=case_id).order_by(Job.id.desc()).first()
    job_status = job.status if job else "NONE"
    
    documents = db.query(Document).filter_by(case_id=case_id).all()
    
    return {
        "job_status": job_status,
        "documents": [
            {"document_id": doc.id, "filename": doc.file_name, "status": doc.status}
            for doc in documents
        ]
    }

@router.get("/{case_id}/summary")
def get_summary(case_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    case = db.get(Case, case_id)
    if not case or str(case.user_id) != str(current_user.user_id):
        raise HTTPException(status_code=404, detail="Case not found")
    doc = get_collection("case_insights").find_one({"case_id": case_id})
    if not doc or not doc.get("summary"):
        raise HTTPException(status_code=404, detail="Summary not generated yet")
    return {"summary": doc["summary"]}

@router.get("/{case_id}/timeline")
def get_timeline(case_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    case = db.get(Case, case_id)
    if not case or str(case.user_id) != str(current_user.user_id):
        raise HTTPException(status_code=404, detail="Case not found")
    doc = get_collection("case_insights").find_one({"case_id": case_id})
    if not doc or not doc.get("timeline"):
        raise HTTPException(status_code=404, detail="Timeline not generated yet")
    return {"timeline": doc["timeline"]}

@router.get("/{case_id}/opinion")
def get_opinion(case_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    case = db.get(Case, case_id)
    if not case or str(case.user_id) != str(current_user.user_id):
        raise HTTPException(status_code=404, detail="Case not found")
    doc = get_collection("case_insights").find_one({"case_id": case_id})
    if not doc or not doc.get("opinion"):
        raise HTTPException(status_code=404, detail="Opinion not generated yet")
    return {"opinion": doc["opinion"]}

@router.get("/{case_id}/metadata")
def get_metadata(case_id: str, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    case = db.get(Case, case_id)
    if not case or str(case.user_id) != str(current_user.user_id):
        raise HTTPException(status_code=404, detail="Case not found")
    doc = get_collection("case_metadata").find_one({"case_id": case_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Metadata not found")
    return doc

@router.post("/{case_id}/chat", response_model=ChatResponse)
def chat_with_case(case_id: str, request: ChatRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    case = db.get(Case, case_id)
    if not case or str(case.user_id) != str(current_user.user_id):
        raise HTTPException(status_code=404, detail="Case not found")
        
    from pipeline_b.embedding.embedder import embed_single
    from pipeline_b.vector_db.qdrant_client import search
    
    query_vector = embed_single(request.message)
    
    chunk_points = search("raw_chunks", query_vector, case_id, limit=5)
    chunk_texts = [p.payload["text"] for p in chunk_points if p.payload]
    
    struct_points = search("structured_medical_data", query_vector, case_id, limit=10)
    struct_texts = [p.payload["text"] for p in struct_points if p.payload]
    
    insights_doc = get_collection("case_insights").find_one({"case_id": case_id})
    summary_text = insights_doc.get("summary", "No summary available.") if insights_doc else "No summary available."
    timeline_text = insights_doc.get("timeline", "No timeline available.") if insights_doc else "No timeline available."
    
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
    
    from shared.llm import get_llm_client, get_text_model
    client = get_llm_client()
    text_model = get_text_model()
    
    resp = client.chat.completions.create(
        model=text_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    
    reply = resp.choices[0].message.content or "I was unable to generate a response."
    return ChatResponse(reply=reply)
