"""Small additive schema upgrades, safe for existing CivicShield databases.

No records are recreated or deleted. PostgreSQL advisory locking serializes
concurrent server startup; the SQL migration is also available for operators.
"""
from sqlalchemy import text


# Kept with the backend so the existing backend-only Docker build can upgrade
# persisted database volumes without mounting the source checkout.
MIGRATION_SQL = """
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
"""


def apply_migrations(engine):
    with engine.begin() as connection:
        if connection.dialect.name == 'postgresql':
            connection.execute(text('SELECT pg_advisory_xact_lock(734816203)'))
        connection.exec_driver_sql(MIGRATION_SQL)
