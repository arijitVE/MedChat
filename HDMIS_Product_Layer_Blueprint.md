# HDIMS Product Layer — Implementation Blueprint v5
### Auth, Verification, Upload, Assignment & Lifecycle Management
### ⚠️ UPDATED — Duplicate detection hardened + 5 remaining issues resolved

---

## CHANGE LOG (v1 → v2 → v3)

### v2 fixes (carried forward)

| # | Issue | Fix Applied |
|---|-------|-------------|
| 2 | `UNIQUE(report_id, field_name, verifier_role)` blocked re-edits & lost history | Removed UNIQUE constraint; latest row = current state, all rows = audit history |
| 3 | `is_locked=TRUE` conflicted with field-level locking law | Removed hard report lock; `lifecycle_status='fully_verified'` is the soft state |
| 4 | HITL fields visible to patient with value exposed | `status==hitl` → hide value, show "Verification required" |
| 5 | Patient signup linked only by email | Added `patient_uid` claim flow as fallback |
| 6 | No rate limiting on auth or upload endpoints | Added login attempt limit + upload rate limit spec |
| 7 | Storage path missing versioning | Path now `storage/{patient_id}/{report_id}/v{upload_count}/original_file` |
| 8 | Cross-patient analytics positioning needed strengthening | Explicit rules: SQL only, numeric_value, aggregation, never LLM; report ownership = patient |

### v3 fixes (carried forward)

| # | Issue | Fix Applied |
|---|-------|-------------|
| 9 | Duplicate detection was too weak then removed entirely | Hybrid detection: SHA-256 exact match (hard block) + metadata similarity (soft warn) |

### v4 fixes (carried forward)

| # | Issue | Fix Applied |
|---|-------|-------------|
| 9a | Re-upload with same file triggered TIER 1 block — logical contradiction | Skip TIER 1 when re-uploading the same report_id; same-file re-upload is intentional |
| 9b | TIER 2 used `file_name` exact match — unreliable ("report.pdf", "scan.jpg") | Replace with: same file extension + same inferred `document_type` + size ±3% + 72h window |
| 9c | Analytics had no deduplication rule — forced/probable duplicates would skew aggregates | All cross-patient analytics queries must deduplicate on `(patient_id, collection_date, field_name)` using `DISTINCT ON` or `ROW_NUMBER()` |
| 9d | No index for TIER 2 metadata query — slow scan at scale | Added `idx_reports_metadata_dup ON reports(patient_id, document_type, file_size_bytes, first_uploaded_at)` |
| 9e | SHA-256 over full bytes in memory — memory spike at 50MB × concurrent uploads | Switch to streaming chunked hash computation via `hashlib` update loop |
| 9f | TIER 1 409 response lacked uploader context — ambiguous when two doctors upload same file | 409 body now includes `uploaded_by_role`, `uploaded_by_user_id`, `uploaded_at` of existing report |
| minor-1 | No DB flag to mark forced/probable duplicates — analytics must filter blind | Added `is_duplicate BOOLEAN DEFAULT FALSE` and `duplicate_of UUID NULL` to reports table |
| minor-2 | EXACT_DUPLICATE_BLOCKED event not logged — only override was logged | Added `EXACT_DUPLICATE_BLOCKED` audit event before returning 409 |
| minor-3 | UI flow for 409 not specified | 409 response shape designed to drive UI: "Use existing" vs "Force upload" actions |

### v5 fixes (this version)

| # | Issue | Fix Applied |
|---|-------|-------------|
| 10 | `document_type` timing gap — TIER 2 useless at upload time because `document_type='unknown'` | Split into `upload_document_type` (MIME/magic bytes, available immediately) and `inferred_document_type` (set by Pipeline A). TIER 2 uses `upload_document_type` as primary. |
| 11 | `duplicate_of` ambiguity — arbitrary pick when multiple matches exist in 72h window | Explicit selection rule: `ORDER BY first_uploaded_at DESC LIMIT 1` (most recent matching report). Documented in TIER 1 and TIER 2 query specs. |
| 12 | Analytics dedup ORDER BY edge case — stale original prioritized over corrected duplicate | Refined to: `ORDER BY is_duplicate ASC, last_edited_at DESC NULLS LAST, first_uploaded_at DESC`. Corrected/re-uploaded data wins. |
| 13 | No deduplication at ingestion layer — duplicates filtered only at query time | Optional: `on_pipeline_a_complete` re-evaluates TIER 2 with `inferred_document_type` and updates `is_duplicate` flags. Performance optimization, not mandatory. |
| 14 | Concurrency edge case — two simultaneous uploads of same file both pass TIER 1 | Accept race condition at current scale (analytics dedup handles it). Documented `SELECT FOR UPDATE` as future option for strict mode. |

---

## AGENT INSTRUCTIONS — READ BEFORE WRITING ANY CODE

> This is the authoritative specification for the Product Layer of the HDIMS system.
> Pipeline A (extraction) and Pipeline B (intelligence) are already built and tested.
> Do NOT modify any existing Pipeline A or Pipeline B code.
> This layer wraps around both pipelines — it does not replace or modify them.

### What This Layer Does

Pipeline A extracts structured fields from medical documents.
Pipeline B provides retrieval, reasoning, and trend analysis.
The Product Layer adds: authentication, role-based access, verification lifecycle,
file storage, doctor-patient assignment, notifications, audit logging, and the
React frontend API contracts.

### The Golden Rules

1. **Never modify `pipeline_a/` or `pipeline_b/` code.** If you need Pipeline A to do
   something new, add a hook in the product layer that calls Pipeline A — do not edit
   Pipeline A internals.
2. **Pipeline B is called by the product layer, not the other way around.** The product
   layer routes requests to Pipeline B engines. Pipeline B knows nothing about users,
   roles, or auth.
3. **`structured_text_for_embedding` column must be removed.** It was a Pipeline A
   artifact before Qdrant existed. Now that Qdrant stores everything as vectors,
   this column is redundant. Remove it from `document_jobs` in the first migration.
4. **All DB writes go through the product layer.** Pipeline A writes extraction results.
   The product layer writes everything else — verification, assignment, auth, files.
5. **Field-level locking is the law.** Verification is per-field, not per-report.
   A doctor verifying field A does not lock field B.
6. **No LLM involvement in auth, routing, DB access, or numeric computation.**
   These rules carry forward from Pipeline B.
7. **Existing test data must survive migrations.** All new columns must have
   sensible defaults. No bare `NOT NULL` constraints on new columns without defaults.
8. **Cross-patient analytics must run on SQL — never LLM.**
   Use `numeric_value` column + aggregation queries only. The analytics engine is
   a SQL engine, not a reasoning engine.
9. **Report ownership is always the patient.** Even when a doctor uploads,
   `primary_owner = patient`. The patient retains data rights.

---

### Mandatory Folder Structure

```
HDIMS/
│
├── shared/                          → Already exists — do NOT modify
├── pipeline_a/                      → Already exists — do NOT modify
├── pipeline_b/                      → Already exists — do NOT modify
│
├── product/
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt_handler.py           → JWT encode/decode, token expiry
│   │   ├── password.py              → bcrypt hash + verify
│   │   ├── middleware.py            → FastAPI auth dependency: get_current_user()
│   │   └── role_guard.py           → require_role(role) decorator
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py                  → SignupRequest, LoginRequest, TokenResponse
│   │   ├── user.py                  → UserProfile, DoctorProfile, PatientProfile
│   │   ├── assignment.py            → AssignmentRequest, AssignmentResponse
│   │   ├── report.py                → ReportUploadRequest, ReportStatusResponse
│   │   ├── verification.py          → FieldVerificationRequest, VerificationResponse
│   │   ├── notification.py          → NotificationItem, NotificationList
│   │   └── admin.py                 → AdminStats, HITLQueueItem
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── user.py              → users table
│   │       ├── assignment.py        → doctor_patient_assignments table
│   │       ├── report.py            → reports table (wraps document_jobs)
│   │       ├── verification.py      → field_verifications table
│   │       ├── audit.py             → audit_log table
│   │       ├── notification.py      → notifications table
│   │       └── file_ref.py          → file_storage_refs table
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py          → signup, login, token refresh, password reset
│   │   ├── assignment_service.py    → create, approve, reject assignments
│   │   ├── upload_service.py        → file save, Pipeline A trigger, re-upload logic
│   │   ├── verification_service.py  → field verify, lock, audit trail
│   │   ├── report_service.py        → report status, release to patient
│   │   ├── notification_service.py  → create, read, mark-read notifications
│   │   ├── search_service.py        → patient search, report search
│   │   └── admin_service.py         → stats, HITL queue, password reset
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth_routes.py           → /auth/signup, /auth/login, /auth/refresh
│   │   ├── doctor_routes.py         → /doctor/* all doctor endpoints
│   │   ├── patient_routes.py        → /patient/* all patient endpoints
│   │   └── admin_routes.py          → /admin/* all admin endpoints
│   │
│   └── utils/
│       ├── __init__.py
│       ├── file_storage.py          → save/delete/path resolution for report files
│       └── pagination.py            → standard paginated response wrapper
│
├── migrations/
│   ├── 001_product_layer_schema.sql → All new tables in one migration
│   └── 002_remove_structured_text.sql → Drop structured_text_for_embedding column
│
├── tests/
│   └── product/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_assignment.py
│       ├── test_upload.py
│       ├── test_verification.py
│       └── test_admin.py
│
├── storage/                         → Raw report files on disk
│   └── {patient_id}/
│       └── {report_id}/
│           └── v{upload_count}/     ← FIX #7: versioned storage
│               └── original_file.{ext}
│
└── frontend/                        → React app (Phase 7 — last)
    ├── src/
    └── package.json
```

---

## 1. Database Schema (All Tables — One Migration)

> **CRITICAL:** Run `migrations/001_product_layer_schema.sql` as a single migration.
> Do not split into separate migrations — cross-table foreign keys will fail.
> All new columns on existing tables must have defaults to protect existing test data.

### Table: users

```sql
CREATE TABLE users (
    user_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('doctor', 'patient', 'admin')),
    full_name       VARCHAR(255) NOT NULL,
    phone           VARCHAR(20),

    -- Doctor-specific
    license_number  VARCHAR(100),           -- NULL for patients/admins
    specialization  VARCHAR(100),

    -- Patient-specific (system-generated)
    patient_uid     VARCHAR(20) UNIQUE,     -- e.g. PAT-00001, NULL for doctors/admins
    date_of_birth   DATE,
    sex             VARCHAR(10),            -- male | female | other

    -- Account state
    is_registered   BOOLEAN DEFAULT TRUE,  -- FALSE for pre-registered patients
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_patient_uid ON users(patient_uid) WHERE patient_uid IS NOT NULL;
```

### Table: doctor_patient_assignments

