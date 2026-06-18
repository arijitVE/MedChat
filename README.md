# DocuMed-AI

DocuMed-AI is an AI-powered Medical Documentation System. It is designed to ingest raw medical documents (both digital PDFs and scanned images), extract structured clinical information, generate longitudinal patient summaries and clinical opinions, and provide a RAG-based chat interface for deep medical research into a specific patient case.

The project is built as a production-ready backend prototype with FastAPI, MySQL, Celery for asynchronous processing, and Qdrant for vector storage.

---

## 🚀 Features at a Glance

- **Case-Based Architecture:** All documents, extraction jobs, summaries, and chat sessions belong to a unified `Case` entity.
- **Intelligent Ingestion:** 
  - Automatically routes pages to **PyMuPDF / pdfplumber** if extractable digital text is detected (fast & cheap).
  - Routes scanned image pages to **GPT-4o Vision** for high-fidelity OCR.
- **Robust Medical Extraction:** Extracts patient info, diagnoses, medications, lab results, procedures, dates, and recommendations into strict JSON schemas with automatic retry cascades.
- **Clinical Summaries & Opinions:** 
  - Automatically builds a chronological timeline of patient history.
  - Generates comprehensive human-readable Medical Summaries.
  - Drafts clinical opinions and prognoses based purely on extracted context (designed to prevent AI hallucinations).
- **RAG-based Chat / Research:** Uploaded documents are chunked, embedded, and stored in Qdrant, allowing users to ask semantic questions like *"Which report mentions diabetes?"*
- **Role-Based Access Control:** Secure JWT authentication with simple `ADMIN` and `USER` roles.

---

## 🛠️ Technology Stack

- **Backend Framework:** FastAPI (Python 3.13)
- **Database (Relational):** MySQL + SQLAlchemy (ORM) + Alembic (Migrations)
- **Database (Vector):** Qdrant
- **Task Queue:** Celery + Redis
- **AI / LLMs:** OpenAI (GPT-4o, GPT-4o-Vision), LangChain, SentenceTransformers
- **Document Processing:** PyMuPDF (fitz), pdfplumber
- **Authentication:** PyJWT, bcrypt

---

## 📂 Repository Structure

```text
DocuMed-AI/
├── main.py                     # FastAPI application entry point
├── shared/                     # Shared models, config, and schemas
│   ├── config.py               # Environment configuration
│   ├── db/                     # SQLAlchemy models (User, Case, Document, etc.)
│   └── schemas/                # Pydantic schemas (Pipeline, Report, Auth)
├── product/                    # Product Layer (API Routes & Auth)
│   ├── api/                    # Routers (auth_routes, case_routes, user_routes)
│   └── auth/                   # JWT Handling, Rate Limiting, Role Guards
├── pipeline_a/                 # Core AI Pipeline (Ingestion -> Extraction -> Summary)
│   ├── ingestion/              # OCR, PyMuPDF parsing, Image routing
│   ├── orchestrator/           # Async Celery pipeline runner
│   ├── llm_extraction/         # GPT-4o JSON extraction & parsers
│   └── normalizer.py           # Medical term normalization & deduplication
├── pipeline_b/                 # RAG / Vector Pipeline
│   ├── embedding/              # Sentence-transformers embedders
│   └── vector_db/              # Qdrant client
├── storage/                    # Local storage for uploaded PDFs
└── qdrant_storage/             # Local storage for vector DB
```

---

## ⚙️ Setup & Installation

### 1. Prerequisites
- Python 3.11+
- MySQL Server (running locally or via Docker)
- Redis Server (for Celery workers)

### 2. Environment Variables
Create a `.env` file in the root directory. You can use `.env.example` if available.
```env
# AI Models
OPENAI_API_KEY="your-openai-key-here"

# Database
DATABASE_URL="mysql+pymysql://hdmis_user:hdmis_pass@localhost:3306/hdmis"

# Auth / Security
SECRET_KEY="your-super-secret-jwt-key"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="admin123"

# Redis
REDIS_URL="redis://localhost:6379/0"

# Qdrant
QDRANT_STORAGE_PATH="./qdrant_storage"
```

### 3. Install Dependencies
Using `uv` or standard `pip`:
```bash
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 4. Database Initialization
The application is configured to automatically create tables on startup if they don't exist. Simply starting the server will initialize your MySQL database.

---

## 🏃‍♂️ Running the Application

You will need two terminal windows to run the full system (one for the API, one for the async workers).

**Terminal 1: Start the FastAPI Server**
```bash
uvicorn main:app --reload
```
The API documentation will be available at: `http://127.0.0.1:8000/docs`

**Terminal 2: Start the Celery Worker**
```bash
celery -A infra.queue.celery_config.celery_app worker --loglevel=info --pool=solo
```
*(Note: Use `--pool=solo` on Windows. On Mac/Linux, you can omit it).*

---

## 📖 Core Workflows (API)

### 1. Authentication
- **`POST /auth/login`**: Authenticate using your `.env` admin credentials or a registered user account to receive a JWT.
- **`POST /auth/signup`**: Register a new standard user.

### 2. Case Management & Pipeline
1. **Create Case**: `POST /api/v1/cases` -> Returns a new `case_id`.
2. **Upload Document**: `POST /api/v1/cases/{case_id}/upload` -> Attach a medical PDF/Image to the case.
3. **Process Case**: `POST /api/v1/cases/{case_id}/process` -> Queues the document in Celery for background extraction. Returns a `job_id`.
4. **Poll Status**: `GET /api/v1/cases/{case_id}/jobs/{job_id}` -> Check if the extraction, timeline, and summary are complete.

### 3. Review AI Generation
- **`GET /api/v1/cases/{case_id}/summary`**: Fetch the generated patient timeline and medical summary.
- **`GET /api/v1/cases/{case_id}/opinion`**: Fetch the generated clinical opinion and recommendations.

### 4. RAG Chat
- **`POST /api/v1/cases/{case_id}/chat`**: Ask questions about the case. The system queries Qdrant to retrieve relevant document chunks and formulates an answer based purely on the uploaded records.
