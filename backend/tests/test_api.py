import io
from datetime import datetime, timezone
from PIL import Image


def image_bytes():
    buffer = io.BytesIO()
    Image.new('RGB', (40, 30), '#304c44').save(buffer, 'PNG')
    return buffer.getvalue()


def test_health_and_authentication(client, roles):
    health = client.get('/api/health')
    assert health.status_code == 200
    assert health.json()['database'] == 'connected'
    assert client.get('/api/incidents').status_code == 401
    assert client.get('/api/incidents', headers={'Authorization': 'Bearer tampered'}).status_code == 401
    assert client.post('/api/auth/login', json={'email': 'citizen@civicshield.demo', 'password': 'wrong'}).status_code == 401
    for role in roles:
        assert client.get('/api/auth/me', headers=roles[role]).json()['role'] == role


def test_register_only_citizen_and_own_scope(client, roles, report):
    response = client.post('/api/auth/register', json={'name': 'Second Citizen', 'email': 'scope@test.example', 'password': 'StrongPassword!12'})
    assert response.status_code == 201
    headers = {'Authorization': 'Bearer ' + response.json()['access_token']}
    assert response.json()['user']['role'] == 'citizen'
    assert client.get('/api/incidents', headers=headers).json() == []
    assert client.get(f'/api/incidents/{report["id"]}', headers=headers).status_code == 403
    assert client.post('/api/auth/register', json={'name': 'Attempt', 'email': 'admin2@test.example', 'password': 'StrongPassword!12', 'role': 'admin'}).status_code == 422
    assert client.post('/api/auth/register', json={'name': 'Again', 'email': 'scope@test.example', 'password': 'StrongPassword!12'}).status_code == 409


def test_report_validation_and_persistence(client, roles, report):
    assert report['reference'].startswith('CS-')
    assert report['status'] == 'Pending Review'
    assert report['category'] == 'Blocked drainage'
    assert report['department_id'] is not None
    assert report['analysis']['mode'] == 'deterministic_text_fallback'
    assert report['analysis']['image_analyzed'] is False
    result = client.get(f'/api/incidents/{report["id"]}', headers=roles['citizen'])
    assert result.status_code == 200
    assert result.json()['description'] == report['description']
    invalid = client.post('/api/reports', headers=roles['citizen'], json={'title': 'A', 'description': 'No', 'latitude': 100, 'longitude': 500})
    assert invalid.status_code == 422
    assert isinstance(invalid.json()['detail'], str)
    assert client.post('/api/reports', headers=roles['worker'], json={'title': 'Not authorized', 'description': 'This report should not be created.', 'latitude': 31, 'longitude': 74}).status_code == 403


def test_edit_withdraw_restore_and_filters(client, roles, report):
    incident_id = report['id']
    edited = client.patch(f'/api/reports/{incident_id}', headers=roles['citizen'], json={'title': 'Updated blocked drain title', 'location_name': 'Integration test crossing'})
    assert edited.status_code == 200
    assert client.get(f'/api/incidents/{incident_id}', headers=roles['authority']).json()['title'] == 'Updated blocked drain title'
    results = client.get('/api/incidents', headers=roles['authority'], params={'search': 'Updated blocked drain title', 'category': 'Blocked drainage', 'status': 'Pending Review'}).json()
    assert any(i['id'] == incident_id for i in results)
    assert client.post(f'/api/reports/{incident_id}/withdraw', headers=roles['citizen'], json={}).json()['status'] == 'Withdrawn'
    assert client.post(f'/api/reports/{incident_id}/withdraw', headers=roles['citizen'], json={}).status_code == 409
    restored = client.post(f'/api/reports/{incident_id}/withdraw', headers=roles['citizen'], json={'restore': True})
    assert restored.status_code == 200
    assert restored.json()['status'] == 'Pending Review'


