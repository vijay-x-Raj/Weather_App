# Weather App

Lightweight Django application that lets you:

* Search current weather for any place name or coordinates
* View a concise 5‑day daily summary (min/max temperature, max wind, symbol code)
* Automatically log every search (query text, resolved name, coords, temperature, symbol)
* Create and store custom date‑range weather snapshots (persisted JSON of the aggregated forecast)
* Review stored range records on their own detail pages

The focus is minimal code, fast startup, and zero external JS frameworks.

---
## Stack & Data Sources

| Layer | Choice | Notes |
|-------|--------|-------|
| Framework | Django 5 | ORM + templating + static serving (dev) |
| DB | SQLite | Default; file `db.sqlite3` |
| HTTP Client | `requests` | For external API calls |
| Geocoding | Open‑Meteo Geocoding API | Forward (name -> lat/lon) |
| Weather Forecast | MET Norway (Locationforecast) | Hourly timeseries aggregated into daily stats |
| Styling | Tailwind CSS CDN | Utility classes only |
| JS | Vanilla ES6 | `static/js/main.js` handles fetch + DOM updates |

---

## Features in Detail

### 1. Search (Current + 5‑Day Summary)
Endpoint: `/api/weather?q=<place>` or `/api/weather?lat=<lat>&lon=<lon>`
1. Forward geocode (if `q` provided) to lat/lon
2. Fetch MET Norway forecast JSON (hourly)
3. Aggregate next ~5 calendar days into arrays:
	* `dates[]`
	* `temperature_min[]` / `temperature_max[]`
	* `wind_speed_max[]`
	* `weather_code[]` (symbol strings like `clearsky_day`)
4. Return JSON; persist a `SimpleSearch` row (with latest temp + symbol).

### 2. Recent Searches
Endpoint: `/api/searches` returns last N (ordered newest first). Each links to a detail page showing the same aggregated forecast again (fresh fetch) plus stored meta.

### 3. Range Records
Create via form on the Ranges page (provides location + start/end dates). Backend stores:
* Original input & resolved name/coords
* Date span
* Snapshot of forecast JSON arrays at creation time (so later viewing is consistent)

Endpoints:
* `POST /api/records` – create
* `GET /api/records` – list
* `GET /records/<id>/` – HTML detail page
* `DELETE /api/records/<id>` – remove

### 4. Minimal Frontend
* No build step; Tailwind loaded from CDN in base template.
* `main.js` handles form submission, renders lists, and navigates to detail pages.

---
## Quick Start

### 1. Clone
```bash
git clone https://github.com/vijay-x-Raj/Weather_App.git
cd Weather_App
```

### 2. (Optional) Create Virtual Environment
```bash
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash / PowerShell use venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Migrations
```bash
python manage.py migrate
```

### 5. Start Dev Server
```bash
python manage.py runserver
```
Visit: http://127.0.0.1:8000/

---
## Usage Walkthrough

1. Open the home page – search form + recent searches + saved ranges appear.
2. Type a city (e.g., "Oslo") and submit – current + 5‑day summary loads, search logged.
3. Click a recent search entry to open its dedicated detail page.
4. Switch to Ranges page, enter a place + start/end (YYYY‑MM‑DD) to save a snapshot.
5. Open a range record detail page any time; data is the stored snapshot (does not re‑fetch).

### API Examples
```bash
curl 'http://127.0.0.1:8000/api/weather?q=Berlin'
curl 'http://127.0.0.1:8000/api/searches'
curl 'http://127.0.0.1:8000/api/records'
```

---
## Data Model Overview

`SimpleSearch`
* query_text, resolved_name
* latitude, longitude
* temperature (float)
* weather_code (symbol string)
* searched_at (auto timestamp)

`WeatherRecord`
* location_input, resolved_name
* latitude, longitude
* start_date, end_date
* weather_json (daily arrays snapshot)
* created_at / updated_at

---
## Design Notes / Rationale

* Keep dependencies minimal (Django + requests only) for easy deployment.
* Store range snapshots to ensure reproducibility even if provider changes or data shifts.
* Use provider’s symbol strings directly (no fragile numeric mapping layer).
* SQLite is enough for lightweight usage; can swap to Postgres by updating `DATABASES` in `settings.py`.

---
## Extending / Next Ideas

* Human‑friendly descriptions for `weather_code` (mapping table)
* Add simple caching layer to avoid duplicate rapid API calls
* Pagination on searches endpoint
* User accounts to keep personal history private
* Export a range record to CSV

---
## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| 500 on /api/weather after provider switch | DB schema expecting Integer for weather_code | Apply migration altering field to CharField |
| Empty results | Geocode failed | Try a more specific place name or include country |
| Wrong time window | Provider hourly horizon changed | Adjust aggregation logic in `services.py` |

Run with `--verbosity 2` for more migration detail: `python manage.py migrate --verbosity 2`.

---
## License

MIT (add a LICENSE file if publishing broadly).

---
## Attribution

* MET Norway Locationforecast API
* Open‑Meteo Geocoding API
* Tailwind CSS

---
## Security / Rate Limits

This app does not proxy or cache provider responses; heavy usage may hit provider rate limits. Consider adding caching (Redis) for production.

---
## Status

Actively developed minimal weather + range snapshot demo.

