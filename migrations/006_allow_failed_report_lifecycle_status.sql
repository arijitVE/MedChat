ALTER TABLE reports
    DROP CONSTRAINT IF EXISTS reports_lifecycle_status_check;

ALTER TABLE reports
    ADD CONSTRAINT reports_lifecycle_status_check
    CHECK (lifecycle_status IN (
        'uploaded',
        'processing',
        'auto_approved',
        'hitl_required',
        'patient_verified',
        'doctor_verified',
        'fully_verified',
        'failed'
    ));
