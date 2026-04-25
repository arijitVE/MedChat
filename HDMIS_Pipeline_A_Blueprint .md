# HDMIS Pipeline A — Implementation Blueprint
### Consensus-Based Medical Document Extraction Pipeline

---

## AGENT INSTRUCTIONS — READ BEFORE WRITING ANY CODE

> This document is the authoritative specification for Pipeline A of the HDMIS system.
> You are a coding agent. Before generating any file, internalize and strictly follow
> every rule in this section. Do not deviate from the folder structure, file names,
> or code patterns defined here.

### Mandatory Folder Structure

You MUST create every file at exactly the path shown below. Do not invent new directories,
do not collapse modules into each other, do not rename files. If a file is not listed here,
ask before creating it.

```
hdmis/
│
├── shared/
│   ├── config.py              → Centralized configuration (env-based, cached singleton)
│   │                             API keys, DB URLs, model configs, thresholds
│   │
│   ├── logger.py              → Structured JSON logging (request_id, doc_id, stage-wise logs)
│   │                             Used across all pipelines for observability
│   │
│   ├── db/
│   │   ├── base.py            → SQLAlchemy Base + metadata registry
│   │   ├── session.py         → DB session factory + FastAPI dependency (get_db)
│   │   └── models/
│   │       ├── document.py    → document_jobs table (status, pipeline version, timestamps)
│   │       ├── ocr.py         → raw OCR output (text, tokens, bounding boxes)
│   │       ├── extraction.py  → LLM structured outputs (JSON)
│   │       ├── matching.py    → fuzzy + semantic comparison results
│   │       ├── confidence.py  → per-field confidence + breakdown
│   │       └── hitl.py        → HITL queue + reviewer decisions
│   │
│   ├── schemas/
│   │   ├── document.py        → Input/output schema for ingestion layer
│   │   ├── report.py          → Core structured medical schema (medications, dosage, etc.)
│   │   └── pipeline.py        → Unified schema for passing data between pipeline stages
│   │
│   └── utils/
│       ├── text.py            → Text cleaning, normalization helpers
│       ├── medical_dict.py    → Synonym maps (PCM → Paracetamol, BID → 2x/day)
│       └── validators.py      → Field validation rules (dosage format, frequency patterns)
│
├── pipeline_a/
│   ├── ingestion/
│   │   └── loader.py          → MIME detection, PDF/image parsing → IngestedDocument
│   │
│   ├── ocr/
│   │   ├── client.py          → Google Vision API wrapper
│   │   ├── parser.py          → Extracts text, tokens, bounding boxes from OCR response
│   │   └── confidence.py      → Aggregates token-level confidence → usable metrics
│   │
│   ├── llm_extraction/
│   │   ├── extractor.py       → Gemini API call + 3-attempt retry cascade
│   │   ├── prompts/
│   │   │   └── prescription_prompt.txt  → Versioned prompt templates
│   │   ├── parser.py          → Validates + parses LLM JSON into Pydantic models
│   │   └── fallback.py        → Regex-based extraction (last resort after retries)
│   │
│   ├── normalization/
│   │   └── normalizer.py      → Standardizes units, expands abbreviations, medical synonyms
│   │                             Imports synonym maps from shared/utils/medical_dict.py
│   │
│   ├── matching/
│   │   └── matcher.py         → Phrase-window OCR matching + contextual semantic similarity
│   │
│   ├── confidence/
│   │   └── scorer.py          → Weighted per-field confidence; fuzzy OCR word mapping
│   │
│   ├── conflict/
│   │   └── resolver.py        → HITL trigger logic + PipelineAOutput assembly
│   │
│   ├── hitl/
│   │   ├── service.py         → Business logic for HITL queue handling
│   │   ├── api.py             → Endpoints for reviewer (approve/edit/reject)
│   │   └── queue.py           → Push low-confidence cases into review pipeline
│   │
│   ├── orchestrator/
│   │   └── process_document.py → Central stage sequencer:
│   │                              ingestion → ocr → llm → normalize → match → score → conflict
│   │                              Handles retries, logging, DB writes
│   │
│   ├── worker/
│   │   └── tasks.py           → Celery async entrypoint; calls orchestrator ONLY
│   │
│   └── api/
│       └── routes.py          → FastAPI endpoints: upload, status poll, HITL submit
│
├── pipeline_b/                → RESERVED. Empty for Phase 2. Do NOT add files here.
│
├── infra/
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── docker-compose.yml → Multi-service setup (API, worker, DB, Redis)
│   ├── queue/
│   │   └── celery_config.py   → Celery + Redis configuration
│   └── scripts/
│       ├── migrate.sh
│       └── seed_data.sh
│
├── tests/
│   └── pipeline_a/
│       ├── test_normalization.py
│       ├── test_matching.py
│       ├── test_conflict.py
│       └── fixtures/
│           └── sample_lab_ocr.txt
│
├── requirements.txt
└── .env.example
```

