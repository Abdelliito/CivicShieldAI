"""Focused numerical, validation, provider-boundary, and orchestration tests.

These unit tests use a temporary SQLite database only for isolation. The deployed
application and the API integration suite use the configured PostgreSQL database.
"""
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import intelligence as ai


@pytest.mark.parametrize("text,category,department", [
    ("There is a blocked drain full of rubbish", "Blocked drainage", "Water & Sanitation"),
    ("An open manhole at the junction", "Open manholes", "Water & Sanitation"),
    ("Fallen electric cable on the pavement", "Fallen electric cables", "Electricity & Streetlights"),
    ("Exposed electrical wiring outside a house", "Exposed electrical wiring", "Electricity & Streetlights"),
    ("A large pothole in the lane", "Potholes", "Roads & Infrastructure"),
    ("The broken road needs repair", "Broken roads", "Roads & Infrastructure"),
    ("Sewer overflow into the lane", "Sewer overflow", "Water & Sanitation"),
    ("Standing water remains on the street", "Water accumulation", "Water & Sanitation"),
    ("Leaking pipe under the pavement", "Water leakage", "Water & Sanitation"),
    ("Garbage accumulation in the alley", "Garbage accumulation", "Solid Waste Management"),
    ("A damaged streetlight in the lane", "Damaged streetlights", "Electricity & Streetlights"),
    ("The traffic signal is broken", "Damaged traffic signals", "Traffic Engineering"),
    ("The infrastructure needs assessment", "Other civic infrastructure hazards", "General Civic Services"),
    ("A storm drain is blocked behind the shops", "Blocked drainage", "Water & Sanitation"),
    ("The broken water main is leaking continuously", "Water leakage", "Water & Sanitation"),
])
def test_supported_categories_and_routing(text, category, department):
    result = ai.classify_text(text)
    assert result.category == category
    assert result.recommended_department == department
    assert result.image_analyzed is False
    assert result.confidence is None
    assert result.human_review_required is True


def test_severity_depends_on_context():
    routine = ai.classify_text("Garbage along a quiet empty lane")
    exposed = ai.classify_text("Garbage blocking the hospital entrance and busy road")
    critical = ai.classify_text("Exposed wire sparking with high voltage beside children")
    assert [r.severity for r in (routine, exposed, critical)] == ["Low", "High", "Critical"]


def test_image_is_not_claimed_analyzed_in_fallback():
    result = ai.classify_text("Blocked drainage in this street", has_image=True)
    assert result.method == "deterministic_text"
    assert not result.image_analyzed
    assert any("NOT been analyzed" in u for u in result.uncertainty)


def test_hazard_schema_rejects_false_image_and_confidence_claims():
    data = ai.classify_text("Blocked drain in the street").model_dump()
    for invalid in ({"image_analyzed": True}, {"confidence": 0.95}, {"category": "Earthquake"}, {"human_review_required": False}, {"assign_team_id": 1}):
        with pytest.raises(ValidationError):
            ai.HazardAnalysis.model_validate({**data, **invalid})


def make_incident(id=1, **extra):
    return SimpleNamespace(**{"id": id, "title": "Blocked drain by market", "description": "Drain blocked with garbage causing standing water", "category": "Blocked drainage", "severity": "High", "status": "Pending Review", "latitude": 31.52, "longitude": 74.35, "archived": False, "created_at": datetime.now(timezone.utc), "duplicate_of": None, "location_name": "Market junction", "reference": f"CS-{id}", **extra})


def test_duplicate_detection_combines_geo_time_category_and_text():
    original = make_incident()
    close = make_incident(2, latitude=31.5201)
    near_different_text = make_incident(3, latitude=31.5201, title="Drain", description="Entirely dissimilar descriptive tokens")
    far = make_incident(4, latitude=32.0)
    old = make_incident(5, created_at=ai.utcnow() - timedelta(days=10))
    different = make_incident(6, category="Potholes")
    archived = make_incident(7, archived=True)
    resolved = make_incident(8, status="Closed")
    matches = ai.duplicate_matches(original, [close, near_different_text, far, old, different, archived, resolved])
    assert {m.target_id for m in matches} == {2, 3}
    assert matches[0].score > matches[1].score
    assert 5 < matches[0].distance_m < 20


def test_risk_weather_change_without_citizen_report():
    clear = ai.calculate_risk(forecast_mm=0, recent_mm=0, historical_floods=0)
    heavy = ai.calculate_risk(forecast_mm=96, recent_mm=44, historical_floods=8)
    assert clear.score == 0 and clear.level == "Low"
    assert heavy.score > clear.score and heavy.level == "High"
    assert heavy.score == pytest.approx(66.4)
    assert "probability" in heavy.factors["limitations"][0]


