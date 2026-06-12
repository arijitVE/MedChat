CREATE TABLE IF NOT EXISTS document_jobs (
    job_id VARCHAR(64) PRIMARY KEY,
    patient_id VARCHAR(128) NOT NULL,
    document_type VARCHAR(32) NOT NULL,
    file_name VARCHAR(512),
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    hitl_required BOOLEAN NOT NULL DEFAULT FALSE,
    hitl_reasons JSON,
    structured_text_for_embedding TEXT,
    uploaded_at DATETIME(6),
    processed_at DATETIME(6),
    error_message TEXT,
    ocr_latency_ms DOUBLE,
    llm_latency_ms DOUBLE,
    uploaded_by_user_id CHAR(36) DEFAULT '00000000-0000-0000-0000-000000000000',
    upload_source VARCHAR(20) DEFAULT 'unknown',
    collection_date DATE DEFAULT (CURRENT_DATE),
    UNIQUE KEY uq_document_jobs_job_id (job_id),
    KEY idx_document_jobs_patient_id (patient_id)
);

CREATE TABLE IF NOT EXISTS ocr_outputs (
    job_id VARCHAR(64) PRIMARY KEY,
    raw_text TEXT NOT NULL,
    words_json JSON,
    page_count INTEGER NOT NULL DEFAULT 1,
    avg_confidence DOUBLE NOT NULL DEFAULT 0.0,
    low_confidence BOOLEAN NOT NULL DEFAULT FALSE,
    ocr_latency_ms DOUBLE,
    UNIQUE KEY uq_ocr_outputs_job_id (job_id)
);