def test_upload_file_permissions_binding_removal(client, roles, report):
    upload = client.post('/api/uploads', headers=roles['citizen'], files={'file': ('road.png', image_bytes(), 'image/png')})
    assert upload.status_code == 201
    attachment = upload.json()
    assert client.get(attachment['url']).status_code == 401
    assert client.get(attachment['url'], headers=roles['citizen']).headers['content-type'] == 'image/jpeg'
    bad = client.post('/api/uploads', headers=roles['citizen'], files={'file': ('fake.png', b'<script>malicious</script>', 'image/png')})
    assert bad.status_code == 422
    invalid_kind = client.post('/api/uploads', headers=roles['citizen'], data={'kind': 'completion'}, files={'file': ('road.png', image_bytes(), 'image/png')})
    assert invalid_kind.status_code == 422
    response = client.post('/api/reports', headers=roles['citizen'], json={'title': 'Photograph binding test', 'description': 'Broken road pavement has a large pothole near the bus stop.', 'latitude': 31.51, 'longitude': 74.35, 'attachment_ids': [attachment['id']]})
    assert response.status_code == 201
    assert response.json()['attachments'][0]['id'] == attachment['id']
    assert client.delete(f'/api/uploads/{attachment["id"]}', headers=roles['worker']).status_code == 403
    assert client.delete(f'/api/uploads/{attachment["id"]}', headers=roles['citizen']).status_code == 200
    assert client.get(attachment['url'], headers=roles['citizen']).status_code == 404


def test_report_edit_links_photograph_and_date_filter_includes_day(client, roles, report):
    upload = client.post('/api/uploads', headers=roles['citizen'], files={'file': ('replacement.png', image_bytes(), 'image/png')}).json()
    edited = client.patch(f'/api/reports/{report["id"]}', headers=roles['citizen'], json={'title': 'Updated photograph report', 'attachment_ids': [upload['id']]})
    assert edited.status_code == 200, edited.text
    assert any(a['id'] == upload['id'] for a in edited.json()['attachments'])
    assert client.patch(f'/api/reports/{report["id"]}', headers=roles['citizen'], json={'attachment_ids': [upload['id']]}).status_code == 200
    assert len(client.get(f'/api/incidents/{report["id"]}', headers=roles['citizen']).json()['attachments']) == 1
    assert client.patch(f'/api/reports/{report["id"]}', headers=roles['citizen'], json={'attachment_ids': [99999999]}).status_code == 400
    today = datetime.now(timezone.utc).date().isoformat()
    results = client.get('/api/incidents', headers=roles['authority'], params={'from_date': today, 'to_date': today})
    assert results.status_code == 200
    assert any(i['id'] == report['id'] for i in results.json())


def test_date_filter_utc_bounds_survive_non_utc_database_session(client, roles):
    from uuid import uuid4
    from sqlalchemy import select, text
    from app.db import SessionLocal, get_db
    from app.main import app
    from app.models import Incident, User
    prefix = f'DATE-BOUNDARY-{uuid4().hex[:8]}'
    timestamps = {
        'previous_day': '2026-01-14T23:59:59+00:00',
        'start_of_day': '2026-01-15T00:00:00+00:00',
        'local_next_day': '2026-01-15T20:30:00+00:00',
        'next_day': '2026-01-16T00:00:00+00:00',
    }
    with SessionLocal() as db:
        citizen = db.scalar(select(User).where(User.email == 'citizen@civicshield.demo'))
        records = {}
        for name, timestamp in timestamps.items():
            incident = Incident(reference=f'{prefix}-{name}', title=f'{prefix} {name}', description='Synthetic fixed-timestamp boundary fixture.', citizen_id=citizen.id, latitude=31.51, longitude=74.35, status='Pending Review', created_at=datetime.fromisoformat(timestamp))
            db.add(incident)
            db.flush()
            records[name] = incident.id
        db.commit()

    def karachi_session():
        with SessionLocal() as db:
            # Deliberately force the timezone that exposed the production bug,
            # independent of the test host's configured PostgreSQL timezone.
            db.execute(text("SET LOCAL TIME ZONE 'Asia/Karachi'"))
            yield db

    original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = karachi_session
    try:
        def filtered_ids(from_date, to_date):
            response = client.get('/api/incidents', headers=roles['authority'], params={'search': prefix, 'from_date': from_date, 'to_date': to_date})
            assert response.status_code == 200, response.text
            return {incident['id'] for incident in response.json()}
        assert filtered_ids('2026-01-15', '2026-01-15') == {records['start_of_day'], records['local_next_day']}
        assert filtered_ids('2026-01-15T20:00:00Z', '2026-01-15T21:00:00Z') == {records['local_next_day']}
        assert filtered_ids('2026-01-16T00:00:00+05:00', '2026-01-16T02:00:00+05:00') == {records['local_next_day']}
    finally:
        if original_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = original_override


