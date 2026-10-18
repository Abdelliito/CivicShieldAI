"""Regression tests for permission boundaries and assignment/merge integrity.

Uses the guarded PostgreSQL `_test` database configured by conftest.py.
"""
import io
import uuid

from PIL import Image


def unique(prefix):
    return f'{prefix}-{uuid.uuid4().hex[:10]}'


def picture():
    data = io.BytesIO()
    Image.new('RGB', (24, 24), '#527c65').save(data, 'PNG')
    return data.getvalue()


def upload_completion(client, roles, incident_id):
    return client.post('/api/uploads', headers=roles['worker'], data={'incident_id': str(incident_id), 'kind': 'completion'}, files={'file': ('completion.png', picture(), 'image/png')})


def worker_team(client, roles):
    return client.get('/api/auth/me', headers=roles['worker']).json()['team_id']


def assign(client, roles, report, team_id=None):
    response = client.post(f'/api/incidents/{report["id"]}/assignments', headers=roles['authority'], json={'team_id': team_id or worker_team(client, roles), 'notes': 'Security regression assignment'})
    assert response.status_code == 201, response.text
    return response.json()


def second_citizen(client):
    response = client.post('/api/auth/register', json={'name': 'Scope audit citizen', 'email': unique('scope') + '@audit.example', 'password': 'AuditPassword!2026'})
    assert response.status_code == 201
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


def second_report(client, headers, parent):
    response = client.post('/api/reports', headers=headers, json={'title': 'Blocked drain reported independently', 'description': 'The drain is blocked and water is pooling beside this crossing; please inspect.', 'latitude': parent['latitude'] + 0.00001, 'longitude': parent['longitude'], 'location_name': 'Independent citizen location'})
    assert response.status_code == 201, response.text
    return response.json()


def test_live_work_blocks_team_and_department_deactivation(client, roles, report):
    department = client.post('/api/departments', headers=roles['admin'], json={'name': unique('Audit department')}).json()
    team = client.post('/api/teams', headers=roles['admin'], json={'name': unique('Audit team'), 'department_id': department['id']}).json()
    assignment = assign(client, roles, report, team['id'])
    for resource, entity in [('teams', team), ('departments', department)]:
        url = f'/api/{resource}/{entity["id"]}'
        assert client.patch(url, headers=roles['admin'], json={'active': False}).status_code == 409
        assert client.delete(url, headers=roles['admin']).status_code == 409
    assert client.patch(f'/api/assignments/{assignment["id"]}', headers=roles['authority'], json={'status': 'Cancelled'}).status_code == 200
    assert client.delete(f'/api/teams/{team["id"]}', headers=roles['admin']).status_code == 200
    assert client.delete(f'/api/departments/{department["id"]}', headers=roles['admin']).status_code == 200
    assert client.patch(f'/api/teams/{team["id"]}', headers=roles['admin'], json={'active': True}).status_code == 422


def test_reassignment_preserves_history_and_rejects_historical_mutation(client, roles, report):
    original = assign(client, roles, report)
    replacement = client.patch(f'/api/assignments/{original["id"]}', headers=roles['authority'], json={'team_id': original['team_id'], 'notes': 'New inspection cycle with same team.'})
    assert replacement.status_code == 200
    assert replacement.json()['id'] != original['id']
    assert client.patch(f'/api/assignments/{original["id"]}', headers=roles['authority'], json={'status': 'In Progress'}).status_code == 409
    assert client.patch(f'/api/assignments/{original["id"]}', headers=roles['worker'], json={'status': 'In Progress'}).status_code == 409
    detail = client.get(f'/api/incidents/{report["id"]}', headers=roles['authority']).json()
    assert detail['status'] == 'Assigned'
    assert next(a for a in detail['assignments'] if a['id'] == original['id'])['status'] == 'Cancelled'


def test_new_assignment_requires_fresh_completion_evidence(client, roles, report):
    original = assign(client, roles, report)
    assert client.patch(f'/api/assignments/{original["id"]}', headers=roles['worker'], json={'status': 'In Progress'}).status_code == 200
    old_photo = upload_completion(client, roles, report['id'])
    assert old_photo.status_code == 201
    replacement = client.patch(f'/api/assignments/{original["id"]}', headers=roles['authority'], json={'team_id': original['team_id']}).json()
    url = f'/api/assignments/{replacement["id"]}'
    assert client.patch(url, headers=roles['worker'], json={'status': 'In Progress'}).status_code == 200
    stale = client.patch(url, headers=roles['worker'], json={'status': 'Submitted', 'notes': 'Attempting to reuse the prior inspection photograph.'})
    assert stale.status_code == 422
    assert upload_completion(client, roles, report['id']).status_code == 201
    assert client.patch(url, headers=roles['worker'], json={'status': 'Submitted', 'notes': 'Current inspection complete, drainage restored and checked.'}).status_code == 200


