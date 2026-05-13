# HDIMS Pipeline B — Implementation Blueprint
### Clinical Retrieval, Reasoning & Analytics Layer

---

## AGENT INSTRUCTIONS — READ BEFORE WRITING ANY CODE

> This document is the authoritative specification for Pipeline B of the HDIMS system.
> Pipeline A is already built and tested. Pipeline B consumes its output exclusively
> through the adapter layer and the PostgreSQL database.
> You are a coding agent. Before generating any file, internalize and strictly follow
> every rule in this section. Do not deviate from folder structure, file names,
> or code patterns defined here.

### Non-Negotiable Rules

1. **Pipeline B never imports Pipeline A code.** The only interface is PostgreSQL (`document_jobs` + `report_fields`) accessed through the adapter layer.
2. **LLM never queries the database directly.** No LangChain SQL agent. No direct DB access from any LLM call. Python executes all queries; LLM only receives results.
3. **Numeric computations are never done by LLM.** Trend direction, percent change, threshold comparisons — all Python. LLM only explains the result.
4. **All outputs are typed Pydantic models.** No raw strings returned from any engine or service.
5. **Doctor and patient system prompts are completely separate constants.** No shared templates. No f-string switching between them. Separate generator functions.
6. **Field names must use canonical form everywhere.** `shared/utils/medical_dict.py` is the single source of truth. Qdrant payloads, SQL queries, and adapter output must all use canonical names.
7. **LangChain is used ONLY for:** LLM orchestration, prompt management, output parsing, future PubMed RAG chains. LangChain is NOT used for DB querying, routing, or business logic.

### Data Source Routing Rules (enforced in code)

| Query type | Data source | Reason |
|---|---|---|
| Numeric filters (`hb < 11`) | PostgreSQL via adapter | Exact, reliable |
| Semantic search | Qdrant vector search | Similarity-based |
| Trend / time series | Qdrant scroll by patient+field | Ordered history |
| Full patient history | Adapter (SQL) | Complete record |
| Retrieval intent parsing | LLM (intent only, not DB) | Natural language |
| Numeric computation | Python only | LLM hallucinates math |

---

### Mandatory Folder Structure

```
HDIMS/
│
├── shared/                          → Already exists — do NOT modify
│
├── pipeline_a/                      → Already exists — do NOT modify
│
├── pipeline_b/
│   │
│   ├── adapters/
│   │   ├── __init__.py
│   │   └── pipeline_a_adapter.py
│   │       → ONLY place that reads document_jobs + report_fields
│   │       → Normalizes into canonical PipelineBInput contract
│   │       → parse_reference_range, compute_is_abnormal
│   │       → get_patient_record, get_all_records_for_patient
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── input.py
│   │   │   → ClinicalField (canonical field with all metadata)
│   │   │   → PatientRecord (job metadata + list[ClinicalField])
│   │   │
│   │   ├── query.py
│   │   │   → QueryType enum: retrieval | reasoning | trend | patient_chat
│   │   │   → PersonaType enum: doctor | patient
│   │   │   → UserQuery, ClassifiedQuery, ParsedFilter
│   │   │
│   │   └── output.py
│   │       → RetrievalResult, ReasoningResult, TrendResult
│   │       → PatientChatResult, AnalyticsResult
│   │       → TrendPoint, ChartJSON, CachedResponse
│   │
│   ├── engines/
│   │   ├── __init__.py
│   │   ├── query_classifier.py
│   │   │   → Hybrid: rules → embedding → GPT-4o fallback
│   │   │   → classify(query, persona) → ClassifiedQuery
│   │   │   → Logs: classification_method, confidence
│   │   │
│   │   ├── intent_parser.py
│   │   │   → LLM-based intent extraction for retrieval queries
│   │   │   → parse_retrieval_intent(query) → ParsedFilter
│   │   │   → "low hemoglobin" → {field: hemoglobin, op: lt, val: 11.5}
│   │   │
│   │   ├── retriever.py
│   │   │   → retrieve_by_filter(ParsedFilter) → list[ClinicalField]
│   │   │   → retrieve_semantic(query_vec, filters) → list[ClinicalField]
│   │   │   → retrieve_for_patient(patient_id, db) → list[PatientRecord]
│   │   │
│   │   ├── generator.py
│   │   │   → LangChain-based GPT-4o wrapper
│   │   │   → generate_doctor_reasoning(context, query) → ReasoningResult
│   │   │   → generate_patient_explanation(context, query) → PatientChatResult
│   │   │   → Separate LangChain chains for doctor vs patient
│   │   │   → Logs: llm_latency_ms, fallback_used
│   │   │
│   │   └── trend_analyzer.py
│   │       → extract_time_series(patient_id, field_name) → list[TrendPoint]
│   │       → compute_trend(points) → dict  [PYTHON ONLY]
│   │       → build_chart_json(field, unit, points) → ChartJSON
│   │       → analyze_trend(patient_id, field_name) → TrendResult
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── retrieval_service.py
│   │   │   → handle_retrieval_query(query, db) → RetrievalResult
│   │   │   → Uses intent_parser + retriever
│   │   │   → Logs: retrieval_type (filter|semantic), result_count
│   │   │
│   │   ├── reasoning_service.py
│   │   │   → handle_reasoning_query(query, patient_id, db) → ReasoningResult
│   │   │   → Uses adapter + retriever + generator
│   │   │   → Context size capped at 15 fields (abnormal-first priority)
│   │   │   → Logs: context_field_count, llm_latency_ms
│   │   │
│   │   ├── trend_service.py
│   │   │   → handle_trend_query(query, patient_id, db) → TrendResult
│   │   │   → Uses trend_analyzer + generator
│   │   │   → Logs: data_points_count, trend_direction
│   │   │
│   │   ├── patient_service.py
│   │   │   → handle_patient_query(query, patient_id, db) → PatientChatResult
│   │   │   → Safety check (BLOCKED_TERMS) runs first
│   │   │   → patient_id filter always applied
│   │   │   → Logs: safety_blocked (bool), llm_latency_ms
│   │   │
│   │   └── analytics_service.py
│   │       → get_patient_analytics(patient_id, db) → AnalyticsResult
│   │       → Abnormality detection in Python
│   │       → Chart JSON built in Python
│   │       → AI insight from GPT-4o (abnormal fields only)
│   │       → Logs: abnormal_count, normal_count
│   │
│   ├── cache/
│   │   ├── __init__.py
│   │   └── response_cache.py
│   │       → Hash-based cache: hash(query + patient_id + query_type)
│   │       → get_cached(cache_key) → CachedResponse | None
│   │       → set_cache(cache_key, result, ttl_seconds)
│   │       → In-memory dict for MVP (Redis-ready interface)
│   │
│   ├── vector_db/
│   │   ├── __init__.py
│   │   └── qdrant_client.py
│   │       → get_client() → QdrantClient (local persistent)
│   │       → ensure_collections_exist()
│   │       → upsert_chunks(chunks) — idempotent
│   │       → search_fields(query_vector, filters) → list[ScoredPoint]
│   │       → get_patient_field_history(patient_id, field_name) → list[dict]
│   │
│   ├── chunking/
│   │   ├── __init__.py
│   │   └── chunker.py
│   │       → chunk_per_field(record) → list[QdrantChunk]
│   │       → chunk_full_document(record) → QdrantChunk
│   │       → chunk_record(record) → list[QdrantChunk]
│   │
│   ├── embedding/
│   │   ├── __init__.py
│   │   └── embedder.py
│   │       → _get_model() — singleton, reuses cached all-MiniLM-L6-v2
│   │       → embed(texts: list[str]) → list[list[float]]
│   │       → embed_single(text: str) → list[float]
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── ingest.py
│   │       → ingest_patient_record(patient_id, job_id, db)
│   │       → ingest_all_existing(db)
│   │       → Called after each Pipeline A job completes
│   │
│   └── api/
│       ├── __init__.py
│       ├── doctor_routes.py
│       │   → POST /api/doctor/query
│       │   → GET  /api/doctor/patient/{patient_id}/summary
│       │   → GET  /api/doctor/patient/{patient_id}/trend
│       │   → GET  /api/doctor/analytics
│       │
│       └── patient_routes.py
│           → POST /api/patient/query
│           → GET  /api/patient/records
│           → GET  /api/patient/report/{job_id}/explain
│
├── tests/
│   └── pipeline_b/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_adapter.py
│       ├── test_classifier.py
│       ├── test_intent_parser.py
│       ├── test_retrieval_service.py
│       ├── test_reasoning_service.py
│       ├── test_trend_service.py
│       ├── test_cache.py
│       └── fixtures/
│           └── sample_pipeline_a_output.json
│
└── dashboard/
    ├── index.html       → Doctor dashboard (Chart.js)
    └── patient.html     → Patient view (simplified)
```

