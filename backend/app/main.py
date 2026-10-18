import asyncio
import io
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from .config import settings
from .db import Base, SessionLocal, engine, get_db
from .models import *
from .schemas import *
from .security import current_user, hash_password, issue_token, require_roles, verify_password
from .services import OFFICIAL_ROLES, TERMINAL, audit, choose_zone, commit, dump, get_incident, incident_dump, notify, process_incident, recalculate, visible_incidents

logger = logging.getLogger(__name__)
official = require_roles('authority', 'admin')
admin = require_roles('admin')


def scheduled_refresh():
    from .intelligence import refresh_risk
    with SessionLocal() as db:
        try:
            refresh_risk(db, fetch_live=True)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception('Scheduled weather refresh failed')


async def weather_scheduler():
    while True:
        await asyncio.sleep(max(1, settings.weather_refresh_minutes) * 60)
        await run_in_threadpool(scheduled_refresh)


@asynccontextmanager
async def lifespan(app):
    if len(settings.jwt_secret) < 32:
        raise RuntimeError('Set JWT_SECRET to a random secret of at least 32 characters in .env.')
    Base.metadata.create_all(engine)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    if settings.demo_mode:
        from .seed import seed_demo
        with SessionLocal() as db:
            seed_demo(db)
    task = asyncio.create_task(weather_scheduler())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title='CivicShield AI', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False, allow_methods=['GET', 'POST', 'PATCH', 'DELETE'], allow_headers=['Authorization', 'Content-Type'])


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    messages = [f"{'.'.join(str(x) for x in e['loc'] if x != 'body')}: {e['msg']}" for e in exc.errors()]
    return JSONResponse(status_code=422, content={'detail': '; '.join(messages)})


@app.get('/api/health')
def health(db: Session = Depends(get_db)):
    db.execute(text('SELECT 1'))
    return {'status': 'ok', 'database': 'connected', 'demo_mode': settings.demo_mode, 'ai_mode': 'vision_api' if settings.openai_api_key else 'transparent_text_rules', 'service': 'CivicShield AI'}


@app.post('/api/auth/login')
def login(data: Login, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email))
    if not user or not user.active or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, 'Email or password is incorrect, or the account is disabled.')
    audit(db, user, 'Signed in')
    commit(db)
    return {'access_token': issue_token(user), 'token_type': 'bearer', 'user': dump(user)}


@app.post('/api/auth/register', status_code=201)
def register(data: Register, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email)):
        raise HTTPException(409, 'An account with this email already exists.')
    user = User(name=data.name, email=data.email, password_hash=hash_password(data.password), role='citizen')
    db.add(user)
    commit(db)
    audit(db, user, 'Registered citizen account')
    commit(db)
    return {'access_token': issue_token(user), 'token_type': 'bearer', 'user': dump(user)}


@app.get('/api/auth/me')
def me(user: User = Depends(current_user)):
    return dump(user)


