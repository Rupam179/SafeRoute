# SafeRoute — API Reference

Base URL (local): `http://localhost:8000`
Interactive docs (auto-generated): `http://localhost:8000/docs`

All request/response bodies are JSON unless noted.

---

## `POST /api/routes`

Find and risk-rank routes between two points.

**Request**
```json
{
  "origin_lat": 22.5726,
  "origin_lng": 88.3639,
  "destination_lat": 22.5958,
  "destination_lng": 88.4497,
  "origin_label": "Howrah",
  "destination_label": "Salt Lake",
  "departure_hour": 21
}
```
`departure_hour` is optional (0-23); server time is used if omitted.

**Response**
```json
{
  "query_id": 17,
  "routes": [
    {
      "label": "fastest",
      "distance_km": 10.2,
      "duration_min": 25.4,
      "risk": {
        "road_damage_score": 62.0,
        "accident_score": 71.5,
        "safety_score": 40.0,
        "time_of_day_score": 55.0,
        "composite_risk": 60.8,
        "signal_counts": {
          "road_damage": 4, "accident_blackspot": 3,
          "crowd_safety_report": 1, "lighting": 2
        }
      },
      "geometry": "encoded_polyline6_string",
      "blackspot_count": 3,
      "damage_count": 4
    },
    { "label": "balanced", "...": "..." },
    { "label": "safest", "...": "..." }
  ],
  "comparison_note": "Safest route is 14% longer but has 38% lower risk than the fastest route."
}
```

`geometry` is an encoded polyline (precision 6) — decode client-side with
the `polyline` npm package (already wired up in `MapView.jsx`).

---

## `GET /api/risk-signals`

Returns risk-signal points for map layers.

**Query params**
- `type` (optional): `accident_blackspot` | `road_damage` | `crowd_safety_report` | `lighting` | `crime_stat` | `poi_density`
- `bbox` (optional): `min_lng,min_lat,max_lng,max_lat` — restrict to viewport
- `limit` (default 2000, max 10000)

**Response**: array of
```json
{ "id": 1, "lat": 22.57, "lng": 88.36, "type": "road_damage",
  "severity": 3, "source": "synthetic_seed", "meta": {}, "time_of_day": null }
```

---

## `POST /api/crowd-reports`

Submit an anonymous safety observation. Immediately promoted into
`risk_signals` and used by the next route-scoring call.

**Request**
```json
{
  "lat": 22.58, "lng": 88.40,
  "lighting": "poor",
  "activity_level": "low",
  "incident_report": false,
  "notes": "Streetlights out on this stretch",
  "reported_at_hour": 22
}
```

**Response**: the created report with `id` and `created_at`.

## `GET /api/crowd-reports`

Lists recent reports (default limit 500), newest first.

---

## `POST /api/damage-detection`

`multipart/form-data`: `file` (image), `lat` (float), `lng` (float).

Forwards the image to `ai_service`, stores the result as a `road_damage`
risk signal + audit row in `model_predictions`.

**Response**
```json
{
  "model_version": "heuristic-fallback-v0",
  "detections": [
    { "class": "pothole", "confidence": 0.71, "bbox_norm": null }
  ],
  "max_severity": 4,
  "risk_signal_id": 812
}
```
`model_version` starts with `heuristic-fallback-v0` until real YOLOv8
weights are placed in `ai_service/weights/best.pt` — after that it will
read `yolov8-roaddamage-v1` (or whatever version string you set in
`train.py`'s output).

---

## `GET /api/analytics/summary`

Dashboard headline numbers: totals by category, average severity by type.

## `GET /api/analytics/risk-by-area`

Coarse lat/lng-grid bucketed hotspot table (top 50 by signal count).
`grid_size_deg` query param (default `0.01`, ≈1.1km) controls bucket size.

---

## `ai_service` (internal, normally called via the backend proxy above)

- `GET /health` → `{"status": "ok", "real_weights_loaded": true|false}`
- `POST /predict` → `multipart/form-data: file` → `{model_version, detections}`
