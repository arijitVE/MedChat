CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    user_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('doctor', 'patient', 'admin')),
    full_name       VARCHAR(255) NOT NULL,
    phone           VARCHAR(20),
    license_number  VARCHAR(100),
    specialization  VARCHAR(100),
    patient_uid     VARCHAR(20) UNIQUE,
    date_of_birth   DATE,
    sex             VARCHAR(10),
    is_registered   BOOLEAN DEFAULT TRUE,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_patient_uid ON users(patient_uid) WHERE patient_uid IS NOT NULL;

CREATE TABLE IF NOT EXISTS doctor_patient_assignments (
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

CREATE INDEX IF NOT EXISTS idx_assignments_doctor ON doctor_patient_assignments(doctor_id);
CREATE INDEX IF NOT EXISTS idx_assignments_patient ON doctor_patient_assignments(patient_id);
CREATE INDEX IF NOT EXISTS idx_assignments_status ON doctor_patient_assignments(status);

CREATE TABLE IF NOT EXISTS reports (
    report_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id                 VARCHAR(255) UNIQUE NOT NULL REFERENCES document_jobs(job_id),
    patient_id             UUID NOT NULL REFERENCES users(user_id),
    uploaded_by            UUID NOT NULL REFERENCES users(user_id),
    doctor_id              UUID REFERENCES users(user_id),
    file_path              VARCHAR(500) NOT NULL,
    file_name              VARCHAR(255) NOT NULL,
    file_mime              VARCHAR(100) NOT NULL,
    file_size_bytes        INTEGER,
    upload_document_type   VARCHAR(100) NOT NULL DEFAULT 'unknown',
    inferred_document_type VARCHAR(50) DEFAULT 'unknown',
    lifecycle_status       VARCHAR(30) NOT NULL DEFAULT 'uploaded'
                           CHECK (lifecycle_status IN (
                               'uploaded', 'processing', 'auto_approved',
                               'hitl_required', 'patient_verified',
                               'doctor_verified', 'fully_verified',
                               'failed'
                           )),
    released_to_patient    BOOLEAN DEFAULT FALSE,
    first_uploaded_at      TIMESTAMPTZ DEFAULT NOW(),
    last_edited_at         TIMESTAMPTZ,
    upload_count           INTEGER DEFAULT 1,
    file_hash              VARCHAR(64),
    is_duplicate           BOOLEAN DEFAULT FALSE,
    duplicate_of           UUID REFERENCES reports(report_id)
);

CREATE INDEX IF NOT EXISTS idx_reports_patient ON reports(patient_id);
CREATE INDEX IF NOT EXISTS idx_reports_doctor ON reports(doctor_id);
CREATE INDEX IF NOT EXISTS idx_reports_job ON reports(job_id);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(lifecycle_status);
CREATE INDEX IF NOT EXISTS idx_reports_hash ON reports(patient_id, file_hash) WHERE file_hash IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_reports_metadata_dup
    ON reports(patient_id, upload_document_type, file_size_bytes, first_uploaded_at)
    WHERE upload_document_type != 'unknown';

CREATE TABLE IF NOT EXISTS field_verifications (
    verification_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id           UUID NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    job_id              VARCHAR(255) NOT NULL,
    field_name          VARCHAR(255) NOT NULL,
    field_value         TEXT,
    verified_by         UUID NOT NULL REFERENCES users(user_id),
    verifier_role       VARCHAR(20) NOT NULL CHECK (verifier_role IN ('patient', 'doctor')),
    verification_type   VARCHAR(20) NOT NULL
                        CHECK (verification_type IN ('approved', 'edited', 'rejected')),
    edited_value        TEXT,
    edit_reason         TEXT,
    is_final            BOOLEAN DEFAULT FALSE,
    verified_at         TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fv_report ON field_verifications(report_id);
CREATE INDEX IF NOT EXISTS idx_fv_field ON field_verifications(report_id, field_name);
CREATE INDEX IF NOT EXISTS idx_fv_field_time ON field_verifications(report_id, field_name, verified_at DESC);
CREATE INDEX IF NOT EXISTS idx_fv_final ON field_verifications(is_final) WHERE is_final = TRUE;

CREATE TABLE IF NOT EXISTS audit_log (
    log_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(user_id),
    user_role       VARCHAR(20),
    action          VARCHAR(50) NOT NULL,
    entity_type     VARCHAR(50),
    entity_id       VARCHAR(255),
    report_id       UUID REFERENCES reports(report_id),
    field_name      VARCHAR(255),
    old_value       TEXT,
    new_value       TEXT,
    metadata        JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_report ON audit_log(report_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_id    UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    sender_id       UUID REFERENCES users(user_id),
    type            VARCHAR(50) NOT NULL,
    title           VARCHAR(255) NOT NULL,
    message         TEXT NOT NULL,
    report_id       UUID REFERENCES reports(report_id),
    is_read         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notif_recipient ON notifications(recipient_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notif_created ON notifications(created_at);

CREATE TABLE IF NOT EXISTS file_storage_refs (
    file_ref_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id        UUID NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    patient_id       UUID NOT NULL REFERENCES users(user_id),
    file_path        VARCHAR(500) NOT NULL,
    file_name        VARCHAR(255) NOT NULL,
    file_mime        VARCHAR(100) NOT NULL,
    file_size_bytes  INTEGER,
    upload_count     INTEGER NOT NULL DEFAULT 1,
    version          INTEGER NOT NULL DEFAULT 1,
    file_hash        VARCHAR(64),
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_file_refs_report ON file_storage_refs(report_id);
CREATE INDEX IF NOT EXISTS idx_file_refs_patient ON file_storage_refs(patient_id);

ALTER TABLE document_jobs
    ADD COLUMN IF NOT EXISTS uploaded_by_user_id UUID DEFAULT '00000000-0000-0000-0000-000000000000'::uuid,
    ADD COLUMN IF NOT EXISTS upload_source VARCHAR(20) DEFAULT 'unknown'
        CHECK (upload_source IN ('doctor', 'patient', 'system', 'unknown')),
    ADD COLUMN IF NOT EXISTS collection_date DATE DEFAULT CURRENT_DATE;

CREATE INDEX IF NOT EXISTS idx_rf_field_name ON report_fields(name);
CREATE INDEX IF NOT EXISTS idx_rf_patient ON report_fields(patient_id);
CREATE INDEX IF NOT EXISTS idx_rf_collection_date ON report_fields(collection_date);

ALTER TABLE report_fields
    ADD COLUMN IF NOT EXISTS numeric_value FLOAT;

UPDATE report_fields
SET numeric_value = CAST(REPLACE(value, ',', '') AS FLOAT)
WHERE REPLACE(value, ',', '') ~ '^[0-9]+\.?[0-9]*$';