```sql
CREATE TABLE doctor_patient_assignments (
    assignment_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id       UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    patient_id      UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    assigned_by     VARCHAR(20) NOT NULL CHECK (assigned_by IN ('admin', 'doctor', 'patient')),
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'active', 'rejected')),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (doctor_id, patient_id)
);

CREATE INDEX idx_assignments_doctor ON doctor_patient_assignments(doctor_id);
CREATE INDEX idx_assignments_patient ON doctor_patient_assignments(patient_id);
CREATE INDEX idx_assignments_status ON doctor_patient_assignments(status);
```

### Table: reports (product-layer wrapper over document_jobs)

```sql
-- FIX #3: Removed is_locked column.
-- Locking is field-level only. Report "lock" is expressed via lifecycle_status = 'fully_verified'.
-- FIX #7: upload_count drives versioned storage path.
-- FIX #9: primary_owner always = patient_id (even for doctor uploads).

CREATE TABLE reports (
    report_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id              VARCHAR(255) UNIQUE NOT NULL,  -- FK to document_jobs.job_id
    patient_id          UUID NOT NULL REFERENCES users(user_id),  -- primary_owner = patient
    uploaded_by         UUID NOT NULL REFERENCES users(user_id),
    doctor_id           UUID REFERENCES users(user_id),  -- assigned doctor at upload time

    -- File reference (points to current version)
    file_path           VARCHAR(500) NOT NULL,
    file_name           VARCHAR(255) NOT NULL,
    file_mime           VARCHAR(100) NOT NULL,
    file_size_bytes     INTEGER,
    -- FIX 10: Document type split — two separate fields to solve timing gap.
    -- upload_document_type: determined immediately from MIME/magic bytes at upload time.
    --   e.g. 'application/pdf', 'image/jpeg', 'image/png', 'image/tiff'
    --   Always available — used as PRIMARY key for TIER 2 duplicate detection.
    upload_document_type  VARCHAR(100) NOT NULL DEFAULT 'unknown',
    -- inferred_document_type: set by Pipeline A after semantic analysis.
    --   e.g. 'cbc', 'lipid_panel', 'xray', 'prescription', 'discharge_summary', 'unknown'
    --   Set to 'unknown' initially; updated by on_pipeline_a_complete hook.
    --   Used as FALLBACK by TIER 2 when available, and for search/filter UI.
    inferred_document_type VARCHAR(50) DEFAULT 'unknown',

    -- Lifecycle status
    -- FIX #3: 'fully_verified' is a SOFT state — not a hard lock.
    lifecycle_status    VARCHAR(30) NOT NULL DEFAULT 'uploaded'
                        CHECK (lifecycle_status IN (
                            'uploaded', 'processing', 'auto_approved',
                            'hitl_required', 'patient_verified',
                            'doctor_verified', 'fully_verified'
                        )),

    -- Release control
    released_to_patient BOOLEAN DEFAULT FALSE,
    -- TRUE automatically if patient uploaded
    -- Doctor-uploaded reports require explicit release

    -- Timestamps
    first_uploaded_at   TIMESTAMPTZ DEFAULT NOW(),
    last_edited_at      TIMESTAMPTZ,         -- set on re-upload

    -- FIX #7: upload_count used to build versioned storage path
    upload_count        INTEGER DEFAULT 1,

    -- FIX #9: Hybrid duplicate detection
    -- SHA-256 hex digest of raw file bytes, computed before any storage write.
    -- Used for exact-match duplicate detection across ALL reports for this patient.
    -- NULL for pre-v3 rows (safe — those rows predate this column).
    file_hash           VARCHAR(64),

    -- FIX minor-1 + FIX 11: Duplicate tracking flags.
    -- is_duplicate = TRUE when this report was created via ?force=true over a TIER 1 block,
    --               OR when TIER 2 fired (probable duplicate warning).
    -- duplicate_of = report_id of the MOST RECENT matching report (FIX 11).
    --   Selection rule: ORDER BY first_uploaded_at DESC LIMIT 1
    --   When multiple matches exist in the 72h window, always pick the newest.
    -- Used to filter duplicates from analytics aggregation queries.
    is_duplicate        BOOLEAN DEFAULT FALSE,
    duplicate_of        UUID REFERENCES reports(report_id)

    -- NOTE: is_locked REMOVED. Use lifecycle_status = 'fully_verified' as the soft state.
    -- Re-upload is blocked at the service layer by checking all fields are NOT doctor_verified.
);

CREATE INDEX idx_reports_patient ON reports(patient_id);
CREATE INDEX idx_reports_doctor ON reports(doctor_id);
CREATE INDEX idx_reports_job ON reports(job_id);
CREATE INDEX idx_reports_status ON reports(lifecycle_status);
-- FIX #9: Hash index for O(1) exact duplicate lookup
CREATE INDEX idx_reports_hash ON reports(patient_id, file_hash) WHERE file_hash IS NOT NULL;
-- FIX 9d + FIX 10: Metadata index for TIER 2 similarity query
-- Uses upload_document_type (always available at upload time) instead of inferred_document_type
CREATE INDEX idx_reports_metadata_dup
    ON reports(patient_id, upload_document_type, file_size_bytes, first_uploaded_at)
    WHERE upload_document_type != 'unknown';
-- FIX 14: Concurrency note — no UNIQUE(patient_id, file_hash) constraint added.
-- Race condition where two simultaneous uploads of the same file both pass TIER 1
-- is accepted at current scale. Analytics dedup (FIX 9c/12) handles any duplicates
-- that slip through. For strict mode, use SELECT ... FOR UPDATE in a transaction.
```

### Table: field_verifications

```sql
-- FIX #2: UNIQUE constraint removed.
-- Multiple rows per (report_id, field_name) are ALLOWED — this is the audit history.
-- Latest row (MAX verified_at) = current state.
-- All rows = full edit history.
-- Upsert pattern replaced with plain INSERT.

CREATE TABLE field_verifications (
    verification_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id           UUID NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    job_id              VARCHAR(255) NOT NULL,       -- denormalized for fast queries
    field_name          VARCHAR(255) NOT NULL,       -- canonical name
    field_value         TEXT,                        -- value at time of verification

    -- Who verified
    verified_by         UUID NOT NULL REFERENCES users(user_id),
    verifier_role       VARCHAR(20) NOT NULL CHECK (verifier_role IN ('patient', 'doctor')),

    -- Verification type
    verification_type   VARCHAR(20) NOT NULL
                        CHECK (verification_type IN ('approved', 'edited', 'rejected')),

    -- If edited, store the new value
    edited_value        TEXT,                       -- NULL if approved without edit
    edit_reason         TEXT,

    -- Is this the final (doctor) verification?
    is_final            BOOLEAN DEFAULT FALSE,       -- TRUE only for doctor verifications

    verified_at         TIMESTAMPTZ DEFAULT NOW()

    -- NO UNIQUE CONSTRAINT — multiple rows allowed per field.
    -- To get current state: SELECT ... ORDER BY verified_at DESC LIMIT 1
    -- To get history: SELECT ... ORDER BY verified_at ASC
);

CREATE INDEX idx_fv_report ON field_verifications(report_id);
CREATE INDEX idx_fv_field ON field_verifications(report_id, field_name);
-- FIX #2: Index for fetching latest per field efficiently
CREATE INDEX idx_fv_field_time ON field_verifications(report_id, field_name, verified_at DESC);
CREATE INDEX idx_fv_final ON field_verifications(is_final) WHERE is_final = TRUE;
```

### Table: audit_log

```sql
CREATE TABLE audit_log (
    log_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(user_id),
    user_role       VARCHAR(20),
    action          VARCHAR(50) NOT NULL,
    -- Actions: UPLOAD | RE_UPLOAD | VERIFY_FIELD | EDIT_FIELD |
    --          ASSIGN_DOCTOR | APPROVE_ASSIGNMENT | REJECT_ASSIGNMENT |
    --          RELEASE_REPORT | VERIFICATION_RESET | PASSWORD_RESET |
    --          LOGIN | LOGOUT | SIGNUP
    entity_type     VARCHAR(50),   -- report | field | assignment | user
    entity_id       VARCHAR(255),  -- report_id, field_name, assignment_id, etc.
    report_id       UUID REFERENCES reports(report_id),
    field_name      VARCHAR(255),
    old_value       TEXT,
    new_value       TEXT,
    metadata        JSONB,         -- any extra context
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_report ON audit_log(report_id);
CREATE INDEX idx_audit_action ON audit_log(action);
CREATE INDEX idx_audit_created ON audit_log(created_at);
```

### Table: notifications

```sql
CREATE TABLE notifications (
    notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_id    UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    sender_id       UUID REFERENCES users(user_id),
    type            VARCHAR(50) NOT NULL,
    -- Types: REPORT_UPLOADED | REPORT_PROCESSED | REPORT_RELEASED |
    --        FIELD_VERIFIED | PATIENT_VERIFIED | DOCTOR_VERIFIED |
    --        ASSIGNMENT_REQUEST | ASSIGNMENT_APPROVED | ASSIGNMENT_REJECTED |
    --        HITL_REQUIRED | RE_UPLOAD_DONE
    title           VARCHAR(255) NOT NULL,
    message         TEXT NOT NULL,
    report_id       UUID REFERENCES reports(report_id),
    is_read         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notif_recipient ON notifications(recipient_id, is_read);
CREATE INDEX idx_notif_created ON notifications(created_at);
```

### Alter existing tables (Migration 001)

```sql
-- Add product-layer columns to document_jobs (Pipeline A table)
-- ALL with defaults to protect existing rows

ALTER TABLE document_jobs
    ADD COLUMN IF NOT EXISTS uploaded_by_user_id UUID,
    ADD COLUMN IF NOT EXISTS upload_source VARCHAR(20) DEFAULT 'unknown'
        CHECK (upload_source IN ('doctor', 'patient', 'system', 'unknown')),
    ADD COLUMN IF NOT EXISTS collection_date DATE;

-- Add indexes for cross-patient analytics (needed for cohort queries)
CREATE INDEX IF NOT EXISTS idx_rf_field_name ON report_fields(name);
CREATE INDEX IF NOT EXISTS idx_rf_patient ON report_fields(patient_id);
CREATE INDEX IF NOT EXISTS idx_rf_collection_date ON report_fields(collection_date);

-- numeric_value index enables "platelet count < 150" queries without full scan
ALTER TABLE report_fields
    ADD COLUMN IF NOT EXISTS numeric_value FLOAT;

-- Backfill numeric_value — clean Indian comma format first, then cast
UPDATE report_fields
SET numeric_value = CAST(REPLACE(value, ',', '') AS FLOAT)
WHERE REPLACE(value, ',', '') ~ '^[0-9]+\.?[0-9]*$';
```

### Migration 002 — Remove structured_text_for_embedding

