"""Photo-first reporting and authority-controlled information-sharing regressions.

Provider-contract responses are explicitly mocked; these tests do not claim a
live AI result. The full report/assignment/evidence lifecycle uses PostgreSQL.
"""
import io
import json
import uuid
from pathlib import Path

import httpx
import pytest
from PIL import Image
from sqlalchemy import create_engine, select, text


def photo():
    stream = io.BytesIO()
    Image.new('RGB', (48, 32), '#55755c').save(stream, 'PNG')
    return stream.getvalue()


def upload(client, headers, incident_id=None):
    data = {'kind': 'completion', 'incident_id': str(incident_id)} if incident_id else {}
    response = client.post('/api/uploads', headers=headers, data=data, files={'file': ('test-evidence.png', photo(), 'image/png')})
    assert response.status_code == 201, response.text
    return response.json()


def worker(client, roles):
    return client.get('/api/auth/me', headers=roles['worker']).json()


def create_assignment(client, roles, incident_id, **options):
    response = client.post(f'/api/incidents/{incident_id}/assignments', headers=roles['authority'], json={'worker_id': worker(client, roles)['id'], 'notes': 'Inspect and repair at this location.', **options})
    assert response.status_code == 201, response.text
    return response.json()


def test_photo_only_report_and_optional_description_are_persisted(client, roles):
    attachment = upload(client, roles['citizen'])
    response = client.post('/api/reports', headers=roles['citizen'], json={'latitude': 31.51, 'longitude': 74.35, 'attachment_ids': [attachment['id']]})
    assert response.status_code == 201, response.text
    report = response.json()
    assert report['title'] == 'Reported civic issue'
    assert report['description'] == ''
    assert report['status'] == 'Pending Review'
    assert report['attachments'][0]['id'] == attachment['id']
    assert report['analysis']['image_analyzed'] is False
    detail = client.get(f'/api/incidents/{report["id"]}', headers=roles['authority']).json()
    assert detail['description'] == '' and detail['attachments']
    from app.db import SessionLocal
    from app.models import Report
    with SessionLocal() as db:
        original = db.scalar(select(Report).where(Report.incident_id == report['id']))
        assert original.original_description == ''


def test_report_needs_photo_or_meaningful_written_evidence(client, roles):
    point = {'latitude': 31.51, 'longitude': 74.35}
    assert client.post('/api/reports', headers=roles['citizen'], json=point).status_code == 422
    assert client.post('/api/reports', headers=roles['citizen'], json={**point, 'description': '  '}).status_code == 422
    response = client.post('/api/reports', headers=roles['citizen'], json={**point, 'description': 'A blocked drain is causing standing water beside the pavement.'})
    assert response.status_code == 201
    assert response.json()['category'] == 'Blocked drainage'
    assert client.patch(f'/api/reports/{response.json()["id"]}', headers=roles['citizen'], json={'title': '', 'description': ''}).status_code == 422


def test_draft_analysis_owner_binding_and_truthful_failure(client, roles, monkeypatch):
    from app import vision
    attachment = upload(client, roles['citizen'])
    controlled = {'status': 'unavailable', 'image_analyzed': False, 'method': 'unavailable', 'summary': 'No configured provider can analyze this photograph. Submit for human review.', 'can_submit': True, 'human_review_required': True}
    monkeypatch.setattr(vision, 'analyze_image_file', lambda *args, **kwargs: controlled)
    url = f'/api/uploads/{attachment["id"]}/analyze'
    response = client.post(url, headers=roles['citizen'], json={})
    assert response.status_code == 200, response.text
    assert response.json()['detection_succeeded'] is False
    assert response.json()['analysis'] == controlled
    assert client.post(url, headers=roles['authority'], json={}).status_code == 403
    account = client.post('/api/auth/register', json={'name': 'Another photo reporter', 'email': f'{uuid.uuid4().hex}@photo.example', 'password': 'PhotoOwnership!2026'}).json()
    stranger = {'Authorization': 'Bearer ' + account['access_token']}
    assert client.post(url, headers=stranger, json={}).status_code == 403
    assert client.get(attachment['url'], headers=stranger).status_code == 403
    from app.db import SessionLocal
    from app.models import Attachment
    with SessionLocal() as db:
        assert db.get(Attachment, attachment['id']).analysis == controlled
    report = client.post('/api/reports', headers=roles['citizen'], json={'latitude': 31.51, 'longitude': 74.35, 'attachment_ids': [attachment['id']]}).json()
    assert report['status'] == 'Pending Review'
    assert client.post(url, headers=roles['citizen'], json={}).status_code == 403