### File Placement Rules

- `shared/` is for code used by more than one pipeline. Do not put pipeline-specific logic here.
- `shared/utils/medical_dict.py` is the single source of truth for all synonym maps. The normalizer imports from here — it does NOT define synonyms inline.
- `shared/utils/validators.py` holds ALL field validation rules. Import it wherever validation is needed.
- `shared/db/models/` has one file per domain entity. Do not merge them into a single `models.py`.
- `pipeline_a/orchestrator/process_document.py` owns the stage call sequence. `worker/tasks.py` calls the orchestrator — it must not call any stage directly.
- Every directory must have an `__init__.py`. Create them all during the scaffolding step.
- `pipeline_b/` must remain empty. Do not scaffold, stub, or populate it.

### Code Quality Rules

- No raw `dict` crosses a stage boundary. All inter-stage data uses the Pydantic models in `shared/schemas/`.
- Every stage function must emit a structured log entry (via `shared/logger.py`) at entry and exit, including `job_id`, `stage`, and `duration_ms`.
- Every external API call (Vision, Gemini) must be wrapped in try/except. Failures must upsert job status in DB — never silently swallow errors.
- All DB writes use upsert (`INSERT ... ON CONFLICT ... DO UPDATE`) on `job_id`. Never use bare `INSERT`. Celery retries will re-execute tasks; duplicate rows must be impossible at the DB level.
- Observability fields (latency, HITL rate, failure rate per stage) must be emitted as structured log fields — see Section 3 for the full required list.

---

## 1. System Overview

Pipeline A is a write-time, asynchronous document understanding engine that transforms raw medical
documents (PDFs, scanned images) into verified, confidence-scored, structured JSON records stored
in PostgreSQL. It operates on a **dual-extraction consensus model**: a large language model
(Gemini 1.5 Pro / MedGemma) acts as the primary semantic parser producing structured JSON, while
Google Cloud Vision OCR provides a raw-text anchor that grounds and verifies the LLM output.

A normalization layer first canonicalizes both outputs (synonym mapping, unit standardization,
spell correction), then a phrase-level fuzzy + contextual semantic matching engine computes
per-field confidence scores. Fields that fall below the confidence threshold — or where critical
data is absent — are automatically routed to a **Human-in-the-Loop (HITL)** review queue.

The final output (`PipelineAOutput`) is written to PostgreSQL. The
`structured_text_for_embedding` field includes all fields — AUTO fields verbatim, HITL fields
tagged with `[LOW_CONFIDENCE]` — so Pipeline B (RAG + retrieval, Phase 2) reads a complete
picture without losing partially-correct data.

---

## 2. Step-by-Step Build Process

---

### Step 1 — Project Scaffold & Configuration

**Objective:** Create the complete folder structure, all `__init__.py` files, dependency manifest,
and environment configuration.

**Input:** Nothing — greenfield setup.  
**Output:** Runnable Python project with settings loading from `.env`.

**Core Logic:**
```
Follow the mandatory folder structure from the AGENT INSTRUCTIONS section exactly.
Create all __init__.py files now — do not defer.

Settings singleton — shared/config.py:
  get_settings() → cached Pydantic BaseSettings
  Reads:
    GEMINI_API_KEY
    GOOGLE_APPLICATION_CREDENTIALS
    DATABASE_URL
    REDIS_URL
    OCR_CONFIDENCE_THRESHOLD       (default: 0.85)
    FIELD_CONFIDENCE_THRESHOLD     (default: 0.85)
    FUZZY_MATCH_THRESHOLD          (default: 85)
```

**Key Dependencies:** `pydantic-settings`, `structlog`, `python-dotenv`

