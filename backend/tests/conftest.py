"""Integration tests use a separate PostgreSQL database and never the demo DB."""
import os
import sys
from pathlib import Path
import pytest
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
configuration = dotenv_values(ROOT / '.env')
test_url = os.getenv('TEST_DATABASE_URL')
if not test_url:
    base_url = make_url(configuration.get('DATABASE_URL') or os.getenv('DATABASE_URL', 'postgresql+psycopg2://civicshield:civicshield@127.0.0.1:5432/civicshield'))
    test_url = base_url.set(database='civicshield_test').render_as_string(hide_password=False)
if not make_url(test_url).database.endswith('_test'):
    raise RuntimeError('TEST_DATABASE_URL must end in _test; tests reset that database schema.')
os.environ['DATABASE_URL'] = test_url
os.environ['JWT_SECRET'] = 'pytest-only-signing-secret-is-at-least-32-characters'
os.environ['DEMO_MODE'] = 'true'
# Never let a developer's configured provider credentials trigger real paid
# image requests during deterministic tests. Provider tests supply local mocks.
for name in set(os.environ) | set(configuration):
    if name.startswith(('VISION_', 'OPENAI_', 'GEMINI_', 'GOOGLE_API_', 'ANTHROPIC_', 'HF_', 'OLLAMA_', 'COMPATIBLE_')):
        os.environ[name] = ''
os.environ['OPENAI_API_KEY'] = ''


@pytest.fixture(scope='session')
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import Base, engine
    Base.metadata.drop_all(engine)
    with TestClient(app) as api:
        yield api


@pytest.fixture(scope='session')
def roles(client):
    result = {}
    for role in ['citizen', 'authority', 'worker', 'admin']:
        response = client.post('/api/auth/login', json={'email': f'{role}@civicshield.demo', 'password': 'CivicDemo!2026'})
        assert response.status_code == 200, response.text
        result[role] = {'Authorization': f'Bearer {response.json()["access_token"]}'}
    return result


@pytest.fixture
def report(client, roles):
    response = client.post('/api/reports', headers=roles['citizen'], json={'title': 'Blocked drain at integration test street', 'description': 'A blocked drain is causing water accumulation after rain near the busy pedestrian crossing.', 'latitude': 31.513, 'longitude': 74.35, 'location_name': 'Synthetic integration test location'})
    assert response.status_code == 201, response.text
    return response.json()
