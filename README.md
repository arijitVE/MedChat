# HDMIS - Healthcare Document Management & Intelligence System

HDMIS is a full-stack healthcare document platform for uploading medical reports, extracting structured clinical fields with OCR and LLM processing, reviewing low-confidence results through doctor HITL workflows, and giving patients, doctors, and admins role-specific dashboards.

The current system includes:

- FastAPI product API with JWT authentication and role guards.
- React + TypeScript frontend for patient, doctor, and admin users.
- Pipeline A for document ingestion, OCR, LLM extraction, normalization, matching, confidence scoring, and HITL decisions.
- Pipeline B for retrieval, trends, analytics, embeddings, and AI-assisted query workflows.
- PostgreSQL persistence, Redis/Celery async processing, local/Qdrant vector storage, and audit-friendly report state transitions.

## Main Features

### Patient

- Signup/login with full-user auth state.
- Upload reports through `POST /patient/upload`.
- View report lifecycle status: `uploaded`, `processing`, `auto_approved`, `hitl_required`, `verified`, `released`, `failed`.
- Search and filter reports through `GET /patient/reports/search`.
- View extracted fields, report detail, EDA, trends, notifications, and account information.
- Use a patient-safe chat assistant with report-specific or general health context.

### Doctor

- Doctor signup with specialization/license fields and admin verification.
- Pending verification screen until admin approval.
- Dashboard, patients, reports, HITL queue, analytics, notifications, and account pages.
- Upload reports for registered patients or pending patient emails.
- View all fields for a report, edit values before verification, verify at report level, unlock verified reports when correction is needed.
- Use a floating global AI assistant across doctor pages with guided modes:
  - Patient-Specific Analysis
  - Global Analytics
  - Report Discussion
  - Trend Analysis
  - OCR/Extraction Investigation
  - Abnormality Review

### Admin

- Dashboard for platform overview.
- Manage users, doctors, patients, doctor-patient assignments, reports, failed jobs, HITL queue, analytics, notifications, audit logs, system health, settings, and logout.
- Approve/reject doctor verification status.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend API | FastAPI, Pydantic v2 |
| Database | PostgreSQL, SQLAlchemy |
| Auth | JWT access/refresh tokens, bcrypt |
| Async jobs | Celery, Redis |
| OCR | Google Cloud Vision |
| LLM extraction | OpenAI |
| Matching | rapidfuzz, sentence-transformers |
| Vector retrieval | Qdrant client |
| Frontend | React 18, TypeScript, Vite |
| Frontend state/data | Zustand, TanStack Query, Axios |
| UI | Tailwind CSS, lucide-react, Recharts |

## Repository Structure

```text
hdmis/
├── frontend/                 # React + TypeScript app
│   └── src/
│       ├── api/              # Axios API contracts
│       ├── components/       # Layout, reports, charts, assistant, notifications
│       ├── hooks/            # React Query and auth hooks
│       ├── pages/            # Patient, doctor, admin, auth screens
│       ├── store/            # Zustand stores
│       ├── types/            # Frontend TypeScript contracts
│       └── validation/       # Zod schemas
├── product/                  # Product layer API, auth, schemas, services
│   ├── api/                  # Auth, patient, doctor, admin, user routes
│   ├── auth/                 # JWT, password, role guards, rate limits
│   ├── schemas/              # Request/response models
│   └── services/             # Upload, reports, assignments, notifications, verification
├── pipeline_a/               # OCR + extraction + confidence + HITL pipeline
├── pipeline_b/               # Retrieval, trends, analytics, query engines
├── shared/                   # Shared config, database models, schemas, utilities
├── migrations/               # SQL migrations
├── infra/                    # Docker, Celery, scripts
├── tests/                    # Backend test suites
├── main.py                   # FastAPI app entrypoint
├── seed_admin.py             # Local admin seed helper
└── requirements.txt          # Python dependencies
```

## Backend Routes

The frontend is aligned to the product-layer routes below.

### Auth

```text
POST /auth/signup
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /users/me
```

### Patient

```text
POST /patient/upload
PUT  /patient/reports/{report_id}/reupload

GET  /patient/reports/search
GET  /patient/reports/{report_id}
GET  /patient/reports/{report_id}/eda
GET  /patient/reports/{report_id}/fields
POST /patient/reports/{report_id}/fields/{field_name}/verify

GET  /patient/assignments
POST /patient/assignments
PUT  /patient/assignments/{assignment_id}/approve
PUT  /patient/assignments/{assignment_id}/reject

POST /patient/chat
GET  /patient/trends

GET  /patient/notifications
PUT  /patient/notifications/{notification_id}/read
```

