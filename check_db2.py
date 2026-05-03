from dotenv import load_dotenv
load_dotenv()
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("=" * 60)
print("TABLE: document_jobs")
print("=" * 60)
jobs = db.execute(text(
    "SELECT job_id, patient_id, status, document_type, processed_at FROM document_jobs ORDER BY processed_at DESC"
)).fetchall()
print(f"Total rows: {len(jobs)}")
for j in jobs:
    print(f"  job_id={j.job_id} | patient={j.patient_id} | status={j.status}")

print()
print("=" * 60)
print("TABLE: report_fields")
print("=" * 60)
fields = db.execute(text(
    "SELECT job_id, name, value, unit, reference_range, confidence FROM report_fields ORDER BY job_id"
)).fetchall()
print(f"Total rows: {len(fields)}")
for f in fields:
    print(f"  job_id={f.job_id} | name={f.name} | value={f.value} | unit={f.unit}")

db.close()