def test_preview_exception_preserves_photo_and_allows_human_review(client, roles, monkeypatch):
    from app import vision
    attachment = upload(client, roles['citizen'])
    def unavailable(*args, **kwargs):
        raise RuntimeError('Controlled upstream failure')
    monkeypatch.setattr(vision, 'analyze_image_file', unavailable)
    response = client.post(f'/api/uploads/{attachment["id"]}/analyze', headers=roles['citizen'])
    assert response.status_code == 200
    assert response.json()['detection_succeeded'] is False
    assert response.json()['analysis']['can_submit'] is True
    assert client.get(attachment['url'], headers=roles['citizen']).status_code == 200


def test_validated_preview_is_reused_once_and_explicit_reanalysis_refreshes(client, roles, monkeypatch):
    from app import vision
    config = vision.ProviderConfig('openai', 'test-vision-model', 'https://vision.example/responses', 'test-only-key')
    monkeypatch.setattr(vision, 'configurations', lambda: [config])
    calls = []
    def provider(url, **kwargs):
        calls.append(kwargs['json'])
        result = {'category': 'Potholes', 'severity': 'Medium', 'recommended_department': 'Roads & Infrastructure', 'summary': 'A visible depression in the road needs inspection.', 'evidence': ['Visible depression in the road surface.'], 'uncertainty': ['Depth cannot be confirmed from a single photograph.'], 'confidence': None, 'image_analyzed': True, 'method': 'vision_model', 'human_review_required': True, 'relevance': 'relevant', 'detected_title': 'Pothole in road surface'}
        return httpx.Response(200, json={'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': json.dumps(result)}]}]})
    monkeypatch.setattr(vision.httpx, 'post', provider)
    attachment = upload(client, roles['citizen'])
    preview = client.post(f'/api/uploads/{attachment["id"]}/analyze', headers=roles['citizen'], json={})
    assert preview.status_code == 200, preview.text
    assert preview.json()['detection_succeeded'] is True
    assert len(calls) == 1
    assert calls[0]['input'][0]['content'][1]['image_url'].startswith('data:image/jpeg;base64,')
    report_response = client.post('/api/reports', headers=roles['citizen'], json={'latitude': 31.51, 'longitude': 74.35, 'attachment_ids': [attachment['id']]})
    assert report_response.status_code == 201, report_response.text
    report = report_response.json()
    assert report['analysis']['image_analyzed'] is True and report['analysis']['reused_draft_analysis'] is True
    assert report['title'] == 'Pothole in road surface' and report['description'] == ''
    assert len(calls) == 1, 'Submitting the reviewed photo must not issue a second paid request.'
    reanalysis = client.post(f'/api/incidents/{report["id"]}/analyze', headers=roles['authority'])
    assert reanalysis.status_code == 200
    assert reanalysis.json()['analysis']['reused_draft_analysis'] is False
    assert len(calls) == 2


