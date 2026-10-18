"""Live weather and understandable, explicitly non-official planning estimates."""
import copy
import math
import threading
import time
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .intelligence import FLOOD_CATEGORIES, TERMINAL_STATUSES, calculate_risk, distance_m
from .models import Incident, User, Zone
from .security import current_user

router = APIRouter(prefix='/api/citizen', tags=['Citizen weather and safety'])
_cache = {}
_cache_lock = threading.Lock()
_TTL = 600
UNITS = {'temperature': '°C', 'humidity': '%', 'wind_speed': 'km/h', 'precipitation': 'mm'}


def condition(code):
    if code == 0:
        return 'Clear sky'
    if code in (1, 2, 3):
        return {1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast'}[code]
    if code in (45, 48):
        return 'Fog'
    if code in (51, 53, 55, 56, 57):
        return 'Drizzle'
    if code in (61, 63, 65, 66, 67):
        return 'Rain'
    if code in (71, 73, 75, 77, 85, 86):
        return 'Snow'
    if code in (80, 81, 82):
        return 'Rain showers'
    if code in (95, 96, 99):
        return 'Thunderstorm'
    return 'Condition unavailable'


def number(value, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError('Weather value missing or invalid')
    if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        raise ValueError('Weather value outside supported range')
    return value


def normalize_weather(raw):
    current = raw['current']
    daily = raw['daily']
    dates = daily['time'][:7]
    if len(dates) != 7 or len(set(dates)) != 7:
        raise ValueError('A complete seven-day forecast is unavailable')
    days = []
    for index, day in enumerate(dates):
        datetime.strptime(day, '%Y-%m-%d')
        code = number(daily['weather_code'][index], 0, 99)
        days.append({
            'date': day,
            'temperature_max': number(daily['temperature_2m_max'][index], -100, 70),
            'temperature_min': number(daily['temperature_2m_min'][index], -100, 70),
            'rain_probability': number(daily['precipitation_probability_max'][index], 0, 100),
            'precipitation_mm': number(daily['precipitation_sum'][index], 0),
            'wind_speed_max': number(daily['wind_speed_10m_max'][index], 0),
            'weather_code': code, 'condition': condition(code),
        })
    code = number(current['weather_code'], 0, 99)
    # Hourly rain is optional: weather remains useful if rainfall history is
    # unavailable, but the risk engine then explicitly declines a complete score.
    rain = {'recent_mm': None, 'forecast_mm': None}
    try:
        anchor = datetime.fromisoformat(current['time']).replace(minute=0, second=0, microsecond=0)
        samples = [(datetime.fromisoformat(t), number(v, 0)) for t, v in
                   zip(raw['hourly']['time'], raw['hourly']['precipitation'], strict=True)]
        recent = [v for t, v in samples if anchor - timedelta(hours=24) <= t < anchor]
        forecast = [v for t, v in samples if anchor <= t < anchor + timedelta(hours=24)]
        rain = {'recent_mm': round(sum(recent), 2) if len(recent) == 24 else None,
                'forecast_mm': round(sum(forecast), 2) if len(forecast) == 24 else None}
    except (KeyError, TypeError, ValueError):
        pass
    return {
        'current': {
            'temperature_2m': number(current['temperature_2m'], -100, 70),
            'relative_humidity_2m': number(current['relative_humidity_2m'], 0, 100),
            'wind_speed_10m': number(current['wind_speed_10m'], 0),
            'weather_code': code, 'condition': condition(code), 'time': current['time'],
        },
        'daily': days, 'units': UNITS, 'source': 'Open-Meteo',
        'updated_at': datetime.now(timezone.utc).isoformat(), 'available': True,
        'synthetic': False, 'timezone': raw.get('timezone', 'UTC'),
        'message': 'Live model-based weather forecast. Forecasts can change.', '_rainfall': rain,
    }


def fetch_weather(latitude, longitude):
    key = (round(latitude, 4), round(longitude, 4))
    # Single flight prevents dashboard weather and safety requests duplicating
    # the same upstream call; failures are cached briefly, never invented.
    with _cache_lock:
        cached = _cache.get(key)
        if cached and time.monotonic() - cached[0] < (600 if cached[1]['available'] else 30):
            return copy.deepcopy(cached[1])
        try:
            response = httpx.get('https://api.open-meteo.com/v1/forecast', params={
                'latitude': latitude, 'longitude': longitude, 'timezone': 'auto',
                'current': 'temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m',
                'daily': 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,wind_speed_10m_max',
                'hourly': 'precipitation', 'past_days': 1, 'forecast_days': 7,
            }, timeout=12, follow_redirects=False)
            response.raise_for_status()
            raw = response.json()
            # past_days also extends the daily arrays. Keep the seven forecast
            # dates beginning with the provider's local current date.
            today = raw['current']['time'][:10]
            start = raw['daily']['time'].index(today)
            raw['daily'] = {k: v[start:start + 7] for k, v in raw['daily'].items()}
            payload = normalize_weather(raw)
        except (httpx.HTTPError, KeyError, ValueError, TypeError, IndexError):
            payload = {'available': False, 'current': None, 'daily': [], 'units': UNITS,
                       'source': 'Open-Meteo', 'synthetic': False, 'updated_at': None,
                       'timezone': None, 'message': 'Weather is unavailable. Check the internet connection and try again shortly.',
                       '_rainfall': {'recent_mm': None, 'forecast_mm': None}}
        if len(_cache) >= 256:
            _cache.pop(next(iter(_cache)))
        _cache[key] = (time.monotonic(), payload)
        return copy.deepcopy(payload)


def selected_location(db, user, latitude, longitude):
    if (latitude is None) != (longitude is None):
        raise HTTPException(422, 'Provide both latitude and longitude.')
    if latitude is not None:
        return latitude, longitude, 'Selected location'
    own = db.scalar(select(Incident).where(Incident.citizen_id == user.id,
                                         Incident.archived.is_(False)).order_by(Incident.created_at.desc()))
    if own:
        return own.latitude, own.longitude, own.location_name or 'Your latest report location'
    return 31.5204, 74.3587, 'Lahore city centre (default; choose your location)'


def public_weather(latitude, longitude, label):
    payload = fetch_weather(latitude, longitude)
    payload.pop('_rainfall', None)
    return {**payload, 'latitude': latitude, 'longitude': longitude, 'location_label': label}


@router.get('/weather')
def weather(latitude: float | None = Query(None, ge=-90, le=90),
            longitude: float | None = Query(None, ge=-180, le=180),
            db: Session = Depends(get_db), user: User = Depends(current_user)):
    return public_weather(*selected_location(db, user, latitude, longitude))


def weather_precautions(weather):
    if not weather['available']:
        return []
    days = weather['daily'][:2]
    entries = []
    rules = [
        ('Heavy rain', any(d['precipitation_mm'] >= 20 for d in days),
         'Heavy rainfall is forecast in the next two days.',
         ['Avoid flooded roads and underpasses.', 'Keep away from open drains and electrical equipment in water.']),
        ('Heat', any(d['temperature_max'] >= 38 for d in days),
         'High temperatures are forecast in the next two days.',
         ['Carry drinking water and seek shade.', 'Check on children, older neighbours and outdoor workers.']),
        ('Wind', any(d['wind_speed_max'] >= 40 for d in days),
         'Strong winds are forecast in the next two days.',
         ['Secure loose outdoor objects.', 'Keep clear of damaged trees and electrical wires.']),
    ]
    for kind, present, summary, actions in rules:
        if present:
            entries.append({'type': kind, 'level': 'Precaution', 'summary': summary,
                            'precautions': actions, 'valid_until': days[-1]['date'],
                            'source': 'Open-Meteo forecast + CivicShield precaution rules', 'official': False})
    return entries


@router.get('/alerts')
def alerts(latitude: float | None = Query(None, ge=-90, le=90),
           longitude: float | None = Query(None, ge=-180, le=180),
           db: Session = Depends(get_db), user: User = Depends(current_user)):
    lat, lon, label = selected_location(db, user, latitude, longitude)
    live = fetch_weather(lat, lon)
    now = datetime.now(timezone.utc)
    zones = db.scalars(select(Zone).where(Zone.active.is_(True))).all()
    covering = [z for z in zones if distance_m(lat, lon, z.latitude, z.longitude) <= z.radius_km * 1000]
    zone = min(covering, key=lambda z: distance_m(lat, lon, z.latitude, z.longitude)) if covering else None
    risks = []
    if zone:
        # Publish aggregate evidence only. Citizen names, descriptions, IDs and
        # photographs from other people's reports never leave this endpoint.
        incidents = db.scalars(select(Incident).where(Incident.archived.is_(False),
            Incident.duplicate_of.is_(None), Incident.status.not_in(TERMINAL_STATUSES),
            Incident.category.in_(FLOOD_CATEGORIES))).all()
        local = [i for i in incidents if distance_m(i.latitude, i.longitude, zone.latitude, zone.longitude) <= zone.radius_km * 1000]
        rainfall = live['_rainfall']
        result = calculate_risk(**rainfall,
            blocked_drains=sum(i.category == 'Blocked drainage' for i in local),
            water_incidents=sum(i.category != 'Blocked drainage' for i in local),
            historical_floods=zone.historical_floods,
            provenance={'weather_source': live['source'], 'weather_updated_at': live['updated_at'],
                        'history_source': 'Synthetic demo records' if settings.demo_mode else 'Administrator-entered historical count',
                        'synthetic_local_records': settings.demo_mode})
        summary = {
            'Low': 'Current evidence suggests a low waterlogging planning score. Local flooding can still occur.',
            'Moderate': 'Rain and local drainage reports suggest increased waterlogging concerns.',
            'High': 'Rain and local drainage reports suggest elevated waterlogging concerns. Plan safer routes.',
            'Insufficient Data': 'There is not enough recent rainfall data to estimate local waterlogging risk.',
        }[result.level]
        risks.append({'id': f'waterlogging-{zone.id}', 'type': 'Flooding / waterlogging',
            'level': result.level, 'summary': summary,
            'precautions': ['Avoid standing water and open manholes.', 'Report blocked drains; use an alternative route when a road is flooded.'],
            'issued_at': now.isoformat(), 'valid_until': (now + timedelta(hours=1)).isoformat(),
            'source': 'CivicShield weighted planning estimate using live Open-Meteo rainfall and local records',
            'is_demo': settings.demo_mode, 'official': False,
            'details': {'score': result.score, 'factors': result.factors, 'provenance': result.provenance}})
    return {'latitude': lat, 'longitude': lon,
        'area': {'id': zone.id if zone else None, 'name': zone.name if zone else label, 'within_supported_zone': bool(zone)},
        'issued_at': now.isoformat(), 'official_alerts': [], 'official_alerts_available': False,
        'official_alerts_message': 'No official warning feed is connected. Check local emergency authorities for official warnings.',
        'risks': risks, 'weather_precautions': weather_precautions(live),
        'message': 'Planning estimates are not official warnings or calibrated flood probabilities.' +
                   (' Local reports and history include synthetic demonstration data.' if settings.demo_mode else '') +
                   (' This location is outside configured local planning zones.' if not zone else '')}