```sql
-- Run AFTER migration 001 and AFTER Qdrant ingestion is confirmed working.
ALTER TABLE document_jobs DROP COLUMN IF EXISTS structured_text_for_embedding;
```

---

## 2. Authentication System

### JWT Design

```python
# product/auth/jwt_handler.py

TOKEN_EXPIRY_MINUTES = 60 * 24      # 24 hours
REFRESH_EXPIRY_DAYS = 7

def create_access_token(user_id: str, role: str, email: str) -> str:
    """
    Payload:
      sub: user_id
      role: doctor | patient | admin
      email: user email
      exp: expiry timestamp
    Sign with SECRET_KEY from settings.
    """

def decode_access_token(token: str) -> dict:
    """
    Decode and verify token.
    Raise HTTPException(401) if expired or invalid.
    Return payload dict.
    """

# product/auth/middleware.py

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Decode token → get user from DB.
    Raise 401 if invalid.
    Raise 403 if user is_active=False.
    This is the universal auth dependency — import in every protected route.
    """

# product/auth/role_guard.py

def require_role(*roles: str):
    """
    Usage: Depends(require_role("doctor", "admin"))
    Raises 403 if current user role not in roles.
    """
```

### FIX #6 — Rate Limiting

```python
# product/auth/rate_limit.py
# Use slowapi (wraps limits per IP) or a simple Redis counter.

# Login attempt limit: 5 attempts per 15 minutes per IP
LOGIN_RATE_LIMIT = "5/15minutes"

# Upload rate limit: 10 uploads per hour per user
UPLOAD_RATE_LIMIT = "10/hour"

# Apply as FastAPI middleware or per-route limiter:
#   @limiter.limit(LOGIN_RATE_LIMIT)
#   async def login(request: Request, ...):
#
# On limit exceeded → raise HTTPException(429, "Too many requests")
# Log the event to audit_log with action = RATE_LIMITED

# Add to .env:
# RATE_LIMIT_STORAGE_URI=redis://localhost:6379  (or memory:// for dev)
```

### Signup Flow

```
POST /auth/signup
body: {email, password, role, full_name, phone?, license_number?, date_of_birth?, sex?}

1. Check email not already registered
2. Hash password (bcrypt, cost factor 12)
3. Generate patient_uid if role == "patient" (PAT-XXXXX, auto-increment)
4. Create user row (is_registered=True)
5. Write SIGNUP audit log entry
6. Return TokenResponse (access_token + user_id + role)

Pre-registered patient signup:
  Priority 1 — patient_uid claim flow (FIX #5):
    If body contains claim_patient_uid:
      Find pre-registered user by patient_uid
      Verify email matches (or admin-issued UID without email)
      Activate: is_registered=True, set password_hash, full_name, etc.
      Write SIGNUP + ACCOUNT_ACTIVATED audit entries

  Priority 2 — email match fallback:
    If doctor previously uploaded a report for this email:
      Find pre-registered user by email
      Update: is_registered=True, set password_hash, full_name, etc.
      All reports uploaded for that email are now linked
      Write SIGNUP + ACCOUNT_ACTIVATED audit entries
```

### Login Flow

```
POST /auth/login
body: {email, password}

FIX #6: Rate limited — 5 attempts per 15 minutes per IP.

1. Find user by email
2. Verify password against hash
3. Check is_active=True
4. Write LOGIN audit log
5. Return TokenResponse
```

---

## 3. Doctor-Patient Assignment

### Assignment States

```
Admin assigns     → status = active  (no approval needed)
Doctor initiates  → status = pending → patient must approve
Patient initiates → status = pending → doctor must approve
```

### Assignment Service

```python
# product/services/assignment_service.py

def create_assignment(doctor_id, patient_id, initiated_by, db) -> Assignment:
    """
    Check: doctor_id user.role == 'doctor'
    Check: patient_id user.role == 'patient'
    Check: no existing active assignment for this pair
    If initiated_by == 'admin': status = active
    Else: status = pending
    Write ASSIGN_DOCTOR audit entry.
    Send notification to the other party.
    """

def approve_assignment(assignment_id, approving_user_id, db) -> Assignment:
    """
    Verify: approving_user is the pending party (not the initiator)
    Set status = active
    Write APPROVE_ASSIGNMENT audit entry.
    Send ASSIGNMENT_APPROVED notification to both parties.
    """

def reject_assignment(assignment_id, rejecting_user_id, db) -> Assignment:
    """
    Set status = rejected
    Write REJECT_ASSIGNMENT audit entry.
    """

def get_doctor_patients(doctor_id, db) -> list[PatientProfile]:
    """Return all patients with active assignment to this doctor."""

def get_patient_doctors(patient_id, db) -> list[DoctorProfile]:
    """Return all doctors with active assignment to this patient."""

def verify_doctor_patient_access(doctor_id, patient_id, db) -> bool:
    """Check if active assignment exists. Used in every doctor route."""
```

---

## 4. Report Upload System

### Upload Flow

```
POST /doctor/upload  OR  POST /patient/upload

FIX #6: Rate limited — 10 uploads per hour per user.

STEP 1 — File validation
  Accept: PDF, JPEG, PNG, TIFF
  Max size: 50MB
  Detect MIME from magic bytes (same as Pipeline A ingestion)
  Read all file bytes into memory now — needed for hash computation in STEP 3.

STEP 2 — Patient confirmation checkpoint (doctor uploads only)
  Doctor must provide: patient_uid OR patient email
  System resolves to patient_id

  FIX #5 — Lookup priority:
    1. Lookup by patient_uid (primary — unambiguous)
    2. Fallback to email lookup only if patient_uid not provided
    3. If not found by either → create pre-registered patient (email only, is_registered=False,
       auto-generate patient_uid, return patient_uid to doctor for handoff to patient)

  Confirm patient_id before proceeding (return 400 if provided patient_uid doesn't match resolved patient)

STEP 3 — FIX #9: Hybrid duplicate detection
  See Section 4a for full logic.
  Short summary:
    a. Compute file_hash = SHA-256(file chunks) — FIX 9e: streaming, not full-bytes-in-memory
    b. TIER 1 — Exact match (skip entirely on re-upload of same report_id — FIX 9a):
         SELECT report_id, uploaded_by, created_at FROM reports
         WHERE patient_id = ? AND file_hash = ?
           AND report_id != :current_report_id_if_reupload  ← excludes self on re-upload
         ORDER BY first_uploaded_at DESC   ← FIX 11: always pick most recent match
         LIMIT 1
         If found → write EXACT_DUPLICATE_BLOCKED audit entry → 409 EXACT_DUPLICATE
           Body includes uploader context (FIX 9f): uploaded_by_role, uploaded_by_user_id
           Caller must add ?force=true to proceed past this block.
    c. TIER 2 — Metadata similarity (only if no exact match; FIX 10: upload_document_type not file_name):
         SELECT report_id FROM reports
         WHERE patient_id = ?
           AND upload_document_type = ?    ← FIX 10: MIME type, available immediately
           AND file_size_bytes BETWEEN ? * 0.97 AND ? * 1.03
           AND first_uploaded_at >= NOW() - INTERVAL '72 hours'
           AND report_id != :current_report_id_if_reupload
         ORDER BY first_uploaded_at DESC   ← FIX 11: always pick most recent match
         LIMIT 1
         If found → 200 with duplicate_warning in body
           Set is_duplicate=TRUE, duplicate_of=<existing_report_id> on the NEW report row
           Write PROBABLE_DUPLICATE_WARNING audit entry (non-blocking)

STEP 4 — File storage (FIX #7 — versioned path)
  report_id = new UUID
  upload_count = 1 (first upload)
  Path: storage/{patient_id}/{report_id}/v1/original.{ext}
  Save file to disk
  Create file_storage_refs row

STEP 5 — Create report row
  lifecycle_status = 'uploaded'
  upload_count = 1
  file_path = storage/{patient_id}/{report_id}/v1/original.{ext}
  file_hash = computed SHA-256 (from STEP 3)
  upload_document_type = detected MIME type from STEP 1 (FIX 10: always available)
  inferred_document_type = 'unknown'  (Pipeline A will update via on_pipeline_a_complete)
  is_duplicate = TRUE if TIER 2 fired, FALSE otherwise
  duplicate_of = existing_report_id if TIER 2 fired, NULL otherwise (FIX 11: most recent match)
  released_to_patient = True  if uploaded by patient
  released_to_patient = False if uploaded by doctor (doctor controls release)
  primary_owner = patient_id  (always the patient — FIX #8)

STEP 6 — Trigger Pipeline A (async via Celery)
  process_document_task.delay(
    job_id=report_id,
    patient_id=patient_id,
    file_bytes_hex=file_bytes.hex(),
    document_type=detected_doc_type
  )
  Update lifecycle_status = 'processing'

STEP 7 — Write audit log (UPLOAD event; include file_hash in metadata)
STEP 8 — Send notification to patient (if doctor uploaded)
STEP 9 — Return {report_id, status: 'processing', patient_uid: <uid>, duplicate_warning?: {...}}
```

### Section 4a — Hybrid Duplicate Detection (FIX #9, all sub-fixes applied)

