# 🛣️ SafeRoute

**An AI-powered, risk-aware navigation system for road safety in India.**
B.Tech CSE (AI) Final Year Project — combines computer-vision road-damage
detection, public accident data, and a crowd-sourced personal-safety layer
into a single composite risk score that ranks routes as **Fastest**,
**Balanced**, and **Safest** — not just shortest.

This repository is a **working, runnable scaffold**, not a slide-deck
concept: the routing pipeline, PostGIS-backed risk engine, crowd-report
system, analytics dashboard, and AI integration point all function
end-to-end today with synthetic seed data. Your team's job over the
8-month build is to replace the synthetic data with real public datasets
and swap the placeholder detector for your trained YOLOv8 model — the
architecture and integration points are already built so that swap
requires no structural rework.

---

## 1. Quick start (5 minutes)

Requirements: Docker + Docker Compose.

```bash
git clone <your-repo-url> saferoute
cd saferoute
cp .env.example .env

# 1. One-time: prepare OSRM routing data for your city/region
#    (default: West Bengal, covers Kolkata — change the URL for your city,
#    see scripts/setup_osrm.sh)
bash scripts/setup_osrm.sh

# 2. Start everything
docker compose up --build -d

# 3. Wait ~15s for Postgres to finish initialising, then seed demo data
docker compose exec backend python -c "print('backend up')"
pip install psycopg2-binary
python db/seed.py --city kolkata

# 4. Open the app
#    Frontend:      http://localhost:8080
#    Backend docs:  http://localhost:8000/docs
#    AI service:    http://localhost:8500/health
```

You should now be able to click two points on the map inside Kolkata and
get Fastest / Balanced / Safest route options with real risk scores
computed against the seeded synthetic data.

> **Nothing to demo yet without OSRM set up?** The backend and frontend
> still run without OSRM — you just can't fetch routes until
> `scripts/setup_osrm.sh` has been run once. Everything else (risk
> layers, crowd reports, damage detection, dashboard) works immediately.

---

## 2. What's actually implemented vs. what your team builds

Being explicit about this distinction is itself good engineering practice
— put it in your report's "Scope & Status" section.

| Component | Status in this scaffold |
|---|---|
| PostGIS schema (`risk_signals`, crowd reports, route logs, model predictions) | ✅ Complete, extensible |
| Risk-scoring engine (composite weighted formula, PostGIS spatial queries) | ✅ Complete, unit-tested, real logic |
| OSRM integration (multi-route candidates → risk scoring → ranking) | ✅ Complete — needs your OSRM data prepared (`scripts/setup_osrm.sh`) |
| Crowd-report API + immediate risk-signal promotion | ✅ Complete |
| Analytics dashboard (summary stats, signal breakdown, hotspot table) | ✅ Complete |
| Frontend (map, route comparison, report form, dashboard) | ✅ Complete, functional |
| AI damage-detection API contract + fallback heuristic | ✅ Complete — heuristic is clearly labelled, **not a real detector** |
| **Trained YOLOv8 road-damage model** | ❌ Your team's core ML deliverable — see `ai_service/app/train.py` |
| **Real accident/crime datasets** (MoRTH, NCRB, data.gov.in) | ❌ Your team's data pipeline — see `docs/DATA_PIPELINE.md` |
| Auth (login/JWT) | ⚠️ `users` table exists; endpoints not wired — add if your team needs per-user report history |
| Production deployment (live URL) | ⚠️ Docker Compose works locally/VPS; see `docs/DEPLOYMENT.md` for Render/Railway |

---

## 3. Folder structure

```
saferoute/
├── docker-compose.yml          # orchestrates db + osrm + backend + ai_service + frontend
├── .env.example
├── scripts/
│   └── setup_osrm.sh           # one-time OSM extract → OSRM data prep
├── db/
│   ├── init.sql                # PostGIS schema (runs automatically on first db start)
│   └── seed.py                 # synthetic demo data generator
├── backend/                    # FastAPI — routing, risk engine, crowd reports, analytics
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py            # risk weights live here — document any changes
│   │   ├── models.py / schemas.py
│   │   ├── routers/             # one file per API area
│   │   └── services/
│   │       ├── risk_engine.py   # <- the core "AI/ML research contribution" logic
│   │       ├── osrm_client.py
│   │       └── geo_utils.py
│   └── tests/
├── ai_service/                  # separate microservice — road damage detection
│   ├── app/
│   │   ├── main.py
│   │   ├── inference.py         # auto-switches: real YOLOv8 if weights present, else heuristic
│   │   └── train.py             # full fine-tuning recipe for RDD2022 + your photos
│   └── weights/                 # put best.pt here (gitignored — see weights/README.md)
├── frontend/                    # React + Leaflet + Recharts
│   └── src/
│       ├── App.jsx
│       └── components/
└── docs/
    ├── ARCHITECTURE.md
    ├── API.md
    ├── DATA_PIPELINE.md
    ├── DEPLOYMENT.md
    ├── MODEL_EVALUATION.md      # fill this in with your REAL numbers
    └── VIVA_PREP.md             # anticipated examiner questions + strong answers
```

