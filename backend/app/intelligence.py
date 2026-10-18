"""Controlled civic intelligence, weather ingestion, and transparent flood scoring.

The offline classifier is a deterministic text heuristic, never image recognition.
All three components have bounded tools and validated handoffs; they can recommend
actions but cannot assign workers, dispatch resources, or resolve/close incidents.
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

logger = logging.getLogger("civicshield.intelligence")

Severity = Literal["Low", "Medium", "High", "Critical"]
RiskLevel = Literal["Low", "Moderate", "High", "Insufficient Data"]
Category = Literal[
    "Potholes", "Broken roads", "Open manholes", "Blocked drainage",
    "Sewer overflow", "Water accumulation", "Garbage accumulation", "Water leakage",
    "Exposed electrical wiring", "Fallen electric cables", "Damaged streetlights",
    "Damaged traffic signals", "Other civic infrastructure hazards",
]
FLOOD_CATEGORIES = {"Blocked drainage", "Sewer overflow", "Water accumulation", "Water leakage"}
TERMINAL_STATUSES = {"Closed", "Resolved", "Rejected", "Withdrawn"}
CATEGORY_RULES: list[tuple[str, tuple[str, ...], str]] = [
    ("Fallen electric cables", ("fallen cable", "fallen wire", "downed cable", "downed wire", "hanging wire", "fallen electric"), "Electricity & Streetlights"),
    ("Exposed electrical wiring", ("exposed wire", "exposed electrical", "bare wire", "live wire", "high voltage", "sparking cable", "electric shock"), "Electricity & Streetlights"),
    ("Open manholes", ("open manhole", "uncovered manhole", "missing manhole", "manhole cover missing"), "Water & Sanitation"),
    ("Blocked drainage", ("blocked drain", "clogged drain", "drain blocked", "drain is blocked", "drains are blocked", "drainage is blocked", "blocked storm drain", "clogged storm drain", "choked drain", "drainage blocked", "drain blockage"), "Water & Sanitation"),
    ("Sewer overflow", ("sewer overflow", "sewage overflow", "overflowing sewer", "sewage", "sewerage", "gutter overflow"), "Water & Sanitation"),
    ("Water accumulation", ("waterlogging", "water logging", "waterlogged", "standing water", "water accumulation", "water has accumulated", "water is pooling", "flooded street", "flooded road", "rainwater", "water pooling"), "Water & Sanitation"),
    ("Water leakage", ("water leak", "leaking pipe", "burst pipe", "broken water pipe", "pipe leak", "leaking water main", "burst water main", "broken water main", "water main is leaking", "water pipe is leaking"), "Water & Sanitation"),
    ("Damaged traffic signals", ("traffic signal", "traffic light", "signal broken"), "Traffic Engineering"),
    ("Damaged streetlights", ("streetlight", "street light", "lamp post", "light pole"), "Electricity & Streetlights"),
    ("Potholes", ("pothole", "pot hole"), "Roads & Infrastructure"),
    ("Broken roads", ("broken road", "road damage", "damaged road", "road crack", "road collapse", "crumbling road"), "Roads & Infrastructure"),
    ("Garbage accumulation", ("garbage", "rubbish", "trash", "waste pile", "litter", "dumping"), "Solid Waste Management"),
]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class HazardAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Category
    severity: Severity
    confidence: float | None = Field(default=None, ge=0, le=1)
    recommended_department: str = Field(min_length=3, max_length=120)
    summary: str = Field(min_length=10, max_length=2000)
    evidence: list[str] = Field(default_factory=list, max_length=25)
    uncertainty: list[str] = Field(default_factory=list, max_length=20)
    image_analyzed: bool = False
    method: Literal["deterministic_text", "vision_model"] = "deterministic_text"
    human_review_required: Literal[True] = True
    detected_title: str | None = Field(default=None, min_length=3, max_length=160)
    relevance: Literal["relevant", "irrelevant", "uncertain"] = "uncertain"

    @model_validator(mode="after")
    def source_is_consistent(self):
        if self.image_analyzed != (self.method == "vision_model"):
            raise ValueError("Image analysis must correspond to an actual vision-model result")
        if self.method == "deterministic_text" and self.confidence is not None:
            raise ValueError("Uncalibrated heuristic output must not advertise a confidence probability")
        return self


class DuplicateMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_id: int
    distance_m: float = Field(ge=0)
    similarity: float = Field(ge=0, le=1)
    score: float = Field(ge=0, le=1)
    reason: str


class RiskWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")
    forecast: float = Field(default=0.42, ge=0)
    recent_rain: float = Field(default=0.18, ge=0)
    blocked_drains: float = Field(default=0.22, ge=0)
    water_incidents: float = Field(default=0.10, ge=0)
    history: float = Field(default=0.08, ge=0)
    forecast_saturation_mm: float = Field(default=60, gt=0)
    recent_saturation_mm: float = Field(default=40, gt=0)
    drain_saturation_count: int = Field(default=3, gt=0)
    water_saturation_count: int = Field(default=3, gt=0)
    history_saturation_count: int = Field(default=10, gt=0)
    moderate_threshold: float = Field(default=35, ge=0, le=100)
    high_threshold: float = Field(default=65, ge=0, le=100)

    @model_validator(mode="after")
    def valid_weights(self):
        if abs(sum(getattr(self, k) for k in ("forecast", "recent_rain", "blocked_drains", "water_incidents", "history")) - 1) > 1e-6:
            raise ValueError("Risk factor weights must sum to 1")
        if self.high_threshold <= self.moderate_threshold:
            raise ValueError("High threshold must exceed moderate threshold")
        return self


class RiskResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: float | None = Field(default=None, ge=0, le=100)
    level: RiskLevel
    factors: dict[str, Any]
    provenance: dict[str, Any]


class DisasterInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    zone_id: int | None
    risk_score: float | None = Field(ge=0, le=100)
    risk_level: RiskLevel
    relevant_incident_ids: list[int]
    vulnerable_locations: list[str]
    summary: str = Field(min_length=10)
    preventive_actions: list[str]
    uncertainties: list[str]


class ResponsePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incident_id: int
    priority: Severity
    department: str
    action: str = Field(min_length=10, max_length=2000)
    reason: str = Field(min_length=10, max_length=3000)
    approval_required: Literal[True] = True
    tools_used: list[str]


def classify_text(description: str, title: str = "", *, has_image: bool = False) -> HazardAnalysis:
    """Phrase matching and explicit context rules; confidence is intentionally null."""
    text = re.sub(r"\s+", " ", f"{title} {description}".lower()).strip()
    # A photo-first report may have no description. Absence of words cannot
    # become an invented image detection; retain an honest manual-review state.
    if not text or len(text) < 5:
        text = "photograph submitted for civic review"
    matches = []
    for category, phrases, department in CATEGORY_RULES:
        found = [p for p in phrases if re.search(r"\b" + re.escape(p) + r"\w*\b", text)]
        if found:
            matches.append((category, found, department))
    evidence = []
    uncertainty = ["Text-only heuristic; category and severity require human verification."]
    if matches:
        category, phrases, department = matches[0]
        evidence = [f"Description contains '{p}'." for p in phrases]
        if len(matches) > 1:
            uncertainty.append("Multiple hazards described: " + ", ".join(m[0] for m in matches))
    else:
        category, department = "Other civic infrastructure hazards", "General Civic Services"
        uncertainty.append("No supported hazard phrase identified; manual categorization required.")

    severity = "Medium"
    if category in {"Garbage accumulation", "Damaged streetlights"}:
        severity = "Low"
    immediate = any(p in text for p in ("sparking", "high voltage", "electrocut", "live wire", "injured", "injury", "person fell", "child fell", "trapped"))
    exposure = any(p in text for p in ("school", "hospital", "children", "crowded", "busy road", "main road", "pedestrian", "market"))
    aggravated = any(p in text for p in ("heavy rain", "knee deep", "waist deep", "rapidly rising", "road collapse", "large", "deep", "spreading", "blocked traffic"))
    if category in {"Open manholes", "Exposed electrical wiring", "Fallen electric cables"}:
        severity = "High"
    if exposure or aggravated:
        severity = "High"
        evidence.append("Reported exposure or adverse conditions raise the review priority.")
    if immediate:
        severity = "Critical"
        evidence.append("Description reports an immediate safety consequence; urgent human review is needed.")
    if has_image:
        uncertainty.append("Photograph retained as evidence but has NOT been analyzed by a vision model.")
    return HazardAnalysis(
        category=category, severity=severity, recommended_department=department,
        summary=f"{category} suggested from report wording. {severity} review priority based on the reported safety context.",
        evidence=evidence, uncertainty=uncertainty,
    )


def distance_m(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    """Haversine distance on WGS84-like sphere, sufficient for candidate screening."""
    a1, a2 = math.radians(lat_a), math.radians(lat_b)
    delta_lat, delta_lon = a2 - a1, math.radians(lon_b - lon_a)
    h = math.sin(delta_lat / 2) ** 2 + math.cos(a1) * math.cos(a2) * math.sin(delta_lon / 2) ** 2
    return 6371008.8 * 2 * math.asin(min(1, math.sqrt(h)))


def text_similarity(a: str, b: str) -> float:
    stops = {"the", "and", "this", "that", "there", "with", "from", "near", "very", "have", "been", "please", "report", "road"}
    def tokens(text):
        return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in stops}
    left, right = tokens(a), tokens(b)
    return len(left & right) / len(left | right) if left and right else 0.0


def duplicate_matches(incident: Any, candidates: list[Any], *, radius_m: float = 180, max_days: int = 7) -> list[DuplicateMatch]:
    results = []
    now = aware(getattr(incident, "created_at", None) or utcnow())
    for other in candidates:
        if other.id == incident.id or other.category != incident.category or getattr(other, "archived", False):
            continue
        if other.status in TERMINAL_STATUSES or getattr(other, "duplicate_of", None):
            continue
        hours = abs((now - aware(other.created_at)).total_seconds()) / 3600
        if hours > max_days * 24:
            continue
        dist = distance_m(incident.latitude, incident.longitude, other.latitude, other.longitude)
        if dist > radius_m:
            continue
        similarity = text_similarity(f"{incident.title} {incident.description}", f"{other.title} {other.description}")
        # Category, distance, timing, and description all influence the score.
        score = 0.25 + 0.35 * (1 - dist / radius_m) + 0.20 * (1 - hours / (max_days * 24)) + 0.20 * similarity
        if score < 0.55:
            continue
        results.append(DuplicateMatch(target_id=other.id, distance_m=round(dist, 2), similarity=round(similarity, 4), score=round(score, 4), reason=f"Same category, {dist:.0f} m apart, {hours:.1f} hours apart, text similarity {similarity:.2f}. Human merge review required."))
    return sorted(results, key=lambda r: r.score, reverse=True)


def risk_weights() -> RiskWeights:
    raw = os.getenv("RISK_WEIGHTS_JSON", "").strip()
    return RiskWeights.model_validate_json(raw) if raw else RiskWeights()


def calculate_risk(*, forecast_mm: float | None, recent_mm: float | None, blocked_drains: int = 0, water_incidents: int = 0, historical_floods: int | None = None, provenance: dict | None = None, weights: RiskWeights | None = None) -> RiskResult:
    config = weights or risk_weights()
    if min(blocked_drains, water_incidents) < 0 or (historical_floods is not None and historical_floods < 0):
        raise ValueError("Incident counts cannot be negative")
    for value in (forecast_mm, recent_mm):
        if value is not None and (not math.isfinite(value) or value < 0):
            raise ValueError("Rainfall must be a finite, nonnegative millimetre value")
    missing = []
    if forecast_mm is None:
        missing.append("forecast rainfall")
    if recent_mm is None:
        missing.append("recent rainfall")
    if historical_floods is None:
        missing.append("historical incident records")
    values = {"forecast_rain_mm": forecast_mm, "recent_rain_mm": recent_mm, "unresolved_blocked_drains": blocked_drains, "unresolved_water_incidents": water_incidents, "historical_floods": historical_floods}
    normalized = {
        "forecast": min((forecast_mm or 0) / config.forecast_saturation_mm, 1),
        "recent_rain": min((recent_mm or 0) / config.recent_saturation_mm, 1),
        "blocked_drains": min(blocked_drains / config.drain_saturation_count, 1),
        "water_incidents": min(water_incidents / config.water_saturation_count, 1),
        "history": min((historical_floods or 0) / config.history_saturation_count, 1),
    }
    contributions = {k: round(v * getattr(config, k) * 100, 2) for k, v in normalized.items()}
    raw_score = round(sum(contributions.values()), 1)
    incomplete_weather = forecast_mm is None or recent_mm is None
    score = None if incomplete_weather else raw_score
    level = "Insufficient Data" if incomplete_weather else "High" if score >= config.high_threshold else "Moderate" if score >= config.moderate_threshold else "Low"
    details = {
        "inputs": values, "contributions": contributions, "missing": missing,
        "explanation": "Required rainfall input is missing or stale; no complete score issued." if incomplete_weather else f"Weighted score {score}/100 from rainfall, unresolved flood-related hazards, and available history.",
        "weights": config.model_dump(), "partial_evidence_score": raw_score if incomplete_weather else None,
        "limitations": ["Heuristic estimate, not a calibrated flood probability or official warning.", "Zone circles are planning approximations; drainage capacity, terrain and hydrology are not modeled."] + (["Historical term omitted; weights remain fixed, so missing history may understate the score."] if historical_floods is None else []),
    }
    return RiskResult(score=score, level=level, factors=details, provenance={"model": "civicshield-weighted-v1", "calculated_at": utcnow().isoformat(), "units": "rainfall mm; normalized risk score 0–100", **(provenance or {})})


def scenario_weather(scenario: str) -> dict:
    values = {"heavy_rain": (96.0, 44.0), "clear": (0.0, 0.0), "missing": (None, None)}
    if scenario not in values:
        raise ValueError("Unknown weather scenario; use heavy_rain, clear, or missing")
    forecast, recent = values[scenario]
    return {"forecast_rain_mm": forecast, "recent_rain_mm": recent, "source": f"SYNTHETIC DEMONSTRATION: {scenario}", "payload": {"synthetic": True, "scenario": scenario, "description": "Injected demonstration scenario; not observed weather or an actual forecast.", "forecast_window_hours": 24, "recent_window_hours": 24}, "error": "Weather deliberately missing in demonstration scenario" if scenario == "missing" else None}


def fetch_open_meteo(latitude: float, longitude: float, *, client: Any = None, now: datetime | None = None) -> dict:
    """Fetch preceding 24-hour model rainfall plus next 24-hour forecast, in UTC."""
    now = aware(now or utcnow())
    params = {"latitude": latitude, "longitude": longitude, "hourly": "precipitation", "past_days": 2, "forecast_days": 3, "timezone": "GMT", "precipitation_unit": "mm"}
    getter = client.get if client else httpx.get
    response = getter("https://api.open-meteo.com/v1/forecast", params=params, timeout=12)
    response.raise_for_status()
    data = response.json()
    hourly = data.get("hourly", {})
    times, precip = hourly.get("time", []), hourly.get("precipitation", [])
    if len(times) != len(precip) or not times:
        raise ValueError("Open-Meteo returned incomplete hourly precipitation")
    end = now.replace(minute=0, second=0, microsecond=0)
    recent_start, forecast_end = end - timedelta(hours=24), end + timedelta(hours=24)
    recent, forecast = [], []
    for timestamp, value in zip(times, precip):
        stamp = aware(datetime.fromisoformat(timestamp.replace("Z", "+00:00")))
        if value is None:
            continue
        value = float(value)
        if value < 0 or not math.isfinite(value):
            raise ValueError("Open-Meteo returned invalid rainfall")
        # Precipitation is the sum of the preceding hour, timestamped at interval end.
        if recent_start < stamp <= end:
            recent.append(value)
        if end < stamp <= forecast_end:
            forecast.append(value)
    if len(recent) != 24 or len(forecast) != 24:
        raise ValueError("Open-Meteo does not contain both complete 24-hour rainfall windows")
    return {
        "forecast_rain_mm": round(sum(forecast), 3), "recent_rain_mm": round(sum(recent), 3),
        "source": "Open-Meteo forecast API (modeled rainfall; not local gauge observations)", "error": None,
        "payload": {"synthetic": False, "latitude": data.get("latitude", latitude), "longitude": data.get("longitude", longitude), "forecast_window_start": end.isoformat(), "forecast_window_end": forecast_end.isoformat(), "recent_window_start": recent_start.isoformat(), "recent_window_end": end.isoformat(), "retrieved_at": now.isoformat(), "attribution": "Weather data by Open-Meteo.com", "documentation": "https://open-meteo.com/en/docs", "hourly_units": data.get("hourly_units", {})},
    }


def _safe_provider_error(exc: Exception) -> str:
    # Never include request headers, data URLs, response bodies, or API keys in logs.
    if isinstance(exc, httpx.HTTPStatusError):
        return f"Provider HTTP {exc.response.status_code}"
    if isinstance(exc, httpx.TimeoutException):
        return "Provider request timed out"
    if isinstance(exc, httpx.RequestError):
        return "Provider network unavailable"
    return f"Invalid provider output ({type(exc).__name__})"


def analyze_vision(description: str, image_path: str | Path, *, title: str = "", client: Any = None) -> HazardAnalysis:
    """Compatibility wrapper over the configured, provider-independent boundary."""
    from .vision import analyze_image_file, VisionFailure
    payload = analyze_image_file(image_path, description=description, title=title, client=client)
    if not payload['image_analyzed']:
        error = payload['errors'][-1] if payload['errors'] else {'code': 'unavailable', 'message': payload['summary']}
        raise VisionFailure(error['code'], error['message'])
    return HazardAnalysis.model_validate({k: v for k, v in payload.items() if k in HazardAnalysis.model_fields})


def bounded_retry(operation: Callable[[], Any], *, max_attempts: int = 2) -> tuple[Any, int, list[str]]:
    failures = []
    for attempt in range(1, max_attempts + 1):
        try:
            return operation(), attempt, failures
        except (httpx.HTTPError, ValueError, RuntimeError, OSError) as exc:
            failures.append(_safe_provider_error(exc))
            if attempt == max_attempts:
                return None, attempt, failures
            time.sleep(0.05)
    raise AssertionError("Unreachable")


def _models():
    # Lazy import keeps pure scoring and schema tests independent of database setup.
    from . import models
    return models


def _execution(db, agent: str, incident_id: int | None, context: dict, output: dict, summary: str, *, status: str = "Completed", error: str | None = None, attempts: int = 1):
    model = _models().AgentExecution
    execution = model(agent=agent, incident_id=incident_id, status=status, summary=summary, input_context=context, output=output, error=error, attempts=attempts)
    db.add(execution)
    db.flush()
    logger.info("agent_execution", extra={"agent": agent, "incident_id": incident_id, "execution_id": execution.id, "status": status, "attempts": attempts})
    return execution


def _incident_context(incident) -> dict:
    return {"incident_id": incident.id, "category": incident.category, "severity": incident.severity, "status": incident.status, "zone_id": incident.zone_id, "latitude": incident.latitude, "longitude": incident.longitude}


def _containing_zone(db, incident):
    m = _models()
    options = [(distance_m(incident.latitude, incident.longitude, zone.latitude, zone.longitude), zone) for zone in db.query(m.Zone).filter(m.Zone.active.is_(True)).all()]
    contained = [(dist, zone) for dist, zone in options if dist <= zone.radius_km * 1000]
    return min(contained, key=lambda pair: pair[0])[1] if contained else None


def analyze_incident(db, incident, *, reuse_attachment_analysis: bool = False) -> dict:
    """Run Civic Intelligence with bounded vision tool, validated fallback, duplicates."""
    from .config import settings
    m = _models()
    db.flush()
    attachments = db.query(m.Attachment).filter(m.Attachment.incident_id == incident.id, m.Attachment.deleted.is_(False), m.Attachment.kind == "report").order_by(m.Attachment.id.desc()).all()
    from .vision import analyze_image_file, provider_status, reusable_analysis
    analysis = classify_text(incident.description or '', incident.title or '', has_image=bool(attachments))
    attempts, provider_failures = 1, []
    configured = provider_status()['configured']
    vision_metadata = {}
    if attachments:
        attachment = attachments[0]
        storage_root = Path(settings.upload_dir).resolve()
        image_path = (storage_root / attachment.storage_name).resolve()
        if image_path.parent != storage_root:
            provider_failures = ["Attachment path failed validation"]
        else:
            cached = reusable_analysis(getattr(attachment, 'analysis', None), image_path) if reuse_attachment_analysis else None
            vision_metadata = cached or analyze_image_file(image_path, description=incident.description or '', title=incident.title or '')
            if hasattr(attachment, 'analysis'):
                attachment.analysis = vision_metadata
            analysis = HazardAnalysis.model_validate({k: v for k, v in vision_metadata.items() if k in HazardAnalysis.model_fields})
            attempts = vision_metadata.get('attempts', 0)
            provider_failures = [f"{e['provider'] or 'image'}: {e['code']} - {e['message']}" for e in vision_metadata.get('errors', [])]
            vision_metadata = {k: v for k, v in vision_metadata.items() if k not in HazardAnalysis.model_fields}
            vision_metadata['reused_draft_analysis'] = cached is not None
    # Revalidate after merging provider and fallback metadata.
    analysis = HazardAnalysis.model_validate(analysis.model_dump())
    incident.category, incident.severity = analysis.category, analysis.severity
    zone = _containing_zone(db, incident)
    incident.zone_id = zone.id if zone else None
    departments = db.query(m.Department).filter(m.Department.active.is_(True)).all()
    department = next((d for d in departments if d.name.lower() == analysis.recommended_department.lower()), None)
    if not department:
        keywords = {"Water & Sanitation": ("water", "drain", "wasa", "sanitation"), "Electricity & Streetlights": ("electric", "streetlight", "lesco"), "Roads & Infrastructure": ("road", "infrastructure"), "Traffic Engineering": ("traffic",), "Solid Waste Management": ("waste", "solid", "garbage"), "General Civic Services": ("general", "civic")}
        department = next((d for d in departments if any(w in d.name.lower() for w in keywords.get(analysis.recommended_department, ()))), None)
    matches = duplicate_matches(incident, db.query(m.Incident).filter(m.Incident.id != incident.id).all(), radius_m=float(os.getenv("DUPLICATE_RADIUS_M", "180")), max_days=int(os.getenv("DUPLICATE_WINDOW_DAYS", "7")))
    matched_ids = {match.target_id for match in matches}
    for previous in db.query(m.DuplicateCandidate).filter(m.DuplicateCandidate.incident_id == incident.id, m.DuplicateCandidate.status == "Pending").all():
        if previous.target_id not in matched_ids:
            previous.status = "Outdated"
            previous.reason += " Candidate no longer matches the current report evidence/location/time window."
    for match in matches:
        existing = db.query(m.DuplicateCandidate).filter(m.DuplicateCandidate.incident_id == incident.id, m.DuplicateCandidate.target_id == match.target_id).first()
        if not existing:
            db.add(m.DuplicateCandidate(incident_id=incident.id, **match.model_dump(), status="Pending"))
        elif existing.status in {"Pending", "Outdated"}:
            for key, value in match.model_dump().items():
                setattr(existing, key, value)
            existing.status = "Pending"
    payload = {**analysis.model_dump(), **vision_metadata, "recommended_department_id": department.id if department else None, "duplicate_candidates": [match.model_dump() for match in matches], "analyzed_at": vision_metadata.get('analyzed_at') or utcnow().isoformat(), "provider_configured": configured, "provider_errors": provider_failures, "zone_match": zone.name if zone else "Outside configured planning zones"}
    payload["mode"] = "vision_model" if analysis.image_analyzed else "deterministic_text_fallback"
    if incident.department_id is None and department:
        incident.department_id = department.id
    incident.analysis = payload
    context = {**_incident_context(incident), "description": incident.description, "title": incident.title, "attachment_ids": [a.id for a in attachments], "tools_allowed": ["read_report", "classify_text", "vision_if_configured", "screen_duplicates", "recommend_department"], "tools_used": ["classify_text", "screen_duplicates", "recommend_department"] + (["vision_provider"] if configured and attachments else [])}
    fallback_used = bool(attachments) and not analysis.image_analyzed
    _execution(db, "Civic Intelligence Agent", incident.id, context, payload, analysis.summary + (" Image understanding unavailable; human review is required." if fallback_used else ""), status="Fallback" if fallback_used else "Completed", error="; ".join(provider_failures) or None, attempts=attempts)
    db.flush()
    return payload


def refresh_weather(db) -> list:
    """Persist one live provider attempt per active zone; failures are persisted too."""
    m = _models()
    snapshots = []
    for zone in db.query(m.Zone).filter(m.Zone.active.is_(True)).all():
        weather, attempts, failures = bounded_retry(lambda: fetch_open_meteo(zone.latitude, zone.longitude))
        if weather is None:
            weather = {"forecast_rain_mm": None, "recent_rain_mm": None, "source": "Open-Meteo unavailable", "payload": {"synthetic": False, "retrieved_at": utcnow().isoformat(), "attempts": attempts}, "error": "; ".join(failures)}
        snapshot = m.WeatherSnapshot(zone_id=zone.id, rainfall_mm=weather["recent_rain_mm"], forecast_rainfall_mm=weather["forecast_rain_mm"], source=weather["source"], is_demo=False, data=weather["payload"], error=weather["error"])
        db.add(snapshot)
        snapshots.append(snapshot)
    db.flush()
    return snapshots


def interpret_risk(*, zone_id: int | None, zone_name: str, risk: RiskResult, incidents: list[Any]) -> DisasterInterpretation:
    relevant = [i for i in incidents if i.category in FLOOD_CATEGORIES and i.status not in TERMINAL_STATUSES and not i.archived and not getattr(i, "duplicate_of", None)]
    actions = []
    if any(i.category == "Blocked drainage" for i in relevant):
        actions.append("Request authority review of blocked drains and a supervised drainage inspection before forecast rainfall.")
    if risk.level in {"Moderate", "High"}:
        actions.append("Review vulnerable road access and prepare a municipal drainage readiness plan; confirm local conditions first.")
    if risk.level == "Insufficient Data":
        actions.append("Restore weather inputs and recalculate before making a flood-risk decision.")
    if not actions:
        actions.append("Continue routine monitoring and verify newly reported flood-related hazards.")
    summary = f"{zone_name}: {risk.level} planning estimate"
    summary += "; complete rainfall inputs unavailable." if risk.score is None else f" at {risk.score}/100. {len(relevant)} unresolved flood-related incident(s) contribute."
    return DisasterInterpretation(zone_id=zone_id, risk_score=risk.score, risk_level=risk.level, relevant_incident_ids=[i.id for i in relevant], vulnerable_locations=list(dict.fromkeys((i.location_name or f"Incident {i.reference}") for i in relevant)), summary=summary, preventive_actions=actions, uncertainties=list(risk.factors.get("missing", [])) + risk.factors.get("limitations", []))


def _response_plan(incident, civic: dict, disaster: DisasterInterpretation) -> ResponsePlan:
    category, severity = civic["category"], civic["severity"]
    actions = {
        "Blocked drainage": "Review the drain obstruction, confirm safe access, and approve a supervised drainage inspection and clearance assignment.",
        "Sewer overflow": "Review the sewer overflow and approve a sanitation inspection with appropriate public access precautions.",
        "Water accumulation": "Verify the water depth and drainage condition, then approve a supervised waterlogging inspection.",
        "Water leakage": "Confirm the leaking water infrastructure and approve an inspection by the water maintenance team.",
        "Open manholes": "Urgently review the uncovered manhole, request authorized site protection, and approve a qualified repair team.",
        "Exposed electrical wiring": "Urgently review the electrical hazard and request a qualified utility team to assess and make the site safe.",
        "Fallen electric cables": "Urgently review the fallen cable and request a qualified utility team to assess isolation and public access protection.",
    }
    action = actions.get(category, "Review the report evidence, confirm the hazard classification, and approve an inspection by the appropriate municipal team.")
    priority = severity
    if category in FLOOD_CATEGORIES and disaster.risk_level == "High" and severity in {"Low", "Medium"}:
        priority = "High"
    reason = f"Civic classification: {category}, reported safety priority {severity}. Disaster Risk Agent handoff: {disaster.summary} All assignments and consequential actions require authority approval."
    return ResponsePlan(incident_id=incident.id, priority=priority, department=civic["recommended_department"], action=action, reason=reason, tools_used=["read_civic_analysis", "read_computed_risk", "propose_authority_action"])


def refresh_risk(db, scenario: str | None = None, fetch_live: bool = True) -> list:
    """Append immutable zone estimates with explicit weather/hazard/history provenance."""
    from .config import settings
    m = _models()
    zones = db.query(m.Zone).filter(m.Zone.active.is_(True)).all()
    if scenario:
        # Endpoint must additionally require authority/admin and DEMO_MODE for scenarios.
        if not settings.demo_mode:
            raise ValueError("Synthetic weather scenarios require DEMO_MODE=true")
        weather = scenario_weather(scenario)
        for zone in zones:
            db.add(m.WeatherSnapshot(zone_id=zone.id, rainfall_mm=weather["recent_rain_mm"], forecast_rainfall_mm=weather["forecast_rain_mm"], source=weather["source"], is_demo=True, data=weather["payload"], error=weather["error"]))
        db.flush()
    elif fetch_live:
        refresh_weather(db)
    incidents = db.query(m.Incident).filter(m.Incident.archived.is_(False)).all()
    assessments = []
    for zone in zones:
        weather = db.query(m.WeatherSnapshot).filter(m.WeatherSnapshot.zone_id == zone.id).order_by(m.WeatherSnapshot.created_at.desc(), m.WeatherSnapshot.id.desc()).first()
        in_zone = [i for i in incidents if distance_m(i.latitude, i.longitude, zone.latitude, zone.longitude) <= zone.radius_km * 1000 and not i.duplicate_of and i.status not in TERMINAL_STATUSES]
        blocked = sum(i.category == "Blocked drainage" for i in in_zone)
        water_count = sum(i.category in FLOOD_CATEGORIES - {"Blocked drainage"} for i in in_zone)
        fresh = bool(weather and (utcnow() - aware(weather.created_at)).total_seconds() <= float(os.getenv("WEATHER_MAX_AGE_HOURS", "6")) * 3600)
        weather_provenance = {"snapshot_id": weather.id if weather else None, "source": weather.source if weather else "No weather snapshot", "created_at": aware(weather.created_at).isoformat() if weather else None, "synthetic": bool(weather and weather.is_demo), "is_demo": bool(weather and weather.is_demo), "stale": bool(weather and not fresh), "error": weather.error if weather else "Weather has not been fetched", "details": weather.data if weather else {}}
        result = calculate_risk(forecast_mm=weather.forecast_rainfall_mm if fresh else None, recent_mm=weather.rainfall_mm if fresh else None, blocked_drains=blocked, water_incidents=water_count, historical_floods=zone.historical_floods, provenance={"zone_id": zone.id, "zone_name": zone.name, "zone_geometry": {"name": zone.name, "latitude": zone.latitude, "longitude": zone.longitude, "radius_km": zone.radius_km}, "weather": weather_provenance, "incident_ids": [i.id for i in in_zone if i.category in FLOOD_CATEGORIES], "history": {"source": "Synthetic demonstration / administrator-entered count" if settings.demo_mode else "Administrator-entered historical count; authenticity not independently verified", "synthetic": settings.demo_mode, "count": zone.historical_floods}, "trigger": f"synthetic:{scenario}" if scenario else "live_weather_refresh" if fetch_live else "incident_or_cached_weather_recalculation"})
        assessment = m.RiskAssessment(zone_id=zone.id, **result.model_dump())
        db.add(assessment)
        db.flush()
        assessments.append(assessment)
        interpretation = interpret_risk(zone_id=zone.id, zone_name=zone.name, risk=result, incidents=in_zone)
        _execution(db, "Disaster Risk Agent", None, {"zone_id": zone.id, "assessment_id": assessment.id, "risk_engine_output": result.model_dump(), "tools_allowed": ["read_calculated_risk", "read_zone_hazards", "explain_factors"], "tools_used": ["read_calculated_risk", "read_zone_hazards", "explain_factors"]}, interpretation.model_dump(), interpretation.summary)
        db.add(m.Recommendation(incident_id=None, agent="Disaster Risk Agent", action=f"{zone.name}: " + " ".join(interpretation.preventive_actions), reason=interpretation.summary + " Numerical score comes exclusively from the configured weighted engine.", priority="High" if result.level == "High" else "Medium" if result.level in {"Moderate", "Insufficient Data"} else "Low", status="Pending"))
    db.flush()
    return assessments


def run_pipeline(db, incident, *, reuse_attachment_analysis: bool = False):
    """Civic → numerical engine → Disaster → Coordinator, with persisted handoffs."""
    m = _models()
    initial_status = incident.status
    try:
        civic = analyze_incident(db, incident, reuse_attachment_analysis=reuse_attachment_analysis)
        assessments = refresh_risk(db, fetch_live=False)
        assessment = next((a for a in assessments if a.zone_id == incident.zone_id), None)
        zone = db.get(m.Zone, incident.zone_id) if incident.zone_id else None
        if assessment:
            risk = RiskResult(score=assessment.score, level=assessment.level, factors=assessment.factors, provenance=assessment.provenance)
        else:
            risk = calculate_risk(forecast_mm=None, recent_mm=None, historical_floods=None, provenance={"source": "Incident outside configured planning zones"})
        nearby = db.query(m.Incident).filter(m.Incident.zone_id == incident.zone_id).all() if incident.zone_id else [incident]
        disaster = interpret_risk(zone_id=incident.zone_id, zone_name=zone.name if zone else "Outside configured zones", risk=risk, incidents=nearby)
        _execution(db, "Disaster Risk Agent", incident.id, {"civic_handoff": civic, "assessment_id": assessment.id if assessment else None, "risk_engine_output": risk.model_dump(), "tools_allowed": ["read_calculated_risk", "read_zone_hazards", "explain_factors"], "tools_used": ["read_calculated_risk", "read_zone_hazards", "explain_factors"]}, disaster.model_dump(), disaster.summary)
        plan = _response_plan(incident, civic, disaster)
        # Validate at the final persistence boundary. This object has no dispatch tool.
        plan = ResponsePlan.model_validate(plan.model_dump())
        _execution(db, "Response Coordinator Agent", incident.id, {"civic_handoff": civic, "disaster_handoff": disaster.model_dump(), "tools_allowed": ["read_civic_analysis", "read_computed_risk", "propose_authority_action"], "tools_used": plan.tools_used}, plan.model_dump(), plan.action)
        db.add(m.Recommendation(incident_id=incident.id, agent="Response Coordinator Agent", action=plan.action, reason=plan.reason, priority=plan.priority, status="Pending"))
        db.flush()
    except (ValueError, RuntimeError) as exc:
        _execution(db, "Pipeline Orchestrator", incident.id, _incident_context(incident), {"human_review_required": True}, "Analysis pipeline failed; incident is preserved for manual review.", status="Failed", error=_safe_provider_error(exc))
    if initial_status in {"Submitted", "Under Analysis"}:
        incident.status = "Pending Review"
        db.flush()
    return incident

