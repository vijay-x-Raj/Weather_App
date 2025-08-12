from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date
from django.db import transaction
import json
from .models import WeatherRecord, SimpleSearch
from .services import geocode, reverse_geocode, fetch_weather


def index(request):
    return render(request, 'weather_app/index.html')

def record_page(request, pk):
    rec = get_object_or_404(WeatherRecord, pk=pk)
    data = rec.weather_json or {}
    daily = data.get('daily') or {}
    days = []
    times = daily.get('time') or []
    tmax = daily.get('temperature_2m_max') or []
    tmin = daily.get('temperature_2m_min') or []
    wind = daily.get('wind_speed_10m_max') or []
    codes = daily.get('weather_code') or []
    for i, d in enumerate(times):
        days.append({
            'date': d,
            't_max': tmax[i] if i < len(tmax) else None,
            't_min': tmin[i] if i < len(tmin) else None,
            'wind': wind[i] if i < len(wind) else None,
            'code': codes[i] if i < len(codes) else None,
        })
    context = {
        'record': rec,
        'days': days,
    }
    return render(request, 'weather_app/record_detail.html', context)

def search_page(request, pk):
    s = get_object_or_404(SimpleSearch, pk=pk)
    # Always fetch fresh weather so page shows current + forecast
    weather = fetch_weather(s.latitude, s.longitude)
    current = weather.get('current') or {}
    daily = weather.get('daily') or {}
    # Build first 7 day list
    days = []
    times = (daily.get('time') or [])[:7]
    tmax = daily.get('temperature_2m_max') or []
    tmin = daily.get('temperature_2m_min') or []
    wind = daily.get('wind_speed_10m_max') or []
    codes = daily.get('weather_code') or []
    for i, d in enumerate(times):
        days.append({
            'date': d,
            't_max': tmax[i] if i < len(tmax) else None,
            't_min': tmin[i] if i < len(tmin) else None,
            'wind': wind[i] if i < len(wind) else None,
            'code': codes[i] if i < len(codes) else None,
        })
    return render(request, 'weather_app/search_detail.html', {
        'search': s,
        'current': current,
        'days': days,
    })


def ranges_page(request):
    """HTML view providing a simple form to create a range record and showing its weather immediately.
    GET: show form + existing records list.
    POST: validate, create record (if valid & location found) then show its per-day weather.
    """
    message = None
    created_record = None
    days = []
    if request.method == 'POST':
        loc = (request.POST.get('location') or '').strip()
        start = request.POST.get('start_date')
        end = request.POST.get('end_date')
        if not loc or not start or not end:
            message = 'All fields required.'
        else:
            try:
                _validate_range(start, end)
                geo = geocode(loc)
                if not geo:
                    message = 'Location not found.'
                else:
                    lat_f = geo['latitude']; lon_f = geo['longitude']
                    data = fetch_weather(lat_f, lon_f, start, end)
                    created_record = WeatherRecord.objects.create(
                        location_input=loc,
                        resolved_name=geo.get('name') or loc,
                        latitude=lat_f,
                        longitude=lon_f,
                        start_date=start,
                        end_date=end,
                        weather_json=data
                    )
                    daily = data.get('daily') or {}
                    times = daily.get('time') or []
                    for i, d in enumerate(times):
                        days.append({
                            'date': d,
                            't_max': (daily.get('temperature_2m_max') or [None])[i] if i < len(daily.get('temperature_2m_max') or []) else None,
                            't_min': (daily.get('temperature_2m_min') or [None])[i] if i < len(daily.get('temperature_2m_min') or []) else None,
                            'wind': (daily.get('wind_speed_10m_max') or [None])[i] if i < len(daily.get('wind_speed_10m_max') or []) else None,
                            'code': (daily.get('weather_code') or [None])[i] if i < len(daily.get('weather_code') or []) else None,
                        })
                    message = 'Created.'
            except ValueError as e:
                message = str(e)
            except Exception:
                message = 'Unexpected error.'
    records = WeatherRecord.objects.order_by('-created_at')[:20]
    return render(request, 'weather_app/ranges.html', {
        'records': records,
        'created_record': created_record,
        'days': days,
        'message': message,
    })


def _validate_range(start_s, end_s):
    ds = parse_date(start_s)
    de = parse_date(end_s)
    if not ds or not de:
        raise ValueError('Bad date format (YYYY-MM-DD)')
    if ds > de:
        raise ValueError('start_date after end_date')
    if (de - ds).days > 30:
        raise ValueError('Range too large (max 31 days)')
    return ds, de