### File Placement Rules

- `pipeline_b/adapters/` is the ONLY place that reads `document_jobs` or `report_fields` directly.
- `pipeline_b/engines/` contains stateless components. They know nothing about doctor vs patient.
- `pipeline_b/services/` orchestrates engines per query type. They own business logic.
- `pipeline_b/cache/` handles response caching. All services must check cache before calling LLM.
- `pipeline_b/api/` handles HTTP only — validation, routing, response formatting.
- `dashboard/` is pure static HTML. No build step. No npm.
- Every directory must have `__init__.py`. Create them all during scaffolding.

---

## 1. System Overview

Pipeline B is a read-time clinical intelligence layer that makes Pipeline A's structured output queryable, interpretable, and analyzable through natural language. It serves two distinct personas — doctors (clinical mode) and patients (safe, simplified mode) — through completely separate API routers backed by shared stateless engines.

**The Adapter Pattern** is the contract boundary. All Pipeline A output is normalized into `PatientRecord` and `ClinicalField` before any engine touches it. If Pipeline A changes, only the adapter changes.

**The Intent Parser** solves the messy query problem. Natural language like `"low hemoglobin"`, `"hb below normal"`, or `"anemia patients"` cannot be reliably parsed by regex. A small, focused LLM call extracts structured filter intent — this does NOT violate the no-LLM-to-DB rule because the LLM only produces a filter spec, Python executes the actual query.

**The Hybrid Classifier** routes queries using rules first (free, fast), then embedding similarity (medium cost), then GPT-4o fallback (rare). Classification method is always logged to monitor fallback rate.

**The Cache Layer** prevents redundant GPT-4o calls. Reasoning results and trend insights are cached by `hash(query + patient_id + query_type)`. Cache is in-memory for MVP with a Redis-compatible interface for later upgrade.

---

## 2. Pydantic Schema Contracts

### pipeline_b/schemas/input.py

```python
from pydantic import BaseModel
from datetime import datetime

class ClinicalField(BaseModel):
    # Identity
    field_id: str                   # f"{job_id}_{name}"
    job_id: str
    patient_id: str
    document_type: str
    collection_date: str | None
    processed_at: datetime

    # Canonical field data
    name: str                       # canonical: "hemoglobin" not "hb%"
    raw_name: str                   # original: "hb%"
    value: str
    numeric_value: float | None     # None if non-numeric ("Not Found")
    unit: str | None
    reference_range: str | None
    ref_low: float | None           # parsed from reference_range
    ref_high: float | None

    # Quality
    confidence: float
    status: str                     # "auto" | "hitl"
    is_abnormal: bool | None        # None if cannot determine

    # Source (Phase 3: "literature" added)
    source_type: str = "patient"

class PatientRecord(BaseModel):
    patient_id: str
    job_id: str
    document_type: str
    processed_at: datetime
    hitl_required: bool
    structured_text: str            # structured_text_for_embedding
    fields: list[ClinicalField]
```

### pipeline_b/schemas/query.py

```python
from enum import Enum
from pydantic import BaseModel

class QueryType(str, Enum):
    retrieval = "retrieval"
    reasoning = "reasoning"
    trend = "trend"
    patient_chat = "patient_chat"

class PersonaType(str, Enum):
    doctor = "doctor"
    patient = "patient"

class UserQuery(BaseModel):
    text: str
    persona: PersonaType
    patient_id: str | None = None
    filters: dict | None = None

class ClassifiedQuery(UserQuery):
    query_type: QueryType
    confidence: float
    classification_method: str      # "rule" | "embedding" | "llm"

class ParsedFilter(BaseModel):
    """Output of intent_parser — structured retrieval intent."""
    field_name: str                 # canonical name
    operator: str                   # "lt" | "gt" | "eq" | "lte" | "gte" | "any"
    value: float | None             # None if operator is "any" (find all records)
    raw_query: str                  # original query for logging
    confidence: float
```

### pipeline_b/schemas/output.py

```python
from pydantic import BaseModel

class TrendPoint(BaseModel):
    date: str
    value: str
    numeric_value: float | None
    unit: str | None
    is_abnormal: bool | None

class ChartJSON(BaseModel):
    type: str                       # "line_chart" | "bar_chart"
    data: dict                      # {x: [...], y: [...]} or bar format
    meta: dict                      # {label, unit, ref_low, ref_high}

class RetrievalResult(BaseModel):
    records: list[dict]             # simplified — no clinical internals
    total_count: int
    query_interpretation: str
    retrieval_type: str             # "filter" | "semantic"

class ReasoningResult(BaseModel):
    interpretation: str
    clinical_significance: str
    possible_conditions: list[str]
    critical_flags: list[str]
    confidence: float
    citations: list[str]            # [] for Phase 2, PubMed refs in Phase 3
    data_used: list[ClinicalField]
    cached: bool = False

class TrendResult(BaseModel):
    field_name: str
    patient_id: str
    data_points: list[TrendPoint]
    trend_direction: str            # "increasing"|"decreasing"|"stable"|"insufficient_data"
    percent_change: float | None
    chart_json: ChartJSON
    insight: str                    # GPT-4o explanation
    cached: bool = False

class PatientChatResult(BaseModel):
    response: str
    simplified_fields: list[dict]   # {name, value, plain_english_status}
    disclaimer: str                 # ALWAYS required — never optional
    safety_blocked: bool = False

class AnalyticsResult(BaseModel):
    patient_id: str
    abnormal_fields: list[ClinicalField]
    normal_fields: list[ClinicalField]
    abnormal_count: int
    normal_count: int
    chart_json: ChartJSON
    ai_insight: str
    cached: bool = False

class CachedResponse(BaseModel):
    cache_key: str
    result: dict                    # serialized result
    created_at: datetime
    query_type: str
```

---

## 3. Adapter Layer (Critical — Read First)

### pipeline_b/adapters/pipeline_a_adapter.py