---

### Step 2 — Pydantic Schema Contracts

**Objective:** Define the typed data contracts that flow between every pipeline stage.
No raw dicts cross stage boundaries.

**Input:** Architectural design decisions.  
**Output:** `shared/schemas/report.py`, `shared/schemas/document.py`, `shared/schemas/pipeline.py`

**Core Logic:**
```
Enums (shared/schemas/report.py):
  DocumentType  → lab_report | prescription | discharge_summary | radiology | unknown
  FieldStatus   → auto | hitl | missing
  JobStatus     → pending | processing | completed | failed | hitl_required

Stage models (in pipeline order):
  IngestedDocument      → job_id, patient_id, file_bytes, mime_type, document_type

  OCRResult             → raw_text, words: [OCRWord(text, confidence, bounding_box)],
                          avg_confidence, low_confidence (bool)

  LLMExtractionResult   → fields: [ExtractedField(name, value, unit,
                          reference_range, collection_date)], raw_llm_response,
                          attempt_count (int), fallback_used (bool)

  NormalizationResult   → fields: [NormalizedField(original_name, normalized_name,
                          original_value, normalized_value, unit)]

  MatchingResult        → field_scores: [FieldMatchScore(field_name, llm_value,
                          ocr_best_phrase, fuzzy_score, semantic_score, combined_score)]

  ScoredField           → name, value, confidence, status, hitl_reason

  PipelineAOutput       → all ScoredFields + hitl_required + hitl_reasons
                          + structured_text_for_embedding  ← Pipeline B reads this
```

**Key Dependencies:** `pydantic==2.x`

---

### Step 3 — Database Layer

**Objective:** Persist job state and extracted fields so the API can poll status and
Pipeline B can query structured text. All writes must be idempotent.

**Input:** `PipelineAOutput` schema.  
**Output:** ORM models in `shared/db/models/`; session factory in `shared/db/session.py`.

**Core Logic:**
```sql
-- shared/db/models/document.py
Table: document_jobs
  job_id (PK, UNIQUE — upsert target)
  patient_id (indexed), document_type, file_name,
  status (JobStatus enum), hitl_required (bool), hitl_reasons (JSON),
  structured_text_for_embedding (text),   ← Pipeline B reads this column
  uploaded_at, processed_at, error_message,
  ocr_latency_ms (float), llm_latency_ms (float)   ← observability columns

-- shared/db/models/extraction.py
Table: report_fields
  id (PK)
  job_id (FK → document_jobs, ON DELETE CASCADE)
  patient_id (indexed, denormalised)
  name, value, unit, reference_range, collection_date,
  confidence (float), status (FieldStatus enum), hitl_reason
  UNIQUE(job_id, name)   ← enables upsert on retry

All DB writes:
  document_jobs → INSERT ... ON CONFLICT (job_id) DO UPDATE SET ...
  report_fields → INSERT ... ON CONFLICT (job_id, name) DO UPDATE SET ...
  Never use bare INSERT anywhere in the codebase.

Session factory (shared/db/session.py):
  get_db() → yields Session (FastAPI dependency)
  init_db() → Base.metadata.create_all()  [dev only; use Alembic in prod]
```

**Key Dependencies:** `sqlalchemy==2.x`, `psycopg2-binary`, `alembic`

---

### Step 4 — Stage 1: Ingestion

**Objective:** Accept raw file bytes, validate MIME type, detect document category,
return `IngestedDocument`.

**Input:** `file_bytes (bytes)`, `file_name (str)`, `patient_id (str)`  
**Output:** `IngestedDocument`

**Core Logic:**
```
File: pipeline_a/ingestion/loader.py

1. Detect MIME from magic bytes first (not extension):
     %PDF     → application/pdf
     \xff\xd8 → image/jpeg
     \x89PNG  → image/png
     II* / MM → image/tiff
   Fallback: mimetypes.guess_type(file_name)

2. Reject if MIME not in supported set → raise ValueError (never silently proceed)

3. Detect DocumentType from filename keywords:
     "lab", "cbc", "blood", "report" → lab_report
     "prescription", "rx"            → prescription
     "discharge", "summary"          → discharge_summary
     "radiology", "xray", "mri"      → radiology
     else                            → unknown

4. Return IngestedDocument with a fresh UUID job_id

Log: emit stage=ingestion, job_id, document_type, mime_type, duration_ms
```

