from datetime import datetime, timedelta

import httpx
import pytest

from app import citizen_weather as weather


def payload():
    anchor = datetime(2026, 10, 19, 12)
    dates = [(anchor + timedelta(days=d)).date().isoformat() for d in range(7)]
    return {'timezone': 'Asia/Karachi',
        'current': {'time': anchor.isoformat(), 'temperature_2m': 28.2,
                    'relative_humidity_2m': 72, 'weather_code': 3, 'wind_speed_10m': 12},
        'daily': {'time': dates, 'weather_code': [3] * 7,
                  'temperature_2m_max': [32] * 7, 'temperature_2m_min': [22] * 7,
                  'precipitation_probability_max': [60] * 7, 'precipitation_sum': [24] * 7,
                  'wind_speed_10m_max': [20] * 7},
        'hourly': {'time': [(anchor + timedelta(hours=h)).isoformat() for h in range(-24, 24)],
                   'precipitation': [1] * 48}}


def test_complete_weather_and_true_rain_windows():
    result = weather.normalize_weather(payload())
    assert len(result['daily']) == 7
    assert result['current']['condition'] == 'Overcast'
    assert result['_rainfall'] == {'recent_mm': 24, 'forecast_mm': 24}
    assert result['synthetic'] is False
    assert weather.weather_precautions(result)[0]['official'] is False


@pytest.mark.parametrize('field,value', [('relative_humidity_2m', 120), ('temperature_2m', None), ('wind_speed_10m', float('nan'))])
def test_invalid_current_never_looks_like_live_data(field, value):
    raw = payload()
    raw['current'][field] = value
    with pytest.raises(ValueError):
        weather.normalize_weather(raw)


def test_partial_rain_does_not_create_complete_score():
    raw = payload()
    raw['hourly']['time'].pop()
    raw['hourly']['precipitation'].pop()
    result = weather.normalize_weather(raw)
    assert result['available']
    assert result['_rainfall']['forecast_mm'] is None


def test_outage_never_fabricates_weather(monkeypatch):
    weather._cache.clear()
    def fail(*args, **kwargs):
        raise httpx.ConnectError('private network details')
    monkeypatch.setattr(weather.httpx, 'get', fail)
    result = weather.public_weather(0, 0, 'Test location')
    assert not result['available'] and result['current'] is None and result['daily'] == []
    assert 'private' not in result['message']
    assert '_rainfall' not in result
    weather._cache.clear()


def test_weather_routes_auth_coverage_and_privacy(client, roles, monkeypatch):
    monkeypatch.setattr(weather, 'fetch_weather', lambda *args: weather.normalize_weather(payload()))
    assert client.get('/api/citizen/weather').status_code == 401
    assert client.get('/api/citizen/weather?latitude=999&longitude=1', headers=roles['citizen']).status_code == 422
    assert client.get('/api/citizen/weather?latitude=31', headers=roles['citizen']).status_code == 422
    result = client.get('/api/citizen/weather?latitude=31.52&longitude=74.35', headers=roles['citizen']).json()
    assert len(result['daily']) == 7 and '_rainfall' not in result
    estimate = client.get('/api/citizen/alerts?latitude=31.52&longitude=74.35', headers=roles['citizen']).json()
    assert estimate['area']['within_supported_zone']
    assert estimate['risks'][0]['details']['score'] is not None
    assert estimate['risks'][0]['is_demo'] and not estimate['risks'][0]['official']
    assert 'incident_ids' not in str(estimate)
    assert 'citizen_id' not in str(estimate)
    outside = client.get('/api/citizen/alerts?latitude=0&longitude=0', headers=roles['citizen']).json()
    assert outside['risks'] == [] and not outside['official_alerts_available']
    assert not outside['area']['within_supported_zone']