### Doctor

```text
POST /doctor/upload
PUT  /doctor/reports/{report_id}/reupload
GET  /doctor/reports/search
GET  /doctor/reports/{report_id}
GET  /doctor/reports/{report_id}/raw-file
GET  /doctor/reports/{report_id}/fields
POST /doctor/reports/{report_id}/verify
POST /doctor/reports/{report_id}/unlock
POST /doctor/reports/{report_id}/fields/{field_name}/edit
POST /doctor/reports/{report_id}/fields/{field_name}/verify

GET  /doctor/assignments
POST /doctor/assignments
PUT  /doctor/assignments/{assignment_id}/approve
PUT  /doctor/assignments/{assignment_id}/reject

POST /doctor/query
GET  /doctor/patients/search
GET  /doctor/patients/{patient_id}/trend
GET  /doctor/patients/{patient_id}/analytics

GET  /doctor/notifications
PUT  /doctor/notifications/{notification_id}/read
```

### Admin

Admin routes are mounted under `/admin` and cover users, doctors, patients, assignments, reports, failed jobs, HITL, analytics, notifications, audit logs, system health, and settings.

## Environment Variables

Copy `.env.example` to `.env` and fill in local values. Never commit `.env`, private keys, service-account JSON files, generated storage, or Qdrant local data.

```bash
cp .env.example .env
```

Common variables:

```env
OPENAI_API_KEY=your-openai-api-key
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/google-service-account.json

DATABASE_URL=postgresql://hdmis_user:hdmis_pass@localhost:5432/hdmis
REDIS_URL=redis://localhost:6379/0

SECRET_KEY=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=1440
JWT_REFRESH_EXPIRY_DAYS=7

STORAGE_PATH=./storage
MAX_FILE_SIZE_MB=50

QDRANT_URL=
QDRANT_STORAGE_PATH=./qdrant_storage

OCR_CONFIDENCE_THRESHOLD=0.85
FIELD_CONFIDENCE_THRESHOLD=0.85
LAB_REPORT_CONFIDENCE_THRESHOLD=0.72
PRESCRIPTION_CONFIDENCE_THRESHOLD=0.80
FUZZY_MATCH_THRESHOLD=85
```

Frontend environment:

```env
VITE_API_URL=http://localhost:8000
```

## Local Setup

### 1. Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Create a PostgreSQL database and run migrations:

```bash
createdb hdmis
for file in migrations/*.sql; do psql "$DATABASE_URL" -f "$file"; done
```

Start Redis if you are not using Docker:

```bash
redis-server
```

Run the API:

```bash
uvicorn main:app --reload
```

Run the Celery worker in another terminal:

```bash
celery -A infra.queue.celery_config.celery_app worker --loglevel=info
```

The API will be available at:

```text
http://localhost:8000
http://localhost:8000/docs
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at:

```text
http://localhost:5173
```

### 3. Docker option

The repository includes Docker files for the API, worker, PostgreSQL, and Redis:

```bash
docker compose -f infra/docker/docker-compose.yml up --build
```

## Admin Seed

For local development, create the default admin user:

```bash
python seed_admin.py
```

The seed script prints the created email and password. Change the password before using any shared or deployed environment.

## Useful Commands

Backend checks:

```bash
python3 -m compileall main.py product pipeline_a pipeline_b shared
pytest
```

Frontend checks:

```bash
cd frontend
npx tsc --noEmit
npm run lint
npm run build
```

Manual Pipeline A test:

```bash
python test_manual.py /path/to/report.pdf
```

## Security Notes

- Do not commit `.env`, Google service-account JSON files, API keys, local uploads, local Qdrant storage, or database dumps.
- Uploaded reports are stored under `STORAGE_PATH` and should remain outside version control.
- If local uploaded files were already tracked before `.gitignore` was updated, untrack them without deleting local files:

  ```bash
  git rm --cached -r storage qdrant_storage
  ```

- The frontend should call only product-layer routes without old `/api/patient/...` or `/api/doctor/...` direct pipeline routes.
- Patient routes require authenticated patient users.
- Doctor routes require authenticated doctors and, for clinical tools, approved verification status.
- Admin routes require authenticated admin users.
- RBAC checks must run before patient-scoped retrieval or vector search.
- Raw report access is protected and should not expose public filesystem URLs.

## Current Status

This is an active academic/product prototype. Core patient, doctor, admin, OCR/LLM extraction, HITL, analytics, and notification flows are present, but production deployment should still add hardened secret management, HTTPS, stricter CORS, observability, backups, and formal clinical safety review.