CREATE TABLE IF NOT EXISTS report_fields (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    job_id VARCHAR(64) NOT NULL,
    patient_id VARCHAR(128) NOT NULL,
    name VARCHAR(256) NOT NULL,
    value TEXT NOT NULL,
    unit VARCHAR(64),
    reference_range VARCHAR(128),
    collection_date VARCHAR(32),
    numeric_value DOUBLE,
    confidence DOUBLE NOT NULL DEFAULT 0.0,
    status VARCHAR(16) NOT NULL DEFAULT 'auto',
    hitl_reason TEXT,
    UNIQUE KEY uq_report_fields_job_id_name (job_id, name),
    KEY idx_report_fields_job_id (job_id),
    KEY idx_rf_patient (patient_id),
    KEY idx_rf_field_name (name),
    KEY idx_rf_collection_date (collection_date),
    CONSTRAINT fk_report_fields_job FOREIGN KEY (job_id)
        REFERENCES document_jobs(job_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS match_results (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    job_id VARCHAR(64) NOT NULL,
    field_name VARCHAR(256) NOT NULL,
    llm_value VARCHAR(512) NOT NULL,
    ocr_best_phrase VARCHAR(512) NOT NULL DEFAULT '',
    fuzzy_score DOUBLE NOT NULL DEFAULT 0.0,
    semantic_score DOUBLE NOT NULL DEFAULT 0.0,
    combined_score DOUBLE NOT NULL DEFAULT 0.0,
    UNIQUE KEY uq_match_results_job_id_field_name (job_id, field_name),
    KEY idx_match_results_job_id (job_id)
);

CREATE TABLE IF NOT EXISTS confidence_breakdowns (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    job_id VARCHAR(64) NOT NULL,
    field_name VARCHAR(256) NOT NULL,
    combined_match_score DOUBLE NOT NULL DEFAULT 0.0,
    ocr_word_confidence DOUBLE NOT NULL DEFAULT 0.5,
    final_score DOUBLE NOT NULL DEFAULT 0.0,
    status VARCHAR(16) NOT NULL DEFAULT 'auto',
    hitl_reason VARCHAR(512),
    UNIQUE KEY uq_confidence_breakdowns_job_id_field_name (job_id, field_name),
    KEY idx_confidence_breakdowns_job_id (job_id)
);

CREATE TABLE IF NOT EXISTS hitl_queue (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    job_id VARCHAR(64) NOT NULL,
    patient_id VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending_review',
    priority INTEGER NOT NULL DEFAULT 0,
    hitl_reasons JSON,
    hitl_field_count INTEGER NOT NULL DEFAULT 0,
    assigned_to VARCHAR(128),
    reviewed_at DATETIME(6),
    review_notes TEXT,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_hitl_queue_job_id (job_id),
    KEY idx_hitl_queue_job_id (job_id),
    KEY idx_hitl_queue_patient_id (patient_id)
);

CREATE TABLE IF NOT EXISTS users (
    user_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    license_number VARCHAR(100),
    specialization VARCHAR(100),
    hospital_name VARCHAR(255),
    years_of_experience INTEGER,
    department VARCHAR(255),
    profile_photo VARCHAR(500),
    verification_status VARCHAR(30) NOT NULL DEFAULT 'approved',
    verification_rejection_reason TEXT,
    patient_uid VARCHAR(20) UNIQUE,
    date_of_birth DATE,
    sex VARCHAR(30),
    age INTEGER,
    gender VARCHAR(30),
    blood_group VARCHAR(10),
    allergies TEXT,
    chronic_conditions TEXT,
    address TEXT,
    emergency_contact VARCHAR(255),
    last_login DATETIME(6),
    is_registered BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    KEY idx_users_email (email),
    KEY idx_users_role (role),
    KEY idx_users_patient_uid (patient_uid),
    KEY idx_users_doctor_verification (role, verification_status),
    CHECK (role IN ('doctor', 'patient', 'admin')),
    CHECK (verification_status IN ('pending_verification', 'approved', 'rejected', 'suspended'))
);

CREATE TABLE IF NOT EXISTS doctor_patient_assignments (
    assignment_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    doctor_id CHAR(36) NOT NULL,
    patient_id CHAR(36) NOT NULL,
    assigned_by VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY uq_assignment_doctor_patient (doctor_id, patient_id),
    KEY idx_assignments_doctor (doctor_id),
    KEY idx_assignments_patient (patient_id),
    KEY idx_assignments_status (status),
    CONSTRAINT fk_assignments_doctor FOREIGN KEY (doctor_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_assignments_patient FOREIGN KEY (patient_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CHECK (assigned_by IN ('admin', 'doctor', 'patient')),
    CHECK (status IN ('pending', 'active', 'rejected'))
);

CREATE TABLE IF NOT EXISTS reports (
    report_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    job_id VARCHAR(64) UNIQUE NOT NULL,
    patient_id CHAR(36) NOT NULL,
    uploaded_by CHAR(36) NOT NULL,
    doctor_id CHAR(36),
    file_path VARCHAR(500) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_mime VARCHAR(100) NOT NULL,
    file_size_bytes INTEGER,
    upload_document_type VARCHAR(100) NOT NULL DEFAULT 'unknown',
    inferred_document_type VARCHAR(50) DEFAULT 'unknown',
    lifecycle_status VARCHAR(30) NOT NULL DEFAULT 'uploaded',
    released_to_patient BOOLEAN DEFAULT FALSE,
    first_uploaded_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    last_edited_at DATETIME(6),
    upload_count INTEGER DEFAULT 1,
    file_hash VARCHAR(64),
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of CHAR(36),
    KEY idx_reports_patient (patient_id),
    KEY idx_reports_doctor (doctor_id),
    KEY idx_reports_job (job_id),
    KEY idx_reports_status (lifecycle_status),
    KEY idx_reports_hash (patient_id, file_hash),
    KEY idx_reports_metadata_dup (patient_id, upload_document_type, file_size_bytes, first_uploaded_at),
    CONSTRAINT fk_reports_job FOREIGN KEY (job_id) REFERENCES document_jobs(job_id),
    CONSTRAINT fk_reports_patient FOREIGN KEY (patient_id) REFERENCES users(user_id),
    CONSTRAINT fk_reports_uploaded_by FOREIGN KEY (uploaded_by) REFERENCES users(user_id),
    CONSTRAINT fk_reports_doctor FOREIGN KEY (doctor_id) REFERENCES users(user_id),
    CONSTRAINT fk_reports_duplicate FOREIGN KEY (duplicate_of) REFERENCES reports(report_id),
    CHECK (lifecycle_status IN (
        'uploaded', 'processing', 'auto_approved', 'hitl_required',
        'patient_verified', 'doctor_verified', 'fully_verified', 'failed'
    ))
);

CREATE TABLE IF NOT EXISTS field_verifications (
    verification_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    report_id CHAR(36) NOT NULL,
    job_id VARCHAR(64) NOT NULL,
    field_name VARCHAR(255) NOT NULL,
    field_value TEXT,
    verified_by CHAR(36) NOT NULL,
    verifier_role VARCHAR(20) NOT NULL,
    verification_type VARCHAR(20) NOT NULL,
    edited_value TEXT,
    edit_reason TEXT,
    is_final BOOLEAN DEFAULT FALSE,
    verified_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    KEY idx_fv_report (report_id),
    KEY idx_fv_field (report_id, field_name),
    KEY idx_fv_field_time (report_id, field_name, verified_at DESC),
    KEY idx_fv_final (is_final),
    CONSTRAINT fk_fv_report FOREIGN KEY (report_id) REFERENCES reports(report_id) ON DELETE CASCADE,
    CONSTRAINT fk_fv_verified_by FOREIGN KEY (verified_by) REFERENCES users(user_id),
    CHECK (verifier_role IN ('patient', 'doctor', 'admin')),
    CHECK (verification_type IN ('approved', 'edited', 'rejected'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    log_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    user_id CHAR(36),
    user_role VARCHAR(20),
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id VARCHAR(255),
    report_id CHAR(36),
    field_name VARCHAR(255),
    old_value TEXT,
    new_value TEXT,
    metadata JSON,
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    KEY idx_audit_user (user_id),
    KEY idx_audit_report (report_id),
    KEY idx_audit_action (action),
    KEY idx_audit_created (created_at),
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_audit_report FOREIGN KEY (report_id) REFERENCES reports(report_id)
);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    recipient_id CHAR(36) NOT NULL,
    sender_id CHAR(36),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    report_id CHAR(36),
    is_read BOOLEAN DEFAULT FALSE,
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    KEY idx_notif_recipient (recipient_id, is_read),
    KEY idx_notif_created (created_at),
    CONSTRAINT fk_notif_recipient FOREIGN KEY (recipient_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_notif_sender FOREIGN KEY (sender_id) REFERENCES users(user_id),
    CONSTRAINT fk_notif_report FOREIGN KEY (report_id) REFERENCES reports(report_id)
);

CREATE TABLE IF NOT EXISTS file_storage_refs (
    file_ref_id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    report_id CHAR(36) NOT NULL,
    patient_id CHAR(36) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_mime VARCHAR(100) NOT NULL,
    file_size_bytes INTEGER,
    upload_count INTEGER NOT NULL DEFAULT 1,
    version INTEGER NOT NULL DEFAULT 1,
    file_hash VARCHAR(64),
    created_at DATETIME(6) DEFAULT CURRENT_TIMESTAMP(6),
    KEY idx_file_refs_report (report_id),
    KEY idx_file_refs_patient (patient_id),
    CONSTRAINT fk_file_refs_report FOREIGN KEY (report_id) REFERENCES reports(report_id) ON DELETE CASCADE,
    CONSTRAINT fk_file_refs_patient FOREIGN KEY (patient_id) REFERENCES users(user_id)
);
