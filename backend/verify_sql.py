"""Execute delivered SQL scripts in an isolated generated PostgreSQL schema."""
import uuid
from sqlalchemy import text
from app.config import ROOT
from app.db import engine


def main():
    namespace = 'civicshield_sql_verify_' + uuid.uuid4().hex
    try:
        with engine.connect() as connection:
            connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
            connection.execute(text(f'SET search_path TO "{namespace}"'))
            connection.commit()
            raw = connection.connection.driver_connection
            with raw.cursor() as cursor:
                cursor.execute((ROOT / 'database' / '001_schema.sql').read_text(encoding='utf-8'))
                cursor.execute("SET civicshield.demo_mode = 'on'")
                cursor.execute((ROOT / 'database' / '002_seed.sql').read_text(encoding='utf-8'))
                cursor.execute('SELECT COUNT(*) FROM incidents')
                incidents = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM users')
                users = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM risk_assessments')
                assessments = cursor.fetchone()[0]
                assert incidents == 12 and users == 4 and assessments >= 4
            raw.commit()
            print(f'SQL verified on PostgreSQL: {incidents} synthetic incidents, {users} role accounts, {assessments} risk assessments; all foreign keys and constraints valid.')
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{namespace}" CASCADE'))


if __name__ == '__main__':
    main()