```
WHY TWO TIERS:
  SHA-256 alone fails when the same physical document is re-scanned at a different
  DPI, rotation, or compression level — same content, different hash.
  Metadata alone fails because "report.pdf" / "scan.jpg" are universal filenames
  and size overlap is frequent across unrelated documents.
  Hybrid = cryptographic exact block + semantic fuzzy warning.

─────────────────────────────────────────────────────────────────
TIER 1 — EXACT DUPLICATE (SHA-256 match)
─────────────────────────────────────────────────────────────────

  Trigger condition:
    Same patient_id + same file_hash (SHA-256 hex)
    AND NOT the same report_id (see re-upload rule below — FIX 9a)

  FIX 11 — Selection rule when multiple matches exist:
    If multiple reports share the same hash for this patient,
    always select the MOST RECENT one:
    ORDER BY first_uploaded_at DESC LIMIT 1
    This ensures consistent, deterministic duplicate_of assignment.

  FIX 9a — Re-upload self-exemption:
    When processing PUT /reports/{report_id}/reupload:
      The caller is intentionally replacing an existing report's file.
      TIER 1 must exclude the current report_id from the hash lookup.
      SQL: WHERE patient_id=? AND file_hash=? AND report_id != :report_id
      If the user re-uploads the exact same file as the current version,
      the query returns nothing → no block → re-upload proceeds normally.
      If the same hash exists on a DIFFERENT report → still 409 (correct).

  FIX minor-2 — Audit before responding:
    Before returning 409, always write an EXACT_DUPLICATE_BLOCKED audit entry.
    metadata: {existing_report_id, file_hash, tier: 1}
    This makes rejections visible in the audit trail, not just overrides.

  FIX 9f — 409 response with uploader context:
    {
      "duplicate_type": "exact",
      "existing_report_id": "<uuid>",
      "existing_uploaded_at": "<iso8601>",
      "uploaded_by_role": "doctor" | "patient",
      "uploaded_by_user_id": "<uuid>",
      "actions": {
        "use_existing": "GET /reports/<existing_report_id>",
        "force_upload": "POST /upload?force=true"
      },
      "message": "This exact file has already been uploaded for this patient."
    }

  FIX minor-3 — UI contract:
    The "actions" field explicitly gives the frontend two choices:
      "Use existing" → link to the existing report
      "Force upload" → retry with ?force=true
    Frontend MUST present both options — no silent swallow.

  Override via ?force=true:
    → Skip TIER 1 check
    → Proceed to STEP 4 with fresh report_id
    → Set is_duplicate=TRUE, duplicate_of=<existing_report_id> on the new report row
    → Write DUPLICATE_OVERRIDE audit entry
       metadata: {existing_report_id, file_hash, tier: 1, forced_by: user_id}

  Scope: patient-scoped only.
    Hash of Patient A's CBC is irrelevant to Patient B.
    Do NOT run cross-patient hash checks.

─────────────────────────────────────────────────────────────────
TIER 2 — PROBABLE DUPLICATE (metadata similarity)
─────────────────────────────────────────────────────────────────

  FIX 9b + FIX 10 — Use upload_document_type, not file_name:
    file_name is unreliable ("report.pdf" is nearly universal).
    upload_document_type is determined from MIME/magic bytes at upload time — always
    available (unlike inferred_document_type which requires Pipeline A to complete).
    Two PDFs of similar size uploaded within 72h for the same patient is a genuine
    probable duplicate signal.

    TIER 2 uses upload_document_type as the PRIMARY comparison field.
    If inferred_document_type is available on BOTH the new and existing report
    (i.e. neither is 'unknown'), it MAY be used as an additional refinement
    in future versions — but is NOT required for the initial implementation.

  Trigger condition (ALL must match):
    Same patient_id
    AND same upload_document_type (MIME-based, e.g. 'application/pdf')
    AND file_size_bytes within ±3% of existing report's file_size_bytes
    AND existing report first_uploaded_at >= NOW() - INTERVAL '72 hours'
    AND report_id != :current_report_id_if_reupload  (self-exemption — FIX 9a)

  FIX 11 — Selection rule when multiple matches exist:
    ORDER BY first_uploaded_at DESC LIMIT 1
    Always pick the most recent matching report for duplicate_of.

  FIX 9d — Index for this query:
    idx_reports_metadata_dup ON reports(patient_id, upload_document_type, file_size_bytes, first_uploaded_at)
    This index is already in the schema. The query planner will use it.

  Response: HTTP 200 (upload proceeds)
    Normal response body PLUS:
    {
      "duplicate_warning": {
        "type": "probable",
        "existing_report_id": "<uuid>",
        "existing_uploaded_at": "<iso8601>",
        "uploaded_by_role": "doctor" | "patient",
        "message": "A similar report was uploaded recently. Please verify this is not a duplicate."
      }
    }

  No ?force required — advisory only. Upload completes.
  Set is_duplicate=TRUE, duplicate_of=<existing_report_id> on the new report row.
  Write PROBABLE_DUPLICATE_WARNING audit entry (non-blocking).
  Frontend must surface the warning before the user navigates away.

─────────────────────────────────────────────────────────────────
HASH COMPUTATION — STREAMING MODE (FIX 9e)
─────────────────────────────────────────────────────────────────

  Problem: loading the full 50MB into memory before hashing causes memory spikes
  when multiple uploads run concurrently.

  Fix: compute SHA-256 in streaming chunks using hashlib's update() loop.
  File bytes are still needed for Pipeline A (which takes hex bytes), so the
  implementation reads chunks, feeds them into both the hasher and a BytesIO
  accumulator simultaneously.

  Python pattern:
    import hashlib, io
    hasher = hashlib.sha256()
    buf = io.BytesIO()
    async for chunk in upload.file:   # UploadFile async iterator
        hasher.update(chunk)
        buf.write(chunk)
    file_hash = hasher.hexdigest()    # final hash — no memory spike
    file_bytes = buf.getvalue()       # full bytes for Pipeline A

  compute_file_hash() in file_storage.py is updated to accept an async iterable
  and return (hash_hex, accumulated_bytes) as a tuple.

─────────────────────────────────────────────────────────────────
RE-UPLOAD AND HASH
─────────────────────────────────────────────────────────────────

  On re-upload:
    Compute new hash from new file using streaming mode (FIX 9e).
    Run TIER 1 with self-exemption (report_id != :this_report_id) — FIX 9a.
    Run TIER 2 with self-exemption.
    Update reports.file_hash = new_hash.
    Update reports.is_duplicate / duplicate_of if TIER 2 fires.

  If user re-uploads exact same file as current version:
    TIER 1 self-exemption → no block → re-upload proceeds.
    This is valid: re-triggering Pipeline A on the same file may be intentional
    (e.g. after correcting a pipeline config, or manual retry).

─────────────────────────────────────────────────────────────────
CONCURRENCY — RACE CONDITION HANDLING (FIX 14)
─────────────────────────────────────────────────────────────────

  Scenario: two simultaneous uploads of the same file for the same patient.
  Both compute SHA-256, both query TIER 1 before either inserts.
  Both pass → both create a report row → duplicate created.

  Options considered:
    A. Accept race condition (RECOMMENDED for current scale)
       → Extremely rare at current upload volume
       → Analytics dedup (FIX 9c/12) handles any duplicates at query time
       → No additional complexity

    B. Partial unique index: UNIQUE(patient_id, file_hash)
       WHERE file_hash IS NOT NULL AND is_duplicate = FALSE
       → Blocks the second insert at DB level
       → BUT breaks ?force=true (which creates intentional duplicates)
       → NOT recommended

    C. Transaction locking: SELECT ... FOR UPDATE (advanced)
       → Wrap TIER 1 check + INSERT in a transaction
       → SELECT 1 FROM reports WHERE patient_id=? AND file_hash=? FOR UPDATE
       → Second concurrent transaction blocks until first commits
       → Correct but adds latency and complexity
       → Recommended as future enhancement if upload volume grows

  Decision: Option A for MVP. Document Option C for future.
  The analytics deduplication layer (FIX 9c with refined ORDER BY — FIX 12)
  already handles any duplicates that slip through the race window.

─────────────────────────────────────────────────────────────────
AUDIT EVENTS SUMMARY
─────────────────────────────────────────────────────────────────

  EXACT_DUPLICATE_BLOCKED     → logged on every TIER 1 hit, BEFORE returning 409 (FIX minor-2)
  DUPLICATE_OVERRIDE          → logged when ?force=true bypasses TIER 1
  PROBABLE_DUPLICATE_WARNING  → logged when TIER 2 fires (non-blocking)

  All three events include in metadata:
    existing_report_id, file_hash, tier (1 or 2), triggered_by: user_id

─────────────────────────────────────────────────────────────────
FIX 9c — ANALYTICS DEDUPLICATION (mandatory in all aggregate queries)
─────────────────────────────────────────────────────────────────

  Even with duplicate detection, duplicates will exist in the DB because:
    - ?force=true allows intentional bypass
    - TIER 2 is advisory-only (non-blocking)

  If analytics queries don't deduplicate, one patient's hemoglobin value
  will appear multiple times in a cohort average, skewing results.

  Rule: ALL cross-patient and per-patient trend analytics queries MUST deduplicate
  on (patient_id, collection_date, field_name) before any aggregation.

  Pattern A — DISTINCT ON (PostgreSQL):
    SELECT DISTINCT ON (rf.patient_id, rf.collection_date, rf.name)
      rf.patient_id, rf.collection_date, rf.name, rf.numeric_value
    FROM report_fields rf
    JOIN reports r ON r.job_id = rf.job_id
    WHERE rf.name = :field_name
      AND rf.numeric_value IS NOT NULL
    ORDER BY rf.patient_id, rf.collection_date, rf.name,
             r.is_duplicate ASC,                          ← prefer non-duplicates
             r.last_edited_at DESC NULLS LAST,            ← FIX 12: corrected data wins
             r.first_uploaded_at DESC

  Pattern B — ROW_NUMBER() for more control:
    WITH ranked AS (
      SELECT rf.*, r.is_duplicate, r.last_edited_at,
        ROW_NUMBER() OVER (
          PARTITION BY rf.patient_id, rf.collection_date, rf.name
          ORDER BY r.is_duplicate ASC,                          -- prefer non-duplicates
                   r.last_edited_at DESC NULLS LAST,            -- FIX 12: corrected data wins
                   r.first_uploaded_at DESC                     -- tiebreaker: newest upload
        ) AS rn
      FROM report_fields rf
      JOIN reports r ON r.job_id = rf.job_id
      WHERE rf.name = :field_name AND rf.numeric_value IS NOT NULL
    )
    SELECT * FROM ranked WHERE rn = 1

  Deduplication priority (FIX 12 — refined):
    1. Non-duplicate rows (is_duplicate=FALSE) are preferred over duplicates
    2. Corrected/re-uploaded rows (last_edited_at IS NOT NULL) win over untouched rows
    3. Newest upload (first_uploaded_at DESC) as final tiebreaker
    If all rows for a (patient, date, field) are duplicates, one is still selected —
    analytics never drops a patient entirely.

  This deduplication rule applies to:
    - get_patient_analytics()
    - cohort/cross-patient aggregation queries
    - trend queries
    - any future analytics added to the system
  Add comment to every analytics function:
    # ANALYTICS: deduplicated on (patient_id, collection_date, field_name) — FIX 9c
```

### Re-upload Flow

```
PUT /doctor/reports/{report_id}/reupload
PUT /patient/reports/{report_id}/reupload

FIX #3: Guard uses field-level state, not is_locked.
GUARD: No field in this report has is_final=True
       → If any field is doctor_verified → raise 403 "Report has finalized fields — cannot re-upload"
GUARD: report.lifecycle_status != 'fully_verified'

1. Verify caller has access to this report
2. Compute new file_hash using streaming mode (FIX 9e)
3. FIX 9a — Run duplicate checks with self-exemption:
   TIER 1: WHERE patient_id=? AND file_hash=? AND report_id != :report_id
     → Same hash as a DIFFERENT report → 409 (still blocks correctly)
     → Same hash as THIS report → no match → passes (re-uploading same file is valid)
   TIER 2: same check with report_id != :report_id
     → Fires on match → warning logged, upload proceeds
4. Increment upload_count:
   new_count = report.upload_count + 1
5. FIX #7 — save to versioned path:
   new_path = storage/{patient_id}/{report_id}/v{new_count}/original.{ext}
   Save new file there (old version files are retained for audit)
6. Reset Pipeline A: call process_document_task with new file
7. Reset all verifications:
   DELETE FROM field_verifications WHERE report_id = ?
8. Reset report:
   lifecycle_status = 'uploaded'
   last_edited_at = NOW()
   upload_count = new_count
   file_path = new_path
   file_hash = new hash
   upload_document_type = new file's MIME type (FIX 10: always re-detect from new file)
   inferred_document_type = 'unknown'  (FIX 10: reset; on_pipeline_a_complete will update)
   is_duplicate / duplicate_of updated per TIER 2 result
   released_to_patient = False  (must be re-released by doctor)
9. Write RE_UPLOAD + VERIFICATION_RESET audit entries
10. Invalidate Pipeline B cache for this patient: invalidate_patient(patient_id)
11. Send RE_UPLOAD_DONE notification to relevant parties
```