@pytest.mark.parametrize('relevance', ['irrelevant', 'uncertain'])
def test_completed_vision_without_relevant_issue_never_claims_detection(client, roles, monkeypatch, relevance):
    from app import vision
    monkeypatch.setattr(vision, 'configurations', lambda: [vision.ProviderConfig('openai', 'test-vision-model', 'https://vision.example/responses', 'test-only-key')])
    result = {'category': 'Potholes', 'severity': 'High', 'recommended_department': 'Roads & Infrastructure', 'summary': 'No clear civic hazard can be confirmed from this photograph.', 'evidence': ['The photograph does not show clear civic infrastructure damage.'], 'uncertainty': ['Please provide a clearer photograph of the issue.'], 'image_analyzed': True, 'method': 'vision_model', 'human_review_required': True, 'relevance': relevance}
    monkeypatch.setattr(vision.httpx, 'post', lambda *args, **kwargs: httpx.Response(200, json={'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': json.dumps(result)}]}]}))
    attachment = upload(client, roles['citizen'])
    response = client.post(f'/api/uploads/{attachment["id"]}/analyze', headers=roles['citizen'], json={})
    assert response.status_code == 200
    assert response.json()['detection_succeeded'] is False
    assert response.json()['analysis']['image_analyzed'] is True
    assert response.json()['analysis']['category'] == 'Other civic infrastructure hazards'
    assert response.json()['analysis']['status'] == relevance


def test_citizen_can_review_category_without_faking_ai(client, roles):
    attachment = upload(client, roles['citizen'])
    response = client.post('/api/reports', headers=roles['citizen'], json={'latitude': 31.51, 'longitude': 74.35, 'attachment_ids': [attachment['id']], 'category': 'Potholes'})
    assert response.status_code == 201
    data = response.json()
    assert data['category'] == 'Potholes'
    assert data['department_name'] == 'Roads & Infrastructure'
    assert data['analysis']['citizen_reviewed_category'] == 'Potholes'
    assert data['analysis']['image_analyzed'] is False
    assert any(event['action'] == 'Citizen reviewed suggested category' for event in data['history'])
    edited = client.patch(f'/api/reports/{data["id"]}', headers=roles['citizen'], json={'category': 'Blocked drainage', 'description': ''})
    assert edited.status_code == 200, edited.text
    assert edited.json()['category'] == 'Blocked drainage'
    assert edited.json()['department_name'] == 'Water & Sanitation'
    assert edited.json()['analysis']['citizen_reviewed_category'] == 'Blocked drainage'
    assert client.post('/api/reports', headers=roles['citizen'], json={'latitude': 31.51, 'longitude': 74.35, 'description': 'Enough report context is provided.', 'category': 'made up'}).status_code == 422


def test_location_only_sharing_redacts_all_worker_read_paths(client, roles, report):
    secret = 'PRIVATEREPORT' + uuid.uuid4().hex
    assert client.patch(f'/api/reports/{report["id"]}', headers=roles['citizen'], json={'title': secret, 'description': secret + ' describes the citizen details.'}).status_code == 200
    citizen_photo = upload(client, roles['citizen'])
    assert client.patch(f'/api/reports/{report["id"]}', headers=roles['citizen'], json={'attachment_ids': [citizen_photo['id']]}).status_code == 200
    assert client.post(f'/api/incidents/{report["id"]}/notes', headers=roles['citizen'], json={'body': secret + ' private citizen note'}).status_code == 201
    # A historic full-report assignment must not expose old notes after a more
    # restrictive reassignment to the same worker.
    old = create_assignment(client, roles, report['id'], notes=secret + ' old instructions')
    assignment = create_assignment(client, roles, report['id'], sharing_scope='location_only')
    url = f'/api/incidents/{report["id"]}'
    detail = client.get(url, headers=roles['worker']).json()
    assert detail['sharing_scope'] == 'location_only'
    assert detail['title'] == 'Location-only task'
    assert detail['description'] == '' and detail['analysis'] == {} and detail['citizen_id'] is None
    assert detail['latitude'] == report['latitude'] and detail['longitude'] == report['longitude']
    assert detail['notes'] == [] and detail['history'] == [] and detail['recommendations'] == [] and detail['duplicates'] == []
    assert detail['attachments'] == []
    assert [row['id'] for row in detail['assignments']] == [assignment['id']]
    assert secret not in json.dumps(detail)
    for endpoint in ['/api/incidents', '/api/dashboard', '/api/assignments', '/api/notifications']:
        response = client.get(endpoint, headers=roles['worker'])
        assert response.status_code == 200
        assert secret not in response.text
    assert client.get('/api/incidents', headers=roles['worker'], params={'search': secret}).json() == []
    assert client.get(citizen_photo['url'], headers=roles['worker']).status_code == 403
    assert client.get('/api/agents', headers=roles['worker']).status_code == 403
    assert client.get('/api/recommendations', headers=roles['worker']).status_code == 403
    assert client.get('/api/audit', headers=roles['worker']).status_code == 403
    assert client.patch(f'/api/assignments/{assignment["id"]}', headers=roles['worker'], json={'sharing_scope': 'full_report'}).status_code == 403
    assert client.get(url, headers=roles['authority']).json()['description'].startswith(secret)
    assert client.get(citizen_photo['url'], headers=roles['authority']).status_code == 200
    assert client.patch(f'/api/assignments/{old["id"]}', headers=roles['worker'], json={'status': 'In Progress'}).status_code == 409