```python
import re
from datetime import datetime
from sqlalchemy.orm import Session
from shared.utils.medical_dict import MEDICAL_SYNONYMS
from pipeline_b.schemas.input import ClinicalField, PatientRecord

def parse_reference_range(ref_str: str | None) -> tuple[float | None, float | None]:
    """
    Handles all formats seen in Indian lab reports:
      "11.5 - 16.4 gm/dl"       → (11.5, 16.4)
      "FEMALE: 11.5 - 16.4"     → (11.5, 16.4)  ← strip prefix
      "3.00 - 5.50"             → (3.0, 5.5)
      "4000-11,000"             → (4000.0, 11000.0)  ← remove commas
      "50-70"                   → (50.0, 70.0)
      "Male 42 52%"             → (42.0, 52.0)  ← space separator
      "0 - 1"                   → (0.0, 1.0)
      "Not Found" | None        → (None, None)

    Algorithm:
      1. Return (None, None) if ref_str is None or non-numeric keywords
      2. Remove commas from numbers (Indian format)
      3. Apply regex: r"([\d]+\.?\d*)\s*[-–\s]\s*([\d]+\.?\d*)"
      4. Parse first two matches as float low, float high
    """

def normalize_field_name(raw_name: str) -> str:
    """
    Import MEDICAL_SYNONYMS from shared.utils.medical_dict.
    Apply same logic as Pipeline A normalizer.
    raw_name.strip().lower() → MEDICAL_SYNONYMS.get(cleaned, cleaned)
    This ensures Qdrant, SQL, and adapter all use identical canonical names.
    """

def compute_is_abnormal(
    numeric_value: float | None,
    ref_low: float | None,
    ref_high: float | None
) -> bool | None:
    """
    Returns:
      True  if numeric_value < ref_low OR numeric_value > ref_high
      False if ref_low <= numeric_value <= ref_high
      None  if any value is None (cannot determine)
    """

def build_clinical_field(row, job_row) -> ClinicalField:
    """
    row     = report_fields ORM row or dict
    job_row = document_jobs ORM row or dict

    Steps:
      1. raw_name = row.name
      2. name = normalize_field_name(raw_name)
      3. numeric_value = float(row.value) if parseable else None
      4. ref_low, ref_high = parse_reference_range(row.reference_range)
      5. is_abnormal = compute_is_abnormal(numeric_value, ref_low, ref_high)
      6. source_type = "patient" (always)
      7. field_id = f"{row.job_id}_{name}"
    """

def get_patient_record(patient_id: str, job_id: str, db: Session) -> PatientRecord | None:
    """
    SELECT * FROM document_jobs WHERE job_id = :job_id AND patient_id = :patient_id
    SELECT * FROM report_fields WHERE job_id = :job_id ORDER BY name
    Build and return PatientRecord. Return None if not found.
    """

def get_all_records_for_patient(patient_id: str, db: Session) -> list[PatientRecord]:
    """
    SELECT * FROM document_jobs
    WHERE patient_id = :patient_id
      AND status IN ('completed', 'hitl_required')
    ORDER BY processed_at ASC

    For each job_id: get all report_fields rows.
    Return list[PatientRecord] sorted oldest → newest.
    """

def get_latest_record(patient_id: str, db: Session) -> PatientRecord | None:
    """Most recent processed document. Returns None if no records."""
```

---

## 4. Qdrant Schema (Fixed — Never Change)

```python
# Every point stored in HDMIS_fields must have this exact payload structure.
# Source_type field enables Phase 3 PubMed chunks in the same collection.

FIELD_CHUNK_PAYLOAD = {
    # Source
    "source_type": "patient",          # patient | literature (Phase 3)
    "chunk_type": "field",             # field | document

    # Patient context
    "patient_id": str,
    "job_id": str,
    "document_type": str,
    "collection_date": str | None,
    "processed_at": str,               # ISO format

    # Field data
    "field_name": str,                 # CANONICAL name — always
    "raw_name": str,
    "value": str,
    "numeric_value": float | None,
    "unit": str | None,
    "reference_range": str | None,
    "ref_low": float | None,
    "ref_high": float | None,
    "is_abnormal": bool | None,
    "confidence": float,

    # Embedded text
    "chunk_text": str,
    # format: "{field_name} {value} {unit} reference {ref_low}-{ref_high} status {normal|abnormal}"
    # e.g.: "hemoglobin 10.5 g/dL reference 11.5-16.4 status abnormal"
}

# chunk_id = deterministic hash of f"field_{job_id}_{field_name}"
# Same document re-ingested always produces same chunk_id → idempotent upsert
```

Collections:
- `HDMIS_fields` — one vector per field per document
- `HDMIS_documents` — one vector per full document (structured_text)

---

## 5. Caching Strategy

```python
# pipeline_b/cache/response_cache.py

import hashlib, json
from datetime import datetime, timedelta
from pipeline_b.schemas.output import CachedResponse

_cache: dict[str, CachedResponse] = {}   # In-memory MVP

TTL = {
    "reasoning": 3600,      # 1 hour — clinical interpretations are stable
    "trend": 1800,          # 30 min — trends change only with new reports
    "retrieval": 300,       # 5 min — retrieval results can change quickly
    "patient_chat": 1800,   # 30 min
    "analytics": 1800,
}

def make_cache_key(query: str, patient_id: str | None, query_type: str) -> str:
    """
    key_string = f"{query.strip().lower()}|{patient_id or 'none'}|{query_type}"
    return hashlib.sha256(key_string.encode()).hexdigest()[:16]
    """

def get_cached(cache_key: str) -> dict | None:
    """Return cached result if exists and not expired. Else None."""

def set_cache(cache_key: str, result: dict, query_type: str):
    """Store with TTL from TTL dict. Serialize result to dict."""

def invalidate_patient(patient_id: str):
    """
    Clear all cached entries for a patient.
    Called when a new Pipeline A job completes for that patient.
    """
```

All services must follow this pattern:
```python
# In every service.handle_*() function:
cache_key = make_cache_key(query.text, query.patient_id, query.query_type)
cached = get_cached(cache_key)
if cached:
    return ResultModel(**cached, cached=True)

result = _compute_result(...)       # actual work
set_cache(cache_key, result.dict(), query.query_type.value)
return result
```

---

## 6. Step-by-Step Build Process

---

### Step 1 — Scaffold + Schemas

**Objective:** Create complete folder structure, all `__init__.py` files, and all Pydantic schema files.

**Core Logic:**
```
Create every directory in the mandatory folder structure.
Create __init__.py in every directory — do not defer.

Implement:
  pipeline_b/schemas/input.py   → ClinicalField, PatientRecord
  pipeline_b/schemas/query.py   → QueryType, PersonaType, UserQuery,
                                   ClassifiedQuery, ParsedFilter
  pipeline_b/schemas/output.py  → All result models + TrendPoint,
                                   ChartJSON, CachedResponse

DO NOT implement any business logic in this step.
```

**Key Dependencies:** `pydantic==2.x` (already installed)

---

### Step 2 — Adapter Layer

**Objective:** Implement `pipeline_a_adapter.py` — the contract boundary.

**Input:** PostgreSQL rows from `document_jobs` + `report_fields`
**Output:** `PatientRecord` objects with fully computed `ClinicalField` list

**Core Logic:** See Section 3 above. Implement all 6 functions exactly as specified.

**Verification:**
```bash
venvHDIMS/bin/python -c "
import sys; sys.path.insert(0, '.')
from shared.db.session import SessionLocal
from pipeline_b.adapters.pipeline_a_adapter import (
    get_all_records_for_patient, parse_reference_range, compute_is_abnormal
)

# Test parse_reference_range
assert parse_reference_range('11.5 - 16.4 gm/dl') == (11.5, 16.4)
assert parse_reference_range('FEMALE: 11.5 - 16.4') == (11.5, 16.4)
assert parse_reference_range('4000-11,000') == (4000.0, 11000.0)
assert parse_reference_range('50-70') == (50.0, 70.0)
assert parse_reference_range(None) == (None, None)
print('✅ parse_reference_range: all formats')

# Test compute_is_abnormal
assert compute_is_abnormal(10.5, 11.5, 16.4) == True    # below range
assert compute_is_abnormal(13.5, 11.5, 16.4) == False   # in range
assert compute_is_abnormal(None, 11.5, 16.4) == None    # unknown
print('✅ compute_is_abnormal: all cases')

# Test full adapter with real DB
db = SessionLocal()
records = get_all_records_for_patient('test-patient-001', db)
db.close()
assert len(records) >= 1
f = records[0].fields[0]
assert f.source_type == 'patient'
assert f.name == f.name.lower()       # canonical name
print(f'✅ Adapter: {len(records)} records, {len(records[0].fields)} fields')
print(f'   Sample: {f.name} = {f.value} {f.unit} abnormal={f.is_abnormal}')
"
```

