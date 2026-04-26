# 🏥 HDMIS — Healthcare Document Management & Intelligence System

**AI-powered medical document extraction with dual-consensus verification and human-in-the-loop review.**

![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?logo=postgresql&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?logo=openai&logoColor=white)
![Google Vision](https://img.shields.io/badge/Google_Vision-OCR-4285F4?logo=google-cloud&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.3+-37814A?logo=celery&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

HDMIS transforms raw medical documents — lab reports, prescriptions, discharge summaries, and radiology reports — into verified, confidence-scored structured records. It uses a **dual-extraction consensus model**: OpenAI GPT-4o semantically parses documents into structured JSON while Google Cloud Vision OCR provides an independent raw-text anchor. A multi-stage pipeline normalizes, matches, and scores every extracted field before storing verified results in PostgreSQL for downstream retrieval.

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     PIPELINE A — Document Understanding             │
│                                                                     │
│  PDF/Image ──► OCR ──► LLM Extraction ──► Normalization             │
│                 │              │                │                    │
│          (raw text +    (structured JSON)  (canonical names,        │
│           confidence)                      units, values)           │
│                 │              │                │                    │
│                 └──────┬───────┘                │                    │
│                        ▼                        │                    │
│                   Matching ◄────────────────────┘                    │
│              (fuzzy + semantic)                                      │
│                        │                                             │
│                        ▼                                             │
│              Confidence Scoring                                      │
│           (weighted per-field scores)                                │
│                        │                                             │
│                        ▼                                             │
│             Conflict Resolution                                      │
│            (AUTO / HITL decision)                                    │
│                        │                                             │
│            ┌───────────┴───────────┐                                │
│            ▼                       ▼                                │
│     ✅ AUTO fields          ⚠️  HITL queue                          │
│            │                       │                                │
│            └───────────┬───────────┘                                │
│                        ▼                                             │
│              PostgreSQL (upsert)                                     │
│         structured_text_for_embedding                                │
└─────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│              PIPELINE B — Knowledge Retrieval (Phase 2)             │
│         Embeddings → Qdrant → LangChain RAG → MedGemma             │
└─────────────────────────────────────────────────────────────────────┘
```

The **dual-extraction consensus model** ensures that no single AI output is blindly trusted. The LLM provides semantic understanding (field names, units, relationships), while OCR provides a raw-text verification anchor. Every LLM-extracted field must be corroborated against the OCR text through phrase-level fuzzy and semantic matching before it can be auto-accepted.

---

## 🔬 Pipeline A — Stage by Stage

| Stage | File | Purpose | Output |
|-------|------|---------|--------|
| **1. Ingestion** | `pipeline_a/ingestion/loader.py` | MIME detection (magic bytes), document type classification from filename keywords | `IngestedDocument` |
| **2. OCR** | `pipeline_a/ocr/client.py`, `parser.py`, `confidence.py` | Google Cloud Vision API extraction with per-word confidence scores | `OCRResult` |
| **3. LLM Extraction** | `pipeline_a/llm_extraction/extractor.py` | OpenAI GPT-4o structured parsing with 3-attempt retry cascade + regex fallback | `LLMExtractionResult` |
| **4. Normalization** | `pipeline_a/normalization/normalizer.py` | Synonym expansion, unit canonicalization, value cleaning (Indian formats) | `NormalizationResult` |
| **5. Matching** | `pipeline_a/matching/matcher.py` | Phrase-window fuzzy (rapidfuzz) + semantic similarity (sentence-transformers) | `MatchingResult` |
| **6. Confidence** | `pipeline_a/confidence/scorer.py` | Weighted per-field scoring with document-type-aware thresholds | `list[ScoredField]` |
| **7. Conflict/HITL** | `pipeline_a/conflict/resolver.py` | HITL trigger evaluation, embedding text assembly, PostgreSQL upsert | `PipelineAOutput` |

---

## 📁 Folder Structure

```
hdmis/
│
├── shared/
│   ├── config.py                → Centralized configuration (env-based, cached singleton)
│   ├── logger.py                → Structured JSON logging (structlog)
│   ├── db/
│   │   ├── base.py              → SQLAlchemy Base + metadata registry
│   │   ├── session.py           → DB session factory + FastAPI dependency (get_db)
│   │   └── models/
│   │       ├── document.py      → document_jobs table (upsert on job_id)
│   │       ├── extraction.py    → report_fields table (upsert on job_id + name)
│   │       ├── ocr.py           → raw OCR output storage
│   │       ├── matching.py      → fuzzy + semantic comparison results
│   │       ├── confidence.py    → per-field confidence breakdown
│   │       └── hitl.py          → HITL queue + reviewer decisions
│   ├── schemas/
│   │   ├── document.py          → IngestedDocument model
│   │   ├── report.py            → All pipeline stage models + enums
│   │   └── pipeline.py          → Unified inter-stage data contract
│   └── utils/
│       ├── text.py              → Text cleaning, phrase window builder
│       ├── medical_dict.py      → Synonym maps (Hb → hemoglobin, PCM → paracetamol)
│       └── validators.py        → Field validation rules
│
├── pipeline_a/
│   ├── ingestion/loader.py      → MIME detection, document type classification
│   ├── ocr/
│   │   ├── client.py            → Google Cloud Vision API wrapper
│   │   ├── parser.py            → Vision response → OCRWord models
│   │   └── confidence.py        → Word-level → aggregate confidence
│   ├── llm_extraction/
│   │   ├── extractor.py         → OpenAI GPT-4o + 3-attempt retry cascade
│   │   ├── parser.py            → JSON validation + {"fields": [...]} unwrap
│   │   ├── fallback.py          → Regex-based extraction (last resort)
│   │   └── prompts/             → Versioned prompt templates
│   ├── normalization/normalizer.py → Synonym expansion, unit standardization
│   ├── matching/matcher.py      → Phrase-window fuzzy + semantic matching
│   ├── confidence/scorer.py     → Weighted confidence scoring
│   ├── conflict/resolver.py     → HITL trigger logic + output assembly
│   ├── hitl/
│   │   ├── service.py           → HITL queue management + review application
│   │   ├── api.py               → HITL reviewer endpoints
│   │   └── queue.py             → Push low-confidence jobs to review
│   ├── orchestrator/process_document.py → Central stage sequencer
│   ├── worker/tasks.py          → Celery async entrypoint
│   └── api/routes.py            → FastAPI endpoints (upload, status, HITL review)
│
├── pipeline_b/                  → Reserved for Phase 2 (RAG + retrieval)
│
├── infra/
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── docker-compose.yml   → api, worker, db, redis services
│   ├── queue/celery_config.py   → Celery + Redis configuration
│   └── scripts/
│       ├── migrate.sh           → Alembic migration runner
│       └── seed_data.sh
│
├── tests/
│   └── pipeline_a/
│       ├── test_normalization.py
│       ├── test_matching.py
│       ├── test_conflict.py
│       ├── test_llm_extraction.py
│       └── fixtures/sample_lab_ocr.txt
│
├── requirements.txt
├── .env.example
└── test_manual.py               → Full pipeline manual test script
```

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **OCR** | Google Cloud Vision API | Document text extraction with per-word confidence |
| **LLM** | OpenAI GPT-4o | Structured field extraction with JSON response format |
| **Embeddings** | sentence-transformers `all-MiniLM-L6-v2` | Contextual semantic similarity for field matching |
| **Fuzzy Matching** | rapidfuzz | Token-set-ratio phrase matching against OCR text |
| **Database** | PostgreSQL + SQLAlchemy 2.x | Persistent storage with idempotent upsert operations |
| **Task Queue** | Celery + Redis | Async document processing with crash-safe retry |
| **API** | FastAPI | REST endpoints for upload, status, and HITL review |
| **Validation** | Pydantic v2 | Typed data contracts between all pipeline stages |
| **Config** | pydantic-settings | Environment-based configuration with `.env` support |
| **Logging** | structlog | Structured JSON logging with per-stage observability |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 15+
- Redis
- Google Cloud Vision service account JSON
- OpenAI API key

### Installation

```bash
git clone https://github.com/Arijit-2003/DocuMed-AI.git
cd DocuMed-AI/hdmis
python3 -m venv venvHdmis
source venvHdmis/bin/activate
pip install -r requirements.txt
```

### Environment Setup

```bash
cp .env.example .env
# Edit .env and fill in your values
```

Full `.env.example`:

```env
# HDMIS Pipeline A — Environment Variables

# --- Google Cloud / LLM ---
OPENAI_API_KEY=your-openai-api-key-here
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# --- Database ---
DATABASE_URL=postgresql://hdmis_user:hdmis_pass@localhost:5432/hdmis_db

# --- Redis / Celery ---
REDIS_URL=redis://localhost:6379/0

# --- Thresholds ---
OCR_CONFIDENCE_THRESHOLD=0.85
FIELD_CONFIDENCE_THRESHOLD=0.85
LAB_REPORT_CONFIDENCE_THRESHOLD=0.72
PRESCRIPTION_CONFIDENCE_THRESHOLD=0.80
FUZZY_MATCH_THRESHOLD=85
```

### Database Setup

```bash
# Create the database
createdb hdmis_db

# Initialize tables (dev mode — uses SQLAlchemy create_all)
venvHdmis/bin/python -c "
from shared.db.session import init_db
init_db()
print('✅ Tables created')
"
```

### Running the Manual Test

```bash
venvHdmis/bin/python test_manual.py /path/to/lab_report.pdf
```

This runs the full 7-stage pipeline and prints detailed output for each stage — OCR text, LLM fields, normalization mappings, matching scores, and final confidence decisions.

---

## 📊 Sample Output

When run against a CBC lab report (e.g., Spandan Diagnostic Center), the pipeline extracts all test results:

```
📄 File : sample_report.pdf  (245892 bytes)
============================================================
📋 Document Type detected : lab_report
   MIME type              : application/pdf

🔍 RAW OCR OUTPUT
Pages processed : 1
Words extracted : 342
Avg confidence  : 0.9812
Low confidence  : False

🤖 RAW LLM EXTRACTION OUTPUT
Fields extracted : 19
Attempt count    : 1
Fallback used    : False
```

### Extracted Fields

| Field Name | Value | Unit | Confidence | Status |
|------------|-------|------|------------|--------|
| hb% | 10.5 | gm/dl | 0.8924 | ✅ AUTO |
| rbc count | 3.5 | 10^6/uL | 0.8756 | ✅ AUTO |
| wbc count | 8400 | /cmm | 0.9012 | ✅ AUTO |
| neutrophil | 68 | % | 0.8834 | ✅ AUTO |
| lymphocyte | 24 | % | 0.8912 | ✅ AUTO |
| eosinophil | 04 | % | 0.8645 | ✅ AUTO |
| monocyte | 03 | % | 0.8523 | ✅ AUTO |
| basophil | 01 | % | 0.7834 | ✅ AUTO |
| platelet count | 2,50,000 | /cmm | 0.8912 | ✅ AUTO |
| pcv | 38.2 | % | 0.8734 | ✅ AUTO |
| mcv | 82.5 | fL | 0.8612 | ✅ AUTO |
| mch | 27.8 | pg | 0.8523 | ✅ AUTO |
| mchc | 33.5 | g/dL | 0.8445 | ✅ AUTO |
| esr | 12 | mm/hr | 0.9123 | ✅ AUTO |
| rdw | 13.2 | % | 0.8234 | ✅ AUTO |
| malaria parasite | Not Found | — | 0.7612 | ✅ AUTO |
| mp (card test) | Negative | — | 0.7534 | ✅ AUTO |
| widal test (s. typhi o) | 1:80 | dilution | 0.7312 | ✅ AUTO |
| widal test (s. typhi h) | 1:160 | dilution | 0.7245 | ✅ AUTO |

### Structured Text for Pipeline B

```
Document type: lab_report
hb%: 10.5 gm/dl (reference: FEMALE: 11.5 - 16.4 gm/dl)
rbc count: 3.5 10^6/uL (reference: 3.00 - 5.50)
wbc count: 8400 /cmm (reference: 4000-11000)
neutrophil: 68 % (reference: 50-70)
lymphocyte: 24 % (reference: 20-40)
platelet count: 2,50,000 /cmm (reference: 1,50,000-4,00,000)
esr: 12 mm/hr (reference: 0-20)
malaria parasite: Not Found
widal test (s. typhi o): 1:80 dilution
widal test (s. typhi h): 1:160 dilution
```

---

## 📈 Confidence Scoring System

### Scoring Formula

```
final_score = 0.7 × combined_match + 0.3 × ocr_word_confidence

combined_score = 0.6 × (fuzzy_score / 100) + 0.4 × semantic_score
```

- **Fuzzy score** (0–100): `rapidfuzz.token_set_ratio` of field context vs OCR phrase windows
- **Semantic score** (0–1): Cosine similarity of `all-MiniLM-L6-v2` embeddings
- **OCR word confidence** (0–1): Mean confidence of OCR words matching the field value (via `partial_ratio ≥ 80`)

### Document-Type-Aware Thresholds

| Document Type | Threshold | Rationale |
|--------------|-----------|-----------|
| `lab_report` | **0.72** | Unstructured OCR layouts, tabular data with noise |
| `prescription` | **0.80** | Semi-structured, handwriting artifacts |
| `default` | **0.85** | Strict threshold for unknown document types |

### AUTO vs HITL Decision

- **AUTO** (`final_score ≥ threshold`): Field is accepted without human review
- **HITL** (`final_score < threshold`): Field is flagged for human-in-the-loop review, tagged with `[LOW_CONFIDENCE]` in the embedding text

---

## 👩‍⚕️ HITL (Human-in-the-Loop)

Four conditions trigger mandatory HITL review:

| # | Trigger Condition | Rationale |
|---|------------------|-----------|
| 1 | Any field confidence below the document-type threshold | Individual field uncertainty |
| 2 | Document-level OCR avg confidence below 0.85 | Poor scan quality affects all fields |
| 3 | LLM returns zero fields after all 3 retries + regex fallback | Complete extraction failure |
| 4 | Critical field missing for the document type (e.g., no `drug_name` on a prescription) | Patient safety requirement |

HITL fields are **tagged in** `structured_text_for_embedding` (not excluded), so Pipeline B still has access to partial data. After human review via the HITL endpoint, fields are promoted to AUTO and the embedding text is regenerated untagged.

---

## 💊 Medical Synonym Maps

`shared/utils/medical_dict.py` maintains ~100+ mappings for Indian and international medical abbreviations:

| Abbreviation | Canonical Name |
|-------------|---------------|
| Hb, Hgb | hemoglobin |
| SGPT, ALT | alanine aminotransferase |
| SGOT, AST | aspartate aminotransferase |
| PCM, Dolo | paracetamol |
| TLC, WBC | total leucocyte count |
| DLC | differential leucocyte count |
| PCV, Hct | packed cell volume / hematocrit |
| BUN | blood urea nitrogen |
| BID | twice daily |
| OD | once daily |

Unit synonyms are also canonicalized: `g/dl` → `g/dL`, `cells/cumm` → `cells/µL`, `mcg` → `µg`, `meq/l` → `mEq/L`.

> **Note:** Indian labs frequently use abbreviations (Hb, TLC, DLC, SGPT, SGOT) not found in international standards. The synonym map is actively maintained as new document types are onboarded.

---

## 🔮 Pipeline B — Phase 2

Pipeline B will provide intelligent knowledge retrieval over the structured medical records produced by Pipeline A:

- **Chunking**: Split `structured_text_for_embedding` into semantically meaningful segments
- **Embeddings**: Generate dense vector representations for each chunk
- **Vector Store**: Index embeddings in Qdrant for fast similarity search
- **RAG Pipeline**: LangChain-based retrieval-augmented generation
- **Medical Reasoning**: MedGemma for domain-specific clinical query responses
- **Interface**: Natural language queries like *"What were the patient's hemoglobin trends over the last 6 months?"*

Pipeline B reads **only** from the `document_jobs.structured_text_for_embedding` column and `report_fields` table — it never imports Pipeline A code directly.

---

## 🧪 Running Tests

```bash
# Individual test files
venvHdmis/bin/python -m pytest tests/pipeline_a/test_normalization.py -v
venvHdmis/bin/python -m pytest tests/pipeline_a/test_matching.py -v
venvHdmis/bin/python -m pytest tests/pipeline_a/test_llm_extraction.py -v
venvHdmis/bin/python -m pytest tests/pipeline_a/test_conflict.py -v

# All tests together
venvHdmis/bin/python -m pytest tests/pipeline_a/ -v
```

Tests mock `structlog`, `rapidfuzz`, and `sentence-transformers` so they run without API keys or heavy ML model downloads. The test suite validates:

- Synonym normalization (`hgb` → `hemoglobin`, `g/dl` → `g/dL`)
- Indian number format handling (`1,50,000` → `150000`)
- Phrase-window matching accuracy
- Fuzzy matching (`Amoxcillin` vs `Amoxicillin` ≥ 85)
- HITL trigger conditions
- Upsert idempotency (no `IntegrityError` on duplicate keys)

---

## 📋 Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | `""` | OpenAI API key for GPT-4o extraction |
| `GOOGLE_APPLICATION_CREDENTIALS` | `""` | Path to Google Cloud Vision service account JSON |
| `DATABASE_URL` | `postgresql://hdmis_user:hdmis_pass@localhost:5432/hdmis_db` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL for Celery broker and result backend |
| `OCR_CONFIDENCE_THRESHOLD` | `0.85` | Document-level OCR confidence below this triggers HITL |
| `FIELD_CONFIDENCE_THRESHOLD` | `0.85` | Default per-field confidence threshold (unknown doc types) |
| `LAB_REPORT_CONFIDENCE_THRESHOLD` | `0.72` | Per-field threshold for lab reports |
| `PRESCRIPTION_CONFIDENCE_THRESHOLD` | `0.80` | Per-field threshold for prescriptions |
| `FUZZY_MATCH_THRESHOLD` | `85` | Minimum rapidfuzz score for OCR word mapping |

---

## ⚠️ Known Limitations (Current MVP)

- **Widal test titres**: Dilution values (e.g., `1:80`, `1:160`) for multiple antigens may be consolidated into fewer fields depending on OCR layout
- **Model download on first run**: `sentence-transformers` checks HuggingFace for the `all-MiniLM-L6-v2` model on each run; can be cached offline for air-gapped environments
- **Pipeline B not yet implemented**: The RAG retrieval layer is reserved for Phase 2
- **Direct orchestrator invocation**: The current MVP runs via `test_manual.py` calling the orchestrator directly; the FastAPI server endpoints are implemented but not yet deployed as a running service

---

## 🤝 Contributing

This project follows **blueprint-driven development**: each pipeline stage has a dedicated specification in the [HDMIS Pipeline A Blueprint](HDMIS_Pipeline_A_Blueprint%20.md).

Guidelines:
1. Read the relevant blueprint section before implementing any stage
2. Follow the mandatory folder structure — do not create files outside the defined tree
3. All inter-stage data must use Pydantic models from `shared/schemas/` — no raw dicts
4. All DB writes must use upsert — no bare `INSERT`
5. Every stage must emit structured logs via `shared/logger.py`
6. Run the test suite and verify all tests pass before submitting changes

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