**Key Dependencies:** `python-multipart` (FastAPI upload), `mimetypes` (stdlib)

---

### Step 5 — Stage 2: OCR

**Objective:** Extract raw text and per-word confidence scores from the document
to act as the verification anchor.

**Input:** `IngestedDocument`  
**Output:** `OCRResult`

**Core Logic:**
```
File: pipeline_a/ocr/client.py   (Vision API wrapper — swappable)
File: pipeline_a/ocr/parser.py   (response → OCRResult)
File: pipeline_a/ocr/confidence.py (word-level → aggregate confidence)

t_start = now()

IF mime_type == "application/pdf":
    pages = pdf_to_images(file_bytes, dpi=200)  # PyMuPDF
ELSE:
    pages = [file_bytes]

FOR each page image:
    response = VisionClient.document_text_detection(image)
    extract: full_text, per-word (text, confidence, bounding_box)
    append to all_words, all_text

avg_confidence = mean(word.confidence for all words)
low_confidence = avg_confidence < OCR_CONFIDENCE_THRESHOLD   # → HITL trigger
ocr_latency_ms = (now() - t_start) * 1000

Log: emit stage=ocr, job_id, page_count, avg_confidence, low_confidence, ocr_latency_ms
Return OCRResult
```

> **Swappability:** The OCR backend is isolated in `ocr/client.py`. To swap to Tesseract or
> Azure: implement the same interface and change the import. Nothing downstream changes.

**Key Dependencies:** `google-cloud-vision`, `pymupdf`

---

### Step 6 — Stage 3: LLM Extraction

**Objective:** Use Gemini to semantically parse the OCR text into structured field JSON.
This stage does **parsing only** — not reasoning or trend analysis (that is Pipeline B).

**Input:** `OCRResult`, `DocumentType`  
**Output:** `LLMExtractionResult`

**Core Logic:**
```
File: pipeline_a/llm_extraction/extractor.py
File: pipeline_a/llm_extraction/parser.py
File: pipeline_a/llm_extraction/fallback.py

Select prompt template by DocumentType (from pipeline_a/llm_extraction/prompts/):
  lab_report     → extract test name, value, unit, reference_range, collection_date
  prescription   → extract drug name, dosage, frequency, prescription_date
  other          → generic key-value extraction

Prompt rules (enforced in system prompt):
  - Respond ONLY with valid JSON, no markdown fences, no preamble
  - Use lowercase canonical field names
  - Do not invent values not present in text
  - temperature=0.0  (deterministic parsing)

t_start = now()

RETRY CASCADE — do not fall back on first failure:
  Attempt 1: standard prompt + full OCR text
  On JSON parse fail or empty response:
    Attempt 2: stricter prompt ("return ONLY a JSON array, no prose, no formatting")
  On second failure:
    Attempt 3: simplified input (first 500 tokens of OCR text only)
  On third failure:
    Activate fallback.py: regex extraction for common medical patterns
      e.g. r"([\w\s]+):\s*([\d.]+)\s*(g/dL|mg/dL|%|mmol/L|IU/L)"
    Return whatever regex captured (may be partial — still better than empty)
  Only if ALL attempts and regex yield nothing:
    Return LLMExtractionResult(fields=[], fallback_used=True)
    → conflict stage will flag HITL

llm_latency_ms = (now() - t_start) * 1000
Strip markdown fences from response before JSON.loads()
Validate each field against ExtractedField Pydantic model

Log: emit stage=llm_extraction, job_id, attempt_count, field_count,
     fallback_used, llm_latency_ms
```

**Key Dependencies:** `google-generativeai` (Gemini 1.5 Pro), structured prompt engineering

---

### Step 7 — Stage 4: Normalization

**Objective:** Canonicalize field names, values, and units from LLM output before comparison.
This removes 60–70% of false conflicts downstream.

**Input:** `LLMExtractionResult`  
**Output:** `NormalizationResult`

