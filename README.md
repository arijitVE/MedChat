# HDIMS - Healthcare Document Management and Intelligence System

HDIMS is a full-stack healthcare document platform for uploading medical reports, extracting structured clinical values through OCR and LLM processing, reviewing uncertain results through doctor human-in-the-loop workflows, and giving patients, doctors, and admins role-specific views of the same report lifecycle.

The project is built as an academic/product prototype with real product-layer APIs, a React frontend, PostgreSQL persistence, async document processing, and AI-assisted retrieval and analytics.

## Table of Contents

- [Purpose](#purpose)
- [What HDIMS Solves](#what-HDIMS-solves)
- [System at a Glance](#system-at-a-glance)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Core Concepts](#core-concepts)
- [User Roles](#user-roles)
- [Report Lifecycle](#report-lifecycle)
- [High-Level Data Flow](#high-level-data-flow)
- [Authentication and Authorization](#authentication-and-authorization)
- [Frontend Architecture](#frontend-architecture)
- [Backend Architecture](#backend-architecture)
- [Pipeline A: OCR and Extraction](#pipeline-a-ocr-and-extraction)
- [Pipeline B: Retrieval, Trends, Analytics, and AI Chat](#pipeline-b-retrieval-trends-analytics-and-ai-chat)
- [Patient Flow](#patient-flow)
- [Doctor Flow](#doctor-flow)
- [Admin Flow](#admin-flow)
- [Report Naming](#report-naming)
- [Analytics and Visualization Logic](#analytics-and-visualization-logic)
- [Notifications](#notifications)
- [Audit Logging](#audit-logging)
- [API Routes](#api-routes)
- [Database and Migrations](#database-and-migrations)
- [Environment Variables](#environment-variables)
- [Local Setup](#local-setup)
- [Admin Seed](#admin-seed)
- [Development Commands](#development-commands)
- [Testing and Verification](#testing-and-verification)
- [Security Notes](#security-notes)
- [Known Implementation Notes](#known-implementation-notes)
- [Future Scope](#future-scope)

## Purpose

Medical documents are often uploaded as PDFs or images and are difficult to search, compare, review, or analyze over time. HDIMS converts those unstructured documents into structured, patient-scoped medical data.

The system is designed around four goals:

1. Help patients upload and understand medical reports without exposing technical OCR or AI details.
2. Help doctors review extracted report values quickly and safely.
3. Help admins manage users, doctor verification, assignments, failed jobs, audit logs, and platform health.
4. Keep every sensitive workflow role-protected, traceable, and grounded in stored data.

## What HDIMS Solves

HDIMS is meant to solve these problems:

- Patients lose track of historical reports.
- Doctors spend time manually reading repeated values from scanned reports.
- OCR and LLM extraction can be useful, but uncertain values must be reviewed.
- Report values need longitudinal visualization across time.
- AI chat should not hallucinate stored medical values.
- Admins need operational control over users, doctors, reports, failed jobs, and system health.

HDIMS therefore separates:

- File upload and storage.
- OCR and extraction.
- Confidence scoring.
- Doctor verification.
- Patient-visible reports.
- Analytics and charts.
- AI explanations and retrieval.
- Admin governance.

## System at a Glance

```text
React frontend
  |
  | Axios + JWT
  v
FastAPI product API
  |
  | PostgreSQL transactions
  v
Reports, users, assignments, fields, notifications, audit logs
  |
  | Background task
  v
Pipeline A
  |
  | OCR -> LLM extraction -> normalization -> confidence -> HITL decision
  v
Structured report fields
  |
  | Query, analytics, retrieval
  v
Pipeline B
  |
  | SQL analytics, trend analysis, retrieval, AI explanation
  v
Role-specific patient, doctor, and admin UX
```

The frontend should use the product-layer routes under:

- `/auth`
- `/users`
- `/patient`
- `/doctor`
- `/admin`

The legacy direct Pipeline B routes under `/api/patient` and `/api/doctor` are still mounted by `main.py`, but the product frontend should avoid them for normal app navigation.

## Technology Stack

| Layer | Technology |
| --- | --- |
| Backend API | FastAPI |
| Validation | Pydantic |
| Database | PostgreSQL |
| ORM / SQL | SQLAlchemy plus SQL text queries |
| Auth | JWT, bcrypt password hashing, role guards |
| Async jobs | Celery and Redis |
| OCR | Google Cloud Vision integration |
| LLM extraction | OpenAI integration |
| Matching | rapidfuzz, sentence-transformers style matching utilities |
| Vector / retrieval | Qdrant client and local vector storage support |
| Frontend | React 18, TypeScript, Vite |
| Routing | React Router |
| Data fetching | TanStack Query |
| API client | Axios interceptors |
| Auth state | Zustand persisted store |
| Forms | React Hook Form, Zod |
| UI | Tailwind CSS, lucide-react |
| Charts | Recharts |

## Repository Structure

```text
HDIMS/
|-- frontend/
|   |-- package.json
|   `-- src/
|       |-- api/                  # Axios API contracts
|       |-- components/           # Layout, report cards, charts, assistant, UI primitives
|       |-- hooks/                # React Query hooks and auth hooks
|       |-- lib/                  # Shared frontend helpers
|       |-- pages/                # Auth, patient, doctor, admin pages
|       |-- providers/            # Realtime/polling providers
|       |-- store/                # Zustand auth store
|       |-- types/                # TypeScript DTOs
|       `-- validation/           # Zod schemas
|-- product/
|   |-- api/                      # Product-layer FastAPI routes
|   |-- auth/                     # JWT, middleware, role guards, rate limits
|   |-- schemas/                  # Request/response schemas
|   |-- services/                 # Business logic services
|   `-- utils/                    # File storage helpers
|-- pipeline_a/
|   |-- api/                      # Direct Pipeline A routes
|   |-- confidence/               # Confidence scoring
|   |-- conflict/                 # Conflict resolution
|   |-- hitl/                     # Human-in-the-loop support
|   |-- ingestion/                # File loading and document creation
|   |-- llm_extraction/           # LLM extraction layer
|   |-- matching/                 # Field matching
|   |-- normalization/            # Value and field normalization
|   |-- ocr/                      # OCR layer
|   |-- orchestrator/             # Pipeline orchestration
|   `-- worker/                   # Celery task entrypoints
|-- pipeline_b/
|   |-- adapters/                 # Reads Pipeline A outputs into query-friendly records
|   |-- api/                      # Legacy direct Pipeline B routes
|   |-- cache/                    # Response caching helpers
|   |-- chunking/                 # Text chunking for retrieval
|   |-- embedding/                # Embedding support
|   |-- engines/                  # Classifier, generator, trend analyzer, retriever
|   |-- ingestion/                # Ingestion helpers for retrieval data
|   |-- schemas/                  # Query and output contracts
|   |-- services/                 # Reasoning, retrieval, trend, patient chat services
|   `-- vector_db/                # Vector database integration
|-- shared/
|   |-- db/                       # Database session and shared models
|   |-- schemas/                  # Shared pipeline schemas
|   `-- utils/                    # Medical dictionary and shared utilities
|-- migrations/                   # SQL migrations applied in order
|-- infra/
|   |-- docker/                   # Docker Compose setup
|   |-- queue/                    # Celery app configuration
|   `-- scripts/                  # Infra helper scripts
|-- tests/                        # Backend tests
|-- dashboard/                    # Static dashboard mount
|-- main.py                       # FastAPI app entrypoint
|-- seed_admin.py                 # Local admin seed helper
|-- requirements.txt              # Python dependencies
|-- .env.example                  # Safe environment template
`-- README.md
```

## Core Concepts

### User

A user is stored in the `users` table and has a role:

- `patient`
- `doctor`
- `admin`

The frontend keeps the full user object in auth state because many pages depend on:

- `user.role`
- `user.full_name`
- `user.email`
- `user.patient_uid`
- `user.verification_status`

### Patient UID

Patients receive a generated UID such as:

```text
PAT-00005
```

Doctors and admins use this UID to link reports and assignments to the correct patient.

### Report

A report is the product-layer record representing an uploaded file. It stores:

- report id
- job id
- patient id
- uploaded by
- doctor id if relevant
- original file metadata
- storage path
- upload document type
- inferred document type
- lifecycle status
- duplicate metadata
- release visibility

### Report field

A report field is an extracted structured value from a report. Examples:

- hemoglobin
- glucose
- platelet count
- cholesterol
- total WBC count

Each field can contain:

- raw name
- normalized name
- value
- numeric value
- unit
- reference range
- confidence
- status
- HITL reason
- collection date

### Assignment

Assignments link doctors and patients. They determine whether a doctor can access patient reports, analytics, and query tools.

### HITL

HITL means human-in-the-loop. In HDIMS, this is the doctor review layer used when automatic extraction is not sufficiently reliable or when manual verification is required.

## User Roles

### Patient

Patients can:

- Sign up and log in.
- Upload their own reports.
- Track upload and processing status.
- View patient-visible reports.
- View extracted report fields.
- View analytics and trends.
- Use guided patient chat.
- View notifications.
- View account/profile information.
- Copy patient UID.
- Log out.

Patients cannot:

- Verify report fields.
- Edit extracted medical values.
- Access doctor routes.
- Access admin routes.
- Access another patient's reports.
- View internal pipeline errors or stack traces.

### Doctor

Doctors can:

- Sign up with license number and specialization.
- Wait for admin approval.
- Access doctor tools only after verification is approved.
- Search assigned patients.
- Upload reports for registered patients.
- Upload reports for pending/unregistered patient emails.
- View reports for assigned or uploaded patients.
- View raw report files through protected doctor routes.
- Edit extracted fields before report verification.
- Verify a report at report level.
- Unlock a verified report when correction is needed.
- View HITL queue.
- View patient-specific analytics.
- Use floating guided AI assistant.
- View notifications.
- Manage account/logout.

Doctors cannot:

- Access admin-only governance.
- Bypass assignment checks.
- Access unrelated private patient records.
- Modify audit logs.
- See provider secrets or internal stack traces.

### Admin

Admins can:

- View platform dashboard/stats.
- List and manage users.
- List doctors and patients.
- Approve, reject, or suspend doctors.
- Assign doctors to patients.
- View reports and failed jobs.
- View HITL queue.
- View analytics.
- View and mark notifications.
- View audit logs.
- View system health.
- View settings.
- Trigger password resets.
- Activate/deactivate users.
- Log out.

Admins should not use patient or doctor clinical flows as a replacement for role-scoped behavior.

## Report Lifecycle

The report lifecycle is the main state machine used by the app.

| Status | Meaning |
| --- | --- |
| `uploaded` | File was saved, but OCR/AI processing has not started yet. |
| `processing` | OCR, extraction, validation, and confidence checks are running. |
| `auto_approved` | AI extraction passed confidence checks and does not require manual review. |
| `hitl_required` | One or more values need doctor/HITL review. |
| `verified` | A doctor verified the report. |
| `released` | The report is finalized and visible to the patient, when release workflow is used. |
| `failed` | OCR/AI processing failed or timed out. |

Patient-facing failure messages must stay non-technical. The UI should show messages like:

```text
Report processing failed. Please try again or upload a clearer document.
```

It should not show raw OCR exceptions, provider errors, OpenAI errors, stack traces, or infrastructure details.

## High-Level Data Flow

### Patient upload

```text
Patient selects a file
  -> frontend sends POST /patient/upload
  -> upload_service validates file
  -> file is saved under STORAGE_PATH
  -> reports row is created
  -> document_jobs row is created
  -> report lifecycle becomes processing
  -> Pipeline A task is scheduled
  -> frontend redirects to reports page
  -> React Query polling refreshes report status
  -> extracted fields become visible after processing and visibility rules pass
```

### Doctor upload

```text
Doctor selects upload flow
  -> registered patient: submit patient UID
  -> unregistered patient: submit pending patient email
  -> POST /doctor/upload
  -> report is linked to patient or pending patient identity
  -> Pipeline A processes report
  -> doctor can review report fields
  -> doctor can verify report
```

### Analytics

```text
Structured report_fields
  -> SQL analytics query
  -> numeric parsing
  -> reference range parsing
  -> abnormal status calculation
  -> trend grouping by field name
  -> frontend Recharts visualizations
```

Important: chart values come from the database, not from an LLM.

### Chat

```text
Guided context selection
  -> patient/report/general or doctor patient/global mode
  -> backend scopes query
  -> retrieval/trend/reasoning service uses scoped records
  -> assistant returns patient-safe or doctor-oriented explanation
```

## Authentication and Authorization

### Backend auth

Auth routes are mounted under `/auth`.

The backend uses:

- bcrypt password hashing
- JWT access tokens
- `get_current_user`
- role guards
- approved doctor guard

The token payload includes:

- `sub`: user id
- `role`
- `email`

### Frontend auth state

The frontend uses Zustand persistence in:

```text
frontend/src/store/authStore.ts
```

The persisted shape is:

```ts
{
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
}
```

This full-user model is important because the app depends on:

- `state.user`
- `user.role`
- `user.full_name`
- `user.email`
- `user.patient_uid`
- `user.verification_status`

### Axios auth

The Axios client is in:

```text
frontend/src/api/client.ts
```

It attaches:

```text
Authorization: Bearer {token}
```

to authenticated requests.

### Route protection

Frontend protected routes enforce role access:

- patient routes require `role === "patient"`
- doctor routes require `role === "doctor"`
- admin routes require `role === "admin"`

Backend role guards are still the source of truth.

## Frontend Architecture

The frontend is a Vite React application.

Important directories:

```text
frontend/src/api
```

Defines API functions. These should match backend product routes exactly.

```text
frontend/src/hooks
```

Wraps API calls with TanStack Query and mutations.

```text
frontend/src/pages
```

Contains route-level pages.

```text
frontend/src/components
```

Contains reusable UI, charts, assistant panels, report cards, sidebars, and layout pieces.

```text
frontend/src/types
```

Contains TypeScript DTOs that mirror backend response shapes.

```text
frontend/src/validation
```

Contains Zod schemas for auth/signup form validation.

### React Query strategy

React Query is used for:

- reports
- report detail
- fields
- EDA
- trends
- analytics
- notifications
- assignments
- admin lists

Processing reports are polled until final status:

- reports list polling while `uploaded` or `processing`
- report detail polling while `uploaded` or `processing`

### UI rules followed by the app

The app prefers:

- role-specific sidebars
- compact clinical layouts
- status badges
- tables for repeated operational data
- cards for repeated report/field items
- Recharts for analytics
- lucide-react icons
- inline user-friendly errors

The app avoids:

- raw backend stack traces
- fake chart values
- public raw file links
- patient access to doctor/admin tools

## Backend Architecture

`main.py` creates the FastAPI app and includes routers from:

- Pipeline A direct routes
- Auth routes
- Admin product routes
- Doctor product routes
- Patient product routes
- User routes
- Legacy Pipeline B direct routes

Product-layer API files live in:

```text
product/api/
```

Business logic lives in:

```text
product/services/
```

Shared database models live in:

```text
shared/db/models/
```

### Product services

Important services:

| File | Purpose |
| --- | --- |
| `auth_service.py` | Signup, login, token refresh, logout, audit entries. |
| `upload_service.py` | Upload/reupload, duplicate checks, file storage, report/job creation, background task scheduling. |
| `report_service.py` | Report detail, doctor access checks, raw report file access, SQL analytics, EDA. |
| `verification_service.py` | Field status, field edit, report verify/unlock, verification audit. |
| `assignment_service.py` | Doctor-patient assignment creation and approval/rejection. |
| `notification_service.py` | Notification creation/listing/read state. |
| `admin_service.py` | Admin dashboard, users, doctors, patients, assignments, reports, failed jobs, HITL, audit logs, health. |
| `search_service.py` | Patient report search and doctor patient search. |

## Pipeline A: OCR and Extraction

Pipeline A converts files into structured medical fields.

### Purpose

Pipeline A is responsible for:

- loading uploaded files
- validating supported document formats
- OCR
- LLM-based field extraction
- field normalization
- confidence scoring
- conflict resolution
- deciding auto approval vs HITL
- persisting extracted fields
- updating report lifecycle status

### Document types

Pipeline A expects medical document type enum values such as:

- `lab_report`
- `prescription`
- `discharge_summary`
- `radiology`
- `unknown`

Upload services should pass a valid document type, normally `unknown` unless a real medical classification exists. MIME types such as `application/pdf` should not be passed as document type.

### Pipeline A flow

```text
Upload saved
  -> document_jobs row created
  -> Pipeline A task starts
  -> loader reads file
  -> OCR extracts text
  -> LLM extracts structured fields
  -> normalization standardizes names/values
  -> matching resolves synonyms
  -> confidence scoring checks reliability
  -> conflict resolver decides field/report status
  -> report_fields are saved
  -> report lifecycle is updated
  -> notifications/audit records are written
```

### HITL decision

Reports can become `hitl_required` when:

- one or more fields have low confidence
- extraction is inconsistent
- abnormality/conflict checks require review
- document quality is poor
- pipeline validation thresholds are not met

Reports can become `auto_approved` when extraction confidence is sufficient.

### Failure handling

If Pipeline A fails, the system should:

- write traceback/error details to `document_jobs.error_message`
- update `document_jobs.status` to `failed`
- update `reports.lifecycle_status` to `failed`
- avoid leaving reports stuck in `processing`
- show only patient-safe errors in patient UI

## Pipeline B: Retrieval, Trends, Analytics, and AI Chat

Pipeline B powers:

- patient chat
- doctor query assistant
- retrieval
- trend analysis
- SQL/vector-backed analytics
- AI explanations

### Patient records adapter

Pipeline B reads report outputs through:

```text
pipeline_b/adapters/pipeline_a_adapter.py
```

This converts stored document jobs and report fields into `PatientRecord` and `ClinicalField` objects.

### Query classification

Queries can be classified as:

- retrieval
- reasoning
- trend
- patient chat

The app uses guided UI first to reduce ambiguous prompts.

### Patient chat

Patient chat supports:

- `Discuss a specific report`
- `General Health discussion`

Specific report mode scopes backend data to the selected report's `job_id`.

General mode uses the patient's stored report history.

Patient responses are educational and must not diagnose, prescribe, or invent medical history.

### Doctor assistant

The doctor assistant is a floating assistant, not a sidebar route.

Initial options:

- Patient-Specific Mode
- Global Analytics Mode

Patient-specific mode then asks for patient context and supports:

- Report Discussion
- Trend Analysis
- Abnormality Review
- Free Chat

Global analytics mode supports:

- Population Trends
- Operational Analytics
- OCR Failure Analysis
- Free Analytics Query

Retrieval must be role-scoped before any AI or vector search.

## Patient Flow

### Signup

Patient signup collects:

- full name
- email
- password
- date of birth
- sex
- phone
- optional medical/profile fields

The frontend keeps date of birth and calculates/derives age as needed. It should not require both age and date of birth from the user.

Patient signup payload uses backend-compatible values:

```json
{
  "email": "patient@example.com",
  "password": "StrongPassword123",
  "role": "patient",
  "full_name": "Patient Name",
  "phone_number": "9999999999",
  "date_of_birth": "1995-04-12",
  "sex": "female",
  "claim_patient_uid": null
}
```

Important patient signup rules:

- `sex` must be `male`, `female`, or `other`.
- Empty date of birth should be sent as `null`.
- Empty `claim_patient_uid` should be sent as `null` or omitted.
- Fake fallback dates must never be sent.

### Dashboard

Patient dashboard shows:

- patient name or identity summary
- patient ID
- report summary cards
- recent reports
- notifications preview
- health trends snapshot

### Reports

Patient reports page supports:

- report search
- filtering
- report lifecycle badges
- upload/reupload where allowed
- click-through to report detail

### Report detail

Patient report detail shows:

- report metadata
- extracted fields
- status badges
- AI summary/explanation copy
- EDA/insight section where available
- verification information

Patients do not see doctor edit controls.

### Trends

Patient trends page uses the same structured analytics dashboard component as doctor patient analytics.

It shows:

- tracked fields
- trend-ready fields
- total data points
- abnormal latest values
- critical changes
- insufficient data
- longitudinal charts
- reference range shading
- single-report reference checks

### Chat Assistant

Patient chat opens with guided options:

1. Discuss a specific report.
2. General Health discussion.

Only after context selection does the free-form input become active.

### Account

Patient account page shows:

- personal information
- patient UID
- copy patient UID
- account/system information
- placeholder password change
- logout

## Doctor Flow

### Signup

Doctor signup requires:

- full name
- email
- password
- phone
- specialization
- license number

Specialization options in the frontend:

- General Physician
- Cardiologist
- Neurologist
- Dermatologist
- Orthopedic Surgeon
- Pediatrician
- Gynecologist
- Psychiatrist
- Radiologist
- Oncologist

Example doctor signup:

```json
{
  "email": "doctor@example.com",
  "password": "StrongPassword123",
  "role": "doctor",
  "full_name": "Doctor Name",
  "phone_number": "9999999999",
  "license_number": "MED-12345",
  "specialization": "General Physician"
}
```

After signup:

- doctor verification status becomes `pending_verification`
- doctor sees verification waiting page
- admin must approve doctor before protected doctor tools work

### Doctor dashboard

Doctor dashboard shows:

- doctor identity/status
- workflow summary cards
- HITL/pending work
- recent report activity
- analytics snapshot

### Doctor reports

Doctors can:

- search reports
- open report detail
- view raw report file
- view all extracted fields
- edit field values before/after unlock
- verify report at report level
- unlock verified report for correction

Field-level verification exists in API support, but current product workflow is report-level verification for doctor efficiency.

### Doctor upload

Doctor upload supports:

- upload for registered patient by patient UID
- upload for unregistered patient email when "Patient not registered" is selected

Pending patient email records should not block future patient signup. When a patient later signs up with the same email, pending reports can be linked to the new account.

### Doctor patient analytics

Navigation flow:

```text
Doctor sidebar -> Analytics -> Select Patient -> /doctor/patients -> patient detail -> Analytics tab
```

The analytics tab uses DB-derived structured values only.

### Doctor floating AI assistant

The doctor assistant:

- is globally available on doctor pages
- floats at bottom-right
- opens as an overlay
- does not force route navigation
- starts with guided options
- scopes retrieval before free chat
- separates patient-specific and global analytics modes

## Admin Flow

Admin pages include:

- Dashboard
- Users
- Doctors
- Patients
- Assignments
- Reports
- Failed Jobs
- HITL Queue
- Analytics
- Notifications
- Audit Logs
- System Health
- Settings
- Logout

Admin can approve doctors through:

```text
PUT /admin/doctors/{doctor_id}/approve
```

Admin can reject doctors through:

```text
PUT /admin/doctors/{doctor_id}/reject
```

Admin can suspend doctors through:

```text
PUT /admin/doctors/{doctor_id}/suspend
```

## Report Naming

Uploaded local filenames are not ideal for clinical UI. HDIMS generates a display report name from:

- patient name
- report type
- patient UID

Example:

```text
Patient_Blood_Report_PAT-00005
```

The backend adds:

- `display_report_name`
- `patient_name`
- `patient_uid`

The frontend uses:

```text
frontend/src/lib/reportName.ts
```

to prefer `display_report_name` and fall back safely when patient metadata is missing.

## Analytics and Visualization Logic

Analytics are calculated from structured DB fields, not LLM-generated values.

The main analytics service is:

```text
product/services/report_service.py
```

Function:

```text
get_patient_sql_analytics(...)
```

It:

- reads `report_fields`
- joins patient reports
- parses numeric values
- parses reference ranges
- groups values by field name
- sorts report values by actual report date ascending
- computes trend direction
- computes percent change
- identifies abnormal latest values
- separates stable, critical, and insufficient data
- returns chart-ready JSON

The frontend visualization component is:

```text
frontend/src/components/charts/PatientAnalyticsDashboard.tsx
```

It renders:

- overview cards
- abnormal findings
- stable parameters
- missing/insufficient data
- longitudinal line charts
- reference range shading
- single-value reference range cards

### Reference range shading

Green shaded areas on charts represent the report's stored reference range or normal range for that lab parameter.

If no green range appears, it usually means:

- no reference range was extracted
- the reference range could not be parsed into numeric min/max
- reference ranges differ across reports, so dashed reference lines are used instead
- the field has only non-numeric or incomplete data

### X-axis dates

Charts use actual report dates derived from:

1. extracted field `collection_date`, when available
2. report `first_uploaded_at`, as fallback

Dates are formatted clinically as:

- `DD/MM/YYYY`

Values are sorted ascending so the newest report appears on the right.

## Notifications

Notifications are role-scoped.

Notification events include:

- report uploaded
- processing completed
- report released
- HITL required
- failed processing
- assignment updates
- system/admin notifications

Frontend notification bell and pages use:

- patient notifications under `/patient/notifications`
- doctor notifications under `/doctor/notifications`
- admin notifications under `/admin/notifications`

## Audit Logging

Audit logs are stored for sensitive actions.

Examples:

- signup
- login
- logout
- token refresh
- upload
- reupload
- report view
- raw report view
- field edit
- report verification
- unlock report
- assignment actions
- admin doctor approval/rejection/suspension

Audit logs are important for clinical traceability and security review.

## API Routes

### Health

```text
GET /health
```

### Auth

```text
POST /auth/signup
POST /auth/login
POST /auth/refresh
POST /auth/logout
```

### User

```text
GET /users/me
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
GET  /patient/analytics

GET  /patient/notifications
PUT  /patient/notifications/{notification_id}/read
```

Note: patient field verification route exists but returns 403 because patients are not allowed to verify medical fields.

### Doctor

```text
POST /doctor/upload
PUT  /doctor/reports/{report_id}/reupload
GET  /doctor/reports/search
GET  /doctor/reports/{report_id}
GET  /doctor/reports/{report_id}/raw-file
POST /doctor/reports/{report_id}/release
POST /doctor/reports/{report_id}/verify
POST /doctor/reports/{report_id}/unlock
GET  /doctor/reports/{report_id}/fields
POST /doctor/reports/{report_id}/fields/{field_name}/verify
POST /doctor/reports/{report_id}/fields/{field_name}/edit

POST /doctor/assignments
GET  /doctor/assignments
PUT  /doctor/assignments/{assignment_id}/approve
PUT  /doctor/assignments/{assignment_id}/reject

POST /doctor/query
GET  /doctor/patients/{patient_id}/trend
GET  /doctor/patients/{patient_id}/analytics
GET  /doctor/patients/search

GET  /doctor/notifications
PUT  /doctor/notifications/{notification_id}/read
```

### Admin

```text
GET  /admin/stats
GET  /admin/dashboard
GET  /admin/users
GET  /admin/doctors
GET  /admin/patients
GET  /admin/users/{user_id}

POST /admin/assignments
GET  /admin/assignments

GET  /admin/reports
GET  /admin/failed-jobs
GET  /admin/hitl-queue
GET  /admin/analytics

GET  /admin/notifications
PUT  /admin/notifications/{notification_id}/read

GET  /admin/audit-logs
GET  /admin/system-health
GET  /admin/settings

POST /admin/password-reset
PUT  /admin/users/{user_id}/deactivate
PUT  /admin/users/{user_id}/activate

PUT  /admin/doctors/{doctor_id}/approve
PUT  /admin/doctors/{doctor_id}/reject
PUT  /admin/doctors/{doctor_id}/suspend
```

### Direct Pipeline A routes

These are mounted for lower-level pipeline access:

```text
POST /api/v1/documents/upload
GET  /api/v1/documents/{job_id}/status
POST /api/v1/documents/{job_id}/hitl-review
```

### Legacy direct Pipeline B routes

These routes are still mounted:

```text
POST /api/patient/query
GET  /api/patient/records
GET  /api/patient/report/{job_id}/explain

POST /api/doctor/query
GET  /api/doctor/patient/{patient_id}/summary
GET  /api/doctor/patient/{patient_id}/trend
GET  /api/doctor/analytics
```

Normal frontend navigation should use product routes instead of these legacy direct routes.

## Database and Migrations

Migrations live in:

```text
migrations/
```

Current migration files:

```text
001_product_layer_schema.sql
002_remove_structured_text.sql
003_fix_product_layer_schema_issues.sql
004_file_storage_refs.sql
005_file_storage_refs_version.sql
006_allow_failed_report_lifecycle_status.sql
007_patient_profile_fields.sql
008_doctor_profile_verification.sql
```

Apply them in sorted order.

Important tables include:

- `users`
- `reports`
- `document_jobs`
- `report_fields`
- `field_verifications`
- `doctor_patient_assignments`
- `notifications`
- `audit_log`

## Environment Variables

Copy:

```bash
cp .env.example .env
```

Important variables:

```env
OPENAI_API_KEY=your-openai-api-key
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/google-service-account.json

DATABASE_URL=postgresql://HDIMS_user:HDIMS_pass@localhost:5432/HDIMS
REDIS_URL=redis://localhost:6379/0

SECRET_KEY=replace-with-a-long-random-secret-at-least-32-characters
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=1440
JWT_REFRESH_EXPIRY_DAYS=7
RATE_LIMIT_STORAGE_URI=memory://

STORAGE_PATH=./storage
MAX_FILE_SIZE_MB=50

QDRANT_URL=
QDRANT_STORAGE_PATH=./qdrant_storage

VITE_API_URL=http://localhost:8000

OCR_CONFIDENCE_THRESHOLD=0.85
FIELD_CONFIDENCE_THRESHOLD=0.85
LAB_REPORT_CONFIDENCE_THRESHOLD=0.72
PRESCRIPTION_CONFIDENCE_THRESHOLD=0.80
FUZZY_MATCH_THRESHOLD=85
```

Never commit `.env`, service-account JSON files, API keys, uploaded reports, local vector storage, or database dumps.

## Local Setup

### Backend setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Create the database:

```bash
createdb HDIMS
```

Apply migrations:

```bash
for file in migrations/*.sql; do psql "$DATABASE_URL" -f "$file"; done
```

Start Redis:

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

API locations:

```text
http://localhost:8000
http://localhost:8000/docs
```

### Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend location:

```text
http://localhost:5173
```

### Docker setup

The repository includes Docker Compose support:

```bash
docker compose -f infra/docker/docker-compose.yml up --build
```

## Admin Seed

For local development, create the default admin:

```bash
python seed_admin.py
```

The current seed script creates:

```text
Email:    admin@HDIMS.com
Password: Admin@123
Name:     System Admin
```

Change this password before using any shared or deployed environment.

## Development Commands

Backend compile check:

```bash
python3 -m compileall main.py product pipeline_a pipeline_b shared
```

Backend tests:

```bash
pytest
```

Frontend TypeScript:

```bash
cd frontend
npx tsc --noEmit
```

Frontend lint:

```bash
cd frontend
npm run lint
```

Frontend production build:

```bash
cd frontend
npm run build
```

Frontend preview:

```bash
cd frontend
npm run preview
```

## Testing and Verification

### Upload verification

Test:

- PDF
- PNG
- JPG/JPEG
- TIFF if supported by loader/OCR path

Expected flow:

```text
uploaded -> processing -> auto_approved / hitl_required / verified / failed
```

No report should remain stuck indefinitely in `processing`.

### Patient verification

Check:

- patient signup
- patient login
- upload
- reports list
- report detail
- extracted fields
- trends page
- patient chat specific report mode
- patient chat general mode
- account page
- logout

### Doctor verification

Check:

- doctor signup
- pending verification screen
- admin approval
- doctor login after approval
- doctor dashboard
- patient search
- doctor upload
- report detail
- raw report button
- field edit
- verify report
- unlock report
- patient analytics tab
- floating assistant

### Admin verification

Check:

- admin login
- dashboard
- users
- doctors
- approve/reject/suspend doctor
- patients
- assignments
- reports
- failed jobs
- HITL queue
- analytics
- notifications
- audit logs
- system health
- settings

## Security Notes

- Do not commit `.env`.
- Do not commit service account JSON files.
- Do not commit uploaded reports under `storage/`.
- Do not commit local Qdrant data under `qdrant_storage/`.
- Do not expose public file URLs for raw reports.
- Do not expose raw prompts, embeddings, vector DB internals, or provider secrets.
- RBAC must execute before retrieval or vector search.
- Patient APIs must only return the authenticated patient's data.
- Doctor APIs must enforce doctor-patient assignment or uploader access.
- Admin APIs must require admin role.
- Patient UI must never show raw pipeline exceptions.
- Doctor UI may show limited operational errors, but not provider credentials or stack traces.
- Production deployment should use HTTPS, strict CORS, secure cookies or hardened token storage, backups, monitoring, and centralized secret management.

If files were accidentally tracked before `.gitignore` was updated, untrack them without deleting local copies:

```bash
git rm --cached -r storage qdrant_storage
git rm --cached .env
```

## Known Implementation Notes

- `main.py` currently mounts both product routes and legacy direct pipeline routes. The frontend should use product routes for normal app behavior.
- `main.py` also contains a local Google credentials path assignment. Replace this with environment-only configuration before deployment.
- The project is an active prototype. Treat production use as requiring additional clinical, security, privacy, and infrastructure review.
- AI explanations are educational support. They are not final diagnosis, prescription, or treatment recommendation.
- Analytics chart values must remain DB-derived. LLMs may explain trends but must not generate numeric graph values.

## Future Scope

Possible future improvements:

- appointment booking
- doctor-patient messaging
- downloadable structured health summaries
- FHIR/EMR/EHR integration
- stronger versioned report archive
- OCR bounding-box highlighting
- synchronized raw report and extracted field view
- annotation/comment workflow
- collaborative doctor review
- more robust vector retrieval with strict RBAC filters
- multilingual support
- voice assistant
- wearable integration
- medication reminders
- cloud backup
- production observability and alerting

## Current Status

HDIMS currently includes patient, doctor, and admin frontend flows; product-layer FastAPI routes; JWT authentication; report upload and reupload; OCR/LLM processing; structured field extraction; report-level doctor verification; analytics visualization; guided patient chat; floating doctor assistant; notifications; assignments; audit logs; and admin governance screens.

It is suitable as an academic/product prototype and a strong base for a secure healthcare document intelligence system, but production deployment needs hardened security, privacy review, clinical validation, operational monitoring, and formal compliance work.