def api_weather(request):
    q = request.GET.get('q')
    lat = request.GET.get('lat')
    lon = request.GET.get('lon') or request.GET.get('lng')
    if lat and lon:
        try:
            lat_f = float(lat); lon_f = float(lon)
        except ValueError:
            return HttpResponseBadRequest('invalid coordinates')
        name = reverse_geocode(lat_f, lon_f)
        data = fetch_weather(lat_f, lon_f)
        current = data.get('current', {})
        SimpleSearch.objects.create(
            query_text=f"{lat_f},{lon_f}", resolved_name=name, latitude=lat_f, longitude=lon_f,
            temperature=current.get('temperature_2m'), weather_code=current.get('weather_code')
        )
        return JsonResponse({
            'location': name,
            'latitude': lat_f,
            'longitude': lon_f,
            'current': data.get('current'),
            'daily': data.get('daily')
        })
    if not q:
        return HttpResponseBadRequest('missing q or lat/lon')
    geo = geocode(q)
    if not geo:
        return JsonResponse({'error': 'Location not found'}, status=404)
    lat_f = geo['latitude']; lon_f = geo['longitude']; name = geo.get('name') or q
    data = fetch_weather(lat_f, lon_f)
    current = data.get('current', {})
    SimpleSearch.objects.create(
        query_text=q, resolved_name=name, latitude=lat_f, longitude=lon_f,
        temperature=current.get('temperature_2m'), weather_code=current.get('weather_code')
    )
    return JsonResponse({
        'location': name,
        'latitude': lat_f,
        'longitude': lon_f,
        'current': data.get('current'),
        'daily': data.get('daily')
    })


@csrf_exempt
def records(request):
    if request.method == 'GET':
        out = list(WeatherRecord.objects.values('id','location_input','resolved_name','start_date','end_date','created_at'))
        return JsonResponse(out, safe=False)
    if request.method == 'POST':
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return HttpResponseBadRequest('invalid json')
        loc = (payload.get('location') or '').strip()
        start = payload.get('start_date'); end = payload.get('end_date')
        if not loc or not start or not end:
            return HttpResponseBadRequest('location, start_date, end_date required')
        try:
            _validate_range(start, end)
        except ValueError as e:
            return HttpResponseBadRequest(str(e))
        geo = geocode(loc)
        if not geo:
            return JsonResponse({'error': 'Location not found'}, status=404)
        lat_f = geo['latitude']; lon_f = geo['longitude']
        data = fetch_weather(lat_f, lon_f, start, end)
    rec = WeatherRecord.objects.create(
            location_input=loc,
            resolved_name=geo.get('name') or loc,
            latitude=lat_f,
            longitude=lon_f,
            start_date=start,
            end_date=end,
            weather_json=data
        )
    return JsonResponse({'id': rec.id, 'location': rec.resolved_name, 'start_date': start, 'end_date': end, 'data': data}, status=201)
    return HttpResponseBadRequest('method not allowed')


@csrf_exempt
def record_detail(request, pk):
    rec = get_object_or_404(WeatherRecord, pk=pk)
    if request.method == 'GET':
        # derive daily_list for convenience
        data = rec.weather_json or {}
        daily = data.get('daily') or {}
        times = daily.get('time') or []
        daily_list = []
        for i, d in enumerate(times):
            daily_list.append({
                'date': d,
                't_max': (daily.get('temperature_2m_max') or [None])[i] if i < len(daily.get('temperature_2m_max') or []) else None,
                't_min': (daily.get('temperature_2m_min') or [None])[i] if i < len(daily.get('temperature_2m_min') or []) else None,
                'wind': (daily.get('wind_speed_10m_max') or [None])[i] if i < len(daily.get('wind_speed_10m_max') or []) else None,
                'weather_code': (daily.get('weather_code') or [None])[i] if i < len(daily.get('weather_code') or []) else None,
            })
        return JsonResponse({
            'id': rec.id,
            'location_input': rec.location_input,
            'resolved_name': rec.resolved_name,
            'start_date': rec.start_date,
            'end_date': rec.end_date,
            'weather_json': rec.weather_json,
            'daily_list': daily_list,
            'updated_at': rec.updated_at,
        })
    if request.method == 'DELETE':
        rec.delete(); return JsonResponse({'status': 'deleted'})
    if request.method == 'PUT':
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return HttpResponseBadRequest('invalid json')
        loc = (payload.get('location') or rec.location_input).strip()
        start = payload.get('start_date') or str(rec.start_date)
        end = payload.get('end_date') or str(rec.end_date)
        try:
            _validate_range(start, end)
        except ValueError as e:
            return HttpResponseBadRequest(str(e))
        geo = geocode(loc)
        if not geo:
            return JsonResponse({'error':'Location not found'}, status=404)
        lat_f = geo['latitude']; lon_f = geo['longitude']
        data = fetch_weather(lat_f, lon_f, start, end)
        with transaction.atomic():
            rec.location_input = loc
            rec.resolved_name = geo.get('name') or loc
            rec.latitude = lat_f
            rec.longitude = lon_f
            rec.start_date = start
            rec.end_date = end
            rec.weather_json = data
            rec.save()
        return JsonResponse({'id': rec.id, 'location': rec.resolved_name, 'data': data})
    return HttpResponseBadRequest('method not allowed')


def searches(request):
    limit = min(int(request.GET.get('limit', 15)), 100)
    qs = SimpleSearch.objects.all()[:limit]
    out = [
        {
            'id': s.id,
            'query': s.resolved_name,
            'latitude': s.latitude,
            'longitude': s.longitude,
            'temperature': s.temperature,
            'weather_code': s.weather_code,
            'searched_at': s.searched_at,
        } for s in qs
    ]
    return JsonResponse(out, safe=False)


@csrf_exempt
def delete_search(request, pk):
    if request.method != 'DELETE':
        return HttpResponseBadRequest('method not allowed')
    try:
        s = SimpleSearch.objects.get(pk=pk)
    except SimpleSearch.DoesNotExist:
        return JsonResponse({'error': 'not found'}, status=404)
    s.delete(); return JsonResponse({'status': 'deleted'})