def test_full_report_sharing_preserves_photo_and_description(client, roles, report):
    attachment = upload(client, roles['citizen'])
    assert client.patch(f'/api/reports/{report["id"]}', headers=roles['citizen'], json={'attachment_ids': [attachment['id']]}).status_code == 200
    create_assignment(client, roles, report['id'])
    detail = client.get(f'/api/incidents/{report["id"]}', headers=roles['worker']).json()
    assert detail['sharing_scope'] == 'full_report'
    assert detail['description'] == report['description'] and detail['analysis']
    assert any(a['id'] == attachment['id'] for a in detail['attachments'])
    assert client.get(attachment['url'], headers=roles['worker']).status_code == 200


def test_direct_worker_assignment_excludes_other_team_members(client, roles, report):
    original = worker(client, roles)
    created = client.post('/api/users', headers=roles['admin'], json={'name': 'Directly selected worker', 'email': f'{uuid.uuid4().hex}@worker.example', 'password': 'DirectWorker!2026', 'role': 'worker', 'team_id': original['team_id']}).json()
    login = client.post('/api/auth/login', json={'email': created['email'], 'password': 'DirectWorker!2026'}).json()
    headers = {'Authorization': 'Bearer ' + login['access_token']}
    assignment = create_assignment(client, roles, report['id'], worker_id=created['id'])
    assert assignment['worker_id'] == created['id'] and assignment['worker_name'] == created['name']
    assert assignment['team_id'] == original['team_id']
    assert client.get(f'/api/incidents/{report["id"]}', headers=headers).status_code == 200
    assert client.get(f'/api/incidents/{report["id"]}', headers=roles['worker']).status_code == 403
    assert not any(row['id'] == report['id'] for row in client.get('/api/incidents', headers=roles['worker']).json())
    assert not any(row['id'] == assignment['id'] for row in client.get('/api/assignments', headers=roles['worker']).json())
    assert client.get('/api/workers', headers=roles['citizen']).status_code == 403
    assert client.get('/api/workers', headers=roles['worker']).status_code == 403
    assert any(row['id'] == created['id'] for row in client.get('/api/workers', headers=roles['authority']).json())
    assert client.post(f'/api/incidents/{report["id"]}/assignments', headers=roles['authority'], json={'worker_id': created['id'], 'team_id': original['team_id'] + 99999}).status_code == 422


