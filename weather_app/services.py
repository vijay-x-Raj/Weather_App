import requests
from datetime import datetime, date
from collections import defaultdict, Counter

# Geocoding still uses Open-Meteo (simple & free)
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
REVERSE_URL = "https://geocoding-api.open-meteo.com/v1/reverse"

# Switched weather provider to MET Norway Location Forecast API (no key required)
MET_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
HEADERS = {"User-Agent": "WeatherApp/1.0 (https://example.com)"}

def geocode(name: str):
    try:
        r = requests.get(GEOCODE_URL, params={"name": name, "count": 1, "language": "en", "format": "json"}, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        res = r.json().get('results') or []
        return res[0] if res else None
    except Exception:
        return None

def reverse_geocode(lat: float, lon: float):
    try:
        r = requests.get(REVERSE_URL, params={"latitude": lat, "longitude": lon, "count": 1, "language": "en", "format": "json"}, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return f"{lat:.2f},{lon:.2f}"
        res = r.json().get('results') or []
        if not res: return f"{lat:.2f},{lon:.2f}"
        p = res[0]
        parts = [p.get('name'), p.get('admin1'), p.get('country')]
        return ", ".join([x for x in parts if x])
    except Exception:
        return f"{lat:.2f},{lon:.2f}"

def _parse_iso(ts: str):
    try:
        return datetime.fromisoformat(ts.replace('Z','+00:00'))
    except Exception:
        return None

def fetch_weather(lat: float, lon: float, start=None, end=None):
    """Fetch weather from MET Norway and adapt to previous schema.
    For a date range, we filter hourly series and aggregate per-day.
    Without range we return current + next 5 days aggregated.
    """
    try:
        r = requests.get(MET_URL, params={"lat": lat, "lon": lon}, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        return {"error": str(e)}
    data = r.json()
    series = (data.get('properties') or {}).get('timeseries') or []
    if not series:
        return {}

    # Current = first entry
    first = series[0]
    inst = (first.get('data') or {}).get('instant', {}).get('details', {})
    # Try to get a symbol code from next hour block
    sym = None
    next_1 = (first.get('data') or {}).get('next_1_hours') or {}
    if 'summary' in next_1:
        sym = (next_1.get('summary') or {}).get('symbol_code')
    current = {
        'temperature_2m': inst.get('air_temperature'),
        'windspeed_10m': inst.get('wind_speed'),
        'relative_humidity_2m': inst.get('relative_humidity'),
        'weather_code': sym,
        'time': first.get('time')
    }

    # Determine target date window
    if start and end:
        try:
            start_d = date.fromisoformat(start)
            end_d = date.fromisoformat(end)
        except ValueError:
            start_d = end_d = None
    else:
        # Take today .. today+4 for 5 days
        now_d = _parse_iso(first.get('time')).date() if _parse_iso(first.get('time')) else date.today()
        start_d = now_d
        # 4 more days
        from datetime import timedelta
        end_d = now_d + timedelta(days=4)

    day_buckets = defaultdict(list)  # date -> list of hourly detail dicts + symbol
    symbol_counts = defaultdict(Counter)
    for entry in series:
        t_iso = entry.get('time')
        dt_obj = _parse_iso(t_iso)
        if not dt_obj:
            continue
        d_only = dt_obj.date()
        if start_d and end_d and (d_only < start_d or d_only > end_d):
            continue
        details = (entry.get('data') or {}).get('instant', {}).get('details', {})
        sym_local = None
        nx = (entry.get('data') or {}).get('next_1_hours') or {}
        if 'summary' in nx:
            sym_local = (nx.get('summary') or {}).get('symbol_code')
        day_buckets[d_only].append(details)
        if sym_local:
            symbol_counts[d_only][sym_local] += 1

    # Aggregate
    daily_dates = sorted(day_buckets.keys())
    temp_max = []
    temp_min = []
    wind_max = []
    weather_codes = []
    times_out = []
    for d in daily_dates:
        details_list = day_buckets[d]
        temps = [h.get('air_temperature') for h in details_list if isinstance(h.get('air_temperature'), (int,float))]
        winds = [h.get('wind_speed') for h in details_list if isinstance(h.get('wind_speed'), (int,float))]
        temp_max.append(max(temps) if temps else None)
        temp_min.append(min(temps) if temps else None)
        wind_max.append(max(winds) if winds else None)
        common_sym = symbol_counts[d].most_common(1)
        weather_codes.append(common_sym[0][0] if common_sym else None)
        times_out.append(d.isoformat())

    daily = {
        'time': times_out,
        'temperature_2m_max': temp_max,
        'temperature_2m_min': temp_min,
        'wind_speed_10m_max': wind_max,
        'weather_code': weather_codes,
    }

    return {
        'provider': 'met.no',
        'current': current,
        'daily': daily,
    }
