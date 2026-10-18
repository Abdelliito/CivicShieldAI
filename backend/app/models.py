from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


def utcnow():
    return datetime.now(timezone.utc)


class Department(Base):
    __tablename__ = 'departments'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default='')
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Team(Base):
    __tablename__ = 'teams'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    department_id: Mapped[int] = mapped_column(ForeignKey('departments.id'))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class User(Base):
    __tablename__ = 'users'
    __table_args__ = (CheckConstraint("role IN ('citizen','authority','worker','admin')", name='valid_user_role'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default='citizen')
    team_id: Mapped[int | None] = mapped_column(ForeignKey('teams.id'), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Zone(Base):
    __tablename__ = 'zones'
    __table_args__ = (CheckConstraint('radius_km > 0 AND historical_floods >= 0', name='valid_zone_measurements'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    radius_km: Mapped[float] = mapped_column(Float, default=2.0)
    historical_floods: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Incident(Base):
    __tablename__ = 'incidents'
    __table_args__ = (
        CheckConstraint("severity IN ('Low','Medium','High','Critical')", name='valid_incident_severity'),
        CheckConstraint("status IN ('Submitted','Under Analysis','Pending Review','Assigned','In Progress','Resolved','Closed','Rejected','Withdrawn','Reopened')", name='valid_incident_status'),
        CheckConstraint('latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180', name='valid_incident_location'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), default='Other')
    severity: Mapped[str] = mapped_column(String(20), default='Medium')
    status: Mapped[str] = mapped_column(String(30), default='Submitted', index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    location_name: Mapped[str] = mapped_column(String(240), default='')
    zone_id: Mapped[int | None] = mapped_column(ForeignKey('zones.id'), nullable=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey('departments.id'), nullable=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey('teams.id'), nullable=True)
    citizen_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    duplicate_of: Mapped[int | None] = mapped_column(ForeignKey('incidents.id'), nullable=True)


class Report(Base):
    __tablename__ = 'reports'
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey('incidents.id'), unique=True)
    citizen_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    original_description: Mapped[str] = mapped_column(Text)
    withdrawn: Mapped[bool] = mapped_column(Boolean, default=False)
    previous_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Attachment(Base):
    __tablename__ = 'attachments'
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey('incidents.id'), nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    filename: Mapped[str] = mapped_column(String(255))
    storage_name: Mapped[str] = mapped_column(String(80), unique=True)
    content_type: Mapped[str] = mapped_column(String(60))
    kind: Mapped[str] = mapped_column(String(30), default='report')
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    analysis: Mapped[dict] = mapped_column(JSON, default=dict, server_default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Note(Base):
    __tablename__ = 'notes'
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey('incidents.id'), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    body: Mapped[str] = mapped_column(Text)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Assignment(Base):
    __tablename__ = 'assignments'
    __table_args__ = (
        CheckConstraint("status IN ('Assigned','Acknowledged','In Progress','Submitted','Cancelled')", name='valid_assignment_status'),
        CheckConstraint("sharing_scope IN ('full_report','location_only')", name='valid_assignment_sharing_scope'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey('incidents.id'), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey('teams.id'))
    assigned_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    worker_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    sharing_scope: Mapped[str] = mapped_column(String(20), default='full_report', server_default='full_report')
    status: Mapped[str] = mapped_column(String(30), default='Assigned')
    notes: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey('incidents.id'), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    detail: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey('incidents.id'), nullable=True)
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text, default='')
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DuplicateCandidate(Base):
    __tablename__ = 'duplicate_candidates'
    __table_args__ = (UniqueConstraint('incident_id', 'target_id', name='unique_duplicate_pair'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey('incidents.id'))
    target_id: Mapped[int] = mapped_column(ForeignKey('incidents.id'))
    score: Mapped[float] = mapped_column(Float, default=0)
    distance_m: Mapped[float] = mapped_column(Float, default=0)
    similarity: Mapped[float] = mapped_column(Float, default=0)
    reason: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(30), default='Pending')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WeatherSnapshot(Base):
    __tablename__ = 'weather_snapshots'
    id: Mapped[int] = mapped_column(primary_key=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey('zones.id'), nullable=True)
    rainfall_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    forecast_rainfall_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(180))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RiskAssessment(Base):
    __tablename__ = 'risk_assessments'
    id: Mapped[int] = mapped_column(primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey('zones.id'), index=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    level: Mapped[str] = mapped_column(String(30))
    factors: Mapped[dict] = mapped_column(JSON, default=dict)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentExecution(Base):
    __tablename__ = 'agent_executions'
    id: Mapped[int] = mapped_column(primary_key=True)
    agent: Mapped[str] = mapped_column(String(80))
    incident_id: Mapped[int | None] = mapped_column(ForeignKey('incidents.id'), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default='Completed')
    summary: Mapped[str] = mapped_column(Text, default='')
    input_context: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Recommendation(Base):
    __tablename__ = 'recommendations'
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey('incidents.id'), nullable=True, index=True)
    agent: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(30), default='Medium')
    status: Mapped[str] = mapped_column(String(30), default='Pending')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