### File Storage Service

```python
# product/utils/file_storage.py

BASE_STORAGE_PATH = settings.STORAGE_PATH  # e.g. "./storage"

# FIX #7: versioned path
def get_file_path(patient_id: str, report_id: str,
                  upload_count: int, filename: str) -> Path:
    """Returns: storage/{patient_id}/{report_id}/v{upload_count}/{filename}"""

def save_file(patient_id: str, report_id: str, upload_count: int,
              filename: str, file_bytes: bytes) -> str:
    """
    Create directories if needed.
    Write file.
    Return full path string.
    Old version directories are NOT deleted — retained for audit trail.
    """

def delete_file(file_path: str) -> None:
    """Delete file from disk. Log warning if not found (don't raise)."""

def get_file_bytes(file_path: str) -> bytes:
    """Read and return file bytes. Raise 404 if not found."""

# FIX 9e: Streaming hash — avoids memory spike on concurrent 50MB uploads.
# Returns (hash_hex, accumulated_bytes) tuple.
# Call this ONCE immediately after receiving the upload — before any other operation.
async def compute_file_hash_streaming(upload_file) -> tuple[str, bytes]:
    """
    Reads upload_file in chunks, computes SHA-256 in streaming mode,
    and accumulates bytes for downstream use (Pipeline A needs file_bytes_hex).

    import hashlib, io
    hasher = hashlib.sha256()
    buf = io.BytesIO()
    async for chunk in upload_file:
        hasher.update(chunk)
        buf.write(chunk)
    return hasher.hexdigest(), buf.getvalue()
    """
```

---

## 5. Verification System (Field-Level)

### Field States

```
auto          → extracted by Pipeline A with high confidence → EDA generated
hitl          → low confidence → EDA blocked → verification required
patient_verified → patient confirmed or edited the value → EDA generated with watermark
doctor_verified  → doctor confirmed or edited the value → FINAL → EDA fully trusted
```

### Verification Rules

```
1. Doctor verification is final — locks the field permanently
2. Patient can verify/edit any field that is NOT yet doctor_verified
3. Once doctor_verified, field cannot be edited by anyone
4. Re-upload resets ALL verifications on the report
5. Patient verification is shown to doctor but NOT treated as final
6. Doctor can re-verify a patient_verified field to make it final
```

### FIX #2 — Verification Service (no upsert — append-only)

```python
# product/services/verification_service.py

def verify_field(
    report_id: str,
    field_name: str,
    verification_type: str,   # approved | edited | rejected
    edited_value: str | None,
    edit_reason: str | None,
    verifying_user: User,
    db: Session
) -> FieldVerificationResponse:
    """
    1. Get report — verify caller has access
    2. Get field from report_fields WHERE job_id=report.job_id AND name=field_name
    3. Check: field not already doctor_verified
       Query: SELECT is_final FROM field_verifications
              WHERE report_id=? AND field_name=? AND is_final=TRUE LIMIT 1
       If found → raise 403 "Field is locked by doctor verification"
    4. Check: if verifying_user.role == 'patient':
         verify active assignment to report's doctor
         set is_final = False
       If verifying_user.role == 'doctor':
         verify doctor has access to this patient
         set is_final = True
    5. If verification_type == 'edited':
         Validate edited_value format (import validators from shared.utils.validators)
         Update report_fields: value = edited_value for this field
         Update report_fields: numeric_value = float(edited_value) if numeric
    6. FIX #2: INSERT new row — do NOT upsert.
       INSERT INTO field_verifications (report_id, job_id, field_name, field_value,
         verified_by, verifier_role, verification_type, edited_value, edit_reason, is_final)
       VALUES (...)
       -- Every action creates a new row. History is preserved.
    7. Write VERIFY_FIELD or EDIT_FIELD audit entry
    8. If is_final: send DOCTOR_VERIFIED notification to patient
       Else: send PATIENT_VERIFIED notification to doctor
    9. Check if all fields are now doctor_verified:
         SELECT COUNT(*) FROM report_fields WHERE job_id = report.job_id
         SELECT COUNT(DISTINCT field_name) FROM field_verifications
           WHERE report_id = ? AND is_final = TRUE
         If counts match → update reports.lifecycle_status = 'fully_verified'
         FIX #3: Do NOT set is_locked. lifecycle_status = 'fully_verified' is the soft state.
    10. Trigger Pipeline B re-ingestion for this report:
         ingest_patient_record(patient_id, job_id, db)
    11. Return FieldVerificationResponse
    """

def get_current_field_verification(report_id: str, field_name: str, db) -> FieldVerification | None:
    """
    FIX #2: Returns the latest verification row for this field.
    SELECT * FROM field_verifications
    WHERE report_id = ? AND field_name = ?
    ORDER BY verified_at DESC LIMIT 1
    """

def get_field_verification_history(report_id: str, field_name: str, db) -> list[FieldVerification]:
    """
    FIX #2: Returns full audit history for a field (all rows).
    SELECT * FROM field_verifications
    WHERE report_id = ? AND field_name = ?
    ORDER BY verified_at ASC
    """

def get_field_verification_status(report_id: str, db) -> list[FieldStatus]:
    """
    FIX #4: Patient visibility rule applied here.

    For each field in report_fields:
      Get latest verification row using get_current_field_verification().

      Determine pipeline_status from report_fields.status (auto | hitl).

      Build FieldStatus:
        field_name: str
        value: str | None         ← FIX #4: None if hitl AND requesting_role == 'patient'
        display_value: str        ← FIX #4: "Verification required" if hitl AND patient
        confidence: float
        pipeline_status: str      # auto | hitl
        patient_verified: bool
        doctor_verified: bool
        is_final: bool
        eda_available: bool       # True if auto OR doctor_verified

      FIX #4 — HITL visibility rule:
        IF field.pipeline_status == 'hitl' AND field is NOT yet doctor_verified:
          IF requesting_user.role == 'patient':
            → value = None
            → display_value = "Verification required"
            → eda_available = False
    """

def get_hitl_queue(doctor_id: str | None, db) -> list[HITLQueueItem]:
    """
    Returns all reports with lifecycle_status = 'hitl_required'
    If doctor_id provided: filter to doctor's patients only
    Ordered by first_uploaded_at ASC (oldest first)
    """
```

### EDA Availability Logic

```
Field state         EDA shown to doctor    EDA shown to patient
auto (unverified)   ✅ with "not verified"  ✅ with "not verified"
hitl (unverified)   ❌ "verification req'd" ❌ "Verification required" (value hidden — FIX #4)
patient_verified    ✅ with "patient verif" ✅ with "patient verif"
doctor_verified     ✅ fully trusted        ✅ "verified by doctor"
```

---

## 6. Report Release System

```python
# product/services/report_service.py

def release_report_to_patient(report_id: str, doctor_id: str, db) -> Report:
    """
    Verify: doctor has active assignment to report's patient
    Verify: report.uploaded_by == doctor_id (only uploader can release)
    Set: reports.released_to_patient = True
    Write RELEASE_REPORT audit entry
    Send REPORT_RELEASED notification to patient
    """

def get_report_for_patient(report_id: str, patient_id: str, db) -> ReportDetail:
    """
    Verify: report.patient_id == patient_id
    Verify: report.released_to_patient == True
    Return report with field verification statuses
    FIX #4: Pass role='patient' into get_field_verification_status()
    so HITL fields are hidden.
    """

def get_report_for_doctor(report_id: str, doctor_id: str, db) -> ReportDetail:
    """
    Verify: doctor has active assignment to report's patient
    Return full report (doctor sees all, including unreleased)
    Doctors always see field values — FIX #4 applies to patients only.
    """
```

---

## 7. API Routes

### Auth Routes

```python
# product/api/auth_routes.py
router = APIRouter(prefix="/auth", tags=["auth"])

POST /auth/signup               → auth_service.signup()
POST /auth/login                → auth_service.login()       ← FIX #6: rate limited
POST /auth/refresh              → auth_service.refresh_token()
POST /auth/logout               → write LOGOUT audit (token blacklist optional for MVP)
POST /auth/password-reset-request → send reset email (admin triggers for college project)
POST /auth/password-reset       → admin_service.reset_password()
```

### Doctor Routes

```python
# product/api/doctor_routes.py
router = APIRouter(prefix="/doctor", tags=["doctor"])
# All routes: Depends(require_role("doctor"))

# Dashboard
GET  /doctor/dashboard          → patient count, recent uploads, HITL count

# Patient management
GET  /doctor/patients           → list all assigned patients (paginated)
GET  /doctor/patients/search    → ?q=name_or_patient_uid
GET  /doctor/patients/{patient_id}/profile
GET  /doctor/patients/{patient_id}/reports
GET  /doctor/patients/{patient_id}/summary  → Pipeline B analytics

# Report operations
POST /doctor/upload             → upload_service.upload(uploaded_by='doctor') ← FIX #6: rate limited
GET  /doctor/reports/{report_id}
GET  /doctor/reports/{report_id}/raw-file  → return file bytes for display
PUT  /doctor/reports/{report_id}/reupload
POST /doctor/reports/{report_id}/release   → release_report_to_patient()

# Verification
GET  /doctor/reports/{report_id}/fields    → all fields with verification status (doctor view)
POST /doctor/reports/{report_id}/fields/{field_name}/verify
GET  /doctor/hitl-queue         → get_hitl_queue(doctor_id)

# Intelligence (Pipeline B)
POST /doctor/query              → pipeline_b.api.doctor_routes (proxy)
GET  /doctor/patients/{patient_id}/trend?field_name=hemoglobin
GET  /doctor/patients/{patient_id}/analytics   ← FIX #8: SQL engine, never LLM

# Assignment
POST /doctor/assignments        → create assignment (doctor initiates)
GET  /doctor/assignments        → list pending + active
PUT  /doctor/assignments/{id}/approve
PUT  /doctor/assignments/{id}/reject

# Notifications
GET  /doctor/notifications
PUT  /doctor/notifications/{id}/read

# Chatbot
POST /doctor/chat               → Pipeline B doctor chatbot
```

### Patient Routes