**Key Dependencies:** `sqlalchemy` (already installed), `shared.utils.medical_dict`

---

### Step 3 — Embedder

**Objective:** Implement `embedder.py` reusing the already-cached `all-MiniLM-L6-v2` model.

**Core Logic:**
```python
# pipeline_b/embedding/embedder.py

from sentence_transformers import SentenceTransformer
import numpy as np

_model = None

def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return [v.tolist() for v in vectors]

def embed_single(text: str) -> list[float]:
    return embed([text])[0]
```

**Key Dependencies:** `sentence-transformers` (already installed)

---

### Step 4 — Chunker

**Objective:** Convert `PatientRecord` into Qdrant-ready chunks with full metadata payload.

**Core Logic:**
```python
# pipeline_b/chunking/chunker.py

from dataclasses import dataclass

@dataclass
class QdrantChunk:
    chunk_id: str
    chunk_text: str
    payload: dict

def _make_chunk_id(job_id: str, field_name: str) -> str:
    """Deterministic — same input always same ID."""
    import hashlib
    raw = f"field_{job_id}_{field_name}"
    return str(int(hashlib.sha256(raw.encode()).hexdigest()[:15], 16))

def chunk_per_field(record: PatientRecord) -> list[QdrantChunk]:
    chunks = []
    for f in record.fields:
        status = "abnormal" if f.is_abnormal else "normal" if f.is_abnormal is False else "unknown"
        ref_part = f"{f.ref_low}-{f.ref_high}" if f.ref_low and f.ref_high else "unknown"
        chunk_text = (
            f"{f.name} {f.value} {f.unit or ''} "
            f"reference {ref_part} status {status}"
        ).strip()

        payload = {
            "source_type": f.source_type,   # "patient"
            "chunk_type": "field",
            "patient_id": f.patient_id,
            "job_id": f.job_id,
            "document_type": f.document_type,
            "collection_date": f.collection_date,
            "processed_at": f.processed_at.isoformat(),
            "field_name": f.name,           # CANONICAL
            "raw_name": f.raw_name,
            "value": f.value,
            "numeric_value": f.numeric_value,
            "unit": f.unit,
            "reference_range": f.reference_range,
            "ref_low": f.ref_low,
            "ref_high": f.ref_high,
            "is_abnormal": f.is_abnormal,
            "confidence": f.confidence,
            "chunk_text": chunk_text,
        }
        chunks.append(QdrantChunk(
            chunk_id=_make_chunk_id(f.job_id, f.name),
            chunk_text=chunk_text,
            payload=payload,
        ))
    return chunks

def chunk_full_document(record: PatientRecord) -> QdrantChunk:
    import hashlib
    chunk_id = str(int(hashlib.sha256(f"doc_{record.job_id}".encode()).hexdigest()[:15], 16))
    payload = {
        "source_type": "patient",
        "chunk_type": "document",
        "patient_id": record.patient_id,
        "job_id": record.job_id,
        "document_type": record.document_type,
        "processed_at": record.processed_at.isoformat(),
        "chunk_text": record.structured_text,
    }
    return QdrantChunk(chunk_id=chunk_id, chunk_text=record.structured_text, payload=payload)

def chunk_record(record: PatientRecord) -> list[QdrantChunk]:
    return chunk_per_field(record) + [chunk_full_document(record)]
```

---

### Step 5 — Qdrant Client

**Objective:** Local persistent Qdrant storage with full metadata filtering.

**Core Logic:**
```python
# pipeline_b/vector_db/qdrant_client.py

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue, Range,
    ScrollRequest
)
from shared.config import get_settings

COLLECTIONS = {"fields": "HDMIS_fields", "documents": "HDMIS_documents"}
VECTOR_SIZE = 384

def get_client() -> QdrantClient:
    settings = get_settings()
    if hasattr(settings, 'QDRANT_URL') and settings.QDRANT_URL:
        return QdrantClient(url=settings.QDRANT_URL)
    return QdrantClient(path="./qdrant_storage")   # local persistent

def ensure_collections_exist():
    client = get_client()
    for name in COLLECTIONS.values():
        if not client.collection_exists(name):
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
            )

def upsert_chunks(chunks: list, vectors: list[list[float]], collection: str):
    """
    chunks: list[QdrantChunk]
    vectors: list[list[float]] — pre-computed by embedder
    Idempotent: chunk_id is deterministic, upsert overwrites existing.
    """
    client = get_client()
    points = [
        PointStruct(id=int(chunk.chunk_id), vector=vec, payload=chunk.payload)
        for chunk, vec in zip(chunks, vectors)
    ]
    client.upsert(collection_name=collection, points=points)

def search_fields(
    query_vector: list[float],
    top_k: int = 10,
    patient_id: str | None = None,
    document_type: str | None = None,
    source_type: str = "patient",
    is_abnormal: bool | None = None,
    field_name: str | None = None,
    numeric_value_lt: float | None = None,
    numeric_value_gt: float | None = None,
) -> list:
    """
    Build Filter from non-None params.
    search HDMIS_fields.
    Return top_k ScoredPoint results.
    """

def get_patient_field_history(patient_id: str, field_name: str) -> list[dict]:
    """
    Scroll HDMIS_fields (not search — we want ALL records not just similar).
    Filter: patient_id == patient_id AND field_name == field_name
    Order by collection_date ASC (in Python after scroll).
    Return list of payload dicts.
    """
```

**Add to shared/config.py:**
```python
QDRANT_URL: str | None = None       # None = use local persistent storage
QDRANT_STORAGE_PATH: str = "./qdrant_storage"
```

**Key Dependencies:** `qdrant-client` (add to requirements.txt)

---

### Step 6 — Ingestion Pipeline

**Objective:** Populate Qdrant from existing Pipeline A records. Run once, then incrementally.

**Core Logic:**
```python
# pipeline_b/ingestion/ingest.py

from shared.logger import get_logger
from pipeline_b.adapters.pipeline_a_adapter import get_patient_record, get_all_records_for_patient
from pipeline_b.chunking.chunker import chunk_record
from pipeline_b.embedding.embedder import embed
from pipeline_b.vector_db.qdrant_client import upsert_chunks, ensure_collections_exist
from pipeline_b.cache.response_cache import invalidate_patient

logger = get_logger(__name__)

def ingest_patient_record(patient_id: str, job_id: str, db):
    t_start = time.time()
    ensure_collections_exist()

    record = get_patient_record(patient_id, job_id, db)
    if not record:
        logger.warning("record_not_found", job_id=job_id, patient_id=patient_id)
        return

    chunks = chunk_record(record)
    texts = [c.chunk_text for c in chunks]
    vectors = embed(texts)

    field_chunks = [c for c in chunks if c.payload["chunk_type"] == "field"]
    doc_chunks = [c for c in chunks if c.payload["chunk_type"] == "document"]
    field_vecs = vectors[:len(field_chunks)]
    doc_vecs = vectors[len(field_chunks):]

    upsert_chunks(field_chunks, field_vecs, "HDMIS_fields")
    upsert_chunks(doc_chunks, doc_vecs, "HDMIS_documents")

    invalidate_patient(patient_id)    # clear stale cache

    logger.info("ingestion_complete",
                job_id=job_id, patient_id=patient_id,
                field_chunks=len(field_chunks),
                duration_ms=round((time.time()-t_start)*1000, 2))

def ingest_all_existing(db):
    """Run once to backfill all existing Pipeline A records."""
    from sqlalchemy import text
    rows = db.execute(text(
        "SELECT job_id, patient_id FROM document_jobs "
        "WHERE status IN ('completed', 'hitl_required')"
    )).fetchall()
    for row in rows:
        ingest_patient_record(row.patient_id, row.job_id, db)
```

