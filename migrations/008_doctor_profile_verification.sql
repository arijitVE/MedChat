ALTER TABLE users
    ADD COLUMN IF NOT EXISTS hospital_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS years_of_experience INTEGER,
    ADD COLUMN IF NOT EXISTS department VARCHAR(255),
    ADD COLUMN IF NOT EXISTS profile_photo VARCHAR(500),
    ADD COLUMN IF NOT EXISTS verification_status VARCHAR(30) NOT NULL DEFAULT 'approved'
        CHECK (verification_status IN (
            'pending_verification',
            'approved',
            'rejected',
            'suspended'
        )),
    ADD COLUMN IF NOT EXISTS verification_rejection_reason TEXT;

UPDATE users
SET verification_status = 'approved'
WHERE role != 'doctor'
  AND verification_status IS NULL;

CREATE INDEX IF NOT EXISTS idx_users_doctor_verification
    ON users(role, verification_status)
    WHERE role = 'doctor';