```python
# product/api/patient_routes.py
router = APIRouter(prefix="/patient", tags=["patient"])
# All routes: Depends(require_role("patient"))

# Profile
GET  /patient/profile
PUT  /patient/profile           → update name, phone, dob, sex

# Reports
POST /patient/upload            → upload_service.upload(uploaded_by='patient') ← FIX #6: rate limited
GET  /patient/reports           → only released_to_patient=True reports
GET  /patient/reports/search    → ?date=&type=
GET  /patient/reports/{report_id}
GET  /patient/reports/{report_id}/raw-file
PUT  /patient/reports/{report_id}/reupload

# Verification (patient can verify their own data)
GET  /patient/reports/{report_id}/fields   → FIX #4: hitl fields hidden (value=None, "Verification required")
POST /patient/reports/{report_id}/fields/{field_name}/verify

# Analytics / EDA (own data only)
GET  /patient/reports/{report_id}/eda      → per-report field chart
GET  /patient/trends?field_name=hemoglobin → time series for own data

# Assignment
POST /patient/assignments       → patient initiates (selects doctor)
GET  /patient/assignments       → list doctors (pending + active)
PUT  /patient/assignments/{id}/approve
PUT  /patient/assignments/{id}/reject

# Chatbot (safe patient mode)
POST /patient/chat              → Pipeline B patient chatbot (with safety layer)

# Notifications
GET  /patient/notifications
PUT  /patient/notifications/{id}/read
```

### Admin Routes

```python
# product/api/admin_routes.py
router = APIRouter(prefix="/admin", tags=["admin"])
# All routes: Depends(require_role("admin"))

GET  /admin/stats               → total doctors, patients, reports, HITL count
GET  /admin/users               → all users (paginated, filterable by role)
GET  /admin/users/{user_id}
POST /admin/assignments         → admin assigns doctor to patient (auto-active)
GET  /admin/hitl-queue          → all HITL reports across all doctors
POST /admin/password-reset      → reset any user's password
PUT  /admin/users/{user_id}/deactivate
PUT  /admin/users/{user_id}/activate
```

---

## 8. Pipeline B Integration Points

The product layer calls Pipeline B — Pipeline B does not call the product layer.

```python
# In doctor_routes.py — proxy to Pipeline B

@router.post("/query")
async def doctor_query(
    body: DoctorQueryRequest,
    current_user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db)
):
    # GUARD: verify doctor has access to the patient being queried
    if body.patient_id:
        verify_doctor_patient_access(current_user.user_id, body.patient_id, db)

    # Forward to Pipeline B
    from pipeline_b.engines.query_classifier import classify
    from pipeline_b.schemas.query import PersonaType
    classified = classify(body.text, PersonaType.doctor)
    # ... route to correct service

@router.get("/patients/{patient_id}/analytics")
async def patient_analytics(
    patient_id: str,
    current_user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db)
):
    verify_doctor_patient_access(current_user.user_id, patient_id, db)
    from pipeline_b.services.analytics_service import get_patient_analytics
    return get_patient_analytics(patient_id, db)
```

### FIX #8 — Cross-Patient Analytics Rules

```
Cross-patient analytics (cohort queries, population trends, benchmarking):

  MUST:
  - Run on PostgreSQL (SQL engine) — not vector DB
  - Use report_fields.numeric_value column for all numeric comparisons
  - Use SQL aggregation: AVG(), MIN(), MAX(), PERCENTILE_CONT(), COUNT()
  - Filter using indexed columns: name, patient_id, collection_date

  MUST NOT:
  - Call LLM for any computation
  - Use Qdrant for aggregation (Qdrant is retrieval only)
  - Perform arithmetic outside SQL

  Example cohort query pattern:
    SELECT
      AVG(numeric_value) as mean,
      PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY numeric_value) as median,
      MIN(numeric_value) as min_val,
      MAX(numeric_value) as max_val,
      COUNT(*) as sample_size
    FROM report_fields
    WHERE name = 'hemoglobin'
      AND numeric_value IS NOT NULL
      AND collection_date BETWEEN :start AND :end

  Report ownership:
    primary_owner = patient_id   (even if doctor uploaded)
    Analytics cross-referencing must respect patient consent scope.
    Do NOT expose individual patient data in cross-patient results —
    only return aggregates.
```

### Pipeline B cache invalidation on verification

```python
# In verification_service.verify_field() — after any field edit:

from pipeline_b.cache.response_cache import invalidate_patient
from pipeline_b.ingestion.ingest import ingest_patient_record

# Re-ingest into Qdrant with corrected values
ingest_patient_record(report.patient_id, report.job_id, db)

# Clear stale reasoning/trend cache
invalidate_patient(str(report.patient_id))
```

---

## 9. Notification Service

```python
# product/services/notification_service.py

def create_notification(
    recipient_id: str,
    sender_id: str | None,
    notif_type: str,
    title: str,
    message: str,
    report_id: str | None,
    db: Session
) -> None:
    """Insert notification row. Never raises — log errors silently."""

# Convenience wrappers used throughout:
def notify_report_uploaded(patient_id, doctor_id, report_id, db): ...
def notify_report_processed(patient_id, report_id, hitl_required, db): ...
def notify_report_released(patient_id, report_id, db): ...
def notify_field_verified(target_user_id, field_name, verifier_role, db): ...
def notify_assignment_request(target_user_id, requester_name, db): ...
def notify_assignment_approved(target_user_id, db): ...
def notify_re_upload(patient_id, doctor_id, report_id, db): ...
```

---

## 10. Pipeline A Completion Hook

After Pipeline A finishes processing a report, it needs to trigger product-layer actions.
Since Pipeline A worker (`tasks.py`) must not be modified, add a post-processing hook
via a Celery signal or a dedicated product-layer task.

```python
# product/services/upload_service.py

@celery_app.task
def on_pipeline_a_complete(job_id: str, patient_id: str, hitl_required: bool,
                            inferred_document_type: str = 'unknown'):
    """
    Called after process_document_task completes.
    Chain: process_document_task | on_pipeline_a_complete

    1. Update reports.lifecycle_status:
         'auto_approved' if not hitl_required
         'hitl_required' if hitl_required
    2. Update reports.processed_at = NOW()
    3. FIX 10: Update reports.inferred_document_type from Pipeline A output.
         Pipeline A determines the semantic document type (e.g. 'cbc', 'lipid_panel')
         from the extracted fields. This is more specific than upload_document_type
         (which is just the MIME type).
    4. FIX 13 (optional — ingestion-layer dedup re-evaluation):
         Now that inferred_document_type is available, optionally re-evaluate TIER 2:
           SELECT report_id FROM reports
           WHERE patient_id = :patient_id
             AND inferred_document_type = :inferred_document_type
             AND inferred_document_type != 'unknown'
             AND file_size_bytes BETWEEN :size * 0.97 AND :size * 1.03
             AND first_uploaded_at >= :this_report_uploaded_at - INTERVAL '72 hours'
             AND report_id != :this_report_id
           ORDER BY first_uploaded_at DESC LIMIT 1
         If match found AND this report's is_duplicate is currently FALSE:
           UPDATE reports SET is_duplicate = TRUE, duplicate_of = :match_id
           Write PROBABLE_DUPLICATE_DETECTED_POST_PIPELINE audit entry
         This is OPTIONAL — the query-time dedup (FIX 9c/12) handles it regardless.
         Benefit: faster analytics, simpler queries, earlier visibility.
    5. Trigger Pipeline B ingestion:
         ingest_patient_record(patient_id, job_id, db)
    6. Send notification:
         notify_report_processed(patient_id, report_id, hitl_required, db)
    7. Write REPORT_PROCESSED audit entry
    """
```

---

## 11. Search Service

```python
# product/services/search_service.py

def search_patients_for_doctor(
    doctor_id: str,
    query: str,         # name or patient_uid
    db: Session
) -> list[PatientProfile]:
    """
    Search within doctor's assigned patients only.
    ILIKE match on: full_name, patient_uid, email
    Returns max 20 results.
    """

def search_reports_for_patient(
    patient_id: str,
    date_from: str | None,
    date_to: str | None,
    document_type: str | None,
    db: Session
) -> list[ReportSummary]:
    """
    Only released_to_patient=True reports.
    Filter by date range and/or document_type.
    """
```

---

## 12. Admin Stats Service

```python
# product/services/admin_service.py

def get_system_stats(db) -> AdminStats:
    """
    Returns:
      total_doctors: int
      total_patients: int
      total_reports: int
      reports_processing: int
      reports_hitl_required: int
      reports_fully_verified: int
      assignments_active: int
      assignments_pending: int
    All computed with COUNT queries — never LLM.
    """

def reset_user_password(user_id: str, new_password: str,
                         admin_id: str, db) -> None:
    """
    Hash new password.
    Update users.password_hash.
    Write PASSWORD_RESET audit entry.
    Send notification to user.
    """
```

---

## 13. Environment Variables to Add

Add to `shared/config.py` and `.env.example`:

```env
# Product Layer
SECRET_KEY=your-jwt-secret-key-minimum-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=1440
STORAGE_PATH=./storage
MAX_FILE_SIZE_MB=50

# FIX #6 — Rate limiting
RATE_LIMIT_STORAGE_URI=memory://   # use redis://localhost:6379 in production
LOGIN_RATE_LIMIT=5/15minutes
UPLOAD_RATE_LIMIT=10/hour

# Optional (for future email notifications)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
```

---

## 14. Implementation Prompts (Strict Order)

### PROMPT 1 — DB Schema Migration

```
TASK: Run the product layer database migration ONLY

Create and execute migrations/001_product_layer_schema.sql containing:
  - CREATE TABLE users
  - CREATE TABLE doctor_patient_assignments
  - CREATE TABLE reports  (no is_locked column — FIX #3; includes file_hash — FIX #9)
  - CREATE TABLE field_verifications  (no UNIQUE constraint — FIX #2)
  - CREATE TABLE audit_log
  - CREATE TABLE notifications
  - ALTER TABLE document_jobs (add new columns with defaults)
  - ALTER TABLE report_fields (add numeric_value column)
  - CREATE all indexes including:
      idx_fv_field_time for latest-row lookup (FIX #2)
      idx_reports_hash on (patient_id, file_hash) for duplicate detection (FIX #9)

Then create migrations/002_remove_structured_text.sql:
  - ALTER TABLE document_jobs DROP COLUMN structured_text_for_embedding

Run migration 001 first. Do NOT run migration 002 until Qdrant
ingestion is confirmed working.

DO NOT touch any pipeline code.

Verify by running:
  psql -U postgres -d HDIMS -c "\dt"
  → should show all 5 new tables plus existing tables

Report back: list of all tables with row counts.
```

### PROMPT 2 — Pydantic Schemas

