# from dotenv import load_dotenv
# load_dotenv()
# import sys
# from pathlib import Path
# sys.path.insert(0, str(Path(__file__).parent))

# from shared.db.session import SessionLocal
# from pipeline_a.orchestrator.process_document import run

# REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else "sample_report.pdf"
# PATIENT_ID  = "test-patient-001"
# DOC_TYPE    = "lab_report"

# file_path = Path(REPORT_PATH)
# assert file_path.exists(), f"File not found: {REPORT_PATH}"

# file_bytes     = file_path.read_bytes()
# file_bytes_hex = file_bytes.hex()
# job_id         = "manual-test-001"

# print(f"\n📄 File      : {file_path.name}")
# print(f"📦 Size      : {len(file_bytes)} bytes")
# print(f"🔑 Job ID    : {job_id}")
# print(f"🏥 Patient   : {PATIENT_ID}")
# print(f"📋 Doc type  : {DOC_TYPE}")
# print("\n⏳ Running pipeline...\n")

# db = SessionLocal()
# try:
#     output = run(
#         job_id         = job_id,
#         patient_id     = PATIENT_ID,
#         file_bytes_hex = file_bytes_hex,
#         document_type  = DOC_TYPE,
#         db             = db
#     )
# finally:
#     db.close()

# print("=" * 55)
# print("✅ PIPELINE COMPLETE")
# print("=" * 55)
# print(f"HITL Required : {output.hitl_required}")
# if output.hitl_reasons:
#     for r in output.hitl_reasons:
#         print(f"  ⚠️  {r}")

# print(f"\nFields extracted: {len(output.scored_fields)}")
# print("-" * 55)
# for f in output.scored_fields:
#     status_icon = "✅" if f.status.value == "auto" else "⚠️ "
#     print(f"{status_icon} {f.name:<35} {f.value} {f.unit or ''}")
#     if f.hitl_reason:
#         print(f"     reason: {f.hitl_reason}")

# print("\n" + "=" * 55)
# print("STRUCTURED TEXT FOR EMBEDDING:")
# print("=" * 55)
# print(output.structured_text_for_embedding)



from dotenv import load_dotenv
load_dotenv()

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from shared.db.session import SessionLocal
from pipeline_a.ingestion import loader
from pipeline_a.ocr.client import run_ocr_on_document
from pipeline_a.ocr.parser import parse_all_responses
from pipeline_a.ocr.confidence import aggregate_confidence
from pipeline_a.llm_extraction.extractor import extract_fields
from pipeline_a.normalization.normalizer import run_normalization
from pipeline_a.matching.matcher import run_matching
from shared.config import get_settings

REPORT_PATH = sys.argv[1] if len(sys.argv) > 1 else "sample_report.pdf"
PATIENT_ID  = "test-patient-001"
JOB_ID      = "manual-test-003"

file_path  = Path(REPORT_PATH)
file_bytes = file_path.read_bytes()

print(f"\n📄 File : {file_path.name}  ({len(file_bytes)} bytes)")
print("=" * 60)

# ── STAGE 1: Ingestion ───────────────────────────────────────
mime_type    = loader.detect_mime_type(file_bytes)
doc_type     = loader.detect_document_type(file_path.name)
print(f"\n📋 Document Type detected : {doc_type}")
print(f"   MIME type              : {mime_type}")

# ── STAGE 2: OCR ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("🔍 RAW OCR OUTPUT")
print("=" * 60)
responses, page_count = run_ocr_on_document(file_bytes, mime_type)
# ocr_result = parse_all_responses(responses, page_count)
raw_text, words = parse_all_responses(responses)
# avg_conf, low_conf = aggregate_confidence(words)
avg_conf, low_conf = aggregate_confidence(words, get_settings().OCR_CONFIDENCE_THRESHOLD)
from shared.schemas.report import OCRResult
ocr_result = OCRResult(
    raw_text=raw_text,
    words=words,
    avg_confidence=avg_conf,
    low_confidence=low_conf
)
print(f"Pages processed : {page_count}")
print(f"Words extracted : {len(ocr_result.words)}")
print(f"Avg confidence  : {ocr_result.avg_confidence:.4f}")
print(f"Low confidence  : {ocr_result.low_confidence}")
print("\n── Full OCR Text ──")
print(ocr_result.raw_text[:3000])
if len(ocr_result.raw_text) > 3000:
    print(f"\n... [truncated — {len(ocr_result.raw_text)} total chars]")