def test_unresolved_drainage_contributes_and_nonflood_does_not():
    base = ai.calculate_risk(forecast_mm=20, recent_mm=10, historical_floods=1)
    blocked = ai.calculate_risk(forecast_mm=20, recent_mm=10, historical_floods=1, blocked_drains=3)
    assert blocked.score == pytest.approx(base.score + 22)
    assert "Open manholes" not in ai.FLOOD_CATEGORIES
    assert "Exposed electrical wiring" not in ai.FLOOD_CATEGORIES


@pytest.mark.parametrize("forecast,recent", [(None, None), (50, None), (None, 20)])
def test_missing_weather_never_fabricates_complete_score(forecast, recent):
    result = ai.calculate_risk(forecast_mm=forecast, recent_mm=recent, blocked_drains=20, historical_floods=10)
    assert result.score is None
    assert result.level == "Insufficient Data"
    assert result.factors["missing"]


def test_missing_history_is_disclosed():
    result = ai.calculate_risk(forecast_mm=5, recent_mm=0)
    assert result.score is not None
    assert "historical incident records" in result.factors["missing"]
    assert any("understate" in item for item in result.factors["limitations"])


def test_risk_config_is_validated_and_bounded():
    with pytest.raises(ValidationError):
        ai.RiskWeights(forecast=0.9)
    with pytest.raises(ValueError):
        ai.calculate_risk(forecast_mm=-2, recent_mm=0)
    with pytest.raises(ValueError):
        ai.calculate_risk(forecast_mm=float("nan"), recent_mm=0)
    result = ai.calculate_risk(forecast_mm=9999, recent_mm=9999, blocked_drains=100, water_incidents=100, historical_floods=100)
    assert result.score == 100


def test_risk_weights_are_configurable(monkeypatch):
    config = ai.RiskWeights().model_dump()
    config["forecast_saturation_mm"] = 120
    monkeypatch.setenv("RISK_WEIGHTS_JSON", json.dumps(config))
    result = ai.calculate_risk(forecast_mm=60, recent_mm=0, historical_floods=0)
    assert result.score == 21


def test_scenarios_are_explicitly_synthetic():
    for name in ("heavy_rain", "clear", "missing"):
        result = ai.scenario_weather(name)
        assert result["payload"]["synthetic"] is True
        assert "SYNTHETIC" in result["source"]
    with pytest.raises(ValueError):
        ai.scenario_weather("bogus")


def weather_response(now, missing=False):
    start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=30)
    times = [(start + timedelta(hours=i)).isoformat().replace("+00:00", "") for i in range(65)]
    rain = [1.0] * len(times)
    if missing:
        rain[20] = None
    return {"hourly": {"time": times, "precipitation": rain}, "hourly_units": {"precipitation": "mm"}}


def test_live_weather_parser_uses_two_complete_24h_windows():
    now = datetime(2026, 10, 16, 12, 31, tzinfo=timezone.utc)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=weather_response(now)))
    with httpx.Client(transport=transport) as client:
        result = ai.fetch_open_meteo(31.52, 74.35, client=client, now=now)
    assert result["recent_rain_mm"] == result["forecast_rain_mm"] == 24
    assert result["payload"]["synthetic"] is False
    assert "modeled" in result["source"]


def test_partial_weather_window_is_rejected():
    now = datetime(2026, 10, 16, 12, 31, tzinfo=timezone.utc)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=weather_response(now, missing=True)))
    with httpx.Client(transport=transport) as client, pytest.raises(ValueError, match="complete 24-hour"):
        ai.fetch_open_meteo(31.52, 74.35, client=client, now=now)