```
TASK: Implement product/schemas/ ONLY

Implement all schema files as defined in Section 7 of the blueprint.
Use Pydantic v2. No business logic — schemas only.

FIX #4: FieldStatus schema must have:
  value: str | None          (None when field is hidden from patient)
  display_value: str         ("Verification required" or the actual value)
  is_value_hidden: bool      (True when hitl + patient role)

Files:
  product/schemas/auth.py
  product/schemas/user.py
  product/schemas/assignment.py
  product/schemas/report.py
  product/schemas/verification.py
  product/schemas/notification.py
  product/schemas/admin.py

Return: full schema code for all files.
```

### PROMPT 3 — Auth System

```
TASK: Implement product/auth/ ONLY

Files:
  product/auth/jwt_handler.py
  product/auth/password.py
  product/auth/middleware.py
  product/auth/role_guard.py
  product/auth/rate_limit.py   ← FIX #6: new file

Implement exactly as specified in Section 2.
Add SECRET_KEY, JWT settings, and RATE_LIMIT_STORAGE_URI to shared/config.py.

Verify with:
  venvHDIMS/bin/python -c "
  import sys; sys.path.insert(0, '.')
  from product.auth.jwt_handler import create_access_token, decode_access_token
  token = create_access_token('user-123', 'doctor', 'test@test.com')
  payload = decode_access_token(token)
  assert payload['sub'] == 'user-123'
  assert payload['role'] == 'doctor'
  print('✅ JWT create + decode works')
  from product.auth.password import hash_password, verify_password
  h = hash_password('mypassword')
  assert verify_password('mypassword', h)
  assert not verify_password('wrongpassword', h)
  print('✅ Password hash + verify works')
  "
```

### PROMPT 4 — Auth Service + Routes

```
TASK: Implement auth service and routes ONLY

Files:
  product/services/auth_service.py
  product/api/auth_routes.py

Endpoints:
  POST /auth/signup
  POST /auth/login
  POST /auth/refresh
  POST /auth/logout

FIX #5: Signup must implement:
  Priority 1 — patient_uid claim flow (body.claim_patient_uid)
  Priority 2 — email match fallback
  Both write SIGNUP + ACCOUNT_ACTIVATED audit entries.

FIX #6: Login route must apply LOGIN_RATE_LIMIT.

Include audit log writes on every action.
Do NOT implement password reset (that's admin_service).

Test manually:
  # Start server, then:
  curl -X POST http://localhost:8000/auth/signup \
    -H "Content-Type: application/json" \
    -d '{"email":"doctor@test.com","password":"test123",
         "role":"doctor","full_name":"Dr. Test"}'
  → should return access_token
```

### PROMPT 5 — Assignment Service + Routes

```
TASK: Implement assignment service and routes ONLY

Files:
  product/services/assignment_service.py
  product/api/doctor_routes.py (assignment endpoints only)
  product/api/patient_routes.py (assignment endpoints only)

Implement exactly as specified in Section 3.
Include notification sends on every state change.
Include audit log on every action.
```

### PROMPT 6 — File Storage + Upload Service

```
TASK: Implement file storage utility and upload service ONLY

Files:
  product/utils/file_storage.py
  product/services/upload_service.py
  product/api/doctor_routes.py (upload endpoints)
  product/api/patient_routes.py (upload endpoints)

FIX #7: file_storage.py must use versioned path:
  storage/{patient_id}/{report_id}/v{upload_count}/original.{ext}
  get_file_path() takes upload_count as argument.

FIX #9: file_storage.py must include compute_file_hash(file_bytes) → str.
  Uses hashlib.sha256. Called BEFORE save_file on every upload and re-upload.

FIX #5: Doctor upload patient lookup:
  1. Lookup by patient_uid first
  2. Fall back to email only if patient_uid not provided
  3. Auto-generate patient_uid for pre-registered patients

FIX #6: Upload routes must apply UPLOAD_RATE_LIMIT.

FIX #9: Implement hybrid duplicate detection BEFORE file storage write (Section 4a):
  TIER 1 — SHA-256 exact match:
    Compute hash from in-memory bytes immediately after file read.
    Query: SELECT report_id FROM reports WHERE patient_id=? AND file_hash=? LIMIT 1
    If match → return 409 with {duplicate_type: "exact", existing_report_id: ...}
    Only proceed if ?force=true in query params.
    Write DUPLICATE_OVERRIDE audit entry when force=true is used.

  TIER 2 — Metadata similarity (only if TIER 1 passed):
    Query: same patient + same upload_document_type + size ±3% + uploaded within 72h (FIX 10)
    If match → continue upload but include duplicate_warning in response body.
    Write PROBABLE_DUPLICATE_WARNING audit entry (non-blocking).

  Store computed file_hash in reports.file_hash on every INSERT and UPDATE.

Implement upload flow exactly as in Section 4 including:
  - MIME detection from magic bytes
  - Patient confirmation checkpoint for doctor uploads
  - Hybrid duplicate detection (FIX #9)
  - Versioned file storage (FIX #7)
  - Celery task chaining (process_document_task | on_pipeline_a_complete)
  - Audit log + notification

Implement re-upload flow including:
  - Guard: check no doctor_verified fields exist (FIX #3 — no is_locked check)
  - Compute new hash + run TIER 1 check on new file before proceeding
  - Versioned file path for new version (FIX #7)
  - Update reports.file_hash with new hash
  - Verification reset
  - Cache invalidation
  - Audit: RE_UPLOAD + VERIFICATION_RESET events
```

### PROMPT 7 — Verification Service + Routes

```
TASK: Implement verification service and routes ONLY

Files:
  product/services/verification_service.py
  product/api/doctor_routes.py (verification endpoints)
  product/api/patient_routes.py (verification endpoints)

FIX #2: Use INSERT (not upsert). No UNIQUE constraint to satisfy.
  Latest row = current state.
  All rows = audit history.
  Use get_current_field_verification() for current state checks.

FIX #3: fully_verified detection:
  When all fields are doctor_verified:
    → lifecycle_status = 'fully_verified'
    → do NOT set is_locked (column does not exist)

FIX #4: get_field_verification_status() must:
  Accept requesting_user_role parameter
  If role == 'patient' AND field.pipeline_status == 'hitl' AND not doctor_verified:
    → value = None, display_value = "Verification required", eda_available = False
  Doctor always sees full value regardless of hitl status.

Include:
  - Field locking after doctor verification (is_final=True check before any edit)
  - EDA availability logic
  - Pipeline B re-ingestion after edit (ingest_patient_record)
  - Cache invalidation (invalidate_patient)
  - Notification to other party
  - Audit log
  - Auto-detect fully_verified status (all fields doctor_verified)
```

### PROMPT 8 — Notification + Search + Admin Services

```
TASK: Implement notification, search, and admin services ONLY

Files:
  product/services/notification_service.py
  product/services/search_service.py
  product/services/admin_service.py
  product/api/admin_routes.py
  product/api/doctor_routes.py (search + notification endpoints)
  product/api/patient_routes.py (search + notification endpoints)

Implement exactly as in Sections 9, 11, 12.
Admin password reset must write PASSWORD_RESET audit entry.
```

### PROMPT 9 — Pipeline B Integration + Report Release

```
TASK: Wire product layer to Pipeline B ONLY

Files:
  product/services/report_service.py
  product/api/doctor_routes.py (Pipeline B proxy endpoints)
  product/api/patient_routes.py (Pipeline B proxy endpoints)

For each Pipeline B call from the product layer:
  - Verify access (doctor-patient assignment check)
  - Call Pipeline B service
  - Return typed response

FIX #4: get_report_for_patient() must pass role='patient'
  into get_field_verification_status() to trigger HITL hiding.

FIX #8: Analytics endpoint must use SQL aggregation (not LLM).
  Document in code: "# ANALYTICS: SQL engine only — never LLM"

Implement release_report_to_patient() exactly as in Section 6.
```

### PROMPT 10 — Tests

```
TASK: Implement product layer tests ONLY

Files:
  tests/product/test_auth.py
  tests/product/test_assignment.py
  tests/product/test_upload.py
  tests/product/test_verification.py
  tests/product/test_admin.py

Key assertions:
  test_auth.py:
    - signup creates user with correct role
    - login returns valid JWT
    - wrong password returns 401
    - pre-registered patient activates via patient_uid claim (FIX #5)
    - pre-registered patient activates via email fallback (FIX #5)
    - login rate limit returns 429 after 5 attempts (FIX #6)

  test_assignment.py:
    - doctor-initiated assignment creates pending status
    - patient approval makes it active
    - doctor cannot see unassigned patient

  test_upload.py:
    - patient confirmation checkpoint blocks wrong patient_uid
    - re-upload creates versioned path v2/, v3/ (FIX #7)
    - re-upload is blocked if any field has is_final=True (FIX #3)
    - re-upload resets all verifications when no final fields exist
    - upload rate limit returns 429 after 10 attempts (FIX #6)
    - same file bytes → same SHA-256 hash stored in reports.file_hash (FIX #9)
    - uploading same file twice → 409 EXACT_DUPLICATE on second upload (FIX #9)
    - ?force=true bypasses exact duplicate block and creates new report (FIX #9)
    - DUPLICATE_OVERRIDE audit entry written when force=true used (FIX #9)
    - same upload_document_type + ±3% size + within 72h → 200 with duplicate_warning in body (FIX #9, FIX 10)
    - PROBABLE_DUPLICATE_WARNING audit entry written for soft warn (FIX #9)
    - different patient same file → no duplicate detection triggered (FIX #9 scope)

  test_verification.py:
    - doctor verification inserts new row, does NOT upsert (FIX #2)
    - patient re-edit inserts additional row — history preserved (FIX #2)
    - latest row reflects current state (FIX #2)
    - doctor verification locks field permanently (is_final=True)
    - locked field raises 403 on further edit
    - all fields doctor_verified → lifecycle_status = 'fully_verified' (FIX #3)
    - is_locked column does NOT exist (FIX #3)
    - HITL field value is None for patient requests (FIX #4)
    - HITL field display_value = "Verification required" for patient (FIX #4)
    - HITL field blocks EDA until doctor_verified (FIX #4)
    - doctor sees HITL field value (FIX #4)

  test_admin.py:
    - admin can reset any user's password
    - admin assignment is immediately active
```

---

## 15. Critical Implementation Notes

**Existing test data must survive.** The `document_jobs` and `report_fields` tables have existing rows from Pipeline A testing. Every `ALTER TABLE` must use `ADD COLUMN IF NOT EXISTS` with a default value. Never add a `NOT NULL` column without a `DEFAULT`. Run migration 001 and verify existing rows still exist before proceeding.

**`structured_text_for_embedding` removal is in migration 002, not 001.** Run migration 002 only after confirming Qdrant ingestion works and Pipeline B can retrieve data without this column. If you remove it before Qdrant is populated, Pipeline B will have nothing to query.

**Patient confirmation checkpoint is security-critical.** A doctor accidentally uploading a report to the wrong patient's record is a patient safety failure. The system must require the doctor to provide the `patient_uid` before finalizing the upload, and the API must return a 400 if the provided `patient_uid` doesn't match the resolved patient.

