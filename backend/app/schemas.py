from datetime import datetime
from typing import Optional, Literal, Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------
class RouteRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    origin_label: Optional[str] = None
    destination_label: Optional[str] = None
    departure_hour: Optional[int] = Field(
        default=None, ge=0, le=23,
        description="0-23. If omitted, current server hour is used for time-of-day weighting."
    )


class RiskBreakdown(BaseModel):
    road_damage_score: float
    accident_score: float
    safety_score: float
    time_of_day_score: float
    composite_risk: float
    signal_counts: dict[str, int]


class RankedRoute(BaseModel):
    label: Literal["fastest", "balanced", "safest"]
    distance_km: float
    duration_min: float
    risk: RiskBreakdown
    geometry: str  # encoded polyline (Google/OSRM polyline6 format)
    blackspot_count: int
    damage_count: int


class RouteResponse(BaseModel):
    query_id: int
    routes: list[RankedRoute]
    comparison_note: str


# ---------------------------------------------------------------------------
# Risk signals
# ---------------------------------------------------------------------------
class RiskSignalOut(BaseModel):
    id: int
    lat: float
    lng: float
    type: str
    severity: int
    source: str
    meta: dict[str, Any] = {}
    time_of_day: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Crowd reports
# ---------------------------------------------------------------------------
class CrowdReportCreate(BaseModel):
    lat: float
    lng: float
    lighting: Literal["good", "moderate", "poor", "unknown"] = "unknown"
    activity_level: Literal["high", "medium", "low", "unknown"] = "unknown"
    incident_report: bool = False
    notes: Optional[str] = None
    reported_at_hour: Optional[int] = Field(default=None, ge=0, le=23)


class CrowdReportOut(BaseModel):
    id: int
    lat: float
    lng: float
    lighting: str
    activity_level: str
    incident_report: bool
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Damage detection (proxied to AI service)
# ---------------------------------------------------------------------------
class DamageDetectionResult(BaseModel):
    model_version: str
    detections: list[dict[str, Any]]
    max_severity: int
    risk_signal_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
class AnalyticsSummary(BaseModel):
    total_risk_signals: int
    total_crowd_reports: int
    total_road_damage_detections: int
    total_accident_blackspots: int
    total_route_queries: int
    signals_by_type: dict[str, int]
    avg_severity_by_type: dict[str, float]
