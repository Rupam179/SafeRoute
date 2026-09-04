from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CrowdReportCreate, CrowdReportOut

router = APIRouter(prefix="/api/crowd-reports", tags=["crowd-reports"])


def _severity_from_report(report: CrowdReportCreate) -> int:
    """Turns a free-form crowd report into a 1-5 severity value that the
    risk engine can consume like any other signal."""
    score = 1
    if report.lighting == "poor":
        score += 1
    if report.activity_level == "low":
        score += 1
    if report.incident_report:
        score += 2
    return min(5, score)


@router.post("", response_model=CrowdReportOut, status_code=201)
def submit_report(report: CrowdReportCreate, db: Session = Depends(get_db)):
    hour = report.reported_at_hour if report.reported_at_hour is not None else datetime.now().hour

    # 1. Insert the raw crowd report (kept verbatim for the record / dashboard)
    row = db.execute(
        text("""
            INSERT INTO crowd_reports
                (geom, lighting, activity_level, incident_report, notes, reported_at_hour)
            VALUES
                (ST_MakePoint(:lng, :lat)::geography, :lighting, :activity_level,
                 :incident_report, :notes, :hour)
            RETURNING id, ST_Y(geom::geometry) AS lat, ST_X(geom::geometry) AS lng,
                      lighting, activity_level, incident_report, notes, created_at
        """),
        {
            "lat": report.lat, "lng": report.lng,
            "lighting": report.lighting, "activity_level": report.activity_level,
            "incident_report": report.incident_report, "notes": report.notes,
            "hour": hour,
        },
    ).mappings().one()

    # 2. Promote it into risk_signals so it immediately feeds the risk engine
    signal_type = "lighting" if report.lighting != "unknown" else "crowd_safety_report"
    severity = _severity_from_report(report)
    time_of_day = "night" if (hour >= 20 or hour < 6) else "day"

    signal_row = db.execute(
        text("""
            INSERT INTO risk_signals (geom, type, severity, source, meta, time_of_day)
            VALUES (
                ST_MakePoint(:lng, :lat)::geography, :type, :severity, 'crowd',
                jsonb_build_object(
                    'lighting', :lighting, 'activity_level', :activity_level,
                    'incident_report', :incident_report
                ),
                :time_of_day
            )
            RETURNING id
        """),
        {
            "lat": report.lat, "lng": report.lng, "type": signal_type,
            "severity": severity, "lighting": report.lighting,
            "activity_level": report.activity_level,
            "incident_report": report.incident_report, "time_of_day": time_of_day,
        },
    ).scalar()

    db.execute(
        text("UPDATE crowd_reports SET risk_signal_id = :sid WHERE id = :rid"),
        {"sid": signal_row, "rid": row["id"]},
    )
    db.commit()

    return dict(row)


@router.get("", response_model=list[CrowdReportOut])
def list_reports(db: Session = Depends(get_db), limit: int = 500):
    rows = db.execute(
        text("""
            SELECT id, ST_Y(geom::geometry) AS lat, ST_X(geom::geometry) AS lng,
                   lighting, activity_level, incident_report, notes, created_at
            FROM crowd_reports ORDER BY created_at DESC LIMIT :limit
        """),
        {"limit": limit},
    ).mappings().all()
    return [dict(r) for r in rows]
