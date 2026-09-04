# SafeRoute — Data Pipeline (replacing synthetic data with real public data)

The seed script (`db/seed.py`) gets you a running demo on day one. Before
your evaluation, replace it with the real, citable sources named in the
project plan. This doc gives the concrete steps.

## 1. Accident black spots / accident statistics

**Sources**
- MoRTH "Road Accidents in India" annual reports — morth.nic.in
- NCRB accidental death & crime statistics — ncrb.gov.in
- data.gov.in — search "road accidents" / "black spots"
- Your state transport department's dashboard, if published

**Pipeline**
1. Download the relevant PDF/CSV/XLS report for your target city/state.
2. Extract tabular data (use `pandas.read_csv` / `tabula-py` for PDFs).
3. Geocode location names to lat/lng — Nominatim (OpenStreetMap) is free:
   ```python
   import requests
   def geocode(place):
       r = requests.get("https://nominatim.openstreetmap.org/search",
                         params={"q": place, "format": "json", "limit": 1},
                         headers={"User-Agent": "SafeRoute-student-project"})
       results = r.json()
       return (float(results[0]["lat"]), float(results[0]["lon"])) if results else None
   ```
   ⚠️ Respect Nominatim's usage policy: max 1 request/second, and it's not
   meant for bulk geocoding — for larger batches, self-host Nominatim or
   use a local gazetteer of known black-spot locations if your source
   report already lists coordinates.
4. Insert into `risk_signals` with `type='accident_blackspot'`,
   `source='MoRTH-2023'` (or whichever report/year), and a `severity`
   derived from the report's own accident-count/fatality bucket (document
   your bucketing rule — e.g. severity 5 = top decile fatality count).
5. Write this as a repeatable script (`db/pipelines/accident_data.py`) —
   not a one-off notebook — so it's rerunnable and demonstrates the "Data
   Pipeline" component from the architecture section of the project plan.

## 2. Road/bridge damage images (for AI training — see `ai_service/app/train.py`)

- RDD2022 / CRDDC dataset (GitHub/Zenodo release)
- SDNET2018 (concrete crack images)
- Your own 150–300 local photos — spread collection across the semester,
  hold out 20% from day one as a never-trained-on test set

## 3. Personal safety layer

- **Crowd reports**: already live via `POST /api/crowd-reports` — the more
  your team and testers use it, the better this layer looks in your demo.
- **OSM POI density** (footfall proxy): query the Overpass API for shops/
  transit/markets near a region, insert as `type='poi_density'`.
  ```
  https://overpass-api.de/api/interpreter
  ```
- **Street lighting**: sample a handful of segments with the Google Street
  View Static API free tier, manually or semi-automatically label visible
  lighting, insert as `type='lighting'`. Do not scrape at scale.
- **NCRB / state police aggregate crime dashboards**: area-level,
  anonymised statistics only. Never attempt to source FIR/General Diary
  level data — this is explicitly out of scope (see project plan Section 4.3).

## 4. Keeping synthetic and real data distinguishable

Always set a specific `source` value (`'MoRTH-2023'`, `'RDD2022'`,
`'crowd'`, `'yolov8-roaddamage-v1'`, etc.) — never leave real data as
`'synthetic_seed'`, and consider deleting/deactivating (`is_active=false`)
synthetic rows once real data covers the same area, so your dashboard and
demo reflect genuine coverage. Document, in your final report, exactly
which `source` values are real vs. illustrative — this transparency is
itself part of your evaluation credibility (project plan Section 10).
