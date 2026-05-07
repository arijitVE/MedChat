ALTER TABLE document_jobs
    ALTER COLUMN uploaded_by_user_id SET DEFAULT '00000000-0000-0000-0000-000000000000'::uuid,
    ALTER COLUMN collection_date SET DEFAULT CURRENT_DATE;

UPDATE document_jobs
SET uploaded_by_user_id = '00000000-0000-0000-0000-000000000000'::uuid
WHERE uploaded_by_user_id IS NULL;

UPDATE document_jobs
SET collection_date = COALESCE(uploaded_at::date, CURRENT_DATE)
WHERE collection_date IS NULL;

ALTER TABLE reports
    ADD CONSTRAINT reports_job_id_document_jobs_fkey
    FOREIGN KEY (job_id) REFERENCES document_jobs(job_id);
