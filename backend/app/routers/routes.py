from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import RouteRequest, RouteResponse, RankedRoute, RiskBreakdown
from app.services import osrm_client, risk_engine

router = APIRouter(prefix="/api/routes", tags=["routes"])


@router.post("", response_model=RouteResponse)
async def find_routes(req: RouteRequest, db: Session = Depends(get_db)):
    try:
        candidates = await osrm_client.get_candidate_routes(
            req.origin_lat, req.origin_lng, req.destination_lat, req.destination_lng
        )
    except osrm_client.OSRMError as e:
        raise HTTPException(status_code=502, detail=str(e))

    if not candidates:
        raise HTTPException(status_code=404, detail="No route found between these points.")

    hour = req.departure_hour if req.departure_hour is not None else datetime.now().hour

    scored = []
    for c in candidates:
        risk = risk_engine.score_route(db, c["geometry"], hour)
        scored.append({
            "geometry": c["geometry"],
            "distance_m": c["distance_m"],
            "duration_s": c["duration_s"],
            "risk": risk,
        })

    labeled = risk_engine.rank_routes(scored)
    note = risk_engine.build_comparison_note(labeled)

    # Log the query for analytics / evaluation (Section 10 of the plan)
    result = db.execute(
        text("""
            INSERT INTO route_queries (origin, destination, origin_label, destination_label, result_summary)
            VALUES (
                ST_MakePoint(:o_lng, :o_lat)::geography,
                ST_MakePoint(:d_lng, :d_lat)::geography,
                :o_label, :d_label, :summary
            )
            RETURNING id
        """),
        {
            "o_lat": req.origin_lat, "o_lng": req.origin_lng,
            "d_lat": req.destination_lat, "d_lng": req.destination_lng,
            "o_label": req.origin_label, "d_label": req.destination_label,
            "summary": _summary_json(labeled),
        },
    )
    query_id = result.scalar()
    db.commit()

    ranked_out = [
        RankedRoute(
            label=r["label"],
            distance_km=round(r["distance_m"] / 1000, 2),
            duration_min=round(r["duration_s"] / 60, 1),
            risk=RiskBreakdown(
                road_damage_score=r["risk"]["road_damage_score"],
                accident_score=r["risk"]["accident_score"],
                safety_score=r["risk"]["safety_score"],
                time_of_day_score=r["risk"]["time_of_day_score"],
                composite_risk=r["risk"]["composite_risk"],
                signal_counts=r["risk"]["signal_counts"],
            ),
            geometry=r["geometry"],
            blackspot_count=r["risk"]["_blackspot_count"],
            damage_count=r["risk"]["_damage_count"],
        )
        for r in labeled
    ]

    return RouteResponse(query_id=query_id, routes=ranked_out, comparison_note=note)


def _summary_json(labeled_routes):
    import json
    return json.dumps([
        {
            "label": r["label"],
            "duration_s": r["duration_s"],
            "distance_m": r["distance_m"],
            "composite_risk": r["risk"]["composite_risk"],
        }
        for r in labeled_routes
    ])
