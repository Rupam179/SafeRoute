"""
Geometry helpers used by the risk engine.

OSRM returns route geometry as an encoded polyline (precision 5 by default,
we request precision 6 for accuracy). We decode it to a list of (lat, lng)
points, then sample points at fixed spacing along the route so we can query
PostGIS for nearby risk signals without having to test every single vertex.
"""
from __future__ import annotations

import math
import polyline as polyline_lib


def decode_polyline(encoded: str, precision: int = 6) -> list[tuple[float, float]]:
    """Returns list of (lat, lng)."""
    return polyline_lib.decode(encoded, precision=precision)


def haversine_m(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """Great-circle distance in metres between two (lat, lng) points."""
    lat1, lng1 = p1
    lat2, lng2 = p2
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = (math.sin(d_phi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def sample_route_points(
    points: list[tuple[float, float]], spacing_m: float
) -> list[tuple[float, float]]:
    """
    Walk along the polyline and emit a point roughly every `spacing_m` metres.
    This gives us an even, resolution-independent set of "road segment"
    checkpoints regardless of how many raw vertices OSRM returned.
    """
    if not points:
        return []

    sampled = [points[0]]
    accumulated = 0.0

    for i in range(1, len(points)):
        seg_len = haversine_m(points[i - 1], points[i])
        accumulated += seg_len
        if accumulated >= spacing_m:
            sampled.append(points[i])
            accumulated = 0.0

    if sampled[-1] != points[-1]:
        sampled.append(points[-1])

    return sampled