**Core Logic:**
```
File: pipeline_a/normalization/normalizer.py
Imports: from shared.utils.medical_dict import MEDICAL_SYNONYMS, UNIT_SYNONYMS
Imports: from shared.utils.validators import validate_field

For each ExtractedField:

  normalize_name(name):
    cleaned = name.strip().lower()
    return MEDICAL_SYNONYMS.get(cleaned, cleaned)
    # e.g. "hgb" → "hemoglobin", "pcm" → "paracetamol", "sgpt" → "alanine aminotransferase"
    # MEDICAL_SYNONYMS is defined in shared/utils/medical_dict.py — never inline here

  normalize_unit(unit):
    cleaned = unit.strip().lower()
    return UNIT_SYNONYMS.get(cleaned, unit)
    # e.g. "g/dl" → "g/dL", "mg/dl" → "mg/dL", "cells/cumm" → "cells/µL"

  normalize_value(value):
    strip whitespace
    remove thousands-separator commas ("1,50,000" → "150000")

Return NormalizationResult with original values preserved alongside normalized
```

> **Rule:** `MEDICAL_SYNONYMS` and `UNIT_SYNONYMS` must never be defined inline in
> `normalizer.py`. They live in `shared/utils/medical_dict.py` so they can be updated
> as a configuration artifact without touching pipeline code.

**Key Dependencies:** `rapidfuzz` (for spell correction support), stdlib for core maps

---

### Step 8 — Stage 5: Matching

**Objective:** For each normalized LLM field, find its best anchor in the OCR text using
phrase-level fuzzy matching and contextual semantic similarity. Single-token matching is
insufficient for medical documents — use sliding n-gram windows.

**Input:** `NormalizationResult`, `OCRResult`  
**Output:** `MatchingResult`

**Core Logic:**
```
File: pipeline_a/matching/matcher.py

# Build OCR phrase windows — NOT single tokens
# Medical values appear as multi-word spans: "Hb: 13.5 g/dL", "Amox 500mg", "BP 120/80"
# Tokenizing on whitespace and comparing single tokens loses this context.

ocr_words = raw_text.split()
ocr_phrases = []
for n in range(2, 6):                              # 2-gram to 5-gram windows
    for i in range(len(ocr_words) - n + 1):
        ocr_phrases.append(" ".join(ocr_words[i:i+n]))
ocr_phrases += ocr_words                           # include unigrams as fallback
deduplicate ocr_phrases

FOR each normalized_field:

  # Build field context string for comparison (not just the bare value)
  field_context = f"{field.normalized_name} {field.normalized_value} {field.unit}".strip()
  # e.g. "hemoglobin 13.5 g/dL"  NOT just "13.5"

  # Fuzzy match: field context vs all OCR phrases (catches typos, OCR scan errors)
  best_phrase, fuzzy_score = rapidfuzz.process.extractOne(
    field_context, ocr_phrases, scorer=token_set_ratio
  )  # score: 0–100

  # Semantic match: embed context strings, not bare values
  # "hemoglobin 13.5 g/dL" vs "Hb 13.5 g/dL" — synonym-aware, not token-exact
  semantic_score = cosine_similarity(
    embed(field_context),
    embed(best_phrase)
  )  # sentence-transformers all-MiniLM-L6-v2, returns 0–1

  combined_score = 0.6 * (fuzzy_score / 100) + 0.4 * semantic_score

  Append FieldMatchScore(field_name, llm_value, ocr_best_phrase=best_phrase,
                          fuzzy_score, semantic_score, combined_score)
```

> **Model note (MVP):** Uses `all-MiniLM-L6-v2` (80MB, fast). Phase 2: swap to
> `medicalai/ClinicalBERT` for domain-tuned medical embeddings. Model is isolated behind
> `_get_embedding_model()` — nothing else changes on swap.

**Key Dependencies:** `rapidfuzz`, `sentence-transformers`, `scikit-learn` (cosine_similarity)

---

### Step 9 — Stage 6a: Confidence Scoring

**Objective:** Combine match scores with OCR word-level confidence into a single per-field score.
Use fuzzy matching (not exact string match) when mapping field values back to OCR words.

**Input:** `MatchingResult`, `NormalizationResult`, `OCRResult`  
**Output:** `list[ScoredField]`