def test_worker_evidence_requires_current_work_in_progress(client, roles, report):
    assert upload_completion(client, roles, report['id']).status_code == 403
    assignment = assign(client, roles, report)
    assert upload_completion(client, roles, report['id']).status_code == 409
    assert client.patch(f'/api/assignments/{assignment["id"]}', headers=roles['worker'], json={'status': 'In Progress'}).status_code == 200
    assert upload_completion(client, roles, report['id']).status_code == 201


def test_consolidated_citizen_sees_safe_parent_status_and_receives_updates(client, roles, report):
    outsider = second_citizen(client)
    child = second_report(client, outsider, report)
    for candidate in child['duplicates']:
        if candidate['related_incident_id'] == report['id']:
            assert candidate['target_title'] == 'Related report — authority review'
    merged = client.post(f'/api/incidents/{child["id"]}/duplicate', headers=roles['authority'], json={'target_id': report['id'], 'action': 'merge'})
    assert merged.status_code == 200
    assignment = assign(client, roles, report)
    detail = client.get(f'/api/incidents/{child["id"]}', headers=outsider).json()
    assert detail['consolidated_incident'] == {'id': report['id'], 'reference': report['reference'], 'status': 'Assigned'}
    assert client.get(f'/api/incidents/{report["id"]}', headers=outsider).status_code == 403
    updates = client.get('/api/notifications', headers=outsider).json()
    assert any(n['incident_id'] == child['id'] and 'Consolidated incident' in n['body'] for n in updates)
    assert client.patch(f'/api/assignments/{assignment["id"]}', headers=roles['worker'], json={'status': 'In Progress'}).status_code == 200
    assert client.get(f'/api/incidents/{child["id"]}', headers=outsider).json()['consolidated_incident']['status'] == 'In Progress'


def test_consolidated_child_cannot_start_independent_workflow(client, roles, report):
    child = second_report(client, roles['citizen'], report)
    assert client.post(f'/api/incidents/{child["id"]}/duplicate', headers=roles['authority'], json={'target_id': report['id'], 'action': 'merge'}).status_code == 200
    base = f'/api/incidents/{child["id"]}'
    assert client.patch(base, headers=roles['authority'], json={'severity': 'Critical', 'reason': 'This must be reviewed on the consolidated parent.'}).status_code == 409
    assert client.patch(f'/api/reports/{child["id"]}', headers=roles['citizen'], json={'title': 'Attempt to change a consolidated report'}).status_code == 409
    assert client.post(base + '/status', headers=roles['authority'], json={'status': 'Rejected', 'reason': 'This would conflict with parent processing.'}).status_code == 409
    assert client.post(base + '/assignments', headers=roles['authority'], json={'team_id': worker_team(client, roles)}).status_code == 409
    assert client.post(base + '/analyze', headers=roles['authority']).status_code == 409


def test_merge_requires_cancellation_of_source_work(client, roles, report):
    child = second_report(client, roles['citizen'], report)
    assignment = assign(client, roles, child)
    url = f'/api/incidents/{child["id"]}/duplicate'
    assert client.post(url, headers=roles['authority'], json={'target_id': report['id'], 'action': 'merge'}).status_code == 409
    assert client.patch(f'/api/assignments/{assignment["id"]}', headers=roles['authority'], json={'status': 'Cancelled'}).status_code == 200
    assert client.post(url, headers=roles['authority'], json={'target_id': report['id'], 'action': 'merge'}).status_code == 200


def test_attachment_ownership_and_other_citizen_notification_scope(client, roles, report):
    outsider = second_citizen(client)
    own_photo = client.post('/api/uploads', headers=roles['citizen'], files={'file': ('own.png', picture(), 'image/png')}).json()
    assert client.get(own_photo['url'], headers=outsider).status_code == 403
    assert client.delete(f'/api/uploads/{own_photo["id"]}', headers=outsider).status_code == 403
    forged = client.post('/api/reports', headers=outsider, json={'title': 'Trying to attach a photograph', 'description': 'The blocked drain must be inspected with an uploaded photograph.', 'latitude': 31.51, 'longitude': 74.35, 'attachment_ids': [own_photo['id']]})
    assert forged.status_code == 400
    notifications = client.get('/api/notifications', headers=roles['citizen']).json()
    assert notifications
    assert client.patch(f'/api/notifications/{notifications[0]["id"]}', headers=outsider, json={'read': True}).status_code == 403


def test_model_recommendation_approval_never_assigns_team(client, roles, report):
    detail = client.get(f'/api/incidents/{report["id"]}', headers=roles['authority']).json()
    recommendation = next(r for r in detail['recommendations'] if r['agent'] == 'Response Coordinator Agent')
    response = client.patch(f'/api/recommendations/{recommendation["id"]}', headers=roles['authority'], json={'status': 'Approved', 'reason': 'Human review completed; assignment remains a separate action.'})
    assert response.status_code == 200
    reread = client.get(f'/api/incidents/{report["id"]}', headers=roles['authority']).json()
    assert reread['team_id'] is None and reread['assignments'] == []
    assert any(row['action'] == 'Recommendation approved' for row in reread['history'])
