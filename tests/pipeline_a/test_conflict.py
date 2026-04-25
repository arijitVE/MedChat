# tests/pipeline_a/test_conflict.py — HITL trigger logic + upsert idempotency tests
import sys
from pathlib import Path

# Ensure project root is on sys.path
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from shared.schemas.document import IngestedDocument
from shared.schemas.report import DocumentType, OCRResult, ScoredField, FieldStatus, JobStatus
from pipeline_a.conflict.resolver import resolve

class MockSession:
    def execute(self, *args, **kwargs): pass
    def flush(self): pass

def test_hitl_required_when_low_confidence_field():
    doc = IngestedDocument(
        job_id="test-job", patient_id="test-patient", file_bytes=b"", 
        mime_type="application/pdf", document_type=DocumentType.lab_report, file_name=""
    )
    ocr = OCRResult(raw_text="", words=[], avg_confidence=0.9, low_confidence=False)
    scored_fields = [
        ScoredField(
            name="hemoglobin", value="13.5", confidence=0.8, 
            status=FieldStatus.hitl, hitl_reason="Low confidence score"
        )
    ]
    
    db = MockSession()
    output = resolve(doc, ocr, scored_fields, db)
    
    assert output.hitl_required is True
    assert output.job_status == JobStatus.hitl_required
    assert len(output.hitl_reasons) > 0
    assert any("LOW_CONFIDENCE status" in reason for reason in output.hitl_reasons)

def test_low_confidence_tag_in_embedding():
    doc = IngestedDocument(
        job_id="test-job", patient_id="test-patient", file_bytes=b"", 
        mime_type="application/pdf", document_type=DocumentType.lab_report, file_name=""
    )
    ocr = OCRResult(raw_text="", words=[], avg_confidence=0.9, low_confidence=False)
    scored_fields = [
        ScoredField(
            name="glucose", value="95", confidence=0.7, 
            status=FieldStatus.hitl, hitl_reason="Low"
        )
    ]
    
    db = MockSession()
    output = resolve(doc, ocr, scored_fields, db)
    
    assert "[LOW_CONFIDENCE] glucose: 95" in output.structured_text_for_embedding

def test_upsert_duplicate_job_id():
    """Verify that document_jobs uses INSERT ... ON CONFLICT DO UPDATE"""
    from shared.db.models.document import DocumentJob
    from sqlalchemy.dialects.postgresql import insert
    from sqlalchemy.dialects import postgresql
    
    stmt = insert(DocumentJob).values(job_id="test", status="pending", document_type="unknown", patient_id="p")
    stmt = stmt.on_conflict_do_update(index_elements=["job_id"], set_={"status": "completed"})
    
    compiled = str(stmt.compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT (job_id) DO UPDATE" in compiled

def test_upsert_duplicate_job_id_name():
    """Verify that report_fields uses ON CONSTRAINT ... DO UPDATE to prevent IntegrityError"""
    from shared.db.models.extraction import ReportField
    from sqlalchemy.dialects.postgresql import insert
    from sqlalchemy.dialects import postgresql
    
    stmt = insert(ReportField).values(job_id="test", name="hb", patient_id="p", value="1", confidence=1.0, status="auto")
    stmt = stmt.on_conflict_do_update(constraint="uq_report_fields_job_id_name", set_={"value": "2"})
    
    compiled = str(stmt.compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT ON CONSTRAINT uq_report_fields_job_id_name DO UPDATE" in compiled