---

### Step 7 — Query Classifier

**Objective:** Hybrid classifier: rules → embedding similarity → GPT-4o fallback.

**Core Logic:**
```python
# pipeline_b/engines/query_classifier.py

from pipeline_b.schemas.query import QueryType, PersonaType, ClassifiedQuery
from pipeline_b.embedding.embedder import embed_single
from shared.logger import get_logger

logger = get_logger(__name__)

RULES: dict[QueryType, list[str]] = {
    QueryType.trend: [
        "trend", "over time", "last 3", "changed", "history",
        "previous", "comparison", "improving", "worsening",
        "getting better", "getting worse", "across visits"
    ],
    QueryType.retrieval: [
        "show me", "find", "list", "which patients", "all patients",
        "who has", "records for", "reports for", "patients with"
    ],
    QueryType.reasoning: [
        "is this normal", "what does", "interpret", "explain",
        "significance", "suggest", "indicate", "abnormal",
        "what is", "why is", "clinical", "diagnosis", "concern"
    ],
    QueryType.patient_chat: [
        "what is my", "am i", "should i", "my report",
        "my result", "my test", "my blood", "understand my"
    ]
}

EXAMPLE_QUERIES: dict[QueryType, list[str]] = {
    QueryType.retrieval: [
        "show me all patients with low hemoglobin",
        "find patients with platelet count below 150",
        "list all lab reports from october 2025",
        "which patients have abnormal ESR",
    ],
    QueryType.reasoning: [
        "is this CBC result normal for a 50 year old female",
        "what does elevated ESR with low hemoglobin indicate",
        "interpret these lab values for me",
        "explain the clinical significance of these findings",
    ],
    QueryType.trend: [
        "how has hemoglobin changed over the last 3 visits",
        "show me the trend for platelet count",
        "is the ESR improving over time",
        "hemoglobin history for this patient",
    ],
    QueryType.patient_chat: [
        "what does my hemoglobin result mean",
        "is my blood test normal",
        "can you explain my report in simple language",
        "what does low hemoglobin mean for me",
    ]
}

# Pre-embed example queries at module load (not per request)
_example_embeddings: dict[QueryType, list[list[float]]] | None = None

def _get_example_embeddings() -> dict[QueryType, list[list[float]]]:
    global _example_embeddings
    if _example_embeddings is None:
        _example_embeddings = {
            qt: [embed_single(q) for q in queries]
            for qt, queries in EXAMPLE_QUERIES.items()
        }
    return _example_embeddings

def _embedding_classify(query_vec: list[float]) -> tuple[QueryType, float]:
    """Compare query against pre-embedded examples. Return best type + score."""
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    examples = _get_example_embeddings()
    best_type, best_score = QueryType.reasoning, 0.0
    for qt, vecs in examples.items():
        scores = cosine_similarity([query_vec], vecs)[0]
        score = float(np.max(scores))
        if score > best_score:
            best_score = score
            best_type = qt
    return best_type, best_score

def _llm_classify(query: str, persona: PersonaType) -> ClassifiedQuery:
    """GPT-4o fallback — only fires when rules + embedding both inconclusive."""
    from openai import OpenAI
    from shared.config import get_settings
    client = OpenAI(api_key=get_settings().OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "system",
            "content": (
                "Classify this medical query into exactly one of: "
                "retrieval, reasoning, trend, patient_chat. "
                "Return JSON: {\"type\": \"...\", \"confidence\": 0.0}"
            )
        }, {"role": "user", "content": query}],
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    import json
    result = json.loads(response.choices[0].message.content)
    return ClassifiedQuery(
        text=query, persona=persona,
        query_type=QueryType(result["type"]),
        confidence=result["confidence"],
        classification_method="llm"
    )

def classify(query: str, persona: PersonaType) -> ClassifiedQuery:
    query_lower = query.lower()
    t_start = time.time()

    # Step 1: Rule match (requires >= 2 keyword hits to avoid false positives)
    scores = {qt: sum(1 for kw in kws if kw in query_lower)
              for qt, kws in RULES.items()}
    best_rule = max(scores, key=scores.get)
    if scores[best_rule] >= 2:
        result = ClassifiedQuery(
            text=query, persona=persona,
            query_type=best_rule,
            confidence=min(scores[best_rule] / 4.0, 1.0),
            classification_method="rule"
        )
        logger.info("query_classified", method="rule", type=best_rule.value,
                    confidence=result.confidence,
                    duration_ms=round((time.time()-t_start)*1000, 2))
        return result

    # Step 2: Embedding similarity
    query_vec = embed_single(query)
    emb_type, emb_score = _embedding_classify(query_vec)
    if emb_score >= 0.70:
        result = ClassifiedQuery(
            text=query, persona=persona,
            query_type=emb_type,
            confidence=emb_score,
            classification_method="embedding"
        )
        logger.info("query_classified", method="embedding", type=emb_type.value,
                    confidence=emb_score,
                    duration_ms=round((time.time()-t_start)*1000, 2))
        return result

    # Step 3: GPT-4o fallback (log this — if > 10% of queries, expand rules)
    logger.warning("classifier_fallback_to_llm", query=query[:100],
                   rule_score=scores[best_rule], emb_score=emb_score)
    result = _llm_classify(query, persona)
    logger.info("query_classified", method="llm", type=result.query_type.value,
                confidence=result.confidence,
                duration_ms=round((time.time()-t_start)*1000, 2))
    return result
```

---

### Step 8 — Intent Parser

**Objective:** Extract structured filter intent from messy natural language retrieval queries.

**Core Logic:**
```python
# pipeline_b/engines/intent_parser.py

# This solves the messy query problem:
# "low hemoglobin"      → {field: hemoglobin, op: lt, val: ref_low}
# "hb below normal"     → {field: hemoglobin, op: lt, val: 11.5}
# "anemia patients"     → {field: hemoglobin, op: lt, val: 11.5}
# "hemoglobin < 11"     → {field: hemoglobin, op: lt, val: 11.0}
# "platelet count low"  → {field: platelet count, op: lt, val: ref_low}

INTENT_SYSTEM_PROMPT = """
You are a medical query intent parser.
Extract the retrieval filter from the query.

Return JSON:
{
  "field_name": "canonical field name (lowercase)",
  "operator": "lt | gt | eq | lte | gte | any",
  "value": number or null,
  "confidence": 0.0-1.0
}

Rules:
- Use canonical field names: hemoglobin, platelet count, neutrophil, etc.
- "low" / "below normal" / "anemia" → operator: lt, value: reference low
  For hemoglobin: female ref low = 11.5, male = 13.5 → use 11.5 (conservative)
- "high" / "elevated" / "above normal" → operator: gt, value: reference high
- If no threshold implied → operator: any, value: null
- Do NOT query the database — only extract intent.
"""

def parse_retrieval_intent(query: str) -> ParsedFilter:
    """
    Call GPT-4o with INTENT_SYSTEM_PROMPT.
    temperature=0.0, response_format=json_object.
    Normalize field_name using MEDICAL_SYNONYMS.
    Return ParsedFilter.
    """

def _normalize_parsed_field(raw: str) -> str:
    """Apply MEDICAL_SYNONYMS to LLM-returned field name."""
    from shared.utils.medical_dict import MEDICAL_SYNONYMS
    return MEDICAL_SYNONYMS.get(raw.strip().lower(), raw.strip().lower())
```

