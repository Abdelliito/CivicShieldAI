"""Controlled scheduler tests; real PostgreSQL engine, no provider network call."""
import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select


def test_scheduled_refresh_persists_weather_and_risk_without_new_reports(client, monkeypatch):
    from app import intelligence as ai, main
    from app.db import SessionLocal
    from app.models import Incident, RiskAssessment, Zone

    with SessionLocal() as db:
        before = ai.refresh_risk(db, scenario='clear')
        db.commit()
        scores = {row.zone_id: row.score for row in before}
        prior_ids = {row.id for row in before}
        incident_count = db.scalar(select(func.count()).select_from(Incident))

    calls = []
    def controlled_weather(latitude, longitude):
        calls.append((latitude, longitude))
        return {'forecast_rain_mm': 96.0, 'recent_rain_mm': 44.0, 'source': 'CONTROLLED TEST PROVIDER — not live weather', 'payload': {'synthetic': True, 'test_only': True, 'forecast_window_hours': 24, 'recent_window_hours': 24}, 'error': None}
    monkeypatch.setattr(ai, 'fetch_open_meteo', controlled_weather)
    main.scheduled_refresh()

    with SessionLocal() as db:
        active_zones = db.scalars(select(Zone).where(Zone.active.is_(True))).all()
        assert len(calls) == len(active_zones)
        assert db.scalar(select(func.count()).select_from(Incident)) == incident_count
        for zone in active_zones:
            latest = db.scalar(select(RiskAssessment).where(RiskAssessment.zone_id == zone.id).order_by(RiskAssessment.id.desc()).limit(1))
            assert latest.id not in prior_ids
            assert latest.score > scores[zone.id]
            assert latest.provenance['trigger'] == 'live_weather_refresh'
            assert latest.provenance['weather']['source'] == 'CONTROLLED TEST PROVIDER — not live weather'


def test_scheduler_uses_configured_interval_and_dispatches_refresh(monkeypatch):
    from app import main
    sleeps, calls = [], []
    async def controlled_sleep(seconds):
        if sleeps:
            raise asyncio.CancelledError
        sleeps.append(seconds)
    def refresh():
        calls.append('scheduled_refresh')
    async def threadpool(function):
        assert function is refresh
        function()
    # Replace only main's asyncio reference, never the process-wide event loop API.
    monkeypatch.setattr(main, 'asyncio', SimpleNamespace(sleep=controlled_sleep, CancelledError=asyncio.CancelledError, create_task=asyncio.create_task))
    monkeypatch.setattr(main, 'run_in_threadpool', threadpool)
    monkeypatch.setattr(main, 'scheduled_refresh', refresh)
    monkeypatch.setattr(main.settings, 'weather_refresh_minutes', 7)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(main.weather_scheduler())
    assert sleeps == [420]
    assert calls == ['scheduled_refresh']


def test_risk_history_keeps_zone_geometry_after_administrative_edit(client):
    from app import intelligence as ai, main
    from app.db import SessionLocal
    from app.models import Zone
    with SessionLocal() as db:
        zone = db.scalar(select(Zone).where(Zone.active.is_(True)).order_by(Zone.id))
        first = next(a for a in ai.refresh_risk(db, scenario='clear') if a.zone_id == zone.id)
        expected = {'name': zone.name, 'latitude': zone.latitude, 'longitude': zone.longitude, 'radius_km': zone.radius_km}
        zone.latitude += .01
        zone.radius_km += .25
        zone.name += ' temporary audit edit'
        # No commit: this isolated mutation is rolled back when the session exits.
        db.flush()
        saved = main.risk_dump(db, first)
        assert first.provenance['zone_geometry'] == expected
        assert saved['zone_name'] == expected['name']
        assert saved['latitude'] == expected['latitude']
        assert saved['radius_km'] == expected['radius_km']