**Doctor verification is permanent.** Once `is_final=True` exists in `field_verifications` for a field, no subsequent API call — from any user, any role — may change that field's value. The verification service must check for `is_final=TRUE` rows before any update, not rely on UI.

**FIX #2 — Never upsert field_verifications.** Always INSERT. Fetch current state with `get_current_field_verification()`. Fetch history with `get_field_verification_history()`. The UNIQUE constraint is gone — the service layer is the guard.

**FIX #3 — `is_locked` does not exist.** Re-upload guard: check `SELECT 1 FROM field_verifications WHERE report_id=? AND is_final=TRUE LIMIT 1`. If any final field exists, block re-upload with 403. `lifecycle_status='fully_verified'` is the only soft state signal.

**FIX #4 — HITL hiding is server-enforced, not UI-enforced.** The API response for patient field access must never return the value of an unverified HITL field. Set `value=None` and `display_value="Verification required"` in the response schema. Do not trust the frontend to hide it.

**FIX #7 — Versioned storage: old versions are kept.** On re-upload, write to `v{new_count}/` — do not delete `v{old_count}/`. This preserves the audit trail of uploaded files. Only the current `file_path` in `reports` points to the latest version.

**Re-upload must reset Pipeline B cache.** After re-upload, `invalidate_patient(patient_id)` must be called so stale reasoning results aren't returned. Then `ingest_patient_record` must be called after Pipeline A re-processes the new file so Qdrant has fresh vectors.

**All Pipeline B calls from the product layer must pass an access guard first.** The pattern is: `verify_doctor_patient_access(doctor_id, patient_id, db)` before any `pipeline_b.*` call. Pipeline B itself knows nothing about assignments — it will happily return any patient's data if asked. The product layer is the only guard.

**Audit log writes must never block the main request.** Wrap all `audit_log` inserts in try/except. A failed audit write must log a warning but not fail the API response. The audit log is observability, not a transaction requirement.

**`numeric_value` backfill in migration 001** — use `REPLACE(value, ',', '')` before casting to handle Indian comma format (`"1,50,000"`). The migration already does this. Test on existing data before running in production.

**FIX #9 — Hash must be computed from in-memory bytes, never re-read from disk.** File I/O between compute and save can race. Always compute `hashlib.sha256(file_bytes).hexdigest()` immediately after reading the upload request body, before any other operation. This is the source of truth for TIER 1 detection. On re-upload, apply the same rule — hash the new bytes before overwriting storage.

**FIX #9 — TIER 1 is a hard block, TIER 2 is advisory.** A 409 from TIER 1 must never be silently swallowed by the service layer. A TIER 2 warning must always appear in the response body even if no frontend currently displays it. The audit entry for both tiers must include `existing_report_id` and `file_hash` in the metadata field for forensics.

**FIX #9 — `?force=true` is an intentional escape hatch, not a bug.** The same file may legitimately need to be re-submitted (e.g., same lab report sent by a different doctor, or patient re-uploading to a different session). `force=true` allows this but always writes a `DUPLICATE_OVERRIDE` audit entry so the override is traceable.

**FIX 10 — `document_type` is now TWO columns, not one.** `upload_document_type` is determined from MIME/magic bytes immediately at upload time (e.g. `'application/pdf'`). `inferred_document_type` is set by Pipeline A after semantic analysis (e.g. `'cbc'`, `'lipid_panel'`). TIER 2 duplicate detection uses `upload_document_type` as the primary comparison field because it is always available at upload time. The old single `document_type` column no longer exists — all code referencing it must be updated to use the appropriate split field.

**FIX 11 — `duplicate_of` always points to the most recent match.** When multiple reports match in TIER 1 or TIER 2, always use `ORDER BY first_uploaded_at DESC LIMIT 1` to select the most recent one. This is deterministic and avoids arbitrary selection. The selection rule must be documented in every query that sets `duplicate_of`.

**FIX 12 — Analytics dedup ORDER BY includes `last_edited_at`.** The refined rule is: `ORDER BY is_duplicate ASC, last_edited_at DESC NULLS LAST, first_uploaded_at DESC`. This ensures that a corrected/re-uploaded report (which has `last_edited_at` set) wins over a stale original. Every analytics function must use this ordering — the old `ORDER BY is_duplicate ASC, first_uploaded_at DESC` is insufficient.

**FIX 13 — Ingestion-layer dedup is optional but recommended.** When `on_pipeline_a_complete` fires with `inferred_document_type`, optionally re-evaluate TIER 2 using the semantic type. If a match is found, update `is_duplicate` and `duplicate_of` on the report. This is NOT mandatory — query-time dedup (FIX 9c/12) handles it regardless — but it speeds up analytics queries and provides earlier visibility.

**FIX 14 — Concurrency race condition is accepted at current scale.** Two simultaneous uploads of the same file can both pass TIER 1 before either inserts. This is extremely rare and is handled by the analytics dedup layer. No UNIQUE(patient_id, file_hash) constraint is added because it would break `?force=true`. For strict mode at scale, use `SELECT ... FOR UPDATE` in a transaction.

---

## 16. Agent Checklist — Before Marking Any Step Complete

- [ ] No Pipeline A or Pipeline B files were modified
- [ ] Migration 001 ran successfully — all 5 new tables exist
- [ ] `field_verifications` has NO UNIQUE constraint (FIX #2)
- [ ] `reports` has NO `is_locked` column (FIX #3)
- [ ] Existing `document_jobs` and `report_fields` rows still exist after migration
- [ ] Migration 002 NOT run yet (run only after Qdrant confirmed working)
- [ ] All new columns on existing tables have DEFAULT values
- [ ] `SECRET_KEY` added to `shared/config.py` and `.env.example`
- [ ] `STORAGE_PATH` added to config
- [ ] `RATE_LIMIT_STORAGE_URI`, `LOGIN_RATE_LIMIT`, `UPLOAD_RATE_LIMIT` added to config (FIX #6)
- [ ] JWT encode/decode verified with inline test
- [ ] Doctor signup creates user with role=doctor, no patient_uid
- [ ] Patient signup creates user with role=patient, auto patient_uid (PAT-XXXXX)
- [ ] Pre-registered patient activates via patient_uid claim flow (FIX #5)
- [ ] Pre-registered patient activates via email fallback (FIX #5)
- [ ] Login rate limited to 5 attempts per 15 minutes per IP (FIX #6)
- [ ] Upload rate limited to 10 per hour per user (FIX #6)
- [ ] Doctor upload resolves patient by patient_uid first, email fallback second (FIX #5)
- [ ] Upload stores file at storage/{patient_id}/{report_id}/v1/ (FIX #7)
- [ ] Re-upload stores at v{upload_count}/ without deleting old versions (FIX #7)
- [ ] `reports.file_hash` column exists (VARCHAR 64, nullable) with index on (patient_id, file_hash) (FIX #9)
- [ ] compute_file_hash() in file_storage.py uses hashlib.sha256, called before save_file (FIX #9)
- [ ] TIER 1: same patient + same hash → 409 EXACT_DUPLICATE (FIX #9)
- [ ] TIER 1: ?force=true bypasses block and writes DUPLICATE_OVERRIDE audit entry (FIX #9)
- [ ] TIER 2: same upload_document_type + ±3% size + within 72h → 200 with duplicate_warning in body (FIX #9, FIX 10)
- [ ] TIER 2: PROBABLE_DUPLICATE_WARNING audit entry written on soft warn (FIX #9)
- [ ] Duplicate detection is patient-scoped only — no cross-patient hash checks (FIX #9)
- [ ] Re-upload runs TIER 1 check on new file hash before writing storage (FIX #9)
- [ ] reports.file_hash updated on re-upload (FIX #9)
- [ ] Re-upload blocked if any is_final=TRUE field exists (FIX #3)
- [ ] Re-upload resets ALL field_verifications rows for that report
- [ ] Re-upload calls `invalidate_patient()` from Pipeline B cache
- [ ] Field verification uses INSERT not upsert (FIX #2)
- [ ] get_current_field_verification() fetches latest row by verified_at DESC (FIX #2)
- [ ] Doctor verification sets `is_final=True` and subsequent edits return 403
- [ ] All-fields doctor_verified → `lifecycle_status='fully_verified'` only — no is_locked (FIX #3)
- [ ] HITL field returns value=None + display_value="Verification required" for patient role (FIX #4)
- [ ] Doctor always sees HITL field value (FIX #4)
- [ ] Patient analytics: SQL aggregation only, no LLM involvement (FIX #8)
- [ ] Analytics code has comment: "# ANALYTICS: SQL engine only — never LLM" (FIX #8)
- [ ] Every Pipeline B call checks doctor-patient assignment first
- [ ] Audit log write is wrapped in try/except — never blocks main request
- [ ] Notification creates a row — never sends email (MVP: in-app only)
- [ ] All routes have role guard: `Depends(require_role(...))`
- [ ] Every directory in `product/` has `__init__.py`
- [ ] `reports` has `upload_document_type` column (VARCHAR 100, NOT NULL, DEFAULT 'unknown') — set from MIME at upload (FIX 10)
- [ ] `reports` has `inferred_document_type` column (VARCHAR 50, DEFAULT 'unknown') — set by on_pipeline_a_complete (FIX 10)
- [ ] Old single `document_type` column does NOT exist on reports table (FIX 10)
- [ ] TIER 2 uses `upload_document_type` for comparison, NOT `inferred_document_type` (FIX 10)
- [ ] `on_pipeline_a_complete` receives and sets `inferred_document_type` (FIX 10)
- [ ] `idx_reports_metadata_dup` indexes on `upload_document_type`, not old `document_type` (FIX 10)
- [ ] TIER 1 query uses `ORDER BY first_uploaded_at DESC LIMIT 1` for deterministic selection (FIX 11)
- [ ] TIER 2 query uses `ORDER BY first_uploaded_at DESC LIMIT 1` for deterministic selection (FIX 11)
- [ ] `duplicate_of` always points to most recent matching report (FIX 11)
- [ ] Analytics dedup ORDER BY: `is_duplicate ASC, last_edited_at DESC NULLS LAST, first_uploaded_at DESC` (FIX 12)
- [ ] Pattern A (DISTINCT ON) and Pattern B (ROW_NUMBER) both use refined ORDER BY (FIX 12)
- [ ] `on_pipeline_a_complete` optionally re-evaluates TIER 2 with `inferred_document_type` (FIX 13)
- [ ] No UNIQUE(patient_id, file_hash) constraint on reports table — race condition accepted (FIX 14)
- [ ] Concurrency strategy documented in Section 4a (FIX 14)
- [ ] Re-upload resets `inferred_document_type` to 'unknown', re-detects `upload_document_type` from new file MIME (FIX 10)