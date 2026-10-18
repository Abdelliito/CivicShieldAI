import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Role = Literal['citizen', 'authority', 'worker', 'admin']
Severity = Literal['Low', 'Medium', 'High', 'Critical']
Status = Literal['Submitted', 'Under Analysis', 'Pending Review', 'Assigned', 'In Progress', 'Resolved', 'Closed', 'Rejected', 'Withdrawn', 'Reopened']
CATEGORIES = ['Potholes','Broken roads','Open manholes','Blocked drainage','Sewer overflow','Water accumulation','Garbage accumulation','Water leakage','Exposed electrical wiring','Fallen electric cables','Damaged streetlights','Damaged traffic signals','Other civic infrastructure hazards']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Login(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)

    @field_validator('email')
    @classmethod
    def email_valid(cls, value):
        value = value.lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
            raise ValueError('Enter a valid email address.')
        return value


class Register(Login):
    name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=200)


class ReportCreate(StrictModel):
    title: str = Field(min_length=5, max_length=180)
    description: str = Field(min_length=15, max_length=5000)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    location_name: str = Field(default='', max_length=240)
    attachment_ids: list[int] = Field(default_factory=list, max_length=8)


class ReportFields(StrictModel):
    title: str | None = Field(default=None, min_length=5, max_length=180)
    description: str | None = Field(default=None, min_length=15, max_length=5000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_name: str | None = Field(default=None, max_length=240)


class ReportEdit(ReportFields):
    attachment_ids: list[int] | None = Field(default=None, max_length=8)


class IncidentEdit(ReportFields):
    category: str | None = None
    severity: Severity | None = None
    department_id: int | None = None
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator('category')
    @classmethod
    def category_valid(cls, value):
        if value is not None and value not in CATEGORIES:
            raise ValueError('Choose a supported hazard category.')
        return value


class StatusChange(StrictModel):
    status: Status
    reason: str = Field(default='', max_length=2000)


class Withdraw(StrictModel):
    restore: bool = False


class Archive(StrictModel):
    archived: bool = True


class DuplicateReview(StrictModel):
    target_id: int
    action: Literal['merge', 'reject', 'separate']


class NoteBody(StrictModel):
    body: str = Field(min_length=2, max_length=5000)


class AssignmentCreate(StrictModel):
    team_id: int
    notes: str = Field(default='', max_length=3000)


class AssignmentEdit(StrictModel):
    team_id: int | None = None
    status: Literal['Assigned', 'Acknowledged', 'In Progress', 'Submitted', 'Cancelled'] | None = None
    notes: str | None = Field(default=None, max_length=3000)


class DepartmentCreate(StrictModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default='', max_length=2000)
    active: bool = True


class DepartmentEdit(StrictModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    active: bool | None = None


class TeamCreate(StrictModel):
    name: str = Field(min_length=2, max_length=120)
    department_id: int
    active: bool = True


class TeamEdit(StrictModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    department_id: int | None = None
    active: bool | None = None


class ZoneCreate(StrictModel):
    name: str = Field(min_length=2, max_length=120)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_km: float = Field(default=2, gt=0, le=50)
    historical_floods: int = Field(default=0, ge=0, le=10000)
    active: bool = True


class ZoneEdit(StrictModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_km: float | None = Field(default=None, gt=0, le=50)
    historical_floods: int | None = Field(default=None, ge=0, le=10000)
    active: bool | None = None


class UserCreate(Register):
    role: Role = 'citizen'
    team_id: int | None = None
    active: bool = True


class UserEdit(StrictModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=254)
    role: Role | None = None
    team_id: int | None = None
    password: str | None = Field(default=None, min_length=10, max_length=200)
    active: bool | None = None

    @field_validator('email')
    @classmethod
    def email_valid(cls, value):
        return Login.email_valid(value) if value is not None else None


class NotificationEdit(StrictModel):
    read: bool


class RiskRefresh(StrictModel):
    scenario: Literal['heavy_rain', 'clear', 'missing'] | None = None


class RecommendationEdit(StrictModel):
    status: Literal['Approved', 'Rejected', 'Overridden']
    reason: str = Field(default='', max_length=2000)