---

### Step 9 — Retriever Engine + Service

**Core Logic:**
```python
# pipeline_b/engines/retriever.py

def retrieve_by_filter(parsed: ParsedFilter) -> list[dict]:
    """
    Use Qdrant payload filter — NOT semantic search.
    Build numeric range filter from parsed.operator + parsed.value.
    Filter on field_name (canonical) + source_type=patient.
    Return list of payload dicts from matching points.
    Log: retrieval_type=filter, result_count, field_name, operator
    """

def retrieve_semantic(query: str, top_k: int = 10,
                      patient_id: str | None = None) -> list[dict]:
    """
    Embed query → search HDMIS_fields.
    Apply patient_id filter if provided.
    Return list of payload dicts.
    Log: retrieval_type=semantic, result_count, top_score
    """

def retrieve_for_patient(patient_id: str, db) -> list[PatientRecord]:
    """Use adapter — not Qdrant — for complete patient history."""

# pipeline_b/services/retrieval_service.py

def handle_retrieval_query(query: ClassifiedQuery, db) -> RetrievalResult:
    cache_key = make_cache_key(query.text, query.patient_id, "retrieval")
    cached = get_cached(cache_key)
    if cached:
        return RetrievalResult(**cached)

    parsed = parse_retrieval_intent(query.text)   # LLM intent only
    if parsed.operator == "any":
        results = retrieve_semantic(query.text, patient_id=query.patient_id)
        retrieval_type = "semantic"
    else:
        results = retrieve_by_filter(parsed)       # Python queries Qdrant
        retrieval_type = "filter"

    result = RetrievalResult(
        records=results,
        total_count=len(results),
        query_interpretation=f"{parsed.field_name} {parsed.operator} {parsed.value}",
        retrieval_type=retrieval_type,
    )
    set_cache(cache_key, result.dict(), "retrieval")
    return result
```

---

### Step 10 — Generator (LangChain)

**Objective:** GPT-4o reasoning using LangChain chains. Completely separate chains for doctor vs patient.

**Core Logic:**
```python
# pipeline_b/engines/generator.py

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from shared.config import get_settings
import time
from shared.logger import get_logger

logger = get_logger(__name__)

# ── Doctor chain ──────────────────────────────────────────────
DOCTOR_SYSTEM = """You are a clinical decision support assistant.
Interpret lab results for doctors. Use clinical terminology.
Always output valid JSON matching this schema:
{
  "interpretation": "...",
  "clinical_significance": "...",
  "possible_conditions": ["..."],
  "critical_flags": ["..."],
  "confidence": 0.85,
  "citations": []
}
Rules:
- Never make definitive diagnosis — provide differential
- Flag critical values (e.g. Hb < 7 is critical)
- citations is always [] (Phase 3 will populate PubMed refs)
- confidence reflects data quality, not certainty of diagnosis
"""

PATIENT_SYSTEM = """You are a health information assistant.
Explain lab results to patients in simple language (8th grade level).
Always output valid JSON:
{
  "response": "...",
  "simplified_fields": [{"name": "...", "value": "...", "status": "..."}]
}
Rules:
- Never diagnose
- Never recommend or contraindicate medications
- Use plain English: "Your hemoglobin is a bit low" not "Hb 10.5 g/dL"
- Be honest but reassuring
- Always encourage seeing a doctor
"""

DISCLAIMER = (
    "This explanation is for informational purposes only and does not "
    "constitute medical advice. Please consult your doctor for "
    "interpretation and treatment decisions."
)

def _get_llm():
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0.0,
        api_key=get_settings().OPENAI_API_KEY
    )

def _build_context(fields: list, max_fields: int = 15) -> str:
    """
    Context size control — max 15 fields to avoid token overflow.
    Priority order:
      1. Abnormal fields first
      2. Most recent fields
      3. Highest confidence fields
    Format each as: "field_name: value unit (ref: range) — ABNORMAL/NORMAL"
    """
    sorted_fields = sorted(
        fields,
        key=lambda f: (
            f.is_abnormal is True,   # abnormal first
            f.confidence             # then by confidence
        ),
        reverse=True
    )[:max_fields]
    lines = []
    for f in sorted_fields:
        status = "ABNORMAL" if f.is_abnormal else "NORMAL" if f.is_abnormal is False else "UNKNOWN"
        lines.append(
            f"{f.name}: {f.value} {f.unit or ''} "
            f"(ref: {f.reference_range or 'unknown'}) — {status}"
        )
    return "\n".join(lines)

def generate_doctor_reasoning(
    fields: list,
    query: str,
) -> dict:
    """
    LangChain chain: ChatPromptTemplate → ChatOpenAI → JsonOutputParser
    Context capped at 15 fields (abnormal-first).
    Logs: llm_latency_ms, field_count_used
    """
    t = time.time()
    context = _build_context(fields)
    prompt = ChatPromptTemplate.from_messages([
        ("system", DOCTOR_SYSTEM),
        ("human", "Patient data:\n{context}\n\nQuestion: {query}")
    ])
    chain = prompt | _get_llm() | JsonOutputParser()
    result = chain.invoke({"context": context, "query": query})
    logger.info("doctor_reasoning_generated",
                llm_latency_ms=round((time.time()-t)*1000, 2),
                field_count=len(fields))
    return result

def generate_patient_explanation(
    fields: list,
    query: str,
) -> dict:
    """
    Separate LangChain chain using PATIENT_SYSTEM.
    Never calls generate_doctor_reasoning.
    Always appends DISCLAIMER to result.
    Logs: llm_latency_ms
    """
    t = time.time()
    context = _build_context(fields, max_fields=10)
    prompt = ChatPromptTemplate.from_messages([
        ("system", PATIENT_SYSTEM),
        ("human", "Patient data:\n{context}\n\nQuestion: {query}")
    ])
    chain = prompt | _get_llm() | JsonOutputParser()
    result = chain.invoke({"context": context, "query": query})
    result["disclaimer"] = DISCLAIMER
    logger.info("patient_explanation_generated",
                llm_latency_ms=round((time.time()-t)*1000, 2))
    return result
```

**Key Dependencies:** `langchain-openai`, `langchain-core` (add to requirements.txt)

---

### Step 11 — Trend Analyzer + Service

**Core Logic:**
```python
# pipeline_b/engines/trend_analyzer.py

def extract_time_series(patient_id: str, field_name: str) -> list[TrendPoint]:
    """
    Call qdrant_client.get_patient_field_history(patient_id, field_name)
    Filter to numeric values only (numeric_value is not None)
    Sort by collection_date ASC
    Return list[TrendPoint]
    """

def compute_trend(points: list[TrendPoint]) -> dict:
    """
    PYTHON ONLY — no LLM.
    Returns:
      {direction, percent_change, first_value, last_value}

    Logic:
      if len(points) < 2:
        return {direction: insufficient_data, percent_change: None}
      first = points[0].numeric_value
      last  = points[-1].numeric_value
      pct   = (last - first) / first * 100  if first != 0 else None
      direction:
        "increasing" if pct > 5
        "decreasing" if pct < -5
        "stable"     otherwise
    """

def build_chart_json(field_name: str, unit: str | None,
                     points: list[TrendPoint],
                     ref_low: float | None = None,
                     ref_high: float | None = None) -> ChartJSON:
    """
    Return ChartJSON(
      type="line_chart",
      data={"x": [p.date for p in points], "y": [p.numeric_value for p in points]},
      meta={"label": field_name, "unit": unit,
            "ref_low": ref_low, "ref_high": ref_high}
    )
    """

def analyze_trend(patient_id: str, field_name: str) -> TrendResult:
    """
    1. extract_time_series → points
    2. compute_trend → {direction, percent_change, ...}  [PYTHON]
    3. build_chart_json → ChartJSON
    4. GPT-4o insight — receives ONLY computed summary, not raw data:
       context = f"{field_name}: {direction}, {pct}% change, "
                 f"first={first_val}, last={last_val}, "
                 f"reference={ref_low}-{ref_high}"
    5. Return TrendResult
    """
```