def test_incident_override_reason_and_permissions(client, roles, report):
    url = f'/api/incidents/{report["id"]}'
    assert client.patch(url, headers=roles['citizen'], json={'severity': 'Critical', 'reason': 'Test override'}).status_code == 403
    assert client.patch(url, headers=roles['authority'], json={'severity': 'Critical'}).status_code == 422
    response = client.patch(url, headers=roles['authority'], json={'severity': 'Critical', 'category': 'Open manholes', 'reason': 'Deep open hole beside school crossing.'})
    assert response.status_code == 200
    assert client.get(url, headers=roles['authority']).json()['severity'] == 'Critical'
    assert any('Deep open' in event['detail'] for event in response.json()['history'])
    assert client.patch(url, headers=roles['authority'], json={'category': 'Unknown unsupported'}).status_code == 422


def test_full_assignment_worker_evidence_verify_reopen(client, roles, report):
    incident_id = report['id']
    assert client.get(f'/api/incidents/{incident_id}', headers=roles['worker']).status_code == 403
    team = client.get('/api/auth/me', headers=roles['worker']).json()['team_id']
    assignment_response = client.post(f'/api/incidents/{incident_id}/assignments', headers=roles['authority'], json={'team_id': team, 'notes': 'Inspect blocked inlet.'})
    assert assignment_response.status_code == 201
    assignment_id = assignment_response.json()['id']
    assert client.get(f'/api/incidents/{incident_id}', headers=roles['worker']).status_code == 200
    assert client.patch(f'/api/reports/{incident_id}', headers=roles['citizen'], json={'title': 'Cannot change assigned report'}).status_code == 409
    assert client.post(f'/api/incidents/{incident_id}/status', headers=roles['authority'], json={'status': 'Closed'}).status_code == 409
    for status in ['Acknowledged', 'In Progress']:
        assert client.patch(f'/api/assignments/{assignment_id}', headers=roles['worker'], json={'status': status}).status_code == 200
    assert client.patch(f'/api/assignments/{assignment_id}', headers=roles['worker'], json={'status': 'Submitted', 'notes': 'Drain cleared; water flow restored.'}).status_code == 422
    evidence = client.post('/api/uploads', headers=roles['worker'], data={'incident_id': str(incident_id), 'kind': 'completion'}, files={'file': ('complete.png', image_bytes(), 'image/png')})
    assert evidence.status_code == 201
    completed = client.patch(f'/api/assignments/{assignment_id}', headers=roles['worker'], json={'status': 'Submitted', 'notes': 'Drain cleared; water flow restored and area inspected.'})
    assert completed.status_code == 200
    assert client.get(f'/api/incidents/{incident_id}', headers=roles['citizen']).json()['status'] == 'Resolved'
    closed = client.post(f'/api/incidents/{incident_id}/status', headers=roles['authority'], json={'status': 'Closed', 'reason': 'Reviewed completion evidence and verified drainage.'})
    assert closed.status_code == 200
    assert client.get(f'/api/incidents/{incident_id}', headers=roles['citizen']).json()['status'] == 'Closed'
    assert client.delete(f'/api/uploads/{evidence.json()["id"]}', headers=roles['worker']).status_code == 409
    assert client.post(f'/api/incidents/{incident_id}/archive', headers=roles['authority'], json={'archived': True}).status_code == 200
    assert all(i['id'] != incident_id for i in client.get('/api/incidents', headers=roles['citizen']).json())
    assert any(i['id'] == incident_id for i in client.get('/api/incidents?include_archived=true', headers=roles['citizen']).json())
    reopened = client.post(f'/api/incidents/{incident_id}/status', headers=roles['authority'], json={'status': 'Reopened', 'reason': 'Water is accumulating again; a further inspection is needed.'})
    assert reopened.status_code == 200
    assert reopened.json()['archived'] is False


def test_reassignment_cancel_and_corrections(client, roles, report):
    teams = client.get('/api/teams', headers=roles['authority']).json()
    url = f'/api/incidents/{report["id"]}/assignments'
    initial = client.post(url, headers=roles['authority'], json={'team_id': teams[0]['id']}).json()
    replacement = client.patch(f'/api/assignments/{initial["id"]}', headers=roles['authority'], json={'team_id': teams[1]['id'], 'notes': 'Roads team requested.'})
    assert replacement.status_code == 200
    replacement_id = replacement.json()['id']
    assert replacement_id != initial['id']
    detail = client.get(f'/api/incidents/{report["id"]}', headers=roles['authority']).json()
    assert detail['team_id'] == teams[1]['id']
    assert detail['department_id'] == teams[1]['department_id']
    assert client.patch(f'/api/assignments/{initial["id"]}', headers=roles['worker'], json={'status': 'In Progress'}).status_code == 403
    cancelled = client.patch(f'/api/assignments/{replacement_id}', headers=roles['authority'], json={'status': 'Cancelled'})
    assert cancelled.status_code == 200
    assert client.get(f'/api/incidents/{report["id"]}', headers=roles['authority']).json()['status'] == 'Pending Review'
    assert client.patch(f'/api/assignments/{initial["id"]}', headers=roles['authority'], json={'status': 'In Progress'}).status_code == 409