**Core Logic:**
```
File: pipeline_a/confidence/scorer.py

FOR each FieldMatchScore:

  # Map field value back to OCR words using fuzzy partial match
  # Do NOT use exact string match — formatting differences break it:
  #   "13.5" vs "13.50", "Hb" vs "HB", "500mg" vs "500 mg"
  matching_words = [
    word for word in ocr_result.words
    if rapidfuzz.fuzz.partial_ratio(field.normalized_value, word.text) >= 80
  ]
  ocr_word_conf = mean(w.confidence for w in matching_words) if matching_words else 0.5
  # 0.5 = penalised but not auto-rejected
  # Monitor semantic_score=0 + fuzzy<50 in logs: signals handwriting/scan quality issues

  # Prioritise match quality (0.7) over raw OCR scan confidence (0.3)
  final_score = 0.7 * match.combined_score + 0.3 * ocr_word_conf

  status = AUTO  if final_score >= FIELD_CONFIDENCE_THRESHOLD
           HITL  otherwise

  hitl_reason = descriptive string if HITL (includes all component scores)

Log: emit stage=confidence_scoring, job_id, field_name, final_score, status per field
     Aggregate: hitl_field_count, auto_field_count, avg_final_score
```

**Key Dependencies:** `rapidfuzz` (fuzzy OCR word mapping)

---

### Step 10 — Stage 6b: Conflict Resolution & Output Assembly

**Objective:** Apply HITL trigger rules, assemble `PipelineAOutput`, and generate
`structured_text_for_embedding`. HITL fields are tagged in the embedding text — not excluded.

**Input:** `IngestedDocument`, `OCRResult`, `list[ScoredField]`  
**Output:** `PipelineAOutput` → written to PostgreSQL via upsert

**Core Logic:**
```
File: pipeline_a/conflict/resolver.py

HITL triggers (any one fires hitl_required = True):
  1. Any field.status == HITL
  2. ocr_result.low_confidence == True
  3. len(scored_fields) == 0  (LLM produced nothing after all retries)
  4. Any critical field absent for this DocumentType
     e.g. prescription with no drug name field

job_status = HITL_REQUIRED if hitl_required else COMPLETED

# Include ALL fields in structured_text_for_embedding.
# Do NOT exclude HITL fields — partial data is still valuable for Pipeline B retrieval.
# Tag HITL fields so the retrieval layer can filter or down-weight them.

structured_text_for_embedding =
  f"Document type: {doc_type}\n"
  + "\n".join(
      f"{f.name}: {f.value} {f.unit} (reference: {f.reference_range})"
      if f.status == AUTO
      else f"[LOW_CONFIDENCE] {f.name}: {f.value} {f.unit}"
      for f in scored_fields
    )

# Upsert — never bare INSERT
upsert_job(db, job_id, status=job_status, hitl_required=hitl_required, ...)
upsert_fields(db, job_id, scored_fields)

Log: emit stage=conflict_resolution, job_id, hitl_required, hitl_field_count,
     total_field_count, job_status, hitl_reason_list
```

**Key Dependencies:** `sqlalchemy`, PostgreSQL

---

### Step 11 — Async Worker (Celery)

**Objective:** Run Stages 2–6 asynchronously so the API returns immediately.
Heavy processing happens in the background with crash-safe retry.

**Input:** Job parameters (job_id, patient_id, file_bytes as hex, document_type)  
**Output:** DB updated with final status.

**Core Logic:**
```
File: pipeline_a/worker/tasks.py
Delegates to: pipeline_a/orchestrator/process_document.py

@celery_app.task(bind=True, max_retries=2)
def process_document_task(self, job_id, patient_id, file_bytes_hex, document_type):
  db = SessionLocal()
  try:
    upsert_job(db, job_id, status=PROCESSING)    # idempotent — safe on retry
    output = orchestrator.run(job_id, patient_id, file_bytes_hex, document_type, db)
    upsert_result(db, output)                    # upsert — safe on retry
  except Exception as exc:
    upsert_job(db, job_id, status=FAILED, error_message=str(exc))
    raise self.retry(exc, countdown=30 * 2**self.request.retries)
  finally:
    db.close()

# tasks.py must NOT call any stage (ocr, llm, etc.) directly.
# All stage sequencing lives in orchestrator/process_document.py.

Celery config (infra/queue/celery_config.py):
  task_acks_late = True            # re-queue if worker crashes mid-task
  worker_prefetch_multiplier = 1   # one task per worker (medical data safety)
  task_serializer = "json"
  result_backend = REDIS_URL

Log: emit stage=worker, job_id, retry_count, total_pipeline_latency_ms, final_status
```