@app.get('/api/incidents')
def incidents(search: str = '', category: str | None = None, status: str | None = None, severity: str | None = None, zone_id: int | None = None, from_date: datetime | None = None, to_date: datetime | None = None, include_archived: bool = False, db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = visible_incidents(db, user)
    if not include_archived:
        query = query.where(Incident.archived.is_(False))
    if search:
        query = query.where(or_(Incident.title.ilike(f'%{search}%'), Incident.description.ilike(f'%{search}%'), Incident.reference.ilike(f'%{search}%'), Incident.location_name.ilike(f'%{search}%')))
    for key, value in [('category', category), ('status', status), ('severity', severity), ('zone_id', zone_id)]:
        if value is not None:
            query = query.where(getattr(Incident, key) == value)
    # Date-only and timezone-free API bounds use UTC, matching persisted event
    # timestamps. Never let PostgreSQL's session timezone silently shift them.
    # Explicit offsets supplied by the frontend retain their original meaning.
    if from_date is not None and from_date.tzinfo is None:
        from_date = from_date.replace(tzinfo=timezone.utc)
    if to_date is not None and to_date.tzinfo is None:
        to_date = to_date.replace(tzinfo=timezone.utc)
    if from_date:
        query = query.where(Incident.created_at >= from_date)
    if to_date:
        if to_date.hour == to_date.minute == to_date.second == to_date.microsecond == 0:
            query = query.where(Incident.created_at < to_date + timedelta(days=1))
        else:
            query = query.where(Incident.created_at <= to_date)
    return [incident_dump(db, i) for i in db.scalars(query.order_by(Incident.created_at.desc())).all()]


@app.get('/api/incidents/{incident_id}')
def incident_details(incident_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return incident_dump(db, get_incident(db, incident_id, user), True, user)


@app.post('/api/reports', status_code=201)
def create_report(data: ReportCreate, db: Session = Depends(get_db), user: User = Depends(require_roles('citizen'))):
    attachments = []
    for attachment_id in set(data.attachment_ids):
        attachment = db.get(Attachment, attachment_id)
        if not attachment or attachment.user_id != user.id or attachment.incident_id is not None or attachment.deleted or attachment.kind != 'report':
            raise HTTPException(400, 'A selected photograph is missing, belongs to someone else, or is already attached.')
        attachments.append(attachment)
    incident = Incident(reference=f'CS-{datetime.now(timezone.utc):%y%m%d}-{secrets.token_hex(3).upper()}', title=data.title, description=data.description, latitude=data.latitude, longitude=data.longitude, location_name=data.location_name, zone_id=choose_zone(db, data.latitude, data.longitude), citizen_id=user.id, category='Other civic infrastructure hazards')
    db.add(incident)
    db.flush()
    db.add(Report(incident_id=incident.id, citizen_id=user.id, original_description=data.description))
    for attachment in attachments:
        attachment.incident_id = incident.id
    audit(db, user, 'Report submitted', data.title, incident.id)
    notify(db, incident, 'Report received', f'{incident.reference} is being analyzed. Thank you for reporting this hazard.')
    commit(db)
    incident = process_incident(db, incident)
    return incident_dump(db, incident, True, user)


@app.patch('/api/reports/{incident_id}')
def edit_report(incident_id: int, data: ReportEdit, db: Session = Depends(get_db), user: User = Depends(require_roles('citizen'))):
    incident = get_incident(db, incident_id, user)
    if incident.duplicate_of:
        raise HTTPException(409, 'The authority must separate this consolidated report before its hazard details can change.')
    if incident.status not in {'Submitted', 'Under Analysis', 'Pending Review', 'Rejected', 'Reopened'} or incident.archived:
        raise HTTPException(409, 'Reports can be edited before assignment. Contact the authority through a note for active work.')
    values = data.model_dump(exclude_unset=True, exclude_none=True)
    if not values:
        raise HTTPException(400, 'Supply at least one report field to change.')
    attachment_ids = values.pop('attachment_ids', None)
    new_attachments = []
    if attachment_ids is not None:
        for attachment_id in set(attachment_ids):
            attachment = db.get(Attachment, attachment_id)
            if not attachment or attachment.deleted or attachment.user_id != user.id or attachment.kind != 'report' or attachment.incident_id not in {None, incident.id}:
                raise HTTPException(400, 'A selected photograph is missing, belongs to another report, or is not your report evidence.')
            if attachment.incident_id is None:
                new_attachments.append(attachment)
        existing = db.scalars(select(Attachment).where(Attachment.incident_id == incident.id, Attachment.kind == 'report', Attachment.deleted.is_(False))).all()
        if len(existing) + len(new_attachments) > 8:
            raise HTTPException(422, 'A report can contain at most 8 photographs. Remove an existing photograph first.')
        for attachment in new_attachments:
            attachment.incident_id = incident.id
    for key, value in values.items():
        setattr(incident, key, value)
    incident.zone_id = choose_zone(db, incident.latitude, incident.longitude)
    incident.status = 'Pending Review'
    audit(db, user, 'Report edited', ', '.join(values) + (f'; linked {len(new_attachments)} new photograph(s)' if new_attachments else ''), incident.id)
    commit(db)
    return incident_dump(db, process_incident(db, incident), True, user)


@app.post('/api/reports/{incident_id}/withdraw')
def withdraw_report(incident_id: int, data: Withdraw, db: Session = Depends(get_db), user: User = Depends(current_user)):
    incident = get_incident(db, incident_id, user)
    if user.role not in {'citizen', 'admin', 'authority'}:
        raise HTTPException(403, 'Only the reporting citizen or authority can withdraw a report.')
    report = db.scalar(select(Report).where(Report.incident_id == incident.id))
    if not report:
        raise HTTPException(404, 'Original report not found.')
    if data.restore:
        if incident.status != 'Withdrawn':
            raise HTTPException(409, 'Only withdrawn reports can be restored.')
        incident.status = report.previous_status or 'Pending Review'
        report.withdrawn = False
        incident.archived = False
        action = 'Report restored'
    else:
        if incident.status not in {'Submitted', 'Under Analysis', 'Pending Review', 'Rejected', 'Reopened'}:
            raise HTTPException(409, 'Assigned, active, or completed work requires authority review before withdrawal.')
        report.previous_status = incident.status
        report.withdrawn = True
        incident.status = 'Withdrawn'
        action = 'Report withdrawn'
    audit(db, user, action, 'Original submission and evidence retained.', incident.id)
    notify(db, incident, action)
    commit(db)
    recalculate(db)
    return incident_dump(db, incident, True, user)


@app.patch('/api/incidents/{incident_id}')
def edit_incident(incident_id: int, data: IncidentEdit, db: Session = Depends(get_db), user: User = Depends(official)):
    incident = get_incident(db, incident_id, user)
    if incident.duplicate_of:
        raise HTTPException(409, 'Separate this consolidated report before changing the incident.')
    values = data.model_dump(exclude_unset=True, exclude_none=True)
    reason = values.pop('reason', '')
    if not values:
        raise HTTPException(400, 'Supply at least one incident field to change.')
    if 'severity' in values and values['severity'] != incident.severity and len(reason.strip()) < 5:
        raise HTTPException(422, 'A justification of at least 5 characters is required for a severity override.')
    if 'department_id' in values:
        department = db.get(Department, values['department_id'])
        if not department or not department.active:
            raise HTTPException(422, 'Choose an active department.')
        if incident.team_id:
            team = db.get(Team, incident.team_id)
            if team and team.department_id != values['department_id']:
                raise HTTPException(409, 'Cancel or reassign the current team before changing to a different department.')
    for key, value in values.items():
        setattr(incident, key, value)
    if 'latitude' in values or 'longitude' in values:
        incident.zone_id = choose_zone(db, incident.latitude, incident.longitude)
    audit(db, user, 'Incident corrected', f"Fields: {', '.join(values)}. {reason}", incident.id)
    notify(db, incident, 'Your report was reviewed', reason or 'The authority updated the incident details.')
    commit(db)
    recalculate(db)
    return incident_dump(db, incident, True)


TRANSITIONS = {
    'Submitted': {'Under Analysis', 'Pending Review', 'Rejected'},
    'Under Analysis': {'Pending Review', 'Rejected'},
    'Pending Review': {'Rejected', 'Under Analysis'},
    'Assigned': {'In Progress', 'Pending Review', 'Rejected'},
    'In Progress': {'Resolved', 'Pending Review'},
    'Resolved': {'Closed', 'In Progress', 'Reopened'},
    'Closed': {'Reopened'},
    'Rejected': {'Reopened'},
    'Withdrawn': {'Reopened'},
    'Reopened': {'Pending Review', 'In Progress', 'Rejected'},
}


@app.post('/api/incidents/{incident_id}/status')
def update_status(incident_id: int, data: StatusChange, db: Session = Depends(get_db), user: User = Depends(official)):
    incident = get_incident(db, incident_id, user)
    if incident.duplicate_of:
        raise HTTPException(409, 'Progress the consolidated parent incident, or separate this report first.')
    if data.status not in TRANSITIONS.get(incident.status, set()):
        raise HTTPException(409, f'Cannot transition from {incident.status} to {data.status}. Use assignment and completion workflows where required.')
    if data.status in {'Rejected', 'Reopened', 'In Progress'} and len(data.reason.strip()) < 5:
        raise HTTPException(422, 'Add a reason of at least 5 characters for this decision.')
    if data.status == 'Resolved':
        raise HTTPException(409, 'A worker must submit completion evidence through their assignment before resolution review.')
    if data.status == 'Closed':
        submitted = current_assignment(db, incident)
        evidence = completion_evidence(db, incident, submitted) if submitted else None
        if not submitted or submitted.status != 'Submitted' or not evidence:
            raise HTTPException(409, 'Verified closure requires a submitted assignment and completion evidence.')
    if data.status == 'In Progress' and not incident.team_id:
        raise HTTPException(409, 'Assign an active team before starting work.')
    old_status = incident.status
    incident.status = data.status
    if data.status in {'Rejected', 'Pending Review', 'Reopened'}:
        for assignment in db.scalars(select(Assignment).where(Assignment.incident_id == incident.id, Assignment.status.in_(['Assigned', 'Acknowledged', 'In Progress']))):
            assignment.status = 'Cancelled'
        incident.team_id = None
    elif data.status == 'In Progress':
        assignment = current_assignment(db, incident)
        if not assignment:
            raise HTTPException(409, 'A current team assignment is required before progressing work.')
        assignment.status = 'In Progress'
        if old_status == 'Resolved':
            audit(db, user, 'Completion corrections requested', data.reason, incident.id)
    if data.status == 'Reopened':
        incident.archived = False
        report = db.scalar(select(Report).where(Report.incident_id == incident.id))
        if report:
            report.withdrawn = False
    audit(db, user, f'Status: {old_status} → {data.status}', data.reason, incident.id)
    notify(db, incident, f'Your report is {data.status.lower()}', data.reason)
    commit(db)
    recalculate(db)
    return incident_dump(db, incident, True)


@app.post('/api/incidents/{incident_id}/archive')
def archive_incident(incident_id: int, data: Archive, db: Session = Depends(get_db), user: User = Depends(official)):
    incident = get_incident(db, incident_id, user)
    if data.archived and incident.status not in TERMINAL:
        raise HTTPException(409, 'Close, reject, or withdraw an incident before archiving it.')
    incident.archived = data.archived
    audit(db, user, 'Incident archived' if data.archived else 'Incident unarchived', 'Record and evidence retained.', incident.id)
    commit(db)
    return incident_dump(db, incident, True)


@app.post('/api/incidents/{incident_id}/analyze')
def analyze(incident_id: int, db: Session = Depends(get_db), user: User = Depends(official)):
    incident = get_incident(db, incident_id, user)
    if incident.status in TERMINAL or incident.archived or incident.duplicate_of:
        raise HTTPException(409, 'Reopen this incident before requesting new analysis.')
    audit(db, user, 'Analysis requested', 'Three-agent pipeline; assignments remain subject to human approval.', incident.id)
    commit(db)
    return incident_dump(db, process_incident(db, incident), True)


@app.post('/api/incidents/{incident_id}/duplicate')
def review_duplicate(incident_id: int, data: DuplicateReview, db: Session = Depends(get_db), user: User = Depends(official)):
    incident = get_incident(db, incident_id, user)
    target = get_incident(db, data.target_id, user)
    if incident.id == target.id:
        raise HTTPException(422, 'An incident cannot duplicate itself.')
    candidate = db.scalar(select(DuplicateCandidate).where(DuplicateCandidate.incident_id == incident.id, DuplicateCandidate.target_id == target.id))
    if not candidate:
        candidate = DuplicateCandidate(incident_id=incident.id, target_id=target.id, reason='Authority-reviewed relationship', score=1)
        db.add(candidate)
    if data.action == 'merge':
        if incident.archived or target.archived or incident.status in TERMINAL or target.status in TERMINAL:
            raise HTTPException(409, 'Reopen and unarchive both reports before consolidating them.')
        if current_assignment(db, incident):
            raise HTTPException(409, 'Cancel or complete the source report assignment before consolidating it.')
        cursor = target
        visited = {incident.id}
        while cursor:
            if cursor.id in visited:
                raise HTTPException(409, 'This merge would create a circular duplicate relationship.')
            visited.add(cursor.id)
            cursor = db.get(Incident, cursor.duplicate_of) if cursor.duplicate_of else None
        incident.duplicate_of = target.id
        candidate.status = 'Confirmed'
    elif data.action == 'separate':
        if incident.duplicate_of != target.id and target.duplicate_of != incident.id:
            raise HTTPException(409, 'These incidents are not currently merged.')
        if incident.duplicate_of == target.id:
            incident.duplicate_of = None
        if target.duplicate_of == incident.id:
            target.duplicate_of = None
        candidate.status = 'Separated'
    else:
        if incident.duplicate_of == target.id:
            raise HTTPException(409, 'Separate the confirmed merge before rejecting it.')
        candidate.status = 'Rejected'
    audit(db, user, f'Duplicate {data.action}', f'{incident.reference} ↔ {target.reference}; original reports preserved.', incident.id)
    audit(db, user, f'Duplicate {data.action}', f'Related report: {incident.reference}.', target.id)
    notify(db, incident, 'Duplicate relationship reviewed', f'The authority chose to {data.action} this relationship. Your submission remains available.')
    commit(db)
    recalculate(db)
    return incident_dump(db, incident, True)


@app.post('/api/uploads', status_code=201)
async def upload(file: UploadFile = File(...), incident_id: int | None = Form(default=None), kind: str = Form(default='report'), db: Session = Depends(get_db), user: User = Depends(current_user)):
    if kind not in {'report', 'completion'}:
        raise HTTPException(422, 'Evidence kind must be report or completion.')
    if incident_id is None and (user.role != 'citizen' or kind != 'report'):
        raise HTTPException(422, 'Choose an incident before uploading completion evidence.')
    if incident_id is not None:
        incident = get_incident(db, incident_id, user)
        if incident.archived or incident.status in TERMINAL:
            raise HTTPException(409, 'Evidence cannot be added to archived or terminal incidents.')
        if user.role == 'citizen' and kind != 'report':
            raise HTTPException(403, 'Completion evidence must be uploaded by the assigned team or authority.')
        if user.role == 'worker' and kind != 'completion':
            raise HTTPException(403, 'Workers can upload completion evidence only.')
        if user.role == 'worker':
            active_team(db, user.team_id)
            assignment = current_assignment(db, incident)
            if not assignment or assignment.team_id != user.team_id or assignment.status != 'In Progress':
                raise HTTPException(409, 'Start your current assignment before uploading completion evidence.')
    content = await file.read(8 * 1024 * 1024 + 1)
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(413, 'Images must be 8 MB or smaller.')
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.format not in {'JPEG', 'PNG', 'WEBP'}:
                raise ValueError('format')
            if image.width * image.height > 30_000_000:
                raise ValueError('dimensions')
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            image = image.convert('RGB')
            image.thumbnail((2400, 2400))
            clean = io.BytesIO()
            image.save(clean, format='JPEG', quality=88)
    except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError):
        raise HTTPException(422, 'Upload a valid JPEG, PNG, or WebP photograph under 30 megapixels.')
    storage_name = secrets.token_hex(24) + '.jpg'
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    (settings.upload_dir / storage_name).write_bytes(clean.getvalue())
    attachment = Attachment(user_id=user.id, incident_id=incident_id, filename=Path(file.filename or 'photograph.jpg').name[:255], storage_name=storage_name, content_type='image/jpeg', kind=kind)
    db.add(attachment)
    audit(db, user, 'Evidence uploaded', f'{kind}: {attachment.filename}', incident_id)
    commit(db)
    return dump(attachment)


@app.get('/api/uploads/{attachment_id}/file')
def attachment_file(attachment_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    attachment = db.get(Attachment, attachment_id)
    if not attachment or attachment.deleted:
        raise HTTPException(404, 'Photograph not found.')
    if attachment.incident_id:
        get_incident(db, attachment.incident_id, user)
    elif attachment.user_id != user.id and user.role not in OFFICIAL_ROLES:
        raise HTTPException(403, 'This photograph belongs to another user.')
    path = settings.upload_dir / attachment.storage_name
    if not path.is_file():
        raise HTTPException(404, 'The photograph file is unavailable.')
    return FileResponse(path, media_type=attachment.content_type, headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})


@app.delete('/api/uploads/{attachment_id}')
def delete_attachment(attachment_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    attachment = db.get(Attachment, attachment_id)
    if not attachment or attachment.deleted:
        raise HTTPException(404, 'Photograph not found.')
    if attachment.incident_id:
        incident = get_incident(db, attachment.incident_id, user)
        if incident.status in {'Closed', 'Resolved'} or incident.archived:
            raise HTTPException(409, 'Completion review and closed evidence is retained. Reopen the incident before changing it.')
    if user.role != 'admin' and attachment.user_id != user.id:
        raise HTTPException(403, 'Only the uploader or administrator can remove this evidence.')
    attachment.deleted = True
    audit(db, user, 'Evidence removed', f'Attachment {attachment.id}; retained for audit.', attachment.incident_id)
    commit(db)
    return {'success': True}


@app.post('/api/incidents/{incident_id}/notes', status_code=201)
def add_note(incident_id: int, data: NoteBody, db: Session = Depends(get_db), user: User = Depends(current_user)):
    incident = get_incident(db, incident_id, user)
    if incident.archived:
        raise HTTPException(409, 'Unarchive this incident before adding notes.')
    note = Note(incident_id=incident.id, user_id=user.id, body=data.body)
    db.add(note)
    audit(db, user, 'Note added', data.body, incident.id)
    if user.id != incident.citizen_id:
        notify(db, incident, 'New authority or team update', data.body)
    commit(db)
    result = dump(note)
    result['author_name'] = user.name
    return result


def authorized_note(db, note_id, user):
    note = db.get(Note, note_id)
    if not note or note.deleted:
        raise HTTPException(404, 'Note not found.')
    get_incident(db, note.incident_id, user)
    if note.user_id != user.id and user.role != 'admin':
        raise HTTPException(403, 'Only the note author or administrator can change this note.')
    return note


@app.patch('/api/notes/{note_id}')
def edit_note(note_id: int, data: NoteBody, db: Session = Depends(get_db), user: User = Depends(current_user)):
    note = authorized_note(db, note_id, user)
    note.body = data.body
    audit(db, user, 'Note edited', data.body, note.incident_id)
    commit(db)
    return dump(note)


@app.delete('/api/notes/{note_id}')
def delete_note(note_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    note = authorized_note(db, note_id, user)
    note.deleted = True
    audit(db, user, 'Note removed', f'Note {note.id}; audit retained.', note.incident_id)
    commit(db)
    return {'success': True}


def active_team(db, team_id):
    team = db.get(Team, team_id)
    department = db.get(Department, team.department_id) if team else None
    if not team or not team.active or not department or not department.active:
        raise HTTPException(422, 'Choose an active team in an active department.')
    return team


def current_assignment(db, incident):
    if not incident.team_id:
        return None
    latest = db.scalar(select(Assignment).where(Assignment.incident_id == incident.id, Assignment.status != 'Cancelled').order_by(Assignment.id.desc()).limit(1))
    return latest if latest and latest.team_id == incident.team_id else None


def completion_evidence(db, incident, assignment):
    # New assignments and authority correction requests require fresh evidence.
    correction = db.scalar(select(AuditLog).where(AuditLog.incident_id == incident.id, AuditLog.action == 'Completion corrections requested').order_by(AuditLog.created_at.desc()).limit(1))
    since = max(assignment.created_at, correction.created_at) if correction else assignment.created_at
    return db.scalar(select(Attachment).where(Attachment.incident_id == incident.id, Attachment.kind == 'completion', Attachment.deleted.is_(False), Attachment.created_at >= since))


def has_open_work(db, cls, entity_id):
    query = select(Assignment).join(Incident).where(Assignment.status != 'Cancelled', Incident.archived.is_(False), Incident.status.notin_(['Closed', 'Rejected', 'Withdrawn']))
    if cls is Department:
        query = query.join(Team, Assignment.team_id == Team.id).where(Team.department_id == entity_id)
    else:
        query = query.where(Assignment.team_id == entity_id)
    return db.scalar(query.limit(1)) is not None


@app.post('/api/incidents/{incident_id}/assignments', status_code=201)
def assign(incident_id: int, data: AssignmentCreate, db: Session = Depends(get_db), user: User = Depends(official)):
    incident = get_incident(db, incident_id, user)
    if incident.status in TERMINAL or incident.status == 'Resolved' or incident.archived or incident.duplicate_of:
        raise HTTPException(409, 'Reopen or separate this incident before assigning it.')
    team = active_team(db, data.team_id)
    for existing in db.scalars(select(Assignment).where(Assignment.incident_id == incident.id, Assignment.status.in_(['Assigned', 'Acknowledged', 'In Progress']))):
        existing.status = 'Cancelled'
    assignment = Assignment(incident_id=incident.id, team_id=team.id, assigned_by=user.id, notes=data.notes)
    db.add(assignment)
    incident.team_id = team.id
    incident.department_id = team.department_id
    incident.status = 'Assigned'
    audit(db, user, 'Team assigned', f'{team.name}. {data.notes}', incident.id)
    notify(db, incident, 'A team has been assigned', team.name)
    commit(db)
    return dump(assignment)


@app.get('/api/assignments')
def assignments(db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = select(Assignment)
    if user.role == 'worker':
        query = query.where(Assignment.team_id == (user.team_id or -1))
    elif user.role == 'citizen':
        query = query.join(Incident).where(Incident.citizen_id == user.id)
    return [dump(a) for a in db.scalars(query.order_by(Assignment.id.desc()))]


@app.patch('/api/assignments/{assignment_id}')
def update_assignment(assignment_id: int, data: AssignmentEdit, db: Session = Depends(get_db), user: User = Depends(current_user)):
    assignment = db.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(404, 'Assignment not found.')
    incident = get_incident(db, assignment.incident_id, user)
    if user.role not in OFFICIAL_ROLES | {'worker'}:
        raise HTTPException(403, 'Citizens cannot change assignments.')
    if assignment.status == 'Cancelled' or incident.status in TERMINAL or incident.archived:
        raise HTTPException(409, 'This assignment is inactive; create a new assignment after reopening.')
    if user.role == 'worker' and (assignment.team_id != user.team_id or data.team_id is not None or data.status == 'Cancelled'):
        raise HTTPException(403, 'Workers can only progress their own assigned tasks.')
    latest = current_assignment(db, incident)
    if not latest or latest.id != assignment.id or incident.duplicate_of:
        raise HTTPException(409, 'This is a historical assignment. Use the current assignment for active work.')
    if user.role == 'worker':
        active_team(db, assignment.team_id)
    if data.team_id is not None:
        team = active_team(db, data.team_id)
        assignment.status = 'Cancelled'
        assignment = Assignment(incident_id=incident.id, team_id=team.id, assigned_by=user.id, status='Assigned', notes=data.notes if data.notes is not None else assignment.notes)
        db.add(assignment)
        db.flush()
        incident.team_id = team.id
        incident.department_id = team.department_id
        incident.status = 'Assigned'
    if data.notes is not None:
        assignment.notes = data.notes
    if data.status:
        allowed = {'Assigned': {'Acknowledged', 'In Progress', 'Cancelled'}, 'Acknowledged': {'In Progress', 'Cancelled'}, 'In Progress': {'Submitted', 'Cancelled'}, 'Submitted': {'In Progress', 'Cancelled'}}
        if data.status != assignment.status and data.status not in allowed.get(assignment.status, set()):
            raise HTTPException(409, f'Cannot change assignment from {assignment.status} to {data.status}.')
        if user.role == 'worker' and assignment.status == 'Submitted':
            raise HTTPException(409, 'Wait for authority review before changing submitted work.')
        if assignment.status == 'Submitted' and data.status == 'In Progress':
            audit(db, user, 'Completion corrections requested', data.notes or 'Authority requested another completion review.', incident.id)
        if data.status == 'Submitted':
            if len(assignment.notes.strip()) < 10:
                raise HTTPException(422, 'Completion requires notes of at least 10 characters.')
            evidence = completion_evidence(db, incident, assignment)
            if not evidence:
                raise HTTPException(422, 'Upload a completion photograph before submitting work.')
            incident.status = 'Resolved'
        elif data.status == 'In Progress':
            incident.status = 'In Progress'
        elif data.status == 'Cancelled':
            incident.status = 'Pending Review'
            incident.team_id = None
        assignment.status = data.status
    audit(db, user, 'Assignment updated', f'{assignment.status}. {assignment.notes}', incident.id)
    notify(db, incident, f'Work update: {incident.status}', assignment.notes)
    commit(db)
    recalculate(db)
    return dump(assignment)


@app.get('/api/departments')
def departments(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [dump(r) for r in db.scalars(select(Department).order_by(Department.id))]


@app.get('/api/teams')
def teams(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [dump(r) for r in db.scalars(select(Team).order_by(Team.id))]


@app.get('/api/zones')
def zones(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [dump(r) for r in db.scalars(select(Zone).order_by(Zone.id))]


@app.get('/api/users')
def users(db: Session = Depends(get_db), user: User = Depends(admin)):
    return [dump(r) for r in db.scalars(select(User).order_by(User.id))]


def create_entity(db, user, cls, data):
    entity = cls(**data)
    db.add(entity)
    audit(db, user, f'{cls.__name__} created', str(data.get('name', '')))
    commit(db)
    return dump(entity)


def update_entity(db, user, cls, entity_id, data):
    entity = db.get(cls, entity_id)
    if not entity:
        raise HTTPException(404, f'{cls.__name__} not found.')
    if not data:
        raise HTTPException(400, 'Supply at least one field to change.')
    if cls in {Team, Department} and data.get('active') is False and has_open_work(db, cls, entity_id):
        raise HTTPException(409, 'Complete or cancel active assignments before deactivating this organization.')
    if cls is Team and data.get('active') is True:
        department = db.get(Department, data.get('department_id', entity.department_id))
        if not department or not department.active:
            raise HTTPException(422, 'Reactivate the department before its team.')
    for key, value in data.items():
        setattr(entity, key, value)
    audit(db, user, f'{cls.__name__} updated', f"{entity.name}: {', '.join(data)}")
    commit(db)
    return dump(entity)


def deactivate_entity(db, user, cls, entity_id):
    return update_entity(db, user, cls, entity_id, {'active': False})


@app.post('/api/departments', status_code=201)
def create_department(data: DepartmentCreate, db: Session = Depends(get_db), user: User = Depends(admin)):
    return create_entity(db, user, Department, data.model_dump())


@app.patch('/api/departments/{entity_id}')
def edit_department(entity_id: int, data: DepartmentEdit, db: Session = Depends(get_db), user: User = Depends(admin)):
    return update_entity(db, user, Department, entity_id, data.model_dump(exclude_unset=True, exclude_none=True))


@app.delete('/api/departments/{entity_id}')
def delete_department(entity_id: int, db: Session = Depends(get_db), user: User = Depends(admin)):
    return deactivate_entity(db, user, Department, entity_id)


@app.post('/api/teams', status_code=201)
def create_team(data: TeamCreate, db: Session = Depends(get_db), user: User = Depends(admin)):
    department = db.get(Department, data.department_id)
    if not department or not department.active:
        raise HTTPException(422, 'Choose an active department.')
    return create_entity(db, user, Team, data.model_dump())


@app.patch('/api/teams/{entity_id}')
def edit_team(entity_id: int, data: TeamEdit, db: Session = Depends(get_db), user: User = Depends(admin)):
    if data.department_id is not None:
        department = db.get(Department, data.department_id)
        if not department or not department.active:
            raise HTTPException(422, 'Choose an active department.')
        if has_open_work(db, Team, entity_id):
            raise HTTPException(409, 'Complete or cancel active team assignments before changing its department.')
    return update_entity(db, user, Team, entity_id, data.model_dump(exclude_unset=True, exclude_none=True))


@app.delete('/api/teams/{entity_id}')
def delete_team(entity_id: int, db: Session = Depends(get_db), user: User = Depends(admin)):
    return deactivate_entity(db, user, Team, entity_id)


@app.post('/api/zones', status_code=201)
def create_zone(data: ZoneCreate, db: Session = Depends(get_db), user: User = Depends(admin)):
    result = create_entity(db, user, Zone, data.model_dump())
    recalculate(db)
    return result


@app.patch('/api/zones/{entity_id}')
def edit_zone(entity_id: int, data: ZoneEdit, db: Session = Depends(get_db), user: User = Depends(admin)):
    result = update_entity(db, user, Zone, entity_id, data.model_dump(exclude_unset=True, exclude_none=True))
    for incident in db.scalars(select(Incident).where(Incident.archived.is_(False))):
        incident.zone_id = choose_zone(db, incident.latitude, incident.longitude)
    commit(db)
    recalculate(db)
    return result


@app.delete('/api/zones/{entity_id}')
def delete_zone(entity_id: int, db: Session = Depends(get_db), user: User = Depends(admin)):
    result = deactivate_entity(db, user, Zone, entity_id)
    recalculate(db)
    return result


@app.post('/api/users', status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db), user: User = Depends(admin)):
    values = data.model_dump()
    values['password_hash'] = hash_password(values.pop('password'))
    if data.role == 'worker' and data.team_id is None:
        raise HTTPException(422, 'Worker accounts require a team.')
    if data.team_id is not None:
        active_team(db, data.team_id)
    return create_entity(db, user, User, values)


@app.patch('/api/users/{entity_id}')
def edit_user(entity_id: int, data: UserEdit, db: Session = Depends(get_db), user: User = Depends(admin)):
    target = db.get(User, entity_id)
    if not target:
        raise HTTPException(404, 'User not found.')
    if target.id == user.id and (data.active is False or (data.role is not None and data.role != 'admin')):
        raise HTTPException(409, 'You cannot disable or demote your own administrator account.')
    values = data.model_dump(exclude_unset=True)
    if any(value is None for key, value in values.items() if key != 'team_id'):
        raise HTTPException(422, 'Only team_id can be cleared.')
    if values.get('password'):
        values['password_hash'] = hash_password(values.pop('password'))
    role = values.get('role', target.role)
    team_id = values.get('team_id', target.team_id)
    if role == 'worker' and team_id is None:
        raise HTTPException(422, 'Worker accounts require a team.')
    if team_id is not None:
        active_team(db, team_id)
    return update_entity(db, user, User, entity_id, values)


@app.delete('/api/users/{entity_id}')
def delete_user(entity_id: int, db: Session = Depends(get_db), user: User = Depends(admin)):
    if entity_id == user.id:
        raise HTTPException(409, 'You cannot disable your own administrator account.')
    return deactivate_entity(db, user, User, entity_id)


@app.get('/api/notifications')
def notifications(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [dump(r) for r in db.scalars(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()))]


@app.patch('/api/notifications/{notification_id}')
def edit_notification(notification_id: int, data: NotificationEdit, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = db.get(Notification, notification_id)
    if not item:
        raise HTTPException(404, 'Notification not found.')
    if item.user_id != user.id:
        raise HTTPException(403, 'This notification belongs to another user.')
    item.read = data.read
    commit(db)
    return dump(item)


@app.get('/api/audit')
def audit_log(db: Session = Depends(get_db), user: User = Depends(official)):
    result = []
    for item in db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(300)):
        row = dump(item)
        author = db.get(User, item.user_id) if item.user_id else None
        row['actor_name'] = author.name if author else 'System'
        result.append(row)
    return result


@app.get('/api/dashboard')
def dashboard(db: Session = Depends(get_db), user: User = Depends(current_user)):
    items = db.scalars(visible_incidents(db, user).where(Incident.archived.is_(False))).all()
    ids = [i.id for i in items]
    recent = db.scalars(select(AuditLog).where(AuditLog.incident_id.in_(ids)).order_by(AuditLog.created_at.desc()).limit(8)).all() if ids else []
    return {'total': len(items), 'new': sum(i.status in {'Submitted', 'Under Analysis', 'Pending Review'} for i in items), 'unresolved': sum(i.status not in {'Resolved', 'Closed', 'Rejected', 'Withdrawn'} for i in items), 'critical': sum(i.severity in {'High', 'Critical'} and i.status not in TERMINAL | {'Resolved'} for i in items), 'awaiting_review': sum(i.status in {'Pending Review', 'Resolved', 'Reopened'} for i in items), 'active': sum(i.status in {'Assigned', 'In Progress'} for i in items), 'resolved': sum(i.status in {'Resolved', 'Closed'} for i in items), 'recent_activity': [dump(i) for i in recent]}


def risk_dump(db, assessment):
    result = dump(assessment)
    geometry = assessment.provenance.get('zone_geometry', {})
    if geometry:
        result.update(zone_name=geometry.get('name'), latitude=geometry.get('latitude'), longitude=geometry.get('longitude'), radius_km=geometry.get('radius_km'))
    else:
        zone = db.get(Zone, assessment.zone_id)
        if zone:
            result.update(zone_name=zone.name, latitude=zone.latitude, longitude=zone.longitude, radius_km=zone.radius_km)
    return result


@app.get('/api/risk')
def risk(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = []
    for zone in db.scalars(select(Zone).where(Zone.active.is_(True)).order_by(Zone.id)):
        assessment = db.scalar(select(RiskAssessment).where(RiskAssessment.zone_id == zone.id).order_by(RiskAssessment.created_at.desc(), RiskAssessment.id.desc()).limit(1))
        if assessment:
            rows.append(risk_dump(db, assessment))
    return rows


@app.post('/api/risk/refresh')
def risk_refresh(data: RiskRefresh, db: Session = Depends(get_db), user: User = Depends(official)):
    if data.scenario and not settings.demo_mode:
        raise HTTPException(403, 'Synthetic weather scenarios require DEMO_MODE=true.')
    from .intelligence import refresh_risk
    try:
        assessments = refresh_risk(db, scenario=data.scenario, fetch_live=data.scenario is None)
        audit(db, user, 'Flood risk refreshed', f'Weather source: synthetic {data.scenario} scenario' if data.scenario else 'Weather refresh requested; see input provenance.')
        commit(db)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        logger.exception('Risk refresh request failed')
        raise HTTPException(502, 'Risk refresh failed. Previous assessments are preserved; try again.')
    return [risk_dump(db, a) for a in assessments]


@app.get('/api/risk/history')
def risk_history(zone_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(official)):
    query = select(RiskAssessment)
    if zone_id is not None:
        query = query.where(RiskAssessment.zone_id == zone_id)
    return [risk_dump(db, r) for r in db.scalars(query.order_by(RiskAssessment.created_at.desc(), RiskAssessment.id.desc()).limit(300))]


@app.get('/api/weather')
def weather(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [dump(r) for r in db.scalars(select(WeatherSnapshot).order_by(WeatherSnapshot.created_at.desc(), WeatherSnapshot.id.desc()).limit(12))]


@app.get('/api/agents')
def agents(db: Session = Depends(get_db), user: User = Depends(official)):
    return [dump(r) for r in db.scalars(select(AgentExecution).order_by(AgentExecution.created_at.desc(), AgentExecution.id.desc()).limit(200))]


@app.get('/api/recommendations')
def recommendations(db: Session = Depends(get_db), user: User = Depends(official)):
    return [dump(r) for r in db.scalars(select(Recommendation).order_by(Recommendation.created_at.desc()).limit(200))]


@app.patch('/api/recommendations/{recommendation_id}')
def review_recommendation(recommendation_id: int, data: RecommendationEdit, db: Session = Depends(get_db), user: User = Depends(official)):
    item = db.get(Recommendation, recommendation_id)
    if not item:
        raise HTTPException(404, 'Recommendation not found.')
    if data.status in {'Rejected', 'Overridden'} and len(data.reason.strip()) < 5:
        raise HTTPException(422, 'Add a reason of at least 5 characters for this decision.')
    item.status = data.status
    audit(db, user, f'Recommendation {data.status.lower()}', f'{item.action}. {data.reason}', item.incident_id)
    commit(db)
    return dump(item)


@app.post('/api/agents/{execution_id}/retry')
def retry_agent(execution_id: int, db: Session = Depends(get_db), user: User = Depends(official)):
    item = db.get(AgentExecution, execution_id)
    if not item:
        raise HTTPException(404, 'Agent execution not found.')
    if item.status != 'Failed':
        raise HTTPException(409, 'Only failed executions require retry.')
    if item.incident_id:
        incident = get_incident(db, item.incident_id, user)
        if incident.status in TERMINAL or incident.archived or incident.duplicate_of:
            raise HTTPException(409, 'Reopen or separate the incident before retrying its analysis.')
    previous_execution_id = db.scalar(select(func.max(AgentExecution.id))) or 0
    item.attempts += 1
    audit(db, user, 'Agent retry requested', item.agent, item.incident_id)
    commit(db)
    if item.incident_id:
        process_incident(db, get_incident(db, item.incident_id, user))
    else:
        from .intelligence import refresh_risk
        try:
            refresh_risk(db, fetch_live=False)
            commit(db)
        except Exception:
            db.rollback()
            raise HTTPException(502, 'The retry failed. The original failed execution and its attempt count are preserved.')
    failed = db.scalar(select(AgentExecution).where(AgentExecution.id > previous_execution_id, AgentExecution.incident_id == item.incident_id, AgentExecution.status == 'Failed').order_by(AgentExecution.id.desc()).limit(1))
    if failed:
        raise HTTPException(502, 'The retry could not complete. Your report is preserved for human review; see the latest failed execution.')
    item.status = 'Retried'
    audit(db, user, 'Agent retry completed', 'New execution records contain the retried results; original error retained.', item.incident_id)
    commit(db)
    return {'success': True, 'execution': dump(item)}