---

## 4. How the risk score actually works (read this before your viva)

For a candidate route, the backend:

1. Decodes the route's polyline into points, then samples it every
   `route_sample_spacing_m` (default 150m) to get evenly-spaced checkpoints
   — this makes scoring independent of how many raw vertices OSRM returned.
2. For each checkpoint, queries `risk_signals` in PostGIS using
   `ST_DWithin(geom, point, radius)` — real great-circle distance, per
   signal type (`road_damage`, `accident_blackspot`, `crowd_safety_report`,
   `lighting`).
3. Converts "how many signals, how severe, how close" into a 0–100
   sub-score per category (severity-weighted hit density).
4. Combines sub-scores into one composite risk score using documented,
   configurable weights (`backend/app/config.py`):

   ```
   composite_risk = 0.35 × road_damage_score
                   + 0.30 × accident_score
                   + 0.20 × safety_score
                   + 0.15 × time_of_day_score
   ```

5. Ranks all candidate routes by time and by risk, and labels them
   **Fastest** (min time), **Safest** (min risk), **Balanced** (best
   normalised trade-off between the two).
6. Generates the explainability sentence — *"Safest route is 12% longer
   but has 40% lower risk than the fastest route"* — directly from the
   underlying numbers, not a canned template.

This is a transparent, hand-designed formula, not a black-box model —
deliberately. The machine-learning component is the road-damage detector;
its output becomes ordinary `road_damage` rows in `risk_signals` and is
consumed by this same pipeline like any other signal. See
`backend/app/services/risk_engine.py` for the fully-commented implementation
and `docs/ARCHITECTURE.md` for the full data flow diagram.

---

## 5. What makes this stand out for a final-year submission

- **It's a real, running system**, not screenshots glued into a report —
  examiners can open the live app and click through it.
- **The risk-scoring algorithm is explainable and testable.** It has unit
  tests (`backend/tests/test_risk_engine.py`) and every score traces back
  to specific database rows — you can answer "why is this route riskier?"
  with actual evidence, live, in your viva.
- **Clean separation between AI perception and rule-based decision logic**
  — a deliberate, defensible architecture choice that shows engineering
  maturity, not just model-fitting.
- **Honest about placeholders.** The AI fallback detector is clearly
  labelled `heuristic-fallback-v0` everywhere (API responses, UI, database
  `source` column) so it can never accidentally be presented as your
  trained model's output.
- **Extensible-by-design database** (`risk_signals` generic table) — you
  can add new risk types later without schema changes.
- **Deployable in one command.** `docker compose up` — a live, clickable
  demo URL is one of your grading rubric's explicit requirements.

---

## 6. Team workflow

Follow the 8-month phased plan from your project document. Suggested first
sprint using this scaffold:

1. Everyone: run Quick Start above, confirm the full stack works locally.
2. Frontend owner: adjust `DEFAULT_CENTER` in `App.jsx` to your city,
   polish styling, extend `RouteSearchForm` with a proper geocoding
   search box (Nominatim) instead of manual pin drops.
3. Backend/DB owner: start replacing `db/seed.py`'s synthetic black-spot
   data with real MoRTH/NCRB/data.gov.in data — see `docs/DATA_PIPELINE.md`.
4. AI/ML lead (you): start `ai_service/app/train.py` on RDD2022 while
   the team collects local photos in parallel (Weeks 4–8, don't leave it
   to the end).
5. Everyone: keep a running decision log (see project plan Section 6) —
   `docs/DECISION_LOG.md` is stubbed for this.

See `docs/API.md` for the full endpoint contract so frontend/backend work
can proceed in parallel without blocking each other.

---

## 7. License / academic use

Built as a final-year project scaffold. Use, modify, and extend freely for
your submission. Cite the original public data sources (MoRTH, NCRB,
data.gov.in, RDD2022, SDNET2018, OpenStreetMap, OSRM) in your report per
their respective terms.
