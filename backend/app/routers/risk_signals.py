from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import RiskSignalOut

router = APIRouter(prefix="/api/risk-signals", tags=["risk-signals"])


@router.get("", response_model=list[RiskSignalOut])
def list_risk_signals(
    db: Session = Depends(get_db),
    type: Optional[str] = Query(None, description="Filter by signal type"),
    bbox: Optional[str] = Query(
        None,
        description="min_lng,min_lat,max_lng,max_lat — restrict to current map viewport"
    ),
    limit: int = Query(2000, le=10000),
):
    """Powers the map's risk layers (accident black spots, road damage,
    crowd safety reports, lighting). Supports viewport bounding-box
    filtering so the frontend only fetches what's currently visible."""
    sql = "SELECT id, ST_Y(geom::geometry) AS lat, ST_X(geom::geometry) AS lng, type, severity, source, meta, time_of_day FROM risk_signals WHERE is_active = TRUE"
    params: dict = {}

    if type:
        sql += " AND type = :type"
        params["type"] = type

    if bbox:
        try:
            min_lng, min_lat, max_lng, max_lat = [float(x) for x in bbox.split(",")]
            sql += """ AND ST_Within(
                geom::geometry,
                ST_MakeEnvelope(:min_lng, :min_lat, :max_lng, :max_lat, 4326)
            )"""
            params.update(min_lng=min_lng, min_lat=min_lat, max_lng=max_lng, max_lat=max_lat)
        except ValueError:
            pass

    sql += " LIMIT :limit"
    params["limit"] = limit

    rows = db.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]