---

### Step 12 — Reasoning Service + Patient Service + Analytics Service

**Core Logic:**
```python
# pipeline_b/services/reasoning_service.py

def handle_reasoning_query(query: ClassifiedQuery, patient_id: str, db) -> ReasoningResult:
    cache_key = make_cache_key(query.text, patient_id, "reasoning")
    cached = get_cached(cache_key)
    if cached:
        return ReasoningResult(**cached, cached=True)

    records = get_all_records_for_patient(patient_id, db)
    all_fields = [f for r in records for f in r.fields]
    # Context cap: 15 fields, abnormal-first (enforced in generator._build_context)

    raw = generate_doctor_reasoning(all_fields, query.text)
    result = ReasoningResult(
        interpretation=raw["interpretation"],
        clinical_significance=raw["clinical_significance"],
        possible_conditions=raw["possible_conditions"],
        critical_flags=raw.get("critical_flags", []),
        confidence=raw["confidence"],
        citations=[],          # Phase 3: PubMed
        data_used=all_fields[:15],
    )
    set_cache(cache_key, result.dict(), "reasoning")
    return result

# pipeline_b/services/patient_service.py

BLOCKED_TERMS = [
    "diagnosis", "diagnose", "prescribe", "prescription",
    "medication", "drug", "treatment", "cancer", "tumor",
    "surgery", "operate", "cure", "medicine"
]

DISCLAIMER = (
    "This explanation is for informational purposes only and does not "
    "constitute medical advice. Please consult your doctor for "
    "interpretation and treatment decisions."
)

def handle_patient_query(query: ClassifiedQuery, patient_id: str, db) -> PatientChatResult:
    # Safety check runs FIRST — before any LLM call
    blocked = any(term in query.text.lower() for term in BLOCKED_TERMS)
    if blocked:
        return PatientChatResult(
            response="For questions about treatment or diagnosis, please consult your doctor.",
            simplified_fields=[],
            disclaimer=DISCLAIMER,
            safety_blocked=True
        )

    cache_key = make_cache_key(query.text, patient_id, "patient_chat")
    cached = get_cached(cache_key)
    if cached:
        return PatientChatResult(**cached)

    # patient_id filter ALWAYS applied — never cross-patient
    records = get_all_records_for_patient(patient_id, db)
    all_fields = [f for r in records for f in r.fields]

    raw = generate_patient_explanation(all_fields, query.text)   # PATIENT chain only

    simplified = []
    for f in all_fields[:10]:
        if f.is_abnormal is True:
            status = "Outside normal range"
        elif f.is_abnormal is False:
            status = "Within normal range"
        else:
            status = "See your doctor for interpretation"
        simplified.append({"name": f.name, "value": f.value, "status": status})

    return PatientChatResult(
        response=raw["response"],
        simplified_fields=simplified,
        disclaimer=DISCLAIMER,     # always set — required field
        safety_blocked=False
    )

# pipeline_b/services/analytics_service.py

def get_patient_analytics(patient_id: str, db) -> AnalyticsResult:
    cache_key = make_cache_key("analytics", patient_id, "analytics")
    cached = get_cached(cache_key)
    if cached:
        return AnalyticsResult(**cached, cached=True)

    records = get_all_records_for_patient(patient_id, db)
    all_fields = [f for r in records for f in r.fields]

    # PYTHON — not LLM
    abnormal = [f for f in all_fields if f.is_abnormal is True]
    normal   = [f for f in all_fields if f.is_abnormal is False]

    # Chart JSON — PYTHON
    latest_fields = records[-1].fields if records else []
    numeric_fields = [f for f in latest_fields if f.numeric_value is not None]
    chart = ChartJSON(
        type="bar_chart",
        data={
            "fields": [f.name for f in numeric_fields],
            "values": [f.numeric_value for f in numeric_fields],
            "ref_low": [f.ref_low for f in numeric_fields],
            "ref_high": [f.ref_high for f in numeric_fields],
        },
        meta={"patient_id": patient_id,
              "date": records[-1].processed_at.isoformat() if records else ""}
    )

    # GPT-4o insight — abnormal fields ONLY, context capped
    insight_context = _build_context(abnormal, max_fields=10)
    llm = _get_llm()
    insight_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a clinical assistant. Summarize key findings. Do not diagnose."),
        ("human", "Abnormal findings:\n{context}\n\nProvide a brief clinical summary.")
    ])
    insight_chain = insight_prompt | llm
    insight = insight_chain.invoke({"context": insight_context}).content

    result = AnalyticsResult(
        patient_id=patient_id,
        abnormal_fields=abnormal,
        normal_fields=normal,
        abnormal_count=len(abnormal),
        normal_count=len(normal),
        chart_json=chart,
        ai_insight=insight,
    )
    set_cache(cache_key, result.dict(), "analytics")
    return result
```

---

### Step 13 — FastAPI Routes

**Core Logic:**
```python
# pipeline_b/api/doctor_routes.py
from fastapi import APIRouter, Depends
from shared.db.session import get_db

router = APIRouter(prefix="/api/doctor", tags=["doctor"])

@router.post("/query")
async def doctor_query(body: UserQuery, db=Depends(get_db)):
    """Route to correct service based on classified query type."""
    classified = classify(body.text, PersonaType.doctor)
    if classified.query_type == QueryType.retrieval:
        return handle_retrieval_query(classified, db)
    elif classified.query_type == QueryType.reasoning:
        return handle_reasoning_query(classified, body.patient_id, db)
    elif classified.query_type == QueryType.trend:
        return handle_trend_query(classified, body.patient_id, db)
    else:
        return handle_reasoning_query(classified, body.patient_id, db)

@router.get("/patient/{patient_id}/summary")
async def patient_summary(patient_id: str, db=Depends(get_db)):
    return get_patient_analytics(patient_id, db)

@router.get("/patient/{patient_id}/trend")
async def patient_trend(patient_id: str, field_name: str, db=Depends(get_db)):
    return analyze_trend(patient_id, field_name)

@router.get("/analytics")
async def analytics(field_name: str, operator: str,
                    value: float | None = None, db=Depends(get_db)):
    parsed = ParsedFilter(field_name=field_name, operator=operator,
                          value=value, raw_query="", confidence=1.0)
    return retrieve_by_filter(parsed)

# pipeline_b/api/patient_routes.py
router = APIRouter(prefix="/api/patient", tags=["patient"])

@router.post("/query")
async def patient_query(body: UserQuery, db=Depends(get_db)):
    # PersonaType.patient ALWAYS applied — body.persona is ignored
    classified = classify(body.text, PersonaType.patient)
    return handle_patient_query(classified, body.patient_id, db)

@router.get("/records")
async def patient_records(patient_id: str, db=Depends(get_db)):
    records = get_all_records_for_patient(patient_id, db)
    # Return simplified view — no clinical internals
    return [{"job_id": r.job_id, "date": r.processed_at,
             "document_type": r.document_type,
             "field_count": len(r.fields)} for r in records]

@router.get("/report/{job_id}/explain")
async def explain_report(job_id: str, patient_id: str, db=Depends(get_db)):
    record = get_patient_record(patient_id, job_id, db)
    if not record:
        raise HTTPException(status_code=404)
    classified = ClassifiedQuery(text="explain my report",
                                  persona=PersonaType.patient,
                                  patient_id=patient_id,
                                  query_type=QueryType.patient_chat,
                                  confidence=1.0,
                                  classification_method="rule")
    return handle_patient_query(classified, patient_id, db)
```

