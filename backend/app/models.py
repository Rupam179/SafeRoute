import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import (
    Column, BigInteger, SmallInteger, String, Boolean, DateTime,
    ForeignKey, Text, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(String, nullable=False, default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RiskSignal(Base):
    __tablename__ = "risk_signals"

    id = Column(BigInteger, primary_key=True)
    geom = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    type = Column(String, nullable=False)
    severity = Column(SmallInteger, nullable=False)
    source = Column(String, nullable=False)
    meta = Column(JSONB, default={})
    time_of_day = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)


class CrowdReport(Base):
    __tablename__ = "crowd_reports"

    id = Column(BigInteger, primary_key=True)
    geom = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    reporter_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    lighting = Column(String, default="unknown")
    activity_level = Column(String, default="unknown")
    incident_report = Column(Boolean, default=False)
    notes = Column(Text)
    reported_at_hour = Column(SmallInteger)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    risk_signal_id = Column(BigInteger, ForeignKey("risk_signals.id", ondelete="SET NULL"))


class RouteQuery(Base):
    __tablename__ = "route_queries"

    id = Column(BigInteger, primary_key=True)
    origin = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    destination = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    origin_label = Column(String)
    destination_label = Column(String)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    result_summary = Column(JSONB)


class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    id = Column(BigInteger, primary_key=True)
    geom = Column(Geography(geometry_type="POINT", srid=4326))
    image_ref = Column(String)
    model_version = Column(String, nullable=False)
    predictions = Column(JSONB, nullable=False)
    max_severity = Column(SmallInteger)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    risk_signal_id = Column(BigInteger, ForeignKey("risk_signals.id", ondelete="SET NULL"))