def test_completion_corrections_require_fresh_evidence(client, roles, report):
    team_id = client.get('/api/auth/me', headers=roles['worker']).json()['team_id']
    assignment = client.post(f'/api/incidents/{report["id"]}/assignments', headers=roles['authority'], json={'team_id': team_id}).json()
    url = f'/api/assignments/{assignment["id"]}'
    assert client.patch(url, headers=roles['worker'], json={'status': 'In Progress'}).status_code == 200
    def upload():
        return client.post('/api/uploads', headers=roles['worker'], data={'incident_id': str(report['id']), 'kind': 'completion'}, files={'file': ('complete.png', image_bytes(), 'image/png')})
    assert upload().status_code == 201
    assert client.patch(url, headers=roles['worker'], json={'status': 'Submitted', 'notes': 'Drain cleared and water flow checked.'}).status_code == 200
    corrections = client.post(f'/api/incidents/{report["id"]}/status', headers=roles['authority'], json={'status': 'In Progress', 'reason': 'Please remove the remaining debris and supply another photograph.'})
    assert corrections.status_code == 200
    assert client.patch(url, headers=roles['worker'], json={'status': 'Submitted', 'notes': 'All remaining debris has been removed.'}).status_code == 422
    assert upload().status_code == 201
    assert client.patch(url, headers=roles['worker'], json={'status': 'Submitted', 'notes': 'All remaining debris has been removed and photographed.'}).status_code == 200


def test_duplicate_detection_merge_reject_separate_cycle(client, roles, report):
    second = client.post('/api/reports', headers=roles['citizen'], json={'title': report['title'], 'description': report['description'], 'latitude': report['latitude'] + .00001, 'longitude': report['longitude'], 'location_name': report['location_name']}).json()
    candidate = next((d for d in second['duplicates'] if d['target_id'] == report['id']), None)
    assert candidate and candidate['distance_m'] < 10 and candidate['similarity'] > .5
    url = f'/api/incidents/{second["id"]}/duplicate'
    assert client.post(url, headers=roles['authority'], json={'target_id': second['id'], 'action': 'merge'}).status_code == 422
    rejected = client.post(url, headers=roles['authority'], json={'target_id': report['id'], 'action': 'reject'})
    assert rejected.status_code == 200
    merged = client.post(url, headers=roles['authority'], json={'target_id': report['id'], 'action': 'merge'})
    assert merged.json()['duplicate_of'] == report['id']
    assert client.post(f'/api/incidents/{report["id"]}/duplicate', headers=roles['authority'], json={'target_id': second['id'], 'action': 'merge'}).status_code == 409
    assert client.get(f'/api/incidents/{report["id"]}', headers=roles['citizen']).status_code == 200
    separated = client.post(url, headers=roles['authority'], json={'target_id': report['id'], 'action': 'separate'})
    assert separated.json()['duplicate_of'] is None


def test_notes_crud_notifications_permissions(client, roles, report):
    note_response = client.post(f'/api/incidents/{report["id"]}/notes', headers=roles['authority'], json={'body': 'Please upload a wider view of the blocked inlet.'})
    assert note_response.status_code == 201
    note_id = note_response.json()['id']
    assert client.patch(f'/api/notes/{note_id}', headers=roles['citizen'], json={'body': 'Cannot edit authority note'}).status_code == 403
    assert client.patch(f'/api/notes/{note_id}', headers=roles['authority'], json={'body': 'Evidence request updated; please include nearby road.'}).status_code == 200
    assert client.delete(f'/api/notes/{note_id}', headers=roles['authority']).status_code == 200
    assert all(n['id'] != note_id for n in client.get(f'/api/incidents/{report["id"]}', headers=roles['citizen']).json()['notes'])
    notifications = client.get('/api/notifications', headers=roles['citizen']).json()
    assert notifications
    notification_id = notifications[0]['id']
    assert client.patch(f'/api/notifications/{notification_id}', headers=roles['authority'], json={'read': True}).status_code == 403
    assert client.patch(f'/api/notifications/{notification_id}', headers=roles['citizen'], json={'read': True}).json()['read'] is True
    assert client.patch(f'/api/notifications/{notification_id}', headers=roles['citizen'], json={'read': False}).json()['read'] is False