---

### Step 14 — Dashboard

**Core Logic:**
```
dashboard/index.html — Doctor dashboard
  Sections:
    1. Query input → POST /api/doctor/query → render result
    2. Patient summary → GET /api/doctor/patient/{id}/summary
       → bar chart (Chart.js) of field values vs reference range
       → AI insight text below chart
    3. Trend → GET /api/doctor/patient/{id}/trend
       → line chart (Chart.js) with reference band

  Chart.js patterns:
    Bar chart: fields on x-axis, values as bars,
               horizontal lines for ref_low and ref_high
    Line chart: dates on x-axis, values on y-axis,
                shaded band between ref_low and ref_high

dashboard/patient.html — Patient view
  Sections:
    1. Simplified query input → POST /api/patient/query
    2. Results card with plain English response
    3. Field status table: name | value | Within/Outside normal range
    4. Disclaimer box — prominently displayed, always visible
```

---

### Step 15 — Tests

```python
# tests/pipeline_b/test_adapter.py
def test_parse_reference_range_all_formats()
def test_compute_is_abnormal_all_cases()
def test_build_clinical_field_from_db_row()
def test_source_type_always_patient()
def test_canonical_name_normalization()

# tests/pipeline_b/test_classifier.py
def test_rule_match_trend_query()
def test_rule_match_retrieval_query()
def test_rule_match_requires_two_keywords()    # single keyword should not match
def test_patient_persona_never_routes_doctor()
def test_classification_method_logged()

# tests/pipeline_b/test_intent_parser.py
def test_parse_low_hemoglobin()         # "low hemoglobin" → lt
def test_parse_hb_below_normal()        # "hb below normal" → lt
def test_parse_explicit_threshold()     # "hemoglobin < 11" → lt, 11.0
def test_parse_any_operator()           # vague query → "any"
def test_field_name_normalized()        # "hgb" → "hemoglobin"

# tests/pipeline_b/test_trend_service.py
def test_compute_trend_increasing()
def test_compute_trend_decreasing()
def test_compute_trend_stable()
def test_compute_trend_insufficient_data()    # len < 2
def test_percent_change_formula()
def test_chart_json_structure()
# NO LLM calls in any trend test — mock generate_doctor_reasoning

# tests/pipeline_b/test_reasoning_service.py
def test_doctor_prompt_used_for_doctor()
def test_patient_prompt_used_for_patient()
def test_disclaimer_always_present()
def test_safety_blocked_on_diagnosis_query()
def test_context_capped_at_15_fields()
def test_cached_result_returned()

# tests/pipeline_b/test_cache.py
def test_cache_key_deterministic()
def test_cache_hit_returns_cached()
def test_cache_miss_returns_none()
def test_invalidate_patient_clears_entries()
```

---

## 7. Observability — Required Log Fields

Every engine and service must emit structured logs via `shared/logger.py`.

```
Query Classifier:
  query_classified: method, type, confidence, duration_ms

Intent Parser:
  intent_parsed: field_name, operator, value, confidence, duration_ms

Retriever:
  retrieval_complete: retrieval_type (filter|semantic), result_count,
                      field_name, operator, duration_ms

Generator (doctor):
  doctor_reasoning_generated: llm_latency_ms, field_count_used, cached

Generator (patient):
  patient_explanation_generated: llm_latency_ms, safety_blocked, cached

Trend Analyzer:
  trend_analyzed: field_name, patient_id, data_points_count,
                  trend_direction, percent_change, duration_ms

Analytics:
  analytics_generated: patient_id, abnormal_count, normal_count,
                       llm_latency_ms, cached

Ingestion:
  ingestion_complete: job_id, patient_id, field_chunks, duration_ms

Cache:
  cache_hit: cache_key, query_type
  cache_miss: cache_key, query_type
  cache_invalidated: patient_id, entries_cleared
```

Monitor these in production:
- `classifier_fallback_to_llm` rate — if > 10%, expand RULES
- `llm_latency_ms` — alert if > 5000ms
- `safety_blocked` rate — monitor patient safety
- `cache_hit` rate — low hit rate means TTLs too short

---

## 8. Critical Implementation Notes

**The adapter is the only DB reader.** If you find any service directly executing SQL against `document_jobs` or `report_fields`, that is a violation. All DB access goes through `pipeline_a_adapter.py`.

**canonical field names must match across all three layers.** Qdrant payload `field_name`, SQL query field names, and adapter output field names must all use the same canonical form from `shared/utils/medical_dict.py`. The adapter's `normalize_field_name()` and the chunker's payload builder both import from the same dict. Never hardcode field names.

**Context size control is non-negotiable.** `generator._build_context()` caps at 15 fields maximum, abnormal-first. Without this cap, a patient with 50+ fields across multiple visits will overflow the GPT-4o context window and produce a truncated or error response.

**Cache invalidation must fire on new ingestion.** When `ingest_patient_record()` completes, it calls `invalidate_patient(patient_id)`. Without this, stale reasoning results will be returned after a patient's new report is processed.

**Patient service applies `patient_id` filter unconditionally.** A patient must never receive another patient's data. The filter is not optional and not user-configurable.

**`citations: []` is a required placeholder now.** Phase 3 adds PubMed RAG. The field exists from day 1 in `ReasoningResult` so the API contract doesn't change when citations become real.

**LangChain is for LLM orchestration only.** Use `ChatPromptTemplate`, `ChatOpenAI`, `JsonOutputParser`, and chains. Do not use LangChain's SQL agents, vector store abstractions (use Qdrant client directly), or routing agents (use the query classifier).

---

## 9. Agent Checklist — Before Marking Any Step Complete

- [ ] File at exact path in mandatory folder structure
- [ ] `pipeline_b/` never imports from `pipeline_a/`
- [ ] All data flows through `PatientRecord` / `ClinicalField` — no raw DB rows in services
- [ ] `source_type: "patient"` set on every Qdrant chunk
- [ ] `chunk_id` is deterministic — same job+field always same ID
- [ ] Qdrant upsert is idempotent — re-run produces no duplicates
- [ ] LLM receives only pre-processed context strings — never raw DB rows
- [ ] `generator._build_context()` caps at 15 fields, abnormal-first
- [ ] Numeric trend computation is Python — LLM only explains
- [ ] Patient routes always use `PersonaType.patient`
- [ ] `BLOCKED_TERMS` check runs before any LLM call in `patient_service`
- [ ] `DISCLAIMER` constant is always set in `PatientChatResult` — never optional
- [ ] Cache check runs before every LLM call in every service
- [ ] `invalidate_patient()` called after every `ingest_patient_record()`
- [ ] `classification_method` logged in every `ClassifiedQuery`
- [ ] Doctor and patient use separate LangChain chains — never shared
- [ ] `citations: []` placeholder exists in every `ReasoningResult`
- [ ] Canonical field names used in Qdrant payload, SQL, and adapter — no raw names
- [ ] `QDRANT_URL` added to `shared/config.py`
- [ ] `langchain-openai` and `langchain-core` added to `requirements.txt`
- [ ] `qdrant-client` added to `requirements.txt`
- [ ] Every directory has `__init__.py`
- [ ] Dashboard HTML fetches from correct API endpoints
- [ ] No LangChain SQL agents anywhere in codebase
