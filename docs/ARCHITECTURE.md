# SafeRoute — Architecture

## 1. System diagram

```
                              ┌─────────────┐
                              │    USER     │
                              └──────┬──────┘
                                     │
                                     ▼
                       ┌─────────────────────────┐
                       │   FRONTEND (React +     │
                       │   Leaflet + Recharts)    │
                       │   nginx:80 in prod       │
                       └────────────┬────────────┘
                                     │ REST (JSON)
                                     ▼
                       ┌─────────────────────────┐
                       │   BACKEND (FastAPI)      │
                       │   :8000                  │
                       │  routers/  services/     │
                       └───┬──────────┬───────────┘
                           │          │
             ┌─────────────┘          └─────────────┐
             ▼                                       ▼
   ┌───────────────────┐                   ┌───────────────────┐
   │  OSRM (:5000)      │                   │  AI SERVICE (:8500)│
   │  candidate routes  │                   │  road damage       │
   │  from OSM data      │                   │  detection (YOLOv8)│
   └────────────────────┘                   └───────────────────┘
             │                                       │
             │  route geometry                       │  detections
             ▼                                       ▼
                       ┌─────────────────────────┐
                       │   RISK ENGINE            │
                       │   (backend/app/services/ │
                       │    risk_engine.py)        │
                       └────────────┬────────────┘
                                     │ ST_DWithin spatial queries
                                     ▼
                       ┌─────────────────────────┐
                       │  PostgreSQL + PostGIS     │
                       │  risk_signals             │
                       │  crowd_reports             │
                       │  route_queries              │
                       │  model_predictions           │
                       └─────────────────────────┘
```

## 2. Request lifecycle: "find a route"

1. Frontend sends `POST /api/routes` with origin/destination lat-lng.
2. Backend calls OSRM (`services/osrm_client.py`) with `alternatives=true`
   → gets 1-3 geometrically distinct candidate routes.
3. For each candidate, `services/risk_engine.score_route()`:
   - decodes the polyline,
   - samples points every 150m along it,
   - queries PostGIS for nearby `risk_signals` per type,
   - computes the weighted composite score.
4. `rank_routes()` labels the candidates fastest / balanced / safest.
5. `build_comparison_note()` generates the trade-off sentence.
6. The query and its result summary are logged to `route_queries` for
   later evaluation (Section 10 of the project plan).
7. Response returns to the frontend, which renders all three route
   polylines on the Leaflet map and the comparison cards in the sidebar.

## 3. Request lifecycle: "submit a road photo"

1. Frontend sends `POST /api/damage-detection` (multipart: image + lat/lng).
2. Backend forwards the raw image bytes to `ai_service` at `POST /predict`.
3. `ai_service/app/inference.py` checks for `weights/best.pt`:
   - if present → real YOLOv8 inference,
   - if absent → heuristic fallback (clearly labelled `heuristic-fallback-v0`).
4. Backend receives detections, computes a severity, and writes:
   - one `risk_signals` row (`type='road_damage'`) so it's immediately
     usable by the next route-scoring call,
   - one `model_predictions` row (raw audit trail for evaluation).
5. Any subsequent `POST /api/routes` request that passes near this point
   will now reflect the new damage signal in its risk score — no restart,
   no batch job, immediate feedback.

## 4. Why a generic `risk_signals` table instead of one table per risk type

Adding a new risk category later (e.g. `flood_prone`, `construction_zone`)
requires zero schema migration — just insert rows with a new `type` value
and, if needed, a new case in `risk_engine.score_route()`. This is the
extensibility property called out in the original project plan (Section 3.2)
and is worth highlighting explicitly in your architecture defence.

## 5. Why the risk formula is a hand-designed weighted sum, not a trained model

Three reasons, all worth stating plainly in your report:

1. **Explainability.** Every score must be traceable to specific signals
   for the UI's trade-off explanation to be honest and useful.
2. **Data scarcity.** A learned ranking model would need labelled
   "ground truth" route-safety data that doesn't exist for a student
   project — training one would mean fitting noise.
3. **Scope discipline.** The project's genuine ML contribution is the
   road-damage *detector* (a well-posed, well-datasetted computer vision
   problem). Layering a second, under-determined ML model on top of that
   for ranking would dilute both the AI story and your ability to defend it.

## 6. Extending the system

| Task | Where to change |
|---|---|
| Add a new risk-signal type | `db/init.sql` CHECK constraint + `risk_engine.py` scoring |
| Adjust risk weights | `backend/app/config.py` (env-overridable) |
| Add authentication | Wire up `users` table with a new `routers/auth.py` (JWT scaffolding libs already in requirements.txt) |
| Swap in real YOLOv8 weights | Drop `best.pt` into `ai_service/weights/`, restart container — no code change |
| Add a new map layer | `frontend/src/components/MapView.jsx`, extend `RISK_COLORS` |
| Change target city | Update `DEFAULT_CENTER` in `App.jsx` + re-run `scripts/setup_osrm.sh` with your region's `.osm.pbf` |
