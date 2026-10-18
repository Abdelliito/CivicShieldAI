"""Windows local-only PostgreSQL setup. Never prints credentials; preserves existing .env."""
from pathlib import Path
import base64
import hashlib
import json
import secrets
import subprocess
import tarfile
import urllib.request
import os
from dotenv import dotenv_values
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'
RUNTIME.mkdir(exist_ok=True)
PACKAGE = '@embedded-postgres/windows-x64'
VERSION = '18.4.0-beta.17'
PG = RUNTIME / 'package/native/bin'
if not (PG / 'pg_ctl.exe').exists():
    metadata = json.load(urllib.request.urlopen(f'https://registry.npmjs.org/{PACKAGE}/{VERSION}'))
    archive = RUNTIME / 'postgres.tgz'
    urllib.request.urlretrieve(metadata['dist']['tarball'], archive)
    digest = 'sha512-' + base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode()
    if digest != metadata['dist']['integrity']:
        raise RuntimeError('PostgreSQL binary package integrity mismatch')
    with tarfile.open(archive) as bundle:
        for member in bundle.getmembers():
            target = (RUNTIME / member.name).resolve()
            if RUNTIME.resolve() not in target.parents:
                raise RuntimeError('Invalid package archive path')
        bundle.extractall(RUNTIME)
env_path = ROOT / '.env'
if not env_path.exists():
    password = secrets.token_hex(20)
    env_path.write_text(
        f'DATABASE_URL=postgresql+psycopg2://civicshield:{password}@127.0.0.1:54329/civicshield\n'
        f'JWT_SECRET={secrets.token_urlsafe(48)}\nDEMO_MODE=true\n'
        'CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173\nWEATHER_REFRESH_MINUTES=30\n'
    )
cfg = dotenv_values(env_path)
url = cfg['DATABASE_URL'].replace('postgresql+psycopg2://', 'postgresql://')
from urllib.parse import urlsplit
parsed = urlsplit(url)
data = RUNTIME / 'pgdata'
if not data.exists():
    pwfile = RUNTIME / 'pg-password'
    pwfile.write_text(parsed.password)
    try:
        subprocess.run([str(PG/'initdb.exe'), '-D', str(data), '-U', parsed.username,
                        f'--pwfile={pwfile}', '--auth=scram-sha-256', '--encoding=UTF8', '--locale=C'], check=True)
    finally:
        pwfile.unlink(missing_ok=True)
status = subprocess.run([str(PG/'pg_ctl.exe'), '-D', str(data), 'status'], capture_output=True)
if status.returncode:
    subprocess.run([str(PG/'pg_ctl.exe'), '-D', str(data), '-l', str(RUNTIME/'postgres.log'),
                    '-o', f'-p {parsed.port or 54329} -h 127.0.0.1', '-w', 'start'], check=True)

conn = psycopg2.connect(url.rsplit('/', 1)[0] + '/postgres')

try:
    conn.autocommit = True

    with conn.cursor() as cur:
        for name in ('civicshield', 'civicshield_test'):
            cur.execute(
                'SELECT 1 FROM pg_database WHERE datname = %s',
                (name,)
            )

            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{name}"')
finally:
    conn.close()

print('Local PostgreSQL ready; existing credentials preserved.')