def test_vision_is_real_structured_server_request(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-key")
    monkeypatch.setenv("VISION_MODEL", "configured-vision-model")
    image = tmp_path / "hazard.png"
    from PIL import Image
    Image.new('RGB', (20, 20), '#5c7369').save(image, 'PNG')
    output = ai.classify_text("Blocked drain in a lane").model_dump()
    output.update(method="vision_model", image_analyzed=True, relevance="relevant", detected_title="Blocked drainage opening", summary="Photo evidence suggests a blocked drainage opening; verify on site.")
    requests = []
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"output": [{"content": [{"type": "output_text", "text": json.dumps(output)}]}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = ai.analyze_vision("Blocked drain", image, client=client)
    assert result.image_analyzed is True
    assert requests[0]["model"] == "configured-vision-model"
    assert requests[0]["store"] is False
    assert requests[0]["input"][0]["content"][1]["image_url"].startswith("data:image/png;base64,")
    assert "tools" not in requests[0]


def test_invalid_provider_output_is_retried_and_sanitized():
    calls = []
    def operation():
        calls.append(1)
        raise ValueError("sensitive provider content must not reach logs")
    output, attempts, errors = ai.bounded_retry(operation)
    assert output is None and attempts == 2 and len(calls) == 2
    assert all("sensitive" not in error for error in errors)


def test_response_plan_cannot_disable_approval():
    with pytest.raises(ValidationError):
        ai.ResponsePlan(incident_id=1, priority="High", department="Water", action="Review the blocked drain", reason="Reported obstruction before rainfall", approval_required=False, tools_used=[])


@pytest.fixture
def db():
    from app.db import Base
    from app import models as m
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        citizen = m.User(name="Unit Citizen", email="unit@example.test", password_hash="test-only", role="citizen")
        zone = m.Zone(name="Synthetic Test Zone", latitude=31.52, longitude=74.35, radius_km=2, historical_floods=8)
        department = m.Department(name="Water & Sanitation")
        session.add_all([citizen, zone, department])
        session.flush()
        incident = m.Incident(reference="TEST-1", title="Blocked drain near market", description="A blocked drain with garbage and standing water near a busy market", latitude=31.52, longitude=74.35, location_name="Market", citizen_id=citizen.id, status="Pending Review")
        session.add(incident)
        session.commit()
        yield session
    engine.dispose()


def test_pipeline_persists_all_agents_handoffs_and_does_not_assign(db, monkeypatch):
    from app import models as m
    from app.config import settings
    monkeypatch.setattr(settings, "demo_mode", True)
    ai.refresh_risk(db, scenario="heavy_rain")
    incident = db.query(m.Incident).first()
    original_status = incident.status
    ai.run_pipeline(db, incident)
    db.commit()
    db.expire_all()
    saved = db.get(m.Incident, incident.id)
    assert saved.category == "Blocked drainage"
    assert saved.status == original_status
    assert saved.team_id is None and db.query(m.Assignment).count() == 0
    executions = db.query(m.AgentExecution).filter(m.AgentExecution.incident_id == saved.id).all()
    assert {e.agent for e in executions} == {"Civic Intelligence Agent", "Disaster Risk Agent", "Response Coordinator Agent"}
    coordinator = next(e for e in executions if e.agent == "Response Coordinator Agent")
    assert coordinator.input_context["disaster_handoff"]["risk_score"] is not None
    assert coordinator.output["approval_required"] is True
    assert db.query(m.Recommendation).filter(m.Recommendation.incident_id == saved.id).first().status == "Pending"


def test_recalculation_appends_history_and_resolved_hazards_reduce_risk(db, monkeypatch):
    from app import models as m
    from app.config import settings
    monkeypatch.setattr(settings, "demo_mode", True)
    incident = db.query(m.Incident).first()
    ai.analyze_incident(db, incident)
    first = ai.refresh_risk(db, scenario="clear")[0]
    incident.status = "Closed"
    db.flush()
    second = ai.refresh_risk(db, fetch_live=False)[0]
    assert first.score > second.score
    assert db.query(m.RiskAssessment).count() == 2
    assert first.provenance["incident_ids"] == [incident.id]


def test_no_weather_produces_persisted_insufficient_assessment(db):
    result = ai.refresh_risk(db, fetch_live=False)[0]
    assert result.score is None and result.level == "Insufficient Data"
    assert result.provenance["weather"]["snapshot_id"] is None


def test_synthetic_scenarios_refused_outside_demo_mode(db, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "demo_mode", False)
    with pytest.raises(ValueError, match="DEMO_MODE"):
        ai.refresh_risk(db, scenario="heavy_rain")


def test_vision_failure_preserves_report_and_logs_fallback(db, monkeypatch):
    from app import models as m
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-key")
    incident = db.query(m.Incident).first()
    db.add(m.Attachment(incident_id=incident.id, user_id=incident.citizen_id, filename="missing.png", storage_name="missing.png", content_type="image/png", kind="report"))
    db.flush()
    result = ai.analyze_incident(db, incident)
    assert result["image_analyzed"] is False
    assert result["provider_errors"]
    execution = db.query(m.AgentExecution).filter(m.AgentExecution.incident_id == incident.id).first()
    # A missing local file must fail before any provider request is attempted.
    assert execution.status == "Fallback" and execution.attempts == 0


def test_report_location_edit_retires_stale_duplicate_candidate(db):
    from app import models as m
    original = db.query(m.Incident).first()
    ai.analyze_incident(db, original)
    other = m.Incident(reference="TEST-2", title=original.title, description=original.description, latitude=original.latitude + .00001, longitude=original.longitude, citizen_id=original.citizen_id, status="Pending Review")
    db.add(other)
    db.flush()
    ai.analyze_incident(db, other)
    candidate = db.query(m.DuplicateCandidate).filter(m.DuplicateCandidate.incident_id == other.id).first()
    assert candidate.status == "Pending"
    other.latitude = 32.0
    ai.analyze_incident(db, other)
    assert candidate.status == "Outdated"
    assert other.analysis["duplicate_candidates"] == []
    other.latitude = original.latitude + .00001
    ai.analyze_incident(db, other)
    assert candidate.status == "Pending"
    candidate.status = "Rejected"
    ai.analyze_incident(db, other)
    assert candidate.status == "Rejected"
