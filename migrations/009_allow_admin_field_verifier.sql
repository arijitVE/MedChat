DO $$
DECLARE
    constraint_name text;
BEGIN
    SELECT c.conname
    INTO constraint_name
    FROM pg_constraint c
    JOIN pg_class t ON t.oid = c.conrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE t.relname = 'field_verifications'
      AND n.nspname = current_schema()
      AND c.contype = 'c'
      AND pg_get_constraintdef(c.oid) LIKE '%verifier_role%'
    LIMIT 1;

    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE field_verifications DROP CONSTRAINT %I', constraint_name);
    END IF;
END $$;

ALTER TABLE field_verifications
    ADD CONSTRAINT field_verifications_verifier_role_check
    CHECK (verifier_role IN ('patient', 'doctor', 'admin'));
