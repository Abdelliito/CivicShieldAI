-- Additive, idempotent upgrade for existing installations; preserves all rows.
-- Run after 001_schema.sql, or let FastAPI startup apply this transactionally.
ALTER TABLE attachments ADD COLUMN IF NOT EXISTS analysis JSON NOT NULL DEFAULT '{}'::json;
ALTER TABLE assignments ADD COLUMN IF NOT EXISTS sharing_scope VARCHAR(20) NOT NULL DEFAULT 'full_report';
ALTER TABLE assignments ADD COLUMN IF NOT EXISTS worker_id INTEGER REFERENCES users(id);
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'assignments'::regclass
          AND conname = 'valid_assignment_sharing_scope'
    ) THEN
        ALTER TABLE assignments ADD CONSTRAINT valid_assignment_sharing_scope
        CHECK (sharing_scope IN ('full_report','location_only'));
    END IF;
END $$;