def test_photo_only_direct_completion_optional_notes_and_authority_corrections(client, roles):
    attachment = upload(client, roles['citizen'])
    report = client.post('/api/reports', headers=roles['citizen'], json={'latitude': 31.51, 'longitude': 74.35, 'attachment_ids': [attachment['id']]}).json()
    assignment = create_assignment(client, roles, report['id'], sharing_scope='location_only')
    endpoint = f'/api/assignments/{assignment["id"]}'
    assert client.patch(endpoint, headers=roles['worker'], json={'status': 'Submitted', 'notes': ''}).status_code == 422
    evidence = upload(client, roles['worker'], report['id'])
    assert client.patch(endpoint, headers=roles['worker'], json={'status': 'Submitted', 'notes': ''}).status_code == 200
    assert client.get(f'/api/incidents/{report["id"]}', headers=roles['citizen']).json()['status'] == 'Resolved'
    assert any(row['incident_id'] == report['id'] and row['title'] == 'Completion ready for review' for row in client.get('/api/notifications', headers=roles['authority']).json())
    details = client.get(f'/api/incidents/{report["id"]}', headers=roles['worker']).json()
    assert [a['id'] for a in details['attachments']] == [evidence['id']]
    correction = client.post(f'/api/incidents/{report["id"]}/status', headers=roles['authority'], json={'status': 'In Progress', 'reason': 'Please clear remaining material and upload fresh evidence.'})
    assert correction.status_code == 200
    assert client.patch(endpoint, headers=roles['worker'], json={'status': 'Submitted', 'notes': ''}).status_code == 422
    upload(client, roles['worker'], report['id'])
    assert client.patch(endpoint, headers=roles['worker'], json={'status': 'Submitted', 'notes': ''}).status_code == 200
    closed = client.post(f'/api/incidents/{report["id"]}/status', headers=roles['authority'], json={'status': 'Closed', 'reason': 'Verified the new completion photograph.'})
    assert closed.status_code == 200 and closed.json()['status'] == 'Closed'
    assert client.get(f'/api/incidents/{report["id"]}', headers=roles['citizen']).json()['status'] == 'Closed'


def test_additive_migration_preserves_old_rows_and_is_idempotent(client):
    from app.db import engine
    from app.migrations import apply_migrations, MIGRATION_SQL
    sql_path = Path(__file__).resolve().parents[2] / 'database' / '003_photo_first_workflow.sql'
    standalone = '\n'.join(line for line in sql_path.read_text(encoding='utf-8').splitlines() if not line.startswith('--')).strip()
    assert standalone == MIGRATION_SQL.strip()
    namespace = 'workflow_upgrade_' + uuid.uuid4().hex
    migration_engine = create_engine(engine.url, connect_args={'options': f'-csearch_path={namespace}'})
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
        with migration_engine.begin() as connection:
            # Minimal previous-version schema is intentional; the upgrade must
            # work on persisted old records without running a fresh-data seed.
            connection.exec_driver_sql('CREATE TABLE users (id INTEGER PRIMARY KEY); CREATE TABLE attachments (id INTEGER PRIMARY KEY, filename TEXT); CREATE TABLE assignments (id INTEGER PRIMARY KEY, notes TEXT); INSERT INTO users VALUES (17); INSERT INTO attachments VALUES (31, \'original-photo.jpg\'); INSERT INTO assignments VALUES (43, \'Keep these work instructions\');')
        apply_migrations(migration_engine)
        apply_migrations(migration_engine)
        with migration_engine.connect() as connection:
            attachment = connection.execute(text('SELECT id, filename, analysis FROM attachments')).mappings().one()
            assignment = connection.execute(text('SELECT id, notes, sharing_scope, worker_id FROM assignments')).mappings().one()
            assert dict(attachment) == {'id': 31, 'filename': 'original-photo.jpg', 'analysis': {}}
            assert dict(assignment) == {'id': 43, 'notes': 'Keep these work instructions', 'sharing_scope': 'full_report', 'worker_id': None}
    finally:
        migration_engine.dispose()
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{namespace}" CASCADE'))
