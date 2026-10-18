import logging
import math
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Session
from .models import Attachment, Assignment, AuditLog, Department, DuplicateCandidate, Incident, Note, Notification, Recommendation, Team, User, Zone, AgentExecution

logger = logging.getLogger(__name__)
OFFICIAL_ROLES = {'authority', 'admin'}
TERMINAL = {'Closed', 'Rejected', 'Withdrawn'}


def dump(row):
    if row is None:
        return None
    result = {}
    for col in inspect(type(row)).columns:
        if col.key in {'password_hash', 'storage_name'}:
            continue
        value = getattr(row, col.key)
        result[col.key] = value.isoformat() if isinstance(value, datetime) else value
    if isinstance(row, Attachment):
        result['url'] = f'/api/uploads/{row.id}/file'
    return result


def commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'This change conflicts with an existing record or reference.')


def audit(db, user, action, detail='', incident_id=None):
    db.add(AuditLog(user_id=user.id if user else None, action=action, detail=detail, incident_id=incident_id))


def notify(db, incident, title, body=''):
    db.add(Notification(user_id=incident.citizen_id, incident_id=incident.id, title=title, body=body or incident.reference))
    # A consolidated report still belongs to its original citizen. Notify those
    # citizens of parent progress without exposing another citizen's report text.
    pending, visited = [incident.id], {incident.id}
    while pending:
        parent_id = pending.pop()
        for child in db.scalars(select(Incident).where(Incident.duplicate_of == parent_id)):
            if child.id in visited:
                continue
            visited.add(child.id)
            pending.append(child.id)
            db.add(Notification(user_id=child.citizen_id, incident_id=child.id, title=title, body=f'Consolidated incident {incident.reference}: {body or title}'))


def get_incident(db, incident_id, user):
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(404, 'Incident not found.')
    if user.role == 'citizen' and incident.citizen_id != user.id:
        raise HTTPException(403, 'You can only access your own reports.')
    if user.role == 'worker' and (not user.team_id or incident.team_id != user.team_id):
        raise HTTPException(403, 'You can only access incidents assigned to your team.')
    return incident


def visible_incidents(db, user):
    statement = select(Incident)
    if user.role == 'citizen':
        statement = statement.where(Incident.citizen_id == user.id)
    elif user.role == 'worker':
        statement = statement.where(Incident.team_id == (user.team_id or -1))
    return statement


def incident_dump(db, incident, detail=False, viewer=None):
    result = dump(incident)
    department = db.get(Department, incident.department_id) if incident.department_id else None
    team = db.get(Team, incident.team_id) if incident.team_id else None
    zone = db.get(Zone, incident.zone_id) if incident.zone_id else None
    result.update(department_name=department.name if department else None, team_name=team.name if team else None, zone_name=zone.name if zone else None)
    result['consolidated_incident'] = None
    parent, visited = incident, {incident.id}
    while parent.duplicate_of and parent.duplicate_of not in visited:
        visited.add(parent.duplicate_of)
        candidate_parent = db.get(Incident, parent.duplicate_of)
        if not candidate_parent:
            break
        parent = candidate_parent
    if parent.id != incident.id:
        result['consolidated_incident'] = {'id': parent.id, 'reference': parent.reference, 'status': parent.status}
    attachments = db.scalars(select(Attachment).where(Attachment.incident_id == incident.id, Attachment.deleted.is_(False)).order_by(Attachment.id)).all()
    result['attachments'] = [dump(a) for a in attachments]
    if detail:
        result['notes'] = []
        for note in db.scalars(select(Note).where(Note.incident_id == incident.id, Note.deleted.is_(False)).order_by(Note.created_at)):
            item = dump(note)
            author = db.get(User, note.user_id)
            item['author_name'] = author.name if author else 'System'
            result['notes'].append(item)
        result['history'] = []
        for entry in db.scalars(select(AuditLog).where(AuditLog.incident_id == incident.id).order_by(AuditLog.created_at.desc())):
            item = dump(entry)
            actor = db.get(User, entry.user_id) if entry.user_id else None
            item['actor_name'] = actor.name if actor else 'System'
            result['history'].append(item)
        result['assignments'] = []
        for assignment in db.scalars(select(Assignment).where(Assignment.incident_id == incident.id).order_by(Assignment.id.desc())):
            item = dump(assignment)
            team = db.get(Team, assignment.team_id)
            item['team_name'] = team.name if team else None
            result['assignments'].append(item)
        result['duplicates'] = []
        for candidate in db.scalars(select(DuplicateCandidate).where((DuplicateCandidate.incident_id == incident.id) | (DuplicateCandidate.target_id == incident.id)).order_by(DuplicateCandidate.id.desc())):
            item = dump(candidate)
            other_id = candidate.target_id if candidate.incident_id == incident.id else candidate.incident_id
            other = db.get(Incident, other_id)
            item['target_reference'] = other.reference if other else None
            may_view_other = viewer is None or viewer.role in OFFICIAL_ROLES or (other and other.citizen_id == viewer.id)
            item['target_title'] = other.title if other and may_view_other else 'Related report — authority review'
            item['related_incident_id'] = other_id
            result['duplicates'].append(item)
        result['recommendations'] = [dump(r) for r in db.scalars(select(Recommendation).where(Recommendation.incident_id == incident.id).order_by(Recommendation.id.desc()))]
    return result


def haversine_km(lat1, lon1, lat2, lon2):
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0, 1-a)))


def choose_zone(db, latitude, longitude):
    candidates = [(haversine_km(latitude, longitude, z.latitude, z.longitude), z) for z in db.scalars(select(Zone).where(Zone.active.is_(True)))]
    eligible = [(d, z) for d, z in candidates if d <= z.radius_km]
    return min(eligible, key=lambda pair: pair[0])[1].id if eligible else None


def process_incident(db, incident):
    from .intelligence import run_pipeline
    incident_id = incident.id
    try:
        run_pipeline(db, incident)
        commit(db)
    except Exception as exc:
        logger.exception('Incident pipeline failed for %s', incident_id)
        db.rollback()
        incident = db.get(Incident, incident_id)
        if incident.status in {'Submitted', 'Under Analysis'}:
            incident.status = 'Pending Review'
        incident.analysis = {'mode': 'unavailable', 'image_analyzed': False, 'human_review_required': True, 'summary': 'Analysis could not complete. Your report is preserved for human review.'}
        db.add(AgentExecution(agent='Civic Intelligence Agent', incident_id=incident_id, status='Failed', summary='Report preserved; human review required.', error=type(exc).__name__, input_context={}, output={}))
        commit(db)
    return db.get(Incident, incident_id)


def recalculate(db):
    from .intelligence import refresh_risk
    try:
        refresh_risk(db, fetch_live=False)
        commit(db)
    except Exception:
        db.rollback()
        logger.exception('Risk refresh failed; previous risk history preserved')
