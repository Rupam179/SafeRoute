"""
SafeRoute Risk Engine
======================

This module is the composite risk-scoring algorithm described in the
project plan (Section 3.2 / 17 of the mentoring transcript):

    composite_risk = w1 * road_damage_score
                    + w2 * accident_score
                    + w3 * safety_score
                    + w4 * time_of_day_score

Each sub-score is computed by:
  1. Sampling the candidate route's polyline at fixed spacing
     (see services/geo_utils.sample_route_points).
  2. For every sample point, querying PostGIS for active risk_signals of
     the relevant `type` within `risk_search_radius_m` metres
     (ST_DWithin on a GEOGRAPHY column — real great-circle distance,
     not flat-earth approximation).
  3. Turning "how many signals, how severe, how close" into a 0-100
     sub-score using severity-weighted density.

This keeps the algorithm fully explainable: every route's score can be
traced back to specific rows in `risk_signals`, which is exactly what lets
the UI show "Safest: 12% longer, 40% less black-spot exposure" instead of
an opaque number.

NOTE ON THE "AI" IN THIS FILE:
This scoring function itself is a transparent, hand-designed weighted
formula — not a black-box model — by design (see project plan Section 27/28:
"the AI's job is perception, not the whole decision"). The machine-learning
component of SafeRoute is the road-damage detector (ai_service/), whose
output becomes `risk_signals` rows of type='road_damage' and is consumed
here like any other signal. This separation is a deliberate, defensible
architecture decision — document it in your report.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.services.geo_utils import decode_polyline, sample_route_points

# Severity is stored 1-5; this converts to a 0-1 multiplier per hit.
SEVERITY_WEIGHT = {1: 0.2, 2: 0.4, 3: 0.6, 4: 0.8, 5: 1.0}

# A route with this many severity-weighted "hits" per sample point is
# treated as maximally risky (100) for that sub-score. Tune this constant
# against your real, populated dataset once you have real signal density —
# document whatever value you land on and why in your evaluation report.
SATURATION_HITS_PER_SAMPLE = 1.5


@dataclass
class SubScore:
    score: float           # 0-100
    hit_count: int
    signal_ids: list[int] = field(default_factory=list)


def _query_nearby_signals(
    db: Session, sample_points: list[tuple[float, float]], signal_type: str
) -> list[dict]:
    """
    For every sample point on the route, find active risk_signals of
    `signal_type` within the configured search radius. Returns raw rows
    (deduplicated by id) with severity, so the caller can aggregate.
    """
    if not sample_points:
        return []

    # Build a single query using UNNEST of the sample points for efficiency
    # instead of N round-trips — this matters once the risk_signals table
    # has tens of thousands of rows.
    lats = [p[0] for p in sample_points]
    lngs = [p[1] for p in sample_points]

    sql = text("""
        SELECT DISTINCT rs.id, rs.severity, rs.meta, rs.time_of_day
        FROM risk_signals rs
        JOIN LATERAL unnest(
            :lats::float8[], :lngs::float8[]
        ) AS pt(lat, lng) ON TRUE
        WHERE rs.type = :signal_type
          AND rs.is_active = TRUE
          AND ST_DWithin(
                rs.geom,
                ST_MakePoint(pt.lng, pt.lat)::geography,
                :radius_m
              )
    """)

    rows = db.execute(
        sql,
        {
            "lats": lats,
            "lngs": lngs,
            "signal_type": signal_type,
            "radius_m": settings.risk_search_radius_m,
        },
    ).mappings().all()

    return [dict(r) for r in rows]


def _score_from_signals(rows: list[dict], num_samples: int) -> SubScore:
    if num_samples == 0:
        return SubScore(score=0.0, hit_count=0)

    weighted_hits = sum(SEVERITY_WEIGHT.get(r["severity"], 0.5) for r in rows)
    density = weighted_hits / num_samples  # weighted hits per sample point
    score = min(100.0, (density / SATURATION_HITS_PER_SAMPLE) * 100.0)

    return SubScore(
        score=round(score, 1),
        hit_count=len(rows),
        signal_ids=[r["id"] for r in rows],
    )


def _time_of_day_score(hour: int, rows_night_sensitive: list[dict]) -> float:
    """
    Simple, explainable rule-based time weighting rather than a learned
    model (deliberately — see project scope boundaries). Night hours carry
    a flat risk premium, further increased if this route already has
    poorly-lit / crowd-flagged segments.
    """
    is_night = hour >= 20 or hour < 6
    base = 55.0 if is_night else 15.0

    poor_lighting_hits = sum(
        1 for r in rows_night_sensitive
        if r.get("meta", {}).get("lighting") == "poor"
    )
    bump = min(30.0, poor_lighting_hits * 6.0) if is_night else 0.0

    return round(min(100.0, base + bump), 1)


def score_route(
    db: Session,
    encoded_geometry: str,
    departure_hour: int,
) -> dict:
    """
    Scores a single OSRM candidate route. Returns a dict matching the
    RiskBreakdown schema plus supporting counts for the UI.
    """
    points = decode_polyline(encoded_geometry, precision=6)
    samples = sample_route_points(points, settings.route_sample_spacing_m)
    n = len(samples)

    damage_rows = _query_nearby_signals(db, samples, "road_damage")
    accident_rows = _query_nearby_signals(db, samples, "accident_blackspot")
    safety_rows = _query_nearby_signals(db, samples, "crowd_safety_report")
    lighting_rows = _query_nearby_signals(db, samples, "lighting")

    damage = _score_from_signals(damage_rows, n)
    accident = _score_from_signals(accident_rows, n)
    safety = _score_from_signals(safety_rows + lighting_rows, n)
    time_score = _time_of_day_score(departure_hour, lighting_rows)

    composite = (
        settings.weight_road_damage * damage.score
        + settings.weight_accident * accident.score
        + settings.weight_safety * safety.score
        + settings.weight_time_of_day * time_score
    )

    return {
        "road_damage_score": damage.score,
        "accident_score": accident.score,
        "safety_score": safety.score,
        "time_of_day_score": time_score,
        "composite_risk": round(composite, 1),
        "signal_counts": {
            "road_damage": damage.hit_count,
            "accident_blackspot": accident.hit_count,
            "crowd_safety_report": len(safety_rows),
            "lighting": len(lighting_rows),
        },
        "_blackspot_count": accident.hit_count,
        "_damage_count": damage.hit_count,
    }


def rank_routes(scored_routes: list[dict]) -> list[dict]:
    """
    Takes a list of {distance_m, duration_s, geometry, risk: {...}} dicts
    and labels them fastest / balanced / safest.

    - fastest  = minimum duration
    - safest   = minimum composite_risk
    - balanced = minimises a normalised combination of time and risk
                 (equal weight, both scaled 0-1 across the candidate set)
    If there are only 1-2 candidate routes, labels degrade gracefully
    (e.g. the same route can't be both fastest and safest unless it
    genuinely is — in that case we still return 3 distinct labels but
    they may point at the same underlying route).
    """
    if not scored_routes:
        return []

    durations = [r["duration_s"] for r in scored_routes]
    risks = [r["risk"]["composite_risk"] for r in scored_routes]
    d_min, d_max = min(durations), max(durations)
    r_min, r_max = min(risks), max(risks)

    def norm(val, lo, hi):
        return 0.0 if hi == lo else (val - lo) / (hi - lo)

    fastest_idx = durations.index(d_min)
    safest_idx = risks.index(r_min)

    balanced_idx = min(
        range(len(scored_routes)),
        key=lambda i: 0.5 * norm(durations[i], d_min, d_max)
                    + 0.5 * norm(risks[i], r_min, r_max)
    )

    labeled = []
    for label, idx in (("fastest", fastest_idx), ("balanced", balanced_idx), ("safest", safest_idx)):
        r = scored_routes[idx]
        labeled.append({**r, "label": label})

    return labeled


def build_comparison_note(labeled_routes: list[dict]) -> str:
    """Generates the human-readable trade-off sentence for the UI, e.g.
    'Safest route is 12% longer but shows 40% less accident/damage exposure
    than the fastest route.' This is the explainability layer the project
    plan calls for."""
    by_label = {r["label"]: r for r in labeled_routes}
    fastest = by_label.get("fastest")
    safest = by_label.get("safest")

    same_route = (
        fastest and safest
        and fastest["duration_s"] == safest["duration_s"]
        and fastest["risk"]["composite_risk"] == safest["risk"]["composite_risk"]
    )
    if not fastest or not safest or same_route:
        return "Only one distinct route was found for this trip — no meaningful trade-off to compare yet."

    if fastest["duration_s"] == 0 or fastest["risk"]["composite_risk"] == 0:
        return "Comparison unavailable for this route pair."

    time_pct = round(
        ((safest["duration_s"] - fastest["duration_s"]) / fastest["duration_s"]) * 100
    )
    risk_pct = round(
        ((fastest["risk"]["composite_risk"] - safest["risk"]["composite_risk"])
         / fastest["risk"]["composite_risk"]) * 100
    )

    time_phrase = f"{time_pct}% longer" if time_pct >= 0 else f"{abs(time_pct)}% faster"
    risk_phrase = f"{risk_pct}% lower risk" if risk_pct >= 0 else f"{abs(risk_pct)}% higher risk"

    return f"Safest route is {time_phrase} but has {risk_phrase} than the fastest route."