**Key Dependencies:** `celery`, `redis`

---

### Step 12 — FastAPI Layer

**Objective:** Expose three endpoints: upload (enqueue job), status poll, and HITL submission.

**Input:** HTTP requests.  
**Output:** JSON responses.

**Core Logic:**
```
File: pipeline_a/api/routes.py

POST /api/v1/documents/upload
  body: multipart (file, patient_id, document_type?)
  → validate file via pipeline_a/ingestion/loader.py
  → upsert DocumentJob(status=PENDING) in DB
  → enqueue process_document_task.delay(...)
  → return UploadResponse(job_id, status=PENDING)

GET /api/v1/documents/{job_id}/status
  → query DocumentJob by job_id
  → if COMPLETED or HITL_REQUIRED: include full PipelineAOutput
  → return JobStatusResponse

POST /api/v1/documents/{job_id}/hitl-review
  body: list of reviewed ScoredField overrides
  → upsert ReportField rows with human-verified values
  → set job status = COMPLETED
  → regenerate structured_text_for_embedding (all fields now untagged AUTO)
  → return updated PipelineAOutput
```

**Key Dependencies:** `fastapi`, `uvicorn`, `python-multipart`

---

### Step 13 — Tests

**Objective:** Validate normalization, matching, and conflict logic without requiring any API keys.

**Input:** Synthetic test fixtures.  
**Output:** Passing test suite.

**Core Logic:**
```
tests/pipeline_a/
├── test_normalization.py   → assert "hgb" → "hemoglobin", "g/dl" → "g/dL"
├── test_matching.py        → assert phrase window match("Hb 13.5 g/dL", ocr_text) >= 85
│                             assert fuzzy("Amoxcillin", "Amoxicillin") >= 85
│                             assert context embed("hemoglobin 13.5 g/dL") similarity
│                                    to embed("Hb 13.5 g/dL") > 0.85
├── test_conflict.py        → assert hitl_required=True when confidence < 0.85
│                             assert "[LOW_CONFIDENCE]" tag in embedding_text for HITL fields
│                             assert upsert on duplicate job_id does not raise or duplicate
└── fixtures/
    └── sample_lab_ocr.txt  → synthetic OCR text for testing without Vision API
```

**Key Dependencies:** `pytest`, `pytest-asyncio`

---

## 3. Critical Implementation Notes

**Field alignment is the hardest engineering problem.**  
OCR returns unstructured token soup; LLM returns structured JSON. Aligning `"Amox 500mg"` (OCR)
to `{"name": "amoxicillin", "value": "500", "unit": "mg"}` (LLM) requires the full normalization
→ phrase-window fuzzy → contextual semantic stack. Never compare raw LLM output directly against
raw OCR text. Skipping normalization before matching inflates false conflict rates by 60–70%.

**Use phrase windows for OCR matching — single tokens are insufficient.**  
Medical values appear as multi-word spans: `Hb: 13.5 g/dL`, `Amox 500mg`, `BP 120/80`.
Splitting on whitespace and comparing individual tokens loses this context. The matcher must build
sliding 2–5 word windows over the OCR text. The semantic comparison must use full field context
strings (`"hemoglobin 13.5 g/dL"`) against those phrase windows — not a bare value against a
bare token. This is the single highest-impact improvement to matching accuracy.

**Use fuzzy matching when mapping field values back to OCR words.**  
The confidence scorer must not use exact string matching to find which OCR words correspond to a
field. Formatting differences (`13.5` vs `13.50`, `Hb` vs `HB`) silently break exact matching and
cause the scorer to fall back to the 0.5 neutral value unnecessarily. Use
`rapidfuzz.fuzz.partial_ratio` with a threshold of 80 instead.

**LLM failure handling uses a retry cascade, not immediate fallback.**  
Returning `fields=[]` on the first API or parse error shifts all responsibility to the conflict
stage and unnecessarily inflates HITL load. The extractor must try three strategies before
giving up: standard prompt → stricter prompt → simplified input. Only then should it activate
regex fallback extraction. `fields=[]` is the last resort after all four approaches fail.