def test_admin_departments_teams_zones_users_complete_lifecycle(client, roles):
    admin = roles['admin']
    assert client.post('/api/departments', headers=roles['authority'], json={'name': 'No permission'}).status_code == 403
    department = client.post('/api/departments', headers=admin, json={'name': 'Test water department', 'description': 'Integration test entity'}).json()
    team = client.post('/api/teams', headers=admin, json={'name': 'Test water team', 'department_id': department['id']}).json()
    zone = client.post('/api/zones', headers=admin, json={'name': 'Test zone', 'latitude': 31.5, 'longitude': 74.3, 'radius_km': 1.2, 'historical_floods': 2}).json()
    user_response = client.post('/api/users', headers=admin, json={'name': 'Test worker', 'email': 'worker-test@test.example', 'role': 'worker', 'team_id': team['id'], 'password': 'StrongPassword!12'})
    assert user_response.status_code == 201
    user = user_response.json()
    assert 'password_hash' not in user
    for endpoint, entity, fields in [('departments', department, {'name': 'Updated water department'}), ('teams', team, {'name': 'Updated water team'}), ('zones', zone, {'radius_km': 1.4}), ('users', user, {'email': 'updated-worker@test.example', 'name': 'Updated worker'})]:
        edited = client.patch(f'/api/{endpoint}/{entity["id"]}', headers=admin, json=fields)
        assert edited.status_code == 200, edited.text
        reread = next(i for i in client.get(f'/api/{endpoint}', headers=admin).json() if i['id'] == entity['id'])
        for key, value in fields.items():
            assert reread[key] == value
        assert client.delete(f'/api/{endpoint}/{entity["id"]}', headers=admin).json()['active'] is False
        assert client.patch(f'/api/{endpoint}/{entity["id"]}', headers=admin, json={'active': True}).json()['active'] is True
    assert client.get('/api/users', headers=roles['authority']).status_code == 403
    assert client.post('/api/teams', headers=admin, json={'name': 'Invalid team', 'department_id': 999999}).status_code == 422
    assert client.post('/api/zones', headers=admin, json={'name': 'Invalid zone', 'latitude': 31, 'longitude': 74, 'radius_km': -1}).status_code == 422
    admin_me = client.get('/api/auth/me', headers=admin).json()
    assert client.delete(f'/api/users/{admin_me["id"]}', headers=admin).status_code == 409
    assert client.patch(f'/api/users/{admin_me["id"]}', headers=admin, json={'role': 'citizen'}).status_code == 409


def test_disabled_accounts_invalidate_existing_tokens(client, roles):
    created = client.post('/api/users', headers=roles['admin'], json={'name': 'Disabled citizen', 'email': 'disabled@test.example', 'password': 'StrongPassword!12'}).json()
    token = client.post('/api/auth/login', json={'email': 'disabled@test.example', 'password': 'StrongPassword!12'}).json()['access_token']
    headers = {'Authorization': 'Bearer ' + token}
    assert client.get('/api/auth/me', headers=headers).status_code == 200
    client.delete(f'/api/users/{created["id"]}', headers=roles['admin'])
    assert client.get('/api/auth/me', headers=headers).status_code == 401
    assert client.post('/api/auth/login', json={'email': 'disabled@test.example', 'password': 'StrongPassword!12'}).status_code == 401
    client.patch(f'/api/users/{created["id"]}', headers=roles['admin'], json={'active': True})
    assert client.post('/api/auth/login', json={'email': 'disabled@test.example', 'password': 'StrongPassword!12'}).status_code == 200


def test_risk_scenarios_history_missing_weather(client, roles):
    authority = roles['authority']
    assert client.post('/api/risk/refresh', headers=roles['citizen'], json={'scenario': 'heavy_rain'}).status_code == 403
    low = client.post('/api/risk/refresh', headers=authority, json={'scenario': 'clear'})
    assert low.status_code == 200, low.text
    scores = {row['zone_id']: row['score'] for row in low.json()}
    high = client.post('/api/risk/refresh', headers=authority, json={'scenario': 'heavy_rain'})
    assert high.status_code == 200
    assert all(row['score'] > scores[row['zone_id']] for row in high.json())
    assert any(row['level'] == 'High' for row in high.json())
    assert all(row['provenance']['weather']['is_demo'] for row in high.json())
    missing = client.post('/api/risk/refresh', headers=authority, json={'scenario': 'missing'})
    assert missing.status_code == 200
    assert all(row['level'] == 'Insufficient Data' and row['score'] is None for row in missing.json())
    first_zone = high.json()[0]['zone_id']
    history = client.get(f'/api/risk/history?zone_id={first_zone}', headers=authority).json()
    assert len(history) >= 3
    assert all(row['zone_id'] == first_zone for row in history)
    assert client.get('/api/weather', headers=authority).json()
    client.post('/api/risk/refresh', headers=authority, json={'scenario': 'heavy_rain'})


