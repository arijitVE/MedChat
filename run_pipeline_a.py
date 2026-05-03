from dotenv import load_dotenv
load_dotenv()
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared.db.session import SessionLocal
from pipeline_a.orchestrator.process_document import run

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else "sample_report.pdf"
PATIENT_ID  = "test-patient-001"
JOB_ID      = "job-pipeline-b-test-003"   # new ID to avoid conflict

file_path = Path(REPORT_PATH)
assert file_path.exists(), f"File not found: {REPORT_PATH}"

file_bytes = file_path.read_bytes()
print(f"File: {file_path.name} ({len(file_bytes)} bytes)")
print(f"Job ID: {JOB_ID}")

db = SessionLocal()
try:
    output = run(
        job_id         = JOB_ID,
        patient_id     = PATIENT_ID,
        file_bytes_hex = file_bytes.hex(),
        document_type  = "lab_report",
        db             = db
    )
    db.commit()   # ← THIS was the missing line
    print("\n✅ COMMITTED TO DB")
except Exception as e:
    db.rollback()
    print(f"\n❌ FAILED: {e}")
    raise
finally:
    db.close()

print(f"Fields saved: {len(output.scored_fields)}")
for f in output.scored_fields:
    icon = "✅" if f.status.value == "auto" else "⚠️ "
    print(f"  {icon} {f.name:<35} {f.value} {f.unit or ''}")