**HITL fields must be tagged in `structured_text_for_embedding`, not excluded.**  
Excluding HITL fields entirely loses partially-correct data that may still be valuable for
Pipeline B retrieval. Tag them with `[LOW_CONFIDENCE]` so the retrieval layer can filter or
down-weight them. After a human approves them via the HITL review endpoint, regenerate the
embedding text with all fields untagged.

**Idempotency is non-negotiable.**  
All DB writes — in the worker, the orchestrator, and the API — must use upsert on `job_id`. Add
`UNIQUE` constraints on `job_id` in `document_jobs` and on `(job_id, name)` in `report_fields`
in the migration, so the database enforces this independently of application logic. Celery retries
will re-execute the full task on worker crash; without upsert, duplicate rows are guaranteed.

**HITL is mandatory in four conditions:**  
1. Any field confidence below `FIELD_CONFIDENCE_THRESHOLD` (default 0.85)  
2. Document-level OCR confidence below `OCR_CONFIDENCE_THRESHOLD` (default 0.85)  
3. LLM extraction returns zero fields after all retry attempts  
4. A document-type-specific critical field is absent (e.g. no drug name on a prescription)  

Never allow auto-acceptance of medical data when any condition is true. A missed drug dosage or
wrong lab value is a patient safety failure, not a data quality issue.

**Celery `task_acks_late=True` is non-negotiable for medical data.**  
Without it, a worker crash between task receipt and DB write silently loses the document. With it,
the task is re-queued and retried. Set `worker_prefetch_multiplier=1` to prevent a single worker
from holding multiple in-flight tasks it cannot complete.

**Pipeline B decoupling is enforced at the DB boundary.**  
Pipeline B must never import or call any Pipeline A module directly. The only interface between
them is the `document_jobs.structured_text_for_embedding` column and the `report_fields` table.
This ensures Pipeline A can be redeployed, refactored, or scaled independently.

**Observability is a first-class requirement, not an afterthought.**  
Every stage must emit structured log fields that support production monitoring without code
changes. Logging is done via `shared/logger.py` (structlog JSON). Required fields per stage:

```
All stages:     job_id, stage, duration_ms, status (success | error)
OCR:            page_count, avg_ocr_confidence, low_confidence, ocr_latency_ms
LLM extraction: attempt_count, field_count, fallback_used, llm_latency_ms
Matching:       phrase_window_count, avg_fuzzy_score, avg_semantic_score
Confidence:     hitl_field_count, auto_field_count, avg_final_score
Conflict:       hitl_required, job_status, hitl_reason_list
Worker:         total_pipeline_latency_ms, retry_count, final_status
```

These fields enable dashboarding of: OCR latency, LLM latency, per-stage HITL rate, overall
failure rate, retry frequency, and threshold calibration signals — all essential for production
SLA monitoring.

**Medical synonym maps must be maintained actively.**  
`shared/utils/medical_dict.py` is a living artifact. Indian labs frequently use `Hb`, `TLC`,
`DLC`, `SGPT`, `SGOT` instead of international abbreviations. The map ships with ~100 entries
but will grow as new document types are onboarded. Treat it as configuration, not code.

---

## 4. Agent Checklist — Before Marking Any Step Complete

- [ ] File is at the exact path specified in the mandatory folder structure
- [ ] No stage function passes a raw `dict` to the next stage — only Pydantic models
- [ ] Every external API call (Vision, Gemini) has try/except that upserts job status on failure
- [ ] All DB writes use upsert — no bare `INSERT` anywhere
- [ ] UNIQUE constraints exist on `job_id` and `(job_id, name)` in the migration
- [ ] Stage emits structured log with `job_id`, `stage`, `duration_ms` at exit
- [ ] All observability fields from Section 3 are present in log output
- [ ] OCR matching uses phrase windows (2–5 word n-grams), not single tokens
- [ ] Semantic matching compares context strings, not bare values
- [ ] OCR word confidence mapping uses `rapidfuzz.partial_ratio`, not exact match
- [ ] LLM extractor retries 3 times before activating regex fallback
- [ ] HITL fields appear in `structured_text_for_embedding` with `[LOW_CONFIDENCE]` tag
- [ ] `shared/utils/medical_dict.py` is the only source of synonym maps — no inline dicts
- [ ] `worker/tasks.py` calls only `orchestrator.run()` — no direct stage calls
- [ ] `pipeline_b/` is empty — no files were added there
- [ ] Every directory has an `__init__.py`