print("\n── Top 20 OCR Words with Confidence ──")
sorted_words = sorted(ocr_result.words, key=lambda w: w.confidence, reverse=True)
for w in sorted_words[:20]:
    print(f"  {w.text:<20} conf={w.confidence:.3f}")

# ── STAGE 3: LLM Extraction ──────────────────────────────────
print("\n" + "=" * 60)
print("🤖 RAW LLM EXTRACTION OUTPUT")
print("=" * 60)
llm_result = extract_fields(ocr_result.raw_text, doc_type, job_id=JOB_ID)
print(f"Fields extracted : {len(llm_result.fields)}")
print(f"Attempt count    : {llm_result.attempt_count}")
print(f"Fallback used    : {llm_result.fallback_used}")
print(f"\nRaw LLM response:")
print(llm_result.raw_llm_response)
print("\n── Parsed Fields ──")
for f in llm_result.fields:
    print(f"  name            : {f.name}")
    print(f"  value           : {f.value}")
    print(f"  unit            : {f.unit}")
    print(f"  reference_range : {f.reference_range}")
    print(f"  collection_date : {f.collection_date}")
    print()

# ── STAGE 4: Normalization ───────────────────────────────────
print("=" * 60)
print("⚙️  NORMALIZATION OUTPUT")
print("=" * 60)
norm_result = run_normalization(llm_result, doc_type, job_id=JOB_ID)
for f in norm_result.fields:
    print(f"  {f.original_name:<25} → {f.normalized_name}")
    print(f"  {f.original_value:<25} → {f.normalized_value}")
    print(f"  unit: {f.unit}")
    print()

# ── STAGE 5: Matching ────────────────────────────────────────
print("=" * 60)
print("🔗 SYNCHRONIZED OUTPUT (OCR ↔ LLM MATCH)")
print("   [This becomes Pipeline B input]")
print("=" * 60)
match_result = run_matching(norm_result, ocr_result, job_id=JOB_ID)
for fs in match_result.field_scores:
    print(f"  Field            : {fs.field_name}")
    print(f"  LLM value        : {fs.llm_value}")
    print(f"  Best OCR phrase  : {fs.ocr_best_phrase}")
    print(f"  Fuzzy score      : {fs.fuzzy_score:.2f}/100")
    print(f"  Semantic score   : {fs.semantic_score:.4f}")
    print(f"  Combined score   : {fs.combined_score:.4f}")
    print()

# ── FULL PIPELINE for structured embedding text ───────────────
print("=" * 60)
print("📦 STRUCTURED TEXT FOR PIPELINE B")
print("=" * 60)
from pipeline_a.orchestrator.process_document import run
db = SessionLocal()
try:
    output = run(
        job_id         = JOB_ID + "-full",
        patient_id     = PATIENT_ID,
        file_bytes_hex = file_bytes.hex(),
        document_type  = doc_type.value if hasattr(doc_type, 'value') else doc_type,
        db             = db
    )
finally:
    db.close()

print(output.structured_text_for_embedding)
print("\n── Final Scored Fields ──")
for f in output.scored_fields:
    icon = "✅" if f.status.value == "auto" else "⚠️ "
    print(f"  {icon} {f.name:<30} {f.value} {f.unit or ''}")
    print(f"     confidence={f.confidence:.4f}  status={f.status.value}")
    if f.hitl_reason:
        print(f"     reason: {f.hitl_reason}")