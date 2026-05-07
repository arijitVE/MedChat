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