def test_agent_orchestration_recommendations_and_audit(client, roles, report):
    executions = client.get('/api/agents', headers=roles['authority']).json()
    names = {r['agent'] for r in executions if r['incident_id'] == report['id']}
    assert {'Civic Intelligence Agent', 'Disaster Risk Agent', 'Response Coordinator Agent'} <= names
    assert all(isinstance(r['input_context'], dict) and isinstance(r['output'], dict) for r in executions)
    recommendations = client.get('/api/recommendations', headers=roles['authority']).json()
    recommendation = next(r for r in recommendations if r['incident_id'] == report['id'])
    url = f'/api/recommendations/{recommendation["id"]}'
    assert client.patch(url, headers=roles['authority'], json={'status': 'Rejected'}).status_code == 422
    for status in ['Approved', 'Rejected', 'Overridden']:
        response = client.patch(url, headers=roles['authority'], json={'status': status, 'reason': 'Reviewed conditions and selected the appropriate action.'})
        assert response.status_code == 200
        assert response.json()['status'] == status
    assert client.get(f'/api/incidents/{report["id"]}', headers=roles['authority']).json()['team_id'] is None
    assert client.post(f'/api/incidents/{report["id"]}/analyze', headers=roles['authority']).status_code == 200
    assert client.get('/api/agents', headers=roles['citizen']).status_code == 403
    audit = client.get('/api/audit', headers=roles['authority']).json()
    assert any('Recommendation' in row['action'] for row in audit)
    dashboard = client.get('/api/dashboard', headers=roles['authority']).json()
    assert dashboard['total'] >= 12
    assert dashboard['total'] == len(client.get('/api/incidents', headers=roles['authority']).json())


def test_failed_analysis_preserved_and_retry_reports_truth(client, roles, report, monkeypatch):
    from app import intelligence
    def fail_pipeline(db, incident):
        raise RuntimeError('Controlled integration test failure')
    with monkeypatch.context() as controlled:
        controlled.setattr(intelligence, 'run_pipeline', fail_pipeline)
        response = client.post(f'/api/incidents/{report["id"]}/analyze', headers=roles['authority'])
        assert response.status_code == 200
        assert response.json()['analysis']['mode'] == 'unavailable'
        assert client.get(f'/api/incidents/{report["id"]}', headers=roles['citizen']).status_code == 200
        execution = next(e for e in client.get('/api/agents', headers=roles['authority']).json() if e['incident_id'] == report['id'] and e['status'] == 'Failed')
        assert client.post(f'/api/agents/{execution["id"]}/retry', headers=roles['citizen']).status_code == 403
        assert client.post(f'/api/agents/{execution["id"]}/retry', headers=roles['authority']).status_code == 502
    retried = client.post(f'/api/agents/{execution["id"]}/retry', headers=roles['authority'])
    assert retried.status_code == 200, retried.text
    assert retried.json()['success'] is True
    assert retried.json()['execution']['status'] == 'Retried'
    assert retried.json()['execution']['attempts'] == 3
    assert client.post(f'/api/agents/{execution["id"]}/retry', headers=roles['authority']).status_code == 409


def test_rejection_archive_unarchive_and_not_found(client, roles, report):
    incident_id = report['id']
    assert client.post(f'/api/incidents/{incident_id}/archive', headers=roles['authority'], json={}).status_code == 409
    assert client.post(f'/api/incidents/{incident_id}/status', headers=roles['authority'], json={'status': 'Rejected', 'reason': 'Duplicate evidence is insufficient to progress this report.'}).status_code == 200
    assert client.post(f'/api/incidents/{incident_id}/archive', headers=roles['authority'], json={'archived': True}).status_code == 200
    assert client.post(f'/api/incidents/{incident_id}/archive', headers=roles['authority'], json={'archived': False}).json()['archived'] is False
    assert client.get('/api/incidents/9999999', headers=roles['admin']).status_code == 404
