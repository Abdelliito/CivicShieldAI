"""Rebuild portable PostgreSQL schema + opt-in synthetic seed SQL from ORM.

Uses a uniquely named temporary schema; never modifies application tables.
"""
import json
import uuid
from datetime import date, datetime
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateIndex, CreateTable
from app.config import ROOT, settings
from app.db import Base, engine
from app import models
from app.seed import seed_demo


def literal(value):
    if value is None:
        return 'NULL'
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (dict, list)):
        return "'" + json.dumps(value, ensure_ascii=True).replace("'", "''") + "'::json"
    if isinstance(value, (datetime, date)):
        value = value.isoformat()
    return "'" + str(value).replace("'", "''") + "'"


def main():
    if not settings.demo_mode:
        raise RuntimeError('Exporting synthetic seed SQL requires DEMO_MODE=true.')
    dialect = postgresql.dialect()
    output = ROOT / 'database'
    output.mkdir(exist_ok=True)
    schema_statements = ['-- CivicShield AI PostgreSQL schema; generated from backend/app/models.py.', '-- Run against a fresh PostgreSQL database. No credentials are embedded.', 'BEGIN;']
    for table in Base.metadata.sorted_tables:
        schema_statements.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ';')
        for index in table.indexes:
            schema_statements.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ';')
    schema_statements.append('COMMIT;')
    (output / '001_schema.sql').write_text('\n\n'.join(schema_statements) + '\n', encoding='utf-8')
    namespace = 'civicshield_sql_export_' + uuid.uuid4().hex
    try:
        with engine.connect() as connection:
            connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
            connection.execute(text(f'SET search_path TO "{namespace}"'))
            Base.metadata.create_all(connection)
            connection.commit()
            with Session(bind=connection, expire_on_commit=False) as db:
                seed_demo(db)
            lines = [
                '-- SYNTHETIC LAHORE DEMONSTRATION DATA ONLY.',
                '-- Demo password for all four seeded roles: CivicDemo!2026',
                '-- This is not real weather, real civic data, or a validated disaster forecast.',
                "-- Explicit opt-in required before running: SET civicshield.demo_mode = 'on';",
                'BEGIN;',
                "DO $$ BEGIN IF current_setting('civicshield.demo_mode', true) IS DISTINCT FROM 'on' THEN RAISE EXCEPTION 'Synthetic seed disabled. Explicitly SET civicshield.demo_mode = on first.'; END IF; IF EXISTS (SELECT 1 FROM users) THEN RAISE EXCEPTION 'Seed expects a fresh database with no user accounts.'; END IF; END $$;",
            ]
            for table in Base.metadata.sorted_tables:
                columns = ', '.join(f'"{column.name}"' for column in table.columns)
                for row in connection.execute(table.select().order_by(table.c.id)).mappings():
                    values = ', '.join(literal(row[column.name]) for column in table.columns)
                    lines.append(f'INSERT INTO "{table.name}" ({columns}) VALUES ({values});')
                lines.append(f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), COALESCE((SELECT MAX(id) FROM \"{table.name}\"), 1), EXISTS(SELECT 1 FROM \"{table.name}\"));")
            lines.append('COMMIT;')
            (output / '002_seed.sql').write_text('\n'.join(lines) + '\n', encoding='utf-8')
            connection.rollback()
    finally:
        # namespace is generated above from a fixed prefix and hex UUID, never user input.
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{namespace}" CASCADE'))
    print('Generated database/001_schema.sql and database/002_seed.sql with synthetic data and explicit opt-in.')


if __name__ == '__main__':
    main()
