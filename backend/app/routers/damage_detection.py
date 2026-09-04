import json

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas import DamageDetectionResult

router = APIRouter(prefix="/api/damage-detection", tags=["damage-detection"])

# maps YOLO damage classes -> 1-5 severity used by risk_signals
CLASS_SEVERITY = {
    "longitudinal_crack": 2,
    "transverse_crack": 2,
    "alligator_crack": 3,
    "pothole": 4,
    "rutting": 3,
    "other_corruption": 2,
}


@router.post("", response_model=DamageDetectionResult)
async def detect_damage(
    file: UploadFile = File(...),
    lat: float = Form(...),
    lng: float = Form(...),
    db: Session = Depends(get_db),
):
    """
    Forwards the image to the AI microservice (ai_service/), which runs the
    trained YOLOv8 road-damage model. The detections are then written into
    risk_signals as type='road_damage' so they immediately participate in
    route risk scoring — this is the AI -> risk-engine integration point
    described in the project plan (Section 27).
    """
    image_bytes = await file.read()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                f"{settings.ai_service_url}/predict",
                files={"file": (file.filename, image_bytes, file.content_type)},
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"AI service unavailable: {e}")

    result = resp.json()
    detections = result.get("detections", [])
    model_version = result.get("model_version", "unknown")

    max_severity = 1
    for d in detections:
        max_severity = max(max_severity, CLASS_SEVERITY.get(d.get("class"), 2))

    risk_signal_id = None
    if detections:
        risk_signal_id = db.execute(
            text("""
                INSERT INTO risk_signals (geom, type, severity, source, meta)
                VALUES (
                    ST_MakePoint(:lng, :lat)::geography, 'road_damage', :severity,
                    :source, CAST(:meta AS jsonb)
                ) RETURNING id
            """),
            {
                "lat": lat, "lng": lng, "severity": max_severity,
                "source": model_version,
                "meta": json.dumps({"detections": detections}),
            },
        ).scalar()

        db.execute(
            text("""
                INSERT INTO model_predictions (geom, image_ref, model_version, predictions, max_severity, risk_signal_id)
                VALUES (ST_MakePoint(:lng, :lat)::geography, :image_ref, :mv, CAST(:preds AS jsonb), :sev, :sid)
            """),
            {
                "lat": lat, "lng": lng, "image_ref": file.filename,
                "mv": model_version, "preds": json.dumps({"detections": detections}),
                "sev": max_severity, "sid": risk_signal_id,
            },
        )
        db.commit()

    return DamageDetectionResult(
        model_version=model_version,
        detections=detections,
        max_severity=max_severity,
        risk_signal_id=risk_signal_id,
    )
